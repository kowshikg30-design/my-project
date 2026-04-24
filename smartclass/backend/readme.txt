```
# Smart Classroom Timetable Scheduler Using Machine Learning

An intelligent system that automatically generates optimized, conflict-free academic timetables using machine learning and constraint-based optimization.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
cd backend
python app.py
```

Open http://localhost:5000 in your browser.
**Default logins:** `admin` / `admin123`, `faculty1` / `faculty123`, `faculty2` / `faculty123`, `faculty3` / `faculty123`, `student1` / `student123`, `student2` / `student123`, `student3` / `student123`
New faculty logins:

faculty1 / faculty123
faculty2 / faculty123
faculty3 / faculty123
New student logins:

student1 / student123
student2 / student123
student3 / student123
## Project Structure

```
Yogi/
├── backend/
│   ├── app.py                  # Flask application (REST API + routes)
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── csp_solver.py       # Constraint Satisfaction Problem solver
│   │   ├── genetic_algorithm.py # Genetic Algorithm optimizer
│   │   ├── decision_tree.py    # Pattern learning from historical data
│   │   ├── clustering.py       # K-Means classroom utilization analysis
│   │   └── pipeline.py         # ML Pipeline orchestrator
│   ├── templates/
│   │   ├── login.html          # Login page
│   │   ├── dashboard.html      # Admin dashboard
│   │   ├── faculty.html        # Faculty portal
│   │   └── student.html        # Student portal
│   └── static/
│       ├── css/style.css       # Application styles
│       └── js/app.js           # Frontend JavaScript
├── database/
│   ├── schema.sql              # Database schema
│   ├── seed_data.sql           # Sample data
│   └── scheduler.db            # SQLite database (auto-created)
├── docs/
│   └── PROJECT_REPORT.md       # Full project documentation
├── requirements.txt
└── README.md
```

## ML Algorithms Used

| Algorithm | Purpose |
|-----------|---------|
| CSP (Constraint Satisfaction) | Generates valid, conflict-free schedules |
| Genetic Algorithm | Optimizes schedule quality (preferences, balance) |
| Decision Tree | Learns optimal patterns from historical data |
| K-Means Clustering | Analyzes classroom utilization patterns |

## Tech Stack

- **Backend:** Python Flask
- **Frontend:** HTML5, CSS3, JavaScript (vanilla)
- **Database:** SQLite (SQL Server compatible schema)
- **ML:** scikit-learn, NumPy

```
