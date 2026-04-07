# pipeline/batch/detector.py

import os
import json
import re
from pathlib import Path
from typing import Iterator

BATCH_INPUT_DIR = "data/input/batch"
STATE_FILE = "data/state/processed_batches.json"

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$") # YYYY-MM-DD


def _load_state() -> dict:
    if Path(STATE_FILE).exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def _save_state(state: dict) -> None:
    Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def mark_batch_processed(batch_date: str) -> None:
    state = _load_state()
    state[batch_date] = {"status": "complete"}
    _save_state(state)


def mark_batch_failed(batch_date: str, reason: str) -> None:
    state = _load_state()
    state[batch_date] = {"status": "failed", "reason": reason}
    _save_state(state)


def get_unprocessed_batches() -> Iterator[Path]:
    state = _load_state()
    batch_root = Path(BATCH_INPUT_DIR)

    if not batch_root.exists():
        return

    folders = [
        entry.name
        for entry in os.scandir(batch_root)
        if entry.is_dir() and _DATE_PATTERN.match(entry.name)
    ]

    folders.sort()

    for folder_name in folders:
        if state.get(folder_name, {}).get("status") == "complete":
            continue
        yield batch_root / folder_name








