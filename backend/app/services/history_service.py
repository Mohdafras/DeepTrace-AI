"""History persistence operations."""
from app.database import get_connection


def create_record(**values: object) -> int:
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO detections (original_filename, predicted_class, real_probability,
              fake_probability, confidence_score, processing_time_ms, threshold)
            VALUES (:original_filename, :predicted_class, :real_probability,
              :fake_probability, :confidence_score, :processing_time_ms, :threshold)
        """, values)
        return int(cursor.lastrowid)


def list_records() -> list[dict[str, object]]:
    with get_connection() as connection:
        return [dict(row) for row in connection.execute("SELECT * FROM detections ORDER BY id DESC")]


def get_record(record_id: int) -> dict[str, object] | None:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM detections WHERE id = ?", (record_id,)).fetchone()
        return dict(row) if row else None


def delete_record(record_id: int) -> bool:
    with get_connection() as connection:
        return connection.execute("DELETE FROM detections WHERE id = ?", (record_id,)).rowcount > 0


def delete_all_records() -> int:
    with get_connection() as connection:
        return connection.execute("DELETE FROM detections").rowcount
