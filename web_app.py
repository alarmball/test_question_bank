"""Local web interface for the graduation-exam question bank."""

from __future__ import annotations

import argparse
import hmac
import json
import secrets
import threading
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from question_bank import DEFAULT_BANK, DEFAULT_PROGRESS, load_bank, load_progress, record_grade


ROOT = Path(__file__).resolve().parent
HTML = ROOT / "web" / "index.html"
EXPLANATIONS_HTML = ROOT / "web" / "explanations.html"
EXPLANATIONS_DATA = ROOT / "explanations.json"
LOGIN_HTML = ROOT / "web" / "login.html"


def create_handler(bank_path: Path, progress_path: Path):
    bank, questions = load_bank(bank_path)
    by_id = {question["id"]: question for question in questions}
    order = [f"{number:02d}" for number in range(1, 13)]
    rank = {number: index for index, number in enumerate(order)}
    display_questions = sorted(questions, key=lambda q: (rank.get(q["id"][:2], len(rank)), q["id"]))
    explanation_data = json.loads(EXPLANATIONS_DATA.read_text(encoding="utf-8"))
    chapters = sorted(explanation_data.get("chapters", []), key=lambda chapter: rank.get(chapter["number"], len(rank)))
    chapter_by_number = {chapter["number"]: chapter for chapter in chapters}
    if len(chapters) != 12 or len(chapter_by_number) != 12 or any(q["id"][:2] not in chapter_by_number for q in questions):
        raise ValueError("해설집의 주제와 문제은행 문항이 일치하지 않습니다.")
    lock = threading.Lock()
    sessions: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def send_bytes(self, data: bytes, content_type: str, status: int = 200, extra_headers: dict[str, str] | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for key, value in (extra_headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(data)

        def send_json(self, value, status: int = 200) -> None:
            self.send_bytes(json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)

        def redirect(self, location: str, cookie: str | None = None) -> None:
            headers = {"Location": location}
            if cookie is not None:
                headers["Set-Cookie"] = cookie
            self.send_bytes(b"", "text/plain; charset=utf-8", 303, headers)

        def role(self) -> str | None:
            raw = self.headers.get("Cookie", "")
            try:
                cookie = SimpleCookie(raw)
                token = cookie["qb_session"].value if "qb_session" in cookie else ""
            except Exception:
                return None
            with lock:
                return sessions.get(token)

        def require_role(self, role: str | None, full: bool = False) -> bool:
            if role is None:
                self.send_json({"error": "로그인이 필요합니다."}, 401)
                return False
            if full and role != "full":
                self.send_json({"error": "문제은행 접근 권한이 없습니다."}, 403)
                return False
            return True

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            role = self.role()
            if path == "/login":
                if role:
                    self.redirect("/" if role == "full" else "/explanations")
                else:
                    self.send_bytes(LOGIN_HTML.read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/health":
                self.send_json({"ok": True})
            elif path == "/api/session":
                if self.require_role(role):
                    self.send_json({"role": role})
            elif path == "/":
                if role is None:
                    self.redirect("/login")
                elif role != "full":
                    self.redirect("/explanations")
                else:
                    self.send_bytes(HTML.read_bytes(), "text/html; charset=utf-8")
            elif path == "/explanations":
                if role is None:
                    self.redirect("/login")
                else:
                    self.send_bytes(EXPLANATIONS_HTML.read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/questions":
                if not self.require_role(role, full=True):
                    return
                self.send_json({"title": bank.get("title", "문제은행"),
                                "note": bank.get("note", ""),
                                "questions": [{k: v for k, v in q.items() if k != "answer"} for q in display_questions]})
            elif path == "/api/explanations":
                if not self.require_role(role):
                    return
                allowed = chapters if role == "full" else [chapter for chapter in chapters if int(chapter["number"]) <= 10]
                self.send_json({"title": explanation_data.get("title", "해설집"),
                                "role": role,
                                "chapters": [{**chapter, "questions": [q for q in questions if q["id"][:2] == chapter["number"]]}
                                             for chapter in allowed]})
            elif path.startswith("/api/answer/"):
                if not self.require_role(role, full=True):
                    return
                qid = path.rsplit("/", 1)[-1]
                if qid in by_id:
                    self.send_json({"id": qid, "answer": by_id[qid]["answer"]})
                else:
                    self.send_json({"error": "문항을 찾지 못했습니다."}, 404)
            elif path == "/api/progress":
                if not self.require_role(role, full=True):
                    return
                with lock:
                    self.send_json(load_progress(progress_path))
            else:
                self.send_json({"error": "경로를 찾지 못했습니다."}, 404)

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path == "/api/logout":
                raw = self.headers.get("Cookie", "")
                try:
                    cookie = SimpleCookie(raw)
                    token = cookie["qb_session"].value if "qb_session" in cookie else ""
                except Exception:
                    token = ""
                with lock:
                    sessions.pop(token, None)
                self.send_bytes(b'{"ok":true}', "application/json; charset=utf-8", extra_headers={"Set-Cookie": "qb_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Strict"})
                return
            if path == "/api/login":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length < 1 or length > 1024:
                        raise ValueError("요청 크기가 올바르지 않습니다.")
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                    password = payload.get("password", "")
                    if not isinstance(password, str):
                        raise ValueError("비밀번호 형식이 올바르지 않습니다.")
                    if hmac.compare_digest(password, "9999"):
                        role = "full"
                    elif hmac.compare_digest(password, "1111"):
                        role = "limited"
                    else:
                        self.send_json({"error": "비밀번호가 올바르지 않습니다."}, 401)
                        return
                    token = secrets.token_urlsafe(32)
                    with lock:
                        sessions[token] = role
                    body = json.dumps({"ok": True, "role": role}, ensure_ascii=False).encode("utf-8")
                    self.send_bytes(body, "application/json; charset=utf-8", extra_headers={"Set-Cookie": f"qb_session={token}; Path=/; HttpOnly; SameSite=Strict"})
                except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
                    self.send_json({"error": str(exc)}, 400)
                return
            if path != "/api/grade":
                self.send_json({"error": "경로를 찾지 못했습니다."}, 404)
                return
            if not self.require_role(self.role(), full=True):
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 4096:
                    raise ValueError("요청 크기가 올바르지 않습니다.")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                qid = payload.get("id")
                grade = payload.get("grade")
                if qid not in by_id or type(grade) is not int or grade not in (0, 1, 2):
                    raise ValueError("문항 또는 점수가 올바르지 않습니다.")
                with lock:
                    progress = load_progress(progress_path)
                    record_grade(progress, progress_path, qid, grade)
                self.send_json({"ok": True, "record_count": len(progress["records"])})
            except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
                self.send_json({"error": str(exc)}, 400)

        def log_message(self, fmt: str, *args) -> None:
            print(f"{self.address_string()} - {fmt % args}", flush=True)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="졸업시험 문제은행 웹 서버")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    parser.add_argument("--progress", type=Path, default=DEFAULT_PROGRESS)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), create_handler(args.bank, args.progress))
    print(f"문제은행 실행 중: http://{args.host}:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
