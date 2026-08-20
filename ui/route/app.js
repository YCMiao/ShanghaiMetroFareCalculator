const $ = (selector) => document.querySelector(selector);

const escapeHtml = (value) => String(value).replace(
  /[&<>'"]/g,
  (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  }[character]),
);

const origin = $("#origin");
const destination = $("#destination");
const message = $("#message");
const result = $("#result");
const selector = $("#station-selector");
const lineList = $("#line-list");
const stationList = $("#station-list-picker");
let selectorTarget = "origin";
let metroMap;
let lines = [];
let stationsById = new Map();

function showMessage(text, isError = false) {
  message.textContent = text;
  message.className = `message${isError ? " error" : ""}`;
}

function routeMap(data) {
  const mapStations = new Map(metroMap.stations.map((station) => [station.id, station]));
  const mapEdges = new Map(metroMap.edges.map((edge) => [edge.id, edge]));
  const line = (edge, className) => {
    const from = mapStations.get(edge.from_station_id);
    const to = mapStations.get(edge.to_station_id);
    return `<line class="${className}" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" stroke="${edge.color}"/>`;
  };
  const network = metroMap.edges.map((edge) => line(edge, "network-edge")).join("");
  const highlighted = data.edge_ids
    .map((edgeId) => mapEdges.get(edgeId))
    .filter(Boolean)
    .map((edge) => line(edge, "route-edge"))
    .join("");
  const endpoints = [data.station_ids[0], data.station_ids.at(-1)]
    .map((stationId, index) => {
      const station = mapStations.get(stationId);
      return `<circle class="map-endpoint endpoint-${index}" cx="${station.x}" cy="${station.y}" r="10"/><text class="map-label" x="${station.x + 14}" y="${station.y - 13}">${escapeHtml(station.name)}</text>`;
    })
    .join("");
  const box = metroMap.view_box;
  return `<svg class="network-svg" viewBox="${box.x} ${box.y} ${box.width} ${box.height}" role="img" aria-label="全网最短路径图"><g>${network}</g><g>${highlighted}</g><g>${endpoints}</g></svg>`;
}

function render(data) {
  const legs = data.legs.map((leg) => `
    <div class="ribbon-leg" style="--line-color:${escapeHtml(leg.color)}">
      <b>${escapeHtml(leg.line_name)}</b>
      <span>${escapeHtml(leg.stations[0])} → ${escapeHtml(leg.stations.at(-1))}</span>
    </div>
  `).join("");
  const transfers = data.transfers.length
    ? `<p class="transfer-note">换乘：${data.transfers.map((item) => (
      `${escapeHtml(item.station)}（${escapeHtml(item.from_line)} → ${escapeHtml(item.to_line)}）`
    )).join("；")}</p>`
    : "";
  const stationRows = data.legs.map((leg) => `
    <li><b>${escapeHtml(leg.line_name)}</b>${leg.stations.map(escapeHtml).join(" → ")}</li>
  `).join("");

  result.innerHTML = `
    <div class="summary">
      <div class="metric"><small>理论最短距离</small><strong>${escapeHtml(data.distance_m)} m</strong></div>
      <div class="metric"><small>按当前里程规则</small><strong>${escapeHtml(data.fare_yuan)} 元</strong></div>
    </div>
    <article class="route-card">
      <h2>全网路径</h2>${routeMap(data)}
      <h2>路线带</h2><div class="route-ribbon">${legs}</div>${transfers}
      <h2>经过站点</h2><ul class="station-list">${stationRows}</ul>
    </article>
  `;
  result.hidden = false;
}

function showLineStations(line) {
  stationList.replaceChildren(...line.station_ids.map((stationId) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "station-choice";
    button.textContent = stationsById.get(stationId).name;
    button.addEventListener("click", () => {
      $("#" + selectorTarget).value = button.textContent;
      selector.close();
    });
    return button;
  }));
  $("#selector-hint").textContent = `已选择 ${line.name}，点击站点完成选择。`;
}

function openSelector(target) {
  selectorTarget = target;
  $("#selector-title").textContent = target === "origin" ? "选择起点" : "选择终点";
  $("#selector-hint").textContent = "先选择线路。";
  stationList.replaceChildren();
  lineList.replaceChildren(...lines.map((line) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "line-choice";
    button.style.setProperty("--line-color", line.color || "#e23646");
    button.textContent = line.name;
    button.addEventListener("click", () => showLineStations(line));
    return button;
  }));
  selector.showModal();
}

async function search() {
  const from = origin.value.trim();
  const to = destination.value.trim();
  if (!from || !to) {
    showMessage("请填写起点站和终点站。", true);
    return;
  }
  showMessage("正在计算路线…");
  result.hidden = true;
  try {
    const response = await fetch("/api/route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ origin: from, destination: to }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "无法计算路线");
    render(data);
    showMessage("已按总区间距离找到路线。");
  } catch (error) {
    showMessage(error.message, true);
  }
}

$("#search").addEventListener("click", search);
[origin, destination].forEach((input) => input.addEventListener("keydown", (event) => {
  if (event.key === "Enter") search();
}));
$("#swap").addEventListener("click", () => {
  [origin.value, destination.value] = [destination.value, origin.value];
  origin.focus();
});
document.querySelectorAll(".map-pick").forEach((button) => {
  button.addEventListener("click", () => openSelector(button.dataset.target));
});

Promise.all([
  fetch("/api/stations").then((response) => response.json()),
  fetch("/api/lines").then((response) => response.json()),
  fetch("/api/map").then((response) => response.json()),
]).then(([stationNames, loadedLines, loadedMap]) => {
  lines = loadedLines;
  metroMap = loadedMap;
  stationsById = new Map(metroMap.stations.map((station) => [station.id, station]));
  $("#stations").innerHTML = stationNames.map((name) => `<option value="${escapeHtml(name)}">`).join("");
}).catch(() => showMessage("无法加载线路图数据。", true));
