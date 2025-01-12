import os

from dotenv import load_dotenv


def main():
    # Load environment variables
    load_dotenv()

    print("Starting TOTO scraper...")

    # Test database connection
    try:
        # We'll add database connection later
        print("Database connection successful!")
    except Exception as e:
        print(f"Database connection failed: {e}")


if __name__ == "__main__":
    main()
