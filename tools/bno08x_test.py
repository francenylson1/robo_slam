#!/usr/bin/env python3
"""
Teste do IMU BNO08x no Raspberry Pi.
Fiação: I2C (SDA, SCL), alimentação; GPIO 27 = INT (opcional). RST não usado (config: BNO08X_GPIO_RST = None).
Pinos em src/core/config.py (BNO08X_GPIO_RST, BNO08X_GPIO_INT, BNO08X_I2C_ADDRESS).

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
        import digitalio
        from digitalio import DigitalInOut
        # Direction fica no módulo digitalio, não em DigitalInOut (evita AttributeError em algumas versões do Blinka)
        Direction = getattr(digitalio, "Direction", None)
        if Direction is None:
            Direction = getattr(DigitalInOut, "Direction", None)
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
        BNO08X_I2C_ADDRESS = 0x4B

    # RST é active-LOW: com GPIO em LOW o BNO08x fica em reset e não aparece no I2C.
    # Colocar RST em HIGH logo no início (antes do I2C) evita ter que rodar "raspi-gpio set 26 op dh" no terminal.
    # O pino não é passado à biblioteca (reset=None) para não haver toggle e ruído.
    if BNO08X_GPIO_RST is not None:
        rst_hold = DigitalInOut(getattr(board, "D{}".format(BNO08X_GPIO_RST)))
        if Direction is not None:
            rst_hold.direction = Direction.OUTPUT
        else:
            rst_hold.direction = 1
        rst_hold.value = True
        print("GPIO {} (RST) em HIGH para sensor sair do reset.".format(BNO08X_GPIO_RST))
        time.sleep(0.35)  # BNO08x precisa de ~300 ms após sair do reset antes de aceitar comandos

    print("Inicializando I2C.")
    # Barramento I2C: em alguns Raspberry (ex. Pi 5) board.SCL/SDA dão "No Hardware I2C on (3,2)".
    # Valid ports costumam ser (bus, SCL, SDA) = (1, 3, 2) = I2C1 com GPIO3=SCL, GPIO2=SDA.
    i2c = None
    # 1) Tentar pinos explícitos do I2C1 (GPIO3=SCL, GPIO2=SDA) que o erro indicou como válidos
    for scl_name, sda_name in [("D3", "D2"), ("SCL", "SDA")]:
        try:
            scl = getattr(board, scl_name, None)
            sda = getattr(board, sda_name, None)
            if scl is not None and sda is not None:
                i2c = busio.I2C(scl, sda)
                print("Usando I2C em {} (SCL) e {} (SDA).".format(scl_name, sda_name))
                break
        except Exception as e:
            if i2c is not None:
                break
            continue
    # 2) Fallback: board.I2C() se existir
    if i2c is None and hasattr(board, "I2C") and callable(getattr(board, "I2C", None)):
        try:
            i2c = board.I2C()
            print("Usando board.I2C().")
        except Exception as e:
            print("board.I2C() falhou:", e)
    # 3) Fallback: adafruit_extended_bus abre /dev/i2c-1 diretamente (evita problema de pinos no Blinka)
    if i2c is None:
        try:
            from adafruit_extended_bus import ExtendedI2C
            i2c = ExtendedI2C(1)  # /dev/i2c-1 = I2C1 no header 40-pin
            print("Usando ExtendedI2C(1) (/dev/i2c-1).")
        except ImportError:
            pass
        except Exception as e:
            print("ExtendedI2C(1) falhou:", e)
    if i2c is None:
        print("Erro: não foi possível criar o barramento I2C.")
        print("Confirme que I2C está ativado: sudo raspi-config -> Interface Options -> I2C")
        print("Verifique: ls /dev/i2c*  (deve listar /dev/i2c-1 etc.)")
        print("Se usar Pi 5 ou outro modelo, tente: pip install adafruit-extended-bus e reinicie o script.")
        sys.exit(1)

    # Não passamos o pino RST à biblioteca (reset=None) para evitar toggle e ruído; já deixamos RST em HIGH acima.
    reset_pin = None

    # Varredura I2C: lista endereços presentes no barramento (ajuda a ver se 0x4A/0x4B aparecem)
    print("Varredura I2C (0x08-0x77)...")
    try:
        i2c.unlock()
    except (ValueError, AttributeError):
        pass
    try:
        if hasattr(i2c, "try_lock") and i2c.try_lock():
            found = []
            for addr in range(0x08, 0x78):
                try:
                    i2c.writeto(addr, bytearray([]))
                    found.append(hex(addr))
                except (OSError, RuntimeError):
                    pass
            i2c.unlock()
            if found:
                print("  Dispositivos encontrados:", ", ".join(found))
                if "0x4a" not in [a.lower() for a in found] and "0x4b" not in [a.lower() for a in found]:
                    print("  BNO08x usa 0x4A (BNO085) ou 0x4B (BNO080). Nenhum dos dois apareceu.")
            else:
                print("  Nenhum dispositivo I2C encontrado. Verifique fiação (SDA/SCL/VCC/GND).")
    except Exception as scan_err:
        print("  (varredura não disponível:", scan_err, ")")

    # Tentar 0x4A (BNO085) e 0x4B (BNO080); alguns módulos/jumper ADR usam 0x4B
    addrs_to_try = [BNO08X_I2C_ADDRESS]
    if 0x4B not in addrs_to_try:
        addrs_to_try.append(0x4B)
    if 0x4A not in addrs_to_try:
        addrs_to_try.append(0x4A)
    bno = None
    for addr in addrs_to_try:
        try:
            bno = BNO08X_I2C(i2c, reset=reset_pin, address=addr, debug=False)  # debug=False evita dump de pacotes SHTP no log
            print("BNO08x conectado no endereço {}.".format(hex(addr)))
            break
        except Exception as e:
            err_str = str(e).lower()
            if "address" in err_str or "0x4" in err_str:
                continue
            raise
    if bno is None:
        print("Erro: BNO08x não respondeu em 0x4A nem 0x4B.")
        print("Verifique: alimentação 3V3, GND, SDA/SCL. Alguns módulos têm jumper ADR (0x4A vs 0x4B).")
        print("PS0/PS1 do BNO08x devem estar no nível correto para modo I2C (consulte o datasheet).")
        sys.exit(1)

    time.sleep(0.2)  # Pequena pausa após abrir conexão antes de habilitar relatórios
    print("BNO08x conectado. Habilitando relatórios (acelerômetro, giro, rotação).")
    for attempt in range(3):
        try:
            bno.enable_feature(BNO_REPORT_ACCELEROMETER)
            bno.enable_feature(BNO_REPORT_GYROSCOPE)
            bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)
            break
        except RuntimeError as e:
            if attempt < 2 and "enable feature" in str(e).lower():
                time.sleep(0.3)
                continue
            raise

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
    read_errors = 0  # erros pontuais (pacotes não-sensor) são normais; não enchem o log
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
                read_errors += 1
                # Pacotes não-sensor (timestamp, comando, etc.) geram exceção; é normal. Só avisa de 5 em 5 erros.
                if read_errors <= 1 or read_errors % 5 == 0:
                    print("  [leitura ignorada {}x: {}]".format(read_errors, e))
            n += 1
            if args.count > 0 and n >= args.count:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário.")
        if read_errors > 0:
            print("(Durante a execução, {} leituras foram ignoradas por pacotes não-sensor – normal no BNO08x.)".format(read_errors))


if __name__ == "__main__":
    main()
