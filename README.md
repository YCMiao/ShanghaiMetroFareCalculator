# Shanghai Metro shortest-path data

`data/metro-network.json` is the current graph skeleton.

- `lines` contains official operating metro lines; line 51 (市域机场线) is excluded.
- Same-named official stations share one station node, so transfers are connected with zero additional cost in the first version.
- Every edge starts with `distance_m: null`. A route must not use an edge until its printed PDF distance has been entered and reviewed.
- `planned_lines` keeps Lines 19-23 disabled by default. When their stations and distances are transcribed, set their status/profile to include them without changing the router.

Refresh the official operating-station snapshot and rebuild the skeleton:

```bash
python3 scripts/fetch_official_snapshot.py --output data/raw/official
python3 scripts/build_official_network.py data/raw/official/<timestamp>
```

`scripts/extract_pdf_distances.py` writes direct, unambiguous readings to `data/auto-distances.json`. `data/distance-audit.json` is reserved for segments that remain ambiguous or cannot be matched to a station label.

```json
{"edge_id": "<edge id>", "distance_m": <printed metre value>, "verification": "reviewed"}
```

```bash
python3 scripts/extract_pdf_distances.py
python3 scripts/apply_pdf_distances.py
```

For manual review, run `python3 scripts/audit_server.py` and open `http://127.0.0.1:8765`. Confirm the candidate value or type the correct metre value; the page updates the graph and removes the item from the audit list.

Run the current tests:

```bash
python3 -m unittest tests/test_build_official_network.py -v
```
