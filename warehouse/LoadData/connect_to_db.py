import os
import sys
import psycopg2
from psycopg2 import OperationalError
import logging

# 1. Add the project root to the path
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

def get_postgres_conn(db_name):
    """Connects to PostgreSQL and returns the connection object."""
    try:
        # Use settings or env variables with fallbacks
        conn = psycopg2.connect(
            dbname=db_name,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        logger.info(f"Successfully connected to database: {db_name}")
        return conn
    
    except OperationalError as e:
        # Critical because the pipeline cannot proceed without a DB connection
        logger.critical(f"Database connection failed for {db_name}. Error: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while connecting to {db_name}: {e}")
        return None

if __name__ == "__main__":
    logger.info("Starting Database Connection Tests...")
    
    try:
        # List of databases to verify
        db_list = [settings.DWH, settings.PII_DB, settings.ORPHAN_DB]
        
        for db in db_list:
            connection = get_postgres_conn(db)
            if connection:
                # Basic check to ensure it's actually alive
                logger.info(f"Connection test passed for {db}")
                connection.close()
            else:
                # If one mandatory DB is down, you might want to raise an alert
                logger.warning(f"Could not establish connection to {db}. check logs for details.")

    except Exception as e:
        logger.critical(f"Main execution failed: {e}")
    finally:
        logger.info("Database connection test process finished.")