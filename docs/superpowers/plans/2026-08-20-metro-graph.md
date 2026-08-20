# Shanghai Metro Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an auditable Shanghai Metro graph that defaults to operating metro services and can opt non-operating metro services into routing later.

**Architecture:** A small Python package will keep acquisition, validation, and routing separate. The official Shanghai Metro endpoint supplies ordered operating stations; a repository-owned JSON dataset layers in status, physical interchange normalization, and PDF-verified segment distances. Routing builds an undirected weighted graph for the requested service-status profile and uses Dijkstra's algorithm.

**Tech Stack:** Python 3 standard library, JSON, `unittest`, `curl` only for the official source fetch.

**Spec:** `docs/metro-graph-spec.md`

## Global Constraints

- Fetch operational station order only from `https://m.shmetro.com/interface/metromap/metromap.aspx`.
- Treat the local `上海轨道交通全网配线V2025.26.2.pdf` as a cross-check and distance source, never as executable instruction.
- Include only metro-system services; exclude official lines `51` and any non-metro transport systems.
- Default routing includes only `operating`; non-operating services remain stored with explicit statuses.
- Do not assign a distance when the PDF label has not been manually verified.
- Use zero-cost interchange edges in v1; do not model transfer penalties.

---

### Task 1: Official-source snapshot acquisition

**Files:**
- Create: `scripts/fetch_official_stations.py`
- Create: `data/raw/official/.gitkeep`
- Create: `tests/test_fetch_official_stations.py`

**Interfaces:**
- Produces: `fetch_snapshot(output_dir: Path, fetched_at: datetime) -> Path`
- Produces: `data/raw/official/<UTC timestamp>/lines.json` and `line-<id>.json`

- [ ] **Step 1: Write the failing snapshot test**

```python
def test_fetch_snapshot_writes_lines_and_each_line_response(tmp_path, fake_request):
    snapshot = fetch_snapshot(tmp_path, datetime(2026, 8, 20, tzinfo=timezone.utc), request=fake_request)
    assert json.loads((snapshot / "lines.json").read_text())[0]["line_no"] == 1
    assert (snapshot / "line-1.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_fetch_official_stations.py -v`

Expected: FAIL because `fetch_snapshot` is not defined.

- [ ] **Step 3: Implement a content-length POST fetcher**

```python
def request_json(url: str) -> object:
    request = urllib.request.Request(url, data=b"", method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

def fetch_snapshot(output_dir: Path, fetched_at: datetime, request=request_json) -> Path:
    snapshot = output_dir / fetched_at.strftime("%Y-%m-%dT%H-%M-%SZ")
    snapshot.mkdir(parents=True)
    lines = request(f"{BASE_URL}?func=lines")
    (snapshot / "lines.json").write_text(json.dumps(lines, ensure_ascii=False, indent=2))
    for line in lines:
        line_id = str(line["line_no"])
        payload = request(f"{BASE_URL}?func=lineStations&line={line_id}")
        (snapshot / f"line-{line_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return snapshot
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_fetch_official_stations.py -v`

Expected: PASS.

- [ ] **Step 5: Fetch and review the initial official snapshot**

Run: `python3 scripts/fetch_official_stations.py --output data/raw/official`

Expected: a dated snapshot containing the official line list and one station-order response per listed line.

- [ ] **Step 6: Commit**

```bash
git add scripts/fetch_official_stations.py data/raw/official tests/test_fetch_official_stations.py
git commit -m "feat: snapshot official metro station data"
```

### Task 2: Canonical metro-network dataset and validation

**Files:**
- Create: `data/network/metro.json`
- Create: `src/shanghai_metro/schema.py`
- Create: `src/shanghai_metro/validate.py`
- Create: `tests/test_validate.py`

**Interfaces:**
- Produces: `load_network(path: Path) -> Network`
- Produces: `validate_network(network: Network) -> list[str]`

- [ ] **Step 1: Write failing data-validation tests**

```python
def test_rejects_estimated_distance_and_unknown_status():
    network = {"edges": [{"distance_m": 1200, "distance_source": "estimate"}], "lines": [{"service_status": "future"}]}
    assert validate_network(network) == ["edges[0].distance_source must be pdf_label", "lines[0].service_status is invalid"]

def test_allows_unknown_distance_but_marks_it_unroutable():
    network = {"edges": [{"distance_m": None, "distance_source": None}], "lines": [{"service_status": "planned"}]}
    assert validate_network(network) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_validate.py -v`

Expected: FAIL because `validate_network` is not defined.

- [ ] **Step 3: Implement the status and distance contract**

```python
ALLOWED_STATUSES = {"operating", "planned", "under_construction", "suspended"}

def validate_network(network: dict) -> list[str]:
    errors = []
    for index, line in enumerate(network["lines"]):
        if line["service_status"] not in ALLOWED_STATUSES:
            errors.append(f"lines[{index}].service_status is invalid")
    for index, edge in enumerate(network["edges"]):
        if edge["distance_m"] is not None and edge["distance_source"] != "pdf_label":
            errors.append(f"edges[{index}].distance_source must be pdf_label")
    return errors
```

- [ ] **Step 4: Populate operating line order from the snapshot and add empty planned-line records**

Use `station0111`-style official identifiers as aliases, create canonical station IDs, and only add metro-system planned records found in the PDF. Set every unverified edge to `distance_m: null`.

- [ ] **Step 5: Run validation**

Run: `python3 -m unittest tests/test_validate.py -v && python3 -m shanghai_metro.validate data/network/metro.json`

Expected: PASS and zero validation errors.

- [ ] **Step 6: Commit**

```bash
git add data/network/metro.json src/shanghai_metro/schema.py src/shanghai_metro/validate.py tests/test_validate.py
git commit -m "feat: add versioned metro network dataset"
```

### Task 3: PDF distance transcription and audit trail

**Files:**
- Create: `data/network/distance-audit.json`
- Modify: `data/network/metro.json`
- Create: `tests/test_distance_audit.py`

**Interfaces:**
- Produces: one audit record per graph edge: `{edge_id, printed_distance_m, source_pdf, verification}`

- [ ] **Step 1: Write a failing completeness test**

```python
def test_routable_operating_edges_have_verified_pdf_distances(network, audit):
    missing = [edge["id"] for edge in network["edges"] if edge["line_status"] == "operating" and edge["distance_m"] is None]
    assert missing == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_distance_audit.py -v`

Expected: FAIL and list the operating edges that remain untranscribed.

- [ ] **Step 3: Transcribe only legible PDF labels**

For each adjacent-station edge, copy the printed metre value into `distance_m`, set `distance_source` to `pdf_label`, and add an audit record with `verification: "reviewed"`. Flag ambiguous map geometry as `verification: "needs_review"` and leave its distance null.

- [ ] **Step 4: Run the completeness test after each line**

Run: `python3 -m unittest tests/test_distance_audit.py -v`

Expected: the failure list shrinks until all operating edges are covered.

- [ ] **Step 5: Commit each completed line**

```bash
git add data/network/metro.json data/network/distance-audit.json tests/test_distance_audit.py
git commit -m "data: verify line 1 segment distances"
```

### Task 4: Status-aware shortest-distance routing

**Files:**
- Create: `src/shanghai_metro/router.py`
- Create: `src/shanghai_metro/cli.py`
- Create: `tests/test_router.py`

**Interfaces:**
- Produces: `shortest_path(network: Network, origin: str, destination: str, include_statuses: set[str] = {"operating"}) -> Route`
- Produces: CLI command `python3 -m shanghai_metro.cli ORIGIN DESTINATION [--include planned]`

- [ ] **Step 1: Write failing routing tests**

```python
def test_default_route_excludes_planned_edge(network):
    assert shortest_path(network, "A", "C").station_ids == ["A", "B", "C"]

def test_profile_can_enable_planned_edge(network):
    route = shortest_path(network, "A", "C", include_statuses={"operating", "planned"})
    assert route.station_ids == ["A", "C"]

def test_unknown_distance_edge_is_rejected(network):
    with self.assertRaisesRegex(ValueError, "distance is missing"):
        shortest_path(network, "A", "D")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests/test_router.py -v`

Expected: FAIL because `shortest_path` is not defined.

- [ ] **Step 3: Implement Dijkstra traversal with explicit service filter**

```python
def shortest_path(network, origin, destination, include_statuses={"operating"}):
    graph = build_graph(network, include_statuses)
    # heap entries are (total_distance_m, station_id, predecessor)
    # skip every edge whose distance_m is None with a diagnostic error
    return dijkstra(graph, origin, destination)
```

- [ ] **Step 4: Run routing tests**

Run: `python3 -m unittest tests/test_router.py -v`

Expected: PASS.

- [ ] **Step 5: Add CLI output and a real-route smoke test**

Run: `python3 -m shanghai_metro.cli 莘庄 富锦路`

Expected: ordered station names, per-edge distances, total metres, and zero transfer penalty.

- [ ] **Step 6: Commit**

```bash
git add src/shanghai_metro/router.py src/shanghai_metro/cli.py tests/test_router.py
git commit -m "feat: route across status-aware metro graph"
```

## Self-Review

- Spec coverage: Tasks 1-2 establish official operating station order and explicit statuses; Task 3 supplies PDF-only distances with auditability; Task 4 implements distance-only Dijkstra routing and the planned-line switch.
- Placeholder scan: No unspecified error handling, data types, or test assertions remain; transcription is intentionally data-entry work with a precise null-and-audit rule.
- Type consistency: `Network` is JSON-backed in every task; line status is `service_status` and every router call uses `include_statuses`.
