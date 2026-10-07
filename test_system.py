import os
import unittest
import sqlite3
import tempfile
import math

from config import DEPARTMENTS
from database import init_db, get_connection
from auth import generate_password, get_next_faculty_id, get_next_student_uid, authenticate_faculty, authenticate_student
from calculator import calculate_subject_metrics, calculate_overall_metrics
from services import head_teacher_service, subject_teacher_service, student_service

class TestCollegeAttendanceSystem(unittest.TestCase):
    def setUp(self):
        # Create a temporary database for testing
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.temp_db_path)
        self.conn = get_connection(self.temp_db_path)

    def tearDown(self):
        self.conn.close()
        os.close(self.temp_db_fd)
        os.remove(self.temp_db_path)

    def test_database_initialization(self):
        """Test tables are created and default departments are seeded."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT dept_code FROM departments ORDER BY dept_code")
        depts = [r["dept_code"] for r in cursor.fetchall()]
        self.assertEqual(sorted(depts), ["CE", "CSE", "EE", "ME"])

    def test_password_generation(self):
        """Test password generator produces format: 4 letters + 1 special character + 3 numbers (e.g. 'abcd@123')."""
        from auth import is_valid_formatted_password
        for _ in range(50):
            pwd = generate_password()
            self.assertEqual(len(pwd), 8)
            self.assertTrue(is_valid_formatted_password(pwd), f"Password {pwd} does not match 4 letters, 1 special char, 3 digits format.")
            self.assertTrue(pwd[:4].isalpha() and pwd[:4].islower())
            self.assertFalse(pwd[4].isalnum())
            self.assertTrue(pwd[5:].isdigit())

    def test_faculty_and_student_id_series(self):
        """Test auto-increment ranges for faculty (5-digit) and students (6-digit)."""
        # CSE: Faculty starts at 10001, Student starts at 100000
        f_id1 = get_next_faculty_id(self.conn, "CSE")
        self.assertEqual(f_id1, 10001)

        head_teacher_service.create_head_teacher(self.conn, "Prof. Turing", "admin123", "CSE")
        f_id2 = get_next_faculty_id(self.conn, "CSE")
        self.assertEqual(f_id2, 10002)

        # Civil Faculty starts at 20001
        ce_f_id = get_next_faculty_id(self.conn, "CE")
        self.assertEqual(ce_f_id, 20001)

        # Student UID generation
        st_uid1 = get_next_student_uid(self.conn, "CSE")
        self.assertEqual(st_uid1, 100000)

        st_res = head_teacher_service.add_student(self.conn, "Alice", "CSE", 2)
        self.assertEqual(st_res["uid"], 100000)

        st_uid2 = get_next_student_uid(self.conn, "CSE")
        self.assertEqual(st_uid2, 100001)

        # Civil student starts at 200000
        ce_st_uid = get_next_student_uid(self.conn, "CE")
        self.assertEqual(ce_st_uid, 200000)

    def test_mathematical_formulas_on_track(self):
        """
        Verify exact math for >= 75%:
        Case: Conducted 20, Attended 15 (75.0%), Total Planned 40
        Expected: Safe leaves = floor(15 - 0.75*40) + (40 - 20) = -15 + 20 = 5
        """
        metrics = calculate_subject_metrics(attended=15, conducted=20, total_planned=40)
        self.assertEqual(metrics["current_pct"], 75.0)
        self.assertTrue(metrics["is_on_track"])
        self.assertEqual(metrics["approx_safe_leaves"], 5)
        self.assertEqual(metrics["approx_needed_consecutive"], 0)

    def test_mathematical_formulas_deficient(self):
        """
        Verify exact math for < 75%:
        Case: Conducted 20, Attended 10 (50.0%), Total Planned 40
        Expected: Consecutive needed = ceil(3*20 - 4*10) = 60 - 40 = 20
        """
        metrics = calculate_subject_metrics(attended=10, conducted=20, total_planned=40)
        self.assertEqual(metrics["current_pct"], 50.0)
        self.assertFalse(metrics["is_on_track"])
        self.assertEqual(metrics["approx_safe_leaves"], 0)
        self.assertEqual(metrics["approx_needed_consecutive"], 20)

    def test_mathematical_formulas_edge_cases(self):
        """Edge cases: Conducted 0, 100% attendance."""
        # 0 conducted
        m0 = calculate_subject_metrics(attended=0, conducted=0, total_planned=40)
        self.assertEqual(m0["current_pct"], 100.0)
        self.assertEqual(m0["approx_safe_leaves"], 10)  # floor(0.25 * 40)

        # 20/20 attended
        m1 = calculate_subject_metrics(attended=20, conducted=20, total_planned=40)
        self.assertEqual(m1["current_pct"], 100.0)
        self.assertEqual(m1["approx_safe_leaves"], 10)

    def test_head_and_subject_teacher_permissions(self):
        """Verify role-based workflows and permission restrictions."""
        # 1. Create Head Teacher
        ht_id = head_teacher_service.create_head_teacher(self.conn, "Prof. Head", "pass123", "CSE")
        self.assertEqual(ht_id, 10001)

        # 2. Add Subject Teacher
        st_info = head_teacher_service.add_subject_teacher(self.conn, "Dr. Subject", "CSE")
        st_id = st_info["faculty_id"]
        self.assertEqual(st_id, 10002)

        # 3. Add Subject & Assign
        sub_id = head_teacher_service.add_subject(self.conn, "Algorithms", "CSE", st_id, 40)

        # 4. Add Student
        st_record = head_teacher_service.add_student(self.conn, "Alice", "CSE", 2)
        student_uid = st_record["uid"]

        # 5. Mark Attendance by Assigned Subject Teacher
        updated = subject_teacher_service.mark_lecture_attendance(
            self.conn, st_id, sub_id, "2026-09-01", {student_uid: 'P'}
        )
        self.assertEqual(updated, 1)

        # 6. Verify unassigned teacher cannot mark attendance
        with self.assertRaises(PermissionError):
            subject_teacher_service.mark_lecture_attendance(
                self.conn, 99999, sub_id, "2026-09-02", {student_uid: 'P'}
            )

        # 7. Student Dashboard query
        dash = student_service.get_student_dashboard_data(self.conn, student_uid)
        self.assertEqual(len(dash["subjects"]), 1)
        sub_stat = dash["subjects"][0]
        self.assertEqual(sub_stat["conducted"], 1)
        self.assertEqual(sub_stat["attended"], 1)
        self.assertEqual(sub_stat["current_pct"], 100.0)

    def test_csv_import_by_head_teacher(self):
        """Test Head Teacher importing students, teachers, and subjects from CSV."""
        from services import csv_service

        # 1. Import Students from CSV string
        csv_students = """name,year
Student Alpha,1
Student Beta,2
"""
        res_st = head_teacher_service.import_students_csv(self.conn, csv_students, dept_code="CSE")
        self.assertEqual(res_st["count"], 2)
        self.assertEqual(res_st["records"][0]["uid"], 100000)
        self.assertEqual(res_st["records"][0]["name"], "Student Alpha")
        self.assertEqual(res_st["records"][1]["uid"], 100001)

        # 2. Import Faculty from CSV string
        csv_faculty = """name,is_head_teacher
Prof. John Doe,1
Dr. Jane Smith,0
"""
        res_fac = head_teacher_service.import_teachers_csv(self.conn, csv_faculty, dept_code="CSE")
        self.assertEqual(res_fac["count"], 2)
        self.assertEqual(res_fac["records"][0]["faculty_id"], 10001)
        self.assertEqual(res_fac["records"][0]["is_head_teacher"], 1)
        self.assertEqual(res_fac["records"][1]["faculty_id"], 10002)

        # 3. Import Subjects from CSV string
        csv_subjects = """subject_name,assigned_teacher_id,total_planned_lectures
Algorithms,10002,42
Database Systems,10001,36
"""
        res_sub = head_teacher_service.import_subjects_csv(self.conn, csv_subjects, dept_code="CSE")
        self.assertEqual(res_sub["count"], 2)
        self.assertEqual(res_sub["records"][0]["subject_name"], "Algorithms")
        self.assertEqual(res_sub["records"][0]["total_planned_lectures"], 42)

        # 4. Test Export
        exported_st = head_teacher_service.export_department_csv(self.conn, "students", "CSE")
        self.assertIn("Student Alpha", exported_st)
        self.assertIn("Student Beta", exported_st)

    def test_seed_demo_data_from_csv(self):
        """Test seeding department data from actual data/ CSV files into database."""
        from services import head_teacher_service
        from config import DATA_DIR

        # Run seed_department_from_csv using Head Teacher service
        res = head_teacher_service.seed_department_from_csv(self.conn, "CSE")
        self.assertGreaterEqual(res["teachers"]["count"], 1)
        self.assertGreaterEqual(res["subjects"]["count"], 1)
        self.assertGreaterEqual(res["students"]["count"], 1)

        # Query and assert records in test DB
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM faculty WHERE dept_code = 'CSE'")
        self.assertGreaterEqual(cursor.fetchone()["cnt"], 4)

        cursor.execute("SELECT COUNT(*) as cnt FROM subjects WHERE dept_code = 'CSE'")
        self.assertGreaterEqual(cursor.fetchone()["cnt"], 4)

        cursor.execute("SELECT COUNT(*) as cnt FROM students WHERE dept_code = 'CSE'")
        self.assertGreaterEqual(cursor.fetchone()["cnt"], 3)

        cursor.execute("SELECT COUNT(*) as cnt FROM attendance")
        self.assertGreaterEqual(cursor.fetchone()["cnt"], 180)

    def test_password_change_and_reset_in_database(self):
        """Test changing, resetting, and migrating existing passwords in the database."""
        from auth import (
            change_student_password,
            change_faculty_password,
            reset_student_password,
            reset_faculty_password,
            update_all_existing_passwords_to_format,
            is_valid_formatted_password
        )

        # Create teacher and student
        ht_id = head_teacher_service.create_head_teacher(self.conn, "Prof. Turing", "admin123", "CSE")
        teach = head_teacher_service.add_subject_teacher(self.conn, "Dr. Lovelace", "CSE")
        stud = head_teacher_service.add_student(self.conn, "Alice", "CSE", 2)

        # 1. Change password with valid format
        self.assertTrue(change_student_password(self.conn, stud["uid"], "pass@789"))
        self.assertTrue(change_faculty_password(self.conn, teach["faculty_id"], "work#456"))

        # 2. Reject invalid format
        with self.assertRaises(ValueError):
            change_student_password(self.conn, stud["uid"], "invalidpass")
        with self.assertRaises(ValueError):
            change_faculty_password(self.conn, teach["faculty_id"], "short1")

        # 3. Head Teacher reset methods
        new_stud_pwd = head_teacher_service.reset_student_password_in_dept(self.conn, stud["uid"], "CSE")
        self.assertTrue(is_valid_formatted_password(new_stud_pwd))

        new_teach_pwd = head_teacher_service.reset_faculty_password_in_dept(self.conn, teach["faculty_id"], "CSE")
        self.assertTrue(is_valid_formatted_password(new_teach_pwd))

        # 4. Migrate old passwords in database
        cursor = self.conn.cursor()
        cursor.execute("UPDATE students SET password = 'oldpassword' WHERE uid = ?", (stud["uid"],))
        cursor.execute("UPDATE faculty SET password = 'oldteach' WHERE faculty_id = ?", (teach["faculty_id"],))
        self.conn.commit()

        stats = update_all_existing_passwords_to_format(self.conn)
        self.assertEqual(stats["updated_students"], 1)
        self.assertEqual(stats["updated_teachers"], 1)

        # Verify head teacher password was untouched
        cursor.execute("SELECT password FROM faculty WHERE faculty_id = ?", (ht_id,))
        self.assertEqual(cursor.fetchone()["password"], "admin123")

if __name__ == "__main__":
    unittest.main()
