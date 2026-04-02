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
    rows = [_generate_date_row(d) for d in dates]

    cursor = conn.cursor()
    for row in rows:
        cursor.execute("""
            INSERT INTO DWH.dim_date 
                (date_id, full_date, day_of_week, month, month_name, quarter, year, is_weekend)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date_id) DO NOTHING
        """, list(row.values()))
    conn.commit()
    cursor.close()
