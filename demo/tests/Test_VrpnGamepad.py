"""
Runs and profiles the vrpnLisu gamepad executable.
"""

import os
import subprocess
import cProfile
import pstats
import io
from datetime import datetime
from typing import Optional

if __name__ == "__main__":
    # Setup profiler
    profiler = cProfile.Profile()
    profiler.enable()

    # Define executable path (relative to script directory)
    executable = "vrpnLisu_Microsoft.exe"  # Adjust if needed

    try:
        # Run the VRPN executable and capture output
        process = subprocess.Popen([executable], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in process.stdout:
            print(line.decode("utf-8").strip())
        process.wait()  # Ensure process completes

    except FileNotFoundError:
        print(f"Error: Could not find executable '{executable}'")
    except KeyboardInterrupt:
        process.kill()
        print("Stopped by keyboard interrupt")
    except Exception as e:
        print(f"Error running executable: {e}")
        if 'process' in locals():
            process.kill()

    # Save profiler stats
    profiler.disable()
    stats_stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream).sort_stats('tottime')
    stats.print_stats()

    timestr = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = "Logs"
    os.makedirs(log_dir, exist_ok=True)  # Ensure Logs directory exists
    with open(f"{log_dir}/Profiler_VrpnGamepad_{timestr}.txt", "w") as f:
        f.write(stats_stream.getvalue())
