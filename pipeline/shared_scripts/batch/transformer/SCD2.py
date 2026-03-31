# pipeline/batch/transformer/scd2.py

import pandas as pd
from datetime import date
from typing import List

# from warehouse.connection import get_warehouse_connection
# from logging.pipeline_logger import get_logger
# logger = get_logger(__name__)

EXPIRY_SENTINEL = date(9999, 12, 31)

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


def _has_changed(existing_row: pd.Series, new_row: pd.Series, tracked_cols: List[str]) -> bool:
    return any(existing_row[col] != new_row[col] for col in tracked_cols)


def apply_scd2(df: pd.DataFrame, table_key: str, batch_date: str, conn) -> None:

    # Step 1: get config for this table
    tracked_cols = SCD2_TRACKED_COLUMNS.get(table_key)
    bk = BUSINESS_KEYS.get(table_key)
    table_name = f"dim_{table_key[:-1]}"

    # Step 2: load current active rows from warehouse
    existing_df = conn.execute(
        f"SELECT * FROM {table_name} WHERE is_current = true"
    ).df()

    # Step 3: loop over incoming rows
    today = date.fromisoformat(batch_date)
    yesterday = today.replace(day=today.day - 1)

    for _, new_row in df.iterrows():

        match = existing_df[existing_df[bk] == new_row[bk]]

        if match.empty:
            # CASE 1: brand new → insert
            new_row["effective_date"] = today
            new_row["expiry_date"] = EXPIRY_SENTINEL
            new_row["is_current"] = True
            conn.execute(f"""
                INSERT INTO {table_name}
                VALUES ({','.join(['?' for _ in new_row])})
            """, list(new_row))

        else:
            existing_row = match.iloc[0]
            if not _has_changed(existing_row, new_row, tracked_cols):
                # CASE 2: nothing changed → skip
                continue
            else:
                # CASE 3: expire old row + insert new version
                conn.execute(f"""
                    UPDATE {table_name}
                    SET expiry_date = ?, is_current = false
                    WHERE {bk} = ? AND is_current = true
                """, [yesterday, new_row[bk]])

                new_row["effective_date"] = today
                new_row["expiry_date"] = EXPIRY_SENTINEL
                new_row["is_current"] = True
                conn.execute(f"""
                    INSERT INTO {table_name}
                    VALUES ({','.join(['?' for _ in new_row])})
                """, list(new_row))
