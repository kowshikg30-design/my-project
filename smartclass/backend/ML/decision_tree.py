
"""
Decision Tree for Pattern Learning from Historical Timetable Data.

WHY DECISION TREE:
- Learns which time-slot + room + faculty combinations historically
  produced the best outcomes (high fitness, low conflicts, good feedback).
- Interpretable: administrators can understand WHY certain slots are preferred.
- Fast inference for real-time slot suggestions.

HOW IT INTERACTS:
Historical data -> Feature extraction -> Decision Tree training
-> Predicts optimal (day, timeslot) for new subject-faculty pairs
-> Suggestions fed as preferences into CSP/GA pipeline.

DATA FLOW:
1. Extract features from timetable_history table
2. Target: fitness_score or student_feedback_score
3. Train DecisionTreeRegressor
4. Predict best slots for upcoming scheduling
"""
import numpy as np
from collections import defaultdict

try:
    from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class TimetablePatternLearner:
    """Learns scheduling patterns from historical data using Decision Trees."""

    def __init__(self):
        self.regressor = None
        self.classifier = None
        self.feature_names = [
            'subject_id', 'faculty_id', 'day_of_week',
            'timeslot_id', 'is_lab', 'priority',
            'student_count', 'room_capacity'
        ]
        self.is_trained = False
        self.accuracy = 0.0
        self.mse = 0.0

    def prepare_features(self, history_records, subjects_map, semesters_map, classrooms_map):
        """Convert historical records into feature matrix and targets."""
        X = []
        y_fitness = []
        y_good_slot = []

        for record in history_records:
            subj = subjects_map.get(record['subject_id'], {})
            sem = semesters_map.get(record['semester_id'], {})
            room = classrooms_map.get(record['classroom_id'], {})

            features = [
                record['subject_id'],
                record['faculty_id'],
                record['day_of_week'],
                record['timeslot_id'],
                subj.get('is_lab', 0),
                subj.get('priority', 5),
                sem.get('student_count', 30),
                room.get('capacity', 50),
            ]
            X.append(features)
            y_fitness.append(record.get('fitness_score', 0.5))
            y_good_slot.append(1 if record.get('fitness_score', 0) > 0.7 else 0)

        return np.array(X), np.array(y_fitness), np.array(y_good_slot)

    def train(self, history_records, subjects_map, semesters_map, classrooms_map):
        """Train decision tree models on historical data."""
        if not SKLEARN_AVAILABLE:
            return {'status': 'error', 'message': 'scikit-learn not installed'}

        if len(history_records) < 10:
            return {'status': 'error', 'message': 'Insufficient training data (need >= 10 records)'}

        X, y_fitness, y_good = self.prepare_features(
            history_records, subjects_map, semesters_map, classrooms_map
        )

        X_train, X_test, y_train, y_test = train_test_split(X, y_fitness, test_size=0.2, random_state=42)

        self.regressor = DecisionTreeRegressor(max_depth=8, min_samples_split=5, random_state=42)
        self.regressor.fit(X_train, y_train)
        predictions = self.regressor.predict(X_test)
        self.mse = mean_squared_error(y_test, predictions)

        X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(X, y_good, test_size=0.2, random_state=42)
        self.classifier = DecisionTreeClassifier(max_depth=6, min_samples_split=5, random_state=42)
        self.classifier.fit(X_train_c, y_train_c)
        self.accuracy = accuracy_score(y_test_c, self.classifier.predict(X_test_c))

        self.is_trained = True

        return {
            'status': 'success',
            'regression_mse': round(self.mse, 4),
            'classification_accuracy': round(self.accuracy, 4),
            'training_samples': len(X_train),
            'test_samples': len(X_test),
        }

    def predict_best_slots(self, subject_id, faculty_id, subject_info, semester_info, available_rooms, timeslots, days):
        """Predict fitness score for each (day, timeslot) combination."""
        if not self.is_trained or self.regressor is None:
            return self._fallback_suggestions(timeslots, days)

        predictions = []
        for day in days:
            for slot in timeslots:
                if slot.get('is_break'):
                    continue
                for room in available_rooms:
                    features = np.array([[
                        subject_id, faculty_id, day, slot['id'],
                        subject_info.get('is_lab', 0),
                        subject_info.get('priority', 5),
                        semester_info.get('student_count', 30),
                        room.get('capacity', 50),
                    ]])
                    score = self.regressor.predict(features)[0]
                    predictions.append({
                        'day': day,
                        'timeslot_id': slot['id'],
                        'room_id': room['id'],
                        'predicted_fitness': round(float(score), 3),
                    })

        predictions.sort(key=lambda x: -x['predicted_fitness'])
        return predictions[:10]

    def _fallback_suggestions(self, timeslots, days):
        """When no model is trained, return balanced suggestions."""
        suggestions = []
        for day in days:
            for slot in timeslots:
                if not slot.get('is_break'):
                    suggestions.append({
                        'day': day,
                        'timeslot_id': slot['id'],
                        'room_id': None,
                        'predicted_fitness': 0.5,
                    })
        return suggestions[:10]

    def get_feature_importance(self):
        """Return feature importance from the trained model."""
        if not self.is_trained or self.regressor is None:
            return {}
        importances = self.regressor.feature_importances_
        return dict(zip(self.feature_names, [round(float(v), 4) for v in importances]))


def generate_synthetic_history(subjects, semesters, faculty_subjects, classrooms, timeslots, n_records=500):
    """Generate synthetic historical data for initial model training."""
    records = []
    non_break = [t for t in timeslots if not t['is_break']]

    for _ in range(n_records):
        subj = subjects[np.random.randint(0, len(subjects))]
        sem_id = subj['semester_id']
        sem = next((s for s in semesters if s['id'] == sem_id), None)
        if not sem:
            continue

        fs_list = [fs for fs in faculty_subjects if fs['subject_id'] == subj['id']]
        if not fs_list:
            continue
        fs = fs_list[np.random.randint(0, len(fs_list))]

        slot = non_break[np.random.randint(0, len(non_break))]
        day = np.random.randint(0, 5)

        if subj['is_lab']:
            valid_rooms = [c for c in classrooms if c['room_type'] == 'lab']
        else:
            valid_rooms = [c for c in classrooms if c['room_type'] == 'lecture']
        if not valid_rooms:
            continue
        room = valid_rooms[np.random.randint(0, len(valid_rooms))]

        fitness = 0.5
        fitness += fs['preference_score'] * 0.03
        if slot['slot_number'] in [1, 2, 4, 5]:
            fitness += 0.1
        if room['capacity'] >= sem.get('student_count', 0):
            fitness += 0.1
        fitness += np.random.normal(0, 0.05)
        fitness = np.clip(fitness, 0, 1)

        records.append({
            'semester_id': sem_id,
            'subject_id': subj['id'],
            'faculty_id': fs['faculty_id'],
            'classroom_id': room['id'],
            'day_of_week': day,
            'timeslot_id': slot['id'],
            'fitness_score': round(float(fitness), 3),
            'student_feedback_score': round(float(np.clip(fitness + np.random.normal(0, 0.1), 0, 1)), 3),
            'conflict_count': max(0, int(np.random.poisson(0.3))),
        })

    return records

