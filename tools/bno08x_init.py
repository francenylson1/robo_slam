#!/usr/bin/env python3
"""
Inicialização do BNO08x alinhada ao tools/bno08x_test.py (que funciona na Raspberry).

- Reset completo no início de cada uso: RST LOW 0.15 s, depois HIGH 0.35 s.
- Mesma ordem de I2C (D3/D2, SCL/SDA, board.I2C(), ExtendedI2C(1)).
- Mesmos relatórios habilitados: ACCELEROMETER, GYROSCOPE, ROTATION_VECTOR.
- debug=False e reset=None na biblioteca (evita dump de pacotes e conflitos).
- Patch _report_length para report 0x7B (evita KeyError e instabilidade).
- Retry: até 2 tentativas de conexão + enable (0,5 s entre tentativas) para maior confiabilidade.

Uso (a partir da raiz do projeto):
  from tools.bno08x_init import init_bno
  bno, get_yaw = init_bno()
"""

import sys
import os
import math
import time

# Permite importar config do projeto
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Patch do report 0x7B ao carregar o módulo (igual bno08x_test evita KeyError em todos os scripts)
def _apply_bno07b_patch():
    try:
        import adafruit_bno08x as _bno_mod
        _orig = getattr(_bno_mod, "_report_length", None)
        if callable(_orig):
            def _safe(rid):
                try:
                    return _orig(rid)
                except KeyError:
                    return 16
            _bno_mod._report_length = _safe
    except Exception:
        pass
_apply_bno07b_patch()


def init_bno(do_reset_cycle=False, verbose=True):
    """
    Inicializa o BNO08x exatamente como bno08x_test.py (que funciona na Raspberry).

    Args:
        do_reset_cycle: se False (padrão), só coloca RST em HIGH (como bno08x_test).
                       Se True, faz LOW 0.15 s depois HIGH (pode causar 0x7B em alguns casos).
        verbose: se True, imprime mensagens (I2C, RST, endereço).

    Returns:
        (bno, get_yaw) ou (None, None) em caso de falha.
    """
    try:
        import board
        import busio
        import digitalio
        from digitalio import DigitalInOut
        Direction = getattr(digitalio, "Direction", None)
        if Direction is None:
            Direction = getattr(DigitalInOut, "Direction", None)
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

    # RST: igual bno08x_test — só HIGH (sem ciclo LOW) para sensor sair do reset e não gerar 0x7B
    if BNO08X_GPIO_RST is not None:
        rst_pin = DigitalInOut(getattr(board, "D{}".format(BNO08X_GPIO_RST)))
        if Direction is not None:
            rst_pin.direction = Direction.OUTPUT
        else:
            rst_pin.direction = 1
        if do_reset_cycle:
            rst_pin.value = False
            time.sleep(0.15)
            if verbose:
                print("BNO08x: RST LOW 0.15 s (reset).")
        rst_pin.value = True
        if verbose:
            print("BNO08x: GPIO {} (RST) em HIGH.".format(BNO08X_GPIO_RST))
        time.sleep(0.35)

    # I2C — mesma ordem que bno08x_test.py
    i2c = None
    for scl_name, sda_name in [("D3", "D2"), ("SCL", "SDA")]:
        try:
            scl = getattr(board, scl_name, None)
            sda = getattr(board, sda_name, None)
            if scl is not None and sda is not None:
                i2c = busio.I2C(scl, sda)
                if verbose:
                    print("BNO08x: I2C em {} (SCL) e {} (SDA).".format(scl_name, sda_name))
                break
        except Exception:
            if i2c is not None:
                break
            continue
    if i2c is None and hasattr(board, "I2C") and callable(getattr(board, "I2C", None)):
        try:
            i2c = board.I2C()
            if verbose:
                print("BNO08x: board.I2C().")
        except Exception:
            pass
    if i2c is None:
        try:
            from adafruit_extended_bus import ExtendedI2C
            i2c = ExtendedI2C(1)
            if verbose:
                print("BNO08x: ExtendedI2C(1).")
        except ImportError:
            pass
        except Exception:
            pass
    if i2c is None:
        return None, None

    addrs_to_try = [BNO08X_I2C_ADDRESS]
    if 0x4B not in addrs_to_try:
        addrs_to_try.append(0x4B)
    if 0x4A not in addrs_to_try:
        addrs_to_try.append(0x4A)

    # Retry até 2 vezes (conexão + enable) para maior confiabilidade na navegação
    max_init_attempts = 2
    for init_attempt in range(max_init_attempts):
        bno = None
        for addr in addrs_to_try:
            try:
                bno = BNO08X_I2C(i2c, reset=None, address=addr, debug=False)
                if verbose:
                    print("BNO08x conectado no endereço {}.".format(hex(addr)))
                break
            except Exception as e:
                err_str = str(e).lower()
                if "address" in err_str or "0x4" in err_str:
                    continue
                break
        if bno is None:
            if init_attempt < max_init_attempts - 1 and verbose:
                print("BNO08x: conexão falhou; retry em 0,5 s...")
            time.sleep(0.5)
            continue

        time.sleep(0.2)
        features_ok = False
        for attempt in range(3):
            try:
                bno.enable_feature(BNO_REPORT_ACCELEROMETER)
                bno.enable_feature(BNO_REPORT_GYROSCOPE)
                bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)
                features_ok = True
                break
            except RuntimeError as e:
                if attempt < 2 and "enable" in str(e).lower():
                    time.sleep(0.3)
                    continue
                break
        if not features_ok:
            if init_attempt < max_init_attempts - 1 and verbose:
                print("BNO08x: enable features falhou; retry em 0,5 s...")
            time.sleep(0.5)
            continue

        def get_yaw():
            try:
                quat_i, quat_j, quat_k, quat_real = bno.quaternion
                siny_cosp = 2 * (quat_real * quat_k + quat_i * quat_j)
                cosy_cosp = 1 - 2 * (quat_j * quat_j + quat_k * quat_k)
                yaw = math.degrees(math.atan2(siny_cosp, cosy_cosp))
                while yaw > 180:
                    yaw -= 360
                while yaw < -180:
                    yaw += 360
                return yaw
            except Exception:
                return None

        # Warm-up: algumas leituras para o ROTATION_VECTOR começar a chegar antes do uso
        for _ in range(8):
            try:
                _ = bno.quaternion
            except Exception:
                pass
            time.sleep(0.05)

        return bno, get_yaw

    return None, None
