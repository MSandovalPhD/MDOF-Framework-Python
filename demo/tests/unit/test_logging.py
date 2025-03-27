"""
Test cases for LISU logging functionality.
"""

import unittest
from unittest.mock import Mock, patch, mock_open
import json
import os
from datetime import datetime
from pathlib import Path
from LISU.logging import LisuLogger

class TestLisuLogger(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.test_log_dir = Path("test_logs")
        self.logger = LisuLogger(self.test_log_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        # Remove test log directory and its contents
        if self.test_log_dir.exists():
            for file in self.test_log_dir.glob("*"):
                file.unlink()
            self.test_log_dir.rmdir()

    def test_initialization(self):
        """Test logger initialization."""
        self.assertTrue(self.test_log_dir.exists())
        self.assertTrue(self.logger.log_file.exists())
        self.assertIsNotNone(self.logger.logger)
        self.assertEqual(self.logger.metrics["events_processed"], 0)
        self.assertEqual(self.logger.metrics["errors"], 0)
        self.assertEqual(self.logger.metrics["warnings"], 0)

    @patch('builtins.open', new_callable=mock_open)
    def test_log_event(self, mock_file):
        """Test event logging."""
        # Test basic event logging
        self.logger.log_event("test_event", {"key": "value"})
        mock_file.assert_called()
        
        # Verify event format
        call_args = mock_file.call_args[0][1]
        event_data = json.loads(call_args)
        self.assertEqual(event_data["type"], "test_event")
        self.assertEqual(event_data["details"]["key"], "value")
        self.assertIn("timestamp", event_data["details"])

    def test_log_device_event(self):
        """Test device-specific event logging."""
        with patch('builtins.open', new_callable=mock_open) as mock_file:
            self.logger.log_device_event("test_device", "connected", {"status": "ok"})
            mock_file.assert_called()
            
            # Verify event format
            call_args = mock_file.call_args[0][1]
            event_data = json.loads(call_args)
            self.assertEqual(event_data["type"], "device_connected")
            self.assertEqual(event_data["details"]["device"], "test_device")
            self.assertEqual(event_data["details"]["status"], "ok")

    def test_log_transformation(self):
        """Test transformation event logging."""
        with patch('builtins.open', new_callable=mock_open) as mock_file:
            self.logger.log_transformation(
                "test_device",
                0.5,
                0.75,
                "exponential",
                {"base": 2.0}
            )
            mock_file.assert_called()
            
            # Verify event format
            call_args = mock_file.call_args[0][1]
            event_data = json.loads(call_args)
            self.assertEqual(event_data["type"], "transformation_applied")
            self.assertEqual(event_data["details"]["device"], "test_device")
            self.assertEqual(event_data["details"]["input"], 0.5)
            self.assertEqual(event_data["details"]["output"], 0.75)
            self.assertEqual(event_data["details"]["transform_type"], "exponential")

    def test_log_error(self):
        """Test error logging."""
        with patch('builtins.open', new_callable=mock_open) as mock_file:
            error = ValueError("Test error")
            context = {"device": "test_device", "operation": "test_op"}
            self.logger.log_error(error, context)
            mock_file.assert_called()
            
            # Verify error metrics
            self.assertEqual(self.logger.metrics["errors"], 1)
            
            # Verify event format
            call_args = mock_file.call_args[0][1]
            event_data = json.loads(call_args)
            self.assertEqual(event_data["type"], "error")
            self.assertEqual(event_data["details"]["error_type"], "ValueError")
            self.assertEqual(event_data["details"]["error_message"], "Test error")
            self.assertEqual(event_data["details"]["context"], context)

    def test_log_warning(self):
        """Test warning logging."""
        with patch('builtins.open', new_callable=mock_open) as mock_file:
            self.logger.log_warning("Test warning", {"device": "test_device"})
            mock_file.assert_called()
            
            # Verify warning metrics
            self.assertEqual(self.logger.metrics["warnings"], 1)
            
            # Verify event format
            call_args = mock_file.call_args[0][1]
            event_data = json.loads(call_args)
            self.assertEqual(event_data["type"], "warning")
            self.assertEqual(event_data["details"]["message"], "Test warning")
            self.assertEqual(event_data["details"]["context"]["device"], "test_device")

    def test_get_metrics(self):
        """Test metrics retrieval."""
        # Log some events
        self.logger.log_event("test_event", {})
        self.logger.log_error(ValueError("test"), {})
        self.logger.log_warning("test", {})
        
        # Get metrics
        metrics = self.logger.get_metrics()
        
        # Verify metrics
        self.assertEqual(metrics["events_processed"], 3)
        self.assertEqual(metrics["errors"], 1)
        self.assertEqual(metrics["warnings"], 1)
        self.assertIn("uptime", metrics)

    def test_cleanup(self):
        """Test logger cleanup."""
        # Start event processing thread
        self.logger.event_thread.start()
        
        # Cleanup
        self.logger.cleanup()
        
        # Verify thread is stopped
        self.assertFalse(self.logger.event_thread.is_alive())

if __name__ == '__main__':
    unittest.main() 