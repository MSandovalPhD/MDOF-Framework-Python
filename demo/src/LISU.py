import sys
from pathlib import Path

# Add the project directory to the Python path
project_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_dir))

import pywinusb.hid as hid
import qprompt
from typing import List, Tuple, Optional, Dict
import Actuation
from LISU.devices import InputDevice
from LISU.datasource import LisuOntology
import Controllers
import json

class LisuManager:
    """Manages LISU input devices and actuation with dynamic, generic configuration."""
    def __init__(self):
        self.device_specs = {}
        self.active_device = None
        self.dev_name = ""
        config_path = Path("./data/visualisation_config.json")
        self.config = self._load_config(config_path)
        self.actuation = Actuation.Actuation()

    def _load_config(self, config_path: Path) -> Dict:
        """Load configuration from JSON or use defaults."""
        default_config = {
            "visualisation": {"options": ["Drishti-v2.6.4", "ParaView"], "selected": None, "render_options": {"resolution": "1920x1080", "colour_scheme": "default", "transparency": 0.5}},
            "actuation": {"config": {"x": 0.0, "y": 0.0, "z": 0.0, "angle": 20.0, "speed": 120.0, "fps": 20, "idx": 0, "idx2": 1, "count_state": 0}, "commands": ["addrotation %.3f %.3f %.3f %s"]},
            "calibration": {"deadzone": 0.1, "scale_factor": 1.0, "axis_mapping": {"x": "generic_x", "y": "generic_y", "z": "generic_z"}},
            "input_devices": {}
        }
        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)
                    return {k: config.get(k, default_config[k]) for k in default_config}
            return default_config
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in {config_path}: {e}")
            return default_config
        except Exception as e:
            print(f"Failed to load configuration from {config_path}: {e}")
            return default_config

    def select_visualisation(self) -> str:
        """Prompt user to select a 3D visualisation tool from JSON options."""
        options = self.config["visualisation"]["options"]
        qprompt.clear()
        print("Available 3D Visualisations:")
        for i, vis in enumerate(options, 1):
            print(f"{i}. {vis}")
        choice = qprompt.ask("Select a visualisation (1-{len}): ", int, min=1, max=len(options))
        selected = options[choice - 1]
        self.config["visualisation"]["selected"] = selected
        print(f"Selected visualisation: {selected}")
        return selected

    def detect_devices(self) -> List[Tuple[str, str, str]]:
        """Detect and list all connected input devices dynamically, including any mouse or gamepad."""
        devices = []
        all_hids = hid.find_all_hid_devices()
        ontology = LisuOntology()
        for device in all_hids:
            vid = f"{device.vendor_id:04x}".lower()  # Convert to hex string, e.g., "054c"
            pid = f"{device.product_id:04x}".lower()  # Convert to hex string, e.g., "09cc"
            for attr in ontology.get_device_attributes():
                if vid == attr["VID"].lower() and pid == attr["PID"].lower():
                    devices.append((vid, pid, attr["name"]))
                # Fallback: assume unknown devices as generic input
                if not devices or not any(d[2] == attr["name"] for d in devices):
                    devices.append((vid, pid, f"Generic_Device_{len(devices)+1}"))
        
        # Attempt to detect any mouse dynamically (including Bluetooth)
        try:
            for device in all_hids:
                vid = f"{device.vendor_id:04x}".lower()
                pid = f"{device.product_id:04x}".lower()
                if "mouse" in device.product_name.lower() or "bluetooth" in device.product_name.lower():
                    devices.append((vid, pid, "Bluetooth_mouse"))
                    break
        except Exception as e:
            print(f"Failed to detect mouse: {e}")
        
        print("Detected Input Devices:")
        for vid, pid, name in devices:
            print(f"VID: {vid}, PID: {pid}, Name: {name}")
        return devices

    def configure_device(self, vid: str, pid: str, name: str) -> Optional[InputDevice]:
        """Configure any device based on JSON config, handling missing axes gracefully."""
        try:
            # Convert hex strings to integers for HID interaction
            vid_int = int(vid, 16)
            pid_int = int(pid, 16)
            device = InputDevice(vid_int, pid_int, name)
            device.open()
            device.callback = self._process_state
            device.button_callback = self._toggle_buttons

            # Apply JSON config dynamically, handling device type (e.g., mouse vs. generic)
            self._configure_generic(device, name)

            print(f"Configured {name} with JSON settings")
            return device
        except Exception as e:
            print(f"Failed to configure {name}: {e}")
            return None

    def _configure_generic(self, device: InputDevice, name: str) -> None:
        """Configure any device type with dynamic calibration, handling missing axes (e.g., no 6DOF for mouse)."""
        cal = self.actuation.config.calibration_settings
        deadzone = float(cal.get("deadzone", 0.1))
        scale_factor = float(cal.get("scale_factor", 1.0))
        mapping = cal.get("axis_mapping", {"x": "generic_x", "y": "generic_y", "z": "generic_z"})

        # Determine device type from ontology or name
        ontology = LisuOntology(vid=device.vid, pid=device.pid)
        device_attrs = ontology.get_device_attributes()
        device_type = device_attrs[0]["type"] if device_attrs else "unknown"

        if name.lower() == "bluetooth_mouse" or device_type.lower() == "mouse":
            device.callback = lambda state: self._process_mouse_state(state, deadzone, scale_factor, mapping)
            device.button_callback = self._toggle_mouse_buttons
        else:
            device.callback = lambda state: self._process_state(state, deadzone, scale_factor, mapping)
            device.button_callback = self._toggle_buttons

    def _process_mouse_state(self, state: Dict, deadzone: float, scale_factor: float, mapping: Dict) -> None:
        """Process mouse state for 1-axis rotation using 'addrotation' (x-axis only, y and z set to 0)."""
        x = state.get("x", 0.0) * scale_factor if abs(state.get("x", 0.0)) > deadzone else 0.0
        vec_input = [x, 0.0, 0.0]  # Only x-axis rotation, y and z set to 0
        self.actuation.process_input(vec_input, self.dev_name)

    def _process_state(self, state: Dict, deadzone: float, scale_factor: float, mapping: Dict) -> None:
        """Process generic device state with dynamic calibration, handling any number of axes."""
        vec_input = [0.0, 0.0, 0.0]  # Default to 3D for 6DOF, adjust dynamically
        if "x" in state and mapping.get("x", "generic_x") == "generic_x":
            vec_input[0] = -state.get("x", 0.0) * scale_factor if abs(state.get("x", 0.0)) > deadzone else 0.0
        if "y" in state and mapping.get("y", "generic_y") == "generic_y":
            vec_input[1] = -state.get("y", 0.0) * scale_factor if abs(state.get("y", 0.0)) > deadzone else 0.0
        if "z" in state and mapping.get("z", "generic_z") == "generic_z":
            vec_input[2] = state.get("z", 0.0) * scale_factor if abs(state.get("z", 0.0)) > deadzone else 0.0
        self.actuation.process_input(vec_input, self.dev_name)

    def _toggle_buttons(self, state: Dict, buttons: List[int]) -> None:
        """Handle generic button events for any device."""
        if buttons and buttons[0] == 1:
            self.actuation.change_actuation(1)

    def _toggle_mouse_buttons(self, state: Dict, buttons: List[int]) -> None:
        """Handle mouse button events (e.g., left/right click)."""
        if buttons and buttons[0] == 1:  # Left click
            print("Mouse left click detected - no action programmed")

    def run(self) -> None:
        """Run the LISU framework workflow for any device."""
        # Step 1: Select visualisation
        visualisation = self.select_visualisation()
        if not visualisation:
            print("No visualisation selected. Exiting.")
            return

        # Step 2: Detect devices
        devices = self.detect_devices()
        if not devices:
            print("No devices detected. Exiting.")
            return

        # Step 3: Configure and activate each device
        for vid, pid, name in devices:
            device = self.configure_device(vid, pid, name)
            if device:
                self.active_device = device
                print(f"Activating {name} for {visualisation}")
                while not self._kbhit() and (device.device.is_plugged() if device.device else False):
                    sleep(0.5)
                device.close()

    def _kbhit(self) -> bool:
        """Check for keyboard input (Windows-specific; replace for cross-platform)."""
        try:
            from msvcrt import kbhit
            return kbhit()
        except ImportError:
            return False

if __name__ == "__main__":
    lisu = LisuManager()
    lisu.run()
