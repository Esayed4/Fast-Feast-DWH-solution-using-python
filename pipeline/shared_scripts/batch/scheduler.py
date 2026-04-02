# pipeline/batch/scheduler.py

import sys
import os
import schedule
import time
import threading

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from pipeline.batch.batch_runner import run_batch


def job():
    print("=" * 50)
    print("Scheduled batch job started")
    print("=" * 50)
    run_batch()


def run_scheduler():
    schedule.every().day.at("06:00").do(job)
    print("Batch scheduler running in background — waiting for 6:00 AM...")
    while True:
        schedule.run_pending()
        time.sleep(60)


def start_batch_scheduler():
    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()
    print("[OK] Batch scheduler thread started")
    return thread
