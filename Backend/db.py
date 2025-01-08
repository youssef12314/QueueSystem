import logging
from mysql.connector import pooling, Error as MySQLError
from datetime import datetime, timedelta
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# MySQL connection pool configuration
try:
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="mypool",
        pool_size=5,
        host="localhost",
        user="root",
        password="X94nunecayjnc",  
        database="queue_management"
    )
    logging.info("Database connection pool initialized successfully.")
except MySQLError as err:
    logging.error(f"Error initializing database connection pool: {err}")
    raise


def get_db_connection():
    try:
        connection = connection_pool.get_connection()
        return connection
    except MySQLError as err:
        logging.error(f"Error getting connection from pool: {err}")
        raise err


def remove_inactive_users():
    while True:
        try:
            with get_db_connection() as db, db.cursor() as cursor:
                threshold_time = datetime.now() - timedelta(minutes=5)
                cursor.execute("DELETE FROM customers WHERE last_active < %s", (threshold_time,))
                db.commit()
                logging.info(f"Inactive users removed successfully at {datetime.now()}.")
            time.sleep(30)
        except MySQLError as e:
            logging.error(f"Database error in remove_inactive_users: {e}")
        except Exception as e:
            logging.error(f"Unexpected error in remove_inactive_users: {e}")
