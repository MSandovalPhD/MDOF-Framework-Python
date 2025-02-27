from typing import Dict, List, Tuple, Optional, Callable
from src.LISU.datasource import LisuOntology
import pywinusb.hid as hid
from timeit import default_timer as high_acc_clock

class InputDevice:
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
        ontology = LisuOntology(vid=hex(self.vid), pid=hex(self.pid))
        device_attrs = ontology.get_device_attributes()
        if not device_attrs:
            raise ValueError(f"No specs found for VID {self.vid}, PID {self.pid}")
        
        spec = device_attrs[0]
        return {
            "axes": {
                axis: {
                    "channel": int(spec[f"{axis}_channel"]),
                    "byte1": int(spec[f"{axis}_byte1"]),
                    "byte2": int(spec[f"{axis}_byte2"]),
                    "scale": int(spec[f"{axis}_scale"])
                } for axis in ["x", "y", "z", "pitch", "roll", "yaw"] if f"{axis}_channel" in spec
            },
            "buttons": [
                {"channel": int(spec["btn1_channel"]), "byte": int(spec["btn1_byte"]), "bit": int(spec["btn1_bit"])},
                {"channel": int(spec["btn2_channel"]), "byte": int(spec["btn2_byte"]), "bit": int(spec["btn2_bit"])}
            ]
        }

    def open(self) -> None:
        if not self.device:
            self.device = hid.HidDeviceFilter(vendor_id=self.vid, product_id=self.pid).get_devices()[0]
            self.device.open()

    def close(self) -> None:
        if self.device:
            self.device.close()
            self.device = None

    def process(self, data: List[int]) -> None:
        max_len = len(data)
        for axis, spec in self.specs["axes"].items():
            if data[0] == spec["channel"] and spec["byte1"] < max_len and spec["byte2"] < max_len:
                self.state[axis] = to_int16(data[spec["byte1"]], data[spec["byte2"]]) / spec["scale"]

        for idx, btn in enumerate(self.specs["buttons"]):
            if data[0] == btn["channel"] and btn["byte"] < max_len:
                mask = 1 << btn["bit"]
                self.state["buttons"][idx] = 1 if data[btn["byte"]] & mask else 0

        self.state["t"] = high_acc_clock()
        if self.callback:
            self.callback(self.state)
        if self.button_callback and any(self.state["buttons"] != [0] * len(self.specs["buttons"])):
            self.button_callback(self.state, self.state["buttons"])

def to_int16(y1: int, y2: int) -> int:
    x = (y1) | (y2 << 8)
    return x - 65536 if x >= 32768 else x

class LisuDevControllers:
    def __init__(self, vid_id: int, pid_id: int):
        self.devices = {
            device["name"]: InputDevice(vid_id, pid_id, device["name"])
            for device in LisuOntology(vid=hex(vid_id), pid=hex(pid_id)).get_device_attributes()
        }
