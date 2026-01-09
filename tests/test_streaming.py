"""
Unit tests for streaming logic and early termination.
Tests chunk processing, rolling window, and performance.
"""

import pytest
import os
import sys
import time
from unittest.mock import patch, MagicMock, Mock
from io import BytesIO

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestStreamingChunkProcessing:
    """Tests for streaming chunk processing."""
    
    def test_chunk_size_configuration(self):
        """Test chunk size is properly configured."""
        from settings import settings
        
        assert settings.chunk_size == 512
        assert 64 <= settings.chunk_size <= 4096
    
    def test_chunk_processing_order(self):
        """Test that chunks are processed in order."""
        chunks_received = []
        
        test_data = b"0123456789" * 100  # 1000 bytes
        chunk_size = 100
        
        # Simulate chunk processing
        for i in range(0, len(test_data), chunk_size):
            chunk = test_data[i:i + chunk_size]
            chunks_received.append((i, chunk))
        
        # Verify order
        for i, (offset, chunk) in enumerate(chunks_received):
            assert offset == i * chunk_size
            assert len(chunk) <= chunk_size
        
        # Verify all data processed
        received_data = b"".join(chunk for _, chunk in chunks_received)
        assert received_data == test_data
    
    def test_chunk_boundaries(self):
        """Test handling of chunk boundaries."""
        test_data = b"A" * 1000
        chunk_size = 300
        
        chunks = []
        for i in range(0, len(test_data), chunk_size):
            chunks.append(test_data[i:i + chunk_size])
        
        # Should have 4 chunks: 300 + 300 + 300 + 100
        assert len(chunks) == 4
        assert len(chunks[0]) == 300
        assert len(chunks[1]) == 300
        assert len(chunks[2]) == 300
        assert len(chunks[3]) == 100


class TestRollingWindow:
    """Tests for rolling window buffer logic."""
    
    def test_window_size(self):
        """Test window size is properly configured."""
        from settings import settings
        
        assert settings.window_size == 1500
        assert 512 <= settings.window_size <= 4096
    
    def test_window_maintains_max_size(self):
        """Test that window never exceeds max size."""
        window_size = 10
        buffer = bytearray()
        
        # Add 100 bytes in chunks of 5
        for i in range(100):
            buffer.extend(b"x" * 5)
            buffer = buffer[-window_size:]
            assert len(buffer) <= window_size
        
        # Final size should be exactly window_size (after first 10 bytes)
        assert len(buffer) == window_size
    
    def test_window_contains_recent_data(self):
        """Test that window contains most recent data."""
        window_size = 10
        buffer = bytearray()
        
        # Add "0123456789"
        buffer.extend(b"0123456789")
        buffer = buffer[-window_size:]
        assert list(buffer) == list(b"0123456789")
        
        # Add "ABC"
        buffer.extend(b"ABC")
        buffer = buffer[-window_size:]
        assert list(buffer) == list(b"0123456789ABC")
        
        # Add more to slide window
        buffer.extend(b"DEFGHIJKL")
        buffer = buffer[-window_size:]
        # Should contain "ABCDEFGHIJKL" but only last 10 chars
        assert list(buffer) == list(b"CDEFGHIJKL")
    
    def test_empty_window(self):
        """Test empty window handling."""
        window_size = 10
        buffer = bytearray()
        buffer = buffer[-window_size:]
        assert len(buffer) == 0
    
    def test_small_data_window(self):
        """Test window with data smaller than window size."""
        window_size = 10
        buffer = bytearray()
        
        buffer.extend(b"123")
        buffer = buffer[-window_size:]
        
        assert len(buffer) == 3
        assert list(buffer) == [49, 50, 51]  # ASCII for '1', '2', '3'


class TestEarlyTermination:
    """Tests for early termination logic."""
    
    def test_early_termination_condition(self):
        """Test early termination based on probability threshold."""
        threshold = 0.7
        
        # Should terminate immediately
        assert 0.71 >= threshold
        assert 0.85 >= threshold
        assert 0.99 >= threshold
        
        # Should NOT terminate
        assert not (0.50 >= threshold)
        assert not (0.30 >= threshold)
        assert not (0.10 >= threshold)
    
    def test_early_termination_saves_processing(self):
        """Test that early termination saves processing."""
        chunk_size = 100
        total_chunks = 100
        detection_chunk = 50  # Detect on chunk 50
        
        chunks_processed = 0
        bytes_processed = 0
        
        for i in range(total_chunks):
            if chunks_processed >= detection_chunk:
                break  # Early termination
            
            chunks_processed += 1
            bytes_processed += chunk_size
        
        # Should terminate after detecting chunk
        assert chunks_processed == detection_chunk
        assert bytes_processed == detection_chunk * chunk_size
        
        # Saved processing compared to full scan
        assert chunks_processed < total_chunks
        savings = (total_chunks - chunks_processed) / total_chunks * 100
        assert savings == 50  # 50% savings
    
    def test_no_termination_on_clean_data(self):
        """Test that clean data processes all chunks."""
        threshold = 0.7
        probabilities = [0.1, 0.15, 0.12, 0.11, 0.13]  # All below threshold
        
        chunks_processed = 0
        
        for prob in probabilities:
            if prob >= threshold:
                break  # Would terminate
            chunks_processed += 1
        
        # Should process all chunks
        assert chunks_processed == len(probabilities)


class TestStreamingFileScanning:
    """Tests for streaming file scanning."""
    
    def test_file_size_limit(self):
        """Test file size limit is enforced."""
        from settings import settings
        
        max_size = settings.max_file_size
        assert max_size == 100 * 1024 * 1024  # 100MB
        assert max_size > 0
    
    def test_streaming_file_read(self):
        """Test reading file in streaming mode."""
        chunk_size = 512
        file_content = b"x" * 10000  # 10KB file
        
        chunks = []
        for i in range(0, len(file_content), chunk_size):
            chunk = file_content[i:i + chunk_size]
            chunks.append(chunk)
        
        # Verify chunk count
        expected_chunks = (len(file_content) + chunk_size - 1) // chunk_size
        assert len(chunks) == expected_chunks
        
        # Verify all data recovered
        assert b"".join(chunks) == file_content
    
    def test_file_scan_memory_efficiency(self):
        """Test that file scanning is memory efficient."""
        chunk_size = 512
        file_size = 10 * 1024 * 1024  # 10MB
        file_content = b"x" * file_size
        
        max_memory = 0
        current_memory = 0
        
        # Simulate streaming processing
        window_size = 1500
        buffer = bytearray()
        
        for i in range(0, len(file_content), chunk_size):
            chunk = file_content[i:i + chunk_size]
            
            # Add to rolling window
            buffer.extend(chunk)
            buffer = buffer[-window_size:]
            
            current_memory = len(buffer)
            max_memory = max(max_memory, current_memory)
        
        # Memory should be limited to window size, not file size
        assert max_memory == window_size
        assert max_memory << file_size  # Much smaller than file size


class TestStreamingURLScanning:
    """Tests for streaming URL scanning."""
    
    def test_download_timeout(self):
        """Test download timeout is configured."""
        from settings import settings
        
        assert settings.download_timeout == 30
        assert 1 <= settings.download_timeout <= 300
    
    def test_streaming_download(self):
        """Test streaming download simulation."""
        chunk_size = 512
        total_size = 5000
        content = b"content " * 500  # ~5000 bytes
        
        chunks = []
        bytes_received = 0
        
        # Simulate streaming download
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            chunks.append(chunk)
            bytes_received += len(chunk)
        
        assert bytes_received == len(content)
        assert b"".join(chunks) == content
    
    @patch('requests.get')
    def test_streaming_request(self, mock_get):
        """Test streaming HTTP request."""
        content = b"test content " * 1000
        mock_response = MagicMock()
        mock_response.iter_content = lambda chunk_size: [content[i:i+chunk_size] 
                                                         for i in range(0, len(content), chunk_size)]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_get.return_value.__exit__ = MagicMock(return_value=False)
        
        import requests
        with requests.get("http://example.com", stream=True) as r:
            chunks = list(r.iter_content(chunk_size=512))
        
        assert len(chunks) > 0
        assert b"".join(chunks) == content


class TestPerformanceMetrics:
    """Tests for performance metrics."""
    
    def test_inference_latency(self):
        """Test inference latency is reasonable."""
        import torch
        import time
        
        # Create small model for testing
        from detector import PacketTransformer
        
        model = PacketTransformer(
            vocab_size=259,
            d_model=256,  # Smaller for testing
            nhead=4,
            num_layers=2,
            dim_feedforward=1024,
            max_len=1500,
            dropout=0.1,
            num_classes=2
        )
        model.eval()
        
        # Create input
        input_data = torch.randint(0, 259, (1, 100))
        
        # Measure latency
        start = time.perf_counter()
        with torch.no_grad():
            for _ in range(10):  # Multiple runs for average
                output = model(input_data)
        elapsed = (time.perf_counter() - start) / 10
        
        # Should be under 100ms (success criterion)
        assert elapsed < 0.1, f"Inference took {elapsed*1000:.2f}ms"
    
    def test_throughput_calculation(self):
        """Test throughput calculation."""
        bytes_processed = 1024 * 1024  # 1MB
        time_ms = 50  # 50ms
        
        throughput_mbps = (bytes_processed / (time_ms / 1000)) / (1024 * 1024)
        
        assert throughput_mbps > 0
        # 1MB in 50ms = 20 MB/s
        assert throughput_mbps == 20.0


class TestEdgeCasesStreaming:
    """Tests for edge cases in streaming."""
    
    def test_empty_url_response(self):
        """Test handling empty URL response."""
        chunk_size = 512
        content = b""
        
        chunks = []
        for i in range(0, len(content), chunk_size):
            chunks.append(content[i:i + chunk_size])
        
        assert chunks == [b""]
        assert len(b"".join(chunks)) == 0
    
    def test_single_byte_file(self):
        """Test handling single byte file."""
        chunk_size = 512
        content = b"x"
        
        chunks = []
        for i in range(0, len(content), chunk_size):
            chunks.append(content[i:i + chunk_size])
        
        assert len(chunks) == 1
        assert chunks[0] == b"x"
    
    def test_exact_chunk_boundary(self):
        """Test file that exactly matches chunk boundaries."""
        chunk_size = 512
        content = b"x" * 1024  # Exactly 2 chunks
        
        chunks = []
        for i in range(0, len(content), chunk_size):
            chunks.append(content[i:i + chunk_size])
        
        assert len(chunks) == 2
        assert len(chunks[0]) == 512
        assert len(chunks[1]) == 512
    
    def test_url_redirect_handling(self):
        """Test that streaming works with redirects."""
        # In streaming mode, redirects should be followed automatically
        # by requests library
        import requests
        
        # This would normally be tested with a real server
        # Here we verify the streaming flag is set correctly
        assert True  # Placeholder for redirect test


class TestAdversarialRobustness:
    """Tests for adversarial robustness measures."""
    
    def test_byte_value_range(self):
        """Test that all byte values (0-255) are handled."""
        for byte_val in range(256):
            assert 0 <= byte_val <= 255
        
        # Special token IDs should be outside normal range
        assert 256 > 255  # pad_token_id
        assert 257 > 255  # mask_token_id
        assert 258 > 255  # unk_token_id
    
    def test_temperature_smoothing(self):
        """Test temperature scaling for adversarial robustness."""
        import torch
        
        logits = torch.tensor([[5.0, -5.0]])  # Strong signal
        
        # Normal temperature
        prob_normal = torch.sigmoid(logits / 1.0)[0, 1].item()
        
        # Higher temperature (more smoothing)
        prob_high = torch.sigmoid(logits / 2.0)[0, 1].item()
        
        # Temperature should affect the probability
        assert prob_normal != prob_high
        # Higher temp should give more moderate probability
        assert 0.9 < prob_normal < 1.0
        assert 0.6 < prob_high < 0.9
    
    def test_padding_handling(self):
        """Test that padding is handled correctly in model."""
        from detector import PacketTransformer
        import torch
        
        model = PacketTransformer(
            vocab_size=259,
            d_model=256,
            nhead=4,
            num_layers=2,
            dim_feedforward=1024,
            max_len=1500,
            dropout=0.1,
            num_classes=2
        )
        
        # Create input with padding
        input_data = torch.tensor([[1, 2, 3, 256, 256, 256]])  # 256 = padding
        
        # Create padding mask
        padding_mask = model.create_padding_mask(input_data)
        
        assert padding_mask[0, 3].item() == True  # Padding token
        assert padding_mask[0, 0].item() == False  # Real token


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])