import argparse
import sys
import logging
from config.logging_config import setup_logging
from watchers.batch_scheduler import start_batch_scheduler

setup_logging()
logger = logging.getLogger(__name__)


def _cmd_watch(args):
    from watchers.watcher import watcher

    run_date = args.date
    if run_date:
        logger.info(f"Starting watcher for date: {run_date}")

    # Start batch scheduler in background thread
    logger.info("Starting batch scheduler in background thread...")
    start_batch_scheduler()
    logger.info("[OK] Batch scheduler started")

    # Start stream watcher (blocking — runs forever)
    logger.info("Starting stream watcher...")
    watcher(run_date=run_date)
    return 0


def _build_parser():
    parser = argparse.ArgumentParser('python main.py')
    sub = parser.add_subparsers(dest='command', required=True)

    p_watch = sub.add_parser('watch', help='start watcher')
    p_watch.add_argument('--date', required=False, default=None)
    p_watch.set_defaults(func=_cmd_watch)
    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
