"""Export the accepted garden for remote reading; --publish explicitly commits/pushes it."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from durable_save import atomic_bytes, save_json
from plant_poem import ROOT, inside


def export_snapshot(source, destination):
    from garden import Garden
    # Checkpoint replacement is atomic: read one complete accepted version.
    garden=Garden.load(source)
    data=json.loads(json.dumps(garden.pack()))
    latest=destination/"latest.json"
    if latest.exists() and (destination/"README.md").exists() and json.loads(latest.read_text(encoding="utf-8"))==data:
        return False
    save_json(latest,data,backup=False)
    lines=["# Visitor thoughts", "", "Updated: "+datetime.now(timezone.utc).isoformat(), "",
           "Normalized root coordinates use the calibrated garden, with (0, 0) at its top left.", ""]
    for plant in garden.plants:
        lines += [f"## {plant.session.plant.title()} — root ({plant.x:.4f}, {plant.y:.4f})", ""]
        for text in plant.session.submissions:
            # Code blocks preserve visitor text without interpreting it as Markdown.
            lines += ["    "+text.replace("\n","\n    "), ""]
    if not garden.plants:
        lines += ["No plants yet.", ""]
    atomic_bytes(destination/"README.md",("\n".join(lines)+"\n").encode("utf-8"))
    return True


def publish(destination, non_interactive=False):
    files=[str((destination/name).relative_to(ROOT)) for name in ("latest.json","README.md")]
    def git(*args,**kwargs):
        if non_interactive:
            environment=os.environ.copy()
            environment.update(GIT_TERMINAL_PROMPT="0",GCM_INTERACTIVE="Never")
            environment.setdefault("GIT_SSH_COMMAND","ssh -oBatchMode=yes -oConnectTimeout=10")
            kwargs.update(env=environment,timeout=30,stdin=subprocess.DEVNULL)
        return subprocess.run(["git",*args],cwd=ROOT,check=True,**kwargs)
    branch=git("symbolic-ref","--quiet","--short","HEAD",capture_output=True,text=True).stdout.strip()
    changed=git("status","--porcelain","--",*files,capture_output=True,text=True).stdout
    if changed:
        git("add","--",*files)
        git("commit","--only","-m","Update visitor garden snapshot","--",*files)
    # A previously failed push is retried even when the checkpoint did not change.
    git("push","origin",f"HEAD:refs/heads/{branch}")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",default="output/exhibit.json")
    parser.add_argument("--publish",action="store_true",help="Commit only snapshot files and push current branch to origin")
    parser.add_argument("--non-interactive",action="store_true",help="No Git credential prompts; bound each Git command to 30 seconds")
    args=parser.parse_args()
    try:
        from run_exhibit import single_instance
        with single_instance(ROOT/"output/snapshot-sync.lock"):
            destination=ROOT/"visitor-data"
            export_snapshot(inside(args.source),destination)
            print(f"Snapshot ready: {destination/'README.md'}")
            if args.publish:
                publish(destination,non_interactive=args.non_interactive)
                print("Garden snapshot published successfully.")
            else:
                print("Export only. Add --publish to commit and push the snapshot.")
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
        parser.exit(1,f"Snapshot sync failed; local exhibit saves remain intact: {exc}\n")


if __name__=="__main__":
    main()
