import os
import sys
import psycopg2
from psycopg2 import OperationalError

# 1. Add the project root to the path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# 2. Import settings (now safe after adding defaults in settings.py)
try:
    from config import settings
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

    
def get_postgres_conn(db_name):
    """Connects to PostgreSQL and returns the connection object."""
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        print(f"--- [SUCCESS] Connected to: {db_name} ---")
        # logger.info()
        return conn
    except OperationalError as e:
        print(f"--- [ERROR] Connection failed for {db_name}: {e} ---")
        #logger.cretical
        return None

if __name__ == "__main__":
    # Test your three databases
    db_list = [settings.DWH, settings.PII_DB, settings.ORPHAN_DB]
    
    for db in db_list:
        connection = get_postgres_conn(db)
        if connection:
            connection.close()