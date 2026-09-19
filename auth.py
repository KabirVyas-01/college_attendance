import secrets
import string
import sqlite3

def generate_password(length=8) -> str:
    """
    Generates a secure 8-character random alphanumeric password
    using lowercase letters and digits [a-z0-9] (e.g. 'a7b3x9k2').
    """
    chars = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))

def get_next_faculty_id(conn: sqlite3.Connection, dept_code: str) -> int:
    """
    Computes the next available 5-digit Faculty ID for the given department.
    (e.g., 10001 for CSE, 20001 for CE, 30001 for ME, 40001 for EE).
    """
    cursor = conn.cursor()
    cursor.execute("SELECT faculty_start FROM departments WHERE dept_code = ?", (dept_code,))
    dept_row = cursor.fetchone()
    if not dept_row:
        raise ValueError(f"Department code '{dept_code}' not found.")
    
    start_id = dept_row["faculty_start"]
    # Look for the highest faculty_id starting with that range
    cursor.execute(
        "SELECT MAX(faculty_id) as max_id FROM faculty WHERE dept_code = ?",
        (dept_code,)
    )
    row = cursor.fetchone()
    if row and row["max_id"] is not None:
        return row["max_id"] + 1
    return start_id

def get_next_student_uid(conn: sqlite3.Connection, dept_code: str) -> int:
    """
    Computes the next available 6-digit Student UID within the department's branch range.
    (e.g., 100000-199999 for CSE, 200000-299999 for CE, etc.).
    """
    cursor = conn.cursor()
    cursor.execute("SELECT uid_start, uid_end FROM departments WHERE dept_code = ?", (dept_code,))
    dept_row = cursor.fetchone()
    if not dept_row:
        raise ValueError(f"Department code '{dept_code}' not found.")
    
    uid_start = dept_row["uid_start"]
    uid_end = dept_row["uid_end"]

    cursor.execute(
        "SELECT MAX(uid) as max_uid FROM students WHERE dept_code = ?",
        (dept_code,)
    )
    row = cursor.fetchone()
    if row and row["max_uid"] is not None:
        next_uid = row["max_uid"] + 1
        if next_uid > uid_end:
            raise ValueError(f"UID limit reached for department {dept_code} ({uid_end}).")
        return next_uid
    return uid_start

def authenticate_faculty(conn: sqlite3.Connection, faculty_id: int, password: str):
    """
    Verifies faculty credentials and returns faculty details if valid.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT faculty_id, name, dept_code, is_head_teacher FROM faculty WHERE faculty_id = ? AND password = ?",
        (faculty_id, password)
    )
    row = cursor.fetchone()
    if row:
        return dict(row)
    return None

def authenticate_student(conn: sqlite3.Connection, uid: int, password: str):
    """
    Verifies student credentials and returns student details if valid.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT uid, name, dept_code, year FROM students WHERE uid = ? AND password = ?",
        (uid, password)
    )
    row = cursor.fetchone()
    if row:
        return dict(row)
    return None
