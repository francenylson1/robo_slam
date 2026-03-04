# Fase 1 – Testes, análises e ajustes (linha reta e giros)

Objetivo: testes exaustivos para afinar navegação em **linha reta**, **giros à esquerda** e **giros à direita** com precisão, antes da integração BNO no `main.py`.

**Documentos relacionados:**
- **`docs/FASE1_ANALISE_LOGS_LINHA_RETA.md`** – Análise dos logs de 9 runs de linha reta (35 s): odom vs BNO, falhas de ref e init, conclusões.
- **`docs/FASE1_SEQUENCIA_TESTES_E_TEMPLATE.md`** – Sequência mínima de testes (ordem dos comandos) e **template de anotação** (tabelas odom vs BNO para linha reta e giros).

---

## Onde rodar

- **Script:** `tests/teste_bno_suite.py`
- **Plataforma:** Raspberry Pi (motores + BNO08x). No desktop o script sai com aviso.
- **Raiz do projeto:** executar na pasta do repositório, ex.: `python tests/teste_bno_suite.py ...`

---

## Comandos úteis

### Linha reta + giros (padrão: 45°, 90°, 180°, 360° – direita e esquerda)

```bash
python tests/teste_bno_suite.py
```

### Só linha reta (sem giros)

```bash
python tests/teste_bno_suite.py --no-turns
```

### Linha reta com duração e calibração BNO

```bash
python tests/teste_bno_suite.py --calibrate --duration 5
```

### Só giros, ângulos específicos, direção esquerda ou direita

```bash
# Giros 90° e 180° para direita e esquerda (both)
python tests/teste_bno_suite.py --no-straight --angles 90 180 --direction both

# Só giros para esquerda
python tests/teste_bno_suite.py --no-straight --direction left --angles 45 90 180

# Só giros para direita
python tests/teste_bno_suite.py --no-straight --direction right --angles 45 90 180
```

### Correção fina do giro com BNO (opcional)

Após o giro por odometria, corrige até o ângulo desejado usando o BNO (tolerância em graus):

```bash
python tests/teste_bno_suite.py --no-straight --use-bno-turn --turn-tolerance 1.5 --angles 90 180
```

### Salvar resultados em CSV (análise e ajuste de ganhos)

```bash
mkdir -p data
python tests/teste_bno_suite.py --csv data/teste_bno_$(date +%Y%m%d_%H%M).csv
```

### TPS de giro e modo quiet

```bash
python tests/teste_bno_suite.py --turn-tps 10 --quiet --csv data/teste.csv
```

---

## Parâmetros de ajuste (config.py)

| Parâmetro | Uso |
|-----------|-----|
| `BNO_STRAIGHT_KP` | Ganho da correção de rumo em linha reta. Aumentar = correção mais forte. |
| `BNO_STRAIGHT_MAX_CORRECTION_TPS` | Limite (TPS) da correção por ciclo. Evita correções bruscas. |
| `BNO_STRAIGHT_INVERT_CORRECTION` | Sentido da correção (True = convenção deste robô). Não trocar sem testar. |
| `TURN_TPS_DEFAULT` | Velocidade (TPS) dos giros. Menor = mais preciso, mais lento. |
| `SPEED_SLOW_TPS` | Velocidade da linha reta. |

Se a **linha reta** ainda desviar ou oscilar, ajustar `BNO_STRAIGHT_KP` e `BNO_STRAIGHT_MAX_CORRECTION_TPS` e rodar de novo com `--csv` para comparar deriva (BNO e odometria).

Se os **giros** ficarem com erro sistemático (ex.: sempre +3°), considerar depois: fator de correção por odometria ou uso de `--use-bno-turn` na navegação.

---

## Checklist Fase 1 (marcar na Raspberry)

- [ ] Rodar linha reta várias vezes (`--no-turns --duration 4` ou 5); anotar deriva BNO e odometria.
- [ ] Rodar giros 45°, 90°, 180°, 360° para **direita** e **esquerda** (`--no-straight --direction both`); anotar erro odometria vs BNO.
- [ ] Testar `--calibrate` antes da suíte; comparar resultados com/sem calibração.
- [ ] Testar `--use-bno-turn --turn-tolerance 1.5` e ver se o erro final do giro cai.
- [ ] Salvar resultados com `--csv`; analisar erros e decidir se ajusta `TURN_TPS_DEFAULT` ou ganhos no `config.py`.
- [ ] Quando estável: documentar no repositório os ganhos/parâmetros usados e um resumo dos erros típicos (ex.: “giro 90° odom ±2°, BNO ±1°”).
- [ ] (Opcional) Se os logs vierem cheios de “DBG::” / “Packet”, redirecionar para arquivo e filtrar: `python3 tests/teste_bno_suite.py ... 2>&1 | tee log.txt` e analisar só o resumo; ou usar `grep -v "DBG::"` para saída mais limpa.

---

## Próximo passo

Quando a Fase 1 estiver estável e anotada, seguir para **Fase 2** (integração BNO no `main.py`) usando o checklist em `docs/REVISAO_BNO_LINHA_RETA.md` e em `docs/PROMPT_CONTINUACAO_BNO_E_INTEGRACAO_2026.md`.
