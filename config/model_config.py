"""
Model-specific configuration for the Packet Inspection Transformer.
"""

# Model Architecture Parameters
MODEL_CONFIG = {
    "vocab_size": 259,  # 0-255 bytes + padding (256) + mask (257) + unknown (258)
    "d_model": 768,     # Model dimension
    "nhead": 12,        # Number of attention heads
    "num_layers": 12,   # Number of transformer layers
    "dim_feedforward": 3072,  # Feedforward dimension
    "max_len": 1500,    # Maximum sequence length
    "dropout": 0.1,     # Dropout rate
    "num_classes": 2    # Binary classification (benign/malicious)
}

# Special Token IDs
SPECIAL_TOKENS = {
    "pad_token_id": 256,
    "mask_token_id": 257,
    "unk_token_id": 258
}

# Inference Settings
INFERENCE_CONFIG = {
    "temperature": 1.0,
    "confidence_threshold": 0.7,
    "batch_size": 32
}

# Streaming Settings
STREAMING_CONFIG = {
    "chunk_size": 512,
    "window_size": 1500,
    "max_file_size": 100 * 1024 * 1024,  # 100MB
    "download_timeout": 30
}

# Risk Level Thresholds
RISK_LEVELS = {
    "BENIGN": (0.0, 0.3),
    "LOW": (0.3, 0.5),
    "MEDIUM": (0.5, 0.7),
    "HIGH": (0.7, 0.9),
    "CRITICAL": (0.9, 1.0)
}

# Performance Metrics
METRICS = {
    "target_latency_ms": 100,
    "target_throughput_mbps": 50
}