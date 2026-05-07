"""Logging utilities for the crawl project."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    log_dir: Path,
    level: int = logging.DEBUG,
    file_prefix: str = "",
) -> logging.Logger:
    """
    Setup a logger with both console and file handlers.
    
    Args:
        name: Logger name (typically __name__)
        log_dir: Directory to save log files
        level: Logging level (DEBUG, INFO, etc.)
        file_prefix: Prefix for log file name
        
    Returns:
        Configured logger instance
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatters
    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # File handler (DEBUG level)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{file_prefix}_{timestamp}.log" if file_prefix else log_dir / f"{timestamp}.log"
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    # Console handler (INFO level, less verbose)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    return logger


class LogSummary:
    """Track statistics for logging summary at the end."""
    
    def __init__(self):
        self.success_count = 0
        self.failed_count = 0
        self.error_count = 0
        self.skipped_count = 0
        self.start_time = datetime.now()
    
    def add_success(self, count: int = 1):
        """Increment success counter."""
        self.success_count += count
    
    def add_failed(self, count: int = 1):
        """Increment failed counter."""
        self.failed_count += count
    
    def add_error(self, count: int = 1):
        """Increment error counter."""
        self.error_count += count
    
    def add_skipped(self, count: int = 1):
        """Increment skipped counter."""
        self.skipped_count += count
    
    def get_duration(self) -> str:
        """Get elapsed time as formatted string."""
        elapsed = datetime.now() - self.start_time
        total_seconds = int(elapsed.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def get_summary_text(self) -> str:
        """Get summary text for logging."""
        total = self.success_count + self.failed_count + self.error_count + self.skipped_count
        return (
            f"Summary: {self.success_count} ok, "
            f"{self.failed_count} failed, "
            f"{self.error_count} errors, "
            f"{self.skipped_count} skipped "
            f"({total} total) in {self.get_duration()}"
        )
