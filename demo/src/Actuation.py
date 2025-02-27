import numpy as np
import socket
import json
from typing import List, Optional, Dict
from pathlib import Path

class ActuationConfig:
    def __init__(self):
        config_path = Path("./data/visualisation_config.json")
        default_config = {
            "visualisation": {"options": ["Drishti-v2.6.4", "ParaView"], "selected": None, "render_options": {"resolution": "1920x1080", "colour_scheme": "default", "transparency": 0.5}},
            "actuation": {"config": {"x": 0.0, "y": 0.0, "z": 0.0, "angle": 20.0, "speed": 120.0, "fps": 20, "idx": 0, "idx2": 1, "count_state": 0}, "commands": {"default": "addrotation %.3f %.3f %.3f %s"}},
            "calibration": {"deadzone": 0.1, "scale_factor": 1.0, "axis_mapping": {"x": "mouse_x", "y": "none", "z": "none"}},
            "input_devices": {"Bluetooth_mouse": {"type": "mouse", "axes": ["x"], "buttons": ["left_click", "right_click"]}}
        }
        self.fun_array = self._load_instructions()

        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)
                    config_data = config.get("actuation", {}).get("config", default_config["actuation"]["config"])
                    vis_data = config.get("visualisation", default_config["visualisation"])
                    cal_data = config.get("calibration", default_config["calibration"])
                    input_devs = config.get("input_devices", default_config["input_devices"])
            else:
                config_data, vis_data, cal_data, input_devs = (default_config["actuation"]["config"],
                                                             default_config["visualisation"],
                                                             default_config["calibration"],
                                                             default_config["input_devices"])
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in {config_path}: {e}")
            config_data, vis_data, cal_data, input_devs = (default_config["actuation"]["config"],
                                                         default_config["visualisation"],
                                                         default_config["calibration"],
                                                         default_config["input_devices"])
        except Exception as e:
            print(f"Failed to load configuration from {config_path}: {e}")
            config_data, vis_data, cal_data, input_devs = (default_config["actuation"]["config"],
                                                         default_config["visualisation"],
                                                         default_config["calibration"],
                                                         default_config["input_devices"])

        self.x: float = float(config_data.get("x", 0.0))
        self.y: float = float(config_data.get("y", 0.0))
        self.z: float = float(config_data.get("z", 0.0))
        self.angle: float = float(config_data.get("angle", 20.0))
        self.speed: float = float(config_data.get("speed", 120.0))
        self.fps: int = int(config_data.get("fps", 20))
        self.idx: int = int(config_data.get("idx", 0))
        self.idx2: int = int(config_data.get("idx2", 1))
        self.count_state: int = int(config_data.get("count_state", 0))

        self.visualisation = vis_data
        self.calibration = cal_data
        self.input_devices = input_devs

    def _load_instructions(self) -> List[str]:
        config_path = Path("./data/visualisation_config.json")
        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)
                    commands = config.get("actuation", {}).get("commands", None)
                    if isinstance(commands, dict):
                        return list(commands.values())
                    elif commands:
                        return sorted([str(cmd) for cmd in commands])
        except Exception as e:
            print(f"Failed to load actuation commands from JSON: {e}")
        return ["addrotation %.3f %.3f %.3f %s"]

    @property
    def visualisation_settings(self) -> Dict:
        return self.visualisation

    @property
    def calibration_settings(self) -> Dict:
        return self.calibration

    @property
    def input_device_settings(self) -> Dict:
        return self.input_devices

class Actuation:
    def __init__(self, vec_input_controller=None):
        self.config = ActuationConfig()
        self.vec_input_controller = vec_input_controller
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_ip = "127.0.0.1"
        self.udp_port = 7755
        self.sock.settimeout(1.0)

    def __del__(self):
        self.sock.close()

    def process_input(self, vec_input: List[float], dev_name: str, command: str = "addrotation %.3f %.3f %.3f %s") -> None:
        """Process and send input data, applying calibration only for devices with 3+ axes."""
        print(f"Processing input: {vec_input}")
        cal = self.config.calibration_settings
        
        # Check number of axes for the device
        dev_config = self.config.input_device_settings.get(dev_name, {})
        num_axes = len(dev_config.get("axes", ["x"]))  # Default to 1 axis if not specified
        
        if num_axes >= 3:
            # Apply calibration for devices with 3 or more axes
            deadzone = float(cal.get("deadzone", 0.1))
            scale_factor = float(cal.get("scale_factor", 1.0))
            vec_input = self.normalise_value(vec_input, deadzone) * scale_factor
            print(f"Calibrated input (3+ axes): {vec_input}")
        else:
            # Skip calibration for devices with fewer than 3 axes (e.g., mouse)
            vec_input = np.array(vec_input)  # Convert to numpy array without calibration
            print(f"Uncalibrated input (<3 axes): {vec_input}")

        if any(v != 0.0 for v in vec_input):
            self._send_command(vec_input, dev_name, command)
        else:
            print(f"Skipping send: All values in {vec_input} are zero")

    def _send_command(self, vec_input: List[float], dev_name: str, command: str) -> None:
        self.config.count_state += 1
        print(f"Count state: {self.config.count_state}")
        if self.config.count_state >= 2:
            message = command % (-vec_input[0], -vec_input[1], vec_input[2], str(self.config.idx2))
            print(f"{dev_name} : {message}")
            try:
                self.sock.sendto(message.encode(), (self.udp_ip, self.udp_port))
                print(f"UDP instruction sent to {self.udp_ip}:{self.udp_port}: {message}")
            except socket.error as e:
                print(f"Failed to send packet: {e}")
            self.config.count_state = 0

    def change_actuation(self, val: int) -> None:
        if val == 1:
            self.config.idx = (self.config.idx + 1) % len(self.config.fun_array)
            if self.config.fun_array:
                fun_name = self.config.fun_array[self.config.idx].split(" ")[0]
                print(f"Button pressed for {fun_name}")
            else:
                print("No actuation commands available")

    def adjust_sensitivity(self, val: int) -> None:
        if val == 1:
            self.config.idx2 += 4 if self.config.idx2 == 1 else 5
            self.config.idx2 = 1 if self.config.idx2 >= 25 else self.config.idx2
            print(f"Sensitivity set to {self.config.idx2}")

    def normalise_value(self, input_pwm: List[float], deadzone: float = 0.1) -> np.ndarray:
        vec_input = np.array(input_pwm)
        vec_input = self._dz_calibration(vec_input, deadzone)
        return np.clip(vec_input, -1.0, 1.0)

    def _dz_calibration(self, stick_input: np.ndarray, deadzone: float) -> np.ndarray:
        magnitude = np.linalg.norm(stick_input)
        if magnitude < deadzone:
            return np.zeros_like(stick_input)
        normalized = stick_input / magnitude
        scaled = normalized * ((magnitude - deadzone) / (1 - deadzone))
        return scaled

def xAxisChangeHandler(valLR: float, valUD: float, actuation: 'Actuation') -> None:
    cal = actuation.config.calibration_settings
    mapping = cal.get("axis_mapping", {})
    if mapping.get("x", "mouse_x") == "mouse_x":
        actuation.config.x = valLR

def yAxisChangeHandler(valLR: float, valUD: float, actuation: 'Actuation') -> None:
    cal = actuation.config.calibration_settings
    mapping = cal.get("axis_mapping", {})
    if mapping.get("y", "mouse_y") == "mouse_y":
        actuation.config.y = valLR

def zAxisChangeHandler(valLR: float, valUD: float, actuation: 'Actuation') -> None:
    cal = actuation.config.calibration_settings
    mapping = cal.get("axis_mapping", {})
    if mapping.get("z", "mouse_z") == "mouse_z":
        actuation.config.z = valLR

def changeActuationHandler(val: int, actuation: 'Actuation') -> None:
    actuation.change_actuation(val)
