import os
import sys
import socket
import keyboard
import pyautogui
import numpy as np

import timeit
import copy
from enum import Enum
from collections import namedtuple

from LISU_datasource import *
from LISU_mouse import *
from Controllers import *

# T: x,y,z R: roll,pitch,yaw
x = 0.0
y = 0.0
z = 0.0
angle = 20.0
speed = 120.0
# For actions
idx = 0
idx2 = 1
action_idx = []
FPS = 20
# HERE FOR THE FUNCTION
count_state = 0
button_state = 0
dev_name = ""
fun_array = ["addrotation %.3f %.3f %.3f %s", "addrotationclip %.3f %.3f %.3f %s"]
#fun_array = ["addrotation %.3f %.3f %.3f 10", "addrotationclip %.3f %.3f %.3f 0"]

###########################
# FPS and Actions dimension
def FPSChangedHandler(val):
    global speed
    if speed >= 372.0:
        speed = 120.0
    val = speed

###########################
def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

###########################
def enumActuation(VecActions):
    global action_idx
    action_idx = [0] * len(VecActions)
    action_idx = VecActions
    print(action_idx)
    return(action_idx)

###########################
def getCurrentActuation():
    global idx
    return(idx)

###########################
# Each movement of the device always causes two HID events, one
# with id 1 and one with id 2, to be generated, one after the other.
class ActuationManager:
    def __init__(self, act_ont):
        self.controller = act_ont.controller
        self.actions = act_ont.actions
        self.ctrname = act_ont.ctrname
        self.usrmod = act_ont.usrmod

###########################
class Actuation:
    #Data for supported controllers
    act_ont = []
    retr_ont = ListAllUserModes()
    for row in retr_ont:
        act_ont.append(ActuationManager(row))

    controller = ()
    actions = ()
    usrmod = ()
    ctrname = ()
    DETECTED_JOYSTICK_IDX = -1

    num_usrmods = len(act_ont)
    for act_idx in range(num_usrmods):
        controller = controller + (str(act_ont[act_idx].usrmod),)
        actions = actions + (str(act_ont[act_idx].usrmod),)
        usrmod = usrmod + (str(act_ont[act_idx].usrmod),)
        ctrname = ctrname + (str(act_ont[act_idx].ctrname),)

    def __init__(self, VecInputController = None):
        self.VecInputController = VecInputController
        self.ctrnameParam = self.VecInputController[idx].productName
        UList = []
        for i in range(0, len(self.ctrname) ) :
            if self.ctrname[i] in self.ctrnameParam:
                self.DETECTED_JOYSTICK_IDX = i
                UList.append(self.usrmod[self.DETECTED_JOYSTICK_IDX])

        self.actuation = UList

###########################
def LisuProcesses(VecInput,lisudevname):
    global idx
    global idx2
    global dev_name
    global count_state
    dev_name = lisudevname
    p =[]
    # Normalise and calibrates
    VecInput = normaliseValue(VecInput)
    VecInput3D = str(np.array2string(VecInput)).strip().lstrip('[ ').rstrip(' ]')
    VecInput3D = " ".join(VecInput3D.split())

    message = "%s :" % lisudevname + " %s" % VecInput

    if VecInput[0] != 0.0 or VecInput[1] != 0.0 or VecInput[2] != 0.0:
        fun_drishti(VecInput)

###########################
# Some functions
def fun_drishti(state):
    # simple default printer callback
    global idx
    global idx2
    global count_state
    global dev_name
    global fun_name
    count_state = count_state + 1
    message = fun_array[idx] % ((-1 * state[0]), -1 * state[1], (1 * state[2]), str(idx2))

    if count_state == 2:
        print("%s : " % dev_name + "%s" % message)
        packetHandler(message)
        count_state = 0
###########################
# To map the any input of any controller to (x, y, z) format
# To be extended to pitch, roll and yaw.
def changeActuationHandler(val):
    global idx
    global idx2
    global dev_name
    global fun_name
    global action_idx

    """ Handler function for the triangle button """
    if val == 1 :
        idx = idx + 1
        if idx >= 2:
            idx = 0
        fun_name = fun_array[idx].split(" ")
        print("%s : " % dev_name + "button pressed for " + fun_name[0])

###########################
def subAngleHandler(val):
    global idx
    global idx2
    global dev_name
    global angle

    """ Handler function for the square button """
    if val == 1 :
        if idx2 == 1:
            idx2 = idx2 + 4
        else:
            idx2 = idx2 + 5
        if idx2 >= 25:
            idx2 = 1

        #print("%s : " % _dev_name + "button pressed for sensitivy ")
        print(idx2)
        #fun_name = fun_array[1].split(" ")
        #print("%s : " % dev_name + "button pressed for " + fun_name[0])
        #idx = 1
###########################
def circleBtnHandler(val):
    """ Handler function for the circle button """
    if val == 1 :
        print("No action programmed here 2...")

###########################
def addAngleHandler(val):
    global angle
    """ Handler function for the cross button """
    if val == 1 :
        print("No action programmed here 1...")
###########################
def xAxisChangeHandler( valLR, valUD ):
    """Callback function which displays the position of the left stick whenever it changes"""
    global x
    x = valLR + valUD

###########################
def yAxisChangeHandler( valLR, valUD ):
    """Callback function which displays the position of the left stick whenever it changes"""
    global y
    y = valLR + valUD

###########################
def zAxisChangeHandler(val):
    """Callback function which displays the position of the left trigger whenever it changes"""
    global z
    z = val

###########################
# For calibration:
def map_range(v, InputRange):
    old_min, old_max, new_min, new_max = InputRange
    return (new_min + (new_max - new_min) * (v - old_min) / (old_max - old_min))

# n: exponent for precision
# n > 1: Increase precision for low input values
# n == 1: No effect
# n < 1 && n > 0: Increase precision for high input values
# n < 0: No sense
def dzSlopedScaledAxial(stick_input, deadzone, n=1):
    x_val = 0
    y_val = 0
    z_val = 0
    deadzone_x = deadzone * np.power(abs(stick_input[2]), n)
    deadzone_y = deadzone * np.power(abs(stick_input[1]), n)
    deadzone_z = deadzone * np.power(abs(stick_input[0]), n)
    sign = np.sign(stick_input)
    if abs(stick_input[0]) > deadzone_x:
        x_val = sign[0] * map_range(abs(stick_input[0]), (deadzone_x, 1, 0, 1))
    if abs(stick_input[1]) > deadzone_y:
        y_val = sign[1] * map_range(abs(stick_input[1]), (deadzone_y, 1, 0, 1))
    if abs(stick_input[2]) > deadzone_z:
        z_val = sign[2] * map_range(abs(stick_input[2]), (deadzone_z, 1, 0, 1))
    return x_val, y_val, z_val

###########################
def dzScaledRadial(stick_input, deadzone):
    input_magnitude = np.linalg.norm(stick_input)
    if input_magnitude < deadzone:
        return 0
    else:
        input_normalized = stick_input / input_magnitude
        # Formula:
        # max_value = 1
        # min_value = 0
        # retval = input_normalized * (min_value + (max_value - min_value) * ((input_magnitude - deadzone) / (max_value - deadzone)))
        retval = input_normalized * map_range(input_magnitude, (deadzone, 1, 0, 1))
        return retval[0], retval[1], retval[2]

###########################
def dzCalibration(stick_input, deadzone):
    # First, check that input does not fall within deadzone
    input_magnitude = np.linalg.norm(stick_input)
    if input_magnitude < deadzone:
        return 0, 0, 0
    # Then apply a scaled_radial transformation
    partial_output = dzScaledRadial(stick_input, deadzone)
    # Then apply a sloped_scaled_axial transformation
    final_output = dzSlopedScaledAxial(partial_output, deadzone)
    return final_output

###########################
def normaliseValue(input_pwn, deadzone = 0.3):
    VecInputM = [ -1 * x, y, z]
    for i in range(len(VecInputM)):
        input_pwn[i] = VecInputM[i]

    # Frist, calibrate the controller
    input_pwn = dzCalibration(input_pwn, deadzone)
    np.set_printoptions(formatter={'float' : lambda x: '%6.4f' % x})
    input_pwn = np.round(np.array(input_pwn),4)
    input_pwn.flatten()

    # Then normalised values
    for i in range(len(input_pwn)):
        if input_pwn[i] > 1.0:
            input_pwn[i] = 1.0

        elif input_pwn[i] < -1.0:
            input_pwn[i] = -1.0

    return input_pwn

###########################
# To send the packet
def packetHandler(packet):
    UDP_IP = "127.0.0.1"
    UDP_PORT = 7755
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    byt = packet.encode()
    sock.sendto(byt, (UDP_IP, UDP_PORT))
