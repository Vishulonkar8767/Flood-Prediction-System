// history.js - Loads, searches, filters, and clears the Prediction History table

let allHistory = [];

document.addEventListener("DOMContentLoaded", () => {
  loadHistory();

  document.getElementById("searchInput").addEventListener("input", applyFilters);
  document.getElementById("filterRisk").addEventListener("change", applyFilters);
  document.getElementById("filterPrediction").addEventListener("change", applyFilters);
  document.getElementById("clearHistoryBtn").addEventListener("click", clearHistory);
});

async function loadHistory() {
  try {
    const res = await fetch("/prediction-history");
    allHistory = await res.json();
    applyFilters();
  } catch (err) {
    document.getElementById("historyTableBody").innerHTML =
      `<tr><td colspan="9" class="text-center text-danger py-4">Failed to load history.</td></tr>`;
  }
}

function applyFilters() {
  const search = document.getElementById("searchInput").value.toLowerCase();
  const riskFilter = document.getElementById("filterRisk").value;
  const predFilter = document.getElementById("filterPrediction").value;

  const filtered = allHistory.filter((row) => {
    const matchesSearch =
      !search ||
      Object.values(row).some((v) => String(v).toLowerCase().includes(search));
    const matchesRisk = !riskFilter || row.risk_level === riskFilter;
    const matchesPred = !predFilter || row.prediction === predFilter;
    return matchesSearch && matchesRisk && matchesPred;
  });

  renderTable(filtered);
}

function renderTable(rows) {
  const body = document.getElementById("historyTableBody");
  const emptyMsg = document.getElementById("historyEmptyMsg");

  if (!rows.length) {
    body.innerHTML = "";
    emptyMsg.style.display = "block";
    return;
  }
  emptyMsg.style.display = "none";

  body.innerHTML = rows.map((row) => `
    <tr>
      <td>${row.date}</td>
      <td>${row.time}</td>
      <td>${row.rainfall}</td>
      <td>${row.river_level}</td>
      <td>${row.river_flow}</td>
      <td>${row.soil_moisture}</td>
      <td>${row.flood_probability}%</td>
      <td><span class="risk-badge ${row.risk_level}">${row.risk_level}</span></td>
      <td><span class="pred-badge ${row.prediction === 'FLOOD' ? 'flood' : 'no-flood'}">${row.prediction}</span></td>
    </tr>
  `).join("");
}

async function clearHistory() {
  if (!confirm("Are you sure you want to clear all prediction history? This cannot be undone.")) {
    return;
  }
  try {
    await fetch("/clear-history", { method: "POST" });
    allHistory = [];
    applyFilters();
  } catch (err) {
    alert("Failed to clear history. Please try again.");
  }
}
