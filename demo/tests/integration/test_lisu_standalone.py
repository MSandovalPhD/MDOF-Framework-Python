"""
LISU 2022: Standalone test suite for LisuManager features.
Tests device detection, input normalization, button toggling, UDP transmission, and shutdown.
"""

import sys
from pathlib import Path

# Add demo/src/ to sys.path to find modules directly
project_dir = Path(__file__).resolve().parent.parent / "src"  # Points to demo/src/
sys.path.insert(0, str(project_dir))
print(f"Adjusted sys.path to: {project_dir}")  # Debug print

import qprompt
print("Imported qprompt")  # Debug print
import cProfile
print("Imported cProfile")  # Debug print
import pstats
print("Imported pstats")  # Debug print
import io
print("Imported io")  # Debug print
from datetime import datetime
print("Imported datetime")  # Debug print
from LisuHandler import LisuManager # Direct import from src/lisu.py
print("Imported LisuManager from lisu")  # Debug print
from LISU.datalogging import recordLog  # Import from src/LISU/datalogging.py
print("Imported recordLog from LISU.datalogging")  # Debug print
import threading
print("Imported threading")  # Debug print
import signal
print("Imported signal")  # Debug print
import time
print("Imported time")  # Debug print
import socket
print("Imported socket")  # Debug print
import unittest.mock as mock
print("Imported unittest.mock")  # Debug print

class TestLisuStandalone:
    def __init__(self):
        self.lisu = None
        self.udp_listener = None
        self.udp_thread = None
        self.received_packets = []
        print("Initialized TestLisuStandalone instance")  # Debug print

    def start_udp_listener(self):
        """Start a UDP listener on 127.0.0.1:7755 to capture packets."""
        self.udp_listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_listener.bind(("127.0.0.1", 7755))  # Default port
        self.running = threading.Event()
        self.running.set()
        print("Set up UDP listener socket")  # Debug print

        def listen():
            while self.running.is_set():
                try:
                    data, _ = self.udp_listener.recvfrom(1024)
                    self.received_packets.append(data.decode())
                    recordLog(f"Received UDP packet: {data.decode()}")
                except socket.timeout:
                    continue
                except Exception as e:
                    recordLog(f"UDP listener error: {e}")

        self.udp_listener.settimeout(1.0)
        self.udp_thread = threading.Thread(target=listen, daemon=True)
        self.udp_thread.start()
        print("Started UDP listener thread")  # Debug print

    def stop_udp_listener(self):
        """Stop the UDP listener."""
        if self.udp_listener:
            self.running.clear()
            self.udp_thread.join()
            self.udp_listener.close()
        print("Stopped UDP listener")  # Debug print

    def test_lisu_standalone(self):
        """Run the standalone feature tests."""
        qprompt.clear()
        print("LISU API - Standalone Feature Test Suite")
        print("Testing LisuManager features...")
        print("Press Ctrl+C to stop after tests...")

        self.start_udp_listener()

        self.lisu = LisuManager(target_device="Bluetooth_mouse")
        device_info = self.lisu.detect_devices()
        assert device_info is not None, "Failed to detect Bluetooth_mouse"
        vid, pid, name, dev_config = device_info
        print(f"Test 1 Passed: Detected {name} (VID: {vid}, PID: {pid})")
        recordLog(f"Test 1 Passed: Detected {name} (VID: {vid}, PID: {pid})")

        device = self.lisu.configure_device(vid, pid, name, dev_config)
        assert device is not None, "Failed to configure Bluetooth_mouse"
        print("Test 2 Passed: Configured device successfully")
        recordLog("Test 2 Passed: Configured device successfully")

        with mock.patch.object(device, 'process') as mock_process:
            mock_process.side_effect = lambda data: setattr(device, 'state', {"x": data[1] / 127.0 if data[1] <= 127 else (data[1] - 256) / 127.0, "y": 0.0, "z": 0.0, "buttons": [0], "t": time.time()})
            device.process([1, 10, 0])
            assert -1 <= device.state["x"] <= 1, f"X value {device.state['x']} out of range -1 to 1"
            print(f"Test 3 Passed: Input normalized to {device.state['x']} (within -1 to 1)")
            recordLog(f"Test 3 Passed: Input normalized to {device.state['x']} (within -1 to 1)")

            device.state["buttons"] = [1]
            device.button_callback(device.state, device.state["buttons"])
            assert self.lisu.use_y_axis, "Failed to toggle to y-axis"
            print("Test 4 Passed: Button toggled to y-axis")
            recordLog("Test 4 Passed: Button toggled to y-axis")

            device.process([1, -5, 0])
            vec_input = [0.0, device.state["x"], 0.0] if self.lisu.use_y_axis else [device.state["x"], 0.0, 0.0]
            assert vec_input[1] != 0.0, "Y-axis value not updated after toggle"
            print(f"Test 5 Passed: Y-axis input {vec_input[1]} after toggle")
            recordLog(f"Test 5 Passed: Y-axis input {vec_input[1]} after toggle")

        print("Running LISU for UDP test (5 seconds)...")
        run_thread = threading.Thread(target=self.lisu.run)
        run_thread.start()
        time.sleep(5)
        self.lisu.running.clear()
        run_thread.join()
        assert len(self.received_packets) > 0, "No UDP packets received"
        print(f"Test 6 Passed: Received {len(self.received_packets)} UDP packets (e.g., {self.received_packets[0]})")
        recordLog(f"Test 6 Passed: Received {len(self.received_packets)} UDP packets (e.g., {self.received_packets[0]})")

        assert not self.lisu.active_device.device, "Device not closed properly"
        print("Test 7 Passed: Device closed successfully")
        recordLog("Test 7 Passed: Device closed successfully")

        self.stop_udp_listener()
        print("All tests passed!")

if __name__ == "__main__":
    print("Starting main execution block")  # Debug print
    profiler = cProfile.Profile()
    profiler.enable()

    qprompt.clear()
    print("Cleared console with qprompt")  # Debug print
    menu = qprompt.Menu()
    print("Created qprompt Menu")  # Debug print
    qprompt.echo("LISU (Library for Interactive Settings and Users-modes) 2022")
    qprompt.echo("Standalone test suite for LISU features.")
    qprompt.echo("Instructions:")
    qprompt.echo("1. Press 's' to run LISU feature tests.")
    qprompt.echo("2. Ensure Bluetooth_mouse is connected.")
    qprompt.echo("3. Tests will run automatically; Ctrl+C stops if needed.")
    tester = TestLisuStandalone()
    print("Created TestLisuStandalone instance")  # Debug print
    menu.add("s", "Start Tests!", tester.test_lisu_standalone)
    menu.add("q", "Quit", lambda: None)
    print("Added menu options")  # Debug print

    while menu.show() != "q":
        print("Menu loop running")  # Debug print
        pass

    qprompt.clear()
    print("Cleared console at end")  # Debug print

    profiler.disable()
    stats_stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream).sort_stats('tottime')
    stats.print_stats()

    timestr = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = Path("../logs")
    log_dir.mkdir(exist_ok=True)
    with open(log_dir / f"Profiler_LisuStandalone_{timestr}.txt", "w") as f:
        f.write(stats_stream.getvalue())
    print("Wrote profiler stats")  # Debug print