import sys
import os
import sqlite3

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, get_connection
from auth import authenticate_faculty, authenticate_student
from cli.ui_helpers import (
    print_header, print_section, print_success, print_error, print_warning, print_info,
    prompt_str, prompt_int, pause, BOLD, RESET, CYAN, GREEN, YELLOW
)
from cli.menus import (
    check_first_time_setup,
    setup_head_teacher_wizard,
    head_teacher_menu,
    subject_teacher_menu,
    student_menu
)
from seed_demo_data import seed_demo_data

def faculty_login_flow(conn: sqlite3.Connection, required_role: str):
    """Handles login for Head Teacher or Subject Teacher."""
    role_name = "Head Teacher" if required_role == "HEAD" else "Subject Teacher"
    print_section(f"{role_name} Login")
    
    faculty_id = prompt_int(f"Enter 5-digit Faculty ID (e.g. 10001)", min_val=10000, max_val=99999)
    if not faculty_id:
        return

    password = prompt_str("Enter Password")
    if not password:
        return

    faculty = authenticate_faculty(conn, faculty_id, password)
    if not faculty:
        print_error("Invalid Faculty ID or Password. Please check your credentials.")
        pause()
        return

    is_head = faculty["is_head_teacher"] == 1
    if required_role == "HEAD" and not is_head:
        print_error(f"Access Denied: Faculty ID {faculty_id} is a Subject Teacher, not a Head Teacher.")
        print_info("Please use the Subject Teacher Login option from the main menu.")
        pause()
        return

    if required_role == "SUBJECT" and is_head:
        # Head teacher can also access subject teacher portal if they teach subjects
        pass

    print_success(f"Welcome back, {faculty['name']} ({faculty['dept_code']})!")
    
    if required_role == "HEAD":
        head_teacher_menu(conn, faculty)
    else:
        subject_teacher_menu(conn, faculty)

def student_login_flow(conn: sqlite3.Connection):
    """Handles login for Students using their 6-digit branch UID."""
    print_section("Student Login")
    
    uid = prompt_int("Enter 6-digit Student UID (e.g. 100000 for CSE, 200000 for CE)", min_val=100000, max_val=999999)
    if not uid:
        return

    password = prompt_str("Enter Password")
    if not password:
        return

    student = authenticate_student(conn, uid, password)
    if not student:
        print_error("Invalid Student UID or Password. Please check your credentials.")
        pause()
        return

    print_success(f"Welcome, {student['name']} ({student['dept_code']}, Year {student['year']})!")
    student_menu(conn, student)

def main():
    """Main application loop."""
    # 1. Initialize DB
    init_db()
    conn = get_connection()

    # 2. Check First-Time Setup
    check_first_time_setup(conn)

    while True:
        print_header(
            "COLLEGE ATTENDANCE MANAGEMENT SYSTEM",
            "Role-Based Access Control | SQLite Persistence | 75% Attendance Advisor"
        )
        print(f"  {BOLD}1.{RESET} Head Teacher Portal (Dept Admin, Faculty & Student Management)")
        print(f"  {BOLD}2.{RESET} Subject Teacher Portal (Planned Lectures & Attendance Marking)")
        print(f"  {BOLD}3.{RESET} Student Portal (Lecture-wise Dashboard & 75% Advisor)")
        print(f"  {BOLD}4.{RESET} Setup Head Teacher for a Department")
        print(f"  {BOLD}5.{RESET} Seed / Reset Demo Sample Data (Quick Test Mode)")
        print(f"  {BOLD}0.{RESET} Exit Application\n")

        choice = prompt_int("Select an option", 0, 5)

        if choice == 0 or choice is None:
            print_info("Thank you for using the College Attendance Management System. Goodbye!")
            break
        elif choice == 1:
            faculty_login_flow(conn, "HEAD")
        elif choice == 2:
            faculty_login_flow(conn, "SUBJECT")
        elif choice == 3:
            student_login_flow(conn)
        elif choice == 4:
            setup_head_teacher_wizard(conn)
        elif choice == 5:
            confirm = prompt_str("Reset and populate demo data? (y/n)", default="y").lower()
            if confirm == 'y':
                seed_demo_data()
                pause()

    conn.close()

if __name__ == "__main__":
    main()
