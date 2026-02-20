#!/usr/bin/env python3
"""
Menu de comandos do robô para testes manuais: frente, esquerda e direita (45°, 90°, 180°).
Permite usar teclado numérico/menu ou setas: ↑ Frente, ← Esquerda 90°, → Direita 90°, ↓ Parar.

Executar apenas na Raspberry Pi. Uso (na raiz do projeto):
  python tools/robot_command_menu.py
  python tools/robot_command_menu.py --forward-duration 3 --turn-tps 12
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


# ---------------------------------------------------------------------------
# Leitura de tecla (setas e um caractere)
# ---------------------------------------------------------------------------
def _get_key_linux():
    """Lê uma tecla (incluindo setas) no Linux. Retorna 'up','down','left','right' ou o caractere."""
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            c2 = sys.stdin.read(1)
            if c2 == "[":
                c3 = sys.stdin.read(1)
                if c3 == "A":
                    return "up"
                if c3 == "B":
                    return "down"
                if c3 == "C":
                    return "right"
                if c3 == "D":
                    return "left"
        return ch.lower() if ch else ""
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def get_key():
    """Lê uma tecla. Em Windows ou sem termios retorna input() de um char (com Enter)."""
    if sys.platform == "linux":
        try:
            return _get_key_linux()
        except Exception:
            pass
    # Fallback: pedir um caractere com Enter
    try:
        line = input().strip().lower()
        if line in ("up", "down", "left", "right"):
            return line
        if line in ("w", "8", "f"):
            return "up"
        if line in ("s", "2"):
            return "down"
        if line in ("a", "4", "l"):
            return "left"
        if line in ("d", "6", "r"):
            return "right"
        return line[0] if line else ""
    except (EOFError, IndexError):
        return "q"


# ---------------------------------------------------------------------------
# BNO08x (opcional)
# ---------------------------------------------------------------------------
def init_bno():
    """Inicializa BNO08x. Retorna (bno, get_yaw) ou (None, None)."""
    try:
        import board
        import busio
        import digitalio
        from digitalio import DigitalInOut
        Direction = getattr(digitalio, "Direction", None) or getattr(DigitalInOut, "Direction", None)
    except ImportError:
        return None, None
    try:
        from adafruit_bno08x.i2c import BNO08X_I2C
        from adafruit_bno08x import (
            BNO_REPORT_ACCELEROMETER,
            BNO_REPORT_GYROSCOPE,
            BNO_REPORT_ROTATION_VECTOR,
        )
    except ImportError:
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
        return None, None
    time.sleep(0.2)
    for attempt in range(3):
        try:
            bno.enable_feature(BNO_REPORT_ACCELEROMETER)
            bno.enable_feature(BNO_REPORT_GYROSCOPE)
            bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)
            break
        except RuntimeError:
            time.sleep(0.3)
    else:
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


# ---------------------------------------------------------------------------
# Motores
# ---------------------------------------------------------------------------
def init_motors():
    from PyQt5.QtCore import QCoreApplication
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication(sys.argv)
    from src.core.robot_motor_controller import RobotMotorController
    return RobotMotorController()


def ticks_to_angle_deg(left_ticks, right_ticks, tpr, circ_m, base_m):
    dist_l = (left_ticks / tpr) * circ_m
    dist_r = (right_ticks / tpr) * circ_m
    return math.degrees((dist_l - dist_r) / base_m)


def cmd_forward(motors, duration_s, get_bno_yaw):
    from src.core.config import SPEED_SLOW_TPS
    print("  → Frente por {:.1f} s ...".format(duration_s))
    yaw0 = get_bno_yaw() if get_bno_yaw else None
    motors.set_target_speed(SPEED_SLOW_TPS, SPEED_SLOW_TPS)
    t0 = time.time()
    while time.time() - t0 < duration_s:
        time.sleep(0.05)
    motors.stop_motors()
    yaw1 = get_bno_yaw() if get_bno_yaw else None
    if yaw0 is not None and yaw1 is not None:
        print("  BNO yaw: {:.1f}° → {:.1f}° (deriva: {:.1f}°)".format(yaw0, yaw1, yaw1 - yaw0))
    print("  Frente concluído.")


def cmd_turn(motors, target_deg, left_turn, turn_tps, get_bno_yaw):
    from src.core.config import (
        TICKS_PER_REVOLUTION,
        ROBOT_WHEEL_CIRCUMFERENCE_M,
        ROBOT_WHEEL_BASE_M,
    )
    lado = "Esquerda" if left_turn else "Direita"
    print("  → Giro {} {:.0f}° ...".format(lado, target_deg))
    if left_turn:
        motors.set_precise_rotation_direction(1, -1)
        motors.set_target_speed(turn_tps, -turn_tps)
    else:
        motors.set_precise_rotation_direction(-1, 1)
        motors.set_target_speed(-turn_tps, turn_tps)
    angle_odom = 0.0
    yaw0 = get_bno_yaw() if get_bno_yaw else None
    # Esquerda: delta > 0, parar quando angle_odom >= target_deg. Direita: delta < 0, parar quando angle_odom <= -target_deg.
    while (left_turn and angle_odom < target_deg) or (not left_turn and angle_odom > -target_deg):
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
    yaw1 = get_bno_yaw() if get_bno_yaw else None
    alvo = target_deg if left_turn else -target_deg
    print("  Odometria: {:.1f}° (alvo {:.0f}°) → erro {:.1f}°".format(
        angle_odom, alvo, angle_odom - alvo))
    if yaw0 is not None and yaw1 is not None:
        print("  BNO yaw: {:.1f}° → {:.1f}° (delta: {:.1f}°)".format(yaw0, yaw1, yaw1 - yaw0))
    print("  Giro concluído.")


def print_menu():
    print()
    print("  ═══════════ MENU DE COMANDOS DO ROBÔ ═══════════")
    print("  SETAS:  ↑ Frente    ← Esquerda 90°   → Direita 90°   ↓ Parar")
    print("  ─────────────────────────────────────────────────")
    print("  1 - Frente (avançar)")
    print("  2 - Esquerda  45°    3 - Esquerda  90°    4 - Esquerda  180°")
    print("  5 - Direita   45°    6 - Direita   90°    7 - Direita   180°")
    print("  8 - Parar")
    print("  0 ou Q - Sair")
    print("  ═══════════════════════════════════════════════════")
    print("  Comando (tecla ou número): ", end="", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Menu de comandos do robô (frente, giros 45/90/180°)")
    parser.add_argument("--forward-duration", type=float, default=2.5,
                        help="Duração do avanço em segundos (default 2.5)")
    parser.add_argument("--turn-tps", type=float, default=12.0,
                        help="TPS para giros no lugar (default 12)")
    parser.add_argument("--no-arrows", action="store_true",
                        help="Usar apenas números/letras (sem leitura de setas)")
    args = parser.parse_args()

    if not is_raspberry_pi():
        print("Execute este script na Raspberry Pi.")
        sys.exit(1)

    print("Inicializando BNO08x (opcional)...")
    bno, get_bno_yaw = init_bno()
    if bno is None:
        print("BNO08x não disponível. Dados de yaw não serão exibidos.")
    else:
        print("BNO08x OK.")

    print("Inicializando motores...")
    motors = init_motors()
    print("Motores OK.")

    use_arrows = not args.no_arrows and sys.platform == "linux"
    if use_arrows:
        print("Modo setas ativo (↑↓←→). Use também 0-8 ou F/L/R/S/Q.")
    else:
        print("Digite o número ou letra e Enter (ex: 1, 6, F, Q).")

    while True:
        print_menu()
        if use_arrows:
            try:
                key = _get_key_linux()
            except Exception:
                key = get_key()
        else:
            key = get_key()

        if not key:
            continue

        # Sair
        if key in ("0", "q"):
            print("Saindo.")
            motors.stop_motors()
            break

        # Parar
        if key in ("8", "s", "down"):
            print("  → Parar.")
            motors.stop_motors()
            continue

        # Frente
        if key in ("1", "f", "up"):
            cmd_forward(motors, args.forward_duration, get_bno_yaw)
            continue

        # Esquerda 90° (seta ou L)
        if key in ("l", "left"):
            cmd_turn(motors, 90, True, args.turn_tps, get_bno_yaw)
            continue
        # Direita 90° (seta ou R)
        if key in ("r", "right"):
            cmd_turn(motors, 90, False, args.turn_tps, get_bno_yaw)
            continue

        # Menu numérico
        if key == "2":
            cmd_turn(motors, 45, True, args.turn_tps, get_bno_yaw)
        elif key == "3":
            cmd_turn(motors, 90, True, args.turn_tps, get_bno_yaw)
        elif key == "4":
            cmd_turn(motors, 180, True, args.turn_tps, get_bno_yaw)
        elif key == "5":
            cmd_turn(motors, 45, False, args.turn_tps, get_bno_yaw)
        elif key == "6":
            cmd_turn(motors, 90, False, args.turn_tps, get_bno_yaw)
        elif key == "7":
            cmd_turn(motors, 180, False, args.turn_tps, get_bno_yaw)
        else:
            print("  Tecla não reconhecida. Use 0-8, F/L/R/S/Q ou setas.")


if __name__ == "__main__":
    main()
