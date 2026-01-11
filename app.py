"""
FastAPI application for Real-Time Malware Detection Gateway.
Provides REST API endpoints for scanning URLs/files and managing threats.
"""

import os
import sys
import time
import logging
import asyncio
import psutil
import torch
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from sse_starlette.sse import EventSourceResponse
import uvicorn

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from settings import settings, reload_settings
from models import (
    URLScanRequest, FileScanRequest, ThresholdUpdateRequest,
    ScanResult, ThreatListResponse, ThreatStats, ThreatLog, HealthStatus,
    SettingsStatus, ThresholdResponse, ErrorResponse, RiskLevel,
    EarlyTerminationSettings
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


# =====================================================================
# Model Info & Resource Monitoring
# =====================================================================

@app.get("/model-info", tags=["System"])
async def get_model_info():
    """
    Get detailed model information including device, cores, and memory.
    """
    detector = get_detector_instance()
    
    # Get CPU info
    cpu_count = psutil.cpu_count(logical=True)
    cpu_count_physical = psutil.cpu_count(logical=False) or cpu_count
    cpu_freq = psutil.cpu_freq()
    cpu_percent = psutil.cpu_percent(interval=0.1)
    
    # Get memory info
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    # Get GPU info if available
    gpu_info = None
    if torch.cuda.is_available():
        gpu_info = {
            "available": True,
            "device_name": torch.cuda.get_device_name(0),
            "device_index": torch.cuda.current_device(),
            "total_memory_gb": torch.cuda.get_device_properties(0).total_memory / (1024**3),
            "allocated_memory_gb": torch.cuda.memory_allocated(0) / (1024**3),
            "cached_memory_gb": torch.cuda.memory_reserved(0) / (1024**3),
            "compute_capability": f"{torch.cuda.get_device_capability(0)[0]}.{torch.cuda.get_device_capability(0)[1]}",
            "force_gpu_enabled": settings.force_gpu
        }
    else:
        gpu_info = {
            "available": False,
            "device_name": None,
            "total_memory_gb": None,
            "allocated_memory_gb": None,
            "cached_memory_gb": None,
            "compute_capability": None,
            "force_gpu_enabled": settings.force_gpu
        }
    
    # Model parameters
    model_loaded = detector.model is not None
    total_params = sum(p.numel() for p in detector.model.parameters()) if model_loaded else 0
    trainable_params = sum(p.numel() for p in detector.model.parameters() if p.requires_grad) if model_loaded else 0
    
    return {
        "device": str(detector.device),
        "device_type": "GPU" if torch.cuda.is_available() else "CPU",
        "cpu": {
            "logical_cores": cpu_count,
            "physical_cores": cpu_count_physical,
            "frequency_mhz": cpu_freq.current if cpu_freq else None,
            "cpu_percent": cpu_percent
        },
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "percent_used": memory.percent,
            "swap_total_gb": round(swap.total / (1024**3), 2),
            "swap_used_gb": round(swap.used / (1024**3), 2)
        },
        "gpu": gpu_info,
        "model": {
            "loaded": model_loaded,
            "model_path": settings.model_path,
            "total_parameters": total_params,
            "trainable_parameters": trainable_params,
            "vocab_size": settings.vocab_size,
            "d_model": settings.d_model,
            "nhead": settings.nhead,
            "num_layers": settings.num_layers,
            "dim_feedforward": settings.dim_feedforward,
            "dropout": settings.dropout
        },
        "uptime_seconds": time.time() - _start_time,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# =====================================================================
# Notification System (Server-Sent Events)
# =====================================================================

# Notification queue for SSE
_notification_queue: Optional[asyncio.Queue] = None

# Log queue for live log streaming
_log_queue: Optional[asyncio.Queue] = None
_log_buffer: list = []
_MAX_LOG_BUFFER = 1000


def get_log_queue() -> asyncio.Queue:
    """Get or create the log queue."""
    global _log_queue
    if _log_queue is None:
        _log_queue = asyncio.Queue()
    return _log_queue


async def enqueue_log(level: str, message: str, source: str = "backend"):
    """Add a log entry to the queue for streaming."""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "message": message,
        "source": source
    }
    
    # Add to buffer for new connections
    global _log_buffer
    _log_buffer.append(log_entry)
    if len(_log_buffer) > _MAX_LOG_BUFFER:
        _log_buffer = _log_buffer[-_MAX_LOG_BUFFER:]
    
    # Enqueue for streaming
    queue = get_log_queue()
    try:
        await queue.put(log_entry)
    except asyncio.QueueFull:
        pass  # Queue is full, skip this log


# Custom log handler to capture logs
class AppLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        try:
            message = self.format(record)
            level = record.levelname
            source = "backend"
            asyncio.create_task(enqueue_log(level, message, source))
        except Exception:
            pass


# Install log handler
_log_handler = AppLogHandler()
logging.getLogger().addHandler(_log_handler)


def get_notification_queue() -> asyncio.Queue:
    """Get or create the notification queue."""
    global _notification_queue
    if _notification_queue is None:
        _notification_queue = asyncio.Queue()
    return _notification_queue


async def notify_clients(event_type: str, data: dict):
    """Send notification to all connected clients."""
    queue = get_notification_queue()
    await queue.put({
        "event": event_type,
        "data": data
    })


@app.get("/notifications/stream", tags=["Notifications"])
async def notifications_stream():
    """
    Server-Sent Events endpoint for real-time notifications.
    
    Events:
    - threat_detected: When a threat is detected and blocked
    - scan_completed: When a scan completes
    - model_status: Model loading/status updates
    - system_alert: System-level alerts
    """
    async def event_generator():
        queue = get_notification_queue()
        try:
            while True:
                # Wait for notification with timeout
                try:
                    notification = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": notification["event"],
                        "data": notification["data"]
                    }
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield {
                        "event": "heartbeat",
                        "data": {"timestamp": datetime.now(timezone.utc).isoformat()}
                    }
        except asyncio.CancelledError:
            pass
    
    return EventSourceResponse(event_generator())


@app.post("/notifications/test", tags=["Notifications"])
async def send_test_notification():
    """Send a test notification to all connected clients."""
    await notify_clients("test", {
        "message": "Test notification",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    return {"status": "sent"}


# =====================================================================
# Live Log Streaming (Server-Sent Events)
# =====================================================================

@app.get("/logs/stream", tags=["Logs"])
async def logs_stream():
    """
    Server-Sent Events endpoint for live log streaming.
    
    Streams log entries from both backend and frontend sources.
    New clients receive recent log history on connection.
    
    Events:
    - log: Log entry from backend or frontend
    """
    async def event_generator():
        queue = get_log_queue()
        
        # Send buffered logs first (recent history)
        for log_entry in _log_buffer[-100:]:  # Send last 100 logs
            yield {
                "event": "log",
                "data": log_entry
            }
        
        try:
            while True:
                # Wait for log with timeout
                try:
                    log_entry = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": "log",
                        "data": log_entry
                    }
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield {
                        "event": "heartbeat",
                        "data": {"timestamp": datetime.now(timezone.utc).isoformat()}
                    }
        except asyncio.CancelledError:
            pass
    
    return EventSourceResponse(event_generator())


@app.get("/logs", tags=["Logs"])
async def get_logs():
    """
    Get recent log entries (non-streaming).
    
    Returns the most recent log entries from the buffer.
    """
    return {
        "logs": _log_buffer[-500:],  # Return last 500 logs
        "total": len(_log_buffer)
    }


@app.post("/logs/test", tags=["Logs"])
async def send_test_log():
    """Send a test log entry."""
    await enqueue_log("INFO", "Test log entry from backend", "backend")
    return {"status": "sent"}


@app.post("/logs/frontend", tags=["Logs"])
async def receive_frontend_log(data: dict):
    """
    Receive and queue a log entry from the frontend.
    
    This endpoint allows the frontend to send log entries
    to be displayed in the shared log viewer.
    """
    level = data.get("level", "INFO")
    message = data.get("message", "")
    await enqueue_log(level, message, "frontend")
    return {"status": "received"}


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
async def scan_url(request: URLScanRequest, early_termination: bool = False):
    """
    Scan a URL for malware.
    
    Stream-downloads the URL and performs malware detection mid-download.
    Early termination occurs if a threat is detected.
    
    - **url**: URL to scan (HTTP/HTTPS only)
    - **block_on_detection**: Block access if threat detected (default: true)
    - **early_termination**: Enable fast block mode - stop at 1KB for high confidence (default: false)
    """
    detector = get_detector_instance()
    
    url_str = str(request.url)
    
    logger.info(f"Scanning URL: {url_str} (early_termination={early_termination})")
    
    try:
        result = detector.scan_url(
            url=url_str,
            block_on_detection=request.block_on_detection,
            early_termination=early_termination if early_termination else None
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
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    except Exception as e:
        logger.error(f"URL scan error: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@app.post("/scan/file", response_model=ScanResult, tags=["Scanning"])
async def scan_file(
    file: UploadFile = File(...),
    block_on_detection: bool = True,
    early_termination: bool = False
):
    """
    Upload and scan a file for malware.
    
    Analyzes file content in streaming mode with rolling window.
    
    - **file**: File to upload and scan
    - **block_on_detection**: Block access if threat detected (default: true)
    - **early_termination**: Enable fast block mode - stop at 1KB for high confidence (default: false)
    """
    detector = get_detector_instance()
    
    filename = file.filename or "uploaded_file"
    logger.info(f"Scanning file: {filename} (early_termination={early_termination})")
    
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
            block_on_detection=block_on_detection,
            early_termination=early_termination if early_termination else None
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
            timestamp=datetime.now(timezone.utc).isoformat()
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
                timestamp=threat_dict.get('timestamp', datetime.now(timezone.utc).isoformat()),
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
    distribution_list = threat_manager.get_risk_distribution()
    
    distribution = {
        "BENIGN": 0,
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0,
        "CRITICAL": 0
    }
    
    for item in distribution_list:
        risk_level = item.get("risk_level", "BENIGN")
        count = item.get("count", 0)
        distribution[risk_level] = count
    
    return distribution


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


@app.get("/settings/early-termination", response_model=EarlyTerminationSettings, tags=["Settings"])
async def get_early_termination_settings():
    """
    Get current early termination (fast block) settings.
    
    When enabled, scanning stops immediately when a high-confidence threat
    is detected (default: 95% confidence after 1KB scanned).
    This provides faster blocking for obvious malware.
    """
    return EarlyTerminationSettings(
        enabled=settings.early_termination_enabled,
        threshold=settings.early_termination_threshold,
        min_bytes=settings.early_termination_min_bytes
    )


@app.post("/settings/early-termination", tags=["Settings"])
async def update_early_termination_settings(request: EarlyTerminationSettings):
    """
    Update early termination (fast block) settings.
    
    - **enabled**: Enable early termination for fast blocking
    - **threshold**: Confidence threshold for early termination (0.0 to 1.0)
    - **min_bytes**: Minimum bytes to scan before allowing early termination
    
    When enabled, threats above the threshold are blocked immediately after
    scanning the minimum bytes. This is faster but may miss nuanced malware.
    For full analysis, keep disabled (default).
    """
    old_settings = {
        "enabled": settings.early_termination_enabled,
        "threshold": settings.early_termination_threshold,
        "min_bytes": settings.early_termination_min_bytes
    }
    
    # Update settings
    settings.early_termination_enabled = request.enabled
    settings.early_termination_threshold = request.threshold
    settings.early_termination_min_bytes = request.min_bytes
    
    # Update detector
    detector = get_detector_instance()
    detector.early_termination_enabled = request.enabled
    detector.early_termination_threshold = request.threshold
    detector.early_termination_min_bytes = request.min_bytes
    
    logger.info(f"Early termination settings updated: {old_settings} -> {request}")
    
    return {
        "old_settings": old_settings,
        "new_settings": request.model_dump(),
        "status": "updated"
    }


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