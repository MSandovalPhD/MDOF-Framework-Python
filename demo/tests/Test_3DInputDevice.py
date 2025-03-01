"""
LISU 2022: Activates a 3D specialized input device from detected controllers.
"""

import qprompt
from src.lisu import LisuManager  # Adjusted import based on your structure
from LISU.datalogging import recordLog

def test_lisu_3d_input() -> None:
    """Test and activate a 3D input device from detected controllers."""
    qprompt.clear()
    print("LISU API - 3D Input Device Test")
    print("Configuring controllers...")
    print("Press Ctrl+C to stop...")

    # List detected devices using LisuManager
    lisu = LisuManager(target_device=None)  # No specific target yet
    device_info = lisu.detect_devices()
    if not device_info:
        print("No 3D input devices detected.")
        recordLog("No 3D input devices detected.")
        qprompt.ask_yesno("Exit? (y/n)", default="y")
        return

    # Select a 3D device (assuming first detected is suitable; refine as needed)
    vid, pid, name, dev_config = device_info
    print(f"Selected device: {name} (VID: {vid}, PID: {pid})")
    recordLog(f"Selected device: {name} (VID: {vid}, PID: {pid})")

    # Configure and run with the detected device
    lisu = LisuManager(target_device=name)
    lisu.run()

if __name__ == "__main__":
    qprompt.clear()
    menu = qprompt.Menu()
    qprompt.echo("LISU (Library for Interactive Settings and Users-modes) 2022")
    qprompt.echo("LISU automatically configures and activates a 3D specialized input device.")
    qprompt.echo("Instructions:")
    qprompt.echo("1. Press 's' to start LISU and activate a 3D input device.")
    qprompt.echo("2. Move the device or press buttons to send actuation commands.")
    qprompt.echo("3. Press Ctrl+C to exit.")
    menu.add("s", "Start!", test_lisu_3d_input)
    menu.add("q", "Quit", lambda: None)

    while menu.show() != "q":
        pass

    qprompt.clear()
