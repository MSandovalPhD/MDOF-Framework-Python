import numpy as np
import socket
import json
from typing import List, Optional
from pathlib import Path
from src.LISU.datasource import LisuOntology  # Adjust path for your structure

class ActuationConfig:
    def __init__(self):
        self.x: float = 0.0
        self.y: float = 0.0
        self.z: float = 0.0
        self.angle: float = 20.0
        self.speed: float = 120.0
        self.fps: int = 20
        self.idx: int = 0
        self.idx2: int = 1
        self.count_state: int = 0
        self.fun_array = self._load_instructions()  # Dynamic loading from ontology or JSON

    def _load_instructions(self) -> List[str]:
        """Load actuation commands dynamically from ontology or JSON configuration."""
        # Try ontology first
        try:
            ontology = LisuOntology()
            commands = ontology.get_actuation_commands()
            if commands:
                print("Loaded actuation commands from ontology")
                return commands
        except Exception as e:
            print(f"Failed to load actuation commands from ontology: {e}")

        # Fall back to JSON configuration
        config_path = Path("./data/drishti_config.json")
        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)
                    commands = config.get("actuation_commands", None)
                    if commands:
                        print("Loaded actuation commands from JSON configuration")
                        return [str(cmd) for cmd in commands]
        except Exception as e:
            print(f"Failed to load actuation commands from JSON: {e}")

        # Default fallback if both fail
        print("Using default actuation commands")
        return ["addrotation %.3f %.3f %.3f %s", "addrotationclip %.3f %.3f %.3f %s"]

class Actuation:
    """Manages controller input and actuation commands for MDOF systems."""
    def __init__(self, vec_input_controller=None):
        self.config = ActuationConfig()
        self.vec_input_controller = vec_input_controller
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_ip = "127.0.0.1"
        self.udp_port = 7755

    def __del__(self):
        self.sock.close()

    def process_input(self, vec_input: List[float], dev_name: str) -> None:
        """Process and send normalized input data."""
        vec_input = self.normalise_value(vec_input)
        if any(v != 0.0 for v in vec_input):
            self._send_command(vec_input, dev_name)

    def _send_command(self, vec_input: List[float], dev_name: str) -> None:
        """Send actuation command via UDP."""
        self.config.count_state += 1
        if self.config.count_state >= 2 and self.config.fun_array:
            if self.config.idx >= len(self.config.fun_array):
                self.config.idx = 0  # Fallback if index exceeds available commands
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
        """Handle actuation mode toggle."""
        if val == 1:
            self.config.idx = (self.config.idx + 1) % len(self.config.fun_array)
            if self.config.fun_array:
                fun_name = self.config.fun_array[self.config.idx].split(" ")[0]
                print(f"Button pressed for {fun_name}")
            else:
                print("No actuation commands available")

    def adjust_sensitivity(self, val: int) -> None:
        """Adjust sensitivity parameter."""
        if val == 1:
            self.config.idx2 += 4 if self.config.idx2 == 1 else 5
            self.config.idx2 = 1 if self.config.idx2 >= 25 else self.config.idx2
            print(f"Sensitivity set to {self.config.idx2}")

    def normalise_value(self, input_pwm: List[float], deadzone: float = 0.3) -> np.ndarray:
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

# Callback functions for external use (unchanged, but ensure they work with dynamic fun_array)
def xAxisChangeHandler(valLR: float, valUD: float, actuation: 'Actuation') -> None:
    actuation.config.x = valLR + valUD

def yAxisChangeHandler(valLR: float, valUD: float, actuation: 'Actuation') -> None:
    actuation.config.y = valLR + valUD

def zAxisChangeHandler(val: float, actuation: 'Actuation') -> None:
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
