import psycopg2
from psycopg2 import extras
import connect_to_db
import os
import sys
from psycopg2 import OperationalError
# ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# # 2. Import settings (now safe after adding defaults in settings.py)
# from config import settings,schemas
import pandas as pd
from datetime import datetime






def load_fact_order(input_df=None, db_name='dwh_db',orphan_db='orphan_db'):
    


    engine_dwh = connect_to_db.get_postgres_conn(db_name)
    engine_orphan = connect_to_db.get_postgres_conn(orphan_db)

    # 1. Load Dimensions (including the Surrogate Keys)
    dim_cust = pd.read_sql("SELECT customer_id, customer_sk FROM dim_customer", engine_dwh)
    dim_rest = pd.read_sql("SELECT restaurant_id FROM dim_restaurant", engine_dwh)
    dim_driv = pd.read_sql("SELECT driver_id, driver_sk FROM dim_driver", engine_dwh)




     # 2. Left Merge to identify matches and pull SKs
# We use left merge first so we can easily separate clean vs orphan records
    processed_df = input_df.merge(dim_cust, on='customer_id', how='left') \
                        .merge(dim_rest, on='restaurant_id', how='left') \
                        .merge(dim_driv, on='driver_id', how='left')
# # 3. Separate Clean and Orphan records
# # Clean records must have all SKs present (not null)
    condition = (
        processed_df['customer_sk'].notna() & 
        processed_df['restaurant_id'].notna() & 
        processed_df['driver_sk'].notna()
    )

    clean_df = processed_df[condition].copy()
    orphan_df = processed_df[~condition].copy()
  
    # --- 4. Process Clean Records ---
    if not clean_df.empty:
        # Drop any columns that aren't in the DWH table (like the original business keys if not needed)
        # Assuming the DWH table structure matches clean_df columns exactly
        target_columns = [
             'order_id', 'order_date_id', 'customer_sk', 'restaurant_id', 
             'driver_sk', 'region_id', 'order_time', 'delivery_time', 
            'row_timestamp', 'order_amount', 'status', 
            'delivery_duration_min', 'is_on_time'
        ]   

# Create a filtered version of the dataframe
        df_to_insert = clean_df[target_columns].copy()

        with engine_dwh.cursor() as cur:
            records = [tuple(x) for x in df_to_insert.to_numpy()]
            columns_str = ', '.join(target_columns)  # explicitly specify columns
            sql = f"""
                INSERT INTO fact_orders ({columns_str})
                VALUES %s
            """
            psycopg2.extras.execute_values(cur, sql, records)
        engine_dwh.commit()
###################### load data here

#     # --- 5. Process Orphan Records ---
    if not orphan_df.empty:
        # Generate metadata for debugging
        orphan_df['is_customer_sk_orphan'] = orphan_df['customer_sk'].isna()
        orphan_df['is_restaurant_sk_orphan'] = orphan_df['restaurant_id'].isna()
        orphan_df['is_driver_sk_orphan'] = orphan_df['driver_sk'].isna()
        
        # Calculate how many FKs failed
        orphan_df['unmatched_fk_count'] = (
            orphan_df[['is_customer_sk_orphan', 'is_restaurant_sk_orphan', 'is_driver_sk_orphan']]
            .sum(axis=1)
        )
        


#-------------------------------------------------------------
    def get_reason(row):
        reasons = []
        # Using .get(column, default) prevents KeyError
        if row.get('is_customer_sk_orphan'): reasons.append("Missing Customer SK")
        if row.get('is_restaurant_sk_orphan'): reasons.append("Missing Restaurant SK")
        if row.get('is_driver_sk_orphan'): reasons.append("Missing Driver SK")
        return ", ".join(reasons)

# Apply the logic
    orphan_df['rejection_reason'] = orphan_df.apply(get_reason, axis=1)
    orphan_df['rejected_at'] = datetime.now()
    target_columns = [
            'rejection_reason','unmatched_fk_count','rejected_at', 'order_id', 'order_date_id', 'customer_id', 'restaurant_id', 
            'driver_id', 'region_id', 'order_time', 'delivery_time', 
            'row_timestamp', 'order_amount', 'status', 
            'delivery_duration_min', 'is_on_time','is_customer_sk_orphan',
            'is_restaurant_sk_orphan','is_driver_sk_orphan',
        ]   
    

    df_orphan_insert=orphan_df[target_columns].copy()
    with engine_orphan.cursor() as cur:
            records = [tuple(x) for x in df_orphan_insert.to_numpy()]
            columns_str = ', '.join(target_columns)  # explicitly specify columns
            sql = f"""
                INSERT INTO orphan_fact_orders ({columns_str})
                VALUES %s
            """
            psycopg2.extras.execute_values(cur, sql, records)
    engine_orphan.commit()
        # Load to Orphan Table
    # orphan_df.to_sql(orphan_table_name, engine_orphan, if_exists='append', index=False)
    # print(f"Loaded {len(orphan_df)} orphan records to {orphan_table_name}.")
 ###################### load data here









#----------------------------------------------------


def load_fact_ticket(input_df=None, db_name='dwh_db',orphan_db='orphan_db'):
    


    engine_dwh = connect_to_db.get_postgres_conn(db_name)
    engine_orphan = connect_to_db.get_postgres_conn(orphan_db)

    # 1. Load Dimensions (including the Surrogate Keys)
    dim_fact = pd.read_sql("SELECT order_id FROM fact_orders", engine_dwh)
    dim_agent = pd.read_sql("SELECT agent_id,agent_sk FROM dim_agent", engine_dwh)
    dim_cust = pd.read_sql("SELECT customer_id, customer_sk FROM dim_customer", engine_dwh)
    dim_driv = pd.read_sql("SELECT driver_id, driver_sk FROM dim_driver", engine_dwh)




     # 2. Left Merge to identify matches and pull SKs
# We use left merge first so we can easily separate clean vs orphan records
    processed_df = input_df.merge(dim_fact, on='order_id', how='left') \
                        .merge(dim_agent, on='agent_id', how='left') \
                        .merge(dim_cust, on='customer_id', how='left') \
                         .merge(dim_driv, on='driver_id', how='left')
 # # 3. Separate Clean and Orphan records
# # Clean records must have all SKs present (not null)
    condition = (
        processed_df['order_id'].notna() & 
        processed_df['agent_id'].notna() 
     )

    clean_df = processed_df[condition].copy()
    orphan_df = processed_df[~condition].copy()
  
    # --- 4. Process Clean Records ---
    if not clean_df.empty:
        # Drop any columns that aren't in the DWH table (like the original business keys if not needed)
        # Assuming the DWH table structure matches clean_df columns exactly
        target_columns = [
            "ticket_id",   "order_id",
            "created_date_id",            "customer_sk",
            "restaurant_id",            "driver_sk",
            "region_id",            "agent_sk",
            "reason_id",            "priority_id",
            "channel_id",            "ticket_create_time",
            "sla_first_due_at",            "sla_resolve_due_at",
            "first_response_at",            "resolved_at",
            "status",            "refund_amount",
            "resolved_on_time",            "resolve_from_creating_min",
            "resolve_from_response_min",            "delay_of_resolving"
    ]

# Create a filtered version of the dataframe
     
        df_to_insert = clean_df[target_columns].copy()

        for col in [
            "ticket_create_time", "sla_first_due_at", "sla_resolve_due_at",
            "first_response_at", "resolved_at"
        ]:
            df_to_insert[col] = pd.to_datetime(df_to_insert[col], errors='coerce')

        with engine_dwh.cursor() as cur:
            records = [tuple(x) for x in df_to_insert.to_numpy()]
            columns_str = ', '.join(target_columns)

            sql = f"""
                INSERT INTO fact_tickets ({columns_str})
                VALUES %s
            """
            psycopg2.extras.execute_values(cur, sql, records)

        engine_dwh.commit()

#     # --- 5. Process Orphan Records ---
    if not orphan_df.empty:
        # Generate metadata for debugging
        orphan_df['is_order_id_orphan'] = orphan_df['order_id'].isna()
        orphan_df['is_agent_sk_orphan'] = orphan_df['agent_id'].isna()
        
        # Calculate how many FKs failed
        orphan_df['unmatched_fk_count'] = (
            orphan_df[['is_order_id_orphan', 'is_agent_sk_orphan' ]]
            .sum(axis=1)
        )
        
#         # Create a descriptive rejection reason
        def get_reason(row):
            reasons = []
            # Using .get(column, default) prevents KeyError
            if row.get('is_order_id_orphan'): reasons.append("Missing order id")
            if row.get('is_agent_sk_orphan'): reasons.append("Missing agent SK")
            return ", ".join(reasons)

    # Apply the logic
        orphan_df['rejection_reason'] = orphan_df.apply(get_reason, axis=1)
        orphan_df['rejected_at'] = datetime.now()
        target_columns = [
            'unmatched_fk_count'
            'rejection_reason',
            "ticket_id",
            "order_id",
            "created_date_id",
            "customer_id",
            "restaurant_id",
            "driver_id",
            "region_id",
            "agent_id",
            "reason_id",
            "priority_id",
            "channel_id",
            "ticket_create_time",
            "sla_first_due_at",
            "sla_resolve_due_at",
            "first_response_at",
            "resolved_at",
            "status",
            "refund_amount",
            "resolved_on_time",
            "resolve_from_creating_min",
            "resolve_from_response_min",
            "delay_of_resolving",
            "is_order_id_orphan",
            "is_agent_sk_orphan"
        ]
        df_to_insert = orphan_df[target_columns].copy()

        with engine_orphan.cursor() as cur:
            records = [tuple(x) for x in df_to_insert.to_numpy()]
            columns_str = ', '.join(target_columns)

            sql = f"""
                INSERT INTO orphan_fact_tickets ({columns_str})
                VALUES %s
            """
            psycopg2.extras.execute_values(cur, sql, records)

        engine_dwh.commit()



#-------------------------------------------------

#
def solve_orphan_ticket_order_id(fact_order_df, orphan_db='orphan_db'):
    conn = connect_to_db.get_postgres_conn(orphan_db)
    
    # Load orphan tickets
    orphan_ticket = pd.read_sql("SELECT * FROM orphan_fact_tickets", conn)
    
    # Find tickets that exist in fact_order_df
    processed_df = orphan_ticket.merge(fact_order_df, on='order_id', how='inner')
    
    if not processed_df.empty:
        order_ids = processed_df['order_id'].tolist()  # list, not tuple

        # Use parameterized query with ANY() — safe even for large lists
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE orphan_fact_tickets SET is_order_id_orphan = FALSE WHERE order_id = ANY(%s)",
                (order_ids,)  # pass as a tuple containing the list
            )
        conn.commit()
def load_ticket_event(input_df, db_name='dwh_db'):
    engine_dwh = connect_to_db.get_postgres_conn(db_name)
    fact_tickets=pd.read_sql("SELECT order_id FROM fact_tickets", engine_dwh)
    # convert to datetime
    input_df['event_ts'] = pd.to_datetime(input_df['event_ts'])

    # get unique tickets
    ticket_ids = input_df['ticket_id'].unique()

    with engine_dwh.begin() as conn:
        for ticket_id in ticket_ids:

            df = input_df[input_df['ticket_id'] == ticket_id]
            df = df.sort_values('event_ts')

            # initialize values
            ticket_create_time = None
            first_response_at = None
            resolved_at = None
            closed_at=None
            status = None

            # loop over events
            for _, row in df.iterrows():

                if row['new_status'] == 'Open' and ticket_create_time is None:
                    ticket_create_time = row['event_ts']

                elif row['new_status'] == 'InProgress' and first_response_at is None:
                    first_response_at = row['event_ts']
                
                elif row['new_status'] == 'Resolved':
                    resolved_at = row['event_ts']

                elif row['new_status'] == 'Closed':
                    closed_at = row['event_ts']

                

                # always update latest status
                status = row['new_status']

            # simple SLA calc
            resolve_from_creating_min = None
            resolve_from_response_min = None

            if ticket_create_time and resolved_at:
                resolve_from_creating_min = (resolved_at - ticket_create_time).total_seconds() / 60

            if first_response_at and resolved_at:
                resolve_from_response_min = (resolved_at - first_response_at).total_seconds() / 60

            resolved_on_time = None
            if resolve_from_creating_min:
                resolved_on_time = resolve_from_creating_min <= 60

            # update DB
            conn.execute("""
                UPDATE fact_tickets
                SET 
                    ticket_create_time = %s,
                    first_response_at = %s,
                    resolved_at = %s,
                    status = %s,
                    resolve_from_creating_min = %s,
                    resolve_from_response_min = %s,
                    resolved_on_time = %s
                WHERE ticket_id = %s
            """, (
                ticket_create_time,
                first_response_at,
                resolved_at,
                status,
                resolve_from_creating_min,
                resolve_from_response_min,
                resolved_on_time,
                ticket_id
            ))

    


 
df=pd.read_json('orders.json')
load_fact_order(df)