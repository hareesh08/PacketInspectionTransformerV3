"""
Configuration management for Real-Time Malware Detection System.
Uses Pydantic BaseSettings for environment variable support.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized configuration for the malware detection gateway.
    All settings can be overridden via environment variables.
    """
    model_config = SettingsConfigDict(
        env_prefix='MALWARE_DETECTOR_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )
    
    # =====================================================================
    # Detection Thresholds
    # =====================================================================
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum probability to classify as threat and block"
    )
    low_risk_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Threshold for LOW risk level"
    )
    medium_risk_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Threshold for MEDIUM risk level"
    )
    high_risk_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Threshold for HIGH risk level"
    )
    critical_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Threshold for CRITICAL risk level"
    )
    
    # =====================================================================
    # Streaming Settings
    # =====================================================================
    chunk_size: int = Field(
        default=512,
        ge=64,
        le=4096,
        description="Bytes per chunk for streaming analysis"
    )
    window_size: int = Field(
        default=1500,
        ge=512,
        le=4096,
        description="Rolling window size for context"
    )
    max_file_size: int = Field(
        default=100 * 1024 * 1024,  # 100MB
        description="Maximum file size for scanning (bytes)"
    )
    download_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Timeout for URL downloads (seconds)"
    )
    
    # =====================================================================
    # Model Settings
    # =====================================================================
    model_path: str = Field(
        default="model/finetuned_best_model.pth",
        description="Path to the pretrained transformer model"
    )
    vocab_size: int = Field(
        default=259,
        description="Vocabulary size (0-255 bytes + padding + mask + unknown)"
    )
    d_model: int = Field(
        default=768,
        description="Model dimension"
    )
    nhead: int = Field(
        default=12,
        description="Number of attention heads"
    )
    num_layers: int = Field(
        default=12,
        description="Number of transformer layers"
    )
    dim_feedforward: int = Field(
        default=3072,
        description="Feedforward dimension"
    )
    temperature: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Temperature scaling for softmax"
    )
    dropout: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="Dropout rate"
    )
    classifier_dropout: float = Field(
        default=0.5,
        ge=0.0,
        le=0.5,
        description="Classifier dropout rate"
    )
    
    # =====================================================================
    # Database Settings
    # =====================================================================
    database_url: str = Field(
        default="sqlite:///threats.db",
        description="Database connection URL"
    )
    database_path: str = Field(
        default="threats.db",
        description="SQLite database file path"
    )
    
    # =====================================================================
    # Server Settings
    # =====================================================================
    host: str = Field(
        default="0.0.0.0",
        description="Server host"
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Server port"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    # =====================================================================
    # Logging Settings
    # =====================================================================
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_format: str = Field(
        default="json",
        description="Log format (json, console)"
    )
    logs_dir: str = Field(
        default="logs",
        description="Directory for log files"
    )
    
    # =====================================================================
    # Security Settings
    # =====================================================================
    api_key: Optional[str] = Field(
        default=None,
        description="API key for authentication (optional)"
    )
    rate_limit_requests: int = Field(
        default=100,
        description="Rate limit per minute"
    )
    
    # =====================================================================
    # Performance Settings
    # =====================================================================
    batch_size: int = Field(
        default=32,
        ge=1,
        le=256,
        description="Batch size for inference"
    )
    max_concurrent_scans: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum concurrent scan operations"
    )
    
    # =====================================================================
    # Risk Level Mapping (computed property)
    # =====================================================================
    @property
    def risk_levels(self) -> dict:
        """Get risk level thresholds as a dictionary."""
        return {
            "BENIGN": (0.0, self.low_risk_threshold),
            "LOW": (self.low_risk_threshold, self.medium_risk_threshold),
            "MEDIUM": (self.medium_risk_threshold, self.high_risk_threshold),
            "HIGH": (self.high_risk_threshold, self.critical_threshold),
            "CRITICAL": (self.critical_threshold, 1.0)
        }
    
    def get_risk_level(self, probability: float) -> str:
        """Determine risk level from probability."""
        for level, (low, high) in self.risk_levels.items():
            if low <= probability < high:
                return level
        return "CRITICAL" if probability >= 1.0 else "BENIGN"
    
    # =====================================================================
    # Utility Methods
    # =====================================================================
    @classmethod
    def from_yaml(cls, config_path: str) -> "Settings":
        """Load settings from YAML configuration file."""
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return cls(**config)
    
    def to_yaml(self, config_path: str) -> None:
        """Save settings to YAML configuration file."""
        import yaml
        config = self.model_dump()
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)


# Global settings instance
settings = Settings()


def reload_settings() -> Settings:
    """Reload settings from environment variables."""
    global settings
    settings = Settings()
    return settings