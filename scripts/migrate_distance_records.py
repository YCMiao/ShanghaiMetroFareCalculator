#!/usr/bin/env python3
"""Migrate name-based ride-edge IDs to official-station-ID ride-edge IDs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _edge_keys(network: dict) -> dict[str, tuple[str, str, str]]:
    names = {station["id"]: station["name"] for station in network["stations"]}
    return {
        edge["id"]: (edge["line_id"], names[edge["from_station_id"]], names[edge["to_station_id"]])
        for edge in network["edges"]
    }


def migrate_entries(entries: list[dict], legacy_network: dict, official_network: dict) -> list[dict]:
    legacy_keys = _edge_keys(legacy_network)
    targets: dict[tuple[str, str, str], list[str]] = {}
    for edge_id, key in _edge_keys(official_network).items():
        targets.setdefault(key, []).append(edge_id)

    migrated = []
    for entry in entries:
        try:
            key = legacy_keys[entry["edge_id"]]
        except KeyError as error:
            raise ValueError(f"legacy edge is missing: {entry['edge_id']}") from error
        candidate_ids = targets.get(key, [])
        if len(candidate_ids) != 1:
            raise ValueError(f"cannot uniquely migrate edge: {entry['edge_id']}")
        migrated.append({**entry, "edge_id": candidate_ids[0]})
    return migrated


def migrate_file(path: Path, legacy_network: dict, official_network: dict) -> None:
    record = json.loads(path.read_text())
    record["entries"] = migrate_entries(record["entries"], legacy_network, official_network)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-network", type=Path, required=True)
    parser.add_argument("--network", type=Path, default=Path("data/metro-network.json"))
    parser.add_argument("--input", type=Path, action="append", required=True)
    args = parser.parse_args()

    legacy_network = json.loads(args.legacy_network.read_text())
    official_network = json.loads(args.network.read_text())
    for path in args.input:
        migrate_file(path, legacy_network, official_network)
        print(path)


if __name__ == "__main__":
    main()
