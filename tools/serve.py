#!/usr/bin/env python3
"""Serve the field manual on loopback only. No uploads or network configuration."""
import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

PUBLIC = Path(__file__).resolve().parents[1]
ROOT_FILES = {"README.md", ".gitignore", "PUBLIC_MANIFEST.json", "VALIDATION.md"}
PUBLIC_DIRS = {"app", "docs", "network", "firmware", "games", "tools", "tests", "figures"}
SECRET_NAMES = {"config.py", ".env", "server.properties", "eula.txt", "server-settings.json", "whitelist.json"}

def public_file(raw_path, root=PUBLIC):
    path = unquote(raw_path)
    if "\x00" in path or "\\" in path:
        return None
    parts = Path(path.lstrip("/")).parts
    if not parts or any(p in {".", "..", "private", "__pycache__", ".git"} for p in parts):
        return None
    if parts[0] not in PUBLIC_DIRS and path.lstrip("/") not in ROOT_FILES:
        return None
    if any(p.startswith(".") or ".local." in p for p in parts) and path != "/.gitignore":
        return None
    if parts[-1] in SECRET_NAMES or Path(parts[-1]).suffix in {".pyc", ".log", ".pcap", ".jpg", ".png", ".zip", ".key"}:
        return None
    candidate = root.joinpath(*parts)
    # Serving is restricted to the reviewed release filenames, never a directory.
    try:
        manifest = root / "PUBLIC_MANIFEST.json"
        if manifest.is_symlink():
            return None
        allowed = json.loads(manifest.read_text())["files"]
        if candidate.relative_to(root).as_posix() not in allowed and path != "/PUBLIC_MANIFEST.json":
            return None
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if any(root.joinpath(*parts[:i]).is_symlink() for i in range(1, len(parts)+1)):
        return None
    if not candidate.resolve().is_relative_to(root.resolve()) or not candidate.is_file():
        return None
    return candidate

class Handler(BaseHTTPRequestHandler):
    private_dir = None
    def log_message(self, *_):
        pass  # URLs and local identifiers do not belong in access logs.
    def send_bytes(self, data, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)
    def do_HEAD(self):
        self.do_GET()
    def do_GET(self):
        host = self.headers.get("Host", "")
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        origin = self.headers.get("Origin")
        if host not in allowed or (origin and origin not in {"http://" + h for h in allowed}) or self.headers.get("Sec-Fetch-Site") == "cross-site":
            return self.send_bytes(b"Local origin required.\n", "text/plain", 403)
        path = urlsplit(self.path).path
        if path == "/api/mode":
            return self.send_bytes(json.dumps({"private_available": self.private_dir is not None}).encode(), "application/json")
        if path.startswith("/api/private"):
            if self.private_dir is None:
                return self.send_bytes(b"Private mode is disabled.\n", "text/plain", 404)
            routes = {"/api/private-profile": ("profile.json", "application/json"),
                      "/api/private-guide": ("START-HERE.md", "text/plain; charset=utf-8"),
                      "/api/private-inventory": ("INVENTORY.md", "text/plain; charset=utf-8")}
            if path not in routes:
                return self.send_bytes(b"Not found.\n", "text/plain", 404)
            name, mime = routes[path]
            target = self.private_dir / name
            try:
                if target.is_symlink() or not target.resolve().is_relative_to(self.private_dir):
                    raise OSError("Invalid path")
                content = target.read_bytes()
                if name == "profile.json":
                    # Only display metadata is exposed. Runtime credentials use another file.
                    data = json.loads(content)
                    content = json.dumps({k: data[k] for k in ("labels", "inventory", "address_note")}).encode()
                return self.send_bytes(content, mime)
            except (OSError, ValueError, KeyError):
                return self.send_bytes(b"Private document unavailable.\n", "text/plain", 404)
        target = public_file("/app/index.html" if path == "/" else path)
        if target is None:
            return self.send_bytes(b"Not found.\n", "text/plain", 404)
        mime = mimetypes.guess_type(str(target))[0] or "text/plain"
        if target.suffix in {".md", ".py", ".ino", ".h", ".sh", ".example"}:
            mime = "text/plain"
        return self.send_bytes(target.read_bytes(), mime + ("; charset=utf-8" if mime.startswith("text/") else ""))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--private-dir", type=Path, help="Explicit opt-in to three private display documents")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use an unprivileged port from 1024 to 65535")
    if args.private_dir:
        root = args.private_dir.resolve()
        if root.is_relative_to(PUBLIC) or not (root / "profile.json").is_file():
            parser.error("Private directory must be outside the public package and contain profile.json")
        Handler.private_dir = root
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Field manual: http://127.0.0.1:{args.port}", flush=True)
    print("Private display enabled." if args.private_dir else "Public examples only.", flush=True)
    print("Loopback only. Stop with Ctrl+C.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
