import os
import sys
import logging
import pandas as pd
import psycopg2
from psycopg2 import extras
from datetime import datetime


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),  ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from loader.load_stream_data import load_fact_order, load_fact_order, load_fact_ticket
from loader.connect_to_db import get_postgres_conn # Assuming this contains your get_postgres_conn function

# 1. Add project root to path


# 2. Import local modules
try:
    from config import settings
    from config.logging_config import setup_logging
    setup_logging()
    logger = logging.getLogger(__name__)
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def handle_order_orphan(db_name='dwh_db', orphan_db='orphan_db'):
    """Re-processes orphan orders by pulling them from the orphan DB and clearing it."""
    engine_orphan = get_postgres_conn(orphan_db)
    if not engine_orphan:
        logger.error(f"Could not connect to {orphan_db}. Skipping order orphans.")
        return

    try:
        # Load the orphans
        fact_orphan = pd.read_sql("SELECT * FROM orphan_fact_orders", engine_orphan)
        
        if fact_orphan.empty:
            logger.info("No orphan orders to process.")
            return

        # Clear the orphan table (we will try to re-insert them or move them back if they fail again)
        with engine_orphan.cursor() as cur:
            cur.execute("DELETE FROM orphan_fact_orders")
        engine_orphan.commit()

        target_columns = [
            'order_id', 'order_date_id', 'customer_id', 'restaurant_id', 
            'driver_id', 'region_id', 'order_time', 'delivery_time', 
            'row_timestamp', 'order_amount', 'status', 
            'delivery_duration_min', 'is_on_time'
        ]
        
        # Select target columns and fix Pandas null types (NaT/NaN)
        fact_orphan = fact_orphan[target_columns].copy()
        fact_orphan = fact_orphan.where(pd.notnull(fact_orphan), None)
         
        logger.info(f"Retrieved {len(fact_orphan)} orphan orders. Re-submitting to DWH...")
        
        load_fact_order(fact_orphan)

    except Exception as e:
        logger.error(f"Error handling order orphans: {e}")
        engine_orphan.rollback()
    finally:
        engine_orphan.close()

def handle_ticket_orphan(db_name='dwh_db', orphan_db='orphan_db'):
    """Re-processes orphan tickets by pulling them from the orphan DB and clearing it."""
    engine_orphan = get_postgres_conn(orphan_db)
    if not engine_orphan:
        logger.error(f"Could not connect to {orphan_db}. Skipping ticket orphans.")
        return

    try:
        fact_orphan = pd.read_sql("SELECT * FROM orphan_fact_tickets", engine_orphan)
        
        if fact_orphan.empty:
            logger.info("No orphan tickets to process.")
            return

        with engine_orphan.cursor() as cur:
            cur.execute("DELETE FROM orphan_fact_tickets")
        engine_orphan.commit()

        target_columns = [
            "ticket_id", "order_id", "created_date_id", "customer_id",
            "restaurant_id", "driver_id", "region_id", "agent_id",
            "reason_id", "priority_id", "channel_id", "ticket_create_time",
            "sla_first_due_at", "sla_resolve_due_at", "first_response_at",
            "resolved_at", "status", "refund_amount", "resolved_on_time",
            "resolve_from_creating_min", "resolve_from_response_min", "delay_of_resolving"
        ]

        fact_orphan = fact_orphan[target_columns].copy()
        fact_orphan = fact_orphan.where(pd.notnull(fact_orphan), None)

        logger.info(f"Retrieved {len(fact_orphan)} orphan tickets. Re-submitting to DWH...")
    
        load_fact_ticket(fact_orphan)



    except Exception as e:
        logger.error(f"Error handling ticket orphans: {e}")
        engine_orphan.rollback()
    finally:
        engine_orphan.close()

if __name__ == "__main__":
    logger.info("Starting Orphan Re-processing Job")
    handle_order_orphan()
    handle_ticket_orphan()
    logger.info("Orphan Re-processing Job Finished")