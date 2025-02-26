"""
Handles retrieval of connected HID controllers.
"""

import pywinusb.hid as hid
from typing import List, Tuple

class LisuControllers:
    """Manages listing of connected HID controllers."""

    @staticmethod
    def LisuListDevices() -> List[Tuple[int, int]]:
        """
        List all connected HID devices by their VID and PID.

        Returns:
            List of tuples containing (vendor_id, product_id) for each HID device.
            Empty list if no devices are found.
        """
        try:
            all_hids = hid.find_all_hid_devices()
            if not all_hids:
                print("No non-system HID class devices available")
                return []
            return [(device.vendor_id, device.product_id) for device in all_hids]
        except Exception as e:
            print(f"Error listing HID devices: {e}")
            return []

if __name__ == "__main__":
    # Example usage
    devices = LisuControllers.LisuListDevices()
    for vid, pid in devices:
        print(f"VID: {hex(vid)}, PID: {hex(pid)}")
