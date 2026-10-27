"""Atomic JSON writes with flushed data and one previous checkpoint."""
import json
import os
from pathlib import Path


def atomic_bytes(path, content):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+".tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        if os.name != "nt":
            descriptor=os.open(path.parent,os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def save_json(path, data, backup=True):
    path=Path(path)
    content=(json.dumps(data,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    if backup and path.exists():
        atomic_bytes(path.with_suffix(".backup.json"),path.read_bytes())
    atomic_bytes(path,content)
