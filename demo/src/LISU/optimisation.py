"""
LISU Framework Optimisation Module
Provides performance optimisations for input processing and state management.
"""

import time
from typing import Dict, List, Optional, Callable, Set, Any
from collections import deque
import numpy as np
from dataclasses import dataclass
import threading
from queue import Queue
import weakref

@dataclass
class PerformanceMetrics:
    """Stores performance metrics for monitoring."""
    transformation_time: List[float] = None
    event_processing_time: List[float] = None
    state_update_time: List[float] = None
    command_send_time: List[float] = None
    cache_hits: int = 0
    cache_misses: int = 0
    events_processed: int = 0
    state_updates: int = 0
    
    def __post_init__(self):
        """Initialise metric lists."""
        self.transformation_time = []
        self.event_processing_time = []
        self.state_update_time = []
        self.command_send_time = []

class PerformanceMonitor:
    """Monitors and measures performance metrics."""
    
    def __init__(self):
        """Initialise the performance monitor."""
        self.metrics = PerformanceMetrics()
        self._lock = threading.Lock()
        
    def measure(self, operation: str, func: Callable) -> Any:
        """
        Measure execution time of a function.
        
        Args:
            operation: Name of the operation being measured
            func: Function to measure
            
        Returns:
            Result of the function execution
        """
        start_time = time.time()
        result = func()
        duration = time.time() - start_time
        
        with self._lock:
            if hasattr(self.metrics, operation):
                getattr(self.metrics, operation).append(duration)
                
        return result
        
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        with self._lock:
            return {
                "transformation_time": {
                    "mean": np.mean(self.metrics.transformation_time) if self.metrics.transformation_time else 0,
                    "max": max(self.metrics.transformation_time) if self.metrics.transformation_time else 0
                },
                "event_processing_time": {
                    "mean": np.mean(self.metrics.event_processing_time) if self.metrics.event_processing_time else 0,
                    "max": max(self.metrics.event_processing_time) if self.metrics.event_processing_time else 0
                },
                "state_update_time": {
                    "mean": np.mean(self.metrics.state_update_time) if self.metrics.state_update_time else 0,
                    "max": max(self.metrics.state_update_time) if self.metrics.state_update_time else 0
                },
                "command_send_time": {
                    "mean": np.mean(self.metrics.command_send_time) if self.metrics.command_send_time else 0,
                    "max": max(self.metrics.command_send_time) if self.metrics.command_send_time else 0
                },
                "cache_hits": self.metrics.cache_hits,
                "cache_misses": self.metrics.cache_misses,
                "events_processed": self.metrics.events_processed,
                "state_updates": self.metrics.state_updates
            }

class TransformationCache:
    """Caches transformation results for improved performance."""
    
    def __init__(self, max_size: int = 1000):
        """
        Initialise the transformation cache.
        
        Args:
            max_size: Maximum number of cached transformations
        """
        self.cache = {}
        self.max_size = max_size
        self._lock = threading.Lock()
        
    def get(self, key: str) -> Optional[float]:
        """
        Get a cached transformation result.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        with self._lock:
            return self.cache.get(key)
            
    def set(self, key: str, value: float):
        """
        Set a transformation result in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            if len(self.cache) >= self.max_size:
                self.cache.pop(next(iter(self.cache)))
            self.cache[key] = value
            
    def clear(self):
        """Clear the cache."""
        with self._lock:
            self.cache.clear()

class OptimisedState:
    """Manages device state with optimised updates."""
    
    def __init__(self):
        """Initialise the optimised state manager."""
        self.current = {}
        self.previous = {}
        self.changed = set()
        self._lock = threading.Lock()
        
    def update(self, new_state: Dict[str, Any]) -> Set[str]:
        """
        Update the current state and track changes.
        
        Args:
            new_state: New state values
            
        Returns:
            Set of changed keys
        """
        with self._lock:
            self.previous = self.current.copy()
            self.current = new_state
            self.changed = {
                k for k, v in new_state.items()
                if k not in self.previous or v != self.previous[k]
            }
            return self.changed
            
    def get_changed(self) -> Set[str]:
        """
        Get the set of changed keys.
        
        Returns:
            Set of changed keys
        """
        with self._lock:
            return self.changed.copy()
            
    def get_value(self, key: str) -> Optional[Any]:
        """
        Get a state value.
        
        Args:
            key: State key
            
        Returns:
            State value or None if not found
        """
        with self._lock:
            return self.current.get(key)
            
    def clear(self):
        """Clear all state data."""
        with self._lock:
            self.current.clear()
            self.previous.clear()
            self.changed.clear()

class EventBatcher:
    """Batches events for efficient processing."""
    
    def __init__(self, batch_size: int = 100, max_delay: float = 0.01):
        """
        Initialise the event batcher.
        
        Args:
            batch_size: Maximum number of events per batch
            max_delay: Maximum delay between batch processing
        """
        self.batch_size = batch_size
        self.max_delay = max_delay
        self.events = []
        self.last_process_time = time.time()
        self._lock = threading.Lock()
        
    def add(self, event: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Add an event to the batch.
        
        Args:
            event: Event to add
            
        Returns:
            Batch of events if batch is full or max delay reached
        """
        with self._lock:
            self.events.append(event)
            current_time = time.time()
            
            if (len(self.events) >= self.batch_size or
                current_time - self.last_process_time >= self.max_delay):
                return self.process_batch()
            return None
            
    def process_batch(self) -> List[Dict[str, Any]]:
        """
        Process the current batch of events.
        
        Returns:
            List of events in the batch
        """
        with self._lock:
            batch = self.events
            self.events = []
            self.last_process_time = time.time()
            return batch
            
    def clear(self):
        """Clear all pending events."""
        with self._lock:
            self.events.clear()
            self.last_process_time = time.time()

class OptimisationManager:
    """Manages all performance optimisations."""
    
    def __init__(self):
        """Initialise the optimisation manager."""
        self.monitor = PerformanceMonitor()
        self.cache = TransformationCache()
        self.state = OptimisedState()
        self.batcher = EventBatcher()
        
    def cleanup(self):
        """Clean up all optimisation resources."""
        self.cache.clear()
        self.state.clear()
        self.batcher.clear() 