from typing import Dict, List, Optional
import pywinusb.hid as hid
import win32com.client
import json
from pathlib import Path
from .logging import LisuLogger
from .devices import InputDevice

class DeviceManager:
    def __init__(self, config_path: str = "data/device_config.json"):
        self.logger = LisuLogger()
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.device_configs = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load device configurations from JSON file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.log_error(e, {"context": "Loading device config"})
                return {}
        return {}
    
    def _save_config(self) -> None:
        """Save device configurations to JSON file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.device_configs, f, indent=4)
            self.logger.log_event("config_saved", {
                "path": str(self.config_path),
                "device_count": len(self.device_configs)
            })
        except Exception as e:
            self.logger.log_error(e, {"context": "Saving device config"})
    
    def detect_new_devices(self) -> List[Dict]:
        """Detect newly connected input devices."""
        new_devices = []
        try:
            # First, detect HID devices
            hid_devices = hid.find_all_hid_devices()
            print(f"\nDetecting HID devices...")
            print(f"Total HID devices found: {len(hid_devices)}")
            
            for device in hid_devices:
                device_id = f"hid_{device.vendor_id:04x}_{device.product_id:04x}"
                if device_id not in self.device_configs:
                    print(f"\nNew HID device detected:")
                    print(f"  Name: {device.product_name}")
                    print(f"  VID: {device.vendor_id:04x}")
                    print(f"  PID: {device.product_id:04x}")
                    
                    device_type = self._determine_device_type(device)
                    new_device = {
                        "name": device.product_name or f"Device_{device_id}",
                        "vid": f"{device.vendor_id:04x}",
                        "pid": f"{device.product_id:04x}",
                        "type": device_type,
                        "library": "pywinusb",
                        "device_id": device_id
                    }
                    new_devices.append(new_device)
            
            # Then, detect non-HID input devices
            wmi = win32com.client.GetObject("winmgmts:")
            input_devices = wmi.InstancesOf("Win32_PnPEntity")
            print(f"\nDetecting non-HID input devices...")
            
            for device in input_devices:
                try:
                    if hasattr(device, 'Name') and device.Name:
                        # Check if it's an input device
                        if any(keyword in device.Name.lower() for keyword in ['mouse', 'keyboard', 'gamepad', 'joystick']):
                            device_id = f"win_{device.DeviceID}"
                            if device_id not in self.device_configs:
                                print(f"\nNew input device detected:")
                                print(f"  Name: {device.Name}")
                                print(f"  Description: {device.Description if hasattr(device, 'Description') else 'N/A'}")
                                print(f"  Device ID: {device.DeviceID}")
                                
                                device_type = self._determine_device_type_from_name(device.Name)
                                new_device = {
                                    "name": device.Name,
                                    "description": device.Description if hasattr(device, 'Description') else '',
                                    "device_id": device_id,
                                    "type": device_type,
                                    "library": "win32",
                                    "class": device.Class if hasattr(device, 'Class') else '',
                                    "manufacturer": device.Manufacturer if hasattr(device, 'Manufacturer') else ''
                                }
                                new_devices.append(new_device)
                except Exception as e:
                    continue
            
            print(f"\nTotal new devices found: {len(new_devices)}")
            return new_devices
            
        except Exception as e:
            print(f"Error detecting devices: {e}")
            self.logger.log_error(e, {"context": "Detecting new devices"})
            return []
    
    def _determine_device_type_from_name(self, name: str) -> str:
        """Determine device type from device name."""
        name_lower = name.lower()
        if "mouse" in name_lower:
            return "mouse"
        elif "keyboard" in name_lower:
            return "keyboard"
        elif "gamepad" in name_lower:
            return "gamepad"
        elif "joystick" in name_lower:
            return "joystick"
        return "unknown"
    
    def _determine_device_type(self, device: hid.HidDevice) -> str:
        """Determine the type of HID device based on its properties."""
        print(f"\nDetermining HID device type:")
        
        # Try to get device type from product name
        product_name = device.product_name.lower()
        if "mouse" in product_name:
            print("  Type: Mouse (Detected from product name)")
            return "mouse"
        elif "keyboard" in product_name:
            print("  Type: Keyboard (Detected from product name)")
            return "keyboard"
        elif "gamepad" in product_name or "joystick" in product_name:
            print("  Type: Gamepad (Detected from product name)")
            return "gamepad"
        
        # Try to get device type from usage page and usage
        try:
            if hasattr(device, 'usage_page') and hasattr(device, 'usage'):
                if device.usage_page == 0x01:  # Generic Desktop Controls
                    if device.usage == 0x02:  # Mouse
                        print("  Type: Mouse (Detected from usage)")
                        return "mouse"
                    elif device.usage == 0x05:  # Gamepad
                        print("  Type: Gamepad (Detected from usage)")
                        return "gamepad"
                    elif device.usage == 0x04:  # Joystick
                        print("  Type: Joystick (Detected from usage)")
                        return "joystick"
                    elif device.usage == 0x06:  # Keyboard
                        print("  Type: Keyboard (Detected from usage)")
                        return "keyboard"
        except Exception as e:
            print(f"  Error checking usage: {e}")
        
        print("  Type: Unknown")
        return "unknown"
    
    def add_device(self, device_info: Dict) -> bool:
        """Add a new device to the configuration."""
        try:
            device_id = device_info.get('device_id')
            if not device_id:
                return False
            
            # Add default configuration based on device type
            if device_info["type"] == "mouse":
                device_info.update({
                    "axes": ["x", "y"],
                    "buttons": ["left_click", "right_click"],
                    "command": "mouse"
                })
            elif device_info["type"] == "gamepad":
                device_info.update({
                    "axes": ["x", "y", "z", "roll"],
                    "buttons": ["button_1", "button_2", "button_3", "button_4"],
                    "command": "gamepad"
                })
            
            self.device_configs[device_id] = device_info
            self._save_config()
            
            self.logger.log_event("device_added", {
                "device": device_info["name"],
                "type": device_info["type"],
                "device_id": device_id
            })
            return True
        except Exception as e:
            self.logger.log_error(e, {"context": "Adding new device"})
            return False
    
    def get_available_devices(self) -> List[Dict]:
        """Get list of all available devices."""
        devices = []
        try:
            # Get HID devices
            hid_devices = hid.find_all_hid_devices()
            for device in hid_devices:
                device_id = f"hid_{device.vendor_id:04x}_{device.product_id:04x}"
                devices.append({
                    "name": device.product_name or f"Device_{device_id}",
                    "vid": f"{device.vendor_id:04x}",
                    "pid": f"{device.product_id:04x}",
                    "type": self._determine_device_type(device),
                    "device_id": device_id,
                    "library": "pywinusb"
                })
            
            # Get non-HID input devices
            wmi = win32com.client.GetObject("winmgmts:")
            input_devices = wmi.InstancesOf("Win32_PnPEntity")
            for device in input_devices:
                try:
                    if hasattr(device, 'Name') and device.Name:
                        if any(keyword in device.Name.lower() for keyword in ['mouse', 'keyboard', 'gamepad', 'joystick']):
                            device_id = f"win_{device.DeviceID}"
                            devices.append({
                                "name": device.Name,
                                "description": device.Description if hasattr(device, 'Description') else '',
                                "device_id": device_id,
                                "type": self._determine_device_type_from_name(device.Name),
                                "library": "win32",
                                "class": device.Class if hasattr(device, 'Class') else '',
                                "manufacturer": device.Manufacturer if hasattr(device, 'Manufacturer') else ''
                            })
                except Exception as e:
                    continue
            
            return devices
        except Exception as e:
            self.logger.log_error(e, {"context": "Getting available devices"})
            return []
    
    def get_configured_devices(self) -> List[Dict]:
        """Get list of all configured devices."""
        return list(self.device_configs.values())
    
    def add_selected_device(self, device: hid.HidDevice) -> bool:
        """Add a selected HID device to the configuration."""
        try:
            device_id = f"{device.vendor_id:04x}_{device.product_id:04x}"
            if device_id in self.device_configs:
                print(f"Device {device.product_name} is already configured.")
                return False
            
            device_type = self._determine_device_type(device)
            device_info = {
                "name": device.product_name or f"Device_{device_id}",
                "vid": f"{device.vendor_id:04x}",
                "pid": f"{device.product_id:04x}",
                "type": device_type,
                "library": "pywinusb",
                "device_id": device_id,
                "axes": [],
                "buttons": [],
                "command": "unknown"
            }
            
            # Add default configuration based on device type
            if device_type == "mouse":
                device_info.update({
                    "axes": ["x", "y"],
                    "buttons": ["left_click", "right_click"],
                    "command": "mouse"
                })
            elif device_type == "gamepad":
                device_info.update({
                    "axes": ["x", "y", "z", "roll"],
                    "buttons": ["button_1", "button_2", "button_3", "button_4"],
                    "command": "gamepad"
                })
            elif device_type == "keyboard":
                device_info.update({
                    "axes": [],
                    "buttons": ["key"],
                    "command": "keyboard"
                })
            
            self.device_configs[device_id] = device_info
            self._save_config()
            
            print(f"\nSuccessfully added device:")
            print(f"  Name: {device_info['name']}")
            print(f"  Type: {device_info['type']}")
            print(f"  VID: {device_info['vid']}")
            print(f"  PID: {device_info['pid']}")
            print(f"  Command: {device_info['command']}")
            
            self.logger.log_event("device_added", {
                "device": device_info["name"],
                "type": device_info["type"],
                "device_id": device_id
            })
            return True
            
        except Exception as e:
            print(f"Error adding device: {e}")
            self.logger.log_error(e, {"context": "Adding selected device"})
            return False 