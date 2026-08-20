#!/usr/bin/env python3
"""Build display coordinates for the local Shanghai Metro SVG network map."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_map(network: dict, snapshot: Path) -> dict:
    coordinates: dict[str, tuple[float, float]] = {}
    for line in network["lines"]:
        source = json.loads((snapshot / f"line-{line['id']}.json").read_text())
        for location in source["levels"][0]["locations"]:
            coordinates[location["id"]] = (round(float(location["x"]) * 1000, 4), round(float(location["y"]) * 1000, 4))

    stations = []
    for station in network["stations"]:
        if station["id"] not in coordinates:
            raise ValueError(f"missing official coordinate: {station['id']}")
        x, y = coordinates[station["id"]]
        stations.append({"id": station["id"], "name": station["name"], "x": x, "y": y})

    colors = {line["id"]: line.get("color") or "#e23646" for line in network["lines"]}
    edges = [{
        "id": edge["id"],
        "from_station_id": edge["from_station_id"],
        "to_station_id": edge["to_station_id"],
        "line_id": edge["line_id"],
        "color": colors[edge["line_id"]],
    } for edge in network["edges"]]
    padding = 35
    xs, ys = [station["x"] for station in stations], [station["y"] for station in stations]
    view_box = {
        "x": max(0, round(min(xs) - padding, 4)),
        "y": max(0, round(min(ys) - padding, 4)),
        "width": round(min(1000, max(xs) + padding) - max(0, min(xs) - padding), 4),
        "height": round(min(1000, max(ys) + padding) - max(0, min(ys) - padding), 4),
    }
    return {"width": 1000, "height": 1000, "view_box": view_box, "stations": stations, "edges": edges}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", type=Path, default=Path("data/metro-network.json"))
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/metro-map.json"))
    args = parser.parse_args()
    metro_map = build_map(json.loads(args.network.read_text()), args.snapshot)
    args.output.write_text(json.dumps(metro_map, ensure_ascii=False, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
