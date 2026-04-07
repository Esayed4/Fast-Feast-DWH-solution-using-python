# pipeline/batch/clean_loader.py

import pandas as pd
from pathlib import Path
from typing import Tuple, Dict, Any

import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))

from reader.extractor import load_file
from loader.PII_writer import write_pii_records
from validators.schema_validator import schema_validate
from validators.business_validator import business_validate

FILE_NAMES = {
    "customers":         "customers.csv",
    "drivers":           "drivers.csv",
    "restaurants":       "restaurants.json",
    "agents":            "agents.csv",
    "cities":            "cities.json",
    "regions":           "regions.csv",
    "segments":          "segments.csv",
    "reasons":           "reasons.csv",
    "priorities":        "priorities.csv",
    "categories":        "categories.csv",
    "teams":             "teams.csv",
    "reason_categories": "reason_categories.csv",
}

ANALYTICS_COLUMNS = {
    "customers":   ["customer_id", "segment_id", "gender", "signup_date"],
    "drivers":     ["driver_id", "shift", "vehicle_type", "hire_date",
                    "rating_avg", "on_time_rate", "cancel_rate", "is_active"],
    "restaurants": ["restaurant_id", "restaurant_name", "category_id",
                    "price_tier", "rating_avg", "prep_time_avg_min", "is_active"],
    "agents":      ["agent_id", "team_id", "skill_level", "hire_date",
                    "avg_handle_time_min", "resolution_rate", "csat_score", "is_active"],
    "cities":      ["city_id", "city_name", "country", "timezone"],
    "regions":     ["region_id", "region_name", "city_id", "delivery_base_fee"],
    "segments":    ["segment_id", "segment_name", "discount_pct", "priority_support"],
    "reasons":     ["reason_id", "reason_name", "reason_category_id",
                    "severity_level", "typical_refund_pct"],
    "priorities":  ["priority_id", "priority_code", "priority_name",
                    "sla_first_response_min", "sla_resolution_min"],
    "categories":  ["category_id", "category_name"],
    "teams":       ["team_id", "team_name"],
}

PII_COLUMNS = {
    "customers": ["full_name", "email", "phone"],
    "drivers":   ["driver_name", "driver_phone", "national_id"],
    "agents":    ["agent_name", "agent_email", "agent_phone"],
}


def _init_quality(table_key: str, batch_date: str) -> Dict[str, Any]:
    return {
        "table":                table_key,
        "batch_date":           batch_date,
        "total_records_read":   0,
        "records_clean":        0,
        "records_quarantined":  0,
        "missing_columns":      [],
        "schema_metrics":       {},
        "business_metrics":     {},
        "success":              False,
        "error":                None,
    }


def load_batch_file(
    batch_folder: Path,
    table_key: str,
    batch_date: str,
    lookup_data: Dict[str, pd.DataFrame] = None,
    pii_conn=None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:

    quality = _init_quality(table_key, batch_date)

    # Step 1: build path and load
    file_path = batch_folder / FILE_NAMES[table_key]
    df = load_file(file_path)
    if df is None:
        quality["error"] = f"Failed to load file: {file_path}"
        return pd.DataFrame(), quality
    quality["total_records_read"] = len(df)

    # Step 2: schema validation
    # checks required columns, nulls, duplicates, dtypes
    clean_df, rejected_df, schema_metrics = schema_validate(df, table_key)
    quality["schema_metrics"] = schema_metrics
    quality["records_quarantined"] += len(rejected_df)

    # if entire file was rejected (missing required columns)
    if clean_df.empty and not df.empty:
        quality["error"] = f"Schema validation failed: {schema_metrics.get('missing_columns')}"
        return pd.DataFrame(), quality

    # Step 3: business validation
    # checks email, phone, ratings, amounts, dates
    clean_df, biz_rejected_df, business_metrics = business_validate(clean_df, table_key)
    quality["business_metrics"] = business_metrics
    quality["records_quarantined"] += len(biz_rejected_df)

    # Step 3.5: write PII to pii_db before stripping
    if pii_conn is not None:
        write_pii_records(clean_df, table_key, pii_conn)

    # Step 4: strip PII columns
    pii_cols = PII_COLUMNS.get(table_key, [])
    if pii_cols:
        clean_df = clean_df.drop(columns=pii_cols, errors="ignore")

    # Step 5: keep only analytics columns
    analytics_cols = ANALYTICS_COLUMNS.get(table_key, [])
    clean_df = clean_df[analytics_cols]

    # Step 6: update quality and return
    quality["records_clean"] = len(clean_df)
    quality["success"] = True
    return clean_df, quality
