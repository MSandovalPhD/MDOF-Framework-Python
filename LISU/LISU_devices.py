from time import sleep
import pywinusb.hid as hid
from collections import namedtuple
from typing import Dict, List, Tuple, Optional, Callable
from timeit import default_timer as high_acc_clock

from LISU_datasource import OntCtrl  # Adjusted for simplified LISU_datasource.py

__version__ = "0.3.1"

# HID usage constants
GENERIC_PAGE = 0x1
BUTTON_PAGE = 0x9
LED_PAGE = 0x8
HID_AXIS_MAP = {0x30: "x", 0x31: "y", 0x32: "z", 0x33: "roll", 0x34: "pitch", 0x35: "yaw"}

# Named tuples for specs and state
AxisSpec = namedtuple("AxisSpec", ["channel", "byte1", "byte2", "scale"])
ButtonSpec = namedtuple("ButtonSpec", ["channel", "byte", "bit"])
LisuDevice = namedtuple("LisuDevice", ["t", "x", "y", "z", "roll", "pitch", "yaw", "buttons"])

def to_int16(y1: int, y2: int) -> int:
    """Convert two bytes to a signed 16-bit integer."""
    x = (y1) | (y2 << 8)
    return x - 65536 if x >= 32768 else x

class ButtonState(list):
    """List subclass representing button states as an integer."""
    def __int__(self) -> int:
        return sum(b << i for i, b in enumerate(reversed(self)))

class LisuDevControllers:
    """Manages device specifications from ontology data."""
    def __init__(self, vid_id: int, pid_id: int):
        """Initialize with VID/PID and fetch device specs from ontology."""
        self.dict_devices: Dict[str, 'DeviceSpec'] = {}
        ontology = OntCtrl(hex(vid_id), hex(pid_id))
        devices = ontology.get_device_attributes()  # Assumes simplified LISU_datasource.py
        
        for dev in devices:
            mappings = {
                "x": AxisSpec(int(dev["x_channel"]), int(dev["x_byte1"]), int(dev["x_byte2"]), int(dev["x_scale"])),
                "y": AxisSpec(int(dev["y_channel"]), int(dev["y_byte1"]), int(dev["y_byte2"]), int(dev["y_scale"])),
                "z": AxisSpec(int(dev["z_channel"]), int(dev["z_byte1"]), int(dev["z_byte2"]), int(dev["z_scale"])),
                "pitch": AxisSpec(int(dev["pitch_channel"]), int(dev["pitch_byte1"]), int(dev["pitch_byte2"]), int(dev["pitch_scale"])),
                "roll": AxisSpec(int(dev["roll_channel"]), int(dev["roll_byte1"]), int(dev["roll_byte2"]), int(dev["roll_scale"])),
                "yaw": AxisSpec(int(dev["yaw_channel"]), int(dev["yaw_byte1"]), int(dev["yaw_byte2"]), int(dev["yaw_scale"])),
            }
            button_mapping = [
                ButtonSpec(int(dev["btn1_channel"]), int(dev["btn1_byte"]), int(dev["btn1_bit"])),
                ButtonSpec(int(dev["btn2_channel"]), int(dev["btn2_byte"]), int(dev["btn2_bit"]))
            ]
            self.dict_devices[dev["name"]] = DeviceSpec(
                name=dev["name"],
                hid_id=[vid_id, pid_id],
                led_id=[LED_PAGE, 0x4B],
                mappings=mappings,
                button_mapping=button_mapping
            )

class DeviceSpec:
    """Represents a single HID input device with 6DOF state."""
    def __init__(
        self,
        name: str,
        hid_id: List[int],
        led_id: List[int],
        mappings: Dict[str, AxisSpec],
        button_mapping: List[ButtonSpec],
        axis_scale: float = 350.0
    ):
        """Initialize device specification."""
        self.name = name
        self.hid_id = hid_id
        self.led_id = led_id
        self.mappings = mappings
        self.button_mapping = button_mapping
        self.axis_scale = axis_scale
        self.led_usage = hid.get_full_usage_id(led_id[0], led_id[1])

        # Initial state
        self.dict_state = {
            "t": -1.0, "x": 0.0, "y": 0.0, "z": 0.0,
            "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
            "buttons": ButtonState([0] * len(button_mapping))
        }
        self.tuple_state = LisuDevice(**self.dict_state)
        
        # Device connection and callbacks
        self.device: Optional[hid.HidDevice] = None
        self.callback: Optional[Callable[[LisuDevice], None]] = None
        self.button_callback: Optional[Callable[[LisuDevice, ButtonState], None]] = None

    @property
    def connected(self) -> bool:
        """Check if the device is connected."""
        return self.device is not None

    def open(self) -> None:
        """Open a connection to the device."""
        if self.device:
            self.device.open()
            self.product_name = self.device.product_name
            self.vendor_name = self.device.vendor_name
            self.version_number = self.device.version_number
            self.serial_number = "".join(f"{ord(char):02X}" for char in self.device.serial_number or "")

    def close(self) -> None:
        """Close the device connection."""
        if self.connected:
            self.device.close()
            self.device = None

    def set_led(self, state: bool) -> None:
        """Set the LED state."""
        if self.connected:
            for report in self.device.find_output_reports():
                if self.led_usage in report:
                    report[self.led_usage] = state
                    report.send()

    def read(self) -> Optional[LisuDevice]:
        """Return the current state of the device."""
        return self.tuple_state if self.connected else None

    def process(self, data: List[int]) -> None:
        """Update state from raw HID data and trigger callbacks."""
        button_changed = False
        max_len_data = len(data)

        for name, spec in self.mappings.items():
            if data[0] == spec.channel and spec.byte1 < max_len_data and spec.byte2 < max_len_data:
                self.dict_state[name] = to_int16(data[spec.byte1], data[spec.byte2]) / self.axis_scale

        for idx, spec in enumerate(self.button_mapping):
            if data[0] == spec.channel and spec.byte < max_len_data:
                mask = 1 << spec.bit
                button_changed |= (self.dict_state["buttons"][idx] != (1 if data[spec.byte] & mask else 0))
                self.dict_state["buttons"][idx] = 1 if data[spec.byte] & mask else 0

        self.dict_state["t"] = high_acc_clock()
        self.tuple_state = LisuDevice(**self.dict_state)

        if self.callback:
            self.callback(self.tuple_state)
        if self.button_callback and button_changed:
            self.button_callback(self.tuple_state, self.tuple_state.buttons)

    def describe_connection(self) -> str:
        """Return a string describing the device connection status."""
        if not self.connected:
            return f"{self.name} [disconnected]"
        return (f"{self.name} connected to {self.vendor_name} {self.product_name} "
                f"version: {self.version_number} [serial: {self.serial_number}]")

if __name__ == "__main__":
    # Example usage
    dev_mgr = LisuDevControllers(0x054c, 0x09cc)  # PS4 controller VID/PID
    for name, spec in dev_mgr.dict_devices.items():
        print(spec.describe_connection())
