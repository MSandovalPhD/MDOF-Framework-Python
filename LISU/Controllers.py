import pygame
from dataclasses import dataclass
from typing import Callable, Optional

from LISU_datasource import ListAllControllers  # Assumed dependency

@dataclass
class ControllerConfig:
    name: str
    axes: int
    buttons: int
    hats: int
    left_trigger_idx: int
    right_trigger_idx: int
    left_stick_lr_idx: int
    left_stick_ud_idx: int
    right_stick_lr_idx: int
    right_stick_ud_idx: int
    left_btn1_idx: int
    right_btn1_idx: int
    left_btn2_idx: int
    right_btn2_idx: int
    hat_left_idx: int
    hat_right_idx: int
    hat_up_idx: int
    hat_down_idx: int
    hat_idx: int
    select_btn_idx: int
    start_btn_idx: int
    triangle_btn_idx: int
    square_btn_idx: int
    circle_btn_idx: int
    cross_x_btn_idx: int

class Controllers:
    """Manages game controllers for MDOF actuation using Pygame."""
    def __init__(self, init_status: Callable[[int], None], ctr_name: str, **callbacks):
        self.supported_controllers = [ControllerConfig(**row.__dict__) for row in ListAllControllers()]
        self.init_status = init_status
        self.ctr_name = ctr_name
        self.callbacks = callbacks
        self.detected_idx = -1
        self.controller = None
        self.clock = None
        self.initialised = False
        self.left_stick_lr = 0.0
        self.left_stick_ud = 0.0
        self.right_stick_lr = 0.0
        self.right_stick_ud = 0.0
        self.left_trigger_pos = -1.0
        self.right_trigger_pos = -1.0
        self.triangle_btn_state = 0
        self.square_btn_state = 0
        self.circle_btn_state = 0
        self.cross_x_btn_state = 0
        self._initialize_pygame()

    def _initialize_pygame(self) -> None:
        """Initialize Pygame and detect supported controller."""
        try:
            pygame.init()
            pygame.joystick.init()
            for i in range(pygame.joystick.get_count()):
                joystick = pygame.joystick.Joystick(i)
                joystick.init()
                if self.ctr_name == joystick.get_name().rstrip():
                    self._validate_and_setup_controller(joystick)
                    break
            if self.controller:
                self.initialised = True
                self.clock = pygame.time.Clock()
                self.init_status(0)
            else:
                self.init_status(-1)
        except pygame.error as e:
            print(f"Pygame initialization failed: {e}")
            self.init_status(-2)

    def _validate_and_setup_controller(self, joystick) -> None:
        """Validate joystick against supported specs."""
        name = joystick.get_name().rstrip()
        for idx, config in enumerate(self.supported_controllers):
            if config.name in name and self._check_specs(joystick, config):
                self.detected_idx = idx
                self.controller = joystick
                self.dof = joystick.get_numaxes()
                self.vec_input = [0] * self.dof
                break

    def _check_specs(self, joystick, config: ControllerConfig) -> bool:
        """Check if joystick matches expected specs."""
        axes = joystick.get_numaxes()
        hats = joystick.get_numhats()
        btns = joystick.get_numbuttons()
        return (axes == config.axes and hats == config.hats and btns >= config.buttons)

    def controller_status(self) -> bool:
        """Process controller inputs and return running status."""
        if not self.initialised:
            return False

        config = self.supported_controllers[self.detected_idx]
        self._process_sticks(config)
        self._process_triggers(config)
        self._process_buttons(config)
        self.clock.tick(self.callbacks.get("FPS", 20))

        keep_running = True
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                keep_running = False
        return keep_running

    def _process_sticks(self, config: ControllerConfig) -> None:
        """Handle stick movements."""
        if "xAxisChanged" in self.callbacks and config.left_stick_lr_idx != -1:
            lr = self.controller.get_axis(config.left_stick_lr_idx)
            ud = self.controller.get_axis(config.left_stick_ud_idx)
            if lr != self.left_stick_lr or ud != self.left_stick_ud:
                self.left_stick_lr, self.left_stick_ud = lr, ud
                self.callbacks["xAxisChanged"](lr, ud)

        if "yAxisChanged" in self.callbacks and config.right_stick_lr_idx != -1:
            lr = self.controller.get_axis(config.right_stick_lr_idx)
            ud = self.controller.get_axis(config.right_stick_ud_idx)
            if lr != self.right_stick_lr or ud != self.right_stick_ud:
                self.right_stick_lr, self.right_stick_ud = lr, ud
                self.callbacks["yAxisChanged"](lr, ud)

    def _process_triggers(self, config: ControllerConfig) -> None:
        """Handle trigger movements."""
        if "zAxisChanged" in self.callbacks and config.left_trigger_idx != -1:
            pos = self.controller.get_axis(config.left_trigger_idx)
            if pos != self.left_trigger_pos:
                self.left_trigger_pos = pos
                self.callbacks["zAxisChanged"](pos)

    def _process_buttons(self, config: ControllerConfig) -> None:
        """Handle button presses."""
        for btn, key, state_attr in [
            ("triangle_btn_idx", "triangleBtnChanged", "triangle_btn_state"),
            ("square_btn_idx", "squareBtnChanged", "square_btn_state"),
            ("circle_btn_idx", "circleBtnChanged", "circle_btn_state"),
            ("cross_x_btn_idx", "crossXBtnChanged", "cross_x_btn_state")
        ]:
            idx = getattr(config, btn)
            if idx != -1 and key in self.callbacks:
                state = self.controller.get_button(idx)
                last_state = getattr(self, state_attr)
                if state != last_state:
                    setattr(self, state_attr, state)
                    self.callbacks[key](state)

def initStatus(status: int) -> None:
    """Callback for initialization status."""
    messages = {0: "Supported controller connected", -1: "No supported controller detected"}
    print(messages.get(status, f"Waiting for controller {status}"))
