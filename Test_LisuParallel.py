"""
LISU 2022. This program activates multiple controllers simultaneously
"""
import os
import sys
import time
import qprompt
import cProfile, pstats, io
from LISU import *
###########################
def testLisu():
    # first be kind with local encodings
    import sys
    if sys.version_info >= (3,):
        # as is, don't handle unicodes
        unicode = str
        raw_input = input
    else:
        # allow to show encoded strings
        import codecs
        sys.stdout = codecs.getwriter('mbcs')(sys.stdout)

    qprompt.clear()
    print("LISU API")
    print("Configuring controllers...")
    print("Press any (system keyboard) key and then 'Ctrl + c' to stop...")
    CONTROLLERS_DETECTED = LisuControllers.LisuListDevices()
    LisuActivateDevices(CONTROLLERS_DETECTED) #Simultaneous
    qprompt.ask_yesno(default="y")
    qprompt.clear()

###########################
if __name__ == '__main__':
    timestr = time.strftime("%Y%m%d-%H%M%S")
    pr = cProfile.Profile()
    pr.enable()

    qprompt.clear()
    menu = qprompt.Menu()
    qprompt.echo("LISU (Library for Interactive Settings and Users-modes) 2022")
    qprompt.echo('LISU automatically configures the input controllers connected to the PC.')
    qprompt.echo('Instructions:')
    qprompt.echo('1. Press the button "Run" to run LISU.')
    qprompt.echo('2. Press your input controller button to change between functions.')
    qprompt.echo('3. Press the "Exit" button to exit.')
    menu.add("s", "Start!", testLisu)
    menu.add("q", "quit")

    while "q" != menu.show():
        pass

    qprompt.clear()

    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('tottime')
    ps.print_stats()

    with open('Logs/Profiler_LisuParallel_'+ timestr + '.txt', 'w+') as f:
        f.write(s.getvalue())
