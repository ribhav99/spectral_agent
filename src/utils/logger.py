import logging
import sys
from datetime import datetime
import os
from pathlib import Path

from .. import config

def setup_logger(name=None):
    """
    Setup logger with standardized formatting
    
    Args:
        name: Optional name for the logger
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parents[2] / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name or __name__)
    
    # Set level based on config
    log_level = getattr(logging, config.LOG_LEVEL.upper())
    logger.setLevel(log_level)
    
    # Create handlers for console and file output
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"trading_agent_{timestamp}.log"
    file_handler = logging.FileHandler(log_file)
    
    # Create formatter and add to handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger 