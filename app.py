"""
FastAPI application for Real-Time Malware Detection Gateway.
Provides REST API endpoints for scanning URLs/files and managing threats.
"""

import os
import sys
import time
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from settings import settings, reload_settings
from models import (
    URLScanRequest, FileScanRequest, ThresholdUpdateRequest,
    ScanResult, ThreatListResponse, ThreatStats, ThreatLog, HealthStatus,
    SettingsStatus, ThresholdResponse, ErrorResponse, RiskLevel
)
from detector import get_detector, StreamingDetector
from threat_manager import get_threat_manager, ThreatManager
from database import get_database, ThreatDatabase

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
_detector: Optional[StreamingDetector] = None
_threat_manager: Optional[ThreatManager] = None
_database: Optional[ThreatDatabase] = None
_start_time: float = time.time()


def get_detector_instance() -> StreamingDetector:
    """Get detector singleton."""
    global _detector
    if _detector is None:
        _detector = get_detector()
    return _detector


def get_threat_manager_instance() -> ThreatManager:
    """Get threat manager singleton."""
    global _threat_manager
    if _threat_manager is None:
        _threat_manager = get_threat_manager()
    return _threat_manager


def get_database_instance() -> ThreatDatabase:
    """Get database singleton."""
    global _database
    if _database is None:
        _database = get_database()
    return _database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global _start_time
    _start_time = time.time()
    
    # Startup
    logger.info("Starting Malware Detection Gateway...")
    
    # Initialize components
    try:
        get_detector_instance()
        logger.info("Detector initialized")
    except Exception as e:
        logger.error(f"Failed to initialize detector: {e}")
    
    try:
        get_threat_manager_instance()
        logger.info("Threat manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize threat manager: {e}")
    
    try:
        get_database_instance()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    logger.info("Malware Detection Gateway started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Malware Detection Gateway...")


# Create FastAPI application
app = FastAPI(
    title="Real-Time Malware Detection Gateway",
    description="Production-grade malware detection system using Transformer model with streaming byte-level analysis",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# Exception Handlers
# =====================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "errors": errors
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": str(exc)
        }
    )


# =====================================================================
# Health & Status Endpoints
# =====================================================================

@app.get("/health", response_model=HealthStatus, tags=["System"])
async def health_check():
    """
    System health check endpoint.
    
    Returns system status including model, database, and resource metrics.
    """
    detector = get_detector_instance()
    db = get_database_instance()
    
    # Calculate memory usage
    import psutil
    process = psutil.Process()
    memory_mb = process.memory_info().rss / (1024 * 1024)
    
    # Determine overall status
    model_loaded = detector.model is not None
    db_connected = db.get_total_count() >= 0
    
    overall_status = "healthy" if (model_loaded and db_connected) else "degraded"
    
    return HealthStatus(
        status=overall_status,
        model={
            "loaded": model_loaded,
            "model_path": settings.model_path,
            "device": str(detector.device),
            "parameters": sum(p.numel() for p in detector.model.parameters()) if model_loaded else None,
            "vocab_size": settings.vocab_size,
            "d_model": settings.d_model,
            "num_layers": settings.num_layers
        },
        database={
            "connected": db_connected,
            "path": settings.database_path,
            "total_threats": db.get_total_count()
        },
        uptime_seconds=time.time() - _start_time,
        memory_usage_mb=round(memory_mb, 2)
    )


@app.get("/settings", response_model=SettingsStatus, tags=["System"])
async def get_settings():
    """Get current system settings."""
    return SettingsStatus(
        confidence_threshold=settings.confidence_threshold,
        chunk_size=settings.chunk_size,
        window_size=settings.window_size,
        temperature=settings.temperature,
        risk_levels=settings.risk_levels
    )


# =====================================================================
# Scanning Endpoints
# =====================================================================

@app.post("/scan/url", response_model=ScanResult, tags=["Scanning"])
async def scan_url(request: URLScanRequest):
    """
    Scan a URL for malware.
    
    Stream-downloads the URL and performs malware detection mid-download.
    Early termination occurs if a threat is detected.
    
    - **url**: URL to scan (HTTP/HTTPS only)
    - **block_on_detection**: Block access if threat detected (default: true)
    """
    detector = get_detector_instance()
    
    url_str = str(request.url)
    
    logger.info(f"Scanning URL: {url_str}")
    
    try:
        result = detector.scan_url(
            url=url_str,
            block_on_detection=request.block_on_detection
        )
        
        return ScanResult(
            source=result.source,
            source_type=result.source_type,
            probability=result.probability,
            risk_level=RiskLevel(result.risk_level),
            bytes_scanned=result.bytes_scanned,
            blocked=result.blocked,
            scan_time_ms=result.scan_time_ms,
            status=result.status,
            details=result.details,
            timestamp=datetime.utcnow().isoformat()
        )
    
    except Exception as e:
        logger.error(f"URL scan error: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@app.post("/scan/file", response_model=ScanResult, tags=["Scanning"])
async def scan_file(
    file: UploadFile = File(...),
    block_on_detection: bool = True
):
    """
    Upload and scan a file for malware.
    
    Analyzes file content in streaming mode with rolling window.
    
    - **file**: File to upload and scan
    - **block_on_detection**: Block access if threat detected (default: true)
    """
    detector = get_detector_instance()
    
    filename = file.filename or "uploaded_file"
    logger.info(f"Scanning file: {filename}")
    
    try:
        # Read file content
        content = await file.read()
        
        # Check size limit
        if len(content) > settings.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed ({settings.max_file_size} bytes)"
            )
        
        # Scan
        result = detector.scan_file(
            file_data=content,
            filename=filename,
            block_on_detection=block_on_detection
        )
        
        return ScanResult(
            source=result.source,
            source_type=result.source_type,
            probability=result.probability,
            risk_level=RiskLevel(result.risk_level),
            bytes_scanned=result.bytes_scanned,
            blocked=result.blocked,
            scan_time_ms=result.scan_time_ms,
            status=result.status,
            details=result.details,
            timestamp=datetime.utcnow().isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File scan error: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


# =====================================================================
# Threat Management Endpoints
# =====================================================================

@app.get("/threats", response_model=ThreatListResponse, tags=["Threats"])
async def get_threats(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    risk_level: Optional[str] = Query(default=None),
    source_type: Optional[str] = Query(default=None)
):
    """
    Get threat logs with pagination and filtering.
    
    - **limit**: Maximum number of results (1-1000)
    - **offset**: Number of results to skip
    - **risk_level**: Filter by risk level (BENIGN, LOW, MEDIUM, HIGH, CRITICAL)
    - **source_type**: Filter by source type (URL, FILE)
    """
    threat_manager = get_threat_manager_instance()
    
    threats_data = threat_manager.get_threats(
        limit=limit,
        offset=offset,
        risk_level=risk_level,
        source_type=source_type
    )
    
    total = len(threats_data)
    
    # Convert dictionaries to ThreatLog objects
    threats = []
    for threat_dict in threats_data:
        try:
            threats.append(ThreatLog(**threat_dict))
        except Exception as e:
            logger.warning(f"Failed to convert threat dict to ThreatLog: {e}")
            # Create a minimal ThreatLog with required fields
            threats.append(ThreatLog(
                id=threat_dict.get('id', 0),
                source=threat_dict.get('source', 'unknown'),
                source_type=threat_dict.get('source_type', 'FILE'),
                probability=threat_dict.get('probability', 0.0),
                bytes_scanned=threat_dict.get('bytes_scanned', 0),
                risk_level=RiskLevel(threat_dict.get('risk_level', 'BENIGN')),
                timestamp=threat_dict.get('timestamp', datetime.utcnow().isoformat()),
                details=threat_dict.get('details'),
                blocked=threat_dict.get('blocked', False)
            ))
    
    return ThreatListResponse(
        threats=threats,
        total=total,
        limit=limit,
        offset=offset
    )


@app.get("/threats/stats", response_model=ThreatStats, tags=["Threats"])
async def get_threat_stats():
    """Get aggregated threat statistics."""
    threat_manager = get_threat_manager_instance()
    stats = threat_manager.get_stats()
    
    db_stats = stats.get("database_stats", {})
    
    # Convert None values to 0 for integer fields
    def safe_int(value, default=0):
        return int(value) if value is not None else default
    
    return ThreatStats(
        total=safe_int(db_stats.get("total")),
        critical=safe_int(db_stats.get("critical")),
        high=safe_int(db_stats.get("high")),
        medium=safe_int(db_stats.get("medium")),
        low=safe_int(db_stats.get("low")),
        benign=safe_int(db_stats.get("benign")),
        total_bytes_scanned=safe_int(db_stats.get("total_bytes_scanned"))
    )


@app.get("/threats/distribution", tags=["Threats"])
async def get_threat_distribution():
    """Get threat distribution by risk level."""
    threat_manager = get_threat_manager_instance()
    return threat_manager.get_risk_distribution()


@app.get("/threats/{threat_id}", tags=["Threats"])
async def get_threat_by_id(threat_id: int):
    """Get a specific threat by ID."""
    db = get_database_instance()
    threat = db.get_threat_by_id(threat_id)
    
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found")
    
    return threat


# =====================================================================
# Settings Endpoints
# =====================================================================

@app.post("/settings/threshold", response_model=ThresholdResponse, tags=["Settings"])
async def update_threshold(request: ThresholdUpdateRequest):
    """
    Update detection confidence threshold dynamically.
    
    - **threshold**: New threshold value (0.0 to 1.0)
    
    Higher values mean fewer false positives but more false negatives.
    """
    old_threshold = settings.confidence_threshold
    
    # Update in settings
    settings.confidence_threshold = request.threshold
    
    # Update in detector
    detector = get_detector_instance()
    detector.set_threshold(request.threshold)
    
    # Update in threat manager
    threat_manager = get_threat_manager_instance()
    threat_manager.update_threshold(request.threshold)
    
    logger.info(f"Threshold updated: {old_threshold} -> {request.threshold}")
    
    return ThresholdResponse(
        old_threshold=old_threshold,
        new_threshold=request.threshold,
        status="updated"
    )


# =====================================================================
# Statistics & Metrics
# =====================================================================

@app.get("/stats", tags=["Statistics"])
async def get_stats():
    """Get detector and system statistics."""
    detector = get_detector_instance()
    threat_manager = get_threat_manager_instance()
    
    return {
        "detector": detector.get_stats(),
        "threat_manager": threat_manager.get_stats(),
        "uptime_seconds": time.time() - _start_time
    }


# =====================================================================
# Root Endpoint
# =====================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Real-Time Malware Detection Gateway",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "scan_url": "/scan/url",
            "scan_file": "/scan/file",
            "threats": "/threats",
            "threats_stats": "/threats/stats",
            "settings": "/settings"
        }
    }


# =====================================================================
# Main Entry Point
# =====================================================================

def main():
    """Run the FastAPI application."""
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()