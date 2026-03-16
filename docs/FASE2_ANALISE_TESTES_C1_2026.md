# Análise dos testes C1 — Março 2026

**Data:** Março 2026  
**Baseado em:** 3 testes realizados na Raspberry Pi com o robô físico.

---

## 1. Resumo executivo

| Conclusão | Detalhe |
|-----------|---------|
| **Faixa frontal correta** | `--robot-model dev` (200° centrado em 0°) está correto para este robô |
| **Onde está o corpo** | ~120° de arco entre 120° e 240° (min 94–130 mm) |
| **Área livre** | ~240° (setores fora do corpo) |
| **Obstáculo à frente** | Parede/objeto a ~1,25 m na direção livre |
| **Próximo passo** | Etapa 2: `--min-stop` e `--min-warn` → Etapa 3: integrar à navegação |

---

## 2. Análise detalhada por teste

### Teste 1 — `--diagnose --scans 2` (diagnóstico angular)

**Objetivo:** Mapear onde está o corpo do robô e a área livre.

#### Resultados
- **Obstáculo mais próximo em 360°:** 94–95 mm (corpo do robô ou alcance mínimo)
- **Setores ocupados (dist &lt; 150 mm):** 120°–240° → **~120°** de arco
- **Setores livres (dist ≥ 150 mm):** 0°–120° e 240°–360° → **~240°**
- **Direção com maior distância:** Scan 1: ~10°, Scan 2: ~350° (variação entre scans)

#### Interpretação
- O corpo do robô ocupa o arco **120°–240°** (lateral/traseira do sensor)
- A frente (direção com mais espaço livre) está em torno de **0°** ou **350°** (zona do cabo ou adjacente)
- A leitura de ~94 mm nos setores ocupados é típica do corpo ou do alcance mínimo do C1

#### Esquema simplificado (visto de cima)

```
        0° (cabo) ← frente livre
              ↑
     livre    |    livre
  260°────────┼────────100°
              |
     OCUPADO  |  OCUPADO
   ( corpo )  |  ( corpo )
  120°────────┼────────240°
              |
          180°
```

---

### Teste 2 — `--front-deg 200 --front-center 180` (faixa centrada em 180°)

**Objetivo:** Validar se 180° é a frente do robô.

#### Resultados
- Faixa frontal: **80° a 280°** (centro 180°)
- **Mínimo frontal:** 94–95 mm
- **Mínimo 360°:** 94–95 mm → frontal = 360°

#### Interpretação
- A faixa frontal **apontou para o corpo** (120°–240° está dentro de 80°–280°)
- **180° NÃO é a frente** neste robô — é a direção do corpo
- O comando `--front-center 180` não deve ser usado para este modelo

---

### Teste 3 — `--robot-model dev` (faixa 200° centrada em 0°)

**Objetivo:** Validar o preset dev (200° centrado em 0°).

#### Resultados
- Faixa frontal: **260°→0°→100°** (±100° a partir de 0°)
- **Mínimo frontal:** ~1246–1248 mm (1,25 m) — estável
- **Mínimo 360°:** 94–98 mm (corpo)

#### Interpretação
- A faixa frontal **exclui o corpo** (120°–240°) e olha apenas para a zona livre
- O mínimo frontal ~1,25 m indica parede ou obstáculo fixo à frente
- **O preset `dev` está correto** para este robô
- A direção de movimento corresponde a **0°** (ou próximo: 350°–10°)

---

## 3. Configuração validada para este robô

| Parâmetro | Valor | Uso |
|-----------|--------|-----|
| **Faixa frontal** | 200° | Preset `dev` |
| **Centro** | 0° | Direção do cabo = frente |
| **Área do corpo** | 120°–240° | Desprezar para detecção de obstáculos |
| **Distância típica à frente** | ~1,25 m | Parede ou limite do ambiente no teste |

---

## 4. Próximos passos (Etapa 2 e 3)

### Etapa 2 — Distâncias mínimas (parada e alerta)

1. Adicionar `--min-stop 0.35` e `--min-warn 0.50` ao `teste_c1_isolado.py`
2. Exibir alerta quando `min frontal < min-warn`
3. **Teste:** Aproximar objeto à frente e confirmar que o alerta aparece abaixo de 50 cm

### Etapa 3 — Integração à navegação

1. Criar `src/core/lidar_c1_reader.py` (leitura C1 + decisão de obstáculo)
2. Integrar no `robot_navigator.py` ou `robot_motor_controller.py`
3. Adicionar em `config.py`: `LIDAR_OBSTACLE_MIN_DISTANCE = 0.35`
4. **Teste:** Colocar obstáculo no caminho durante navegação e validar parada automática

---

## 5. Observações técnicas dos logs

- **Saúde: None** — pode ser normal para algumas bibliotecas; o scan funciona
- **In waiting: 3 / 0** — mensagens da biblioteca rplidarc1
- **Variação de pontos por scan:** 262–545 pts — normal (taxa de rotação do motor)
- **Erro de encoding:** caracteres como `ð`, `Â°` indicam UTF-8 no terminal da Pi; não afetam o funcionamento
