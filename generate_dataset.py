"""
generate_dataset.py
--------------------
Generates a realistic SYNTHETIC dataset for the AI-Based Flood Prediction
System. Labels are NOT random — they are derived from a weighted risk score
built from the environmental parameters, then passed through a sigmoid and
sampled with a small amount of noise so the ML model has real patterns to
learn (higher rainfall / river level / river flow / soil moisture / previous
rainfall => higher flood probability; higher drainage capacity / elevation
=> lower flood probability).

Run:
    python generate_dataset.py
Output:
    flood_dataset.csv  (1500 records)
"""

import numpy as np
import pandas as pd

RANDOM_SEED = 42
N_RECORDS = 1500

np.random.seed(RANDOM_SEED)


def normalize(value, low, high):
    """Scale a value into 0-1 range given its known min/max bounds."""
    return np.clip((value - low) / (high - low), 0, 1)


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def generate_dataset(n=N_RECORDS):
    # ---- Feature ranges (matches spec in section 14) ----
    rainfall = np.random.gamma(shape=2.0, scale=45, size=n)            # 0-300ish
    rainfall = np.clip(rainfall, 0, 300)

    temperature = np.random.uniform(10, 45, n)

    humidity = np.random.normal(65, 20, n)
    humidity = np.clip(humidity, 20, 100)

    river_level = np.random.gamma(shape=2.0, scale=2.2, size=n)
    river_level = np.clip(river_level, 0, 15)

    river_flow = np.random.gamma(shape=2.0, scale=450, size=n)
    river_flow = np.clip(river_flow, 0, 3000)

    soil_moisture = np.random.normal(55, 22, n)
    soil_moisture = np.clip(soil_moisture, 10, 100)

    wind_speed = np.random.uniform(0, 100, n)

    pressure = np.random.normal(1005, 20, n)
    pressure = np.clip(pressure, 950, 1050)

    previous_rainfall = np.random.gamma(shape=2.0, scale=35, size=n)
    previous_rainfall = np.clip(previous_rainfall, 0, 250)

    drainage_capacity = np.random.uniform(10, 100, n)

    elevation = np.random.gamma(shape=1.5, scale=70, size=n)
    elevation = np.clip(elevation, 0, 500)

    # ---- Weighted risk score built from normalized features ----
    rainfall_n = normalize(rainfall, 0, 300)
    river_level_n = normalize(river_level, 0, 15)
    river_flow_n = normalize(river_flow, 0, 3000)
    soil_moisture_n = normalize(soil_moisture, 10, 100)
    prev_rainfall_n = normalize(previous_rainfall, 0, 250)
    humidity_n = normalize(humidity, 20, 100)
    wind_n = normalize(wind_speed, 0, 100)
    drainage_n = normalize(drainage_capacity, 10, 100)
    elevation_n = normalize(elevation, 0, 500)
    pressure_drop_n = normalize(1050 - pressure, 0, 100)  # low pressure -> storms

    risk_score = (
        0.24 * rainfall_n
        + 0.20 * river_level_n
        + 0.16 * river_flow_n
        + 0.13 * soil_moisture_n
        + 0.10 * prev_rainfall_n
        + 0.06 * humidity_n
        + 0.05 * pressure_drop_n
        + 0.03 * wind_n
        - 0.14 * drainage_n
        - 0.11 * elevation_n
    )

    # Center and scale so sigmoid spreads probabilities well
    risk_centered = (risk_score - risk_score.mean()) / risk_score.std()
    noise = np.random.normal(0, 0.35, n)  # realism: not a perfect function
    flood_probability = sigmoid(1.6 * risk_centered + noise)

    flood = np.random.binomial(1, flood_probability)

    df = pd.DataFrame({
        "Rainfall": rainfall.round(1),
        "Temperature": temperature.round(1),
        "Humidity": humidity.round(1),
        "River_Water_Level": river_level.round(2),
        "River_Flow": river_flow.round(1),
        "Soil_Moisture": soil_moisture.round(1),
        "Wind_Speed": wind_speed.round(1),
        "Atmospheric_Pressure": pressure.round(1),
        "Previous_Rainfall": previous_rainfall.round(1),
        "Drainage_Capacity": drainage_capacity.round(1),
        "Elevation": elevation.round(1),
        "Flood": flood
    })

    return df


if __name__ == "__main__":
    df = generate_dataset()
    df.to_csv("flood_dataset.csv", index=False)

    print("Dataset generated successfully!")
    print(f"Total records : {len(df)}")
    print(f"Flood cases   : {df['Flood'].sum()}")
    print(f"No-flood cases: {(df['Flood'] == 0).sum()}")
    print(f"Flood ratio   : {df['Flood'].mean():.2%}")
    print("Saved to flood_dataset.csv")
