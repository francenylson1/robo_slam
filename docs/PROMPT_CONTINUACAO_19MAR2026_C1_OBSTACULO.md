# Prompt de Continuação — Projeto Robô SLAM 2026 (C1 Obstáculo OK)

**Data:** 19 de março de 2026  
**Branch ativa:** `robo_slam_2026_C1_obstaculo`  
**Objetivo:** Permitir abrir uma nova conversa e dar continuidade ao projeto sem perder contexto.

---

## 1. Situação atual do projeto

O **RP Lidar C1 está funcionando corretamente** como parada de emergência: detecta obstáculos à frente (lixeira, pessoa, mesa) e para os motores de forma estável. A navegação ida continua operacional, com parada automática quando obstáculo < 85 cm no cone frontal.

### O que foi resolvido (Mar 2026)
- **rplidarc1** tinha parada inconsistente (às vezes parava, às vezes atropelava)
- Migração para **pyrplidarsdk** (SDK oficial SLAMTEC)
- **Bug crítico:** pyrplidarsdk retorna ângulos em **radianos** — o código tratava como graus, causando falsa detecção de obstáculo a 9 cm (corpo do robô na zona frontal)
- Correção: `math.degrees(ang)` no fluxo pyrplidarsdk
- Resultado: parada **consistente** em testes com lixeira e pessoa (várias repetições)
- **Timeout de navegação:** 45 s → 300 s (5 min); permite múltiplas paradas para usuários se servirem (ex.: garçom)
- **BNO (Fase 2b):** Desativado. Testes 19/03 (fusão e só correção) falharam: deriva, passou do POI, parada de emergência inconsistente.
- **Bug de escala do mapa (19/03/2026):** YAML dos mapas `_90` e `_270` tinha resolução pela metade (0.023904 → corrigido para 0.047808 m/px). Sala real: 6.26m × 12.00m. Posição inicial do robô atualizada para (~3.54, ~7.74) metros reais. POIs e áreas proibidas devem ser recriados pelo operador via GUI.

---

## 2. Fases concluídas e seguintes

| Fase | Nome | Status | Descrição |
|------|------|--------|-----------|
| 1 | Semi-autônoma (Odometria) | ✅ Concluída | Navegação ida/volta, odometria + CTE, áreas proibidas |
| 2a | C1 integrado (parada emergência) | ✅ Concluída | LIDAR C1 detecta obstáculo frontal, para motores |
| 2b | Correção de trajetória | 🔬 Em análise | BNO falhou em todos os modos (19/03). Nova estratégia: Abordagem C (scan matching com mapa PGM). Ver seção 11. |
| 2c | Desvio de obstáculos | 📋 Planejada | Ao se aproximar de mesa: realinhar e ir em direção ao POI (não só parar) |
| 3 | Localização (AMCL-like / Abordagem C) | 🔧 Pré-requisito: fix escala YAML ✅ | Scan matching C1 vs mapa PGM para correção de pose em tempo real |
| 4 | SLAM completo | 📋 Planejada | Navegação 15–25 m, máxima autonomia |

---

## 3. Branches e tags importantes

| Branch/Tag | Uso | Descrição |
|------------|-----|-----------|
| `robo_slam_2026_C1_obstaculo` | **Desenvolvimento atual** | C1 OK com pyrplidarsdk; checkpoint pós-validação |
| `robo_slam_2026_lidar_c1` | Histórico | Branch-mãe; mesmos commits que C1_obstaculo |
| `v1.0-semi-autonoma` | Produção | Navegação sem C1, para uso com alunos |

---

## 4. Arquivos principais e lógica

### Navegação e C1
- `src/main.py` — Ponto de entrada
- `src/core/robot_motor_controller.py` — Motores; em `set_target_speed`, chama `lidar_reader.has_obstacle()` e força (0, 0) se obstáculo < limite
- `src/core/lidar_c1_reader.py` — Leitura C1 em thread; backends `rplidarc1` e `pyrplidarsdk`; pyrplidarsdk é o principal (`LIDAR_C1_BACKEND`)

### Configuração
- `src/core/config.py`:
  - `LIDAR_C1_ENABLED = True`
  - `LIDAR_OBSTACLE_MIN_DISTANCE = 0.85` (parar se < 85 cm)
  - `LIDAR_C1_BACKEND = "pyrplidarsdk"`
  - `NAVIGATION_MAX_DURATION_S = 300` (5 min; permite múltiplas paradas para usuários se servirem)
  - `USE_BNO_IN_NAVIGATION = False` (BNO desativado; estado estável)
  - `ROBOT_INITIAL_POSITION = (3.54, 7.74)` (atualizado após correção do YAML de escala)

### Parâmetros do C1 (lidar_c1_reader.py)
- `FRONT_CENTER_DEG = 350` — Frente do robô no sensor (calibração wizard)
- `FRONT_WIDTH_DEG = 200` — Cone frontal em graus
- `PARACHOQUES_ZONE = (120, 240)` — Ignorar reflexos do corpo

### Ferramentas
- `tools/calibracao_c1_orientacao.py` — Wizard de calibração (usa rplidarc1)
- `tools/teste_c1_isolado.py` — Teste isolado do C1 (usa rplidarc1)
- `tools/c1_mapa_visual.py` — Visualização do mapa LIDAR (usa rplidarc1)

---

## 5. Biblioteca rplidarc1 — manter ou remover?

**Recomendação: MANTER** (ver `docs/ANALISE_RPLIDARC1_MANTER_OU_REMOVER_19MAR2026.md`).

- **main.py / navegação:** Usa `pyrplidarsdk` (estável)
- **Tools (calibração, teste isolado, mapa visual):** Usam `rplidarc1`; migrar exigiria refatoração
- **Fallback:** Se pyrplidarsdk falhar em algum sistema, ainda existe rplidarc1 no `lidar_c1_reader`

---

## 6. Comportamento esperado e observado (Mar 2026)

- **Parada:** Robô para quando obstáculo (lixeira, pessoa) está a menos de 85 cm na frente
- **Deriva:** Quando o robô desvia e se aproxima de uma mesa lateral, o LIDAR vê a mesa no cone frontal e para — isso é esperado (parada de segurança)
- **Próxima fase:** Lógica de desvio (realinhar e ir em direção ao POI) será posterior; hoje o sistema só **para**, não **desvia**

---

## 7. Fluxo Git (Desktop → Raspberry Pi)
Sempre fazer o commi  atualizar o git para que seja possível atualizar a Raspberry que é o hardware de teste físico.

### Na Raspberry Pi — atualizar
```bash
cd ~/robo_slam
git fetch origin
git checkout robo_slam_2026_C1_obstaculo
git pull origin robo_slam_2026_C1_obstaculo
source venv/bin/activate
# pyrplidarsdk já deve estar instalado
python main.py
```

### Dependências
- `pyrplidarsdk>=0.1.2` — Backend principal
- `rplidarc1>=0.1.3` — Tools e fallback

---

## 8. Prompt para nova conversa (copiar e colar)

### 8.1 Prompt padrão (para amanhã: mais testes → próxima fase)

Copie e cole o texto abaixo **no início** de um novo chat. Ele já descreve o plano de amanhã:

```
Sou desenvolvedor do projeto Robô SLAM 2026. Preciso dar continuidade ao desenvolvimento.

**Contexto completo:** Leia o arquivo docs/PROMPT_CONTINUACAO_19MAR2026_C1_OBSTACULO.md — ele contém o estado atual do projeto, fases concluídas, branch ativa, arquivos principais e próximas etapas planejadas.

**Branch de trabalho:** robo_slam_2026_C1_obstaculo

**Estado atual:** O RP Lidar C1 está funcionando com pyrplidarsdk (parada de emergência estável). Testes validados com lixeira e pessoa — parada consistente em múltiplas repetições. Fases concluídas: 1 (odometria/navegação ida-volta) e 2a (C1 obstáculo à frente).

**Plano imediato:** Hoje/amanhã farei mais testes de validação do C1 em diferentes cenários. Depois disso vamos para a próxima fase planejada: Fase 2b (deriva do robô) e Fase 2c (desvio de obstáculos — quando se aproximar de mesa, realinhar e ir em direção ao POI, não só parar).

**Observação conhecida:** O robô tem deriva (odometria). Quando deriva perto de mesa, o LIDAR vê a mesa no cone frontal e para — isso é esperado (parada de segurança). A lógica de desvio/realinhamento será desenvolvida na Fase 2c.

Preciso [substitua aqui pela tarefa específica de agora — ex.: "revisar os logs de teste", "ajustar LIDAR_OBSTACLE_MIN_DISTANCE", "começar a Fase 2b", etc.].
```

### 8.2 Exemplos de tarefa para substituir no final

- `"Analisar os logs que anexei de um teste de navegação com obstáculo."`
- `"Preparar um resumo do que precisamos para iniciar a Fase 2b (deriva)."`
- `"Começar a implementar a Fase 2c — desvio de obstáculos: quando o robô parar por obstáculo lateral (mesa), realinhar e seguir em direção ao POI."`
- `"Ajustar LIDAR_OBSTACLE_MIN_DISTANCE para 0.70 m e documentar."`

---

## 9. Como usar @ no Cursor (referenciar arquivos)

O **@** no Cursor permite anexar arquivos ou pastas ao chat para o assistente ter contexto. Use quando a tarefa envolver código específico.

### 9.1 Passo a passo para usar @

1. **Abra um novo chat** (Ctrl+L no Linux/Windows, Cmd+L no Mac).
2. **Digite @** na caixa de mensagem (o menu de sugestões aparece).
3. **Escolha o tipo de referência:**
   - `@Docs` — documentação do Cursor
   - `@Codebase` — busca em todo o projeto
   - `@File` — um arquivo específico (digite o nome ou caminho)
   - `@Folder` — uma pasta inteira
4. **Digite o nome do arquivo** (ex.: `lidar_c1`) e selecione na lista.
5. **Envie a mensagem** — o conteúdo do arquivo será incluído no contexto.

### 9.2 Quais arquivos referenciar — lista prática

| Se você for... | Use @ com estes arquivos |
|----------------|--------------------------|
| **Trabalhar no LIDAR C1** (parada, distância, backends) | `@src/core/lidar_c1_reader.py` e `@src/core/config.py` |
| **Integração C1 com motores** (quem para, quando) | `@src/core/robot_motor_controller.py` e `@src/core/lidar_c1_reader.py` |
| **Configuração geral** (velocidade, C1, POIs) | `@src/core/config.py` |
| **Navegação** (trajetória, pathfinding, chegada ao POI) | `@src/core/robot_navigator.py` e `@src/core/path_finder.py` |
| **Fase 2b — Deriva** (odometria, correção de rumo) | `@src/core/robot_navigator.py`, `@src/core/config.py` (BNO, odometria) |
| **Fase 2c — Desvio de obstáculos** (lógica de desvio) | `@src/core/lidar_c1_reader.py`, `@src/core/robot_navigator.py` |
| **Ferramenta de calibração C1** | `@tools/calibracao_c1_orientacao.py` |
| **Teste isolado do C1** | `@tools/teste_c1_isolado.py` |
| **Dar contexto geral do projeto** (sempre útil no início) | `@docs/PROMPT_CONTINUACAO_19MAR2026_C1_OBSTACULO.md` |

### 9.3 Exemplos práticos de uso do @

**Exemplo 1 — Ajustar distância de parada:**
```
@docs/PROMPT_CONTINUACAO_19MAR2026_C1_OBSTACULO.md @src/core/config.py

Quero mudar LIDAR_OBSTACLE_MIN_DISTANCE de 0.85 para 0.70 m. Onde altero e o que mais preciso ajustar?
```

**Exemplo 2 — Começar Fase 2c (desvio):**
```
@docs/PROMPT_CONTINUACAO_19MAR2026_C1_OBSTACULO.md @src/core/lidar_c1_reader.py @src/core/robot_navigator.py

Vamos iniciar a Fase 2c — desvio de obstáculos. Hoje o robô só para. Preciso que, quando parar por obstáculo lateral (mesa), ele tente realinhar e seguir em direção ao POI. O lidar_c1_reader retorna só a distância mínima — precisaremos de distância por setor (esq/centro/dir)?
```

**Exemplo 3 — Revisar logs:**
```
@docs/PROMPT_CONTINUACAO_19MAR2026_C1_OBSTACULO.md

Fiz testes ontem. Colo os logs abaixo. O que você observa? [cole os logs]
```

**Regra geral:** Use `@docs/PROMPT_CONTINUACAO_19MAR2026_C1_OBSTACULO.md` no início de **qualquer** nova conversa para carregar o contexto. Depois adicione os arquivos específicos da tarefa.

---

## 10. Estrutura de pastas relevante

```
robo_slam/
├── src/
│   ├── main.py
│   └── core/
│       ├── config.py           # LIDAR_C1_BACKEND, LIDAR_OBSTACLE_MIN_DISTANCE
│       ├── robot_motor_controller.py  # Integração C1 (has_obstacle)
│       ├── lidar_c1_reader.py   # Leitura C1 (pyrplidarsdk + rplidarc1)
│       ├── robot_navigator.py
│       ├── path_finder.py
│       └── map_manager.py
├── tools/
│   ├── calibracao_c1_orientacao.py
│   ├── teste_c1_isolado.py
│   └── c1_mapa_visual.py
├── docs/
│   ├── PROMPT_CONTINUACAO_19MAR2026_C1_OBSTACULO.md  # Este arquivo
│   └── ANALISE_RPLIDARC1_MANTER_OU_REMOVER_19MAR2026.md
└── requirements.txt            # pyrplidarsdk, rplidarc1
```

---

## 11. Próxima fase: Abordagem C — Scan Matching com mapa PGM (Fase 3)

### Por que essa abordagem

BNO + odometria + CTE falharam consistentemente em corrigir deriva. A causa raiz é que todos estimam posição sem "ver" o ambiente real. O C1 Lidar já lê o ambiente real — usá-lo para corrigir a pose é a solução mais robusta disponível no hardware atual.

### Pré-requisitos concluídos ✅

| Item | Status | Detalhe |
|------|--------|---------|
| Mapa PGM gerado pelo C1 | ✅ | `mapa-03122025_final_90.pgm` (131×251 px) |
| YAML com resolução correta | ✅ **CORRIGIDO 19/03** | 0.023904 → **0.047808 m/px** (era metade do real) |
| Sala real representada | ✅ | 6.26m × 12.00m — confirmado |
| C1 lendo scans em tempo real | ✅ | Via `pyrplidarsdk`, thread dedicada |
| Odometria em metros reais | ✅ | `ROBOT_WHEEL_CIRCUMFERENCE_M=0.525`, `TICKS_PER_REVOLUTION=45` |
| POIs recriados pelo operador | ⏳ Pendente | Recriar via GUI após primeira execução com YAML correto |

### Como funciona o scan matching

1. O mapa PGM é carregado como uma grade de ocupância (pixels pretos = paredes/obstáculos)
2. A cada ~1-2 s, o scan atual do C1 (360 pontos em metros reais) é comparado com o mapa
3. O algoritmo busca o deslocamento `(dx, dy, dθ)` que melhor alinha o scan com o mapa
4. Esse deslocamento corrige a pose estimada pela odometria
5. A navegação continua usando a pose corrigida para calcular a distância até o POI

### O robô chega ao POI por coordenadas x,y?

**Sim.** A lógica de destino não muda. O que muda é que a pose `(x, y, θ)` durante o trajeto será corrigida pelo scan matching, reduzindo a deriva. O robô para quando a pose corrigida indica que chegou às coordenadas do POI.

### Arquitetura do novo módulo (a implementar)

```
src/core/lidar_pose_corrector.py   ← NOVO
  - Carrega PGM + YAML como grade de ocupância
  - Recebe scan C1 (lista de (ângulo, distância))
  - Executa ICP simplificado ou correlação de ocupância
  - Retorna (dx, dy, dθ) — correção de pose
  - Rodando em thread, corrigindo a cada ~1-2 s
```

Integração: `robot_navigator._update_pose_with_odometry()` aplica a correção após odometria.

### Resolução do mapa e precisão esperada

- Resolução: **0.047808 m/px ≈ 4.78 cm/px**
- Precisão teórica do scan matching: **±5-10 cm**
- Frequência de correção: **a cada 1-2 s** (adequado para Raspberry Pi 4)
- Impacto no CPU: estimado **5-15%** com numpy vetorizado

### Após correção do YAML — o que muda no comportamento

- Posição inicial calculada automaticamente: `(74×0.047808, 162×0.047808)` = **(3.54, 7.74)** metros reais
- POIs precisam ser recriados clicando no mapa (GUI já funcionará na escala correta)
- Áreas proibidas precisam ser recriadas (mesma razão)
- Odometria e motores: **sem alterações** (já estavam em metros reais)
