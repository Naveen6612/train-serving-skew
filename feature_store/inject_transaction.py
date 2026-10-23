
import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# -------------------------------
# Configuration
# -------------------------------

CSV_PATH = Path("feature_repo/data/ecommerce_transactions.csv")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "feature_store_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

TABLE_NAME = "ecommerce_transactions"

# Change this to match your CSV's actual date column.
TRANSACTION_DATE_COLUMN = "Date"


def load_csv(csv_path: Path) -> pd.DataFrame:
    """Read and validate the input CSV."""

    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {csv_path.resolve()}"
        )

    df = pd.read_csv(csv_path)

    if df.empty:
        raise ValueError("The CSV file contains no rows.")

    df.columns = df.columns.str.strip()

    if df.columns.duplicated().any():
        raise ValueError("Duplicate column names found in the CSV.")

    print(f"Loaded {len(df)} rows from {csv_path}")
    print("Columns:", df.columns.tolist())

    return df


def standardize_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Convert event timestamps to UTC and create created_timestamp."""

    if TRANSACTION_DATE_COLUMN not in df.columns:
        raise ValueError(
            f"Missing date column '{TRANSACTION_DATE_COLUMN}'. "
            f"Available columns: {df.columns.tolist()}"
        )

    # Parse timestamps; invalid or missing values become NaT.
    df[TRANSACTION_DATE_COLUMN] = pd.to_datetime(
        df[TRANSACTION_DATE_COLUMN],
        errors="coerce",
        utc=True,
    )

    invalid_count = df[TRANSACTION_DATE_COLUMN].isna().sum()

    if invalid_count:
        raise ValueError(
            f"{invalid_count} rows have invalid or missing "
            f"{TRANSACTION_DATE_COLUMN} values. Fix these rows "
            "before ingestion."
        )

    # Use the event timestamp as created_timestamp when absent.
    if "created_timestamp" not in df.columns:
        df["created_timestamp"] = df[TRANSACTION_DATE_COLUMN]
    else:
        df["created_timestamp"] = pd.to_datetime(
            df["created_timestamp"],
            errors="coerce",
            utc=True,
        )

        invalid_created = df["created_timestamp"].isna().sum()

        if invalid_created:
            raise ValueError(
                f"{invalid_created} rows have invalid or missing "
                "created_timestamp values."
            )

    print("Timestamps standardized to UTC.")
    return df


def ingest_to_postgres(df: pd.DataFrame) -> None:
    """Write the DataFrame to PostgreSQL."""

    # Build the URL safely, including passwords with special characters.
    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    try:
        # Verify database connectivity before writing.
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        print(f"Connected to PostgreSQL database: {DB_NAME}")

        # Replace the table on each full CSV ingestion.
        df.to_sql(
            name=TABLE_NAME,
            con=engine,
            if_exists="replace",
            index=False,
            chunksize=1000,
            method="multi",
        )

        print(
            f"Successfully loaded {len(df)} rows "
            f"into '{TABLE_NAME}'."
        )

        with engine.connect() as connection:
            row_count = connection.execute(
                text(f'SELECT COUNT(*) FROM "{TABLE_NAME}"')
            ).scalar_one()

        print(f"Verified database row count: {row_count}")

    finally:
        engine.dispose()


def main() -> None:
    try:
        df = load_csv(CSV_PATH)
        df = standardize_timestamps(df)
        ingest_to_postgres(df)
    except Exception as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
