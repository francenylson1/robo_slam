#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
joystick_map_tool.py — Mapear eixos e botões do joystick (pygame)

Uso:
  python joystick_map_tool.py
  python joystick_map_tool.py --device 1
  python joystick_map_tool.py --heartbeat 3 --save mapa_joystick.json

Objetivo: ver qual índice pygame (0,1,2…) mexe com cada eixo/botão.
Depois copias os números para joystick_controller_2026.py (--stick-x, --stick-y, BTN_*).

Saída:
  - Tabela de eixos atualizada quando algum valor muda (ou a cada 0,25 s).
  - Cada botão: linha "BOTÃO N pressionado / solto".
  - D-pad (hat): "HAT h: (x, y)".

Ctrl+C para sair. Com --save, grava JSON com último snapshot dos eixos e lista de botões testados.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mapear joystick — eixos e botões (pygame)")
    parser.add_argument(
        "--device",
        type=int,
        default=0,
        help="Índice do joystick (0 = primeiro). Padrão: 0",
    )
    parser.add_argument(
        "--save",
        type=str,
        default="",
        metavar="FICHEIRO.json",
        help="Ao sair (Ctrl+C), grava snapshot em JSON",
    )
    parser.add_argument(
        "--heartbeat",
        type=float,
        default=0.0,
        metavar="SEG",
        help="Se > 0, imprime eixos a cada N segundos (ex.: 3) além das mudanças",
    )
    args = parser.parse_args()

    import pygame

    pygame.init()
    pygame.joystick.init()

    n = pygame.joystick.get_count()
    if n == 0:
        print("ERRO: Nenhum joystick. Liga USB/Bluetooth e tenta de novo.")
        sys.exit(1)

    if args.device < 0 or args.device >= n:
        print(f"ERRO: --device {args.device} inválido. Há {n} joystick(s) (0..{n - 1}).")
        sys.exit(2)

    joy = pygame.joystick.Joystick(args.device)
    joy.init()

    nome = joy.get_name()
    num_axes = joy.get_numaxes()
    num_buttons = joy.get_numbuttons()
    num_hats = joy.get_numhats()

    print()
    print("=" * 64)
    print("  MAPEAMENTO DE JOYSTICK")
    print("=" * 64)
    print(f"  Dispositivo pygame: [{args.device}]")
    print(f"  Nome: {nome}")
    print(f"  Eixos: {num_axes}  |  Botões: {num_buttons}  |  Hats: {num_hats}")
    print()
    print("  INSTRUÇÕES:")
    print("    1) Mexe o analógico ESQUERDO — observa qual de a0,a1,a2… muda.")
    print("    2) Mexe o analógico DIREITO — idem.")
    print("    3) Carrega em cada botão — aparece BOTÃO N.")
    print("    4) Usa o D-pad — aparece HAT.")
    print("  Ctrl+C para sair.")
    print("=" * 64)
    print()

    axes_last = [joy.get_axis(i) for i in range(num_axes)]
    buttons_tested: set[int] = set()
    last_hb = 0.0

    def snapshot() -> dict[str, Any]:
        return {
            "joystick_index": args.device,
            "name": nome,
            "num_axes": num_axes,
            "num_buttons": num_buttons,
            "num_hats": num_hats,
            "axes": {f"axis_{i}": round(joy.get_axis(i), 4) for i in range(num_axes)},
            "buttons_tested_sorted": sorted(buttons_tested),
        }

    line0 = "  ".join(f"a{i}={axes_last[i]:+.3f}" for i in range(num_axes))
    print(f"  [início] {line0}")
    print()

    try:
        while True:
            pygame.event.pump()
            now = time.monotonic()

            for ev in pygame.event.get():
                if ev.type == pygame.JOYBUTTONDOWN:
                    buttons_tested.add(ev.button)
                    print(f"  >>> BOTÃO {ev.button} PRESSIONADO")
                elif ev.type == pygame.JOYBUTTONUP:
                    print(f"  <<< BOTÃO {ev.button} solto")
                elif ev.type == pygame.JOYHATMOTION:
                    print(f"  ... HAT {ev.hat}: ({ev.value[0]}, {ev.value[1]})")

            axes_now = [joy.get_axis(i) for i in range(num_axes)]
            changed = any(abs(axes_now[i] - axes_last[i]) > 0.015 for i in range(num_axes))
            if changed:
                axes_last = axes_now.copy()
                line = "  ".join(f"a{i}={axes_now[i]:+.3f}" for i in range(num_axes))
                print(f"  [eixos] {line}")

            if args.heartbeat > 0 and (now - last_hb) >= args.heartbeat:
                last_hb = now
                line = "  ".join(f"a{i}={axes_now[i]:+.3f}" for i in range(num_axes))
                print(f"  [pulso] {line}")

            time.sleep(0.02)

    except KeyboardInterrupt:
        print()
        print("  Interrompido (Ctrl+C).")

    data = snapshot()
    print()
    print("-" * 64)
    print("  RESUMO — copia para o controlador:")
    print("-" * 64)
    print(f"  Nome detectado: {nome}")
    print("  Exemplo linha de comando (ajusta os números conforme [eixos] acima):")
    print(
        f'    python joystick_controller_2026.py --stick-x EIXO_X --stick-y EIXO_Y --arm-with-a --debug-axes'
    )
    print("  Substituir EIXO_X / EIXO_Y pelos índices do analógico que mexem ao andar / virar.")
    print("  Botões vistos (índices pygame):", sorted(buttons_tested) if buttons_tested else "(nenhum registo)")

    if args.save:
        path = args.save
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  Gravado: {path}")

    joy.quit()
    pygame.quit()


if __name__ == "__main__":
    main()
