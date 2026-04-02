import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
import logging

# 1. Path and Logging Setup
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

try:
    from config.logging_config import setup_logging
    setup_logging()
    logger = logging.getLogger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

def transform_tickets_to_fact(input_df):
    """
    Transforms Ticket source data into DWH Fact Ticket format with 
    calculated SLA metrics and string-formatted timestamps.
    """
    logger.info(f"Processing {len(input_df)} ticket records.")

    try:
        # Convert necessary columns to datetime for calculations
        dt_cols = ['created_at', 'first_response_at', 'resolved_at', 'sla_first_due_at', 'sla_resolve_due_at']
        for col in dt_cols:
            input_df[col] = pd.to_datetime(input_df[col])

        fact_df = pd.DataFrame()

        # --- Basic ID Mapping ---
        fact_df['ticket_id'] = input_df['ticket_id'].astype(str)
        fact_df['order_id'] = input_df['order_id'].astype(str)
        fact_df['created_date_id'] = input_df['created_at'].dt.strftime('%Y%m%d').astype(int)
        
        # Pass-through IDs
        cols_to_copy = [
            'customer_id', 'restaurant_id', 'driver_id', 
            'agent_id', 'reason_id', 'priority_id', 'channel_id'
        ]
        for col in cols_to_copy:
            fact_df[col] = input_df[col]

        # --- Time Fields (Strictly Strings) ---
        fact_df['ticket_create_time'] = input_df['created_at'].dt.strftime('%Y-%m-%d %H:%M:%S')
        fact_df['sla_first_due_at'] = input_df['sla_first_due_at'].dt.strftime('%Y-%m-%d %H:%M:%S')
        fact_df['sla_resolve_due_at'] = input_df['sla_resolve_due_at'].dt.strftime('%Y-%m-%d %H:%M:%S')
        fact_df['first_response_at'] = input_df['first_response_at'].dt.strftime('%Y-%m-%d %H:%M:%S')
        fact_df['resolved_at'] = input_df['resolved_at'].dt.strftime('%Y-%m-%d %H:%M:%S')

        # --- Status and Metrics ---
        fact_df['status'] = input_df['status']
        fact_df['refund_amount'] = input_df['refund_amount'].fillna(0.0)

        # --- SLA Calculations (Minutes) ---
        # 1. Resolve from creation
        fact_df['resolve_from_creating_min'] = (
            (input_df['resolved_at'] - input_df['created_at']).dt.total_seconds() / 60
        ).fillna(0).astype(int)

        # 2. Resolve from first response
        fact_df['resolve_from_response_min'] = (
            (input_df['resolved_at'] - input_df['first_response_at']).dt.total_seconds() / 60
        ).fillna(0).astype(int)

        # 3. Delay of resolving (Minutes past the SLA deadline)
        delay = (input_df['resolved_at'] - input_df['sla_resolve_due_at']).dt.total_seconds() / 60
        fact_df['delay_of_resolving'] = delay.apply(lambda x: int(x) if x > 0 else 0)

        # 4. Resolved on time (Boolean as String)
        fact_df['resolved_on_time'] = (input_df['resolved_at'] <= input_df['sla_resolve_due_at']).astype(str)

        # Final Clean: Handle Nulls for SQL safety
        fact_df = fact_df.where(pd.notnull(fact_df), None)

        logger.info("Ticket transformation successful.")
        return fact_df

    except Exception as e:
        logger.error(f"Ticket transformation failed: {e}")
        raise

# # --- Test with your provided data ---
# if __name__ == "__main__":
#     raw_tickets = [
#         {
#             "ticket_id": "3c178a5e-7207-43ed-b51a-c4ca6fdd354b",
#             "order_id": "3bb9d7df-1b6f-4e91-aa62-c338800a3540",
#             "customer_id": 299, "driver_id": 87, "restaurant_id": 8, "agent_id": 1,
#             "reason_id": 3, "priority_id": 3, "channel_id": 4, "status": "Closed",
#             "refund_amount": 0.0, "created_at": "2026-02-20 15:32:05",
#             "first_response_at": "2026-02-20 15:32:55", "resolved_at": "2026-02-20 16:06:05",
#             "sla_first_due_at": "2026-02-20 15:33:05", "sla_resolve_due_at": "2026-02-20 15:47:05"
#         }
#     ]
    
#     df_in = pd.DataFrame(raw_tickets)
#     df_out = transform_tickets_to_fact(df_in)
    
#     logger.info("Sample Output JSON:")
#     logger.info(df_out.to_json(orient="records", indent=2))