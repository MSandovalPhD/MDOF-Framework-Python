from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
import json
from .movement_registry import MovementRegistry, MovementType

@dataclass
class ControllerConfig:
    name: str
    vid: str
    pid: str
    type: str
    library: str
    axes: List[str]
    buttons: List[str]
    command: str
    calibration: Dict

class DynamicOntology:
    def __init__(self):
        self.movement_registry = MovementRegistry()
        self.controller_configs: Dict[str, ControllerConfig] = {}
        self.game_configs: Dict[str, Dict] = {}
    
    def register_controller(self, name: str, vid: str, pid: str, 
                          controller_type: str, library: str,
                          axes: List[str], buttons: List[str],
                          command: str, calibration: Dict) -> None:
        """
        Register a new controller configuration.
        
        Args:
            name: Unique identifier for the controller
            vid: Vendor ID
            pid: Product ID
            controller_type: Type of controller (e.g., "gamepad", "mouse")
            library: Library to use for the controller
            axes: List of available axes
            buttons: List of available buttons
            command: Default command type
            calibration: Calibration settings
        """
        self.controller_configs[name] = ControllerConfig(
            name=name,
            vid=vid,
            pid=pid,
            type=controller_type,
            library=library,
            axes=axes,
            buttons=buttons,
            command=command,
            calibration=calibration
        )
    
    def register_game(self, game_id: str, config: Dict) -> None:
        """
        Register game-specific configuration.
        
        Args:
            game_id: Unique identifier for the game
            config: Game-specific configuration including:
                   - Available movements
                   - Controller mappings
                   - Visualization settings
        """
        self.game_configs[game_id] = config
    
    def generate_ontology(self, game_id: str, available_controllers: List[str]) -> Dict:
        """
        Generate a complete ontology configuration for a specific game and controllers.
        
        Args:
            game_id: Identifier of the game
            available_controllers: List of controller names to include
            
        Returns:
            Dict containing the complete configuration
        """
        if game_id not in self.game_configs:
            raise ValueError(f"Game {game_id} not found in registry")
        
        game_config = self.game_configs[game_id]
        controller_configs = {
            name: self.controller_configs[name]
            for name in available_controllers
            if name in self.controller_configs
        }
        
        # Generate the complete configuration
        config = {
            "game": {
                "id": game_id,
                "config": game_config
            },
            "controllers": {
                name: {
                    "vid": config.vid,
                    "pid": config.pid,
                    "type": config.type,
                    "library": config.library,
                    "axes": config.axes,
                    "buttons": config.buttons,
                    "command": config.command,
                    "calibration": config.calibration
                }
                for name, config in controller_configs.items()
            },
            "movements": {
                name: {
                    "type": movement.type.value,
                    "parameters": movement.parameters,
                    "conditions": movement.conditions
                }
                for name, movement in self.movement_registry.available_movements.items()
            },
            "patterns": self.movement_registry.movement_patterns
        }
        
        return config
    
    def save_ontology(self, config: Dict, output_path: Path) -> None:
        """
        Save the generated ontology to a file.
        
        Args:
            config: The configuration to save
            output_path: Path where to save the configuration
        """
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=4)
    
    def load_ontology(self, input_path: Path) -> Dict:
        """
        Load an ontology configuration from a file.
        
        Args:
            input_path: Path to the configuration file
            
        Returns:
            Dict containing the loaded configuration
        """
        with open(input_path, 'r') as f:
            return json.load(f)
    
    def get_controller_config(self, name: str) -> Optional[ControllerConfig]:
        """Retrieve a controller configuration by name."""
        return self.controller_configs.get(name)
    
    def get_game_config(self, game_id: str) -> Optional[Dict]:
        """Retrieve a game configuration by ID."""
        return self.game_configs.get(game_id)
    
    def list_controllers(self) -> List[str]:
        """List all registered controller names."""
        return list(self.controller_configs.keys())
    
    def list_games(self) -> List[str]:
        """List all registered game IDs."""
        return list(self.game_configs.keys()) 