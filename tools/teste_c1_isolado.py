#!/usr/bin/env python3
"""
Teste isolado do RP Lidar C1 — Fase 2 do projeto.

Usa a biblioteca rplidarc1 (específica para C1) para evitar "Descriptor length mismatch".
O pacote rplidar genérico não suporta o protocolo do C1.

Uso:
  python tools/teste_c1_isolado.py
  python tools/teste_c1_isolado.py --port /dev/ttyUSB0 --scans 5
  python tools/teste_c1_isolado.py --front-deg 60           # Apenas 60° frontais
  python tools/teste_c1_isolado.py --robot-model dev         # Modelo atual (~200°)
  python tools/teste_c1_isolado.py --robot-model wide       # Faixa frontal ampla
  python tools/teste_c1_isolado.py --diagnose --scans 2      # Descobrir 0° e área livre

Requer: pip install rplidarc1 (Python 3.10+)
"""

import argparse
import asyncio
import sys

DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_BAUD = 460800

# Presets por modelo de robô — largura total da faixa frontal (graus)
# 0° = frente do sensor; ângulo aumenta no sentido horário
ROBOT_MODEL_PRESETS = {
    "narrow":   60,   # Visão estreita (ex: robôs compactos, corredores)
    "medium":   90,   # Padrão moderado
    "wide":    120,   # Amplo (ex: ambientes abertos)
    "dev":     200,   # Modelo em desenvolvimento — faixa frontal ampla
    "hemi":    180,   # Hemisfério frontal (meia circunferência)
    "panoramic": 270, # Quase 360° — robôs com sensores rotativos ou redundância
}


def _norm_angle(deg: float) -> float:
    """Normaliza ângulo para [0, 360)."""
    return deg % 360.0


def is_in_frontal_cone(angle_deg: float, center_deg: float, width_deg: float) -> bool:
    """
    Verifica se o ângulo está dentro do cone frontal.

    Args:
        angle_deg: Ângulo do ponto (0-360, 0° = frente, sentido horário).
        center_deg: Centro do cone frontal (geralmente 0°).
        width_deg: Largura total do cone em graus (ex: 200 = ±100° em relação ao centro).

    Returns:
        True se o ponto está na faixa frontal.
    """
    if width_deg >= 360:
        return True
    half = width_deg / 2.0
    # Centro em 0°: frontal vai de -half a +half
    # Em 0-360: [360-half, 360) ∪ [0, half]
    a = _norm_angle(angle_deg)
    c = _norm_angle(center_deg)
    # Distância angular mínima ao centro (considerando wrap-around)
    diff = abs(a - c)
    if diff > 180:
        diff = 360 - diff
    return diff <= half


DIAGNOSE_SECTOR_DEG = 20  # Graus por setor no modo --diagnose
DIAGNOSE_OCCUPIED_THRESHOLD_MM = 150  # Abaixo disso = provável corpo/obstáculo fixo


def get_frontal_range_desc(center_deg: float, width_deg: float) -> str:
    """
    Retorna descrição legível do intervalo frontal.

    Para center=0, width=200 (modelo dev): ±100° → 260° a 100° (via 0°).
    """
    if width_deg >= 360:
        return "360° (todos os pontos)"
    half = width_deg / 2.0
    c = _norm_angle(center_deg)
    start = _norm_angle(c - half)
    end = _norm_angle(c + half)
    if start > end:
        return f"{start:.0f}°→0°→{end:.0f}° (±{half:.0f}°, total {width_deg:.0f}°)"
    return f"{start:.0f}° a {end:.0f}° (centro {c:.0f}°, largura {width_deg:.0f}°)"


def _print_diagnose(valid_points: list) -> None:
    """
    Imprime mapa angular por setores para descobrir 0° e área livre.
    Setores com dist < DIAGNOSE_OCCUPIED_THRESHOLD_MM = provável corpo do robô.
    """
    n_sectors = int(360 / DIAGNOSE_SECTOR_DEG)
    sector_min = [float("inf")] * n_sectors
    sector_count = [0] * n_sectors

    for p in valid_points:
        ang = p.get("a_deg", 0)
        d = p.get("d_mm") or 0
        if d <= 0:
            continue
        idx = int(ang / DIAGNOSE_SECTOR_DEG) % n_sectors
        sector_min[idx] = min(sector_min[idx], d)
        sector_count[idx] += 1

    print("\n📊 MODO DIAGNÓSTICO — Mapa angular (setores de {}°):".format(DIAGNOSE_SECTOR_DEG))
    print("   Ângulo      | min(mm) | pts | status")
    print("   " + "-" * 40)

    deg_free = 0
    deg_occupied = 0
    best_angle = None
    best_dist = 0

    for i in range(n_sectors):
        lo = i * DIAGNOSE_SECTOR_DEG
        hi = lo + DIAGNOSE_SECTOR_DEG
        d_min = sector_min[i] if sector_min[i] != float("inf") else 0
        n = sector_count[i]
        occupied = d_min < DIAGNOSE_OCCUPIED_THRESHOLD_MM if d_min > 0 else False
        status = "⚠️ ocupado" if occupied else "✓ livre"
        if occupied:
            deg_occupied += DIAGNOSE_SECTOR_DEG
        else:
            deg_free += DIAGNOSE_SECTOR_DEG
        if d_min > best_dist and d_min > 0:
            best_dist = d_min
            best_angle = (lo + hi) / 2
        print("   {:3.0f}°–{:3.0f}°   | {:6.0f} | {:3} | {}".format(lo, hi, d_min, n, status))

    print("   " + "-" * 40)
    print("   Área LIVRE (dist >= {} mm):  ~{:.0f}°".format(DIAGNOSE_OCCUPIED_THRESHOLD_MM, deg_free))
    print("   Área OCUPADA (dist < {} mm): ~{:.0f}° (corpo/obstáculo)".format(
        DIAGNOSE_OCCUPIED_THRESHOLD_MM, deg_occupied))
    if best_angle is not None:
        print("   Direção com MAIOR distância: ~{:.0f}° (min={:.0f} mm) — provável FRENTE livre".format(
            best_angle, best_dist))
    print("   Referência: 0° = direção do cabo preto do sensor. Ver docs/FASE2_TESTES_C1_COMO_SABER_0_GRAUS.md")
    print()


async def run_scan(lidar, args):
    """Lê da fila e exibe estatísticas a cada batch de pontos."""
    points = []
    scan_count = 0
    last_angle = None

    while True:
        try:
            # Timeout curto para permitir verificação de stop_event
            data = await asyncio.wait_for(lidar.output_queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            if lidar.stop_event.is_set():
                break
            continue
        except Exception:
            if lidar.stop_event.is_set():
                break
            continue

        points.append(data)
        ang = data.get("a_deg", 0)
        dist = data.get("d_mm", 0)

        # Detecta nova varredura (ângulo volta de ~360 para ~0)
        if last_angle is not None and last_angle > 350 and ang < 10:
            scan_count += 1
            valid = [p for p in points if (p.get("d_mm") or 0) > 0]
            if valid:
                center = getattr(args, "front_center", 0)
                width = getattr(args, "front_width", None)
                if width is not None:
                    frontal = [p for p in valid if is_in_frontal_cone(p.get("a_deg", 0), center, width)]
                    n_total, n_front = len(points), len(frontal)
                    if frontal:
                        d_min_all = min((p.get("d_mm") or 0) for p in valid)
                        d_min_front = min((p.get("d_mm") or 0) for p in frontal)
                        print(f"Scan {scan_count}: {n_total} pts | "
                              f" frontal ({n_front} pts): min={d_min_front:.0f} mm ({d_min_front/1000:.2f} m) | "
                              f" 360° min={d_min_all:.0f} mm")
                    else:
                        print(f"Scan {scan_count}: {n_total} pts | frontal ({n_front} pts): sem dados válidos")
                else:
                    d_min = min((p.get("d_mm") or 0) for p in valid)
                    n = len(points)
                    print(f"Scan {scan_count}: {n} pontos | Obstáculo mais próximo: {d_min:.0f} mm ({d_min/1000:.2f} m)")
                # Modo --diagnose: mapa angular por setores (descobrir 0° e área livre)
                if getattr(args, "diagnose", False) and valid:
                    _print_diagnose(valid)
            points = []
            if args.scans > 0 and scan_count >= args.scans:
                lidar.stop_event.set()
                break
        last_angle = ang


async def main_async(args):
    try:
        from rplidarc1.scanner import RPLidar
    except ImportError:
        try:
            from rplidarc1 import RPLidar
        except ImportError:
            print("❌ Pacote 'rplidarc1' não instalado.")
            print("   Execute: pip uninstall rplidar && pip install rplidarc1")
            print("   Requer Python 3.10+")
            return 1

    # Resolve faixa frontal: --robot-model tem prioridade sobre --front-deg
    front_width = getattr(args, "front_width", None)
    front_center = getattr(args, "front_center", 0)

    print("=" * 60)
    print("🔬 Teste isolado — RP Lidar C1 (rplidarc1)")
    print("=" * 60)
    print(f"   Porta: {args.port}")
    print(f"   Baudrate: {args.baud}")
    print(f"   Scans: {'contínuo (Ctrl+C para parar)' if args.scans == 0 else args.scans}")
    if front_width is not None:
        rng = get_frontal_range_desc(front_center, front_width)
        print(f"   Faixa frontal: {rng}")
    else:
        print("   Faixa frontal: 360° (todos os pontos)")
    print()

    lidar = RPLidar(args.port, args.baud, timeout=0.2)
    try:
        health = lidar.healthcheck()
        print(f"💚 Saúde: {health}")
        if health and "Good" not in str(health):
            print("   ⚠️ Sensor pode ter problemas. Verifique conexão e alimentação.")

        print("\n📡 Iniciando leitura de varreduras...")
        print("   Ângulo 0° = frente do sensor; sentido horário.")
        print("-" * 60)

        if hasattr(asyncio, "TaskGroup"):
            # Python 3.11+
            async with asyncio.TaskGroup() as tg:
                tg.create_task(lidar.simple_scan())
                tg.create_task(run_scan(lidar, args))
        else:
            # Python 3.10 fallback
            scan_task = asyncio.create_task(lidar.simple_scan())
            run_task = asyncio.create_task(run_scan(lidar, args))
            await asyncio.gather(scan_task, run_task)

        lidar.reset()
    except KeyboardInterrupt:
        lidar.stop_event.set()
        lidar.reset()
        print("\n⚠️ Interrompido pelo usuário.")
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        try:
            lidar.shutdown()
        except Exception:
            pass

    print("\n✅ Sensor desconectado.")
    print("=" * 60)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Teste isolado do RP Lidar C1 — lê e exibe dados do sensor (rplidarc1).",
        epilog="Presets: " + ", ".join(f"{k}={v}°" for k, v in ROBOT_MODEL_PRESETS.items()),
    )
    parser.add_argument("--port", "-p", default=DEFAULT_PORT, help=f"Porta serial (padrão: {DEFAULT_PORT})")
    parser.add_argument("--baud", "-b", type=int, default=DEFAULT_BAUD, help=f"Baudrate (padrão: {DEFAULT_BAUD})")
    parser.add_argument("--scans", "-n", type=int, default=0, help="Número de varreduras (0 = contínuo)")
    parser.add_argument(
        "--diagnose", "-d",
        action="store_true",
        help="Modo diagnóstico: exibe mapa angular por setores para descobrir 0° e área livre vs ocupada",
    )
    fg = parser.add_argument_group("Faixa frontal (para diferentes modelos de robô)")
    fg.add_argument(
        "--front-deg",
        metavar="GRAUS",
        type=float,
        default=None,
        help="Largura total do cone frontal em graus (ex: 60, 200). Centro = 0° (frente do sensor)",
    )
    fg.add_argument(
        "--front-center",
        metavar="GRAUS",
        type=float,
        default=0,
        help="Ângulo central da faixa frontal (padrão: 0° = frente do sensor)",
    )
    fg.add_argument(
        "--robot-model",
        choices=list(ROBOT_MODEL_PRESETS.keys()),
        default=None,
        help=f"Preset de modelo: narrow(60°), medium(90°), wide(120°), dev(200°), hemi(180°), panoramic(270°)",
    )
    args = parser.parse_args()
    # Resolve front_width: robot-model sobrescreve --front-deg
    if args.robot_model is not None:
        args.front_width = float(ROBOT_MODEL_PRESETS[args.robot_model])
    elif args.front_deg is not None:
        args.front_width = args.front_deg
    else:
        args.front_width = None
    args.front_center = args.front_center
    args.diagnose = getattr(args, "diagnose", False)
    if args.diagnose and (args.scans is None or args.scans == 0):
        args.scans = 2  # Diagnóstico precisa de pelo menos 2 varreduras
    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
