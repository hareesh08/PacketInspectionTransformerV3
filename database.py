"""
SQLite database operations for threat logging.
Provides thread-safe database access with proper indexing.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Generator
from contextlib import contextmanager
from threading import Lock
import logging

from models import RiskLevel, SourceType

logger = logging.getLogger(__name__)


class ThreatDatabase:
    """
    SQLite database manager for threat logs.
    Implements connection pooling and proper indexing for performance.
    """
    
    # Table schema
    SCHEMA = """
        CREATE TABLE IF NOT EXISTS threats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_type TEXT NOT NULL,
            probability REAL NOT NULL,
            bytes_scanned INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            details TEXT,
            blocked BOOLEAN DEFAULT FALSE,
            scan_time_ms REAL DEFAULT 0.0,
            status TEXT DEFAULT 'THREAT_DETECTED'
        )
    """
    
    # Indexes for common queries
    INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_timestamp ON threats(timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_risk_level ON threats(risk_level)",
        "CREATE INDEX IF NOT EXISTS idx_source ON threats(source)",
        "CREATE INDEX IF NOT EXISTS idx_source_type ON threats(source_type)",
        "CREATE INDEX IF NOT EXISTS idx_probability ON threats(probability)",
        "CREATE INDEX IF NOT EXISTS idx_blocked ON threats(blocked)",
    ]
    
    def __init__(self, db_path: str = "threats.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._lock = Lock()
        self._init_database()
        logger.info(f"ThreatDatabase initialized: {self.db_path}")
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Get database connection with automatic cleanup.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for concurrency
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance durability and speed
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _init_database(self) -> None:
        """Initialize database schema and indexes."""
        with self.get_connection() as conn:
            conn.execute(self.SCHEMA)
            for index_sql in self.INDEXES:
                try:
                    conn.execute(index_sql)
                except sqlite3.OperationalError:
                    pass  # Index already exists
        logger.info("Database schema initialized")
    
    def log_threat(
        self,
        source: str,
        source_type: str,
        probability: float,
        bytes_scanned: int,
        risk_level: str,
        details: Optional[Dict[str, Any]] = None,
        blocked: bool = False,
        scan_time_ms: float = 0.0,
        status: str = "THREAT_DETECTED"
    ) -> int:
        """
        Log a detected threat to the database.
        
        Args:
            source: URL or filename
            source_type: Type of source (URL/FILE)
            probability: Malware probability from model
            bytes_scanned: Bytes processed
            risk_level: Computed risk level
            details: Additional details dictionary
            blocked: Whether access was blocked
            scan_time_ms: Time taken for scan
            status: Scan status
            
        Returns:
            int: ID of inserted row
        """
        details_json = json.dumps(details) if details else None
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO threats 
                (source, source_type, probability, bytes_scanned, risk_level, 
                 details, blocked, scan_time_ms, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                source, source_type, probability, bytes_scanned, risk_level,
                details_json, blocked, scan_time_ms, status
            ))
            
            threat_id = cursor.lastrowid
            logger.info(f"Logged threat ID {threat_id}: {source} ({risk_level}, {probability:.2%})")
            
            return threat_id
    
    def log_clean_scan(
        self,
        source: str,
        source_type: str,
        probability: float,
        bytes_scanned: int,
        details: Optional[Dict[str, Any]] = None,
        scan_time_ms: float = 0.0
    ) -> int:
        """
        Log a clean (non-malicious) scan result.
        
        Args:
            source: URL or filename
            source_type: Type of source
            probability: Malware probability
            bytes_scanned: Bytes processed
            details: Additional details
            scan_time_ms: Time taken for scan
            
        Returns:
            int: ID of inserted row
        """
        risk_level = self.calculate_risk_level(probability)
        return self.log_threat(
            source=source,
            source_type=source_type,
            probability=probability,
            bytes_scanned=bytes_scanned,
            risk_level=risk_level,
            details=details,
            blocked=False,
            scan_time_ms=scan_time_ms,
            status="CLEAN"
        )
    
    def get_recent_threats(
        self,
        limit: int = 100,
        offset: int = 0,
        risk_level: Optional[str] = None,
        source_type: Optional[str] = None,
        blocked: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent threat logs with optional filtering.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            risk_level: Filter by risk level
            source_type: Filter by source type
            blocked: Filter by blocked status
            
        Returns:
            List of threat dictionaries
        """
        query = "SELECT * FROM threats WHERE 1=1"
        params = []
        
        if risk_level:
            query += " AND risk_level = ?"
            params.append(risk_level)
        
        if source_type:
            query += " AND source_type = ?"
            params.append(source_type)
        
        if blocked is not None:
            query += " AND blocked = ?"
            params.append(blocked)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                data = dict(zip(columns, row))
                # Parse details JSON
                if data.get('details'):
                    try:
                        data['details'] = json.loads(data['details'])
                    except json.JSONDecodeError:
                        pass
                results.append(data)
            
            return results
    
    def get_threat_by_id(self, threat_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific threat by ID.
        
        Args:
            threat_id: Threat ID to retrieve
            
        Returns:
            Threat dictionary or None
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM threats WHERE id = ?",
                (threat_id,)
            )
            row = cursor.fetchone()
            
            if row:
                data = dict(row)
                if data.get('details'):
                    try:
                        data['details'] = json.loads(data['details'])
                    except json.JSONDecodeError:
                        pass
                return data
            return None
    
    def get_threat_stats(self) -> Dict[str, Any]:
        """
        Get aggregated threat statistics.
        
        Returns:
            Dictionary with threat statistics
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN risk_level = 'CRITICAL' THEN 1 ELSE 0 END) as critical,
                    SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) as high,
                    SUM(CASE WHEN risk_level = 'MEDIUM' THEN 1 ELSE 0 END) as medium,
                    SUM(CASE WHEN risk_level = 'LOW' THEN 1 ELSE 0 END) as low,
                    SUM(CASE WHEN risk_level = 'BENIGN' THEN 1 ELSE 0 END) as benign,
                    SUM(bytes_scanned) as total_bytes_scanned,
                    SUM(CASE WHEN blocked = 1 THEN 1 ELSE 0 END) as total_blocked,
                    AVG(scan_time_ms) as avg_scan_time_ms,
                    MAX(timestamp) as last_threat_time
                FROM threats
            """)
            
            row = cursor.fetchone()
            return dict(row) if row else {}
    
    def get_threats_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get threats within a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum results
            
        Returns:
            List of threats
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM threats
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (start_time, end_time, limit))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_threat_distribution(self) -> List[Dict[str, Any]]:
        """
        Get threat distribution by risk level over time.
        
        Returns:
            List of distribution buckets
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    risk_level,
                    COUNT(*) as count,
                    AVG(probability) as avg_probability,
                    SUM(bytes_scanned) as total_bytes
                FROM threats
                WHERE timestamp > datetime('now', '-24 hours')
                GROUP BY risk_level
                ORDER BY 
                    CASE risk_level
                        WHEN 'CRITICAL' THEN 1
                        WHEN 'HIGH' THEN 2
                        WHEN 'MEDIUM' THEN 3
                        WHEN 'LOW' THEN 4
                        WHEN 'BENIGN' THEN 5
                    END
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def calculate_risk_level(self, probability: float) -> str:
        """
        Calculate risk level from probability.
        
        Args:
            probability: Malware probability (0.0 to 1.0)
            
        Returns:
            Risk level string
        """
        if probability >= 0.9:
            return "CRITICAL"
        elif probability >= 0.7:
            return "HIGH"
        elif probability >= 0.5:
            return "MEDIUM"
        elif probability >= 0.3:
            return "LOW"
        else:
            return "BENIGN"
    
    def cleanup_old_threats(self, days: int = 30) -> int:
        """
        Delete threats older than specified days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of deleted rows
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM threats
                WHERE timestamp < datetime('now', ?)
            """, (f'-{days} days',))
            
            deleted = cursor.rowcount
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old threat records")
            
            return deleted
    
    def get_total_count(self) -> int:
        """
        Get total number of threat records.
        
        Returns:
            Total count
        """
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM threats")
            return cursor.fetchone()[0]
    
    def vacuum(self) -> None:
        """Optimize database file size."""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
        logger.info("Database vacuum completed")


# Global database instance
database: Optional[ThreatDatabase] = None


def get_database(db_path: str = "threats.db") -> ThreatDatabase:
    """
    Get or create database instance.
    
    Args:
        db_path: Database file path
        
    Returns:
        ThreatDatabase instance
    """
    global database
    if database is None or database.db_path != db_path:
        database = ThreatDatabase(db_path)
    return database


def init_database(db_path: str = "threats.db") -> ThreatDatabase:
    """
    Initialize database with given path.
    
    Args:
        db_path: Database file path
        
    Returns:
        Initialized ThreatDatabase
    """
    global database
    database = ThreatDatabase(db_path)
    return database