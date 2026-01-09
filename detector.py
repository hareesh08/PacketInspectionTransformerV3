"""
Core streaming DPI and model inference logic.
Handles real-time malware detection with streaming byte-level analysis.
"""

import os
import sys
import time
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass
import threading

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import requests
from io import BytesIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settings import settings
from models import RiskLevel, SourceType, ScanStatus

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result of a malware scan."""
    source: str
    source_type: str
    probability: float
    risk_level: str
    bytes_scanned: int
    blocked: bool
    scan_time_ms: float
    status: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "source_type": self.source_type,
            "probability": self.probability,
            "risk_level": self.risk_level,
            "bytes_scanned": self.bytes_scanned,
            "blocked": self.blocked,
            "scan_time_ms": self.scan_time_ms,
            "status": self.status,
            "details": self.details,
            "timestamp": self.timestamp
        }


class PositionalEncoding(nn.Module):
    """Sinusoidal Positional Encoding."""
    
    def __init__(self, d_model: int, max_len: int = 1500):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * 
                           (-torch.log(torch.tensor(10000.0)) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, :x.size(1)]


class PacketTransformer(nn.Module):
    """
    Packet Transformer Encoder for malware detection.
    Based on the architecture from ModelLoader.py.
    """
    
    def __init__(self,
                 vocab_size: int = 259,
                 d_model: int = 768,
                 nhead: int = 12,
                 num_layers: int = 12,
                 dim_feedforward: int = 3072,
                 max_len: int = 1500,
                 dropout: float = 0.1,
                 num_classes: int = 2):
        super().__init__()
        
        # Special token IDs
        self.pad_token_id = 256
        self.mask_token_id = 257
        self.unk_token_id = 258
        self.vocab_size = vocab_size
        self.d_model = d_model
        
        # Embedding layer
        self.embedding = nn.Embedding(vocab_size, d_model)
        
        # Positional encoding
        self.pos_encoder = PositionalEncoding(d_model, max_len)
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            activation='relu'
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers)
        
        # Mean pooling classifier
        self.fc1 = nn.Linear(d_model, 512)
        self.fc2 = nn.Linear(512, 128)
        self.fc3 = nn.Linear(128, num_classes)
        self.dropout = nn.Dropout(dropout)
        
        self._init_weights()
    
    def _init_weights(self) -> None:
        """Initialize weights."""
        nn.init.xavier_uniform_(self.embedding.weight)
        nn.init.xavier_uniform_(self.fc1.weight)
        nn.init.xavier_uniform_(self.fc2.weight)
        nn.init.xavier_uniform_(self.fc3.weight)
        nn.init.zeros_(self.fc1.bias)
        nn.init.zeros_(self.fc2.bias)
        nn.init.zeros_(self.fc3.bias)
    
    def forward(self, 
                src: torch.Tensor,
                src_key_padding_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass through the model.
        
        Args:
            src: Input tensor [batch_size, seq_len]
            src_key_padding_mask: Padding mask
            
        Returns:
            Logits tensor [batch_size, num_classes]
        """
        # Embedding
        x = self.embedding(src) * (self.d_model ** 0.5)
        
        # Positional encoding
        x = self.pos_encoder(x)
        
        # Transformer encoder
        x = self.transformer_encoder(x, src_key_padding_mask=src_key_padding_mask)
        
        # Mean pooling
        x = x.mean(dim=1)
        
        # Classifier
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.fc3(x)
        
        return x
    
    def create_padding_mask(self, src: torch.Tensor) -> torch.Tensor:
        """Create padding mask for variable-length sequences."""
        return src == self.pad_token_id


class StreamingDetector:
    """
    Streaming DPI detector for real-time malware analysis.
    Processes data in chunks with rolling window buffer.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the streaming detector.
        
        Args:
            model_path: Path to pretrained model checkpoint
        """
        self.model_path = model_path or settings.model_path
        
        # Force GPU if available and settings allow
        if torch.cuda.is_available():
            if settings.force_gpu:
                self.device = torch.device('cuda')
                torch.cuda.set_device(settings.gpu_device_id)
                logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
            else:
                self.device = torch.device('cpu')
                logger.info("GPU available but force_gpu is disabled, using CPU")
        else:
            self.device = torch.device('cpu')
            logger.info("No GPU available, using CPU")
        
        # Streaming parameters
        self.chunk_size = settings.chunk_size
        self.window_size = settings.window_size
        self.max_file_size = settings.max_file_size
        self.download_timeout = settings.download_timeout
        self.temperature = settings.temperature
        self.confidence_threshold = settings.confidence_threshold
        
        # Early termination parameters (fast block mode)
        self.early_termination_enabled = settings.early_termination_enabled
        self.early_termination_threshold = settings.early_termination_threshold
        self.early_termination_min_bytes = settings.early_termination_min_bytes
        
        # Model
        self.model: Optional[PacketTransformer] = None
        self._load_model()
        
        # Statistics
        self._lock = threading.Lock()
        self.stats = {
            "total_scans": 0,
            "threats_blocked": 0,
            "total_bytes_scanned": 0,
            "avg_scan_time_ms": 0.0
        }
        
        logger.info(f"StreamingDetector initialized on {self.device}")
    
    def _load_model(self) -> None:
        """Load the pretrained transformer model."""
        try:
            # Create model architecture
            self.model = PacketTransformer(
                vocab_size=settings.vocab_size,
                d_model=settings.d_model,
                nhead=settings.nhead,
                num_layers=settings.num_layers,
                dim_feedforward=settings.dim_feedforward,
                max_len=settings.window_size,
                dropout=settings.dropout,
                num_classes=2
            )
            
            # Load checkpoint if exists
            if os.path.exists(self.model_path):
                try:
                    checkpoint = torch.load(
                        self.model_path,
                        map_location=self.device,
                        weights_only=False
                    )
                    
                    # Get state dict (handle both 'model_state_dict' and direct dict)
                    if 'model_state_dict' in checkpoint:
                        state_dict = checkpoint['model_state_dict']
                    else:
                        state_dict = checkpoint
                    
                    # Remap keys if they have 'transformer.' or 'classifier.' prefix
                    new_state_dict = {}
                    needs_remapping = any(k.startswith('transformer.') or k.startswith('classifier.') for k in state_dict.keys())
                    
                    # Keys to ignore (from pretrained model but not used in downstream model)
                    ignored_keys = {'mlm_decoder.weight', 'mlm_decoder.bias'}
                    
                    if needs_remapping:
                        logger.info("Remapping checkpoint keys to match model architecture...")
                        for key, value in state_dict.items():
                            # Skip ignored keys
                            if key in ignored_keys:
                                continue
                            # Remove 'transformer.' prefix
                            if key.startswith('transformer.'):
                                new_key = key.replace('transformer.', '', 1)
                            # Remove 'classifier.' prefix and map to fc layers
                            elif key.startswith('classifier.'):
                                new_key = key.replace('classifier.', '', 1)
                            else:
                                new_key = key
                            new_state_dict[new_key] = value
                        
                        # Load with strict=False to ignore missing keys
                        self.model.load_state_dict(new_state_dict, strict=False)
                        logger.info("Model weights loaded successfully (some keys ignored)")
                    else:
                        # Load with strict=False to handle extra keys
                        self.model.load_state_dict(state_dict, strict=False)
                        logger.info("Model loaded from checkpoint")
                    
                    logger.info(f"Model loaded from {self.model_path}")
                except Exception as e:
                    logger.warning(f"Could not load model weights: {e}")
                    logger.info("Using randomly initialized model")
            else:
                logger.warning(f"Model file not found: {self.model_path}")
            
            # Move to device and set eval mode
            self.model.to(self.device)
            self.model.eval()
            
            # Count parameters
            total_params = sum(p.numel() for p in self.model.parameters())
            logger.info(f"Model ready: {total_params:,} parameters")
            
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise
    
    def byte_to_token_ids(self, data: bytes) -> List[int]:
        """
        Convert bytes to token IDs (0-255).
        
        Args:
            data: Raw byte data
            
        Returns:
            List of token IDs
        """
        return list(data)
    
    def pad_or_truncate(self, tokens: List[int], length: int) -> List[int]:
        """
        Pad or truncate token list to specified length.
        
        Args:
            tokens: List of token IDs
            length: Target length
            
        Returns:
            Padded/truncated token list
        """
        if len(tokens) < length:
            # Pad with padding token (256)
            tokens = tokens + [self.model.pad_token_id] * (length - len(tokens))
        else:
            # Truncate
            tokens = tokens[:length]
        return tokens
    
    def preprocess(self, data: bytes) -> torch.Tensor:
        """
        Preprocess byte data for model input.
        
        Args:
            data: Raw byte data
            
        Returns:
            Model input tensor [1, seq_len]
        """
        tokens = self.byte_to_token_ids(data)
        tokens = self.pad_or_truncate(tokens, self.window_size)
        tensor = torch.tensor([tokens], dtype=torch.long)
        return tensor.to(self.device)
    
    @torch.no_grad()
    def infer(self, data: bytes) -> float:
        """
        Run model inference on byte data.
        
        Args:
            data: Raw byte data
            
        Returns:
            Malware probability (0.0 to 1.0)
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        # Preprocess
        tensor = self.preprocess(data)
        
        # Create padding mask
        padding_mask = self.model.create_padding_mask(tensor)
        
        # Forward pass
        logits = self.model(tensor, src_key_padding_mask=padding_mask)
        
        # Apply temperature scaling
        scaled_logits = logits / self.temperature
        
        # Get probability of malware (class 1)
        probability = torch.sigmoid(scaled_logits[0, 1]).item()
        
        return probability
    
    def scan_url(
        self,
        url: str,
        block_on_detection: bool = True,
        progress_callback: Optional[Callable[[int, float], None]] = None,
        early_termination: Optional[bool] = None
    ) -> ScanResult:
        """
        Stream-download URL and detect malware mid-download.
        
        Args:
            url: URL to scan
            block_on_detection: Block if threat detected
            progress_callback: Optional callback(bytes_scanned, probability)
            early_termination: Override early termination setting (None = use default)
            
        Returns:
            ScanResult with detection details
        """
        # Use parameter override or default from settings
        use_early_termination = (
            early_termination if early_termination is not None
            else self.early_termination_enabled
        )
        
        start_time = time.perf_counter()
        buffer = bytearray()
        bytes_scanned = 0
        max_probability = 0.0
        early_termination_active = False
        
        logger.info(f"Starting URL scan: {url} (early_termination={use_early_termination})")
        
        try:
            with requests.get(
                url,
                stream=True,
                timeout=self.download_timeout,
                headers={'User-Agent': 'MalwareDetector/1.0'}
            ) as response:
                response.raise_for_status()
                
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if not chunk:
                        break
                    
                    # Add to buffer (rolling window)
                    buffer.extend(chunk)
                    buffer = buffer[-self.window_size:]
                    bytes_scanned += len(chunk)
                    
                    # Check size limit
                    if bytes_scanned > self.max_file_size:
                        logger.warning(f"File size exceeded limit, stopping scan")
                        break
                    
                    # Run inference
                    probability = self.infer(bytes(buffer))
                    max_probability = max(max_probability, probability)
                    
                    # Progress callback
                    if progress_callback:
                        progress_callback(bytes_scanned, probability)
                    
                    # Early termination check (fast block mode)
                    if use_early_termination and bytes_scanned >= self.early_termination_min_bytes:
                        if probability >= self.early_termination_threshold:
                            logger.warning(
                                f"EARLY TERMINATION: Threat detected at {bytes_scanned} bytes "
                                f"(confidence: {probability:.4f})"
                            )
                            early_termination_active = True
                            scan_time_ms = (time.perf_counter() - start_time) * 1000
                            return self._create_blocked_result(
                                url, "URL", probability, bytes_scanned, scan_time_ms,
                                details={"early_termination": True}
                            )
                    
                    # Standard threshold check
                    if probability >= self.confidence_threshold:
                        logger.warning(f"Threat detected mid-download: {probability:.4f}")
                        
                        # Log and return blocked result
                        scan_time_ms = (time.perf_counter() - start_time) * 1000
                        return self._create_blocked_result(
                            url, "URL", probability, bytes_scanned, scan_time_ms
                        )
                
                # Clean scan
                scan_time_ms = (time.perf_counter() - start_time) * 1000
                return self._create_clean_result(
                    url, "URL", max_probability, bytes_scanned, scan_time_ms,
                    details={"early_termination_attempted": early_termination_active}
                )
                
        except requests.RequestException as e:
            scan_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Download failed: {e}")
            return ScanResult(
                source=url,
                source_type="URL",
                probability=0.0,
                risk_level="BENIGN",
                bytes_scanned=bytes_scanned,
                blocked=False,
                scan_time_ms=scan_time_ms,
                status="ERROR",
                details={"error": str(e)}
            )
    
    def scan_file(
        self,
        file_data: bytes,
        filename: str = "uploaded_file",
        block_on_detection: bool = True,
        early_termination: Optional[bool] = None
    ) -> ScanResult:
        """
        Scan file data in streaming mode.
        
        Args:
            file_data: Raw file bytes
            filename: Original filename
            block_on_detection: Block if threat detected
            early_termination: Override early termination setting (None = use default)
            
        Returns:
            ScanResult with detection details
        """
        # Use parameter override or default from settings
        use_early_termination = (
            early_termination if early_termination is not None
            else self.early_termination_enabled
        )
        
        start_time = time.perf_counter()
        buffer = bytearray()
        bytes_scanned = 0
        max_probability = 0.0
        early_termination_active = False
        
        logger.info(f"Starting file scan: {filename} ({len(file_data)} bytes) (early_termination={use_early_termination})")
        
        # Process in chunks
        for i in range(0, len(file_data), self.chunk_size):
            chunk = file_data[i:i + self.chunk_size]
            
            # Add to buffer (rolling window)
            buffer.extend(chunk)
            buffer = buffer[-self.window_size:]
            bytes_scanned += len(chunk)
            
            # Run inference
            probability = self.infer(bytes(buffer))
            max_probability = max(max_probability, probability)
            
            # Early termination check (fast block mode)
            if use_early_termination and bytes_scanned >= self.early_termination_min_bytes:
                if probability >= self.early_termination_threshold:
                    logger.warning(
                        f"EARLY TERMINATION: Threat detected at {bytes_scanned} bytes "
                        f"(confidence: {probability:.4f})"
                    )
                    early_termination_active = True
                    scan_time_ms = (time.perf_counter() - start_time) * 1000
                    return self._create_blocked_result(
                        filename, "FILE", probability, bytes_scanned, scan_time_ms,
                        details={"early_termination": True}
                    )
            
            # Standard threshold check
            if probability >= self.confidence_threshold:
                logger.warning(f"Threat detected in file: {probability:.4f}")
                
                scan_time_ms = (time.perf_counter() - start_time) * 1000
                return self._create_blocked_result(
                    filename, "FILE", probability, bytes_scanned, scan_time_ms
                )
        
        # Clean scan
        scan_time_ms = (time.perf_counter() - start_time) * 1000
        return self._create_clean_result(
            filename, "FILE", max_probability, bytes_scanned, scan_time_ms,
            details={"early_termination_attempted": early_termination_active}
        )
    
    async def _send_notification(self, event_type: str, data: dict):
        """Send notification to connected clients via SSE."""
        try:
            from app import notify_clients
            await notify_clients(event_type, data)
        except Exception:
            pass  # Notification system may not be initialized
    
    def _create_blocked_result(
        self,
        source: str,
        source_type: str,
        probability: float,
        bytes_scanned: int,
        scan_time_ms: float,
        details: Optional[Dict[str, Any]] = None
    ) -> ScanResult:
        """Create a blocked scan result."""
        risk_level = settings.get_risk_level(probability)
        
        with self._lock:
            self.stats["total_scans"] += 1
            self.stats["threats_blocked"] += 1
            self.stats["total_bytes_scanned"] += bytes_scanned
        
        # Import here to avoid circular imports
        from threat_manager import get_threat_manager
        threat_manager = get_threat_manager()
        
        # Log to threat manager
        result = threat_manager.log_threat(
            source=source,
            source_type=source_type,
            probability=probability,
            bytes_scanned=bytes_scanned,
            scan_time_ms=scan_time_ms,
            blocked=True
        )
        
        # Create notification data
        notification_data = {
            "source": source,
            "source_type": source_type,
            "probability": probability,
            "risk_level": risk_level,
            "bytes_scanned": bytes_scanned,
            "scan_time_ms": scan_time_ms,
            "timestamp": datetime.utcnow().isoformat() if hasattr(datetime, 'utcnow') else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        
        # Schedule notification (will be executed if async context is available)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._send_notification("threat_detected", notification_data))
        except RuntimeError:
            pass  # No event loop
        
        # Merge details
        result_details = {"log_id": result.get("threat_id")}
        if details:
            result_details.update(details)
        
        return ScanResult(
            source=source,
            source_type=source_type,
            probability=probability,
            risk_level=risk_level,
            bytes_scanned=bytes_scanned,
            blocked=True,
            scan_time_ms=scan_time_ms,
            status="THREAT_DETECTED",
            details=result_details
        )
    
    def _create_clean_result(
        self,
        source: str,
        source_type: str,
        probability: float,
        bytes_scanned: int,
        scan_time_ms: float,
        details: Optional[Dict[str, Any]] = None
    ) -> ScanResult:
        """Create a clean scan result."""
        risk_level = settings.get_risk_level(probability)
        
        with self._lock:
            self.stats["total_scans"] += 1
            self.stats["total_bytes_scanned"] += bytes_scanned
        
        # Import here to avoid circular imports
        from threat_manager import get_threat_manager
        threat_manager = get_threat_manager()
        
        # Log to threat manager
        result = threat_manager.log_clean(
            source=source,
            source_type=source_type,
            probability=probability,
            bytes_scanned=bytes_scanned,
            scan_time_ms=scan_time_ms
        )
        
        # Merge details
        result_details = {"log_id": result.get("threat_id")}
        if details:
            result_details.update(details)
        
        return ScanResult(
            source=source,
            source_type=source_type,
            probability=probability,
            risk_level=risk_level,
            bytes_scanned=bytes_scanned,
            blocked=False,
            scan_time_ms=scan_time_ms,
            status="CLEAN",
            details=result_details
        )
    
    def set_threshold(self, threshold: float) -> None:
        """
        Update confidence threshold.
        
        Args:
            threshold: New threshold value (0.0 to 1.0)
        """
        self.confidence_threshold = threshold
        logger.info(f"Confidence threshold updated: {threshold}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        with self._lock:
            return dict(self.stats)


# Global detector instance
detector: Optional[StreamingDetector] = None


def get_detector(model_path: Optional[str] = None) -> StreamingDetector:
    """
    Get or create detector instance.
    
    Args:
        model_path: Optional model path
        
    Returns:
        StreamingDetector instance
    """
    global detector
    if detector is None:
        detector = StreamingDetector(model_path)
    return detector


def init_detector(model_path: Optional[str] = None) -> StreamingDetector:
    """
    Initialize detector with given model path.
    
    Args:
        model_path: Model checkpoint path
        
    Returns:
        Initialized StreamingDetector
    """
    global detector
    detector = StreamingDetector(model_path)
    return detector