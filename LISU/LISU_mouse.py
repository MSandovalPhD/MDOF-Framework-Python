"""
Move cursor with any controller using Pygame and mouse input.
"""

from threading import Thread
from time import sleep
from typing import Optional
import pygame
import mouse

# Configuration constants
VELOCITY = 0.3  # Mouse movement speed
SPF = 0.016     # Seconds per frame (refresh rate)
DEADZONE = 0.25 # Joystick deadzone threshold
SCALE = VELOCITY / SPF  # Scaling factor for movement

def mouse_action() -> None:
    """Perform a left mouse click."""
    mouse.click('left')

def move(dx: float, dy: float) -> None:
    """Move the mouse cursor by dx, dy from current position."""
    x, y = mouse.get_position()
    mouse.move(x + dx, y + dy)

class MouseWorker(Thread):
    """Thread to continuously move the mouse based on controller input."""
    def __init__(self) -> None:
        """Initialize the worker thread."""
        super().__init__()
        self.dx: float = 0.0
        self.dy: float = 0.0
        self.go_on: bool = True

    def run(self) -> None:
        """Run the thread, moving the mouse until stopped."""
        while self.go_on:
            if abs(self.dx) > DEADZONE or abs(self.dy) > DEADZONE:
                move(self.dx * SCALE, self.dy * SCALE)
            sleep(SPF)

    def stop(self) -> None:
        """Stop the worker thread."""
        self.go_on = False

if __name__ == "__main__":
    # Example usage with a simple Pygame joystick setup
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print("No joystick detected")
        exit(1)

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    worker = MouseWorker()
    worker.start()

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt
            worker.dx = joystick.get_axis(0)  # Left stick X-axis
            worker.dy = joystick.get_axis(1)  # Left stick Y-axis
            if joystick.get_button(0):        # Example: Button 0 for click
                mouse_action()
            sleep(SPF)
    except KeyboardInterrupt:
        worker.stop()
        worker.join()
        pygame.quit()
        print("Mouse control stopped")
