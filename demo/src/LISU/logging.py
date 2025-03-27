"""
LISU Framework Logging Module
Provides comprehensive logging functionality for the LISU framework.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import json
import threading
from queue import Queue
import time

class LisuLogger:
    """Manages logging for the LISU framework with support for multiple output formats."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialise the LISU logger.
        
        Args:
            log_dir: Directory for log files. If None, uses 'logs' in the current directory.
        """
        self.log_dir = log_dir or Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # Set up logging format
        self.log_format = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(module)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"lisu_{timestamp}.log"
        
        # Set up file handler
        self.file_handler = logging.FileHandler(self.log_file)
        self.file_handler.setFormatter(self.log_format)
        
        # Set up console handler
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setFormatter(self.log_format)
        
        # Set up logger
        self.logger = logging.getLogger("LISU")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.file_handler)
        self.logger.addHandler(self.console_handler)
        
        # Set up event logging
        self.event_queue = Queue()
        self.event_thread = threading.Thread(target=self._process_events, daemon=True)
        self.event_thread.start()
        
        # Performance metrics
        self.metrics: Dict[str, Any] = {
            "start_time": time.time(),
            "events_processed": 0,
            "errors": 0,
            "warnings": 0
        }
        
        self.logger.info("LISU Logger initialised")

    def _process_events(self):
        """Process events from the queue in a separate thread."""
        while True:
            try:
                event = self.event_queue.get()
                if event is None:  # Shutdown signal
                    break
                    
                self._write_event(event)
                self.metrics["events_processed"] += 1
                
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")
                self.metrics["errors"] += 1
                
            finally:
                self.event_queue.task_done()

    def _write_event(self, event: Dict[str, Any]):
        """
        Write an event to the log file.
        
        Args:
            event: Event dictionary containing event details
        """
        try:
            event["timestamp"] = datetime.now().isoformat()
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            self.logger.error(f"Error writing event: {e}")

    def log_event(self, event_type: str, details: Dict[str, Any], level: str = "INFO"):
        """
        Log an event with the specified type and details.
        
        Args:
            event_type: Type of event (e.g., "device_connected", "command_sent")
            details: Dictionary containing event details
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        event = {
            "type": event_type,
            "details": details,
            "level": level
        }
        self.event_queue.put(event)
        
        # Also log to standard logger
        log_func = getattr(self.logger, level.lower())
        log_func(f"{event_type}: {json.dumps(details)}")

    def log_device_event(self, device_name: str, event_type: str, details: Dict[str, Any]):
        """
        Log a device-specific event.
        
        Args:
            device_name: Name of the device
            event_type: Type of event
            details: Event details
        """
        self.log_event(
            f"device_{event_type}",
            {"device": device_name, **details}
        )

    def log_transformation(self, device_name: str, input_value: float, output_value: float, 
                          transform_type: str, config: Dict[str, Any]):
        """
        Log a transformation event.
        
        Args:
            device_name: Name of the device
            input_value: Original input value
            output_value: Transformed output value
            transform_type: Type of transformation applied
            config: Transformation configuration
        """
        self.log_event(
            "transformation_applied",
            {
                "device": device_name,
                "input": input_value,
                "output": output_value,
                "transform_type": transform_type,
                "config": config
            }
        )

    def log_error(self, error: Exception, context: Dict[str, Any]):
        """
        Log an error with context.
        
        Args:
            error: Exception that occurred
            context: Additional context information
        """
        self.metrics["errors"] += 1
        self.log_event(
            "error",
            {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context
            },
            "ERROR"
        )

    def log_warning(self, message: str, context: Dict[str, Any]):
        """
        Log a warning with context.
        
        Args:
            message: Warning message
            context: Additional context information
        """
        self.metrics["warnings"] += 1
        self.log_event(
            "warning",
            {
                "message": message,
                "context": context
            },
            "WARNING"
        )

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current logging metrics.
        
        Returns:
            Dictionary containing logging metrics
        """
        self.metrics["uptime"] = time.time() - self.metrics["start_time"]
        return self.metrics

    def cleanup(self):
        """Clean up logging resources."""
        self.event_queue.put(None)  # Signal event thread to stop
        self.event_thread.join()
        self.logger.info("LISU Logger cleaned up") 