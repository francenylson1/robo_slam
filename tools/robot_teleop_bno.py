#!/usr/bin/env python3
"""
Navegação do robô com correção em tempo real pelo BNO08x e controle por teclado.

Baseado no robot_command_menu.py. Inclui:
  1) Giros 45°, 90°, 180° (esquerda/direita) - mesmo comportamento do menu, com ajustes finos possíveis.
  2) Navegação para frente e para trás com correção em tempo real usando o IMU BNO08x (linha reta).
  3) Teleop por teclado: W=frente, S=trás, A=giro esquerda, D=giro direita, X/Espaço=parar, Q=sair.
     Teclas principais: 1=Frente N s (BNO), 4=Esq 90°, 6=Dir 90°, X=Parar, 0=Sair. 2/3/5/7=outros giros.

Executar na Raspberry Pi. Uso (na raiz do projeto):
  python tools/robot_teleop_bno.py
  python tools/robot_teleop_bno.py --forward-duration 5 --kp 0.8
No Thonny: use 0-8 e Enter (W/S/A/D contínuo não disponível; use 1 para frente 4s com BNO).
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
# Leitura de tecla com timeout (para teleop em tempo real)
# ---------------------------------------------------------------------------
def _read_byte_timeout(fd, timeout_sec=0.04):
    import select
    if select.select([fd], [], [], timeout_sec)[0]:
        return sys.stdin.read(1)
    return None


def get_key_or_none(timeout_sec=0.05):
    """
    Lê uma tecla se houver entrada em até timeout_sec. Retorna a tecla ou None.
    Suporta setas e letras. No Thonny use números/letras + Enter (timeout retorna None).
    """
    if not sys.stdin.isatty():
        return None
    if sys.platform != "linux":
        return None
    try:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = _read_byte_timeout(fd, timeout_sec)
            if ch is None:
                return None
            if ch == "\x1b":
                c2 = _read_byte_timeout(fd, 0.06)
                if c2 is None:
                    return ""
                c3 = _read_byte_timeout(fd, 0.06)
                if c3 is None:
                    return ""
                if c2 == "[" and c3 in "ABCD":
                    return {"A": "w", "B": "s", "C": "d", "D": "a"}[c3]
                if c2 == "O" and c3 in "ABCD":
                    return {"A": "w", "B": "s", "C": "d", "D": "a"}[c3]
            return ch.lower() if ch else ""
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except Exception:
        return None


def get_key_blocking():
    """Lê uma tecla (bloqueante). Para uso com menu numérico (1-8, 0) no Thonny."""
    if sys.platform == "linux" and sys.stdin.isatty():
        try:
            import termios
            import tty
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    c2 = _read_byte_timeout(fd, 0.08)
                    c3 = _read_byte_timeout(fd, 0.08) if c2 else None
                    if c2 == "[" and c3 in "ABCD":
                        return {"A": "w", "B": "s", "C": "d", "D": "a"}[c3]
                    if c2 == "O" and c3 in "ABCD":
                        return {"A": "w", "B": "s", "C": "d", "D": "a"}[c3]
                return ch.lower() if ch else ""
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except Exception:
            pass
    try:
        line = input().strip().lower()
        if line in ("w", "s", "a", "d"):
            return line
        return line[0] if line else ""
    except (EOFError, IndexError):
        return "q"


# ---------------------------------------------------------------------------
# BNO08x: usa tools/bno08x_init (reset cycle + init igual ao bno08x_test.py)
# ---------------------------------------------------------------------------
def init_bno(debug=False):
    """Inicializa BNO08x via bno08x_init (reset + I2C + ACCEL+GYRO+ROTATION_VECTOR)."""
    try:
        from tools.bno08x_init import init_bno as _bno_init
        return _bno_init(do_reset_cycle=True, verbose=not debug)
    except ImportError:
        if debug:
            print("  init_bno: falha ao importar tools.bno08x_init")
        return None, None


# ---------------------------------------------------------------------------
# Motores e correção BNO em tempo real
# ---------------------------------------------------------------------------
def init_motors():
    from PyQt5.QtCore import QCoreApplication
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication(sys.argv)
    from src.core.robot_motor_controller import RobotMotorController
    return RobotMotorController(), app


def ticks_to_angle_deg(left_ticks, right_ticks, tpr, circ_m, base_m):
    dist_l = (left_ticks / tpr) * circ_m
    dist_r = (right_ticks / tpr) * circ_m
    return math.degrees((dist_l - dist_r) / base_m)


def compute_straight_correction(yaw_ref, get_bno_yaw, base_tps, kp, max_correction, invert_correction=False):
    """
    Calcula (left_tps, right_tps) para manter linha reta usando BNO.
    err = yaw_now - yaw_ref: positivo = robot virou à esquerda -> corrigir com roda direita mais rápida.
    Se o robô ainda curvar para um lado, use --invert-correction.
    """
    yaw_now = get_bno_yaw() if get_bno_yaw else None
    if yaw_now is None:
        return base_tps, base_tps
    err = normalize_angle_deg(yaw_now - yaw_ref)
    if invert_correction:
        err = -err
    corr = kp * err
    corr = max(-max_correction, min(max_correction, corr))
    # Virou esquerda (err>0) -> reduzir esquerda, aumentar direita = virar à direita para corrigir.
    left_tps = base_tps - corr
    right_tps = base_tps + corr
    return left_tps, right_tps


def cmd_forward_straight(motors, duration_s, get_bno_yaw, app, base_tps, kp=1.0, max_correction=12.0, invert_correction=False):
    """Avança por duration_s segundos com correção BNO em tempo real (linha reta)."""
    yaw_ref = get_bno_yaw() if get_bno_yaw else None
    if yaw_ref is None:
        print("  AVISO: BNO indisponivel, frente sem correção de deriva.")
    else:
        print("  -> Frente {:.1f} s com correção BNO (rumo {:.1f}°).".format(duration_s, yaw_ref))
    t0 = time.time()
    while time.time() - t0 < duration_s:
        if app:
            app.processEvents()
        left_tps, right_tps = compute_straight_correction(
            yaw_ref if yaw_ref is not None else 0.0, get_bno_yaw, base_tps, kp, max_correction, invert_correction
        )
        motors.set_target_speed(left_tps, right_tps)
        time.sleep(0.03)
    motors.stop_motors()
    yaw1 = get_bno_yaw() if get_bno_yaw else None
    if yaw_ref is not None and yaw1 is not None:
        print("  BNO: rumo {:.1f}° -> {:.1f}° (deriva: {:.1f}°)".format(yaw_ref, yaw1, yaw1 - yaw_ref))
    print("  Frente concluído.")


def cmd_back_straight(motors, duration_s, get_bno_yaw, app, base_tps, kp=1.0, max_correction=12.0, invert_correction=False):
    """Recua por duration_s com correção BNO."""
    yaw_ref = get_bno_yaw() if get_bno_yaw else None
    if yaw_ref is None:
        print("  AVISO: BNO indisponivel, ré sem correção.")
    else:
        print("  -> Ré {:.1f} s com correção BNO.".format(duration_s))
    t0 = time.time()
    base_neg = -base_tps
    while time.time() - t0 < duration_s:
        if app:
            app.processEvents()
        left_tps, right_tps = compute_straight_correction(
            yaw_ref if yaw_ref is not None else 0.0, get_bno_yaw, base_neg, kp, max_correction, invert_correction
        )
        motors.set_target_speed(left_tps, right_tps)
        time.sleep(0.03)
    motors.stop_motors()
    print("  Ré concluído.")


def cmd_turn(motors, target_deg, left_turn, turn_tps, get_bno_yaw, app=None):
    """Giro no lugar (45, 90 ou 180°). Sentido: Esquerda=(-1,1), Direita=(1,-1)."""
    from src.core.config import (
        TICKS_PER_REVOLUTION,
        ROBOT_WHEEL_CIRCUMFERENCE_M,
        ROBOT_WHEEL_BASE_M,
    )
    lado = "Esquerda" if left_turn else "Direita"
    print("  -> Giro {} {:.0f}° ...".format(lado, target_deg))
    if left_turn:
        motors.set_precise_rotation_direction(-1, 1)
        motors.set_target_speed(-turn_tps, turn_tps)
    else:
        motors.set_precise_rotation_direction(1, -1)
        motors.set_target_speed(turn_tps, -turn_tps)
    angle_odom = 0.0
    while (left_turn and angle_odom > -target_deg) or (not left_turn and angle_odom < target_deg):
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
    time.sleep(0.15)
    alvo = -target_deg if left_turn else target_deg
    print("  Odometria: {:.1f}° (alvo {:.0f}°) -> erro {:.1f}°".format(angle_odom, alvo, angle_odom - alvo))
    print("  Giro concluído.")


def print_instructions():
    print()
    print("  ========== TELEOP (uma tecla = um comando) ==========")
    print("  W = Frente    S = Tras    A = Giro esq    D = Giro dir")
    print("  1 = Frente 8s (BNO)    4 = Esq 90 deg    6 = Dir 90 deg")
    print("  X ou Espaco = Parar    0 ou Q = Sair")
    print("  =====================================================")
    print("  Comando: ", end="", flush=True)


def main():
    try:
        from src.core.config import (
            BNO_STRAIGHT_KP,
            BNO_STRAIGHT_MAX_CORRECTION_TPS,
            BNO_STRAIGHT_INVERT_CORRECTION,
            TURN_TPS_DEFAULT,
        )
    except ImportError:
        BNO_STRAIGHT_KP = 1.0
        BNO_STRAIGHT_MAX_CORRECTION_TPS = 12.0
        BNO_STRAIGHT_INVERT_CORRECTION = False
        TURN_TPS_DEFAULT = 12.0
    parser = argparse.ArgumentParser(description="Teleop com correção BNO (linha reta)")
    parser.add_argument("--forward-duration", type=float, default=4.0, help="Duração do comando 1=Frente (s)")
    parser.add_argument("--turn-tps", type=float, default=TURN_TPS_DEFAULT, help="TPS para giros (default: config)")
    parser.add_argument("--kp", type=float, default=BNO_STRAIGHT_KP, help="Ganho Kp correção BNO (default: config)")
    parser.add_argument("--max-correction", type=float, default=BNO_STRAIGHT_MAX_CORRECTION_TPS, help="Máx. TPS correção (default: config)")
    parser.add_argument("--invert-correction", action="store_true", help="Inverter correção (ou use config BNO_STRAIGHT_INVERT_CORRECTION)")
    parser.add_argument("--teleop-tps", type=float, default=25.0, help="TPS para W/S (frente/trás contínuo)")
    parser.add_argument("--no-arrows", action="store_true", help="Usar só números/letras (Thonny)")
    parser.add_argument("--debug-bno", action="store_true", help="Mostrar mensagens de diagnóstico do BNO08x")
    parser.add_argument("--calibrate", action="store_true", help="Calibrar BNO08x antes (deixe o robô parado e plano ~15–30 s)")
    args = parser.parse_args()
    # Respeitar config para inversão da correção (config pode forçar True)
    args.invert_correction = args.invert_correction or BNO_STRAIGHT_INVERT_CORRECTION

    if not is_raspberry_pi():
        print("Execute este script na Raspberry Pi.")
        sys.exit(1)

    os.environ["ROBOT_MOTOR_QUIET"] = "1"
    print("Inicializando BNO08x...")
    bno, get_bno_yaw = init_bno(debug=args.debug_bno)
    if bno is None:
        print("BNO08x nao disponivel. Navegacao sera sem correção de deriva.")
        if not args.debug_bno:
            print("  Dica: execute com --debug-bno para ver em que etapa falhou.")
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
    motors, qt_app = init_motors()
    print("Motores OK.")

    try:
        from src.core.config import SPEED_SLOW_TPS
    except ImportError:
        SPEED_SLOW_TPS = 20
    base_tps_fwd = args.teleop_tps
    turn_tps = args.turn_tps
    yaw_ref = None  # definido ao entrar em forward/back no teleop
    command = "stop"
    use_timeout = sys.stdin.isatty() and sys.platform == "linux" and not args.no_arrows

    print_instructions()
    while True:
        if qt_app:
            qt_app.processEvents()
        if use_timeout:
            key = get_key_or_none(0.02)
        else:
            print("  Comando (W/S/A/D 1 4 6 X 0): ", end="", flush=True)
            key = get_key_blocking()
        if key is not None and key != "":
            if key in ("q", "0"):
                print("Saindo.")
                motors.stop_motors()
                break
            if key in ("x", " ", "8"):
                command = "stop"
                motors.stop_motors()
                print("Parar.")
                continue
            if key in ("w", "1"):
                if key == "1":
                    cmd_forward_straight(
                        motors, args.forward_duration, get_bno_yaw, qt_app,
                        SPEED_SLOW_TPS, args.kp, args.max_correction, args.invert_correction
                    )
                else:
                    command = "forward"
                    yaw_ref = get_bno_yaw() if get_bno_yaw else None
            elif key == "s":
                command = "back"
                yaw_ref = get_bno_yaw() if get_bno_yaw else None
            elif key == "a":
                command = "turn_left"
            elif key == "d":
                command = "turn_right"
            elif key == "2":
                cmd_turn(motors, 45, True, turn_tps, get_bno_yaw, qt_app)
            elif key == "3":
                cmd_turn(motors, 90, True, turn_tps, get_bno_yaw, qt_app)
            elif key == "4":
                cmd_turn(motors, 180, True, turn_tps, get_bno_yaw, qt_app)
            elif key == "5":
                cmd_turn(motors, 45, False, turn_tps, get_bno_yaw, qt_app)
            elif key == "6":
                cmd_turn(motors, 90, False, turn_tps, get_bno_yaw, qt_app)
            elif key == "7":
                cmd_turn(motors, 180, False, turn_tps, get_bno_yaw, qt_app)
            elif key in ("", "\n", "\r", "^", "[", "O"):
                continue
            else:
                continue
        # Aplicar comando contínuo (teleop)
        if command == "forward":
            ref = yaw_ref if yaw_ref is not None else (get_bno_yaw() or 0.0)
            left, right = compute_straight_correction(
                ref, get_bno_yaw, base_tps_fwd, args.kp, args.max_correction, args.invert_correction
            )
            motors.set_target_speed(left, right)
        elif command == "back":
            ref = yaw_ref if yaw_ref is not None else (get_bno_yaw() or 0.0)
            left, right = compute_straight_correction(
                ref, get_bno_yaw, -base_tps_fwd, args.kp, args.max_correction, args.invert_correction
            )
            motors.set_target_speed(left, right)
        elif command == "turn_left":
            motors.set_precise_rotation_direction(-1, 1)
            motors.set_target_speed(-turn_tps, turn_tps)
        elif command == "turn_right":
            motors.set_precise_rotation_direction(1, -1)
            motors.set_target_speed(turn_tps, -turn_tps)
        elif command == "stop":
            motors.stop_motors()
            motors.clear_precise_rotation_direction()
        time.sleep(0.02)


if __name__ == "__main__":
    main()
