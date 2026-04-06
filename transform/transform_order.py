import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
import logging

# 1. Path Setup and Logging Configuration
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

try:
    from config.logging_config import setup_logging
    setup_logging()
    logger = logging.getLogger(__name__)
except ImportError:
    # Fallback if config is not present
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

def transform_to_order_fact(input_df):
    """
    Transforms input into a Fact table format where all 
    date/time fields are strictly strings.
    """
    logger.info(f"Starting transformation for {len(input_df)} records.")
    
    try:
        # 1. Convert to datetime objects temporarily for calculations
        temp_created = pd.to_datetime(input_df['order_created_at'])
        temp_delivered = pd.to_datetime(input_df['delivered_at'])

        fact_df = pd.DataFrame()

        # --- ID and Basic Mapping ---
        fact_df['order_id'] = input_df['order_id'].astype(str)
        fact_df['order_date_id'] = temp_created.dt.strftime('%Y%m%d').astype(int)
        fact_df['customer_id'] = input_df['customer_id']
        fact_df['restaurant_id'] = input_df['restaurant_id']
        fact_df['driver_id'] = input_df['driver_id']
        fact_df['region_id'] = input_df['region_id']

        # --- Date/Time Fields (Strictly Strings) ---
        fact_df['order_time'] = temp_created.dt.strftime('%Y-%m-%d %H:%M:%S')
        fact_df['delivery_time'] = temp_delivered.dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Generate the processing timestamp as a string
        fact_df['row_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # --- Metrics and Status ---
        fact_df['order_amount'] = input_df['total_amount']
        fact_df['status'] = input_df['order_status'].astype(str)

        # --- SLA Calculations ---
        duration = (temp_delivered - temp_created).dt.total_seconds() / 60
        fact_df['delivery_duration_min'] = duration.fillna(0).astype(int)

        # Boolean result as a String "True" or "False"
        fact_df['is_on_time'] = (fact_df['delivery_duration_min'] <= 45).astype(str)

        # 2. Final Sanitize: Ensure NaT/NaN are converted to None for SQL safety
        fact_df = fact_df.where(pd.notnull(fact_df), None)
        
        logger.info("Transformation completed successfully.")
        return fact_df

    except Exception as e:
        logger.error(f"Transformation failed: {str(e)}")
        raise

# df = pd.read_json("output_orders_clean.json", orient="records")
# df_fact = transform_to_string_fact(df)
# df_fact.to_json("output_orders_fact.json", orient="records", indent=2)
# print(df_fact.dtypes)
# --- Test Execution ---

# raw_data = {
#     "order_id": ["101", "102"],
#     "customer_id": [1, 2],
#     "restaurant_id": [55, 60],
#     "driver_id": [10, 11],
#     "region_id": [1, 2],
#     "total_amount": [25.50, 42.00],
#     "order_status": ["Delivered", "Delivered"],
#     "order_created_at": ["2026-03-31 10:00:00", "2026-03-31 11:00:00"],
#     "delivered_at": ["2026-03-31 10:30:00", "2026-03-31 12:15:00"] 
# }

# logger.info("Initializing Test Data...")
# df_test_input = pd.DataFrame(raw_data)

# # Run transformation
# df_fact_output = transform_to_string_fact(df_test_input)

# # Verify results via Logger
# logger.info("--- Data Sample (JSON Format) ---")
# logger.info(df_fact_output.to_json(orient="records", indent=2))

# # Type Verification
# first_row = df_fact_output.iloc[0]
# logger.info(f"VERIFICATION: order_time is {type(first_row['order_time'])}")
# logger.info(f"VERIFICATION: row_timestamp is {type(first_row['row_timestamp'])}")
# logger.info(f"VERIFICATION: is_on_time is {type(first_row['is_on_time'])}")

# if isinstance(first_row['order_time'], str):
#     logger.info("Type Check Passed: Date fields are strings.")
# else:
#     logger.warning("Type Check Failed: Date fields are NOT strings.")