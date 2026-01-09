"""
Unit tests for the FastAPI application endpoints.
Tests API endpoints, request validation, and responses.
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAPIEndpoints:
    """Tests for API endpoints."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch('app.get_detector_instance') as mock_detector, \
             patch('app.get_threat_manager_instance') as mock_tm, \
             patch('app.get_database_instance') as mock_db:
            
            # Mock detector
            mock_detector.return_value = MagicMock()
            
            # Mock threat manager
            mock_tm.return_value = MagicMock()
            
            # Mock database
            mock_db.return_value = MagicMock()
            
            yield {
                'detector': mock_detector,
                'threat_manager': mock_tm,
                'database': mock_db
            }
    
    def test_root_endpoint(self, mock_dependencies):
        """Test root endpoint returns API info."""
        from app import app
        
        with TestClient(app) as client:
            response = client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Real-Time Malware Detection Gateway"
            assert data["version"] == "1.0.0"
            assert data["status"] == "running"
            assert "endpoints" in data
    
    def test_health_endpoint(self, mock_dependencies):
        """Test health endpoint returns status."""
        from app import app
        
        with patch('psutil.Process') as mock_psutil:
            mock_process = MagicMock()
            mock_process.memory_info.return_value.rss = 1024 * 1024 * 100  # 100MB
            mock_psutil.return_value = mock_process
            
            with TestClient(app) as client:
                response = client.get("/health")
                
                assert response.status_code == 200
                data = response.json()
                assert "status" in data
                assert "model" in data
                assert "database" in data
                assert "uptime_seconds" in data
                assert "memory_usage_mb" in data
    
    def test_settings_endpoint(self, mock_dependencies):
        """Test settings endpoint returns config."""
        from app import app
        
        with TestClient(app) as client:
            response = client.get("/settings")
            
            assert response.status_code == 200
            data = response.json()
            assert data["confidence_threshold"] == 0.7
            assert data["chunk_size"] == 512
            assert data["window_size"] == 1500
            assert data["temperature"] == 1.0
            assert "risk_levels" in data
    
    def test_threshold_update(self, mock_dependencies):
        """Test threshold update endpoint."""
        from app import app
        
        with TestClient(app) as client:
            response = client.post(
                "/settings/threshold",
                json={"threshold": 0.8}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["old_threshold"] == 0.7
            assert data["new_threshold"] == 0.8
            assert data["status"] == "updated"
    
    def test_threshold_update_validation(self, mock_dependencies):
        """Test threshold update validation."""
        from app import app
        
        with TestClient(app) as client:
            # Threshold too high
            response = client.post(
                "/settings/threshold",
                json={"threshold": 1.5}
            )
            assert response.status_code == 422
            
            # Threshold too low
            response = client.post(
                "/settings/threshold",
                json={"threshold": -0.1}
            )
            assert response.status_code == 422


class TestURLScanEndpoint:
    """Tests for URL scanning endpoint."""
    
    @pytest.fixture
    def mock_detector(self):
        """Create mock detector."""
        mock = MagicMock()
        mock.scan_url.return_value = MagicMock(
            source="http://example.com/file.exe",
            source_type="URL",
            probability=0.85,
            risk_level="HIGH",
            bytes_scanned=1024,
            blocked=True,
            scan_time_ms=50.5,
            status="THREAT_DETECTED",
            details={"log_id": 1}
        )
        return mock
    
    def test_scan_url_success(self, mock_detector):
        """Test successful URL scan."""
        from app import app
        
        with patch('app.get_detector_instance', return_value=mock_detector):
            with TestClient(app) as client:
                response = client.post(
                    "/scan/url",
                    json={"url": "http://example.com/file.exe"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["source"] == "http://example.com/file.exe"
                assert data["source_type"] == "URL"
                assert data["probability"] == 0.85
                assert data["risk_level"] == "HIGH"
                assert data["blocked"] is True
    
    def test_scan_url_validation(self):
        """Test URL validation."""
        from app import app
        
        with TestClient(app) as client:
            # Invalid URL (non-HTTP)
            response = client.post(
                "/scan/url",
                json={"url": "ftp://example.com/file.exe"}
            )
            assert response.status_code == 422
            
            # Invalid URL format
            response = client.post(
                "/scan/url",
                json={"url": "not-a-url"}
            )
            assert response.status_code == 422
    
    def test_scan_url_block_option(self, mock_detector):
        """Test block_on_detection option."""
        from app import app
        
        with patch('app.get_detector_instance', return_value=mock_detector):
            with TestClient(app) as client:
                response = client.post(
                    "/scan/url",
                    json={
                        "url": "http://example.com/file.exe",
                        "block_on_detection": False
                    }
                )
                
                assert response.status_code == 200


class TestFileScanEndpoint:
    """Tests for file scanning endpoint."""
    
    @pytest.fixture
    def mock_detector(self):
        """Create mock detector."""
        mock = MagicMock()
        mock.scan_file.return_value = MagicMock(
            source="test.exe",
            source_type="FILE",
            probability=0.15,
            risk_level="BENIGN",
            bytes_scanned=2048,
            blocked=False,
            scan_time_ms=30.0,
            status="CLEAN",
            details={"log_id": 2}
        )
        return mock
    
    def test_scan_file_success(self, mock_detector):
        """Test successful file scan."""
        from app import app
        
        with patch('app.get_detector_instance', return_value=mock_detector):
            with TestClient(app) as client:
                response = client.post(
                    "/scan/file",
                    files={"file": ("test.exe", b"file content", "application/octet-stream")}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["source"] == "test.exe"
                assert data["source_type"] == "FILE"
                assert data["risk_level"] == "BENIGN"
                assert data["blocked"] is False
    
    def test_scan_file_size_limit(self, mock_detector):
        """Test file size limit enforcement."""
        from app import app
        import settings
        
        with patch('app.get_detector_instance', return_value=mock_detector):
            with TestClient(app) as client:
                # Create large file content
                large_content = b"x" * (settings.max_file_size + 1)
                
                response = client.post(
                    "/scan/file",
                    files={"file": ("large.exe", large_content)}
                )
                
                assert response.status_code == 413


class TestThreatEndpoints:
    """Tests for threat management endpoints."""
    
    @pytest.fixture
    def mock_threat_manager(self):
        """Create mock threat manager."""
        mock = MagicMock()
        mock.get_threats.return_value = [
            {
                "id": 1,
                "source": "http://example.com/malware.exe",
                "source_type": "URL",
                "probability": 0.85,
                "bytes_scanned": 1024,
                "risk_level": "HIGH",
                "timestamp": "2024-01-01T00:00:00",
                "details": None,
                "blocked": True
            }
        ]
        mock.get_stats.return_value = {
            "session_stats": {},
            "database_stats": {
                "total": 10,
                "critical": 1,
                "high": 2,
                "medium": 3,
                "low": 2,
                "benign": 2,
                "total_bytes_scanned": 10000
            }
        }
        mock.get_risk_distribution.return_value = [
            {"risk_level": "HIGH", "count": 5, "avg_probability": 0.8},
            {"risk_level": "MEDIUM", "count": 3, "avg_probability": 0.6}
        ]
        return mock
    
    def test_get_threats(self, mock_threat_manager):
        """Test getting threat list."""
        from app import app
        
        with patch('app.get_threat_manager_instance', return_value=mock_threat_manager):
            with TestClient(app) as client:
                response = client.get("/threats")
                
                assert response.status_code == 200
                data = response.json()
                assert "threats" in data
                assert "total" in data
                assert "limit" in data
                assert "offset" in data
    
    def test_get_threats_pagination(self, mock_threat_manager):
        """Test threat pagination."""
        from app import app
        
        with patch('app.get_threat_manager_instance', return_value=mock_threat_manager):
            with TestClient(app) as client:
                response = client.get("/threats?limit=50&offset=10")
                
                assert response.status_code == 200
                data = response.json()
                assert data["limit"] == 50
                assert data["offset"] == 10
    
    def test_get_threats_filtering(self, mock_threat_manager):
        """Test threat filtering."""
        from app import app
        
        with patch('app.get_threat_manager_instance', return_value=mock_threat_manager):
            with TestClient(app) as client:
                response = client.get("/threats?risk_level=HIGH&source_type=URL")
                
                assert response.status_code == 200
    
    def test_get_threat_stats(self, mock_threat_manager):
        """Test getting threat statistics."""
        from app import app
        
        with patch('app.get_threat_manager_instance', return_value=mock_threat_manager):
            with TestClient(app) as client:
                response = client.get("/threats/stats")
                
                assert response.status_code == 200
                data = response.json()
                assert data["total"] == 10
                assert data["critical"] == 1
                assert data["high"] == 2
    
    def test_get_threat_distribution(self, mock_threat_manager):
        """Test getting threat distribution."""
        from app import app
        
        with patch('app.get_threat_manager_instance', return_value=mock_threat_manager):
            with TestClient(app) as client:
                response = client.get("/threats/distribution")
                
                assert response.status_code == 200
                data = response.json()
                assert isinstance(data, list)
    
    def test_get_threat_by_id(self):
        """Test getting specific threat by ID."""
        from app import app
        
        mock_db = MagicMock()
        mock_db.get_threat_by_id.return_value = {
            "id": 1,
            "source": "http://example.com/malware.exe",
            "source_type": "URL",
            "probability": 0.85,
            "bytes_scanned": 1024,
            "risk_level": "HIGH",
            "timestamp": "2024-01-01T00:00:00"
        }
        
        with patch('app.get_database_instance', return_value=mock_db):
            with TestClient(app) as client:
                response = client.get("/threats/1")
                
                assert response.status_code == 200
                data = response.json()
                assert data["id"] == 1
    
    def test_get_threat_not_found(self):
        """Test 404 for non-existent threat."""
        from app import app
        
        mock_db = MagicMock()
        mock_db.get_threat_by_id.return_value = None
        
        with patch('app.get_database_instance', return_value=mock_db):
            with TestClient(app) as client:
                response = client.get("/threats/999")
                
                assert response.status_code == 404


class TestStatsEndpoint:
    """Tests for statistics endpoint."""
    
    def test_get_stats(self):
        """Test getting overall statistics."""
        from app import app
        
        mock_detector = MagicMock()
        mock_detector.get_stats.return_value = {
            "total_scans": 100,
            "threats_blocked": 5,
            "total_bytes_scanned": 1000000
        }
        
        mock_tm = MagicMock()
        mock_tm.get_stats.return_value = {}
        
        with patch('app.get_detector_instance', return_value=mock_detector), \
             patch('app.get_threat_manager_instance', return_value=mock_tm):
            with TestClient(app) as client:
                response = client.get("/stats")
                
                assert response.status_code == 200
                data = response.json()
                assert "detector" in data
                assert "threat_manager" in data
                assert "uptime_seconds" in data


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])