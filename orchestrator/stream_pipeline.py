
"""
Stream processor that handles incoming data through the validation pipeline
"""

import logging
import time
import os
import sys
from pathlib import Path
import pandas as pd
from config import settings as s
from reader.extractor import load_file
from validators.schema_validator import schema_validate
from validators.business_validator import business_validate
from validators.quarantine_writer import quarantine_bad_file, quarantine_bad_rows
from config.schemas import SCHEMA_REGISTRY
from transformer.transform_order import transform_to_order_fact 
from transformer.transform_tickets import transform_tickets_to_fact
from loader.load_stream_data import load_fact_order
from loader.load_stream_data import load_fact_ticket

logger = logging.getLogger(__name__)

def run_stream(run_date: str, hour: str):
    """
    Process streaming data for a specific date and hour.
    """
    start_time = time.time()
    hour_dir = s.STREAM_INPUT_DIR / run_date / hour
    
    logger.info(f"STREAM PROCESSOR STARTED")
    logger.info(f"Input Directory: {hour_dir}")

    metrics = {
        "run_date": run_date,
        "hour": hour,
        "tables": {},
        "total_files_processed": 0,
        "total_rows_in": 0,
        "total_rows_clean": 0,
        "total_rows_rejected": 0,
        "total_bad_files": 0,
        "processing_time": 0
    }
    
    # Check folder exists
    if not hour_dir.exists():
        logger.warning(f"Hour folder does not exist: {hour_dir}")
        return metrics
    
    if not hour_dir.is_dir():
        logger.warning(f"Path exists but is not a directory: {hour_dir}")
        return metrics
    
    # Build file mapping from SCHEMA_REGISTRY
    file_mapping = {}
    for table_name, schema in SCHEMA_REGISTRY.items():
        source_file = schema.get("source_file")
        if source_file:
            is_stream_table = table_name in ["orders", "tickets", "ticket_events"]
            file_mapping[source_file] = {
                "table": table_name,
                "required": is_stream_table
            }

    # Process each file
    for filename, config in file_mapping.items():
        file_path = hour_dir / filename
        
        if not file_path.exists():
            if config["required"]:
                logger.warning(f"Required file missing: {filename}")
                metrics["tables"][config["table"]] = {"error": "File not found"}
            continue
        
        logger.info(f"\nProcessing: {filename}")
        
        try:
            table_metrics = process_file(file_path, config["table"], run_date)
            metrics["tables"][config["table"]] = table_metrics
            
            metrics["total_files_processed"] += 1
            metrics["total_rows_in"] += table_metrics.get("rows_in", 0)
            metrics["total_rows_clean"] += table_metrics.get("clean_rows", 0)
            metrics["total_rows_rejected"] += table_metrics.get("bad_rows_count", 0)
            
            if table_metrics.get("is_bad_file", False):
                metrics["total_bad_files"] += 1
            
            logger.info(f"  Summary: {filename}")
            logger.info(f"    Total rows: {table_metrics.get('rows_in', 0):,}")
            logger.info(f"    Clean rows: {table_metrics.get('clean_rows', 0):,}")
            logger.info(f"    Bad rows: {table_metrics.get('bad_rows_count', 0):,}")
            if table_metrics.get("is_bad_file", False):
                logger.info(f"    [BAD FILE] Quarantined to: quarantine/{run_date}/bad_files/")
            
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}", exc_info=True)
            metrics["tables"][config["table"]] = {"error": str(e)}
    
    metrics["processing_time"] = time.time() - start_time
    
    logger.info("\n" + "=" * 70)
    logger.info("PROCESSING SUMMARY")
    logger.info(f"Total processing time: {metrics['processing_time']:.2f} seconds")
    logger.info(f"Files processed: {metrics['total_files_processed']}")
    logger.info(f"Bad files (schema failures): {metrics['total_bad_files']}")
    logger.info(f"Total rows input: {metrics['total_rows_in']:,}")
    logger.info(f"Total clean rows: {metrics['total_rows_clean']:,}")
    logger.info(f"Total bad rows (validation failures): {metrics['total_rows_rejected']:,}")
    
    if metrics['total_rows_in'] > 0:
        acceptance_rate = (metrics['total_rows_clean'] / metrics['total_rows_in']) * 100
        logger.info(f"Acceptance rate: {acceptance_rate:.2f}%")
    
    logger.info("=" * 70)
    
    return metrics


def process_file(file_path: Path, table_name: str, run_date: str) -> dict:
    """
    Process a single file through the validation pipeline.
    """
    metrics = {
        "table_name": table_name,
        "file_name": file_path.name,
        "rows_in": 0,
        "clean_rows": 0,
        "bad_rows_count": 0,
        "is_bad_file": False,
        "bad_file_path": None,
        "bad_rows_path": None
    }
    
    # Step 1: Extract data
    logger.info(f"  [1/3] Reading file...")
    df = load_file(file_path)
    
    # Handle file loading failure
    if df is None:
        logger.error(f"  Failed to read {file_path.name}")
        metrics["error"] = "Failed to load file"
        metrics["is_bad_file"] = True
        
        error_df = pd.DataFrame([{
            "file_name": file_path.name,
            "error": "Failed to read file",
            "rejection_reason": f"[{table_name}][FAILED_TO_READ] Could not read file"
        }])
        
        metrics["bad_file_path"] = quarantine_bad_file(
            error_df,
            table_name,
            run_date,
            reason_prefix=f"[{table_name}][FAILED_TO_READ] "
        )
        return metrics
    
    metrics["rows_in"] = len(df)
    
    # Check for empty file
    if df.empty:
        logger.error(f"  [BAD FILE] File is empty: {file_path.name}")
        metrics["is_bad_file"] = True
        metrics["bad_rows_count"] = 0
        
        df_with_reason = df.copy()
        df_with_reason["rejection_reason"] = f"[{table_name}][EMPTY_FILE] File is empty"
        
        metrics["bad_file_path"] = quarantine_bad_file(
            df_with_reason,
            table_name,
            run_date,
            reason_prefix=f"[{table_name}][EMPTY_FILE] "
        )
        return metrics
    
    logger.info(f"  [OK] Read {len(df):,} rows, {len(df.columns)} columns")
    
    # Step 2: Schema validation
    logger.info(f"  [2/3] Running schema validation...")
    clean_schema, rejected_schema, schema_metrics = schema_validate(df, table_name)
    
    # Check for schema not found
    if "SCHEMA_NOT_FOUND" in schema_metrics.get("missing_columns", []):
        logger.error(f"  [BAD FILE] Schema not found for table: {table_name}")
        metrics["is_bad_file"] = True
        metrics["bad_rows_count"] = len(df)
        
        df_with_reason = df.copy()
        df_with_reason["rejection_reason"] = f"[{table_name}][SCHEMA_NOT_FOUND] No schema found"
        
        metrics["bad_file_path"] = quarantine_bad_file(
            df_with_reason,
            table_name,
            run_date,
            reason_prefix=f"[{table_name}][SCHEMA_NOT_FOUND] "
        )
        return metrics
    
    # Check for missing required columns (structural failure)
    if schema_metrics.get("missing_columns"):
        logger.error(f"  [BAD FILE] Missing required columns: {schema_metrics['missing_columns']}")
        metrics["is_bad_file"] = True
        metrics["bad_rows_count"] = len(df)
        
        df_with_reason = df.copy()
        df_with_reason["rejection_reason"] = f"[{table_name}][MISSING_COLUMNS] Missing: {schema_metrics['missing_columns']}"
        
        metrics["bad_file_path"] = quarantine_bad_file(
            df_with_reason,
            table_name,
            run_date,
            reason_prefix=f"[{table_name}][MISSING_COLUMNS] "
        )
        return metrics
    
    logger.info(f"  [OK] Schema validation: {len(clean_schema):,} clean, {len(rejected_schema):,} rejected")
    
    if len(rejected_schema) > 0:
        if schema_metrics.get("null_counts"):
            null_cols = [f"{col}({count})" for col, count in schema_metrics["null_counts"].items() if count > 0]
            if null_cols:
                logger.info(f"    - Null values: {', '.join(null_cols)}")
        
        if schema_metrics.get("duplicate_counts", 0) > 0:
            logger.info(f"    - Duplicates: {schema_metrics['duplicate_counts']}")
        
        if schema_metrics.get("dtype_fails"):
            dtype_cols = [f"{col}({count})" for col, count in schema_metrics["dtype_fails"].items()]
            logger.info(f"    - Type errors: {', '.join(dtype_cols)}")
    
    # Step 3: Business validation
    logger.info(f"  [3/3] Running business validation...")
    clean_business = pd.DataFrame()
    rejected_business = pd.DataFrame()
    business_metrics = {}
    
    if not clean_schema.empty:
        clean_business, rejected_business, business_metrics = business_validate(clean_schema, table_name)
        logger.info(f"  [OK] Business validation: {len(clean_business):,} clean, {len(rejected_business):,} rejected")
        
        if len(rejected_business) > 0:
            for check_type, failures in business_metrics.get("checks", {}).items():
                if failures:
                    failure_details = [f"{col}({count})" for col, count in failures.items()]
                    logger.info(f"    - {check_type}: {', '.join(failure_details)}")
    else:
        logger.info(f"  [SKIP] No rows passed schema validation, skipping business validation")
    
    # Combine row-level rejected rows
    all_bad_rows = pd.concat([rejected_schema, rejected_business], ignore_index=True)
    metrics["bad_rows_count"] = len(all_bad_rows)
    metrics["clean_rows"] = len(clean_business)
    
    # Quarantine bad rows
    if not all_bad_rows.empty:
        logger.info(f"  Quarantining {len(all_bad_rows)} Rejected rows...")
        metrics["bad_rows_path"] = quarantine_bad_rows(
            all_bad_rows,
            table_name,
            run_date,
            reason_prefix=f"[{table_name}] "
        )
        logger.info(f"  [OK] Rejected rows appended to quarantine/{run_date}/{table_name}_rejected.csv")

    if table_name == "orders":
        clean_business_order = transform_to_order_fact(clean_business)
        load_fact_order(clean_business_order)
    elif table_name == "tickets":
        clean_business_ticket = transform_tickets_to_fact(clean_business)
        load_fact_ticket(clean_business_ticket)

    return metrics