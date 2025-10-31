import os, numpy as np, pandas as pd
rng = np.random.default_rng(42)
path = r"D:\Study\Eng Project A\qml-pipeline\backend\uploads"
os.makedirs(path, exist_ok=True)

iris = pd.DataFrame({
    "sepal_length": rng.normal(5.8, 0.8, 150).round(2),
    "sepal_width":  rng.normal(3.0, 0.4, 150).round(2),
    "petal_length": rng.normal(3.7, 1.5, 150).round(2),
    "petal_width":  rng.normal(1.1, 0.6, 150).round(2),
    "target": rng.integers(0, 3, 150)
})
iris.to_csv(os.path.join(path, "iris_like.csv"), index=False)

wine = pd.DataFrame({
    "Alcohol":    rng.normal(13.0, 1.0, 150).round(2),
    "Magnesium":  rng.normal(100, 15, 150).round(0).astype(int),
    "Flavanoids": rng.normal(2.5, 0.7, 150).round(2),
    "Proline":    rng.normal(750, 200, 150).round(0).astype(int),
    "Class":      rng.integers(0, 3, 150)
})
wine.to_csv(os.path.join(path, "wine_small.csv"), index=False)

house = pd.DataFrame({
    "Price":         rng.normal(600_000, 150_000, 200).round(0).astype(int),
    "Area":          rng.normal(120, 30, 200).round(1),
    "Rooms":         rng.integers(1, 5, 200),
    "DistanceToCBD": np.clip(rng.normal(10, 5, 200), 0, None).round(1),
    "GoodDeal":      rng.integers(0, 2, 200)
})
house.to_csv(os.path.join(path, "real_estate.csv"), index=False)

print("Created: iris_like.csv, wine_small.csv, real_estate.csv in", path)
