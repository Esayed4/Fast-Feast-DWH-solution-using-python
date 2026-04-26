import os
import sys
import logging
import pandas as pd
import numpy as np
import psycopg2
from psycopg2 import extras
from datetime import datetime
from loader import connect_to_db

# 1. Path and Logging Setup
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

try:
    from config import settings
    from config.logging_config import setup_logging
    logger = logging.getLogger(__name__)
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# --- Helper Function for Null Handling ---
def clean_for_psycopg2(df, columns):
    """Ensures DataFrame only has target columns and converts NaN/NaT to None."""
    clean_df = df[columns].copy()
    for col in columns:
        clean_df[col] = clean_df[col].apply(lambda x: None if pd.isna(x) or x is pd.NA else x)
    return clean_df
 
# --- 1. Load Fact Orders ---
def load_fact_order(input_df=None, db_name='dwh_db', orphan_db='orphan_db'):
    if input_df is None or input_df.empty:
        logger.info("No orders provided for processing.")
        return 0, 0

    engine_dwh = connect_to_db.get_postgres_conn(db_name)
    engine_orphan = connect_to_db.get_postgres_conn(orphan_db)

    try:
        # Load Dimensions
        dim_cust = pd.read_sql("SELECT customer_id, customer_sk FROM DWH.dim_customer WHERE is_current=True", engine_dwh)
        dim_rest = pd.read_sql("SELECT restaurant_id AS restaurant_id_dwh FROM DWH.dim_restaurant", engine_dwh)
        dim_driv = pd.read_sql("SELECT driver_id, driver_sk FROM DWH.dim_driver WHERE is_current=True", engine_dwh)

        # Merge
        processed_df = input_df.merge(dim_cust, on='customer_id', how='left') \
                               .merge(dim_rest, left_on='restaurant_id', right_on='restaurant_id_dwh', how='left') \
                               .merge(dim_driv, on='driver_id', how='left')

        condition = (
            processed_df['customer_sk'].notna() & 
            processed_df['restaurant_id_dwh'].notna() & 
            processed_df['driver_sk'].notna()
        )

        clean_df = processed_df[condition].copy()
        orphan_df = processed_df[~condition].copy()
        loaded_count = 0
        orphan_count = 0

        # Insert Clean Records
        if not clean_df.empty:
            target_cols = [
                'order_id', 'order_date_id', 'customer_sk', 'restaurant_id', 
                'driver_sk', 'region_id', 'order_time', 'delivery_time', 
                'row_timestamp', 'order_amount', 'status', 
                'delivery_duration_min', 'is_on_time'
            ]
            df_to_insert = clean_for_psycopg2(clean_df, target_cols)
            with engine_dwh.cursor() as cur:
                extras.execute_values(cur, f"INSERT INTO DWH.fact_orders ({','.join(target_cols)}) VALUES %s", 
                                      [tuple(x) for x in df_to_insert.values.tolist()])
            engine_dwh.commit()
            loaded_count = len(clean_df)  # ADD THIS
            logger.info(f"Loaded {loaded_count} orders to DWH.")
            # logger.info(f"Loaded {len(clean_df)} orders to DWH.")
        
        if not orphan_df.empty:
            orphan_count = len(orphan_df)
            orphan_df['is_customer_sk_orphan'] = orphan_df['customer_sk'].isna()
            orphan_df['is_restaurant_sk_orphan'] = orphan_df['restaurant_id_dwh'].isna()
            orphan_df['is_driver_sk_orphan'] = orphan_df['driver_sk'].isna()
            orphan_df['unmatched_fk_count'] = orphan_df[['is_customer_sk_orphan', 'is_restaurant_sk_orphan', 'is_driver_sk_orphan']].sum(axis=1)
            orphan_df['rejection_reason'] = orphan_df.apply(lambda r: ", ".join([k for k,v in {'Cust':r.is_customer_sk_orphan,'Rest':r.is_restaurant_sk_orphan,'Driv':r.is_driver_sk_orphan}.items() if v]), axis=1)
            orphan_df['rejected_at'] = datetime.now()

            orphan_cols = ['rejection_reason','unmatched_fk_count','rejected_at', 'order_id', 'order_date_id', 'customer_id', 'restaurant_id', 'driver_id', 'region_id', 'order_time', 'delivery_time', 'row_timestamp', 'order_amount', 'status', 'delivery_duration_min', 'is_on_time','is_customer_sk_orphan','is_restaurant_sk_orphan','is_driver_sk_orphan']
            df_orphan_insert = clean_for_psycopg2(orphan_df, orphan_cols)
            with engine_orphan.cursor() as cur:
                extras.execute_values(cur, f"INSERT INTO orphan_fact_orders ({','.join(orphan_cols)}) VALUES %s", 
                                      [tuple(x) for x in df_orphan_insert.values.tolist()])
            engine_orphan.commit()
            orphan_count = len(orphan_df)  # ADD THIS
            logger.warning(f"Sent {orphan_count} orphan orders to Orphan DB.")
            # logger.warning(f"Sent {len(orphan_df)} orphan orders to Orphan DB.")
        return loaded_count, orphan_count
    finally:
        engine_dwh.close()
        engine_orphan.close()

# --- 2. Load Fact Tickets ---
def load_fact_ticket(input_df=None, db_name='dwh_db', orphan_db='orphan_db'):
    if input_df is None or input_df.empty:
        return 0, 0

    engine_dwh = connect_to_db.get_postgres_conn(db_name)
    engine_orphan = connect_to_db.get_postgres_conn(orphan_db)

    try:
        dim_fact = pd.read_sql("SELECT order_id AS orderid_exists,region_id FROM DWH.fact_orders", engine_dwh)
        dim_agent = pd.read_sql("SELECT agent_id, agent_sk FROM DWH.dim_agent WHERE is_current=True", engine_dwh)
        dim_cust = pd.read_sql("SELECT customer_id, customer_sk FROM DWH.dim_customer WHERE is_current=True", engine_dwh)
        dim_driv = pd.read_sql("SELECT driver_id, driver_sk FROM DWH.dim_driver WHERE is_current=True", engine_dwh)
 

        processed_df = input_df.merge(dim_fact, left_on='order_id', right_on='orderid_exists', how='left') \
                               .merge(dim_agent, on='agent_id', how='left') \
                               .merge(dim_cust, on='customer_id', how='left') \
                               .merge(dim_driv, on='driver_id', how='left')
        condition = processed_df['orderid_exists'].notna() & processed_df['agent_sk'].notna()
        clean_df = processed_df[condition].copy()
        orphan_df = processed_df[~condition].copy()
        loaded_count = 0  
        orphan_count = 0  

        if not clean_df.empty:

            target_cols = ["ticket_id", "order_id", "created_date_id", "customer_sk", "restaurant_id", "driver_sk","region_id", "agent_sk", "reason_id", "priority_id", "channel_id", "ticket_create_time", "sla_first_due_at", "sla_resolve_due_at", "first_response_at", "resolved_at", "status", "refund_amount", "resolved_on_time", "resolve_from_creating_min", "resolve_from_response_min", "delay_of_resolving"]
            df_to_insert = clean_for_psycopg2(clean_df, target_cols)
            
            with engine_dwh.cursor() as cur:
                extras.execute_values(cur, f"INSERT INTO DWH.fact_tickets ({','.join(target_cols)}) VALUES %s", 
                                      [tuple(x) for x in df_to_insert.values.tolist()])
            engine_dwh.commit()
            loaded_count = len(clean_df)  # ADD THIS
            logger.info(f"Loaded {loaded_count} tickets to DWH.")

        if not orphan_df.empty:
            orphan_df['is_order_id_orphan'] = orphan_df['orderid_exists'].isna()
            orphan_df['is_agent_sk_orphan'] = orphan_df['agent_sk'].isna()
            orphan_df['unmatched_fk_count'] = orphan_df[['is_order_id_orphan', 'is_agent_sk_orphan']].sum(axis=1)
            orphan_df['rejection_reason'] = orphan_df.apply(lambda r: "Missing Order" if r.is_order_id_orphan else "Missing Agent", axis=1)
            
            orphan_cols = ['unmatched_fk_count', 'rejection_reason', "ticket_id", "order_id", "created_date_id", "customer_id", "restaurant_id", "driver_id", "agent_id", "reason_id", "priority_id", "channel_id", "ticket_create_time", "sla_first_due_at", "sla_resolve_due_at", "first_response_at", "resolved_at", "status", "refund_amount", "resolved_on_time", "resolve_from_creating_min", "resolve_from_response_min", "delay_of_resolving", "is_order_id_orphan", "is_agent_sk_orphan"]
            df_to_orphan = clean_for_psycopg2(orphan_df, orphan_cols)
            with engine_orphan.cursor() as cur:
                extras.execute_values(cur, f"INSERT INTO orphan_fact_tickets ({','.join(orphan_cols)}) VALUES %s", 
                                      [tuple(x) for x in df_to_orphan.values.tolist()])
            engine_orphan.commit()
            orphan_count = len(orphan_df)
            logger.warning(f"Sent {orphan_count} orphan tickets to Orphan DB.")
        return loaded_count, orphan_count
    finally:
        engine_dwh.close()
        engine_orphan.close()



if __name__ == "__main__":
    try:
         
        df = pd.read_json('output_ticket_events_transformed.json')
        df = df.replace({None: np.nan})
        load_fact_ticket(df)
    except Exception as e:
        logger.error(f"Critical error in main: {e}")

 

