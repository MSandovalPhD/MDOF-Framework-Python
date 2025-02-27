import hid
from multiprocessing import Process, Queue
from time import sleep
from typing import List, Tuple, Optional

from src.LISU.devices import InputDevice
from src.controllers import Controllers
from src.actuation import Actuation, xAxisChangeHandler, yAxisChangeHandler, zAxisChangeHandler, changeActuationHandler, subAngleHandler, circleBtnHandler, addAngleHandler, LisuProcesses
import pygame
from src.LISU.datasource import LisuOntology

class LisuManager:
    def __init__(self):
        self.device_specs = {}
        self.active_device = None
        self.dev_name = ""
        self.fun_array = self._load_actuation_commands()
        self.count_state = 0
        self.idx2 = 0
        self.idx3 = 1
        self.actuation = Actuation()

    def _load_actuation_commands(self) -> List[str]:
        ontology = LisuOntology()
        commands = ontology.get_actuation_commands()
        return commands if commands else ["addrotation %.3f %.3f %.3f %s", "addrotationclip %.3f %.3f %.3f %s"]

    def list_devices(self) -> List[str]:
        devices = []
        all_hids = hid.find_all_hid_devices()
        for device in all_hids:
            for name, spec in self.device_specs.items():
                if device.vendor_id == spec.vid and device.product_id == spec.pid:
                    devices.append(name)
        return devices

    def start_device(self, vendor_id: int, product_id: int, device_type: str = "gamepad") -> Optional[InputDevice]:
        try:
            dev_filter = hid.HidDeviceFilter(vendor_id=vendor_id, product_id=product_id)
            all_hids = dev_filter.get_devices()
            if not all_hids:
                raise ValueError("No HID devices detected")

            dev = all_hids[0]
            lisudevname = " ".join(dev.product_name.split()).replace("ACRUX", "")
            if lisudevname == "Wireless Controller":
                lisudevname = "PS4 Controller"
            self.dev_name = lisudevname

            device = InputDevice(vendor_id, product_id, lisudevname)
            device.open()
            device.callback = self._process_state
            device.button_callback = self._toggle_buttons

            print(f"LISU has found {lisudevname}")
            print(f"You can start using {lisudevname}")

            while not self._kbhit() and device.device.is_plugged():
                sleep(0.5)
            device.close()
            return device
        except Exception as e:
            print(f"Failed to start device: {e}")
            return None

    def _process_state(self, state: dict) -> None:
        vec_input = [
            -state.get("x", 0.0) if abs(state.get("x", 0.0)) > 0.3 else 0.0,
            -state.get("y", 0.0) if abs(state.get("y", 0.0)) > 0.2 else 0.0,
            state.get("z", 0.0) if abs(state.get("z", 0.0)) > 0.2 else 0.0
        ]
        self.actuation.process_input(vec_input, self.dev_name)

    def _toggle_buttons(self, state: dict, buttons: List[int]) -> None:
        if buttons[0] == 1:
            self.actuation.change_actuation(1)
        if buttons[1] == 1 and len(buttons) > 1:
            self.actuation.adjust_sensitivity(1)

    def activate_devices(self, device_list: List[Tuple[int, int]]) -> None:
        processes = []
        queue = Queue()
        for vid, pid in device_list:
            p = Process(target=self._run_device, args=(vid, pid, queue))
            p.start()
            processes.append(p)
        for p in processes:
            p.join()
        while not queue.empty():
            print(queue.get())

    def _run_device(self, vendor_id: int, product_id: int, queue: Queue) -> None:
        try:
            device = self.start_device(vendor_id, product_id, "generic")
            queue.put(f"Started {self.dev_name}")
        except Exception as e:
            queue.put(f"Error with {vendor_id}/{product_id}: {e}")

    def _kbhit(self) -> bool:
        try:
            from msvcrt import kbhit
            return kbhit()
        except ImportError:
            return False

if __name__ == "__main__":
    lisu = LisuManager()
    devices = [(0x054c, 0x09cc)]  # Example: PS4 controller VID/PID
    lisu.activate_devices(devices)
