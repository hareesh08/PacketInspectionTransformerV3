# Real-Time Malware Detection Gateway

A production-grade malware detection system that inspects network traffic and files in real-time using Transformer models with streaming byte-level analysis.

## 🚀 Features

- **Streaming DPI**: Real-time analysis with 512-byte chunks and 1500-byte rolling window
- **Early Termination**: Stops processing immediately when threat is detected
- **Low Latency**: Target <100ms inference time with optimized PyTorch model
- **Risk Classification**: 5-level risk assessment (BENIGN → CRITICAL)
- **SQLite Logging**: Persistent threat logs with proper indexing
- **FastAPI Endpoints**: RESTful API for scanning and management
- **Configuration Management**: Pydantic settings with environment variable support

## 📁 Project Structure

```
PacketInspectionTransformerV2/
├── app.py                          # FastAPI application & endpoints
├── detector.py                     # Core DPI & model inference logic
├── threat_manager.py               # Threat logging & risk assessment
├── database.py                     # SQLite database operations
├── models.py                       # Pydantic data models
├── settings.py                     # Configuration management
├── config/
│   ├── system_config.json          # Runtime configuration
│   └── model_config.py             # Model-specific settings
├── model/
│   └── finetuned_best_model.pth    # Pretrained transformer
├── requirements.txt                # Python dependencies
├── tests/
│   ├── test_api.py                 # API endpoint tests
│   ├── test_detector.py            # Detection logic tests
│   └── test_streaming.py           # Streaming tests
├── logs/                           # Structured logs
├── docs/
│   └── ARCHITECTURE_PLAN.md        # Detailed architecture documentation
└── README.md                       # This file
```

## 🛠️ Installation

```bash
# Clone or navigate to project directory
cd PacketInspectionTransformerV2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Ensure model file exists
# Place your finetuned_best_model.pth in model/ directory
```

## ⚙️ Configuration

Configuration is managed through `settings.py` with Pydantic BaseSettings. All settings can be overridden via environment variables.

### Key Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| `confidence_threshold` | 0.7 | Detection threshold (0.0-1.0) |
| `chunk_size` | 512 | Bytes per chunk for streaming |
| `window_size` | 1500 | Rolling window size |
| `max_file_size` | 100MB | Maximum file size |
| `temperature` | 1.0 | Temperature scaling |
| `host` | 0.0.0.0 | Server host |
| `port` | 8000 | Server port |

### Environment Variables

```bash
export MALWARE_DETECTOR_CONFIDENCE_THRESHOLD=0.8
export MALWARE_DETECTOR_HOST=0.0.0.0
export MALWARE_DETECTOR_PORT=8000
```

## 🏃 Usage

### Start the Server

```bash
# Development mode
python app.py

# Or with uvicorn directly
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Scan URL
```bash
curl -X POST "http://localhost:8000/scan/url" \
  -H "Content-Type: application/json" \
  -d '{"url": "http://example.com/file.exe"}'
```

#### Upload File
```bash
curl -X POST "http://localhost:8000/scan/file" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@suspicious.exe"
```

#### Get Threat Logs
```bash
curl "http://localhost:8000/threats?limit=50&risk_level=HIGH"
```

#### Update Threshold
```bash
curl -X POST "http://localhost:8000/settings/threshold" \
  -H "Content-Type: application/json" \
  -d '{"threshold": 0.8}'
```

#### Get Statistics
```bash
curl http://localhost:8000/stats
```

## 📊 Risk Levels

| Probability | Risk Level | Action |
|-------------|------------|--------|
| 0.0 - 0.3 | BENIGN | Allow |
| 0.3 - 0.5 | LOW | Log only |
| 0.5 - 0.7 | MEDIUM | Log & warn |
| 0.7 - 0.9 | HIGH | Log & alert |
| 0.9 - 1.0 | CRITICAL | Block & alert |

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_detector.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

## 🔧 Architecture

### Streaming DPI Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ URL/File    │────▶│ Chunking    │────▶│ Rolling     │────▶│ Transformer │
│ Input       │     │ (512 bytes) │     │ Window      │     │ Inference   │
└─────────────┘     └─────────────┘     │ (-1500)     │     └─────────────┘
                                        └─────────────┘           │
                                                                    ▼
                                                   ┌─────────────────────────┐
                                                   │ Temperature Scaling +   │
                                                   │ Sigmoid Activation      │
                                                   └─────────────────────────┘
                                                            │
                          ┌─────────────────────────────────┼─────────────────────────────────┐
                          ▼                                 ▼                                 ▼
                   ┌─────────────┐                  ┌─────────────┐                  ┌─────────────┐
                   │ Probability │                  │ Probability │                  │ Probability │
                   │ < Threshold │                  │ ≥ Threshold │                  │ ≥ Critical  │
                   └─────────────┘                  └─────────────┘                  └─────────────┘
                          │                                 │                                 │
                          ▼                                 ▼                                 ▼
                   ┌─────────────┐                  ┌─────────────┐                  ┌─────────────┐
                   │ Continue    │                  │ Log Threat  │                  │ Block &     │
                   │ Processing  │                  │ Alert       │                  │ Alert       │
                   └─────────────┘                  └─────────────┘                  └─────────────┘
```

### Model Architecture

Based on the Packet Inspection Transformer with:
- **12 Transformer Encoder Layers**
- **12 Attention Heads**
- **768 Model Dimension**
- **259 Vocabulary Size** (0-255 bytes + special tokens)
- **Mean Pooling Classifier**

## 📈 Performance

- **Target Latency**: <100ms per inference
- **Memory Efficiency**: No full-file loading (streaming only)
- **Throughput**: ~20 MB/s processing speed
- **Early Termination**: Saves ~50% processing on detected threats

## 🔐 Security Considerations

- Input validation on all URLs and file paths
- Maximum file size enforcement (100MB default)
- Download timeout protection (30s default)
- CORS middleware configured for production
- Rate limiting available via settings

## 📝 Logging

Logs are stored in structured JSON format in the `logs/` directory:
- `threats_YYYYMMDD.log` - Daily threat logs
- Structured format for easy parsing
- Includes probability, risk level, bytes scanned

## 🐳 Docker Support (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📄 License

This project is provided as-is for educational and research purposes.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes
4. Add tests
5. Submit pull request

## 📞 Support

For issues and questions, please open a GitHub issue.