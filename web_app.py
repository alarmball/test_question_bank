"""Local web interface for the graduation-exam question bank."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
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
WRONG_NOTES_HTML = ROOT / "web" / "wrong_notes.html"

# 전체 학습 공간의 권한 식별값과 기본 비밀번호. 배포 환경에서는
# QB_FULL_PASSWORD 환경 변수가 이 기본값을 대체한다.
FULL_AUTHORITY = "1014"


def create_handler(bank_path: Path, progress_path: Path, serverless: bool = False, secure_cookies: bool | None = None):
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
    full_password = os.getenv("QB_FULL_PASSWORD", FULL_AUTHORITY if not serverless else "")
    limited_password = os.getenv("QB_LIMITED_PASSWORD", "1111" if not serverless else "")
    session_secret = os.getenv("QB_SESSION_SECRET", "")
    if secure_cookies is None:
        secure_cookies = serverless
    if serverless and (not full_password or not limited_password or not session_secret):
        raise ValueError("Vercel 환경 변수 QB_FULL_PASSWORD, QB_LIMITED_PASSWORD, QB_SESSION_SECRET이 필요합니다.")

    def sign(payload: dict) -> str:
        body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=")
        signature = base64.urlsafe_b64encode(hmac.new(session_secret.encode(), body, hashlib.sha256).digest()).rstrip(b"=")
        return body.decode() + "." + signature.decode()

    def verify(token: str) -> dict | None:
        try:
            body, signature = token.split(".", 1)
            expected = base64.urlsafe_b64encode(hmac.new(session_secret.encode(), body.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
            if not hmac.compare_digest(signature, expected):
                return None
            payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
            if payload.get("role") not in {"full", "limited"} or payload.get("exp", 0) < time.time():
                return None
            return payload
        except (ValueError, UnicodeError, KeyError, TypeError, binascii.Error):
            return None

    def cookie_header(payload: dict) -> str:
        secure = "; Secure" if secure_cookies else ""
        return f"qb_session={sign(payload)}; Max-Age=2592000; Path=/; HttpOnly; SameSite=Strict{secure}"

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

        def session(self) -> dict | None:
            raw = self.headers.get("Cookie", "")
            try:
                cookie = SimpleCookie(raw)
                token = cookie["qb_session"].value if "qb_session" in cookie else ""
            except Exception:
                return None
            if serverless:
                return verify(token)
            with lock:
                role = sessions.get(token)
            return {"role": role} if role else None

        def role(self) -> str | None:
            session = self.session()
            return session.get("role") if session else None

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
                    self.send_json({"role": role, "authority": FULL_AUTHORITY if role == "full" else None})
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
            elif path == "/wrong-notes":
                if role is None:
                    self.redirect("/login")
                elif role != "full":
                    self.redirect("/explanations")
                else:
                    self.send_bytes(WRONG_NOTES_HTML.read_bytes(), "text/html; charset=utf-8")
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
                if serverless:
                    session = self.session() or {}
                    grades = session.get("grades", {})
                    self.send_json({"version": 1, "records": [{"id": qid, "grade": grade} for qid, grade in grades.items()],
                                    "attempts": session.get("attempts", 0), "storage": "browser"})
                else:
                    with lock:
                        self.send_json(load_progress(progress_path))
            elif path == "/api/wrong-notes":
                if not self.require_role(role, full=True):
                    return
                if serverless:
                    session = self.session() or {}
                    records = [{"id": qid, "grade": grade} for qid, grade in session.get("grades", {}).items()]
                else:
                    with lock:
                        records = load_progress(progress_path).get("records", [])
                latest = {}
                for record in records:
                    if record.get("id") in by_id and record.get("grade") in (0, 1, 2):
                        latest[record["id"]] = record["grade"]
                notes = [{**by_id[qid], "grade": grade} for qid, grade in latest.items() if grade < 2]
                notes.sort(key=lambda question: (rank.get(question["id"][:2], len(rank)), question["id"]))
                self.send_json({"authority": FULL_AUTHORITY, "notes": notes})
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
                if not serverless:
                    with lock:
                        sessions.pop(token, None)
                secure = "; Secure" if secure_cookies else ""
                self.send_bytes(b'{"ok":true}', "application/json; charset=utf-8", extra_headers={"Set-Cookie": f"qb_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Strict{secure}"})
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
                    if hmac.compare_digest(password, full_password):
                        role = "full"
                    elif hmac.compare_digest(password, limited_password):
                        role = "limited"
                    else:
                        self.send_json({"error": "비밀번호가 올바르지 않습니다."}, 401)
                        return
                    if serverless:
                        issued = {"role": role, "exp": int(time.time()) + 2592000,
                                  "grades": {} if role == "full" else {}, "attempts": 0}
                        cookie = cookie_header(issued)
                    else:
                        token = secrets.token_urlsafe(32)
                        with lock:
                            sessions[token] = role
                        cookie = f"qb_session={token}; Path=/; HttpOnly; SameSite=Strict"
                    body = json.dumps({"ok": True, "role": role,
                                       "authority": FULL_AUTHORITY if role == "full" else None}, ensure_ascii=False).encode("utf-8")
                    self.send_bytes(body, "application/json; charset=utf-8", extra_headers={"Set-Cookie": cookie})
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
                if serverless:
                    session = self.session() or {}
                    grades = dict(session.get("grades", {}))
                    grades[qid] = grade
                    attempts = int(session.get("attempts", 0)) + 1
                    updated = {**session, "grades": grades, "attempts": attempts}
                    records = [{"id": key, "grade": value} for key, value in grades.items()]
                    body = json.dumps({"ok": True, "record_count": attempts,
                                       "progress": {"version": 1, "records": records, "attempts": attempts}},
                                      ensure_ascii=False).encode("utf-8")
                    self.send_bytes(body, "application/json; charset=utf-8", extra_headers={"Set-Cookie": cookie_header(updated)})
                else:
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
