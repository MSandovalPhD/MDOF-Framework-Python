import logging
from datetime import datetime
from typing import Any

class LisuLogger:
    """Handles logging of LISU events to a timestamped file."""
    def __init__(self, log_dir: str = "./logs"):
        """Initialize logger with a timestamped file."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file = f"{log_dir}/LISU_{timestamp}.txt"
        logging.basicConfig(
            filename=log_file,
            level=logging.DEBUG,
            format='%(asctime)s, %(message)s'
        )
        self.logger = logging.getLogger("LisuLogger")

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
