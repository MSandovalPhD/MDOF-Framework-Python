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
        axes = self.dev_config.get("axes", ["x"])
        buttons = self.dev_config.get("buttons", [])
        dev_type = self.dev_config.get("type", "unknown")
        specs = {
            "axes": {axis: {"channel": -1, "byte1": -1, "byte2": -1, "scale": 127} for axis in axes},
            "buttons": [{"channel": -1, "byte": idx, "bit": 0} for idx in range(len(buttons))],
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
        # Validate data length
        if not isinstance(data, list) or not data:
            logger.log_event("device_invalid_data", {
                "name": self.name,
                "error": "Invalid or empty data received"
            })
            return
        
        if len(data) > self.MAX_DATA_LENGTH:
            data = data[:self.MAX_DATA_LENGTH]
            logger.log_event("device_data_truncated", {
                "name": self.name,
                "original_length": len(data),
                "truncated_length": self.MAX_DATA_LENGTH
            })

        # Log raw data with validation
        logger.log_event("device_raw_data", {
            "name": self.name,
            "data_length": len(data),
            "timestamp": self.state["t"]
        })

        max_len = len(data)
        if max_len > 1:
            try:
                # Process x-axis
                x_raw = data[1] if data[1] <= 127 else data[1] - 256
                self.state["x"] = self._validate_axis_value(x_raw, "x")
                if abs(self.state["x"]) >= self.AXIS_DEADZONE:
                    logger.log_event("device_axis_update", {
                        "name": self.name,
                        "axis": "x",
                        "raw_value": x_raw,
                        "normalized_value": self.state["x"]
                    })

                # Process y-axis
                if max_len > 2:
                    y_raw = data[2] if data[2] <= 127 else data[2] - 256
                    self.state["y"] = self._validate_axis_value(y_raw, "y")
                    if abs(self.state["y"]) >= self.AXIS_DEADZONE:
                        logger.log_event("device_axis_update", {
                            "name": self.name,
                            "axis": "y",
                            "raw_value": y_raw,
                            "normalized_value": self.state["y"]
                        })

                # Process z-axis
                if max_len > 3:
                    z_raw = data[3] if data[3] <= 127 else data[3] - 256
                    self.state["z"] = self._validate_axis_value(z_raw, "z")
                    if abs(self.state["z"]) >= self.AXIS_DEADZONE:
                        logger.log_event("device_axis_update", {
                            "name": self.name,
                            "axis": "z",
                            "raw_value": z_raw,
                            "normalized_value": self.state["z"]
                        })

                # Process buttons
                if max_len > 0:
                    try:
                        button_states = [(data[0] & (1 << i)) != 0 for i in range(8)]
                        validated_states = self._validate_button_states(button_states)
                        
                        if validated_states != self.state["buttons"]:
                            changed_buttons = [i for i, (old, new) in enumerate(zip(self.state["buttons"], validated_states)) if old != new]
                            logger.log_event("device_button_update", {
                                "name": self.name,
                                "old_states": self.state["buttons"],
                                "new_states": validated_states,
                                "changed_buttons": changed_buttons
                            })
                            self.state["buttons"] = validated_states
                            if self.button_callback:
                                self.button_callback(self.state["buttons"])
                    except Exception as e:
                        logger.log_event("device_button_error", {
                            "name": self.name,
                            "error": str(e)
                        })

            except Exception as e:
                logger.log_event("device_processing_error", {
                    "name": self.name,
                    "error": str(e),
                    "data": data
                })
                return

        self.state["t"] = high_acc_clock()
        logger.log_event("device_state_updated", {
            "name": self.name,
            "state": self._filter_sensitive_data(self.state),
            "timestamp": self.state["t"]
        })
        if self.callback:
            self.callback(self.state)

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

def to_int16(y1: int, y2: int) -> int:
    x = (y1) | (y2 << 8)
    return x - 65536 if x >= 32768 else x
