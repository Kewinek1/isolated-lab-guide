"""Pico W MicroPython: an explicitly enabled isolated-lab HTTP/LED service."""
from machine import Pin
import json
import network
import socket
import sys
import time

from http_core import MAX_HEADER_BYTES, dispatch, validate_config


def read_headers(client):
    request = b""
    start = time.ticks_ms()
    client.settimeout(2)
    while b"\r\n\r\n" not in request:
        if time.ticks_diff(time.ticks_ms(), start) >= 3000:
            raise ValueError("Request deadline exceeded")
        room = MAX_HEADER_BYTES - len(request)
        if room <= 0:
            raise ValueError("Header too large")
        block = client.recv(min(room, 256))
        if not block:
            raise ValueError("Incomplete request")
        request += block
    return request


def respond(client, status, payload):
    reasons = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 404: "Not Found",
               405: "Method Not Allowed", 503: "Service Unavailable"}
    body = json.dumps(payload).encode("utf-8")
    headers = ("HTTP/1.1 %d %s\r\nContent-Type: application/json\r\n"
               "Content-Length: %d\r\nConnection: close\r\nCache-Control: no-store\r\n"
               % (status, reasons[status], len(body)))
    if status == 401:
        headers += 'WWW-Authenticate: Bearer realm="lab"\r\n'
    response = (headers + "\r\n").encode("ascii") + body
    sent = 0
    while sent < len(response):
        count = client.send(response[sent:])
        if not count:
            raise OSError("Connection closed during response")
        sent += count


def run():
    led = Pin("LED", Pin.OUT, value=0)  # Pico W onboard LED is not GPIO25.
    wlan = network.WLAN()
    wlan.active(False)
    try:
        import config
    except ImportError:
        print("No private config.py. WiFi remains off. Read firmware/README.md.")
        return
    try:
        validate_config(config)
    except (ValueError, AttributeError, TypeError) as error:
        print("Configuration rejected:", error)
        return
    print("MicroPython:", sys.version)
    print("Mode:", config.MODE, "| HTTP plaintext | isolated lab only")
    # RP2 also supports rp2.country() on releases without network.country().
    if hasattr(network, "country"):
        network.country(config.COUNTRY)
    else:
        import rp2
        rp2.country(config.COUNTRY)
    server = None
    try:
        wlan.active(True)
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        start = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), start) > 20000:
                raise RuntimeError("WiFi join timed out; verify lab SSID, password and 2.4 GHz")
            time.sleep_ms(100)
        if hasattr(wlan, "ipconfig"):
            address = wlan.ipconfig("addr4")[0]
        else:
            address = wlan.ifconfig()[0]
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(socket.getaddrinfo(address, config.PORT, socket.AF_INET, socket.SOCK_STREAM)[0][-1])
        server.listen(1)
        server.settimeout(1)
        print("LOCAL ONLY: http://%s:%d/status" % (address, config.PORT))
        print("Keep this address and configuration out of the public repository.")
        while wlan.isconnected():
            try:
                client, _peer = server.accept()
            except OSError:
                continue
            try:
                request = read_headers(client)
                status, payload, next_state = dispatch(request, config.MODE, config.API_TOKEN, led.value())
                led.value(1 if next_state else 0)
                respond(client, status, payload)
            except ValueError:
                try:
                    respond(client, 400, {"error": "bad request"})
                except OSError:
                    pass
            except OSError:
                pass  # Per-client timeout or disconnect; no request/token logging.
            finally:
                client.close()
    except KeyboardInterrupt:
        print("Stopped from USB terminal.")
    finally:
        if server is not None:
            server.close()
        wlan.active(False)
        led.off()
        print("Service stopped; WiFi off; LED off.")


if __name__ == "__main__":
    run()
