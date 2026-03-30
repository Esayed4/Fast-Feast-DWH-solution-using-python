# Reads all configuration from .env and exposes clean Python variables.

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# BASE PATHS

BASE_DIR = Path(os.getenv("BASE_DIR", "Fast-Feast-DWH-solution-using-python"))

# INPUT PATHS

BATCH_INPUT_DIR = Path(os.getenv("BATCH_INPUT_DIR", "data/input/batch"))
STREAM_INPUT_DIR = Path(os.getenv("STREAM_INPUT_DIR", "data/input/stream"))
MASTER_DIR = Path(os.getenv("MASTER_DIR", "data/master"))

# =============================================================================

# DATABASE PATHS
POSTGRES_USER= 'admin'
POSTGRES_PASSWORD= 'admin'
PII_DB='pii_db'
ORPHAN_DB='orphan_db'
DWH='dwh_db'
DWH_PATH = Path(os.getenv("DWH_PATH", "data/warehouse.db"))
PII_DB_PATH = Path(os.getenv("PII_DB_PATH", "data/pii_db.db"))
ORPHAN_DB_PATH = Path(os.getenv("ORPHAN_DB_PATH", "data/orphan_db.db"))

# =============================================================================

# QUARANTINE PATHS

QUARANTINE_BAD_FILES_DIR = Path(os.getenv("QUARANTINE_BAD_FILES_DIR", "quarantine/bad_files"))
QUARANTINE_DB_PATH = Path(os.getenv("QUARANTINE_DB_PATH", "quarantine/quarantine.db"))

# =============================================================================

# LOGGING

LOG_DIR = Path(os.getenv("LOG_DIR", "logging/logs"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# =============================================================================

# ALERT SETTINGS

ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")