"""
Quarantine Module

Handles two types of rejections:
1. Bad Files (schema failures) - Whole file rejected due to missing columns or schema issues
they are saved to quarantine/YYYY-MM-DD/bad_files/ with timestamp

2. Bad Rows (validation failures) - Individual rows rejected due to data quality issues
they are appended to quarantine/YYYY-MM-DD/{table_name}_rejected.csv

"""

from pathlib import Path
import pandas as pd
from config import settings as set
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def quarantine_bad_file(df: pd.DataFrame, table_name: str, run_date: str, reason_prefix: str = "") -> Path | None:
    """
    Save entire file rejections to quarantine/YYYY-MM-DD/bad_files/
    
    Args:
        df: Rejected rows (entire file)
        table_name: Source table name
        run_date: Processing date (YYYY-MM-DD)
        reason_prefix: Optional prefix for rejection reasons
    
    Returns:
        Path to quarantine file, or None if no data
    """
    if df is None or df.empty:
        return None
    
    # Create date directory with bad_files subfolder
    out_dir = set.QUARANTINE_ROOT / run_date / "bad_files"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    df_to_write = df.copy()
    if reason_prefix and "rejection_reason" in df_to_write.columns:
        df_to_write["rejection_reason"] = (
            reason_prefix + df_to_write["rejection_reason"].astype(str)
        )
    
    # Timestamp to avoid overwriting multiple bad files for same table on same date
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"{table_name}_bad_file_{timestamp}.csv"
    
    df_to_write.to_csv(path, index=False)
    logger.info(f"[BAD_FILE] Quarantined {len(df)} rows (entire file) to {path}")
    return path


def quarantine_bad_rows(df: pd.DataFrame, table_name: str, run_date: str, reason_prefix: str = "") -> Path | None:
    """
    Save row-level rejections to quarantine/YYYY-MM-DD/{table_name}_rejected.csv
    
    Args:
        df: Rejected rows (individual rows)
        table_name: Source table name
        run_date: Processing date (YYYY-MM-DD)
        reason_prefix: Optional prefix for rejection reasons
    
    Returns:
        Path to quarantine file, or None if no data
    """
    if df is None or df.empty:  
        return None
    
    # Create date directory (no subfolder for bad rows)
    out_dir = set.QUARANTINE_ROOT / run_date
    out_dir.mkdir(parents=True, exist_ok=True)
    
    df_to_write = df.copy()
    if reason_prefix and "rejection_reason" in df_to_write.columns:
        df_to_write["rejection_reason"] = (
            reason_prefix + df_to_write["rejection_reason"].astype(str)
        )
    
    # Fixed filename for appending directly under date folder
    path = out_dir / f"{table_name}_rejected.csv"
    
    write_header = not path.exists()
    df_to_write.to_csv(path, mode='a', index=False, header=write_header)
    logger.info(f"[Rejected_rows] Appended {len(df)} rows to {path}")
    return path