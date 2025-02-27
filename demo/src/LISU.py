import Actuation
from LISU.devices import InputDevice
from LISU.datasource import LisuOntology
from Controllers import Controllers

import pywinusb.hid as hid
from time import sleep
import qprompt
from typing import List, Tuple, Optional, Dict
import json
from pathlib import Path

class LisuManager:
    """Manages LISU input devices and actuation with dynamic visualisation and configuration."""
    def __init__(self):
        self.device_specs = {}
        self.active_device = None
        self.dev_name = ""
        config_path = Path(__file__).parent.parent / "data" / "visualisation_config.json"
        self.config = self._load_config(config_path)
        self.actuation = Actuation.Actuation()

    def _load_config(self, config_path: Path) -> Dict:
        """Load configuration from JSON or use defaults."""
        default_config = {
            "visualisation": {"options": ["Drishti-v2.6.4", "ParaView"], "selected": None, "render_options": {"resolution": "1920x1080"}},
            "actuation": {"config": {"x": 0.0, "y": 0.0, "z": 0.0}, "commands": {"default": "addrotation %.3f %.3f %.3f %s"}},
            "calibration": {"default": {"deadzone": 0.1, "scale_factor": 1.0}},
            "input_devices": {}
        }
        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)
                    return {k: config.get(k, default_config[k]) for k in default_config}
            return default_config
        except Exception as e:
            print(f"Failed to load config: {e}")
            return default_config

    def select_visualisation(self) -> str:
        """Prompt user to select a 3D visualisation tool."""
        options = self.config["visualisation"]["options"]
        qprompt.clear()
        print("Available 3D Visualisations:")
        for i, vis in enumerate(options, 1):
            print(f"{i}. {vis}")
        choice = qprompt.ask(f"Select a visualisation (1-{len(options)}): ", int, min=1, max=len(options))
        selected = options[choice - 1]
        self.config["visualisation"]["selected"] = selected
        print(f"Selected visualisation: {selected}")
        return selected

    def detect_devices(self, use_ontology: bool = False) -> List[Tuple[str, str, str, Dict]]:
        """Detect connected input devices and match with JSON config."""
        devices = []
        all_hids = hid.find_all_hid_devices()
        input_devices = self.config["input_devices"]

        for device in all_hids:
            vid = f"{device.vendor_id:04x}".lower()
            pid = f"{device.product_id:04x}".lower()
            dev_config = None
            dev_name = f"Generic_Device_{len(devices) + 1}"

            # Match with JSON config
            for name, config in input_devices.items():
                if config.get("vid") == vid and config.get("pid") == pid:
                    dev_name = name
                    dev_config = config
                    break

            # Fallback to ontology only if use_ontology is True
            if not dev_config and use_ontology:
                ontology = LisuOntology(vid=vid, pid=pid)
                attrs = ontology.get_device_attributes()
                if attrs:
                    dev_name = attrs[0]["name"]
                    dev_config = {"type": attrs[0]["type"], "axes": ["x"] * int(attrs[0]["dof"]), "buttons": ["btn"] * int(attrs[0]["btns"])}

            devices.append((vid, pid, dev_name, dev_config or {"type": "unknown", "library": "pywinusb", "axes": ["x"], "buttons": []}))

        print("Detected Input Devices:")
        for vid, pid, name, config in devices:
            print(f"VID: {vid}, PID: {pid}, Name: {name}, Config: {config}")
        return devices

    def configure_device(self, vid: str, pid: str, name: str, dev_config: Dict) -> Optional[InputDevice]:
        """Configure a device based on its config."""
        try:
            print(f"Configuring - VID: {vid}, PID: {pid}, Name: {name}")
            library = dev_config.get("library", "pywinusb")
            if library != "pywinusb":
                print(f"Unsupported library {library} for {name}, falling back to pywinusb")
                library = "pywinusb"

            # Ensure vid and pid are valid hex strings
            if not all(c in '0123456789abcdef' for c in vid.lower()) or not all(c in '0123456789abcdef' for c in pid.lower()):
                raise ValueError(f"Invalid hex string - VID: {vid}, PID: {pid}")

            # Pass vid and pid as integers to InputDevice
            device = InputDevice(int(vid, 16), int(pid, 16), name)
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
            print(f"Configured {name} with {library}")
            return device
        except ValueError as e:
            print(f"Failed to configure {name}: {e}")
            return None
        except Exception as e:
            print(f"Failed to configure {name}: {e}")
            return None

    def _process_mouse_state(self, state: Dict, deadzone: float, scale_factor: float, mapping: Dict, dev_config: Dict) -> None:
        """Process mouse state for 1-axis rotation."""
        x = state.get("x", 0.0) * scale_factor if abs(state.get("x", 0.0)) > deadzone else 0.0
        vec_input = [x, 0.0, 0.0]
        command = self.config["actuation"]["commands"].get(dev_config.get("command", "mouse"), "addrotation %.3f %.3f %.3f %s")
        self.actuation.process_input(vec_input, self.dev_name, command)

    def _process_state(self, state: Dict, deadzone: float, scale_factor: float, dev_config: Dict) -> None:
        """Process generic device state."""
        vec_input = [
            state.get("x", 0.0) * scale_factor if abs(state.get("x", 0.0)) > deadzone else 0.0,
            state.get("y", 0.0) * scale_factor if abs(state.get("y", 0.0)) > deadzone else 0.0,
            state.get("z", 0.0) * scale_factor if abs(state.get("z", 0.0)) > deadzone else 0.0
        ]
        command = self.config["actuation"]["commands"].get(dev_config.get("command", "default"), "addrotation %.3f %.3f %.3f %s")
        self.actuation.process_input(vec_input, self.dev_name, command)

    def _toggle_buttons(self, state: Dict, buttons: List[int]) -> None:
        """Handle button events."""
        if buttons and buttons[0] == 1:
            print(f"Button pressed on {self.dev_name}")

    def run(self) -> None:
        """Run the LISU framework workflow."""
        visualisation = self.select_visualisation()
        devices = self.detect_devices(use_ontology=False)  # Skip ontology by default
        if not devices:
            print("No devices detected. Exiting.")
            return

        for vid, pid, name, dev_config in devices:
            device = self.configure_device(vid, pid, name, dev_config)
            if device:
                self.active_device = device
                print(f"Activating {name} for {visualisation}")
                while not self._kbhit() and (device.device.is_plugged() if device.device else False):
                    sleep(0.5)
                device.close()

    def _kbhit(self) -> bool:
        """Check for keyboard input (Windows-specific)."""
        try:
            from msvcrt import kbhit
            return kbhit()
        except ImportError:
            return False

if __name__ == "__main__":
    lisu = LisuManager()
    lisu.run()
