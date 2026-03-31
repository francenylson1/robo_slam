#!/usr/bin/env python3
"""
Inicialização do BNO08x alinhada ao tools/bno08x_test.py (que funciona na Raspberry).

- Opcional `do_reset_cycle=True`: RST LOW 0.15 s, depois HIGH 0.35 s (segunda tentativa no joystick).
- Mesma ordem de I2C (D3/D2, SCL/SDA, board.I2C(), ExtendedI2C(1)).
- Mesmos relatórios habilitados: ACCELEROMETER, GYROSCOPE, ROTATION_VECTOR.
- debug=False e reset=None na biblioteca (evita dump de pacotes e conflitos).
- Patches 0x7B: debug.reports, _AVAIL_SENSOR_REPORTS, skip em BNO08X._process_report (evita falha no enable_feature).
- Retry: até 4 tentativas (conexão + enable + yaw válido); I2C unlock antes de abrir o sensor.

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

def _apply_bno08x_library_patches():
    """
    Compatibilidade com firmwares que enviam relatório 0x7B (padding/reservado):
    a lib Adafruit faz reports[report_id] e _AVAIL_SENSOR_REPORTS[report_id] — sem isto,
    enable_feature() pode falhar com KeyError e o init devolve (None, None).
    Também ignora 0x7B em BNO08X._process_report (mais seguro entre versões).
    """
    try:
        import adafruit_bno08x as _bno_mod
        _orig_rl = getattr(_bno_mod, "_report_length", None)
        if callable(_orig_rl):
            def _safe_rl(rid):
                try:
                    return _orig_rl(rid)
                except KeyError:
                    return 16
            _bno_mod._report_length = _safe_rl
    except Exception:
        pass
    try:
        from adafruit_bno08x import debug as _bno_debug
        _bno_debug.reports.setdefault(0x7B, "PAD_OR_UNKNOWN_0x7B")
    except Exception:
        pass
    try:
        import adafruit_bno08x as _m
        _q14 = getattr(_m, "_Q_POINT_14_SCALAR", 2 ** (14 * -1))
        _ar = getattr(_m, "_AVAIL_SENSOR_REPORTS", None)
        if isinstance(_ar, dict) and 0x7B not in _ar:
            # Mesmo formato que ROTATION_VECTOR (quat); descartado pelo skip abaixo se incorreto
            _ar[0x7B] = (_q14, 4, 14)
    except Exception:
        pass
    try:
        from adafruit_bno08x import BNO08X
        from adafruit_bno08x import debug as _bno_dbgmod
        if not getattr(BNO08X, "_robo_safe_process_report_patched", False):
            _orig_pr = BNO08X._process_report

            def _robo_safe_process_report(self, report_id, report_bytes):
                # 0x7B = padding; firmware também envia IDs não mapeados na Adafruit → KeyError / UNKNOWN
                if report_id == 0x7B:
                    return
                if report_id < 0xF0 and _bno_dbgmod.reports.get(report_id) is None:
                    return
                try:
                    return _orig_pr(self, report_id, report_bytes)
                except KeyError:
                    return

            BNO08X._process_report = _robo_safe_process_report
            BNO08X._robo_safe_process_report_patched = True
    except Exception:
        pass


def _silence_bno08x_console_spam():
    """Evita que _dbg da Adafruit imprima blocos 'Packet' / DBG:: (I/O no terminal atrasa o teleop)."""
    try:
        from adafruit_bno08x import BNO08X

        setattr(BNO08X, "_dbg", lambda *args, **kwargs: None)
        try:
            from adafruit_bno08x import i2c as _bno_i2c

            if hasattr(_bno_i2c, "BNO08X_I2C"):
                setattr(_bno_i2c.BNO08X_I2C, "_dbg", lambda *args, **kwargs: None)
        except Exception:
            pass
    except Exception:
        pass


_apply_bno08x_library_patches()
_silence_bno08x_console_spam()


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

    try:
        i2c.unlock()
    except (ValueError, AttributeError, TypeError):
        pass

    addrs_to_try = [BNO08X_I2C_ADDRESS]
    if 0x4B not in addrs_to_try:
        addrs_to_try.append(0x4B)
    if 0x4A not in addrs_to_try:
        addrs_to_try.append(0x4A)

    # Várias tentativas: conexão, enable, yaw válido (pacote 0x7B costumava quebrar só o enable)
    max_init_attempts = 4
    for init_attempt in range(max_init_attempts):
        bno = None
        for addr in addrs_to_try:
            try:
                bno = BNO08X_I2C(i2c, reset=None, address=addr, debug=False)
                setattr(bno, "_debug", False)
                if verbose:
                    print("BNO08x conectado no endereço {}.".format(hex(addr)))
                break
            except Exception as e:
                if verbose:
                    print("BNO08x: falha em {}: {}".format(hex(addr), e))
                continue
        if bno is None:
            if verbose and init_attempt < max_init_attempts - 1:
                print("BNO08x: nenhum endereço respondeu; retry em 0,5 s...")
            time.sleep(0.5)
            continue

        time.sleep(0.2)
        features_ok = False
        for attempt in range(4):
            try:
                bno.enable_feature(BNO_REPORT_ACCELEROMETER)
                bno.enable_feature(BNO_REPORT_GYROSCOPE)
                bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)
                features_ok = True
                break
            except (RuntimeError, KeyError, ValueError) as e:
                if attempt < 3 and (
                    "enable" in str(e).lower()
                    or "key" in str(e).lower()
                    or "report" in str(e).lower()
                ):
                    time.sleep(0.35)
                    continue
                if verbose:
                    print("BNO08x: enable_feature: {}".format(e))
                break
            except Exception as e:
                if verbose:
                    print("BNO08x: enable_feature (exc): {}".format(e))
                if attempt < 3:
                    time.sleep(0.35)
                    continue
                break
        if not features_ok:
            if verbose and init_attempt < max_init_attempts - 1:
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

        # Warm-up + confirmação de yaw (senão teleop pensa que há BNO e não há leitura útil)
        for _ in range(20):
            try:
                _ = bno.quaternion
            except Exception:
                pass
            time.sleep(0.04)

        yaw_ready = False
        for _ in range(18):
            if get_yaw() is not None:
                yaw_ready = True
                break
            time.sleep(0.04)
        if not yaw_ready:
            if verbose and init_attempt < max_init_attempts - 1:
                print("BNO08x: yaw ainda indisponível após warm-up; retry...")
            time.sleep(0.45)
            continue

        return bno, get_yaw

    return None, None
