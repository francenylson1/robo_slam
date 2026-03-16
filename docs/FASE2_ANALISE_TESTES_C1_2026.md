# Análise dos testes C1 — Março 2026

**Data:** Março 2026  
**Baseado em:** 3 testes realizados na Raspberry Pi com o robô físico.

---

## 1. Resumo executivo

| Conclusão | Detalhe |
|-----------|---------|
| **Posição do C1** | Frente do robô — sensor no parachoques preto, à frente do corpo vermelho |
| **0° (cabo)** | Traseira → aponta para o corpo vermelho |
| **180° (frente)** | Direção de movimento → parachoques e estruturas em C (~94 mm) |
| **Faixa frontal para obstáculos** | Centro **180°**, largura 200° |
| **Limiar corpo** | Ignorar leituras < 150 mm (parachoques) |
| **Limiar parada** | Obstáculo real em 150–350 mm à frente |
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
- O arco **120°–240°** contém o **parachoques** e estruturas em C que circundam o C1 (~94–130 mm)
- O C1 está na **frente** do robô (parachoques); o corpo vermelho fica atrás (0°)
- **180°** = direção de movimento = frente do robô (parachoques mais próximo)

#### Esquema simplificado (visto de cima)

```
        0° (cabo) = TRASEIRA
        corpo vermelho atrás
              ↑
     livre    |    livre
  260°────────┼────────100°
              |
  PARACHOQUES |  PARACHOQUES
  (94–130 mm) |  (94–130 mm)
  120°────────┼────────240°
              |
          180° = FRENTE
        (direção de movimento)
```

---

### Teste 2 — `--front-deg 200 --front-center 180` (faixa centrada em 180°)

**Objetivo:** Validar se 180° é a frente do robô.

#### Resultados
- Faixa frontal: **80° a 280°** (centro 180°)
- **Mínimo frontal:** 94–95 mm
- **Mínimo 360°:** 94–95 mm → frontal = 360°

#### Interpretação
- A faixa frontal centrada em 180° **apontou para a frente** (direção de movimento)
- O mínimo 94 mm é o **parachoques** à frente do C1 — correto
- **180° é a frente** do robô; use `--front-center 180` para detecção de obstáculos

---

### Teste 3 — `--robot-model dev` (faixa 200° centrada em 0°)

**Objetivo:** Validar o preset dev (200° centrado em 0°).

#### Resultados
- Faixa frontal: **260°→0°→100°** (±100° a partir de 0°)
- **Mínimo frontal:** ~1246–1248 mm (1,25 m) — estável
- **Mínimo 360°:** 94–98 mm (corpo)

#### Interpretação
- Faixa 260°→0°→100° olha para **trás e laterais** (exclui 120°–240°)
- O mínimo ~1,25 m é parede/obstáculo **atrás** ou nas laterais (não à frente)
- Para **obstáculos à frente** use centro **180°**, não 0°

---

## 3. Configuração validada para este robô

### Montagem física (confirmada)
- **C1:** sensor no parachoques preto, na **frente** do robô
- **Corpo vermelho:** atrás do C1 (traseira)
- **0°:** traseira (cabo aponta para o corpo)
- **180°:** frente (direção de movimento)

### Parâmetros para detecção de obstáculos

| Parâmetro | Valor | Uso |
|-----------|--------|-----|
| **Faixa frontal** | 200° | `--front-deg 200` |
| **Centro** | **180°** | `--front-center 180` — frente = direção de movimento |
| **Limiar corpo (ignorar)** | < 150 mm | Parachoques à frente do C1 |
| **Limiar parada** | < 350 mm | Obstáculo real à frente |

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
