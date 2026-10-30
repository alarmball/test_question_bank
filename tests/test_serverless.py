"""Exercise Vercel-style stateless auth and browser-scoped progress locally."""

import http.cookiejar
import json
import os
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from question_bank import DEFAULT_BANK
from web_app import create_handler


os.environ["QB_FULL_PASSWORD"] = "test-full"
os.environ["QB_LIMITED_PASSWORD"] = "test-limited"
os.environ["QB_SESSION_SECRET"] = "test-secret-with-enough-random-looking-characters"
PROGRESS = Path(__file__).resolve().parent.parent / "tmp" / "serverless-progress-test.json"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def launch():
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(DEFAULT_BANK, PROGRESS, serverless=True, secure_cookies=False))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def client():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), NoRedirect())


def request(server, opener, path, data=None):
    body = None if data is None else json.dumps(data).encode("utf-8")
    url = f"http://127.0.0.1:{server.server_port}{path}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"} if body is not None else {})
    try:
        response = opener.open(req, timeout=5)
    except urllib.error.HTTPError as error:
        response = error
    raw = response.read()
    return response.code, json.loads(raw) if raw and response.headers.get_content_type() == "application/json" else raw


def main():
    assert not PROGRESS.exists()
    server = launch()
    try:
        guest = client()
        assert request(server, guest, "/api/questions")[0] == 401
        assert request(server, guest, "/api/login", {"password": "wrong"})[0] == 401

        limited = client()
        assert request(server, limited, "/api/login", {"password": "test-limited"})[1]["role"] == "limited"
        assert request(server, limited, "/api/questions")[0] == 403
        chapters = request(server, limited, "/api/explanations")[1]["chapters"]
        assert [ch["number"] for ch in chapters] == [f"{n:02d}" for n in range(1, 11)]

        full = client()
        assert request(server, full, "/api/login", {"password": "test-full"})[1]["role"] == "full"
        assert len(request(server, full, "/api/questions")[1]["questions"]) == 24
        grade = request(server, full, "/api/grade", {"id": "06A", "grade": 2})[1]
        assert grade["progress"]["attempts"] == 1
        assert grade["progress"]["records"] == [{"id": "06A", "grade": 2}]
        assert request(server, full, "/api/progress")[1]["attempts"] == 1
        assert not PROGRESS.exists()
    finally:
        server.shutdown()
        server.server_close()

    server = launch()
    try:
        persisted = request(server, full, "/api/progress")[1]
        assert persisted["records"] == [{"id": "06A", "grade": 2}]
        assert persisted["attempts"] == 1
        assert request(server, full, "/api/logout", {})[0] == 200
        assert request(server, full, "/api/progress")[0] == 401
    finally:
        server.shutdown()
        server.server_close()
    print("PASS: stateless access, browser progress, session restart")


if __name__ == "__main__":
    main()
