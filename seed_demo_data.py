import sqlite3
import datetime
from database import init_db, get_connection
from config import DB_PATH

def seed_demo_data(db_path=DB_PATH):
    """
    Populates sample departments, teachers, subjects, students, and attendance records
    for quick testing and demonstration.
    """
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    print("[*] Clearing existing sample records...")
    cursor.execute("DELETE FROM attendance")
    cursor.execute("DELETE FROM subjects")
    cursor.execute("DELETE FROM students")
    cursor.execute("DELETE FROM faculty")

    print("[*] Seeding Head Teachers & Subject Teachers...")
    # CSE Faculty
    cursor.execute("INSERT INTO faculty VALUES (10001, 'Prof. Alan Turing', 'admin123', 'CSE', 1)")
    cursor.execute("INSERT INTO faculty VALUES (10002, 'Dr. Ada Lovelace', 'teach123', 'CSE', 0)")
    cursor.execute("INSERT INTO faculty VALUES (10003, 'Prof. Claude Shannon', 'teach123', 'CSE', 0)")
    cursor.execute("INSERT INTO faculty VALUES (10004, 'Dr. Grace Hopper', 'teach123', 'CSE', 0)")

    # Civil Faculty
    cursor.execute("INSERT INTO faculty VALUES (20001, 'Prof. Isambard Brunel', 'admin123', 'CE', 1)")
    cursor.execute("INSERT INTO faculty VALUES (20002, 'Dr. Gustave Eiffel', 'teach123', 'CE', 0)")

    # Mechanical Faculty
    cursor.execute("INSERT INTO faculty VALUES (30001, 'Prof. James Watt', 'admin123', 'ME', 1)")

    # Electrical Faculty
    cursor.execute("INSERT INTO faculty VALUES (40001, 'Prof. Nikola Tesla', 'admin123', 'EE', 1)")

    print("[*] Seeding Subjects...")
    # CSE Subjects
    cursor.execute("INSERT INTO subjects (subject_id, subject_name, dept_code, assigned_teacher_id, total_planned_lectures) VALUES (1, 'Data Structures & Algorithms', 'CSE', 10002, 40)")
    cursor.execute("INSERT INTO subjects (subject_id, subject_name, dept_code, assigned_teacher_id, total_planned_lectures) VALUES (2, 'Operating Systems', 'CSE', 10003, 40)")
    cursor.execute("INSERT INTO subjects (subject_id, subject_name, dept_code, assigned_teacher_id, total_planned_lectures) VALUES (3, 'Database Management Systems', 'CSE', 10004, 40)")
    cursor.execute("INSERT INTO subjects (subject_id, subject_name, dept_code, assigned_teacher_id, total_planned_lectures) VALUES (4, 'Computer Networks', 'CSE', 10001, 35)")

    # CE Subjects
    cursor.execute("INSERT INTO subjects (subject_id, subject_name, dept_code, assigned_teacher_id, total_planned_lectures) VALUES (5, 'Structural Analysis', 'CE', 20002, 45)")

    print("[*] Seeding Students...")
    # CSE Students (100000 - 199999)
    cursor.execute("INSERT INTO students VALUES (100000, 'Alice Smith', 'stud123', 'CSE', 2)")
    cursor.execute("INSERT INTO students VALUES (100001, 'Bob Jones', 'stud123', 'CSE', 2)")
    cursor.execute("INSERT INTO students VALUES (100002, 'Charlie Brown', 'stud123', 'CSE', 2)")

    # CE Students (200000 - 299999)
    cursor.execute("INSERT INTO students VALUES (200000, 'David Miller', 'stud123', 'CE', 3)")
    cursor.execute("INSERT INTO students VALUES (200001, 'Emma Watson', 'stud123', 'CE', 3)")

    print("[*] Seeding 20 Lecture Attendance Records...")
    # Generate 20 dates
    base_date = datetime.date(2026, 8, 1)
    dates = [(base_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(20)]

    # DSA Subject (ID 1):
    # - Alice attended 18/20 (90%) -> Absences on dates[5], dates[10]
    # - Bob attended 12/20 (60%) -> Absences on dates[0..7]
    # - Charlie attended 20/20 (100%)
    for idx, d in enumerate(dates):
        # Alice
        status_alice = 'A' if idx in (5, 10) else 'P'
        cursor.execute("INSERT INTO attendance (student_uid, subject_id, date, status) VALUES (?, ?, ?, ?)", (100000, 1, d, status_alice))

        # Bob
        status_bob = 'A' if idx < 8 else 'P'
        cursor.execute("INSERT INTO attendance (student_uid, subject_id, date, status) VALUES (?, ?, ?, ?)", (100001, 1, d, status_bob))

        # Charlie
        cursor.execute("INSERT INTO attendance (student_uid, subject_id, date, status) VALUES (?, ?, ?, ?)", (100002, 1, d, 'P'))

    # OS Subject (ID 2):
    # - Alice attended 15/20 (75%) -> Absences on dates[0, 1, 2, 3, 4]
    # - Bob attended 16/20 (80%) -> Absences on dates[0, 1, 2, 3]
    # - Charlie attended 18/20 (90%)
    for idx, d in enumerate(dates):
        status_alice = 'A' if idx < 5 else 'P'
        cursor.execute("INSERT INTO attendance (student_uid, subject_id, date, status) VALUES (?, ?, ?, ?)", (100000, 2, d, status_alice))

        status_bob = 'A' if idx < 4 else 'P'
        cursor.execute("INSERT INTO attendance (student_uid, subject_id, date, status) VALUES (?, ?, ?, ?)", (100001, 2, d, status_bob))

        status_charlie = 'A' if idx in (2, 8) else 'P'
        cursor.execute("INSERT INTO attendance (student_uid, subject_id, date, status) VALUES (?, ?, ?, ?)", (100002, 2, d, status_charlie))

    # DBMS Subject (ID 3):
    # - Alice attended 10/20 (50% - Low!) -> Needs consecutive lectures
    # - Bob attended 19/20 (95%)
    # - Charlie attended 17/20 (85%)
    for idx, d in enumerate(dates):
        status_alice = 'A' if idx < 10 else 'P'
        cursor.execute("INSERT INTO attendance (student_uid, subject_id, date, status) VALUES (?, ?, ?, ?)", (100000, 3, d, status_alice))

        status_bob = 'A' if idx == 0 else 'P'
        cursor.execute("INSERT INTO attendance (student_uid, subject_id, date, status) VALUES (?, ?, ?, ?)", (100001, 3, d, status_bob))

        status_charlie = 'A' if idx in (1, 4, 7) else 'P'
        cursor.execute("INSERT INTO attendance (student_uid, subject_id, date, status) VALUES (?, ?, ?, ?)", (100002, 3, d, status_charlie))

    conn.commit()
    conn.close()
    print("[SUCCESS] Demo data populated successfully!")
    print("\nSample Login Credentials for Testing:")
    print("---------------------------------------------------------------")
    print("1. HEAD TEACHER (CSE):      ID: 10001   | Password: admin123")
    print("2. SUBJECT TEACHER (Ada):   ID: 10002   | Password: teach123")
    print("3. STUDENT (Alice):         UID: 100000 | Password: stud123")
    print("4. STUDENT (Bob):           UID: 100001 | Password: stud123")
    print("5. STUDENT (Charlie):       UID: 100002 | Password: stud123")
    print("---------------------------------------------------------------")

if __name__ == "__main__":
    seed_demo_data()
