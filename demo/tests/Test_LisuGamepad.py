"""
LISU 2022: Activates a gamepad from detected input controllers.
"""

import qprompt
import cProfile
import pstats
import io
from datetime import datetime
from src.lisu import LisuManager  # Adjusted import
from LISU.datalogging import recordLog
from pathlib import Path

def test_lisu_gamepad() -> None:
    """Test and activate a gamepad from detected controllers."""
    qprompt.clear()
    print("LISU API - Gamepad Test")
    print("Configuring controllers...")
    print("Press Ctrl+C to stop...")

    # List detected devices using LisuManager
    lisu = LisuManager(target_device=None)  # No specific target yet
    device_info = lisu.detect_devices()
    if not device_info:
        print("No gamepads detected.")
        recordLog("No gamepads detected.")
        qprompt.ask_yesno("Exit? (y/n)", default="y")
        return

    # Select a gamepad (assuming first detected; refine if needed)
    vid, pid, name, dev_config = device_info
    if dev_config.get("type") != "gamepad":
        print(f"Detected device {name} is not a gamepad.")
        recordLog(f"Detected device {name} is not a gamepad.")
        qprompt.ask_yesno("Exit? (y/n)", default="y")
        return

    print(f"Selected gamepad: {name} (VID: {vid}, PID: {pid})")
    recordLog(f"Selected gamepad: {name} (VID: {vid}, PID: {pid})")

    # Configure and run with the detected gamepad
    lisu = LisuManager(target_device=name)
    lisu.run()

if __name__ == "__main__":
    # Setup profiler
    profiler = cProfile.Profile()
    profiler.enable()

    qprompt.clear()
    menu = qprompt.Menu()
    qprompt.echo("LISU (Library for Interactive Settings and Users-modes) 2022")
    qprompt.echo("LISU automatically configures and activates a gamepad from detected controllers.")
    qprompt.echo("Instructions:")
    qprompt.echo("1. Press 's' to start LISU and activate a gamepad.")
    qprompt.echo("2. Move the gamepad or press buttons to send actuation commands.")
    qprompt.echo("3. Press Ctrl+C to exit.")
    menu.add("s", "Start!", test_lisu_gamepad)
    menu.add("q", "Quit", lambda: None)

    while menu.show() != "q":
        pass

    qprompt.clear()

    # Save profiler stats
    profiler.disable()
    stats_stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream).sort_stats('tottime')
    stats.print_stats()

    timestr = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = Path("logs")  # Match your framework’s log directory
    log_dir.mkdir(exist_ok=True)  # Ensure directory exists
    with open(log_dir / f"Profiler_LisuGamepad_{timestr}.txt", "w") as f:
        f.write(stats_stream.getvalue())
