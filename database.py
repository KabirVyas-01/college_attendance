import sqlite3
import os
from config import DB_PATH, DEPARTMENTS

def get_connection(db_path=DB_PATH):
    """
    Returns an SQLite connection with Row factory and Foreign Keys enabled.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path=DB_PATH):
    """
    Initializes the database tables and inserts default departments if they do not exist.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Departments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        dept_code TEXT PRIMARY KEY,
        dept_name TEXT NOT NULL,
        uid_start INTEGER NOT NULL,
        uid_end INTEGER NOT NULL,
        faculty_start INTEGER NOT NULL
    );
    """)

    # 2. Faculty table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faculty (
        faculty_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        password TEXT NOT NULL,
        dept_code TEXT NOT NULL,
        is_head_teacher INTEGER DEFAULT 0,
        FOREIGN KEY (dept_code) REFERENCES departments (dept_code) ON DELETE CASCADE
    );
    """)

    # 3. Students table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        uid INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        password TEXT NOT NULL,
        dept_code TEXT NOT NULL,
        year INTEGER NOT NULL,
        FOREIGN KEY (dept_code) REFERENCES departments (dept_code) ON DELETE CASCADE
    );
    """)

    # 4. Subjects table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_name TEXT NOT NULL,
        dept_code TEXT NOT NULL,
        assigned_teacher_id INTEGER,
        total_planned_lectures INTEGER DEFAULT 40,
        FOREIGN KEY (dept_code) REFERENCES departments (dept_code) ON DELETE CASCADE,
        FOREIGN KEY (assigned_teacher_id) REFERENCES faculty (faculty_id) ON DELETE SET NULL
    );
    """)

    # 5. Attendance records table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_uid INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT CHECK(status IN ('P', 'A')) NOT NULL,
        FOREIGN KEY (student_uid) REFERENCES students (uid) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects (subject_id) ON DELETE CASCADE,
        UNIQUE (student_uid, subject_id, date)
    );
    """)

    # Seed default departments if missing
    for dept in DEPARTMENTS:
        cursor.execute("""
        INSERT OR IGNORE INTO departments (dept_code, dept_name, uid_start, uid_end, faculty_start)
        VALUES (?, ?, ?, ?, ?);
        """, (dept["dept_code"], dept["dept_name"], dept["uid_start"], dept["uid_end"], dept["faculty_start"]))

    conn.commit()
    conn.close()
