#!/usr/bin/env python3
"""Create the distance-pending metro graph from an official source snapshot."""

from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path


NON_METRO_LINE_IDS = {51}
PLANNED_METRO_LINES = [
    {"id": "19", "name": "19号线", "service_status": "planned", "enabled_by_default": False},
    {"id": "20", "name": "20号线", "service_status": "planned", "enabled_by_default": False},
    {"id": "21", "name": "21号线", "service_status": "planned", "enabled_by_default": False},
    {"id": "22", "name": "22号线", "service_status": "planned", "enabled_by_default": False},
    {"id": "23", "name": "23号线", "service_status": "planned", "enabled_by_default": False},
]
BRANCH_EDGE_CORRECTIONS = (
    ("5", "闵行开发区", "江川路", "东川路", "江川路"),
    ("10", "龙柏新村", "虹桥火车站", "龙柏新村", "龙溪路"),
    ("11", "上海赛车场", "嘉定北", "上海赛车场", "嘉定新城"),
)


def apply_branch_corrections(edges: list[dict], stations: dict[str, dict]) -> list[dict]:
    """Replace concatenation artifacts in the official one-list branch ordering."""
    def edge_names(edge: dict) -> tuple[str, str, str]:
        return edge["line_id"], stations[edge["from_station_id"]]["name"], stations[edge["to_station_id"]]["name"]

    corrected = list(edges)
    for line, old_from, old_to, new_from, new_to in BRANCH_EDGE_CORRECTIONS:
        false_index = next((index for index, edge in enumerate(corrected)
                            if edge_names(edge) == (line, old_from, old_to)), None)
        if false_index is None:
            continue
        candidates = {
            name: sorted({station_id for edge in edges if edge["line_id"] == line
                          for station_id in (edge["from_station_id"], edge["to_station_id"])
                          if stations[station_id]["name"] == name})
            for name in (new_from, new_to)
        }
        if any(len(ids) != 1 for ids in candidates.values()):
            raise ValueError(f"cannot identify branch endpoints for Line {line}")
        from_station_id, to_station_id = candidates[new_from][0], candidates[new_to][0]
        corrected[false_index] = {
            "id": f"{line}:{from_station_id}:{to_station_id}",
            "from_station_id": from_station_id,
            "to_station_id": to_station_id,
            "line_id": line,
            "distance_m": None,
            "distance_source": None,
            "verification": "pending_pdf",
        }
    return corrected


def build_network(lines: list[dict], stations_by_line: dict[int, dict], fetched_at: str) -> dict:
    stations: dict[str, dict] = {}
    station_lines: dict[str, set[str]] = {}
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
            station_id = official_station_id
            station_ids.append(station_id)
            stations.setdefault(station_id, {
                "id": station_id,
                "name": location["title"],
                "official_id": official_station_id,
            })
        line_id = str(official_line_id)
        for station_id in station_ids:
            station_lines.setdefault(station_id, set()).add(line_id)
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

    transfers = []
    station_ids_by_name: dict[str, list[str]] = {}
    for station in stations.values():
        station_ids_by_name.setdefault(station["name"], []).append(station["id"])
    for station_ids in station_ids_by_name.values():
        for left, right in combinations(sorted(station_ids), 2):
            if station_lines[left] != station_lines[right]:
                transfers.append({
                    "id": f"transfer:{left}:{right}",
                    "from_station_id": left,
                    "to_station_id": right,
                    "distance_m": 0,
                })

    return {
        "schema_version": 2,
        "generated_from": {
            "source": "https://m.shmetro.com/interface/metromap/metromap.aspx",
            "fetched_at": fetched_at,
            "scope": "official operating metro stations; airport link line 51 excluded",
        },
        "stations": sorted(stations.values(), key=lambda station: station["id"]),
        "lines": graph_lines,
        "planned_lines": PLANNED_METRO_LINES,
        "edges": apply_branch_corrections(edges, stations),
        "transfers": transfers,
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
