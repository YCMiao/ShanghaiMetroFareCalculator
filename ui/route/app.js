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
  const maxStationsPerRow = 14;
  const createStop = (stationId) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "route-stop";
    button.innerHTML = `<span>${escapeHtml(stationsById.get(stationId).name)}</span>`;
    button.addEventListener("click", () => {
      $("#" + selectorTarget).value = stationsById.get(stationId).name;
      selector.close();
    });
    return button;
  };
  const createRow = (stationIds, rowIndex, hasNextRow, rowCount) => {
    const row = document.createElement("div");
    row.className = `track-row ${rowIndex % 2 ? "track-row-reverse" : "track-row-forward"}`;
    if (hasNextRow) row.classList.add(rowIndex % 2 ? "continues-left" : "continues-right");
    row.style.setProperty("--station-count", stationIds.length);
    if (!hasNextRow && rowCount > 1 && stationIds.length < maxStationsPerRow) {
      row.classList.add("partial-row");
      row.style.setProperty("--track-width", `${stationIds.length / maxStationsPerRow * 100}%`);
    }
    row.append(...stationIds.map(createStop));
    return row;
  };
  const createTrackRows = (stationIds) => {
    const rows = [];
    for (let start = 0; start < stationIds.length; start += maxStationsPerRow) {
      const rowIndex = rows.length;
      const chunk = stationIds.slice(start, start + maxStationsPerRow);
      rows.push(rowIndex % 2 ? chunk.reverse() : chunk);
    }
    return rows.map((row, index) => createRow(row, index, index < rows.length - 1, rows.length));
  };
  const adjacency = new Map(line.station_ids.map((stationId) => [stationId, []]));
  for (const edge of line.edges || []) {
    adjacency.get(edge.from_station_id)?.push(edge.to_station_id);
    adjacency.get(edge.to_station_id)?.push(edge.from_station_id);
  }
  const findPath = (start, target) => {
    const previous = new Map([[start, null]]);
    const queue = [start];
    for (let index = 0; index < queue.length; index += 1) {
      const current = queue[index];
      if (current === target) break;
      for (const next of adjacency.get(current) || []) {
        if (!previous.has(next)) {
          previous.set(next, current);
          queue.push(next);
        }
      }
    }
    if (!previous.has(target)) return null;
    const path = [];
    for (let current = target; current !== null; current = previous.get(current)) path.unshift(current);
    return path;
  };
  const leaves = [...adjacency].filter(([, neighbours]) => neighbours.length === 1).map(([stationId]) => stationId);
  const mainPath = findPath(line.station_ids[0], line.station_ids.at(-1)) || line.station_ids;
  const branchLeaf = leaves.find((stationId) => !mainPath.includes(stationId));
  const branchPath = branchLeaf && leaves.length === 3
    ? findPath(branchLeaf, mainPath.find((stationId) => (adjacency.get(stationId) || []).length > 2))?.reverse()
    : null;
  let branchConnection;
  stationList.style.setProperty("--line-color", line.color || "#e23646");
  const picker = document.createDocumentFragment();
  const mainRows = createTrackRows(mainPath);
  if (branchPath) {
    const junctionIndex = mainPath.indexOf(branchPath[0]);
    const mainRowIndex = Math.floor(junctionIndex / maxStationsPerRow);
    const mainRowStations = mainPath.slice(mainRowIndex * maxStationsPerRow, (mainRowIndex + 1) * maxStationsPerRow);
    const isReverseRow = mainRowIndex % 2 === 1;
    let junctionPosition = junctionIndex % maxStationsPerRow;
    if (isReverseRow) junctionPosition = mainRowStations.length - 1 - junctionPosition;
    let branchStations = branchPath.slice(1);
    let branchOffset = junctionPosition;
    let branchReversed = false;
    if (junctionPosition + branchPath.length > mainRowStations.length) {
      branchStations = [...branchPath.slice(1)].reverse();
      branchOffset = junctionPosition - branchPath.length + 1;
      branchReversed = true;
    }
    const branch = createRow(branchStations, 0, false, 1);
    branch.classList.add("branch-track");
    const spacer = document.createElement("span");
    spacer.className = "branch-spacer";
    if (branchReversed) branch.append(spacer); else branch.prepend(spacer);
    branch.style.setProperty("--station-count", branchPath.length);
    branch.style.setProperty("--track-width", `${branchPath.length / mainRowStations.length * 100}%`);
    branch.style.setProperty("--branch-offset", `${branchOffset / mainRowStations.length * 100}%`);
    branch.style.setProperty("--branch-junction", branchReversed
      ? `${(branchPath.length - 0.5) / branchPath.length * 100}%`
      : `${0.5 / branchPath.length * 100}%`);
    branch.setAttribute("aria-label", `由 ${stationsById.get(branchPath[0]).name} 分出的支线`);
    mainRows[mainRowIndex].classList.add("continues-over-branch");
    branchConnection = {branch, junctionRow: mainRows[mainRowIndex]};
    mainRows.splice(mainRowIndex + 1, 0, branch);
  }
  picker.append(...mainRows);
  stationList.replaceChildren(picker);
  if (branchConnection) {
    requestAnimationFrame(() => {
      const lineCenterOffset = 19.5;
      const sourceTop = branchConnection.junctionRow.getBoundingClientRect().top + lineCenterOffset;
      const targetTop = branchConnection.branch.getBoundingClientRect().top + lineCenterOffset;
      branchConnection.branch.style.setProperty("--branch-connector-top", `${sourceTop - branchConnection.branch.getBoundingClientRect().top}px`);
      branchConnection.branch.style.setProperty("--branch-connector-height", `${targetTop - sourceTop}px`);
    });
  }
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
