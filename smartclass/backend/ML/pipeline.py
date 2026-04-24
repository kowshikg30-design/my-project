
"""
ML Pipeline Orchestrator - Coordinates all ML components.

DATA FLOW:
1. Load data from database
2. (Optional) Train Decision Tree on historical data -> get slot suggestions
3. (Optional) Run Clustering on past timetable -> get room priorities
4. Run CSP Solver -> generate valid timetable
5. Run Genetic Algorithm -> optimize the timetable
6. Store results + update historical data
7. Return optimized schedule with analytics
"""
import time
from .csp_solver import CSPSolver
from .genetic_algorithm import GeneticScheduler
from .decision_tree import TimetablePatternLearner, generate_synthetic_history
from .clustering import ClassroomAnalyzer


class SchedulingPipeline:
    """End-to-end ML pipeline for timetable generation."""

    def __init__(self, data):
        self.data = data
        self.pattern_learner = TimetablePatternLearner()
        self.room_analyzer = ClassroomAnalyzer()
        self.results = {}

    def run(self, use_ml=True, ga_generations=80, ga_population=25):
        """
        Execute the full scheduling pipeline.
        Returns dict with schedule, analytics, and ML insights.
        """
        pipeline_start = time.time()
        self.results = {
            'status': 'running',
            'steps': [],
            'ml_insights': {},
        }

        # Step 1: Train pattern learner on historical/synthetic data
        if use_ml:
            self._step_train_pattern_learner()
            self._step_cluster_rooms()

        # Step 2: CSP - Generate valid timetable
        csp_result = self._step_csp_solve()
        if csp_result is None:
            self.results['status'] = 'failed'
            self.results['error'] = 'CSP solver could not find a valid schedule'
            return self.results

        # Step 3: GA - Optimize the timetable
        optimized, fitness, ga_stats = self._step_ga_optimize(csp_result, ga_generations, ga_population)

        total_time = round(time.time() - pipeline_start, 2)

        self.results['status'] = 'success'
        self.results['schedule'] = optimized
        self.results['analytics'] = {
            'total_entries': len(optimized),
            'fitness_score': round(fitness, 2),
            'conflicts': ga_stats['final_conflicts'],
            'ga_generations': ga_stats['generations'],
            'generation_time_seconds': total_time,
        }
        self.results['fitness_history'] = ga_stats.get('fitness_history', [])

        return self.results

    def _step_train_pattern_learner(self):
        step_start = time.time()
        try:
            subjects_map = {s['id']: s for s in self.data['subjects']}
            semesters_map = {s['id']: s for s in self.data['semesters']}
            classrooms_map = {c['id']: c for c in self.data['classrooms']}

            history = self.data.get('history', [])
            if len(history) < 10:
                history = generate_synthetic_history(
                    self.data['subjects'], self.data['semesters'],
                    self.data['faculty_subjects'], self.data['classrooms'],
                    self.data['timeslots'], n_records=500
                )

            train_result = self.pattern_learner.train(history, subjects_map, semesters_map, classrooms_map)
            self.results['ml_insights']['pattern_learner'] = train_result
            self.results['ml_insights']['feature_importance'] = self.pattern_learner.get_feature_importance()
        except Exception as e:
            train_result = {'status': 'error', 'message': str(e)}

        self.results['steps'].append({
            'name': 'Pattern Learning (Decision Tree)',
            'duration': round(time.time() - step_start, 3),
            'result': train_result.get('status', 'unknown'),
        })

    def _step_cluster_rooms(self):
        step_start = time.time()
        try:
            history = self.data.get('history', [])
            if history:
                room_features = self.room_analyzer.compute_room_features(
                    history, self.data['classrooms'], self.data['semesters']
                )
                cluster_result = self.room_analyzer.fit(room_features)
                self.results['ml_insights']['room_clusters'] = cluster_result
            else:
                cluster_result = {'status': 'skipped', 'message': 'No historical data'}
        except Exception as e:
            cluster_result = {'status': 'error', 'message': str(e)}

        self.results['steps'].append({
            'name': 'Room Clustering (K-Means)',
            'duration': round(time.time() - step_start, 3),
            'result': cluster_result.get('status', 'unknown'),
        })

    def _step_csp_solve(self):
        step_start = time.time()
        try:
            solver = CSPSolver(self.data)
            solution = solver.solve()
            status = 'success' if solution else 'failed'
        except Exception as e:
            solution = None
            status = f'error: {str(e)}'

        self.results['steps'].append({
            'name': 'CSP Solver (Constraint Satisfaction)',
            'duration': round(time.time() - step_start, 3),
            'result': status,
            'entries': len(solution) if solution else 0,
        })
        return solution

    def _step_ga_optimize(self, csp_solution, generations, population):
        step_start = time.time()
        try:
            ga = GeneticScheduler(
                self.data, csp_solution,
                population_size=population,
                generations=generations,
            )
            optimized, fitness, stats = ga.evolve()
            status = 'success'
        except Exception as e:
            optimized = csp_solution
            fitness = 0
            stats = {'generations': 0, 'final_conflicts': -1, 'fitness_history': []}
            status = f'error: {str(e)}'

        self.results['steps'].append({
            'name': 'Genetic Algorithm (Optimization)',
            'duration': round(time.time() - step_start, 3),
            'result': status,
        })
        return optimized, fitness, stats
