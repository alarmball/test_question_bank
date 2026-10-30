"""Vercel Python Function entry point."""

import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from question_bank import DEFAULT_BANK, DEFAULT_PROGRESS  # noqa: E402
from web_app import create_handler  # noqa: E402


_app_handler = create_handler(DEFAULT_BANK, DEFAULT_PROGRESS, serverless=True)


class handler(BaseHTTPRequestHandler):
    """Vercel's Python runtime discovers this explicit HTTP handler class."""

    send_bytes = _app_handler.send_bytes
    send_json = _app_handler.send_json
    redirect = _app_handler.redirect
    session = _app_handler.session
    role = _app_handler.role
    require_role = _app_handler.require_role
    do_GET = _app_handler.do_GET
    do_POST = _app_handler.do_POST
    log_message = _app_handler.log_message
