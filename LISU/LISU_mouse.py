'''
Move cursor with any Controller.
'''
from threading import Thread
from time import sleep
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
import mouse
import keyboard

VELOCITY = .3
SPF = .016
DEADZONE = .25

SCALE = VELOCITY / SPF

def mouse_action():
    mouse.click('left')

def move(dx, dy):
    x, y = mouse.get_position()
    x += dx
    y += dy
    mouse.move(x, y)

class Worker(Thread):
    def __init__(self) -> None:
        super().__init__()
        self.dx = 0
        self.dy = 0
        self.go_on = True

    def run(self):
        while self.go_on:
            move(self.dx, self.dy)
            sleep(SPF)
