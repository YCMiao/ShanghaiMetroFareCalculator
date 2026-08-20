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

Run the current tests:

```bash
python3 -m unittest tests/test_build_official_network.py -v
```
