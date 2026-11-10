"""SQLite storage for detection metadata."""
import sqlite3
from contextlib import closing, contextmanager
from collections.abc import Generator

from app.config import settings


def initialize_database() -> None:
    """Create the history table if it does not already exist."""
    db_path = settings.resolve(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_filename TEXT NOT NULL,
                predicted_class TEXT NOT NULL CHECK(predicted_class IN ('REAL', 'FAKE')),
                real_probability REAL NOT NULL,
                fake_probability REAL NOT NULL,
                confidence_score REAL NOT NULL,
                processing_time_ms REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(detections)")}
        if "threshold" not in columns:
            # Do not invent thresholds for records created before this migration.
            connection.execute("ALTER TABLE detections ADD COLUMN threshold REAL")


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection returning rows as dictionaries."""
    connection = sqlite3.connect(settings.resolve(settings.database_path))
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()
