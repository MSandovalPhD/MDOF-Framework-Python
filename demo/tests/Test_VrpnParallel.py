"""
Runs and profiles multiple VRPN executables in parallel.
"""

import os
import cProfile
import pstats
import io
from datetime import datetime
from subprocess import Popen
from contextlib import ExitStack
from typing import List

def run_vrpn_parallel(executables: List[str]) -> None:
    """Run multiple VRPN executables in parallel and wait for completion."""
    try:
        with ExitStack() as stack:
            processes = [stack.enter_context(Popen([exe])) for exe in executables]
            stack.callback(lambda: [p.kill() for p in processes if p.poll() is None])
            for process in processes:
                process.wait()
    except KeyboardInterrupt:
        print("Stopped by keyboard interrupt")
    except Exception as e:
        print(f"Error running VRPN executables: {e}")

if __name__ == "__main__":
    # Setup profiler
    profiler = cProfile.Profile()
    profiler.enable()

    # Define executables (relative to script directory)
    executables = ["vrpnLisu_device_0.exe", "vrpnLisu_device_1.exe"]

    # Run the parallel processes
    run_vrpn_parallel(executables)

    # Save profiler stats
    profiler.disable()
    stats_stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream).sort_stats('tottime')
    stats.print_stats()

    timestr = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = "Logs"
    os.makedirs(log_dir, exist_ok=True)  # Ensure Logs directory exists
    with open(f"{log_dir}/Profiler_VrpnParallel_{timestr}.txt", "w") as f:
        f.write(stats_stream.getvalue())
