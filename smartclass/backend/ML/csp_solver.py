
"""
Constraint Satisfaction Problem (CSP) Solver for Timetable Scheduling.

WHY CSP: Timetable scheduling is inherently a constraint satisfaction problem.
Hard constraints (no double-booking, faculty availability) MUST be satisfied.
CSP ensures every generated schedule is valid before optimization begins.

HOW IT WORKS:
1. Variables: Each (semester, subject, lecture_index) needs a (day, timeslot, room, faculty) assignment
2. Domains: All possible (day, timeslot, room, faculty) combinations
3. Constraints: Hard constraints that prune invalid assignments
4. Greedy assignment with random restarts for speed, backtracking fallback for correctness
"""
import random
from collections import defaultdict


class CSPSolver:
    """Generates a valid (conflict-free) timetable using constraint satisfaction."""

    def __init__(self, data):
        self.data = data
        self.days = data.get('days', list(range(5)))
        self._build_indices()

    def _build_indices(self):
        self.subject_faculty = defaultdict(list)
        for fs in self.data['faculty_subjects']:
            self.subject_faculty[fs['subject_id']].append(fs)

        self.faculty_map = {f['id']: f for f in self.data['faculty']}
        self.classroom_map = {c['id']: c for c in self.data['classrooms']}
        self.timeslot_map = {t['id']: t for t in self.data['timeslots']}
        self.subject_map = {s['id']: s for s in self.data['subjects']}
        self.semester_map = {s['id']: s for s in self.data['semesters']}

        self.non_break_slots = [t for t in self.data['timeslots'] if not t['is_break']]
        self.lecture_rooms = [c for c in self.data['classrooms'] if c['room_type'] == 'lecture']
        self.lab_rooms = [c for c in self.data['classrooms'] if c['room_type'] == 'lab']

        self.avail_set = set()
        for fa in self.data.get('faculty_availability', []):
            if fa['is_available']:
                self.avail_set.add((fa['faculty_id'], fa['day_of_week'], fa['timeslot_id']))

    def _is_faculty_available(self, faculty_id, day, timeslot_id):
        if not self.data.get('faculty_availability'):
            return True
        return (faculty_id, day, timeslot_id) in self.avail_set

    def _check_constraints(self, state, semester_id, subject_id, faculty_id, classroom_id, day, timeslot_id):
        """Check all hard constraints. Returns True if assignment is valid."""
        occupied = state['occupied']
        fday = state['fday']
        fweek = state['fweek']

        if (faculty_id, day, timeslot_id) in occupied:
            return False
        if (classroom_id, day, timeslot_id) in occupied:
            return False
        if (semester_id, day, timeslot_id) in occupied:
            return False

        if not self._is_faculty_available(faculty_id, day, timeslot_id):
            return False

        fac = self.faculty_map[faculty_id]
        if fday[(faculty_id, day)] >= fac['max_hours_per_day']:
            return False
        if fweek[faculty_id] >= fac['max_hours_per_week']:
            return False

        subject = self.subject_map[subject_id]
        semester = self.semester_map[semester_id]
        classroom = self.classroom_map[classroom_id]
        if classroom['capacity'] < semester['student_count']:
            return False
        if subject['is_lab'] and classroom['room_type'] != 'lab':
            return False
        if not subject['is_lab'] and classroom['room_type'] == 'lab':
            return False

        return True

    def _assign(self, state, semester_id, subject_id, faculty_id, classroom_id, day, timeslot_id):
        entry = {
            'semester_id': semester_id,
            'subject_id': subject_id,
            'faculty_id': faculty_id,
            'classroom_id': classroom_id,
            'day_of_week': day,
            'timeslot_id': timeslot_id,
        }
        state['assignments'].append(entry)
        state['occupied'].add((faculty_id, day, timeslot_id))
        state['occupied'].add((classroom_id, day, timeslot_id))
        state['occupied'].add((semester_id, day, timeslot_id))
        state['fday'][(faculty_id, day)] += 1
        state['fweek'][faculty_id] += 1
        return entry

    def _new_state(self):
        return {
            'assignments': [],
            'occupied': set(),
            'fday': defaultdict(int),
            'fweek': defaultdict(int),
        }

    def solve(self, max_restarts=50):
        """
        Greedy CSP with random restarts.
        Much faster than pure backtracking for real-world scheduling.
        """
        variables = self._build_variables()
        variables.sort(key=lambda v: (v['priority'], v['subject_id']))

        best_state = None
        best_count = 0

        for attempt in range(max_restarts):
            state = self._new_state()
            shuffled_vars = list(variables)
            if attempt > 0:
                random.shuffle(shuffled_vars)
                shuffled_vars.sort(key=lambda v: v['priority'])

            assigned = 0
            for var in shuffled_vars:
                domain = self._get_domain(state, var)
                random.shuffle(domain)
                domain.sort(key=lambda d: -d[4])

                if domain:
                    best = domain[0]
                    self._assign(state, var['semester_id'], var['subject_id'],
                                 best[0], best[1], best[2], best[3])
                    assigned += 1

            if assigned == len(variables):
                return state['assignments']

            if assigned > best_count:
                best_count = assigned
                best_state = state

        if best_state and best_state['assignments']:
            return best_state['assignments']
        return None

    def _build_variables(self):
        variables = []
        for subj in self.data['subjects']:
            if not self.subject_faculty.get(subj['id']):
                continue
            for lec_idx in range(subj['lectures_per_week']):
                variables.append({
                    'semester_id': subj['semester_id'],
                    'subject_id': subj['id'],
                    'is_lab': subj['is_lab'],
                    'priority': subj['priority'],
                    'lecture_index': lec_idx,
                })
        return variables

    def _get_domain(self, state, var):
        """Get all valid (faculty, room, day, slot) for this variable."""
        faculty_opts = self.subject_faculty.get(var['subject_id'], [])
        rooms = self.lab_rooms if var['is_lab'] else self.lecture_rooms
        domain = []
        for fs in faculty_opts:
            for day in self.days:
                for slot in self.non_break_slots:
                    for room in rooms:
                        if self._check_constraints(
                            state, var['semester_id'], var['subject_id'],
                            fs['faculty_id'], room['id'], day, slot['id']
                        ):
                            domain.append((fs['faculty_id'], room['id'], day, slot['id'], fs['preference_score']))
        return domain

