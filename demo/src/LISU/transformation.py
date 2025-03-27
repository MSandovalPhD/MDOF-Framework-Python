"""
Transformation Manager Module
Handles input transformations and mappings for the LISU framework.
"""

from typing import Dict, List, Optional, Tuple
from LISU.logging import LisuLogger
import time

class TransformationManager:
    """
    Manages input transformations and mappings for the LISU framework.
    
    This class handles:
    - Input axis transformations (scaling, deadzone, etc.)
    - Button mappings
    - Command transformations
    - Calibration adjustments
    """
    
    def __init__(self):
        """Initialize the Transformation Manager with logging."""
        self.logger = LisuLogger()
        self.transformations: Dict[str, Dict] = {}
        self.calibrations: Dict[str, Dict] = {}
        self.history: List[Dict] = []  # Add history tracking
    
    def add_transformation(self, device_id: str, transformation: Dict) -> None:
        """
        Add a transformation configuration for a device.
        
        Args:
            device_id: Unique identifier for the device
            transformation: Dictionary containing transformation settings
        """
        self.transformations[device_id] = transformation
        self.logger.log_event("transformation_added", {
            "device_id": device_id,
            "transformation": transformation
        })
    
    def add_calibration(self, device_id: str, calibration: Dict) -> None:
        """
        Add calibration settings for a device.
        
        Args:
            device_id: Unique identifier for the device
            calibration: Dictionary containing calibration settings
        """
        self.calibrations[device_id] = calibration
        self.logger.log_event("calibration_added", {
            "device_id": device_id,
            "calibration": calibration
        })
    
    def clear_history(self):
        """Clear the transformation history."""
        self.history = []
    
    def transform_axis(self, device_id: str, axis: str, value: float) -> float:
        """
        Apply transformations to an axis value.
        
        Args:
            device_id: Unique identifier for the device
            axis: Name of the axis to transform
            value: Raw axis value
            
        Returns:
            Transformed axis value
        """
        if device_id not in self.transformations:
            return value
            
        transform = self.transformations[device_id]
        if axis not in transform:
            return value
            
        # Apply deadzone
        deadzone = transform[axis].get("deadzone", 0.0)
        if abs(value) < deadzone:
            return 0.0
            
        # Apply scaling
        scale = transform[axis].get("scale", 1.0)
        transformed_value = value * scale
        
        # Record in history
        self.history.append({
            "timestamp": time.time(),
            "device_id": device_id,
            "axis": axis,
            "input_value": value,
            "output_value": transformed_value
        })
        
        return transformed_value
    
    def get_button_mapping(self, device_id: str) -> Dict[str, str]:
        """
        Get button mappings for a device.
        
        Args:
            device_id: Unique identifier for the device
            
        Returns:
            Dictionary mapping button names to commands
        """
        if device_id not in self.transformations:
            return {}
            
        return self.transformations[device_id].get("buttons", {})
    
    def get_calibration(self, device_id: str) -> Dict:
        """
        Get calibration settings for a device.
        
        Args:
            device_id: Unique identifier for the device
            
        Returns:
            Dictionary containing calibration settings
        """
        return self.calibrations.get(device_id, {})
    
    def remove_device(self, device_id: str) -> None:
        """
        Remove all transformations and calibrations for a device.
        
        Args:
            device_id: Unique identifier for the device
        """
        if device_id in self.transformations:
            del self.transformations[device_id]
        if device_id in self.calibrations:
            del self.calibrations[device_id]
        self.logger.log_event("device_removed", {"device_id": device_id}) 