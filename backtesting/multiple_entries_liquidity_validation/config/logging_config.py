"""
Logging Configuration
=====================

Set's up Python's logging system for the backtester

"""
import logging

from datetime import datetime
from typing import Optional
from pathlib import Path

FILE_FORMAT = "%(asctime)s - %(levelname)-8s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOG_PATH = '/Users/martin/Documents/Work/Programming_VS_Code/Python_Trading/backtesting/multiple_entries_liquidity_validation/logs'

def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: str = LOG_PATH,
) -> logging.Logger:
    """
    Configure the logging system for the backtester.

    Call this once at the start of program (in run.py)
    After calling this, any module can use logging.getLogger(__name__)

    Args:
        level: Minimum log level ("DEBUG", "INFO", etc.)
        log_file: Name of log file
        log_dir: Directory for log files
    
    Returns:
        root_logger
    """
    # Get the root logger
    root_logger = logging.getLogger()

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Set root level
    root_logger.setLevel(level)

    # File handler
    # ------------
    
    # Create log directory if needed
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Set up handler
    file_path = log_path / log_file
    handler = logging.FileHandler(filename=file_path, encoding='utf-8')
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(FILE_FORMAT, DATE_FORMAT))
    root_logger.addHandler(handler)
    
    # Log the setup itself
    root_logger.info("Logging configured: level=%s, file=%s", level, log_file or "disabled")

    return root_logger

def get_logger(name: Optional[str] = None, level: str = "INFO") -> logging.Logger:
    """
    
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    if name:
        log_file = f"backtest_{name}_{timestamp}.log"
    else:
        log_file = f"backtest_{timestamp}.log"
    
    return setup_logging(level, log_file)