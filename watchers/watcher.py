"""
File Watcher Module

Monitors the streaming input directory for newly created date/hour partitions

Behavior:
- Watches directories structured as: YYYY-MM-DD/HH/
- Ignores pre-existing folders (only processes newly created ones)
- Optionally filters by a specific run date when --date YYYY-MM-DD is added 
- Ensures each hour is processed exactly once

Usage:
    python main.py watch
    python main.py watch --date YYYY-MM-DD

Dependencies:
- watchdog (filesystem monitoring)
- run_stream (ETL processing entry point)
"""
import logging
import re
import time
from pathlib import Path
from config.settings import STREAM_INPUT_DIR
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from orchestrator.stream_pipeline import run_stream
from queue import Queue, Empty

logger = logging.getLogger(__name__)

HOUR_DIR_RE = re.compile(r"^\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class StreamEventHandler(FileSystemEventHandler):
    """
    Handles file system events for new stream data directories.
    
    This handler watches for new hour-level directories and queues them
    for processing. It includes duplicate detection and date filtering.
    
    """
     
    def __init__(self, processing_queue, run_date=None):
        super().__init__()
        self.run_date = run_date
        self.seen_hours = set()  # To track processed hours and avoid duplicates
        self.processing_queue = processing_queue

    def on_created(self, event):
        """
        Called when a file or directory is created.
        
        Only processes directory creation events
        Includes a settle time to ensure all files in the directory
        have been written before queuing for processing.

        """

        if not event.is_directory:
            return

        path = Path(event.src_path)

        if not self._is_valid_hour_dir(path):
            return
        path_str = str(path)
        if path_str in self.seen_hours:
            return
        
        # Wait to ensure all files are written
        time.sleep(3)
        self.seen_hours.add(path_str)

        # Extract date and hour from directory structure
        date_str = path.parent.name
        hour_str = path.name

        logger.info(f"[DETECT] New partition: {date_str}/{hour_str}")
        
        # Add to queue for async processing
        self.processing_queue.put((date_str, hour_str))

    def _is_valid_hour_dir(self, path: Path) -> bool:

        """
        Validate that a directory matches our expected hour-level pattern.
        """
        # Check 1: Must be an hour-named directory (00-23)
        if not HOUR_DIR_RE.match(path.name):
            return False

        # Check 2: Parent must be date-named directory (YYYY-MM-DD)
        date_str = path.parent.name
        if not DATE_RE.match(date_str):
            logger.warning(f"Invalid date format in parent directory: {date_str}")
            return False

        # Check 3: If we filter by date, ensure it matches
        if self.run_date and date_str != self.run_date:
            logger.warning(f"Skipping {path} - filtered by date (expected {self.run_date})")
            return False

        return True

        
def prescan_existing(watch_dir: Path, processing_queue, run_date=None):
    """
    Scan existing directories - BUT DO NOT ADD THEM TO QUEUE.
    This just logs what exists without processing them.
    """
    logger.info("[PRESCAN] Checking existing folders (will NOT process old data)...")
    
    existing_hours = []
    
    if run_date:
        date_dirs = [watch_dir / run_date] if (watch_dir / run_date).exists() else []
    else:
        date_dirs = [p for p in watch_dir.iterdir() if p.is_dir()] if watch_dir.exists() else []

    for date_dir in date_dirs:
        if not date_dir.exists() or not date_dir.is_dir():
            continue

        if not DATE_RE.match(date_dir.name):
            continue

        for hour_dir in sorted(date_dir.iterdir()):
            if hour_dir.is_dir() and HOUR_DIR_RE.match(hour_dir.name):
                logger.info(f"[PRESCAN] Found: {date_dir.name}/{hour_dir.name}")                # processing_queue.put((date_dir.name, hour_dir.name)) # Add to processing queue
                existing_hours.append(f"{date_dir.name}/{hour_dir.name}")
            
    if existing_hours:
        logger.info(f"[PRESCAN] Found {len(existing_hours)} existing partition(s) (ignored)")
        for hour in existing_hours[:10]:  # Show first 10
            logger.info(f"  - {hour}")
        if len(existing_hours) > 10:
            logger.info(f"  ... and {len(existing_hours) - 10} more")
    else:
        logger.info("[PRESCAN] No existing folders found")               
    return existing_hours    
    
def watcher(run_date = None):
    """
        Main watcher loop.

        Initializes directory monitoring, handles queue processing,
        and triggers ETL execution for new partitions.
    """

    watch_dir = STREAM_INPUT_DIR 
    watch_dir.mkdir(parents=True, exist_ok=True)
    processing_queue = Queue()

    # Prescan existing directories
    # prescan_existing(watch_dir, processing_queue, run_date=run_date)

    event_handler = StreamEventHandler(processing_queue, run_date=run_date)
    observer = Observer()
    observer.schedule(event_handler, str(STREAM_INPUT_DIR), recursive=True)
    observer.start()

    logger.info(f"[WATCHER] Watching directory: {watch_dir}")
    if run_date:
        logger.info(f"[WATCHER] Filtering for date: {run_date}")
    logger.info("[WATCHER] Press Ctrl-C to stop")
    
    try:
        while True:
            try:
                date_str, hour_str = processing_queue.get(timeout=1)  # Wait for new items with a timeout to allow graceful shutdown
                logger.info(f"[QUEUE] Processing {date_str}/{hour_str}")
                metrics = run_stream(date_str, hour_str)

                # Log processing results
                if metrics["total_files_processed"] > 0:
                    logger.info(
                        f"[QUEUE] Completed {date_str}/{hour_str} - "
                        f"Files: {metrics['total_files_processed']}, "
                        f"Rows: {metrics['total_rows_in']} -> "
                        f"Clean: {metrics['total_rows_clean']}, "
                        f"Rejected: {metrics['total_rows_rejected']}"
                    )
                else:
                    logger.info(f"[QUEUE] No files found in {date_str}/{hour_str}")
            except Empty:
                # sleep 0.5 seconds when queue is empty 
                time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("[WATCHER] Interrupted by user")
    finally:
        observer.stop()
        observer.join()
        logger.info("[WATCHER] Stopped")


