# Graphical Route Selector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add line-first station selection and an SVG-wide-network path display to the local route interface.

**Architecture:** A generator reads the saved official station coordinates and writes a derived `data/metro-map.json` containing only display coordinates, ride-edge geometry, and line colours. `route_server.py` serves this map data and returns the route edge IDs along with the existing result payload. The browser draws the complete network as muted SVG segments, then draws the returned ride edges as a coloured foreground route.

**Tech Stack:** Python 3 standard library, JSON, HTML, CSS, vanilla JavaScript, `unittest`.

**Spec:** `docs/graphical-route-selector-spec.md`

## Global Constraints

- Keep `route.py` as the only shortest-path and fare-calculation implementation.
- Use only coordinates from `data/raw/official/2026-08-20T03-09-43Z`.
- Preserve text-input station search and its station-name normalization.
- Do not add walking distance, transfer penalties, real-time data, or a geographic base map.
- All new interface controls must work with keyboard focus and narrow phone layouts.

---

### Task 1: Produce a display-only metro map dataset

**Files:**
- Create: `scripts/build_metro_map.py`
- Create: `data/metro-map.json`
- Create: `tests/test_build_metro_map.py`

**Interfaces:**
- Produces `build_map(network: dict, snapshot: Path) -> dict`.
- Output shape: `{width: 1000, height: 1000, stations: [{id, name, x, y}], edges: [{id, from_station_id, to_station_id, line_id, color}]}`.

- [ ] **Step 1: Write a failing coordinate test**

```python
def test_uses_official_normalized_coordinates_and_line_colour(tmp_path):
    network = {"stations": [{"id": "station0111", "name": "莘庄"}], "lines": [{"id": "1", "color": "#e3002b"}], "edges": []}
    snapshot = write_snapshot(tmp_path, 1, [{"id": "station0111", "title": "莘庄", "x": "0.3201", "y": "0.6252"}])
    metro_map = build_map(network, snapshot)
    assert metro_map["stations"] == [{"id": "station0111", "name": "莘庄", "x": 320.1, "y": 625.2}]
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `python3 -m unittest tests/test_build_metro_map.py -v`

Expected: FAIL because `build_metro_map.py` does not exist.

- [ ] **Step 3: Implement coordinate collection and edge projection**

```python
coordinates[location["id"]] = {"x": float(location["x"]) * 1000, "y": float(location["y"]) * 1000}
edge_records = [{**edge, "color": line_colours[edge["line_id"]]} for edge in network["edges"]]
```

For stations with multiple official points, select the coordinate closest to the median coordinate for that station name. Exclude a ride edge only when one endpoint has no official coordinate, and report the skipped ID.

- [ ] **Step 4: Generate and verify the checked-in map data**

Run: `python3 scripts/build_metro_map.py --network data/metro-network.json --snapshot data/raw/official/2026-08-20T03-09-43Z --output data/metro-map.json`

Expected: every operating ride edge is represented exactly once and every coordinate lies within the 1000 by 1000 view box.

### Task 2: Expose selection and route-display data from the local server

**Files:**
- Modify: `route_server.py`
- Modify: `tests/test_route_server.py`

**Interfaces:**
- `GET /api/map` returns `data/metro-map.json`.
- `GET /api/lines` returns `{id, name, color, station_ids}` for operating lines.
- `POST /api/route` additionally returns `edge_ids` and `station_ids` from the calculated `Route`.

- [ ] **Step 1: Write failing route response tests**

```python
response = route_response(network, "甲", "乙")
assert response["edge_ids"] == ["1:a:b"]
assert response["station_ids"] == ["a", "b"]
```

- [ ] **Step 2: Implement direct serialization from the existing `Route`**

```python
return {"edge_ids": route.edge_ids, "station_ids": route.station_ids, **existing_display_payload}
```

Read `metro-map.json` only for `/api/map`; do not recompute coordinates per request.

- [ ] **Step 3: Run server and API checks**

Run: `python3 route_server.py --port 8766`

Expected: `/api/stations`, `/api/lines`, `/api/map`, and a real `POST /api/route` respond with JSON.

### Task 3: Build the graphical selection sheet and SVG path display

**Files:**
- Modify: `ui/route/index.html`
- Modify: `ui/route/style.css`
- Modify: `ui/route/app.js`

**Interfaces:**
- `openSelector(target: "origin" | "destination")` opens a line picker.
- `drawMap(map: MapData, routeEdgeIds: string[])` renders background network and foreground route.

- [ ] **Step 1: Add accessible selection controls and dialog markup**

```html
<button type="button" class="map-pick" data-target="origin">按线路选择</button>
<dialog id="station-selector" aria-labelledby="selector-title">
  <h2 id="selector-title">选择起点</h2>
  <div id="line-list"></div>
  <div id="station-list"></div>
</dialog>
```

- [ ] **Step 2: Implement line-first selection**

```javascript
function chooseStation(target, name) {
  document.querySelector(`#${target}`).value = name;
  selector.close();
}
```

Render line buttons with their actual official colours; after a line is clicked, show only that line’s official ordered station list.

- [ ] **Step 3: Implement SVG map layers**

```javascript
const background = map.edges.map(edge => line(edge, "network-edge")).join("");
const highlighted = routeEdgeIds.map(id => line(edgeById.get(id), "route-edge")).join("");
svg.innerHTML = `<g>${background}</g><g>${highlighted}</g>`;
```

Use the 1000 by 1000 view box, muted thin background lines, route-coloured foreground segments, and small endpoint markers. Do not place every station label on the full map; labels appear only for route endpoints and station selection lists.

- [ ] **Step 4: Add responsive styling and visual QA**

Use a bottom sheet on small screens and a centered dialog on desktop. Keep the existing route summary; place the SVG map immediately below it. Test “莘庄 → 滴水湖”, a direct route, a route with transfers, keyboard dialog opening/closing, and viewport widths of 390px and 1280px.

- [ ] **Step 5: Run final verification**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`

Expected: all tests pass and the browser shows one highlighted SVG edge for each returned ride edge.

## Self-review

- Line-first selection is explicit for both start and destination: Task 3.
- Global visual route uses official snapshot coordinates rather than a hand-traced raster: Task 1 and Task 3.
- Python remains the route and fare authority: Task 2.
- Existing textual input and output remain available: Task 3.
- The official reference image informed the visual language only; it is not copied or used as route data.
