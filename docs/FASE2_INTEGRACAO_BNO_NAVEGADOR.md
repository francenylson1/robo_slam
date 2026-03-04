# Fase 2 – Integração BNO no navegador

Resumo do que foi implementado no branch `robo_slam_2026_1_bno_com_odometria`.

---

## O que foi feito

1. **Init BNO no RobotNavigator**
   - No `__init__` do navegador, apenas em Raspberry (`is_raspberry_pi()`): chama `tools.bno08x_init.init_bno(do_reset_cycle=False, verbose=False)`.
   - Armazena `self._get_bno_yaw` e `self._bno_yaw_ref = None`. Em desktop ou se o init falhar, `_get_bno_yaw` fica `None` e toda a lógica BNO é ignorada.

2. **Correção de rumo em linha reta**
   - **`_ensure_bno_yaw_ref()`:** espera até a primeira leitura válida de yaw (timeout `BNO_FIRST_READ_TIMEOUT` do config) e define `_bno_yaw_ref`. Não usa 0° por padrão.
   - **`_apply_bno_straight_correction(left_tps, right_tps)`:** usa `BNO_STRAIGHT_KP`, `BNO_STRAIGHT_MAX_CORRECTION_TPS`, `BNO_STRAIGHT_INVERT_CORRECTION` do config; retorna (left_tps, right_tps) corrigidos ou inalterados se BNO indisponível. Se `get_bno_yaw()` retorna `None`, retorna (left_tps, right_tps) sem alterar.
   - **`_move_towards_target()`:** quando `linear_speed_ms > 0`, aplica `_apply_bno_straight_correction` antes de `set_target_speed`. Quando `abs(angle_error) > 45°`, zera `_bno_yaw_ref` para o próximo trecho em linha reta ter referência nova.
   - **`_stable_final_approach()`:** quando `linear_speed_ms > 0`, aplica a mesma correção antes de `set_target_speed`.

3. **Ângulo da pose (odometria + BNO)**
   - **`_update_pose_with_odometry()`:** quando BNO está disponível e não está em giro preciso, usa o ângulo do BNO (`get_bno_yaw()`) como `current_angle` em vez do ângulo integrado só pela odometria. A posição continua sendo atualizada com `delta_distance` e o ângulo atual (agora do BNO quando há leitura válida). Assim, sob patinação, o rumo no mapa permanece correto.

---

## Checklist de integração (atendido)

- Init BNO via `tools.bno08x_init.init_bno(do_reset_cycle=False)`.
- Primeira leitura antes de corrigir: `_ensure_bno_yaw_ref()` com timeout do config.
- Quando não há leitura no laço: `_apply_bno_straight_correction` retorna (left_tps, right_tps) sem alterar.
- `yaw_ref` sempre da leitura real do BNO no momento “rumo a manter”; referência limpa ao girar muito (>45°).
- Ganhos e invert do `config.py`.
- Patch 0x7B e debug=False já no init; não se cria BNO em outro módulo.

---

## Como testar

1. Na Raspberry, fazer pull do branch `robo_slam_2026_1_bno_com_odometria`.
2. Abrir o main (interface com mapa) e iniciar uma navegação até um POI.
3. Verificar no console se aparece: "DEBUG: BNO08x integrado ao navegador".
4. Observar se a trajetória em linha reta fica mais estável e se, após patinação, o rumo no mapa continua coerente (ângulo do BNO na pose).

---

## Reverter

Se precisar voltar ao comportamento só odometria, usar o branch `robo_slam_2026_1_bno_ok` (sem integração no navegador) ou remover/desativar a lógica BNO no `robot_navigator.py`.
