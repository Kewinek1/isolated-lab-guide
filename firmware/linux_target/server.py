#!/usr/bin/env python3
"""Isolated-lab IDOR lesson. Dummy records; no shell, files, or target scanning.

"insecure" authenticates a token but omits the record owner check.
"secure" adds that owner check; it is still a toy HTTP server without TLS.
"""
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import ipaddress
import json
from pathlib import Path

RECORDS = {
    "1": {"id": "1", "owner": "alpha", "message": "Fictional record A"},
    "2": {"id": "2", "owner": "beta", "message": "Fictional record B"},
}


def validate_tokens(tokens):
    if not isinstance(tokens, dict) or set(tokens) != {"alpha", "beta"}:
        raise ValueError("Token file must contain exactly alpha and beta")
    for value in tokens.values():
        if (not isinstance(value, str) or not 32 <= len(value) <= 128
                or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in value)):
            raise ValueError("Use generated 32-128 character URL-safe tokens")
    if tokens["alpha"] == tokens["beta"]:
        raise ValueError("The two identities need different tokens")
    return tokens


def load_tokens(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        raw = stream.read(4097)
    if len(raw) > 4096:
        raise ValueError("Token file too large")
    return validate_tokens(json.loads(raw))


class LabServer(HTTPServer):
    allow_reuse_address = True

    def __init__(self, address, mode, tokens):
        if mode not in ("secure", "insecure"):
            raise ValueError("Unknown mode")
        self.mode = mode
        self.tokens = validate_tokens(tokens)
        super().__init__(address, LabHandler)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(3)
        return connection, address


class LabHandler(BaseHTTPRequestHandler):
    server_version = "LabLesson"
    sys_version = ""

    def log_message(self, *_args):
        pass  # No client addresses, headers, tokens, or paths are logged.

    def respond(self, status, data):
        body = json.dumps(data, sort_keys=True).encode("utf-8") + b"\n"
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        if status == 401:
            self.send_header("WWW-Authenticate", 'Bearer realm="lab"')
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def do_GET(self):
        authorization = self.headers.get_all("Authorization", [])
        if len(authorization) != 1 or not authorization[0].startswith("Bearer "):
            self.respond(401, {"error": "bearer token required"})
            return
        supplied = authorization[0][7:]
        identity = None
        for candidate, token in self.server.tokens.items():
            # Header decoding is Latin-1; bytes support constant-time comparison.
            if hmac.compare_digest(supplied.encode("latin-1"), token.encode("ascii")):
                identity = candidate
        if identity is None:
            self.respond(401, {"error": "invalid token"})
            return
        if self.path == "/status":
            self.respond(200, {"mode": self.server.mode, "identity": identity})
            return
        if not self.path.startswith("/records/"):
            self.respond(404, {"error": "not found"})
            return
        record = RECORDS.get(self.path[len("/records/"):])
        if record is None:
            self.respond(404, {"error": "not found"})
            return
        # The only intentionally missing check in insecure mode is ownership.
        if self.server.mode == "secure" and record["owner"] != identity:
            self.respond(403, {"error": "record belongs to another identity"})
            return
        self.respond(200, record)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("secure", "insecure"), default="secure")
    parser.add_argument("--bind", default="127.0.0.1", help="Exact IPv4 address; default loopback")
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--tokens-file", required=True, type=Path)
    parser.add_argument("--allow-lab-listener", action="store_true",
                        help="Acknowledge a listener on a verified isolated lab interface")
    args = parser.parse_args(argv)
    try:
        address = ipaddress.IPv4Address(args.bind)
    except ipaddress.AddressValueError:
        parser.error("--bind must be a literal IPv4 address")
    if address.is_unspecified or address.is_multicast or address == ipaddress.IPv4Address("255.255.255.255"):
        parser.error("--bind requires one concrete unicast interface address")
    if not address.is_loopback and not args.allow_lab_listener:
        parser.error("A non-loopback bind requires --allow-lab-listener after isolation checks")
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be from 1024 to 65535")
    return args


def main():
    args = parse_args()
    try:
        tokens = load_tokens(args.tokens_file)
    except (OSError, ValueError) as error:
        raise SystemExit("Token file rejected: " + str(error)) from None
    with LabServer((args.bind, args.port), args.mode, tokens) as server:
        print("Lesson mode:", args.mode, "| HTTP plaintext | Ctrl+C stops the server", flush=True)
        print("Listening on the selected interface, TCP port", args.port, flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Stopped.")


if __name__ == "__main__":
    main()
