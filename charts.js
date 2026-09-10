// charts.js - Fetches /model-info and renders 5 interactive Chart.js charts
// on the Analytics page.

document.addEventListener("DOMContentLoaded", async () => {
  try {
    const res = await fetch("/model-info");
    const info = await res.json();
    if (info.error) {
      console.error(info.error);
      return;
    }
    renderFloodDistribution(info);
    renderRainfallChart(info);
    renderRiverLevelChart(info);
    renderFeatureImportance(info);
    renderModelComparison(info);
    renderRocCurve(info);
  } catch (err) {
    console.error("Failed to load analytics data:", err);
  }

  try {
    const corrRes = await fetch("/feature-correlation");
    const corrInfo = await corrRes.json();
    if (!corrInfo.error) renderCorrelationHeatmap(corrInfo);
  } catch (err) {
    console.error("Failed to load correlation data:", err);
  }
});

const palette = {
  flood: "#e64848",
  noFlood: "#1aa179",
  blue: "#1e6fd9",
  teal: "#17a2b8",
  warning: "#f2a33c",
  purple: "#8757e5",
};

// Chart 1: Flood vs No-Flood distribution (doughnut)
function renderFloodDistribution(info) {
  new Chart(document.getElementById("floodDistChart"), {
    type: "doughnut",
    data: {
      labels: ["Flood", "No Flood"],
      datasets: [{
        data: [info.flood_cases, info.no_flood_cases],
        backgroundColor: [palette.flood, palette.noFlood],
        borderWidth: 2,
        borderColor: "#fff",
      }],
    },
    options: {
      plugins: { legend: { position: "bottom" } },
      cutout: "62%",
    },
  });
}

// Chart 2: Rainfall vs Flood Probability (scatter)
function renderRainfallChart(info) {
  const rainfall = info.sample_rainfall || [];
  const flood = info.sample_flood || [];
  const points = rainfall.map((r, i) => ({ x: r, y: flood[i] === 1 ? 100 : 0 }));

  new Chart(document.getElementById("rainfallChart"), {
    type: "scatter",
    data: {
      datasets: [{
        label: "Sample records",
        data: points,
        backgroundColor: points.map(p => p.y === 100 ? palette.flood : palette.noFlood),
      }],
    },
    options: {
      scales: {
        x: { title: { display: true, text: "Rainfall (mm)" } },
        y: { title: { display: true, text: "Flood Occurred (0=No, 100=Yes)" }, min: -10, max: 110 },
      },
      plugins: { legend: { display: false } },
    },
  });
}

// Chart 3: River Water Level vs Flood Cases
function renderRiverLevelChart(info) {
  const river = info.sample_river_level || [];
  const flood = info.sample_flood || [];
  const points = river.map((r, i) => ({ x: r, y: flood[i] === 1 ? 100 : 0 }));

  new Chart(document.getElementById("riverLevelChart"), {
    type: "scatter",
    data: {
      datasets: [{
        label: "Sample records",
        data: points,
        backgroundColor: points.map(p => p.y === 100 ? palette.flood : palette.blue),
      }],
    },
    options: {
      scales: {
        x: { title: { display: true, text: "River Water Level (m)" } },
        y: { title: { display: true, text: "Flood Occurred (0=No, 100=Yes)" }, min: -10, max: 110 },
      },
      plugins: { legend: { display: false } },
    },
  });
}

// Chart 4: Feature Importance (horizontal bar)
function renderFeatureImportance(info) {
  const importance = info.feature_importance || [];
  new Chart(document.getElementById("featureImportanceChart"), {
    type: "bar",
    data: {
      labels: importance.map(f => f.feature.replace(/_/g, " ")),
      datasets: [{
        label: "Importance (%)",
        data: importance.map(f => f.importance),
        backgroundColor: palette.purple,
      }],
    },
    options: {
      indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: { x: { title: { display: true, text: "Importance (%)" } } },
    },
  });
}

// ROC Curve (one line per model, plus a diagonal reference line)
function renderRocCurve(info) {
  const models = info.models || {};
  const colors = [palette.blue, palette.warning, palette.purple, palette.teal];
  const datasets = Object.keys(models).map((name, i) => {
    const points = (models[name].roc_curve || []).map(p => ({ x: p.fpr, y: p.tpr }));
    return {
      label: `${name} (AUC ${models[name].auc.toFixed(3)})`,
      data: points,
      borderColor: colors[i % colors.length],
      backgroundColor: "transparent",
      showLine: true,
      pointRadius: 0,
      borderWidth: 2,
      tension: 0.15,
    };
  });

  datasets.push({
    label: "Random guess",
    data: [{ x: 0, y: 0 }, { x: 1, y: 1 }],
    borderColor: "#ccc",
    borderDash: [6, 6],
    showLine: true,
    pointRadius: 0,
    borderWidth: 1.5,
  });

  new Chart(document.getElementById("rocCurveChart"), {
    type: "scatter",
    data: { datasets },
    options: {
      scales: {
        x: { title: { display: true, text: "False Positive Rate" }, min: 0, max: 1 },
        y: { title: { display: true, text: "True Positive Rate" }, min: 0, max: 1 },
      },
      plugins: { legend: { position: "bottom" } },
    },
  });
}

// Feature Correlation Heatmap (rendered as a grid of colored cells via a bar-matrix trick)
function renderCorrelationHeatmap(info) {
  const labels = info.features || [];
  const matrix = info.matrix || [];
  const cellData = [];
  for (let i = 0; i < labels.length; i++) {
    for (let j = 0; j < labels.length; j++) {
      cellData.push({ x: labels[j], y: labels[i], v: matrix[i][j] });
    }
  }

  new Chart(document.getElementById("correlationHeatmap"), {
    type: "scatter",
    data: {
      datasets: [{
        label: "Correlation",
        data: cellData.map(c => ({ x: c.x, y: c.y })),
        backgroundColor: cellData.map(c => correlationColor(c.v)),
        pointStyle: "rect",
        pointRadius: 15,
      }],
    },
    options: {
      scales: {
        x: { type: "category", labels, ticks: { autoSkip: false, maxRotation: 60, minRotation: 60, font: { size: 9 } } },
        y: { type: "category", labels, reverse: true, ticks: { font: { size: 9 } } },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const c = cellData[ctx.dataIndex];
              return `${c.x} vs ${c.y}: ${c.v.toFixed(2)}`;
            },
          },
        },
      },
    },
  });
}

function correlationColor(v) {
  // v ranges -1..1; blue for negative, red for positive, white near 0
  const intensity = Math.min(Math.abs(v), 1);
  if (v >= 0) {
    const g = Math.round(255 * (1 - intensity));
    return `rgba(230,72,72,${0.15 + intensity * 0.85})`.replace("230,72,72", `230,${g},${g}`);
  } else {
    const g = Math.round(255 * (1 - intensity));
    return `rgba(${g},${g},230,${0.15 + intensity * 0.85})`;
  }
}

// Chart 5: Model Comparison (grouped bar)
function renderModelComparison(info) {
  const models = info.models || {};
  const names = Object.keys(models);

  new Chart(document.getElementById("modelComparisonChart"), {
    type: "bar",
    data: {
      labels: names,
      datasets: [
        { label: "Accuracy", data: names.map(n => models[n].accuracy), backgroundColor: palette.blue },
        { label: "Precision", data: names.map(n => models[n].precision), backgroundColor: palette.teal },
        { label: "Recall", data: names.map(n => models[n].recall), backgroundColor: palette.warning },
        { label: "F1-score", data: names.map(n => models[n].f1_score), backgroundColor: palette.purple },
      ],
    },
    options: {
      plugins: { legend: { position: "bottom" } },
      scales: { y: { title: { display: true, text: "Score (%)" }, max: 100 } },
    },
  });
}