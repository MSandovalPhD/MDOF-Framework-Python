"""
LISU Framework Handler Module
Core handler for the LISU framework, managing device input, transformations, and visualisation.
"""

import Actuation
from LISU.devices import InputDevice
import pywinusb.hid as hid
import qprompt
from typing import List, Tuple, Optional, Dict
import json
from pathlib import Path
import threading
import signal
import sys
from LISU.logging import LisuLogger
from LISU.optimisation import OptimisationManager
import time
from LISU.transformation import TransformationManager

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
        
        self.logger.log_event("initialisation_complete", {
            "visualisation": self.selected_visualisation,
            "config_loaded": bool(self.config)
        })

    def signal_handler(self, sig, frame):
        """Handle Ctrl+C signal to gracefully stop the application."""
        self.logger.log_event("shutdown_signal_received", {"signal": "SIGINT"})
        self.running.clear()

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
        """
        Dynamically generate visualisation options from the ontology.
        
        Returns:
            str: The selected visualisation name
        """
        options = self.config["visualisation"]["options"]
        if not options:
            raise ValueError("No visualisation options defined in configuration.")
        
        qprompt.clear()
        print("Available Visualisations:")
        
        # Get visualisation types from ontology
        vis_types = self.config.get("ontology", {}).get("visualisations", {}).get("types", [])
        
        # Group visualisations by type
        grouped_options = {}
        for option in options:
            vis_config = self.config["visualisation"]["render_options"]["visualisations"].get(option, {})
            vis_type = vis_config.get("type", "unknown")
            if vis_type not in grouped_options:
                grouped_options[vis_type] = []
            grouped_options[vis_type].append(option)
        
        # Display grouped options
        for vis_type in vis_types:
            if vis_type in grouped_options:
                print(f"\n{vis_type.upper()} Applications:")
                for i, vis in enumerate(grouped_options[vis_type], 1):
                    print(f"{i}. {vis}")
        
        # Get user selection
        total_options = len(options)
        choice = qprompt.ask(f"Select a visualisation (1-{total_options}): ", int, min=1, max=total_options)
        selected = options[choice - 1]
        
        # Update configuration
        self.config["visualisation"]["selected"] = selected
        
        # Get visualisation type and available functions
        vis_config = self.config["visualisation"]["render_options"]["visualisations"].get(selected, {})
        vis_type = vis_config.get("type", "unknown")
        available_functions = self.config.get("ontology", {}).get("visualisations", {}).get("functions", {}).get(vis_type, [])
        
        print(f"\nSelected visualisation: {selected} ({vis_type})")
        print(f"Available functions: {', '.join(available_functions)}")
        
        return selected

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
            vid_int = int(vid, 16)
            pid_int = int(pid, 16)
            device = InputDevice(vid_int, pid_int, name, dev_config)
            device.open()
            
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
            
        This method:
        1. Updates optimised state tracking
        2. Retrieves device-specific mappings
        3. Applies cached transformations
        4. Sends transformed values to the visualisation
        5. Logs all transformations and errors
        """
        try:
            # Update optimised state
            changed_keys = self.optimisation_manager.state.update(state)
            if not changed_keys:
                return  # Skip processing if no changes
                
            device_type = dev_config["type"]
            mappings = self.config["device_mappings"].get(device_type, {})
            
            for axis, mapping in mappings.items():
                if axis not in changed_keys:
                    continue
                    
                # Get transformation configuration
                transform = mapping["transform"]
                transform_type = transform["type"]
                transform_config = transform["config"]
                
                # Try to get cached transformation
                cache_key = f"{device_type}_{axis}_{state[axis]}"
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
                    self._send_command(mapping["output"], transformed_value)
                    
        except Exception as e:
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
            for button in buttons:
                if button not in self.button_mappings:
                    continue
                    
                mapping = self.button_mappings[button]
                transform_config = {
                    "threshold": 0.5,
                    "high_value": 1.0,
                    "low_value": 0.0
                }
                
                # Apply threshold transformation
                value = state.get(button, 0.0)
                transformed_value = self.transformation_manager.transform_input(
                    value, "non_linear.threshold", transform_config
                )
                
                if transformed_value > 0.0:
                    action = mapping["action"]
                    if action == "change_axis":
                        self._change_axis(mapping["axis"])
                    elif action == "increase_speed":
                        self._adjust_speed(1.1)
                    elif action == "decrease_speed":
                        self._adjust_speed(0.9)
                        
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
        """
        Configure the LISU framework and run the main loop.
        
        This method handles device selection, configuration, and the main execution loop.
        It also manages the visualisation selection and device monitoring.
        """
        try:
            # Select and configure device
            device_info = self.select_device()
            if not device_info:
                self.logger.log_warning("No device selected", {"action": "exiting"})
                return
                
            vid, pid, name, dev_config = device_info
            device = self.configure_device(vid, pid, name, dev_config)
            if not device:
                self.logger.log_warning("Failed to configure device", {"action": "exiting"})
                return
                
            # Select visualisation
            if not self.select_visualisation():
                self.logger.log_warning("No visualisation selected", {"action": "exiting"})
                return
                
            # Start device monitoring
            device.start_monitoring()
            
            # Main loop
            while self.running.is_set():
                try:
                    # Process any pending events
                    batch = self.optimisation_manager.batcher.add({
                        "type": "tick",
                        "timestamp": time.time()
                    })
                    
                    if batch:
                        self.optimisation_manager.monitor.measure(
                            "event_processing_time",
                            lambda: self._process_event_batch(batch)
                        )
                    
                    # Process any pending commands
                    if self.selected_visualisation:
                        self.optimisation_manager.monitor.measure(
                            "command_send_time",
                            lambda: self.selected_visualisation.process_commands()
                        )
                        
                    # Sleep briefly to prevent CPU overuse
                    time.sleep(0.01)
                    
                except KeyboardInterrupt:
                    self.logger.log_event("shutdown_signal_received", {"signal": "SIGINT"})
                    self.running.clear()
                    break
                except Exception as e:
                    self.logger.log_error(e, {
                        "device": self.dev_name,
                        "state": None,
                        "config": None
                    })
                    time.sleep(1)  # Prevent rapid error loops
                    
            # Cleanup
            device.stop_monitoring()
            device.close()
            
        except Exception as e:
            self.logger.log_error(e, {
                "device": None,
                "state": None,
                "config": None
            })
        finally:
            self.running.clear()

    def _process_event_batch(self, batch: List[Dict[str, Any]]):
        """Process a batch of events."""
        for event in batch:
            self.optimisation_manager.monitor.metrics.events_processed += 1
            # Process event as needed

    def stop(self):
        """
        Stop the LISU framework and clean up resources.
        """
        self.running.clear()
        if hasattr(self, 'selected_visualisation') and self.selected_visualisation:
            self.selected_visualisation.close()

    def __del__(self):
        """
        Destructor to ensure proper cleanup of resources.
        """
        self.stop()

    def cleanup(self):
        """Clean up resources and log final metrics."""
        self.logger.log_event("framework_shutting_down", {
            **self.logger.get_metrics(),
            **self.optimisation_manager.monitor.get_metrics()
        })
        self.transformation_manager.clear_history()
        self.optimisation_manager.cleanup()
        self.stop()
        self.logger.cleanup()

if __name__ == "__main__":
    lisu = LisuManager()
    lisu.configure_and_run()