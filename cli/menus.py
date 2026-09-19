import sqlite3
import datetime
from typing import Dict, Any
from config import DEPARTMENTS, MIN_ATTENDANCE_PCT
from auth import authenticate_faculty, authenticate_student
from cli.ui_helpers import (
    print_header, print_section, print_success, print_error, print_warning, print_info,
    render_table, prompt_str, prompt_int, pause, BOLD, RESET, GREEN, RED, YELLOW, CYAN
)
from services import (
    head_teacher_service,
    subject_teacher_service,
    student_service
)

def check_first_time_setup(conn: sqlite3.Connection):
    """
    Checks if at least one department has a Head Teacher configured.
    If none are found, guides the user through initial Head Teacher setup.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM faculty WHERE is_head_teacher = 1")
    count = cursor.fetchone()["count"]
    if count == 0:
        print_header("FIRST-TIME SYSTEM INITIALIZATION", "No Head Teacher found. Please configure the initial Head Teacher.")
        setup_head_teacher_wizard(conn)

def setup_head_teacher_wizard(conn: sqlite3.Connection):
    """Wizard to setup a Head Teacher for a department."""
    print_section("Select Department to Setup Head Teacher")
    for idx, dept in enumerate(DEPARTMENTS, 1):
        is_configured = head_teacher_service.is_head_teacher_configured(conn, dept["dept_code"])
        status = f"{GREEN}(Configured){RESET}" if is_configured else f"{YELLOW}(Not Configured){RESET}"
        print(f"  {idx}. {dept['dept_code']} - {dept['dept_name']} {status}")

    choice = prompt_int("Select Department number", 1, len(DEPARTMENTS))
    if not choice:
        return

    dept = DEPARTMENTS[choice - 1]
    dept_code = dept["dept_code"]

    if head_teacher_service.is_head_teacher_configured(conn, dept_code):
        ht = head_teacher_service.get_head_teacher(conn, dept_code)
        print_warning(f"Head Teacher for {dept_code} already exists: {ht['name']} (Faculty ID: {ht['faculty_id']})")
        pause()
        return

    print_section(f"Configure Head Teacher for {dept['dept_name']} ({dept_code})")
    name = prompt_str("Enter Head Teacher's Full Name")
    if not name:
        return
    password = prompt_str("Enter Head Teacher's Password (or leave blank to auto-generate)", allow_empty=True)
    if not password:
        from auth import generate_password
        password = generate_password(8)

    faculty_id = head_teacher_service.create_head_teacher(conn, name, password, dept_code)
    
    print_success(f"Head Teacher created successfully!")
    print(f"\n{BOLD}================ LOGIN CREDENTIALS ================{RESET}")
    print(f"  Role:        Head Teacher ({dept_code})")
    print(f"  Faculty ID:  {BOLD}{faculty_id}{RESET} (Use this to login)")
    print(f"  Name:        {name}")
    print(f"  Password:    {BOLD}{password}{RESET}")
    print(f"{BOLD}===================================================={RESET}\n")
    pause()

# =====================================================================
# Head Teacher Workflows
# =====================================================================

def head_teacher_menu(conn: sqlite3.Connection, faculty: Dict[str, Any]):
    dept_code = faculty["dept_code"]
    while True:
        print_header(
            f"HEAD TEACHER DASHBOARD - {dept_code}",
            f"Logged in as: {faculty['name']} (Faculty ID: {faculty['faculty_id']})"
        )
        print("  1. Department Overview & Statistics")
        print("  2. Add Subject Teacher (Auto-assign 5-digit ID & Password)")
        print("  3. Remove Subject Teacher")
        print("  4. List All Faculty in Department")
        print("  5. Add New Subject")
        print("  6. Assign / Reassign Subject Teacher")
        print("  7. Remove Subject")
        print("  8. List All Subjects")
        print("  9. Add Student (Auto-assign 6-digit Branch UID & Password)")
        print("  10. Remove Student")
        print("  11. List All Students")
        print("  0. Logout")

        choice = prompt_int("Enter option", 0, 11)
        if choice == 0 or choice is None:
            print_info("Logged out from Head Teacher account.")
            break
        elif choice == 1:
            view_department_overview(conn, dept_code)
        elif choice == 2:
            add_teacher_flow(conn, dept_code)
        elif choice == 3:
            remove_teacher_flow(conn, dept_code)
        elif choice == 4:
            list_faculty_flow(conn, dept_code)
        elif choice == 5:
            add_subject_flow(conn, dept_code)
        elif choice == 6:
            assign_subject_flow(conn, dept_code)
        elif choice == 7:
            remove_subject_flow(conn, dept_code)
        elif choice == 8:
            list_subjects_flow(conn, dept_code)
        elif choice == 9:
            add_student_flow(conn, dept_code)
        elif choice == 10:
            remove_student_flow(conn, dept_code)
        elif choice == 11:
            list_students_flow(conn, dept_code)

def view_department_overview(conn: sqlite3.Connection, dept_code: str):
    print_section(f"Department Overview: {dept_code}")
    faculty_list = head_teacher_service.list_faculty(conn, dept_code)
    students_list = head_teacher_service.list_students(conn, dept_code)
    subjects_list = head_teacher_service.list_subjects(conn, dept_code)

    print(f"Total Faculty:  {len(faculty_list)}")
    print(f"Total Students: {len(students_list)}")
    print(f"Total Subjects: {len(subjects_list)}")
    pause()

def add_teacher_flow(conn: sqlite3.Connection, dept_code: str):
    print_section("Add Subject Teacher")
    name = prompt_str("Enter Subject Teacher's Full Name")
    if not name:
        return
    res = head_teacher_service.add_subject_teacher(conn, name, dept_code)
    print_success("Subject Teacher added successfully!")
    print(f"\n{BOLD}================ TEACHER CREDENTIALS ================{RESET}")
    print(f"  Faculty ID: {BOLD}{res['faculty_id']}{RESET}")
    print(f"  Name:       {res['name']}")
    print(f"  Department: {res['dept_code']}")
    print(f"  Password:   {BOLD}{res['password']}{RESET}")
    print(f"{BOLD}===================================================={RESET}\n")
    pause()

def remove_teacher_flow(conn: sqlite3.Connection, dept_code: str):
    print_section("Remove Subject Teacher")
    list_faculty_flow(conn, dept_code, pause_after=False)
    teacher_id = prompt_int("Enter Faculty ID to remove (0 to cancel)", min_val=0)
    if not teacher_id:
        return
    try:
        if head_teacher_service.remove_subject_teacher(conn, teacher_id, dept_code):
            print_success(f"Faculty ID {teacher_id} successfully removed.")
        else:
            print_error(f"Faculty ID {teacher_id} not found in department {dept_code}.")
    except ValueError as e:
        print_error(str(e))
    pause()

def list_faculty_flow(conn: sqlite3.Connection, dept_code: str, pause_after: bool = True):
    print_section(f"Faculty Roster ({dept_code})")
    faculty_list = head_teacher_service.list_faculty(conn, dept_code)
    headers = ["Faculty ID", "Name", "Role", "Assigned Subjects", "Password"]
    rows = []
    for f in faculty_list:
        role = "Head Teacher" if f["is_head_teacher"] == 1 else "Subject Teacher"
        rows.append([f["faculty_id"], f["name"], role, f["subjects_count"], f["password"]])
    render_table(headers, rows)
    if pause_after:
        pause()

def add_subject_flow(conn: sqlite3.Connection, dept_code: str):
    print_section("Add New Subject")
    name = prompt_str("Enter Subject Name (e.g. Data Structures)")
    if not name:
        return
    planned = prompt_int("Enter approx. total planned lectures for semester", min_val=1, default=40)
    
    # Optional teacher assignment
    print("\nAvailable Faculty to Assign:")
    list_faculty_flow(conn, dept_code, pause_after=False)
    teacher_id = prompt_int("Enter Faculty ID to assign (or 0 for Unassigned)", min_val=0, default=0)
    assigned_id = teacher_id if teacher_id != 0 else None

    try:
        sub_id = head_teacher_service.add_subject(conn, name, dept_code, assigned_id, planned)
        print_success(f"Subject '{name}' created with ID: {sub_id}")
    except Exception as e:
        print_error(f"Failed to create subject: {e}")
    pause()

def assign_subject_flow(conn: sqlite3.Connection, dept_code: str):
    print_section("Assign / Reassign Subject Teacher")
    list_subjects_flow(conn, dept_code, pause_after=False)
    sub_id = prompt_int("Enter Subject ID to assign", min_val=1)
    if not sub_id:
        return
    
    list_faculty_flow(conn, dept_code, pause_after=False)
    teacher_id = prompt_int("Enter Faculty ID to assign to this subject (0 for Unassigned)", min_val=0)
    assigned_id = teacher_id if teacher_id != 0 else None

    try:
        if head_teacher_service.assign_subject_teacher(conn, sub_id, assigned_id, dept_code):
            print_success(f"Subject ID {sub_id} assigned to Teacher {assigned_id or 'Unassigned'}.")
        else:
            print_error("Subject not found or does not belong to this department.")
    except ValueError as e:
        print_error(str(e))
    pause()

def remove_subject_flow(conn: sqlite3.Connection, dept_code: str):
    print_section("Remove Subject")
    list_subjects_flow(conn, dept_code, pause_after=False)
    sub_id = prompt_int("Enter Subject ID to remove (0 to cancel)", min_val=0)
    if not sub_id:
        return
    if head_teacher_service.remove_subject_flow(conn, sub_id, dept_code) if hasattr(head_teacher_service, 'remove_subject_flow') else head_teacher_service.remove_subject(conn, sub_id, dept_code):
        print_success(f"Subject ID {sub_id} removed.")
    else:
        print_error("Subject not found.")
    pause()

def list_subjects_flow(conn: sqlite3.Connection, dept_code: str, pause_after: bool = True):
    print_section(f"Subjects Offering ({dept_code})")
    subjects = head_teacher_service.list_subjects(conn, dept_code)
    headers = ["Subject ID", "Subject Name", "Assigned Teacher", "Teacher ID", "Planned Lectures"]
    rows = []
    for s in subjects:
        t_name = s["teacher_name"] if s["teacher_name"] else "UNASSIGNED"
        t_id = s["assigned_teacher_id"] if s["assigned_teacher_id"] else "-"
        rows.append([s["subject_id"], s["subject_name"], t_name, t_id, s["total_planned_lectures"]])
    render_table(headers, rows)
    if pause_after:
        pause()

def add_student_flow(conn: sqlite3.Connection, dept_code: str):
    print_section(f"Add Student ({dept_code})")
    name = prompt_str("Enter Student's Full Name")
    if not name:
        return
    year = prompt_int("Enter Student Year (1 - 4)", min_val=1, max_val=4, default=1)
    
    try:
        res = head_teacher_service.add_student(conn, name, dept_code, year)
        print_success("Student added successfully!")
        print(f"\n{BOLD}================ STUDENT CREDENTIALS ================{RESET}")
        print(f"  Student UID: {BOLD}{res['uid']}{RESET} (Use this 6-digit UID to login)")
        print(f"  Name:        {res['name']}")
        print(f"  Department:  {res['dept_code']}")
        print(f"  Year:        Year {res['year']}")
        print(f"  Password:    {BOLD}{res['password']}{RESET}")
        print(f"{BOLD}===================================================={RESET}\n")
    except ValueError as e:
        print_error(str(e))
    pause()

def remove_student_flow(conn: sqlite3.Connection, dept_code: str):
    print_section("Remove Student")
    list_students_flow(conn, dept_code, pause_after=False)
    uid = prompt_int("Enter 6-digit Student UID to remove (0 to cancel)", min_val=0)
    if not uid:
        return
    if head_teacher_service.remove_student(conn, uid, dept_code):
        print_success(f"Student UID {uid} successfully removed.")
    else:
        print_error(f"Student UID {uid} not found in department {dept_code}.")
    pause()

def list_students_flow(conn: sqlite3.Connection, dept_code: str, pause_after: bool = True):
    print_section(f"Enrolled Students ({dept_code})")
    students = head_teacher_service.list_students(conn, dept_code)
    headers = ["Student UID", "Name", "Department", "Year", "Password"]
    rows = []
    for st in students:
        rows.append([st["uid"], st["name"], st["dept_code"], f"Year {st['year']}", st["password"]])
    render_table(headers, rows)
    if pause_after:
        pause()

# =====================================================================
# Subject Teacher Workflows
# =====================================================================

def subject_teacher_menu(conn: sqlite3.Connection, faculty: Dict[str, Any]):
    teacher_id = faculty["faculty_id"]
    while True:
        print_header(
            "SUBJECT TEACHER DASHBOARD",
            f"Logged in as: {faculty['name']} (Faculty ID: {teacher_id}, Dept: {faculty['dept_code']})"
        )
        print("  1. View My Assigned Subjects")
        print("  2. Enter / Edit Total Planned Lectures")
        print("  3. Mark Lecture Attendance (Present / Absent)")
        print("  4. View Subject Attendance Sheet & 75% Summary")
        print("  0. Logout")

        choice = prompt_int("Enter option", 0, 4)
        if choice == 0 or choice is None:
            print_info("Logged out from Subject Teacher account.")
            break
        elif choice == 1:
            view_assigned_subjects_flow(conn, teacher_id)
        elif choice == 2:
            edit_planned_lectures_flow(conn, teacher_id)
        elif choice == 3:
            mark_attendance_flow(conn, teacher_id)
        elif choice == 4:
            view_subject_sheet_flow(conn, teacher_id)

def view_assigned_subjects_flow(conn: sqlite3.Connection, teacher_id: int, pause_after: bool = True):
    print_section("My Assigned Subjects")
    subjects = subject_teacher_service.get_assigned_subjects(conn, teacher_id)
    headers = ["Subject ID", "Subject Name", "Department", "Planned Lectures", "Lectures Conducted"]
    rows = []
    for s in subjects:
        rows.append([
            s["subject_id"],
            s["subject_name"],
            s["dept_code"],
            s["total_planned_lectures"],
            s["conducted_count"]
        ])
    render_table(headers, rows)
    if pause_after:
        pause()

def edit_planned_lectures_flow(conn: sqlite3.Connection, teacher_id: int):
    print_section("Edit Total Planned Lectures")
    subjects = subject_teacher_service.get_assigned_subjects(conn, teacher_id)
    if not subjects:
        print_warning("No subjects currently assigned to you.")
        pause()
        return

    view_assigned_subjects_flow(conn, teacher_id, pause_after=False)
    sub_id = prompt_int("Enter Subject ID to update", min_val=1)
    if not sub_id:
        return

    new_planned = prompt_int("Enter new total planned lectures for semester", min_val=1)
    if not new_planned:
        return

    try:
        if subject_teacher_service.update_planned_lectures(conn, teacher_id, sub_id, new_planned):
            print_success(f"Total planned lectures for Subject {sub_id} updated to {new_planned}.")
    except Exception as e:
        print_error(str(e))
    pause()

def mark_attendance_flow(conn: sqlite3.Connection, teacher_id: int):
    print_section("Mark Lecture Attendance")
    subjects = subject_teacher_service.get_assigned_subjects(conn, teacher_id)
    if not subjects:
        print_warning("You do not have any assigned subjects.")
        pause()
        return

    view_assigned_subjects_flow(conn, teacher_id, pause_after=False)
    sub_id = prompt_int("Select Subject ID", min_val=1)
    if not sub_id:
        return

    if not subject_teacher_service.verify_teacher_assignment(conn, teacher_id, sub_id):
        print_error("Access Denied: You are not assigned to teach this subject.")
        pause()
        return

    students = subject_teacher_service.get_department_students_for_subject(conn, sub_id)
    if not students:
        print_warning("No students found enrolled in this subject's department.")
        pause()
        return

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    lecture_date = prompt_str("Enter Lecture Date (YYYY-MM-DD)", default=today_str)

    print_section(f"Attendance Marking Options ({len(students)} students)")
    print("  1. Fast Mode: Mark ALL as Present (P) by default, then specify Absentees (A)")
    print("  2. Sequential Mode: Prompt (P/A) student by student")
    mode = prompt_int("Select Mode", 1, 2, default=1)

    status_dict = {}

    if mode == 1:
        # Default all to P
        for st in students:
            status_dict[st["uid"]] = 'P'

        print_info("All students temporarily marked as Present (P).")
        print("\nStudent Roster:")
        render_table(["UID", "Name", "Year"], [[st["uid"], st["name"], f"Year {st['year']}"] for st in students])
        
        absent_input = prompt_str(
            "Enter UIDs of ABSENT students separated by commas (or press Enter if none)",
            allow_empty=True
        )
        if absent_input:
            absent_uids = [u.strip() for u in absent_input.split(",") if u.strip()]
            for uid_str in absent_uids:
                try:
                    uid_val = int(uid_str)
                    if uid_val in status_dict:
                        status_dict[uid_val] = 'A'
                    else:
                        print_warning(f"UID {uid_val} not in student list; ignored.")
                except ValueError:
                    print_warning(f"Invalid UID '{uid_str}'; ignored.")
    else:
        # Sequential mode
        print("\nEnter 'P' for Present or 'A' for Absent for each student:")
        for st in students:
            while True:
                val = prompt_str(f"[{st['uid']}] {st['name']} (Year {st['year']}) (P/A)", default="P").upper()
                if val in ('P', 'A'):
                    status_dict[st["uid"]] = val
                    break
                print_error("Please enter 'P' or 'A'.")

    # Confirm and save
    print_section("Summary of Attendance to Save")
    p_count = sum(1 for s in status_dict.values() if s == 'P')
    a_count = sum(1 for s in status_dict.values() if s == 'A')
    print(f"Date: {lecture_date} | Total: {len(status_dict)} | Present: {GREEN}{p_count}{RESET} | Absent: {RED}{a_count}{RESET}")

    saved = subject_teacher_service.mark_lecture_attendance(conn, teacher_id, sub_id, lecture_date, status_dict)
    print_success(f"Successfully recorded attendance for {saved} students on {lecture_date}!")
    pause()

def view_subject_sheet_flow(conn: sqlite3.Connection, teacher_id: int):
    print_section("Subject Attendance Sheet")
    subjects = subject_teacher_service.get_assigned_subjects(conn, teacher_id)
    if not subjects:
        print_warning("No subjects assigned.")
        pause()
        return

    view_assigned_subjects_flow(conn, teacher_id, pause_after=False)
    sub_id = prompt_int("Enter Subject ID", min_val=1)
    if not sub_id:
        return

    try:
        data = subject_teacher_service.get_subject_attendance_summary(conn, teacher_id, sub_id)
        sub = data["subject"]
        print_header(
            f"ATTENDANCE ROSTER: {sub['subject_name']}",
            f"Total Conducted: {data['total_conducted']} | Approx. Total Planned: {sub['total_planned_lectures']}"
        )

        headers = ["UID", "Name", "Year", "Attended", "Conducted", "Current %", "75% Status", "Approx. Advice"]
        rows = []
        for st in data["students"]:
            status_tag = f"{GREEN}>= 75%{RESET}" if st["is_on_track"] else f"{RED}< 75%{RESET}"
            if st["is_on_track"]:
                advice = f"approx. safe leaves: {st['approx_safe_leaves']}"
            else:
                advice = f"approx. need: {st['approx_needed_consecutive']} consecutive"

            pct_str = f"{st['percentage']}%"
            rows.append([st["uid"], st["name"], f"Yr {st['year']}", st["attended"], st["conducted"], pct_str, status_tag, advice])

        render_table(headers, rows)
    except Exception as e:
        print_error(str(e))
    pause()

# =====================================================================
# Student Workflows
# =====================================================================

def student_menu(conn: sqlite3.Connection, student: Dict[str, Any]):
    uid = student["uid"]
    while True:
        print_header(
            "STUDENT ATTENDANCE DASHBOARD",
            f"UID: {uid} | Name: {student['name']} | Dept: {student['dept_code']} | Year {student['year']}"
        )
        print("  1. Complete Attendance Dashboard (with 75% Advisor)")
        print("  2. View Lecture-by-Lecture Date History for a Subject")
        print("  0. Logout")

        choice = prompt_int("Enter option", 0, 2)
        if choice == 0 or choice is None:
            print_info("Logged out from Student account.")
            break
        elif choice == 1:
            view_student_dashboard_flow(conn, uid)
        elif choice == 2:
            view_student_history_flow(conn, uid)

def view_student_dashboard_flow(conn: sqlite3.Connection, uid: int):
    data = student_service.get_student_dashboard_data(conn, uid)
    st = data["student"]
    overall = data["overall"]

    print_section("Subject-Wise Lecture Attendance & 75% Leave Advisor")
    
    headers = [
        "Subject Name",
        "Teacher",
        "Conducted",
        "Attended",
        "Absent",
        "Current %",
        "approx. Planned",
        "approx. 75% Leave / Need Advisor"
    ]
    rows = []
    for s in data["subjects"]:
        pct_color = GREEN if s["is_on_track"] else RED
        pct_str = f"{pct_color}{s['current_pct']}%{RESET}"

        if s["is_on_track"]:
            advisor_str = f"{GREEN}approx. safe leaves: {s['approx_safe_leaves']}{RESET}"
        else:
            advisor_str = f"{RED}approx. need: {s['approx_needed_consecutive']} consecutive{RESET}"

        rows.append([
            s["subject_name"],
            s["teacher_name"],
            s["conducted"],
            s["attended"],
            s["absent"],
            pct_str,
            s["approx_total_planned"],
            advisor_str
        ])

    render_table(headers, rows)

    # Overall Summary
    print_section("Overall Semester Attendance Summary")
    overall_color = GREEN if overall["is_on_track"] else RED
    print(f"  Total Conducted Across All Subjects: {overall['total_conducted']}")
    print(f"  Total Attended:                      {overall['total_attended']}")
    print(f"  Total Absent:                        {overall['total_absent']}")
    print(f"  Overall Attendance Percentage:       {overall_color}{BOLD}{overall['overall_pct']}%{RESET}")
    if overall["is_on_track"]:
        print_success("Your overall attendance is currently above the required 75% threshold!")
    else:
        print_warning("Your overall attendance is below 75%! Please attend upcoming lectures to maintain eligibility.")

    pause()

def view_student_history_flow(conn: sqlite3.Connection, uid: int):
    data = student_service.get_student_dashboard_data(conn, uid)
    subjects = data["subjects"]
    if not subjects:
        print_warning("No subjects found.")
        pause()
        return

    print_section("Select Subject to View Date-wise Log")
    for idx, s in enumerate(subjects, 1):
        print(f"  {idx}. {s['subject_name']} (Conducted: {s['conducted']}, Attended: {s['attended']})")

    choice = prompt_int("Select Subject", 1, len(subjects))
    if not choice:
        return

    selected = subjects[choice - 1]
    history = student_service.get_student_subject_history(conn, uid, selected["subject_id"])

    print_header(f"Attendance Log: {selected['subject_name']}", f"Student UID: {uid}")
    headers = ["Date", "Status"]
    rows = []
    for record in history:
        status_str = f"{GREEN}Present (P){RESET}" if record["status"] == 'P' else f"{RED}Absent (A){RESET}"
        rows.append([record["date"], status_str])

    render_table(headers, rows)
    pause()
