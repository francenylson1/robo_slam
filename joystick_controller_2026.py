#!/usr/bin/env python3
"""
joystick_controller_2026.py — Controle manual do robô via joystick iPega PG-9076

Modo de uso:
  python joystick_controller_2026.py             # controle normal com BNO
  python joystick_controller_2026.py --identify  # identifica eixos/botões (calibração)
  python joystick_map_tool.py                   # mapeamento completo (recomendado)
  python joystick_controller_2026.py --preset shanwan   # perfil shanwan Android GamePad
  python joystick_controller_2026.py --no-bno    # frente sem correção BNO
  python joystick_controller_2026.py --tps 25 --step-deg 15
  python joystick_controller_2026.py --use-motor-trim   # aplica fatores L/R do autónomo (padrão: só BNO)

Mapeamento (iPega PG-9076 no modo PC):
  Analógico esquerdo Y   →  Frente / ré (reta; BNO corrige; X ignorado)
  Analógico esquerdo X   →  Giro no lugar (só com Y no centro)
  D-pad                  →  Giro de N graus/clique (--step-deg)
  Botão de giro 180°     →  por defeito o mesmo índice que "Y" no perfil; em muitos
                            gamepads Android o índice 3 é o X físico — use buttons.turn_180 no JSON
  Botão B                →  Parar | L1/R1 TPS | Start sair
  Analógico direito      →  Reservado

Resumo: frente/ré = só eixo Y (BNO). Eixo X não curva durante frente/ré.
Giro no lugar = X com Y neutro. D-pad = passos em graus; Y = 180°.

Execute na Raspberry Pi com o joystick conectado via Bluetooth ou USB.
"""

import sys
import os
import time
import math
import json
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
DEADZONE               = 0.14   # Zona morta dos eixos
# Após deadzone: |Y| <= NEUTRAL → pode usar X para girar no lugar
Y_NEUTRAL_MAX          = 0.14
# |Y| >= MOVE_MIN → frente/ré. Faixa entre NEUTRAL e MOVE = parado (histerese anti-drift)
# NOTA: 0.18–0.32 era largo demais — stick “médio” ficava sempre parado após armar.
Y_MOVE_MIN             = 0.22
SELECT_TOGGLE_DEBOUNCE_S = 0.35  # evita duplo toggle (armar+desarmar num clique)
# |X| acima (com Y neutro): giro no lugar proporcional
SPIN_MIN_ABS_X         = 0.12
TPS_DEFAULT            = 25.0
TPS_MIN                = 10.0
TPS_MAX                = 45.0
TPS_STEP               = 5.0
LOOP_HZ                = 50
L1_R1_DEBOUNCE_S       = 0.28
BTN_Y_DEBOUNCE_S       = 0.55

# D-pad: graus por clique (padrao 22.5); --step-deg no argparse
HAT_ID                   = 0
DPAD_TURN_DEG_DEFAULT    = 22.5
DPAD_TURN_TPS            = 12.0
DPAD_TURN_THRESHOLD_DEG  = 1.5
DPAD_TURN_TIMEOUT_S      = 5.0
# Ignora critério de parada pelo BNO nos primeiros instantes (evita falso 0° se o yaw atrasar)
DPAD_TURN_MIN_ACTIVE_S   = 0.22
TURN_180_TIMEOUT_S       = 14.0
# Giro sem BNO (--no-bno): duração ≈ |Δ°| / OPEN_LOOP_TURN_DPS (ajuste com --turn-open-loop-dps)
OPEN_LOOP_TURN_DPS_DEFAULT = 58.0


def default_button_map() -> dict[str, int]:
    """Índices pygame para iPega PG-9076 (modo PC)."""
    return {
        "a": BTN_A,
        "b": BTN_B,
        "y": BTN_Y,
        "turn_180": BTN_Y,  # pode sobrescrever no perfil (ex.: índice do X físico)
        "select": BTN_SELECT,
        "start": BTN_START,
        "l1": BTN_L1,
        "r1": BTN_R1,
    }


def load_joystick_profile_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


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

        elapsed = time.time() - t0
        yaw_now = get_bno_yaw()
        if yaw_now is not None and elapsed >= DPAD_TURN_MIN_ACTIVE_S:
            # get_yaw (quaternion) segue convenção habitual: yaw aumenta em CCW.
            # delta_deg > 0 = giro à direita (CW) → yaw diminui → delta_done negativo.
            # delta_deg < 0 = giro à esquerda (CCW) → yaw aumenta → delta_done positivo.
            delta_done = normalize_angle_deg(yaw_now - yaw_start)
            if delta_deg > 0.0:
                if delta_done <= -stop_at:
                    break
            else:
                if delta_done >= stop_at:
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
        if abs(actual_deg) < 1.0 and abs(delta_deg) > 3.0:
            print(
                "  AVISO: BNO não registrou giro — patinagem, fusão IMU, obstáculo ou motores; "
                "tente --use-motor-trim se o autónomo estiver calibrado para este piso."
            )
    else:
        print("  D-pad concluído (sem leitura final do BNO).")

    return actual_deg


def cmd_turn_open_loop(
    motors,
    delta_deg: float,
    turn_tps: float,
    deg_per_sec: float,
    timeout_s: float,
    qt_app=None,
) -> None:
    """
    Giro por tempo quando não há BNO. Calibre --turn-open-loop-dps na pista
    (graus/s reais do giro no lugar com DPAD_TURN_TPS).
    """
    if deg_per_sec <= 0:
        print("  Giro: --turn-open-loop-dps deve ser > 0.")
        return
    dur = min(abs(delta_deg) / deg_per_sec, timeout_s)
    lado = "DIR →" if delta_deg > 0 else "← ESQ"
    print(f"  Giro {lado} {abs(delta_deg):.1f}° (malha aberta ~{dur:.1f}s, sem BNO)")

    if delta_deg > 0:
        motors.set_precise_rotation_direction(1, -1)
        motors.set_target_speed(turn_tps, -turn_tps)
    else:
        motors.set_precise_rotation_direction(-1, 1)
        motors.set_target_speed(-turn_tps, turn_tps)

    t_spin = time.time()
    while time.time() - t_spin < dur:
        if qt_app:
            qt_app.processEvents()
        time.sleep(0.02)

    motors.stop_motors()
    motors.clear_precise_rotation_direction()
    time.sleep(0.12)
    print("  Giro concluído (malha aberta; ajuste --turn-open-loop-dps se passar/faltar ângulo).")


def cmd_turn(
    motors,
    delta_deg: float,
    get_bno_yaw,
    open_loop_dps: float,
    turn_tps: float,
    threshold_deg: float,
    timeout_s: float,
    qt_app=None,
) -> float | None:
    """D-pad / 180°: BNO se disponível; senão malha aberta."""
    if get_bno_yaw is not None:
        return cmd_turn_bno(
            motors, delta_deg, get_bno_yaw,
            turn_tps, threshold_deg, timeout_s, qt_app,
        )
    cmd_turn_open_loop(motors, delta_deg, turn_tps, open_loop_dps, timeout_s, qt_app)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Loop principal de controle
# ─────────────────────────────────────────────────────────────────────────────
def run_control_loop(joystick, motors, get_bno_yaw, use_bno: bool,
                     tps_base: float, kp: float, max_corr: float,
                     invert_bno: bool, qt_app,
                     dpad_step_deg: float, arm_start: bool,
                     y_neutral_max: float, y_move_min: float,
                     debug_axes: bool,
                     stick_x_idx: int, stick_y_idx: int,
                     invert_stick_y: bool,
                     arm_with_a: bool,
                     btn_map: dict[str, int],
                     hat_id: int,
                     open_loop_dps: float) -> None:
    import pygame

    yaw_ref:   float | None = None   # Referência BNO para linha reta
    speed_tps: float        = tps_base
    running:   bool         = True

    MODE_LABELS = {
        "forward":    "FRENTE (reta BNO)",
        "back":       "RÉ    (reta BNO)",
        "turn_left":  "GIRO ESQ (no lugar)",
        "turn_right": "GIRO DIR (no lugar)",
        "stop":       "PARAR ",
    }

    prev_mode = "stop"
    prev_hat  = (0, 0)
    prev_l1     = False
    prev_r1     = False
    prev_turn_180 = False
    prev_select = False
    prev_a      = False
    last_select_toggle_t = 0.0
    last_l1r1_t = 0.0
    last_y_t    = 0.0
    last_debug_axes_t = 0.0
    loop_dt     = 1.0 / LOOP_HZ
    motors_armed = bool(arm_start)

    motors.stop_motors()

    print()
    print("=" * 60)
    print(f"  CONTROLE ATIVO — velocidade base: {speed_tps:.0f} TPS")
    print(f"  BNO na reta (só eixo Y): {'SIM' if use_bno and get_bno_yaw else 'NÃO'}")
    if os.environ.get("ROBO_TELEOP_NO_MOTOR_TRIM", "").lower() in ("1", "true", "yes", "on"):
        print("  Trim de motores (autónomo): DESLIGADO — fatores 1.0; use --use-motor-trim se precisar da calibração mecânica")
    else:
        print("  Trim de motores (autónomo): LIGADO (--use-motor-trim)")
    if os.environ.get("ROBO_TELEOP_DISABLE_LIDAR", "").lower() in ("1", "true", "yes", "on"):
        print("  Lidar C1: DESLIGADO (--no-lidar) — sem parada automática por obstáculo")
    turn_180_idx = btn_map.get("turn_180", btn_map["y"])
    print(f"  D-pad: {dpad_step_deg:.1f}°/clique | Giro 180°: botão pygame índice {turn_180_idx} (perfil: turn_180 ou y)")
    print(f"  Stick: Y=frente/ré (|Y|>={y_move_min:.2f}) | X=gira só com |Y|<={y_neutral_max:.2f}")
    print(f"  Eixos stick: pygame índices X={stick_x_idx} Y={stick_y_idx}"
          f"{' (Y invertido)' if invert_stick_y else ''}")
    arm_help = "SELECT ou botão A" if arm_with_a else "SELECT"
    print(f"  {arm_help} = armar/desarmar | L1/R1=TPS  B=parar  Start=sair")
    if motors_armed:
        print("  Estado: MOTORES ARMADOS (--arm-start)")
    else:
        print("  Estado: MOTORES DESARMADOS — pressione SELECT para armar (segurança)")
    print("=" * 60)

    while running:
        t0 = time.time()

        if qt_app:
            qt_app.processEvents()

        pygame.event.pump()

        # ── Eixos do analógico (índices dependem do driver — iPega 0,1; muitos Android 2,3 ou 3,4)
        raw_x = joystick.get_axis(stick_x_idx)
        raw_y = joystick.get_axis(stick_y_idx)
        if invert_stick_y:
            raw_y = -raw_y

        axis_x = apply_deadzone(raw_x, DEADZONE)
        axis_y = apply_deadzone(raw_y, DEADZONE)

        # ── Lê botões (índices do perfil / iPega) ─────────────────────────
        bmap = btn_map
        btn_b      = joystick.get_button(bmap["b"])
        btn_a      = joystick.get_button(bmap["a"])
        btn_l1     = joystick.get_button(bmap["l1"])
        btn_r1     = joystick.get_button(bmap["r1"])
        btn_turn_180 = joystick.get_button(bmap.get("turn_180", bmap["y"]))
        btn_select = joystick.get_button(bmap["select"])
        btn_start  = joystick.get_button(bmap["start"])
        now_mono  = time.monotonic()

        def _toggle_arm(source: str) -> None:
            nonlocal motors_armed, last_select_toggle_t, yaw_ref
            if (now_mono - last_select_toggle_t) < SELECT_TOGGLE_DEBOUNCE_S:
                return
            motors_armed = not motors_armed
            last_select_toggle_t = now_mono
            print(f"  [{source}] Motores {'ARMADOS' if motors_armed else 'DESARMADOS'}")
            if not motors_armed:
                motors.stop_motors()
                yaw_ref = None

        if btn_select and not prev_select:
            _toggle_arm("SELECT")
        prev_select = btn_select
        if arm_with_a and (btn_a and not prev_a):
            _toggle_arm("A")
        prev_a = btn_a

        if debug_axes and (now_mono - last_debug_axes_t) >= 1.0:
            last_debug_axes_t = now_mono
            nax = joystick.get_numaxes()
            parts = [f"a{i}={joystick.get_axis(i):+.2f}" for i in range(nax)]
            print("  [debug] " + " ".join(parts))
            print(
                f"  [debug] stick usa índices ({stick_x_idx},{stick_y_idx}) "
                f"raw=({raw_x:+.2f},{raw_y:+.2f}) dz=({axis_x:+.2f},{axis_y:+.2f}) "
                f"|y|={abs(axis_y):.2f} "
                f"zona={'mov' if abs(axis_y) >= y_move_min else ('neut' if abs(axis_y) <= y_neutral_max else 'morta')} "
                f"armed={motors_armed}"
            )

        # ── Sair (sempre) ─────────────────────────────────────────────────
        if btn_start:
            print("  Start pressionado → saindo.")
            running = False
            break

        # ── Parar emergência (sempre) ─────────────────────────────────────
        if btn_b:
            motors.stop_motors()
            yaw_ref = None
            if prev_mode != "stop":
                print("  [B] PARADO")
                prev_mode = "stop"
            time.sleep(loop_dt)
            continue

        # ── L1/R1: TPS mesmo desarmado (ajuste antes de armar) ────────────
        if (btn_l1 and not prev_l1 and (now_mono - last_l1r1_t) >= L1_R1_DEBOUNCE_S):
            speed_tps = max(TPS_MIN, speed_tps - TPS_STEP)
            last_l1r1_t = now_mono
            print(f"  Velocidade base: {speed_tps:.0f} TPS (L1 -)")
        if (btn_r1 and not prev_r1 and (now_mono - last_l1r1_t) >= L1_R1_DEBOUNCE_S):
            speed_tps = min(TPS_MAX, speed_tps + TPS_STEP)
            last_l1r1_t = now_mono
            print(f"  Velocidade base: {speed_tps:.0f} TPS (R1 +)")
        prev_l1 = btn_l1
        prev_r1 = btn_r1

        # Sem armar: não aceita D-pad, Y nem analógico (só drift/ruído)
        if not motors_armed:
            motors.stop_motors()
            yaw_ref = None
            if prev_mode != "stop":
                prev_mode = "stop"
            elapsed = time.time() - t0
            time.sleep(max(0.0, loop_dt - elapsed))
            continue

        # ── D-pad: giro fixo por clique (BNO) ─────────────────────────────
        try:
            hat = joystick.get_hat(hat_id)
        except Exception:
            hat = (0, 0)

        if hat != prev_hat:
            dpad_x = hat[0]
            if dpad_x == -1 and prev_hat[0] != -1:
                motors.stop_motors()
                yaw_ref = None
                cmd_turn(
                    motors, -dpad_step_deg,
                    get_bno_yaw if use_bno else None,
                    open_loop_dps,
                    DPAD_TURN_TPS, DPAD_TURN_THRESHOLD_DEG,
                    DPAD_TURN_TIMEOUT_S, qt_app,
                )
            elif dpad_x == 1 and prev_hat[0] != 1:
                motors.stop_motors()
                yaw_ref = None
                cmd_turn(
                    motors, +dpad_step_deg,
                    get_bno_yaw if use_bno else None,
                    open_loop_dps,
                    DPAD_TURN_TPS, DPAD_TURN_THRESHOLD_DEG,
                    DPAD_TURN_TIMEOUT_S, qt_app,
                )
            prev_hat = hat

        # ── Botão turn_180 (perfil; por defeito = Y): 180° (borda de subida + debounce) ──
        if btn_turn_180 and not prev_turn_180 and (now_mono - last_y_t) >= BTN_Y_DEBOUNCE_S:
            motors.stop_motors()
            yaw_ref = None
            last_y_t = now_mono
            print("  [Giro 180°] botão índice {}".format(bmap.get("turn_180", bmap["y"])))
            cmd_turn(
                motors, 180.0,
                get_bno_yaw if use_bno else None,
                open_loop_dps,
                DPAD_TURN_TPS, DPAD_TURN_THRESHOLD_DEG,
                TURN_180_TIMEOUT_S, qt_app,
            )
        prev_turn_180 = btn_turn_180

        # ── Analógico: histerese em Y (evita “frente” só com drift do stick)
        abs_y = abs(axis_y)
        abs_x = abs(axis_x)
        if abs_y <= y_neutral_max:
            y_zone = "neutral"
        elif abs_y >= y_move_min:
            y_zone = "move"
        else:
            y_zone = "dead"
        y_command = y_zone == "move"
        y_neutral = y_zone == "neutral"
        x_spin    = y_neutral and (abs_x >= SPIN_MIN_ABS_X)

        if y_command:
            # Frente ou ré: sempre reta; eixo X não altera L/R (só BNO)
            base_tps = -axis_y * speed_tps
            if use_bno and get_bno_yaw:
                yaw_now = get_bno_yaw()
                if yaw_now is not None:
                    if yaw_ref is None:
                        yaw_ref = yaw_now
                        tag = "FRENTE" if base_tps > 0 else "RÉ"
                        print(f"  BNO ref={yaw_ref:.1f}° ({tag}, X ignorado)")

                    err = normalize_angle_deg(yaw_now - yaw_ref)
                    if invert_bno:
                        err = -err
                    corr = max(-max_corr, min(max_corr, kp * err))
                    left_tps  = base_tps - corr
                    right_tps = base_tps + corr
                else:
                    left_tps = right_tps = base_tps
            else:
                left_tps = right_tps = base_tps

            motors.clear_precise_rotation_direction()
            motors.set_target_speed(left_tps, right_tps)
            mode = "forward" if base_tps > 0 else "back"

        elif x_spin:
            # Giro no lugar proporcional ao X (BNO não corrige reta aqui)
            yaw_ref = None
            tps = speed_tps * min(1.0, abs_x)
            if axis_x > 0:
                motors.set_precise_rotation_direction(1, -1)
                motors.set_target_speed(tps, -tps)
                mode = "turn_right"
            else:
                motors.set_precise_rotation_direction(-1, 1)
                motors.set_target_speed(-tps, tps)
                mode = "turn_left"

        else:
            motors.stop_motors()
            yaw_ref = None
            mode = "stop"

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

    if count > 1:
        print(f"  AVISO: {count} joysticks encontrados — usando o índice 0.")
        print("  Se o robô se mover sozinho, pode ser o dispositivo errado.")
        print("  Feche outros controles virtuais ou defina: export SDL_JOYSTICK_DEVICE=...")

    joy = pygame.joystick.Joystick(0)
    joy.init()
    name = joy.get_name()
    print(f"  Joystick detectado: {name}")
    print(f"  Eixos: {joy.get_numaxes()}  |  Botões: {joy.get_numbuttons()}  |  Hats: {joy.get_numhats()}")
    low = name.lower()
    if "shanwan" in low or "android" in low:
        print("  Dica (shanwan): python joystick_controller_2026.py --preset shanwan")
    return joy


def init_bno():
    """Inicializa BNO08x. Retorna (bno, get_yaw_fn) ou (None, None)."""
    try:
        from tools.bno08x_init import init_bno as _init
        # 1) RST só em HIGH (menos 0x7B instável); 2) se falhar, ciclo RST completo
        bno, get_yaw = _init(do_reset_cycle=False, verbose=False)
        if bno is None:
            print("  BNO08x: primeira tentativa falhou — retry com ciclo RST...")
            bno, get_yaw = _init(do_reset_cycle=True, verbose=False)
        if bno is not None:
            print("  BNO08x: OK")
        else:
            print("  BNO08x: não disponível — frente sem correção de deriva")
            print("  Dica: verifique I2C (i2cdetect), cabo, 3V3 e tools/bno08x_test.py")
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
    inv = parser.add_mutually_exclusive_group()
    inv.add_argument(
        "--invert-bno", action="store_true",
        help="Força correção BNO invertida (sobrescreve config)",
    )
    inv.add_argument(
        "--no-invert-bno", action="store_true",
        help="Desliga inversão da correção BNO (sobrescreve config)",
    )
    parser.add_argument(
        "--step-deg", type=float, default=DPAD_TURN_DEG_DEFAULT,
        help=f"Graus por clique no D-pad (padrao {DPAD_TURN_DEG_DEFAULT})",
    )
    parser.add_argument(
        "--arm-start", action="store_true",
        help="Inicia com motores já armados (padrão: desarmado até SELECT)",
    )
    parser.add_argument(
        "--y-move-min", type=float, default=Y_MOVE_MIN,
        help=f"|Y| após deadzone para frente/ré (padrão {Y_MOVE_MIN})",
    )
    parser.add_argument(
        "--y-neutral-max", type=float, default=Y_NEUTRAL_MAX,
        help=f"|Y| máximo para considerar eixo Y neutro e usar X para girar (padrão {Y_NEUTRAL_MAX})",
    )
    parser.add_argument(
        "--debug-axes", action="store_true",
        help="Imprime a cada 1s todos os eixos pygame + stick usado (diagnóstico)",
    )
    parser.add_argument(
        "--preset",
        choices=["", "shanwan"],
        default="",
        help="Carrega perfil embutido (shanwan = joystick_profile_shanwan_android.json na raiz)",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default="",
        metavar="FICHEIRO.json",
        help="Perfil próprio: stick_x/y, hat_id, buttons {a,b,y,turn_180,select,start,l1,r1}",
    )
    parser.add_argument(
        "--stick-x", type=int, default=None,
        help="Eixo X do stick (sobrescreve perfil; padrão 0 iPega se sem --preset)",
    )
    parser.add_argument(
        "--stick-y", type=int, default=None,
        help="Eixo Y do stick (sobrescreve perfil; padrão 1 iPega se sem --preset)",
    )
    parser.add_argument(
        "--android-gamepad", action="store_true",
        help="Atalho: usa eixos 2 e 3 para o stick (comum em gamepads Android/shanwan)",
    )
    parser.add_argument(
        "--invert-stick-y", action="store_true",
        help="Inverte o eixo Y do stick (se frente/ré estiverem trocados)",
    )
    parser.add_argument(
        "--arm-with-a", action="store_true",
        help="Também armar/desarmar com o botão A (útil se SELECT tiver índice errado)",
    )
    parser.add_argument(
        "--use-motor-trim",
        action="store_true",
        help="Aplica LEFT/RIGHT_MOTOR_CORRECTION_FACTOR (autónomo). Padrão: fatores 1.0 no teleop para não somar com BNO.",
    )
    parser.add_argument(
        "--no-lidar",
        action="store_true",
        help="Não inicia o Lidar C1 (sem parada por obstáculo; útil se o C1/USB falhar ou para testes).",
    )
    parser.add_argument(
        "--turn-open-loop-dps",
        type=float,
        default=OPEN_LOOP_TURN_DPS_DEFAULT,
        metavar="DEG/S",
        help=(
            "Com --no-bno: graus/s estimados para D-pad e giro 180° em malha aberta "
            f"(padrão {OPEN_LOOP_TURN_DPS_DEFAULT}; suba se faltar ângulo, baixe se passar)"
        ),
    )
    args = parser.parse_args()
    if args.invert_bno:
        invert_bno = True
    elif args.no_invert_bno:
        invert_bno = False
    else:
        invert_bno = BNO_STRAIGHT_INVERT_CORRECTION

    if not is_raspberry_pi():
        print("AVISO: Este script foi projetado para rodar na Raspberry Pi.")
        print("       Modo --identify pode funcionar em desenvolvimento.")
        if not args.identify:
            sys.exit(1)

    if args.y_neutral_max >= args.y_move_min:
        print("ERRO: --y-neutral-max deve ser menor que --y-move-min (faixa de histerese).")
        sys.exit(2)

    profile_data = None
    if args.profile:
        profile_data = load_joystick_profile_json(args.profile)
    elif args.preset == "shanwan":
        profile_data = load_joystick_profile_json(
            os.path.join(ROOT, "joystick_profile_shanwan_android.json")
        )

    btn_map = default_button_map()
    hat_id = HAT_ID
    invert_stick_eff = args.invert_stick_y
    arm_with_a_eff = args.arm_with_a

    if profile_data:
        stick_x_idx = int(profile_data.get("stick_x", 0))
        stick_y_idx = int(profile_data.get("stick_y", 1))
        invert_stick_eff = bool(profile_data.get("invert_stick_y", invert_stick_eff))
        hat_id = int(profile_data.get("hat_id", HAT_ID))
        for k, v in profile_data.get("buttons", {}).items():
            if k in btn_map or k == "turn_180":
                btn_map[k] = int(v)
        if "turn_180" not in profile_data.get("buttons", {}):
            btn_map["turn_180"] = btn_map["y"]
        arm_with_a_eff = bool(args.arm_with_a or profile_data.get("arm_with_a_default"))
        desc = profile_data.get("description") or (args.preset or args.profile or "perfil")
        print(f"  Perfil carregado: {desc}")
        print(f"  Botões pygame: {btn_map}")
    elif args.android_gamepad:
        stick_x_idx, stick_y_idx = 2, 3
    else:
        stick_x_idx = args.stick_x if args.stick_x is not None else 0
        stick_y_idx = args.stick_y if args.stick_y is not None else 1

    if profile_data is not None and (args.stick_x is not None or args.stick_y is not None):
        if args.stick_x is not None:
            stick_x_idx = args.stick_x
        if args.stick_y is not None:
            stick_y_idx = args.stick_y

    os.environ.setdefault("ROBOT_MOTOR_QUIET", "1")
    os.environ["ROBO_TELEOP_JOYSTICK"] = "1"
    if args.no_lidar:
        os.environ["ROBO_TELEOP_DISABLE_LIDAR"] = "1"
    else:
        os.environ.pop("ROBO_TELEOP_DISABLE_LIDAR", None)
    if args.use_motor_trim:
        os.environ.pop("ROBO_TELEOP_NO_MOTOR_TRIM", None)
    else:
        os.environ["ROBO_TELEOP_NO_MOTOR_TRIM"] = "1"

    print()
    print("=" * 60)
    print("  Robô SLAM 2026 — Controle Manual Joystick iPega PG-9076")
    print("=" * 60)

    # ── Joystick ──────────────────────────────────────────────────────────────
    joystick = init_pygame_joystick()

    n_axes = joystick.get_numaxes()
    if not (0 <= stick_x_idx < n_axes and 0 <= stick_y_idx < n_axes):
        print(
            f"ERRO: eixos inválidos — stick-x={stick_x_idx} stick-y={stick_y_idx} "
            f"mas o joystick só tem {n_axes} eixos (0..{n_axes - 1})."
        )
        sys.exit(2)

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
            joystick       = joystick,
            motors         = motors,
            get_bno_yaw    = get_bno_yaw,
            use_bno        = use_bno,
            tps_base       = args.tps,
            kp             = args.kp,
            max_corr       = args.max_corr,
            invert_bno     = invert_bno,
            qt_app         = qt_app,
            dpad_step_deg  = args.step_deg,
            arm_start      = args.arm_start,
            y_neutral_max  = args.y_neutral_max,
            y_move_min     = args.y_move_min,
            debug_axes     = args.debug_axes,
            stick_x_idx    = stick_x_idx,
            stick_y_idx    = stick_y_idx,
            invert_stick_y = invert_stick_eff,
            arm_with_a     = arm_with_a_eff,
            btn_map        = btn_map,
            hat_id         = hat_id,
            open_loop_dps  = args.turn_open_loop_dps,
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
