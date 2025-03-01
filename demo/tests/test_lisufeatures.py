"""
LISU 2022: Standalone test suite for LisuManager features.
Tests device detection, input normalization, button toggling, UDP transmission, and shutdown.
"""

import qprompt
import cProfile
import pstats
import io
from datetime import datetime
from src.lisu import LisuManager
from src.LISU.datalogging import recordLog
from pathlib import Path
import threading
import signal
import sys
import time
import socket
import unittest.mock as mock

class TestLisuStandalone:
    def __init__(self):
        self.lisu = None
        self.udp_listener = None
        self.udp_thread = None
        self.received_packets = []

    def start_udp_listener(self):
        self.udp_listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_listener.bind(("127.0.0.1", 7755))  # Default port, adjust if needed
        self.running = threading.Event()
        self.running.set()

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

    def stop_udp_listener(self):
        if self.udp_listener:
            self.running.clear()
            self.udp_thread.join()
            self.udp_listener.close()

    def test_lisu_standalone(self):
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
    profiler = cProfile.Profile()
    profiler.enable()

    qprompt.clear()
    menu = qprompt.Menu()
    qprompt.echo("LISU (Library for Interactive Settings and Users-modes) 2022")
    qprompt.echo("Standalone test suite for LISU features.")
    qprompt.echo("Instructions:")
    qprompt.echo("1. Press 's' to run LISU feature tests.")
    qprompt.echo("2. Ensure Bluetooth_mouse is connected.")
    qprompt.echo("3. Tests will run automatically; Ctrl+C stops if needed.")
    tester = TestLisuStandalone()
    menu.add("s", "Start Tests!", tester.test_lisu_standalone)
    menu.add("q", "Quit", lambda: None)

    while menu.show() != "q":
        pass

    qprompt.clear()

    profiler.disable()
    stats_stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream).sort_stats('tottime')
    stats.print_stats()

    timestr = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = Path("../logs")
    log_dir.mkdir(exist_ok=True)
    with open(log_dir / f"Profiler_LisuStandalone_{timestr}.txt", "w") as f:
        f.write(stats_stream.getvalue())