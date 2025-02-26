"""
LISU 2022: Activates a gamepad from detected input controllers.
"""

import qprompt
import cProfile
import pstats
import io
from datetime import datetime
from LISU import LisuManager
from LISU_getcontrollers import LisuControllers
from typing import Optional

def test_lisu() -> None:
    """Test and activate a gamepad from detected controllers."""
    qprompt.clear()
    print("LISU API")
    print("Configuring controllers...")
    print("Press 'Ctrl + C' to stop...")

    # Detect controllers
    controllers_detected = LisuControllers.LisuListDevices()
    if not controllers_detected:
        print("No controllers detected.")
        qprompt.ask_yesno(default="y")
        return

    # Initialize LISU manager and start gamepad
    lisu = LisuManager()
    vid, pid = controllers_detected[0]  # Use first detected device
    lisu.start_gamepad(vid, pid)
    qprompt.ask_yesno(default="y")
    qprompt.clear()

if __name__ == "__main__":
    # Setup profiler
    profiler = cProfile.Profile()
    profiler.enable()

    # Display menu
    qprompt.clear()
    menu = qprompt.Menu()
    qprompt.echo("LISU (Library for Interactive Settings and Users-modes) 2022")
    qprompt.echo("LISU automatically configures and activates a gamepad from detected controllers.")
    qprompt.echo("Instructions:")
    qprompt.echo("1. Press 's' to run LISU.")
    qprompt.echo("2. Press your gamepad button to change functions.")
    qprompt.echo("3. Press 'q' to exit.")
    menu.add("s", "Start!", test_lisu)
    menu.add("q", "Quit")

    while menu.show() != "q":
        pass

    qprompt.clear()

    # Save profiler stats
    profiler.disable()
    stats_stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream).sort_stats('tottime')
    stats.print_stats()

    timestr = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = "Logs"
    os.makedirs(log_dir, exist_ok=True)  # Ensure Logs directory exists
    with open(f"{log_dir}/Profiler_LisuGamepad_{timestr}.txt", "w") as f:
        f.write(stats_stream.getvalue())
