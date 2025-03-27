"""
LISU Framework Handler Module
Core handler for the LISU framework, managing device input, transformations, and visualisation.
"""

import Actuation
from LISU.devices import InputDevice
import pywinusb.hid as hid
import qprompt
from typing import List, Tuple, Optional, Dict, Any
import json
from pathlib import Path
import threading
import signal
import sys
import msvcrt
from LISU.logging import LisuLogger
from LISU.optimisation import OptimisationManager
import time
from LISU.transformation import TransformationManager
from LISU.device_manager import DeviceManager
from LISU.device_config import configure_new_device
import pygame

class LisuManager:
    """
    Manages the LISU framework's core functionality.
    
    This class implements the Device Layer of the LISU framework, handling:
    - Input device detection and configuration
    - Visualisation selection and management
    - Device state processing and command mapping
    - Calibration and button mapping
    
    The framework supports:
    - Multiple input devices (mice, gamepads, VR controllers)
    - Various visualisation options (3D viewers, VR applications)
    - Linear and non-linear input transformations
    - Dynamic device mapping and calibration
    - Performance optimisations for input processing
    """
    
    def __init__(self):
        """Initialise the LISU Manager with logging and core components."""
        # Set up logging
        self.logger = LisuLogger()
        self.logger.log_event("framework_started", {"version": "1.0.0"})
        
        # Initialise core components
        self.config = self._load_config()
        self.running = threading.Event()
        self.running.set()
        self.current_visualisation = None
        self.dev_name = None
        self.transformation_manager = TransformationManager()
        self.optimisation_manager = OptimisationManager()
        self.use_axis = "x"
        self.button_mappings = {}
        self.speed_factor = 1.0
        
        # Load configuration
        config_path = Path(__file__).parent / "data" / "visualisation_config.json"
        self.logger.log_event("loading_config", {"path": str(config_path)})
        self.config = self._load_config(config_path)
        
        # Initialise visualisation and actuation
        self.selected_visualisation = self.select_visualisation()
        self.actuation = Actuation.Actuation(selected_visualisation=self.selected_visualisation)
        
        # Set up signal handling
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Start keyboard monitoring thread
        self.keyboard_thread = threading.Thread(target=self._monitor_keyboard, daemon=True)
        self.keyboard_thread.start()
        
        self.logger.log_event("initialisation_complete", {
            "visualisation": self.selected_visualisation,
            "config_loaded": bool(self.config)
        })

    def _monitor_keyboard(self):
        """Monitor keyboard for ESC key press."""
        while self.running.is_set():
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'\x1b':  # ESC key
                    print("\nESC pressed. Stopping...")
                    self.stop()
            time.sleep(0.1)

    def signal_handler(self, sig, frame):
        """Handle Ctrl+C signal to gracefully stop the application."""
        print("\nCtrl+C pressed. Stopping...")
        self.stop()

    def _load_config(self, config_path: Path = None) -> Dict:
        """
        Load and validate the configuration file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Dict containing the loaded configuration
            
        Raises:
            ValueError: If configuration file is invalid
        """
        default_config = {
            "visualisation": {
                "options": ["Drishti-v2.6.4", "ParaView", "Unity_VR_Game"],
                "selected": None,
                "render_options": {
                    "resolution": "1920x1080",
                    "visualisations": {
                        "Drishti-v2.6.4": {"udp_ip": "127.0.0.1", "udp_port": 7755, "command": "addrotation %.3f %.3f %.3f %.3f"},
                        "ParaView": {"udp_ip": "192.168.1.100", "udp_port": 7766, "command": "rotate %.3f %.3f %.3f"},
                        "Unity_VR_Game": {"udp_ip": "127.0.0.1", "udp_port": 12345, "command": "move %.3f %.3f %.3f"}
                    }
                }
            },
            "actuation": {
                "config": {"x": 0.0, "y": 0.0, "z": 0.0},
                "commands": {
                    "default": "addrotation %.3f %.3f %.3f %.3f",
                    "mouse": "addrotation %.3f %.3f %.3f %.3f",
                    "unity_movement": "move %.3f %.3f %.3f",
                    "unity_rotation": "rotate %.3f %.3f %.3f",
                    "unity_brake": "BRAKE",
                    "unity_release": "RELEASE"
                }
            },
            "calibration": {
                "default": {"deadzone": 0.1, "scale_factor": 1.0},
                "devices": {
                    "Bluetooth_mouse": {
                        "deadzone": 0.1,
                        "scale_factor": 1.0,
                        "axis_mapping": {
                            "x": "unity_rotation",
                            "y": "unity_movement"
                        },
                        "button_mapping": {
                            "left_click": "unity_brake",
                            "right_click": "unity_release"
                        }
                    },
                    "axis 4 button joystick": {
                        "deadzone": 0.1,
                        "scale_factor": 1.0,
                        "axis_mapping": {
                            "axis_0": "addrotation",  # X axis
                            "axis_1": "addrotation",  # Y axis
                            "axis_2": "addrotation",  # Z axis
                            "axis_3": "addrotation"   # Roll axis
                        },
                        "button_mapping": {
                            "button_0": "increase_speed",
                            "button_1": "decrease_speed"
                        }
                    }
                }
            },
            "input_devices": {
                "Bluetooth_mouse": {
                    "vid": "046d",
                    "pid": "b03a",
                    "type": "mouse",
                    "library": "pywinusb",
                    "axes": ["x", "y"],
                    "buttons": ["left_click", "right_click"],
                    "command": "mouse"
                },
                "axis 4 button joystick": {
                    "vid": "0000",
                    "pid": "0000",
                    "type": "gamepad",
                    "library": "pygame",
                    "axes": ["axis_0", "axis_1", "axis_2", "axis_3"],
                    "buttons": ["button_0", "button_1", "button_2", "button_3"],
                    "command": "gamepad"
                }
            }
        }
        
        try:
            if config_path and config_path.exists():
                with open(config_path, "r") as f:
                    config_content = f.read()
                    self.logger.log_event("config_loaded", {"content": config_content})
                    config = json.loads(config_content)
                    
                    # Load and validate input devices
                    loaded_devices = config.get("input_devices", default_config["input_devices"])
                    self.logger.log_event("devices_loaded", {"devices": loaded_devices})
                    config["input_devices"] = loaded_devices
                    
                    # Ensure calibration settings exist
                    if "calibration" not in config:
                        config["calibration"] = default_config["calibration"]
                    if "devices" not in config["calibration"]:
                        config["calibration"]["devices"] = {}
                    
                    return {k: config.get(k, default_config[k]) for k in default_config}
            else:
                self.logger.log_warning("No configuration file found", {"path": str(config_path)})
                return default_config
                
        except json.JSONDecodeError as e:
            self.logger.log_error(e, {"file": str(config_path)})
            return default_config
        except Exception as e:
            self.logger.log_error(e, {"file": str(config_path)})
            return default_config

    def select_visualisation(self) -> str:
        """Select a visualisation from the available options."""
        options = self.config["visualisation"]["options"]
        qprompt.clear()
        print("\nAvailable Visualisations:")
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        
        while True:
            try:
                choice = qprompt.ask_int("Select a visualisation", min=1, max=len(options))
                selected = options[choice - 1]
                print(f"\nSelected visualisation: {selected}")
                self.logger.log_event("visualisation_selected", {"visualisation": selected})
                return selected
            except ValueError:
                print("Please enter a valid number")
            except IndexError:
                print("Please select a number from the list")

    def list_devices(self) -> List[Tuple[str, str, str, Dict]]:
        """
        List all available HID devices and match them with configured devices.
        
        Returns:
            List of tuples containing (vid, pid, name, config) for matched devices
        """
        all_hids = hid.find_all_hid_devices()
        print(f"Detected HID devices: {len(all_hids)} found")
        for device in all_hids:
            vid = f"{device.vendor_id:04x}".lower()
            pid = f"{device.product_id:04x}".lower()
            print(f"HID Device - VID: {vid}, PID: {pid}, Product: {device.product_name}")

        input_devices = self.config["input_devices"]
        print(f"Configured devices from configuration: {input_devices}")
        available_devices = []
        for device in all_hids:
            vid = f"{device.vendor_id:04x}".lower()
            pid = f"{device.product_id:04x}".lower()
            for name, config in input_devices.items():
                if config.get("vid") == vid and config.get("pid") == pid:
                    print(f"Match found: {name} (VID: {vid}, PID: {pid})")
                    available_devices.append((vid, pid, name, config))
        if not available_devices:
            print("No matches between detected HID devices and configuration.")
        return available_devices

    def select_device(self) -> Optional[Tuple[str, str, str, Dict]]:
        """
        Allow user to select an input device from available devices.
        
        Returns:
            Tuple of (vid, pid, name, config) for selected device, or None if no device selected
        """
        devices = self.list_devices()
        if not devices:
            print("No compatible devices found.")
            self.logger.log_warning("No compatible devices found.")
            return None

        qprompt.clear()
        print("Available Devices:")
        for i, (vid, pid, name, config) in enumerate(devices, 1):
            print(f"{i}. {name} (VID: {vid}, PID: {pid}, Type: {config.get('type', 'unknown')})")
        choice = qprompt.ask(f"Select a device (1-{len(devices)}) ", int, min=1, max=len(devices))
        return devices[choice - 1]

    def configure_buttons(self, dev_config: Dict) -> Dict:
        """
        Configure button mappings for a device.
        
        Args:
            dev_config: Device configuration dictionary
            
        Returns:
            Dictionary of button mappings
        """
        if not qprompt.ask_yesno("Configure buttons? (y/n)", default="n"):
            return {}
        
        buttons = dev_config.get("buttons", [])
        if not buttons:
            print("No buttons available for this device.")
            return {}

        actions = ["change_axis", "increase_speed", "decrease_speed"]
        mappings = {}
        
        while qprompt.ask_yesno("Add a button mapping? (y/n)", default="y"):
            print("Available Buttons:")
            for i, btn in enumerate(buttons, 1):
                print(f"{i}. {btn}")
            btn_choice = qprompt.ask(f"Select a button (1-{len(buttons)}) ", int, min=1, max=len(buttons))
            selected_btn = buttons[btn_choice - 1]

            print("Available Actions:")
            for i, action in enumerate(actions, 1):
                print(f"{i}. {action}")
            action_choice = qprompt.ask(f"Select an action (1-{len(actions)}) ", int, min=1, max=len(actions))
            selected_action = actions[action_choice - 1]

            if selected_action == "change_axis":
                axes = ["x", "y", "z"]
                axis_choice = qprompt.ask("Select axis (1=x, 2=y, 3=z) ", int, min=1, max=3)
                mappings[selected_btn] = {"action": "change_axis", "axis": axes[axis_choice - 1]}
            else:
                mappings[selected_btn] = {"action": selected_action}

            print(f"Configured {selected_btn} to {selected_action}")
            self.logger.log_event("button_mapping_configured", {
                "device": self.dev_name,
                "button": selected_btn,
                "action": selected_action
            })

        return mappings

    def configure_device(self, vid: str, pid: str, name: str, dev_config: Dict) -> Optional[InputDevice]:
        """
        Configure an input device with the specified parameters.
        
        Args:
            vid: Vendor ID of the device
            pid: Product ID of the device
            name: Name of the device
            dev_config: Device configuration dictionary
            
        Returns:
            Configured InputDevice instance, or None if configuration fails
        """
        try:
            # Convert VID/PID to integers, handling both hex strings and decimal strings
            try:
                vid_int = int(vid, 16) if vid.startswith('0x') or any(c in vid.upper() for c in 'ABCDEF') else int(vid)
                pid_int = int(pid, 16) if pid.startswith('0x') or any(c in pid.upper() for c in 'ABCDEF') else int(pid)
            except ValueError:
                # If conversion fails, use 0 for pygame devices
                vid_int = 0
                pid_int = 0
            
            device = InputDevice(
                name=name,
                vid=vid_int,
                pid=pid_int,
                device_type=dev_config["type"],
                library=dev_config["library"],
                axes=dev_config["axes"],
                buttons=dev_config["buttons"],
                command=dev_config["command"],
                logger=self.logger
            )
            
            # Apply calibration settings
            cal = self.config["calibration"]["devices"].get(name, self.config["calibration"]["default"])
            deadzone = float(cal.get("deadzone", 0.1))
            scale_factor = float(cal.get("scale_factor", 1.0))
            
            # Set up device callbacks based on type
            if dev_config["type"] == "mouse":
                mapping = cal.get("axis_mapping", {"x": "mouse_x", "y": "none", "z": "none"})
                device.callback = lambda state: self._process_mouse_state(state, deadzone, scale_factor, mapping, dev_config)
            else:
                device.callback = lambda state: self._process_state(state, deadzone, scale_factor, dev_config)
            
            # Configure button mappings
            self.button_mappings = self.configure_buttons(dev_config)
            device.button_callback = lambda state, buttons: self._handle_buttons(state, buttons, dev_config)
            
            self.dev_name = name
            print(f"Configured {name} successfully")
            self.logger.log_event("device_configured", {
                "device": self.dev_name,
                "config": dev_config
            })
            return device
        except Exception as e:
            print(f"Failed to configure {name}: {e}")
            self.logger.log_error(e, {
                "device": name,
                "config": dev_config
            })
            return None

    def _process_state(self, state: Dict, deadzone: float, scale_factor: float, dev_config: Dict) -> None:
        """
        Process device state using configured transformations and optimisations.
        
        Args:
            state: Current state of the device
            deadzone: Base deadzone value
            scale_factor: Base scale factor
            dev_config: Device configuration dictionary
        """
        try:
            # Log the incoming state for debugging
            print(f"Processing state: {state}")
            
            # Update optimised state
            changed_keys = self.optimisation_manager.state.update(state)
            if not changed_keys:
                return  # Skip processing if no changes
                
            device_type = dev_config["type"]
            device_name = dev_config.get("name", "")
            
            # Get device-specific calibration
            cal = self.config["calibration"]["devices"].get(device_name, self.config["calibration"]["default"])
            deadzone = float(cal.get("deadzone", deadzone))
            scale_factor = float(cal.get("scale_factor", scale_factor))
            
            # Process each axis
            for axis in dev_config["axes"]:
                if axis not in state:
                    continue
                    
                value = state[axis]
                print(f"Processing axis {axis} with value {value}")
                
                # Apply deadzone
                if abs(value) < deadzone:
                    value = 0.0
                
                # Apply scale factor
                value *= scale_factor
                
                # Only process if value is non-zero
                if value != 0.0:
                    # Get axis mapping from configuration
                    axis_mapping = cal.get("axis_mapping", {}).get(axis, "addrotation")
                    
                    # Create command based on mapping
                    if axis_mapping == "addrotation":
                        # For addrotation, map axes to x, y, z rotations
                        if axis == "axis_0":  # X axis
                            command = f"addrotation {value:.3f} 0.0 0.0 0.0"
                        elif axis == "axis_1":  # Y axis
                            command = f"addrotation 0.0 {value:.3f} 0.0 0.0"
                        elif axis == "axis_2":  # Z axis
                            command = f"addrotation 0.0 0.0 {value:.3f} 0.0"
                        elif axis == "axis_3":  # Roll axis
                            command = f"addrotation 0.0 0.0 0.0 {value:.3f}"
                        else:
                            continue
                    else:
                        # For other commands, use the mapping directly
                        command = f"{axis_mapping} {value:.3f}"
                    
                    # Send command via UDP
                    try:
                        if hasattr(self, 'actuation') and self.actuation:
                            print(f"Sending UDP command: {command} to {self.actuation.udp_ip}:{self.actuation.udp_port}")
                            self.actuation.sock.sendto(command.encode(), (self.actuation.udp_ip, self.actuation.udp_port))
                            print(f"UDP Command sent successfully: {command}")
                    except Exception as e:
                        print(f"Error sending UDP command: {e}")
                        self.logger.log_error(e, {
                            "device": self.dev_name,
                            "command": command,
                            "value": value
                        })
                    
        except Exception as e:
            print(f"Error in _process_state: {e}")
            self.logger.log_error(e, {
                "device": self.dev_name,
                "state": state,
                "config": dev_config
            })

    def _process_mouse_state(self, state: Dict, deadzone: float, scale_factor: float, mapping: Dict, dev_config: Dict) -> None:
        """
        Process mouse state using optimised transformations.
        
        Args:
            state: Current state of the mouse
            deadzone: Base deadzone value
            scale_factor: Base scale factor
            mapping: Axis mapping configuration
            dev_config: Device configuration dictionary
        """
        try:
            # Update optimised state
            changed_keys = self.optimisation_manager.state.update(state)
            if not changed_keys:
                return  # Skip processing if no changes
                
            mouse_mappings = self.config["device_mappings"].get("mouse", {})
            
            for axis, axis_mapping in mouse_mappings.items():
                if axis not in changed_keys:
                    continue
                    
                # Get transformation configuration
                transform = axis_mapping["transform"]
                transform_type = transform["type"]
                transform_config = transform["config"]
                
                # Try to get cached transformation
                cache_key = f"mouse_{axis}_{state[axis]}"
                transformed_value = self.optimisation_manager.cache.get(cache_key)
                
                if transformed_value is None:
                    # Apply transformation if not cached
                    transformed_value = self.optimisation_manager.monitor.measure(
                        "transformation_time",
                        lambda: self.transformation_manager.transform_input(
                            state[axis], transform_type, transform_config
                        )
                    )
                    self.optimisation_manager.cache.set(cache_key, transformed_value)
                    self.optimisation_manager.monitor.metrics.cache_misses += 1
                else:
                    self.optimisation_manager.monitor.metrics.cache_hits += 1
                
                # Log transformation
                self.logger.log_transformation(
                    self.dev_name,
                    state[axis],
                    transformed_value,
                    transform_type,
                    transform_config
                )
                
                # Send transformed value to output
                if transformed_value != 0.0:  # Only send non-zero values
                    self._send_command(axis_mapping["output"], transformed_value)
                    
        except Exception as e:
            self.logger.log_error(e, {
                "device": self.dev_name,
                "state": state,
                "config": dev_config
            })
            
    def _handle_buttons(self, state: Dict, buttons: List[str], dev_config: Dict) -> None:
        """
        Handle button presses using threshold transformations.
        
        Args:
            state: Current state of the device
            buttons: List of pressed buttons
            dev_config: Device configuration dictionary
        """
        try:
            # Process each button that has a mapping
            for button, mapping in self.button_mappings.items():
                # Check if button is pressed
                if button in state and state[button]:
                    action = mapping["action"]
                    if action == "change_axis":
                        self._change_axis(mapping["axis"])
                    elif action == "increase_speed":
                        self._adjust_speed(1.1)
                        print(f"Speed increased to: {self.speed_factor:.2f}")
                    elif action == "decrease_speed":
                        self._adjust_speed(0.9)
                        print(f"Speed decreased to: {self.speed_factor:.2f}")
                        
        except Exception as e:
            print(f"Error handling buttons: {e}")
            self.logger.log_error(e, {
                "device": self.dev_name,
                "state": state,
                "config": dev_config
            })
            
    def _send_command(self, command: str, value: float) -> None:
        """
        Send command to the current visualisation.
        
        Args:
            command: Command to send
            value: Value associated with the command
        """
        try:
            if self.selected_visualisation:
                self.actuation.process_input([value, 0.0, 0.0], self.dev_name, command)
        except Exception as e:
            print(f"Error sending command: {e}")
            self.logger.log_error(e, {
                "device": self.dev_name,
                "command": command,
                "value": value
            })

    def configure_and_run(self):
        """Configure and run the LISU framework."""
        try:
            # Initialize actuation system first
            if not hasattr(self, 'actuation') or not self.actuation:
                self.actuation = Actuation.Actuation(selected_visualisation=self.selected_visualisation)
                print(f"\nInitialized actuation system for {self.selected_visualisation}")
                print(f"UDP IP: {self.actuation.udp_ip}, Port: {self.actuation.udp_port}")
            
            # Get available devices using HID and pygame
            qprompt.clear()
            print("\nDetecting input devices...")
            
            # Get HID devices using pywinusb
            hid_devices = hid.find_all_hid_devices()
            print(f"\nHID devices found: {len(hid_devices)}")
            for i, device in enumerate(hid_devices, 1):
                print(f"{i}. HID Device - VID: {device.vendor_id:04x}, PID: {device.product_id:04x}, Product: {device.product_name}")
            
            # Get gamepad devices using pygame
            pygame.init()
            pygame.joystick.init()
            joystick_count = pygame.joystick.get_count()
            print(f"\nGamepad devices found: {joystick_count}")
            for i in range(joystick_count):
                joystick = pygame.joystick.Joystick(i)
                joystick.init()
                print(f"{i + len(hid_devices) + 1}. Gamepad - {joystick.get_name()}")
            
            # Let user select a device
            try:
                selection = int(input("\nEnter the number of the device you want to use (or 0 to exit): "))
                if selection == 0:
                    print("No device selected.")
                    return
                
                total_devices = len(hid_devices) + joystick_count
                if not 1 <= selection <= total_devices:
                    print("Invalid selection.")
                    return
                
                # Determine which library to use based on selection
                if selection <= len(hid_devices):
                    # HID device selected
                    selected_device = hid_devices[selection - 1]
                    library = "pywinusb"
                    
                    # Determine device type based on product name
                    product_name = selected_device.product_name.lower()
                    if "mouse" in product_name or "trackball" in product_name:
                        device_type = "mouse"
                        axes = ["x", "y"]
                        buttons = ["left_click", "right_click"]
                    elif "keyboard" in product_name:
                        device_type = "keyboard"
                        axes = []
                        buttons = ["space", "enter", "esc"]
                    elif "gamepad" in product_name or "joystick" in product_name:
                        device_type = "gamepad"
                        axes = ["x", "y", "z", "roll"]
                        buttons = [f"button_{i}" for i in range(8)]
                    else:
                        device_type = "unknown"
                        axes = ["x", "y"]
                        buttons = ["button_1", "button_2"]
                    
                    # Create device configuration
                    device_config = {
                        "vid": f"{selected_device.vendor_id:04x}",
                        "pid": f"{selected_device.product_id:04x}",
                        "type": device_type,
                        "library": library,
                        "axes": axes,
                        "buttons": buttons,
                        "command": device_type
                    }
                    
                    # Configure the device
                    device = self.configure_device(
                        device_config["vid"],
                        device_config["pid"],
                        selected_device.product_name,
                        device_config
                    )
                else:
                    # Gamepad device selected
                    joystick_index = selection - len(hid_devices) - 1
                    joystick = pygame.joystick.Joystick(joystick_index)
                    joystick.init()
                    library = "pygame"
                    device_type = "gamepad"
                    
                    # Get the number of axes and buttons
                    num_axes = joystick.get_numaxes()
                    num_buttons = joystick.get_numbuttons()
                    
                    # Create appropriate axes and buttons lists
                    axes = [f"axis_{i}" for i in range(num_axes)]
                    buttons = [f"button_{i}" for i in range(num_buttons)]
                    
                    # Create device configuration
                    device_config = {
                        "vid": "0000",  # pygame doesn't provide VID/PID
                        "pid": "0000",
                        "type": device_type,
                        "library": library,
                        "axes": axes,
                        "buttons": buttons,
                        "command": "gamepad"
                    }
                    
                    try:
                        # Configure the device
                        device = self.configure_device(
                            device_config["vid"],
                            device_config["pid"],
                            joystick.get_name(),
                            device_config
                        )
                        
                        if not device:
                            print("Failed to configure device.")
                            return
                        
                        print(f"\nSelected device:")
                        print(f"  Name: {device.name}")
                        print(f"  Type: {device.device_type}")
                        print(f"  Library: {device.library}")
                        
                        # Set up device callbacks
                        device.callback = lambda state: self._process_state(state, 0.1, 1.0, device_config)
                        device.button_callback = lambda state, buttons: self._handle_buttons(state, buttons, device_config)
                        
                        # Start monitoring
                        device.start_monitoring()
                        
                        print("\nDevice monitoring started. Press ESC to exit.")
                        print("Moving the joystick should send UDP commands to the visualization.")
                        
                        # Keep the program running until ESC is pressed
                        while True:
                            if msvcrt.kbhit():
                                key = msvcrt.getch()
                                if key == b'\x1b':  # ESC key
                                    print("\nESC pressed. Stopping...")
                                    device.stop_monitoring()
                                    if library == "pygame":
                                        pygame.quit()
                                    break
                            time.sleep(0.1)
                            
                    except Exception as e:
                        print(f"Error configuring device: {e}")
                        if 'device' in locals() and device:
                            try:
                                device.stop_monitoring()
                            except:
                                pass
                        if library == "pygame":
                            pygame.quit()
                        return
                
            except ValueError:
                print("Please enter a valid number.")
                return
            
        except Exception as e:
            print(f"Error in configure_and_run: {e}")
            self.logger.log_error(e, {"context": "configure_and_run"})
        finally:
            # Clean up
            if 'device' in locals():
                device.stop_monitoring()
            if 'pygame' in locals():
                pygame.quit()

    def _process_event_batch(self, batch: List[Dict[str, Any]]):
        """Process a batch of events."""
        for event in batch:
            try:
                # Get device state
                device_state = event.get("state", {})
                if not device_state:
                    continue

                # Get device name and config
                device_name = event.get("device")
                if not device_name:
                    continue

                device_config = self.config.get("input_devices", {}).get(device_name, {})
                if not device_config:
                    continue

                # Process axis values
                for axis in ["x", "y", "z"]:
                    if axis in device_state:
                        value = device_state[axis]
                        # Apply transformations
                        transformed_value = self.transformation_manager.transform_axis(
                            device_name, axis, value
                        )
                        # Apply speed factor
                        transformed_value *= self.speed_factor
                        
                        # Send command with proper format for Drishti
                        if self.selected_visualisation == "Drishti-v2.6.4":
                            command = f"addrotation {transformed_value:.3f} 0.0 0.0 0.0"
                            try:
                                self.actuation.sock.sendto(command.encode(), (self.actuation.udp_ip, self.actuation.udp_port))
                                print(f"UDP Command sent: {command}")
                            except Exception as e:
                                print(f"Error sending UDP command: {e}")

                # Process button states
                if "buttons" in device_state:
                    button_states = device_state["buttons"]
                    for i, state in enumerate(button_states):
                        if state and i in self.button_mappings:
                            mapping = self.button_mappings[i]
                            if mapping["action"] == "increase_speed":
                                self.speed_factor *= 1.1
                                print(f"Speed increased to: {self.speed_factor:.2f}")
                            elif mapping["action"] == "decrease_speed":
                                self.speed_factor *= 0.9
                                print(f"Speed decreased to: {self.speed_factor:.2f}")

            except Exception as e:
                self.logger.log_error(e, {
                    "device": device_name,
                    "state": device_state,
                    "config": device_config
                })

    def stop(self):
        """
        Stop the LISU framework and clean up resources.
        """
        print("Stopping framework...")
        self.running.clear()
        
        # Close UDP socket
        if hasattr(self, 'actuation') and self.actuation:
            try:
                self.actuation.sock.close()
            except Exception as e:
                print(f"Error closing UDP socket: {e}")
        
        # Clean up resources
        self.cleanup()
        
        print("Framework stopped.")
        sys.exit(0)  # Force exit the program

    def cleanup(self):
        """Clean up resources and log final metrics."""
        try:
            # Log final metrics
            self.logger.log_event("framework_shutting_down", {
                **self.logger.get_metrics(),
                **self.optimisation_manager.monitor.get_metrics()
            })
            
            # Clean up components
            self.transformation_manager.clear_history()
            self.optimisation_manager.cleanup()
            self.logger.cleanup()
            
            # Clear any remaining events
            self.running.clear()
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
            sys.exit(1)  # Exit with error code if cleanup fails

    def __del__(self):
        """
        Destructor to ensure proper cleanup of resources.
        """
        self.stop()

if __name__ == "__main__":
    lisu = LisuManager()
    lisu.configure_and_run()