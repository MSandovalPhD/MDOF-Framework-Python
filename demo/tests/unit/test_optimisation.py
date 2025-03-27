"""
Test cases for LISU performance optimization.
"""

import unittest
from unittest.mock import Mock, patch
import time
from LISU.optimisation import (
    PerformanceMetrics,
    PerformanceMonitor,
    TransformationCache,
    OptimisedState,
    EventBatcher,
    OptimisationManager
)

class TestPerformanceOptimisation(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.optimisation_manager = OptimisationManager()

    def test_performance_monitor(self):
        """Test performance monitoring functionality."""
        # Test measurement
        with self.optimisation_manager.monitor.measure("test_operation"):
            time.sleep(0.1)  # Simulate work
        
        metrics = self.optimisation_manager.monitor.get_metrics()
        self.assertIn("test_operation", metrics)
        self.assertGreater(metrics["test_operation"]["mean"], 0)
        self.assertGreater(metrics["test_operation"]["max"], 0)

    def test_transformation_cache(self):
        """Test transformation caching."""
        # Test cache hit
        self.optimisation_manager.cache.set("test_key", 0.5)
        value = self.optimisation_manager.cache.get("test_key")
        self.assertEqual(value, 0.5)
        
        # Test cache miss
        value = self.optimisation_manager.cache.get("nonexistent")
        self.assertIsNone(value)
        
        # Test cache clear
        self.optimisation_manager.cache.clear()
        value = self.optimisation_manager.cache.get("test_key")
        self.assertIsNone(value)

    def test_optimised_state(self):
        """Test optimized state management."""
        # Test state update
        changed = self.optimisation_manager.state.update({
            "x": 0.5,
            "y": 0.3
        })
        self.assertEqual(changed, {"x", "y"})
        
        # Test unchanged values
        changed = self.optimisation_manager.state.update({
            "x": 0.5,
            "y": 0.3
        })
        self.assertEqual(changed, set())
        
        # Test value retrieval
        self.assertEqual(self.optimisation_manager.state.get("x"), 0.5)
        self.assertEqual(self.optimisation_manager.state.get("y"), 0.3)
        self.assertIsNone(self.optimisation_manager.state.get("z"))

    def test_event_batcher(self):
        """Test event batching functionality."""
        # Test event addition
        self.optimisation_manager.batcher.add({"type": "test", "value": 1})
        self.assertEqual(len(self.optimisation_manager.batcher.pending), 1)
        
        # Test batch processing
        batch = self.optimisation_manager.batcher.add({"type": "test", "value": 2})
        self.assertEqual(len(batch), 2)
        self.assertEqual(len(self.optimisation_manager.batcher.pending), 0)
        
        # Test batch clearing
        self.optimisation_manager.batcher.add({"type": "test", "value": 3})
        self.optimisation_manager.batcher.clear()
        self.assertEqual(len(self.optimisation_manager.batcher.pending), 0)

    def test_optimisation_manager(self):
        """Test overall optimization manager."""
        # Test state processing
        with self.optimisation_manager.monitor.measure("state_processing"):
            changed = self.optimisation_manager.state.update({
                "x": 0.5,
                "y": 0.3
            })
        
        # Test transformation caching
        with self.optimisation_manager.monitor.measure("transformation"):
            self.optimisation_manager.cache.set("test_transform", 0.75)
            value = self.optimisation_manager.cache.get("test_transform")
        
        # Test event batching
        with self.optimisation_manager.monitor.measure("event_processing"):
            batch = self.optimisation_manager.batcher.add({
                "type": "test",
                "value": 1
            })
        
        # Verify metrics
        metrics = self.optimisation_manager.monitor.get_metrics()
        self.assertIn("state_processing", metrics)
        self.assertIn("transformation", metrics)
        self.assertIn("event_processing", metrics)

    def test_performance_metrics(self):
        """Test performance metrics dataclass."""
        metrics = PerformanceMetrics(
            transformation_time={"mean": 0.1, "max": 0.2},
            event_processing_time={"mean": 0.05, "max": 0.1},
            state_update_time={"mean": 0.01, "max": 0.02},
            command_send_time={"mean": 0.03, "max": 0.06},
            cache_hits=10,
            cache_misses=2,
            events_processed=100,
            state_updates=50
        )
        
        self.assertEqual(metrics.transformation_time["mean"], 0.1)
        self.assertEqual(metrics.event_processing_time["max"], 0.1)
        self.assertEqual(metrics.cache_hits, 10)
        self.assertEqual(metrics.state_updates, 50)

if __name__ == '__main__':
    unittest.main() 