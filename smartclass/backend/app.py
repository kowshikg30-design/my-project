
"""
Smart Classroom Timetable Scheduler - Flask Application
Main application with REST API endpoints and template rendering.
"""
import os
import sqlite3
from datetime import date
from functools import wraps
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, g

try:
    # Support running as `python app.py` from the backend folder.
    from ML.pipeline import SchedulingPipeline
except ModuleNotFoundError:
    # Support importing as `backend.app` from the project root.
    from .ML.pipeline import SchedulingPipeline

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'smart-scheduler-secret-2025')

DEFAULT_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'database', 'scheduler.db')
)
DB_PATH = os.environ.get('DB_PATH', DEFAULT_DB_PATH)


# ─── Database Helpers ────────────────────────────────────────────────

def ensure_attendance_schema(db):
    """Ensure attendance tables exist for both fresh and existing databases."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS attendance_students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            registration_number TEXT NOT NULL UNIQUE,
            linked_user_id INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS attendance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('present', 'absent')),
            marked_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES attendance_students(id) ON DELETE CASCADE,
            FOREIGN KEY (marked_by) REFERENCES users(id),
            UNIQUE(student_id, attendance_date)
        );
    """)
    cols = {row[1] for row in db.execute("PRAGMA table_info(attendance_students)").fetchall()}
    if 'linked_user_id' not in cols:
        db.execute("ALTER TABLE attendance_students ADD COLUMN linked_user_id INTEGER")
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_attendance_students_linked_user_id ON attendance_students(linked_user_id)"
    )


def ensure_faculty_schema(db):
    """Ensure faculty status column exists on existing databases."""
    table_exists = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='faculty'"
    ).fetchone()
    if not table_exists:
        return

    cols = {row[1] for row in db.execute("PRAGMA table_info(faculty)").fetchall()}
    if 'is_active' not in cols:
        db.execute("ALTER TABLE faculty ADD COLUMN is_active INTEGER DEFAULT 1")
    db.execute("UPDATE faculty SET is_active = 1 WHERE is_active IS NULL")


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        ensure_faculty_schema(g.db)
        ensure_attendance_schema(g.db)
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def dict_row(row):
    return dict(row) if row else None


def dict_rows(rows):
    return [dict(r) for r in rows]


def get_json_data():
    """Safely parse JSON request bodies."""
    return request.get_json(silent=True) or {}


def parse_iso_date(value):
    """Parse YYYY-MM-DD date strings and return normalized ISO date."""
    if value is None or str(value).strip() == '':
        return None
    try:
        return date.fromisoformat(str(value).strip()).isoformat()
    except ValueError:
        return None


def init_db():
    """Initialize database from schema and seed files."""
    db = sqlite3.connect(DB_PATH)
    schema_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'schema.sql')
    seed_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'seed_data.sql')

    with open(schema_path) as f:
        db.executescript(f.read())

    check = db.execute("SELECT COUNT(*) FROM departments").fetchone()[0]
    if check == 0:
        with open(seed_path) as f:
            db.executescript(f.read())
        print("[DB] Seed data loaded.")

    _ensure_default_users(db)

    db.close()
    print("[DB] Database initialized.")


def _ensure_default_users(db):
    """Ensure demo logins exist for each portal."""
    demo_users = [
        ('admin', 'admin123', 'admin', None),
        ('faculty1', 'faculty123', 'faculty', 1),
        ('faculty2', 'faculty123', 'faculty', 2),
        ('faculty3', 'faculty123', 'faculty', 3),
        ('faculty4', 'faculty123', 'faculty', 4),
        ('faculty5', 'faculty123', 'faculty', 5),
        ('faculty6', 'faculty123', 'faculty', 6),
        ('faculty7', 'faculty123', 'faculty', 7),
        ('student1', 'student123', 'student', 1),
        ('student2', 'student123', 'student', 2),
        ('student3', 'student123', 'student', 3),
    ]
    for username, password, role, linked_id in demo_users:
        db.execute(
            """
            INSERT OR IGNORE INTO users (username, password_hash, role, linked_id)
            VALUES (?, ?, ?, ?)
            """,
            (username, password, role, linked_id),
        )
    db.commit()


# ─── Auth Decorator ──────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('login_page'))

            if session.get('role') == 'faculty':
                linked_id = session.get('linked_id')
                faculty_row = None
                if linked_id is not None:
                    faculty_row = get_db().execute(
                        "SELECT is_active FROM faculty WHERE id = ?",
                        (linked_id,),
                    ).fetchone()
                if not faculty_row or int(faculty_row['is_active'] or 0) != 1:
                    session.clear()
                    if request.path.startswith('/api/'):
                        return jsonify({'error': 'Faculty account is inactive'}), 403
                    return redirect(url_for('login_page'))

            if session.get('role') not in allowed_roles:
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Forbidden'}), 403
                if session.get('role') == 'faculty':
                    return redirect(url_for('faculty_page'))
                if session.get('role') == 'student':
                    return redirect(url_for('student_page'))
                return redirect(url_for('dashboard_page'))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ─── Page Routes ─────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('role', 'admin')
        if role == 'faculty':
            return redirect(url_for('faculty_page'))
        elif role == 'student':
            return redirect(url_for('student_page'))
        return redirect(url_for('dashboard_page'))
    return redirect(url_for('login_page'))


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/dashboard')
@roles_required('admin')
def dashboard_page():
    return render_template('dashboard.html')


@app.route('/faculty-view')
@roles_required('faculty')
def faculty_page():
    return render_template('faculty.html', current_user={
        'id': session.get('user_id'),
        'username': session.get('username'),
        'role': session.get('role'),
        'linked_id': session.get('linked_id'),
    })


@app.route('/student-view')
@roles_required('student')
def student_page():
    return render_template('student.html', current_user={
        'id': session.get('user_id'),
        'username': session.get('username'),
        'role': session.get('role'),
        'linked_id': session.get('linked_id'),
    })


# ─── Auth API ────────────────────────────────────────────────────────

@app.route('/api/login', methods=['POST'])
def api_login():
    data = get_json_data()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username:
        return jsonify({'status': 'error', 'message': 'Username is required'}), 400
    if not password:
        return jsonify({'status': 'error', 'message': 'Password is required'}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    if not user:
        return jsonify({'status': 'error', 'message': 'Username not found'}), 401

    if user['password_hash'] != password:
        return jsonify({'status': 'error', 'message': 'Wrong password'}), 401

    if user['role'] == 'faculty':
        faculty = db.execute(
            "SELECT is_active FROM faculty WHERE id = ?",
            (user['linked_id'],),
        ).fetchone()
        if not faculty:
            return jsonify({'status': 'error', 'message': 'Faculty profile not found'}), 403
        if int(faculty['is_active'] or 0) != 1:
            return jsonify({'status': 'error', 'message': 'Faculty account is inactive. Contact admin.'}), 403

    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    session['linked_id'] = user['linked_id']
    return jsonify({'status': 'success', 'role': user['role']})


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'status': 'success'})


# ─── Department API ──────────────────────────────────────────────────

@app.route('/api/departments', methods=['GET'])
@roles_required('admin')
def get_departments():
    db = get_db()
    rows = db.execute("SELECT * FROM departments ORDER BY name").fetchall()
    return jsonify(dict_rows(rows))


@app.route('/api/departments', methods=['POST'])
@roles_required('admin')
def add_department():
    data = get_json_data()
    db = get_db()
    try:
        db.execute("INSERT INTO departments (name, code, head_of_department) VALUES (?, ?, ?)",
                   (data['name'], data['code'], data.get('head_of_department', '')))
        db.commit()
        return jsonify({'status': 'created'}), 201
    except KeyError as e:
        return jsonify({'error': f"Missing field: {e.args[0]}"}), 400
    except sqlite3.IntegrityError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/departments/<int:dept_id>', methods=['PUT'])
@roles_required('admin')
def update_department(dept_id):
    data = get_json_data()
    db = get_db()
    try:
        db.execute("UPDATE departments SET name=?, code=?, head_of_department=? WHERE id=?",
                   (data['name'], data['code'], data.get('head_of_department', ''), dept_id))
        db.commit()
        return jsonify({'status': 'updated'})
    except KeyError as e:
        return jsonify({'error': f"Missing field: {e.args[0]}"}), 400
    except sqlite3.IntegrityError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/departments/<int:dept_id>', methods=['DELETE'])
@roles_required('admin')
def delete_department(dept_id):
    db = get_db()
    try:
        db.execute("DELETE FROM departments WHERE id=?", (dept_id,))
        db.commit()
        return jsonify({'status': 'deleted'})
    except sqlite3.IntegrityError as e:
        return jsonify({'error': str(e)}), 400


# ─── Course API ──────────────────────────────────────────────────────

@app.route('/api/courses', methods=['GET'])
@roles_required('admin')
def get_courses():
    db = get_db()
    rows = db.execute("""
        SELECT c.*, d.name as department_name
        FROM courses c JOIN departments d ON c.department_id = d.id
        ORDER BY c.name
    """).fetchall()
    return jsonify(dict_rows(rows))


@app.route('/api/courses', methods=['POST'])
@roles_required('admin')
def add_course():
    data = get_json_data()
    db = get_db()
    try:
        db.execute("INSERT INTO courses (name, code, department_id, semester_count) VALUES (?, ?, ?, ?)",
                   (data['name'], data['code'], data['department_id'], data.get('semester_count', 8)))
        db.commit()
        return jsonify({'status': 'created'}), 201
    except KeyError as e:
        return jsonify({'error': f"Missing field: {e.args[0]}"}), 400
    except sqlite3.IntegrityError as e:
        return jsonify({'error': str(e)}), 400


# ─── Semester API ────────────────────────────────────────────────────

@app.route('/api/semesters', methods=['GET'])
@roles_required('admin', 'student')
def get_semesters():
    db = get_db()
    rows = db.execute("""
        SELECT s.*, c.name as course_name, c.code as course_code
        FROM semesters s JOIN courses c ON s.course_id = c.id
        ORDER BY c.name, s.semester_number
    """).fetchall()
    return jsonify(dict_rows(rows))


@app.route('/api/semesters', methods=['POST'])
@roles_required('admin')
def add_semester():
    data = get_json_data()
    db = get_db()
    try:
        db.execute("INSERT INTO semesters (course_id, semester_number, academic_year, student_count) VALUES (?, ?, ?, ?)",
                   (data['course_id'], data['semester_number'], data['academic_year'], data.get('student_count', 0)))
        db.commit()
        return jsonify({'status': 'created'}), 201
    except KeyError as e:
        return jsonify({'error': f"Missing field: {e.args[0]}"}), 400
    except sqlite3.IntegrityError as e:
        return jsonify({'error': str(e)}), 400


# ─── Subject API ─────────────────────────────────────────────────────

@app.route('/api/subjects', methods=['GET'])
@roles_required('admin')
def get_subjects():
    db = get_db()
    rows = db.execute("""
        SELECT sub.*, s.semester_number, c.name as course_name
        FROM subjects sub
        JOIN semesters s ON sub.semester_id = s.id
        JOIN courses c ON s.course_id = c.id
        ORDER BY c.name, s.semester_number, sub.name
    """).fetchall()
    return jsonify(dict_rows(rows))


@app.route('/api/subjects', methods=['POST'])
@roles_required('admin')
def add_subject():
    data = get_json_data()
    db = get_db()
    try:
        db.execute(
            "INSERT INTO subjects (name, code, semester_id, lectures_per_week, is_lab, priority) VALUES (?, ?, ?, ?, ?, ?)",
            (data['name'], data['code'], data['semester_id'],
             data.get('lectures_per_week', 3), data.get('is_lab', 0), data.get('priority', 5)))
        db.commit()
        return jsonify({'status': 'created'}), 201
    except KeyError as e:
        return jsonify({'error': f"Missing field: {e.args[0]}"}), 400
    except sqlite3.IntegrityError as e:
        return jsonify({'error': str(e)}), 400


# ─── Faculty API ─────────────────────────────────────────────────────

@app.route('/api/faculty', methods=['GET'])
@roles_required('admin', 'faculty')
def get_faculty():
    db = get_db()
    query = """
        SELECT f.*, d.name as department_name
        FROM faculty f JOIN departments d ON f.department_id = d.id
    """
    args = []
    if session.get('role') == 'faculty':
        query += " WHERE f.id = ?"
        args.append(session.get('linked_id'))
    query += " ORDER BY f.name"
    rows = db.execute(query, args).fetchall()
    return jsonify(dict_rows(rows))


@app.route('/api/faculty', methods=['POST'])
@roles_required('admin')
def add_faculty():
    data = get_json_data()
    db = get_db()
    try:
        db.execute(
            "INSERT INTO faculty (name, email, department_id, designation, max_hours_per_day, max_hours_per_week, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data['name'], data['email'], data['department_id'],
             data.get('designation', ''), data.get('max_hours_per_day', 6), data.get('max_hours_per_week', 25),
             data.get('is_active', 1)))
        db.commit()
        return jsonify({'status': 'created'}), 201
    except KeyError as e:
        return jsonify({'error': f"Missing field: {e.args[0]}"}), 400
    except sqlite3.IntegrityError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/faculty/<int:faculty_id>/status', methods=['PUT'])
@roles_required('admin')
def update_faculty_status(faculty_id):
    data = get_json_data()
    raw = data.get('is_active')

    if isinstance(raw, bool):
        is_active = 1 if raw else 0
    else:
        try:
            is_active = int(raw) # type: ignore
        except (TypeError, ValueError):
            return jsonify({'error': 'is_active must be 0 or 1'}), 400

    if is_active not in (0, 1):
        return jsonify({'error': 'is_active must be 0 or 1'}), 400

    db = get_db()
    cursor = db.execute(
        "UPDATE faculty SET is_active = ? WHERE id = ?",
        (is_active, faculty_id),
    )
    db.commit()

    if cursor.rowcount == 0:
        return jsonify({'error': 'Faculty not found'}), 404

    return jsonify({'status': 'updated', 'faculty_id': faculty_id, 'is_active': is_active})


@app.route('/api/faculty-subjects', methods=['GET'])
@roles_required('admin', 'faculty')
def get_faculty_subjects():
    db = get_db()
    query = """
        SELECT fs.*, f.name as faculty_name, sub.name as subject_name, sub.code as subject_code
        FROM faculty_subjects fs
        JOIN faculty f ON fs.faculty_id = f.id
        JOIN subjects sub ON fs.subject_id = sub.id
    """
    args = []
    if session.get('role') == 'faculty':
        query += " WHERE fs.faculty_id = ?"
        args.append(session.get('linked_id'))
    rows = db.execute(query, args).fetchall()
    return jsonify(dict_rows(rows))


@app.route('/api/faculty-subjects', methods=['POST'])
@roles_required('admin')
def add_faculty_subject():
    data = get_json_data()
    db = get_db()
    try:
        db.execute("INSERT INTO faculty_subjects (faculty_id, subject_id, preference_score) VALUES (?, ?, ?)",
                   (data['faculty_id'], data['subject_id'], data.get('preference_score', 5)))
        db.commit()
        return jsonify({'status': 'created'}), 201
    except KeyError as e:
        return jsonify({'error': f"Missing field: {e.args[0]}"}), 400
    except sqlite3.IntegrityError as e:
        return jsonify({'error': str(e)}), 400


# ─── Classroom API ───────────────────────────────────────────────────

@app.route('/api/classrooms', methods=['GET'])
@roles_required('admin', 'student')
def get_classrooms():
    db = get_db()
    rows = db.execute("SELECT * FROM classrooms ORDER BY name").fetchall()
    return jsonify(dict_rows(rows))


@app.route('/api/classrooms', methods=['POST'])
@roles_required('admin')
def add_classroom():
    data = get_json_data()
    db = get_db()
    try:
        db.execute(
            "INSERT INTO classrooms (name, building, floor, capacity, room_type, has_projector, has_ac) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data['name'], data.get('building', ''), data.get('floor', 0),
             data['capacity'], data.get('room_type', 'lecture'),
             data.get('has_projector', 1), data.get('has_ac', 0)))
        db.commit()
        return jsonify({'status': 'created'}), 201
    except KeyError as e:
        return jsonify({'error': f"Missing field: {e.args[0]}"}), 400
    except sqlite3.IntegrityError as e:
        return jsonify({'error': str(e)}), 400


# ─── Timeslot API ────────────────────────────────────────────────────

@app.route('/api/timeslots', methods=['GET'])
@roles_required('admin', 'faculty', 'student')
def get_timeslots():
    db = get_db()
    rows = db.execute("SELECT * FROM timeslots ORDER BY slot_number").fetchall()
    return jsonify(dict_rows(rows))


# ─── Timetable Generation API ───────────────────────────────────────

@app.route('/api/generate', methods=['POST'])
@roles_required('admin')
def generate_timetable():
    """Main endpoint: triggers the full ML pipeline."""
    db = get_db()
    params = get_json_data()

    data = _load_scheduling_data(db)
    if not data['subjects']:
        return jsonify({'error': 'No subjects found. Add data first.'}), 400
    if not data['faculty_subjects']:
        return jsonify({'error': 'No faculty-subject mappings found.'}), 400

    pipeline = SchedulingPipeline(data)
    result = pipeline.run(
        use_ml=params.get('use_ml', True),
        ga_generations=params.get('ga_generations', 80),
        ga_population=params.get('ga_population', 25),
    )

    if result['status'] == 'success':
        version = _get_next_version(db)
        _save_timetable(db, result['schedule'], version)
        _log_generation(db, version, result)
        _notify_students_timetable_generated(db, version)
        result['timetable_version'] = version

    return jsonify(result)


@app.route('/api/timetable', methods=['GET'])
@roles_required('admin', 'faculty', 'student')
def get_timetable():
    """Get the latest generated timetable, with optional filters."""
    db = get_db()
    version = request.args.get('version')
    semester_id = request.args.get('semester_id')
    faculty_id = request.args.get('faculty_id')

    query = """
        SELECT te.*,
               sub.name as subject_name, sub.code as subject_code, sub.is_lab,
               f.name as faculty_name,
               cr.name as classroom_name, cr.room_type,
               ts.start_time, ts.end_time, ts.label as slot_label,
               s.semester_number, c.name as course_name
        FROM timetable_entries te
        JOIN subjects sub ON te.subject_id = sub.id
        JOIN faculty f ON te.faculty_id = f.id
        JOIN classrooms cr ON te.classroom_id = cr.id
        JOIN timeslots ts ON te.timeslot_id = ts.id
        JOIN semesters s ON te.semester_id = s.id
        JOIN courses c ON s.course_id = c.id
    """
    conditions = []
    args = []

    if version:
        conditions.append("te.timetable_version = ?")
        args.append(int(version))
    else:
        conditions.append("te.timetable_version = (SELECT MAX(timetable_version) FROM timetable_entries)")

    if session.get('role') == 'student':
        conditions.append("te.semester_id = ?")
        args.append(int(session.get('linked_id')))
    elif semester_id:
        conditions.append("te.semester_id = ?")
        args.append(int(semester_id))

    if session.get('role') == 'faculty':
        conditions.append("te.faculty_id = ?")
        args.append(int(session.get('linked_id')))
    elif faculty_id:
        conditions.append("te.faculty_id = ?")
        args.append(int(faculty_id))

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY te.day_of_week, ts.slot_number"

    rows = db.execute(query, args).fetchall()
    return jsonify(dict_rows(rows))


@app.route('/api/timetable/versions', methods=['GET'])
@roles_required('admin')
def get_versions():
    db = get_db()
    rows = db.execute("""
        SELECT DISTINCT timetable_version, COUNT(*) as entry_count,
               MIN(created_at) as created_at
        FROM timetable_entries GROUP BY timetable_version ORDER BY timetable_version DESC
    """).fetchall()
    return jsonify(dict_rows(rows))


# ─── Swap Requests API ──────────────────────────────────────────────

@app.route('/api/swap-requests', methods=['GET'])
@roles_required('admin', 'faculty')
def get_swap_requests():
    db = get_db()
    query = """
        SELECT sr.*, f.name as faculty_name,
               sub.name as subject_name, ts.label as current_slot
        FROM swap_requests sr
        JOIN faculty f ON sr.faculty_id = f.id
        JOIN timetable_entries te ON sr.entry_id = te.id
        JOIN subjects sub ON te.subject_id = sub.id
        JOIN timeslots ts ON te.timeslot_id = ts.id
    """
    args = []
    if session.get('role') == 'faculty':
        query += " WHERE sr.faculty_id = ?"
        args.append(session.get('linked_id'))
    query += " ORDER BY sr.created_at DESC"
    rows = db.execute(query, args).fetchall()
    return jsonify(dict_rows(rows))


@app.route('/api/swap-requests', methods=['POST'])
@roles_required('faculty')
def create_swap_request():
    data = get_json_data()
    db = get_db()
    try:
        faculty_id = int(session.get('linked_id'))
        entry = db.execute(
            "SELECT id FROM timetable_entries WHERE id = ? AND faculty_id = ?",
            (data['entry_id'], faculty_id)
        ).fetchone()
        if not entry:
            return jsonify({'error': 'You can only request swaps for your own timetable entries'}), 403
        db.execute(
            "INSERT INTO swap_requests (faculty_id, entry_id, requested_day, requested_timeslot_id, reason) VALUES (?, ?, ?, ?, ?)",
            (faculty_id, data['entry_id'], data.get('requested_day'),
             data.get('requested_timeslot_id'), data.get('reason', '')))
        db.commit()
        return jsonify({'status': 'created'}), 201
    except KeyError as e:
        return jsonify({'error': f"Missing field: {e.args[0]}"}), 400
    except sqlite3.IntegrityError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/swap-requests/<int:req_id>/approve', methods=['POST'])
@roles_required('admin')
def approve_swap(req_id):
    db = get_db()
    req = dict_row(db.execute("SELECT * FROM swap_requests WHERE id=?", (req_id,)).fetchone())
    if not req:
        return jsonify({'error': 'Not found'}), 404

    if req['requested_day'] is not None:
        db.execute("UPDATE timetable_entries SET day_of_week=? WHERE id=?",
                   (req['requested_day'], req['entry_id']))
    if req['requested_timeslot_id']:
        db.execute("UPDATE timetable_entries SET timeslot_id=? WHERE id=?",
                   (req['requested_timeslot_id'], req['entry_id']))

    db.execute("UPDATE swap_requests SET status='approved' WHERE id=?", (req_id,))
    db.commit()
    return jsonify({'status': 'approved'})


@app.route('/api/swap-requests/<int:req_id>/reject', methods=['POST'])
@roles_required('admin')
def reject_swap(req_id):
    db = get_db()
    db.execute("UPDATE swap_requests SET status='rejected' WHERE id=?", (req_id,))
    db.commit()
    return jsonify({'status': 'rejected'})


@app.route('/api/swap-requests/<int:req_id>', methods=['DELETE'])
@roles_required('admin')
def delete_swap_request(req_id):
    db = get_db()
    cursor = db.execute("DELETE FROM swap_requests WHERE id=?", (req_id,))
    db.commit()
    if cursor.rowcount == 0:
        return jsonify({'error': 'Swap request not found'}), 404
    return jsonify({'status': 'deleted'})


@app.route('/api/swap-requests/clear', methods=['DELETE'])
@roles_required('admin')
def clear_swap_requests():
    db = get_db()
    db.execute("DELETE FROM swap_requests")
    db.commit()
    return jsonify({'status': 'deleted'})


# ─── Analytics API ───────────────────────────────────────────────────

@app.route('/api/analytics/overview', methods=['GET'])
@roles_required('admin')
def analytics_overview():
    db = get_db()
    stats = {
        'departments': db.execute("SELECT COUNT(*) FROM departments").fetchone()[0],
        'courses': db.execute("SELECT COUNT(*) FROM courses").fetchone()[0],
        'subjects': db.execute("SELECT COUNT(*) FROM subjects").fetchone()[0],
        'faculty': db.execute("SELECT COUNT(*) FROM faculty").fetchone()[0],
        'classrooms': db.execute("SELECT COUNT(*) FROM classrooms").fetchone()[0],
        'timetable_entries': db.execute("SELECT COUNT(*) FROM timetable_entries").fetchone()[0],
    }

    logs = db.execute("""
        SELECT * FROM generation_logs ORDER BY created_at DESC LIMIT 5
    """).fetchall()
    stats['recent_generations'] = dict_rows(logs)

    return jsonify(stats)


@app.route('/api/analytics/faculty-workload', methods=['GET'])
@roles_required('admin')
def faculty_workload():
    db = get_db()
    rows = db.execute("""
        SELECT f.id, f.name, f.max_hours_per_week,
               COUNT(te.id) as assigned_hours,
               COUNT(DISTINCT te.day_of_week) as active_days
        FROM faculty f
        LEFT JOIN timetable_entries te ON f.id = te.faculty_id
            AND te.timetable_version = (SELECT MAX(timetable_version) FROM timetable_entries)
        GROUP BY f.id
        ORDER BY f.name
    """).fetchall()
    return jsonify(dict_rows(rows))


@app.route('/api/analytics/room-utilization', methods=['GET'])
@roles_required('admin')
def room_utilization():
    db = get_db()
    rows = db.execute("""
        SELECT cr.id, cr.name, cr.capacity, cr.room_type,
               COUNT(te.id) as used_slots,
               30 as total_slots
        FROM classrooms cr
        LEFT JOIN timetable_entries te ON cr.id = te.classroom_id
            AND te.timetable_version = (SELECT MAX(timetable_version) FROM timetable_entries)
        GROUP BY cr.id
        ORDER BY cr.name
    """).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d['utilization_pct'] = round(d['used_slots'] / 30 * 100, 1)
        result.append(d)
    return jsonify(result)


# ─── Notifications API ──────────────────────────────────────────────

@app.route('/api/notifications', methods=['GET'])
@roles_required('student')
def get_notifications():
    db = get_db()
    rows = db.execute("""
        SELECT *
        FROM notifications
        WHERE user_type = 'student' AND user_id = ?
        ORDER BY created_at DESC
        LIMIT 20
    """, (session.get('user_id'),)).fetchall()
    return jsonify(dict_rows(rows))


@app.route('/api/notifications/mark-read', methods=['POST'])
@roles_required('student')
def mark_notifications_read():
    db = get_db()
    db.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_type = 'student' AND user_id = ?
    """, (session.get('user_id'),))
    db.commit()
    return jsonify({'status': 'success'})


@app.route('/api/notifications/<int:notification_id>', methods=['DELETE'])
@roles_required('student')
def delete_notification(notification_id):
    db = get_db()
    cursor = db.execute("""
        DELETE FROM notifications
        WHERE id = ?
          AND user_type = 'student'
          AND user_id = ?
    """, (notification_id, session.get('user_id')))
    db.commit()
    if cursor.rowcount == 0:
        return jsonify({'error': 'Notification not found'}), 404
    return jsonify({'status': 'success'})


@app.route('/api/notifications/clear', methods=['DELETE'])
@roles_required('student')
def clear_notifications():
    db = get_db()
    db.execute("""
        DELETE FROM notifications
        WHERE user_type = 'student'
          AND user_id = ?
    """, (session.get('user_id'),))
    db.commit()
    return jsonify({'status': 'success'})


# Student Attendance API

@app.route('/api/attendance/students', methods=['GET'])
@roles_required('admin', 'faculty')
def get_attendance_students():
    db = get_db()
    rows = db.execute("""
        SELECT id, name, registration_number, is_active, created_at
        FROM attendance_students
        ORDER BY name
    """).fetchall()
    return jsonify(dict_rows(rows))


@app.route('/api/attendance/students', methods=['POST'])
@roles_required('faculty')
def add_attendance_student():
    data = get_json_data()
    name = str(data.get('name', '')).strip()
    registration_number = str(data.get('registration_number', '')).strip()

    if not name:
        return jsonify({'error': 'Student name is required'}), 400
    if not registration_number:
        return jsonify({'error': 'Registration number is required'}), 400

    db = get_db()
    try:
        db.execute("""
            INSERT INTO attendance_students (name, registration_number, is_active)
            VALUES (?, ?, 1)
        """, (name, registration_number))
        db.commit()
        return jsonify({'status': 'created'}), 201
    except sqlite3.IntegrityError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/attendance', methods=['GET'])
@roles_required('admin', 'faculty', 'student')
def get_attendance_sheet():
    raw_date = request.args.get('date')
    attendance_date = parse_iso_date(raw_date) if raw_date else date.today().isoformat()
    if raw_date and not attendance_date:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    db = get_db()
    query = """
        SELECT
            s.id AS student_id,
            s.name AS student_name,
            s.registration_number,
            ? AS attendance_date,
            ar.status,
            ar.updated_at
        FROM attendance_students s
        LEFT JOIN attendance_records ar
            ON ar.student_id = s.id
           AND ar.attendance_date = ?
        WHERE s.is_active = 1
    """
    args = [attendance_date, attendance_date]

    if session.get('role') == 'student':
        student_row = _resolve_attendance_student_for_current_user(db)
        if not student_row:
            return jsonify([])
        query += " AND s.id = ?"
        args.append(student_row['id'])

    query += " ORDER BY s.name"
    rows = db.execute(query, args).fetchall()

    sheet = []
    for index, row in enumerate(rows, start=1):
        item = dict(row)
        item['serial_no'] = index
        sheet.append(item)
    return jsonify(sheet)


@app.route('/api/attendance', methods=['POST'])
@roles_required('faculty')
def mark_attendance():
    data = get_json_data()
    try:
        student_id = int(data.get('student_id'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Valid student_id is required'}), 400

    status = str(data.get('status', '')).strip().lower()
    if status not in {'present', 'absent'}:
        return jsonify({'error': "Status must be either 'present' or 'absent'"}), 400

    raw_date = data.get('date')
    attendance_date = parse_iso_date(raw_date) if raw_date else date.today().isoformat()
    if raw_date and not attendance_date:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    db = get_db()
    student = db.execute(
        """
        SELECT id, name, registration_number, linked_user_id
        FROM attendance_students
        WHERE id = ? AND is_active = 1
        """,
        (student_id,)
    ).fetchone()
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    existing = db.execute(
        "SELECT status FROM attendance_records WHERE student_id = ? AND attendance_date = ?",
        (student_id, attendance_date)
    ).fetchone()

    db.execute("""
        INSERT INTO attendance_records (student_id, attendance_date, status, marked_by, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(student_id, attendance_date)
        DO UPDATE SET
            status = excluded.status,
            marked_by = excluded.marked_by,
            updated_at = CURRENT_TIMESTAMP
    """, (student_id, attendance_date, status, session.get('user_id')))

    previous_status = existing['status'] if existing else None
    if previous_status != status:
        _notify_students_attendance_marked(
            db,
            student,
            attendance_date,
            status
        )

    db.commit()
    return jsonify({'status': 'saved', 'student_id': student_id, 'date': attendance_date, 'attendance': status})


@app.route('/api/attendance/bulk', methods=['POST'])
@roles_required('faculty')
def mark_attendance_bulk():
    data = get_json_data()
    status = str(data.get('status', '')).strip().lower()
    if status not in {'present', 'absent'}:
        return jsonify({'error': "Status must be either 'present' or 'absent'"}), 400

    raw_date = data.get('date')
    attendance_date = parse_iso_date(raw_date) if raw_date else date.today().isoformat()
    if raw_date and not attendance_date:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    db = get_db()
    students = db.execute(
        """
        SELECT id, name, registration_number, linked_user_id
        FROM attendance_students
        WHERE is_active = 1
        ORDER BY id
        """
    ).fetchall()

    if not students:
        return jsonify({'status': 'saved', 'updated_count': 0, 'date': attendance_date, 'attendance': status})

    rows = [
        (student['id'], attendance_date, status, session.get('user_id'))
        for student in students
    ]
    db.executemany("""
        INSERT INTO attendance_records (student_id, attendance_date, status, marked_by, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(student_id, attendance_date)
        DO UPDATE SET
            status = excluded.status,
            marked_by = excluded.marked_by,
            updated_at = CURRENT_TIMESTAMP
    """, rows)

    _notify_students_bulk_attendance_marked(db, attendance_date, status, students)
    db.commit()
    return jsonify({
        'status': 'saved',
        'updated_count': len(rows),
        'date': attendance_date,
        'attendance': status
    })


@app.route('/api/attendance/records', methods=['GET'])
@roles_required('admin', 'faculty', 'student')
def get_attendance_records():
    from_date_raw = request.args.get('from_date')
    to_date_raw = request.args.get('to_date')
    from_date = parse_iso_date(from_date_raw)
    to_date = parse_iso_date(to_date_raw)
    student_id = request.args.get('student_id')

    if from_date_raw and not from_date:
        return jsonify({'error': 'Invalid from_date format. Use YYYY-MM-DD'}), 400
    if to_date_raw and not to_date:
        return jsonify({'error': 'Invalid to_date format. Use YYYY-MM-DD'}), 400

    db = get_db()
    query = """
        SELECT
            ar.id,
            ar.attendance_date,
            ar.status,
            ar.updated_at,
            s.id AS student_id,
            s.name AS student_name,
            s.registration_number
        FROM attendance_records ar
        JOIN attendance_students s ON s.id = ar.student_id
    """
    conditions = []
    args = []

    if from_date:
        conditions.append("ar.attendance_date >= ?")
        args.append(from_date)
    if to_date:
        conditions.append("ar.attendance_date <= ?")
        args.append(to_date)
    if student_id:
        try:
            sid = int(student_id)
        except ValueError:
            return jsonify({'error': 'Invalid student_id'}), 400
        conditions.append("ar.student_id = ?")
        args.append(sid)

    if session.get('role') == 'student':
        student_row = _resolve_attendance_student_for_current_user(db)
        if not student_row:
            return jsonify({
                'summary': {
                    'total_records': 0,
                    'present_count': 0,
                    'absent_count': 0,
                    'attendance_rate_pct': 0,
                },
                'records': [],
            })
        conditions.append("ar.student_id = ?")
        args.append(student_row['id'])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY ar.attendance_date DESC, s.name ASC"

    records = dict_rows(db.execute(query, args).fetchall())

    present_count = sum(1 for record in records if record['status'] == 'present')
    absent_count = sum(1 for record in records if record['status'] == 'absent')
    total_count = len(records)
    rate = round((present_count / total_count) * 100, 2) if total_count else 0

    return jsonify({
        'summary': {
            'total_records': total_count,
            'present_count': present_count,
            'absent_count': absent_count,
            'attendance_rate_pct': rate,
        },
        'records': records,
    })


def _resolve_attendance_notification_user_id(db, attendance_student):
    """Resolve the student user account that should receive attendance notifications."""
    linked_user_id = attendance_student['linked_user_id']
    if linked_user_id:
        return linked_user_id

    registration_number = str(attendance_student['registration_number'] or '').strip()
    if not registration_number:
        return None

    user = db.execute(
        """
        SELECT id
        FROM users
        WHERE role = 'student' AND LOWER(username) = LOWER(?)
        LIMIT 1
        """,
        (registration_number,),
    ).fetchone()
    return user['id'] if user else None


def _notify_students_attendance_marked(db, attendance_student, attendance_date, status):
    user_id = _resolve_attendance_notification_user_id(db, attendance_student)
    if not user_id:
        return

    status_label = 'Present' if status == 'present' else 'Absent'
    message = (
        f"Attendance update: {attendance_student['name']} ({attendance_student['registration_number']}) "
        f"was marked {status_label} on {attendance_date}."
    )
    db.execute(
        """
        INSERT INTO notifications (user_type, user_id, message, is_read)
        VALUES (?, ?, ?, 0)
        """,
        ('student', user_id, message),
    )


def _resolve_attendance_student_for_current_user(db):
    """Resolve attendance profile for logged-in student user."""
    user_id = session.get('user_id')
    username = str(session.get('username', '')).strip()
    linked_id = session.get('linked_id')

    if user_id:
        row = db.execute(
            """
            SELECT id, name, registration_number
            FROM attendance_students
            WHERE is_active = 1 AND linked_user_id = ?
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        if row:
            return row

    if username:
        row = db.execute(
            """
            SELECT id, name, registration_number
            FROM attendance_students
            WHERE is_active = 1 AND LOWER(registration_number) = LOWER(?)
            LIMIT 1
            """,
            (username,),
        ).fetchone()
        if row:
            return row

    if linked_id is not None:
        try:
            sid = int(linked_id)
        except (TypeError, ValueError):
            sid = None
        if sid:
            row = db.execute(
                """
                SELECT id, name, registration_number
                FROM attendance_students
                WHERE is_active = 1 AND id = ?
                LIMIT 1
                """,
                (sid,),
            ).fetchone()
            if row:
                return row

    return None


def _notify_students_bulk_attendance_marked(db, attendance_date, status, students):
    for student in students:
        _notify_students_attendance_marked(db, student, attendance_date, status)


# Internal Helpers
def _load_scheduling_data(db):
    return {
        'semesters': dict_rows(db.execute("SELECT * FROM semesters").fetchall()),
        'subjects': dict_rows(db.execute("SELECT * FROM subjects").fetchall()),
        'faculty': dict_rows(db.execute("SELECT * FROM faculty").fetchall()),
        'faculty_subjects': dict_rows(db.execute("SELECT * FROM faculty_subjects").fetchall()),
        'classrooms': dict_rows(db.execute("SELECT * FROM classrooms WHERE is_active=1").fetchall()),
        'timeslots': dict_rows(db.execute("SELECT * FROM timeslots ORDER BY slot_number").fetchall()),
        'faculty_availability': dict_rows(db.execute("SELECT * FROM faculty_availability").fetchall()),
        'history': dict_rows(db.execute("SELECT * FROM timetable_history").fetchall()),
        'days': [0, 1, 2, 3, 4],
    }


def _get_next_version(db):
    row = db.execute("SELECT MAX(timetable_version) FROM timetable_entries").fetchone()
    return (row[0] or 0) + 1


def _save_timetable(db, schedule, version):
    for entry in schedule:
        db.execute("""
            INSERT INTO timetable_entries
            (timetable_version, semester_id, subject_id, faculty_id, classroom_id, day_of_week, timeslot_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (version, entry['semester_id'], entry['subject_id'], entry['faculty_id'],
              entry['classroom_id'], entry['day_of_week'], entry['timeslot_id']))
    db.commit()


def _log_generation(db, version, result):
    analytics = result.get('analytics', {})
    steps = result.get('steps', [])
    algo_names = ', '.join(s['name'] for s in steps)
    db.execute("""
        INSERT INTO generation_logs
        (timetable_version, algorithm_used, fitness_score, conflicts_resolved, generation_time_seconds)
        VALUES (?, ?, ?, ?, ?)
    """, (version, algo_names, analytics.get('fitness_score', 0),
          analytics.get('conflicts', 0), analytics.get('generation_time_seconds', 0)))
    db.commit()


def _notify_students_timetable_generated(db, version):
    student_users = db.execute(
        "SELECT id, linked_id FROM users WHERE role = 'student'"
    ).fetchall()
    for user in student_users:
        semester_suffix = f" for semester {user['linked_id']}" if user['linked_id'] else ""
        message = f"New timetable version {version} is available{semester_suffix}. Please check your dashboard."
        db.execute(
            """
            INSERT INTO notifications (user_type, user_id, message, is_read)
            VALUES (?, ?, ?, 0)
            """,
            ('student', user['id'], message),
        )
    db.commit()


# ─── Main ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    init_db()
    app.run(debug=True, port=5000)
