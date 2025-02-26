import os
import sys
import time
import logging

timestr2 = time.strftime("%Y%m%d-%H%M%S")

logging.basicConfig(filename=("LISU_" + timestr2 + ".txt"), level=logging.DEBUG, format='%(asctime)s, %(message)s')

def recordLog(message):
    logging.info(message)
