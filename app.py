"""
app.py
-------
Flask backend for the AI-Based Flood Prediction System.

Endpoints:
    GET  /                      -> Dashboard Home
    GET  /prediction            -> Flood Prediction page
    GET  /analytics             -> Analytics page (charts)
    GET  /history               -> Prediction History page
    GET  /about                 -> About Project page

    POST /predict                -> run the ML model on submitted parameters
    GET  /random-data            -> generate a realistic random parameter set
    GET  /model-info             -> model metrics + feature importance (JSON)
    GET  /prediction-history      -> list of stored predictions (JSON)
    POST /clear-history           -> wipe stored prediction history

Run:
    python app.py
Then open http://127.0.0.1:5000
"""

import json
import os
import random
import sqlite3
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
import requests
from flask import Flask, Response, jsonify, render_template, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "flood_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "scaler.pkl")
MODEL_INFO_PATH = os.path.join(BASE_DIR, "model_info.json")
DATASET_PATH = os.path.join(BASE_DIR, "flood_dataset.csv")
DB_PATH = os.path.join(BASE_DIR, "history.db")

FEATURE_COLUMNS = [
    "Rainfall", "Temperature", "Humidity", "River_Water_Level",
    "River_Flow", "Soil_Moisture", "Wind_Speed", "Atmospheric_Pressure",
    "Previous_Rainfall", "Drainage_Capacity", "Elevation"
]

# Realistic ranges used both for validation and for the random data generator
FEATURE_RANGES = {
    "Rainfall": (0, 300),
    "Temperature": (10, 45),
    "Humidity": (20, 100),
    "River_Water_Level": (0, 15),
    "River_Flow": (0, 3000),
    "Soil_Moisture": (10, 100),
    "Wind_Speed": (0, 100),
    "Atmospheric_Pressure": (950, 1050),
    "Previous_Rainfall": (0, 250),
    "Drainage_Capacity": (10, 100),
    "Elevation": (0, 500),
}

# ---------------------------------------------------------------------
# Load model artifacts (with graceful error handling per spec section 16)
# ---------------------------------------------------------------------
model = None
scaler = None
model_info = None
dataset_df = None
load_error = None

try:
    if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
        raise FileNotFoundError(
            "Model or scaler file missing. Run 'python train_model.py' first."
        )
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)

    if not os.path.exists(MODEL_INFO_PATH):
        raise FileNotFoundError(
            "model_info.json missing. Run 'python train_model.py' first."
        )
    with open(MODEL_INFO_PATH) as f:
        model_info = json.load(f)

    if os.path.exists(DATASET_PATH):
        dataset_df = pd.read_csv(DATASET_PATH)
except Exception as e:  # noqa: BLE001
    load_error = str(e)
    print(f"[STARTUP WARNING] {load_error}")


# ---------------------------------------------------------------------
# SQLite history storage
# ---------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            rainfall REAL,
            river_level REAL,
            river_flow REAL,
            soil_moisture REAL,
            flood_probability REAL,
            risk_level TEXT,
            prediction TEXT
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


def get_risk_level(probability):
    """probability is 0-100"""
    if probability >= 65:
        return "HIGH"
    elif probability >= 35:
        return "MEDIUM"
    else:
        return "LOW"


def validate_input(data):
    """Returns (cleaned_dict, error_message_or_None)"""
    cleaned = {}
    for col in FEATURE_COLUMNS:
        if col not in data or data[col] in (None, "", "null"):
            return None, f"Missing value for '{col}'."
        try:
            value = float(data[col])
        except (TypeError, ValueError):
            return None, f"Invalid (non-numeric) value for '{col}'."
        if np.isnan(value) or np.isinf(value):
            return None, f"Invalid value for '{col}'."
        low, high = FEATURE_RANGES[col]
        # Clamp gently instead of hard-rejecting, but warn if wildly out of range
        if value < low - abs(low) - 1 or value > high * 3 + 1:
            return None, f"'{col}' value {value} is unrealistic (expected {low}-{high})."
        value = float(np.clip(value, low, high))
        cleaned[col] = value
    return cleaned, None


# ---------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------
@app.route("/")
def index():
    stats = {
        "total_records": model_info["total_records"] if model_info else 0,
        "accuracy": model_info["models"][model_info["best_model"]]["accuracy"] if model_info else 0,
        "flood_cases": model_info["flood_cases"] if model_info else 0,
        "no_flood_cases": model_info["no_flood_cases"] if model_info else 0,
        "num_parameters": model_info["num_parameters"] if model_info else len(FEATURE_COLUMNS),
        "best_model": model_info["best_model"] if model_info else "N/A",
    }
    return render_template("index.html", stats=stats, load_error=load_error, active="dashboard")


@app.route("/prediction")
def prediction_page():
    return render_template(
        "prediction.html",
        feature_ranges=FEATURE_RANGES,
        load_error=load_error,
        active="prediction",
    )


@app.route("/analytics")
def analytics_page():
    return render_template("analytics.html", load_error=load_error, active="analytics")


@app.route("/history")
def history_page():
    return render_template("history.html", active="history")


@app.route("/about")
def about_page():
    return render_template("about.html", active="about")


# ---------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------
@app.route("/predict", methods=["POST"])
def predict():
    if model is None or scaler is None:
        return jsonify({"error": "Model not loaded. Please run train_model.py."}), 500

    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            return jsonify({"error": "Invalid or missing JSON body."}), 400

        cleaned, error = validate_input(data)
        if error:
            return jsonify({"error": error}), 400

        input_df = pd.DataFrame([[cleaned[c] for c in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
        scaled = scaler.transform(input_df)

        proba = model.predict_proba(scaled)[0]
        classes = list(model.classes_)
        flood_idx = classes.index(1) if 1 in classes else 1
        no_flood_idx = classes.index(0) if 0 in classes else 0

        flood_probability = round(float(proba[flood_idx]) * 100, 2)
        no_flood_probability = round(float(proba[no_flood_idx]) * 100, 2)
        prediction_label = "Flood" if flood_probability >= 50 else "No Flood"
        risk_level = get_risk_level(flood_probability)

        # Save to history
        now = datetime.now()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO history
               (date, time, rainfall, river_level, river_flow, soil_moisture,
                flood_probability, risk_level, prediction)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                now.strftime("%d-%m-%Y"),
                now.strftime("%H:%M:%S"),
                cleaned["Rainfall"],
                cleaned["River_Water_Level"],
                cleaned["River_Flow"],
                cleaned["Soil_Moisture"],
                flood_probability,
                risk_level,
                "FLOOD" if prediction_label == "Flood" else "NO FLOOD",
            ),
        )
        conn.commit()
        conn.close()

        return jsonify({
            "prediction": prediction_label,
            "flood_probability": flood_probability,
            "no_flood_probability": no_flood_probability,
            "risk_level": risk_level,
            "model_used": model_info["best_model"] if model_info else "Unknown",
            "input_parameters": cleaned,
        })

    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Server error while predicting: {str(e)}"}), 500


@app.route("/random-data")
def random_data():
    """
    Generates a realistic random parameter set. Randomly targets a
    low / medium / high risk scenario so demos can show varied outcomes.
    """
    scenario = random.choice(["low", "medium", "high"])

    def rnd(low, high):
        return round(random.uniform(low, high), 1)

    if scenario == "low":
        data = {
            "Rainfall": rnd(0, 60),
            "Temperature": rnd(20, 35),
            "Humidity": rnd(20, 55),
            "River_Water_Level": rnd(0, 3),
            "River_Flow": rnd(0, 500),
            "Soil_Moisture": rnd(10, 40),
            "Wind_Speed": rnd(0, 30),
            "Atmospheric_Pressure": rnd(1010, 1050),
            "Previous_Rainfall": rnd(0, 40),
            "Drainage_Capacity": rnd(60, 100),
            "Elevation": rnd(150, 500),
        }
    elif scenario == "medium":
        data = {
            "Rainfall": rnd(60, 150),
            "Temperature": rnd(18, 38),
            "Humidity": rnd(50, 80),
            "River_Water_Level": rnd(3, 7),
            "River_Flow": rnd(500, 1400),
            "Soil_Moisture": rnd(40, 70),
            "Wind_Speed": rnd(20, 60),
            "Atmospheric_Pressure": rnd(990, 1020),
            "Previous_Rainfall": rnd(30, 100),
            "Drainage_Capacity": rnd(35, 65),
            "Elevation": rnd(40, 200),
        }
    else:  # high
        data = {
            "Rainfall": rnd(150, 300),
            "Temperature": rnd(22, 38),
            "Humidity": rnd(75, 100),
            "River_Water_Level": rnd(7, 15),
            "River_Flow": rnd(1400, 3000),
            "Soil_Moisture": rnd(70, 100),
            "Wind_Speed": rnd(30, 100),
            "Atmospheric_Pressure": rnd(950, 995),
            "Previous_Rainfall": rnd(90, 250),
            "Drainage_Capacity": rnd(10, 40),
            "Elevation": rnd(0, 60),
        }

    data["_scenario"] = scenario
    return jsonify(data)


@app.route("/model-info")
def model_info_route():
    if model_info is None:
        return jsonify({"error": "Model info not available. Please run train_model.py."}), 500
    payload = dict(model_info)

    # Add a small sample of the dataset for scatter/line charts on Analytics
    if dataset_df is not None:
        sample = dataset_df.sample(min(150, len(dataset_df)), random_state=1)
        payload["sample_rainfall"] = sample["Rainfall"].round(1).tolist()
        payload["sample_river_level"] = sample["River_Water_Level"].round(2).tolist()
        payload["sample_flood"] = sample["Flood"].tolist()

    return jsonify(payload)


@app.route("/live-weather")
def live_weather():
    """
    Fetches current weather for a given lat/lon from Open-Meteo (free, no API
    key required) and maps it onto the model's input parameters. Fields the
    weather API can't provide (river level, river flow, soil moisture proxy,
    drainage capacity) are filled with reasonable estimates/placeholders that
    the user can still edit before predicting.
    """
    try:
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        if lat is None or lon is None:
            return jsonify({"error": "Missing 'lat' and 'lon' query parameters."}), 400

        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m,precipitation"
            "&daily=precipitation_sum"
            "&past_days=1&forecast_days=1&timezone=auto"
        )
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        weather = resp.json()

        current = weather.get("current", {})
        daily = weather.get("daily", {})
        precipitation_sums = daily.get("precipitation_sum", [])

        rainfall_today = precipitation_sums[-1] if precipitation_sums else current.get("precipitation", 0) or 0
        previous_rainfall = precipitation_sums[0] if len(precipitation_sums) > 1 else rainfall_today * 0.6

        def clip(val, key):
            low, high = FEATURE_RANGES[key]
            return round(float(np.clip(val, low, high)), 1)

        mapped = {
            "Rainfall": clip(rainfall_today, "Rainfall"),
            "Temperature": clip(current.get("temperature_2m", 25), "Temperature"),
            "Humidity": clip(current.get("relative_humidity_2m", 60), "Humidity"),
            "Wind_Speed": clip(current.get("wind_speed_10m", 10), "Wind_Speed"),
            "Atmospheric_Pressure": clip(current.get("pressure_msl", 1013), "Atmospheric_Pressure"),
            "Previous_Rainfall": clip(previous_rainfall, "Previous_Rainfall"),
            # Not available from a weather API — sensible defaults the user should verify/adjust
            "River_Water_Level": clip(2.0, "River_Water_Level"),
            "River_Flow": clip(400, "River_Flow"),
            "Soil_Moisture": clip(45 + rainfall_today * 0.3, "Soil_Moisture"),
            "Drainage_Capacity": clip(60, "Drainage_Capacity"),
            "Elevation": clip(100, "Elevation"),
            "_note": "River level, river flow, soil moisture, drainage capacity and elevation are "
                     "estimated placeholders — please verify or adjust them for your specific location.",
        }
        return jsonify(mapped)

    except requests.RequestException as e:
        return jsonify({"error": f"Could not reach the weather service: {str(e)}"}), 502
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Failed to fetch live weather: {str(e)}"}), 500


@app.route("/feature-correlation")
def feature_correlation():
    if dataset_df is None:
        return jsonify({"error": "Dataset not available. Please run generate_dataset.py."}), 500
    corr = dataset_df[FEATURE_COLUMNS].corr().round(3)
    return jsonify({
        "features": [c.replace("_", " ") for c in FEATURE_COLUMNS],
        "matrix": corr.values.tolist(),
    })


@app.route("/prediction-history")
def prediction_history():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM history ORDER BY id DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route("/prediction-history/pdf")
def prediction_history_pdf():
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.lib.units import mm
        from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                         Paragraph, Spacer)
        from reportlab.lib.styles import getSampleStyleSheet
        import io

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM history ORDER BY id DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                                 topMargin=15 * mm, bottomMargin=15 * mm)
        styles = getSampleStyleSheet()
        elements = [
            Paragraph("AI-Based Flood Prediction System — Prediction History", styles["Title"]),
            Paragraph(f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} | "
                      f"Total records: {len(rows)}", styles["Normal"]),
            Spacer(1, 10),
        ]

        header = ["Date", "Time", "Rainfall (mm)", "River Level (m)", "River Flow (m³/s)",
                  "Soil Moisture (%)", "Flood Prob.", "Risk", "Prediction"]
        data = [header]
        for r in rows:
            data.append([
                r["date"], r["time"], r["rainfall"], r["river_level"], r["river_flow"],
                r["soil_moisture"], f'{r["flood_probability"]}%', r["risk_level"], r["prediction"],
            ])
        if len(data) == 1:
            data.append(["No prediction history available.", "", "", "", "", "", "", "", ""])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e6fd9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8fc")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(table)
        doc.build(elements)

        pdf_bytes = buffer.getvalue()
        buffer.close()

        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment; filename=flood_prediction_history.pdf"},
        )
    except ImportError:
        return jsonify({"error": "PDF export requires the 'reportlab' package. "
                                  "Run: pip install reportlab"}), 500
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Failed to generate PDF: {str(e)}"}), 500


@app.route("/clear-history", methods=["POST"])
def clear_history():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM history")
    conn.commit()
    conn.close()
    return jsonify({"status": "cleared"})


# ---------------------------------------------------------------------
# Error handlers (section 16: user-friendly messages, not raw tracebacks)
# ---------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Page not found."}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error. Please try again."}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)