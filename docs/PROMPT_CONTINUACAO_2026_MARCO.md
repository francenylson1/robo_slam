# Prompt de continuidade do projeto – Março 2026

Use este arquivo ao iniciar um **novo chat** para dar sequência ao projeto sem perder o que já foi feito. Cole ou anexe este documento e indique o próximo passo desejado.

---

## 1. Contexto do projeto

- **Projeto:** Robô Garçom Autônomo – navegação em mapa, POIs, áreas proibidas, pathfinding A*.
- **Stack:** Python 3, PyQt5, SQLite, Raspberry Pi 4 (4 GB), motores via GPIO, **IMU BNO08x** (I2C), futuramente RPLidar C1.
- **Referência de contexto inicial:** `docs/PROJETO Robô Garçom Autônomo.md`, `docs/PROMPT_CONTINUACAO_BNO_E_INTEGRACAO_2026.md`.
- **Estrutura de desenvolvimento:** (1) desenvolvimento no **desktop**; (2) **commit e push** para o Git após alterações; (3) na **Raspberry Pi**: `git pull` para testar fisicamente. **Sempre** fazer commit/push quando houver mudanças relevantes para poder atualizar a Raspberry.

---

## 2. Ambiente e repositório

- **Branch de trabalho atual:** `robo_slam_2026_1_bno_com_odometria`.
- **Repositório:** GitHub; fluxo: desktop → commit → push; Raspberry → `git pull`.
- **Checkpoint disponível:** tag `checkpoint-antes-fase1-bno-retas` (base só odometria, antes da Fase 1). Ver `docs/CHECKPOINT_ANTES_FASE1.md`.

---

## 3. O que já está funcionando (estado atual)

- **Navegação com mapa PGM:** carregamento de mapa, POIs, áreas proibidas, planejamento A*, navegação até POI.
- **Pose:** odometria (ticks) + **BNO08x** integrado no navegador conforme **Fase 1** (BNO só nas retas).
- **Comportamento no POI:** robô vai até o POI e **para sem giro** (regra “só ida” em `_stable_final_approach`: distância < 25 cm por ≥ 0,5 s → considera chegada).
- **Correção de rumo BNO:** aplicada **sempre que há avanço** (v > 0) em `_move_towards_target` e `_stable_final_approach`; referência de yaw limpa em curvas fortes (angle_error > 45°). Fórmula: `left = base_tps - corr`, `right = base_tps + corr` com ganhos do config. **Nota:** tentativa de aplicar correção BNO “só em trechos retos” (in_straight) causou caos na saída da base (odometria nas curvas errava e o controlador mandava comandos errados); foi revertida.
- **Fase 1 – BNO só nas retas (pose):** em `_update_pose_with_odometry`, o **ângulo** usa BNO apenas quando `|delta_angle_deg| < STRAIGHT_ANGLE_THRESHOLD_DEG` (3°), ou seja, em trechos “reta”; em giros usa só odometria. Config: `USE_BNO_IN_NAVIGATION = True`, `USE_BNO_ON_STRAIGHTS_ONLY = True`, `STRAIGHT_ANGLE_THRESHOLD_DEG = 3.0`.
- **Afinação do desvio:** leve desvio para a direita reduzido com `BNO_STRAIGHT_KP = 1.4` e doc `docs/AFINACAO_DESVIO_NAVEGACAO.md` (KP, INVERT, `LEFT_MOTOR_CORRECTION_FACTOR` no `robot_motor_controller.py`). Ajuste fino (linhas retas, curvas, desvios) fica para depois.
- **BNO init:** único em `tools/bno08x_init.py` com `do_reset_cycle=False`, RST HIGH, warm-up, patch 0x7B; navegador chama esse init. Suíte de testes isolada: `tests/teste_bno_suite.py` (linha reta + giros 45/90/180/360°, correção BNO; referência de comportamento correto).

---

## 4. Fases do roadmap (odometria + BNO gradual)

Conforme `docs/ESTRATEGIA_ODOMETRIA_E_BNO_GRADATIVO.md`:

| # | Fase | Status | Descrição breve |
|---|------|--------|------------------|
| **1** | **BNO só nas retas** | **CONCLUÍDA** | Critério “reta”: \|Δθ\| < limiar (3°). Em retas: ângulo da pose usa BNO; correção de rumo BNO aplicada ao avançar. Em giros: só odometria. Navegação estável; POI sem giro; desvio à direita atenuado (afinação posterior). |
| **2** | **BNO nos giros** | **PENDENTE** | Durante o giro: ângulo só odometria. Ao terminar o giro: correção única do ângulo com BNO (ex.: como em `teste_bno_suite.py --use-bno-turn`). |
| **3** | **Localização no mapa PGM** | **PENDENTE** | Usar mapa (e eventualmente LIDAR) para corrigir pose (x, y, θ) no mapa; navegação mais confiável a mesas/POIs. |
| **4** | **Ajustes** | **PENDENTE** | Ajuste fino de: linhas retas, curvas, desvios de obstáculos ou áreas proibidas (parte de desvio/evitação ainda não implementada). Inclui afinagem de BNO e, se aplicável, localização. |

---

## 5. Arquivos e pastas importantes

| O quê | Onde |
|------|------|
| Config (ganhos BNO, flags Fase 1, geometria) | `src/core/config.py` |
| Navegador (pose, correção BNO, POI sem giro, waypoints) | `src/core/robot_navigator.py` |
| Motores (PID, fatores E/D deriva) | `src/core/robot_motor_controller.py` |
| Aplicação principal (mapa, POIs, áreas, UI) | `src/main.py` |
| Init BNO (único ponto de criação do BNO) | `tools/bno08x_init.py` |
| Teste BNO contínuo | `tools/bno08x_test.py` |
| Suíte BNO (linha reta + giros; referência) | `tests/teste_bno_suite.py` |
| Estratégia fases 1–4 | `docs/ESTRATEGIA_ODOMETRIA_E_BNO_GRADATIVO.md` |
| Afinação desvio (KP, INVERT, fator motor) | `docs/AFINACAO_DESVIO_NAVEGACAO.md` |
| Integração BNO no navegador (Fase 2 doc) | `docs/FASE2_INTEGRACAO_BNO_NAVEGADOR.md` |
| Checklist integração BNO (yaw_ref, primeira leitura) | `docs/REVISAO_BNO_LINHA_RETA.md` |
| Checkpoint antes Fase 1 | `docs/CHECKPOINT_ANTES_FASE1.md` |
| Prompt anterior BNO/integração | `docs/PROMPT_CONTINUACAO_BNO_E_INTEGRACAO_2026.md` |

---

## 6. Comportamentos críticos (não regredir)

- **POI “só ida”:** em `_stable_final_approach`, quando **não** é retorno à base e distância < 25 cm por ≥ 0,5 s → considera chegada e para **sem giro**. Não exigir alinhamento angular para parar no POI.
- **Correção BNO ao avançar:** aplicar `_apply_bno_straight_correction` sempre que `linear_speed_ms > 0` (e limpar `_bno_yaw_ref` quando `angle_error > 45°`). Não restringir correção “só em trechos retos” no controle dos motores (causou caos na saída da base).
- **Init BNO:** usar apenas `tools.bno08x_init.init_bno(do_reset_cycle=False)`; primeira leitura válida antes de definir `yaw_ref` (timeout em config). Ver checklist em `docs/REVISAO_BNO_LINHA_RETA.md` se for mexer em BNO no navegador.

---

## 7. Próximos passos sugeridos (para o novo chat)

- **Fase 2:** Implementar correção de giro com BNO ao **final** do giro (odometria para parar o giro; depois correção fina até ângulo desejado com BNO), inspirado em `teste_bno_suite.py --use-bno-turn`.
- **Fase 3:** Desenhar/implementar localização no mapa PGM (e eventualmente integração com LIDAR).
- **Fase 4:** Ajustes finos de linhas retas, curvas e desvios (obstáculos/áreas proibidas quando implementados); refinar `BNO_STRAIGHT_KP`, `LEFT_MOTOR_CORRECTION_FACTOR` conforme `docs/AFINACAO_DESVIO_NAVEGACAO.md`.

---

## 8. Como usar este prompt em um novo chat

1. Abra um **novo chat** no Cursor.
2. Cole ou anexe este arquivo: `docs/PROMPT_CONTINUACAO_2026_MARCO.md`.
3. Escreva algo como: *“Quero continuar o projeto de navegação do robô. Use o prompt anexado como contexto. Próximo passo: [Fase 2 – BNO nos giros / Fase 3 – localização no mapa PGM / Fase 4 – ajustes finos / ou tarefa específica].”*
4. Lembre: após alterações, fazer **commit e push** e informar o usuário para atualizar a Raspberry com `git pull`.

---

*Documento gerado para continuidade em novo chat. Reflete o estado após Fase 1 concluída (BNO só nas retas), POI sem giro estável, e afinagem inicial do desvio. Fases 2, 3 e 4 pendentes.*
