import psycopg2
from psycopg2 import extras
import connect_to_db
import os
import sys
from psycopg2 import OperationalError
 
import pandas as pd
from datetime import datetime
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# 2. Import settings and setup logging
try:
    from config import settings
    from config.logging_config import setup_logging
    setup_logging()
    logger = logging.getLogger(__name__)
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

    

def handel_order_orphan(db_name='dwh_db',orphan_db='orphan_db'):
    engine_orphan = connect_to_db.get_postgres_conn(orphan_db)
    fact_orphan=pd.read_sql("SELECT * FROM orphan_fact_orders", engine_orphan)
    
    with engine_orphan.cursor() as cur:
       cur.execute("DELETE FROM orphan_fact_orders")
    engine_orphan.commit()

    target_columns = [
             'order_id', 'order_date_id', 'customer_id', 'restaurant_id', 
             'driver_id', 'region_id', 'order_time', 'delivery_time', 
            'row_timestamp', 'order_amount', 'status', 
            'delivery_duration_min', 'is_on_time'
        ]
    fact_orphan = fact_orphan[target_columns]
    #load_fact_order(fact_orphan,'dwh_db','orphan_db')



def handel_ticket_orphan(db_name='dwh_db',orphan_db='orphan_db'):
    engine_orphan = connect_to_db.get_postgres_conn(orphan_db)
    fact_orphan=pd.read_sql("SELECT * FROM orphan_fact_tickets", engine_orphan)
    print(fact_orphan.head)
    with engine_orphan.cursor() as cur:
       cur.execute("DELETE FROM orphan_fact_tickets")
    engine_orphan.commit()

    target_columns = [
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
            "delay_of_resolving"
        ]
    fact_orphan = fact_orphan[target_columns]
    #load_fact_ticket(fact_orphan,'dwh_db','orphan_db')

handel_order_orphan()
    