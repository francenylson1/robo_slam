#!/usr/bin/env python3
"""
Teste de sincronia: motores, odometria (ticks) e BNO08x.
Objetivos:
  - Linha reta: andar para frente e verificar se o robô não desvia (BNO yaw estável, odometria alinhada).
  - Giros: 45°, 90°, 180° com eficiência e sem deriva (comparar ângulo odometria vs BNO).

Executar apenas na Raspberry Pi (motores + BNO conectados).
Requer: pip install PyQt5 adafruit-blinka adafruit-circuitpython-bno08x (e adafruit-extended-bus se Pi 5).

Uso (na raiz do projeto):
  python tools/sync_test_motors_bno.py
  python tools/sync_test_motors_bno.py --duration 6 --csv logs_sync.csv
  python tools/sync_test_motors_bno.py --no-turns   # só linha reta
  python tools/sync_test_motors_bno.py --no-straight --turn-tps 10   # só giros
"""

import sys
import os
import math
import time
import argparse
import csv

# Raiz do projeto para imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def is_raspberry_pi():
    try:
        with open("/proc/device-tree/model", "r") as f:
            return "raspberry" in f.read().lower()
    except Exception:
        return False


def init_bno():
    """Inicializa BNO08x (I2C, RST em HIGH). Retorna (bno, get_yaw_func) ou (None, None)."""
    try:
        import board
        import busio
        import digitalio
        from digitalio import DigitalInOut
        Direction = getattr(digitalio, "Direction", None) or getattr(DigitalInOut, "Direction", None)
    except ImportError:
        print("Instale adafruit-blinka para usar o BNO08x.")
        return None, None
    try:
        # Corrige KeyError quando o BNO envia report desconhecido (ex.: 0x7B) que a lib não trata
        import adafruit_bno08x as _bno_mod
        _orig_report_length = getattr(_bno_mod, "_report_length", None)
        if callable(_orig_report_length):
            def _safe_report_length(report_id):
                try:
                    return _orig_report_length(report_id)
                except KeyError:
                    return 16
            _bno_mod._report_length = _safe_report_length
        from adafruit_bno08x.i2c import BNO08X_I2C
        from adafruit_bno08x import (
            BNO_REPORT_ACCELEROMETER,
            BNO_REPORT_GYROSCOPE,
            BNO_REPORT_ROTATION_VECTOR,
        )
    except ImportError:
        print("Instale adafruit-circuitpython-bno08x.")
        return None, None

    try:
        from src.core.config import BNO08X_GPIO_RST, BNO08X_I2C_ADDRESS
    except ImportError:
        BNO08X_GPIO_RST = 26
        BNO08X_I2C_ADDRESS = 0x4B

    if BNO08X_GPIO_RST is not None:
        rst = DigitalInOut(getattr(board, "D{}".format(BNO08X_GPIO_RST)))
        if Direction is not None:
            rst.direction = Direction.OUTPUT
        rst.value = True
        time.sleep(0.35)

    i2c = None
    for scl_name, sda_name in [("D3", "D2"), ("SCL", "SDA")]:
        try:
            scl = getattr(board, scl_name, None)
            sda = getattr(board, sda_name, None)
            if scl and sda:
                i2c = busio.I2C(scl, sda)
                break
        except Exception:
            continue
    if i2c is None and hasattr(board, "I2C") and callable(getattr(board, "I2C", None)):
        try:
            i2c = board.I2C()
        except Exception:
            pass
    if i2c is None:
        try:
            from adafruit_extended_bus import ExtendedI2C
            i2c = ExtendedI2C(1)
        except ImportError:
            pass
    if i2c is None:
        print("Não foi possível criar I2C para o BNO08x.")
        return None, None

    addrs = [BNO08X_I2C_ADDRESS, 0x4B, 0x4A]
    bno = None
    for addr in addrs:
        try:
            bno = BNO08X_I2C(i2c, reset=None, address=addr, debug=False)
            break
        except Exception:
            continue
    if bno is None:
        print("BNO08x não encontrado no I2C.")
        return None, None

    time.sleep(0.2)
    # Habilitar só o necessário para yaw (ROTATION_VECTOR). Evita processar relatórios extras que geram KeyError.
    for attempt in range(3):
        try:
            bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)
            break
        except (RuntimeError, KeyError):
            time.sleep(0.3)
    else:
        print("Falha ao habilitar relatório de rotação do BNO08x.")
        return None, None

    def get_yaw():
        try:
            quat_i, quat_j, quat_k, quat_real = bno.quaternion
            siny_cosp = 2 * (quat_real * quat_k + quat_i * quat_j)
            cosy_cosp = 1 - 2 * (quat_j * quat_j + quat_k * quat_k)
            return math.degrees(math.atan2(siny_cosp, cosy_cosp))
        except Exception:
            return None

    return bno, get_yaw


def init_motors():
    """Inicializa PyQt e RobotMotorController. Retorna controller ou None."""
    try:
        from PyQt5.QtCore import QCoreApplication
    except ImportError:
        print("PyQt5 necessário para o controlador de motores.")
        return None
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication(sys.argv)
    try:
        from src.core.robot_motor_controller import RobotMotorController
    except ImportError as e:
        print("Não foi possível importar RobotMotorController:", e)
        return None
    ctrl = RobotMotorController()
    return ctrl


def ticks_to_angle_deg(left_ticks, right_ticks, ticks_per_rev, wheel_circ_m, wheel_base_m):
    """Converte ticks L/R em variação de ângulo (graus)."""
    dist_l = (left_ticks / ticks_per_rev) * wheel_circ_m
    dist_r = (right_ticks / ticks_per_rev) * wheel_circ_m
    delta_rad = (dist_l - dist_r) / wheel_base_m
    return math.degrees(delta_rad)


def ticks_to_distance_m(left_ticks, right_ticks, ticks_per_rev, wheel_circ_m):
    """Distância percorrida (média das duas rodas) em metros."""
    dist_l = (abs(left_ticks) / ticks_per_rev) * wheel_circ_m
    dist_r = (abs(right_ticks) / ticks_per_rev) * wheel_circ_m
    return (dist_l + dist_r) / 2.0


def run_straight_test(motors, get_bno_yaw, duration_s, sample_interval, config, csv_rows, verbose=True):
    """Avança em linha reta por duration_s segundos. Registra BNO yaw e odometria."""
    from src.core.config import (
        TICKS_PER_REVOLUTION,
        ROBOT_WHEEL_CIRCUMFERENCE_M,
        ROBOT_WHEEL_BASE_M,
        SPEED_SLOW_TPS,
    )
    if verbose:
        print("\n--- Teste LINHA RETA (frente) ---")
        print("Avançando por {:.1f} s a {:.0f} TPS. Amostragem a cada {:.2f} s.".format(
            duration_s, SPEED_SLOW_TPS, sample_interval))
    motors.set_target_speed(SPEED_SLOW_TPS, SPEED_SLOW_TPS)
    t0 = time.time()
    yaw_list = []
    odom_angle = 0.0
    last_t = t0
    while time.time() - t0 < duration_s:
        time.sleep(sample_interval)
        t = time.time()
        ticks = motors.get_and_reset_ticks()
        if ticks:
            delta_deg = ticks_to_angle_deg(
                ticks["left"], ticks["right"],
                TICKS_PER_REVOLUTION, ROBOT_WHEEL_CIRCUMFERENCE_M, ROBOT_WHEEL_BASE_M
            )
            odom_angle += delta_deg
        yaw = get_bno_yaw() if get_bno_yaw else None
        if yaw is not None:
            yaw_list.append(yaw)
        dist_m = 0.0
        if ticks:
            dist_m = ticks_to_distance_m(
                ticks["left"], ticks["right"],
                TICKS_PER_REVOLUTION, ROBOT_WHEEL_CIRCUMFERENCE_M
            )
        row = {"test": "reta", "t": t - t0, "odom_angle_deg": odom_angle, "bno_yaw": yaw, "dist_m": dist_m}
        csv_rows.append(row)
    motors.stop_motors()
    # Resultados
    yaw_start = yaw_list[0] if yaw_list else None
    yaw_end = yaw_list[-1] if yaw_list else None
    yaw_drift_bno = (yaw_end - yaw_start) if (yaw_start is not None and yaw_end is not None) else None
    if verbose:
        print("  Odometria (ângulo acumulado): {:.2f}°".format(odom_angle))
        if yaw_drift_bno is not None:
            print("  BNO yaw: início={:.2f}° fim={:.2f}° → deriva={:.2f}°".format(
                yaw_start, yaw_end, yaw_drift_bno))
        else:
            print("  BNO: sem leitura válida.")
    return {
        "odom_angle_deg": odom_angle,
        "bno_yaw_drift_deg": yaw_drift_bno,
        "bno_yaw_start": yaw_start,
        "bno_yaw_end": yaw_end,
    }


def run_turn_test(motors, get_bno_yaw, target_deg, turn_tps, config, csv_rows, verbose=True):
    """Gira no lugar até target_deg (graus). Sentido: positivo = esquerda frente, direita trás."""
    from src.core.config import (
        TICKS_PER_REVOLUTION,
        ROBOT_WHEEL_CIRCUMFERENCE_M,
        ROBOT_WHEEL_BASE_M,
    )
    if verbose:
        print("\n--- Teste GIRO {:.0f}° ---".format(target_deg))
    # Sentido: giro “positivo” = esquerda +, direita -
    motors.set_precise_rotation_direction(1, -1)
    motors.set_target_speed(turn_tps, -turn_tps)
    angle_odom = 0.0
    yaw_start = get_bno_yaw() if get_bno_yaw else None
    t0 = time.time()
    sample_interval = 0.05
    while abs(angle_odom) < abs(target_deg):
        time.sleep(sample_interval)
        ticks = motors.get_and_reset_ticks()
        if ticks:
            delta = ticks_to_angle_deg(
                ticks["left"], ticks["right"],
                TICKS_PER_REVOLUTION, ROBOT_WHEEL_CIRCUMFERENCE_M, ROBOT_WHEEL_BASE_M
            )
            angle_odom += delta
        yaw = get_bno_yaw() if get_bno_yaw else None
        csv_rows.append({"test": "giro_{:.0f}".format(target_deg), "t": time.time() - t0,
                         "odom_angle_deg": angle_odom, "bno_yaw": yaw, "dist_m": None})
    motors.stop_motors()
    motors.clear_precise_rotation_direction()
    time.sleep(0.2)
    yaw_end = get_bno_yaw() if get_bno_yaw else None
    bno_delta = (yaw_end - yaw_start) if (yaw_start is not None and yaw_end is not None) else None
    if verbose:
        print("  Odometria: {:.2f}° (alvo {:.0f}°) → erro {:.2f}°".format(
            angle_odom, target_deg, angle_odom - target_deg))
        if bno_delta is not None:
            print("  BNO: início={:.2f}° fim={:.2f}° → delta={:.2f}°".format(
                yaw_start, yaw_end, bno_delta))
    return {
        "target_deg": target_deg,
        "odom_angle_deg": angle_odom,
        "odom_error_deg": angle_odom - target_deg,
        "bno_delta_deg": bno_delta,
        "bno_yaw_start": yaw_start,
        "bno_yaw_end": yaw_end,
    }


def main():
    try:
        from src.core.config import TURN_TPS_DEFAULT
    except ImportError:
        TURN_TPS_DEFAULT = 12.0
    parser = argparse.ArgumentParser(description="Teste de sincronia motores + odometria + BNO08x")
    parser.add_argument("--duration", type=float, default=5.0, help="Duração do teste de linha reta (s)")
    parser.add_argument("--no-straight", action="store_true", help="Pular teste de linha reta")
    parser.add_argument("--no-turns", action="store_true", help="Pular testes de giro")
    parser.add_argument("--csv", type=str, default="", help="Arquivo CSV para salvar amostras")
    parser.add_argument("--turn-tps", type=float, default=TURN_TPS_DEFAULT, help="TPS para giros (default: config)")
    args = parser.parse_args()

    if not is_raspberry_pi():
        print("Este script deve ser executado na Raspberry Pi (motores e BNO08x).")
        sys.exit(1)

    print("Inicializando BNO08x...")
    bno, get_bno_yaw = init_bno()
    if bno is None:
        print("AVISO: BNO08x não disponível. Testes continuarão só com odometria.")
    else:
        print("BNO08x OK.")

    print("Inicializando motores...")
    motors = init_motors()
    if motors is None:
        print("Erro: não foi possível inicializar o controlador de motores.")
        sys.exit(1)
    print("Motores OK.")

    try:
        from src.core.config import (
            TICKS_PER_REVOLUTION,
            ROBOT_WHEEL_CIRCUMFERENCE_M,
            ROBOT_WHEEL_BASE_M,
        )
    except ImportError:
        print("Erro: config do projeto não encontrado.")
        sys.exit(1)
    config = {
        "TICKS_PER_REVOLUTION": TICKS_PER_REVOLUTION,
        "ROBOT_WHEEL_CIRCUMFERENCE_M": ROBOT_WHEEL_CIRCUMFERENCE_M,
        "ROBOT_WHEEL_BASE_M": ROBOT_WHEEL_BASE_M,
    }
    csv_rows = []
    results = []

    if not args.no_straight:
        r = run_straight_test(
            motors, get_bno_yaw, args.duration, 0.2, config, csv_rows
        )
        results.append(("Linha reta", r))

    if not args.no_turns:
        for angle in (45, 90, 180):
            time.sleep(0.5)
            r = run_turn_test(
                motors, get_bno_yaw, angle, args.turn_tps, config, csv_rows
            )
            results.append(("Giro {:.0f}°".format(angle), r))

    # Resumo
    print("\n========== RESUMO SINCRONIA ==========")
    for name, r in results:
        if "reta" in name.lower():
            print("{}: odom_angle={:.2f}° | BNO deriva={}".format(
                name, r.get("odom_angle_deg", 0),
                r.get("bno_yaw_drift_deg") if r.get("bno_yaw_drift_deg") is not None else "N/A"))
        else:
            print("{}: odom={:.2f}° (erro {:.2f}°) | BNO delta={}".format(
                name, r.get("odom_angle_deg", 0), r.get("odom_error_deg", 0),
                r.get("bno_delta_deg") if r.get("bno_delta_deg") is not None else "N/A"))

    if args.csv and csv_rows:
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["test", "t", "odom_angle_deg", "bno_yaw", "dist_m"])
            w.writeheader()
            for row in csv_rows:
                w.writerow({k: row.get(k) for k in w.fieldnames})
        print("Amostras salvas em:", args.csv)

    print("Fim do teste de sincronia.")


if __name__ == "__main__":
    main()
