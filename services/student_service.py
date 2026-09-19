import sqlite3
from typing import Dict, Any, List
from calculator import calculate_subject_metrics, calculate_overall_metrics

def get_student_dashboard_data(conn: sqlite3.Connection, student_uid: int) -> Dict[str, Any]:
    """
    Builds the complete student dashboard, including:
    - Student info
    - Subject-wise attendance stats (conducted, attended, %, approx. planned, 75% advisor)
    - Overall semester attendance percentage
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.uid, s.name, s.dept_code, s.year, d.dept_name
        FROM students s
        JOIN departments d ON s.dept_code = d.dept_code
        WHERE s.uid = ?
        """,
        (student_uid,)
    )
    student_row = cursor.fetchone()
    if not student_row:
        raise ValueError(f"Student with UID {student_uid} not found.")

    student_info = dict(student_row)
    dept_code = student_info["dept_code"]

    # Get all subjects offered in this department
    cursor.execute(
        """
        SELECT sub.subject_id, sub.subject_name, sub.total_planned_lectures,
               f.name as teacher_name
        FROM subjects sub
        LEFT JOIN faculty f ON sub.assigned_teacher_id = f.faculty_id
        WHERE sub.dept_code = ?
        ORDER BY sub.subject_name ASC
        """,
        (dept_code,)
    )
    subjects = [dict(r) for r in cursor.fetchall()]

    subjects_data = []
    for sub in subjects:
        sub_id = sub["subject_id"]
        
        # Count total lectures conducted for this subject
        cursor.execute(
            "SELECT COUNT(DISTINCT date) as total_conducted FROM attendance WHERE subject_id = ?",
            (sub_id,)
        )
        conducted = cursor.fetchone()["total_conducted"]

        # Count attended by this student
        cursor.execute(
            "SELECT COUNT(*) as attended FROM attendance WHERE subject_id = ? AND student_uid = ? AND status = 'P'",
            (sub_id, student_uid)
        )
        attended = cursor.fetchone()["attended"]

        # Compute 75% analytics
        planned = sub["total_planned_lectures"] or 0
        metrics = calculate_subject_metrics(attended, conducted, planned)

        subjects_data.append({
            "subject_id": sub_id,
            "subject_name": sub["subject_name"],
            "teacher_name": sub["teacher_name"] or "Not Assigned",
            "conducted": metrics["conducted"],
            "attended": metrics["attended"],
            "absent": metrics["absent"],
            "current_pct": metrics["current_pct"],
            "total_planned": metrics["total_planned"],
            "approx_total_planned": metrics["total_planned"],
            "remaining_planned": metrics["remaining_planned"],
            "is_on_track": metrics["is_on_track"],
            "approx_safe_leaves": metrics["approx_safe_leaves"],
            "approx_needed_consecutive": metrics["approx_needed_consecutive"],
            "advice_message": metrics["advice_message"]
        })

    overall_metrics = calculate_overall_metrics(subjects_data)

    return {
        "student": student_info,
        "subjects": subjects_data,
        "overall": overall_metrics
    }

def get_student_subject_history(conn: sqlite3.Connection, student_uid: int, subject_id: int) -> List[Dict[str, Any]]:
    """
    Fetches the lecture-by-lecture attendance log for a student in a specific subject.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT a.date, a.status, s.subject_name
        FROM attendance a
        JOIN subjects s ON a.subject_id = s.subject_id
        WHERE a.student_uid = ? AND a.subject_id = ?
        ORDER BY a.date ASC
        """,
        (student_uid, subject_id)
    )
    return [dict(row) for row in cursor.fetchall()]
