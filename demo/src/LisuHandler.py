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
                "default": {"deadzone": 0.2, "scale_factor": 1.0},
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
                        "deadzone": 0.2,
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

    def detect_devices(self) -> List[Dict]:
        """
        Detect available input devices using configured libraries.
        
        Returns:
            List of dictionaries containing device information
        """
        devices = []
        
        try:
            # Get configured devices from ontology
            configured_devices = self.config.get("input_devices", {})
            
            # Detect HID devices
            if self.config.get("use_pywinusb", True):
                try:
                    hid_devices = hid.find_all_hid_devices()
                    
                    for device in hid_devices:
                        # Convert VID/PID to hex strings for comparison
                        vid_hex = f"{device.vendor_id:04x}"
                        pid_hex = f"{device.product_id:04x}"
                        
                        # Look for matching device in ontology
                        for dev_name, dev_config in configured_devices.items():
                            if (dev_config.get("vid", "").lower() == vid_hex and 
                                dev_config.get("pid", "").lower() == pid_hex and
                                dev_config.get("library") == "pywinusb"):
                                devices.append({
                                    "name": dev_name,
                                    "vid": vid_hex,
                                    "pid": pid_hex,
                                    "type": dev_config.get("type", "unknown"),
                                    "library": "pywinusb",
                                    "product": device.product_name
                                })
                                break
                except ImportError:
                    print("pywinusb not available")
            
            # Detect pygame devices
            if self.config.get("use_pygame", True):
                try:
                    pygame.init()
                    pygame.joystick.init()
                    
                    for i in range(pygame.joystick.get_count()):
                        joystick = pygame.joystick.Joystick(i)
                        joystick.init()
                        
                        # Get device name and try to match with ontology
                        device_name = joystick.get_name()
                        for dev_name, dev_config in configured_devices.items():
                            if (dev_config.get("library") == "pygame" and
                                dev_config.get("type") == "3d_input"):  # For now, assume all pygame devices are 3D input
                                devices.append({
                                    "name": dev_name,
                                    "type": "3d_input",
                                    "library": "pygame",
                                    "product": device_name,
                                    "device_index": i
                                })
                                break
                except ImportError:
                    print("pygame not available")
            
            return devices
            
        except Exception as e:
            print(f"Error detecting devices: {e}")
            self.logger.log_error(e)
            return []

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

    def configure_device(self, vid: str, pid: str, name: str, dev_config: Dict, device_index: int = 0) -> Optional[InputDevice]:
        """
        Configure an input device with the specified parameters.
        
        Args:
            vid: Vendor ID of the device
            pid: Product ID of the device
            name: Name of the device
            dev_config: Device configuration dictionary
            device_index: Index of the device (for pygame devices)
            
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
            
            # Get available functions based on device type
            device_type = dev_config.get("type", "")
            if device_type == "gamepad":
                available_functions = [
                    "Movement Control (X, Y, Z axes)",
                    "Speed Control (Roll axis)",
                    "Button Actions (increase/decrease speed)"
                ]
            elif device_type == "mouse":
                available_functions = [
                    "Movement Control (X, Y axes)",
                    "Button Actions (unity_brake/release)"
                ]
            else:
                available_functions = ["Movement Control"]
            
            # Let user select functions
            print("\nAvailable functions for this device:")
            for i, func in enumerate(available_functions, 1):
                print(f"{i}. {func}")
            
            selected_functions = []
            while True:
                try:
                    choice = input("\nEnter function number to select (or 'done' to finish, 'back' to go back): ")
                    if choice.lower() == 'done':
                        break
                    elif choice.lower() == 'back':
                        return None
                    
                    func_index = int(choice) - 1
                    if 0 <= func_index < len(available_functions):
                        selected_functions.append(available_functions[func_index])
                        print(f"Selected: {available_functions[func_index]}")
                    else:
                        print("Invalid selection. Please try again.")
                except ValueError:
                    print("Please enter a valid number or 'done'/'back'")
            
            if not selected_functions:
                print("No functions selected. Going back...")
                return None
            
            device = InputDevice(
                name=name,
                vid=vid_int,
                pid=pid_int,
                device_type=dev_config["type"],
                library=dev_config["library"],
                axes=dev_config["axes"],
                buttons=dev_config["buttons"],
                command=dev_config["command"],
                logger=self.logger,
                device_index=device_index
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
                "config": dev_config,
                "selected_functions": selected_functions
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
        try:
            # Update optimised state
            changed_keys = self.optimisation_manager.state.update(state)
            if not changed_keys:
                return  # Skip processing if no changes
                
            device_type = dev_config["type"]
            device_name = dev_config.get("name", "")
            
            # Get device-specific calibration and mappings
            cal = self.config["calibration"]["devices"].get(device_name, self.config["calibration"]["default"])
            
            # Get visualization-specific command format
            vis_config = self.config["visualisation"]["render_options"]["visualisations"].get(self.selected_visualisation, {})
            command_format = vis_config.get("command", self.config["actuation"]["commands"]["default"])
            
            # Process each axis using ontology mappings
            has_movement = False
            x_value = 0.0
            y_value = 0.0
            z_value = 0.0
            angle_value = 1.0  # Default minimum angle
            
            # Process axes based on device type
            if device_type == "gamepad":
                # Map axes according to calibration
                axis_mapping = cal.get("axis_mapping", {})
                
                # Process X axis (axis_0)
                if "axis_0" in state:
                    value = state["axis_0"]
                    if abs(value) >= deadzone:
                        x_value = value * scale_factor
                        has_movement = True
                
                # Process Y axis (axis_1)
                if "axis_1" in state:
                    value = state["axis_1"]
                    if abs(value) >= deadzone:
                        y_value = value * scale_factor
                        has_movement = True
                
                # Process Z axis (axis_2)
                if "axis_2" in state:
                    value = state["axis_2"]
                    if abs(value) >= deadzone:
                        z_value = value * scale_factor
                        has_movement = True
                
                # Process Roll axis (axis_3)
                if "axis_3" in state:
                    value = state["axis_3"]
                    if abs(value) >= deadzone:
                        # Map roll to angle range (1.0 to 10.0)
                        angle_value = 1.0 + (abs(value) * 9.0)
            
            # Only send UDP command if there's actual movement in X, Y, or Z axes
            if has_movement:
                # Format command based on visualization type
                if self.selected_visualisation == "Drishti-v2.6.4":
                    command = f"addrotation {x_value:.3f} {y_value:.3f} {z_value:.3f} {angle_value:.3f}"
                elif self.selected_visualisation == "ParaView":
                    command = f"rotate {x_value:.3f} {y_value:.3f} {z_value:.3f}"
                elif self.selected_visualisation == "Unity_VR_Game":
                    command = f"move {x_value:.3f} {y_value:.3f} {z_value:.3f}"
                else:
                    command = command_format % (x_value, y_value, z_value, angle_value)
                
                # Send command via UDP
                try:
                    if hasattr(self, 'actuation') and self.actuation:
                        self.actuation.sock.sendto(command.encode(), (self.actuation.udp_ip, self.actuation.udp_port))
                        print(f"UDP Command sent: {command}")
                except Exception as e:
                    print(f"Error sending UDP command: {e}")
                    self.logger.log_error(e, {
                        "device": self.dev_name,
                        "command": command,
                        "values": {"x": x_value, "y": y_value, "z": z_value, "angle": angle_value}
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
                
            device_name = dev_config.get("name", "")
            device_type = dev_config.get("type", "")
            
            # Get device-specific calibration and mappings
            cal = self.config["calibration"]["devices"].get(device_name, self.config["calibration"]["default"])
            device_mappings = self.config["device_mappings"].get(device_type, {})
            
            # Get visualization-specific command format
            vis_config = self.config["visualisation"]["render_options"]["visualisations"].get(self.selected_visualisation, {})
            command_format = vis_config.get("command", self.config["actuation"]["commands"]["default"])
            
            # Process each axis using ontology mappings
            has_movement = False
            x_value = 0.0
            y_value = 0.0
            z_value = 0.0
            angle_value = 1.0  # Default minimum angle
            
            # Process X axis
            if "x" in state:
                value = state["x"]
                if abs(value) >= deadzone:
                    x_value = value * scale_factor
                    has_movement = True
            
            # Process Y axis
            if "y" in state:
                value = state["y"]
                if abs(value) >= deadzone:
                    y_value = value * scale_factor
                    has_movement = True
            
            # Only send UDP command if there's actual movement
            if has_movement:
                # Format command based on visualization type
                if self.selected_visualisation == "Drishti-v2.6.4":
                    command = f"addrotation {x_value:.3f} {y_value:.3f} {z_value:.3f} {angle_value:.3f}"
                elif self.selected_visualisation == "ParaView":
                    command = f"rotate {x_value:.3f} {y_value:.3f} {z_value:.3f}"
                elif self.selected_visualisation == "Unity_VR_Game":
                    command = f"move {x_value:.3f} {y_value:.3f} {z_value:.3f}"
                else:
                    command = command_format % (x_value, y_value, z_value, angle_value)
                
                # Send command via UDP
                try:
                    if hasattr(self, 'actuation') and self.actuation:
                        self.actuation.sock.sendto(command.encode(), (self.actuation.udp_ip, self.actuation.udp_port))
                        print(f"UDP Command sent: {command}")
                except Exception as e:
                    print(f"Error sending UDP command: {e}")
                    self.logger.log_error(e, {
                        "device": self.dev_name,
                        "command": command,
                        "values": {"x": x_value, "y": y_value, "z": z_value, "angle": angle_value}
                    })
                    
        except Exception as e:
            print(f"Error in _process_mouse_state: {e}")
            self.logger.log_error(e, {
                "device": self.dev_name,
                "state": state,
                "config": dev_config
            })
            
    def _handle_buttons(self, state: Dict, buttons: Dict, dev_config: Dict) -> None:
        """
        Handle button presses and map them to actions using ontology mappings.
        
        Args:
            state: Current device state
            buttons: Button states
            dev_config: Device configuration
        """
        try:
            # If no button mappings are configured, return early
            if not self.button_mappings:
                return
                
            device_name = dev_config.get("name", "")
            device_type = dev_config.get("type", "")
            
            # Get device-specific calibration and mappings
            cal = self.config["calibration"]["devices"].get(device_name, self.config["calibration"]["default"])
            button_mapping = cal.get("button_mapping", {})
            
            # Check each button in our mappings
            for button, action in button_mapping.items():
                if button in state and state[button]:
                    print(f"Button {button} pressed, executing action: {action}")
                    
                    # Handle different action types
                    if action == "increase_speed":
                        # Get current speed from roll axis
                        if "axis_3" in state:
                            current_speed = 1.0 + (abs(state["axis_3"]) * 9.0)
                            new_speed = min(10.0, current_speed + 1.0)
                            state["axis_3"] = (new_speed - 1.0) / 9.0
                            print(f"Rotation speed increased to: {new_speed:.1f}")
                            
                    elif action == "decrease_speed":
                        # Get current speed from roll axis
                        if "axis_3" in state:
                            current_speed = 1.0 + (abs(state["axis_3"]) * 9.0)
                            new_speed = max(1.0, current_speed - 1.0)
                            state["axis_3"] = (new_speed - 1.0) / 9.0
                            print(f"Rotation speed decreased to: {new_speed:.1f}")
                            
                    elif action == "unity_brake":
                        # Send brake command to Unity
                        if self.selected_visualisation == "Unity_VR_Game":
                            command = "BRAKE"
                            try:
                                self.actuation.sock.sendto(command.encode(), (self.actuation.udp_ip, self.actuation.udp_port))
                                print("UDP Command sent: BRAKE")
                            except Exception as e:
                                print(f"Error sending brake command: {e}")
                                
                    elif action == "unity_release":
                        # Send release command to Unity
                        if self.selected_visualisation == "Unity_VR_Game":
                            command = "RELEASE"
                            try:
                                self.actuation.sock.sendto(command.encode(), (self.actuation.udp_ip, self.actuation.udp_port))
                                print("UDP Command sent: RELEASE")
                            except Exception as e:
                                print(f"Error sending release command: {e}")
                    
                    # Log the button action
                    self.logger.log_event("button_action", {
                        "device": self.dev_name,
                        "button": button,
                        "action": action,
                        "state": state
                    })
                    
        except Exception as e:
            print(f"Error handling buttons: {e}")
            self.logger.log_error(e, {
                "device": self.dev_name,
                "state": state,
                "buttons": buttons
            })
            
    def _send_command(self, command: str, value: float) -> None:
        """
        Send command to the current visualisation using ontology command formats.
        
        Args:
            command: Command to send
            value: Value associated with the command
        """
        try:
            if not self.selected_visualisation:
                return
                
            # Get visualization-specific command format
            vis_config = self.config["visualisation"]["render_options"]["visualisations"].get(self.selected_visualisation, {})
            command_format = vis_config.get("command", self.config["actuation"]["commands"]["default"])
            
            # Format command based on visualization type
            if self.selected_visualisation == "Drishti-v2.6.4":
                formatted_command = f"addrotation {value:.3f} 0.0 0.0 1.0"
            elif self.selected_visualisation == "ParaView":
                formatted_command = f"rotate {value:.3f} 0.0 0.0"
            elif self.selected_visualisation == "Unity_VR_Game":
                formatted_command = f"move {value:.3f} 0.0 0.0"
            else:
                formatted_command = command_format % (value, 0.0, 0.0, 1.0)
            
            # Send command via UDP
            if hasattr(self, 'actuation') and self.actuation:
                self.actuation.sock.sendto(formatted_command.encode(), (self.actuation.udp_ip, self.actuation.udp_port))
                print(f"UDP Command sent: {formatted_command}")
                
        except Exception as e:
            print(f"Error sending command: {e}")
            self.logger.log_error(e, {
                "device": self.dev_name,
                "command": command,
                "value": value,
                "visualisation": self.selected_visualisation
            })

    def configure_and_run(self):
        """Configure and run the LISU framework."""
        try:
            # Initialize actuation system first
            if not hasattr(self, 'actuation') or not self.actuation:
                self.actuation = Actuation.Actuation(selected_visualisation=self.selected_visualisation)
                print(f"\nInitialized actuation system for {self.selected_visualisation}")
                print(f"UDP IP: {self.actuation.udp_ip}, Port: {self.actuation.udp_port}")
            
            # Get available devices from ontology
            qprompt.clear()
            print("\nAvailable devices from configuration:")
            
            # Get configured devices from ontology
            configured_devices = self.config.get("input_devices", {})
            
            # List configured devices with their functions
            for i, (dev_name, dev_config) in enumerate(configured_devices.items(), 1):
                device_type = dev_config.get('type', 'unknown')
                library = dev_config.get('library', 'unknown')
                axes = dev_config.get('axes', [])
                buttons = dev_config.get('buttons', [])
                
                print(f"{i}. {dev_name}")
                print(f"   Type: {device_type}")
                print(f"   Library: {library}")
                print(f"   Axes: {', '.join(axes)}")
                print(f"   Buttons: {', '.join(buttons)}")
                
                # Print available functions based on device type
                if device_type == "gamepad":
                    print("   Available Functions:")
                    print("   - Movement: X, Y, Z axes control rotation")
                    print("   - Speed Control: Roll axis (axis_3) controls rotation speed (1.0-10.0)")
                    print("   - Button Actions: increase_speed, decrease_speed")
                elif device_type == "mouse":
                    print("   Available Functions:")
                    print("   - Movement: X, Y axes control rotation")
                    print("   - Button Actions: unity_brake, unity_release")
            
            # Let user select a device
            try:
                selection = int(input("\nEnter the number of the device you want to use (or 0 to exit): "))
                if selection == 0:
                    print("No device selected.")
                    return
                
                if not 1 <= selection <= len(configured_devices):
                    print("Invalid selection.")
                    return
                
                # Get selected device configuration
                device_name = list(configured_devices.keys())[selection - 1]
                device_config = configured_devices[device_name]
                
                # Configure the device based on its library
                if device_config["library"] == "pygame":
                    try:
                        pygame.init()
                        pygame.joystick.init()
                        joystick_count = pygame.joystick.get_count()
                        
                        if joystick_count == 0:
                            print("No gamepad devices found.")
                            return
                        
                        # Use the first available joystick
                        joystick = pygame.joystick.Joystick(0)
                        joystick.init()
                        
                        # Configure the device
                        device = self.configure_device(
                            device_config["vid"],
                            device_config["pid"],
                            device_name,
                            device_config,
                            device_index=0
                        )
                    except ImportError:
                        print("pygame not available")
                        return
                else:  # pywinusb
                    try:
                        # Find matching HID device
                        hid_devices = hid.find_all_hid_devices()
                        matching_device = None
                        
                        for hid_device in hid_devices:
                            vid_hex = f"{hid_device.vendor_id:04x}"
                            pid_hex = f"{hid_device.product_id:04x}"
                            
                            if (device_config.get("vid", "").lower() == vid_hex and 
                                device_config.get("pid", "").lower() == pid_hex):
                                matching_device = hid_device
                                break
                        
                        if not matching_device:
                            print("Matching HID device not found.")
                            return
                        
                        # Configure the device
                        device = self.configure_device(
                            f"{matching_device.vendor_id:04x}",
                            f"{matching_device.product_id:04x}",
                            device_name,
                            device_config
                        )
                    except ImportError:
                        print("pygame not available")
                        return
                
                if not device:
                    print("Failed to configure device.")
                    return
                
                print(f"\nSelected device:")
                print(f"  Name: {device.name}")
                print(f"  Type: {device.device_type}")
                print(f"  Library: {device.library}")
                
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
                            if hasattr(device, 'stop_monitoring'):
                                device.stop_monitoring()
                            if device.library == "pygame":
                                pygame.quit()
                            break
                    time.sleep(0.1)
                    
            except ValueError:
                print("Please enter a valid number.")
                return
            
        except Exception as e:
            print(f"Error in configure_and_run: {e}")
            self.logger.log_error(e, {"context": "configure_and_run"})
        finally:
            # Clean up
            if 'device' in locals() and hasattr(device, 'stop_monitoring'):
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
        """Cleanup when the manager is destroyed."""
        try:
            if hasattr(self, 'running') and self.running:
                self.stop()
        except Exception as e:
            print(f"Error during cleanup: {e}")
            # Don't re-raise the exception in __del__

    def select_device(self) -> Optional[Dict]:
        """
        Allow user to select an input device from available devices.
        
        Returns:
            Dictionary containing device information, or None if no device selected
        """
        devices = self.detect_devices()
        if not devices:
            print("No compatible devices found.")
            self.logger.log_warning("No compatible devices found.")
            return None

        qprompt.clear()
        print("\nDetecting input devices...\n")
        
        # Group devices by type
        hid_devices = [d for d in devices if d["library"] == "pywinusb"]
        gamepad_devices = [d for d in devices if d["library"] == "pygame"]
        
        # Print HID devices
        if hid_devices:
            print("HID devices found:", len(hid_devices))
            for i, device in enumerate(hid_devices, 1):
                print(f"{i}. HID Device - VID: {device['vid']}, PID: {device['pid']}, Product: {device['product']}")
        
        # Print gamepad devices
        if gamepad_devices:
            print("\nGamepad devices found:", len(gamepad_devices))
            for i, device in enumerate(gamepad_devices, len(hid_devices) + 1):
                print(f"{i}. Gamepad - {device['product']}")
        
        # Get user selection
        choice = qprompt.ask("\nEnter the number of the device you want to use (or 0 to exit): ", int, min=0, max=len(devices))
        if choice == 0:
            return None
            
        return devices[choice - 1]

if __name__ == "__main__":
    lisu = LisuManager()
    lisu.configure_and_run()