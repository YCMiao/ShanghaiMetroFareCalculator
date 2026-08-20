#!/usr/bin/env python3
"""Local web server for the Shanghai Metro shortest-distance interface."""

from __future__ import annotations

import argparse
import json
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from route import fare_yuan, shortest_path


def line_picker_data(network: dict) -> list[dict]:
    """Return lines with their ride-edge topology for the station picker."""
    edges_by_line: dict[str, list[dict]] = {}
    for edge in network["edges"]:
        edges_by_line.setdefault(edge["line_id"], []).append({
            "from_station_id": edge["from_station_id"],
            "to_station_id": edge["to_station_id"],
        })
    return [{**line, "edges": edges_by_line.get(line["id"], [])} for line in network["lines"]]


def route_response(network: dict, origin: str, destination: str) -> dict:
    route = shortest_path(network, origin, destination)
    names = {station["id"]: station["name"].strip() for station in network["stations"]}
    edges = {edge["id"]: edge for edge in [*network["edges"], *network["transfers"]]}
    lines = {line["id"]: line for line in network["lines"]}
    legs, active_leg, transfers = [], None, []
    for index, edge_id in enumerate(route.edge_ids):
        edge = edges[edge_id]
        if "line_id" not in edge:
            before = next((edges[item]["line_id"] for item in reversed(route.edge_ids[:index]) if "line_id" in edges[item]), None)
            after = next((edges[item]["line_id"] for item in route.edge_ids[index + 1:] if "line_id" in edges[item]), None)
            transfers.append({"station": names[route.station_ids[index]], "from_line": lines.get(before, {}).get("name", f"{before}号线"), "to_line": lines.get(after, {}).get("name", f"{after}号线")})
            active_leg = None
            continue
        line_id = edge["line_id"]
        destination_name = names[route.station_ids[index + 1]]
        if active_leg is None or active_leg["line_id"] != line_id:
            line = lines[line_id]
            active_leg = {"line_id": line_id, "line_name": line["name"], "color": line.get("color") or "#e23646", "stations": [names[route.station_ids[index]], destination_name]}
            legs.append(active_leg)
        else:
            active_leg["stations"].append(destination_name)
    station_names = []
    for station_id in route.station_ids:
        name = names[station_id]
        if not station_names or station_names[-1] != name:
            station_names.append(name)
    return {
        "distance_m": route.distance_m,
        "fare_yuan": fare_yuan(route.distance_m),
        "station_ids": route.station_ids,
        "edge_ids": route.edge_ids,
        "stations": station_names,
        "legs": legs,
        "transfers": transfers,
    }


def handler(root: Path):
    ui_root = root / "ui" / "route"
    content_types = {"/": ("index.html", "text/html; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8"), "/app.js": ("app.js", "application/javascript; charset=utf-8")}

    class RouteHandler(BaseHTTPRequestHandler):
        def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK):
            body = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/stations":
                network = json.loads((root / "data" / "metro-network.json").read_text())
                return self.send_json(sorted({station["name"].strip() for station in network["stations"]}))
            if path == "/api/lines":
                network = json.loads((root / "data" / "metro-network.json").read_text())
                return self.send_json(line_picker_data(network))
            if path == "/api/map":
                return self.send_json(json.loads((root / "data" / "metro-map.json").read_text()))
            if path not in content_types:
                return self.send_error(HTTPStatus.NOT_FOUND)
            filename, content_type = content_types[path]
            body = (ui_root / filename).read_bytes()
            self.send_response(HTTPStatus.OK); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

        def do_POST(self):
            if urlparse(self.path).path != "/api/route":
                return self.send_error(HTTPStatus.NOT_FOUND)
            try:
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                network = json.loads((root / "data" / "metro-network.json").read_text())
                return self.send_json(route_response(network, payload["origin"], payload["destination"]))
            except (ValueError, KeyError, json.JSONDecodeError) as error:
                return self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def log_message(self, *_):
            pass

    return RouteHandler


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8766")))
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), handler(ROOT))
    print(f"Open http://{args.host}:{args.port}")
    server.serve_forever()
