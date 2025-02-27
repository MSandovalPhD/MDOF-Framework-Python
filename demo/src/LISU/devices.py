from typing import Dict, List, Tuple, Optional, Callable
from src.LISU.datasource import LisuOntology
import pywinusb.hid as hid
from timeit import default_timer as high_acc_clock

class InputDevice:
    """Generic representation of any input device, configured via ontology and dynamic config."""
    def __init__(self, vid: int, pid: int, name: str):
        self.vid = vid
        self.pid = pid
        self.name = name
        self.specs = self._load_specs()
        self.state = {
            "t": -1.0, "x": 0.0, "y": 0.0, "z": 0.0, "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
            "buttons": [0] * len(self.specs.get("buttons", []))
        }
        self.device: Optional[hid.HidDevice] = None
        self.callback: Optional[Callable] = None
        self.button_callback: Optional[Callable] = None

    def _load_specs(self) -> Dict:
        """Load device specifications from the ontology, including optional properties."""
        ontology = LisuOntology(vid=hex(self.vid), pid=hex(self.pid))
        device_attrs = ontology.get_device_attributes()
        if not device_attrs:
            raise ValueError(f"No specs found for VID {self.vid}, PID {self.pid}")
        
        spec = device_attrs[0]
        return {
            "axes": {
                axis: {
                    "channel": int(spec.get(f"{axis}_channel", -1)),
                    "byte1": int(spec.get(f"{axis}_byte1", -1)),
                    "byte2": int(spec.get(f"{axis}_byte2", -1)),
                    "scale": int(spec.get(f"{axis}_scale", 350))
                } for axis in ["x", "y", "z", "pitch", "roll", "yaw"] if f"{axis}_channel" in spec
            },
            "buttons": [
                {"channel": int(spec.get("btn1_channel", -1)), "byte": int(spec.get("btn1_byte", -1)), "bit": int(spec.get("btn1_bit", -1))},
                {"channel": int(spec.get("btn2_channel", -1)), "byte": int(spec.get("btn2_byte", -1)), "bit": int(spec.get("btn2_bit", -1))}
            ],
            "type": spec.get("type", "unknown")
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
            if (spec["channel"] != -1 and data[0] == spec["channel"] and 
                spec["byte1"] < max_len and spec["byte2"] < max_len):
                self.state[axis] = to_int16(data[spec["byte1"]], data[spec["byte2"]]) / spec["scale"]

        for idx, btn in enumerate(self.specs["buttons"]):
            if (btn["channel"] != -1 and data[0] == btn["channel"] and btn["byte"] < max_len):
                mask = 1 << btn["bit"]
                self.state["buttons"][idx] = 1 if data[btn["byte"]] & mask else 0

        self.state["t"] = high_acc_clock()
        if self.callback:
            self.callback(self.state)
        if self.button_callback and any(self.state["buttons"] != [0] * len(self.specs["buttons"])):
            self.button_callback(self.state, self.state["buttons"])

def to_int16(y1: int, y2: int) -> int:
    """Convert two bytes to a signed 16-bit integer."""
    x = (y1) | (y2 << 8)
    return x - 65536 if x >= 32768 else x

class LisuDevControllers:
    """Manages generic input devices via ontology."""
    def __init__(self, vid_id: int, pid_id: int):
        self.devices = {
            device["name"]: InputDevice(vid_id, pid_id, device["name"])
            for device in LisuOntology(vid=hex(vid_id), pid=hex(pid_id)).get_device_attributes()
        }
