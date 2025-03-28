from typing import Dict, List, Any, Optional, Callable
import pywinusb.hid as hid
import pygame
import time
from LISU.logging import LisuLogger
import numpy as np
import threading

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

    def __init__(self, name: str, vid: int, pid: int, device_type: str,
                 library: str = "pywinusb", axes: List[str] = None,
                 buttons: List[str] = None, command: str = "unknown",
                 logger: Optional[LisuLogger] = None, device_index: int = 0):
        """
        Initialise an input device.
        
        Args:
            name: Name of the device
            vid: Vendor ID
            pid: Product ID
            device_type: Type of device (e.g., "mouse", "keyboard", "gamepad")
            library: Library to use (pywinusb or pygame)
            axes: List of available axes
            buttons: List of available buttons
            command: Default command type
            logger: Optional logger instance
            device_index: Index of the device (for pygame devices)
        """
        self.name = name
        self.vid = vid
        self.pid = pid
        self.device_type = device_type
        self.library = library
        self.axes = axes or []
        self.buttons = buttons or []
        self.command = command
        self.logger = logger or LisuLogger()
        self.device = None
        self.running = threading.Event()  # Initialize as threading.Event
        self.running.set()  # Set the event to True initially
        self.callback = None
        self.button_callback = None
        self.device_index = device_index
        self.state = {
            "axes": {axis: 0.0 for axis in self.axes},
            "buttons": {button: False for button in self.buttons}
        }
        self._last_state = {}  # Initialize _last_state for state comparison
        
        # Initialize libraries if needed
        if self.library == "pygame":
            pygame.init()
            pygame.joystick.init()
    
    def start_monitoring(self):
        """Start monitoring the device."""
        try:
            if self.library == "pywinusb":
                self._start_pywinusb_monitoring()
            elif self.library == "pygame":
                self._start_pygame_monitoring()
            else:
                raise ValueError(f"Unsupported library: {self.library}")
        except Exception as e:
            self.logger.log_error(e, {"context": "Starting device monitoring"})
            raise
    
    def _start_pywinusb_monitoring(self):
        """Start monitoring using pywinusb."""
        try:
            # Create a filter for the device
            device_filter = hid.HidDeviceFilter(vendor_id=self.vid, product_id=self.pid)
            devices = device_filter.get_devices()
            
            if not devices:
                raise ValueError(f"No HID device found with VID: {self.vid:04x}, PID: {self.pid:04x}")
            
            # Get the first matching device
            self.device = devices[0]
            
            # Open the device
            self.device.open()
            
            # Set up data handler
            def data_handler(data):
                if self.callback:
                    self.callback(self._process_data(data))
            
            # Set the raw data handler
            self.device.set_raw_data_handler(data_handler)
            self.running = True
            
            self.logger.log_event("device_started", {
                "device": self.name,
                "type": self.device_type,
                "library": self.library,
                "vid": f"{self.vid:04x}",
                "pid": f"{self.pid:04x}"
            })
            
        except Exception as e:
            self.logger.log_error(e, {"context": "Starting pywinusb monitoring"})
            if self.device:
                try:
                    self.device.close()
                except:
                    pass
            raise
    
    def _start_pygame_monitoring(self):
        """Start monitoring pygame joystick events."""
        try:
            if not pygame.get_init():
                pygame.init()
            if not pygame.joystick.get_init():
                pygame.joystick.init()
            
            # Initialize the joystick
            if self.device_index is not None:
                joystick = pygame.joystick.Joystick(self.device_index)
                joystick.init()
                print(f"Initialized pygame joystick: {joystick.get_name()}")
                
                while self.running.is_set():
                    pygame.event.pump()
                    
                    # Get current state
                    state = {}
                    
                    # Get axis values
                    for i in range(joystick.get_numaxes()):
                        state[f'axis_{i}'] = joystick.get_axis(i)
                    
                    # Get button states
                    for i in range(joystick.get_numbuttons()):
                        state[f'button_{i}'] = joystick.get_button(i)
                    
                    # Send state to callback if it has changed
                    if state != self._last_state:
                        self._last_state = state.copy()
                        if self.callback:
                            self.callback(state)
                        if self.button_callback:
                            self.button_callback(state, self.buttons)
                    
                    time.sleep(0.01)  # Small delay to prevent CPU overuse
                    
        except Exception as e:
            print(f"Error in pygame monitoring: {e}")
            self.logger.log_error(e, {"device": self.name})
        finally:
            if pygame.get_init():
                pygame.quit()
    
    def stop_monitoring(self):
        """Stop monitoring the device."""
        try:
            self.running.clear()  # Clear the event to stop monitoring
            if self.device:
                if self.library == "pywinusb":
                    try:
                        self.device.close()
                    except:
                        pass
                elif self.library == "pygame":
                    try:
                        self.device.quit()
                    except:
                        pass
            
            self.logger.log_event("device_stopped", {
                "device": self.name,
                "type": self.device_type
            })
        except Exception as e:
            self.logger.log_error(e, {"context": "Stopping device monitoring"})
            raise
    
    def _process_data(self, data: List[int]) -> Dict[str, Any]:
        """Process raw HID data into a standardized format."""
        try:
            # Basic data validation
            if not data or len(data) < 4:
                return self.state
            
            # Process mouse data (assuming standard HID mouse format)
            if self.device_type == "mouse":
                # data[0] is report ID, data[1] is button state, data[2] is X, data[3] is Y
                self.state["buttons"]["left_click"] = bool(data[1] & 0x01)
                self.state["buttons"]["right_click"] = bool(data[1] & 0x02)
                self.state["axes"]["x"] = data[2]
                self.state["axes"]["y"] = data[3]
            
            return self.state
            
        except Exception as e:
            self.logger.log_error(e, {"context": "Processing device data"})
            return self.state

    def _validate_and_log_init(self):
        """Validate initialization parameters and log the event."""
        if not isinstance(self.vid, int) or not isinstance(self.pid, int):
            raise ValueError("VID and PID must be integers")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Device name must be a non-empty string")
        
        # Filter sensitive information from config
        safe_config = self._filter_sensitive_data(self.state)
        
        self.logger.log_event("device_initialized", {
            "name": self.name,
            "vid": f"{self.vid:04x}",
            "pid": f"{self.pid:04x}",
            "config": safe_config,
            "specs": self._filter_sensitive_data(self.state)
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
        if abs(normalized - self.state["axes"][axis]) < self.AXIS_DEADZONE:
            return self.state["axes"][axis]
        
        self.state["axes"][axis] = normalized
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
        current_time = time.time()
        if current_time - self.last_button_update < self.BUTTON_DEBOUNCE_TIME:
            return self.state["buttons"]
        
        self.last_button_update = current_time
        return states

    def _load_specs(self) -> Dict:
        """Load device specifications with proper mouse data format."""
        dev_type = self.command
        
        # Mouse-specific specs
        specs = {
            "axes": {axis: {"channel": i, "byte1": i+1, "byte2": -1, "scale": 127} for i, axis in enumerate(self.axes)},
            "buttons": {button: {"channel": i, "byte": 0, "bit": i} for i, button in enumerate(self.buttons)},
            "type": dev_type
        }
        
        self.logger.log_event("device_specs_loaded", {
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
                self.logger.log_event("device_opened", {
                    "name": self.name,
                    "vid": f"{self.vid:04x}",
                    "pid": f"{self.pid:04x}",
                    "status": "success"
                })
            except Exception as e:
                self.logger.log_event("device_open_failed", {
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
                self.logger.log_event("device_closed", {
                    "name": self.name,
                    "status": "success"
                })
            except Exception as e:
                self.logger.log_event("device_close_failed", {
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
                self.state["axes"]["x"] = self._validate_axis_value(x_raw, "x")
                if abs(self.state["axes"]["x"]) >= self.AXIS_DEADZONE:
                    print(f"X axis value: {self.state['axes']['x']:.3f}")

                # Process Y axis (fourth byte)
                y_raw = data[3] if data[3] <= 127 else data[3] - 256
                self.state["axes"]["y"] = self._validate_axis_value(y_raw, "y")
                if abs(self.state["axes"]["y"]) >= self.AXIS_DEADZONE:
                    print(f"Y axis value: {self.state['axes']['y']:.3f}")

                # Update timestamp
                self.state["t"] = time.time()

                # Call the callback if set
                if self.callback:
                    self.callback(self.state)

        except Exception as e:
            print(f"Error processing mouse data: {e}")
            self.logger.log_error(e, {
                "device": self.name,
                "raw_data": data,
                "state": self.state
            })

    def set_callback(self, callback: Callable) -> None:
        """Set the callback function for state updates with validation."""
        if not callable(callback):
            raise ValueError("Callback must be callable")
        
        self.callback = callback
        self.logger.log_event("device_callback_set", {
            "name": self.name,
            "callback_type": callback.__name__ if hasattr(callback, '__name__') else "unknown"
        })

    def set_button_callback(self, callback: Callable) -> None:
        """Set the callback function for button updates with validation."""
        if not callable(callback):
            raise ValueError("Button callback must be callable")
        
        self.button_callback = callback
        self.logger.log_event("device_button_callback_set", {
            "name": self.name,
            "callback_type": callback.__name__ if hasattr(callback, '__name__') else "unknown"
        })

def to_int16(y1: int, y2: int) -> int:
    x = (y1) | (y2 << 8)
    return x - 65536 if x >= 32768 else x
