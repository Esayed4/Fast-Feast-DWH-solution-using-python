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
DWH_PATH = Path(os.getenv("DWH_PATH", "data/warehouse.db"))
PII_DB_PATH = Path(os.getenv("PII_DB_PATH", "data/pii_db.db"))
ORPHAN_DB_PATH = Path(os.getenv("ORPHAN_DB_PATH", "data/orphan_db.db"))

# POSTGRESQL
POSTGRES_USER     = os.getenv("POSTGRES_USER", "admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")
DWH               = os.getenv("DWH", "dwh_db")
PII_DB            = os.getenv("PII_DB", "pii_db")
ORPHAN_DB         = os.getenv("ORPHAN_DB", "orphan_db")

# =============================================================================
# QUARANTINE PATHS
QUARANTINE_BAD_FILES_DIR = Path(os.getenv("QUARANTINE_BAD_FILES_DIR", "quarantine"))
QUARANTINE_DB_PATH = Path(os.getenv("QUARANTINE_DB_PATH", "quarantine/quarantine.db"))

# =============================================================================
# LOGGING
LOG_DIR   = Path(os.getenv("LOG_DIR", "logging/logs"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# =============================================================================
# ALERT SETTINGS
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM")
ALERT_EMAIL_TO   = os.getenv("ALERT_EMAIL_TO")
SMTP_HOST        = os.getenv("SMTP_HOST")
SMTP_PORT        = int(os.getenv("SMTP_PORT", "587"))
SMTP_PASSWORD    = os.getenv("SMTP_PASSWORD")

# =============================================================================
# VALIDATION RULES
EMAIL_REGEX      = os.getenv("EMAIL_REGEX", r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_REGEX = os.getenv("PHONE_REGEX", r"^0(10|11|12|15)\d{8}$")
AGENT_PHONE_REGEX = os.getenv("AGENT_PHONE_REGEX", r"^(10|11|12|15)\d{8}$")
RATING_MIN       = float(os.getenv("RATING_MIN", "0.0"))
RATING_MAX       = float(os.getenv("RATING_MAX", "5.0"))
AMOUNT_MIN       = float(os.getenv("AMOUNT_MIN", "0.0"))
ON_TIME_RATE_MIN = float(os.getenv("ON_TIME_RATE_MIN", "0.0"))
ON_TIME_RATE_MAX = float(os.getenv("ON_TIME_RATE_MAX", "1.0"))
