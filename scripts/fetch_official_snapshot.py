#!/usr/bin/env python3
"""Download the official Shanghai Metro line and station-order responses."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen


BASE_URL = "https://m.shmetro.com/interface/metromap/metromap.aspx"


def fetch_json(url: str) -> object:
    request = Request(url, data=b"", method="POST")
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed official endpoint
        return json.load(response)


def write_snapshot(output_root: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    destination = output_root / timestamp
    destination.mkdir(parents=True, exist_ok=False)
    lines = fetch_json(f"{BASE_URL}?func=lines")
    (destination / "lines.json").write_text(json.dumps(lines, ensure_ascii=False, indent=2) + "\n")
    for line in lines:
        line_id = line["line_no"]
        payload = fetch_json(f"{BASE_URL}?func=lineStations&line={line_id}")
        (destination / f"line-{line_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/raw/official"))
    args = parser.parse_args()
    print(write_snapshot(args.output))


if __name__ == "__main__":
    main()
