import numpy as np
import socket
import json
from typing import List, Optional, Dict
from pathlib import Path
from src.LISU.datasource import LisuOntology

class ActuationConfig:
    def __init__(self):
        config_path = Path("./data/visualisation_config.json")
        default_config = {
            "actuation": {
                "config": {
                    "x": 0.0,
                    "y": 0.0,
                    "z": 0.0,
                    "angle": 20.0,
                    "speed": 120.0,
                    "fps": 20,
                    "idx": 0,
                    "idx2": 1,
                    "count_state": 0
                },
                "commands": ["addrotation %.3f %.3f %.3f %s", "addrotationclip %.3f %.3f %.3f %s"]
            },
            "visualisation": {
                "selected": "3d_model_view",
                "render_options": {
                    "resolution": "1920x1080",
                    "color_scheme": "default",
                    "transparency": 0.5
                }
            },
            "calibration": {
                "deadzone": 0.25,
                "scale_factor": 1.0,
                "axis_mapping": {
                    "x": "left_stick_lr",
                    "y": "left_stick_ud",
                    "z": "right_trigger"
                }
            }
        }
        self.fun_array = self._load_instructions()

        # Load configuration from JSON or use defaults
        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)
                    config_data = config.get("actuation", {}).get("config", default_config["actuation"]["config"])
                    vis_data = config.get("visualisation", default_config["visualisation"])
                    cal_data = config.get("calibration", default_config["calibration"])
            else:
                config_data, vis_data, cal_data = (default_config["actuation"]["config"],
                                                 default_config["visualisation"],
                                                 default_config["calibration"])
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in {config_path}: {e}")
            config_data, vis_data, cal_data = (default_config["actuation"]["config"],
                                             default_config["visualisation"],
                                             default_config["calibration"])
        except Exception as e:
            print(f"Failed to load configuration from {config_path}: {e}")
            config_data, vis_data, cal_data = (default_config["actuation"]["config"],
                                             default_config["visualisation"],
                                             default_config["calibration"])

        # Set instance attributes from config or defaults
        self.x: float = float(config_data.get("x", 0.0))
        self.y: float = float(config_data.get("y", 0.0))
        self.z: float = float(config_data.get("z", 0.0))
        self.angle: float = float(config_data.get("angle", 20.0))
        self.speed: float = float(config_data.get("speed", 120.0))
        self.fps: int = int(config_data.get("fps", 20))
        self.idx: int = int(config_data.get("idx", 0))
        self.idx2: int = int(config_data.get("idx2", 1))
        self.count_state: int = int(config_data.get("count_state", 0))

        # Store visualization and calibration for other scripts to access
        self.visualisation = vis_data
        self.calibration = cal_data

    def _load_instructions(self) -> List[str]:
        """Load actuation commands dynamically from ontology, JSON, or generate default alphabetically."""
        # Try ontology first
        try:
            ontology = LisuOntology()
            commands = ontology.get_actuation_commands()
            if commands:
                print("Loaded actuation commands from ontology")
                return sorted(commands)  # Ensure alphabetical order
        except Exception as e:
            print(f"Failed to load actuation commands from ontology: {e}")

        # Fall back to JSON configuration
        config_path = Path("./data/visualisation_config.json")
        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)
                    commands = config.get("actuation", {}).get("commands", None)
                    if commands:
                        print("Loaded actuation commands from JSON configuration")
                        return sorted([str(cmd) for cmd in commands])  # Ensure alphabetical order
        except Exception as e:
            print(f"Failed to load actuation commands from JSON: {e}")

        # Default fallback: generate alphabetically ordered commands starting with "addrotation"
        default_commands = ["addrotation %.3f %.3f %.3f %s", "addrotationclip %.3f %.3f %.3f %s"]
        print("Using default alphabetically ordered actuation commands")
        return sorted(default_commands)  # Ensures "addrotation" is first

    @property
    def visualization_settings(self) -> Dict:
        """Get visualisation settings."""
        return self.visualisation

    @property
    def calibration_settings(self) -> Dict:
        """Get calibration settings."""
        return self.calibration

class Actuation:
    def __init__(self, vec_input_controller=None):
        self.config = ActuationConfig()
        self.vec_input_controller = vec_input_controller
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_ip = "127.0.0.1"
        self.udp_port = 7755

    def __del__(self):
        self.sock.close()

    def process_input(self, vec_input: List[float], dev_name: str) -> None:
        """Process and send normalized input data, applying calibration."""
        cal = self.config.calibration_settings
        deadzone = float(cal.get("deadzone", 0.25))
        scale_factor = float(cal.get("scale_factor", 1.0))
        vec_input = self.normalise_value(vec_input, deadzone) * scale_factor
        if any(v != 0.0 for v in vec_input):
            self._send_command(vec_input, dev_name)

    def _send_command(self, vec_input: List[float], dev_name: str) -> None:
        self.config.count_state += 1
        if self.config.count_state >= 2 and self.config.fun_array:
            if self.config.idx >= len(self.config.fun_array):
                self.config.idx = 0
            message = self.config.fun_array[self.config.idx] % (
                -vec_input[0], -vec_input[1], vec_input[2], str(self.config.idx2)
            )
            print(f"{dev_name} : {message}")
            try:
                self.sock.sendto(message.encode(), (self.udp_ip, self.udp_port))
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

    def normalise_value(self, input_pwm: List[float], deadzone: float = 0.25) -> np.ndarray:
        """Normalize and calibrate controller input to [-1, 1] range."""
        vec_input = np.array(input_pwm)
        vec_input = self._dz_calibration(vec_input, deadzone)
        return np.clip(vec_input, -1.0, 1.0)

    def _dz_calibration(self, stick_input: np.ndarray, deadzone: float) -> np.ndarray:
        """Apply deadzone calibration to stick input."""
        magnitude = np.linalg.norm(stick_input)
        if magnitude < deadzone:
            return np.zeros_like(stick_input)
        normalized = stick_input / magnitude
        scaled = normalized * ((magnitude - deadzone) / (1 - deadzone))
        return scaled

def xAxisChangeHandler(valLR: float, valUD: float, actuation: 'Actuation') -> None:
    cal = actuation.config.calibration_settings
    mapping = cal.get("axis_mapping", {})
    mapped_lr = mapping.get("x", "left_stick_lr")
    mapped_ud = mapping.get("y", "left_stick_ud")
    if mapped_lr == "left_stick_lr" and mapped_ud == "left_stick_ud":
        actuation.config.x = valLR + valUD

def yAxisChangeHandler(valLR: float, valUD: float, actuation: 'Actuation') -> None:
    cal = actuation.config.calibration_settings
    mapping = cal.get("axis_mapping", {})
    mapped_lr = mapping.get("x", "left_stick_lr")
    mapped_ud = mapping.get("y", "left_stick_ud")
    if mapped_lr == "left_stick_lr" and mapped_ud == "left_stick_ud":
        actuation.config.y = valLR + valUD

def zAxisChangeHandler(val: float, actuation: 'Actuation') -> None:
    cal = actuation.config.calibration_settings
    mapping = cal.get("axis_mapping", {})
    if mapping.get("z", "right_trigger") == "right_trigger":
        actuation.config.z = val

def changeActuationHandler(val: int, actuation: 'Actuation') -> None:
    actuation.change_actuation(val)

def subAngleHandler(val: int, actuation: 'Actuation') -> None:
    actuation.adjust_sensitivity(val)

def circleBtnHandler(val: int) -> None:
    if val == 1:
        print("No action programmed for circle button...")

def addAngleHandler(val: int) -> None:
    if val == 1:
        print("No action programmed for cross button...")
