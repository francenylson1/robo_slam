#!/usr/bin/env python3
"""
Suíte de testes BNO08x: linha reta com correção de rumo e giros 45°, 90°, 180°, 360°.

Usa sempre config.py: SPEED_SLOW_TPS, TURN_TPS_DEFAULT, BNO_STRAIGHT_KP,
BNO_STRAIGHT_MAX_CORRECTION_TPS, BNO_STRAIGHT_INVERT_CORRECTION e geometria do robô.

Executar na Raspberry Pi (motores + BNO08x). Uso (na raiz do projeto):
  python tests/teste_bno_suite.py
  python tests/teste_bno_suite.py --calibrate --duration 5
  python tests/teste_bno_suite.py --no-straight
  python tests/teste_bno_suite.py --no-turns --angles 90 180
  python tests/teste_bno_suite.py --csv data/teste_bno.csv
"""

import sys
import os
import math
import time
import argparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def is_raspberry_pi():
    try:
        with open("/proc/device-tree/model", "r") as f:
            return "raspberry" in f.read().lower()
    except Exception:
        return False


def normalize_angle_deg(deg):
    """Coloca ângulo em [-180, 180]."""
    while deg > 180:
        deg -= 360
    while deg < -180:
        deg += 360
    return deg


# ---------------------------------------------------------------------------
# BNO08x init: mesmo procedimento do tools/bno08x_test.py (reset + I2C + 3 relatórios)
# ---------------------------------------------------------------------------
def _init_bno_suite():
    """Inicializa BNO08x via tools.bno08x_init (igual bno08x_test: RST HIGH apenas, sem ciclo)."""
    try:
        from tools.bno08x_init import init_bno as _init
        return _init(do_reset_cycle=False, verbose=True)
    except ImportError:
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        try:
            from tools.bno08x_init import init_bno as _init
            return _init(do_reset_cycle=False, verbose=True)
        except ImportError:
            return None, None


def init_motors():
    """Retorna (motors, app)."""
    try:
        from PyQt5.QtCore import QCoreApplication
    except ImportError:
        return None, None
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication(sys.argv)
    try:
        from src.core.robot_motor_controller import RobotMotorController
    except ImportError:
        return None, None
    return RobotMotorController(), app


def ticks_to_angle_deg(left_ticks, right_ticks, tpr, circ_m, base_m):
    dist_l = (left_ticks / tpr) * circ_m
    dist_r = (right_ticks / tpr) * circ_m
    return math.degrees((dist_l - dist_r) / base_m)


def compute_straight_correction(yaw_ref, get_bno_yaw, base_tps, kp, max_correction, invert_correction=False):
    """Calcula (left_tps, right_tps) para manter linha reta usando BNO (valores de config)."""
    yaw_now = get_bno_yaw() if get_bno_yaw else None
    if yaw_now is None:
        return base_tps, base_tps
    err = normalize_angle_deg(yaw_now - yaw_ref)
    if invert_correction:
        err = -err
    corr = kp * err
    corr = max(-max_correction, min(max_correction, corr))
    left_tps = base_tps - corr
    right_tps = base_tps + corr
    return left_tps, right_tps


# ---------------------------------------------------------------------------
# Teste: linha reta COM correção BNO (ganhos do config)
# ---------------------------------------------------------------------------
def run_straight_bno_test(motors, get_bno_yaw, app, duration_s, results_list, verbose=True):
    """Avança em linha reta por duration_s segundos com correção de rumo BNO (config)."""
    from src.core.config import (
        TICKS_PER_REVOLUTION,
        ROBOT_WHEEL_CIRCUMFERENCE_M,
        ROBOT_WHEEL_BASE_M,
        SPEED_SLOW_TPS,
        BNO_STRAIGHT_KP,
        BNO_STRAIGHT_MAX_CORRECTION_TPS,
        BNO_STRAIGHT_INVERT_CORRECTION,
    )
    if verbose:
        print("\n--- Teste LINHA RETA (com correção BNO) ---")
        print("  Duração: {:.1f} s | TPS: {} | Kp: {} | max_corr: {} | invert: {}".format(
            duration_s, SPEED_SLOW_TPS, BNO_STRAIGHT_KP, BNO_STRAIGHT_MAX_CORRECTION_TPS,
            BNO_STRAIGHT_INVERT_CORRECTION))
    yaw_ref = get_bno_yaw() if get_bno_yaw else None
    if yaw_ref is None:
        if verbose:
            print("  AVISO: BNO sem leitura; frente sem correção de rumo.")
    elif verbose:
        print("  Rumo de referência BNO: {:.1f}°".format(yaw_ref))
    t0 = time.time()
    yaw_list = []
    odom_angle = 0.0
    sample_interval = 0.03
    while time.time() - t0 < duration_s:
        if app:
            app.processEvents()
        base_tps = SPEED_SLOW_TPS
        left_tps, right_tps = compute_straight_correction(
            yaw_ref if yaw_ref is not None else 0.0,
            get_bno_yaw, base_tps,
            BNO_STRAIGHT_KP, BNO_STRAIGHT_MAX_CORRECTION_TPS, BNO_STRAIGHT_INVERT_CORRECTION
        )
        motors.set_target_speed(left_tps, right_tps)
        time.sleep(sample_interval)
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
    motors.stop_motors()
    yaw_start = yaw_list[0] if yaw_list else None
    yaw_end = yaw_list[-1] if yaw_list else None
    yaw_drift_raw = (yaw_end - yaw_start) if (yaw_start is not None and yaw_end is not None) else None
    yaw_drift = normalize_angle_deg(yaw_drift_raw) if yaw_drift_raw is not None else None
    if verbose:
        print("  Odometria (ângulo acumulado): {:.2f}°".format(odom_angle))
        if yaw_drift is not None:
            print("  BNO yaw: início={:.2f}° fim={:.2f}° → deriva={:.2f}° (normalizada)".format(
                yaw_start, yaw_end, yaw_drift))
        else:
            print("  BNO: sem leitura válida.")
    r = {
        "name": "Linha reta (BNO)",
        "odom_angle_deg": odom_angle,
        "bno_yaw_drift_deg": yaw_drift,
        "bno_yaw_start": yaw_start,
        "bno_yaw_end": yaw_end,
    }
    results_list.append(r)
    return r


# ---------------------------------------------------------------------------
# Teste: giro no lugar (odometria + BNO) — sentido direita (angle_odom positivo)
# ---------------------------------------------------------------------------
def run_turn_test(motors, get_bno_yaw, app, target_deg, turn_tps, results_list, verbose=True):
    """Gira no lugar target_deg graus para a DIREITA (odometria positiva)."""
    from src.core.config import (
        TICKS_PER_REVOLUTION,
        ROBOT_WHEEL_CIRCUMFERENCE_M,
        ROBOT_WHEEL_BASE_M,
    )
    if verbose:
        print("\n--- Teste GIRO {:.0f}° (direita) ---".format(target_deg))
    motors.set_precise_rotation_direction(1, -1)
    motors.set_target_speed(turn_tps, -turn_tps)
    angle_odom = 0.0
    yaw_start = get_bno_yaw() if get_bno_yaw else None
    t0 = time.time()
    while angle_odom < target_deg:
        if app:
            app.processEvents()
        time.sleep(0.05)
        ticks = motors.get_and_reset_ticks()
        if ticks:
            delta = ticks_to_angle_deg(
                ticks["left"], ticks["right"],
                TICKS_PER_REVOLUTION, ROBOT_WHEEL_CIRCUMFERENCE_M, ROBOT_WHEEL_BASE_M
            )
            angle_odom += delta
    motors.stop_motors()
    motors.clear_precise_rotation_direction()
    time.sleep(0.2)
    yaw_end = get_bno_yaw() if get_bno_yaw else None
    bno_delta_raw = (yaw_end - yaw_start) if (yaw_start is not None and yaw_end is not None) else None
    bno_delta = normalize_angle_deg(bno_delta_raw) if bno_delta_raw is not None else None
    odom_error = angle_odom - target_deg
    if verbose:
        print("  Odometria: {:.2f}° (alvo {:.0f}°) → erro {:.2f}°".format(
            angle_odom, target_deg, odom_error))
        if bno_delta is not None:
            print("  BNO: início={:.2f}° fim={:.2f}° → delta={:.2f}° (normalizado)".format(
                yaw_start, yaw_end, bno_delta))
    r = {
        "name": "Giro {:.0f}°".format(target_deg),
        "target_deg": target_deg,
        "odom_angle_deg": angle_odom,
        "odom_error_deg": odom_error,
        "bno_delta_deg": bno_delta,
        "bno_yaw_start": yaw_start,
        "bno_yaw_end": yaw_end,
    }
    results_list.append(r)
    return r


def main():
    parser = argparse.ArgumentParser(
        description="Suíte de testes BNO08x: linha reta com correção + giros 45/90/180/360°"
    )
    parser.add_argument("--duration", type=float, default=4.0, help="Duração da linha reta (s)")
    parser.add_argument("--no-straight", action="store_true", help="Pular teste de linha reta")
    parser.add_argument("--no-turns", action="store_true", help="Pular testes de giro")
    parser.add_argument("--angles", type=int, nargs="+", default=[45, 90, 180, 360],
                        help="Ângulos de giro em graus (default: 45 90 180 360)")
    parser.add_argument("--turn-tps", type=float, default=None,
                        help="TPS para giros (default: config TURN_TPS_DEFAULT)")
    parser.add_argument("--calibrate", action="store_true",
                        help="Calibrar BNO08x antes (robô parado e plano ~15–30 s)")
    parser.add_argument("--csv", type=str, default="", help="Arquivo CSV para salvar resultados")
    parser.add_argument("--quiet", action="store_true", help="Menos saída por teste")
    args = parser.parse_args()

    if not is_raspberry_pi():
        print("Execute este script na Raspberry Pi (motores e BNO08x).")
        sys.exit(1)

    from src.core.config import TURN_TPS_DEFAULT
    turn_tps = args.turn_tps if args.turn_tps is not None else TURN_TPS_DEFAULT

    os.environ["ROBOT_MOTOR_QUIET"] = "1"
    print("Inicializando BNO08x (reset + init como bno08x_test.py)...")
    bno, get_bno_yaw = _init_bno_suite()
    if bno is None:
        print("AVISO: BNO08x não disponível. Linha reta será sem correção; giros usam só odometria.")
    else:
        print("BNO08x OK.")

    if args.calibrate and bno is not None:
        print("Calibração BNO08x: deixe o robô parado e em superfície plana...")
        try:
            bno.begin_calibration()
            print("Aguarde ~15–30 s (Ctrl+C para pular).")
            for i in range(60):
                time.sleep(0.5)
                try:
                    s = bno.calibration_status
                    if (i + 1) % 6 == 0:
                        print("  Calibração status:", s)
                except Exception:
                    pass
            print("Calibração concluída (ou tempo esgotado).")
        except KeyboardInterrupt:
            print("\nCalibração interrompida.")
        except Exception as e:
            print("  Erro na calibração:", e)

    print("Inicializando motores...")
    motors, app = init_motors()
    if motors is None:
        print("Erro: não foi possível inicializar o controlador de motores.")
        sys.exit(1)
    print("Motores OK. Ganhos de correção BNO e TPS vêm de config.py.")
    time.sleep(0.5)  # Estabilização do BNO após init dos motores

    results = []
    if not args.no_straight:
        run_straight_bno_test(
            motors, get_bno_yaw, app, args.duration, results, verbose=not args.quiet
        )
    if not args.no_turns:
        for angle in args.angles:
            if angle <= 0 or angle > 360:
                print("  Ignorando ângulo inválido: {}°".format(angle))
                continue
            time.sleep(0.5)
            run_turn_test(
                motors, get_bno_yaw, app, angle, turn_tps, results, verbose=not args.quiet
            )

    # Resumo
    print("\n========== RESUMO TESTES BNO ==========")
    for r in results:
        if "Linha reta" in r.get("name", ""):
            drift = r.get("bno_yaw_drift_deg")
            print("{}: odom_angle={:.2f}° | BNO deriva={}".format(
                r["name"], r.get("odom_angle_deg", 0),
                "{:.2f}°".format(drift) if drift is not None else "N/A"))
        else:
            err = r.get("odom_error_deg", 0)
            delta = r.get("bno_delta_deg")
            print("{}: odom={:.2f}° (erro {:.2f}°) | BNO delta={}".format(
                r["name"], r.get("odom_angle_deg", 0), err,
                "{:.2f}°".format(delta) if delta is not None else "N/A"))
    print("========================================")

    if args.csv and results:
        import csv as csv_module
        with open(args.csv, "w", newline="") as f:
            w = csv_module.DictWriter(f, fieldnames=[
                "name", "odom_angle_deg", "odom_error_deg", "bno_yaw_drift_deg", "bno_delta_deg",
                "bno_yaw_start", "bno_yaw_end", "target_deg"
            ])
            w.writeheader()
            for row in results:
                w.writerow({k: row.get(k) for k in w.fieldnames})
        print("Resultados salvos em:", args.csv)

    print("Fim da suíte de testes BNO.")


if __name__ == "__main__":
    main()
