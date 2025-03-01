# Multiple Degrees-Of-Freedom Input Devices for Interactive Command and Control within Virtual Reality in Industrial Visualisations

LISU (Layered Interaction System for User-Modes) is a framework developed for managing the raw input data from heterogeneous input devices. LISU offers a solution for VR (Virtual Reality) developers, creators, and designers to resolve interoperability and compatibility issues in VR applications caused by the heterogeneity of input controllers by unifying the roles of multiple code segments and APIs for input management.

## Features

- Controller management for gamepads and 3D input devices (e.g., PS4, SpaceMouse).
- Actuation logic for MDOF system interaction via UDP.
- Parallel processing of multiple input devices.
- Integration with VRPN for networked device communication.
- Ontology-based device configuration using RDF (`idoo.owl`).
- Comprehensive testing and profiling tools.

## Installation

### Prerequisites

- Python 3.7 or higher
- Windows (for `pywinusb` and VRPN executables)

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/MSandovalPhD/MDOF-Framework-Python.git
   cd MDOF-Framework-Python
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure the VRPN executables (`vrpnLisu_device_0.exe`, `vrpnLisu_device_1.exe`) are in the `demo/bin/` directory.

4. Verify the ontology file (`idoo.owl`) is in the `demo/data/` directory.

## Usage

### Running the Framework

1. Navigate to the `demo/` directory:
   ```bash
   cd demo
   ```

2. Run test scripts from the `tests/` directory to activate controllers or test functionality:
   ```bash
   python tests/test_lisufeatures.py    # Test this framewrok features   
   ```

3. Use the main LISU module for custom device activation:
   ```python
   from lisu import LisuManager
   lisu = LisuManager()
   lisu.start_gamepad(0x054c, 0x09cc)  # Example for PS4 controller (VID/PID)
   ```

### Profiling

Each test script generates profiling stats in `demo/logs/Profiler_<ScriptName>_<Timestamp>.txt`. Review these files for performance insights.

## Directory Structure

```
MDOF-Framework-Python/
├── demo/                       # Main project directory
│   ├── bin/                    # VRPN executables
│   │   ├── vrpnLisu_device_0.exe
│   │   └── vrpnLisu_device_1.exe
│   ├── data/                   # Data files (e.g., ontology)
│   │   └── idoo.owl
│   ├── logs/                   # Log and profiler output (generated at runtime)
│   ├── src/                    # Source code
│   │   ├── __init__.py
│   │   ├── actuation.py
│   │   ├── controllers.py
│   │   ├── lisu/               # LISU-specific modules
│   │   │   ├── __init__.py
│   │   │   ├── datalogging.py
│   │   │   ├── datasource.py
│   │   │   ├── devices.py
│   │   │   ├── getcontrollers.py
│   │   │   └── mouse.py
│   │   └── lisu.py
│   ├── tests/                  # Test scripts
│   │   ├── __init__.py
│   │   ├── test_lisufeatures.py
├── requirements.txt            # Project dependencies
└── setup.py                    # Setup script for packaging/distribution
└── README.md                   # Project overview
```

## Dependencies

List of required Python packages (see `requirements.txt`):
- `pywinusb` (for HID device handling)
- `pygame` (for gamepad input)
- `mouse` (for mouse control)
- `rdflib` (for ontology parsing)
- `qprompt` (for interactive menus)

## License

MIT License (specify if applicable, or update with your preferred license).

## Contributing

Contributions are welcome! Please fork the repository, make changes, and submit pull requests. For major changes, please open an issue first to discuss.

## Contact

Mario Sandoval - mariosandovalac@gmail.com

Project Link: [MDOF-Framework-Python](https://github.com/MSandovalPhD/MDOF-Framework-Python)

All related research papers can be found on [Mario Sandoval Olivé's Academia.edu page](https://manchester.academia.edu/MarioSandovalOliv%C3%A9).

### Note

LISU is a research project of the University of Manchester. Any unauthorised use or claim of this work will be considered a violation of intellectual property rights.
