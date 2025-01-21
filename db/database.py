import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

USER = os.getenv("DB_USER")
PASS = os.getenv("DB_PASS")
NAME = os.getenv("DB_NAME")
HOST = os.getenv("DB_HOST")
PORT = os.getenv("DB_PORT")
DATABASE_URL = f"postgresql://{USER}:{PASS}@{HOST}:{PORT}/{NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
