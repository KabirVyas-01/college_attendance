import sqlite3
from typing import List, Dict, Any, Optional
from calculator import calculate_subject_metrics

def get_assigned_subjects(conn: sqlite3.Connection, teacher_id: int) -> List[Dict[str, Any]]:
    """Fetches all subjects assigned to a given subject teacher."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.subject_id, s.subject_name, s.dept_code, s.total_planned_lectures,
               COUNT(DISTINCT a.date) as conducted_count
        FROM subjects s
        LEFT JOIN attendance a ON s.subject_id = a.subject_id
        WHERE s.assigned_teacher_id = ?
        GROUP BY s.subject_id
        ORDER BY s.subject_id ASC
        """,
        (teacher_id,)
    )
    return [dict(row) for row in cursor.fetchall()]

def verify_teacher_assignment(conn: sqlite3.Connection, teacher_id: int, subject_id: int) -> bool:
    """Verifies that the teacher is assigned to teach the specified subject."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT subject_id FROM subjects WHERE subject_id = ? AND assigned_teacher_id = ?",
        (subject_id, teacher_id)
    )
    return cursor.fetchone() is not None

def update_planned_lectures(conn: sqlite3.Connection, teacher_id: int, subject_id: int, total_planned: int) -> bool:
    """Updates the total planned lectures for an assigned subject."""
    if not verify_teacher_assignment(conn, teacher_id, subject_id):
        raise PermissionError("Access Denied: You are not assigned to this subject.")
    if total_planned <= 0:
        raise ValueError("Total planned lectures must be greater than 0.")

    cursor = conn.cursor()
    cursor.execute(
        "UPDATE subjects SET total_planned_lectures = ? WHERE subject_id = ?",
        (total_planned, subject_id)
    )
    conn.commit()
    return cursor.rowcount > 0

def get_department_students_for_subject(conn: sqlite3.Connection, subject_id: int) -> List[Dict[str, Any]]:
    """Fetches all students in the department offering this subject."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT st.uid, st.name, st.dept_code, st.year
        FROM students st
        JOIN subjects sub ON st.dept_code = sub.dept_code
        WHERE sub.subject_id = ?
        ORDER BY st.uid ASC
        """,
        (subject_id,)
    )
    return [dict(row) for row in cursor.fetchall()]

def mark_lecture_attendance(conn: sqlite3.Connection, teacher_id: int, subject_id: int,
                            date_str: str, student_statuses: Dict[int, str]) -> int:
    """
    Records or updates attendance (P or A) for students on a specific lecture date.
    Returns the number of student records updated.
    """
    if not verify_teacher_assignment(conn, teacher_id, subject_id):
        raise PermissionError("Access Denied: You are not assigned to this subject.")

    cursor = conn.cursor()
    records_saved = 0
    for uid, status in student_statuses.items():
        status_clean = status.upper().strip()
        if status_clean not in ('P', 'A'):
            continue
        cursor.execute(
            """
            INSERT INTO attendance (student_uid, subject_id, date, status)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(student_uid, subject_id, date) DO UPDATE SET status = excluded.status
            """,
            (uid, subject_id, date_str, status_clean)
        )
        records_saved += 1

    conn.commit()
    return records_saved

def get_subject_attendance_summary(conn: sqlite3.Connection, teacher_id: int, subject_id: int) -> Dict[str, Any]:
    """
    Generates a full attendance roster summary for a subject:
    Total planned, total conducted, and each student's attendance stats with 75% analysis.
    """
    if not verify_teacher_assignment(conn, teacher_id, subject_id):
        raise PermissionError("Access Denied: You are not assigned to this subject.")

    cursor = conn.cursor()
    cursor.execute(
        "SELECT subject_id, subject_name, dept_code, total_planned_lectures FROM subjects WHERE subject_id = ?",
        (subject_id,)
    )
    subject = dict(cursor.fetchone())

    # Get distinct lecture dates conducted for this subject
    cursor.execute(
        "SELECT DISTINCT date FROM attendance WHERE subject_id = ? ORDER BY date ASC",
        (subject_id,)
    )
    lecture_dates = [row["date"] for row in cursor.fetchall()]
    total_conducted = len(lecture_dates)

    # Get student attendance stats
    students = get_department_students_for_subject(conn, subject_id)
    student_records = []

    for st in students:
        uid = st["uid"]
        cursor.execute(
            "SELECT COUNT(*) as attended FROM attendance WHERE subject_id = ? AND student_uid = ? AND status = 'P'",
            (subject_id, uid)
        )
        attended_count = cursor.fetchone()["attended"]
        metrics = calculate_subject_metrics(attended_count, total_conducted, subject["total_planned_lectures"])

        student_records.append({
            "uid": uid,
            "name": st["name"],
            "year": st["year"],
            "attended": attended_count,
            "conducted": total_conducted,
            "percentage": metrics["current_pct"],
            "is_on_track": metrics["is_on_track"],
            "approx_safe_leaves": metrics["approx_safe_leaves"],
            "approx_needed_consecutive": metrics["approx_needed_consecutive"]
        })

    return {
        "subject": subject,
        "total_conducted": total_conducted,
        "lecture_dates": lecture_dates,
        "students": student_records
    }
