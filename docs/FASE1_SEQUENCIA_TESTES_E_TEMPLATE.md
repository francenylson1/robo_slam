# Fase 1 – Sequência mínima de testes e template de anotação

Documento para padronizar os testes na Raspberry e registrar resultados (odom vs BNO) de forma consistente.

---

## Sequência mínima de testes (Raspberry)

Executar **na ordem** abaixo. Cada bloco pode ser repetido mais de uma vez se quiser mais amostras (ex.: 3x linha reta, 3x cada giro).

### Pré-requisitos

- Robô em superfície plana, bateria OK.
- Opcional: `--calibrate` no primeiro comando do dia (uma vez).

### 1. Linha reta (correção BNO)

| Ordem | Comando | Duração | O que anotar |
|-------|---------|---------|--------------|
| 1.1 | `python3 tests/teste_bno_suite.py --no-turns --duration 35` | 35 s | odom_angle, BNO deriva, “Rumo ref” ou “BNO sem leitura” |
| 1.2 | (repetir 1.1) | 35 s | idem |
| 1.3 | (repetir 1.1) | 35 s | idem |

**Alternativa curta (10 s)** para checagem rápida:

```bash
python3 tests/teste_bno_suite.py --no-turns --duration 10
```

### 2. Giros à direita

| Ordem | Comando | O que anotar |
|-------|---------|--------------|
| 2.1 | `python3 tests/teste_bno_suite.py --no-straight --direction right --angles 90` | odom_angle, odom_error, BNO delta |
| 2.2 | `python3 tests/teste_bno_suite.py --no-straight --direction right --angles 180` | idem |
| 2.3 | (opcional) `--angles 45 90 180` | idem para cada ângulo |

### 3. Giros à esquerda

| Ordem | Comando | O que anotar |
|-------|---------|--------------|
| 3.1 | `python3 tests/teste_bno_suite.py --no-straight --direction left --angles 90` | odom_angle, odom_error, BNO delta |
| 3.2 | `python3 tests/teste_bno_suite.py --no-straight --direction left --angles 180` | idem |

### 4. Suíte completa (uma vez por sessão)

Para gerar CSV e ter visão geral:

```bash
mkdir -p data
python3 tests/teste_bno_suite.py --duration 10 --angles 90 180 --direction both --csv data/fase1_$(date +%Y%m%d_%H%M).csv
```

Ajuste `--duration` e `--angles` conforme quiser; `--direction both` roda os mesmos ângulos à esquerda e à direita.

---

## Template de anotação – Linha reta (odom vs BNO)

Copie a tabela abaixo (ou use o CSV) e preencha a cada run. “Ref BNO” = se apareceu “Rumo de referência BNO” (Sim) ou “BNO sem leitura” (Não) ou “BNO não disponível” (N/A).

| Data | Hora | Run | Duração (s) | Ref BNO | Odometria (ângulo acum.) ° | BNO deriva ° | Observações |
|------|------|-----|-------------|---------|---------------------------|--------------|-------------|
|      |      | 1   | 35          |         |                           |              |             |
|      |      | 2   | 35          |         |                           |              |             |
|      |      | 3   | 35          |         |                           |              |             |
|      |      | 4   | 35          |         |                           |              |             |
|      |      | 5   | 35          |         |                           |              |             |
|      |      | 6   | 35          |         |                           |              |             |
|      |      | 7   | 35          |         |                           |              |             |
|      |      | 8   | 35          |         |                           |              |             |
|      |      | 9   | 35          |         |                           |              |             |
|      |      | 10  | 35          |         |                           |              |             |

**Legenda Ref BNO:** Sim = teve rumo de referência; Não = “BNO sem leitura”; N/A = “BNO não disponível”.

---

## Template de anotação – Giros (odom vs BNO)

Uma linha por giro (sentido + ângulo).

| Data | Hora | Sentido | Alvo ° | Odometria ° | Erro odom ° | BNO delta ° | Observações |
|------|------|---------|--------|-------------|-------------|-------------|-------------|
|      |      | D       | 90     |             |             |             |             |
|      |      | D       | 180    |             |             |             |             |
|      |      | E       | 90     |             |             |             |             |
|      |      | E       | 180    |             |             |             |             |

*(D = direita, E = esquerda.)*

---

## CSV gerado pela suíte

Ao usar `--csv data/arquivo.csv`, a suíte já grava colunas úteis. Para **linha reta** o resumo impresso traz `odom_angle` e `bno_yaw_drift_deg`. Para **giros**, o CSV tem `name`, `direction`, `target_deg`, `odom_angle_deg`, `odom_error_deg`, `bno_delta_deg`, etc.

Você pode:
- Rodar com `--csv` e depois colar os números no template de anotação, ou
- Usar o CSV como registro primário e o template só para observações e decisões (ex.: “ajustar Kp”, “recalibrar”).

---

## Checklist rápido por sessão de testes

- [ ] 1× linha reta 35 s (ou 3× para estatística)
- [ ] 1× giro 90° direita + 1× 180° direita
- [ ] 1× giro 90° esquerda + 1× 180° esquerda
- [ ] Anotar na tabela (ou salvar CSV)
- [ ] Se “BNO sem leitura” ou “BNO não disponível” aparecer, anotar e considerar retry/calibração

---

*Ver também: `docs/FASE1_ANALISE_LOGS_LINHA_RETA.md` (análise dos seus 9 runs) e `docs/FASE1_TESTES_NAVEGACAO.md` (comandos e parâmetros).*
