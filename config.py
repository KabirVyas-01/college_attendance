import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "college_attendance.db")

# Supported Departments with branch codes, full names, and UID ranges
# CSE: 100000 - 199999, Faculty start: 10001
# CE:  200000 - 299999, Faculty start: 20001
# ME:  300000 - 399999, Faculty start: 30001
# EE:  400000 - 499999, Faculty start: 40001
DEPARTMENTS = [
    {
        "dept_code": "CSE",
        "dept_name": "Computer Science & Engineering",
        "uid_start": 100000,
        "uid_end": 199999,
        "faculty_start": 10001
    },
    {
        "dept_code": "CE",
        "dept_name": "Civil Engineering",
        "uid_start": 200000,
        "uid_end": 299999,
        "faculty_start": 20001
    },
    {
        "dept_code": "ME",
        "dept_name": "Mechanical Engineering",
        "uid_start": 300000,
        "uid_end": 399999,
        "faculty_start": 30001
    },
    {
        "dept_code": "EE",
        "dept_name": "Electrical Engineering",
        "uid_start": 400000,
        "uid_end": 499999,
        "faculty_start": 40001
    }
]

# Required attendance threshold percentage
MIN_ATTENDANCE_PCT = 75.0
