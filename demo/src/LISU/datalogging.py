import logging
from datetime import datetime
from typing import Any
from pathlib import Path

class LisuLogger:
    """Handles logging of LISU events to a timestamped file."""
    def __init__(self, log_dir: str = "./logs"):
        """Initialize logger with a timestamped file."""
        # Convert to absolute path and ensure directory exists
        log_dir_path = Path(log_dir).resolve()
        log_dir_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file = log_dir_path / f"LISU_{timestamp}.txt"
        print(f"Initializing logger with file: {log_file}")  # Debug output
        
        logging.basicConfig(
            filename=str(log_file),  # Convert Path to string
            level=logging.DEBUG,
            format='%(asctime)s, %(message)s'
        )
        self.logger = logging.getLogger("LisuLogger")
        
        # Test log to verify setup
        self.logger.debug("Logger initialized successfully")

    def record_log(self, message: Any) -> None:
        """Log a message to the file."""
        try:
            self.logger.info(str(message))
        except Exception as e:
            print(f"Failed to log message: {e}")

# Singleton instance for convenience
logger = LisuLogger()

def recordLog(message: Any) -> None:
    """Global function to record a log message."""
    logger.record_log(message)

if __name__ == "__main__":
    # Example usage
    recordLog("Test log entry")
