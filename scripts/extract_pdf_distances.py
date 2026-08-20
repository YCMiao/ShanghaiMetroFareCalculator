#!/usr/bin/env python3
"""Extract only unambiguous station-to-station distances from the PDF text layout."""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path


NUMBER = re.compile(r"(?<![\d+])[0-9]{3,4}(?![\d+])")


def _text_layout(pdf: Path) -> list[str]:
    with tempfile.NamedTemporaryFile(suffix=".txt") as handle:
        subprocess.run(
            ["gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=txtwrite", "-dTextFormat=3", f"-sOutputFile={handle.name}", str(pdf)],
            check=True,
        )
        return Path(handle.name).read_text(errors="replace").splitlines()


def _occurrences(lines: list[str], name: str) -> list[tuple[int, int]]:
    return [(line.find(name) + len(name) / 2, row) for row, line in enumerate(lines) if line.find(name) >= 0]


def _choose_route_positions(candidates: list[list[tuple[int, int]]]) -> list[tuple[int, int] | None]:
    """Choose the compact visual path when a label appears more than once."""
    result: list[tuple[int, int] | None] = []
    start = 0
    while start < len(candidates):
        if not candidates[start]:
            result.append(None)
            start += 1
            continue
        end = start
        while end < len(candidates) and candidates[end]:
            end += 1
        states = [(0, [point]) for point in candidates[start]]
        for choices in candidates[start + 1:end]:
            next_states = []
            for point in choices:
                cost, path = min(
                    states,
                    key=lambda state: state[0] + (state[1][-1][0] - point[0]) ** 2 + (state[1][-1][1] - point[1]) ** 2,
                )
                next_states.append((cost + (path[-1][0] - point[0]) ** 2 + (path[-1][1] - point[1]) ** 2, path + [point]))
            states = next_states
        result.extend(min(states, key=lambda state: state[0])[1])
        start = end
    return result


def extract(network: dict, layout: list[str]) -> tuple[list[dict], list[dict]]:
    names = {station["id"]: station["name"] for station in network["stations"]}
    numbers = []
    for row, line in enumerate(layout):
        for match in NUMBER.finditer(line):
            value = int(match.group())
            if 400 <= value <= 6000:
                numbers.append((match.start(), row, value))

    edges_by_line: dict[str, list[dict]] = {}
    for edge in network["edges"]:
        edges_by_line.setdefault(edge["line_id"], []).append(edge)

    candidates: list[tuple[dict, tuple[float, int, int, int] | None, tuple[float, int, int, int] | None]] = []
    for line in network["lines"]:
        station_ids = line["station_ids"]
        points = _choose_route_positions([_occurrences(layout, names[station_id]) for station_id in station_ids])
        for edge, origin, destination in zip(edges_by_line[line["id"]], points, points[1:]):
            if origin is None or destination is None:
                candidates.append((edge, None, None))
                continue
            midpoint = ((origin[0] + destination[0]) / 2, (origin[1] + destination[1]) / 2)
            ranked = sorted(
                (math.hypot(x - midpoint[0], (y - midpoint[1]) * 2), value, x, y)
                for x, y, value in numbers
            )
            candidates.append((edge, ranked[0], ranked[1] if len(ranked) > 1 else None))

    token_counts: dict[tuple[int, int, int], int] = {}
    for _, first, _ in candidates:
        if first:
            token_counts[first[1:]] = token_counts.get(first[1:], 0) + 1

    automatic, audit = [], []
    for edge, first, second in candidates:
        if first is None:
            audit.append({"edge_id": edge["id"], "reason": "station_label_not_found"})
            continue
        distance, value, x, y = first
        unique = token_counts[(value, x, y)] == 1
        separated = second is None or second[0] >= distance * 1.7
        if distance <= 30 and unique and separated:
            automatic.append({"edge_id": edge["id"], "distance_m": value, "verification": "auto_read"})
        else:
            audit.append({
                "edge_id": edge["id"],
                "reason": "ambiguous_or_distant_numeric_label",
                "nearest_candidate_m": value,
            })
    return automatic, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=Path("上海轨道交通全网配线V2025.26.2.pdf"))
    parser.add_argument("--network", type=Path, default=Path("data/metro-network.json"))
    parser.add_argument("--auto-output", type=Path, default=Path("data/auto-distances.json"))
    parser.add_argument("--audit-output", type=Path, default=Path("data/distance-audit.json"))
    args = parser.parse_args()
    network = json.loads(args.network.read_text())
    automatic, audit = extract(network, _text_layout(args.pdf))
    args.auto_output.write_text(json.dumps({"source_pdf": args.pdf.name, "unit": "m", "entries": automatic}, ensure_ascii=False, indent=2) + "\n")
    args.audit_output.write_text(json.dumps({"source_pdf": args.pdf.name, "unit": "m", "entries": audit}, ensure_ascii=False, indent=2) + "\n")
    print(f"automatic={len(automatic)}; audit={len(audit)}")


if __name__ == "__main__":
    main()
