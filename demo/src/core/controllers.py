from typing import Dict, List, Optional, Callable
from pathlib import Path
import json
from .dynamic_ontology import DynamicOntology
from .movement_registry import MovementRegistry, MovementType
from .udp_client import UDPClient, MovementVector, MovementCommand
from .game_configs import get_unity_game_config

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
        
        # Initialize UDP client for Unity game
        self.udp_client = UDPClient()
        
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
        # Register Unity game configuration
        unity_config = get_unity_game_config()
        self.ontology.register_game("unity_vr_game", unity_config)
        
        # Register default controllers
        self.ontology.register_controller(
            name="Bluetooth_mouse",
            vid="046d",
            pid="b03a",
            controller_type="mouse",
            library="pywinusb",
            axes=["x", "y"],
            buttons=["left_click", "right_click"],
            command="mouse",
            calibration={"deadzone": 0.1, "scale_factor": 1.0}
        )
        
        # Register movements for Unity game
        for name, movement_data in unity_config["movements"].items():
            self.ontology.movement_registry.register_movement(
                name=name,
                movement_type=MovementType(movement_data["type"]),
                parameters=movement_data["parameters"]
            )
    
    def _initialize_device(self):
        """Initialize the input device based on available controllers."""
        # Get available controllers
        available_controllers = self.ontology.list_controllers()
        if not available_controllers:
            self.init_status(-1)
            return
        
        # For now, use the first available controller
        self.controller_name = available_controllers[0]
        self.controller_config = self.ontology.get_controller_config(self.controller_name)
        
        # Initialize device state
        for axis in self.controller_config.axes:
            self.state["axes"][axis] = 0.0
        for button in self.controller_config.buttons:
            self.state["buttons"][button] = False
        
        # Connect to Unity game
        if self.game_id == "unity_vr_game":
            if not self.udp_client.connect():
                print("Warning: Failed to connect to Unity game")
        
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
        if self.game_id != "unity_vr_game":
            return
        
        # Get calibration settings
        calibration = self.controller_config.calibration
        deadzone = float(calibration.get("deadzone", 0.1))
        scale_factor = float(calibration.get("scale_factor", 1.0))
        
        # Process axes for Unity game
        if "x" in self.state["axes"]:
            x_value = self.state["axes"]["x"]
            if abs(x_value) > deadzone:
                scaled_value = x_value * scale_factor
                if scaled_value > 0:
                    self.udp_client.send_rotation(MovementVector(0, 1, 0))  # Rotate right
                else:
                    self.udp_client.send_rotation(MovementVector(0, -1, 0))  # Rotate left
        
        if "y" in self.state["axes"]:
            y_value = self.state["axes"]["y"]
            if abs(y_value) > deadzone:
                scaled_value = y_value * scale_factor
                if scaled_value > 0:
                    self.udp_client.send_movement(MovementVector(0, 0, 1))  # Forward
                else:
                    self.udp_client.send_movement(MovementVector(0, 0, -1))  # Backward
        
        # Process buttons for Unity game
        if "left_click" in self.state["buttons"] and self.state["buttons"]["left_click"]:
            self.udp_client.send_brake()
        elif "right_click" in self.state["buttons"] and self.state["buttons"]["right_click"]:
            self.udp_client.send_release()
    
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
    
    def __del__(self):
        """Cleanup when the controller is destroyed."""
        if hasattr(self, 'udp_client'):
            self.udp_client.disconnect() 