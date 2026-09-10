// prediction.js - Handles the Flood Prediction page:
// input fields <-> sliders sync, Generate Random Data, Predict, Random+Predict, Clear

const FIELD_IDS = [
  "Rainfall", "Temperature", "Humidity", "River_Water_Level", "River_Flow",
  "Soil_Moisture", "Wind_Speed", "Atmospheric_Pressure", "Previous_Rainfall",
  "Drainage_Capacity", "Elevation"
];

const FIELD_LABELS = {
  Rainfall: "Rainfall (mm)",
  Temperature: "Temperature (°C)",
  Humidity: "Humidity (%)",
  River_Water_Level: "River Water Level (m)",
  River_Flow: "River Flow (m³/s)",
  Soil_Moisture: "Soil Moisture (%)",
  Wind_Speed: "Wind Speed (km/h)",
  Atmospheric_Pressure: "Atmospheric Pressure (hPa)",
  Previous_Rainfall: "Previous Rainfall (mm)",
  Drainage_Capacity: "Drainage Capacity (%)",
  Elevation: "Elevation (m)"
};

function showAlert(message) {
  const alertBox = document.getElementById("formAlert");
  alertBox.textContent = message;
  alertBox.classList.remove("d-none");
  setTimeout(() => alertBox.classList.add("d-none"), 4500);
}

function setFieldValue(id, value) {
  const input = document.getElementById(id);
  const slider = document.querySelector(`.param-slider[data-target="${id}"]`);
  if (input) input.value = value;
  if (slider) slider.value = value;
}

function getAllValues() {
  const values = {};
  let hasEmpty = false;
  FIELD_IDS.forEach((id) => {
    const el = document.getElementById(id);
    if (!el.value || el.value.trim() === "") {
      hasEmpty = true;
    }
    values[id] = el.value;
  });
  return { values, hasEmpty };
}

// ---- Sync sliders <-> number inputs ----
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".param-slider").forEach((slider) => {
    slider.addEventListener("input", () => {
      const targetId = slider.getAttribute("data-target");
      document.getElementById(targetId).value = slider.value;
    });
  });

  document.querySelectorAll(".param-input").forEach((input) => {
    input.addEventListener("input", () => {
      const slider = document.querySelector(`.param-slider[data-target="${input.id}"]`);
      if (slider && input.value !== "") slider.value = input.value;
    });
  });

  document.getElementById("randomBtn").addEventListener("click", () => generateRandomData());
  document.getElementById("liveWeatherBtn").addEventListener("click", () => fetchLiveWeather());
  document.getElementById("predictBtn").addEventListener("click", () => runPrediction());
  document.getElementById("randomPredictBtn").addEventListener("click", async () => {
    await generateRandomData();
    runPrediction();
  });
  document.getElementById("clearBtn").addEventListener("click", clearForm);
});

function clearForm() {
  FIELD_IDS.forEach((id) => setFieldValue(id, ""));
  document.querySelectorAll(".param-slider").forEach((s) => (s.value = s.min));
  document.getElementById("scenarioBadge").textContent = "No scenario yet";
  document.getElementById("resultContent").classList.add("d-none");
  document.getElementById("resultPlaceholder").classList.remove("d-none");
}

async function generateRandomData() {
  try {
    const res = await fetch("/random-data");
    if (!res.ok) throw new Error("Failed to fetch random data");
    const data = await res.json();

    FIELD_IDS.forEach((id) => {
      if (data[id] !== undefined) setFieldValue(id, data[id]);
    });

    const scenario = (data._scenario || "unknown").toUpperCase();
    const badge = document.getElementById("scenarioBadge");
    badge.textContent = `Scenario: ${scenario} RISK`;
    badge.className = "badge " + (
      scenario === "HIGH" ? "bg-danger-subtle text-danger" :
      scenario === "MEDIUM" ? "bg-warning-subtle text-warning" :
      "bg-success-subtle text-success"
    );
  } catch (err) {
    showAlert("Could not generate random data. Please check the server.");
  }
}

async function fetchLiveWeather() {
  const btn = document.getElementById("liveWeatherBtn");
  const originalHtml = btn.innerHTML;

  if (!navigator.geolocation) {
    showAlert("Geolocation isn't supported by this browser. Try Generate Random Data instead.");
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Locating...';

  navigator.geolocation.getCurrentPosition(
    async (position) => {
      const { latitude, longitude } = position.coords;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Fetching weather...';
      try {
        const res = await fetch(`/live-weather?lat=${latitude}&lon=${longitude}`);
        const data = await res.json();
        if (!res.ok) {
          showAlert(data.error || "Could not fetch live weather data.");
          return;
        }
        FIELD_IDS.forEach((id) => {
          if (data[id] !== undefined) setFieldValue(id, data[id]);
        });
        const badge = document.getElementById("scenarioBadge");
        badge.textContent = "Live weather data";
        badge.className = "badge bg-primary-subtle text-primary";
        if (data._note) showAlert(data._note);
      } catch (err) {
        showAlert("Server error while fetching live weather.");
      } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
      }
    },
    (error) => {
      showAlert("Location access denied or unavailable. Try Generate Random Data instead.");
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    },
    { timeout: 8000 }
  );
}

async function runPrediction() {
  const { values, hasEmpty } = getAllValues();
  if (hasEmpty) {
    showAlert("Please fill in all fields or click 'Generate Random Data' first.");
    return;
  }

  const predictBtn = document.getElementById("predictBtn");
  const originalHtml = predictBtn.innerHTML;
  predictBtn.disabled = true;
  predictBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Predicting...';

  try {
    const res = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
    const data = await res.json();

    if (!res.ok) {
      showAlert(data.error || "Prediction failed. Please check your inputs.");
      return;
    }

    renderResult(data);
  } catch (err) {
    showAlert("Server error. Please make sure the Flask app is running.");
  } finally {
    predictBtn.disabled = false;
    predictBtn.innerHTML = originalHtml;
  }
}

function renderResult(data) {
  document.getElementById("resultPlaceholder").classList.add("d-none");
  const content = document.getElementById("resultContent");
  content.classList.remove("d-none");

  const isFlood = data.prediction === "Flood";
  const banner = document.getElementById("resultBanner");
  const icon = document.getElementById("resultIcon");
  const text = document.getElementById("resultText");

  banner.className = "result-banner " + (isFlood ? "flood" : "no-flood");
  icon.className = "bi " + (isFlood ? "bi-exclamation-triangle-fill" : "bi-check-circle-fill");
  text.textContent = isFlood ? "FLOOD RISK DETECTED" : "NO FLOOD RISK";

  document.getElementById("floodProbText").textContent = data.flood_probability + "%";
  document.getElementById("floodProbBar").style.width = data.flood_probability + "%";
  document.getElementById("noFloodProbText").textContent = data.no_flood_probability + "%";
  document.getElementById("noFloodProbBar").style.width = data.no_flood_probability + "%";

  const riskPill = document.getElementById("riskPill");
  riskPill.textContent = data.risk_level;
  riskPill.className = "risk-pill " + data.risk_level;

  document.getElementById("modelUsedText").textContent = data.model_used;

  const summary = document.getElementById("inputSummary");
  summary.innerHTML = "";
  Object.entries(data.input_parameters).forEach(([key, value]) => {
    const row = document.createElement("div");
    row.innerHTML = `<span>${FIELD_LABELS[key] || key}</span><strong>${value}</strong>`;
    summary.appendChild(row);
  });

  content.scrollIntoView({ behavior: "smooth", block: "nearest" });
}