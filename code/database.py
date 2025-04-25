import os
import psycopg2
from psycopg2.extras import DictCursor


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Consider raising a specific exception or logging an error
    # if the DATABASE_URL is critical and not found.
    # For simplicity here, we'll let psycopg2 connection fail or add a check.
    print("Warning: DATABASE_URL environment variable not set.")


class Database:
    def __init__(self):
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL is not set. Cannot connect to database.")
        # Connect to the database
        self.conn = psycopg2.connect(DATABASE_URL)
        # Initialize the necessary table
        self.init_db()

    def init_db(self):
        """Creates the students table if it doesn't exist."""
        with self.conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                user_id BIGINT,
                student_number TEXT,
                student_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, student_number)
            )
            """)
        self.conn.commit()

    def add_student(self, user_id: int, number: str, name: str):
        """Adds or updates a student record for a user."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO students (user_id, student_number, student_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, student_number)
                DO UPDATE SET student_name = EXCLUDED.student_name;
                """,
                (user_id, number, name),
            )
        self.conn.commit()

    def get_students(self, user_id: int, order_by: str = "student_number"):
        """Retrieves all students for a given user, ordered as specified."""
        # Validate order_by to prevent SQL injection (allow only specific columns)
        allowed_orders = {"student_number", "student_name"}
        if order_by not in allowed_orders:
            order_by = "student_number"  # Default to a safe value

        # Use f-string carefully here because we validated order_by against a fixed set
        query = f"""
            SELECT student_number, student_name
            FROM students
            WHERE user_id = %s
            ORDER BY {order_by}
        """
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(query, (user_id,))
            return cur.fetchall()

    def find_students(self, user_id: int, query: str):
        """Finds students by number (exact) or name (partial, case-insensitive)."""
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT student_number, student_name FROM students
                WHERE user_id = %s
                AND (student_number = %s OR LOWER(student_name) LIKE %s)
                ORDER BY student_number;
                """,
                (user_id, query, f"%{query.lower()}%"),
            )
            return cur.fetchall()

    # TODO: Add methods for edit and delete later

    # Optional: Add a close method to close the connection when the bot stops
    def close(self):
        if self.conn:
            self.conn.close()
