# pipline file watcher
import re
import time
from pathlib import Path
from config.settings import STREAM_INPUT_DIR
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pipeline.pipeline import run_stream
from queue import Queue, Empty


HOUR_DIR_RE = re.compile(r"^\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class StreamEventHandler(FileSystemEventHandler):
    def __init__(self, processing_queue, run_date=None):
        super().__init__()
        self.run_date = run_date
        self.seen_hours = set()  # To track processed hours and avoid duplicates
        self.processing_queue = processing_queue

    def on_created(self, event):
        if not event.is_directory:
            return

        path = Path(event.src_path)

        if not self._is_valid_hour_dir(path):
            return
        path_str = str(path)
        if path_str in self.seen_hours:
            return
        self.seen_hours.add(path_str)

        date_str = path.parent.name
        hour_str = path.name

        print(f"[NEW] Detected hour folder: {date_str}/{hour_str}")
        self.processing_queue.put((date_str, hour_str))

    def _is_valid_hour_dir(self, path: Path) -> bool:
        # Last folder must be HH
        if not HOUR_DIR_RE.match(path.name):
            return False

        # Parent folder must be YYYY-MM-DD
        date_str = path.parent.name
        if not DATE_RE.match(date_str):
            return False

         # If specific date mode, only allow that date
        if self.run_date and date_str != self.run_date:
            return False

        return True

        
def prescan_existing(watch_dir: Path, processing_queue, run_date=None):
    print("Pre-scanning existing folders...")

    if run_date:
        date_dirs = [watch_dir / run_date]
    else:
        date_dirs = [p for p in watch_dir.iterdir() if p.is_dir()] if watch_dir.exists() else []

    for date_dir in date_dirs:
        if not date_dir.exists() or not date_dir.is_dir():
            continue

        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_dir.name):
            continue

        for hour_dir in sorted(date_dir.iterdir()):
            if hour_dir.is_dir() and HOUR_DIR_RE.match(hour_dir.name):
                print(f"[OLD] Found existing hour folder: {date_dir.name}/{hour_dir.name}")
                processing_queue.put((date_dir.name, hour_dir.name)) # Add to processing queue

def watcher(run_date = None):

    watch_dir = STREAM_INPUT_DIR 
    watch_dir.mkdir(parents=True, exist_ok=True)
    processing_queue = Queue()
    prescan_existing(watch_dir, processing_queue, run_date=run_date)

    event_handler = StreamEventHandler(processing_queue, run_date=run_date)
    observer = Observer()
    observer.schedule(event_handler, str(STREAM_INPUT_DIR), recursive=True)
    observer.start()
    print("Watcher started")
    print(f"Watching: {watch_dir}")
    print(f"run_date: {run_date}")
    print("Press Ctrl-C to stop")
    
    try:
        while True:
            try:
                date_str, hour_str = processing_queue.get(timeout=1)  # Wait for new items with a timeout to allow graceful shutdown
                print(f"[QUEUE] Processing {date_str}/{hour_str}")
                run_stream(date_str, hour_str)

            except Empty:
                time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    print("Watcher stopped.")


