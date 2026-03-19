# Plano Fase 2b — Deriva e Correção de Trajetória

**Data:** 19 de março de 2026  
**Objetivo:** Melhorar a precisão da navegação para que o robô mantenha o rumo e chegue ao POI com menor desvio. Pré-requisito para a Fase 2c (desvio de obstáculos).

---

## 1. O que já existe no código

### 1.1 Odometria (base)
- **Fonte:** Encoders (ticks) das rodas esquerda e direita
- **Cálculo:** `delta_distance = (dist_left + dist_right) / 2`, `delta_angle_rad = (dist_left - dist_right) / ROBOT_WHEEL_BASE_M`
- **Atualização:** `current_position` (x, y) e `current_angle` em `_update_pose_with_odometry()`

### 1.2 CTE (Cross-Track Error) — já implementado
- **O que faz:** Calcula o desvio perpendicular do robô em relação ao segmento de caminho (waypoint anterior → waypoint atual)
- **Onde:** `_calculate_cte()` e `_move_towards_target()` em `robot_navigator.py`
- **Lógica:** CTE positivo = robô à esquerda da linha → corrige ângulo para a direita
- **Parâmetros:** Ganho 1.2, limite ±20° na correção angular
- **Condição:** Só aplica quando há path com waypoints (`path_index > 0`); navegação direta não usa CTE

### 1.3 Correção assimétrica dos motores
- **Onde:** `robot_motor_controller.py`
- **Valores:** `LEFT_MOTOR_CORRECTION_FACTOR = 0.96`, `RIGHT_MOTOR_CORRECTION_FACTOR = 1.0`
- **Objetivo:** Compensar deriva sistemática à direita (motor esquerdo mais fraco)

### 1.4 BNO08x — implementado mas desativado
- **Status:** `USE_BNO_IN_NAVIGATION = False` em `config.py`
- **Motivo:** Causava desvio sistemático para a direita em testes anteriores
- **O que tem:** Filtro complementar (fusão odometria + BNO), correção de rumo em linha reta (`_apply_bno_straight_correction`), rejeição de spikes

---

## 2. Causas da deriva

| Causa | Efeito | Mitigação existente |
|-------|--------|---------------------|
| Diferença entre rodas (diâmetro, atrito) | Curva gradual para um lado | LEFT_MOTOR_CORRECTION_FACTOR |
| Patinação / deslizamento | Odometria subestima ou superestima | Nenhuma (BNO ajudaria) |
| Erro acumulativo em distâncias longas | Posição (x,y) e ângulo divergem | Nenhuma |
| Navegação direta (sem waypoints) | CTE não é aplicado | Nenhuma |
| Calibração incorreta | TICKS_PER_REVOLUTION, ROBOT_WHEEL_BASE_M | Valores em config |

---

## 3. Estratégia proposta (ordem de prioridade)

### Opção A — Reativar BNO com calibração cuidadosa (prioridade alta)
**Objetivo:** Usar o IMU para corrigir deriva angular em linha reta.

**Passos:**
1. Verificar se o BNO08x está conectado e funcionando na Raspberry (`tools/sync_test_motors_bno.py` ou `tools/bno08x_test.py`)
2. Testar `BNO_STRAIGHT_INVERT_CORRECTION`: se o robô desvia para a direita com BNO, tentar `False` (a convenção pode estar invertida)
3. Reduzir ganhos: `BNO_STRAIGHT_KP` (ex.: 0.4 em vez de 0.7), `BNO_FILTER_ALPHA` (ex.: 0.08 em vez de 0.15)
4. Ativar em fases: primeiro só `_apply_bno_straight_correction` (correção de rumo), sem fusão na pose; depois, se estável, ativar `USE_BNO_IN_NAVIGATION = True`
5. Validar: linha reta de 3–4 m, verificar se a deriva diminui

**Arquivos:** `config.py`, `robot_navigator.py`

---

### Opção B — Refinar CTE e ampliar uso (prioridade média)
**Objetivo:** Aplicar correção transversal mesmo em navegação “quase direta”.

**Problema atual:** CTE só é aplicado quando `path_index > 0` e há path com múltiplos waypoints. Em navegação direta ao POI (sem waypoints intermediários), o robô não tem “linha de referência” para corrigir.

**Solução:** Para navegação direta, criar um segmento virtual: (posição_base, POI). Assim o CTE pode ser calculado como desvio em relação à linha base→POI.

**Implementação:**
- Em `_move_towards_target()`, quando `is_direct_navigation` (path vazio ou ≤2 pontos):
  - Usar `base_position` ou `path[0]` como início do segmento e `current_target` como fim
  - Calcular CTE em relação a esse segmento
  - Aplicar correção angular (com ganho menor para não sobrecorrigir)

**Arquivos:** `robot_navigator.py`

---

### Opção C — Fator de correção progressivo na odometria (prioridade baixa)
**Objetivo:** Compensar erro acumulativo em distâncias longas.

**Lógica (existia em backup):**
```python
distance_correction_factor = 1.0 + (total_distance_traveled * 0.002)  # 0.2% por metro
dist_left = dist_left_raw * distance_correction_factor
dist_right = dist_right_raw * distance_correction_factor
```

**Cuidado:** Pode piorar se a deriva for angular (não linear). Usar só se testes mostrarem erro principalmente em distância.

**Arquivos:** `robot_navigator.py` (`_update_pose_with_odometry`)

---

### Opção D — Calibração dos parâmetros físicos
**Objetivo:** Garantir que TICKS, circunferência e base estejam corretos.

**Parâmetros em `config.py`:**
- `TICKS_PER_REVOLUTION = 45` — medir: uma volta completa da roda = quantos ticks?
- `ROBOT_WHEEL_CIRCUMFERENCE_M = 0.525` — medir circunferência real
- `ROBOT_WHEEL_BASE_M = 0.378` — distância entre centros das rodas

**Ferramenta:** `tools/sync_test_motors_bno.py` — teste de linha reta e giros, comparar odometria vs BNO (se disponível).

---

## 4. Fluxo da lógica de correção (resumo)

```
┌─────────────────────────────────────────────────────────────────┐
│                    ATUALIZAÇÃO DE POSE                           │
├─────────────────────────────────────────────────────────────────┤
│  Ticks (L, R) → delta_dist, delta_angle                          │
│       ↓                                                          │
│  Odometria pura: new_angle = current_angle + delta_angle          │
│       ↓                                                          │
│  [Se BNO ativo] Filtro complementar:                             │
│     new_angle += BNO_FILTER_ALPHA * (bno_angle - new_angle)       │
│       ↓                                                          │
│  current_angle = new_angle                                      │
│  current_position += (delta_x, delta_y)  [usando current_angle]   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    CONTROLE DE MOVIMENTO                         │
├─────────────────────────────────────────────────────────────────┤
│  angle_error = target_angle - current_angle                       │
│       ↓                                                          │
│  [Se path com waypoints] CTE = desvio perpendicular ao segmento  │
│     cte_correction = atan2(1.2 * cte, distance)  [limitado ±20°] │
│     angle_error -= cte_correction                                │
│       ↓                                                          │
│  [Se BNO ativo e avançando] _apply_bno_straight_correction()      │
│     Ajusta left_tps, right_tps para manter rumo                 │
│       ↓                                                          │
│  set_target_speed(left_tps, right_tps)                           │
│       ↓                                                          │
│  [Em robot_motor_controller] left_tps *= LEFT_MOTOR_CORRECTION  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Ordem de implementação sugerida

| # | Ação | Risco | Impacto esperado |
|---|------|-------|------------------|
| 1 | Calibrar BNO (Opção A): testar INVERT e ganhos reduzidos | Baixo | Alto se BNO estiver OK |
| 2 | CTE em navegação direta (Opção B) | Baixo | Médio |
| 3 | Ajustar LEFT_MOTOR_CORRECTION_FACTOR (Opção D) | Baixo | Médio se deriva for sistemática |
| 4 | Fator progressivo (Opção C) | Médio | Baixo; só se necessário |

---

## 6. Validação

- **Linha reta:** Robô percorre 3–4 m em linha reta; desvio lateral < 15 cm
- **Giro 90°:** Após giro, rumo alinhado com esperado (odometria ou BNO)
- **Rota completa:** Ida ao POI + retorno; robô volta próximo da base (< 30 cm)
- **Com obstáculo:** Parada OK (já validado); após remover obstáculo, robô segue ao POI (Fase 2c)

---

## 7. Arquivos principais

| Arquivo | Função |
|---------|--------|
| `src/core/config.py` | USE_BNO_IN_NAVIGATION, BNO_*, TICKS_PER_REVOLUTION, ROBOT_WHEEL_* |
| `src/core/robot_navigator.py` | _update_pose_with_odometry, _move_towards_target, _calculate_cte, _apply_bno_straight_correction |
| `src/core/robot_motor_controller.py` | LEFT_MOTOR_CORRECTION_FACTOR, set_target_speed |
| `tools/sync_test_motors_bno.py` | Teste de linha reta e giros com BNO |
| `tools/bno08x_test.py` | Verificar se BNO responde |
