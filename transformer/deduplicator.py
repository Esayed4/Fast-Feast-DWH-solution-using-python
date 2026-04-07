# pipeline/shared_scripts/deduplicator.py

import pandas as pd

BUSINESS_KEYS = {
    "segments":    "segment_id",
    "categories":  "category_id",
    "teams":       "team_id",
    "regions":     "region_id",
    "cities":      "city_id",
    "restaurants": "restaurant_id",
    "reasons":     "reason_id",
    "priorities":  "priority_id",
    "customers":   "customer_id",
    "drivers":     "driver_id",
    "agents":      "agent_id",
}

DWH_TABLE_NAMES = {
    "segments":    "dim_segment",
    "categories":  "dim_category",
    "teams":       "dim_team",
    "regions":     "dim_region",
    "cities":      "dim_city",
    "restaurants": "dim_restaurant",
    "reasons":     "dim_reason",
    "priorities":  "dim_priority",
    "customers":   "dim_customer",
    "drivers":     "dim_driver",
    "agents":      "dim_agent",
}


def deduplicate(df: pd.DataFrame, table_key: str, conn) -> pd.DataFrame:
    bk = BUSINESS_KEYS.get(table_key)
    table_name = DWH_TABLE_NAMES.get(table_key)

    if bk is None or table_name is None:
        return df

    # get existing business keys from DWH
    cursor = conn.cursor()
    cursor.execute(f"SELECT {bk} FROM DWH.{table_name}")
    existing_keys = set(row[0] for row in cursor.fetchall())
    cursor.close()

    # keep only rows whose business key is NOT already in DWH
    before = len(df)
    df = df[~df[bk].isin(existing_keys)]
    after = len(df)

    if before - after > 0:
        print(f"  [DEDUP] {before - after} duplicate rows removed from {table_key}")

    return df
