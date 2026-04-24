-- ============================================================
-- Smart Classroom Timetable Scheduler - Database Schema
-- Compatible with SQL Server and SQLite
-- ============================================================

-- Departments
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    code TEXT NOT NULL UNIQUE,
    head_of_department TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Courses / Programs
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,
    department_id INTEGER NOT NULL,
    semester_count INTEGER DEFAULT 8,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

-- Semesters
CREATE TABLE IF NOT EXISTS semesters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    semester_number INTEGER NOT NULL,
    academic_year TEXT NOT NULL,
    student_count INTEGER DEFAULT 0,
    FOREIGN KEY (course_id) REFERENCES courses(id),
    UNIQUE(course_id, semester_number, academic_year)
);

-- Subjects
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,
    semester_id INTEGER NOT NULL,
    lectures_per_week INTEGER DEFAULT 3,
    is_lab INTEGER DEFAULT 0,
    priority INTEGER DEFAULT 5,  -- 1=highest, 10=lowest
    FOREIGN KEY (semester_id) REFERENCES semesters(id)
);

-- Faculty
CREATE TABLE IF NOT EXISTS faculty (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    department_id INTEGER NOT NULL,
    designation TEXT,
    max_hours_per_day INTEGER DEFAULT 6,
    max_hours_per_week INTEGER DEFAULT 25,
    is_active INTEGER DEFAULT 1,
    password_hash TEXT DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

-- Faculty-Subject mapping
CREATE TABLE IF NOT EXISTS faculty_subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    preference_score INTEGER DEFAULT 5,  -- 1-10 preference
    FOREIGN KEY (faculty_id) REFERENCES faculty(id),
    FOREIGN KEY (subject_id) REFERENCES subjects(id),
    UNIQUE(faculty_id, subject_id)
);

-- Faculty availability
CREATE TABLE IF NOT EXISTS faculty_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,  -- 0=Mon, 1=Tue, ..., 4=Fri
    timeslot_id INTEGER NOT NULL,
    is_available INTEGER DEFAULT 1,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id),
    FOREIGN KEY (timeslot_id) REFERENCES timeslots(id)
);

-- Classrooms
CREATE TABLE IF NOT EXISTS classrooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    building TEXT,
    floor INTEGER,
    capacity INTEGER NOT NULL,
    room_type TEXT DEFAULT 'lecture',  -- lecture, lab, seminar
    has_projector INTEGER DEFAULT 1,
    has_ac INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1
);

-- Time slots
CREATE TABLE IF NOT EXISTS timeslots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_number INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    is_break INTEGER DEFAULT 0,
    label TEXT
);

-- Generated Timetable entries
CREATE TABLE IF NOT EXISTS timetable_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timetable_version INTEGER NOT NULL,
    semester_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    faculty_id INTEGER NOT NULL,
    classroom_id INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,  -- 0=Mon..4=Fri
    timeslot_id INTEGER NOT NULL,
    is_locked INTEGER DEFAULT 0,  -- manually locked entries
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (semester_id) REFERENCES semesters(id),
    FOREIGN KEY (subject_id) REFERENCES subjects(id),
    FOREIGN KEY (faculty_id) REFERENCES faculty(id),
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id),
    FOREIGN KEY (timeslot_id) REFERENCES timeslots(id)
);

-- Historical timetables for ML training
CREATE TABLE IF NOT EXISTS timetable_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    semester_id INTEGER,
    subject_id INTEGER,
    faculty_id INTEGER,
    classroom_id INTEGER,
    day_of_week INTEGER,
    timeslot_id INTEGER,
    academic_year TEXT,
    fitness_score REAL,
    student_feedback_score REAL,
    conflict_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Swap requests from faculty
CREATE TABLE IF NOT EXISTS swap_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id INTEGER NOT NULL,
    entry_id INTEGER NOT NULL,
    requested_day INTEGER,
    requested_timeslot_id INTEGER,
    reason TEXT,
    status TEXT DEFAULT 'pending',  -- pending, approved, rejected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id),
    FOREIGN KEY (entry_id) REFERENCES timetable_entries(id)
);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_type TEXT NOT NULL,  -- admin, faculty, student
    user_id INTEGER,
    message TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Attendance student roster (admin-managed)
CREATE TABLE IF NOT EXISTS attendance_students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    registration_number TEXT NOT NULL UNIQUE,
    linked_user_id INTEGER,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily student attendance records
CREATE TABLE IF NOT EXISTS attendance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    attendance_date TEXT NOT NULL, -- YYYY-MM-DD
    status TEXT NOT NULL CHECK(status IN ('present', 'absent')),
    marked_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES attendance_students(id) ON DELETE CASCADE,
    FOREIGN KEY (marked_by) REFERENCES users(id),
    UNIQUE(student_id, attendance_date)
);

-- System users (admin login)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin',  -- admin, faculty, student
    linked_id INTEGER,  -- faculty.id or semester.id
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ML model metadata
CREATE TABLE IF NOT EXISTS ml_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    model_type TEXT NOT NULL,
    accuracy REAL,
    trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_path TEXT,
    parameters TEXT  -- JSON string of hyperparameters
);

-- Analytics / logs
CREATE TABLE IF NOT EXISTS generation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timetable_version INTEGER,
    algorithm_used TEXT,
    fitness_score REAL,
    conflicts_resolved INTEGER,
    generation_time_seconds REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
