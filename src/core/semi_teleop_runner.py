# -*- coding: utf-8 -*-
"""
Arranque do modo semi-autônomo: servidor HTTP do rosto + Chromium kiosk + joystick.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _make_status_handler(
    robot_face_dir: Path,
    status_path: Path,
) -> type[SimpleHTTPRequestHandler]:
    class TeleopFaceHTTPRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(robot_face_dir), **kwargs)

        def do_GET(self) -> None:
            p = urlparse(self.path).path
            if p == "/api/teleop_status":
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                raw = b"{}"
                try:
                    if status_path.is_file():
                        raw = status_path.read_bytes()
                except OSError:
                    pass
                self.wfile.write(raw)
                return
            return super().do_GET()

        def log_message(self, format: str, *args) -> None:
            pass

    return TeleopFaceHTTPRequestHandler


def start_teleop_face_server(
    robot_face_dir: Path,
    status_path: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> tuple[ThreadingHTTPServer, threading.Thread]:
    handler = _make_status_handler(robot_face_dir, status_path)
    httpd = ThreadingHTTPServer((host, port), handler)
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    return httpd, th


def _find_chromium() -> str | None:
    for name in ("chromium-browser", "chromium", "google-chrome-stable", "google-chrome"):
        p = shutil.which(name)
        if p:
            return p
    return None


def run_semi_teleop_session(
    port: int | None = None,
    status_path: Path | None = None,
) -> int:
    """
    Inicia servidor do rosto, Chromium em kiosk e joystick até o utilizador sair (Start no comando).
    Retorna o código de saída do processo do joystick.
    """
    root = _project_root()
    face_dir = root / "display" / "robot_face"
    if not face_dir.is_dir():
        print(f"ERRO: pasta do rosto inexistente: {face_dir}", file=sys.stderr)
        return 2

    status = status_path or (face_dir / "teleop_status.json")
    status.parent.mkdir(parents=True, exist_ok=True)
    try:
        status.write_text("{}", encoding="utf-8")
    except OSError as e:
        print(f"ERRO: não foi possível criar {status}: {e}", file=sys.stderr)
        return 2

    prt = port or int(os.environ.get("ROBO_FACE_HTTP_PORT", "8765"))
    os.environ["ROBO_TELEOP_FACE_STATUS_FILE"] = str(status.resolve())

    httpd, _ = start_teleop_face_server(face_dir, status, port=prt)
    time.sleep(0.35)
    url = f"http://127.0.0.1:{prt}/index.html?teleop=1"

    chromium = _find_chromium()
    chrome_proc: subprocess.Popen | None = None
    if chromium:
        chrome_proc = subprocess.Popen(
            [
                chromium,
                "--kiosk",
                "--noerrdialogs",
                "--disable-infobars",
                "--disable-session-crashed-bubble",
                url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        print(
            "AVISO: Chromium não encontrado no PATH — abra manualmente no navegador:\n"
            f"  {url}",
            file=sys.stderr,
        )

    joy_script = root / "joystick_controller_2026.py"
    if not joy_script.is_file():
        print(f"ERRO: {joy_script} não encontrado.", file=sys.stderr)
        if chrome_proc:
            chrome_proc.terminate()
        httpd.shutdown()
        return 2

    joy_cmd = [
        sys.executable,
        str(joy_script),
        "--preset",
        "shanwan",
        "--no-lidar",
    ]
    env = os.environ.copy()
    env["ROBO_TELEOP_FACE_STATUS_FILE"] = str(status.resolve())

    print("Modo semi-autônomo: rosto em", url)
    print("Comando joystick:", " ".join(joy_cmd))

    try:
        joy = subprocess.run(joy_cmd, cwd=str(root), env=env)
        code = joy.returncode
    except KeyboardInterrupt:
        code = 130
    finally:
        if chrome_proc and chrome_proc.poll() is None:
            chrome_proc.terminate()
            try:
                chrome_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                chrome_proc.kill()
        httpd.shutdown()

    return code if code is not None else 0
