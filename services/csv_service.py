import csv
import io
import os
import sqlite3
from typing import Optional, List, Dict, Any, Union
from auth import generate_password, get_next_faculty_id, get_next_student_uid
from config import DATA_DIR, DEPARTMENTS

def _normalize_key(key: str) -> str:
    """Normalizes header column name by stripping whitespace and converting to lowercase."""
    return key.strip().lower().replace(" ", "_").replace("-", "_")

def _get_reader(csv_source: Union[str, io.TextIOBase]) -> csv.DictReader:
    """
    Accepts a filepath, a multi-line CSV string, or a file-like stream,
    and returns a csv.DictReader with normalized fieldnames.
    """
    if isinstance(csv_source, str):
        if "\n" in csv_source or "\r" in csv_source:
            # It's raw CSV content
            stream = io.StringIO(csv_source.strip())
        elif os.path.exists(csv_source):
            # It's a file path
            with open(csv_source, mode="r", encoding="utf-8-sig") as f:
                content = f.read()
            stream = io.StringIO(content.strip())
        else:
            # Might be a single line CSV or empty
            stream = io.StringIO(csv_source.strip())
    else:
        # File-like object (e.g. from Flask request.files['file'].stream or io.StringIO)
        raw = csv_source.read()
        if isinstance(raw, bytes):
            text = raw.decode("utf-8-sig", errors="replace")
        else:
            text = raw
        stream = io.StringIO(text.strip())

    reader = csv.DictReader(stream)
    return reader

def import_students_from_csv(
    conn: sqlite3.Connection,
    csv_source: Union[str, io.TextIOBase],
    dept_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Imports student records from a CSV file or string.
    Supported headers: uid, name, password, dept_code, year
    - If uid is missing/empty, automatically assigns the next branch UID.
    - If password is missing/empty, generates an 8-character password.
    - If dept_code is passed, verifies or defaults to that department.
    """
    cursor = conn.cursor()
    reader = _get_reader(csv_source)
    imported = []
    errors = []

    valid_depts = {d["dept_code"] for d in DEPARTMENTS}

    for idx, raw_row in enumerate(reader, start=1):
        row = {_normalize_key(k): (v.strip() if v else "") for k, v in raw_row.items() if k}
        
        name = row.get("name") or row.get("student_name") or row.get("full_name")
        if not name:
            errors.append(f"Row {idx}: Missing student name.")
            continue

        target_dept = dept_code or row.get("dept_code") or row.get("dept") or "CSE"
        target_dept = target_dept.upper()

        if dept_code and target_dept != dept_code.upper():
            errors.append(f"Row {idx} ({name}): Department '{target_dept}' does not match authorized department '{dept_code}'. Skipped.")
            continue

        if target_dept not in valid_depts:
            errors.append(f"Row {idx} ({name}): Invalid department code '{target_dept}'.")
            continue

        # UID
        raw_uid = row.get("uid") or row.get("student_uid") or row.get("id")
        if raw_uid and raw_uid.isdigit():
            uid = int(raw_uid)
        else:
            uid = get_next_student_uid(conn, target_dept)

        # Password
        password = row.get("password") or row.get("pass")
        if not password:
            password = generate_password(8)

        # Year
        raw_year = row.get("year") or row.get("academic_year") or "1"
        try:
            year = int(raw_year)
            if not (1 <= year <= 4):
                year = 1
        except ValueError:
            year = 1

        try:
            cursor.execute(
                """
                INSERT INTO students (uid, name, password, dept_code, year)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(uid) DO UPDATE SET
                    name = excluded.name,
                    password = excluded.password,
                    dept_code = excluded.dept_code,
                    year = excluded.year
                """,
                (uid, name, password, target_dept, year)
            )
            imported.append({
                "uid": uid,
                "name": name,
                "password": password,
                "dept_code": target_dept,
                "year": year
            })
        except Exception as e:
            errors.append(f"Row {idx} ({name}): Failed to save - {str(e)}")

    conn.commit()
    return {
        "success": len(imported) > 0 or len(errors) == 0,
        "count": len(imported),
        "records": imported,
        "errors": errors
    }

def import_teachers_from_csv(
    conn: sqlite3.Connection,
    csv_source: Union[str, io.TextIOBase],
    dept_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Imports faculty/teachers from a CSV file or string.
    Supported headers: faculty_id, name, password, dept_code, is_head_teacher
    - If faculty_id is missing, auto-assigns next 5-digit Faculty ID.
    - If password is missing, auto-generates 8-character password.
    """
    cursor = conn.cursor()
    reader = _get_reader(csv_source)
    imported = []
    errors = []

    valid_depts = {d["dept_code"] for d in DEPARTMENTS}

    for idx, raw_row in enumerate(reader, start=1):
        row = {_normalize_key(k): (v.strip() if v else "") for k, v in raw_row.items() if k}

        name = row.get("name") or row.get("teacher_name") or row.get("faculty_name")
        if not name:
            errors.append(f"Row {idx}: Missing faculty name.")
            continue

        target_dept = dept_code or row.get("dept_code") or row.get("dept") or "CSE"
        target_dept = target_dept.upper()

        if dept_code and target_dept != dept_code.upper():
            errors.append(f"Row {idx} ({name}): Department '{target_dept}' does not match authorized department '{dept_code}'. Skipped.")
            continue

        if target_dept not in valid_depts:
            errors.append(f"Row {idx} ({name}): Invalid department code '{target_dept}'.")
            continue

        raw_fid = row.get("faculty_id") or row.get("teacher_id") or row.get("id")
        if raw_fid and raw_fid.isdigit():
            faculty_id = int(raw_fid)
        else:
            faculty_id = get_next_faculty_id(conn, target_dept)

        password = row.get("password") or row.get("pass")
        if not password:
            password = generate_password(8)

        raw_head = row.get("is_head_teacher") or row.get("head_teacher") or row.get("role") or "0"
        if raw_head.lower() in ("1", "true", "yes", "head", "head teacher"):
            is_head = 1
        else:
            is_head = 0

        try:
            cursor.execute(
                """
                INSERT INTO faculty (faculty_id, name, password, dept_code, is_head_teacher)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(faculty_id) DO UPDATE SET
                    name = excluded.name,
                    password = excluded.password,
                    dept_code = excluded.dept_code,
                    is_head_teacher = excluded.is_head_teacher
                """,
                (faculty_id, name, password, target_dept, is_head)
            )
            imported.append({
                "faculty_id": faculty_id,
                "name": name,
                "password": password,
                "dept_code": target_dept,
                "is_head_teacher": is_head
            })
        except Exception as e:
            errors.append(f"Row {idx} ({name}): Failed to save - {str(e)}")

    conn.commit()
    return {
        "success": len(imported) > 0 or len(errors) == 0,
        "count": len(imported),
        "records": imported,
        "errors": errors
    }

def import_subjects_from_csv(
    conn: sqlite3.Connection,
    csv_source: Union[str, io.TextIOBase],
    dept_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Imports subjects from a CSV file or string.
    Supported headers: subject_id, subject_name, dept_code, assigned_teacher_id, total_planned_lectures
    """
    cursor = conn.cursor()
    reader = _get_reader(csv_source)
    imported = []
    errors = []

    valid_depts = {d["dept_code"] for d in DEPARTMENTS}

    for idx, raw_row in enumerate(reader, start=1):
        row = {_normalize_key(k): (v.strip() if v else "") for k, v in raw_row.items() if k}

        name = row.get("subject_name") or row.get("name") or row.get("title")
        if not name:
            errors.append(f"Row {idx}: Missing subject name.")
            continue

        target_dept = dept_code or row.get("dept_code") or row.get("dept") or "CSE"
        target_dept = target_dept.upper()

        if dept_code and target_dept != dept_code.upper():
            errors.append(f"Row {idx} ({name}): Department '{target_dept}' does not match authorized department '{dept_code}'. Skipped.")
            continue

        if target_dept not in valid_depts:
            errors.append(f"Row {idx} ({name}): Invalid department code '{target_dept}'.")
            continue

        raw_teacher = row.get("assigned_teacher_id") or row.get("teacher_id") or row.get("faculty_id")
        assigned_id = None
        if raw_teacher and raw_teacher.isdigit() and int(raw_teacher) > 0:
            assigned_id = int(raw_teacher)

        raw_planned = row.get("total_planned_lectures") or row.get("planned_lectures") or row.get("planned") or "40"
        try:
            planned = int(raw_planned)
            if planned <= 0:
                planned = 40
        except ValueError:
            planned = 40

        raw_sub_id = row.get("subject_id") or row.get("id")
        try:
            if raw_sub_id and raw_sub_id.isdigit():
                sub_id = int(raw_sub_id)
                cursor.execute(
                    """
                    INSERT INTO subjects (subject_id, subject_name, dept_code, assigned_teacher_id, total_planned_lectures)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(subject_id) DO UPDATE SET
                        subject_name = excluded.subject_name,
                        dept_code = excluded.dept_code,
                        assigned_teacher_id = excluded.assigned_teacher_id,
                        total_planned_lectures = excluded.total_planned_lectures
                    """,
                    (sub_id, name, target_dept, assigned_id, planned)
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO subjects (subject_name, dept_code, assigned_teacher_id, total_planned_lectures)
                    VALUES (?, ?, ?, ?)
                    """,
                    (name, target_dept, assigned_id, planned)
                )
                sub_id = cursor.lastrowid

            imported.append({
                "subject_id": sub_id,
                "subject_name": name,
                "dept_code": target_dept,
                "assigned_teacher_id": assigned_id,
                "total_planned_lectures": planned
            })
        except Exception as e:
            errors.append(f"Row {idx} ({name}): Failed to save - {str(e)}")

    conn.commit()
    return {
        "success": len(imported) > 0 or len(errors) == 0,
        "count": len(imported),
        "records": imported,
        "errors": errors
    }

def import_attendance_from_csv(
    conn: sqlite3.Connection,
    csv_source: Union[str, io.TextIOBase]
) -> Dict[str, Any]:
    """
    Imports lecture attendance records from a CSV file or string.
    Supported headers: student_uid, subject_id, date, status
    """
    cursor = conn.cursor()
    reader = _get_reader(csv_source)
    imported = []
    errors = []

    for idx, raw_row in enumerate(reader, start=1):
        row = {_normalize_key(k): (v.strip() if v else "") for k, v in raw_row.items() if k}

        raw_uid = row.get("student_uid") or row.get("uid")
        raw_sid = row.get("subject_id")
        date_str = row.get("date")
        status = (row.get("status") or "").upper()

        if not (raw_uid and raw_sid and date_str and status in ("P", "A")):
            errors.append(f"Row {idx}: Invalid fields (expected student_uid, subject_id, date, status='P'/'A').")
            continue

        try:
            cursor.execute(
                """
                INSERT INTO attendance (student_uid, subject_id, date, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(student_uid, subject_id, date) DO UPDATE SET
                    status = excluded.status
                """,
                (int(raw_uid), int(raw_sid), date_str, status)
            )
            imported.append({"student_uid": int(raw_uid), "subject_id": int(raw_sid), "date": date_str, "status": status})
        except Exception as e:
            errors.append(f"Row {idx}: {str(e)}")

    conn.commit()
    return {
        "success": len(imported) > 0 or len(errors) == 0,
        "count": len(imported),
        "records": imported,
        "errors": errors
    }

def load_department_demo_data_from_csv(
    conn: sqlite3.Connection,
    dept_code: str,
    data_dir: str = DATA_DIR
) -> Dict[str, Any]:
    """
    Allows a Head Teacher of a specific department to load/seed demo data
    for their department directly from the standard CSV files in data_dir.
    """
    results = {}
    
    # 1. Teachers
    teachers_path = os.path.join(data_dir, "teachers.csv")
    if os.path.exists(teachers_path):
        results["teachers"] = import_teachers_from_csv(conn, teachers_path, dept_code=dept_code)
    else:
        results["teachers"] = {"success": False, "count": 0, "errors": [f"Missing {teachers_path}"]}

    # 2. Subjects
    subjects_path = os.path.join(data_dir, "subjects.csv")
    if os.path.exists(subjects_path):
        results["subjects"] = import_subjects_from_csv(conn, subjects_path, dept_code=dept_code)
    else:
        results["subjects"] = {"success": False, "count": 0, "errors": [f"Missing {subjects_path}"]}

    # 3. Students
    students_path = os.path.join(data_dir, "students.csv")
    if os.path.exists(students_path):
        results["students"] = import_students_from_csv(conn, students_path, dept_code=dept_code)
    else:
        results["students"] = {"success": False, "count": 0, "errors": [f"Missing {students_path}"]}

    # 4. Attendance
    attendance_path = os.path.join(data_dir, "attendance.csv")
    if os.path.exists(attendance_path):
        results["attendance"] = import_attendance_from_csv(conn, attendance_path)

    return results

def export_to_csv_string(conn: sqlite3.Connection, entity_type: str, dept_code: Optional[str] = None) -> str:
    """Exports students, faculty, or subjects to CSV formatted string."""
    cursor = conn.cursor()
    output = io.StringIO()
    writer = csv.writer(output)

    if entity_type == "students":
        writer.writerow(["uid", "name", "password", "dept_code", "year"])
        if dept_code:
            cursor.execute("SELECT uid, name, password, dept_code, year FROM students WHERE dept_code = ? ORDER BY uid ASC", (dept_code,))
        else:
            cursor.execute("SELECT uid, name, password, dept_code, year FROM students ORDER BY uid ASC")
        for row in cursor.fetchall():
            writer.writerow([row["uid"], row["name"], row["password"], row["dept_code"], row["year"]])

    elif entity_type in ("faculty", "teachers"):
        writer.writerow(["faculty_id", "name", "password", "dept_code", "is_head_teacher"])
        if dept_code:
            cursor.execute("SELECT faculty_id, name, password, dept_code, is_head_teacher FROM faculty WHERE dept_code = ? ORDER BY faculty_id ASC", (dept_code,))
        else:
            cursor.execute("SELECT faculty_id, name, password, dept_code, is_head_teacher FROM faculty ORDER BY faculty_id ASC")
        for row in cursor.fetchall():
            writer.writerow([row["faculty_id"], row["name"], row["password"], row["dept_code"], row["is_head_teacher"]])

    elif entity_type == "subjects":
        writer.writerow(["subject_id", "subject_name", "dept_code", "assigned_teacher_id", "total_planned_lectures"])
        if dept_code:
            cursor.execute("SELECT subject_id, subject_name, dept_code, assigned_teacher_id, total_planned_lectures FROM subjects WHERE dept_code = ? ORDER BY subject_id ASC", (dept_code,))
        else:
            cursor.execute("SELECT subject_id, subject_name, dept_code, assigned_teacher_id, total_planned_lectures FROM subjects ORDER BY subject_id ASC")
        for row in cursor.fetchall():
            writer.writerow([row["subject_id"], row["subject_name"], row["dept_code"], row["assigned_teacher_id"] or "", row["total_planned_lectures"]])

    return output.getvalue()

def get_csv_template(entity_type: str) -> str:
    """Returns downloadable/copyable CSV template with headers and sample rows."""
    if entity_type == "students":
        return "name,year\nAlice Smith,2\nBob Jones,2\nCharlie Brown,2\n"
    elif entity_type in ("faculty", "teachers"):
        return "name,is_head_teacher\nDr. Ada Lovelace,0\nProf. Claude Shannon,0\n"
    elif entity_type == "subjects":
        return "subject_name,assigned_teacher_id,total_planned_lectures\nData Structures & Algorithms,10002,40\nOperating Systems,10003,40\n"
    return ""
