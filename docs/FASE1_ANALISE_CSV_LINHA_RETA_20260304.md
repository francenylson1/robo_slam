# Análise dos CSV – Linha reta (04/03/2026)

Arquivos analisados: 13 runs de linha reta (suíte BNO, `--no-turns --duration 35`).

---

## Tabela resumo (ordenada por horário)

| Arquivo | Hora | Odometria (°) | BNO deriva (°) | BNO início→fim | Avaliação |
|---------|------|----------------|----------------|----------------|------------|
| linha_reta_20260304_1241.csv | 12:41 | **+5,31** | -5,14 | 7,75 → 2,61 | Aceitável |
| linha_reta_20260304_1245.csv | 12:45 | **-3,54** | -0,40 | -0,09 → -0,50 | Bom |
| linha_reta_20260304_1544.csv | 15:44 | **+1,77** | -0,09 | -0,10 → -0,19 | Muito bom |
| linha_reta_20260304_1545.csv | 15:45 | **-132,63** | -0,43 | -0,10 → -0,53 | ❌ Desorientado (esquerda) |
| linha_reta_20260304_1546.csv | 15:46 | **-111,41** | 0,10 | -0,10 → ~0 | ❌ Desorientado (esquerda) |
| linha_reta_20260304_1548.csv | 15:48 | **-206,90** | -0,01 | -0,10 → -0,10 | ❌ Desorientado (esquerda) |
| linha_reta_20260304_1550.csv | 15:50 | **-14,15** | -0,26 | -0,09 → -0,36 | Aceitável |
| linha_reta_20260304_1552.csv | 15:52 | **-1,77** | -0,35 | -0,10 → -0,45 | Muito bom |
| linha_reta_20260304_1554.csv | 15:54 | **-30,06** | 0,09 | -0,09 → ~0 | Moderado (curva esq.) |
| linha_reta_20260304_1555.csv | 15:55 | **~0** | 0,28 | -0,11 → 0,17 | Muito bom |
| linha_reta_20260304_1556.csv | 15:56 | **-53,05** | -0,94 | -0,08 → -1,02 | ❌ Desorientado (esquerda) |
| linha_reta_20260304_1557.csv | 15:57 | **-175,07** | 0,61 | -0,09 → 0,52 | ❌ Desorientado (esquerda) |
| linha_reta_20260304_1559.csv | 15:59 | **+21,22** | 1,12 | -0,10 → 1,02 | Moderado (curva dir.) |

---

## O que cada coluna significa

- **Odometria (°):** ângulo acumulado pelos ticks das rodas. Em linha reta ideal seria próximo de 0. **Negativo** = rodas indicam giro para a **esquerda**; **positivo** = giro para a **direita**.
- **BNO deriva (°):** diferença (yaw_fim − yaw_início) pelo BNO. Indica quanto o robô girou segundo o IMU.
- **BNO início → fim:** yaw no início e no fim do teste (graus).

Quando a odometria dá valores muito altos (ex.: -130°, -207°, -175°) e o BNO mostra poucos graus, em geral:
- a **odometria** está integrando patinação ou erro de encoder (uma roda “girou” muito no lugar ou deslizou), ou
- o **robô realmente curveu/girou** e o BNO em alguns casos subestima (fusão com magnetômetro, atraso).

Os runs que “foram na metade do caminho para esquerda ou direita” costumam ser exatamente os de **|odometria| grande** (e muitas vezes BNO deriva pequena).

---

## Conclusões

1. **Runs claramente desorientados (curva forte para um lado):**  
   **1545** (-132°), **1546** (-111°), **1548** (-207°), **1556** (-53°), **1557** (-175°).  
   Todos com odometria **negativa** (tendência a ir para a **esquerda**). Em 4 deles o BNO mostra deriva pequena (< 1°), ou seja, grande divergência odom vs BNO.

2. **Os “3 testes” que você citou** que foram para a metade do caminho para esquerda/direita batem com parte desses: por exemplo 1545, 1548 e 1557 (três dos piores em |odom|). O 1546 e 1556 completam o grupo dos 5 piores.

3. **Runs bons ou aceitáveis (odom próximo de 0 ou moderado):**  
   1245 (-3,5°), 1544 (+1,8°), 1550 (-14°), 1552 (-1,8°), 1555 (~0°), 1559 (+21°).  
   Em 1559 a odometria +21° indica curva para a **direita** (único run com odom positivo alto nos dados).

4. **Padrão:**  
   - Vários runs **estáveis** (odom entre ~-15° e +5°, BNO deriva pequena).  
   - Vários runs com **odom muito negativo** (robô ou odometria “virando” para a esquerda).  
   - **Um run** (1559) com odom **positivo** (+21°, curva para a direita).

5. **Recomendações:**  
   - Continuar anotando **piso** e **bateria** nos runs desorientados (1545–1548 e 1556–1557 estão próximos no tempo; ver se há fator comum).  
   - Testar **TPS mais baixo** (menos patinação) ou **superfície mais aderente**.  
   - Para navegação futura, considerar **confiar mais no BNO** quando |odom| for muito grande (possível correção ou fusão odom + BNO).

---

*Gerado a partir dos CSV em `data/linha_reta_20260304_*.csv`.*
