"""
Pydantic v2 data model for API requests and responses.
Defines schemas for malware detection gateway endpoints.
"""

from datetime import datetime, timezone
from typing import Optional, List, Any, Dict
from enum import Enum
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    field_validator,
    model_validator
)
import re


# =====================================================================
# Enums
# =====================================================================

class RiskLevel(str, Enum):
    """Risk classification levels for detected threats."""
    BENIGN = "BENIGN"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SourceType(str, Enum):
    """Type of source being scanned."""
    URL = "URL"
    FILE = "FILE"


class ScanStatus(str, Enum):
    """Status of a scan operation."""
    CLEAN = "CLEAN"
    THREAT_DETECTED = "THREAT_DETECTED"
    ERROR = "ERROR"
    PENDING = "PENDING"


# =====================================================================
# Request Models
# =====================================================================

class URLScanRequest(BaseModel):
    """Request model for URL scanning endpoint."""
    url: HttpUrl = Field(
        ...,
        description="URL to scan for malware",
        examples=["http://example.com/file.exe"]
    )
    block_on_detection: bool = Field(
        default=True,
        description="Block download if threat detected"
    )
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: HttpUrl) -> HttpUrl:
        """Validate URL scheme and format."""
        if v.scheme not in ('http', 'https'):
            raise ValueError('Only HTTP and HTTPS URLs are allowed')
        return v


class FileScanRequest(BaseModel):
    """Request model for file scanning endpoint."""
    filename: Optional[str] = Field(
        default=None,
        description="Original filename if available"
    )
    block_on_detection: bool = Field(
        default=True,
        description="Block file if threat detected"
    )


class EarlyTerminationSettings(BaseModel):
    """Settings for early termination (fast block) mode."""
    enabled: bool = Field(
        default=False,
        description="Enable early termination - stop scanning when high confidence threat detected"
    )
    threshold: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Probability threshold for early termination (blocks immediately at this confidence)"
    )
    min_bytes: int = Field(
        default=1024,
        ge=64,
        description="Minimum bytes to scan before allowing early termination"
    )


class ThresholdUpdateRequest(BaseModel):
    """Request model for updating detection threshold."""
    threshold: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="New confidence threshold (0.0 to 1.0)",
        examples=[0.7, 0.8]
    )
    
    @field_validator('threshold')
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        """Validate threshold is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Threshold must be between 0.0 and 1.0')
        return v


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of results to return"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of results to skip"
    )


class ThreatFilterParams(BaseModel):
    """Filter parameters for threat queries."""
    risk_level: Optional[RiskLevel] = Field(
        default=None,
        description="Filter by risk level"
    )
    source_type: Optional[SourceType] = Field(
        default=None,
        description="Filter by source type"
    )
    start_time: Optional[datetime] = Field(
        default=None,
        description="Filter threats after this time"
    )
    end_time: Optional[datetime] = Field(
        default=None,
        description="Filter threats before this time"
    )


# =====================================================================
# Response Models
# =====================================================================

class ScanResult(BaseModel):
    """Response model for scan results."""
    source: str = Field(
        ...,
        description="URL or filename that was scanned"
    )
    source_type: SourceType = Field(
        ...,
        description="Type of source scanned"
    )
    probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Malware probability from model"
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Computed risk level"
    )
    bytes_scanned: int = Field(
        ...,
        description="Total bytes processed"
    )
    blocked: bool = Field(
        ...,
        description="Whether the source was blocked"
    )
    scan_time_ms: float = Field(
        ...,
        description="Time taken for scan in milliseconds"
    )
    status: ScanStatus = Field(
        ...,
        description="Scan status"
    )
    details: Optional[dict] = Field(
        default=None,
        description="Additional details about the scan"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the scan was performed"
    )


class ThreatLog(BaseModel):
    """Model for threat log entries from database."""
    id: int = Field(
        ...,
        description="Unique threat log ID"
    )
    source: str = Field(
        ...,
        description="Source URL or filename"
    )
    source_type: SourceType = Field(
        ...,
        description="Type of source"
    )
    probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Malware probability"
    )
    bytes_scanned: int = Field(
        ...,
        description="Bytes processed before detection"
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Risk classification"
    )
    timestamp: datetime = Field(
        ...,
        description="When the threat was detected"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional details about the detection"
    )
    blocked: bool = Field(
        default=False,
        description="Whether access was blocked"
    )
    
    @field_validator('risk_level', mode='before')
    @classmethod
    def validate_risk_level(cls, v):
        """Convert string risk_level to enum."""
        if isinstance(v, str):
            return RiskLevel(v)
        return v
    
    @field_validator('source_type', mode='before')
    @classmethod
    def validate_source_type(cls, v):
        """Convert string source_type to enum."""
        if isinstance(v, str):
            return SourceType(v)
        return v
    
    @field_validator('timestamp', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        """Convert timestamp string to datetime."""
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                return v
        return v
    
    @classmethod
    def from_db_row(cls, row: tuple, columns: tuple) -> "ThreatLog":
        """Create from database row."""
        data = dict(zip(columns, row))
        return cls(**data)


class ThreatStats(BaseModel):
    """Statistics about threat detections."""
    total: int = Field(
        default=0,
        description="Total number of threats"
    )
    critical: int = Field(
        default=0,
        description="Number of CRITICAL threats"
    )
    high: int = Field(
        default=0,
        description="Number of HIGH threats"
    )
    medium: int = Field(
        default=0,
        description="Number of MEDIUM threats"
    )
    low: int = Field(
        default=0,
        description="Number of LOW threats"
    )
    benign: int = Field(
        default=0,
        description="Number of BENIGN classifications"
    )
    total_bytes_scanned: int = Field(
        default=0,
        description="Total bytes processed"
    )


class ThreatListResponse(BaseModel):
    """Response for threat list endpoint."""
    threats: List[ThreatLog] = Field(
        ...,
        description="List of threat logs"
    )
    total: int = Field(
        ...,
        description="Total number of matching threats"
    )
    limit: int = Field(
        ...,
        description="Limit used"
    )
    offset: int = Field(
        ...,
        description="Offset used"
    )


class ThresholdResponse(BaseModel):
    """Response for threshold update."""
    old_threshold: float = Field(
        ...,
        description="Previous threshold value"
    )
    new_threshold: float = Field(
        ...,
        description="New threshold value"
    )
    status: str = Field(
        ...,
        description="Status message"
    )


# =====================================================================
# Health & Status Models
# =====================================================================

class ModelStatus(BaseModel):
    """Status of the ML model."""
    loaded: bool = Field(
        ...,
        description="Whether model is loaded"
    )
    model_path: str = Field(
        ...,
        description="Path to model file"
    )
    device: str = Field(
        ...,
        description="Compute device (cuda/cpu)"
    )
    parameters: Optional[int] = Field(
        default=None,
        description="Total model parameters"
    )
    vocab_size: int = Field(
        ...,
        description="Vocabulary size"
    )
    d_model: int = Field(
        ...,
        description="Model dimension"
    )
    num_layers: int = Field(
        ...,
        description="Number of transformer layers"
    )


class DatabaseStatus(BaseModel):
    """Status of database connection."""
    connected: bool = Field(
        ...,
        description="Whether database is connected"
    )
    path: str = Field(
        ...,
        description="Database file path"
    )
    total_threats: int = Field(
        ...,
        description="Total threats in database"
    )


class HealthStatus(BaseModel):
    """System health status response."""
    status: str = Field(
        ...,
        description="Overall system status"
    )
    model: ModelStatus = Field(
        ...,
        description="Model status"
    )
    database: DatabaseStatus = Field(
        ...,
        description="Database status"
    )
    uptime_seconds: float = Field(
        ...,
        description="Server uptime in seconds"
    )
    memory_usage_mb: float = Field(
        ...,
        description="Current memory usage"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When status was checked"
    )


class SettingsStatus(BaseModel):
    """Current settings status."""
    confidence_threshold: float = Field(
        ...,
        description="Current detection threshold"
    )
    chunk_size: int = Field(
        ...,
        description="Streaming chunk size"
    )
    window_size: int = Field(
        ...,
        description="Rolling window size"
    )
    temperature: float = Field(
        ...,
        description="Temperature scaling value"
    )
    risk_levels: dict = Field(
        ...,
        description="Current risk level thresholds"
    )


# =====================================================================
# Error Models
# =====================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(
        ...,
        description="Error type"
    )
    message: str = Field(
        ...,
        description="Error message"
    )
    details: Optional[dict] = Field(
        default=None,
        description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When error occurred"
    )


class ValidationErrorResponse(BaseModel):
    """Validation error response."""
    error: str = Field(
        default="VALIDATION_ERROR",
        description="Error type"
    )
    message: str = Field(
        ...,
        description="Validation error message"
    )
    field_errors: List[dict] = Field(
        ...,
        description="List of field errors"
    )