
"""
K-Means Clustering for Classroom Utilization Analysis.

WHY CLUSTERING:
- Groups classrooms by usage patterns to identify underutilized rooms
- Helps predict which rooms are best suited for which types of classes
- Informs room allocation decisions in the scheduling pipeline

HOW IT INTERACTS:
Timetable data -> Usage statistics per room -> K-Means clusters
-> Labels: 'high_usage', 'medium_usage', 'low_usage'
-> Room selection priority in CSP/GA uses cluster labels

DATA FLOW:
1. Aggregate room usage from timetable entries
2. Features: occupancy_rate, avg_class_size_ratio, variety_of_subjects, time_spread
3. K-Means groups rooms into usage tiers
4. Scheduler prioritizes underutilized rooms to balance load
"""
import numpy as np
from collections import defaultdict

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class ClassroomAnalyzer:
    """Analyzes classroom utilization patterns using K-Means clustering."""

    def __init__(self, n_clusters=3):
        self.n_clusters = n_clusters
        self.model = None
        self.scaler = None
        self.labels = {}
        self.cluster_names = {0: 'low_usage', 1: 'medium_usage', 2: 'high_usage'}
        self.is_fitted = False

    def compute_room_features(self, timetable_entries, classrooms, semesters, total_slots_per_week=30):
        """
        Compute utilization features for each classroom.
        Features:
        1. occupancy_rate: fraction of total available slots used
        2. avg_capacity_ratio: avg(class_size / room_capacity)
        3. subject_variety: number of distinct subjects taught
        4. day_spread: number of distinct days room is used
        5. peak_hour_usage: fraction of classes in morning slots (1-5)
        """
        room_stats = {}
        classroom_map = {c['id']: c for c in classrooms}
        semester_map = {s['id']: s for s in semesters}

        room_entries = defaultdict(list)
        for entry in timetable_entries:
            room_entries[entry['classroom_id']].append(entry)

        for room in classrooms:
            entries = room_entries.get(room['id'], [])
            n_entries = len(entries)

            occupancy_rate = n_entries / total_slots_per_week if total_slots_per_week > 0 else 0

            capacity_ratios = []
            for e in entries:
                sem = semester_map.get(e['semester_id'], {})
                ratio = sem.get('student_count', 0) / room['capacity'] if room['capacity'] > 0 else 0
                capacity_ratios.append(ratio)
            avg_capacity_ratio = np.mean(capacity_ratios) if capacity_ratios else 0

            subjects = set(e['subject_id'] for e in entries)
            subject_variety = len(subjects) / max(n_entries, 1)

            days = set(e['day_of_week'] for e in entries)
            day_spread = len(days) / 5.0

            morning_count = sum(1 for e in entries if e['timeslot_id'] <= 5)
            peak_usage = morning_count / max(n_entries, 1)

            room_stats[room['id']] = {
                'room_id': room['id'],
                'room_name': room['name'],
                'features': [occupancy_rate, avg_capacity_ratio, subject_variety, day_spread, peak_usage],
                'raw': {
                    'total_classes': n_entries,
                    'occupancy_rate': round(occupancy_rate, 3),
                    'avg_capacity_ratio': round(float(avg_capacity_ratio), 3),
                    'unique_subjects': len(subjects),
                    'days_used': len(days),
                }
            }

        return room_stats

    def fit(self, room_stats):
        """Fit K-Means on room features."""
        if not SKLEARN_AVAILABLE:
            return {'status': 'error', 'message': 'scikit-learn not installed'}

        if len(room_stats) < self.n_clusters:
            return {'status': 'error', 'message': f'Need at least {self.n_clusters} rooms'}

        room_ids = list(room_stats.keys())
        X = np.array([room_stats[rid]['features'] for rid in room_ids])

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.model = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        self.model.fit(X_scaled)

        cluster_occupancy = defaultdict(list)
        for i, rid in enumerate(room_ids):
            cluster_occupancy[self.model.labels_[i]].append(room_stats[rid]['features'][0])

        avg_occ = {c: np.mean(occs) for c, occs in cluster_occupancy.items()}
        sorted_clusters = sorted(avg_occ.keys(), key=lambda c: avg_occ[c])
        label_map = {}
        names = ['low_usage', 'medium_usage', 'high_usage']
        for i, c in enumerate(sorted_clusters):
            label_map[c] = names[min(i, len(names) - 1)]

        self.labels = {}
        for i, rid in enumerate(room_ids):
            self.labels[rid] = label_map[self.model.labels_[i]]

        self.is_fitted = True

        return {
            'status': 'success',
            'clusters': {
                rid: {
                    'cluster': self.labels[rid],
                    **room_stats[rid]['raw']
                }
                for rid in room_ids
            },
            'inertia': round(float(self.model.inertia_), 4),
        }

    def get_room_priority(self, room_id):
        """Get scheduling priority for a room (lower = schedule first)."""
        if not self.is_fitted:
            return 2
        label = self.labels.get(room_id, 'medium_usage')
        return {'low_usage': 1, 'medium_usage': 2, 'high_usage': 3}.get(label, 2)

    def get_utilization_report(self):
        """Generate a utilization summary report."""
        if not self.is_fitted:
            return {'status': 'not_fitted'}

        report = defaultdict(list)
        for rid, label in self.labels.items():
            report[label].append(rid)

        return dict(report)

