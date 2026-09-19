# College Attendance Management System

A clean, modular, standalone Python command-line application backed by SQLite (`college_attendance.db`) that manages college lecture-wise attendance, strict role-based access control, auto-incrementing UID series, and an intelligent **75% Attendance Advisor**.

---

## Key Features

1. **Department Architecture & UID Ranges:**
   - **Computer Science & Engineering (CSE):** Faculty ID starts at `10001`, Students `100000 - 199999`
   - **Civil Engineering (CE):** Faculty ID starts at `20001`, Students `200000 - 299999`
   - **Mechanical Engineering (ME):** Faculty ID starts at `30001`, Students `300000 - 399999`
   - **Electrical Engineering (EE):** Faculty ID starts at `40001`, Students `400000 - 499999`
   - **Auto-generated 8-character passwords:** Secure alphanumeric `[a-z0-9]` passwords (e.g. `k9m3x7p2`).

2. **Role-Based Workflows:**
   - **Head Teacher Portal:**
     - Add / remove Subject Teachers (auto-assigns 5-digit Faculty ID & 8-character password).
     - Add / remove Subjects and map/assign teachers to subjects.
     - Add / remove Students (auto-assigns 6-digit branch UID & 8-character password).
     - View department-wide roster and statistics.
   - **Subject Teacher Portal:**
     - Set / edit **approx. total planned lectures** for assigned subjects in the semester.
     - Mark lecture attendance (**Present / Absent**) per date (supports both Fast-Batch mode and Sequential mode).
     - View subject attendance rosters with 75% status flags.
     - Strictly restricted from modifying students or other teachers.
   - **Student Dashboard:**
     - View lecture-wise attendance: Conducted, Attended, Absent, and Current Percentage.
     - View **approx. total number of lectures** in the semester.
     - View **approx. leaves allowed** (if $\ge 75\%$) or **approx. consecutive lectures needed to attend** (if $< 75\%$).
     - View overall semester attendance percentage across all subjects.
     - View lecture-by-lecture date log.

---

## 75% Attendance Mathematics

For each subject with Conducted lectures $C$, Attended lectures $A$, and Total Planned lectures $T$:

- **Current Attendance Percentage:**
  $$\text{Current \%} = \left( \frac{A}{C} \right) \times 100$$

- **If $\text{Current \%} \ge 75\%$ (On Track):**
  $$\text{Approx. Safe Leaves} = \max\left(0, \lfloor A - 0.75 \times T \rfloor + (T - C)\right)$$
  *(Calculates how many more lectures the student can miss across the remainder of the semester while maintaining $\ge 75\%$)*

- **If $\text{Current \%} < 75\%$ (Deficient):**
  $$\text{Approx. Consecutive Lectures Needed} = \max\left(0, \lceil 3 \times C - 4 \times A \rceil\right)$$
  *(Calculates the minimum uninterrupted streak of lectures the student must attend to climb back above $75\%$)*

---

## Project Structure

```
college_attendance/
├── config.py                 # Branch mappings, UID ranges, and DB path
├── database.py               # SQLite schema & foreign-key connection helper
├── auth.py                   # Secure password generation & authentication
├── calculator.py             # Attendance % formulas & 75% advisor logic
├── services/
│   ├── head_teacher_service.py    # Dept admin, faculty, subject & student management
│   ├── subject_teacher_service.py # Planned lectures, attendance marking & sheets
│   └── student_service.py         # Student dashboard & lecture history queries
├── cli/
│   ├── ui_helpers.py         # Dynamic ASCII tables, colors, headers, and input prompts
│   └── menus.py              # Interactive role-based CLI workflows
├── seed_demo_data.py         # Realistic sample data for instant testing
├── test_system.py            # Automated unit and integration test suite
├── main.py                   # Main runnable application entry point
└── README.md                 # System documentation
```

---

## How to Run

### Requirements
- Python 3.8+ (Uses only standard library: `sqlite3`, `secrets`, `datetime`, `math`, `os`, `sys`). **Zero external pip dependencies needed!**

### Run in VS Code:
1. Open [`main.py`](file:///D:/KABIR%20CS%20work/DT%20project/college_attendance/main.py).
2. Press **`F5`** (or click the Play ▷ button).
3. The interactive menu will run directly in your VS Code terminal.

### Run in Terminal:
```powershell
python main.py
```

---

## Demo Test Credentials

| Role | Name | ID / UID | Password | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Head Teacher (CSE)** | Prof. Alan Turing | `10001` | `admin123` | Full CSE Dept Admin |
| **Subject Teacher (DSA)** | Dr. Ada Lovelace | `10002` | `teach123` | Teaches Data Structures |
| **Subject Teacher (OS)** | Prof. Claude Shannon | `10003` | `teach123` | Teaches Operating Systems |
| **Student 1** | Alice Smith | `100000` | `stud123` | Mixed attendance (90% DSA, 75% OS, 50% DBMS) |
| **Student 2** | Bob Jones | `100001` | `stud123` | Good attendance (60% DSA, 80% OS, 95% DBMS) |
| **Student 3** | Charlie Brown | `100002` | `stud123` | High attendance (100% DSA, 90% OS, 85% DBMS) |
