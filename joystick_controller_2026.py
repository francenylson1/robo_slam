#!/usr/bin/env python3
"""
joystick_controller_2026.py — Controle manual do robô via joystick iPega PG-9076

Modo de uso:
  python joystick_controller_2026.py             # controle normal com BNO
  python joystick_controller_2026.py --identify  # identifica eixos/botões (calibração)
  python joystick_controller_2026.py --no-bno    # frente sem correção BNO
  python joystick_controller_2026.py --tps 25    # velocidade máxima personalizada

Mapeamento dos controles (iPega PG-9076 no modo PC):
  Analógico esquerdo Y   →  Frente (cima) / Ré (baixo) — velocidade proporcional
  Analógico esquerdo X   →  Giro esquerda/direita — proporcional
  Analógico direito      →  Reservado (futuro)
  Botão B (círculo)      →  PARAR imediatamente
  Botão L1               →  Reduzir velocidade base (-5 TPS)
  Botão R1               →  Aumentar velocidade base (+5 TPS)
  Botão Start            →  Sair do programa

Correção BNO:
  Quando o robô vai reto (eixo Y dominante, X < 20%), o BNO08x corrige
  automaticamente qualquer desvio angular, mantendo a linha reta.
  Ao iniciar um giro (X > 20%), a referência BNO é descartada e o controle
  passa a ser puramente diferencial (sem conflito com o BNO).

Execute na Raspberry Pi com o joystick conectado via Bluetooth ou USB.
"""

import sys
import os
import time
import math
import argparse

# ── Raiz do projeto no sys.path ───────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ─────────────────────────────────────────────────────────────────────────────
# Mapeamento iPega PG-9076 (modo PC/XInput no Linux)
# Use  --identify  para confirmar estes valores no seu controle.
# ─────────────────────────────────────────────────────────────────────────────
AXIS_LEFT_X  = 0   # Analógico esquerdo, horizontal  (–1=esq, +1=dir)
AXIS_LEFT_Y  = 1   # Analógico esquerdo, vertical    (–1=frente, +1=ré)
AXIS_RIGHT_X = 2   # Analógico direito, horizontal
AXIS_RIGHT_Y = 3   # Analógico direito, vertical

BTN_A        = 0   # Botão A / Cruz         (confirmar)
BTN_B        = 1   # Botão B / Círculo      → PARAR
BTN_X        = 2   # Botão X / Quadrado
BTN_Y        = 3   # Botão Y / Triângulo
BTN_L1       = 4   # Ombro esquerdo         → velocidade –5 TPS
BTN_R1       = 5   # Ombro direito          → velocidade +5 TPS
BTN_L2       = 6   # Gatilho esquerdo (digital)
BTN_R2       = 7   # Gatilho direito (digital)
BTN_SELECT   = 8   # Select / Back
BTN_START    = 9   # Start                  → SAIR

# ─────────────────────────────────────────────────────────────────────────────
# Parâmetros de controle
# ─────────────────────────────────────────────────────────────────────────────
DEADZONE               = 0.12   # Zona morta do analógico (0–1). Ignora ruído do stick.
STRAIGHT_THRESHOLD_X   = 0.20   # Abaixo deste X: modo reto com BNO. Acima: giro puro.
TPS_DEFAULT            = 25.0   # Velocidade base padrão (Ticks Por Segundo)
TPS_MIN                = 10.0   # Velocidade mínima permitida
TPS_MAX                = 45.0   # Velocidade máxima permitida
TPS_STEP               = 5.0    # Passo de ajuste L1/R1
LOOP_HZ                = 50     # Frequência do loop de controle (50 Hz = 20 ms)

# D-pad — giro preciso com BNO (22.5° por clique = 16 cliques por volta completa)
HAT_ID                  = 0     # D-pad é o hat 0 na maioria dos controles
DPAD_TURN_DEG           = 22.5  # Graus por clique (360°/16)
DPAD_TURN_TPS           = 12.0  # Velocidade do giro (não muito rápido para BNO acompanhar)
DPAD_TURN_THRESHOLD_DEG = 1.0   # Para dentro desta margem do alvo (inércia faz o resto)
DPAD_TURN_TIMEOUT_S     = 4.0   # Timeout de segurança por clique


def is_raspberry_pi() -> bool:
    try:
        with open("/proc/device-tree/model", "r") as f:
            return "raspberry" in f.read().lower()
    except Exception:
        return False


def normalize_angle_deg(deg: float) -> float:
    while deg > 180:
        deg -= 360
    while deg < -180:
        deg += 360
    return deg


def apply_deadzone(value: float, deadzone: float) -> float:
    """Remove o ruído do centro do analógico e re-escala para [–1, +1]."""
    if abs(value) < deadzone:
        return 0.0
    sign = 1.0 if value > 0 else -1.0
    return sign * (abs(value) - deadzone) / (1.0 - deadzone)


# ─────────────────────────────────────────────────────────────────────────────
# Modo --identify : imprime eixos e botões em tempo real
# ─────────────────────────────────────────────────────────────────────────────
def run_identify_mode(joystick) -> None:
    """
    Imprime todos os eixos e botões em tempo real.
    Pressione cada botão/eixo para descobrir o índice correto.
    Pressione Ctrl+C para sair.
    """
    import pygame
    print()
    print("=" * 60)
    print("  MODO IDENTIFICAÇÃO — iPega PG-9076")
    print("  Mova os analógicos e pressione os botões.")
    print("  Ctrl+C para sair.")
    print("=" * 60)

    num_axes    = joystick.get_numaxes()
    num_buttons = joystick.get_numbuttons()
    num_hats    = joystick.get_numhats()
    print(f"  Eixos: {num_axes}  |  Botões: {num_buttons}  |  Hats: {num_hats}")
    print()

    prev_axes    = [0.0] * num_axes
    prev_buttons = [0]   * num_buttons
    prev_hats    = [(0, 0)] * num_hats

    try:
        while True:
            pygame.event.pump()

            axes    = [joystick.get_axis(i)   for i in range(num_axes)]
            buttons = [joystick.get_button(i) for i in range(num_buttons)]
            hats    = [joystick.get_hat(i)    for i in range(num_hats)]

            changed = False

            for i, (now, prev) in enumerate(zip(axes, prev_axes)):
                if abs(now - prev) > 0.05:
                    print(f"  [EIXO  {i:2d}] {now:+.3f}")
                    changed = True
            for i, (now, prev) in enumerate(zip(buttons, prev_buttons)):
                if now != prev:
                    estado = "PRESSIONADO" if now else "solto     "
                    print(f"  [BOTÃO {i:2d}] {estado}")
                    changed = True
            for i, (now, prev) in enumerate(zip(hats, prev_hats)):
                if now != prev:
                    print(f"  [HAT   {i:2d}] {now}")
                    changed = True

            prev_axes    = axes
            prev_buttons = buttons
            prev_hats    = hats

            time.sleep(0.04)

    except KeyboardInterrupt:
        print("\n  Identificação encerrada.")


# ─────────────────────────────────────────────────────────────────────────────
# Giro preciso via D-pad (BNO mede o ângulo girado)
# ─────────────────────────────────────────────────────────────────────────────
def cmd_turn_bno(motors, delta_deg: float, get_bno_yaw,
                 turn_tps: float, threshold_deg: float,
                 timeout_s: float, qt_app=None) -> float | None:
    """
    Gira delta_deg graus usando o BNO08x como sensor de ângulo.

    - delta_deg positivo = direita (sentido horário)
    - delta_deg negativo = esquerda (sentido anti-horário)
    - Para quando o BNO reportar que o ângulo girado atingiu
      (|delta_deg| - threshold_deg), deixando a inércia completar o resto.
    - Retorna o ângulo efetivamente girado, ou None se BNO indisponível.
    """
    if get_bno_yaw is None:
        print(f"  D-pad: BNO não disponível — giro de {delta_deg:+.1f}° cancelado.")
        return None

    yaw_start = get_bno_yaw()
    if yaw_start is None:
        print("  D-pad: sem leitura BNO — giro cancelado.")
        return None

    lado  = "DIR →" if delta_deg > 0 else "← ESQ"
    print(f"  D-pad {lado}  {abs(delta_deg):.1f}°  (BNO ref={yaw_start:.1f}°)")

    # Inicia giro
    if delta_deg > 0:
        motors.set_precise_rotation_direction(1, -1)
        motors.set_target_speed(turn_tps, -turn_tps)
    else:
        motors.set_precise_rotation_direction(-1, 1)
        motors.set_target_speed(-turn_tps, turn_tps)

    target_abs  = abs(delta_deg)
    stop_at     = target_abs - threshold_deg   # para um pouco antes (inércia completa)
    t0          = time.time()

    while time.time() - t0 < timeout_s:
        if qt_app:
            qt_app.processEvents()

        yaw_now = get_bno_yaw()
        if yaw_now is not None:
            delta_done = normalize_angle_deg(yaw_now - yaw_start)
            if delta_deg > 0 and delta_done >= stop_at:
                break
            if delta_deg < 0 and delta_done <= -stop_at:
                break

        time.sleep(0.015)

    motors.stop_motors()
    motors.clear_precise_rotation_direction()
    time.sleep(0.12)   # aguarda inércia mecânica parar

    yaw_final  = get_bno_yaw()
    actual_deg = normalize_angle_deg(yaw_final - yaw_start) if yaw_final is not None else None

    if actual_deg is not None:
        erro = actual_deg - delta_deg
        print(f"  D-pad concluído: girou {actual_deg:+.1f}°  "
              f"(alvo {delta_deg:+.1f}°, erro {erro:+.1f}°)")
    else:
        print("  D-pad concluído (sem leitura final do BNO).")

    return actual_deg


# ─────────────────────────────────────────────────────────────────────────────
# Loop principal de controle
# ─────────────────────────────────────────────────────────────────────────────
def run_control_loop(joystick, motors, get_bno_yaw, use_bno: bool,
                     tps_base: float, kp: float, max_corr: float,
                     invert_bno: bool, qt_app) -> None:
    import pygame

    yaw_ref:   float | None = None   # Referência BNO para linha reta
    speed_tps: float        = tps_base
    running:   bool         = True

    # Labels para log no terminal
    MODE_LABELS = {
        "forward":    "FRENTE",
        "back":       "RÉ    ",
        "turn_left":  "ESQ   ",
        "turn_right": "DIR   ",
        "stop":       "PARAR ",
    }

    prev_mode = "stop"
    prev_hat  = (0, 0)   # estado anterior do D-pad (edge detection)
    loop_dt   = 1.0 / LOOP_HZ

    print()
    print("=" * 60)
    print(f"  CONTROLE ATIVO — velocidade base: {speed_tps:.0f} TPS")
    print(f"  BNO correção: {'SIM' if use_bno and get_bno_yaw else 'NÃO'}")
    print(f"  D-pad ←/→: giro preciso {DPAD_TURN_DEG:.1f}° por clique (BNO)")
    print(f"  L1/R1=velocidade  B=parar  Start=sair")
    print("=" * 60)

    while running:
        t0 = time.time()

        if qt_app:
            qt_app.processEvents()

        pygame.event.pump()

        # ── Lê eixos analógicos ───────────────────────────────────────────
        raw_x = joystick.get_axis(AXIS_LEFT_X)
        raw_y = joystick.get_axis(AXIS_LEFT_Y)

        axis_x = apply_deadzone(raw_x, DEADZONE)
        axis_y = apply_deadzone(raw_y, DEADZONE)

        # ── Lê botões ─────────────────────────────────────────────────────
        btn_b     = joystick.get_button(BTN_B)
        btn_l1    = joystick.get_button(BTN_L1)
        btn_r1    = joystick.get_button(BTN_R1)
        btn_start = joystick.get_button(BTN_START)

        # ── D-pad: giro preciso 22.5° por clique (edge detection) ─────────
        try:
            hat = joystick.get_hat(HAT_ID)
        except Exception:
            hat = (0, 0)

        if hat != prev_hat:
            dpad_x = hat[0]
            if dpad_x == -1 and prev_hat[0] != -1:      # clique ← esquerda
                motors.stop_motors()
                yaw_ref = None
                cmd_turn_bno(
                    motors, -DPAD_TURN_DEG,
                    get_bno_yaw if use_bno else None,
                    DPAD_TURN_TPS, DPAD_TURN_THRESHOLD_DEG,
                    DPAD_TURN_TIMEOUT_S, qt_app,
                )
            elif dpad_x == 1 and prev_hat[0] != 1:      # clique → direita
                motors.stop_motors()
                yaw_ref = None
                cmd_turn_bno(
                    motors, +DPAD_TURN_DEG,
                    get_bno_yaw if use_bno else None,
                    DPAD_TURN_TPS, DPAD_TURN_THRESHOLD_DEG,
                    DPAD_TURN_TIMEOUT_S, qt_app,
                )
            prev_hat = hat

        # ── Ajuste de velocidade (L1/R1) ──────────────────────────────────
        if btn_l1:
            speed_tps = max(TPS_MIN, speed_tps - TPS_STEP)
            print(f"  Velocidade base: {speed_tps:.0f} TPS (–)")
            time.sleep(0.3)   # debounce
        if btn_r1:
            speed_tps = min(TPS_MAX, speed_tps + TPS_STEP)
            print(f"  Velocidade base: {speed_tps:.0f} TPS (+)")
            time.sleep(0.3)

        # ── Sair ──────────────────────────────────────────────────────────
        if btn_start:
            print("  Start pressionado → saindo.")
            running = False
            break

        # ── Parar emergência ──────────────────────────────────────────────
        if btn_b:
            motors.stop_motors()
            yaw_ref = None
            if prev_mode != "stop":
                print("  [B] PARADO")
                prev_mode = "stop"
            time.sleep(loop_dt)
            continue

        # ── Determina modo pelo analógico ─────────────────────────────────
        moving_y    = abs(axis_y) > 0.0
        turning     = abs(axis_x) > STRAIGHT_THRESHOLD_X
        going_fwd   = axis_y < 0.0   # –1 = cima = frente
        going_back  = axis_y > 0.0

        if not moving_y and not turning:
            # ── Parado ────────────────────────────────────────────────────
            motors.stop_motors()
            yaw_ref = None
            mode = "stop"

        elif turning and not moving_y:
            # ── Giro no lugar ─────────────────────────────────────────────
            yaw_ref = None
            tps = speed_tps * abs(axis_x)
            if axis_x > 0:
                motors.set_precise_rotation_direction(1, -1)
                motors.set_target_speed(tps, -tps)
                mode = "turn_right"
            else:
                motors.set_precise_rotation_direction(-1, 1)
                motors.set_target_speed(-tps, tps)
                mode = "turn_left"

        else:
            # ── Movimento com possível curva ──────────────────────────────
            # base_tps proporcional ao eixo Y (negativo = frente)
            base_tps = -axis_y * speed_tps   # positivo = frente, negativo = ré

            if turning:
                # Curva com deslocamento: modo diferencial, sem BNO
                yaw_ref = None
                motors.clear_precise_rotation_direction()
                diff = axis_x * speed_tps * 0.6   # suaviza a curva
                left_tps  = base_tps + diff
                right_tps = base_tps - diff
                motors.set_target_speed(left_tps, right_tps)
            else:
                # Linha reta: BNO corrige desvio angular
                if use_bno and get_bno_yaw:
                    yaw_now = get_bno_yaw()
                    if yaw_now is not None:
                        if yaw_ref is None:
                            # Nova referência ao entrar em modo reto
                            yaw_ref = yaw_now
                            if get_bno_yaw:
                                print(f"  BNO ref={yaw_ref:.1f}° ({MODE_LABELS.get('forward' if base_tps > 0 else 'back', '')})")

                        err = normalize_angle_deg(yaw_now - yaw_ref)
                        if invert_bno:
                            err = -err
                        corr = max(-max_corr, min(max_corr, kp * err))
                        left_tps  = base_tps - corr
                        right_tps = base_tps + corr
                    else:
                        # BNO sem leitura: modo sem correção
                        left_tps = right_tps = base_tps
                else:
                    # BNO desativado ou indisponível
                    left_tps = right_tps = base_tps

                motors.clear_precise_rotation_direction()
                motors.set_target_speed(left_tps, right_tps)

            mode = "forward" if base_tps > 0 else "back"

        # ── Log de mudança de modo ─────────────────────────────────────────
        if mode != prev_mode:
            label = MODE_LABELS.get(mode, mode)
            extra = f"  [TPS base={speed_tps:.0f}]" if mode not in ("stop",) else ""
            print(f"  [{label}]{extra}")
            prev_mode = mode

        # ── Mantém frequência do loop ──────────────────────────────────────
        elapsed = time.time() - t0
        sleep_t = max(0.0, loop_dt - elapsed)
        time.sleep(sleep_t)


# ─────────────────────────────────────────────────────────────────────────────
# Inicialização de periféricos
# ─────────────────────────────────────────────────────────────────────────────
def init_pygame_joystick():
    """Inicializa pygame e retorna o primeiro joystick encontrado."""
    import pygame
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.joystick.init()

    count = pygame.joystick.get_count()
    if count == 0:
        print("ERRO: Nenhum joystick detectado.")
        print("  Conecte o iPega PG-9076 via Bluetooth ou USB e tente novamente.")
        sys.exit(1)

    joy = pygame.joystick.Joystick(0)
    joy.init()
    print(f"  Joystick detectado: {joy.get_name()}")
    print(f"  Eixos: {joy.get_numaxes()}  |  Botões: {joy.get_numbuttons()}  |  Hats: {joy.get_numhats()}")
    return joy


def init_bno():
    """Inicializa BNO08x. Retorna (bno, get_yaw_fn) ou (None, None)."""
    try:
        from tools.bno08x_init import init_bno as _init
        bno, get_yaw = _init(do_reset_cycle=False, verbose=False)
        if bno is not None:
            print("  BNO08x: OK")
        else:
            print("  BNO08x: não disponível — frente sem correção de deriva")
        return bno, get_yaw
    except Exception as e:
        print(f"  BNO08x: falha ao inicializar ({e})")
        return None, None


def init_motors():
    """Inicializa motor controller com PyQt5."""
    from PyQt5.QtCore import QCoreApplication
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication(sys.argv)
    from src.core.robot_motor_controller import RobotMotorController
    motors = RobotMotorController()
    return motors, app


# ─────────────────────────────────────────────────────────────────────────────
# Ponto de entrada
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    # ── Parâmetros de linha de comando ────────────────────────────────────────
    try:
        from src.core.config import (
            BNO_STRAIGHT_KP,
            BNO_STRAIGHT_MAX_CORRECTION_TPS,
            BNO_STRAIGHT_INVERT_CORRECTION,
        )
    except ImportError:
        BNO_STRAIGHT_KP                = 0.35
        BNO_STRAIGHT_MAX_CORRECTION_TPS = 8.0
        BNO_STRAIGHT_INVERT_CORRECTION  = True

    parser = argparse.ArgumentParser(
        description="Controle manual do robô via joystick iPega PG-9076 com correção BNO"
    )
    parser.add_argument(
        "--identify", action="store_true",
        help="Modo identificação: imprime eixos e botões em tempo real (para calibrar)"
    )
    parser.add_argument(
        "--no-bno", action="store_true",
        help="Desativa correção BNO (frente sem compensação de desvio)"
    )
    parser.add_argument(
        "--tps", type=float, default=TPS_DEFAULT,
        help=f"Velocidade base inicial em TPS (padrão: {TPS_DEFAULT})"
    )
    parser.add_argument(
        "--kp", type=float, default=BNO_STRAIGHT_KP,
        help=f"Ganho proporcional BNO (padrão config: {BNO_STRAIGHT_KP})"
    )
    parser.add_argument(
        "--max-corr", type=float, default=BNO_STRAIGHT_MAX_CORRECTION_TPS,
        help=f"Correção máxima BNO em TPS (padrão config: {BNO_STRAIGHT_MAX_CORRECTION_TPS})"
    )
    parser.add_argument(
        "--invert-bno", action="store_true", default=BNO_STRAIGHT_INVERT_CORRECTION,
        help="Inverte a correção BNO (use se o robô corrigir para o lado errado)"
    )
    args = parser.parse_args()

    if not is_raspberry_pi():
        print("AVISO: Este script foi projetado para rodar na Raspberry Pi.")
        print("       Modo --identify pode funcionar em desenvolvimento.")
        if not args.identify:
            sys.exit(1)

    os.environ.setdefault("ROBOT_MOTOR_QUIET", "1")

    print()
    print("=" * 60)
    print("  Robô SLAM 2026 — Controle Manual Joystick iPega PG-9076")
    print("=" * 60)

    # ── Joystick ──────────────────────────────────────────────────────────────
    joystick = init_pygame_joystick()

    if args.identify:
        run_identify_mode(joystick)
        return

    # ── BNO ───────────────────────────────────────────────────────────────────
    use_bno = not args.no_bno
    if use_bno:
        _, get_bno_yaw = init_bno()
    else:
        get_bno_yaw = None
        print("  BNO: desativado por --no-bno")

    # ── Motores ───────────────────────────────────────────────────────────────
    print("  Inicializando motores...", end=" ", flush=True)
    motors, qt_app = init_motors()
    print("OK")

    # ── Loop de controle ──────────────────────────────────────────────────────
    try:
        run_control_loop(
            joystick    = joystick,
            motors      = motors,
            get_bno_yaw = get_bno_yaw,
            use_bno     = use_bno,
            tps_base    = args.tps,
            kp          = args.kp,
            max_corr    = args.max_corr,
            invert_bno  = args.invert_bno,
            qt_app      = qt_app,
        )
    except KeyboardInterrupt:
        print("\n  Ctrl+C — encerrando.")
    finally:
        motors.stop_motors()
        print("  Motores parados. Até logo!")
        import pygame
        pygame.quit()


if __name__ == "__main__":
    main()
