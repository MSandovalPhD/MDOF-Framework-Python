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
    """Manages LISU input devices and actuation with dynamic visualisation and configuration."""
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
            "calibration": {"deadzone": 0.1, "scale_factor": 1.0, "axis_mapping": {"x": "mouse_x", "y": "none", "z": "none"}},
            "input_devices": {"Bluetooth_mouse": {"type": "mouse", "axes": ["x"], "buttons": ["left_click", "right_click"]}}
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

    def detect_devices(self) -> List[Tuple[int, int, str]]:
        """Detect and list all connected input devices, including Bluetooth mouse."""
        devices = []
        all_hids = hid.find_all_hid_devices()
        ontology = LisuOntology()
        for device in all_hids:
            vid, pid = device.vendor_id, device.product_id
            for attr in ontology.get_device_attributes():
                if hex(vid) == attr["VID"] and hex(pid) == attr["PID"]:
                    devices.append((vid, pid, attr["name"]))
        
        # Simulate Bluetooth mouse detection (assuming VID/PID for a generic Bluetooth mouse, e.g., 0x046D for Logitech)
        bluetooth_mouse = (0x046D, 0xC52B, "Bluetooth_mouse")  # Example Logitech mouse VID/PID
        if any(dev[2].lower() == "bluetooth_mouse" for dev in devices) or not devices:  # Ensure unique
            devices.append(bluetooth_mouse)
        
        print("Detected Input Devices:")
        for vid, pid, name in devices:
            print(f"VID: {hex(vid)}, PID: {hex(pid)}, Name: {name}")
        return devices

    def configure_device(self, vid: int, pid: int, name: str) -> Optional[InputDevice]:
        """Configure a device based on JSON config, handling mouse with 1-axis rotation."""
        try:
            device = InputDevice(vid, pid, name)
            device.open()
            device.callback = self._process_state
            device.button_callback = self._toggle_buttons

            # Apply JSON config for device type (e.g., mouse)
            if name.lower() == "bluetooth_mouse":
                self._configure_mouse(device)
            else:
                self._configure_generic(device)

            print(f"Configured {name} with JSON settings")
            return device
        except Exception as e:
            print(f"Failed to configure {name}: {e}")
            return None

    def _configure_mouse(self, device: InputDevice) -> None:
        """Configure Bluetooth mouse for 1-axis rotation using 'addrotation'."""
        cal = self.actuation.config.calibration_settings
        deadzone = float(cal.get("deadzone", 0.1))
        scale_factor = float(cal.get("scale_factor", 1.0))
        mapping = cal.get("axis_mapping", {"x": "mouse_x", "y": "none", "z": "none"})

        # Mouse has only x-axis movement; set y, z to 0 for 6DOF
        device.callback = lambda state: self._process_mouse_state(state, deadzone, scale_factor, mapping)
        device.button_callback = self._toggle_mouse_buttons

    def _configure_generic(self, device: InputDevice) -> None:
        """Configure generic device with full 6DOF if supported."""
        cal = self.actuation.config.calibration_settings
        deadzone = float(cal.get("deadzone", 0.1))
        scale_factor = float(cal.get("scale_factor", 1.0))
        device.callback = lambda state: self._process_state(state, deadzone, scale_factor)
        device.button_callback = self._toggle_buttons

    def _process_mouse_state(self, state: Dict, deadzone: float, scale_factor: float, mapping: Dict) -> None:
        """Process mouse state for 1-axis rotation using 'addrotation'."""
        x = state.get("x", 0.0) * scale_factor if abs(state.get("x", 0.0)) > deadzone else 0.0
        vec_input = [x, 0.0, 0.0]  # Only x-axis rotation, y and z set to 0
        self.actuation.process_input(vec_input, self.dev_name)

    def _process_state(self, state: Dict, deadzone: float, scale_factor: float) -> None:
        """Process generic device state with dynamic calibration."""
        vec_input = [
            -state.get("x", 0.0) * scale_factor if abs(state.get("x", 0.0)) > deadzone else 0.0,
            -state.get("y", 0.0) * scale_factor if abs(state.get("y", 0.0)) > deadzone else 0.0,
            state.get("z", 0.0) * scale_factor if abs(state.get("z", 0.0)) > deadzone else 0.0
        ]
        self.actuation.process_input(vec_input, self.dev_name)

    def _toggle_buttons(self, state: Dict, buttons: List[int]) -> None:
        """Handle generic button events."""
        if buttons[0] == 1:
            changeActuationHandler(1, self.actuation)

    def _toggle_mouse_buttons(self, state: Dict, buttons: List[int]) -> None:
        """Handle mouse button events (e.g., left/right click)."""
        if buttons[0] == 1:  # Left click
            print("Mouse left click detected - no action programmed")

    def run(self) -> None:
        """Run the LISU framework workflow."""
        # Step 1: Select visualisation
        visualisation = self.select_visualisation()

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
