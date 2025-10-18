from __future__ import annotations
from pathlib import Path


def output_path(filename: str) -> str:
    root = Path(__file__).resolve().parents[2] # architect_ai/
    out = root / "output" / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    return str(out)