# -*- coding: utf-8 -*-
"""Review, preview, and publish. Publish tests never push."""
from __future__ import annotations

import json
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from dataio import write_data
from edit import make_server, publish_programme, publish_status, summarize_programmes
from programme_factory import base


class _Result:
    def __init__(self, code: int = 0, out: str = "", err: str = "") -> None:
        self.returncode = code
        self.stdout = out
        self.stderr = err


def _serve(tmp_path: Path, data: dict | None = None):
    write_data(data or base(), tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>editor</title>", encoding="utf-8")
    httpd = make_server(tmp_path, dist, "127.0.0.1", 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def _request(port: int, method: str, path: str, body: dict | None = None) -> tuple[int, dict | str]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data is not None else {}
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    last_error: Exception | None = None
    for _ in range(30):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
                content_type = response.headers.get("Content-Type", "")
                if "json" in content_type:
                    return response.status, json.loads(raw.decode("utf-8"))
                return response.status, raw.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                return exc.code, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return exc.code, raw
        except urllib.error.URLError as exc:
            last_error = exc
            time.sleep(0.05)
    raise AssertionError(f"editor did not accept a connection: {last_error}")


def test_summary_names_moves_cancels_and_renames() -> None:
    before = base()
    after = base()
    after["contributions"][0]["session_id"] = "B002"
    after["contributions"][1]["status"] = "cancelled"
    after["people"][0]["family"] = "Changed"
    summary = summarize_programmes(before, after)
    assert summary == ["1 talk moved, 1 talk cancelled, 1 name corrected."]


def test_publish_is_blocked_while_validation_fails(tmp_path: Path) -> None:
    data = base()
    data["contributions"][0]["authors"][0]["person_id"] = "PER-9999"
    httpd = _serve(tmp_path, data)
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout
    try:
        status, payload = _request(httpd.server_address[1], "POST", "/api/publish", {})
        assert status == 409
        assert isinstance(payload, dict)
        assert payload["errors"]
        assert "blocked" in payload["error"]
        again = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout
        assert again == head
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_publish_opens_a_dev_pr_or_prints_the_compare_url(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    data_dir = repo / "data"
    data_dir.mkdir(parents=True)
    write_data(base(), data_dir)
    calls: list[list[str]] = []

    def runner(args, cwd, capture_output, text):
        calls.append(list(args))
        if args[:2] == ["gh", "pr"]:
            return _Result(0, "https://github.com/shadowcaramel/Conference-schedule/pull/50\n")
        return _Result(0, "")

    opened = publish_programme(repo, data_dir, "1 talk moved.", runner)
    assert opened["pull_request"] == "https://github.com/shadowcaramel/Conference-schedule/pull/50"
    create = next(args for args in calls if args[:2] == ["gh", "pr"])
    assert create[3:5] == ["--base", "dev"]
    assert all(arg != "main" for args in calls for arg in args)

    def missing(args, cwd, capture_output, text):
        if args[0] == "gh":
            raise FileNotFoundError(args[0])
        return _Result(0, "")

    fallback = publish_programme(repo, data_dir, "1 talk moved.", missing)
    assert fallback["pull_request"] is None
    assert "compare/dev...editor/programme-" in fallback["compare_url"]
    assert "gh is not available" in fallback["detail"]


def test_publish_status_reads_check_rollups() -> None:
    def runner(args, capture_output, text, cwd=None):
        assert args[:3] == ["gh", "pr", "view"]
        return _Result(
            0,
            json.dumps(
                {
                    "state": "MERGED",
                    "url": args[3],
                    "statusCheckRollup": [
                        {"name": "test", "conclusion": "success"},
                        {"name": "pages", "conclusion": "success"},
                    ],
                }
            ),
        )

    status = publish_status("https://example.test/pull/50", runner)
    assert status["state"] == "MERGED"
    assert status["checks"][1] == {"name": "pages", "status": "success"}


def test_preview_serves_the_site_built_from_draft_data(tmp_path: Path) -> None:
    httpd = _serve(tmp_path)
    port = httpd.server_address[1]
    try:
        status, payload = _request(port, "POST", "/api/preview", {})
        assert status == 200
        assert isinstance(payload, dict)
        page_status, page = _request(port, "GET", payload["url"])
        assert page_status == 200
        assert isinstance(page, str)
        assert "data.js" in page or "PROGRAMME" in page
        script_status, script = _request(port, "GET", "/preview/data.js")
        assert script_status == 200
        assert isinstance(script, str)
        assert "Title C-01" in script
    finally:
        httpd.shutdown()
        httpd.server_close()
