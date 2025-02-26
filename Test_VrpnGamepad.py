import os
import sys
import time
import subprocess
import cProfile, pstats, io

###########################
if __name__ == '__main__':
    timestr = time.strftime("%Y%m%d-%H%M%S")
    pr = cProfile.Profile()
    pr.enable()

    try:
        #proc  = subprocess.Popen(["C:/Users/mso_2/OneDrive - The University of Manchester/Desktop/Genearted From PC/VR Test/vrpnLisu.v.2.exe"], stdout=subprocess.PIPE)
        proc  = subprocess.Popen(["vrpnLisu_Microsoft.exe"], stdout=subprocess.PIPE)
        for line in proc.stdout:
            print(line.decode("utf-8").strip())

    except KeyboardInterrupt:
        proc.kill()
        print("Got Keyboard interrupt")

    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('tottime')
    ps.print_stats()

    with open('Logs/Profiler_VrpnGamepad_'+ timestr + '.txt', 'w+') as f:
        f.write(s.getvalue())
