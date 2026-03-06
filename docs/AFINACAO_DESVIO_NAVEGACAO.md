# Afinação do desvio na navegação (chegar ao POI sem desvio)

Quando o robô chega ao POI com **leve desvio para a direita**, dois níveis de correção atuam. Ajuste nesta ordem.

---

## 1. Correção BNO (rumo em linha reta)

**Arquivo:** `src/core/config.py`

| Parâmetro | Efeito | Se o robô desvia para a **direita** | Se o robô desvia para a **esquerda** |
|-----------|--------|-------------------------------------|--------------------------------------|
| `BNO_STRAIGHT_KP` | Força da correção de rumo (BNO). Maior = corrige mais. | **Aumentar** (ex.: 1.4, 1.5) | Reduzir (ex.: 1.0) |
| `BNO_STRAIGHT_INVERT_CORRECTION` | Sentido da correção. | Testar **False** se aumentar KP piorar | Testar **True** |
| `BNO_STRAIGHT_MAX_CORRECTION_TPS` | Limite máximo de TPS de correção por ciclo. | Só aumentar se a correção parecer “travada” (ex.: 14) | — |

- O BNO compara o yaw atual com a referência e aplica `left = base - corr`, `right = base + corr` (com possível inversão).
- Valores atuais típicos: `BNO_STRAIGHT_KP = 1.4`, `BNO_STRAIGHT_INVERT_CORRECTION = True`.

---

## 2. Correção por motor (fator fixo)

**Arquivo:** `src/core/robot_motor_controller.py`

| Constante | Efeito |
|-----------|--------|
| `LEFT_MOTOR_CORRECTION_FACTOR` | Multiplicador na roda **esquerda** (ex.: 0.9 = 90%). Menor = esquerda mais fraca → tendência a curvar para a **direita**. |
| `RIGHT_MOTOR_CORRECTION_FACTOR` | Referência (geralmente 1.0). |

- Hoje: esquerda em **0.9** para compensar deriva à direita.
- Se **mesmo com BNO forte** ainda desviar para a direita: reduzir um pouco mais o esquerdo (ex.: **0.88**).
- Se passar a desviar para a **esquerda**: aumentar o esquerdo (ex.: **0.92** ou **1.0**) e/ou reduzir `BNO_STRAIGHT_KP`.

---

## Ordem sugerida de afinação

1. Ajustar **só** `BNO_STRAIGHT_KP` (ex.: 1.2 → 1.4 → 1.5) e testar.
2. Se o desvio inverter (ir para a esquerda): testar `BNO_STRAIGHT_INVERT_CORRECTION = False`.
3. Se ainda sobrar desvio para a direita: afinar `LEFT_MOTOR_CORRECTION_FACTOR` (ex.: 0.88) no `robot_motor_controller.py`.

---

## Logs úteis

- **CORREÇÃO_DERIVA:** mostra `left→left_corrigido`, `right→right_corrigido` e os fatores E/D aplicados.
- **Posição final vs POI:** comparar `(3.10, 8.81)` com o POI `(3.21, 8.66)` para ver se o robô ficou à esquerda/direita e à frente/atrás do alvo.
