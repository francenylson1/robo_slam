#!/usr/bin/env python3
"""
Teste isolado do RP Lidar C1 — Fase 2 do projeto.

Usa a biblioteca rplidarc1 (específica para C1) para evitar "Descriptor length mismatch".
O pacote rplidar genérico não suporta o protocolo do C1.

Uso:
  python tools/teste_c1_isolado.py
  python tools/teste_c1_isolado.py --port /dev/ttyUSB0 --scans 5

Requer: pip install rplidarc1 (Python 3.10+)
"""

import argparse
import asyncio
import sys

DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_BAUD = 460800


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
                d_min = min((p.get("d_mm") or 0) for p in valid)
                n = len(points)
                print(f"Scan {scan_count}: {n} pontos | Obstáculo mais próximo: {d_min:.0f} mm ({d_min/1000:.2f} m)")
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

    print("=" * 60)
    print("🔬 Teste isolado — RP Lidar C1 (rplidarc1)")
    print("=" * 60)
    print(f"   Porta: {args.port}")
    print(f"   Baudrate: {args.baud}")
    print(f"   Scans: {'contínuo (Ctrl+C para parar)' if args.scans == 0 else args.scans}")
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
        description="Teste isolado do RP Lidar C1 — lê e exibe dados do sensor (rplidarc1)."
    )
    parser.add_argument("--port", "-p", default=DEFAULT_PORT, help=f"Porta serial (padrão: {DEFAULT_PORT})")
    parser.add_argument("--baud", "-b", type=int, default=DEFAULT_BAUD, help=f"Baudrate (padrão: {DEFAULT_BAUD})")
    parser.add_argument("--scans", "-n", type=int, default=0, help="Número de varreduras (0 = contínuo)")
    args = parser.parse_args()
    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
