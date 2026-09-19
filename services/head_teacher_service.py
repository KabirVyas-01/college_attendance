import sqlite3
from typing import Optional, List, Dict, Any
from auth import generate_password, get_next_faculty_id, get_next_student_uid

def is_head_teacher_configured(conn: sqlite3.Connection, dept_code: str) -> bool:
    """Checks if a Head Teacher is already registered for the specified department."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT faculty_id FROM faculty WHERE dept_code = ? AND is_head_teacher = 1",
        (dept_code,)
    )
    return cursor.fetchone() is not None

def get_head_teacher(conn: sqlite3.Connection, dept_code: str) -> Optional[Dict[str, Any]]:
    """Fetches the Head Teacher details for a department."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT faculty_id, name, dept_code, password FROM faculty WHERE dept_code = ? AND is_head_teacher = 1",
        (dept_code,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None

def create_head_teacher(conn: sqlite3.Connection, name: str, password: str, dept_code: str) -> int:
    """
    Creates the Head Teacher for a department with the department's starting 5-digit Faculty ID.
    """
    faculty_id = get_next_faculty_id(conn, dept_code)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO faculty (faculty_id, name, password, dept_code, is_head_teacher)
        VALUES (?, ?, ?, ?, 1)
        """,
        (faculty_id, name.strip(), password.strip(), dept_code)
    )
    conn.commit()
    return faculty_id

def add_subject_teacher(conn: sqlite3.Connection, name: str, dept_code: str) -> Dict[str, Any]:
    """
    Head Teacher creates a Subject Teacher.
    Auto-assigns the next 5-digit Faculty ID and generates an 8-character password.
    """
    faculty_id = get_next_faculty_id(conn, dept_code)
    auto_password = generate_password(8)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO faculty (faculty_id, name, password, dept_code, is_head_teacher)
        VALUES (?, ?, ?, ?, 0)
        """,
        (faculty_id, name.strip(), auto_password, dept_code)
    )
    conn.commit()
    return {
        "faculty_id": faculty_id,
        "name": name.strip(),
        "password": auto_password,
        "dept_code": dept_code
    }

def remove_subject_teacher(conn: sqlite3.Connection, faculty_id: int, dept_code: str) -> bool:
    """
    Removes a subject teacher from the department. Cannot remove the Head Teacher through this method.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT faculty_id, is_head_teacher FROM faculty WHERE faculty_id = ? AND dept_code = ?",
        (faculty_id, dept_code)
    )
    row = cursor.fetchone()
    if not row:
        return False
    if row["is_head_teacher"] == 1:
        raise ValueError("Cannot remove the Head Teacher. Reassignment or department reset required.")

    # Unassign subjects first (or rely on ON DELETE SET NULL)
    cursor.execute("UPDATE subjects SET assigned_teacher_id = NULL WHERE assigned_teacher_id = ?", (faculty_id,))
    cursor.execute("DELETE FROM faculty WHERE faculty_id = ?", (faculty_id,))
    conn.commit()
    return True

def list_faculty(conn: sqlite3.Connection, dept_code: str) -> List[Dict[str, Any]]:
    """Returns list of all faculty members in the department."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT f.faculty_id, f.name, f.dept_code, f.is_head_teacher, f.password,
               COUNT(s.subject_id) as subjects_count
        FROM faculty f
        LEFT JOIN subjects s ON f.faculty_id = s.assigned_teacher_id
        WHERE f.dept_code = ?
        GROUP BY f.faculty_id
        ORDER BY f.faculty_id ASC
        """,
        (dept_code,)
    )
    return [dict(row) for row in cursor.fetchall()]

def add_subject(conn: sqlite3.Connection, subject_name: str, dept_code: str,
                assigned_teacher_id: Optional[int] = None, total_planned_lectures: int = 40) -> int:
    """Adds a new subject to the department and optionally assigns a teacher."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO subjects (subject_name, dept_code, assigned_teacher_id, total_planned_lectures)
        VALUES (?, ?, ?, ?)
        """,
        (subject_name.strip(), dept_code, assigned_teacher_id, total_planned_lectures)
    )
    conn.commit()
    return cursor.lastrowid

def remove_subject(conn: sqlite3.Connection, subject_id: int, dept_code: str) -> bool:
    """Removes a subject from the department (cascades attendance records)."""
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM subjects WHERE subject_id = ? AND dept_code = ?",
        (subject_id, dept_code)
    )
    conn.commit()
    return cursor.rowcount > 0

def assign_subject_teacher(conn: sqlite3.Connection, subject_id: int, teacher_id: Optional[int], dept_code: str) -> bool:
    """Maps or re-assigns a subject to a faculty teacher."""
    cursor = conn.cursor()
    if teacher_id is not None:
        # Validate teacher belongs to this department
        cursor.execute("SELECT faculty_id FROM faculty WHERE faculty_id = ? AND dept_code = ?", (teacher_id, dept_code))
        if not cursor.fetchone():
            raise ValueError(f"Teacher ID {teacher_id} does not exist in department {dept_code}.")

    cursor.execute(
        "UPDATE subjects SET assigned_teacher_id = ? WHERE subject_id = ? AND dept_code = ?",
        (teacher_id, subject_id, dept_code)
    )
    conn.commit()
    return cursor.rowcount > 0

def list_subjects(conn: sqlite3.Connection, dept_code: str) -> List[Dict[str, Any]]:
    """Lists all subjects in a department with assigned teacher name."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.subject_id, s.subject_name, s.dept_code, s.total_planned_lectures,
               s.assigned_teacher_id, f.name as teacher_name
        FROM subjects s
        LEFT JOIN faculty f ON s.assigned_teacher_id = f.faculty_id
        WHERE s.dept_code = ?
        ORDER BY s.subject_id ASC
        """,
        (dept_code,)
    )
    return [dict(row) for row in cursor.fetchall()]

def add_student(conn: sqlite3.Connection, name: str, dept_code: str, year: int) -> Dict[str, Any]:
    """
    Head Teacher adds a new student.
    Auto-assigns next 6-digit branch UID and generates an 8-character password.
    """
    uid = get_next_student_uid(conn, dept_code)
    auto_password = generate_password(8)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO students (uid, name, password, dept_code, year)
        VALUES (?, ?, ?, ?, ?)
        """,
        (uid, name.strip(), auto_password, dept_code, int(year))
    )
    conn.commit()
    return {
        "uid": uid,
        "name": name.strip(),
        "password": auto_password,
        "dept_code": dept_code,
        "year": int(year)
    }

def remove_student(conn: sqlite3.Connection, uid: int, dept_code: str) -> bool:
    """Removes a student from the department (cascades attendance records)."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE uid = ? AND dept_code = ?", (uid, dept_code))
    conn.commit()
    return cursor.rowcount > 0

def list_students(conn: sqlite3.Connection, dept_code: str) -> List[Dict[str, Any]]:
    """Lists all students enrolled in the department."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT uid, name, password, dept_code, year
        FROM students
        WHERE dept_code = ?
        ORDER BY uid ASC
        """,
        (dept_code,)
    )
    return [dict(row) for row in cursor.fetchall()]
