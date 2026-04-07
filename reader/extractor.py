# Reads CSV and JSON files into pandas DataFrames.

import logging
import json
import pandas as pd
from pathlib import Path

# All log messages from here will be prefixed with (shared_scripts.loader)

logger = logging.getLogger(__name__)


def load_file(file_path: Path) -> pd.DataFrame:

    # Convert to Path object in case a plain string was passed

    file_path = Path(file_path)

    # Stop immediately if file doesn't exist

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return None

    # Stop immediately if file is empty

    if file_path.stat().st_size == 0:
        logger.error(f"File is empty: {file_path}")
        return None

    # Read the file extension to decide which loader to use

    extension = file_path.suffix.lower()

    if extension == ".csv":
        return load_csv(file_path)
    elif extension == ".json":
        return load_json(file_path)
    else:
        # Any other file type is not supported
        
        logger.error(f"Unsupported file type '{extension}': {file_path.name}")
        return None


def load_csv(file_path: Path) -> pd.DataFrame:

    logger.info(f"Loading CSV: {file_path.name}")

    try:
        df = pd.read_csv(
            file_path,

            # Disable pandas default null detection so we control it ourselves
            keep_default_na=False,

            # These specific string values will be treated as null (NaN)
            na_values=["", "NULL", "null", "None", "NaN", "nan"],
        )
        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns from {file_path.name}")
        return df

    except Exception as e:
        logger.error(f"Failed to read CSV '{file_path.name}': {e}")
        return None


def load_json(file_path: Path) -> pd.DataFrame:

    logger.info(f"Loading JSON: {file_path.name}")

    try:
        # Use json.load() bec it reads them as Python None which pandas handles safely
        with open(file_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        df = pd.DataFrame(raw)

        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns from {file_path.name}")
        return df

    except Exception as e:
        logger.error(f"Failed to read JSON '{file_path.name}': {e}")
        return None