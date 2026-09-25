"""Local web interface for the bundled GeoResearch pipeline."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs"
STATIC = ROOT / "static"
ENV_FILE = ROOT / ".env"
KEYS = ("ANTHROPIC_API_KEY", "PERPLEXITY_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY")
FILES = {
    "twitter_intel.json": "Social research",
    "deep_research.json": "Source research",
    "audit.md": "Source audit",
    "paper_draft.md": "Research draft",
    "script.md": "YouTube script",
    "paper.tex": "LaTeX paper",
    "refs.bib": "References",
    "paper.pdf": "PDF paper",
}
MIME = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8", ".md": "text/plain; charset=utf-8", ".tex": "text/plain; charset=utf-8", ".bib": "text/plain; charset=utf-8", ".pdf": "application/pdf"}
lock = threading.Lock()
active_run: str | None = None


def env_values() -> dict[str, str]:
    values = {key: os.environ.get(key, "") for key in KEYS}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                if key.strip() in KEYS:
                    values[key.strip()] = value.strip().strip('"\'')
    return values


def configured(value: str) -> bool:
    return bool(value) and "xxxx" not in value.lower()


def metadata(run_id: str) -> dict:
    if not re.fullmatch(r"[a-f0-9]{12}", run_id):
        raise FileNotFoundError
    path = RUNS / run_id / "meta.json"
    if not path.is_file():
        raise FileNotFoundError
    return json.loads(path.read_text(encoding="utf-8"))


def save_meta(run_id: str, data: dict) -> None:
    (RUNS / run_id / "meta.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def output_files(run_id: str) -> list[dict]:
    base = RUNS / run_id / "output"
    found = []
    if base.exists():
        for path in base.rglob("*"):
            if path.is_file() and path.name in FILES:
                found.append({"name": path.name, "label": FILES[path.name], "bytes": path.stat().st_size})
    return sorted(found, key=lambda item: list(FILES).index(item["name"]))


def run_pipeline(run_id: str, mode: str, topic: str) -> None:
    global active_run
    directory = RUNS / run_id
    args = [sys.executable, "-u", str(ROOT / "pipeline.py")]
    if mode == "social":
        args.append("--twitter")
    elif mode == "research":
        args.append("--research")
    args.append(topic)
    data = metadata(run_id)
    data["status"] = "running"
    save_meta(run_id, data)
    try:
        with (directory / "run.log").open("w", encoding="utf-8", errors="replace") as log:
            process = subprocess.run(args, cwd=directory, stdout=log, stderr=subprocess.STDOUT, check=False)
        log_text = (directory / "run.log").read_text(encoding="utf-8", errors="replace")
        log_text = re.sub(r"\x1b\[[0-9;]*m", "", log_text)
        partial = bool(re.search(r"(?:Twitter Intelligence|Deep Web Research|Merge/Build|LaTeX generation) failed:", log_text, re.IGNORECASE))
        data["status"] = "failed" if process.returncode else "partial" if partial else "complete"
        data["exit_code"] = process.returncode
    except Exception as exc:
        (directory / "run.log").write_text(str(exc), encoding="utf-8")
        data["status"] = "failed"
        data["error"] = str(exc)
    finally:
        data["finished_at"] = datetime.now().astimezone().isoformat()
        save_meta(run_id, data)
        with lock:
            active_run = None


class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, status: int, body: bytes, content_type: str, *, filename: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status: int, data: dict | list) -> None:
        self.send_bytes(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), MIME[".json"])

    def read_json(self) -> dict:
        if self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json":
            raise ValueError("Send JSON data.")
        if self.headers.get("Origin") not in (None, f"http://{self.headers.get('Host')}"):
            raise ValueError("This request must come from the local app.")
        size = int(self.headers.get("Content-Length", "0"))
        if size < 1 or size > 10000:
            raise ValueError("Request is empty or too large.")
        data = json.loads(self.rfile.read(size))
        if not isinstance(data, dict):
            raise ValueError("Invalid request.")
        return data

    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)
        try:
            if path == "/api/state":
                keys = env_values()
                self.send_json(200, {"keys": {key: configured(keys[key]) for key in KEYS}, "active_run": active_run})
            elif path == "/api/runs":
                runs = []
                for entry in RUNS.iterdir():
                    if entry.is_dir():
                        try:
                            data = metadata(entry.name)
                            data["files"] = output_files(entry.name)
                            runs.append(data)
                        except (FileNotFoundError, ValueError, json.JSONDecodeError):
                            continue
                self.send_json(200, sorted(runs, key=lambda item: item["created_at"], reverse=True))
            elif re.fullmatch(r"/api/runs/[a-f0-9]{12}", path):
                run_id = path.rsplit("/", 1)[1]
                data = metadata(run_id)
                data["files"] = output_files(run_id)
                log = RUNS / run_id / "run.log"
                data["log"] = re.sub(r"\x1b\[[0-9;]*m", "", log.read_text(encoding="utf-8", errors="replace")[-5000:]) if log.exists() else ""
                self.send_json(200, data)
            elif re.fullmatch(r"/api/runs/[a-f0-9]{12}/files/[^/]+", path):
                _, _, _, run_id, _, name = path.split("/", 5)
                if name not in FILES:
                    raise FileNotFoundError
                base = RUNS / run_id / "output"
                candidates = list(base.rglob(name)) if base.exists() else []
                if not candidates:
                    raise FileNotFoundError
                file = candidates[0]
                download = "download=1" in urlparse(self.path).query
                self.send_bytes(200, file.read_bytes(), MIME.get(file.suffix, "application/octet-stream"), filename=name if download else None)
            else:
                file = STATIC / ("index.html" if path == "/" else path.lstrip("/"))
                if file.resolve().is_relative_to(STATIC.resolve()) and file.is_file() and file.suffix in (".html", ".css", ".js"):
                    self.send_bytes(200, file.read_bytes(), MIME[file.suffix])
                else:
                    raise FileNotFoundError
        except FileNotFoundError:
            self.send_json(404, {"error": "Not found."})

    def do_POST(self) -> None:
        global active_run
        try:
            data = self.read_json()
            if self.path == "/api/settings":
                supplied = {key: str(data.get(key, "")).strip() for key in KEYS}
                if any("\n" in value or "\r" in value for value in supplied.values()):
                    raise ValueError("API keys must each be a single line.")
                if not any(supplied.values()):
                    raise ValueError("Enter at least one API key.")
                existing = env_values()
                existing.update({key: value for key, value in supplied.items() if value})
                retained = []
                if ENV_FILE.exists():
                    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
                        if "=" not in line or line.split("=", 1)[0].strip() not in KEYS:
                            retained.append(line)
                ENV_FILE.write_text("\n".join(retained + [f"{key}={existing[key]}" for key in KEYS]) + "\n", encoding="utf-8")
                self.send_json(200, {"saved": True, "keys": {key: configured(existing[key]) for key in KEYS}})
            elif self.path == "/api/runs":
                topic = str(data.get("topic", "")).strip()
                mode = data.get("mode")
                if not 3 <= len(topic) <= 180 or any(ord(char) < 32 for char in topic):
                    raise ValueError("Enter a topic between 3 and 180 characters.")
                if mode not in ("full", "social", "research"):
                    raise ValueError("Choose a research type.")
                required = KEYS if mode == "full" else (("ANTHROPIC_API_KEY", "PERPLEXITY_API_KEY") if mode == "social" else ("ANTHROPIC_API_KEY", "PERPLEXITY_API_KEY", "GOOGLE_API_KEY"))
                missing = [key for key in required if not configured(env_values()[key])]
                if missing:
                    raise ValueError("Add the required API keys in Settings before starting.")
                with lock:
                    if active_run:
                        self.send_json(409, {"error": "A research run is already in progress."})
                        return
                    run_id = uuid.uuid4().hex[:12]
                    active_run = run_id
                (RUNS / run_id).mkdir()
                entry = {"id": run_id, "topic": topic, "mode": mode, "status": "queued", "created_at": datetime.now().astimezone().isoformat()}
                save_meta(run_id, entry)
                threading.Thread(target=run_pipeline, args=(run_id, mode, topic), daemon=True).start()
                self.send_json(201, entry)
            else:
                self.send_json(404, {"error": "Not found."})
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})


if __name__ == "__main__":
    RUNS.mkdir(exist_ok=True)
    host, port = "127.0.0.1", int(os.environ.get("GEORESEARCH_PORT", "8765"))
    print(f"GeoResearch Studio: http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
