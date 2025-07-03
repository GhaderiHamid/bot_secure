import os
import mysql.connector
from mysql.connector import Error, pooling
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

# استفاده از connection pool برای عملکرد بهتر و اتصال پایدارتر
pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **DB_CONFIG)

def get_connection():
    try:
        conn = pool.get_connection()
        if not conn.is_connected():
            conn.reconnect(attempts=3, delay=2)
        return conn
    except Error as e:
        print(f"❌ اتصال به دیتابیس شکست خورد: {e}")
        raise

def execute_query(query, params=None, fetchone=False, fetchall=False, commit=False):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if commit:
            conn.commit()
        if fetchone:
            return cursor.fetchone()
        if fetchall:
            return cursor.fetchall()
    except Error as e:
        print(f"[❌ QUERY ERROR] {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()