# pipeline/batch/batch_runner.py

import sys
import os
from datetime import date

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from config import settings
from loader.connect_to_db import get_postgres_conn
from watchers.batch_detector import (
    get_unprocessed_batches,
    mark_batch_processed,
    mark_batch_failed
)
from loader.load_batch_data import load_batch_file
from transformer.scd2 import apply_scd2
from loader.PII_writer import upsert_scd1
from transformer.deduplicator import deduplicate
from loader.load_stream_data import load_fact_order
from loader.load_stream_data import load_fact_ticket
from warehouse.Handel_Orphan import handle_order_orphan, handle_ticket_orphan

SCD1_TABLES = [
    "segments",
    "categories",
    "teams",
    "regions",
    "cities",
    "restaurants",
    "reasons",
    "priorities",
]

SCD2_TABLES = [
    "customers",
    "drivers",
    "agents",
]

DWH_TABLE_NAMES = {
    "segments":    "dim_segment",
    "categories":  "dim_category",
    "teams":       "dim_team",
    "regions":     "dim_region",
    "cities":      "dim_city",
    "restaurants": "dim_restaurant",
    "reasons":     "dim_reason",
    "priorities":  "dim_priority",
}


def run_batch():

    # Step 1: connect to DWH and PII DB
    conn = get_postgres_conn(settings.DWH)
    pii_conn = get_postgres_conn(settings.PII_DB)

    if conn is None:
        print("[ERROR] Could not connect to DWH — aborting")
        return
    if pii_conn is None:
        print("[ERROR] Could not connect to PII DB — aborting")
        return

    # Step 2: get unprocessed batch folders
    for batch_folder in get_unprocessed_batches():
        batch_date = batch_folder.name
        print(f"\n{'='*50}")
        print(f"Processing batch: {batch_date}")
        print(f"{'='*50}")

        try:
            # Step 3: load SCD1 tables first
            print("\n--- Loading SCD1 tables ---")
            lookup_data = {}

            for table_key in SCD1_TABLES:
                print(f"  Loading {table_key}...")
                clean_df, quality = load_batch_file(
                    batch_folder, table_key, batch_date, lookup_data, pii_conn
                )

                if not quality["success"]:
                    print(f"  [SKIP] {table_key} — {quality['error']}")
                    continue

                # deduplicate before loading
                clean_df = deduplicate(clean_df, table_key, conn)

                if clean_df.empty:
                    print(f"  [SKIP] {table_key} — all rows already exist in DWH")
                    continue

                lookup_data[table_key] = clean_df
                dwh_table = DWH_TABLE_NAMES[table_key]
                upsert_scd1(clean_df, dwh_table, conn)
                print(f"  [OK] {table_key} — {quality['records_clean']} rows loaded")

            # Step 4: load SCD2 tables
            print("\n--- Loading SCD2 tables ---")
            for table_key in SCD2_TABLES:
                print(f"  Loading {table_key}...")
                clean_df, quality = load_batch_file(
                    batch_folder, table_key, batch_date, lookup_data, pii_conn
                )

                if not quality["success"]:
                    print(f"  [SKIP] {table_key} — {quality['error']}")
                    continue

                # SCD2 handles its own deduplication internally
                apply_scd2(clean_df, table_key, batch_date, conn)
                print(f"  [OK] {table_key} — {quality['records_clean']} rows processed")

            # Step 5: generate dim_date
            # print("\n--- Generating dim_date ---")
            # from datetime import timedelta

            # cursor = conn.cursor()
            # cursor.execute("SELECT MAX(full_date) FROM DWH.dim_date")
            # max_date = cursor.fetchone()[0]
            # cursor.close()

            # batch_dt = date.fromisoformat(batch_date)

            # only generate if batch_date is not already covered
            # if max_date is None or batch_dt > max_date:
            #     start_dt = batch_dt if max_date is None else max_date + timedelta(days=1)
            #     end_dt = batch_dt.replace(year=batch_dt.year + 5)
            #     dates = [start_dt + timedelta(days=i) for i in range((end_dt - start_dt).days + 1)]
            #     generate_dim_date(dates, conn)
            #     print(f"  [OK] dim_date generated from {start_dt} to {end_dt}")
            # else:
            #     print(f"  [SKIP] dim_date already covers {batch_date}")

            # Step 6: retry streaming orphans now that dimensions are updated
            print("\n--- Retrying streaming orphans ---")
            try:
                load_fact_order(handle_order_orphan())
                print("  [OK] Order orphans retried")
            except Exception as e:
                print(f"  [WARN] Order orphan retry failed — {e}")

            try:
                load_fact_ticket(handle_ticket_orphan())
                print("  [OK] Ticket orphans retried")
            except Exception as e:
                print(f"  [WARN] Ticket orphan retry failed — {e}")

            # Step 7: mark batch as complete
            mark_batch_processed(batch_date)
            print(f"\n[DONE] Batch {batch_date} completed successfully")

        except Exception as e:
            import traceback
            traceback.print_exc()
            mark_batch_failed(batch_date, str(e))
            print(f"\n[FAILED] Batch {batch_date} failed — {e}")
            conn.rollback()

    
    
    conn.close()
    pii_conn.close()


if __name__ == "__main__":
    run_batch()
