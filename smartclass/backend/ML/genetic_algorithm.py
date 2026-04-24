
"""
Genetic Algorithm (GA) for Timetable Optimization.

WHY GA: After CSP generates a valid schedule, GA optimizes it for quality:
- Minimizing gaps in student schedules
- Balancing faculty workload across days
- Honoring faculty preferences for time slots
- Distributing subjects evenly across the week

HOW IT INTERACTS WITH CSP:
CSP output -> Initial population seed for GA -> GA evolves better schedules

DATA FLOW:
1. CSP provides feasible solutions (valid chromosomes)
2. GA creates population of valid timetables
3. Fitness function evaluates each timetable
4. Selection, crossover, mutation produce new generations
5. Best individual after N generations is the optimized timetable
"""
import random
import copy
from collections import defaultdict


class GeneticScheduler:
    """Optimizes a valid timetable using evolutionary computation."""

    def __init__(self, data, csp_solution, population_size=30, generations=100,
                 crossover_rate=0.8, mutation_rate=0.15, elite_count=3):
        self.data = data
        self.base_solution = csp_solution
        self.population_size = population_size
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.elite_count = elite_count

        self.days = data.get('days', list(range(5)))
        self.non_break_slots = [t for t in data['timeslots'] if not t['is_break']]
        self.lecture_rooms = [c for c in data['classrooms'] if c['room_type'] == 'lecture']
        self.lab_rooms = [c for c in data['classrooms'] if c['room_type'] == 'lab']
        self.subject_map = {s['id']: s for s in data['subjects']}
        self.faculty_map = {f['id']: f for f in data['faculty']}
        self.semester_map = {s['id']: s for s in data['semesters']}
        self.classroom_map = {c['id']: c for c in data['classrooms']}

        self.subject_faculty = defaultdict(list)
        for fs in data['faculty_subjects']:
            self.subject_faculty[fs['subject_id']].append(fs)

        self.best_fitness_history = []

    def _create_individual(self, base):
        """Create a slightly mutated copy of the base solution."""
        individual = copy.deepcopy(base)
        for _ in range(random.randint(1, 5)):
            self._mutate_entry(individual)
        return individual

    def _initialize_population(self):
        population = [copy.deepcopy(self.base_solution)]
        for _ in range(self.population_size - 1):
            population.append(self._create_individual(self.base_solution))
        return population

    def fitness(self, schedule):
        """
        Multi-objective fitness function (higher is better).
        Components:
        1. Conflict penalty (hard constraint violations)
        2. Faculty preference satisfaction
        3. Workload balance across days
        4. Gap minimization for students
        5. Subject distribution across week
        """
        score = 1000.0

        conflict_penalty = self._count_conflicts(schedule) * 100
        score -= conflict_penalty

        pref_score = self._faculty_preference_score(schedule)
        score += pref_score * 2

        balance_score = self._workload_balance_score(schedule)
        score += balance_score * 3

        gap_penalty = self._student_gap_penalty(schedule)
        score -= gap_penalty * 1.5

        dist_score = self._subject_distribution_score(schedule)
        score += dist_score * 2

        return max(score, 0)

    def _count_conflicts(self, schedule):
        conflicts = 0
        seen_faculty = set()
        seen_room = set()
        seen_semester = set()

        for entry in schedule:
            fkey = (entry['faculty_id'], entry['day_of_week'], entry['timeslot_id'])
            rkey = (entry['classroom_id'], entry['day_of_week'], entry['timeslot_id'])
            skey = (entry['semester_id'], entry['day_of_week'], entry['timeslot_id'])

            if fkey in seen_faculty:
                conflicts += 1
            seen_faculty.add(fkey)

            if rkey in seen_room:
                conflicts += 1
            seen_room.add(rkey)

            if skey in seen_semester:
                conflicts += 1
            seen_semester.add(skey)

        return conflicts

    def _faculty_preference_score(self, schedule):
        total = 0
        for entry in schedule:
            for fs in self.subject_faculty.get(entry['subject_id'], []):
                if fs['faculty_id'] == entry['faculty_id']:
                    total += fs['preference_score']
                    break
        return total

    def _workload_balance_score(self, schedule):
        faculty_days = defaultdict(lambda: defaultdict(int))
        for entry in schedule:
            faculty_days[entry['faculty_id']][entry['day_of_week']] += 1

        total_variance = 0
        for fid, days in faculty_days.items():
            counts = [days.get(d, 0) for d in self.days]
            mean = sum(counts) / len(counts)
            variance = sum((c - mean) ** 2 for c in counts) / len(counts)
            total_variance += variance

        max_possible = len(faculty_days) * 10
        return max(0, max_possible - total_variance * 5)

    def _student_gap_penalty(self, schedule):
        semester_day_slots = defaultdict(list)
        for entry in schedule:
            key = (entry['semester_id'], entry['day_of_week'])
            semester_day_slots[key].append(entry['timeslot_id'])

        total_gaps = 0
        for key, slots in semester_day_slots.items():
            slots.sort()
            for i in range(1, len(slots)):
                gap = slots[i] - slots[i - 1] - 1
                if gap > 0:
                    slot_a = self.data['timeslots'][slots[i - 1] - 1] if slots[i - 1] <= len(self.data['timeslots']) else None
                    slot_b = self.data['timeslots'][slots[i] - 1] if slots[i] <= len(self.data['timeslots']) else None
                    if slot_a and slot_b and not slot_a.get('is_break') and not slot_b.get('is_break'):
                        total_gaps += gap
        return total_gaps

    def _subject_distribution_score(self, schedule):
        """Reward spreading same subject across different days."""
        subject_days = defaultdict(set)
        for entry in schedule:
            subject_days[(entry['semester_id'], entry['subject_id'])].add(entry['day_of_week'])

        score = 0
        for key, days in subject_days.items():
            subj = self.subject_map.get(key[1])
            if subj:
                expected = min(subj['lectures_per_week'], 5)
                score += min(len(days), expected)
        return score

    def _mutate_entry(self, schedule):
        if not schedule:
            return
        idx = random.randint(0, len(schedule) - 1)
        entry = schedule[idx]

        mutation_type = random.choice(['swap_time', 'swap_room', 'swap_day'])

        if mutation_type == 'swap_time':
            new_slot = random.choice(self.non_break_slots)
            entry['timeslot_id'] = new_slot['id']
        elif mutation_type == 'swap_room':
            subj = self.subject_map.get(entry['subject_id'], {})
            rooms = self.lab_rooms if subj.get('is_lab') else self.lecture_rooms
            if rooms:
                sem = self.semester_map.get(entry['semester_id'], {})
                valid_rooms = [r for r in rooms if r['capacity'] >= sem.get('student_count', 0)]
                if valid_rooms:
                    entry['classroom_id'] = random.choice(valid_rooms)['id']
        elif mutation_type == 'swap_day':
            entry['day_of_week'] = random.choice(self.days)

    def _crossover(self, parent1, parent2):
        """Single-point crossover preserving semester groupings."""
        if random.random() > self.crossover_rate:
            return copy.deepcopy(parent1), copy.deepcopy(parent2)

        semesters = list(set(e['semester_id'] for e in parent1))
        if len(semesters) < 2:
            return copy.deepcopy(parent1), copy.deepcopy(parent2)

        split = random.randint(1, len(semesters) - 1)
        set_a = set(semesters[:split])

        child1 = [copy.deepcopy(e) for e in parent1 if e['semester_id'] in set_a] + \
                 [copy.deepcopy(e) for e in parent2 if e['semester_id'] not in set_a]
        child2 = [copy.deepcopy(e) for e in parent2 if e['semester_id'] in set_a] + \
                 [copy.deepcopy(e) for e in parent1 if e['semester_id'] not in set_a]

        return child1, child2

    def _select(self, population, fitnesses):
        """Tournament selection."""
        tournament_size = 3
        selected = []
        for _ in range(2):
            candidates = random.sample(list(zip(population, fitnesses)), min(tournament_size, len(population)))
            winner = max(candidates, key=lambda x: x[1])
            selected.append(winner[0])
        return selected

    def evolve(self):
        """Run the genetic algorithm. Returns (best_schedule, best_fitness, history)."""
        population = self._initialize_population()
        best_overall = None
        best_fitness = -1

        for gen in range(self.generations):
            fitnesses = [self.fitness(ind) for ind in population]

            paired = list(zip(population, fitnesses))
            paired.sort(key=lambda x: -x[1])

            if paired[0][1] > best_fitness:
                best_fitness = paired[0][1]
                best_overall = copy.deepcopy(paired[0][0])

            self.best_fitness_history.append(best_fitness)

            next_gen = [copy.deepcopy(p[0]) for p in paired[:self.elite_count]]

            while len(next_gen) < self.population_size:
                parents = self._select(population, fitnesses)
                child1, child2 = self._crossover(parents[0], parents[1])

                if random.random() < self.mutation_rate:
                    self._mutate_entry(child1)
                if random.random() < self.mutation_rate:
                    self._mutate_entry(child2)

                next_gen.extend([child1, child2])

            population = next_gen[:self.population_size]

        conflicts = self._count_conflicts(best_overall) if best_overall else -1
        return best_overall, best_fitness, {
            'generations': self.generations,
            'final_conflicts': conflicts,
            'fitness_history': self.best_fitness_history
        }
