"""
Test cases for LISU input transformations.
"""

import unittest
from unittest.mock import Mock, patch
import numpy as np
from LISU.transformation import TransformationManager

class TestTransformationManager(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.transformer = TransformationManager()

    def test_linear_transformations(self):
        """Test linear transformation functions."""
        # Test direct transformation
        config = {"deadzone": 0.1, "scale_factor": 1.0}
        self.assertEqual(self.transformer._direct_transform(0.5, config), 0.5)
        self.assertEqual(self.transformer._direct_transform(0.05, config), 0.0)  # Below deadzone
        
        # Test scaled transformation
        config = {
            "input_min": -1.0,
            "input_max": 1.0,
            "output_min": 0.0,
            "output_max": 100.0
        }
        self.assertEqual(self.transformer._scaled_transform(0.0, config), 50.0)
        self.assertEqual(self.transformer._scaled_transform(-1.0, config), 0.0)
        self.assertEqual(self.transformer._scaled_transform(1.0, config), 100.0)
        
        # Test normalized transformation
        config = {"deadzone": 0.1}
        self.assertEqual(self.transformer._normalised_transform(0.5, config), 0.5)
        self.assertEqual(self.transformer._normalised_transform(0.05, config), 0.0)  # Below deadzone
        self.assertEqual(self.transformer._normalised_transform(2.0, config), 1.0)  # Clamped

    def test_non_linear_transformations(self):
        """Test non-linear transformation functions."""
        # Test exponential transformation
        config = {"base": 2.0, "factor": 1.0, "deadzone": 0.1}
        self.assertGreater(self.transformer._exponential_transform(0.5, config), 0.5)
        self.assertEqual(self.transformer._exponential_transform(0.05, config), 0.0)  # Below deadzone
        
        # Test smoothed transformation
        config = {"device_id": "test", "window_size": 3}
        values = [0.0, 0.5, 1.0]
        for value in values:
            self.transformer._smoothed_transform(value, config)
        self.assertLess(self.transformer._smoothed_transform(0.0, config), 1.0)  # Should be smoothed
        
        # Test threshold transformation
        config = {"threshold": 0.5, "high_value": 1.0, "low_value": 0.0}
        self.assertEqual(self.transformer._threshold_transform(0.6, config), 1.0)
        self.assertEqual(self.transformer._threshold_transform(0.4, config), 0.0)
        
        # Test adaptive transformation
        config = {"device_id": "test", "sensitivity": 1.0}
        self.transformer._adaptive_transform(0.5, config)  # Initial value
        self.assertGreater(self.transformer._adaptive_transform(1.0, config), 1.0)  # Should adapt to velocity

    def test_transform_input(self):
        """Test the main transform_input function."""
        # Test linear transformation
        result = self.transformer.transform_input(0.5, "direct", {"deadzone": 0.1})
        self.assertEqual(result, 0.5)
        
        # Test non-linear transformation
        result = self.transformer.transform_input(0.5, "exponential", {"base": 2.0, "factor": 1.0})
        self.assertGreater(result, 0.5)
        
        # Test unknown transformation type
        result = self.transformer.transform_input(0.5, "unknown", {})
        self.assertEqual(result, 0.5)  # Should fall back to direct transformation

    def test_batch_transform(self):
        """Test batch transformation of multiple values."""
        values = [0.0, 0.5, 1.0]
        config = {"deadzone": 0.1, "scale_factor": 1.0}
        
        # Test linear transformation
        results = self.transformer.batch_transform(values, "direct", config)
        self.assertEqual(len(results), len(values))
        self.assertEqual(results, values)
        
        # Test non-linear transformation
        results = self.transformer.batch_transform(values, "exponential", {"base": 2.0, "factor": 1.0})
        self.assertEqual(len(results), len(values))
        self.assertTrue(all(r > v for r, v in zip(results, values)))

    def test_history_management(self):
        """Test input history management."""
        # Test history initialization
        self.transformer._smoothed_transform(0.5, {"device_id": "test", "window_size": 3})
        self.assertIn("test", self.transformer.input_history)
        
        # Test history clearing
        self.transformer.clear_history("test")
        self.assertNotIn("test", self.transformer.input_history)
        
        # Test clearing all history
        self.transformer._smoothed_transform(0.5, {"device_id": "test2", "window_size": 3})
        self.transformer.clear_history()
        self.assertEqual(len(self.transformer.input_history), 0)

if __name__ == '__main__':
    unittest.main() 