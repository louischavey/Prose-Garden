"""Cross-platform launcher: python start_camera_garden.py --calibrate."""
import argparse
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--rows", type=int, default=2)
    parser.add_argument("--cols", type=int, default=3)
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--confirm-setup", action="store_true")
    parser.add_argument("--profile", default="camera-profile.json")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--load", help="Saved garden path relative to project folder")
    args = parser.parse_args()
    if not args.calibrate and not args.confirm_setup:
        parser.error("Use --calibrate for a new setup or --confirm-setup for an unchanged setup")
    garden_args = [sys.executable, str(ROOT/"garden.py"), "--hand-stream", "--gallery-mode",
                   "--hand-rows", str(args.rows), "--hand-cols", str(args.cols), "--hand-port", str(args.port)]
    if args.load:
        garden_args += ["--load", args.load]
    camera_args = [sys.executable, str(ROOT/"camera_stream.py"), "--camera", str(args.camera),
                   "--rows", str(args.rows), "--cols", str(args.cols), "--port", str(args.port),
                   "--profile", str(ROOT/args.profile), "--calibrate" if args.calibrate else "--confirm-setup"]
    # Camera calibration happens while the garden is already visible.
    garden = subprocess.Popen(garden_args, cwd=ROOT)
    camera = None
    try:
        time.sleep(.8)
        if garden.poll() is not None:
            return garden.returncode or 1
        camera = subprocess.Popen(camera_args, cwd=ROOT)
        while garden.poll() is None:
            if camera.poll() is not None:
                print("Camera stopped. Garden remains usable with mouse; close garden to finish/save.")
                return garden.wait() or camera.returncode
            time.sleep(.2)
        return garden.returncode
    except KeyboardInterrupt:
        print("Close the garden window normally to save accepted words.")
        return garden.wait()
    finally:
        if camera is not None and camera.poll() is None:
            camera.terminate()
            try:
                camera.wait(timeout=3)
            except subprocess.TimeoutExpired:
                camera.kill()
                camera.wait()


if __name__ == "__main__":
    raise SystemExit(main())
