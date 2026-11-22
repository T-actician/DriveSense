import os
import sys
from pathlib import Path


def resource_path(rel):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / rel


def data_dir():
    d = Path(os.environ.get("DRIVESENSE_DATA", Path(__file__).resolve().parent.parent / "config"))
    d.mkdir(parents=True, exist_ok=True)
    return d