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
   - Init único em `tools/bno08x_init.py` (reset cycle + I2C + ACCEL+GYRO+ROTATION_VECTOR), alinhado ao `tools/bno08x_test.py` que funciona na Raspberry.  
   - Suíte de testes: `tests/teste_bno_suite.py` (linha reta com correção BNO + giros 45°, 90°, 180°, 360°).  
   - Ganhos centralizados em `src/core/config.py`: `BNO_STRAIGHT_KP`, `BNO_STRAIGHT_MAX_CORRECTION_TPS`, `BNO_STRAIGHT_INVERT_CORRECTION = True`, `TURN_TPS_DEFAULT`.  
   - **Resultado atual:** linha reta com BNO **melhor** que a linha reta só com odometria no main.py; variação em torno do POI de ~5 cm; ainda não perfeito, mas bem melhor.  
   - Outros scripts que usam BNO: `tools/robot_teleop_bno.py`, `tools/robot_command_menu.py`, `tools/sync_test_motors_bno.py` (todos usam `tools/bno08x_init.py`).

3. **Documentação**  
   - `docs/NAVEGACAO_ODOMETRIA_VS_IMU_BNO.md`: por que a navegação só odometria pode parecer mais precisa que o teste com IMU quando a correção estava invertida; sugestão de integrar BNO no laço do navegador (fusão odometria + BNO).

---

## Checklist – O que foi feito

- [x] Configuração BNO08x (I2C, RST, endereço) em `src/core/config.py`.
- [x] Ganhos de correção BNO no config: `BNO_STRAIGHT_KP`, `BNO_STRAIGHT_MAX_CORRECTION_TPS`, `BNO_STRAIGHT_INVERT_CORRECTION`, `TURN_TPS_DEFAULT`.
- [x] Módulo único de init BNO: `tools/bno08x_init.py` (reset cycle + mesmo procedimento do `bno08x_test.py`).
- [x] Suíte de testes BNO: `tests/teste_bno_suite.py` (linha reta + giros 45/90/180/360°; opções `--no-turns`, `--calibrate`, `--duration`, `--angles`, `--csv`).
- [x] Correção de rumo em linha reta com sentido correto (`BNO_STRAIGHT_INVERT_CORRECTION = True`).
- [x] Teleop e menu usando config e `bno08x_init`: `robot_teleop_bno.py`, `robot_command_menu.py`, `sync_test_motors_bno.py`.
- [x] Documentação: `docs/NAVEGACAO_ODOMETRIA_VS_IMU_BNO.md`.
- [x] Branch de checkpoint: `robo_slam_2026_1_bno_antes_da_integracao_com_odometria_testes`.

---

## Checklist – O que falta fazer (em ordem sugerida)

### Fase 1 – Testes adicionais com BNO isolado (antes de integrar)

- [ ] Rodar mais testes com **giros** (`teste_bno_suite.py` sem `--no-turns`): 45°, 90°, 180°, 360°; anotar erros de odometria vs BNO.
- [ ] Testar outras opções da suíte: `--calibrate`, `--duration`, `--angles`, `--csv`; ajustar `BNO_STRAIGHT_KP` / `BNO_STRAIGHT_MAX_CORRECTION_TPS` se necessário para reduzir os ~5 cm de variação.
- [ ] (Opcional) Ajuste fino de giros (usar BNO como feedback para correção até o ângulo desejado).

### Fase 2 – Integração odometria + mapa + IMU BNO08x

- [ ] Integrar BNO ao fluxo do **main.py** / navegador: usar BNO para melhorar a estimativa de **ângulo** (ou pose) em vez de só odometria (ex.: fusão simples ou complementar filter).
- [ ] Manter compatibilidade com navegação atual (mapa, POIs, áreas proibidas); validar que a navegação com BNO não regride em relação à atual.
- [ ] Testar criação de POI, áreas proibidas e rotas com a nova integração.

### Fase 3 – Sensor C1 RPLidar (evitar obstáculos)

- [ ] Implementar suporte ao sensor **C1 RPLidar** (leitura de scans, integração com o stack atual).
- [ ] Usar dados do RPLidar para **evitar obstáculos** em tempo real (desvios ou paradas) sem desfazer o que já funciona em odometria + mapa (+ BNO após integração).
- [ ] Documentar e testar na Raspberry com o hardware disponível.

---

## Branches e fluxo Git

- **`robo_slam_2026_1_bno_ok`** – branch onde foi feito o trabalho atual de BNO e testes; já em uso na Raspberry.
- **`robo_slam_2026_1_bno_antes_da_integracao_com_odometria_testes`** – branch de **checkpoint** criada a partir do estado atual; representa “BNO funcionando bem em testes isolados, antes de integrar com odometria/mapa no main.py”.
- **Workflow:** desenvolvimento no desktop → commit → push; na Raspberry: `git pull origin <branch>` para testar. Sempre que fizer alterações relevantes, fazer commit e push para não perder nada.

---

## Arquivos e pastas importantes

| O quê | Onde |
|------|------|
| Config geral e ganhos BNO | `src/core/config.py` |
| Init BNO (referência: bno08x_test) | `tools/bno08x_init.py` |
| Teste BNO standalone | `tools/bno08x_test.py` |
| Suíte de testes BNO (linha reta + giros) | `tests/teste_bno_suite.py` |
| Teleop com correção BNO | `tools/robot_teleop_bno.py` |
| Menu de comandos | `tools/robot_command_menu.py` |
| Teste sincronia motores+BNO | `tools/sync_test_motors_bno.py` |
| Navegador (odometria + mapa; ainda sem BNO) | `src/core/robot_navigator.py` |
| Controlador de motores (PID, perfis) | `src/core/robot_motor_controller.py` |
| Aplicação principal (mapa, POIs, áreas) | `src/main.py` |
| Doc. odometria vs IMU | `docs/NAVEGACAO_ODOMETRIA_VS_IMU_BNO.md` |

---

## Como usar este prompt em um novo chat

1. Abra um **novo chat** no Cursor.
2. Cole ou anexe este arquivo: `docs/PROMPT_CONTINUACAO_BNO_E_INTEGRACAO_2026.md`.
3. Diga, por exemplo: “Quero continuar o projeto de navegação do robô. Use o prompt anexado como contexto. Próximo passo: [descreva o que quer fazer, ex.: mais testes com --turns, ou começar a integração BNO no main.py, ou esboço do RPLidar C1].”
4. Trabalhe na branch que fizer sentido: `robo_slam_2026_1_bno_ok` para evoluir; ou `robo_slam_2026_1_bno_antes_da_integracao_com_odometria_testes` para manter um ponto de restauração antes da integração.

---

*Documento gerado para continuidade do projeto em novo chat. Última atualização: checkpoint antes da integração odometria + mapa + IMU.*
