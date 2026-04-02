# run_pipeline.py
"""
Main entry point for the data pipeline
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path

from pipeline.runners.pipeline_runner import PipelineRunner
from pipeline.watcher import FileWatcher
from config import settings as s

# Configure logging
logging.basicConfig(
    level=s.LOG_LEVEL,
    format=s.LOG_FORMAT
)
logger = logging.getLogger(__name__)


def run_stream(run_date: str, hour: str):
    """Run pipeline in stream mode for a specific hour"""
    logger.info(f"Starting stream mode for {run_date} {hour}")
    runner = PipelineRunner(run_date, hour)
    metrics = runner.run()
    return metrics


def run_batch(run_date: str):
    """Run pipeline in batch mode for a specific date"""
    logger.info(f"Starting batch mode for {run_date}")
    
    # Process batch files
    batch_dir = s.BATCH_INPUT_DIR / run_date
    if not batch_dir.exists():
        logger.error(f"Batch directory not found: {batch_dir}")
        return
    
    runner = PipelineRunner(run_date)
    
    # Override input dir for batch
    runner.input_dir = batch_dir
    metrics = runner.run()
    return metrics


def run_watcher():
    """Run pipeline in watcher mode (monitor for new files)"""
    logger.info("Starting watcher mode")
    watcher = FileWatcher(s.STREAM_INPUT_DIR)
    watcher.watch()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data Pipeline Runner")
    parser.add_argument("mode", choices=["stream", "batch", "watcher"], 
                       help="Mode to run the pipeline")
    parser.add_argument("--date", help="Run date (YYYY-MM-DD)")
    parser.add_argument("--hour", help="Hour (HH)", default=None)
    
    args = parser.parse_args()
    
    if args.mode == "stream":
        if not args.date or not args.hour:
            parser.error("stream mode requires --date and --hour")
        run_stream(args.date, args.hour)
    
    elif args.mode == "batch":
        if not args.date:
            parser.error("batch mode requires --date")
        run_batch(args.date)
    
    elif args.mode == "watcher":
        run_watcher()