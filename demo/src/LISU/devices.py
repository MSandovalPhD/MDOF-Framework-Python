from typing import Dict, List, Tuple, Optional, Callable
import pywinusb.hid as hid
from timeit import default_timer as high_acc_clock
from LISU.logging import LisuLogger
import numpy as np

# Initialize logger
logger = LisuLogger()

class InputDevice:
    # Constants for validation
    AXIS_DEADZONE = 0.01  # Minimum change to trigger axis update
    BUTTON_DEBOUNCE_TIME = 0.05  # Seconds between button state changes
    MAX_AXIS_VALUE = 1.0
    MIN_AXIS_VALUE = -1.0
    MAX_BUTTON_COUNT = 8
    MAX_DATA_LENGTH = 64

    def __init__(self, vid: int, pid: int, name: str, dev_config: Optional[Dict] = None):
        self.vid = vid
        self.pid = pid
        self.name = name
        self.dev_config = dev_config or {}
        self.specs = self._load_specs()
        self.state = {
            "t": -1.0, "x": 0.0, "y": 0.0, "z": 0.0, "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
            "buttons": [0] * len(self.specs.get("buttons", []))
        }
        self.device: Optional[hid.HidDevice] = None
        self.callback: Optional[Callable] = None
        self.button_callback: Optional[Callable] = None
        self.last_button_update = 0.0
        self.last_axis_values = {axis: 0.0 for axis in ["x", "y", "z"]}
        
        # Validate and log initialization
        self._validate_and_log_init()

    def _validate_and_log_init(self):
        """Validate initialization parameters and log the event."""
        if not isinstance(self.vid, int) or not isinstance(self.pid, int):
            raise ValueError("VID and PID must be integers")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Device name must be a non-empty string")
        
        # Filter sensitive information from config
        safe_config = self._filter_sensitive_data(self.dev_config)
        
        logger.log_event("device_initialized", {
            "name": self.name,
            "vid": f"{self.vid:04x}",
            "pid": f"{self.pid:04x}",
            "config": safe_config,
            "specs": self._filter_sensitive_data(self.specs)
        })

    def _filter_sensitive_data(self, data: Dict) -> Dict:
        """Remove sensitive information from data before logging."""
        if not isinstance(data, dict):
            return data
        
        filtered = data.copy()
        sensitive_keys = {"password", "key", "secret", "token"}
        
        for key in filtered:
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                filtered[key] = "[REDACTED]"
            elif isinstance(filtered[key], dict):
                filtered[key] = self._filter_sensitive_data(filtered[key])
        
        return filtered

    def _validate_axis_value(self, value: float, axis: str) -> float:
        """Validate and normalize axis value."""
        if not isinstance(value, (int, float)):
            raise ValueError(f"Invalid {axis} value type: {type(value)}")
        
        # Normalize and clamp
        normalized = min(max(value / 127.0, self.MIN_AXIS_VALUE), self.MAX_AXIS_VALUE)
        
        # Check if change exceeds deadzone
        if abs(normalized - self.last_axis_values[axis]) < self.AXIS_DEADZONE:
            return self.last_axis_values[axis]
        
        self.last_axis_values[axis] = normalized
        return normalized

    def _validate_button_states(self, states: List[bool]) -> List[bool]:
        """Validate and process button states."""
        if not isinstance(states, list):
            raise ValueError("Button states must be a list")
        
        # Ensure correct number of buttons
        if len(states) > self.MAX_BUTTON_COUNT:
            states = states[:self.MAX_BUTTON_COUNT]
        elif len(states) < len(self.state["buttons"]):
            states.extend([False] * (len(self.state["buttons"]) - len(states)))
        
        # Check for changes
        if states == self.state["buttons"]:
            return self.state["buttons"]
        
        # Apply debounce
        current_time = high_acc_clock()
        if current_time - self.last_button_update < self.BUTTON_DEBOUNCE_TIME:
            return self.state["buttons"]
        
        self.last_button_update = current_time
        return states

    def _load_specs(self) -> Dict:
        """Load device specifications with proper mouse data format."""
        axes = self.dev_config.get("axes", ["x", "y"])
        buttons = self.dev_config.get("buttons", ["left_click", "right_click"])
        dev_type = self.dev_config.get("type", "unknown")
        
        # Mouse-specific specs
        specs = {
            "axes": {
                "x": {"channel": 0, "byte1": 1, "byte2": -1, "scale": 127},
                "y": {"channel": 1, "byte1": 2, "byte2": -1, "scale": 127}
            },
            "buttons": [
                {"channel": 0, "byte": 0, "bit": 0},  # Left click
                {"channel": 1, "byte": 0, "bit": 1}   # Right click
            ],
            "type": dev_type
        }
        
        logger.log_event("device_specs_loaded", {
            "name": self.name,
            "specs": specs
        })
        return specs

    def open(self) -> None:
        if not self.device:
            try:
                self.device = hid.HidDeviceFilter(vendor_id=self.vid, product_id=self.pid).get_devices()[0]
                self.device.open()
                self.device.set_raw_data_handler(self.process)
                logger.log_event("device_opened", {
                    "name": self.name,
                    "vid": f"{self.vid:04x}",
                    "pid": f"{self.pid:04x}",
                    "status": "success"
                })
            except Exception as e:
                logger.log_event("device_open_failed", {
                    "name": self.name,
                    "vid": f"{self.vid:04x}",
                    "pid": f"{self.pid:04x}",
                    "error": str(e),
                    "status": "error"
                })
                raise

    def close(self) -> None:
        if self.device:
            try:
                self.device.close()
                self.device = None
                logger.log_event("device_closed", {
                    "name": self.name,
                    "status": "success"
                })
            except Exception as e:
                logger.log_event("device_close_failed", {
                    "name": self.name,
                    "error": str(e),
                    "status": "error"
                })
                raise

    def process(self, data: List[int]) -> None:
        """Process incoming device data with validation."""
        # Debug logging for raw data
        print(f"Raw data received: {data}")
        
        # Validate data length
        if not isinstance(data, list) or not data:
            print("Invalid or empty data received")
            return
        
        if len(data) > self.MAX_DATA_LENGTH:
            data = data[:self.MAX_DATA_LENGTH]
            print(f"Data truncated to {self.MAX_DATA_LENGTH} bytes")

        # Process mouse data
        try:
            # HID Mouse data format:
            # [report_id, buttons, x, y, wheel, ...]
            if len(data) >= 4:
                # Skip report ID (first byte)
                report_id = data[0]
                
                # Process buttons (second byte)
                button_states = [
                    bool(data[1] & 0x01),  # Left click
                    bool(data[1] & 0x02)   # Right click
                ]
                validated_states = self._validate_button_states(button_states)
                
                if validated_states != self.state["buttons"]:
                    changed_buttons = [i for i, (old, new) in enumerate(zip(self.state["buttons"], validated_states)) if old != new]
                    print(f"Button states changed: {changed_buttons}")
                    self.state["buttons"] = validated_states
                    if self.button_callback:
                        self.button_callback(self.state["buttons"])

                # Process X axis (third byte)
                x_raw = data[2] if data[2] <= 127 else data[2] - 256
                self.state["x"] = self._validate_axis_value(x_raw, "x")
                if abs(self.state["x"]) >= self.AXIS_DEADZONE:
                    print(f"X axis value: {self.state['x']:.3f}")

                # Process Y axis (fourth byte)
                y_raw = data[3] if data[3] <= 127 else data[3] - 256
                self.state["y"] = self._validate_axis_value(y_raw, "y")
                if abs(self.state["y"]) >= self.AXIS_DEADZONE:
                    print(f"Y axis value: {self.state['y']:.3f}")

                # Update timestamp
                self.state["t"] = high_acc_clock()

                # Call the callback if set
                if self.callback:
                    self.callback(self.state)

        except Exception as e:
            print(f"Error processing mouse data: {e}")
            logger.log_error(e, {
                "device": self.name,
                "raw_data": data,
                "state": self.state
            })

    def set_callback(self, callback: Callable) -> None:
        """Set the callback function for state updates with validation."""
        if not callable(callback):
            raise ValueError("Callback must be callable")
        
        self.callback = callback
        logger.log_event("device_callback_set", {
            "name": self.name,
            "callback_type": callback.__name__ if hasattr(callback, '__name__') else "unknown"
        })

    def set_button_callback(self, callback: Callable) -> None:
        """Set the callback function for button updates with validation."""
        if not callable(callback):
            raise ValueError("Button callback must be callable")
        
        self.button_callback = callback
        logger.log_event("device_button_callback_set", {
            "name": self.name,
            "callback_type": callback.__name__ if hasattr(callback, '__name__') else "unknown"
        })

    def start_monitoring(self) -> None:
        """
        Start monitoring the device for input events.
        This method opens the device and sets up the data handler.
        """
        try:
            self.open()
            logger.log_event("device_monitoring_started", {
                "name": self.name,
                "status": "success"
            })
        except Exception as e:
            logger.log_event("device_monitoring_failed", {
                "name": self.name,
                "error": str(e),
                "status": "error"
            })
            raise

    def stop_monitoring(self) -> None:
        """
        Stop monitoring the device for input events.
        This method closes the device and cleans up resources.
        """
        try:
            if self.device:
                # Remove the data handler before closing
                self.device.set_raw_data_handler(None)
                self.close()
                logger.log_event("device_monitoring_stopped", {
                    "name": self.name,
                    "status": "success"
                })
        except Exception as e:
            logger.log_event("device_monitoring_stop_failed", {
                "name": self.name,
                "error": str(e),
                "status": "error"
            })
            raise

def to_int16(y1: int, y2: int) -> int:
    x = (y1) | (y2 << 8)
    return x - 65536 if x >= 32768 else x
