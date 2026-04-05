# Logs pipeline-level summaries at the end of each run.

import logging
import time

logger = logging.getLogger(__name__)


def log_pipeline_start(run_date: str):

    # Marks the beginning of the daily pipeline run
    logger.info(f"[PIPELINE START] run_date={run_date}")

def log_pipeline_end(
    run_date: str,
    total_files: int,
    total_rows_loaded: int,
    total_rows_valid: int,
    total_rows_quarantined: int,
    duration_sec: float,
):
    # Final summary of the entire daily run
    logger.info(
        f"[PIPELINE END] run_date={run_date} | "
        f"total_files={total_files} | "
        f"total_rows_loaded={total_rows_loaded} | "
        f"total_rows_valid={total_rows_valid} | "
        f"total_rows_quarantined={total_rows_quarantined} | "
        f"duration={duration_sec:.1f}s"
    )
