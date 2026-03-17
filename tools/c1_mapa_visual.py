#!/usr/bin/env python3
"""
Mapeamento visual do RP Lidar C1 — análise gráfica para diagnóstico.

Exibe os dados do C1 em formato polar (ângulo vs distância) e cartesiano,
com destaque da faixa frontal, zona parachoques e logs de debug.

Uso:
  python tools/c1_mapa_visual.py --port /dev/ttyUSB0 --scans 3
  python tools/c1_mapa_visual.py --port /dev/ttyUSB0 --scans 5 --front-deg 180 --front-center 180
  python tools/c1_mapa_visual.py --port /dev/ttyUSB0 --scans 3 --save mapa.png
  python tools/c1_mapa_visual.py --port /dev/ttyUSB0 --scans 3 --no-gui  # Só salva PNG (Raspberry sem display)
  python tools/c1_mapa_visual.py --port /dev/ttyUSB0 --scans 3 --export-csv dados.csv  # Exportar para análise

Requer: pip install rplidarc1 matplotlib
"""

import argparse
import asyncio
import csv
import logging
import sys
from datetime import datetime
from pathlib import Path

# Configuração de log
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("c1_mapa")

DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_BAUD = 460800


def _norm_angle(deg: float) -> float:
    return deg % 360.0


def is_in_frontal_cone(angle_deg: float, center_deg: float, width_deg: float) -> bool:
    if width_deg >= 360:
        return True
    half = width_deg / 2.0
    a = _norm_angle(angle_deg)
    c = _norm_angle(center_deg)
    diff = abs(a - c)
    if diff > 180:
        diff = 360 - diff
    return diff <= half


async def coletar_scans(port: str, baud: int, n_scans: int):
    """Coleta n_scans do C1 e retorna lista de pontos [{a_deg, d_mm}, ...]."""
    try:
        from rplidarc1.scanner import RPLidar
    except ImportError:
        try:
            from rplidarc1 import RPLidar
        except ImportError:
            raise ImportError("rplidarc1 não instalado. Execute: pip install rplidarc1") from None

    lidar = RPLidar(port, baud, timeout=0.2)
    points = []
    last_angle = None
    scan_count = 0

    async def consume():
        nonlocal points, last_angle, scan_count
        while not lidar.stop_event.is_set():
            try:
                data = await asyncio.wait_for(lidar.output_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.debug("Erro na fila: %s", e)
                continue

            points.append(data)
            ang = data.get("a_deg", 0)
            if last_angle is not None and last_angle > 350 and ang < 10:
                scan_count += 1
                logger.info("Scan %d completo: %d pontos", scan_count, len(points))
                if n_scans > 0 and scan_count >= n_scans:
                    lidar.stop_event.set()
                    break
            last_angle = ang

    try:
        lidar.healthcheck()
        logger.info("C1 conectado. Saúde: %s", lidar.healthcheck())
    except Exception as e:
        logger.warning("Healthcheck: %s (continuando...)", e)

    if hasattr(asyncio, "TaskGroup"):
        async with asyncio.TaskGroup() as tg:
            tg.create_task(lidar.simple_scan())
            await consume()
    else:
        t1 = asyncio.create_task(lidar.simple_scan())
        await consume()
        t1.cancel()

    try:
        lidar.reset()
        lidar.shutdown()
    except Exception:
        pass

    valid = [p for p in points if (p.get("d_mm") or 0) > 0]
    logger.info("Total: %d pontos válidos (dist > 0)", len(valid))
    return valid


def plotar_mapa(points, args):
    """Gera visualização polar e cartesiana dos pontos."""
    try:
        import matplotlib
        if getattr(args, "no_gui", False):
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as e:
        logger.error("matplotlib não instalado: %s", e)
        logger.error("Execute: pip install matplotlib")
        return False

    angles = np.array([_norm_angle(p.get("a_deg", 0)) for p in points])
    dists_mm = np.array([p.get("d_mm", 0) or 0 for p in points])
    dists_m = dists_mm / 1000.0

    # Polar: 180° (frente) no topo, 0° (trás) embaixo
    angles_rad = np.radians(180 - angles)

    front_center = getattr(args, "front_center", 180)
    front_width = getattr(args, "front_width", None)
    parach_lo, parach_hi = getattr(args, "parachoques_zone", (120, 240))

    # Máscara frontal
    in_frontal = np.array([is_in_frontal_cone(a, front_center, front_width or 360) for a in angles])
    in_parach = (angles >= parach_lo) & (angles <= parach_hi)

    fig = plt.figure(figsize=(14, 7))
    fig.suptitle(f"C1 Mapeamento — {len(points)} pontos | {datetime.now().strftime('%H:%M:%S')}", fontsize=12)

    # --- Plot polar ---
    ax1 = fig.add_subplot(121, projection="polar")
    ax1.scatter(angles_rad, dists_m, c="steelblue", s=2, alpha=0.6, label="todos")
    if front_width and front_width < 360:
        frontal_angles = angles[in_frontal]
        frontal_dists = dists_m[in_frontal]
        if len(frontal_angles) > 0:
            fr_rad = np.radians(180 - frontal_angles)
            ax1.scatter(fr_rad, frontal_dists, c="orange", s=4, alpha=0.8, label="frontal")
    ax1.set_theta_zero_location("N")
    ax1.set_theta_direction(-1)
    ax1.set_title("Vista polar (0°=trás, 180°=frente)")
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(True, alpha=0.3)

    # --- Plot cartesiano (x=frente, y= lateral) ---
    ax2 = fig.add_subplot(122)
    # 180° = +x (frente), 90° = +y (esquerda)
    x = dists_m * np.cos(np.radians(180 - angles))
    y = dists_m * np.sin(np.radians(180 - angles))
    ax2.scatter(x, y, c="steelblue", s=2, alpha=0.6)
    if front_width and front_width < 360 and np.any(in_frontal):
        ax2.scatter(x[in_frontal], y[in_frontal], c="orange", s=4, alpha=0.8)
    ax2.axhline(0, color="gray", linestyle="--", alpha=0.5)
    ax2.axvline(0, color="gray", linestyle="--", alpha=0.5)
    ax2.set_xlabel("Frente (m)")
    ax2.set_ylabel("Lateral (m)")
    ax2.set_title("Vista cartesiana (robô na origem)")
    ax2.set_aspect("equal")
    ax2.grid(True, alpha=0.3)

    # Anotar estatísticas no cartesiano
    if len(dists_m) > 0:
        d_min = np.min(dists_m)
        d_max = np.max(dists_m)
        frontal_dists = dists_m[in_frontal] if np.any(in_frontal) else dists_m
        d_min_fr = np.min(frontal_dists) if len(frontal_dists) > 0 else 0
        stats = f"min: {d_min:.2f}m | max: {d_max:.2f}m | frontal min: {d_min_fr:.2f}m"
        ax2.text(0.02, 0.98, stats, transform=ax2.transAxes, fontsize=9, va="top", family="monospace")

    plt.tight_layout()

    save_path = getattr(args, "save", None)
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info("Figura salva em %s", save_path)
    if not getattr(args, "no_gui", False):
        plt.show()
    else:
        plt.close()
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Mapeamento visual do RP Lidar C1 — análise gráfica para diagnóstico.",
    )
    parser.add_argument("--port", "-p", default=DEFAULT_PORT, help="Porta serial")
    parser.add_argument("--baud", "-b", type=int, default=DEFAULT_BAUD, help="Baudrate")
    parser.add_argument("--scans", "-n", type=int, default=3, help="Número de varreduras")
    parser.add_argument(
        "--front-deg",
        type=float,
        default=None,
        help="Largura da faixa frontal (graus). Ex: 180.",
    )
    parser.add_argument(
        "--front-center",
        type=float,
        default=180,
        help="Centro da faixa frontal (padrão: 180° = frente)",
    )
    parser.add_argument(
        "--parachoques-zone",
        type=str,
        default="120:240",
        help="Zona parachoques (padrão: 120:240)",
    )
    parser.add_argument(
        "--save",
        "-s",
        metavar="ARQUIVO",
        help="Salvar figura em PNG",
    )
    parser.add_argument(
        "--export-csv",
        metavar="ARQUIVO",
        help="Exportar pontos brutos (ângulo, distância) para CSV (análise em planilha)",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Não exibir janela (só salva se --save). Útil na Raspberry sem display.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Log mais detalhado",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger("c1_mapa").setLevel(logging.DEBUG)

    try:
        lo_s, hi_s = args.parachoques_zone.strip().split(":")
        args.parachoques_zone = (float(lo_s), float(hi_s))
    except (ValueError, AttributeError):
        args.parachoques_zone = (120.0, 240.0)

    args.front_width = args.front_deg

    logger.info("Conectando ao C1 em %s...", args.port)
    points = asyncio.run(coletar_scans(args.port, args.baud, args.scans))

    if not points:
        logger.error("Nenhum ponto coletado. Verifique conexão.")
        return 1

    # Exportar CSV se solicitado
    export_path = getattr(args, "export_csv", None)
    if export_path:
        with open(export_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["angulo_deg", "distancia_mm"])
            for p in points:
                w.writerow([p.get("a_deg", 0), p.get("d_mm", 0)])
        logger.info("Pontos exportados para %s (%d linhas)", export_path, len(points))

    logger.info("Gerando visualização...")
    plotar_mapa(points, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
