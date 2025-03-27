"""
Test runner script for LISU framework tests.
"""

import pytest
import sys
from pathlib import Path

def run_tests():
    """Run all tests in the test suite."""
    # Get the tests directory
    tests_dir = Path(__file__).resolve().parent
    
    # Run pytest with coverage
    pytest_args = [
        "--verbose",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html",
        str(tests_dir)
    ]
    
    # Run the tests
    sys.exit(pytest.main(pytest_args))

if __name__ == "__main__":
    run_tests() 