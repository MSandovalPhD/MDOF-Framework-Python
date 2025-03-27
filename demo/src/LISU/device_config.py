import sys
from typing import Dict, List
from .device_manager import DeviceManager
from .logging import LisuLogger

def print_device_list(devices: List[Dict], title: str = "Available Devices:") -> None:
    """Print a formatted list of devices."""
    print(f"\n{title}")
    print("-" * 50)
    for i, device in enumerate(devices, 1):
        print(f"{i}. {device['name']} (VID: {device['vid']}, PID: {device['pid']}, Type: {device['type']})")
    print("-" * 50)

def get_user_choice(prompt: str, valid_choices: List[str]) -> str:
    """Get user input with validation."""
    while True:
        choice = input(prompt).lower()
        if choice in valid_choices:
            return choice
        print(f"Invalid choice. Please choose from: {', '.join(valid_choices)}")

def configure_new_device(device_manager: DeviceManager, from_main: bool = False) -> None:
    """Handle the process of detecting and configuring new devices."""
    logger = LisuLogger()
    
    # Detect new devices
    new_devices = device_manager.detect_new_devices()
    if not new_devices:
        print("\nNo new devices detected.")
        return
    
    print_device_list(new_devices, "New Devices Detected:")
    
    # Ask if user wants to configure any new devices
    choice = get_user_choice("\nWould you like to configure any of these devices? (y/n): ", ["y", "n"])
    if choice == "n":
        return
    
    # Let user select which devices to configure
    while True:
        try:
            device_index = int(input("\nEnter the number of the device to configure (or 0 to finish): ")) - 1
            if device_index == -1:
                break
            if 0 <= device_index < len(new_devices):
                device = new_devices[device_index]
                if device_manager.add_device(device):
                    print(f"\nSuccessfully configured {device['name']}")
                    if from_main:
                        return device  # Return the configured device for immediate use
                else:
                    print(f"\nFailed to configure {device['name']}")
            else:
                print("Invalid device number.")
        except ValueError:
            print("Please enter a valid number.")
        
        choice = get_user_choice("\nConfigure another device? (y/n): ", ["y", "n"])
        if choice == "n":
            break
    
    if from_main:
        return None  # Return None if no device was configured

def main():
    """Main entry point for device configuration."""
    try:
        device_manager = DeviceManager()
        
        while True:
            print("\nDevice Configuration Menu:")
            print("1. Detect and configure new devices")
            print("2. List all configured devices")
            print("3. Exit")
            
            choice = get_user_choice("\nEnter your choice (1-3): ", ["1", "2", "3"])
            
            if choice == "1":
                configure_new_device(device_manager)
            elif choice == "2":
                configured_devices = device_manager.get_configured_devices()
                print_device_list(configured_devices, "Configured Devices:")
            elif choice == "3":
                print("\nExiting device configuration...")
                break
        
    except Exception as e:
        logger.log_error(e, {"context": "Device configuration"})
        print(f"\nAn error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 