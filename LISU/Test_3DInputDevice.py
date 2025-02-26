"""
LISU 2022. This program activates a 3D specialised input device from the input controllers detected.
"""

import qprompt
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
    print("Press any (system keyboard) key to stop...")
    CONTROLLERS_DETECTED = LisuControllers.LisuListDevices()
    _3DINPUT = GetFromList3DInput(CONTROLLERS_DETECTED)
    LisuGamepadStart2(_3DINPUT)
    qprompt.ask_yesno(default="y")
    qprompt.clear()


###########################
if __name__ == '__main__':
    qprompt.clear()
    menu = qprompt.Menu()
    qprompt.echo("LISU (Library for Interactive Settings and Users-modes) 2022")
    qprompt.echo('LISU automatically configures and activates a 3D specialised input device from the input controllers detected.')
    qprompt.echo('Instructions:')
    qprompt.echo('1. Press the button "Run" to run LISU.')
    qprompt.echo('2. Press your input controller button to change between functions.')
    qprompt.echo('3. Press the "Exit" button to exit.')
    menu.add("s", "Start!", testLisu)
    menu.add("q", "quit")

    while "q" != menu.show():
        pass

    qprompt.clear()
