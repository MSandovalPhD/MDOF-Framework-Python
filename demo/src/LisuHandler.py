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
    def __init__(self):
        self.device = None
        self.dev_name = ""
        self.running = threading.Event()
        self.running.set()
        self.use_axis = "x"
        self.button_mappings = {}
        self.speed_factor = 1.0
        config_path = Path(__file__).parent / "data" / "visualisation_config.json"
        print(f"Looking for config at: {config_path}")
        self.config = self._load_config(config_path)
        self.selected_visualisation = self.select_visualisation()
        self.actuation = Actuation.Actuation(selected_visualisation=self.selected_visualisation)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, sig, frame):
        recordLog("Received Ctrl+C, stopping")
        self.running.clear()

    def _load_config(self, config_path: Path) -> Dict:
        default_config = {
            "visualisation": {
                "options": ["Drishti-v2.6.4", "ParaView"],
                "selected": None,
                "render_options": {"resolution": "1920x1080"}
            },
            "actuation": {"config": {"x": 0.0, "y": 0.0, "z": 0.0}, "commands": {"default": "addrotation %.3f %.3f %.3f %.3f"}},
            "calibration": {
                "default": {"deadzone": 0.1, "scale_factor": 1.0},
                "devices": {}
            },
            "input_devices": {
                "Bluetooth_mouse": {"vid": "046d", "pid": "b03a", "type": "mouse", "library": "pywinusb", "axes": ["x"], "buttons": ["left_click", "right_click"], "command": "mouse"},
                "PS4_Controller": {"vid": "054c", "pid": "09cc", "type": "gamepad", "library": "pywinusb", "axes": ["x", "y", "z"], "buttons": ["btn1", "btn2"], "command": "default"}
            }
        }
        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    config_content = f.read()
                    print(f"Raw config content: {config_content}")  # Debug raw file content
                    config = json.loads(config_content)
                    print(f"Parsed config: {config}")
                    loaded_devices = config.get("input_devices", default_config["input_devices"])
                    print(f"Loaded input_devices: {loaded_devices}")
                    config["input_devices"] = loaded_devices
                    if "calibration" not in config:
                        config["calibration"] = default_config["calibration"]
                    if "devices" not in config["calibration"]:
                        config["calibration"]["devices"] = {}
                    return {k: config.get(k, default_config[k]) for k in default_config}
            else:
                recordLog(f"No JSON config found at {config_path}, using default configuration with options")
                print(f"Config file not found at {config_path}, using default with input_devices: {default_config['input_devices']}")
                return default_config
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in {config_path}: {e}")
            recordLog(f"Invalid JSON in {config_path}: {e}")
            return default_config
        except Exception as e:
            print(f"Failed to load config from {config_path}: {e}")
            recordLog(f"Failed to load config from {config_path}: {e}")
            return default_config

    def select_visualisation(self) -> str:
        options = self.config["visualisation"]["options"]
        if not options:
            raise ValueError("No visualisation options defined in config.")
        qprompt.clear()
        print("Available 3D Visualisations:")
        for i, vis in enumerate(options, 1):
            print(f"{i}. {vis}")
        choice = qprompt.ask(f"Select a visualisation (1-{len(options)}): ", int, min=1, max=len(options))
        selected = options[choice - 1]
        self.config["visualisation"]["selected"] = selected
        print(f"Selected visualisation: {selected}")
        return selected

    def list_devices(self) -> List[Tuple[str, str, str, Dict]]:
        all_hids = hid.find_all_hid_devices()
        print(f"Detected HID devices: {len(all_hids)} found")
        for device in all_hids:
            vid = f"{device.vendor_id:04x}".lower()
            pid = f"{device.product_id:04x}".lower()
            print(f"HID Device - VID: {vid}, PID: {pid}, Product: {device.product_name}")

        input_devices = self.config["input_devices"]
        print(f"Configured devices from JSON: {input_devices}")
        available_devices = []
        for device in all_hids:
            vid = f"{device.vendor_id:04x}".lower()
            pid = f"{device.product_id:04x}".lower()
            for name, config in input_devices.items():
                if config.get("vid") == vid and config.get("pid") == pid:
                    print(f"Match found: {name} (VID: {vid}, PID: {pid})")
                    available_devices.append((vid, pid, name, config))
        if not available_devices:
            print("No matches between detected HID devices and config.")
        return available_devices

    def select_device(self) -> Optional[Tuple[str, str, str, Dict]]:
        devices = self.list_devices()
        if not devices:
            print("No compatible devices found.")
            recordLog("No compatible devices found.")
            return None

        qprompt.clear()
        print("Available Devices:")
        for i, (vid, pid, name, config) in enumerate(devices, 1):
            print(f"{i}. {name} (VID: {vid}, PID: {pid}, Type: {config.get('type', 'unknown')})")
        choice = qprompt.ask(f"Select a device (1-{len(devices)}) ", int, min=1, max=len(devices))
        return devices[choice - 1]

    def configure_buttons(self, dev_config: Dict) -> Dict:
        if not qprompt.ask_yesno("Configure buttons? (y/n)", default="n"):
            return {}
        
        buttons = dev_config.get("buttons", [])
        if not buttons:
            print("No buttons available for this device.")
            return {}

        actions = ["change_axis", "increase_speed", "decrease_speed"]
        mappings = {}
        
        while qprompt.ask_yesno("Add a button mapping? (y/n)", default="y"):
            print("Available Buttons:")
            for i, btn in enumerate(buttons, 1):
                print(f"{i}. {btn}")
            btn_choice = qprompt.ask(f"Select a button (1-{len(buttons)}) ", int, min=1, max=len(buttons))
            selected_btn = buttons[btn_choice - 1]

            print("Available Actions:")
            for i, action in enumerate(actions, 1):
                print(f"{i}. {action}")
            action_choice = qprompt.ask(f"Select an action (1-{len(actions)}) ", int, min=1, max=len(actions))
            selected_action = actions[action_choice - 1]

            if selected_action == "change_axis":
                axes = ["x", "y", "z"]
                axis_choice = qprompt.ask("Select axis (1=x, 2=y, 3=z) ", int, min=1, max=3)
                mappings[selected_btn] = {"action": "change_axis", "axis": axes[axis_choice - 1]}
            else:
                mappings[selected_btn] = {"action": selected_action}

            print(f"Configured {selected_btn} to {selected_action}")
            recordLog(f"Configured {selected_btn} to {selected_action}")

        return mappings

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
            self.button_mappings = self.configure_buttons(dev_config)
            device.button_callback = lambda state, buttons: self._handle_buttons(state, buttons, dev_config)
            self.dev_name = name
            print(f"Configured {name} successfully")
            recordLog(f"Configured {name} successfully")
            return device
        except Exception as e:
            print(f"Failed to configure {name}: {e}")
            recordLog(f"Failed to configure {name}: {e}")
            return None

    def _handle_buttons(self, state: Dict, buttons: List[int], dev_config: Dict) -> None:
        if not self.running.is_set():
            return
        for i, btn_state in enumerate(buttons):
            if btn_state == 1 and i < len(dev_config.get("buttons", [])):
                btn_name = dev_config["buttons"][i]
                mapping = self.button_mappings.get(btn_name)
                if mapping:
                    action = mapping["action"]
                    if action == "change_axis":
                        self.use_axis = mapping["axis"]
                        print(f"Button {btn_name} switched to {self.use_axis}-axis")
                        recordLog(f"Button {btn_name} switched to {self.use_axis}-axis")
                    elif action == "increase_speed":
                        self.speed_factor = min(self.speed_factor + 0.5, 5.0)
                        print(f"Speed increased to {self.speed_factor}")
                        recordLog(f"Speed increased to {self.speed_factor}")
                    elif action == "decrease_speed":
                        self.speed_factor = max(self.speed_factor - 0.5, 0.1)
                        print(f"Speed decreased to {self.speed_factor}")
                        recordLog(f"Speed decreased to {self.speed_factor}")

    def _process_mouse_state(self, state: Dict, deadzone: float, scale_factor: float, mapping: Dict, dev_config: Dict) -> None:
        if not self.running.is_set():
            return
        x = state.get("x", 0.0) * scale_factor * self.speed_factor
        vec_input = {"x": [x, 0.0, 0.0], "y": [0.0, x, 0.0], "z": [0.0, 0.0, x]}
        selected_vec = vec_input.get(self.use_axis, [x, 0.0, 0.0])
        recordLog(f"Using {self.use_axis}-axis for {self.dev_name}: {selected_vec}")
        command = self.config["actuation"]["commands"].get(dev_config.get("command", "mouse"), "addrotation %.3f %.3f %.3f %.3f")
        print(f"Calling actuation for {self.dev_name} with input: {selected_vec}")
        self.actuation.process_input(selected_vec, self.dev_name, command)

    def _process_state(self, state: Dict, deadzone: float, scale_factor: float, dev_config: Dict) -> None:
        if not self.running.is_set():
            return
        vec_input = [
            state.get("x", 0.0) * scale_factor * self.speed_factor if abs(state.get("x", 0.0)) > deadzone else 0.0,
            state.get("y", 0.0) * scale_factor * self.speed_factor if abs(state.get("y", 0.0)) > deadzone else 0.0,
            state.get("z", 0.0) * scale_factor * self.speed_factor if abs(state.get("z", 0.0)) > deadzone else 0.0
        ]
        command = self.config["actuation"]["commands"].get(dev_config.get("command", "default"), "addrotation %.3f %.3f %.3f %.3f")
        print(f"Calling actuation for {self.dev_name} with input: {vec_input}")
        recordLog(f"Calling actuation for {self.dev_name} with input: {vec_input}")
        self.actuation.process_input(vec_input, self.dev_name, command)

    def configure_and_run(self):
        device_info = self.select_device()
        if not device_info:
            print("Exiting due to no device selected.")
            return

        vid, pid, name, dev_config = device_info
        self.device = self.configure_device(vid, pid, name, dev_config)
        if self.device:
            print(f"Activating {name} for {self.selected_visualisation}")
            print("[Press Ctrl+C to stop...]")
            recordLog(f"Activating {name} for {self.selected_visualisation}")
            try:
                while self.running.is_set() and self.device.device.is_plugged():
                    threading.Event().wait(0.1)
            except Exception as e:
                print(f"Unexpected error in run loop: {e}")
                recordLog(f"Unexpected error in run loop: {e}")
            finally:
                self.running.clear()
                self.device.close()
                print(f"Closed {name}")
                recordLog(f"Closed {name}")
                sys.exit(0)

    def start_gamepad(self, vid: int, pid: int):
        device_info = self._detect_gamepad(vid, pid)
        if not device_info:
            print(f"No gamepad found with VID: {hex(vid)}, PID: {hex(pid)}")
            recordLog(f"No gamepad found with VID: {hex(vid)}, PID: {hex(pid)}")
            return

        vid_str, pid_str, name, dev_config = device_info
        self.device = self.configure_device(vid_str, pid_str, name, dev_config)
        if self.device:
            print(f"Starting gamepad {name} (VID: {vid_str}, PID: {pid_str}) for {self.selected_visualisation}")
            recordLog(f"Starting gamepad {name} (VID: {vid_str}, PID: {pid_str}) for {self.selected_visualisation}")
            try:
                while self.running.is_set() and self.device.device.is_plugged():
                    threading.Event().wait(0.1)
            except Exception as e:
                print(f"Unexpected error in gamepad loop: {e}")
                recordLog(f"Unexpected error in gamepad loop: {e}")
            finally:
                self.running.clear()
                self.device.close()
                print(f"Closed gamepad {name}")
                recordLog(f"Closed gamepad {name}")
                sys.exit(0)

    def _detect_gamepad(self, vid: int, pid: int) -> Optional[Tuple[str, str, str, Dict]]:
        all_hids = hid.find_all_hid_devices()
        input_devices = self.config["input_devices"]
        vid_str = f"{vid:04x}".lower()
        pid_str = f"{pid:04x}".lower()
        for device in all_hids:
            dev_vid = f"{device.vendor_id:04x}".lower()
            dev_pid = f"{device.product_id:04x}".lower()
            for name, config in input_devices.items():
                if (config.get("vid") == dev_vid and config.get("pid") == dev_pid and
                    config.get("type") == "gamepad" and dev_vid == vid_str and dev_pid == pid_str):
                    print(f"Found gamepad: {name} (VID: {dev_vid}, PID: {dev_pid})")
                    recordLog(f"Found gamepad: {name} (VID: {dev_vid}, PID: {dev_pid})")
                    return (dev_vid, dev_pid, name, config)
        return None

if __name__ == "__main__":
    lisu = LisuManager()
    lisu.configure_and_run()