#!/usr/bin/env python3
"""Apply reviewed PDF segment distances to the generated metro graph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def apply_distances(network: dict, audit: dict) -> dict:
    edges = {edge["id"]: edge for edge in network["edges"]}
    for entry in audit["entries"]:
        edge = edges.get(entry["edge_id"])
        if edge is None:
            raise ValueError(f"unknown edge: {entry['edge_id']}")
        if not isinstance(entry["distance_m"], int) or entry["distance_m"] <= 0:
            raise ValueError(f"invalid distance for: {entry['edge_id']}")
        verification = entry.get("verification")
        if verification not in {"auto_read", "reviewed"}:
            raise ValueError(f"unverified distance: {entry['edge_id']}")
        edge.update({
            "distance_m": entry["distance_m"],
            "distance_source": "pdf_label",
            "verification": verification,
        })
    return network


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", type=Path, default=Path("data/metro-network.json"))
    parser.add_argument("--input", type=Path, action="append", default=[Path("data/auto-distances.json")])
    args = parser.parse_args()
    network = json.loads(args.network.read_text())
    for source in args.input:
        updated = apply_distances(network, json.loads(source.read_text()))
    args.network.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
    print(args.network)


if __name__ == "__main__":
    main()
