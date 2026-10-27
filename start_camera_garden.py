"""Cross-platform launcher: python start_camera_garden.py --calibrate."""
import argparse
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def main():
    from gesture_trials import pose_configuration
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--mouse-only",action="store_true",help="Use mouse selection with voice; do not open a camera")
    parser.add_argument("--rows", type=int, default=2)
    parser.add_argument("--cols", type=int, default=3)
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--confirm-setup", action="store_true")
    parser.add_argument("--profile", default="camera-profile.json")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--load", help="Saved garden path relative to project folder")
    parser.add_argument("--output", help="Stable save basename for exhibit recovery")
    parser.add_argument("--resilient", action="store_true", help="Retry camera crashes up to three times, keeping garden open")
    parser.add_argument("--gesture-source", choices=("model",), default="model")
    parser.add_argument("--interaction", choices=("click", "legacy"), default="click")
    parser.add_argument("--click-pose", choices=("Closed_Fist","Open_Palm","Victory","Pointing_Up","Thumb_Up"), default="Thumb_Up")
    parser.add_argument("--enable-pinch", action="store_true", help="Also accept experimental pinch rule as the same click")
    parser.add_argument("--voice-input",action="store_true",help="Keyboard-free plant type and automatic planting from dictation")
    parser.add_argument("--mic-device")
    parser.add_argument("--speech-language",default="en-US")
    parser.add_argument("--word-compression",type=float,default=.35)
    parser.add_argument("--growth-words",type=int)
    parser.add_argument("--words-seconds",type=float,default=15.,help="Maximum spoken-thought duration after speech begins")
    parser.add_argument("--plant-pose")
    parser.add_argument("--cultivate-pose")
    args = parser.parse_args()
    if not 0 <= args.word_compression <= 1 or not 1 <= args.words_seconds <= 60:
        parser.error("word-compression must be 0..1 and words-seconds must be 1..60")
    if args.growth_words is not None and not 0 <= args.growth_words <= 100:
        parser.error("growth-words must be 0..100")
    if not args.mouse_only and not args.calibrate and not args.confirm_setup:
        parser.error("Use --calibrate for a new setup or --confirm-setup for an unchanged setup")
    if args.enable_pinch and args.interaction != "click":
        parser.error("--enable-pinch requires single-click interaction")
    if args.voice_input and args.interaction != "click":
        parser.error("--voice-input requires single-click interaction")
    try:
        _, args.plant_pose, args.cultivate_pose = pose_configuration(args.gesture_source, args.plant_pose, args.cultivate_pose)
    except ValueError as exc:
        parser.error(str(exc))
    garden_args = [sys.executable, "-u", str(ROOT/"garden.py"), "--gallery-mode",
                   "--hand-rows", str(args.rows), "--hand-cols", str(args.cols), "--hand-port", str(args.port)]
    garden_args += ["--mouse-only"] if args.mouse_only else ["--hand-stream"]
    if args.load:
        garden_args += ["--load", args.load]
    garden_args += ["--word-compression",str(args.word_compression),"--words-seconds",str(args.words_seconds)]
    if args.growth_words is not None:
        garden_args += ["--growth-words",str(args.growth_words)]
    if args.output:
        garden_args += ["--output", args.output]
    if args.voice_input:
        garden_args += ["--voice-input","--speech-language",args.speech_language]
    if args.mic_device is not None:
        garden_args += ["--mic-device",args.mic_device]
    if args.interaction == "click":
        garden_args += ["--hand-click"]
    else:
        garden_args += ["--legacy-hand-gestures"]
    camera_args = [sys.executable, "-u", str(ROOT/"camera_stream.py"), "--camera", str(args.camera),
                   "--rows", str(args.rows), "--cols", str(args.cols), "--port", str(args.port),
                   "--profile", str(ROOT/args.profile), "--calibrate" if args.calibrate else "--confirm-setup",
                   "--plant-pose", args.plant_pose, "--cultivate-pose", args.cultivate_pose,
                   "--gesture-source", args.gesture_source, "--interaction", args.interaction, "--click-pose", args.click_pose]
    if args.enable_pinch:
        camera_args += ["--enable-pinch"]
    # Camera calibration happens while the garden is already visible.
    garden = subprocess.Popen(garden_args, cwd=ROOT)
    camera = None
    try:
        time.sleep(.8)
        if garden.poll() is not None:
            return garden.returncode or 1
        if args.mouse_only:
            return garden.wait()
        camera = subprocess.Popen(camera_args, cwd=ROOT)
        camera_retries = 0
        while garden.poll() is None:
            if camera.poll() is not None:
                if args.resilient and camera.returncode and camera_retries < 3:
                    camera_retries += 1
                    delay = min(8, 2**camera_retries)
                    print(f"Camera failed; retry {camera_retries}/3 in {delay}s. Keep camera/tray fixed.", flush=True)
                    deadline = time.monotonic()+delay
                    while garden.poll() is None and time.monotonic() < deadline:
                        time.sleep(.2)
                    if garden.poll() is not None:
                        break
                    retry_args = ["--confirm-setup" if value == "--calibrate" else value for value in camera_args]
                    camera = subprocess.Popen(retry_args, cwd=ROOT)
                    continue
                print("Camera stopped. Garden remains usable with mouse; close garden to finish/save.")
                if args.resilient:
                    return garden.wait()
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
