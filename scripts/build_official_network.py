#!/usr/bin/env python3
"""Create the distance-pending metro graph from an official source snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


NON_METRO_LINE_IDS = {51}
PLANNED_METRO_LINES = [
    {"id": "19", "name": "19号线", "service_status": "planned", "enabled_by_default": False},
    {"id": "20", "name": "20号线", "service_status": "planned", "enabled_by_default": False},
    {"id": "21", "name": "21号线", "service_status": "planned", "enabled_by_default": False},
    {"id": "22", "name": "22号线", "service_status": "planned", "enabled_by_default": False},
    {"id": "23", "name": "23号线", "service_status": "planned", "enabled_by_default": False},
]


def build_network(lines: list[dict], stations_by_line: dict[int, dict], fetched_at: str) -> dict:
    stations: dict[str, dict] = {}
    graph_lines: list[dict] = []
    edges: list[dict] = []

    for line in lines:
        official_line_id = int(line["line_no"])
        if official_line_id in NON_METRO_LINE_IDS:
            continue
        locations = stations_by_line[official_line_id]["levels"][0]["locations"]
        station_ids = []
        for location in locations:
            official_station_id = location["id"]
            station_id = f"station:{location['title']}"
            station_ids.append(station_id)
            station = stations.setdefault(station_id, {
                "id": station_id,
                "name": location["title"],
                "official_ids": [],
            })
            station["official_ids"].append(official_station_id)
        line_id = str(official_line_id)
        graph_lines.append({
            "id": line_id,
            "name": f"{line_id}号线" if line_id != "41" else "浦江线",
            "color": line.get("color"),
            "service_status": "operating",
            "enabled_by_default": True,
            "station_ids": station_ids,
        })
        for origin, destination in zip(station_ids, station_ids[1:]):
            edges.append({
                "id": f"{line_id}:{origin}:{destination}",
                "from_station_id": origin,
                "to_station_id": destination,
                "line_id": line_id,
                "distance_m": None,
                "distance_source": None,
                "verification": "pending_pdf",
            })

    return {
        "schema_version": 1,
        "generated_from": {
            "source": "https://m.shmetro.com/interface/metromap/metromap.aspx",
            "fetched_at": fetched_at,
            "scope": "official operating metro stations; airport link line 51 excluded",
        },
        "stations": sorted(stations.values(), key=lambda station: station["id"]),
        "lines": graph_lines,
        "planned_lines": PLANNED_METRO_LINES,
        "edges": edges,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path, help="directory created by fetch_official_snapshot.py")
    parser.add_argument("--output", type=Path, default=Path("data/metro-network.json"))
    args = parser.parse_args()

    lines = json.loads((args.snapshot / "lines.json").read_text())
    station_data = {
        int(line["line_no"]): json.loads((args.snapshot / f"line-{line['line_no']}.json").read_text())
        for line in lines
        if int(line["line_no"]) not in NON_METRO_LINE_IDS
    }
    network = build_network(lines, station_data, fetched_at=args.snapshot.name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(network, ensure_ascii=False, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
