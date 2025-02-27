from typing import Dict, List, Tuple, Optional, Callable
import pywinusb.hid as hid
from timeit import default_timer as high_acc_clock
from pathlib import Path

class InputDevice:
    """Generic representation of any input device, configured via provided config."""
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

    def _load_specs(self) -> Dict:
        """Load device specifications from provided config, with minimal defaults."""
        axes = self.dev_config.get("axes", ["x"])
        buttons = self.dev_config.get("buttons", [])
        dev_type = self.dev_config.get("type", "unknown")

        # Default specs if not fully specified
        return {
            "axes": {
                axis: {
                    "channel": -1,  # Assume raw data parsing if not specified
                    "byte1": -1,
                    "byte2": -1,
                    "scale": 350  # Default scale, adjustable via config later
                } for axis in axes
            },
            "buttons": [
                {"channel": -1, "byte": idx, "bit": 0} for idx in range(len(buttons))
            ],
            "type": dev_type
        }

    def open(self) -> None:
        """Open connection to the device, setting raw data handler."""
        if not self.device:
            self.device = hid.HidDeviceFilter(vendor_id=self.vid, product_id=self.pid).get_devices()[0]
            self.device.open()
            self.device.set_raw_data_handler(self.process)

    def close(self) -> None:
        """Close the device connection."""
        if self.device:
            self.device.close()
            self.device = None

    def process(self, data: List[int]) -> None:
        """Process raw HID data to update device state and trigger callbacks."""
        max_len = len(data)
        for axis, spec in self.specs["axes"].items():
            # Simplified: Assume axes are in first few bytes if not specified
            if spec["byte1"] == -1 and max_len > 1:
                self.state[axis] = to_int16(data[1], data[2] if max_len > 2 else 0) / spec["scale"]

        for idx, btn in enumerate(self.specs["buttons"]):
            if btn["byte"] < max_len:
                self.state["buttons"][idx] = 1 if data[btn["byte"]] & 0x01 else 0

        self.state["t"] = high_acc_clock()
        if self.callback:
            self.callback(self.state)
        if self.button_callback and any(self.state["buttons"]):
            self.button_callback(self.state, self.state["buttons"])

def to_int16(y1: int, y2: int) -> int:
    """Convert two bytes to a signed 16-bit integer."""
    x = (y1) | (y2 << 8)
    return x - 65536 if x >= 32768 else x
