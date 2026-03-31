# pipeline/batch/clean_loader.py

import pandas as pd
from pathlib import Path
from typing import Tuple, Dict, Any

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from pipeline.shared_scripts.extractor import load_file


FILE_NAMES = {
    "customers":   "customers.csv",
    "drivers":     "drivers.csv",
    "restaurants": "restaurants.json",
    "agents":      "agents.csv",
    "cities":      "cities.json",
    "regions":     "regions.csv",
    "segments":    "segments.csv",
    "reasons":     "reasons.csv",
    "priorities":  "priorities.csv",
}

ANALYTICS_COLUMNS = {
    "customers":   ["customer_id", "segment_id", "gender", "signup_date"],
    "drivers":     ["driver_id", "shift", "vehicle_type", "hire_date",
                    "rating_avg", "on_time_rate", "cancel_rate", "is_active"],
    "restaurants": ["restaurant_id", "restaurant_name", "category_name",
                    "price_tier", "rating_avg", "prep_time_avg_min", "is_active"],
    "agents":      ["agent_id", "team_name", "skill_level", "hire_date",
                    "avg_handle_time_min", "resolution_rate", "csat_score", "is_active"],
    "cities":      ["city_id", "city_name", "country", "timezone"],
    "regions":     ["region_id", "region_name", "city_id", "delivery_base_fee"],
    "segments":    ["segment_id", "segment_name", "discount_pct", "priority_support"],
    "reasons":     ["reason_id", "reason_name", "reason_category_name",
                    "severity_level", "typical_refund_pct"],
    "priorities":  ["priority_id", "priority_code", "priority_name",
                    "sla_first_response_min", "sla_resolution_min"],
}

PII_COLUMNS = {
    "customers": ["full_name", "email", "phone"],
    "drivers":   ["driver_name", "driver_phone", "national_id"],
    "agents":    ["agent_name", "agent_email", "agent_phone"],
}

REQUIRED_COLUMNS = {
    "customers":   ["customer_id", "segment_id", "signup_date",
                    "full_name", "email", "phone", "gender"],
    "drivers":     ["driver_id", "shift", "vehicle_type", "hire_date",
                    "rating_avg", "on_time_rate", "cancel_rate", "is_active",
                    "driver_name", "driver_phone", "national_id"],
    "restaurants": ["restaurant_id", "restaurant_name", "category_id",
                    "price_tier", "rating_avg", "prep_time_avg_min", "is_active"],
    "agents":      ["agent_id", "team_id", "skill_level", "hire_date",
                    "avg_handle_time_min", "resolution_rate", "csat_score",
                    "is_active", "agent_name", "agent_email"],
    "cities":      ["city_id", "city_name", "country", "timezone"],
    "regions":     ["region_id", "region_name", "city_id", "delivery_base_fee"],
    "segments":    ["segment_id", "segment_name", "discount_pct", "priority_support"],
    "reasons":     ["reason_id", "reason_name", "reason_category_id", "severity_level"],
    "priorities":  ["priority_id", "priority_code", "priority_name",
                    "sla_first_response_min", "sla_resolution_min"],
}


def _init_quality(table_key: str, batch_date: str) -> Dict[str, Any]:
    return {
        "table":                table_key,
        "batch_date":           batch_date,
        "total_records_read":   0,
        "records_clean":        0,
        "records_quarantined":  0,
        "missing_columns":      [],
        "null_pct":             {},
        "success":              False,
        "error":                None,
    }


def load_batch_file(
    batch_folder: Path,
    table_key: str,
    batch_date: str,
    lookup_data: Dict[str, pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:

    quality = _init_quality(table_key, batch_date)

    # Step 1: build path and load
    file_path = batch_folder / FILE_NAMES[table_key]
    df = load_file(file_path)
    if df is None:
        quality["error"] = f"Failed to load file: {file_path}"
        return pd.DataFrame(), quality
    quality["total_records_read"] = len(df)

    # Step 2: check required columns exist
    required = REQUIRED_COLUMNS.get(table_key, [])
    missing = [col for col in required if col not in df.columns]
    if missing:
        quality["missing_columns"] = missing
        quality["error"] = f"Missing required columns: {missing}"
        return pd.DataFrame(), quality

    # Step 3: drop nulls in required fields
    null_mask = df[required].isnull().any(axis=1)
    bad_df = df[null_mask]
    clean_df = df[~null_mask]
    quality["records_quarantined"] += len(bad_df)

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
