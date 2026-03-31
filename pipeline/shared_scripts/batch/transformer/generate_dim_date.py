# pipeline/batch/transformer/generate_dim_date.py

import pandas as pd
from datetime import date
from typing import List


def _generate_date_row(d: date) -> dict:
    return {
        "date_id":     int(d.strftime("%Y%m%d")),
        "full_date":   d,
        "day_of_week": d.strftime("%A"),
        "month":       d.month,
        "month_name":  d.strftime("%B"),
        "quarter":     (d.month - 1) // 3 + 1,
        "year":        d.year,
        "is_weekend":  d.weekday() >= 5,
    }


def generate_dim_date(dates: List[date], conn) -> None:

    # generate rows and build DataFrame
    rows = [_generate_date_row(d) for d in dates]
    df = pd.DataFrame(rows)

    # upsert into dim_date
    conn.execute("""
        INSERT OR REPLACE INTO dim_date
        SELECT * FROM df
    """)
