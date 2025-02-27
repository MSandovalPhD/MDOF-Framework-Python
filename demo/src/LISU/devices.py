from typing import Dict, List, Tuple, Optional, Callable
import pywinusb.hid as hid
from timeit import default_timer as high_acc_clock
from LISU.datalogging import recordLog

class InputDevice:
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
        axes = self.dev_config.get("axes", ["x"])
        buttons = self.dev_config.get("buttons", [])
        dev_type = self.dev_config.get("type", "unknown")
        return {
            "axes": {axis: {"channel": -1, "byte1": -1, "byte2": -1, "scale": 127} for axis in axes},  # Max mouse delta
            "buttons": [{"channel": -1, "byte": idx, "bit": 0} for idx in range(len(buttons))],
            "type": dev_type
        }

    def open(self) -> None:
        if not self.device:
            self.device = hid.HidDeviceFilter(vendor_id=self.vid, product_id=self.pid).get_devices()[0]
            self.device.open()
            self.device.set_raw_data_handler(self.process)
            recordLog(f"Opened device {self.name} (VID: {self.vid:04x}, PID: {self.pid:04x})")

    def close(self) -> None:
        if self.device:
            self.device.close()
            self.device = None
            recordLog(f"Closed device {self.name}")

    def process(self, data: List[int]) -> None:
        recordLog(f"Raw HID data for {self.name}: {data}")
        max_len = len(data)
        if max_len > 1:
            # Mouse x-axis delta (byte 1), normalize to -1 to 1
            x_raw = data[1] if data[1] <= 127 else data[1] - 256  # Convert to signed -128 to 127
            self.state["x"] = x_raw / 127.0  # Scale to -1 to 1
        for idx, btn in enumerate(self.specs["buttons"]):
            if btn["byte"] < max_len:
                self.state["buttons"][idx] = 1 if data[btn["byte"]] & 0x01 else 0

        self.state["t"] = high_acc_clock()
        recordLog(f"Updated state for {self.name}: {self.state}")
        if self.callback:
            self.callback(self.state)
        if self.button_callback and any(self.state["buttons"]):
            self.button_callback(self.state, self.state["buttons"])

def to_int16(y1: int, y2: int) -> int:
    x = (y1) | (y2 << 8)
    return x - 65536 if x >= 32768 else x
