const cityForm = document.getElementById("city-form");
const cityInput = document.getElementById("city-input");
const searchBtn = document.getElementById("search-btn");
const statusMessage = document.getElementById("status-message");
const resultCard = document.getElementById("result-card");
const addCityBtn = document.getElementById("add-city-btn");
const filterInput = document.getElementById("filter-input");
const sortSelect = document.getElementById("sort-select");
const compareTbody = document.getElementById("compare-tbody");
const compareTable = document.getElementById("compare-table");
const compareEmpty = document.getElementById("compare-empty");
const compareCount = document.getElementById("compare-count");
const bedtimeForm = document.getElementById("bedtime-form");
const bedtimeResults = document.getElementById("bedtime-results");

let currentResult = null;
const STORAGE_KEY = "sunclock_cities";

cityForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const city = cityInput.value.trim();
  if (!city) return;

  searchBtn.disabled = true;
  searchBtn.textContent = "Searching…";
  statusMessage.textContent = "";
  statusMessage.className = "status-message";
  resultCard.hidden = true;

  try {
    const res = await fetch(`/api/suntimes?city=${encodeURIComponent(city)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Something went wrong.");

    currentResult = data;
    renderResult(data);
  } catch (err) {
    statusMessage.textContent = err.message;
    statusMessage.className = "status-message error";
  } finally {
    searchBtn.disabled = false;
    searchBtn.textContent = "Search";
  }
});

function renderResult(data) {
  document.getElementById("result-place").textContent = data.place;
  document.getElementById("sunrise-val").textContent = formatTime(data.sunrise);
  document.getElementById("sunset-val").textContent = formatTime(data.sunset);
  document.getElementById("daylength-val").textContent = data.day_length || "—";
  document.getElementById("noon-val").textContent = formatTime(data.solar_noon);

  const tipsList = document.getElementById("tips-list");
  tipsList.innerHTML = "";
  (data.tips || []).forEach(tip => {
    const li = document.createElement("li");
    li.textContent = tip;
    tipsList.appendChild(li);
  });

  resultCard.hidden = false;
}

function formatTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

addCityBtn.addEventListener("click", () => {
  if (!currentResult) {
    alert("Please search for a city first.");
    return;
  }
  const cities = getCities();
  if (cities.some(c => c.place === currentResult.place)) {
    alert("That city is already in your comparison list.");
    return;
  }
  cities.push(currentResult);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cities));
  renderCompareTable();
});

function getCities() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || []; }
  catch { return []; }
}

function removeCity(place) {
  const cities = getCities().filter(c => c.place !== place);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cities));
  renderCompareTable();
}

function renderCompareTable() {
  let cities = getCities();
  const filter = filterInput.value.trim().toLowerCase();
  if (filter) cities = cities.filter(c => c.place.toLowerCase().includes(filter));

  const sortVal = sortSelect.value;
  if (sortVal === "sunrise") cities.sort((a, b) => new Date(a.sunrise) - new Date(b.sunrise));
  else if (sortVal === "name") cities.sort((a, b) => a.place.localeCompare(b.place));
  else if (sortVal === "daylength") cities.sort((a, b) => (b.day_length || "").localeCompare(a.day_length || ""));

  compareCount.textContent = getCities().length;

  if (cities.length === 0) {
    compareEmpty.hidden = false;
    compareTable.hidden = true;
    return;
  }
  compareEmpty.hidden = true;
  compareTable.hidden = false;

  compareTbody.innerHTML = "";
  cities.forEach(c => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${c.place}</td>
      <td>${formatTime(c.sunrise)}</td>
      <td>${formatTime(c.sunset)}</td>
      <td>${c.day_length || "—"}</td>
      <td><button class="remove-btn">Remove</button></td>
    `;
    tr.querySelector(".remove-btn").addEventListener("click", () => removeCity(c.place));
    compareTbody.appendChild(tr);
  });
}

filterInput.addEventListener("input", renderCompareTable);
sortSelect.addEventListener("change", renderCompareTable);

bedtimeForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const wakeTime = document.getElementById("wake-time-input").value;
  bedtimeResults.innerHTML = "Calculating…";

  try {
    const res = await fetch(`/api/bedtime?wake_time=${encodeURIComponent(wakeTime)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Something went wrong.");

    bedtimeResults.innerHTML = "";
    data.options.forEach(opt => {
      const div = document.createElement("div");
      div.className = "bedtime-option";
      div.textContent = `${opt.bedtime} → ${opt.hours_sleep}h (${opt.cycles} cycles)`;
      bedtimeResults.appendChild(div);
    });
  } catch (err) {
    bedtimeResults.textContent = err.message;
  }
});

renderCompareTable();