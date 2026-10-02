# -*- coding: utf-8 -*-
"""Local programme editor.

A standard-library HTTP server bound to 127.0.0.1. It serves ``editor/dist``
and a small JSON API: read the programme, save one record, validate. Every
write goes through ``dataio``. Validation calls ``validate.py`` directly.

Delete, preview, and publish are later slices. This server does not upload
anything.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA_DIR, ROOT, utf8_stdout  # noqa: E402
from dataio import FILES, canonical_value, load_data, write_data  # noqa: E402
from schedule import place  # noqa: E402
from validate import validate_data  # noqa: E402

utf8_stdout()

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1"})
MAX_BODY = 1_000_000
DIST_DIR = ROOT / "editor" / "dist"

# Opaque ids for new records. Existing ids are never rewritten.
_ID_SHAPE: dict[str, tuple[str, int]] = {
    "tracks": ("T-", 2),
    "rooms": ("ROOM-", 3),
    "sessions": ("B", 3),
    "contributions": ("C-", 4),
    "people": ("PER-", 4),
    "organizations": ("ORG-", 3),
    "resources": ("RES-", 4),
    "changes": ("CHG-", 4),
}

_RECORD_PATH = re.compile(r"^/api/records/(?P<kind>[a-z]+)/(?P<rid>.+)$")
_CREATE_PATH = re.compile(r"^/api/records/(?P<kind>[a-z]+)$")


class EditError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def check_host(host: str) -> None:
    """Refuse any bind address that is not loopback."""
    if host not in LOOPBACK_HOSTS:
        raise SystemExit(
            f"The editor only listens on 127.0.0.1 (got {host})."
        )


def mentions(record_id: str, message: str) -> bool:
    """True when ``message`` cites ``record_id`` as its own token."""
    if not record_id:
        return False
    return bool(
        re.search(
            r"(?<![A-Za-z0-9-])" + re.escape(record_id) + r"(?![A-Za-z0-9-])",
            message,
        )
    )


def diagnostics_payload(data: dict, record_id: str | None = None) -> dict:
    diag = validate_data(data)
    payload: dict = {
        "diagnostics": {"errors": list(diag.errors), "warnings": list(diag.warnings)},
    }
    if record_id:
        payload["for_record"] = {
            "id": record_id,
            "errors": [msg for msg in diag.errors if mentions(record_id, msg)],
            "warnings": [msg for msg in diag.warnings if mentions(record_id, msg)],
        }
    return payload


def placement_payload(data: dict) -> dict:
    """Clock times from ``schedule.place``. The editor does not recompute them."""
    try:
        placed = place(data)
    except (TypeError, ValueError, KeyError):
        return {"sessions": {}, "contributions": {}}
    return placed


def read_programme(data_dir: Path) -> dict:
    data = load_data(data_dir)
    payload = dict(data)
    payload["placement"] = placement_payload(data)
    payload["diagnostics"] = diagnostics_payload(data)["diagnostics"]
    return payload


def generate_id(kind: str, existing: set[str]) -> str:
    prefix, width = _ID_SHAPE[kind]
    highest = 0
    for ident in existing:
        if not ident.startswith(prefix):
            continue
        tail = ident[len(prefix):]
        if tail.isdigit():
            highest = max(highest, int(tail))
    number = highest + 1
    while True:
        candidate = f"{prefix}{number:0{width}d}"
        if candidate not in existing:
            return candidate
        number += 1


def _existing_ids(records: list) -> set[str]:
    return {item["id"] for item in records if isinstance(item, dict) and isinstance(item.get("id"), str)}


def _canon_or_400(kind: str, value: object) -> None:
    try:
        canonical_value(kind, value)
    except (KeyError, TypeError, ValueError) as exc:
        raise EditError(400, f"record cannot be stored: {exc}") from exc


def update_record(data_dir: Path, kind: str, record_id: str, body: dict) -> dict:
    if kind not in FILES:
        raise EditError(404, f"unknown record type {kind}")
    if not isinstance(body, dict):
        raise EditError(400, "record must be an object")
    if "id" in body and body["id"] != record_id:
        raise EditError(400, "id is read-only")
    record = dict(body)
    record["id"] = record_id
    data = load_data(data_dir)
    if kind == "conference":
        current = data["conference"].get("id") if isinstance(data.get("conference"), dict) else None
        if current != record_id:
            raise EditError(404, "no conference record with that id")
        data["conference"] = record
        _canon_or_400(kind, data["conference"])
    else:
        items = data.get(kind)
        if not isinstance(items, list):
            raise EditError(400, f"{kind} is not a list")
        index = next((i for i, item in enumerate(items) if isinstance(item, dict) and item.get("id") == record_id), None)
        if index is None:
            raise EditError(404, f"no {kind} record {record_id}")
        items[index] = record
        _canon_or_400(kind, items)
    write_data(data, data_dir)
    stored = load_data(data_dir)
    saved = stored["conference"] if kind == "conference" else next(
        item for item in stored[kind] if item.get("id") == record_id
    )
    payload = {"record": saved, "placement": placement_payload(stored)}
    payload.update(diagnostics_payload(stored, record_id))
    return payload


def create_record(data_dir: Path, kind: str, body: dict) -> dict:
    if kind == "conference":
        raise EditError(400, "the conference record already exists")
    if kind not in _ID_SHAPE:
        raise EditError(404, f"unknown record type {kind}")
    if not isinstance(body, dict):
        raise EditError(400, "record must be an object")
    if body.get("id"):
        raise EditError(400, "do not send an id; the server generates one")
    data = load_data(data_dir)
    items = data.get(kind)
    if not isinstance(items, list):
        raise EditError(400, f"{kind} is not a list")
    record = dict(body)
    record["id"] = generate_id(kind, _existing_ids(items))
    items.append(record)
    _canon_or_400(kind, items)
    write_data(data, data_dir)
    stored = load_data(data_dir)
    saved = next(item for item in stored[kind] if item.get("id") == record["id"])
    payload = {"record": saved, "placement": placement_payload(stored)}
    payload.update(diagnostics_payload(stored, record["id"]))
    return payload


def validate_request(data_dir: Path, body: dict) -> dict:
    """Validate the files, or a draft record substituted in memory. Never writes."""
    data = load_data(data_dir)
    record_id: str | None = None
    if body.get("kind") or body.get("record"):
        kind = body.get("kind")
        record = body.get("record")
        if kind not in FILES:
            raise EditError(400, "unknown record type")
        if not isinstance(record, dict):
            raise EditError(400, "record must be an object")
        if kind == "conference":
            current = data["conference"].get("id") if isinstance(data.get("conference"), dict) else None
            if record.get("id") and record.get("id") != current:
                raise EditError(400, "id is read-only")
            draft = dict(record)
            draft["id"] = current
            data["conference"] = draft
            record_id = current if isinstance(current, str) else None
        else:
            if not isinstance(record.get("id"), str) or not record["id"]:
                raise EditError(400, "a draft record needs its existing id")
            record_id = record["id"]
            items = data.get(kind)
            if not isinstance(items, list):
                raise EditError(400, f"{kind} is not a list")
            index = next((i for i, item in enumerate(items) if isinstance(item, dict) and item.get("id") == record_id), None)
            if index is None:
                items.append(record)
            else:
                items[index] = record
    return diagnostics_payload(data, record_id)


def make_server(data_dir: Path, dist_dir: Path, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    check_host(host)
    directory = Path(data_dir)
    assets = Path(dist_dir)

    class EditorHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: object) -> None:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            try:
                if path == "/api/data":
                    with self.server.lock:  # type: ignore[attr-defined]
                        payload = read_programme(directory)
                    self._send_json(200, payload)
                    return
                if path == "/api/validate":
                    with self.server.lock:  # type: ignore[attr-defined]
                        payload = validate_request(directory, {})
                    self._send_json(200, payload)
                    return
                if path.startswith("/api/"):
                    raise EditError(404, "unknown API path")
                self._send_static(path)
            except EditError as exc:
                self._send_json(exc.status, {"error": exc.message})

        def do_POST(self) -> None:  # noqa: N802
            self._route_write("POST")

        def do_PUT(self) -> None:  # noqa: N802
            self._route_write("PUT")

        def _route_write(self, method: str) -> None:
            path = unquote(self.path.split("?", 1)[0])
            try:
                body = self._read_json()
                with self.server.lock:  # type: ignore[attr-defined]
                    if path == "/api/validate" and method == "POST":
                        payload = validate_request(directory, body)
                        status = 200
                    else:
                        created = _CREATE_PATH.fullmatch(path)
                        updated = _RECORD_PATH.fullmatch(path)
                        if method == "POST" and created:
                            payload = create_record(directory, created.group("kind"), body)
                            status = 201
                        elif method == "PUT" and updated:
                            payload = update_record(
                                directory,
                                updated.group("kind"),
                                updated.group("rid"),
                                body,
                            )
                            status = 200
                        elif path.startswith("/api/"):
                            raise EditError(404, "unknown API path")
                        else:
                            raise EditError(405, "method not allowed")
                self._send_json(status, payload)
            except EditError as exc:
                self._send_json(exc.status, {"error": exc.message})

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length") or "0")
            if length < 0 or length > MAX_BODY:
                raise EditError(413, "body is too large")
            raw = self.rfile.read(length) if length else b""
            if not raw:
                return {}
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise EditError(400, "body is not JSON") from exc
            if not isinstance(parsed, dict):
                raise EditError(400, "body must be a JSON object")
            return parsed

        def _send_json(self, status: int, payload: dict) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def _send_static(self, url_path: str) -> None:
            rel = unquote(url_path)
            if rel.endswith("/"):
                rel += "index.html"
            if rel == "":
                rel = "/index.html"
            root = assets.resolve()
            candidate = (root / rel.lstrip("/")).resolve()
            if root != candidate and root not in candidate.parents:
                raise EditError(403, "path is outside the editor build")
            if candidate.is_file():
                self._send_file(candidate)
                return
            suffix = Path(rel).suffix
            index = root / "index.html"
            if not suffix and index.is_file():
                self._send_file(index)
                return
            message = (
                "The editor build is missing. From the repository root run: "
                "cd editor && npm install && npm run build"
            )
            raw = message.encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _send_file(self, path: Path) -> None:
            raw = path.read_bytes()
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            if mime.startswith("text/") or mime in {"application/javascript", "image/svg+xml"}:
                mime += "; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(raw)

    httpd = ThreadingHTTPServer((host, port), EditorHandler)
    httpd.lock = threading.Lock()  # type: ignore[attr-defined]
    return httpd


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the local programme editor on 127.0.0.1.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--data", type=Path, default=DATA_DIR)
    parser.add_argument("--dist", type=Path, default=DIST_DIR)
    args = parser.parse_args(argv)
    check_host(args.host)
    httpd = make_server(args.data, args.dist, args.host, args.port)
    host, port = httpd.server_address[:2]
    print(f"Programme editor at http://{host}:{port}/")
    print("Listening on loopback only. This process does not deploy.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
