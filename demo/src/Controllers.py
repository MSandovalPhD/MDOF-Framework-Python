from typing import Callable, Optional
from src.LISU.devices import InputDevice
from LISU_getcontrollers import LisuControllers

class Controllers:
    def __init__(self, init_status: Callable[[int], None], ctr_name: str, **callbacks):
        self.ontology = LisuOntology()
        self.devices = [
            InputDevice(vid, pid, name)
            for vid, pid, name in [
                (vid, pid, attr["name"]) for vid, pid in LisuControllers.LisuListDevices()
                for attr in self.ontology.get_device_attributes() if hex(vid) == attr["VID"] and hex(pid) == attr["PID"]
            ] if name in ctr_name
        ]
        if not self.devices:
            self.init_status(-1)
            return
        self.device = self.devices[0]
        self.device.open()
        self.callbacks = callbacks
        self.init_status(0)
        self.state = {"x": 0.0, "y": 0.0, "z": 0.0, "buttons": [0] * len(self.device.specs["buttons"])}

    def controller_status(self) -> bool:
        if not self.device.connected:
            return False

        for axis, spec in self.device.specs["axes"].items():
            if axis in self.callbacks:
                value = self.state.get(axis, 0.0)
                self.callbacks[axis](value, 0)

        for idx, btn in enumerate(self.device.specs["buttons"]):
            if f"btn{idx+1}" in self.callbacks:
                self.callbacks[f"btn{idx+1}"](self.state["buttons"][idx])

        keep_running = True
        if not self._kbhit():
            keep_running = False
        return keep_running

    def _kbhit(self) -> bool:
        try:
            from msvcrt import kbhit
            return kbhit()
        except ImportError:
            return False
