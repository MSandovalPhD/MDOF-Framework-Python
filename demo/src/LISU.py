import hid
from multiprocessing import Process, Queue
from time import sleep
from typing import List, Tuple, Optional

from src.LISU.devices import LisuDevControllers
from src.controllers import Controllers
from src.actuation import Actuation, xAxisChangeHandler, yAxisChangeHandler, zAxisChangeHandler, changeActuationHandler, subAngleHandler, circleBtnHandler, addAngleHandler, LisuProcesses
import pygame

from src.LISU.datasource import LisuOntology  # Add this import

class LisuManager:
    """Manages LISU input devices and actuation for MDOF systems."""
    def __init__(self):
        self.device_specs = {}
        self.active_device = None
        self.dev_name = ""
        self.fun_array = self._load_actuation_commands()  # Load dynamic commands
        self.count_state = 0
        self.idx2 = 0
        self.idx3 = 1
        self.actuation = Actuation()  # Pass fun_array if needed

    def _load_actuation_commands(self) -> List[str]:
        """Load actuation commands dynamically from the ontology."""
        ontology = LisuOntology()
        commands = ontology.get_actuation_commands()
        return commands if commands else ["addrotation %.3f %.3f %.3f %s", "addrotationclip %.3f %.3f %.3f %s"]

    def list_devices(self) -> List[str]:
        """List all connected devices matching supported specs."""
        devices = []
        all_hids = hid.find_all_hid_devices()
        for device in all_hids:
            for name, spec in self.device_specs.items():
                if device.vendor_id == spec.hid_id[0] and device.product_id == spec.hid_id[1]:
                    devices.append(name)
        return devices

    def start_gamepad(self, vendor_id: int, product_id: int) -> Optional[Controllers]:
        """Initialize and run a gamepad controller."""
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

            # Pass fun_array to Actuation if needed
            actuation = Actuation()  # Current implementation already loads dynamically
            joystick = Controllers(
                initStatus, lisudevname,
                xAxisChanged=lambda lr, ud: xAxisChangeHandler(lr, ud, actuation),
                yAxisChanged=lambda lr, ud: yAxisChangeHandler(lr, ud, actuation),
                zAxisChanged=lambda val: zAxisChangeHandler(val, actuation),
                triangleBtnChanged=lambda val: changeActuationHandler(val, actuation),
                squareBtnChanged=lambda val: subAngleHandler(val, actuation),
                circleBtnChanged=circleBtnHandler,
                crossXBtnChanged=addAngleHandler,
                FPS=20
            )

            if not hasattr(joystick, 'DOF'):
                raise ValueError(f"Failed to initialize {lisudevname}")

            print(f"LISU has found {lisudevname}")
            vec_input = [0] * joystick.DOF
            if joystick.initialised:
                print(f"You can start using {lisudevname}")
                while joystick.controllerStatus():
                    LisuProcesses(vec_input, lisudevname)
                pygame.quit()
            return joystick
        except Exception as e:
            print(f"Failed to start gamepad: {e}")
            return None

    def start_3d_input(self, vendor_id: int, product_id: int, device_num: int = 0) -> None:
        """Initialize and run a 3D input device."""
        try:
            dev_filter = hid.HidDeviceFilter(vendor_id=vendor_id, product_id=product_id)
            all_hids = dev_filter.get_devices()
            if not all_hids or device_num >= len(all_hids):
                raise ValueError("No suitable HID devices detected")

            dev = all_hids[device_num]
            self.dev_name = f"{dev.vendor_name} {dev.product_name}".strip()
            spec = self.device_specs.get(self.list_devices()[0])  # Assumes first device
            if not spec:
                raise ValueError("No supported device spec found")

            new_device = spec.__class__(vendor_id, product_id)  # Assumes constructor
            new_device.device = dev
            new_device.callback = self._process_3d_state
            new_device.button_callback = self._toggle_3d_buttons

            new_device.open()
            dev.set_raw_data_handler(lambda x: new_device.process(x))
            self.active_device = new_device
            print(f"You can start using {self.dev_name}")

            while not self._kbhit() and new_device.device.is_plugged():
                sleep(0.5)
        except Exception as e:
            print(f"Failed to start 3D input: {e}")
        finally:
            if self.active_device:
                self.active_device.close()

    def _process_3d_state(self, state) -> None:
        """Process 3D input state."""
        vec_input = [
            -state.x if abs(state.x) > 0.3 else 0.0,
            -state.y if abs(state.y) > 0.2 else 0.0,
            state.z if abs(state.z) > 0.2 else 0.0
        ]
        self.actuation.process_input(vec_input, self.dev_name)

    def _toggle_3d_buttons(self, state, buttons) -> None:
        """Handle 3D input button events."""
        if buttons[0] == 1:
            self.actuation.change_actuation(1)
        if buttons[1] == 1:
            self.actuation.adjust_sensitivity(1)

    def activate_devices(self, device_list: List[Tuple[int, int]]) -> None:
        """Activate multiple devices in parallel."""
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
        """Run a single device process."""
        try:
            obj = LisuDevControllers(vendor_id, product_id)
            self.device_specs = obj.dict_devices
            joystick = self.start_gamepad(vendor_id, product_id)
            queue.put(f"Started {self.dev_name}")
        except Exception as e:
            queue.put(f"Error with {vendor_id}/{product_id}: {e}")

    def _kbhit(self) -> bool:
        """Check for keyboard input (Windows-specific; replace for cross-platform)."""
        try:
            from msvcrt import kbhit
            return kbhit()
        except ImportError:
            return False  # Placeholder for non-Windows systems

if __name__ == "__main__":
    lisu = LisuManager()
    devices = [(0x054c, 0x09cc)]  # Example: PS4 controller VID/PID
    lisu.activate_devices(devices)
