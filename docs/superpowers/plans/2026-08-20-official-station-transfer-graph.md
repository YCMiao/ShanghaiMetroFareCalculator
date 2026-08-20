# Official Station Transfer Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every official station ID an independent graph node and represent every same-name multi-line interchange as a zero-distance transfer edge.

**Architecture:** `build_network` will preserve each `location["id"]` as the canonical `station_id`, so ride edges never join lines through a shared name. It will derive a `transfers` array by grouping stations by exact Chinese name and creating an undirected zero-metre connection for each pair of stations from different lines. A migration utility will convert the existing name-based ride-edge IDs in auto, manual, and pending distance files to the regenerated official-ID edge IDs before those distances are applied.

**Tech Stack:** Python 3 standard library, JSON, `unittest`.

**Spec:** `docs/metro-graph-spec.md`

## Global Constraints

- Include only operating metro lines 1--18 and 41; line 51 remains excluded.
- Node IDs must be the official `stationXXXX` values from the saved official snapshot.
- Every transfer has `distance_m: 0`; do not add transfer categories, walking distances, penalties, or special cases.
- Preserve all existing PDF distance values and their verification statuses.
- Existing branch corrections for Lines 5, 10, and 11 must keep their verified distances after migration.

---

### Task 1: Define official-ID nodes and explicit transfer records

**Files:**
- Modify: `scripts/build_official_network.py`
- Modify: `tests/test_build_official_network.py`
- Modify: `tests/test_branch_topology.py`

**Interfaces:**
- Produces a station record `{id, name, official_id}` for each official map location.
- Produces ride edges with IDs `{line_id}:{from_station_id}:{to_station_id}`.
- Produces `transfers`, each `{id, from_station_id, to_station_id, distance_m: 0}`.

- [ ] **Step 1: Write failing tests for separated same-name stations and transfers**

```python
def test_keeps_same_name_locations_separate_and_adds_zero_transfer():
    network = build_network(
        [{"line_no": 1}, {"line_no": 2}],
        {1: {"levels": [{"locations": [{"id": "station0123", "title": "人民广场"}]}]},
         2: {"levels": [{"locations": [{"id": "station0201", "title": "人民广场"}]}]}},
        fetched_at="2026-08-20T00:00:00Z",
    )
    assert {station["id"] for station in network["stations"]} == {"station0123", "station0201"}
    assert network["transfers"] == [{"id": "transfer:station0123:station0201", "from_station_id": "station0123", "to_station_id": "station0201", "distance_m": 0}]
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `python3 -m unittest tests/test_build_official_network.py -v`

Expected: FAIL because stations are currently keyed by name and no `transfers` key exists.

- [ ] **Step 3: Implement official-ID station and transfer generation**

```python
station_id = location["id"]
stations[station_id] = {"id": station_id, "name": location["title"], "official_id": location["id"]}

for name, ids in stations_by_name.items():
    for left, right in combinations(sorted(ids), 2):
        transfers.append({"id": f"transfer:{left}:{right}", "from_station_id": left, "to_station_id": right, "distance_m": 0})
```

Update `apply_branch_corrections` to locate correction endpoints by `(line_id, station_name)` from the generated ride edges, rather than assembling name-based IDs.

- [ ] **Step 4: Run build and branch tests**

Run: `python3 -m unittest tests/test_build_official_network.py tests/test_branch_topology.py -v`

Expected: PASS, including the corrected 5/10/11 branch endpoints.

### Task 2: Migrate the PDF-distance audit trail

**Files:**
- Create: `scripts/migrate_distance_records.py`
- Create: `tests/test_migrate_distance_records.py`
- Modify: `data/auto-distances.json`
- Modify: `data/distance-audit.json`
- Modify: `data/manual-distances.json`

**Interfaces:**
- Produces `migrate_entries(entries: list[dict], legacy_network: dict, official_network: dict) -> list[dict]`.
- Accepts a legacy record with a name-based `edge_id`; returns the same record with the matching official-ID ride `edge_id`.

- [ ] **Step 1: Write a failing migration test**

```python
def test_migrates_a_name_based_edge_id_without_changing_distance():
    legacy = {"edges": [{"id": "2:station:国家会展中心:station:虹桥火车站", "line_id": "2", "from_station_id": "station:国家会展中心", "to_station_id": "station:虹桥火车站"}]}
    official = {"stations": [{"id": "station0234", "name": "国家会展中心"}, {"id": "station0223", "name": "虹桥火车站"}], "edges": [{"id": "2:station0234:station0223", "line_id": "2", "from_station_id": "station0234", "to_station_id": "station0223"}]}
    result = migrate_entries([{"edge_id": legacy["edges"][0]["id"], "distance_m": 1842, "verification": "reviewed"}], legacy, official)
    assert result[0]["edge_id"] == "2:station0234:station0223"
    assert result[0]["distance_m"] == 1842
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `python3 -m unittest tests/test_migrate_distance_records.py -v`

Expected: FAIL because the migration module does not exist.

- [ ] **Step 3: Implement deterministic migration and rejection of ambiguity**

```python
def edge_key(edge, stations):
    return (edge["line_id"], stations[edge["from_station_id"]]["name"], stations[edge["to_station_id"]]["name"])

def migrate_entries(entries, legacy_network, official_network):
    targets = {edge_key(edge, official_stations): edge["id"] for edge in official_network["edges"]}
    return [{**entry, "edge_id": targets[edge_key(legacy_edges[entry["edge_id"]], legacy_stations)]} for entry in entries]
```

Raise `ValueError` when a legacy edge has no target or more than one target. Save a temporary legacy network before rebuilding, migrate all three distance-record files, rebuild from the snapshot, and apply automatic plus manual distances to the new network.

- [ ] **Step 4: Run data-integrity checks**

Run: `python3 scripts/migrate_distance_records.py --snapshot data/raw/official/2026-08-20T03-09-43Z --network data/metro-network.json --auto data/auto-distances.json --manual data/manual-distances.json --audit data/distance-audit.json && python3 -m unittest discover -s tests -v`

Expected: PASS; every record references a current ride edge, all existing distances and verification values are retained, and no transfer record appears in a PDF-distance file.

### Task 3: Keep the audit interface compatible with official-ID edges

**Files:**
- Modify: `ui/audit/index.html`
- Modify: `tests/test_audit_server.py`

**Interfaces:**
- The audit page displays endpoint names from `network.edges[*].from_station_id` and `to_station_id`, not from parsing an edge ID.

- [ ] **Step 1: Write a failing audit-page behavior check**

```javascript
function edgeNames(edge) {
  return [stationName(edge.from_station_id), stationName(edge.to_station_id)];
}
```

The check must cover `2:station0234:station0223` and require `国家会展中心 → 虹桥火车站`.

- [ ] **Step 2: Replace string splitting with edge lookup**

```javascript
const edge = network.edges.find(item => item.id === e.edge_id);
const [from, to] = [name(edge.from_station_id), name(edge.to_station_id)];
```

- [ ] **Step 3: Run the complete suite and manually open the local audit page**

Run: `python3 -m unittest discover -s tests -v`

Expected: PASS; pending records render their Chinese endpoint names and submitting a review still updates manual distances and the network.

## Self-review

- Official IDs are the only node IDs: covered in Task 1.
- All same-name cross-line groups become explicit zero-distance transfers: covered in Task 1.
- Existing automatic, manual, and pending PDF records survive: covered in Task 2.
- The reviewer interface no longer depends on the retired ID format: covered in Task 3.
- No transfer type, transfer penalty, or special-case distance is introduced.
