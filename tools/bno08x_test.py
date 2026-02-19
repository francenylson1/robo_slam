#!/usr/bin/env python3
"""
Teste do IMU BNO08x no Raspberry Pi.
Fiação: I2C (SDA, SCL), alimentação, GPIO 26 = RST, GPIO 27 = INT.
Pinos definidos em src/core/config.py (BNO08X_GPIO_RST, BNO08X_GPIO_INT).

Uso:
  python tools/bno08x_test.py          # leitura contínua
  python tools/bno08x_test.py --calibrate  # inicia calibração (deixe parado e plano)

Requer na Raspberry Pi:
  pip install adafruit-blinka adafruit-circuitpython-bno08x
  I2C habilitado: sudo raspi-config -> Interface Options -> I2C
  Opcional em /boot/config.txt: dtparam=i2c_arm_baudrate=400000
"""

import sys
import os
# Permite importar config do projeto
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import time
import argparse

# Verifica se estamos no Raspberry Pi antes de importar hardware
def _is_raspberry_pi():
    try:
        with open("/proc/device-tree/model", "r") as f:
            return "raspberry" in f.read().lower()
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Teste IMU BNO08x (I2C, GPIO 26=RST, 27=INT)")
    parser.add_argument("--calibrate", action="store_true", help="Iniciar calibração (deixe o sensor parado e plano)")
    parser.add_argument("--interval", type=float, default=0.2, help="Intervalo entre leituras em segundos (default 0.2)")
    parser.add_argument("--count", type=int, default=0, help="Número de leituras (0 = infinito)")
    args = parser.parse_args()

    if not _is_raspberry_pi():
        print("Este script deve ser executado na Raspberry Pi (IMU BNO08x conectado por I2C/GPIO).")
        print("No desktop não há hardware para testar.")
        sys.exit(1)

    try:
        import board
        import busio
        from digitalio import DigitalInOut
    except ImportError:
        print("Instale adafruit-blinka: pip install adafruit-blinka")
        sys.exit(1)

    try:
        from adafruit_bno08x.i2c import BNO08X_I2C
        from adafruit_bno08x import (
            BNO_REPORT_ACCELEROMETER,
            BNO_REPORT_GYROSCOPE,
            BNO_REPORT_ROTATION_VECTOR,
        )
    except ImportError:
        print("Instale adafruit-circuitpython-bno08x: pip install adafruit-circuitpython-bno08x")
        sys.exit(1)

    try:
        from src.core.config import BNO08X_GPIO_RST, BNO08X_GPIO_INT, BNO08X_I2C_ADDRESS
    except ImportError:
        BNO08X_GPIO_RST = 26
        BNO08X_GPIO_INT = 27
        BNO08X_I2C_ADDRESS = 0x4A

    print("Inicializando I2C e pino de reset (GPIO {}).".format(BNO08X_GPIO_RST))
    i2c = busio.I2C(board.SCL, board.SDA)
    reset_pin = DigitalInOut(getattr(board, "D{}".format(BNO08X_GPIO_RST)))
    reset_pin.direction = DigitalInOut.Direction.OUTPUT

    try:
        bno = BNO08X_I2C(i2c, reset=reset_pin, address=BNO08X_I2C_ADDRESS)
    except Exception as e:
        print("Erro ao conectar ao BNO08x:", e)
        print("Verifique: I2C ativado (raspi-config), fiação (SDA/SCL/VCC/GND, RST no GPIO 26).")
        sys.exit(1)

    print("BNO08x conectado. Habilitando relatórios (acelerômetro, giro, rotação).")
    bno.enable_feature(BNO_REPORT_ACCELEROMETER)
    bno.enable_feature(BNO_REPORT_GYROSCOPE)
    bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)

    # Status de calibração (0 = não calibrado, 3 = totalmente calibrado)
    try:
        status = bno.calibration_status
        print("Status de calibração (0-3, 3=ok):", status)
        if status < 3:
            print("  Sugestão: execute com --calibrate e deixe o sensor parado e plano por alguns segundos.")
    except Exception as e:
        print("(Não foi possível ler calibration_status:", e, ")")

    if args.calibrate:
        print("Iniciando calibração. Mantenha o sensor parado e em superfície plana...")
        try:
            bno.begin_calibration()
            print("Calibração iniciada. Aguarde ~10–30 s e depois interrompa com Ctrl+C.")
            n = 0
            while True:
                time.sleep(0.5)
                try:
                    s = bno.calibration_status
                    n += 1
                    if n % 4 == 0:
                        print("  Calibração status:", s)
                except Exception:
                    pass
        except KeyboardInterrupt:
            print("\nCalibração interrompida.")
        return

    print("Leitura contínua (Ctrl+C para sair). Intervalo: {} s\n".format(args.interval))
    n = 0
    try:
        while True:
            try:
                accel_x, accel_y, accel_z = bno.acceleration
                gyro_x, gyro_y, gyro_z = bno.gyro
                quat_i, quat_j, quat_k, quat_real = bno.quaternion
                # Ângulos de Euler aproximados a partir do quaternion (em graus)
                import math
                siny_cosp = 2 * (quat_real * quat_k + quat_i * quat_j)
                cosy_cosp = 1 - 2 * (quat_j * quat_j + quat_k * quat_k)
                yaw = math.degrees(math.atan2(siny_cosp, cosy_cosp))
                sinp = 2 * (quat_real * quat_j - quat_k * quat_i)
                if abs(sinp) >= 1:
                    pitch = math.degrees(math.copysign(math.pi / 2, sinp))
                else:
                    pitch = math.degrees(math.asin(sinp))
                sinr_cosp = 2 * (quat_real * quat_i + quat_j * quat_k)
                cosr_cosp = 1 - 2 * (quat_i * quat_i + quat_j * quat_j)
                roll = math.degrees(math.atan2(sinr_cosp, cosr_cosp))

                print(
                    "Accel: {:+.2f} {:+.2f} {:+.2f} m/s² | "
                    "Giro: {:+.2f} {:+.2f} {:+.2f} rad/s | "
                    "Yaw/Pitch/Roll: {:+.1f} {:+.1f} {:+.1f}°".format(
                        accel_x, accel_y, accel_z,
                        gyro_x, gyro_y, gyro_z,
                        yaw, pitch, roll
                    )
                )
            except Exception as e:
                print("Erro na leitura:", e)
            n += 1
            if args.count > 0 and n >= args.count:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário.")


if __name__ == "__main__":
    main()
