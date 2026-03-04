# Prompt de continuidade – BNO08x, integração e RPLidar C1

Use este texto ao iniciar um **novo chat** para dar sequência ao projeto sem perder o que já foi feito.

---

## Contexto do projeto

- **Projeto:** Robô Garçom Autônomo (navegação em mapa, POIs, áreas proibidas).
- **Ambiente:** Desenvolvimento no **desktop**; alterações vão para o **Git (nuvem)**; testes físicos na **Raspberry Pi**. Sempre que houver mudanças: commit + push no desktop e `git pull` na Raspberry.
- **Repositório:** GitHub; branch principal de trabalho até agora: `robo_slam_2026_1_bno_ok`. Branch de checkpoint criada: `robo_slam_2026_1_bno_antes_da_integracao_com_odometria_testes`.

---

## O que já está funcionando

1. **Navegação só odometria + mapa (main.py)**  
   - Seleção de mapa, POIs, áreas proibidas, planejamento de caminho (A*).  
   - Posição e ângulo apenas por odometria (ticks).  
   - Navegação estável e “quase perfeita” nas palavras do usuário; **não usa IMU BNO08x**.

2. **IMU BNO08x – testes isolados**  
   - Init único em `tools/bno08x_init.py`: **RST em HIGH** (sem ciclo LOW→HIGH por padrão, `do_reset_cycle=False`), I2C, ACCEL+GYRO+ROTATION_VECTOR, **warm-up** de quaternion após enable das features, **patch 0x7B** ao carregar o módulo. Alinhado ao `tools/bno08x_test.py` que funciona na Raspberry.  
   - Suíte de testes: `tests/teste_bno_suite.py` (linha reta com correção BNO + giros **esquerda e direita** 45°, 90°, 180°, 360°; opção `--use-bno-turn` para correção fina do giro). **Antes de iniciar a linha reta**, o teste **espera até 1,5 s** pela primeira leitura válida de yaw para definir `yaw_ref` (evita “BNO sem leitura” e desvio).  
   - Ganhos em `src/core/config.py`: `BNO_STRAIGHT_KP`, `BNO_STRAIGHT_MAX_CORRECTION_TPS`, `BNO_STRAIGHT_INVERT_CORRECTION = True`, `TURN_TPS_DEFAULT`.  
   - **Resultado atual:** linha reta com BNO **funcionando** (correção ativa com referência e leituras válidas); variação em torno do POI ~5 cm; preparado para mais testes e depois integração.  
   - Outros scripts que usam BNO: `tools/robot_teleop_bno.py`, `tools/robot_command_menu.py`, `tools/sync_test_motors_bno.py` (todos usam `bno08x_init` com `do_reset_cycle=False`).

3. **Documentação**  
   - `docs/NAVEGACAO_ODOMETRIA_VS_IMU_BNO.md`: odometria vs IMU; sugestão de integrar BNO no navegador.  
   - **`docs/REVISAO_BNO_LINHA_RETA.md`**: por que a linha reta desviava para a esquerda (primeira leitura `None`, sem referência); warm-up e espera da primeira leitura; **checklist para integrar BNO no sistema** (obrigatório ler antes da Fase 2).

---

## Checklist – O que foi feito

- [x] Configuração BNO08x (I2C, RST, endereço) em `src/core/config.py`.
- [x] Ganhos de correção BNO no config: `BNO_STRAIGHT_KP`, `BNO_STRAIGHT_MAX_CORRECTION_TPS`, `BNO_STRAIGHT_INVERT_CORRECTION`, `TURN_TPS_DEFAULT`.
- [x] Módulo único de init BNO: `tools/bno08x_init.py` – RST HIGH apenas (`do_reset_cycle=False`), patch 0x7B no load, warm-up de quaternion após enable das features; alinhado ao `bno08x_test.py`.
- [x] Suíte de testes BNO: `tests/teste_bno_suite.py` (linha reta + giros esq/dir 45/90/180/360°; `--direction left|right|both`, `--use-bno-turn`, `--turn-tolerance`; `--no-turns`, `--calibrate`, `--duration`, `--angles`, `--csv`). **Espera primeira leitura válida (até 1,5 s)** antes de iniciar linha reta.
- [x] Correção de rumo em linha reta com sentido correto (`BNO_STRAIGHT_INVERT_CORRECTION = True`).
- [x] Teleop e menu usando config e `bno08x_init(do_reset_cycle=False)`: `robot_teleop_bno.py`, `robot_command_menu.py`, `sync_test_motors_bno.py`.
- [x] Documentação: `docs/NAVEGACAO_ODOMETRIA_VS_IMU_BNO.md`, **`docs/REVISAO_BNO_LINHA_RETA.md`** (causa do desvio + checklist de integração).
- [x] Branch de checkpoint: `robo_slam_2026_1_bno_antes_da_integracao_com_odometria_testes`.

---

## Checklist – O que falta fazer (em ordem sugerida)

### Fase 1 – Testes adicionais com BNO isolado (antes de integrar)

- [x] Suíte com **giros à esquerda e à direita**: `--direction left`, `--direction right`, `--direction both`; ângulos 45°, 90°, 180°, 360°.
- [x] Opção **correção fina de giro por BNO**: `--use-bno-turn` e `--turn-tolerance` (ex.: 1.5°).
- [x] Documentação dos procedimentos: **`docs/FASE1_TESTES_NAVEGACAO.md`** (comandos, checklist, parâmetros de ajuste).
- [ ] Rodar mais testes na Raspberry com **giros** (esquerda e direita); anotar erros odometria vs BNO.
- [ ] Testar `--calibrate`, `--duration`, `--angles`, `--csv`; ajustar `BNO_STRAIGHT_KP` / `BNO_STRAIGHT_MAX_CORRECTION_TPS` se necessário para reduzir os ~5 cm de variação.
- [ ] (Opcional) Ajustar `TURN_TPS_DEFAULT` ou fatores de odometria com base nos CSV.

### Fase 2 – Integração odometria + mapa + IMU BNO08x

**Antes de integrar**, seguir o **checklist de integração BNO** abaixo (resumo de `docs/REVISAO_BNO_LINHA_RETA.md`) para não reintroduzir o bug de “linha reta desviando” (falta de referência/leituras válidas).

- [ ] Integrar BNO ao fluxo do **main.py** / navegador: usar BNO para melhorar a estimativa de **ângulo** (ou pose) em vez de só odometria (ex.: fusão simples ou complementar filter).
- [ ] Manter compatibilidade com navegação atual (mapa, POIs, áreas proibidas); validar que a navegação com BNO não regride em relação à atual.
- [ ] Testar criação de POI, áreas proibidas e rotas com a nova integração.

#### Checklist para integrar navegação BNO no sistema (obrigatório na Fase 2)

Ao levar o BNO do ambiente isolado (teste_bno_suite, teleop, menu) para o navegador/main.py, **sempre** garantir:

| # | Regra | Detalhe |
|---|--------|---------|
| 1 | **Init BNO** | Usar só `tools.bno08x_init.init_bno(do_reset_cycle=False)`. O init já faz retry (até 2 tentativas) e warm-up. Não instanciar `BNO08X_I2C` direto. |
| 2 | **Primeira leitura antes de mover** | Antes de “linha reta com correção BNO”, **não** confiar numa única chamada a `get_bno_yaw()`. Esperar leitura válida (timeout BNO_FIRST_READ_TIMEOUT em config (ex. 2,5 s), polling ~50 ms) e só então definir `yaw_ref`. |
| 3 | **Quando não há leitura no laço** | Se `get_bno_yaw()` retorna `None` → usar (base_tps, base_tps). **Não** usar 0° como correção nem valor antigo sem marcar como não confiável. |
| 4 | **Referência (yaw_ref)** | `yaw_ref` = **sempre** leitura real do BNO no momento “rumo a manter”. **Nunca** usar 0° por padrão quando não houve leitura. |
| 5 | **Ganhos e invert** | Usar `config.py`: `BNO_STRAIGHT_KP`, `BNO_STRAIGHT_MAX_CORRECTION_TPS`, `BNO_STRAIGHT_INVERT_CORRECTION`. Não trocar invert sem testar linha reta. |
| 6 | **Patch 0x7B** | Já aplicado em `bno08x_init` ao importar. Qualquer uso de BNO deve passar pelo init (não criar BNO em outro módulo). |
| 7 | **Debug** | Nunca `BNO08X_I2C(..., debug=True)` em produção; atrasa o laço e prejudica leituras. |
| 8 | **Referência de comportamento** | Se a linha reta falhar na integração, comparar com `teste_bno_suite.py` e `bno08x_test.py` (comportamento correto isolado). |

**Resumo:** Sempre obter **uma leitura válida** antes de definir o rumo de referência; **nunca assumir 0°** quando não houve leitura; usar só o init centralizado e os ganhos do config. Detalhes e causa do bug original em `docs/REVISAO_BNO_LINHA_RETA.md`.

### Fase 3 – Sensor C1 RPLidar (evitar obstáculos)

- [ ] Implementar suporte ao sensor **C1 RPLidar** (leitura de scans, integração com o stack atual).
- [ ] Usar dados do RPLidar para **evitar obstáculos** em tempo real (desvios ou paradas) sem desfazer o que já funciona em odometria + mapa (+ BNO após integração).
- [ ] Documentar e testar na Raspberry com o hardware disponível.

---

## Branches e fluxo Git

- **`robo_slam_2026_1_bno_ok`** – branch onde foi feito o trabalho atual de BNO e testes; já em uso na Raspberry.
- **`robo_slam_2026_1_bno_antes_da_integracao_com_odometria_testes`** – branch de **checkpoint** criada a partir do estado atual; representa “BNO funcionando bem em testes isolados, antes de integrar com odometria/mapa no main.py”.
- **Workflow:** desenvolvimento no desktop → commit → push; na Raspberry: `git pull origin <branch>` para testar. Sempre que fizer alterações relevantes, fazer commit e push para não perder nada.

### Conferir se a Raspberry está na mesma versão do desktop

Use o **hash do último commit** como referência.

**No desktop** (depois do push):
```bash
cd /caminho/do/robo_slam
git log -1 --oneline
# Exemplo: a1b2c3d Fase 1: retry BNO + timeout primeira leitura
```
Anote o hash (ex.: `a1b2c3d`) ou a linha inteira.

**Na Raspberry** (depois do pull):
```bash
cd ~/robo_slam   # ou o caminho do seu clone
git pull origin robo_slam_2026_1_bno_ok
git log -1 --oneline
```
Se o hash e a mensagem forem **iguais** aos do desktop, a Raspberry está na mesma versão.

**Comando direto para comparar:**  
Desktop: `git rev-parse HEAD`  
Raspberry: `git rev-parse HEAD`  
Se os dois retornarem o mesmo hash (ex.: `a1b2c3d4e5f6...`), as versões são iguais.

---

## Arquivos e pastas importantes

| O quê | Onde |
|------|------|
| Config geral e ganhos BNO | `src/core/config.py` |
| Init BNO (referência: bno08x_test) | `tools/bno08x_init.py` |
| Teste BNO standalone | `tools/bno08x_test.py` |
| Suíte de testes BNO (linha reta + giros esq/dir + correção BNO) | `tests/teste_bno_suite.py` |
| Guia Fase 1 – testes linha reta e giros | `docs/FASE1_TESTES_NAVEGACAO.md` |
| Análise logs linha reta (odom vs BNO) | `docs/FASE1_ANALISE_LOGS_LINHA_RETA.md` |
| Sequência mínima de testes + template anotação | `docs/FASE1_SEQUENCIA_TESTES_E_TEMPLATE.md` |
| Teleop com correção BNO | `tools/robot_teleop_bno.py` |
| Menu de comandos | `tools/robot_command_menu.py` |
| Teste sincronia motores+BNO | `tools/sync_test_motors_bno.py` |
| Navegador (odometria + mapa; ainda sem BNO) | `src/core/robot_navigator.py` |
| Controlador de motores (PID, perfis) | `src/core/robot_motor_controller.py` |
| Aplicação principal (mapa, POIs, áreas) | `src/main.py` |
| Doc. odometria vs IMU | `docs/NAVEGACAO_ODOMETRIA_VS_IMU_BNO.md` |
| Doc. BNO linha reta + checklist integração | `docs/REVISAO_BNO_LINHA_RETA.md` |

---

## Como usar este prompt em um novo chat

1. Abra um **novo chat** no Cursor.
2. Cole ou anexe este arquivo: `docs/PROMPT_CONTINUACAO_BNO_E_INTEGRACAO_2026.md`.
3. Diga, por exemplo: “Quero continuar o projeto de navegação do robô. Use o prompt anexado como contexto. Próximo passo: [descreva o que quer fazer, ex.: mais testes com giros (--turns), ou começar a integração BNO no main.py seguindo o checklist, ou esboço do RPLidar C1].”
4. **Se for integrar BNO no sistema (Fase 2):** peça ao assistente para seguir o “Checklist para integrar navegação BNO no sistema” deste documento e consultar `docs/REVISAO_BNO_LINHA_RETA.md` quando relevante.
5. Trabalhe na branch que fizer sentido: `robo_slam_2026_1_bno_ok` para evoluir; ou `robo_slam_2026_1_bno_antes_da_integracao_com_odometria_testes` para manter um ponto de restauração antes da integração.

---

*Documento gerado para continuidade do projeto em novo chat. Última atualização: BNO linha reta estável (warm-up + espera 1ª leitura); checklist de integração incluído; pronto para Fase 1 (mais testes) ou Fase 2 (integração) com regras claras.*
