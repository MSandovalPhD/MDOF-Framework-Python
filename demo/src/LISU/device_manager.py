from typing import Dict, List, Optional
import pywinusb.hid as hid
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
        """Detect newly connected HID devices."""
        new_devices = []
        try:
            all_devices = hid.find_all_hid_devices()
            for device in all_devices:
                device_id = f"{device.vendor_id:04x}_{device.product_id:04x}"
                if device_id not in self.device_configs:
                    new_devices.append({
                        "name": device.product_name or f"Device_{device_id}",
                        "vid": f"{device.vendor_id:04x}",
                        "pid": f"{device.product_id:04x}",
                        "type": self._determine_device_type(device),
                        "library": "pywinusb"
                    })
        except Exception as e:
            self.logger.log_error(e, {"context": "Detecting new devices"})
        return new_devices
    
    def _determine_device_type(self, device: hid.HidDevice) -> str:
        """Determine the type of device based on its properties."""
        # Check if it's a mouse
        if device.usage_page == 0x01 and device.usage == 0x02:
            return "mouse"
        # Check if it's a gamepad/joystick
        elif device.usage_page == 0x01 and device.usage == 0x05:
            return "gamepad"
        # Default to unknown
        return "unknown"
    
    def add_device(self, device_info: Dict) -> bool:
        """Add a new device to the configuration."""
        try:
            device_id = f"{device_info['vid']}_{device_info['pid']}"
            
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
                "vid": device_info["vid"],
                "pid": device_info["pid"]
            })
            return True
        except Exception as e:
            self.logger.log_error(e, {"context": "Adding new device"})
            return False
    
    def get_available_devices(self) -> List[Dict]:
        """Get list of all available devices."""
        try:
            all_devices = hid.find_all_hid_devices()
            return [{
                "name": device.product_name or f"Device_{device.vendor_id:04x}_{device.product_id:04x}",
                "vid": f"{device.vendor_id:04x}",
                "pid": f"{device.product_id:04x}",
                "type": self._determine_device_type(device)
            } for device in all_devices]
        except Exception as e:
            self.logger.log_error(e, {"context": "Getting available devices"})
            return []
    
    def get_configured_devices(self) -> List[Dict]:
        """Get list of all configured devices."""
        return list(self.device_configs.values()) 