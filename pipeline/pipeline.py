# pipeline/runners/stream_runner.py

from pathlib import Path

from config.settings import STREAM_INPUT_DIR
from pipeline.shared_scripts.extractor import load_file


def run_stream(run_date: str, hour: str):
    hour_dir = STREAM_INPUT_DIR / run_date / hour

    print("=" * 50)
    print("STREAM RUNNER STARTED")
    print(f"Date:   {run_date}")
    print(f"Hour:   {hour}")
    print(f"Folder: {hour_dir}")

    # 1) Check folder exists
    if not hour_dir.exists():
        print("Hour folder does not exist")
        print("=" * 50)
        return

    if not hour_dir.is_dir():
        print("Path exists but is not a directory")
        print("=" * 50)
        return

    # 2) Build expected file paths
    orders_path = hour_dir / "orders.json"
    tickets_path = hour_dir / "tickets.csv"
    events_path = hour_dir / "ticket_events.json"

    # 3) Load files using your shared loader
    orders_df = load_file(orders_path)
    tickets_df = load_file(tickets_path)
    events_df = load_file(events_path)

    # 4) Print what happened
    print("\nLOAD RESULTS")

    if orders_df is None:
        print("orders.json       -> failed to load")
    else:
        print(f"orders.json       -> {len(orders_df)} rows, {len(orders_df.columns)} cols")

    if tickets_df is None:
        print("tickets.csv       -> failed to load")
    else:
        print(f"tickets.csv       -> {len(tickets_df)} rows, {len(tickets_df.columns)} cols")

    if events_df is None:
        print("ticket_events.json -> failed to load")
    else:
        print(f"ticket_events.json -> {len(events_df)} rows, {len(events_df.columns)} cols")

    print("STREAM RUNNER FINISHED")
    print("=" * 50)