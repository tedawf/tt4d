import os

import psycopg2
from dotenv import load_dotenv


class Database:
    def __init__(self):
        load_dotenv()
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(
                dbname=os.getenv("POSTGRES_NAME"),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASS"),
                host=os.getenv("POSTGRES_HOST"),
                port=os.getenv("POSTGRES_PORT"),
            )
            return True
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return False

    def disconnect(self):
        if self.conn:
            self.conn.close()


# Test database connection
if __name__ == "__main__":
    db = Database()
    if db.connect():
        print("Successfully connected to database!")
        db.disconnect()
