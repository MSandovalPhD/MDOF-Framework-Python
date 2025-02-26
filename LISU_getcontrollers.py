"""
Handling getting controllers
"""

from time import sleep
from msvcrt import kbhit

import pywinusb.hid as hid

class LisuControllers:

    def LisuListDevices():
        listVID = []
        listPID = []

        all_hids = hid.find_all_hid_devices()
        if all_hids:
            while True:
                for index, device in enumerate(all_hids):
                    listVID.append(device.vendor_id)
                    listPID.append(device.product_id)
                break;
            else:
                print("There's not any non system HID class device available")

        return list(zip(listVID, listPID))
