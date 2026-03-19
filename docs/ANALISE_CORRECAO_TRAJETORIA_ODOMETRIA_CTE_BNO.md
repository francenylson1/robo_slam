# Análise: Correção de Trajetória — Odometria, CTE e BNO

**Data:** 19 de março de 2026  
**Objetivo:** Explicar o que já existe, por que não está funcionando bem, e o papel do BNO.

---

## 1. O que já temos no sistema

### 1.1 Odometria (fonte da pose)
- **Onde:** `_update_pose_with_odometry()` em `robot_navigator.py`
- **Entrada:** Ticks das rodas esquerda e direita
- **Saída:** `current_position` (x, y) e `current_angle` (θ)

**Cálculo:**
```
delta_distance = (dist_left + dist_right) / 2
delta_angle = (dist_left - dist_right) / base_rodas

current_angle += delta_angle
delta_x = delta_distance * cos(current_angle)
delta_y = delta_distance * sin(current_angle)
current_position += (delta_x, delta_y)
```

**Problema central:** A posição (x, y) depende do ângulo. Se o ângulo deriva (erro acumulado), a posição também deriva.

---

### 1.2 CTE (Cross-Track Error)
- **Onde:** `_calculate_cte()` e `_move_towards_target()` em `robot_navigator.py`
- **O que faz:** Calcula o desvio perpendicular do robô em relação ao segmento de caminho (waypoint anterior → waypoint atual)
- **Quando aplica:** Quando `path_index > 0` e `path_index < len(path)` — ou seja, **já está aplicado** em navegação direta (path = [base, POI], path_index = 1)

**Lógica:**
```
CTE = distância perpendicular de current_position à linha (path_start, path_end)
CTE > 0 → robô à esquerda da linha → corrige ângulo para a direita
angle_error -= cte_correction  (ganho 1.2, limite ±20°)
```

**Problema:** O CTE usa `current_position`. Se a odometria erra, `current_position` está errado. O robô pensa que está em (x, y), mas na realidade está em outro lugar. A correção do CTE pode ser **no sentido errado** ou **exagerada**.

---

### 1.3 Correção assimétrica dos motores
- **Onde:** `robot_motor_controller.py`
- **Valores:** `LEFT_MOTOR_CORRECTION_FACTOR = 0.96`
- **Objetivo:** Compensar deriva sistemática à direita (motor esquerdo mais fraco)

---

### 1.4 BNO08x — implementado mas desativado
- **Status:** `USE_BNO_IN_NAVIGATION = False` em `config.py`
- **O que faz quando ativo:**
  1. **Filtro complementar na pose:** `current_angle = odom_angle + alpha * (bno_angle - odom_angle)` — corrige o ângulo usado na pose
  2. **Correção de rumo em linha reta:** `_apply_bno_straight_correction()` — ajusta left_tps/right_tps para manter o rumo ao avançar

---

## 2. Por que a correção de trajetória não está funcionando bem?

### Cadeia de dependências

```
Odometria (ângulo) deriva
        ↓
current_angle errado
        ↓
current_position errado (delta_x, delta_y usam o ângulo)
        ↓
CTE calculado com posição errada → correção pode piorar
        ↓
angle_error (target - current_angle) também errado
        ↓
Robô "corrige" para o lugar errado
```

**Conclusão:** O CTE e a odometria formam um laço. Se a odometria (especialmente o ângulo) deriva, todo o resto fica comprometido. O CTE sozinho não resolve — ele depende de uma pose razoavelmente correta.

---

## 3. Por que o BNO foi desativado (bugs documentados)

| Bug / sintoma | Causa provável | Documento |
|---------------|----------------|------------|
| Desvio sistemático para a direita | `BNO_STRAIGHT_INVERT_CORRECTION` no sentido errado; ou ganho alto | PROMPT_CONTINUACAO_FASE2, NAVEGACAO_ODOMETRIA_VS_IMU_BNO |
| Giro infinito no POI | BNO disputando com odometria durante giro; ângulo da pose "travado" | ESTRATEGIA_ODOMETRIA_E_BNO_GRADATIVO |
| "Virtual de ré" | BNO e odometria em conflito; pose exibida incoerente | ESTRATEGIA_ODOMETRIA_E_BNO_GRADATIVO |
| Correção no sentido errado | Convenção de yaw ou INVERT incorreta | NAVEGACAO_ODOMETRIA_VS_IMU_BNO |

---

## 4. Por que o BNO FOI considerado no plano (e deve ser)

O plano em `PLANO_FASE2B_DERIVA_CORRECAO_TRAJETORIA.md` coloca o BNO como **Opção A — prioridade alta**. O BNO é a única fonte que pode **corrigir o ângulo independentemente da odometria**. Sem isso:

- Odometria continua errando no ângulo
- Posição continua errando
- CTE continua calculando com dados ruins

**O BNO ataca a raiz:** o ângulo. Se o ângulo for mais estável (fusão odometria + BNO), a posição melhora e o CTE passa a fazer sentido.

---

## 5. Resumo: o que cada componente faz e sua limitação

| Componente | Função | Limitação |
|------------|--------|-----------|
| **Odometria** | Estima pose (x, y, θ) | Ângulo acumula erro (patinação, diferença entre rodas) |
| **CTE** | Corrige desvio lateral em relação ao caminho | Depende de `current_position` correto; se odometria erra, CTE erra |
| **LEFT_MOTOR_CORRECTION** | Compensa assimetria física | Só ajuda se a deriva for sistemática (sempre para um lado) |
| **BNO** | Corrige ângulo (rumo) independente das rodas | Desativado por bugs; precisa calibração para reativar |

---

## 6. Estratégia recomendada (ordem) — atualizado pós-teste 19/03

1. ~~Reativar BNO~~ — **Descartado:** testes causaram perda total de trajetória (diagonal, passou do POI)

2. **Refinar CTE** — ampliar uso em navegação direta; ajustar ganho/limite

3. **Calibrar parâmetros físicos** — TICKS_PER_REVOLUTION, ROBOT_WHEEL_BASE_M, LEFT_MOTOR_CORRECTION_FACTOR

4. **C1 para correção** — não prioritário para trajetória; C1 é mais útil para desvio de obstáculos (Fase 2c) e futura localização (Fase 3)

---

## 7. Arquivos relevantes

| Arquivo | O que alterar |
|---------|---------------|
| `config.py` | USE_BNO_IN_NAVIGATION, BNO_STRAIGHT_INVERT_CORRECTION, BNO_STRAIGHT_KP, BNO_FILTER_ALPHA |
| `robot_navigator.py` | _update_pose_with_odometry, _move_towards_target, _apply_bno_straight_correction |
| `robot_motor_controller.py` | LEFT_MOTOR_CORRECTION_FACTOR |

---

## 8. Teste BNO 19/03/2026 — resultado

**Teste 1 (fusão na pose):** BNO com ganhos conservadores (KP 0.4, ALPHA 0.08). Resultado: **perda total de trajetória** (diagonal dir/esq, passou do POI).

**Teste 2 (só correção de rumo):** USE_BNO_POSE_FUSION=False. Pose 100% odometria; BNO só em _apply_bno_straight_correction (ajusta TPS ao avançar). Ganhos KP 0.35, MAX 8 TPS. Em teste.
