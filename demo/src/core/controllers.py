from typing import Dict, List, Optional, Callable
from pathlib import Path
import json
from .dynamic_ontology import DynamicOntology
from .movement_registry import MovementRegistry, MovementType

class Controllers:
    """Manages input devices using dynamic configuration from the ontology system."""
    
    def __init__(self, game_id: str, init_status: Callable[[int], None], **callbacks):
        """
        Initialize the Controllers system.
        
        Args:
            game_id: Identifier of the game being used
            init_status: Callback function for initialization status
            **callbacks: Additional callbacks for different events
        """
        self.ontology = DynamicOntology()
        self.game_id = game_id
        self.callbacks = callbacks
        self.init_status = init_status
        
        # Load default configurations
        self._load_default_configs()
        
        # Initialize device state
        self.state = {
            "axes": {},
            "buttons": {},
            "patterns": {}
        }
        
        # Initialize device
        self._initialize_device()
    
    def _load_default_configs(self):
        """Load default controller and game configurations."""
        # Register default controllers
        self.ontology.register_controller(
            name="Bluetooth_mouse",
            vid="046d",
            pid="b03a",
            controller_type="mouse",
            library="pywinusb",
            axes=["x"],
            buttons=["left_click", "right_click"],
            command="mouse",
            calibration={"deadzone": 0.1, "scale_factor": 1.0}
        )
        
        self.ontology.register_controller(
            name="PS4_Controller",
            vid="054c",
            pid="09cc",
            controller_type="gamepad",
            library="pywinusb",
            axes=["x", "y", "z"],
            buttons=["btn1", "btn2"],
            command="default",
            calibration={"deadzone": 0.1, "scale_factor": 1.0}
        )
        
        # Register default movements
        self.ontology.movement_registry.register_movement(
            name="rotate_x",
            movement_type=MovementType.ROTATION,
            parameters={"axis": "x", "speed": 1.0}
        )
        
        self.ontology.movement_registry.register_movement(
            name="rotate_y",
            movement_type=MovementType.ROTATION,
            parameters={"axis": "y", "speed": 1.0}
        )
        
        self.ontology.movement_registry.register_movement(
            name="rotate_z",
            movement_type=MovementType.ROTATION,
            parameters={"axis": "z", "speed": 1.0}
        )
    
    def _initialize_device(self):
        """Initialize the input device based on available controllers."""
        # Get available controllers
        available_controllers = self.ontology.list_controllers()
        if not available_controllers:
            self.init_status(-1)
            return
        
        # For now, use the first available controller
        # In a real implementation, you would want to let the user choose
        self.controller_name = available_controllers[0]
        self.controller_config = self.ontology.get_controller_config(self.controller_name)
        
        # Initialize device state
        for axis in self.controller_config.axes:
            self.state["axes"][axis] = 0.0
        for button in self.controller_config.buttons:
            self.state["buttons"][button] = False
        
        self.init_status(0)
    
    def update_state(self, new_state: Dict):
        """
        Update the current state of the controller.
        
        Args:
            new_state: Dictionary containing new state values
        """
        # Update axes
        if "axes" in new_state:
            for axis, value in new_state["axes"].items():
                if axis in self.state["axes"]:
                    self.state["axes"][axis] = value
        
        # Update buttons
        if "buttons" in new_state:
            for button, value in new_state["buttons"].items():
                if button in self.state["buttons"]:
                    self.state["buttons"][button] = value
        
        # Process the new state
        self._process_state()
    
    def _process_state(self):
        """Process the current state and trigger appropriate callbacks."""
        # Get calibration settings
        calibration = self.controller_config.calibration
        deadzone = float(calibration.get("deadzone", 0.1))
        scale_factor = float(calibration.get("scale_factor", 1.0))
        
        # Process axes
        for axis, value in self.state["axes"].items():
            if abs(value) > deadzone:
                scaled_value = value * scale_factor
                if axis in self.callbacks:
                    self.callbacks[axis](scaled_value)
        
        # Process buttons
        for button, value in self.state["buttons"].items():
            if value and button in self.callbacks:
                self.callbacks[button]()
    
    def register_movement(self, name: str, movement_type: MovementType,
                         parameters: Dict, conditions: Optional[Dict] = None):
        """
        Register a new movement type.
        
        Args:
            name: Unique identifier for the movement
            movement_type: Type of movement
            parameters: Movement parameters
            conditions: Optional conditions for the movement
        """
        self.ontology.movement_registry.register_movement(
            name=name,
            movement_type=movement_type,
            parameters=parameters,
            conditions=conditions
        )
    
    def register_pattern(self, name: str, movements: List[str],
                        conditions: Optional[Dict] = None):
        """
        Register a new movement pattern.
        
        Args:
            name: Unique identifier for the pattern
            movements: List of movement names
            conditions: Optional conditions for the pattern
        """
        self.ontology.movement_registry.register_pattern(
            name=name,
            movements=movements,
            conditions=conditions
        )
    
    def get_current_config(self) -> Dict:
        """Get the current configuration for the game and controller."""
        return self.ontology.generate_ontology(
            self.game_id,
            [self.controller_name]
        )
    
    def save_config(self, output_path: Path):
        """
        Save the current configuration to a file.
        
        Args:
            output_path: Path where to save the configuration
        """
        config = self.get_current_config()
        self.ontology.save_ontology(config, output_path)
    
    def load_config(self, input_path: Path):
        """
        Load a configuration from a file.
        
        Args:
            input_path: Path to the configuration file
        """
        config = self.ontology.load_ontology(input_path)
        # Update the current configuration
        self._update_from_config(config)
    
    def _update_from_config(self, config: Dict):
        """Update the current state from a loaded configuration."""
        # Update controller configuration
        if "controllers" in config and self.controller_name in config["controllers"]:
            controller_config = config["controllers"][self.controller_name]
            self.controller_config = self.ontology.get_controller_config(self.controller_name)
        
        # Update movement registry
        if "movements" in config:
            for name, movement_data in config["movements"].items():
                self.ontology.movement_registry.register_movement(
                    name=name,
                    movement_type=MovementType(movement_data["type"]),
                    parameters=movement_data["parameters"],
                    conditions=movement_data.get("conditions")
                )
        
        # Update patterns
        if "patterns" in config:
            for name, pattern_data in config["patterns"].items():
                self.ontology.movement_registry.register_pattern(
                    name=name,
                    movements=pattern_data["movements"],
                    conditions=pattern_data.get("conditions")
                ) 