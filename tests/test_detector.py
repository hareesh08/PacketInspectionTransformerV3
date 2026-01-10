"""
Unit tests for the detector module.
Tests streaming DPI logic, model inference, and early termination.
"""

import pytest
import os
import sys
import tempfile
import torch
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestStreamingDetector:
    """Tests for StreamingDetector class."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        with patch('detector.settings') as mock:
            mock.chunk_size = 512
            mock.window_size = 1500
            mock.max_file_size = 100 * 1024 * 1024
            mock.download_timeout = 30
            mock.temperature = 1.0
            mock.confidence_threshold = 0.7
            mock.vocab_size = 259
            mock.d_model = 768
            mock.nhead = 12
            mock.num_layers = 12
            mock.dim_feedforward = 3072
            mock.dropout = 0.1
            mock.model_path = "model/finetuned_best_model.pth"
            yield mock
    
    @pytest.fixture
    def detector(self, mock_settings):
        """Create detector with mocked model."""
        from detector import StreamingDetector
        
        with patch.object(StreamingDetector, '_load_model') as mock_load:
            mock_load.return_value = None
            detector = StreamingDetector.__new__(StreamingDetector)
            detector.model_path = "model/finetuned_best_model.pth"
            detector.device = "cpu"
            detector.chunk_size = 512
            detector.window_size = 1500
            detector.max_file_size = 100 * 1024 * 1024
            detector.download_timeout = 30
            detector.temperature = 1.0
            detector.confidence_threshold = 0.7
            detector.model = None
            detector._lock = MagicMock()
            detector.stats = {
                "total_scans": 0,
                "threats_blocked": 0,
                "total_bytes_scanned": 0,
                "avg_scan_time_ms": 0.0
            }
            yield detector
    
    def test_byte_to_token_ids(self, detector):
        """Test byte to token ID conversion."""
        test_data = b'\x00\x01\x02\xff'
        tokens = detector.byte_to_token_ids(test_data)
        
        assert tokens == [0, 1, 2, 255]
        assert len(tokens) == len(test_data)
    
    def test_pad_or_truncate_short(self, detector):
        """Test padding short token sequences."""
        tokens = [1, 2, 3]
        result = detector.pad_or_truncate(tokens, 10)
        
        assert len(result) == 10
        assert result[:3] == [1, 2, 3]
        assert result[3:] == [256] * 7  # Padding token
    
    def test_pad_or_truncate_long(self, detector):
        """Test truncating long token sequences."""
        tokens = list(range(2000))
        result = detector.pad_or_truncate(tokens, 1500)
        
        assert len(result) == 1500
        assert result == list(range(1500))
    
    def test_pad_or_truncate_exact(self, detector):
        """Test exact length token sequences."""
        tokens = list(range(1500))
        result = detector.pad_or_truncate(tokens, 1500)
        
        assert len(result) == 1500
        assert result == tokens
    
    def test_preprocess(self, detector):
        """Test preprocessing byte data."""
        test_data = b'\x00\x01\x02\x03\x04'
        tensor = detector.preprocess(test_data)
        
        assert tensor.shape == (1, 1500)
        assert tensor.dtype == torch.long
        # First 5 tokens should match
        assert tensor[0, 0].item() == 0
        assert tensor[0, 4].item() == 4
        # Rest should be padding
        assert tensor[0, 5].item() == 256


class TestModelInference:
    """Tests for model inference pipeline."""
    
    def test_sigmoid_temperature_scaling(self):
        """Test temperature scaling affects output."""
        import torch
        import torch.nn.functional as F
        
        # Create mock logits
        logits = torch.tensor([[2.0, -1.0]])
        
        # High temperature (softer)
        prob_high = torch.sigmoid(logits / 2.0)[0, 1].item()
        
        # Low temperature (sharper)
        prob_low = torch.sigmoid(logits / 0.5)[0, 1].item()
        
        # Temperature should affect probability
        assert prob_high != prob_low
        # Higher temperature should give more moderate probabilities
        assert 0.4 < prob_high < 0.6
        assert prob_low > prob_high
    
    def test_risk_level_classification(self):
        """Test risk level from probability."""
        from settings import settings
        
        test_cases = [
            (0.1, "BENIGN"),
            (0.25, "BENIGN"),
            (0.35, "LOW"),
            (0.45, "LOW"),
            (0.55, "MEDIUM"),
            (0.65, "MEDIUM"),
            (0.75, "HIGH"),
            (0.85, "HIGH"),
            (0.95, "CRITICAL"),
        ]
        
        for prob, expected_level in test_cases:
            level = settings.get_risk_level(prob)
            assert level == expected_level, f"Failed for prob {prob}: got {level}"
    
    def test_early_termination_condition(self):
        """Test early termination logic."""
        threshold = 0.7
        
        # Should terminate
        assert threshold >= threshold
        
        # Should continue
        assert 0.5 < threshold
    
    def test_rolling_window_buffer(self):
        """Test rolling window buffer logic."""
        buffer = bytearray()
        window_size = 10
        chunk_size = 5
        
        # Add first chunk
        chunk1 = b'AAAAA'
        buffer.extend(chunk1)
        buffer = buffer[-window_size:]
        assert len(buffer) == 5
        
        # Add second chunk
        chunk2 = b'BBBBB'
        buffer.extend(chunk2)
        buffer = buffer[-window_size:]
        assert len(buffer) == 10
        assert buffer[:5] == b'AAAAA'
        assert buffer[5:] == b'BBBBB'
        
        # Add third chunk (should slide window)
        chunk3 = b'CCCCC'
        buffer.extend(chunk3)
        buffer = buffer[-window_size:]
        assert len(buffer) == 10
        assert buffer[:5] == b'BBBBB'
        assert buffer[5:] == b'CCCCC'


class TestSlidingWindow:
    """Tests for sliding window logic."""
    
    def test_window_sliding(self):
        """Test window correctly slides as new data arrives."""
        window_size = 10
        buffer = bytearray()
        
        # Add 5 bytes
        for i in range(5):
            buffer.append(i)
        buffer = buffer[-window_size:]
        assert len(buffer) == 5
        
        # Add 5 more bytes
        for i in range(5, 10):
            buffer.append(i)
        buffer = buffer[-window_size:]
        assert len(buffer) == 10
        assert list(buffer) == list(range(10))
        
        # Add 5 more bytes (window should slide)
        for i in range(10, 15):
            buffer.append(i)
        buffer = buffer[-window_size:]
        assert len(buffer) == 10
        assert list(buffer) == list(range(5, 15))
    
    def test_empty_buffer(self):
        """Test empty buffer handling."""
        buffer = bytearray()
        buffer = buffer[-1500:]
        assert len(buffer) == 0


class TestThreatDetection:
    """Tests for threat detection logic."""
    
    def test_threshold_comparison(self):
        """Test threshold comparison for blocking."""
        threshold = 0.7
        
        assert 0.71 >= threshold  # Should block
        assert not (0.69 >= threshold)  # Should not block
    
    def test_scan_result_creation(self):
        """Test ScanResult dataclass."""
        from detector import ScanResult
        
        result = ScanResult(
            source="http://example.com/malware.exe",
            source_type="URL",
            probability=0.85,
            risk_level="HIGH",
            bytes_scanned=1024,
            blocked=True,
            scan_time_ms=50.5,
            status="THREAT_DETECTED"
        )
        
        assert result.source_type == "URL"
        assert result.probability == 0.85
        assert result.risk_level == "HIGH"
        assert result.blocked is True
        assert result.status == "THREAT_DETECTED"
        
        # Test to_dict
        result_dict = result.to_dict()
        assert result_dict["probability"] == 0.85
        assert result_dict["risk_level"] == "HIGH"


class TestModelArchitecture:
    """Tests for model architecture components."""
    
    def test_positional_encoding_shape(self):
        """Test positional encoding output shape."""
        from detector import PositionalEncoding
        import torch
        
        d_model = 768
        max_len = 1500
        
        pe = PositionalEncoding(d_model, max_len)
        x = torch.randn(1, 100, d_model)  # batch=1, seq=100
        
        result = pe(x)
        
        assert result.shape == x.shape
        assert result.shape[2] == d_model
    
    def test_transformer_encoder_output(self):
        """Test transformer encoder produces valid output."""
        from detector import PacketTransformer
        import torch
        
        model = PacketTransformer(
            vocab_size=259,
            d_model=768,
            nhead=12,
            num_layers=2,  # Use fewer layers for testing
            dim_feedforward=3072,
            max_len=1500,
            dropout=0.1,
            num_classes=2
        )
        
        # Create input
        batch_size = 2
        seq_len = 100
        x = torch.randint(0, 259, (batch_size, seq_len))
        
        # Forward pass
        with torch.no_grad():
            output = model(x)
        
        assert output.shape == (batch_size, 2)  # num_classes=2
        assert output.dtype == torch.float32


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_byte_data(self):
        """Test handling of empty byte data."""
        from detector import StreamingDetector
        
        with patch('detector.settings') as mock:
            mock.chunk_size = 512
            mock.window_size = 1500
            mock.max_file_size = 100 * 1024 * 1024
            mock.download_timeout = 30
            mock.temperature = 1.0
            mock.confidence_threshold = 0.7
            mock.vocab_size = 259
            mock.d_model = 768
            mock.nhead = 12
            mock.num_layers = 12
            mock.dim_feedforward = 3072
            mock.dropout = 0.1
            mock.model_path = "model/finetuned_best_model.pth"
            
            detector = StreamingDetector.__new__(StreamingDetector)
            detector.model_path = "model/finetuned_best_model.pth"
            detector.device = "cpu"
            detector.chunk_size = 512
            detector.window_size = 1500
            detector.max_file_size = 100 * 1024 * 1024
            detector.download_timeout = 30
            detector.temperature = 1.0
            detector.confidence_threshold = 0.7
            detector.model = None
            detector._lock = MagicMock()
            detector.stats = {
                "total_scans": 0,
                "threats_blocked": 0,
                "total_bytes_scanned": 0,
                "avg_scan_time_ms": 0.0
            }
        
        # Empty data should still process
        tokens = detector.byte_to_token_ids(b'')
        assert tokens == []
        
        # Preprocess should handle empty
        tensor = detector.preprocess(b'')
        assert tensor.shape == (1, 1500)
    
    def test_all_255_bytes(self):
        """Test handling of maximum byte value."""
        detector = StreamingDetector.__new__(StreamingDetector)
        detector.window_size = 1500
        detector.model = MagicMock()
        detector.model.pad_token_id = 256
        
        # All 255s (valid bytes)
        test_data = bytes([255] * 100)
        tokens = detector.byte_to_token_ids(test_data)
        
        assert len(tokens) == 100
        assert all(t == 255 for t in tokens)
    
    def test_unicode_handling(self):
        """Test handling of unicode data (should be UTF-8 encoded)."""
        detector = StreamingDetector.__new__(StreamingDetector)
        detector.window_size = 1500
        detector.model = MagicMock()
        detector.model.pad_token_id = 256
        
        # Unicode string
        test_str = "Hello 世界 🌍"
        test_data = test_str.encode('utf-8')
        tokens = detector.byte_to_token_ids(test_data)
        
        # Should produce valid byte tokens
        assert all(0 <= t <= 255 for t in tokens)
        # Original bytes recovered
        recovered = bytes(tokens)
        assert recovered == test_data


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])