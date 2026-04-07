
import pandas as pd

# SCD1 primary keys
PRIMARY_KEYS = {
    "dim_segment":    "segment_id",
    "dim_category":   "category_id",
    "dim_team":       "team_id",
    "dim_restaurant": "restaurant_id",
    "dim_city":       "city_id",
    "dim_region":     "region_id",
    "dim_reason":     "reason_id",
    "dim_priority":   "priority_id",
}

# PII columns per table
PII_COLUMNS = {
    "customers": ["customer_id", "full_name", "email", "phone"],
    "drivers":   ["driver_id", "driver_name", "driver_phone", "national_id"],
    "agents":    ["agent_id", "agent_name", "agent_email", "agent_phone"],
}

# PII table names
PII_TABLE_NAMES = {
    "customers": "dim_customer_pii",
    "drivers":   "dim_driver_pii",
    "agents":    "dim_agent_pii",
}


def upsert_scd1(df: pd.DataFrame, table_name: str, conn) -> None:
    pk = PRIMARY_KEYS.get(table_name)
    cols = list(df.columns)

    col_names = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    updates = ", ".join([f"{c} = EXCLUDED.{c}" for c in cols if c != pk])

    query = f"""
        INSERT INTO DWH.{table_name} ({col_names})
        VALUES ({placeholders})
        ON CONFLICT ({pk}) DO UPDATE
        SET {updates}
    """

    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute(query, list(row))
    conn.commit()
    cursor.close()


def write_pii_records(df: pd.DataFrame, table_key: str, conn) -> None:
    pii_cols = PII_COLUMNS.get(table_key)
    table_name = PII_TABLE_NAMES.get(table_key)

    # skip tables with no PII
    if pii_cols is None or table_name is None:
        return

    # keep only PII columns that exist in df
    available_cols = [c for c in pii_cols if c in df.columns]
    pii_df = df[available_cols].copy()

    col_str = ", ".join(available_cols)
    placeholders = ", ".join(["%s"] * len(available_cols))

    cursor = conn.cursor()
    for _, row in pii_df.iterrows():
        cursor.execute(f"""
            INSERT INTO PII.{table_name} ({col_str})
            VALUES ({placeholders})
            ON CONFLICT DO NOTHING
        """, list(row))
    conn.commit()
    cursor.close()
