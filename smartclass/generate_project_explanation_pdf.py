from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem


OUTPUT_FILE = "SmartClass_Project_Explanation.pdf"


def heading(text, styles):
    return Paragraph(text, styles["Heading2Custom"])


def body(text, styles):
    return Paragraph(text, styles["BodyCustom"])


def bullet_list(items, styles):
    return ListFlowable(
        [
            ListItem(Paragraph(item, styles["BodyCustom"]), leftIndent=8)
            for item in items
        ],
        bulletType="bullet",
        start="circle",
        leftIndent=18,
        bulletColor=colors.black,
    )


def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_FILE,
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title="SmartClass Project Explanation",
        author="SmartClass Team",
    )

    base_styles = getSampleStyleSheet()
    styles = {
        "TitleCustom": ParagraphStyle(
            "TitleCustom",
            parent=base_styles["Title"],
            fontSize=20,
            leading=24,
            spaceAfter=16,
            textColor=colors.HexColor("#0d1b2a"),
        ),
        "Heading2Custom": ParagraphStyle(
            "Heading2Custom",
            parent=base_styles["Heading2"],
            fontSize=13,
            leading=16,
            spaceBefore=8,
            spaceAfter=6,
            textColor=colors.HexColor("#1b263b"),
        ),
        "BodyCustom": ParagraphStyle(
            "BodyCustom",
            parent=base_styles["BodyText"],
            fontSize=10.5,
            leading=14,
            spaceAfter=5,
        ),
        "PitchCustom": ParagraphStyle(
            "PitchCustom",
            parent=base_styles["BodyText"],
            fontSize=10.5,
            leading=15,
            backColor=colors.HexColor("#f1f5f9"),
            borderColor=colors.HexColor("#cbd5e1"),
            borderWidth=0.7,
            borderPadding=8,
            borderRadius=3,
            spaceBefore=6,
            spaceAfter=8,
        ),
    }

    story = []
    story.append(Paragraph("SmartClass Project – Full Explanation", styles["TitleCustom"]))
    story.append(
        body(
            "SmartClass is an AI-assisted college timetable and classroom management system built using "
            "Flask, SQLite, and Python-based optimization modules. It automates timetable generation while "
            "supporting real college workflows like faculty preference handling, swap requests, attendance, "
            "and student notifications.",
            styles,
        )
    )
    story.append(Spacer(1, 4))

    story.append(heading("1) Problem Statement", styles))
    story.append(
        bullet_list(
            [
                "Manual timetable creation is complex and time-consuming.",
                "Multiple hard constraints must be satisfied: no clashes, room capacity, lab compatibility, faculty availability.",
                "Different stakeholders (admin, faculty, student) need role-specific views and actions.",
            ],
            styles,
        )
    )

    story.append(heading("2) Technology Stack", styles))
    story.append(
        bullet_list(
            [
                "Backend: Python Flask API (`backend/app.py`).",
                "Database: SQLite (`database/scheduler.db`) initialized via `schema.sql` and `seed_data.sql`.",
                "Frontend: Template-based pages (`dashboard.html`, `faculty.html`, `student.html`, `login.html`).",
                "ML/Optimization modules: CSP, Genetic Algorithm, Decision Tree, and KMeans.",
            ],
            styles,
        )
    )

    story.append(heading("3) Architecture Overview", styles))
    story.append(
        bullet_list(
            [
                "Data Layer: Academic entities, timetable versions, history, attendance, notifications, users.",
                "API Layer: CRUD and workflow endpoints for all roles.",
                "Scheduling Layer: `SchedulingPipeline` orchestrates ML + optimization.",
                "UI Layer: Role-based portals for admin, faculty, and students.",
            ],
            styles,
        )
    )

    story.append(heading("4) Role-Based Features", styles))
    story.append(
        bullet_list(
            [
                "Admin: Master-data management, timetable generation, analytics, swap approvals.",
                "Faculty: View personal schedule, submit swap requests, mark attendance.",
                "Student: View timetable, attendance records, and notifications.",
            ],
            styles,
        )
    )

    story.append(heading("5) Scheduling Intelligence Pipeline", styles))
    story.append(body("The scheduler follows a hybrid 4-stage flow:", styles))
    story.append(
        bullet_list(
            [
                "Data Loading: Collects semesters, subjects, faculty, classrooms, time slots, mappings, history, and availability.",
                "Pattern Learning (Decision Tree): Learns useful slot patterns from historical/synthetic data.",
                "Room Clustering (KMeans): Groups rooms by utilization patterns to support better allocation decisions.",
                "CSP Solver: Produces a valid conflict-free timetable by satisfying hard constraints first.",
                "Genetic Algorithm: Optimizes the valid timetable for quality (preferences, balance, fewer gaps, better distribution).",
            ],
            styles,
        )
    )

    story.append(heading("6) Why CSP + GA Together?", styles))
    story.append(
        bullet_list(
            [
                "CSP ensures correctness and feasibility.",
                "GA improves quality once a feasible base schedule exists.",
                "This combination is practical and robust for real timetable systems.",
            ],
            styles,
        )
    )

    story.append(heading("7) Database Design Highlights", styles))
    story.append(
        bullet_list(
            [
                "Core tables: departments, courses, semesters, subjects, faculty, faculty_subjects, classrooms, timeslots.",
                "Operational tables: timetable_entries (versioned), swap_requests, notifications.",
                "Learning/analytics tables: timetable_history, generation_logs.",
                "Attendance tables: attendance_students, attendance_records.",
                "Access control table: users with role and linked_id mapping.",
            ],
            styles,
        )
    )

    story.append(heading("8) Key API Groups", styles))
    story.append(
        bullet_list(
            [
                "Authentication APIs (`/api/login`, `/api/logout`).",
                "Master-data CRUD APIs (departments, courses, subjects, faculty, classrooms, etc.).",
                "Timetable APIs (`/api/generate`, `/api/timetable`, `/api/timetable/versions`).",
                "Swap APIs for faculty and admin approvals.",
                "Analytics APIs for workload, room utilization, and overview.",
                "Attendance + notifications APIs for daily operations.",
            ],
            styles,
        )
    )

    story.append(heading("9) End-to-End User Flow", styles))
    story.append(
        bullet_list(
            [
                "Admin logs in and configures academic/resource data.",
                "Admin triggers generation; pipeline creates and optimizes timetable.",
                "System stores a new timetable version and logs metrics.",
                "Faculty views assigned schedule and can request swaps.",
                "Faculty marks attendance; students receive updates and see attendance rate.",
            ],
            styles,
        )
    )

    story.append(heading("10) Strengths", styles))
    story.append(
        bullet_list(
            [
                "Conflict-free scheduling with optimization-based quality improvements.",
                "Role-driven real workflows beyond simple timetable generation.",
                "Versioning and logs for traceability and analytics.",
                "Integrated attendance and communication module.",
            ],
            styles,
        )
    )

    story.append(heading("11) Current Limitations", styles))
    story.append(
        bullet_list(
            [
                "Demo-level authentication; password handling should be hardened.",
                "SQLite suits prototypes/small deployment but has scale limits.",
                "Model quality depends on historical data quality and quantity.",
                "Advanced explainability/report export can be further improved.",
            ],
            styles,
        )
    )

    story.append(heading("12) Future Improvements", styles))
    story.append(
        bullet_list(
            [
                "Use secure hashing/JWT and production-grade auth practices.",
                "Add export formats (PDF/Excel/calendar), richer dashboards, and explainable recommendations.",
                "Allow manual lock constraints and interactive conflict resolution.",
                "Move to PostgreSQL and background workers for larger institutions.",
            ],
            styles,
        )
    )

    story.append(heading("One-Minute Pitch", styles))
    story.append(
        Paragraph(
            "SmartClass is an intelligent academic scheduling platform that automates timetable generation "
            "using a hybrid CSP + Genetic Algorithm engine, enhanced with machine learning for pattern "
            "learning and room utilization insights. It handles not only schedule generation but also real "
            "institutional workflows such as faculty swap requests, attendance tracking, analytics, and "
            "student notifications through role-based portals.",
            styles["PitchCustom"],
        )
    )

    doc.build(story)


if __name__ == "__main__":
    build_pdf()
