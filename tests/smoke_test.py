#!/usr/bin/env python3
"""Smoke tests for paper-reading-skills.

Covers:
  - installer install + doctor with isolated HOME
  - validator readable output + --json + --contract/--strict + existing xmlns SVG
  - bridge token auth + JSONL write + HTML marker insertion

The test uses only Python stdlib and Node.js for the installer.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "paper-reading"
VALIDATOR = SKILL / "scripts" / "validate_paper_html.py"
BRIDGE = SKILL / "scripts" / "bridge.py"
EXAMPLE = SKILL / "examples" / "minimal-paper.html"
INSTALLER = ROOT / "bin" / "install.js"


def run(cmd, *, cwd=ROOT, env=None, check=True):
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"command failed: {' '.join(map(str, cmd))}\n"
            f"exit={result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def http_json(url: str, *, method="GET", payload=None, token=None, expect_status=200):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-Paper-Bridge-Token"] = token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = resp.read().decode("utf-8")
            if resp.status != expect_status:
                raise AssertionError(f"expected HTTP {expect_status}, got {resp.status}: {body}")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        if exc.code != expect_status:
            raise AssertionError(f"expected HTTP {expect_status}, got {exc.code}: {body}")
        return json.loads(body)


def wait_health(url: str, token: str):
    deadline = time.time() + 8
    last_error = None
    while time.time() < deadline:
        try:
            return http_json(url, token=token)
        except Exception as exc:  # server not ready yet
            last_error = exc
            time.sleep(0.1)
    raise AssertionError(f"bridge did not become ready: {last_error}")


def test_validator():
    result = run([sys.executable, str(VALIDATOR), str(EXAMPLE), "--contract", "--strict", "--json"])
    payload = json.loads(result.stdout)
    assert payload["summary"]["ok"] is True, result.stdout
    assert payload["summary"]["error_count"] == 0, result.stdout
    assert payload["summary"]["warn_count"] == 0, result.stdout
    assert payload["summary"]["contract"] is True, result.stdout
    assert payload["summary"]["strict"] is True, result.stdout

    # 默认模式下，只有 warning 不失败；strict 模式下 warning 会导致失败。
    with tempfile.TemporaryDirectory(prefix="paper-strict-") as tmp:
        warn_html = Path(tmp) / "warn-only.html"
        warn_html.write_text(
            """<!doctype html><html><body>
<div class="formula-card">
  <div class="formula-card__equation formula-card__equation-rendered" data-katex="x"></div>
  <div class="formula-card__equation formula-card__equation-plain"></div>
</div>
</body></html>""",
            encoding="utf-8",
        )
        default_result = run([sys.executable, str(VALIDATOR), str(warn_html), "--json"])
        assert default_result.returncode == 0, default_result.stdout
        strict_result = run([sys.executable, str(VALIDATOR), str(warn_html), "--strict", "--json"], check=False)
        assert strict_result.returncode == 1, strict_result.stdout

    with tempfile.TemporaryDirectory(prefix="paper-validator-") as tmp:
        html_path = Path(tmp) / "existing-xmlns.html"
        html_path.write_text(
            """<!doctype html><html><body>
<svg class="svg-figure concept-visual" width="120" height="80" viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg" font-family="Arial, sans-serif">
  <rect x="0" y="0" width="120" height="80" fill="#ffffff"/>
  <text x="60" y="42" text-anchor="middle" fill="#000000">OK</text>
</svg>
</body></html>""",
            encoding="utf-8",
        )
        result = run([sys.executable, str(VALIDATOR), str(html_path), "--json"])
        payload = json.loads(result.stdout)
        assert payload["summary"]["ok"] is True, result.stdout


def test_installer():
    if shutil.which("node") is None:
        raise AssertionError("node is required for installer smoke test")
    with tempfile.TemporaryDirectory(prefix="paper-install-home-") as home:
        env = os.environ.copy()
        env["PAPER_READING_INSTALL_HOME"] = home
        run(["node", str(INSTALLER), "install"], env=env)
        run(["node", str(INSTALLER), "doctor"], env=env)
        claude_skill = Path(home) / ".claude" / "skills" / "paper-reading" / "SKILL.md"
        codex_skill = Path(home) / ".codex" / "skills" / "paper-reading" / "SKILL.md"
        assert claude_skill.exists(), claude_skill
        assert codex_skill.exists(), codex_skill


def test_bridge_token_writeback():
    with tempfile.TemporaryDirectory(prefix="paper-bridge-") as tmp:
        page = Path(tmp) / "paper.html"
        log = Path(tmp) / "requests.jsonl"
        page.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        port = free_port()
        token = "local-test-token"
        proc = subprocess.Popen(
            [
                sys.executable,
                str(BRIDGE),
                "--page", str(page),
                "--log", str(log),
                "--port", str(port),
                "--token", token,
            ],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            base = f"http://127.0.0.1:{port}"
            wait_health(base + "/healthz", token)
            http_json(base + "/healthz", expect_status=401)
            payload = {
                "id": "smoke-mark-1",
                "kind": "logic",
                "text": "研究目的：把论文中的旧瓶颈、关键动作和证据链组织成一篇可连续阅读、可追问、可重组的长文。",
                "anchorText": "研究目的：把论文中的旧瓶颈、关键动作和证据链组织成一篇可连续阅读、可追问、可重组的长文。",
                "question": "这条链路怎么理解？",
                "sectionId": "thesis",
                "sectionTitle": "研究目的",
                "pageTitle": "Paper Reading Minimal Example",
                "url": "http://localhost/paper.html",
            }
            response = http_json(
                base + "/__paper_annotation",
                method="POST",
                payload=payload,
                token=token,
            )
            assert response["ok"] is True, response
            assert log.exists(), log
            rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
            assert rows and rows[-1]["id"] == "smoke-mark-1", rows
            updated = page.read_text(encoding="utf-8")
            assert 'data-question-id="smoke-mark-1"' in updated, updated
            assert 'class="annotation-highlight"' in updated, updated
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)


def main():
    tests = [test_validator, test_installer, test_bridge_token_writeback]
    for test in tests:
        test()
        print(f"✓ {test.__name__}")
    print("All smoke tests passed.")


if __name__ == "__main__":
    main()
