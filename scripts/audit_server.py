#!/usr/bin/env python3
"""Local-only server for reviewing unresolved PDF distances."""
from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.apply_pdf_distances import apply_distances


def resolve(root: Path, edge_id: str, distance_m: int) -> dict:
    if not isinstance(distance_m, int) or distance_m <= 0:
        raise ValueError("distance_m must be a positive integer")
    audit_path, manual_path, network_path = root / "data/distance-audit.json", root / "data/manual-distances.json", root / "data/metro-network.json"
    audit = json.loads(audit_path.read_text())
    if edge_id not in {entry["edge_id"] for entry in audit["entries"]}:
        raise ValueError("edge is not awaiting review")
    audit["entries"] = [entry for entry in audit["entries"] if entry["edge_id"] != edge_id]
    manual = json.loads(manual_path.read_text()) if manual_path.exists() else {"unit": "m", "entries": []}
    entry = {"edge_id": edge_id, "distance_m": distance_m, "verification": "reviewed"}
    manual["entries"] = [item for item in manual["entries"] if item["edge_id"] != edge_id] + [entry]
    network = apply_distances(json.loads(network_path.read_text()), {"entries": [entry]})
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    manual_path.write_text(json.dumps(manual, ensure_ascii=False, indent=2) + "\n")
    network_path.write_text(json.dumps(network, ensure_ascii=False, indent=2) + "\n")
    return {"remaining": len(audit["entries"])}


def handler(root: Path):
    class AuditHandler(BaseHTTPRequestHandler):
        def send_json(self, payload, status=HTTPStatus.OK):
            body = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def do_GET(self):
            if self.path == "/api/audit": return self.send_json(json.loads((root / "data/distance-audit.json").read_text()))
            if self.path == "/api/network": return self.send_json(json.loads((root / "data/metro-network.json").read_text()))
            if self.path == "/":
                body=(root / "ui/audit/index.html").read_bytes(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); return self.wfile.write(body)
            self.send_error(404)
        def do_POST(self):
            if self.path != "/api/resolve": return self.send_error(404)
            try:
                payload=json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                return self.send_json(resolve(root, payload["edge_id"], payload["distance_m"]))
            except (ValueError, KeyError, json.JSONDecodeError) as error: return self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        def log_message(self, *_): pass
    return AuditHandler


if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--port", type=int, default=8765); args=parser.parse_args()
    server=ThreadingHTTPServer(("127.0.0.1", args.port), handler(ROOT))
    print(f"Open http://127.0.0.1:{args.port}"); server.serve_forever()
