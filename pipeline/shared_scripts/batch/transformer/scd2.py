# pipeline/batch/transformer/scd2.py

import pandas as pd
from datetime import date, timedelta
from typing import List

# from logging.pipeline_logger import get_logger
# logger = get_logger(__name__)

SCD2_TRACKED_COLUMNS = {
    "customers": ["segment_id"],
    "drivers":   ["shift", "vehicle_type", "rating_avg",
                  "on_time_rate", "cancel_rate", "is_active"],
    "agents":    ["team_id", "skill_level", "avg_handle_time_min",
                  "resolution_rate", "csat_score", "is_active"],
}

BUSINESS_KEYS = {
    "customers": "customer_id",
    "drivers":   "driver_id",
    "agents":    "agent_id",
}

TABLE_NAMES = {
    "customers": "dim_customer",
    "drivers":   "dim_driver",
    "agents":    "dim_agent",
}

SURROGATE_KEYS = {
    "customers": "customer_sk",
    "drivers":   "driver_sk",
    "agents":    "agent_sk",
}


def _has_changed(existing_row: pd.Series, new_row: pd.Series, tracked_cols: List[str]) -> bool:
    return any(str(existing_row[col]) != str(new_row[col]) for col in tracked_cols)


def apply_scd2(df: pd.DataFrame, table_key: str, batch_date: str, conn) -> None:

    # Step 1: get config for this table
    tracked_cols = SCD2_TRACKED_COLUMNS.get(table_key)
    bk = BUSINESS_KEYS.get(table_key)
    table_name = TABLE_NAMES.get(table_key)
    cols = [c for c in df.columns]

    # Step 2: load current active rows from warehouse
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM DWH.{table_name} WHERE is_current = true")
    rows = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description]
    existing_df = pd.DataFrame(rows, columns=col_names)

    # Step 3: loop over incoming rows
    today = date.fromisoformat(batch_date)
    yesterday = today - timedelta(days=1)

    for _, new_row in df.iterrows():

        match = existing_df[existing_df[bk] == new_row[bk]]

        if match.empty:
            # CASE 1: brand new → insert
            insert_cols = cols + ["start_date", "end_date", "is_current"]
            placeholders = ", ".join(["%s"] * len(insert_cols))
            col_str = ", ".join(insert_cols)
            values = list(new_row) + [today, None, True]

            cursor.execute(f"""
                INSERT INTO DWH.{table_name} ({col_str})
                VALUES ({placeholders})
            """, values)

        else:
            existing_row = match.iloc[0]
            if not _has_changed(existing_row, new_row, tracked_cols):
                # CASE 2: nothing changed → skip
                continue
            else:
                # CASE 3: expire old row + insert new version
                cursor.execute(f"""
                    UPDATE DWH.{table_name}
                    SET end_date = %s, is_current = false
                    WHERE {bk} = %s AND is_current = true
                """, [yesterday, new_row[bk]])

                insert_cols = cols + ["start_date", "end_date", "is_current"]
                placeholders = ", ".join(["%s"] * len(insert_cols))
                col_str = ", ".join(insert_cols)
                values = list(new_row) + [today, None, True]

                cursor.execute(f"""
                    INSERT INTO DWH.{table_name} ({col_str})
                    VALUES ({placeholders})
                """, values)

    conn.commit()
    cursor.close()
