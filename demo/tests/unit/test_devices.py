"""
Test cases for LISU device handling and validation.
"""

import unittest
from unittest.mock import Mock, patch
import numpy as np
from LISU.devices import InputDevice
from LISU.logging import LisuLogger

class TestInputDevice(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.vid = 0x046D
        self.pid = 0xB03A
        self.name = "Test Device"
        self.dev_config = {
            "axes": ["x", "y", "z"],
            "buttons": ["left", "right", "middle"],
            "type": "mouse"
        }
        self.device = InputDevice(self.vid, self.pid, self.name, self.dev_config)

    def test_initialization(self):
        """Test device initialization."""
        self.assertEqual(self.device.vid, self.vid)
        self.assertEqual(self.device.pid, self.pid)
        self.assertEqual(self.device.name, self.name)
        self.assertEqual(self.device.dev_config, self.dev_config)
        self.assertIsNotNone(self.device.specs)
        self.assertIsNone(self.device.device)
        self.assertIsNone(self.device.callback)
        self.assertIsNone(self.device.button_callback)

    def test_axis_validation(self):
        """Test axis value validation."""
        # Test valid values
        self.assertEqual(self.device._validate_axis_value(127, "x"), 1.0)
        self.assertEqual(self.device._validate_axis_value(-127, "x"), -1.0)
        self.assertEqual(self.device._validate_axis_value(0, "x"), 0.0)
        
        # Test value clamping
        self.assertEqual(self.device._validate_axis_value(200, "x"), 1.0)
        self.assertEqual(self.device._validate_axis_value(-200, "x"), -1.0)
        
        # Test deadzone
        self.device._validate_axis_value(10, "x")  # Set initial value
        self.assertEqual(self.device._validate_axis_value(11, "x"), 0.07874015748031496)  # Within deadzone
        self.assertEqual(self.device._validate_axis_value(20, "x"), 0.15748031496062992)  # Outside deadzone

    def test_button_validation(self):
        """Test button state validation."""
        # Test valid states
        states = [True, False, True]
        validated = self.device._validate_button_states(states)
        self.assertEqual(validated, states)
        
        # Test state truncation
        long_states = [True] * 10
        validated = self.device._validate_button_states(long_states)
        self.assertEqual(len(validated), 8)  # MAX_BUTTON_COUNT
        
        # Test state padding
        short_states = [True]
        validated = self.device._validate_button_states(short_states)
        self.assertEqual(len(validated), len(self.device.state["buttons"]))

    def test_sensitive_data_filtering(self):
        """Test sensitive data filtering."""
        data = {
            "name": "test",
            "password": "secret123",
            "api_key": "abc123",
            "nested": {
                "secret_token": "xyz789",
                "normal_data": "value"
            }
        }
        filtered = self.device._filter_sensitive_data(data)
        self.assertEqual(filtered["password"], "[REDACTED]")
        self.assertEqual(filtered["api_key"], "[REDACTED]")
        self.assertEqual(filtered["nested"]["secret_token"], "[REDACTED]")
        self.assertEqual(filtered["nested"]["normal_data"], "value")

    @patch('pywinusb.hid.HidDeviceFilter')
    def test_device_open_close(self, mock_hid_filter):
        """Test device opening and closing."""
        # Mock HID device
        mock_device = Mock()
        mock_hid_filter.return_value.get_devices.return_value = [mock_device]
        
        # Test successful open
        self.device.open()
        mock_device.open.assert_called_once()
        mock_device.set_raw_data_handler.assert_called_once_with(self.device.process)
        
        # Test successful close
        self.device.close()
        mock_device.close.assert_called_once()

    def test_data_processing(self):
        """Test device data processing."""
        # Test valid data
        data = [0, 127, 0, 0]  # Button 0, x=127, y=0, z=0
        self.device.process(data)
        self.assertEqual(self.device.state["x"], 1.0)
        self.assertEqual(self.device.state["y"], 0.0)
        self.assertEqual(self.device.state["z"], 0.0)
        
        # Test invalid data
        self.device.process([])  # Empty data
        self.device.process([0] * 100)  # Data too long
        
        # Test button processing
        data = [1, 0, 0, 0]  # Button 0 pressed
        self.device.process(data)
        self.assertEqual(self.device.state["buttons"][0], 1)

    def test_callback_setting(self):
        """Test callback function setting."""
        def test_callback(state):
            pass
        
        # Test valid callback
        self.device.set_callback(test_callback)
        self.assertEqual(self.device.callback, test_callback)
        
        # Test invalid callback
        with self.assertRaises(ValueError):
            self.device.set_callback(None)
        
        # Test button callback
        self.device.set_button_callback(test_callback)
        self.assertEqual(self.device.button_callback, test_callback)
        
        # Test invalid button callback
        with self.assertRaises(ValueError):
            self.device.set_button_callback(None)

if __name__ == '__main__':
    unittest.main() 