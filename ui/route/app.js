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

function showMessage(text, isError = false) {
  message.textContent = text;
  message.className = `message${isError ? " error" : ""}`;
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
    <li>
      <b>${escapeHtml(leg.line_name)}</b>
      ${leg.stations.map(escapeHtml).join(" → ")}
    </li>
  `).join("");

  result.innerHTML = `
    <div class="summary">
      <div class="metric">
        <small>理论最短距离</small>
        <strong>${escapeHtml(data.distance_m)} m</strong>
      </div>
      <div class="metric">
        <small>按当前里程规则</small>
        <strong>${escapeHtml(data.fare_yuan)} 元</strong>
      </div>
    </div>
    <article class="route-card">
      <h2>路线带</h2>
      <div class="route-ribbon">${legs}</div>
      ${transfers}
      <h2>经过站点</h2>
      <ul class="station-list">${stationRows}</ul>
    </article>
  `;
  result.hidden = false;
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
    if (!response.ok) {
      throw new Error(data.error || "无法计算路线");
    }
    render(data);
    showMessage("已按总区间距离找到路线。");
  } catch (error) {
    showMessage(error.message, true);
  }
}

$("#search").addEventListener("click", search);
[origin, destination].forEach((input) => {
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      search();
    }
  });
});

$("#swap").addEventListener("click", () => {
  [origin.value, destination.value] = [destination.value, origin.value];
  origin.focus();
});

fetch("/api/stations")
  .then((response) => response.json())
  .then((stations) => {
    $("#stations").innerHTML = stations.map(
      (name) => `<option value="${escapeHtml(name)}">`,
    ).join("");
  })
  .catch(() => showMessage("无法加载站名列表。", true));
