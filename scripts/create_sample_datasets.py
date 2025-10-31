#!/usr/bin/env python3
"""
Generate three small example CSV datasets for QML pipeline testing.
"""
import numpy as np
import pandas as pd
import os

np.random.seed(42)

# Create output directory
output_dir = os.path.join(os.path.dirname(__file__), '..', 'backend', 'uploads')
os.makedirs(output_dir, exist_ok=True)

# 1. iris_like.csv - 4 numeric features, 3 classes (0-2)
n_iris = 150
iris_data = {
    'sepal_length': np.clip(np.random.normal(5.8, 0.8, n_iris), 4.0, 8.0),
    'sepal_width': np.clip(np.random.normal(3.0, 0.4, n_iris), 2.0, 4.5),
    'petal_length': np.clip(np.random.normal(3.7, 1.7, n_iris), 1.0, 7.0),
    'petal_width': np.clip(np.random.normal(1.2, 0.7, n_iris), 0.1, 2.5),
    'species': np.random.choice([0, 1, 2], n_iris, p=[0.33, 0.34, 0.33])
}
iris_df = pd.DataFrame(iris_data)
iris_path = os.path.join(output_dir, 'iris_like.csv')
iris_df.to_csv(iris_path, index=False)
print(f"✓ Created {iris_path}")
print(iris_df.head())
print()

# 2. diabetes_small.csv - 5 numeric features, binary label (0/1)
n_diabetes = 180
diabetes_data = {
    'Glucose': np.clip(np.random.normal(120, 30, n_diabetes), 50, 200).astype(int),
    'BMI': np.clip(np.random.normal(32, 7, n_diabetes), 18, 50),
    'Age': np.clip(np.random.normal(40, 15, n_diabetes), 20, 80).astype(int),
    'Insulin': np.clip(np.random.normal(80, 100, n_diabetes), 0, 400).astype(int),
    'BloodPressure': np.clip(np.random.normal(70, 15, n_diabetes), 40, 120).astype(int),
    'Outcome': np.random.choice([0, 1], n_diabetes, p=[0.65, 0.35])
}
diabetes_df = pd.DataFrame(diabetes_data)
diabetes_path = os.path.join(output_dir, 'diabetes_small.csv')
diabetes_df.to_csv(diabetes_path, index=False)
print(f"✓ Created {diabetes_path}")
print(diabetes_df.head())
print()

# 3. wine_small.csv - 4 numeric features, 3 classes (0-2)
n_wine = 160
wine_data = {
    'Alcohol': np.clip(np.random.normal(10.5, 1.5, n_wine), 8, 15),
    'Magnesium': np.clip(np.random.normal(100, 20, n_wine), 50, 150).astype(int),
    'Flavanoids': np.clip(np.random.normal(2.0, 1.0, n_wine), 0, 5),
    'Proline': np.clip(np.random.normal(750, 300, n_wine), 200, 1500).astype(int),
    'Class': np.random.choice([0, 1, 2], n_wine, p=[0.30, 0.40, 0.30])
}
wine_df = pd.DataFrame(wine_data)
wine_path = os.path.join(output_dir, 'wine_small.csv')
wine_df.to_csv(wine_path, index=False)
print(f"✓ Created {wine_path}")
print(wine_df.head())
print()

print("All sample datasets created successfully!")
