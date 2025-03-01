import Actuation
from LISU.devices import InputDevice
import pywinusb.hid as hid
import qprompt
from typing import List, Tuple, Optional, Dict
import json
from pathlib import Path
import threading
import signal
import sys
from LISU.datalogging import recordLog

class LisuManager:
    def __init__(self, target_device: str = "Bluetooth_mouse"):
        self.target_device = target_device
        self.device_specs = {}
        self.active_device = None
        self.dev_name = ""
        self.running = threading.Event()
        self.running.set()
        self.use_y_axis = False
        config_path = Path(__file__).parent.parent / "data" / "visualisation_config.json"
        self.config = self._load_config(config_path)
        self.selected_visualisation = self.select_visualisation()
        self.actuation = Actuation.Actuation(selected_visualisation=self.selected_visualisation)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, sig, frame):
        recordLog("Received Ctrl+C, stopping")
        self.running.clear()

    def _load_config(self, config_path: Path) -> Dict:
        default_config = {
            "visualisation": {"options": [], "selected": None, "render_options": {"resolution": "1920x1080"}},
            "actuation": {"config": {"x": 0.0, "y": 0.0, "z": 0.0}, "commands": {"default": "addrotation %.3f %.3f %.3f %s"}},
            "calibration": {"default": {"deadzone": 0.1, "scale_factor": 1.0}},
            "input_devices": {}
        }
        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)
                    return {k: config.get(k, default_config[k]) for k in default_config}
            recordLog("No JSON config found, using minimal default configuration")
            return default_config
        except Exception as e:
            print(f"Failed to load config: {e}")
            recordLog(f"Failed to load config: {e}")
            return default_config

    def select_visualisation(self) -> str:
        options = self.config["visualisation"]["options"]
        if not options:
            raise ValueError("No visualisation options defined in config. Please update visualisation_config.json.")
        qprompt.clear()
        print("Available 3D Visualisations:")
        for i, vis in enumerate(options, 1):
            print(f"{i}. {vis}")
        choice = qprompt.ask(f"Select a visualisation (1-{len(options)}): ", int, min=1, max=len(options))
        selected = options[choice - 1]
        self.config["visualisation"]["selected"] = selected
        print(f"Selected visualisation: {selected}")
        return selected

    def detect_devices(self) -> Optional[Tuple[str, str, str, Dict]]:
        all_hids = hid.find_all_hid_devices()
        input_devices = self.config["input_devices"]
        for device in all_hids:
            vid = f"{device.vendor_id:04x}".lower()
            pid = f"{device.product_id:04x}".lower()
            for name, config in input_devices.items():
                if (config.get("vid") == vid and config.get("pid") == pid and 
                    name == self.target_device):
                    print(f"Found target device: {name} (VID: {vid}, PID: {pid})")
                    recordLog(f"Found target device: {name} (VID: {vid}, PID: {pid})")
                    return (vid, pid, name, config)
        print(f"Target device '{self.target_device}' not found.")
        recordLog(f"Target device '{self.target_device}' not found.")
        return None

    def configure_device(self, vid: str, pid: str, name: str, dev_config: Dict) -> Optional[InputDevice]:
        try:
            vid_int = int(vid, 16)
            pid_int = int(pid, 16)
            device = InputDevice(vid_int, pid_int, name, dev_config)
            device.open()
            cal = self.config["calibration"]["devices"].get(name, self.config["calibration"]["default"])
            deadzone = float(cal.get("deadzone", 0.1))
            scale_factor = float(cal.get("scale_factor", 1.0))
            if dev_config["type"] == "mouse":
                mapping = cal.get("axis_mapping", {"x": "mouse_x", "y": "none", "z": "none"})
                device.callback = lambda state: self._process_mouse_state(state, deadzone, scale_factor, mapping, dev_config)
            else:
                device.callback = lambda state: self._process_state(state, deadzone, scale_factor, dev_config)
            device.button_callback = self._toggle_buttons
            self.dev_name = name
            print(f"Configured {name} successfully")
            recordLog(f"Configured {name} successfully")
            return device
        except Exception as e:
            print(f"Failed to configure {name}: {e}")
            recordLog(f"Failed to configure {name}: {e}")
            return None

    def _process_mouse_state(self, state: Dict, deadzone: float, scale_factor: float, mapping: Dict, dev_config: Dict) -> None:
        if not self.running.is_set():
            return
        x = state.get("x", 0.0)
        if self.use_y_axis:
            vec_input = [0.0, x, 0.0]
            recordLog(f"Using y-axis for {self.dev_name}: {vec_input}")
        else:
            vec_input = [x, 0.0, 0.0]
            recordLog(f"Using x-axis for {self.dev_name}: {vec_input}")
        command = self.config["actuation"]["commands"].get(dev_config.get("command", "mouse"), "addrotation %.3f %.3f %.3f %s")
        print(f"Calling actuation for {self.dev_name} with input: {vec_input}")
        self.actuation.process_input(vec_input, self.dev_name, command)

    def _process_state(self, state: Dict, deadzone: float, scale_factor: float, dev_config: Dict) -> None:
        if not self.running.is_set():
            return
        vec_input = [
            state.get("x", 0.0) * scale_factor if abs(state.get("x", 0.0)) > deadzone else 0.0,
            state.get("y", 0.0) * scale_factor if abs(state.get("y", 0.0)) > deadzone else 0.0,
            state.get("z", 0.0) * scale_factor if abs(state.get("z", 0.0)) > deadzone else 0.0
        ]
        command = self.config["actuation"]["commands"].get(dev_config.get("command", "default"), "addrotation %.3f %.3f %.3f %s")
        print(f"Calling actuation for {self.dev_name} with input: {vec_input}")
        recordLog(f"Calling actuation for {self.dev_name} with input: {vec_input}")
        self.actuation.process_input(vec_input, self.dev_name, command)

    def _toggle_buttons(self, state: Dict, buttons: List[int]) -> None:
        if not self.running.is_set():
            return
        if buttons and buttons[0] == 1:
            self.use_y_axis = not self.use_y_axis
            axis = "y" if self.use_y_axis else "x"
            print(f"Button pressed on {self.dev_name}, switched to {axis}-axis")
            recordLog(f"Button pressed on {self.dev_name}, switched to {axis}-axis")

    def run(self) -> None:
        device_info = self.detect_devices()
        if not device_info:
            print("Exiting due to no target device found.")
            return

        vid, pid, name, dev_config = device_info
        device = self.configure_device(vid, pid, name, dev_config)
        if device:
            self.active_device = device
            print(f"Activating {name} for {self.selected_visualisation}")
            print("[Press Ctrl+C to stop...]")
            recordLog(f"Activating {name} for {self.selected_visualisation}")
            try:
                while self.running.is_set() and device.device.is_plugged():
                    threading.Event().wait(0.1)
            except Exception as e:
                print(f"Unexpected error in run loop: {e}")
                recordLog(f"Unexpected error in run loop: {e}")
            finally:
                self.running.clear()
                device.close()
                print(f"Closed {name}")
                recordLog(f"Closed {name}")
                sys.exit(0)

if __name__ == "__main__":
    lisu = LisuManager(target_device="Bluetooth_mouse")
    lisu.run()