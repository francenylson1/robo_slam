# Prompt de Continuação — Projeto Robô SLAM 2026 (Fase 2 — Lidar C1)

**Data:** Março 2026  
**Objetivo:** Permitir abrir uma nova conversa e dar continuidade ao projeto sem perder contexto.

---

## 1. Visão Geral do Projeto

Projeto de robô autônomo para aplicação educacional (alunos) e exploração comercial. Desenvolvimento em **Python puro, sem ROS**. Hardware: Raspberry Pi 4 (4 GB), em migração para Pi 5 (8 GB).

---

## 2. Fases do Projeto

| Fase | Nome | Status | Descrição |
|------|------|--------|-----------|
| 1 | Semi-autônoma (Odometria) | ✅ **Concluída e validada** | Navegação ida/volta com odometria + CTE. Áreas proibidas ativas. |
| 2 | Lidar C1 (Em andamento) | 🔄 Teste isolado OK | Integração do RP Lidar C1 para detecção de obstáculos e futura localização. |
| 3 | Localização (AMCL-like) | 📋 Planejada | Usar mapa Aurora + C1 para correção de pose. |
| 4 | SLAM completo | 📋 Planejada | Navegação 15–25 m, máxima autonomia. |

---

## 3. Versões Estáveis (para uso com alunos)

| Tag/Branch | Uso | Descrição |
|------------|-----|-----------|
| **`v1.0-semi-autonoma`** | Produção com alunos | Tag Git imutável. Navegação ida/volta, sem BNO, sem C1. Áreas proibidas ativas. Recuperar: `git checkout v1.0-semi-autonoma` |
| **`robo_slam_2026_ida_volta`** | Desenvolvimento | Branch com ida/volta e "Definir nova partida" com seleção de ângulo real. |
| **`robo_slam_2026_lidar_c1`** | Fase 2 | Branch atual para integração do C1. |

---

## 4. O que já está funcionando

### 4.1 Navegação
- Ida até POI (ponto de interesse) com planejamento de caminho.
- Pausa configurável no destino (`ARRIVAL_PAUSE_TIME = 5.0` s).
- Retorno automático à base.
- Ajuste de ângulo final (270°).
- Watchdog de navegação (timeouts: `NAVIGATION_MAX_DURATION_S`, `RETURN_MAX_DURATION_S`).
- Evitação de áreas proibidas (PathFinder A*, quando há áreas no mapa).
- CTE (Cross-Track Error) para manter o robô na trajetória.
- "Definir nova partida" com escolha de ângulo real (0°, 90°, 180°, 270° ou odometria) para sincronizar robô virtual e físico.

### 4.2 Interface
- Controles manuais: frente/trás (press & hold), giros (slider 15°–180°).
- Mapa PGM carregado de `c1/c1_sala_maker/mapa-03122025_final_90`.
- POIs no mapa 54: `x1-2026` até `x6-2026`, `x-2026`.
- Áreas proibidas: adicionar, excluir, exportar/importar JSON.

### 4.3 C1 — Teste isolado
- Script: `tools/teste_c1_isolado.py` (usa biblioteca **rplidarc1**, não rplidar genérico).
- Porta: `/dev/ttyUSB0`, baudrate: **460800** (obrigatório para C1).
- Comando: `python tools/teste_c1_isolado.py --port /dev/ttyUSB0`.
- Resultado: lê varreduras 360°, ~500 pontos por rotação, obstáculo mais próximo ~96–98 mm (corpo do robô ou alcance mínimo).

---

## 5. Variáveis de calibração dos motores

| Arquivo | Variável | Valor atual | Função |
|---------|----------|-------------|--------|
| `src/core/robot_motor_controller.py` | `LEFT_MOTOR_CORRECTION_FACTOR` | 0.96 | Correção do motor esquerdo para reduzir desvio à direita. Ajustar (0.95–0.97) se o robô tender a desviar. |
| `src/core/robot_motor_controller.py` | `RIGHT_MOTOR_CORRECTION_FACTOR` | 1.0 | Motor direito (referência). |
| `src/core/config.py` | `ROBOT_SPEED`, `ROBOT_MAX_SPEED` | 0.30 | Velocidade em m/s. |
| `src/core/config.py` | `FORBIDDEN_AREA_INFLATION_RADIUS` | 0.20 | Margem (m) ao redor de áreas proibidas. |

**BNO08x:** Desativado (`USE_BNO_IN_NAVIGATION = False`) — causava desvio sistemático para a direita. Uso futuro previsto: fusão com C1/localização.

---

## 6. Plano de testes do C1 — Próximas etapas

O C1 está **apenas funcionando no teste isolado**. Próximos passos para entendê-lo e integrá-lo:

### Etapa 1 — Filtrar por ângulo
- **Objetivo:** Considerar apenas pontos "à frente" do robô.
- **Implementação sugerida:** Criar opção no `teste_c1_isolado.py` (ex.: `--front-deg 60`) para exibir só pontos em uma faixa angular (ex.: 330°–30° = 60° central).
- **Teste:** Rodar com diferentes faixas e conferir se os valores fazem sentido (paredes à frente, laterais, etc.).

### Etapa 2 — Definir distâncias mínimas
- **Objetivo:** Definir limiares de parada (ex.: 0.35 m) e alerta (ex.: 0.50 m).
- **Implementação sugerida:** Parâmetros `--min-stop 0.35` e `--min-warn 0.50` no script de teste; exibir alerta quando obstáculo mais próximo na faixa frontal for menor que o limite.
- **Teste:** Aproximar objeto à frente e verificar se o script indica corretamente quando está abaixo dos limites.

### Etapa 3 — Integrar ao fluxo de navegação
- **Objetivo:** Durante a navegação, ler o C1 em um loop/thread assíncrona e parar os motores se obstáculo &lt; limite na frente.
- **Implementação sugerida:**
  - Módulo `src/core/lidar_c1_reader.py` para encapsular leitura e decisão (obstáculo próximo?).
  - Chamar de `robot_navigator.py` ou `robot_motor_controller.py` antes de aplicar velocidades.
  - Parâmetro em `config.py`: `LIDAR_OBSTACLE_MIN_DISTANCE = 0.35` (parar se &lt; 35 cm na frente).
- **Teste:** Colocar obstáculo no caminho durante navegação e confirmar parada automática.

---

## 7. Estrutura de arquivos relevante

```
robo_slam/
├── src/
│   ├── main.py                 # Ponto de entrada
│   ├── core/
│   │   ├── config.py           # Configurações globais
│   │   ├── robot_motor_controller.py  # Motores + LEFT_MOTOR_CORRECTION_FACTOR
│   │   ├── robot_navigator.py  # Navegação, path, CTE
│   │   ├── path_finder.py      # A* e áreas proibidas
│   │   └── map_manager.py      # Banco SQLite (POIs, áreas, mapas)
│   └── interfaces/
│       ├── main_window.py      # UI PyQt5
│       └── map_widget.py       # Desenho do mapa e robô
├── tools/
│   ├── teste_c1_isolado.py      # Teste do C1 (rplidarc1)
│   └── bno08x_init.py          # BNO (desativado na navegação)
├── data/
│   └── robot.db                # SQLite: mapas, POIs, áreas proibidas
├── docs/
│   ├── FASE2_LIDAR_C1.md       # Doc da Fase 2
│   └── PROMPT_CONTINUACAO_FASE2_C1_2026.md  # Este prompt
└── requirements.txt            # Inclui rplidarc1>=0.1.3
```

---

## 8. Banco de dados e mapa

- **Mapa ativo:** `mapa-03122025_final_90` (ID 54).
- **Dimensões:** 6.55 m × 12.55 m.
- **POIs:** x1-2026 a x6-2026, x-2026.
- **Resolução:** 0.05 m/pixel (PGM).

---

## 9. Como retomar a conversa

Copie o texto abaixo ao abrir uma nova conversa:

---

**Início do prompt para nova conversa**

Sou desenvolvedor do projeto Robô SLAM 2026. Preciso dar continuidade à Fase 2 (integração do RP Lidar C1). O arquivo `docs/PROMPT_CONTINUACAO_FASE2_C1_2026.md` contém o contexto completo do projeto, fases, o que já funciona, versões estáveis e o plano de testes do C1.

**Estado atual:** O C1 está funcionando no teste isolado (`tools/teste_c1_isolado.py` com rplidarc1, 460800 baud). Próximas etapas planejadas:

1. **Filtrar por ângulo** — Testar no script isolado exibir apenas pontos da faixa frontal (ex.: 60°).
2. **Definir distâncias mínimas** — Parâmetros de parada (0.35 m) e alerta (0.50 m) no teste.
3. **Integrar ao fluxo de navegação** — Módulo de leitura do C1 + parada automática quando obstáculo &lt; limite na frente.

Preciso [descreva aqui a tarefa específica que deseja realizar].

**Fim do prompt para nova conversa**

---

## 10. Observações técnicas

- **Raspberry Pi:** `git pull` pode exigir `git stash` ou `git checkout -- data/robot.db` se houver alterações locais.
- **C1:** Usar sempre `rplidarc1` (não `rplidar`); o C1 usa protocolo diferente e retorna "Descriptor length mismatch" com rplidar genérico.
- **Python:** rplidarc1 exige Python 3.10+ (TaskGroup); Raspberry Pi com Python 3.11 está OK.
- **Sincronização desktop ↔ Pi:** Commit e push no desktop; `git pull` no Pi (com stash se necessário).
