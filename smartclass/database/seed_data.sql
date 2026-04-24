-- ============================================================
-- Sample Seed Data for Smart Classroom Timetable Scheduler
-- ============================================================

-- Time Slots (8 slots per day)
INSERT INTO timeslots (slot_number, start_time, end_time, is_break, label) VALUES
(1, '09:00', '09:50', 0, 'Period 1'),
(2, '09:50', '10:40', 0, 'Period 2'),
(3, '10:40', '11:00', 1, 'Morning Break'),
(4, '11:00', '11:50', 0, 'Period 3'),
(5, '11:50', '12:40', 0, 'Period 4'),
(6, '12:40', '13:30', 1, 'Lunch Break'),
(7, '13:30', '14:20', 0, 'Period 5'),
(8, '14:20', '15:10', 0, 'Period 6');

-- Departments
INSERT INTO departments (name, code, head_of_department) VALUES
('Computer Science', 'CS', 'Dr. Sharma'),
('Electronics', 'EC', 'Dr. Patel'),
('Mechanical', 'ME', 'Dr. Singh'),
('Mathematics', 'MATH', 'Dr. Gupta');

-- Courses
INSERT INTO courses (name, code, department_id, semester_count) VALUES
('B.Tech Computer Science', 'BTCS', 1, 8),
('B.Tech Electronics', 'BTEC', 2, 8),
('B.Tech Mechanical', 'BTME', 3, 8);

-- Semesters (current academic year)
INSERT INTO semesters (course_id, semester_number, academic_year, student_count) VALUES
(1, 3, '2025-26', 60),
(1, 5, '2025-26', 55),
(2, 3, '2025-26', 50),
(2, 5, '2025-26', 45),
(3, 3, '2025-26', 40),
(3, 5, '2025-26', 35);

-- Subjects (CS Sem 3)
INSERT INTO subjects (name, code, semester_id, lectures_per_week, is_lab, priority) VALUES
('Data Structures', 'CS301', 1, 4, 0, 2),
('Database Management', 'CS302', 1, 3, 0, 3),
('Computer Networks', 'CS303', 1, 3, 0, 4),
('Operating Systems', 'CS304', 1, 3, 0, 3),
('DS Lab', 'CS305', 1, 2, 1, 2),
('DBMS Lab', 'CS306', 1, 2, 1, 3);

-- Subjects (CS Sem 5)
INSERT INTO subjects (name, code, semester_id, lectures_per_week, is_lab, priority) VALUES
('Machine Learning', 'CS501', 2, 4, 0, 1),
('Software Engineering', 'CS502', 2, 3, 0, 3),
('Compiler Design', 'CS503', 2, 3, 0, 4),
('Web Technologies', 'CS504', 2, 3, 0, 5),
('ML Lab', 'CS505', 2, 2, 1, 1),
('Web Lab', 'CS506', 2, 2, 1, 5);

-- Subjects (EC Sem 3)
INSERT INTO subjects (name, code, semester_id, lectures_per_week, is_lab, priority) VALUES
('Digital Electronics', 'EC301', 3, 4, 0, 2),
('Signals & Systems', 'EC302', 3, 3, 0, 3),
('Circuit Theory', 'EC303', 3, 3, 0, 4),
('Electronics Lab', 'EC304', 3, 2, 1, 2);

-- Subjects (EC Sem 5)
INSERT INTO subjects (name, code, semester_id, lectures_per_week, is_lab, priority) VALUES
('VLSI Design', 'EC501', 4, 3, 0, 2),
('Microprocessors', 'EC502', 4, 4, 0, 3),
('Communication Systems', 'EC503', 4, 3, 0, 4),
('VLSI Lab', 'EC504', 4, 2, 1, 2);

-- Subjects (ME Sem 3)
INSERT INTO subjects (name, code, semester_id, lectures_per_week, is_lab, priority) VALUES
('Thermodynamics', 'ME301', 5, 4, 0, 2),
('Fluid Mechanics', 'ME302', 5, 3, 0, 3),
('Strength of Materials', 'ME303', 5, 3, 0, 3),
('Workshop Lab', 'ME304', 5, 2, 1, 2);

-- Subjects (ME Sem 5)
INSERT INTO subjects (name, code, semester_id, lectures_per_week, is_lab, priority) VALUES
('Heat Transfer', 'ME501', 6, 3, 0, 2),
('CAD/CAM', 'ME502', 6, 3, 0, 3),
('Manufacturing', 'ME503', 6, 4, 0, 4),
('CAD Lab', 'ME504', 6, 2, 1, 3);

-- Classrooms
INSERT INTO classrooms (name, building, floor, capacity, room_type, has_projector, has_ac) VALUES
('LH-101', 'Main Block', 1, 80, 'lecture', 1, 1),
('LH-102', 'Main Block', 1, 60, 'lecture', 1, 0),
('LH-201', 'Main Block', 2, 70, 'lecture', 1, 1),
('LH-202', 'Main Block', 2, 50, 'lecture', 1, 0),
('LH-301', 'Main Block', 3, 40, 'lecture', 0, 0),
('CS-LAB-1', 'CS Block', 1, 40, 'lab', 1, 1),
('CS-LAB-2', 'CS Block', 1, 35, 'lab', 1, 1),
('EC-LAB-1', 'EC Block', 1, 40, 'lab', 1, 0),
('ME-WORKSHOP', 'Workshop', 0, 30, 'lab', 0, 0),
('SEMINAR-1', 'Main Block', 3, 100, 'seminar', 1, 1);

-- Faculty
INSERT INTO faculty (name, email, department_id, designation, max_hours_per_day, max_hours_per_week) VALUES
('Dr. Anand Kumar', 'anand@univ.edu', 1, 'Professor', 5, 20),
('Prof. Neha Verma', 'neha@univ.edu', 1, 'Asst. Professor', 6, 24),
('Dr. Rajesh Iyer', 'rajesh@univ.edu', 1, 'Assoc. Professor', 5, 22),
('Prof. Priya Nair', 'priya@univ.edu', 1, 'Asst. Professor', 6, 24),
('Dr. Suresh Menon', 'suresh@univ.edu', 2, 'Professor', 5, 20),
('Prof. Kavita Joshi', 'kavita@univ.edu', 2, 'Asst. Professor', 6, 24),
('Dr. Arun Pillai', 'arun@univ.edu', 2, 'Assoc. Professor', 5, 22),
('Dr. Mohan Das', 'mohan@univ.edu', 3, 'Professor', 5, 20),
('Prof. Reena Shah', 'reena@univ.edu', 3, 'Asst. Professor', 6, 24),
('Dr. Vikram Rao', 'vikram@univ.edu', 3, 'Assoc. Professor', 5, 22),
('Prof. Sanjay Mishra', 'sanjay@univ.edu', 4, 'Asst. Professor', 6, 24);

-- Faculty-Subject Mappings
INSERT INTO faculty_subjects (faculty_id, subject_id, preference_score) VALUES
(1, 1, 9), (1, 5, 7),    -- Dr. Anand -> DS, DS Lab
(2, 2, 8), (2, 6, 7),    -- Prof. Neha -> DBMS, DBMS Lab
(3, 3, 9), (3, 4, 8),    -- Dr. Rajesh -> CN, OS
(4, 7, 9), (4, 11, 8),   -- Prof. Priya -> ML, ML Lab
(4, 8, 7),               -- Prof. Priya -> SE
(1, 9, 6),               -- Dr. Anand -> Compiler Design
(2, 10, 7), (2, 12, 6),  -- Prof. Neha -> Web Tech, Web Lab
(5, 13, 9), (5, 16, 7),  -- Dr. Suresh -> Digital Electronics, EC Lab
(6, 14, 8),              -- Prof. Kavita -> Signals
(7, 15, 8),              -- Dr. Arun -> Circuit Theory
(5, 17, 8),              -- Dr. Suresh -> VLSI
(6, 18, 9), (6, 20, 7),  -- Prof. Kavita -> Microprocessors, VLSI Lab
(7, 19, 8),              -- Dr. Arun -> Comm Systems
(8, 21, 9), (8, 24, 7),  -- Dr. Mohan -> Thermo, Workshop
(9, 22, 8),              -- Prof. Reena -> Fluid Mechanics
(10, 23, 9),             -- Dr. Vikram -> SOM
(8, 25, 7),              -- Dr. Mohan -> Heat Transfer
(9, 26, 8), (9, 28, 7),  -- Prof. Reena -> CAD/CAM, CAD Lab
(10, 27, 9);             -- Dr. Vikram -> Manufacturing

-- Admin user
INSERT INTO users (username, password_hash, role) VALUES
('admin', 'admin123', 'admin');

-- Additional faculty users
INSERT INTO users (username, password_hash, role, linked_id) VALUES
('faculty4', 'faculty123', 'faculty', 4),
('faculty5', 'faculty123', 'faculty', 5),
('faculty6', 'faculty123', 'faculty', 6),
('faculty7', 'faculty123', 'faculty', 7);
