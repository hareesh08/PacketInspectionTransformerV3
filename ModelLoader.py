#!/usr/bin/env python3
"""
Integrated Malware Detection System with PacketInspection Transformer

This module combines the PacketInspection Transformer with MBP pretraining
with the alert system for real-time packet analysis and threat notification.
"""

import os
import json
import time
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import threading
from torch.nn import TransformerEncoder, TransformerEncoderLayer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PositionalEncoding(nn.Module):
    """Sinusoidal Positional Encoding as specified in the paper"""
    
    def __init__(self, d_model: int, max_len: int = 1500):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-torch.log(torch.tensor(10000.0)) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, :x.size(1)]
        return x

class PacketTransformerWithMBP(nn.Module):
    """
    Packet Transformer Encoder with Masked Byte Prediction (MBP) capability
    """
    
    def __init__(self,
                 vocab_size: int = 259,  # 0-255 bytes + padding (256) + mask (257) + unknown (258)
                 d_model: int = 768,
                 nhead: int = 12,
                 num_layers: int = 12,
                 dim_feedforward: int = 3072,
                 max_len: int = 1500,
                 dropout: float = 0.1):
        super().__init__()
        
        # Special token IDs
        self.pad_token_id = 256
        self.mask_token_id = 257
        self.unk_token_id = 258
        self.vocab_size = vocab_size
        
        # Embedding layer: Convert byte IDs to dense vectors
        self.embedding = nn.Embedding(vocab_size, d_model)
        
        # Positional encoding
        self.pos_encoder = PositionalEncoding(d_model, max_len)
        
        # Transformer encoder with 12 layers
        encoder_layer = TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            activation='relu'
        )
        self.transformer_encoder = TransformerEncoder(encoder_layer, num_layers)
        
        self.d_model = d_model
        
        # MLM decoder for pretraining
        self.mlm_decoder = nn.Linear(d_model, vocab_size)
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        """Initialize weights as specified in the paper"""
        nn.init.xavier_uniform_(self.embedding.weight)
        nn.init.xavier_uniform_(self.mlm_decoder.weight)
    
    def forward(self, 
                src: torch.Tensor, 
                src_key_padding_mask: Optional[torch.Tensor] = None, 
                mlm: bool = False) -> torch.Tensor:
        """
        Forward pass through the transformer
        
        Args:
            src: Input tensor of shape [batch_size, seq_len] containing byte values
            src_key_padding_mask: Optional mask for padding tokens [batch_size, seq_len]
            mlm: If True, returns MLM logits for pretraining
            
        Returns:
            If mlm=True: Tensor of shape [batch_size, seq_len, vocab_size] (MLM logits)
            If mlm=False: Tensor of shape [batch_size, seq_len, d_model] (hidden states)
        """
        # 1. Embedding: [batch_size, seq_len] -> [batch_size, seq_len, d_model]
        x = self.embedding(src) * (self.d_model ** 0.5)  # Scale embeddings
        
        # 2. Positional encoding: Add position information
        x = self.pos_encoder(x)
        
        # 3. Transformer encoder: Learn contextual relationships
        x = self.transformer_encoder(x, src_key_padding_mask=src_key_padding_mask)
        
        # 4. Output processing
        if mlm:
            # For MLM pretraining: return logits for each token
            return self.mlm_decoder(x)  # [batch_size, seq_len, vocab_size]
        else:
            # For downstream tasks: return hidden states
            return x  # [batch_size, seq_len, d_model]

class MeanPoolingClassifier(nn.Module):
    """
    Mean Pooling Classifier for downstream tasks as specified in the paper
    """
    
    def __init__(self, d_model: int = 768, num_classes: int = 3, dropout: float = 0.5):
        super().__init__()
        
        # Three-layer feedforward network
        self.fc1 = nn.Linear(d_model, 512)
        self.fc2 = nn.Linear(512, 128)
        self.fc3 = nn.Linear(128, num_classes)
        self.dropout = nn.Dropout(dropout)
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        """Initialize classifier weights"""
        for layer in [self.fc1, self.fc2, self.fc3]:
            nn.init.xavier_uniform_(layer.weight)
            nn.init.zeros_(layer.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the classifier
        
        Args:
            x: Hidden states from transformer [batch_size, seq_len, d_model]
            
        Returns:
            Logits tensor of shape [batch_size, num_classes]
        """
        # Mean pooling across sequence length
        x = x.mean(dim=1)  # [batch_size, seq_len, d_model] -> [batch_size, d_model]
        
        # Three-layer feedforward with ReLU and dropout
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.fc3(x)
        
        return x  # [batch_size, num_classes]

class PacketInspectionTransformerWithPretraining(nn.Module):
    """
    Complete Packet Inspection Transformer with MBP pretraining capability
    """
    
    def __init__(self,
                 vocab_size: int = 258,
                 d_model: int = 768,
                 nhead: int = 12,
                 num_layers: int = 12,
                 dim_feedforward: int = 3072,
                 max_len: int = 1500,
                 num_classes: int = 2,
                 dropout: float = 0.1,
                 classifier_dropout: float = 0.5):
        super().__init__()
        
        # Transformer encoder with MBP capability
        self.transformer = PacketTransformerWithMBP(
            vocab_size=vocab_size,
            d_model=d_model,
            nhead=nhead,
            num_layers=num_layers,
            dim_feedforward=dim_feedforward,
            max_len=max_len,
            dropout=dropout
        )
        
        # Mean pooling classifier for downstream tasks
        self.classifier = MeanPoolingClassifier(
            d_model=d_model,
            num_classes=num_classes,
            dropout=classifier_dropout
        )
        
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.max_len = max_len
        self.pad_token_id = 256
        self.mask_token_id = 257
    
    def forward(self, 
                packet_bytes: torch.Tensor, 
                padding_mask: Optional[torch.Tensor] = None,
                pretraining: bool = False) -> torch.Tensor:
        """
        Forward pass through the model
        
        Args:
            packet_bytes: Input tensor [batch_size, seq_len] with byte values
            padding_mask: Optional padding mask [batch_size, seq_len]
            pretraining: If True, use MBP pretraining mode
            
        Returns:
            If pretraining=True: MLM logits [batch_size, seq_len, vocab_size]
            If pretraining=False: Classification logits [batch_size, num_classes]
        """
        if pretraining:
            # MBP Pretraining mode
            hidden_states = self.transformer(packet_bytes, padding_mask, mlm=True)
            return hidden_states
        else:
            # Downstream task mode
            hidden_states = self.transformer(packet_bytes, padding_mask, mlm=False)
            logits = self.classifier(hidden_states)
            return logits
    
    def create_padding_mask(self, packet_bytes: torch.Tensor) -> torch.Tensor:
        """Create padding mask for variable-length sequences"""
        return packet_bytes == self.pad_token_id

def create_pretrained_model(num_classes: int = 2, 
                           max_packet_length: int = 1500,
                           dropout: float = 0.1) -> PacketInspectionTransformerWithPretraining:
    """
    Create the model with pretraining capability exactly as specified in the paper
    
    Args:
        num_classes: Number of output classes
        max_packet_length: Maximum sequence length
        dropout: Dropout rate
        
    Returns:
        PacketInspectionTransformerWithPretraining model
    """
    return PacketInspectionTransformerWithPretraining(
        vocab_size=259,           # 0-255 bytes + padding (256) + mask (257) + unknown (258)
        d_model=768,              # Model dimension as in paper
        nhead=12,                 # 12 attention heads as in paper
        num_layers=12,            # 12 transformer layers as in paper
        dim_feedforward=3072,     # Feedforward dimension as in paper
        max_len=max_packet_length,
        num_classes=num_classes,
        dropout=dropout,
        classifier_dropout=0.5
    )


class AlertLevel(Enum):
    """Alert severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertType(Enum):
    """Types of alerts."""
    MALWARE_DETECTED = "MALWARE_DETECTED"
    SUSPICIOUS_FLOW = "SUSPICIOUS_FLOW"
    SYSTEM_STATUS = "SYSTEM_STATUS"


class AlertSystem:
    """Centralized alert system for malware detection events."""
    
    def __init__(self, log_file: str = "malware_alerts.log", 
                 web_alerts_file: str = "web_alerts.json"):
        """Initialize the alert system."""
        self.log_file = log_file
        self.web_alerts_file = web_alerts_file
        self.alerts_history = []
        self._lock = threading.Lock()
        
        # Terminal colors
        self.colors = {
            'RED': '\033[91m', 'YELLOW': '\033[93m', 'GREEN': '\033[92m',
            'MAGENTA': '\033[95m', 'BOLD': '\033[1m', 'RESET': '\033[0m'
        }
        
        # Alert level colors and symbols
        self.alert_colors = {
            AlertLevel.LOW: self.colors['GREEN'],
            AlertLevel.MEDIUM: self.colors['YELLOW'],
            AlertLevel.HIGH: self.colors['RED'],
            AlertLevel.CRITICAL: self.colors['MAGENTA']
        }
        
        self.alert_symbols = {
            AlertLevel.LOW: "ℹ️",
            AlertLevel.MEDIUM: "⚠️",
            AlertLevel.HIGH: "🚨",
            AlertLevel.CRITICAL: "🔥"
        }
        
        self._setup_logging()
        logger.info("🔔 Alert System initialized")
    
    def _setup_logging(self):
        """Set up alert logging configuration."""
        alert_logger = logging.getLogger('malware_alerts')
        alert_logger.setLevel(logging.INFO)
        
        if not alert_logger.handlers:
            file_handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            alert_logger.addHandler(file_handler)
        
        self.alert_logger = alert_logger
    
    def create_alert(self, alert_type: AlertType, level: AlertLevel, title: str, 
                    message: str, details: Optional[Dict] = None) -> Dict:
        """Create and process a new alert."""
        alert = {
            'id': f"alert_{int(time.time() * 1000)}",
            'timestamp': datetime.now().isoformat(),
            'type': alert_type.value,
            'level': level.value,
            'title': title,
            'message': message,
            'details': details or {},
            'acknowledged': False
        }
        
        with self._lock:
            self.alerts_history.append(alert)
        
        self._process_alert(alert)
        return alert
    
    def _process_alert(self, alert: Dict):
        """Process alert through all notification channels."""
        self._show_terminal_alert(alert)
        self._log_alert(alert)
        self._save_web_alert(alert)
    
    def _show_terminal_alert(self, alert: Dict):
        """Display alert in terminal with colors and formatting."""
        level = AlertLevel(alert['level'])
        color = self.alert_colors[level]
        symbol = self.alert_symbols[level]
        reset = self.colors['RESET']
        bold = self.colors['BOLD']
        
        border = "=" * 80
        print(f"\n{color}{border}{reset}")
        print(f"{color}{bold}{symbol} MALWARE DETECTION ALERT - {level.value}{reset}")
        print(f"{color}{border}{reset}")
        print(f"{bold}🎯 {alert['title']}{reset}")
        print(f"📝 {alert['message']}")
        print(f"🕐 {alert['timestamp']}")
        
        if alert['details']:
            print(f"\n{bold}📊 Details:{reset}")
            for key, value in alert['details'].items():
                if isinstance(value, dict):
                    print(f"   {key}:")
                    for sub_key, sub_value in value.items():
                        print(f"     {sub_key}: {sub_value}")
                else:
                    print(f"   {key}: {value}")
        
        print(f"{color}{border}{reset}\n")
    
    def _log_alert(self, alert: Dict):
        """Log alert to file."""
        log_message = f"[{alert['level']}] {alert['type']} - {alert['title']}: {alert['message']}"
        self.alert_logger.info(log_message)
        if alert['details']:
            self.alert_logger.info(f"Alert details: {json.dumps(alert['details'], indent=2)}")
    
    def _make_json_safe(self, obj):
        """Convert numpy arrays and other non-JSON serializable objects."""
        if hasattr(obj, 'tolist'):
            return obj.tolist()
        elif hasattr(obj, '__dict__'):
            return {key: self._make_json_safe(value) for key, value in obj.__dict__.items()}
        elif isinstance(obj, dict):
            return {key: self._make_json_safe(value) for key, value in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_safe(item) for item in obj]
        else:
            return obj
    
    def _save_web_alert(self, alert: Dict):
        """Save alert for web interface consumption."""
        web_alerts = []
        
        if os.path.exists(self.web_alerts_file):
            try:
                with open(self.web_alerts_file, 'r') as f:
                    web_alerts = json.load(f)
            except (json.JSONDecodeError, IOError):
                web_alerts = []
        
        web_alerts.append(self._make_json_safe(alert))
        web_alerts = web_alerts[-50:]  # Keep only last 50 alerts
        
        try:
            with open(self.web_alerts_file, 'w') as f:
                json.dump(web_alerts, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save web alerts: {e}")
    
    def malware_detection_alert(self, pcap_file: str, malicious_flows: int, total_flows: int,
                              malicious_packets: int, total_packets: int, threat_level: str) -> Dict:
        """Create a malware detection alert."""
        malicious_flow_ratio = malicious_flows / total_flows if total_flows > 0 else 0
        
        # Determine alert level
        if threat_level == "CRITICAL" or malicious_flow_ratio > 0.5:
            alert_level = AlertLevel.CRITICAL
        elif threat_level == "HIGH" or malicious_flow_ratio > 0.2:
            alert_level = AlertLevel.HIGH
        elif threat_level == "MEDIUM" or malicious_flow_ratio > 0:
            alert_level = AlertLevel.MEDIUM
        else:
            alert_level = AlertLevel.LOW
        
        title = "Malware Detected in Network Traffic"
        message = (f"Analysis of {os.path.basename(pcap_file)} revealed {malicious_flows} malicious "
                  f"flows out of {total_flows} total flows ({malicious_flow_ratio:.1%})")
        
        details = {
            'analysis_summary': {
                'pcap_file': pcap_file,
                'total_flows': total_flows,
                'malicious_flows': malicious_flows,
                'benign_flows': total_flows - malicious_flows,
                'total_packets': total_packets,
                'malicious_packets': malicious_packets,
                'malicious_flow_ratio': malicious_flow_ratio,
                'threat_level': threat_level
            }
        }
        
        return self.create_alert(
            alert_type=AlertType.MALWARE_DETECTED,
            level=alert_level,
            title=title,
            message=message,
            details=details
        )
    
    def get_alert_statistics(self) -> Dict:
        """Get alert statistics."""
        with self._lock:
            if not self.alerts_history:
                return {
                    'total_alerts': 0,
                    'by_level': {},
                    'by_type': {},
                    'acknowledged_count': 0
                }
            
            stats = {
                'total_alerts': len(self.alerts_history),
                'by_level': {},
                'by_type': {},
                'acknowledged_count': sum(1 for alert in self.alerts_history if alert.get('acknowledged', False))
            }
            
            # Count by level
            for level in AlertLevel:
                stats['by_level'][level.value] = sum(
                    1 for alert in self.alerts_history if alert['level'] == level.value
                )
            
            # Count by type
            for alert_type in AlertType:
                stats['by_type'][alert_type.value] = sum(
                    1 for alert in self.alerts_history if alert['type'] == alert_type.value
                )
            
            return stats


class MalwareDetectorService:
    """Production malware detection service using the trained transformer model."""
    
    def __init__(self, model_path: Optional[str] = None, alert_system: Optional[AlertSystem] = None):
        """Initialize the malware detection service."""
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Default model path in same directory or model subdirectory
        if model_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Try current directory first, then model subdirectory
            default_path = os.path.join(current_dir, 'finetuned_best_model.pth')
            if not os.path.exists(default_path):
                default_path = os.path.join(current_dir, 'model', 'finetuned_best_model.pth')
            model_path = default_path
        
        self.model_path = model_path
        self.alert_system = alert_system
        
        # Model configuration
        self.max_packet_length = 1500
        self.num_classes = 2
        self.optimal_threshold = 0.75
        self.padding_value = 256
        
        # Class mappings
        self.class_names = {0: 'Benign', 1: 'Malicious'}
        self.class_colors = {0: '\033[92m', 1: '\033[91m'}
        self.reset_color = '\033[0m'
        
        # Performance stats
        self.model_accuracy = 0.8391  # 83.91%
        self.model_f1_score = 0.839
        
        # Initialize model
        self.model = None
        self._load_model()
        
        logger.info(f"✅ Malware Detection Service initialized")
        logger.info(f"📱 Device: {self.device}")
        logger.info(f"🎯 Optimal threshold: {self.optimal_threshold}")
        logger.info(f"📊 Model accuracy: {self.model_accuracy:.1%}")
    
    def _load_model(self):
        """Load the trained model from checkpoint."""
        try:
            # Create model architecture
            self.model = create_pretrained_model(
                num_classes=self.num_classes, 
                max_packet_length=self.max_packet_length
            )
            
            # Try to load the model if it exists
            if os.path.exists(self.model_path):
                # Load checkpoint with weights_only=False to handle PyTorch 2.6 security changes
                try:
                    checkpoint = torch.load(self.model_path, map_location='cpu', weights_only=False)
                    self.model.load_state_dict(checkpoint['model_state_dict'])
                    logger.info(f"📋 Model loaded from {self.model_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not load model weights: {e}")
                    logger.info("📋 Using randomly initialized model")
            else:
                logger.warning(f"⚠️ Model file not found: {self.model_path}")
                logger.info("📋 Using randomly initialized model")
            
            # Move to device and set evaluation mode
            self.model.to(self.device)
            self.model.eval()
            
            # Log model info
            total_params = sum(p.numel() for p in self.model.parameters())
            logger.info(f"📋 Model initialized: {total_params:,} parameters")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize model: {e}")
            raise
    
    def preprocess_packets(self, packet_payloads: List[bytes]) -> torch.Tensor:
        """Preprocess packet payloads into model input format."""
        processed_packets = []
        
        for payload in packet_payloads:
            # Convert bytes to integers
            if isinstance(payload, bytes):
                packet_ints = list(payload)
            elif isinstance(payload, (list, np.ndarray)):
                packet_ints = list(payload)
            else:
                logger.warning(f"Unexpected payload type: {type(payload)}")
                packet_ints = []
            
            # Ensure all values are in valid range (0-255)
            packet_ints = [min(max(int(b), 0), 255) for b in packet_ints]
            
            # Pad or truncate to max_packet_length
            if len(packet_ints) < self.max_packet_length:
                packet_ints.extend([self.padding_value] * (self.max_packet_length - len(packet_ints)))
            elif len(packet_ints) > self.max_packet_length:
                packet_ints = packet_ints[:self.max_packet_length]
                logger.debug(f"Truncated packet from {len(packet_ints)} to {self.max_packet_length} bytes")
            
            processed_packets.append(packet_ints)
        
        return torch.tensor(processed_packets, dtype=torch.long)
    
    def predict_batch(self, packet_data: torch.Tensor, batch_size: int = 32) -> Dict:
        """Predict malware for a batch of packets with memory-efficient processing."""
        total_samples = len(packet_data)
        
        # Initialize result containers
        all_logits = []
        all_probabilities = []
        all_default_predictions = []
        all_optimal_predictions = []
        all_confidence_scores = []
        all_malicious_probs = []
        
        with torch.no_grad():
            # Process in smaller batches to manage GPU memory
            for i in range(0, total_samples, batch_size):
                end_idx = min(i + batch_size, total_samples)
                batch = packet_data[i:end_idx].to(self.device)
                
                # Create padding mask
                padding_mask = self.model.create_padding_mask(batch)
                
                # Get model predictions (using pretraining=False for downstream task)
                raw_logits = self.model(batch, padding_mask, pretraining=False)
                probabilities = F.softmax(raw_logits, dim=1)
                
                # Default predictions (argmax)
                default_predictions = torch.argmax(raw_logits, dim=1)
                
                # Optimal threshold predictions
                optimal_predictions = (probabilities[:, 1] > self.optimal_threshold).long()
                
                # Calculate confidence scores
                confidence_scores = torch.max(probabilities, dim=1)[0]
                malicious_probs = probabilities[:, 1]
                
                # Move to CPU and store
                all_logits.append(raw_logits.cpu())
                all_probabilities.append(probabilities.cpu())
                all_default_predictions.append(default_predictions.cpu())
                all_optimal_predictions.append(optimal_predictions.cpu())
                all_confidence_scores.append(confidence_scores.cpu())
                all_malicious_probs.append(malicious_probs.cpu())
                
                # Clear GPU cache after each batch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
        
        # Concatenate all results
        return {
            'raw_logits': torch.cat(all_logits, dim=0).numpy(),
            'probabilities': torch.cat(all_probabilities, dim=0).numpy(),
            'default_predictions': torch.cat(all_default_predictions, dim=0).numpy(),
            'optimal_predictions': torch.cat(all_optimal_predictions, dim=0).numpy(),
            'confidence_scores': torch.cat(all_confidence_scores, dim=0).numpy(),
            'malicious_probabilities': torch.cat(all_malicious_probs, dim=0).numpy(),
            'threshold_used': self.optimal_threshold,
            'batch_size': total_samples,
            'prediction_timestamp': datetime.now().isoformat(),
            'processing_info': {
                'total_samples': total_samples,
                'batch_size_used': batch_size,
                'num_batches': len(all_logits)
            }
        }
    
    def get_dynamic_threshold(self, packet_size: int) -> float:
        """Calculate dynamic threshold based on packet size to compensate for model bias."""
        if packet_size <= 100:
            return 0.75  # More lenient threshold for small packets
        elif packet_size <= 800:
            # Gradual linear interpolation from 0.75 to 0.80
            ratio = (packet_size - 100) / 700
            return 0.75 + (0.80 - 0.75) * ratio
        else:
            return 0.85  # Higher threshold for large packets
    
    def analyze_packets(self, packet_payloads: List[bytes], max_batch_size: int = 16, 
                       pcap_file: str = "unknown") -> Dict:
        """Complete packet analysis pipeline from raw payloads to predictions."""
        if not packet_payloads:
            return {
                'status': 'error',
                'message': 'No packet payloads provided',
                'malicious_count': 0,
                'total_count': 0
            }
        
        try:
            # Preprocess packets
            packet_data = self.preprocess_packets(packet_payloads)
            
            # Get predictions
            predictions = self.predict_batch(packet_data, batch_size=max_batch_size)
            
            # Apply dynamic thresholding
            optimal_preds = []
            dynamic_thresholds = []
            
            for i, payload in enumerate(packet_payloads):
                packet_size = len(payload)
                dynamic_threshold = self.get_dynamic_threshold(packet_size)
                dynamic_thresholds.append(dynamic_threshold)
                
                malicious_prob = float(predictions['malicious_probabilities'][i])
                is_malicious = malicious_prob > dynamic_threshold
                optimal_preds.append(1 if is_malicious else 0)
            
            optimal_preds = np.array(optimal_preds)
            
            # Update predictions with dynamic results
            predictions['optimal_predictions'] = optimal_preds
            predictions['dynamic_thresholds'] = np.array(dynamic_thresholds)
            
            # Analyze results
            malicious_count = int(np.sum(optimal_preds))
            total_count = len(packet_payloads)
            benign_count = total_count - malicious_count
            malicious_ratio = malicious_count / total_count if total_count > 0 else 0
            
            # Risk assessment
            if malicious_ratio > 0.5:
                risk_level = "HIGH"
                risk_color = "\033[91m"  # Red
            elif malicious_ratio > 0.1:
                risk_level = "MEDIUM"
                risk_color = "\033[93m"  # Yellow
            else:
                risk_level = "LOW"
                risk_color = "\033[92m"  # Green
            
            # Send alert if malware detected and alert system is available
            if malicious_count > 0 and self.alert_system:
                self.alert_system.malware_detection_alert(
                    pcap_file=pcap_file,
                    malicious_flows=malicious_count,
                    total_flows=total_count,
                    malicious_packets=malicious_count,
                    total_packets=total_count,
                    threat_level=risk_level
                )
            
            return {
                'status': 'success',
                'predictions': predictions,
                'summary': {
                    'total_packets': total_count,
                    'malicious_packets': malicious_count,
                    'benign_packets': benign_count,
                    'malicious_ratio': malicious_ratio,
                    'risk_level': risk_level,
                    'risk_color': risk_color,
                    'contains_malware': malicious_count > 0
                },
                'model_info': {
                    'model_accuracy': self.model_accuracy,
                    'base_threshold': self.optimal_threshold,
                    'dynamic_thresholding': True,
                    'threshold_range': f"{min(predictions['dynamic_thresholds']):.2f}-{max(predictions['dynamic_thresholds']):.2f}",
                    'device': str(self.device)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing packets: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'malicious_count': 0,
                'total_count': len(packet_payloads)
            }
    
    def format_analysis_summary(self, analysis_results: Dict) -> str:
        """Format analysis results for terminal display."""
        if analysis_results['status'] != 'success':
            return f"❌ Analysis failed: {analysis_results.get('message', 'Unknown error')}"
        
        summary = analysis_results['summary']
        reset = self.reset_color
        
        # Header
        output = "\n" + "="*60 + "\n"
        output += "🛡️  MALWARE DETECTION ANALYSIS RESULTS\n"
        output += "="*60 + "\n"
        
        # Summary stats
        output += f"📊 Total Packets Analyzed: {summary['total_packets']}\n"
        output += f"{self.class_colors[0]}✅ Benign Packets: {summary['benign_packets']}{reset}\n"
        output += f"{self.class_colors[1]}🚨 Malicious Packets: {summary['malicious_packets']}{reset}\n"
        output += f"📈 Malicious Ratio: {summary['malicious_ratio']:.1%}\n"
        
        # Risk assessment
        risk_color = summary['risk_color']
        output += f"{risk_color}🎯 Risk Level: {summary['risk_level']}{reset}\n"
        
        # Alert if malware detected
        if summary['contains_malware']:
            output += f"\n{self.class_colors[1]}🚨 ALERT: MALWARE DETECTED IN TRAFFIC!{reset}\n"
            output += f"{self.class_colors[1]}⚠️  {summary['malicious_packets']} packets flagged as malicious{reset}\n"
        else:
            output += f"\n{self.class_colors[0]}✅ All packets classified as benign{reset}\n"
        
        # Model info
        output += f"\n📋 Model Info: {self.model_accuracy:.1%} accuracy, threshold {self.optimal_threshold}\n"
        output += f"💻 Device: {analysis_results['model_info']['device']}\n"
        output += "="*60 + "\n"
        
        return output


def main():
    """Test the integrated malware detection system."""
    print("🛡️  Integrated Malware Detection System Test")
    print("=" * 50)
    
    # Initialize alert system
    alert_system = AlertSystem()
    
    # Initialize malware detector service with alert system
    service = MalwareDetectorService(alert_system=alert_system)
    
    # Create dummy packet payloads for testing
    dummy_payloads = [
        b"GET /index.html HTTP/1.1\r\nHost: example.com\r\n\r\n",
        b"POST /login HTTP/1.1\r\nContent-Type: application/json\r\n\r\n",
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 50
    ]
    
    print(f"🔍 Analyzing {len(dummy_payloads)} test packets...")
    
    # Analyze packets
    results = service.analyze_packets(dummy_payloads, pcap_file="test_capture.pcap")
    
    # Display results
    print(service.format_analysis_summary(results))
    
    # Show alert statistics
    stats = alert_system.get_alert_statistics()
    print(f"\n📊 Alert Statistics:")
    print(f"Total alerts: {stats['total_alerts']}")
    print(f"By level: {stats['by_level']}")
    print(f"By type: {stats['by_type']}")
    
    print("\n✅ System test completed")


if __name__ == "__main__":
    main()