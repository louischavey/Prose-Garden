"""Voice exhibit supervisor. Run with the project's virtualenv Python."""
import argparse
from contextlib import contextmanager
from datetime import datetime
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


@contextmanager
def single_instance(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b", buffering=0) as lock:
        if os.fstat(lock.fileno()).st_size == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("An exhibit supervisor is already running. Close it before starting another.") from exc
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def recover(checkpoint, initial=None):
    """Validate before launching: a corrupt save must never become an empty garden."""
    from garden import Garden
    from durable_save import save_json
    backup=checkpoint.with_suffix(".backup.json")
    source = checkpoint if checkpoint.exists() else backup if backup.exists() else initial
    try:
        garden = Garden.load(source) if source is not None else Garden()
    except (ValueError,OSError):
        if source != checkpoint or not backup.exists():
            raise
        garden=Garden.load(backup)
        stamp=datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        checkpoint.replace(checkpoint.with_name(checkpoint.name+f".corrupt-{stamp}"))
        print("Recovered previous checkpoint; preserved corrupt file for inspection.",flush=True)
    if not checkpoint.exists():
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        save_json(checkpoint,garden.pack(),backup=False)
    return checkpoint


def fresh_session(checkpoint):
    """Clear the visible garden for a manual launch, preserving previous accepted work."""
    archive = checkpoint.parent/"previous-sessions"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    for source,suffix in ((checkpoint,"json"),(checkpoint.with_suffix(".backup.json"),"backup.json")):
        if source.exists():
            archive.mkdir(parents=True,exist_ok=True)
            source.replace(archive/f"{checkpoint.stem}-{stamp}.{suffix}")


def stop_tree(child):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            os.killpg(child.pid, signal.SIGKILL)
        else:
            child.kill()
        child.wait()


def start_sync(checkpoint, logs):
    """Publish once per manual launch, independently of the visitor processes."""
    logs.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    log=logs/f"sync-{stamp}.log"
    try:
        with log.open("w",encoding="utf-8") as output:
            subprocess.Popen([sys.executable,"-u",str(ROOT/"sync_garden.py"),
                              "--source",str(checkpoint),"--publish","--non-interactive"],
                             cwd=ROOT,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT)
        print(f"Garden snapshot syncing in background. Result/log: {log}",flush=True)
    except OSError as exc:
        print(f"Snapshot sync could not start; exhibit will continue: {exc}",flush=True)


def supervise(command, checkpoint, logs, initial=None, retries=3):
    logs.mkdir(parents=True, exist_ok=True)
    for attempt in range(retries+1):
        recover(checkpoint, initial)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        log = logs / f"exhibit-{stamp}.log"
        print(f"Starting voice exhibit. Recovery: {checkpoint}\nLog: {log}", flush=True)
        with log.open("w", encoding="utf-8") as output:
            child = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                                     start_new_session=os.name != "nt")
            try:
                code = child.wait()
            except KeyboardInterrupt:
                print("Stopping. Unconfirmed draft is discarded; accepted checkpoint remains.", flush=True)
                stop_tree(child)
                return 130
        if code == 0:
            return 0  # Normal window close is intentional, never a crash.
        stop_tree(child)
        if attempt == retries:
            print(f"Stopped after {retries} crash retries. Inspect {log}", flush=True)
            return code
        delay = min(8, 2**(attempt+1))
        print(f"Process failed ({code}); restarting from accepted checkpoint in {delay}s.", flush=True)
        time.sleep(delay)
    return 1


def main():
    from plant_poem import inside
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/exhibit", help="Persistent save basename")
    parser.add_argument("--load", help="Import an existing garden only if the exhibit checkpoint does not exist")
    parser.add_argument("--resume", action="store_true", help="Compatibility: resume is now the default")
    parser.add_argument("--fresh",action="store_true",help="Explicitly archive the current garden and start empty")
    parser.add_argument("--no-sync",action="store_true",help="Skip the automatic startup Git snapshot publish")
    parser.add_argument("--camera",type=int,default=0)
    parser.add_argument("--mic-device",default="1")
    parser.add_argument("--hold-seconds",type=float,default=.75)
    parser.add_argument("--word-compression",type=float,default=.35)
    parser.add_argument("--words-seconds",type=float,default=15.)
    parser.add_argument("--growth-words",type=int,default=2)
    args, forwarded = parser.parse_known_args()
    if any(value.split("=")[0] in ("--calibrate", "--legacy-hand-gestures", "--interaction") for value in forwarded):
        parser.error("Calibrate separately first; exhibit startup uses the saved setup and single-click voice flow")
    try:
        base = inside(args.output).with_suffix("")
        checkpoint = base.with_suffix(".json")
        initial = inside(args.load) if args.load else None
        command = [sys.executable, "-u", str(ROOT/"start_camera_garden.py"),
                   "--confirm-setup", "--enable-pinch", "--voice-input", "--resilient",
                   "--camera",str(args.camera),"--mic-device",args.mic_device,
                   "--hold-seconds",str(args.hold_seconds),"--word-compression",str(args.word_compression),
                   "--words-seconds",str(args.words_seconds),"--growth-words",str(args.growth_words),
                   "--output", str(base), "--load", str(checkpoint), *forwarded]
        # Global supervisor lock prevents accidental port/microphone competition.
        with single_instance(ROOT/"output/exhibit.lock"):
            if args.fresh:
                fresh_session(checkpoint)
            recover(checkpoint,initial)
            if not args.no_sync:
                start_sync(checkpoint,ROOT/"output/logs")
            return supervise(command, checkpoint, ROOT/"output/logs", initial)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Exhibit could not start: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
