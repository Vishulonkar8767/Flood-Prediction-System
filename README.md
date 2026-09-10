# 🌊 AI-Based Flood Prediction System

An academic Machine Learning project that predicts flood risk from environmental and weather
parameters, wrapped in a full, interactive Flask + Bootstrap web dashboard.

---

## 📋 Project Description

This system uses supervised machine learning to classify whether a given set of environmental
conditions (rainfall, river level, soil moisture, etc.) indicates a **Flood** or **No Flood**
risk. It includes a synthetic-but-realistic dataset generator, a model training/comparison
pipeline, and a modern web dashboard for live predictions, analytics, and history tracking —
suitable for an MCA / B.Tech final-year project demonstration.

---

## ✨ Features

- Interactive multi-page dashboard (Dashboard, Prediction, Analytics, History, About)
- Manual parameter entry **or** one-click realistic random data generation (Low/Medium/High risk scenarios)
- "Random Data + Predict" one-click demo button
- Live flood probability, risk level (LOW/MEDIUM/HIGH), and model explainability
- 5 interactive Chart.js visualizations (distribution, rainfall vs. flood, river level vs. flood,
  feature importance, model comparison)
- Prediction history stored in SQLite with search, filter, and clear
- Graceful error handling (missing model/dataset, invalid inputs, server errors)
- Fully responsive Bootstrap 5 UI with sidebar navigation, hover effects, and animations

---

## 🛠️ Technologies

| Layer        | Tech |
|--------------|------|
| ML / Data    | Python, Pandas, NumPy, Scikit-learn, Matplotlib, Seaborn, Joblib |
| Backend      | Flask, SQLite |
| Frontend     | HTML5, CSS3, JavaScript, Bootstrap 5, Chart.js, Bootstrap Icons |

---

## 📊 Dataset

`generate_dataset.py` creates **1,500 synthetic records** with 11 parameters:

Rainfall (mm), Temperature (°C), Humidity (%), River Water Level (m), River Flow (m³/s),
Soil Moisture (%), Wind Speed (km/h), Atmospheric Pressure (hPa), Previous Rainfall (mm),
Drainage Capacity (%), Elevation (m) → target: **Flood** (0 = No Flood, 1 = Flood)

Labels are **not random** — they come from a weighted risk score (higher rainfall / river
level / river flow / soil moisture / previous rainfall increase risk; higher drainage capacity
and elevation reduce it), passed through a sigmoid with noise, so the model learns genuine
patterns instead of memorizing noise.

---

## 🤖 Machine Learning Algorithms

Three classifiers are trained and compared in `train_model.py`:

1. **Random Forest** (also used for feature-importance explainability)
2. **Decision Tree**
3. **Logistic Regression**

Each is evaluated with **Accuracy, Precision, Recall, F1-score, and Confusion Matrix**. The
best model (highest F1-score) is saved as `flood_model.pkl`, alongside `scaler.pkl`
(StandardScaler) and `model_info.json` (metrics + feature importance, used by the Analytics page).

Typical results (may vary slightly run to run since data is randomly generated):

| Model | Accuracy | Precision | Recall | F1-score |
|-------|----------|-----------|--------|----------|
| Random Forest | ~74% | ~74% | ~73% | ~74% |
| Decision Tree | ~64% | ~64% | ~63% | ~63% |
| Logistic Regression | ~74% | ~74% | ~73% | ~73% |

---

## 📦 Installation

**Requirements:** Python 3.9+ and VS Code on Windows (also works on macOS/Linux).

1. Open the project folder in VS Code.
2. Open a terminal (`` Ctrl+` ``) and create/activate a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 How to Run

Run these three commands **in order**, from the project root:

```bash
venv\Scripts\activate
pip install -r requirements.txt
python generate_dataset.py
python train_model.py
python app.py
```

- `generate_dataset.py` → creates `flood_dataset.csv` (1,500 records)
- `train_model.py` → trains & compares the 3 models, saves `flood_model.pkl`, `scaler.pkl`, `model_info.json`
- `app.py` → starts the Flask server

Then open your browser at:

```
http://127.0.0.1:5000
```

> If you skip step 1 or 2, the dashboard will still load but will show a friendly
> "Setup needed" banner explaining which script to run.

---

## 🎯 Example Predictions

**High-risk input:**
Rainfall = 220 mm, River Level = 9.8 m, River Flow = 2200 m³/s, Soil Moisture = 88%,
Drainage Capacity = 25%, Elevation = 15 m
→ **FLOOD RISK DETECTED**, Flood Probability ≈ 88%, Risk Level: **HIGH**

**Low-risk input:**
Rainfall = 20 mm, River Level = 1.2 m, River Flow = 150 m³/s, Soil Moisture = 25%,
Drainage Capacity = 85%, Elevation = 300 m
→ **NO FLOOD RISK**, Flood Probability ≈ 6%, Risk Level: **LOW**

(Exact numbers vary slightly depending on the model trained in your run — use
**Generate Random Data** on the Prediction page to try many scenarios instantly.)

---

## 🖼️ Screenshots

*(Add screenshots here after running the app — Dashboard, Prediction Result, Analytics charts,
and History table make a strong presentation set.)*

---

## 🔮 Future Scope


- Incorporate satellite/GIS elevation and land-cover data
- Explore deep learning (LSTM) for time-series flood forecasting
- Add SMS/email alerting for HIGH risk predictions
- Deploy to cloud (Render/Heroku/Azure) with a production database

---

## 🎓 How to Demonstrate This Project in a College Presentation

1. **Start the application** — run `python app.py` in the terminal (after the dataset/model
   have already been generated once).
2. **Open the dashboard** — go to `http://127.0.0.1:5000` and point out the stat cards
   (total records, model accuracy, flood/no-flood case counts).
3. **Go to Flood Prediction** and click **Generate Random Data**.
4. **Show the generated environmental values** now filled into the input fields/sliders,
   and mention the scenario badge (Low/Medium/High risk).
5. **Click Predict Flood.**
6. **Show the flood probability, risk level, and the input parameters** used, plus which
   model produced the result.
7. **Click Generate Random Data again** to get a different scenario.
8. **Show a different prediction outcome** (e.g. switch from a LOW to a HIGH risk case) —
   this demonstrates the model responds meaningfully to different inputs.
9. **Open the Analytics page** and walk through the 5 charts.
10. **Explain feature importance** (which parameters matter most, e.g. Rainfall, River Level,
    River Flow) **and model accuracy** (compare Random Forest vs Decision Tree vs Logistic
    Regression using the grouped bar chart).
11. **Open Prediction History** and show that every prediction made during the demo has been
    logged with date, time, and key parameters — demonstrate the search/filter and (optionally)
    Clear History.

---

## 📁 Project Structure

```
flood-prediction-project/
│
├── app.py                  # Flask backend & API endpoints
├── train_model.py           # Trains/compares ML models, saves model + scaler
├── generate_dataset.py       # Generates the synthetic dataset
├── flood_model.pkl           # Saved best-performing model (generated)
├── scaler.pkl                 # Saved StandardScaler (generated)
├── model_info.json            # Metrics + feature importance (generated)
├── flood_dataset.csv           # Generated dataset (generated)
├── history.db                   # SQLite prediction history (generated at runtime)
├── requirements.txt
│
├── templates/
│   ├── base.html            # Shared layout: sidebar + topbar (used by all pages)
│   ├── index.html            # Dashboard Home
│   ├── prediction.html         # Flood Prediction page
│   ├── analytics.html           # Analytics / charts page
│   ├── history.html              # Prediction History page
│   └── about.html                 # About Project page
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── dashboard.js
│       ├── prediction.js
│       ├── charts.js
│       └── history.js
│
└── README.md
```

> Note: `flood_model.pkl`, `scaler.pkl`, `model_info.json`, `flood_dataset.csv`, and
> `history.db` are **generated** by running the scripts above — they are not meant to be
> hand-edited.
