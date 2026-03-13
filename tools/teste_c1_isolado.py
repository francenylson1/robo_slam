#!/usr/bin/env python3
"""
Teste isolado do RP Lidar C1 — Fase 2 do projeto.

Conecta ao sensor C1 via USB, lê varreduras (scans) e exibe o que retorna.
Use para validar: conexão, ângulos, distâncias, qualidade dos dados.

Uso:
  python tools/teste_c1_isolado.py
  python tools/teste_c1_isolado.py --port /dev/ttyUSB0 --baud 115200
  python tools/teste_c1_isolado.py --scans 5   # apenas 5 varreduras

O C1 pode usar 115200 (padrão) ou 460800 baud. Se falhar, tente o outro.
"""

import argparse
import sys
import time

# Porta serial típica no Raspberry Pi / Linux
DEFAULT_PORT = "/dev/ttyUSB0"
# C1: 115200 ou 460800 (testar ambos se necessário)
DEFAULT_BAUD = 115200


def main():
    parser = argparse.ArgumentParser(
        description="Teste isolado do RP Lidar C1 — lê e exibe dados do sensor."
    )
    parser.add_argument(
        "--port", "-p",
        default=DEFAULT_PORT,
        help=f"Porta serial (padrão: {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--baud", "-b",
        type=int,
        default=DEFAULT_BAUD,
        help=f"Baudrate (padrão: {DEFAULT_BAUD}; C1 pode usar 460800)"
    )
    parser.add_argument(
        "--scans", "-n",
        type=int,
        default=0,
        help="Número de varreduras a exibir (0 = contínuo até Ctrl+C)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=3.0,
        help="Timeout da porta serial em segundos"
    )
    args = parser.parse_args()

    try:
        from rplidar import RPLidar
    except ImportError:
        print("❌ Pacote 'rplidar' não instalado.")
        print("   Execute: pip install rplidar")
        sys.exit(1)

    print("=" * 60)
    print("🔬 Teste isolado — RP Lidar C1")
    print("=" * 60)
    print(f"   Porta: {args.port}")
    print(f"   Baudrate: {args.baud}")
    print(f"   Scans: {'contínuo (Ctrl+C para parar)' if args.scans == 0 else args.scans}")
    print()

    lidar = None
    try:
        lidar = RPLidar(args.port, baudrate=args.baud, timeout=args.timeout)
        lidar.connect()

        info = lidar.get_info()
        print("📋 Informações do sensor:")
        for k, v in info.items():
            print(f"   {k}: {v}")

        health = lidar.get_health()
        print(f"\n💚 Saúde: {health[0]} (código: {health[1]})")
        if health[0] != "Good":
            print("   ⚠️ Sensor pode ter problemas. Verifique conexão e alimentação.")

        lidar.start_motor()
        time.sleep(0.5)

        print("\n📡 Iniciando leitura de varreduras...")
        print("   Formato: (qualidade, ângulo°, distância_mm)")
        print("   Ângulo 0° = frente do sensor; sentido horário.")
        print("-" * 60)

        count = 0
        for i, scan in enumerate(lidar.iter_scans(min_len=5)):
            count += 1
            # Cada scan é lista de (quality, angle, distance)
            # angle em graus [0, 360), distance em mm
            n = len(scan)
            if n == 0:
                continue

            # Amostra: primeiro, meio e último ponto
            samples = []
            if n >= 1:
                samples.append(scan[0])
            if n >= 2:
                samples.append(scan[n // 2])
            if n >= 3:
                samples.append(scan[-1])

            print(f"Scan {count}: {n} pontos | Amostra: ", end="")
            for q, ang, dist in samples:
                print(f"({q},{ang:.1f}°,{dist:.0f}mm) ", end="")
            print()

            # Distância mínima na varredura (obstáculo mais próximo)
            valid = [(q, a, d) for q, a, d in scan if d > 0]
            if valid:
                _, _, d_min = min(valid, key=lambda x: x[2])
                print(f"         → Obstáculo mais próximo: {d_min:.0f} mm ({d_min/1000:.2f} m)")

            if args.scans > 0 and count >= args.scans:
                break

    except FileNotFoundError as e:
        print(f"❌ Porta {args.port} não encontrada.")
        print("   Verifique se o C1 está conectado: ls /dev/ttyUSB* /dev/ttyACM*")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro: {e}")
        if "115200" in str(args.baud):
            print("   Dica: O C1 pode usar 460800. Tente: --baud 460800")
        sys.exit(1)
    finally:
        if lidar:
            try:
                lidar.stop()
                lidar.stop_motor()
                lidar.disconnect()
            except Exception:
                pass
        print("\n✅ Sensor desconectado.")

    print("\n" + "=" * 60)
    print("✅ Teste concluído.")
    print("=" * 60)


if __name__ == "__main__":
    main()
