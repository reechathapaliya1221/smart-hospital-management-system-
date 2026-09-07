import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class WaitTimePredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.department_encoder = LabelEncoder()
        self.priority_encoder = LabelEncoder()
        self.peak_hours = [(9, 11), (14, 17)]  # 9-11 AM and 2-5 PM
        self.is_trained = False
        
    def extract_time_features(self, timestamp=None):
        """Extract time-based features"""
        if timestamp is None:
            timestamp = datetime.now()
        
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        is_weekend = 1 if day_of_week >= 5 else 0
        is_peak = 0
        for start, end in self.peak_hours:
            if start <= hour <= end:
                is_peak = 1
                break
        
        return {
            'hour': hour,
            'day_of_week': day_of_week,
            'is_weekend': is_weekend,
            'is_peak_hour': is_peak,
            'month': timestamp.month
        }
    
    def prepare_features(self, queue_data):
        """Prepare features for ML model"""
        features = []
        
        for data in queue_data:
            time_features = self.extract_time_features(data.get('timestamp'))
            
            # Department encoding
            if self.is_trained:
                dept_encoded = self.department_encoder.transform([data['department']])[0]
            else:
                dept_encoded = len(self.department_encoder.classes_) if data['department'] not in self.department_encoder.classes_ else 0
            
            # Priority encoding
            if self.is_trained:
                priority_encoded = self.priority_encoder.transform([data['priority']])[0]
            else:
                priority_encoded = 0
            
            features.append([
                dept_encoded,
                priority_encoded,
                data.get('waiting_count', 0),
                data.get('in_progress_count', 0),
                data.get('doctor_available', 1),
                data.get('historical_avg', 30),
                time_features['hour'],
                time_features['day_of_week'],
                time_features['is_weekend'],
                time_features['is_peak_hour'],
                data.get('emergency_count', 0)
            ])
        
        return np.array(features)
    
    def train_model(self, historical_data=None):
        """Train the ML model with historical data"""
        if historical_data is None:
            historical_data = self.generate_synthetic_data()
        
        df = pd.DataFrame(historical_data)
        
        # Encode categorical variables
        self.department_encoder.fit(df['department'].unique())
        self.priority_encoder.fit(df['priority'].unique())
        
        # Prepare features
        X = []
        y = []
        
        for _, row in df.iterrows():
            features = [
                self.department_encoder.transform([row['department']])[0],
                self.priority_encoder.transform([row['priority']])[0],
                row['waiting_count'],
                row['in_progress_count'],
                row['doctor_available'],
                row['historical_avg'],
                row['hour'],
                row['day_of_week'],
                row['is_weekend'],
                row['is_peak_hour'],
                row['emergency_count']
            ]
            X.append(features)
            y.append(row['actual_wait_time'])
        
        X = np.array(X)
        y = np.array(y)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train multiple models and select best
        models = {
            'RandomForest': RandomForestRegressor(n_estimators=100, random_state=42),
            'GradientBoosting': GradientBoostingRegressor(n_estimators=100, random_state=42)
        }
        
        best_model = None
        best_score = -float('inf')
        
        for name, model in models.items():
            scores = cross_val_score(model, X_scaled, y, cv=5, scoring='r2')
            avg_score = scores.mean()
            if avg_score > best_score:
                best_score = avg_score
                best_model = model
                best_model.fit(X_scaled, y)
        
        self.model = best_model
        self.is_trained = True
        
        # Save model
        os.makedirs('ml_model', exist_ok=True)
        joblib.dump(self.model, 'ml_model/wait_time_model.pkl')
        joblib.dump(self.scaler, 'ml_model/scaler.pkl')
        joblib.dump(self.department_encoder, 'ml_model/department_encoder.pkl')
        joblib.dump(self.priority_encoder, 'ml_model/priority_encoder.pkl')
        
        # Evaluate
        y_pred = self.model.predict(X_scaled)
        mae = mean_absolute_error(y, y_pred)
        r2 = r2_score(y, y_pred)
        
        print(f"Model trained - MAE: {mae:.2f} minutes, R2: {r2:.3f}")
        
        return self.model
    
    def predict_wait_time(self, features_dict):
        """Predict waiting time for new patient"""
        if not self.is_trained:
            try:
                self.load_model()
            except:
                self.train_model([])
        
        time_features = self.extract_time_features()
        
        # Encode features
        dept_encoded = self.department_encoder.transform([features_dict['department']])[0]
        priority_encoded = self.priority_encoder.transform([features_dict['priority']])[0]
        
        features = np.array([[
            dept_encoded,
            priority_encoded,
            features_dict.get('waiting_count', 0),
            features_dict.get('in_progress_count', 0),
            features_dict.get('doctor_available', 1),
            features_dict.get('historical_avg', 30),
            time_features['hour'],
            time_features['day_of_week'],
            time_features['is_weekend'],
            time_features['is_peak_hour'],
            features_dict.get('emergency_count', 0)
        ]])
        
        features_scaled = self.scaler.transform(features)
        predicted_time = self.model.predict(features_scaled)[0]
        
        # Apply priority adjustment
        priority_multiplier = {
            'emergency': 0.3,
            'urgent': 0.7,
            'normal': 1.0
        }.get(features_dict['priority'], 1.0)
        
        predicted_time = predicted_time * priority_multiplier
        
        # Ensure minimum and maximum bounds
        predicted_time = max(5, min(120, predicted_time))
        
        return int(predicted_time)
    
    def load_model(self):
        """Load pre-trained model"""
        self.model = joblib.load('ml_model/wait_time_model.pkl')
        self.scaler = joblib.load('ml_model/scaler.pkl')
        self.department_encoder = joblib.load('ml_model/department_encoder.pkl')
        self.priority_encoder = joblib.load('ml_model/priority_encoder.pkl')
        self.is_trained = True
    
    def generate_synthetic_data(self):
        """Generate synthetic training data"""
        data = []
        departments = ['General Medicine', 'Cardiology', 'Pediatrics', 'Orthopedics', 'Neurology', 'ENT']
        priorities = ['normal', 'urgent', 'emergency']
        
        for _ in range(5000):
            dept = np.random.choice(departments)
            priority = np.random.choice(priorities, p=[0.7, 0.2, 0.1])
            waiting_count = np.random.poisson(8)
            in_progress_count = np.random.randint(1, 4)
            doctor_available = np.random.choice([0, 1], p=[0.2, 0.8])
            
            # Time features
            hour = np.random.choice(range(8, 20))
            day_of_week = np.random.choice(range(7))
            is_weekend = 1 if day_of_week >= 5 else 0
            is_peak_hour = 1 if (9 <= hour <= 11 or 14 <= hour <= 17) else 0
            
            emergency_count = np.random.poisson(1)
            
            # Base wait time calculation
            base_time = {
                'General Medicine': 15,
                'Cardiology': 25,
                'Pediatrics': 18,
                'Orthopedics': 20,
                'Neurology': 30,
                'ENT': 15
            }[dept]
            
            priority_factor = {'normal': 1, 'urgent': 0.7, 'emergency': 0.3}[priority]
            
            actual_wait = base_time * priority_factor
            actual_wait += waiting_count * 2.5
            actual_wait += in_progress_count * 5
            actual_wait += emergency_count * 8
            actual_wait *= (1.5 if is_peak_hour else 1)
            actual_wait *= (0.8 if doctor_available else 1.2)
            
            # Add noise
            actual_wait += np.random.normal(0, 3)
            actual_wait = max(5, min(90, actual_wait))
            
            data.append({
                'department': dept,
                'priority': priority,
                'waiting_count': waiting_count,
                'in_progress_count': in_progress_count,
                'doctor_available': doctor_available,
                'historical_avg': 25,
                'hour': hour,
                'day_of_week': day_of_week,
                'is_weekend': is_weekend,
                'is_peak_hour': is_peak_hour,
                'emergency_count': emergency_count,
                'actual_wait_time': int(actual_wait)
            })
        
        return data

# Singleton instance
predictor = WaitTimePredictor()