"""
LISU 2022: Activates a 3D specialized input device from detected controllers.
"""

import qprompt
from LISU import LisuManager
from LISU_getcontrollers import LisuControllers
from typing import Optional

def test_lisu() -> None:
    """Test and activate a 3D input device from detected controllers."""
    qprompt.clear()
    print("LISU API")
    print("Configuring controllers...")
    print("Press any key (system keyboard) to stop...")

    # Detect controllers
    controllers_detected = LisuControllers.LisuListDevices()
    if not controllers_detected:
        print("No controllers detected.")
        qprompt.ask_yesno(default="y")
        return

    # Initialize LISU manager and start 3D input
    lisu = LisuManager()
    vid, pid = controllers_detected[0]  # Use first detected device
    lisu.start_3d_input(vid, pid)
    qprompt.ask_yesno(default="y")
    qprompt.clear()

if __name__ == "__main__":
    qprompt.clear()
    menu = qprompt.Menu()
    qprompt.echo("LISU (Library for Interactive Settings and Users-modes) 2022")
    qprompt.echo("LISU automatically configures and activates a 3D specialized input device.")
    qprompt.echo("Instructions:")
    qprompt.echo("1. Press 's' to run LISU.")
    qprompt.echo("2. Press your input controller button to change functions.")
    qprompt.echo("3. Press 'q' to exit.")
    menu.add("s", "Start!", test_lisu)
    menu.add("q", "Quit")

    while menu.show() != "q":
        pass

    qprompt.clear()
