"""
Threat logging and risk assessment manager.
Handles risk classification and structured logging.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from database import get_database, logger
from models import RiskLevel, ScanStatus
from settings import settings

# Configure structured JSON logging
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


class ThreatManager:
    """
    Manages threat detection, classification, and logging.
    Provides risk assessment and structured alert generation.
    """
    
    # Risk level thresholds (probability ranges)
    RISK_LEVELS = {
        (0.0, 0.3): "BENIGN",
        (0.3, 0.5): "LOW",
        (0.5, 0.7): "MEDIUM",
        (0.7, 0.9): "HIGH",
        (0.9, 1.0): "CRITICAL"
    }
    
    # Alert colors for terminal output
    ALERT_COLORS = {
        "BENIGN": "\033[92m",   # Green
        "LOW": "\033[93m",      # Yellow
        "MEDIUM": "\033[93m",   # Yellow
        "HIGH": "\033[91m",     # Red
        "CRITICAL": "\033[95m"  # Magenta
    }
    
    # Alert symbols (ASCII-safe versions to avoid encoding issues on Windows)
    ALERT_SYMBOLS = {
        "BENIGN": "[OK]",
        "LOW": "[INFO]",
        "MEDIUM": "[WARN]",
        "HIGH": "[ALERT]",
        "CRITICAL": "[CRITICAL]"
    }
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize threat manager.
        
        Args:
            db_path: Optional database path override
        """
        self.db_path = db_path or settings.database_path
        self.database = get_database(self.db_path)
        self._setup_logging()
        
        # Statistics
        self.stats = {
            "total_scans": 0,
            "threats_detected": 0,
            "clean_scans": 0,
            "blocked": 0,
            "total_bytes_scanned": 0
        }
        
        logger.info(f"ThreatManager initialized with database: {self.db_path}")
    
    def _setup_logging(self) -> None:
        """Configure structured logging."""
        # Ensure logs directory exists
        logs_dir = Path(settings.logs_dir)
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create threat logger
        self.logger = logging.getLogger('threats')
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # File handler with JSON formatting
        log_file = logs_dir / f"threats_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler with colors
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # JSON formatter for file
        class JSONFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_data = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": record.levelname,
                    "name": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                if record.exc_info:
                    log_data["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_data)
        
        # Standard formatter for console
        class ColoredFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                return record.getMessage()
        
        file_handler.setFormatter(JSONFormatter())
        console_handler.setFormatter(ColoredFormatter())
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def calculate_risk_level(self, probability: float) -> str:
        """
        Calculate risk level from probability.
        
        Args:
            probability: Malware probability (0.0 to 1.0)
            
        Returns:
            Risk level string
        """
        for (low, high), level in self.RISK_LEVELS.items():
            if low <= probability < high:
                return level
        return "CRITICAL" if probability >= 1.0 else "BENIGN"
    
    def get_risk_level_enum(self, probability: float) -> RiskLevel:
        """Get risk level as enum."""
        return RiskLevel(self.calculate_risk_level(probability))
    
    def should_block(self, probability: float) -> bool:
        """
        Determine if source should be blocked based on probability.
        
        Args:
            probability: Malware probability
            
        Returns:
            True if should block
        """
        return probability >= settings.confidence_threshold
    
    def log_threat(
        self,
        source: str,
        source_type: str,
        probability: float,
        bytes_scanned: int,
        scan_time_ms: float,
        details: Optional[Dict[str, Any]] = None,
        blocked: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Log a detected threat.
        
        Args:
            source: URL or filename
            source_type: Type of source
            probability: Malware probability
            bytes_scanned: Bytes processed
            scan_time_ms: Time taken for scan
            details: Additional details
            blocked: Whether access was blocked
            
        Returns:
            Threat result dictionary
        """
        risk_level = self.calculate_risk_level(probability)
        is_blocked = blocked if blocked is not None else self.should_block(probability)
        status = ScanStatus.THREAT_DETECTED if probability >= settings.low_risk_threshold else ScanStatus.CLEAN
        
        # Update statistics
        self.stats["total_scans"] += 1
        self.stats["total_bytes_scanned"] += bytes_scanned
        
        if is_blocked:
            self.stats["threats_detected"] += 1
            self.stats["blocked"] += 1
        else:
            self.stats["clean_scans"] += 1
        
        # Prepare details
        threat_details = {
            "model_confidence": probability,
            "risk_level": risk_level,
            "threshold_used": settings.confidence_threshold,
            **(details or {})
        }
        
        # Log to database
        threat_id = self.database.log_threat(
            source=source,
            source_type=source_type,
            probability=probability,
            bytes_scanned=bytes_scanned,
            risk_level=risk_level,
            details=threat_details,
            blocked=is_blocked,
            scan_time_ms=scan_time_ms,
            status=status.value
        )
        
        # Structured log entry
        log_entry = {
            "threat_id": threat_id,
            "source": source,
            "source_type": source_type,
            "probability": probability,
            "risk_level": risk_level,
            "bytes_scanned": bytes_scanned,
            "blocked": is_blocked,
            "scan_time_ms": scan_time_ms
        }
        
        if is_blocked:
            self.logger.warning(f"THREAT BLOCKED: {json.dumps(log_entry)}")
            self._show_alert(source, probability, risk_level, bytes_scanned, scan_time_ms)
        else:
            self.logger.info(f"Threat logged: {json.dumps(log_entry)}")
        
        return {
            "threat_id": threat_id,
            "source": source,
            "source_type": source_type,
            "probability": probability,
            "risk_level": risk_level,
            "bytes_scanned": bytes_scanned,
            "blocked": is_blocked,
            "scan_time_ms": scan_time_ms,
            "status": status.value
        }
    
    def log_clean(
        self,
        source: str,
        source_type: str,
        probability: float,
        bytes_scanned: int,
        scan_time_ms: float,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log a clean scan result.
        
        Args:
            source: URL or filename
            source_type: Type of source
            probability: Malware probability
            bytes_scanned: Bytes processed
            scan_time_ms: Time taken for scan
            details: Additional details
            
        Returns:
            Log result dictionary
        """
        self.stats["total_scans"] += 1
        self.stats["clean_scans"] += 1
        self.stats["total_bytes_scanned"] += bytes_scanned
        
        scan_details = {
            "model_confidence": probability,
            "risk_level": "BENIGN",
            **(details or {})
        }
        
        threat_id = self.database.log_clean_scan(
            source=source,
            source_type=source_type,
            probability=probability,
            bytes_scanned=bytes_scanned,
            details=scan_details,
            scan_time_ms=scan_time_ms
        )
        
        self.logger.info(f"Clean scan logged: {source} (prob={probability:.4f})")
        
        return {
            "threat_id": threat_id,
            "source": source,
            "source_type": source_type,
            "probability": probability,
            "risk_level": "BENIGN",
            "bytes_scanned": bytes_scanned,
            "blocked": False,
            "scan_time_ms": scan_time_ms,
            "status": "CLEAN"
        }
    
    def _show_alert(
        self,
        source: str,
        probability: float,
        risk_level: str,
        bytes_scanned: int,
        scan_time_ms: float
    ) -> None:
        """Display threat alert in terminal."""
        color = self.ALERT_COLORS.get(risk_level, "\033[0m")
        symbol = self.ALERT_SYMBOLS.get(risk_level, "[WARN]")
        reset = "\033[0m"
        bold = "\033[1m"
        
        border = "=" * 70
        print(f"\n{color}{border}{reset}")
        print(f"{color}{bold}{symbol} MALWARE DETECTION ALERT - {risk_level}{reset}")
        print(f"{color}{border}{reset}")
        print(f"{bold}Source: {source}{reset}")
        print(f"Probability: {probability:.4f} ({probability:.1%})")
        print(f"Bytes Scanned: {bytes_scanned:,}")
        print(f"Scan Time: {scan_time_ms:.2f}ms")
        print(f"{color}{border}{reset}\n")
    
    def get_threats(
        self,
        limit: int = 100,
        offset: int = 0,
        risk_level: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get threat logs.
        
        Args:
            limit: Maximum results
            offset: Results to skip
            risk_level: Filter by risk level
            source_type: Filter by source type
            
        Returns:
            List of threat dictionaries
        """
        return self.database.get_recent_threats(
            limit=limit,
            offset=offset,
            risk_level=risk_level,
            source_type=source_type
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get threat manager statistics.
        
        Returns:
            Statistics dictionary
        """
        db_stats = self.database.get_threat_stats()
        
        return {
            "session_stats": self.stats,
            "database_stats": db_stats,
            "current_threshold": settings.confidence_threshold,
            "risk_distribution": db_stats
        }
    
    def get_risk_distribution(self) -> List[Dict[str, Any]]:
        """
        Get threat distribution by risk level.
        
        Returns:
            List of distribution buckets
        """
        return self.database.get_threat_distribution()
    
    def update_threshold(self, threshold: float) -> Dict[str, Any]:
        """
        Update detection threshold.
        
        Args:
            threshold: New threshold value
            
        Returns:
            Update result
        """
        old_threshold = settings.confidence_threshold
        settings.confidence_threshold = threshold
        
        self.logger.info(f"Threshold updated: {old_threshold} -> {threshold}")
        
        return {
            "old_threshold": old_threshold,
            "new_threshold": threshold,
            "status": "updated"
        }


# Global threat manager instance
threat_manager: Optional[ThreatManager] = None


def get_threat_manager(db_path: Optional[str] = None) -> ThreatManager:
    """
    Get or create threat manager instance.
    
    Args:
        db_path: Optional database path
        
    Returns:
        ThreatManager instance
    """
    global threat_manager
    if threat_manager is None:
        threat_manager = ThreatManager(db_path)
    return threat_manager


def init_threat_manager(db_path: Optional[str] = None) -> ThreatManager:
    """
    Initialize threat manager with given path.
    
    Args:
        db_path: Database file path
        
    Returns:
        Initialized ThreatManager
    """
    global threat_manager
    threat_manager = ThreatManager(db_path)
    return threat_manager


# Convenience function for logging
def log_detection(
    source: str,
    source_type: str,
    probability: float,
    bytes_scanned: int,
    scan_time_ms: float,
    blocked: bool = False,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function to log a detection.
    
    Args:
        source: URL or filename
        source_type: Type of source
        probability: Malware probability
        bytes_scanned: Bytes processed
        scan_time_ms: Time taken
        blocked: Whether blocked
        details: Additional details
        
    Returns:
        Threat result
    """
    manager = get_threat_manager()
    
    if manager.should_block(probability) or blocked:
        return manager.log_threat(
            source=source,
            source_type=source_type,
            probability=probability,
            bytes_scanned=bytes_scanned,
            scan_time_ms=scan_time_ms,
            blocked=blocked,
            details=details
        )
    else:
        return manager.log_clean(
            source=source,
            source_type=source_type,
            probability=probability,
            bytes_scanned=bytes_scanned,
            scan_time_ms=scan_time_ms,
            details=details
        )