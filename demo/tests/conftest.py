"""
Shared test configuration for LISU framework tests.
"""

import sys
from pathlib import Path
import pytest

# Add src directory to Python path
project_dir = Path(__file__).resolve().parent.parent
src_dir = project_dir / "src"
sys.path.insert(0, str(src_dir))

# Test configuration
TEST_CONFIG = {
    "device": {
        "vid": 0x046D,
        "pid": 0xB03A,
        "name": "Test Device",
        "config": {
            "axes": ["x", "y", "z"],
            "buttons": ["left", "right", "middle"],
            "type": "mouse"
        }
    },
    "transformation": {
        "linear": {
            "deadzone": 0.1,
            "scale_factor": 1.0
        },
        "non_linear": {
            "base": 2.0,
            "factor": 1.0,
            "deadzone": 0.1
        }
    },
    "logging": {
        "test_log_dir": "test_logs",
        "max_events": 1000
    },
    "optimisation": {
        "cache_size": 1000,
        "batch_size": 10,
        "window_size": 3
    }
}

@pytest.fixture
def test_config():
    """Provide test configuration to all tests."""
    return TEST_CONFIG

@pytest.fixture
def test_device():
    """Create a test device instance."""
    from LISU.devices import InputDevice
    config = TEST_CONFIG["device"]
    return InputDevice(
        vid=config["vid"],
        pid=config["pid"],
        name=config["name"],
        dev_config=config["config"]
    )

@pytest.fixture
def test_logger():
    """Create a test logger instance."""
    from LISU.logging import LisuLogger
    return LisuLogger(TEST_CONFIG["logging"]["test_log_dir"])

@pytest.fixture
def test_transformer():
    """Create a test transformation manager instance."""
    from LISU.transformation import TransformationManager
    return TransformationManager()

@pytest.fixture
def test_optimisation_manager():
    """Create a test optimisation manager instance."""
    from LISU.optimisation import OptimisationManager
    return OptimisationManager() 