import sys
from pathlib import Path

# Add the project directory to the Python path
project_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_dir))

from threading import Thread
from time import sleep
from typing import Optional
import mouse
from LISU.devices import InputDevice

VELOCITY = 0.3
SPF = 0.016
DEADZONE = 0.25
SCALE = VELOCITY / SPF

def mouse_action() -> None:
    mouse.click('left')

def move(dx: float, dy: float) -> None:
    x, y = mouse.get_position()
    mouse.move(x + dx, y + dy)

class MouseWorker(Thread):
    def __init__(self, input_device: Optional['InputDevice'] = None) -> None:
        super().__init__()
        self.dx: float = 0.0
        self.dy: float = 0.0
        self.go_on: bool = True
        self.device = input_device

    def run(self) -> None:
        while self.go_on:
            if self.device:
                dx = self.device.state.get("x", 0.0)
                dy = self.device.state.get("y", 0.0)
                if abs(dx) > DEADZONE or abs(dy) > DEADZONE:
                    move(dx * SCALE, dy * SCALE)
            else:
                if abs(self.dx) > DEADZONE or abs(self.dy) > DEADZONE:
                    move(self.dx * SCALE, self.dy * SCALE)
            sleep(SPF)

    def stop(self) -> None:
        self.go_on = False

    def update_input(self, dx: float, dy: float) -> None:
        self.dx = dx
        self.dy = dy
