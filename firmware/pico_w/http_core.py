"""Small, bounded HTTP lesson shared by MicroPython and CPython tests.

Only empty-body requests are supported. Token mode adds an access check, not TLS.
"""

MAX_HEADER_BYTES = 2048


def validate_config(config):
    if config.ENABLE_NETWORK is not True:
        raise ValueError("Networking disabled: create and review private config.py")
    for name in ("WIFI_SSID", "WIFI_PASSWORD"):
        value = getattr(config, name, "")
        if not isinstance(value, str) or not value or value.startswith("REPLACE_"):
            raise ValueError("Set " + name + " in private config.py")
    if len(config.WIFI_PASSWORD) < 8:
        raise ValueError("Use a WPA2/WPA3 lab network with a passphrase of at least 8 characters")
    if config.MODE not in ("token", "lab"):
        raise ValueError("MODE must be token or lab")
    if config.MODE == "lab" and config.ALLOW_UNAUTHENTICATED_LAB is not True:
        raise ValueError("Lab mode requires explicit ALLOW_UNAUTHENTICATED_LAB=True")
    if config.MODE == "token":
        token = config.API_TOKEN
        if (not isinstance(token, str) or len(token) < 32 or len(token) > 128
                or token.startswith("REPLACE_")
                or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in token)):
            raise ValueError("Set a fresh 32-128 character URL-safe random API_TOKEN")
    country = getattr(config, "COUNTRY", "XX")
    if len(country) != 2 or country == "XX" or not all("A" <= c <= "Z" for c in country):
        raise ValueError("Set the installation country's two-letter COUNTRY code")
    if type(config.PORT) is not int or not 1024 <= config.PORT <= 65535:
        raise ValueError("PORT must be an integer from 1024 to 65535")


def parse_request(raw):
    """Return method, exact target, lowercase headers; reject ambiguous framing."""
    if len(raw) > MAX_HEADER_BYTES or b"\r\n\r\n" not in raw:
        raise ValueError("Incomplete or oversized headers")
    head, body = raw.split(b"\r\n\r\n", 1)
    if body:
        raise ValueError("Request bodies are unsupported")
    for value in head:
        if value != 10 and value != 13 and not 32 <= value <= 126:
            raise ValueError("Headers must use printable ASCII")
    lines = head.decode("ascii").split("\r\n")
    parts = lines[0].split(" ")
    if len(parts) != 3 or parts[2] not in ("HTTP/1.0", "HTTP/1.1"):
        raise ValueError("Malformed request line")
    method, target, version = parts
    if not target.startswith("/"):
        raise ValueError("An origin-form target is required")
    headers = {}
    for line in lines[1:]:
        if ":" not in line:
            raise ValueError("Malformed header")
        name, value = line.split(":", 1)
        if not name or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-" for c in name):
            raise ValueError("Malformed header name")
        name = name.lower()
        if name in headers:
            raise ValueError("Duplicate header")
        headers[name] = value.strip()
    if version == "HTTP/1.1" and not headers.get("host"):
        raise ValueError("Host required")
    if "transfer-encoding" in headers or headers.get("content-length", "0") != "0":
        raise ValueError("Request bodies are unsupported")
    return method, target, headers


def token_matches(actual, expected):
    # Avoid an early exit on a matching prefix. This is not a timing-proof claim.
    if len(actual) != len(expected):
        return False
    mismatch = 0
    for index in range(len(expected)):
        mismatch |= ord(actual[index]) ^ ord(expected[index])
    return mismatch == 0


def dispatch(raw, mode, token, led_state):
    """Return (HTTP status, JSON-compatible payload, next LED state)."""
    try:
        method, target, headers = parse_request(raw)
    except (ValueError, UnicodeError):
        return 400, {"error": "bad request"}, led_state
    if mode not in ("token", "lab"):
        return 503, {"error": "invalid mode"}, led_state
    if mode == "token" and (not token or not token_matches(headers.get("authorization", ""), "Bearer " + token)):
        return 401, {"error": "bearer token required"}, led_state
    if method == "GET" and target in ("/", "/status"):
        return 200, {"led": bool(led_state), "mode": mode}, led_state
    if method == "POST" and target in ("/led/on", "/led/off"):
        next_state = target == "/led/on"
        return 200, {"led": next_state}, next_state
    if target in ("/", "/status", "/led/on", "/led/off"):
        return 405, {"error": "method not allowed"}, led_state
    return 404, {"error": "not found"}, led_state
