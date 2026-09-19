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
        """Test password generator produces 8-char lowercase alphanumeric string."""
        for _ in range(50):
            pwd = generate_password(8)
            self.assertEqual(len(pwd), 8)
            self.assertTrue(all(c.isalnum() and (c.islower() or c.isdigit()) for c in pwd))

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

if __name__ == "__main__":
    unittest.main()
