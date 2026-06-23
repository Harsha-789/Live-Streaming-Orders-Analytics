"""
db_manager.py - Database management module for Live Streaming Orders Analytics

Key design:
- load_data() reads ONLY the new/delta rows (by tracking row count) instead of
  re-reading the entire CSV on every change — scales to large datasets.
- Each caller opens its own connection via get_connection() (SQLite is not
  thread-safe across connections).
"""

import sqlite3
import pandas as pd

DB_FILE    = "orders.db"
TABLE_NAME = "orders"


def get_connection(db_file: str = DB_FILE) -> sqlite3.Connection:
    """Open (or create) the SQLite database and ensure the schema exists."""
    conn = sqlite3.connect(db_file)
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    """Create orders table and a metadata table to track CSV row offset."""
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            order_id    INTEGER,
            customer_id INTEGER,
            product_id  INTEGER,
            quantity    INTEGER,
            order_date  TEXT
        )
    """)
    # Tracks how many CSV rows have already been read (enables delta loading)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _meta (
            key   TEXT PRIMARY KEY,
            value INTEGER
        )
    """)
    conn.execute("INSERT OR IGNORE INTO _meta (key, value) VALUES ('csv_rows_loaded', 0)")
    conn.commit()


def _get_csv_offset(conn: sqlite3.Connection) -> int:
    """Return the number of CSV rows already loaded into the DB."""
    row = conn.execute("SELECT value FROM _meta WHERE key='csv_rows_loaded'").fetchone()
    return row[0] if row else 0


def _set_csv_offset(conn: sqlite3.Connection, offset: int) -> None:
    conn.execute("UPDATE _meta SET value=? WHERE key='csv_rows_loaded'", (offset,))
    conn.commit()


def load_data(conn: sqlite3.Connection, csv_file: str) -> int:
    """
    Load ONLY the new (delta) rows from csv_file since the last load.
    Skips rows already seen using a stored row-count offset.
    Filters invalid (non-positive) quantities and exact duplicates.
    Returns the number of net new rows inserted.
    """
    try:
        offset = _get_csv_offset(conn)

        # Count total rows without loading the whole file
        total_rows = sum(1 for _ in open(csv_file)) - 1  # subtract header

        if total_rows <= offset:
            return 0  # Nothing new

        # Read ONLY the new rows (delta)
        df = pd.read_csv(csv_file, skiprows=range(1, offset + 1), on_bad_lines="skip")  # skip already-loaded rows
        df = df[df["quantity"] > 0].drop_duplicates()

        if df.empty:
            _set_csv_offset(conn, total_rows)
            return 0

        before = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
        df.to_sql(TABLE_NAME, conn, if_exists="append", index=False)

        # Remove any exact duplicates that may have arrived
        conn.execute(f"""
            DELETE FROM {TABLE_NAME}
            WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM {TABLE_NAME}
                GROUP BY order_id, customer_id, product_id, quantity, order_date
            )
        """)
        conn.commit()

        after = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
        _set_csv_offset(conn, total_rows)
        return after - before

    except Exception as exc:
        print(f"[db_manager] load_data error: {exc}")
        return 0


def query_product_totals(conn: sqlite3.Connection) -> pd.DataFrame:
    """Return total quantity grouped by product_id, sorted ascending."""
    return pd.read_sql(
        f"SELECT product_id, SUM(quantity) AS total_qty FROM {TABLE_NAME} GROUP BY product_id ORDER BY product_id",
        conn,
    )


def query_date_totals(conn: sqlite3.Connection) -> pd.DataFrame:
    """Return total quantity grouped by order_date, sorted chronologically."""
    return pd.read_sql(
        f"SELECT order_date, SUM(quantity) AS total_qty FROM {TABLE_NAME} GROUP BY order_date ORDER BY order_date",
        conn,
    )
