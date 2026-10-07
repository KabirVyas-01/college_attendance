import secrets
import string
import sqlite3

def generate_password(length: int = 8, special_chars: str = "@") -> str:
    """
    Generates a password formatted as 4 letters, 1 special character, and 3 numbers (e.g. 'abcd@123').
    Format: [4 lowercase letters][1 special char][3 digits]
    """
    letters = "".join(secrets.choice(string.ascii_lowercase) for _ in range(4))
    special = secrets.choice(special_chars) if special_chars else "@"
    numbers = "".join(secrets.choice(string.digits) for _ in range(3))
    return f"{letters}{special}{numbers}"

def is_valid_formatted_password(password: str) -> bool:
    """
    Verifies if a password adheres to the format: 4 letters + 1 special character + 3 numbers.
    e.g. 'abcd@123'
    """
    if len(password) != 8:
        return False
    return (
        password[:4].isalpha()
        and not password[4].isalnum()
        and password[5:].isdigit()
    )

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

def change_student_password(conn: sqlite3.Connection, uid: int, new_password: str, old_password: str = None) -> bool:
    """
    Updates the password for an existing student in the database.
    Requires new password to match format: 4 letters, 1 special char, 3 numbers (e.g. 'abcd@123').
    """
    if not is_valid_formatted_password(new_password):
        raise ValueError("Password must follow the format of 4 letters, 1 special character, and 3 numbers (e.g. 'abcd@123').")

    cursor = conn.cursor()
    if old_password is not None:
        cursor.execute("SELECT password FROM students WHERE uid = ?", (uid,))
        row = cursor.fetchone()
        if not row or row["password"] != old_password:
            raise ValueError("Current password does not match.")

    cursor.execute("UPDATE students SET password = ? WHERE uid = ?", (new_password, uid))
    conn.commit()
    return cursor.rowcount > 0

def change_faculty_password(conn: sqlite3.Connection, faculty_id: int, new_password: str, old_password: str = None) -> bool:
    """
    Updates the password for an existing faculty member in the database.
    Subject teachers must use format: 4 letters, 1 special char, 3 numbers.
    Head teachers may use any non-empty password or the formatted password.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT is_head_teacher, password FROM faculty WHERE faculty_id = ?", (faculty_id,))
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Faculty ID {faculty_id} not found.")

    is_head = row["is_head_teacher"] == 1
    if not is_head and not is_valid_formatted_password(new_password):
        raise ValueError("Password must follow the format of 4 letters, 1 special character, and 3 numbers (e.g. 'abcd@123').")

    if old_password is not None and row["password"] != old_password:
        raise ValueError("Current password does not match.")

    cursor.execute("UPDATE faculty SET password = ? WHERE faculty_id = ?", (new_password, faculty_id))
    conn.commit()
    return cursor.rowcount > 0

def reset_student_password(conn: sqlite3.Connection, uid: int) -> str:
    """
    Generates a new password formatted as 'abcd@123' and updates the student in the database.
    """
    new_pwd = generate_password()
    cursor = conn.cursor()
    cursor.execute("UPDATE students SET password = ? WHERE uid = ?", (new_pwd, uid))
    conn.commit()
    return new_pwd

def reset_faculty_password(conn: sqlite3.Connection, faculty_id: int) -> str:
    """
    Generates a new password formatted as 'abcd@123' and updates the teacher in the database.
    """
    new_pwd = generate_password()
    cursor = conn.cursor()
    cursor.execute("UPDATE faculty SET password = ? WHERE faculty_id = ?", (new_pwd, faculty_id))
    conn.commit()
    return new_pwd

def update_all_existing_passwords_to_format(conn: sqlite3.Connection) -> dict:
    """
    Directly updates all existing students and subject teachers in the database whose
    passwords do not match the 'abcd@123' format (4 letters, 1 special char, 3 numbers).
    Leaves Head Teachers untouched.
    """
    cursor = conn.cursor()
    updated_students = 0
    updated_teachers = 0

    # 1. Update students
    cursor.execute("SELECT uid, password FROM students")
    for row in cursor.fetchall():
        if not is_valid_formatted_password(row["password"]):
            new_pwd = generate_password()
            cursor.execute("UPDATE students SET password = ? WHERE uid = ?", (new_pwd, row["uid"]))
            updated_students += 1

    # 2. Update subject teachers (except head teachers)
    cursor.execute("SELECT faculty_id, password FROM faculty WHERE is_head_teacher = 0")
    for row in cursor.fetchall():
        if not is_valid_formatted_password(row["password"]):
            new_pwd = generate_password()
            cursor.execute("UPDATE faculty SET password = ? WHERE faculty_id = ?", (new_pwd, row["faculty_id"]))
            updated_teachers += 1

    conn.commit()
    return {
        "updated_students": updated_students,
        "updated_teachers": updated_teachers
    }

