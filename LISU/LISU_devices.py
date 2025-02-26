"""
Handling raw data inputs example
"""
from time import sleep
import pywinusb.hid as hid
from collections import namedtuple
import timeit
import copy
from pywinusb.hid import usage_pages, helpers, winapi

from LISU_datasource import *

# current version number
__version__ = "0.3.1"

# clock for timing
high_acc_clock = timeit.default_timer

GENERIC_PAGE = 0x1
BUTTON_PAGE = 0x9
LED_PAGE = 0x8
MULTI_AXIS_CONTROLLER_CAP = 0x8

HID_AXIS_MAP = {
    0x30: "x",
    0x31: "y",
    0x32: "z",
    0x33: "roll",
    0x34: "pitch",
    0x35: "yaw",
}

import pprint

AxisSpec = namedtuple("AxisSpec", ["channel", "byte1", "byte2", "scale"])
ButtonSpec = namedtuple("ButtonSpec", ["channel", "byte", "bit"])

def to_int16(y1, y2):
    x = (y1) | (y2 << 8)
    if x >= 32768:
        x = -(65536 - x)
    return x

# tuple for 6DOF results
LisuDevice = namedtuple(
    "LisuDevice", ["t", "x", "y", "z", "roll", "pitch", "yaw", "buttons"]
)

class LisuDictionary(object):
    def __init__(self, name, device_specs):
        self.name = name
        self.device_specs = device_specs

class LisuMappings(object):
    def __init__(self, x, y, z, pitch, yaw, raw):
        self.x = x
        self.y = y
        self.z = z
        self.pitch = pitch
        self.roll = roll
        self.yaw = yaw

class LisuControllersManager:
    def __init__(self, ctr_ont):
        self.name = ctr_ont.name
        self.x_channel = int(ctr_ont.x_channel)
        self.x_byte1 = int(ctr_ont.x_byte1)
        self.x_byte2 = int(ctr_ont.x_byte2)
        self.x_scale = int(ctr_ont.x_scale)
        self.y_channel = int(ctr_ont.y_channel)
        self.y_byte1 = int(ctr_ont.y_byte1)
        self.y_byte2 = int(ctr_ont.y_byte2)
        self.y_scale = int(ctr_ont.y_scale)
        self.z_channel = int(ctr_ont.z_channel)
        self.z_byte1 = int(ctr_ont.z_byte1)
        self.z_byte2 = int(ctr_ont.z_byte2)
        self.z_scale = int(ctr_ont.z_scale)
        self.pitch_channel = int(ctr_ont.pitch_channel)
        self.pitch_byte1 = int(ctr_ont.pitch_byte1)
        self.pitch_byte2 = int(ctr_ont.pitch_byte2)
        self.pitch_scale = int(ctr_ont.pitch_scale)
        self.roll_channel = int(ctr_ont.roll_channel)
        self.roll_byte1 = int(ctr_ont.roll_byte1)
        self.roll_byte2 = int(ctr_ont.roll_byte2)
        self.roll_scale = int(ctr_ont.roll_scale)
        self.yaw_channel = int(ctr_ont.yaw_channel)
        self.yaw_byte1 = int(ctr_ont.yaw_byte1)
        self.yaw_byte2 = int(ctr_ont.yaw_byte2)
        self.yaw_scale = int(ctr_ont.yaw_scale)
        self.btn1_channel = int(ctr_ont.btn1_channel)
        self.btn1_byte = int(ctr_ont.btn1_byte)
        self.btn1_bit = int(ctr_ont.btn1_bit)
        self.btn2_channel = int(ctr_ont.btn2_channel)
        self.btn2_byte = int(ctr_ont.btn2_byte)
        self.btn2_bit = int(ctr_ont.btn2_bit)

class LisuDevControllers:
    #Data for supported controllers
    def __init__(self, vid_id, pid_id):
        ctr_ont = []        
        oOntCtrl = OntCtrl(hex(vid_id), hex(pid_id))
        retr_ont = oOntCtrl.LisuDeviceAttributes()
        for row in retr_ont:
            ctr_ont.append(LisuControllersManager(row))

        _dict_devices = {}
        _mappings = {}
        _button_mapping = []
        #Filling Tuples
        num_devices = len(ctr_ont)
        for ctr_idx in range(num_devices):
            _mappings["x"] = AxisSpec(channel = ctr_ont[ctr_idx].x_channel, byte1 = ctr_ont[ctr_idx].x_byte1, byte2 = ctr_ont[ctr_idx].x_byte2, scale = ctr_ont[ctr_idx].x_scale)
            _mappings["y"] = AxisSpec(channel = ctr_ont[ctr_idx].y_channel, byte1 = ctr_ont[ctr_idx].y_byte1, byte2 = ctr_ont[ctr_idx].y_byte2, scale = ctr_ont[ctr_idx].y_scale)
            _mappings["z"] = AxisSpec(channel = ctr_ont[ctr_idx].z_channel, byte1 = ctr_ont[ctr_idx].z_byte1, byte2 = ctr_ont[ctr_idx].z_byte2, scale = ctr_ont[ctr_idx].z_scale)
            _mappings["pitch"] = AxisSpec(channel = ctr_ont[ctr_idx].pitch_channel, byte1 = ctr_ont[ctr_idx].pitch_byte1, byte2 = ctr_ont[ctr_idx].pitch_byte2, scale = ctr_ont[ctr_idx].pitch_scale)
            _mappings["roll"] = AxisSpec(channel = ctr_ont[ctr_idx].roll_channel, byte1 = ctr_ont[ctr_idx].roll_byte1, byte2 = ctr_ont[ctr_idx].roll_byte2, scale = ctr_ont[ctr_idx].roll_scale)
            _mappings["yaw"] = AxisSpec(channel = ctr_ont[ctr_idx].yaw_channel, byte1 = ctr_ont[ctr_idx].yaw_byte1, byte2 = ctr_ont[ctr_idx].yaw_byte2, scale = ctr_ont[ctr_idx].yaw_scale)
            _button_mapping.append(ButtonSpec(channel = ctr_ont[ctr_idx].btn1_channel, byte = ctr_ont[ctr_idx].btn1_byte, bit = ctr_ont[ctr_idx].btn1_bit))
            _button_mapping.append(ButtonSpec(channel = ctr_ont[ctr_idx].btn2_channel, byte = ctr_ont[ctr_idx].btn2_byte, bit = ctr_ont[ctr_idx].btn2_bit))
            _dict_devices [ctr_ont[ctr_idx].name] = DeviceSpec(
                                                    name = ctr_ont[ctr_idx].name,
                                                    hid_id = [vid_id, pid_id],
                                                    led_id=[0x8, 0x4B],
                                                    mappings = _mappings,
                                                    button_mapping = _button_mapping
                                                    )
        self.dict_devices = _dict_devices

class ButtonState(list):
    def __int__(self):
        return sum((b << i) for (i, b) in enumerate(reversed(self)))

class DeviceSpec(object):
    """Holds the specification of a single input device supported by the ontology"""

    def __init__(
        self, name, hid_id, led_id, mappings, button_mapping, axis_scale=350.0
    ):
        self.name = name
        self.hid_id = hid_id
        self.led_id = led_id
        self.mappings = mappings
        self.button_mapping = button_mapping
        self.axis_scale = axis_scale

        self.led_usage = hid.get_full_usage_id(led_id[0], led_id[1])
        # initialise to a vector of 0s for each state
        self.dict_state = {
            "t": -1,
            "x": 0,
            "y": 0,
            "z": 0,
            "roll": 0,
            "pitch": 0,
            "yaw": 0,
            "buttons": ButtonState([0] * len(self.button_mapping)),
        }
        self.tuple_state = LisuDevice(**self.dict_state)

        # start in disconnected state
        self.device = None
        self.callback = None
        self.button_callback = None

    def describe_connection(self):
        """Return string representation of the device, including
        the connection state"""
        if self.device == None:
            return "%s [disconnected]" % (self.name)
        else:
            return "%s connected to %s %s version: %s [serial: %s]" % (
                self.name,
                self.vendor_name,
                self.product_name,
                self.version_number,
                self.serial_number,
            )

    @property
    def connected(self):
        """True if the device has been connected"""
        return self.device is not None

    @property
    def state(self):
        """Return the current value of read()
        Returns: state: {t,x,y,z,pitch,yaw,roll,button} namedtuple
                None if the device is not open.
        """
        return self.read()

    def open(self):
        """Open a connection to the device, if possible"""
        if self.device:
            self.device.open()
        # copy in product details
        self.product_name = self.device.product_name
        self.vendor_name = self.device.vendor_name
        self.version_number = self.device.version_number
        # doesn't seem to work on 3dconnexion devices...
        # serial number will be a byte string, we convert to a hex id
        self.serial_number = "".join(
            ["%02X" % ord(char) for char in self.device.serial_number]
        )

    def set_led(self, state):
        """Set the LED state to state (True or False)"""
        if self.connected:
            reports = self.device.find_output_reports()
            for report in reports:
                if self.led_usage in report:
                    report[self.led_usage] = state
                    report.send()

    def close(self):
        """Close the connection, if it is open"""
        if self.connected:
            self.device.close()
            self.device = None

    def read(self):
        """Return the current state of this navigation controller.
        Returns:
            state: {t,x,y,z,pitch,yaw,roll,button} namedtuple
            None if the device is not open.
        """
        if self.connected:
            return self.tuple_state
        else:
            return None

    def process(self, data):
        """
        Update the state based on the incoming data
        This function updates the state of the DeviceSpec object, giving values for each
        axis [x,y,z,roll,pitch,yaw] in range [-1.0, 1.0]
        The state tuple is only set when all DOF have been read correctly.
        The timestamp (in fractional seconds since the start of the program)  is written as element "t"
        If callback is provided, it is called on with a copy of the current state tuple.
        If button_callback is provided, it is called only on button state changes with the argument (state, button_state).
        Parameters:
            data    The data for this HID event, as returned by the HID callback
        """
        button_changed = False

        #NEED TO TRACK LENGHT OF DATA AS SOME DEVICES MIGHT BE LONGER THAN OTHERS

        for name, (chan, b1, b2, flip) in self.mappings.items():


            if data[0] == chan:

                max_len_data = len(data)

                if(int(b1) < max_len_data and int(b2) < max_len_data):
                    self.dict_state[name] = (
                        flip * to_int16(data[b1], data[b2]) / float(self.axis_scale)
                    )



        for button_index, (chan, byte, bit) in enumerate(self.button_mapping):
            if data[0] == chan:
                button_changed = True
                # update the button vector
                mask = 1 << bit
                self.dict_state["buttons"][button_index] = (
                    1 if (data[byte] & mask) != 0 else 0
                )

        self.dict_state["t"] = high_acc_clock()

        # must receive both parts of the 6DOF state before we return the state dictionary
        if len(self.dict_state) == 8:
            self.tuple_state = LisuDevice(**self.dict_state)

        # call any attached callbacks
        if self.callback:
            self.callback(self.tuple_state)

        # only call the button callback if the button state actually changed
        if self.button_callback and button_changed:
            self.button_callback(self.tuple_state, self.tuple_state.buttons)
