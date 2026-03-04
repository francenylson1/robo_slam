# Fase 1 – Análise dos logs de linha reta (35 s)

Análise dos testes de percursos em linha reta com duração de 35 s, correção BNO (quando disponível) e saída da suíte `teste_bno_suite.py --no-turns --duration 35`.

---

## Resumo dos runs (9 testes no paste)

| # | Odometria (ângulo acum.) | BNO deriva | Referência BNO no início? | Observação |
|---|---------------------------|------------|---------------------------|------------|
| 1 | +210,44° | +2,55° | Sim (-0,1°) | Odometria muito alta vs BNO |
| 2 | +141,47° | +23,73° | Sim (-0,1°) | Ambos indicam deriva para a direita |
| 3 | +12,38° | -0,81° | **Não** (BNO sem leitura) | Sem correção de rumo |
| 4 | -178,61° | N/A | **BNO não disponível** | Init falhou (pacote 0x7B) |
| 5 | -100,80° | +2,65° | Sim (-0,1°) | Odometria negativa vs BNO positivo |
| 6 | **-8,84°** | **0,00°** | Sim (-0,11°) | Melhor run: baixa deriva |
| 7 | +1,77° | +1,10° | Sim (-0,07°) | Boa concordância |
| 8 | -5,31° | +0,88° | **Não** (BNO sem leitura) | Sem correção |
| 9 | -139,70° | -0,40° | Sim (-0,08°) | Odometria muito negativa vs BNO |

*(Os caracteres Ã¢ngulo/inÃ­cio nos logs são artefato de encoding UTF-8 no terminal; os números estão corretos.)*

---

## Conclusões da análise

### 1. Disponibilidade do BNO

- **1 run:** BNO não inicializou (“BNO não disponível” + pacote 0x7B logo após init). Recomendação: retry no init ou delay maior após RST.
- **2 runs:** BNO OK mas **sem leitura válida** dentro do timeout de 1,5 s → “BNO sem leitura; frente sem correção de rumo”. Nesses runs a correção não atuou; o robô andou com (base_tps, base_tps).
- **6 runs:** Referência BNO obtida (yaw_ref em torno de -0,1°) e correção ativa.

### 2. Odometria vs BNO

- **Odometria (ângulo acumulado):** em teoria, em linha reta deveria ficar perto de 0°. Valores como +210°, +141°, -178°, -139°, -100° indicam que a odometria está integrando uma rotação muito grande (deriva real do robô e/ou erro de calibração/assinatura dos ticks).
- **BNO deriva:** quando há ref, fica entre -0,81° e +23,73°. Em vários runs o BNO indica poucos graus (0° a ~2,65°) enquanto a odometria indica dezenas ou centenas de graus → forte divergência odom vs BNO.
- **Interpretação:**  
  - Ou a odometria está errando (fator esquerda/direita, TPR, base, ou direção dos ticks),  
  - Ou o robô realmente girou muito (patinação, piso, assimetria) e o BNO subestima (fusão com magnetômetro, atraso, etc.).  
  O run 6 (odom -8,84°, BNO 0°) é o mais coerente e indica que quando a correção BNO está ativa e a deriva é pequena, os dois podem concordar bem.

### 3. Debug “DBG::” nos logs

- Os blocos `********** Packet *************` e `DBG::` vêm da biblioteca Adafruit (SHTP). O nosso código já usa `debug=False` em `bno08x_init`.
- Esse dump pode ainda ser impresso quando a lib recebe relatórios “UNKNOWN” (ex.: 0x7B). Efeitos: poluição do log e possível atraso no laço, reduzindo a taxa de leitura do ROTATION_VECTOR.
- **Recomendações:**  
  - Atualizar `adafruit-circuitpython-bno08x` / `adafruit-blinka` na Raspberry.  
  - Se a versão já for a mais recente, considerar redirecionar stdout durante o teste (ex.: `python tests/teste_bno_suite.py ... 2>&1 | grep -v "DBG::"`) para análise, ou abrir issue/PR na lib para não imprimir em modo não-debug.

### 4. Próximos passos sugeridos

1. **Estabilizar init BNO:** retry ou delay após RST para evitar o “BNO não disponível” (run 4).
2. **Aumentar chance de 1ª leitura:** aumentar timeout de espera da primeira leitura (ex.: 2,5 s) ou mais warm-up no init.
3. **Revisar odometria:** conferir sinais e fatores (TPR, base, circunferência) e, se possível, comparar com distância/ângulo real (fita no chão, giro de 90° no lugar).
4. **Seguir com a sequência mínima de testes e o template de anotação** em `docs/FASE1_SEQUENCIA_TESTES_E_TEMPLATE.md` para padronizar os próximos testes e análise.

---

## Referência rápida dos números (para planilha)

| Run | odom_deg | bno_drift_deg | ref_ok | obs |
|-----|----------|---------------|--------|-----|
| 1 | 210.44 | 2.55 | 1 | |
| 2 | 141.47 | 23.73 | 1 | |
| 3 | 12.38 | -0.81 | 0 | sem ref |
| 4 | -178.61 | N/A | - | BNO init fail |
| 5 | -100.80 | 2.65 | 1 | |
| 6 | -8.84 | 0.00 | 1 | melhor |
| 7 | 1.77 | 1.10 | 1 | |
| 8 | -5.31 | 0.88 | 0 | sem ref |
| 9 | -139.70 | -0.40 | 1 | |

*(ref_ok: 1 = teve yaw_ref, 0 = sem leitura no timeout, - = BNO indisponível)*
