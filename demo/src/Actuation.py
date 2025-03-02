import numpy as np
import socket
import json
from typing import List, Optional, Dict
from pathlib import Path
from LISU.datalogging import recordLog

class ActuationConfig:
    def __init__(self, selected_visualisation: str = None):
        config_path = Path(__file__).parent / "data" / "visualisation_config.json"
        default_config = {
            "visualisation": {
                "options": [], "selected": None,
                "render_options": {"resolution": "1920x1080"}
            },
            "actuation": {
                "config": {"x": 0.0, "y": 0.0, "z": 0.0, "angle": 20.0, "speed": 120.0, "fps": 20, "idx": 0, "idx2": 1, "count_state": 0},
                "commands": {"default": "addrotation %.3f %.3f %.3f %.3f"}
            },
            "calibration": {"deadzone": 0.1, "scale_factor": 1.0, "axis_mapping": {"x": "mouse_x", "y": "none", "z": "none"}},
            "input_devices": {}
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
                config_data, vis_data, cal_data, input_devs = (
                    default_config["actuation"]["config"],
                    default_config["visualisation"],
                    default_config["calibration"],
                    default_config["input_devices"]
                )
                recordLog("No JSON config found, using minimal default configuration")
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in {config_path}: {e}")
            recordLog(f"Invalid JSON in {config_path}: {e}")
            config_data, vis_data, cal_data, input_devs = (
                default_config["actuation"]["config"],
                default_config["visualisation"],
                default_config["calibration"],
                default_config["input_devices"]
            )
        except Exception as e:
            print(f"Failed to load configuration from {config_path}: {e}")
            recordLog(f"Failed to load configuration from {config_path}: {e}")
            config_data, vis_data, cal_data, input_devs = (
                default_config["actuation"]["config"],
                default_config["visualisation"],
                default_config["calibration"],
                default_config["input_devices"]
            )

        self.x = float(config_data.get("x", 0.0))
        self.y = float(config_data.get("y", 0.0))
        self.z = float(config_data.get("z", 0.0))
        self.angle = float(config_data.get("angle", 20.0))
        self.speed = float(config_data.get("speed", 120.0))
        self.fps = int(config_data.get("fps", 20))
        self.idx = int(config_data.get("idx", 0))
        self.idx2 = int(config_data.get("idx2", 1))
        self.count_state = int(config_data.get("count_state", 0))

        self.visualisation = vis_data
        self.calibration = cal_data
        self.input_devices = input_devs
        vis_settings = self.visualisation["render_options"].get("visualisations", {}).get(selected_visualisation or "default", {})
        self.udp_ip = vis_settings.get("udp_ip", "127.0.0.1")
        self.udp_port = vis_settings.get("udp_port", 7755)

    def _load_instructions(self) -> List[str]:
        config_path = Path(__file__).parent / "data" / "visualisation_config.json"
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
            recordLog(f"Failed to load actuation commands from JSON: {e}")
        return ["addrotation %.3f %.3f %.3f %.3f"]

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
    def __init__(self, vec_input_controller=None, selected_visualisation: str = None):
        self.config = ActuationConfig(selected_visualisation)
        self.vec_input_controller = vec_input_controller
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_ip = self.config.udp_ip
        self.udp_port = self.config.udp_port
        self.sock.settimeout(1.0)
        recordLog(f"Actuation initialized with UDP: {self.udp_ip}:{self.udp_port}")

    def __del__(self):
        self.sock.close()

    def process_input(self, vec_input: List[float], dev_name: str, command: str = "addrotation %.3f %.3f %.3f %.3f") -> None:
        recordLog(f"Processing input for {dev_name}: {vec_input}")
        cal = self.config.calibration_settings
        
        dev_config = self.config.input_device_settings.get(dev_name, {})
        num_axes = len(dev_config.get("axes", ["x"]))
        
        if num_axes >= 3:
            deadzone = float(cal.get("deadzone", 0.1))
            scale_factor = float(cal.get("scale_factor", 1.0))
            vec_input = self.normalise_value(vec_input, deadzone) * scale_factor
            recordLog(f"Calibrated input (3+ axes) for {dev_name}: {vec_input}")
        else:
            vec_input = np.array(vec_input)
            recordLog(f"Uncalibrated input (<3 axes) for {dev_name}: {vec_input}")

        if any(v != 0.0 for v in vec_input):
            self._send_command(vec_input, dev_name, command)
        else:
            recordLog(f"Skipping send for {dev_name}: All values in {vec_input} are zero")

    def _send_command(self, vec_input: List[float], dev_name: str, command: str) -> None:
        self.config.count_state += 1
        recordLog(f"Count state for {dev_name}: {self.config.count_state}")
        if self.config.count_state >= 2:
            dev_config = self.config.input_device_settings.get(dev_name, {})
            num_axes = len(dev_config.get("axes", ["x"]))
            try:
                if num_axes == 1:
                    message = command % (-vec_input[0], 0.0, 0.0, self.config.angle)
                else:
                    message = command % (-vec_input[0], -vec_input[1], vec_input[2], self.config.angle)
                print(f"{dev_name} : {message}")
                recordLog(f"Preparing to send for {dev_name}: {message}")
                self.sock.sendto(message.encode(), (self.udp_ip, self.udp_port))
                print(f"UDP instruction sent to {self.udp_ip}:{self.udp_port}: {message}")
                recordLog(f"UDP instruction sent to {self.udp_ip}:{self.udp_port}: {message}")
            except socket.error as e:
                print(f"Failed to send packet: {e}")
                recordLog(f"Failed to send packet for {dev_name}: {e}")
            except Exception as e:
                print(f"Unexpected error in send: {e}")
                recordLog(f"Unexpected error in send for {dev_name}: {e}")
            self.config.count_state = 0

    def change_actuation(self, val: int) -> None:
        if val == 1:
            self.config.idx = (self.config.idx + 1) % len(self.config.fun_array)
            if self.config.fun_array:
                fun_name = self.config.fun_array[self.config.idx].split(" ")[0]
                print(f"Button pressed for {fun_name}")
                recordLog(f"Button pressed for {fun_name}")
            else:
                print("No actuation commands available")
                recordLog("No actuation commands available")

    def adjust_sensitivity(self, val: int) -> None:
        if val == 1:
            self.config.idx2 += 4 if self.config.idx2 == 1 else 5
            self.config.idx2 = 1 if self.config.idx2 >= 25 else self.config.idx2
            print(f"Sensitivity set to {self.config.idx2}")
            recordLog(f"Sensitivity set to {self.config.idx2}")

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