# Prompt de Continuação — Projeto Robô SLAM 2026 (C1 Obstáculo OK)

**Data:** 19 de março de 2026  
**Branch ativa:** `robo_slam_2026_C1_obstaculo`  
**Objetivo:** Permitir abrir uma nova conversa e dar continuidade ao projeto sem perder contexto.

---

## 1. Situação atual do projeto

O **RP Lidar C1 está funcionando corretamente** como parada de emergência: detecta obstáculos à frente (lixeira, pessoa, mesa) e para os motores de forma estável. A navegação ida/volta continua operacional, com parada automática quando obstáculo < 85 cm no cone frontal.

### O que foi resolvido (Mar 2026)
- **rplidarc1** tinha parada inconsistente (às vezes parava, às vezes atropelava)
- Migração para **pyrplidarsdk** (SDK oficial SLAMTEC)
- **Bug crítico:** pyrplidarsdk retorna ângulos em **radianos** — o código tratava como graus, causando falsa detecção de obstáculo a 9 cm (corpo do robô na zona frontal)
- Correção: `math.degrees(ang)` no fluxo pyrplidarsdk
- Resultado: parada **consistente** em testes com lixeira e pessoa (várias repetições)

---

## 2. Fases concluídas e seguintes

| Fase | Nome | Status | Descrição |
|------|------|--------|-----------|
| 1 | Semi-autônoma (Odometria) | ✅ Concluída | Navegação ida/volta, odometria + CTE, áreas proibidas |
| 2a | C1 integrado (parada emergência) | ✅ Concluída | LIDAR C1 detecta obstáculo frontal, para motores |
| 2b | Deriva e correção de trajetória | 📋 Próxima | Robô desvia do caminho (odometria); tratar em fase futura |
| 2c | Desvio de obstáculos | 📋 Planejada | Ao se aproximar de mesa: realinhar e ir em direção ao POI (não só parar) |
| 3 | Localização (AMCL-like) | 📋 Planejada | Mapa Aurora + C1 para correção de pose |
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

```
Sou desenvolvedor do projeto Robô SLAM 2026. Preciso dar continuidade ao desenvolvimento.

**Contexto completo:** Leia o arquivo `docs/PROMPT_CONTINUACAO_19MAR2026_C1_OBSTACULO.md` — contém fases concluídas, branch ativa, arquivos principais e próximas etapas.

**Branch:** `robo_slam_2026_C1_obstaculo`

**Estado atual:** O C1 está funcionando com pyrplidarsdk (parada de emergência estável). Fases concluídas: 1 (odometria) e 2a (C1 obstáculo). Próximas: 2b (deriva), 2c (desvio de obstáculos), 3 (localização).

Preciso [descreva aqui a tarefa que deseja realizar].
```

---

## 9. Estrutura de pastas relevante

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
