import sys
from pathlib import Path

# Ensure project root is in sys.path (reinforces src/__init__.py)
project_dir = Path(__file__).resolve().parent.parent.parent  # MDOF-Framework-Python/
sys.path.insert(0, str(project_dir))

# Optional: Import test utilities or leave empty
__all__ = []