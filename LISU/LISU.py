"""
Handling raw data inputs example
"""
from multiprocessing import *
from msvcrt import kbhit
import socket

from LISU_devices import *
from LISU_getcontrollers import *
from LISU_mouse import *
from Controllers import *
from Actuation import *

import keyboard
import subprocess
import sys

import qprompt

##########################
# global variables
device_specs = {}
supported_devices = []

C = []
_active_device = None
count_state = 0
idx2 = 0
idx3 = 1
_dev_name = ""

#fun_array = ["addrotation %.3f %.3f %.3f 5", "addrotationclip %.3f %.3f %.3f 0"]
fun_array = ["addrotation %.3f %.3f %.3f %s", "addrotationclip %.3f %.3f %.3f %s"]

##########################
class LisuDevicesView(object):
    def __init__(self, d):
        self.__dict__ = d

##########################
def close():
    """Close the active device, if it exists"""
    if _active_device is not None:
        _active_device.close()

###########################
def read():
    """Return the current state of the active navigation controller.
    Returns:
        state: {t,x,y,z,pitch,yaw,roll,button} namedtuple
        None if the device is not open.
    """
    if _active_device is not None:
        return _active_device.tuple_state
    else:
        return None

###########################
def list_devices():
    """Return a list of the supported devices connected
    Returns:
        A list of string names of the devices supported which were found. Empty if no supported devices found
    """
    global device_specs

    devices = []
    all_hids = hid.find_all_hid_devices()
    if all_hids:
        for index, device in enumerate(all_hids):
            for device_name, spec in device_specs.items():
                if (
                    device.vendor_id == spec.hid_id[0]
                    and device.product_id == spec.hid_id[1]
                ):
                    devices.append(device_name)
    return devices

###########################
def callback_function(state):
    global idx2
    global idx3
    global _dev_name
    global count_state

    var_x = None
    var_y = None
    var_z = None
    count_state = count_state + 1

    if abs(getattr(state, "x")) > 0.3:
        var_x = -1 * getattr(state, "x")
    else:
        var_x = 0.0

    if abs(getattr(state, "y")) > 0.2:
        var_y = -1 * getattr(state, "y")
    else:
        var_y = 0.0

    if abs(getattr(state, "z")) > 0.2:
        var_z = 1 * getattr(state, "z")
    else:
        var_z = 0.0

    if abs(getattr(state, "pitch")) > 0.2:
        var_x = -1 * getattr(state, "pitch")
    else:
        var_x = 0.0

    if abs(getattr(state, "yaw")) > 0.2:
        var_y = -1 * getattr(state, "yaw")
    else:
        var_y = 0.0

    if abs(getattr(state, "roll")) > 0.2:
        var_z = 1 * getattr(state, "roll")
    else:
        var_z = 0.0

    #if count_state == 5:
    if count_state == 10:
        if var_x  != 0.0 or var_y != 0.0 or var_z != 0.0:
            message = fun_array[idx2] % (var_x, var_y, var_z, str(idx3))
            print_message = "%s: %s" % (_dev_name, message)
            print(print_message)
            packetHandler(message)
        count_state = 0

###########################
def toggle_led(state, buttons):
    global idx2
    global idx3
    global _dev_name
    global count_state

    # Switch on the led on left push, off on right push
    if buttons[0] == 1:
        idx2 = idx2 + 1
        if idx2 >= 2:
            idx2 = 0
        fun_name = fun_array[idx2].split(" ")
        #fun_name = fun_array[0].split(" ")
        print("%s : " % _dev_name + "button pressed for " + fun_name[0])
        #print("%s : " % _dev_name + "button pressed for " + fun_name[0])
        #idx2 = 0

    if buttons[1] == 1:
        if idx3 == 1:
            idx3 = idx3 + 4
        else:
            idx3 = idx3 + 5
        if idx3 >= 25:
            idx3 = 1
        print("%s : " % _dev_name + "button pressed for sensitivy " + str(idx3))
        #fun_name = fun_array[1].split(" ")
        #print("%s : " % _dev_name + "button pressed for " + fun_name[0])
        #idx2 = 1

###########################
def set_led(state):
    if _active_device:
        _active_device.set_led(state)

###########################
# Activate controllers with already program instructions
def startLisuGamepad(target_vendor_id, target_product_id, device = None, DeviceNumber = 0):
    # if no device name specified, look for any matching device and choose the first
    #print('VID=',hex(target_vendor_id))
    #print('PID=',hex(target_product_id))
    try:
        #Check for gamepad - first
        LisuGamepad(target_vendor_id, target_product_id)
        #Check for 3D input - second
        Lisu3DInput(target_vendor_id, target_product_id)
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt. You can press 'Exit' now.")

###########################
# Activate 1 game controller by name
def LisuGamepadStart(lisudev):
    try:
        if(lisudev == None):
            return False

        lisudevname = lisudev.device_name.strip()
        if lisudevname == "Wireless Controller":
            lisudevname = "PS4 Controller"

        Joystick = Controllers(initStatus, lisudevname,
                xAxisChanged = xAxisChangeHandler,
                yAxisChanged = yAxisChangeHandler,
                zAxisChanged = zAxisChangeHandler,
                triangleBtnChanged = changeActuationHandler,
                squareBtnChanged = subAngleHandler,
                circleBtnChanged = circleBtnHandler,
                crossXBtnChanged = addAngleHandler)

        if hasattr(Joystick,'DOF'):
            print("LISU has found %s" % lisudevname.lstrip())

            DOF = Joystick.DOF
            VecInput = [0] * DOF
            C.append(Joystick.VecInput)

            if Joystick.initialised :
                keepRunning = True
            else:
                keepRunning = False

            print("You can start using %s" % lisudevname.lstrip())

            while keepRunning == True :
                starttime = timeit.default_timer()
                keepRunning = Joystick.controllerStatus()
                P = LisuProcesses(VecInput,lisudevname)

            pygame.quit()
    except:
        print("Something went wrong.")

def LisuGamepadStart2(lisudev, device = None, DeviceNumber = 0):
    global _active_device
    global device_specs
    global _dev_name
    global idx2
    global idx3

    objLisuDevControllers = LisuDevControllers(lisudev.vendor_id,lisudev.product_id)
    device_specs = objLisuDevControllers.dict_devices

    if device == None:
        all_devices = list_devices()
        if len(all_devices) > 0:
            device = all_devices[0]
        else:
            return None

    found_devices = []
    all_hids = hid.HidDeviceFilter(vendor_id = lisudev.vendor_id, product_id = lisudev.product_id).get_devices()

    if not all_hids:
        print("No HID devices detected")
        return None
    else:
        for index, dev in enumerate(all_hids):
            spec = device_specs[device]
            found_devices.append({"Spec":spec,"HIDDevice":dev})
            device_name = str("{0.vendor_name} {0.product_name}".format(dev, dev.vendor_id, dev.product_id))
            _dev_name = device_name.lstrip()
            print("LISU has found %s" % device_name.lstrip())

    if len(found_devices) == 0:
        print("No supported devices found")
        return None
    else:
        if len(found_devices) <= DeviceNumber:
            DeviceNumber = 0

        if len(found_devices) > DeviceNumber:
            # create a copy of the device specification
            spec = found_devices[DeviceNumber]["Spec"]
            dev = found_devices[DeviceNumber]["HIDDevice"]
            new_device = copy.deepcopy(spec)
            new_device.device = dev

            # set the callbacks
            new_device.callback = callback_function
            new_device.button_callback = toggle_led
            # open the device and set the data handler
            try:
                new_device.open()
                dev.set_raw_data_handler(lambda x: new_device.process(x))
                _active_device = new_device
                print("You can start using %s" % device_name.lstrip())

                while not kbhit() and new_device.device.is_plugged():
                    #just keep the device opened to receive events
                    sleep(0.5)
                return
            finally:
                new_device.close()

        print("Unknown error occured.")

###########################
# List game controllers
def GetFromListGamepads(LisuListDevices):
    found_devices = []
    numControllersDetected = len(LisuListDevices)
    for i in range(0, numControllersDetected):
        new_tuple = LisuListDevices[i]
        _vid = new_tuple[0]
        _pid = new_tuple[1]
        #print(hex(_vid), ",", hex(_pid))
        all_hids = hid.HidDeviceFilter(vendor_id = _vid, product_id =_pid).get_devices()

        if not all_hids:
            break
        else:
            for index, dev in enumerate(all_hids):
                device_name = str("{0.vendor_name} {0.product_name}".format(dev, dev.vendor_id, dev.product_id))
                lisudevname = " ".join(dev.product_name.split())
                lisudevname = lisudevname.replace("ACRUX", "")
                if lisudevname == "Wireless Controller":
                    lisudevname = "PS4 Controller"

                Joystick = Controllers(initStatus, lisudevname)

                if hasattr(Joystick,'DOF'):
                    found_devices.append({"device_name":dev.product_name,
                                          "vendo_id":hex(dev.vendor_id),
                                          "product_id":hex(dev.product_id)
                                          })

    if not found_devices:
        print("No HID devices detected")
        return None
    else:
        LisuObject = LisuDevicesView(found_devices[0])
        return LisuObject

###########################
# List 3D specialised input mechanisms
def GetFromList3DInput(LisuListDevices, device = None):
    global _active_device
    global device_specs
    global _dev_name
    global idx2
    global idx3

    found_devices = []
    numControllersDetected = len(LisuListDevices)

    for i in range(0, numControllersDetected):
        new_tuple = LisuListDevices[i]
        _vid = new_tuple[0]
        _pid = new_tuple[1]

        objLisuDevControllers = LisuDevControllers(_vid, _pid)
        device_specs = objLisuDevControllers.dict_devices

        var = get3DInput(_vid, _pid)
        if var:
            found_devices.append(var[0])

    if not found_devices:
        print("No HID devices detected")
        return None
    else:
        LisuObject = LisuDevicesView(found_devices[0])
        return LisuObject

def get3DInput(target_vendor_id, target_product_id, device = None, DeviceNumber = 0):
    global _active_device
    global device_specs
    global _dev_name
    global idx2
    global idx3

    if device == None:
        all_devices = list_devices()
        if len(all_devices) > 0:
            device = all_devices[0]
        else:
            return None

    found_devices = []
    print_found_devices = []
    all_hids = hid.HidDeviceFilter(vendor_id = target_vendor_id, product_id =target_product_id).get_devices()

    if not all_hids:
        print("No HID devices detected")
        return None
    else:
        for index, dev in enumerate(all_hids):
            spec = device_specs[device]
            found_devices.append({"Spec":spec,"HIDDevice":dev})
            device_name = str("{0.vendor_name} {0.product_name}".format(dev, dev.vendor_id, dev.product_id))

    if len(found_devices) == 0:
        print("No supported devices found")
        return None
    else:
        if len(found_devices) <= DeviceNumber:
            DeviceNumber = 0

        if len(found_devices) > DeviceNumber:
            # create a copy of the device specification
            print_found_devices.append({"device_name":dev.product_name,"vendor_id":dev.vendor_id,"product_id":dev.product_id})
            return print_found_devices

###########################
def LisuGamepad(target_vendor_id, target_product_id, device = None, DeviceNumber = 0):
    global _active_device
    global device_specs
    global _dev_name
    global idx2
    global idx3

    found_devices = []
    all_hids = hid.HidDeviceFilter(vendor_id = target_vendor_id, product_id =target_product_id).get_devices()

    if not all_hids:
        print("No HID devices detected")
        return None
    else:
        for index, dev in enumerate(all_hids):
            device_name = str("{0.vendor_name} {0.product_name}".format(dev, dev.vendor_id, dev.product_id))
            lisudevname = " ".join(dev.product_name.split())
            lisudevname = lisudevname.replace("ACRUX", "")
            _dev_name = lisudevname

            if lisudevname == "Wireless Controller":
                lisudevname = "PS4 Controller"

            Joystick = Controllers(initStatus, lisudevname,
                    xAxisChanged = xAxisChangeHandler,
                    yAxisChanged = yAxisChangeHandler,
                    zAxisChanged = zAxisChangeHandler,
                    triangleBtnChanged = changeActuationHandler,
                    squareBtnChanged = subAngleHandler,
                    circleBtnChanged = circleBtnHandler,
                    crossXBtnChanged = addAngleHandler)

            if hasattr(Joystick,'DOF'):
                print("LISU has found %s" % lisudevname.lstrip())

                DOF = Joystick.DOF
                VecInput = [0] * DOF
                C.append(Joystick.VecInput)

                if Joystick.initialised :
                    keepRunning = True
                else:
                    keepRunning = False

                print("You can start using %s" % lisudevname.lstrip())

                while keepRunning == True :
                    starttime = timeit.default_timer()
                    keepRunning = Joystick.controllerStatus()
                    P = LisuProcesses(VecInput,lisudevname)

                pygame.quit()

###########################
def Lisu3DInput(target_vendor_id, target_product_id, device = None, DeviceNumber = 0):
    global _active_device
    global device_specs
    global _dev_name
    global idx2
    global idx3

    if device == None:
        all_devices = list_devices()
        if len(all_devices) > 0:
            device = all_devices[0]
        else:
            return None

    found_devices = []
    all_hids = hid.HidDeviceFilter(vendor_id = target_vendor_id, product_id =target_product_id).get_devices()

    if not all_hids:
        print("No HID devices detected")
        return None
    else:
        for index, dev in enumerate(all_hids):
            spec = device_specs[device]
            found_devices.append({"Spec":spec,"HIDDevice":dev})
            device_name = str("{0.vendor_name} {0.product_name}".format(dev, dev.vendor_id, dev.product_id))
            print("LISU has found %s" % device_name.lstrip())

    if len(found_devices) == 0:
        print("No supported devices found")
        return None
    else:
        if len(found_devices) <= DeviceNumber:
            DeviceNumber = 0

        if len(found_devices) > DeviceNumber:
            # create a copy of the device specification
            spec = found_devices[DeviceNumber]["Spec"]
            dev = found_devices[DeviceNumber]["HIDDevice"]
            new_device = copy.deepcopy(spec)
            new_device.device = dev

            # set the callbacks
            new_device.callback = callback_function
            new_device.button_callback = toggle_led
            # open the device and set the data handler
            try:
                new_device.open()
                dev.set_raw_data_handler(lambda x: new_device.process(x))
                _active_device = new_device
                print("You can start using %s" % device_name.lstrip())

                while not kbhit() and new_device.device.is_plugged():
                    #just keep the device opened to receive events
                    sleep(0.5)
                return
            finally:
                new_device.close()

        print("Unknown error occured.")

###########################
def mainLisuControllers(tuple_list):
    global device_specs
    global supported_devices

    try:
        _vid = tuple_list[0]
        _pid = tuple_list[1]
        objLisuDevControllers = LisuDevControllers(_vid, _pid)

        device_specs = objLisuDevControllers.dict_devices
        supported_devices = list(device_specs.keys())

        dev = startLisuGamepad(_vid, _pid)
        if dev:
            dev.set_led(0)
            while 1:
                sleep(0.5)
                dev.set_led(1)
                sleep(0.5)
                dev.set_led(0)
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt. You can press 'Exit' now.")
##################################################################
# New function to get controller supported individually
def LisuGetInputController(Lisu_tuple_list):
    global supported_devices
    numControllersDetected = len(Lisu_tuple_list)
    LC = []
    try:
        for i in range(0, numControllersDetected):
            new_tuple = Lisu_tuple_list[i]
            _vid = new_tuple[0]
            _pid = new_tuple[1]
            objLisuDevControllers = LisuDevControllers(_vid, _pid)
            if objLisuDevControllers != None:
                LC.append(objLisuDevControllers)

        print(LC)

    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt. You can press 'Exit' now.")
##################################################################
def LisuActivateDevices(LisuListDevices):
    try:
        P = []
        numControllersDetected = len(LisuListDevices)
        # Enabling paralellism to send over port via UDP
        # i: DOF of the raw input data, to direct processes based on number of DOF (i) and actions (j) detected
        for i in range(0, numControllersDetected):
            p = Process(target=mainLisuControllers, args=(LisuListDevices[i], ))
            p.start()
            P.append(p)

        for p in P:
            p.join()

    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt. You can press 'Exit' now.")
