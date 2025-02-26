import os
import sys
import time
import cProfile, pstats, io
from contextlib import ExitStack
from subprocess import Popen

def kill(process):
    if process.poll() is None:  # still running
        process.kill()

###########################
if __name__ == '__main__':

    timestr = time.strftime("%Y%m%d-%H%M%S")
    pr = cProfile.Profile()
    pr.enable()

    try:
        with ExitStack() as stack:  # to clean up properly in case of exceptions
            processes = []
            for program in ['vrpnLisu_device_0.exe', 'vrpnLisu_device_1.exe']:
                processes.append(stack.enter_context(Popen(program)))  # start program
                stack.callback(kill, processes[-1])
            for process in processes:
                process.wait()

    except KeyboardInterrupt:
        print("Got Keyboard interrupt")

    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('tottime')
    ps.print_stats()

    with open('Logs/Profiler_Vrpn2_'+ timestr + '.txt', 'w+') as f:
        f.write(s.getvalue())
