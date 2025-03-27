import sys
from pathlib import Path

# Add the project directory to the Python path
project_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_dir))

from LISU.logging import LisuLogger
from LISU.datasource import LisuOntology
from LISU.devices import InputDevice

# Create a default logger instance
logger = LisuLogger()

__all__ = ['logger', 'LisuOntology', 'InputDevice']