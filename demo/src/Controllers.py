from LISU.devices import InputDevice
from LISU.datasource import LisuOntology
from LISU.getcontrollers import LisuControllers
from Actuation import Actuation, xAxisChangeHandler, yAxisChangeHandler, zAxisChangeHandler, changeActuationHandler
from typing import Callable, Optional, Dict
from pathlib import Path

class Controllers:
    """Manages generic input devices via ontology, using dynamic configuration from JSON."""
    def __init__(self, init_status: Callable[[int], None], ctr_name: str, **callbacks):
        self.ontology = LisuOntology()
        self.devices = [
            InputDevice(vid, pid, name)
            for vid, pid, name in [
                (vid, pid, attr["name"]) for vid, pid in LisuControllers.LisuListDevices()
                for attr in self.ontology.get_device_attributes() if hex(vid) == attr["VID"] and hex(pid) == attr["PID"]
            ] if name in ctr_name
        ]
        if not self.devices:
            self.init_status(-1)
            return
        self.device = self.devices[0]
        self.device.open()
        self.callbacks = callbacks
        self.actuation = Actuation.Actuation()  # Create Actuation instance for callbacks
        self.init_status(0)
        self.state = {"x": 0.0, "y": 0.0, "z": 0.0, "buttons": [0] * len(self.device.specs["buttons"])}
        self.calibration = self.actuation.config.calibration_settings

    def controller_status(self) -> bool:
        """Process generic device input, applying dynamic calibration, and return running status."""
        if not self.device.connected:
            return False

        cal = self.calibration
        deadzone = float(cal.get("deadzone", 0.25))
        scale_factor = float(cal.get("scale_factor", 1.0))
        mapping = cal.get("axis_mapping", {})

        # Process axes with dynamic mapping and calibration
        for axis, spec in self.device.specs["axes"].items():
            mapped_axis = mapping.get(axis, axis)  # Default to axis if no mapping
            if mapped_axis in self.callbacks and axis in self.state:
                value = self.state[axis] * scale_factor if abs(self.state[axis]) > deadzone else 0.0
                if axis == "x":
                    self.callbacks[mapped_axis](value, 0)  # Simplified; adapt to actual callback
                elif axis == "y":
                    self.callbacks[mapped_axis](value, 0)
                elif axis == "z":
                    self.callbacks[mapped_axis](value)

        # Process buttons
        for idx, btn in enumerate(self.device.specs["buttons"]):
            mapped_btn = f"btn{idx+1}"
            if mapped_btn in self.callbacks:
                self.callbacks[mapped_btn](self.state["buttons"][idx])

        keep_running = True
        if not self._kbhit():
            keep_running = False
        return keep_running

    def _kbhit(self) -> bool:
        """Check for keyboard input (Windows-specific; replace for cross-platform)."""
        try:
            from msvcrt import kbhit
            return kbhit()
        except ImportError:
            return False
