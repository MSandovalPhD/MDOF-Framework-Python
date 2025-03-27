from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class MovementType(Enum):
    ROTATION = "rotation"
    TRANSLATION = "translation"
    SCALE = "scale"
    CUSTOM = "custom"

@dataclass
class Movement:
    name: str
    type: MovementType
    parameters: Dict
    conditions: Optional[Dict] = None

class MovementRegistry:
    def __init__(self):
        self.available_movements: Dict[str, Movement] = {}
        self.movement_patterns: Dict[str, List[str]] = {}
    
    def register_movement(self, name: str, movement_type: MovementType, 
                         parameters: Dict, conditions: Optional[Dict] = None) -> None:
        """
        Register a new movement type with its parameters and conditions.
        
        Args:
            name: Unique identifier for the movement
            movement_type: Type of movement (from MovementType enum)
            parameters: Dictionary of parameters required for the movement
            conditions: Optional conditions that must be met for the movement
        """
        self.available_movements[name] = Movement(
            name=name,
            type=movement_type,
            parameters=parameters,
            conditions=conditions
        )
    
    def register_pattern(self, name: str, movements: List[str], 
                        conditions: Optional[Dict] = None) -> None:
        """
        Register a pattern of movements that can be executed together.
        
        Args:
            name: Unique identifier for the pattern
            movements: List of movement names that form the pattern
            conditions: Optional conditions for the pattern execution
        """
        # Validate that all movements exist
        for movement in movements:
            if movement not in self.available_movements:
                raise ValueError(f"Movement {movement} not found in registry")
        
        self.movement_patterns[name] = {
            'movements': movements,
            'conditions': conditions
        }
    
    def get_movement(self, name: str) -> Optional[Movement]:
        """Retrieve a movement by name."""
        return self.available_movements.get(name)
    
    def get_pattern(self, name: str) -> Optional[Dict]:
        """Retrieve a movement pattern by name."""
        return self.movement_patterns.get(name)
    
    def list_available_movements(self) -> List[str]:
        """List all registered movement names."""
        return list(self.available_movements.keys())
    
    def list_patterns(self) -> List[str]:
        """List all registered pattern names."""
        return list(self.movement_patterns.keys())
    
    def remove_movement(self, name: str) -> None:
        """Remove a movement and its associated patterns."""
        if name in self.available_movements:
            del self.available_movements[name]
            # Remove patterns that use this movement
            self.movement_patterns = {
                pattern_name: pattern_data
                for pattern_name, pattern_data in self.movement_patterns.items()
                if name not in pattern_data['movements']
            }
    
    def remove_pattern(self, name: str) -> None:
        """Remove a movement pattern."""
        if name in self.movement_patterns:
            del self.movement_patterns[name] 