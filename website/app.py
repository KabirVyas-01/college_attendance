import os
import sys
import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash

# Ensure parent directory is in python path to reuse existing modules and database
PARENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from config import DEPARTMENTS, MIN_ATTENDANCE_PCT
from database import init_db, get_connection
from auth import authenticate_faculty, authenticate_student
from services import (
    head_teacher_service,
    subject_teacher_service,
    student_service
)
from seed_demo_data import seed_demo_data

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.urandom(24)

# Initialize database on startup
init_db()

# =====================================================================
# Auth Decorators
# =====================================================================

def head_teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'head_teacher':
            flash("Please sign in with a Head Teacher account to access this section.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def subject_teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') not in ('subject_teacher', 'head_teacher'):
            flash("Please sign in with a Faculty/Teacher account to access this section.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'student':
            flash("Please sign in with your 6-digit Student UID to access your dashboard.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# =====================================================================
# Core / Authentication Routes
# =====================================================================

@app.route('/')
def index():
    role = session.get('user_role')
    if role == 'head_teacher':
        return redirect(url_for('head_teacher_dashboard'))
    elif role == 'subject_teacher':
        return redirect(url_for('subject_teacher_dashboard'))
    elif role == 'student':
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html', departments=DEPARTMENTS)

@app.route('/login', methods=['POST'])
def login_post():
    role = request.form.get('role')
    raw_id = request.form.get('identifier', '').strip()
    password = request.form.get('password', '').strip()

    if not raw_id or not password:
        flash("Please enter both ID/UID and password.", "error")
        return redirect(url_for('login'))

    try:
        id_val = int(raw_id)
    except ValueError:
        flash("Invalid ID format. Please enter numerical ID/UID.", "error")
        return redirect(url_for('login'))

    conn = get_connection()

    if role == 'student':
        student = authenticate_student(conn, id_val, password)
        conn.close()
        if student:
            session.clear()
            session['user_id'] = student['uid']
            session['user_name'] = student['name']
            session['user_role'] = 'student'
            session['user_dept'] = student['dept_code']
            flash(f"Welcome back, {student['name']}!", "success")
            return redirect(url_for('student_dashboard'))
        else:
            flash("Invalid Student UID or password. Please verify credentials.", "error")
            return redirect(url_for('login'))

    elif role in ('subject_teacher', 'head_teacher'):
        faculty = authenticate_faculty(conn, id_val, password)
        conn.close()
        if not faculty:
            flash("Invalid Faculty ID or password. Please verify credentials.", "error")
            return redirect(url_for('login'))

        is_head = faculty['is_head_teacher'] == 1
        if role == 'head_teacher' and not is_head:
            flash(f"Access Denied: Faculty ID {id_val} is a Subject Teacher, not a Head Teacher.", "error")
            return redirect(url_for('login'))

        session.clear()
        session['user_id'] = faculty['faculty_id']
        session['user_name'] = faculty['name']
        session['user_dept'] = faculty['dept_code']
        
        if is_head and role == 'head_teacher':
            session['user_role'] = 'head_teacher'
            flash(f"Signed in as Head Teacher ({faculty['dept_code']})", "success")
            return redirect(url_for('head_teacher_dashboard'))
        else:
            session['user_role'] = 'subject_teacher'
            flash(f"Signed in as Faculty ({faculty['dept_code']})", "success")
            return redirect(url_for('subject_teacher_dashboard'))

    conn.close()
    flash("Unknown authentication request.", "error")
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for('login'))

@app.route('/seed-demo-data')
def seed_data_route():
    seed_demo_data()
    flash("Demo data has been populated in the shared database! You can now test with sample accounts.", "success")
    return redirect(url_for('login'))

@app.route('/setup')
def setup_page():
    return render_template('setup.html', departments=DEPARTMENTS)

@app.route('/setup', methods=['POST'])
def setup_post():
    dept_code = request.form.get('dept_code')
    name = request.form.get('name', '').strip()
    password = request.form.get('password', '').strip()

    if not name or not dept_code:
        flash("Please provide all required fields.", "error")
        return redirect(url_for('setup_page'))

    if not password:
        from auth import generate_password
        password = generate_password(8)

    conn = get_connection()
    if head_teacher_service.is_head_teacher_configured(conn, dept_code):
        conn.close()
        flash(f"Head Teacher for {dept_code} is already registered.", "warning")
        return redirect(url_for('login'))

    faculty_id = head_teacher_service.create_head_teacher(conn, name, password, dept_code)
    conn.close()

    flash(f"Head Teacher created for {dept_code}! Faculty ID: {faculty_id}, Password: {password}", "success")
    return redirect(url_for('login'))

# =====================================================================
# Head Teacher Routes
# =====================================================================

@app.route('/head-teacher')
@head_teacher_required
def head_teacher_dashboard():
    dept_code = session.get('user_dept')
    conn = get_connection()
    
    faculty_list = head_teacher_service.list_faculty(conn, dept_code)
    subjects_list = head_teacher_service.list_subjects(conn, dept_code)
    students_list = head_teacher_service.list_students(conn, dept_code)
    
    faculty = {
        'faculty_id': session.get('user_id'),
        'name': session.get('user_name'),
        'dept_code': dept_code
    }
    conn.close()
    return render_template(
        'head_teacher/dashboard.html',
        faculty=faculty,
        faculty_list=faculty_list,
        subjects_list=subjects_list,
        students_list=students_list
    )

@app.route('/head-teacher/faculty')
@head_teacher_required
def head_teacher_faculty():
    dept_code = session.get('user_dept')
    conn = get_connection()
    faculty_list = head_teacher_service.list_faculty(conn, dept_code)
    conn.close()
    return render_template('head_teacher/faculty.html', dept_code=dept_code, faculty_list=faculty_list)

@app.route('/head-teacher/faculty/add', methods=['POST'])
@head_teacher_required
def head_teacher_add_faculty():
    name = request.form.get('name', '').strip()
    dept_code = session.get('user_dept')
    if not name:
        flash("Teacher name is required.", "error")
        return redirect(url_for('head_teacher_faculty'))

    conn = get_connection()
    res = head_teacher_service.add_subject_teacher(conn, name, dept_code)
    conn.close()

    flash(f"Subject Teacher '{res['name']}' created! Assigned Faculty ID: {res['faculty_id']}, Password: {res['password']}", "success")
    return redirect(url_for('head_teacher_faculty'))

@app.route('/head-teacher/faculty/remove/<int:faculty_id>', methods=['POST'])
@head_teacher_required
def head_teacher_remove_faculty(faculty_id):
    dept_code = session.get('user_dept')
    conn = get_connection()
    try:
        if head_teacher_service.remove_subject_teacher(conn, faculty_id, dept_code):
            flash(f"Faculty ID {faculty_id} has been removed.", "info")
        else:
            flash(f"Faculty member not found.", "error")
    except ValueError as e:
        flash(str(e), "error")
    finally:
        conn.close()
    return redirect(url_for('head_teacher_faculty'))

@app.route('/head-teacher/subjects')
@head_teacher_required
def head_teacher_subjects():
    dept_code = session.get('user_dept')
    conn = get_connection()
    subjects_list = head_teacher_service.list_subjects(conn, dept_code)
    faculty_list = head_teacher_service.list_faculty(conn, dept_code)
    conn.close()
    return render_template('head_teacher/subjects.html', dept_code=dept_code, subjects_list=subjects_list, faculty_list=faculty_list)

@app.route('/head-teacher/subjects/add', methods=['POST'])
@head_teacher_required
def head_teacher_add_subject():
    dept_code = session.get('user_dept')
    name = request.form.get('name', '').strip()
    planned = int(request.form.get('planned', 40))
    teacher_id_raw = int(request.form.get('teacher_id', 0))
    assigned_teacher_id = teacher_id_raw if teacher_id_raw != 0 else None

    if not name:
        flash("Subject name is required.", "error")
        return redirect(url_for('head_teacher_subjects'))

    conn = get_connection()
    sub_id = head_teacher_service.add_subject(conn, name, dept_code, assigned_teacher_id, planned)
    conn.close()

    flash(f"Subject '{name}' created with ID #{sub_id}!", "success")
    return redirect(url_for('head_teacher_subjects'))

@app.route('/head-teacher/subjects/assign/<int:subject_id>', methods=['POST'])
@head_teacher_required
def head_teacher_assign_subject(subject_id):
    dept_code = session.get('user_dept')
    teacher_id_raw = int(request.form.get('teacher_id', 0))
    assigned_teacher_id = teacher_id_raw if teacher_id_raw != 0 else None

    conn = get_connection()
    try:
        head_teacher_service.assign_subject_teacher(conn, subject_id, assigned_teacher_id, dept_code)
        flash("Teaching assignment updated successfully!", "success")
    except ValueError as e:
        flash(str(e), "error")
    finally:
        conn.close()
    return redirect(url_for('head_teacher_subjects'))

@app.route('/head-teacher/subjects/remove/<int:subject_id>', methods=['POST'])
@head_teacher_required
def head_teacher_remove_subject(subject_id):
    dept_code = session.get('user_dept')
    conn = get_connection()
    if head_teacher_service.remove_subject(conn, subject_id, dept_code):
        flash(f"Subject #{subject_id} removed.", "info")
    else:
        flash("Subject not found.", "error")
    conn.close()
    return redirect(url_for('head_teacher_subjects'))

@app.route('/head-teacher/students')
@head_teacher_required
def head_teacher_students():
    dept_code = session.get('user_dept')
    conn = get_connection()
    students_list = head_teacher_service.list_students(conn, dept_code)
    conn.close()
    return render_template('head_teacher/students.html', dept_code=dept_code, students_list=students_list)

@app.route('/head-teacher/students/add', methods=['POST'])
@head_teacher_required
def head_teacher_add_student():
    dept_code = session.get('user_dept')
    name = request.form.get('name', '').strip()
    year = int(request.form.get('year', 1))

    if not name:
        flash("Student name is required.", "error")
        return redirect(url_for('head_teacher_students'))

    conn = get_connection()
    try:
        res = head_teacher_service.add_student(conn, name, dept_code, year)
        flash(f"Student '{res['name']}' enrolled! Assigned 6-digit UID: {res['uid']}, Password: {res['password']}", "success")
    except ValueError as e:
        flash(str(e), "error")
    finally:
        conn.close()
    return redirect(url_for('head_teacher_students'))

@app.route('/head-teacher/students/remove/<int:uid>', methods=['POST'])
@head_teacher_required
def head_teacher_remove_student(uid):
    dept_code = session.get('user_dept')
    conn = get_connection()
    if head_teacher_service.remove_student(conn, uid, dept_code):
        flash(f"Student UID {uid} removed.", "info")
    else:
        flash("Student not found.", "error")
    conn.close()
    return redirect(url_for('head_teacher_students'))

# =====================================================================
# Subject Teacher Routes
# =====================================================================

@app.route('/teacher')
@subject_teacher_required
def subject_teacher_dashboard():
    teacher_id = session.get('user_id')
    conn = get_connection()
    subjects = subject_teacher_service.get_assigned_subjects(conn, teacher_id)
    faculty = {
        'faculty_id': teacher_id,
        'name': session.get('user_name'),
        'dept_code': session.get('user_dept')
    }
    conn.close()
    return render_template('subject_teacher/dashboard.html', faculty=faculty, subjects=subjects)

@app.route('/teacher/subjects/<int:subject_id>/planned', methods=['POST'])
@subject_teacher_required
def subject_teacher_update_planned(subject_id):
    teacher_id = session.get('user_id')
    planned = int(request.form.get('planned', 40))

    conn = get_connection()
    try:
        subject_teacher_service.update_planned_lectures(conn, teacher_id, subject_id, planned)
        flash(f"Planned lectures updated to {planned}!", "success")
    except Exception as e:
        flash(str(e), "error")
    finally:
        conn.close()
    return redirect(url_for('subject_teacher_dashboard'))

@app.route('/teacher/subjects/<int:subject_id>/attendance')
@subject_teacher_required
def subject_teacher_mark_attendance(subject_id):
    teacher_id = session.get('user_id')
    conn = get_connection()
    
    if not subject_teacher_service.verify_teacher_assignment(conn, teacher_id, subject_id):
        conn.close()
        flash("Access Denied: You are not assigned to teach this subject.", "error")
        return redirect(url_for('subject_teacher_dashboard'))

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subjects WHERE subject_id = ?", (subject_id,))
    subject = dict(cursor.fetchone())

    students = subject_teacher_service.get_department_students_for_subject(conn, subject_id)
    conn.close()

    today_date = datetime.date.today().strftime("%Y-%m-%d")
    return render_template('subject_teacher/mark_attendance.html', subject=subject, students=students, today_date=today_date)

@app.route('/teacher/subjects/<int:subject_id>/attendance/save', methods=['POST'])
@subject_teacher_required
def subject_teacher_save_attendance(subject_id):
    teacher_id = session.get('user_id')
    date_str = request.form.get('date', datetime.date.today().strftime("%Y-%m-%d"))

    conn = get_connection()
    students = subject_teacher_service.get_department_students_for_subject(conn, subject_id)
    
    status_dict = {}
    for st in students:
        val = request.form.get(f"status_{st['uid']}", 'P')
        status_dict[st['uid']] = val

    try:
        saved = subject_teacher_service.mark_lecture_attendance(conn, teacher_id, subject_id, date_str, status_dict)
        flash(f"Saved attendance for {saved} students on {date_str}!", "success")
    except Exception as e:
        flash(str(e), "error")
    finally:
        conn.close()

    return redirect(url_for('subject_teacher_subject_roster', subject_id=subject_id))

@app.route('/teacher/subjects/<int:subject_id>/roster')
@subject_teacher_required
def subject_teacher_subject_roster(subject_id):
    teacher_id = session.get('user_id')
    conn = get_connection()
    try:
        data = subject_teacher_service.get_subject_attendance_summary(conn, teacher_id, subject_id)
    except Exception as e:
        flash(str(e), "error")
        conn.close()
        return redirect(url_for('subject_teacher_dashboard'))

    conn.close()
    return render_template('subject_teacher/subject_roster.html', data=data)

# =====================================================================
# Student Routes
# =====================================================================

@app.route('/student')
@student_required
def student_dashboard():
    uid = session.get('user_id')
    conn = get_connection()
    try:
        data = student_service.get_student_dashboard_data(conn, uid)
    except Exception as e:
        flash(str(e), "error")
        conn.close()
        return redirect(url_for('login'))

    conn.close()
    return render_template(
        'student/dashboard.html',
        student=data['student'],
        subjects=data['subjects'],
        overall=data['overall']
    )

@app.route('/student/subjects/<int:subject_id>/history')
@student_required
def student_subject_history(subject_id):
    uid = session.get('user_id')
    conn = get_connection()
    
    cursor = conn.cursor()
    cursor.execute("SELECT subject_name FROM subjects WHERE subject_id = ?", (subject_id,))
    row = cursor.fetchone()
    subject_name = row['subject_name'] if row else "Subject"

    history = student_service.get_student_subject_history(conn, uid, subject_id)
    conn.close()

    return render_template(
        'student/subject_history.html',
        student_uid=uid,
        subject_name=subject_name,
        history=history
    )

# =====================================================================
# App Runner
# =====================================================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  COLLEGE ATTENDANCE WEBSITE RUNNING")
    print("  Open in your browser: http://127.0.0.1:5000")
    print("="*60 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
