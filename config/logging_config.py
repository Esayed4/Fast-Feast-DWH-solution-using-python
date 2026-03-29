# Configures the Python logging system for the entire pipeline.
# Called once at pipeline startup from orchestrator.py.

import logging
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from datetime import date
from config.settings import LOG_LEVEL, LOG_DIR


def setup_logging():

    # Create the log directory if it doesn't exist

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Define the log message format
    # Fields: timestamp | level | module that called the logger | message
    
    formatter = logging.Formatter(
        format="%(asctime)s | %(levelname)-8s | %(module)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Writes logs to a daily rotating file
  
    log_file = LOG_DIR / f"{date.today()}.log"
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",        # rotate at midnight every day
        backupCount=7         # keep 7 days of history
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(LOG_LEVEL)

    # Prints logs to terminal when running not just into files

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(LOG_LEVEL)

    # Get the ROOT logger and attach both handlers

    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Confirm logging is ready

    logging.info(f"Logging initialized — level={LOG_LEVEL} | file={log_file}")