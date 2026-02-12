import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


load_dotenv()


def _build_database_url() -> str:
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")

    missing = [
        key
        for key, value in [
            ("DB_USER", db_user),
            ("DB_PASS", db_pass),
            ("DB_HOST", db_host),
            ("DB_PORT", db_port),
            ("DB_NAME", db_name),
        ]
        if not value
    ]
    if missing:
        raise ValueError(
            f"Missing required DB env vars: {', '.join(missing)}. "
            "Set them in environment or .env before starting the app."
        )

    return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"


DATABASE_URL = _build_database_url()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
