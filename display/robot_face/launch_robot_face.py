#!/usr/bin/env python3
"""Abre a animação do rosto no navegador (Chromium kiosk recomendado na Raspberry Pi)."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description="Launcher do rosto HTML (tela 7\")")
    p.add_argument(
        "--kiosk",
        action="store_true",
        help="Tenta Chromium em modo kiosk (tela cheia)",
    )
    p.add_argument(
        "--browser",
        default="",
        help="Comando do navegador (ex.: chromium-browser ou firefox)",
    )
    args = p.parse_args()

    html = Path(__file__).resolve().parent / "index.html"
    if not html.is_file():
        print(f"Arquivo não encontrado: {html}", file=sys.stderr)
        return 1

    url = html.as_uri()

    if args.browser:
        cmd = [args.browser, url]
        if args.kiosk:
            cmd[1:1] = ["--kiosk", "--noerrdialogs", "--disable-infobars"]
        return subprocess.call(cmd)

    candidates = [
        "chromium-browser",
        "chromium",
        "google-chrome",
        "firefox",
        "xdg-open",
    ]
    if args.kiosk:
        for name in ("chromium-browser", "chromium", "google-chrome"):
            path = shutil.which(name)
            if path:
                return subprocess.call(
                    [
                        path,
                        "--kiosk",
                        "--noerrdialogs",
                        "--disable-infobars",
                        url,
                    ]
                )

    for name in candidates:
        path = shutil.which(name)
        if path:
            return subprocess.call([path, url])

    if sys.platform == "darwin":
        return subprocess.call(["open", url])
    print("Nenhum navegador encontrado no PATH.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
