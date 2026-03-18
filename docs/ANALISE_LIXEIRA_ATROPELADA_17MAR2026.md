# Análise: Lixeira detectada intermitentemente e atropelada (Mar 2026)

## Resumo dos sintomas relatados

1. **Teste 1:** Lixeira a ~70 cm → robô parou. Lixeira puxada mais ~70 cm → parou de novo. Depois disso **parou de parar**.
2. **Teste 2:** Recarregou o mapa → **não parou**.
3. **Teste 3:** Reiniciou o sistema → parou a ~45 cm. Em seguida **parou de parar** e **atropelou a lixeira**.

## Logs analisados

Nos logs fornecidos, o LIDAR C1 **estava detectando** o obstáculo:
- `distância frontal = 0.34m`, `0.36m`, `0.38m`, `0.15m` (parar se < 0.60 m)
- `LIDAR C1: OBSTÁCULO < 0.60m → PARANDO MOTORES!` aparece várias vezes
- A posição do robô permanece fixa em (3.38, 6.30)m durante todo o trecho

Ou seja: o sistema **parou os motores** corretamente. O problema observado em outros testes (não parar e atropelar) está ligado a cenários em que a detecção **perde** o obstáculo e o código **desbloqueia** os motores indevidamente.

## Causas identificadas

### 1. Desbloqueio com 2 scans consecutivos livres

**Problema:** O código antigo exigia apenas **2 varreduras completas** sem obstáculo para considerar a frente livre e definir `_obstacle_distance_m = inf`, desbloqueando os motores.

**Por que causava atropelo:** O C1 pode ter leituras intermitentes (reflexos ruins, ângulo da lixeira, movimento). Se 2 scans seguidos “não virem” o obstáculo, o sistema concluía que estava livre e liberava o movimento. Como o obstáculo ainda estava na frente, o robô voltava a avançar e podia colidir.

### 2. `min_ignore` = 150 mm na frente

**Problema:** Leituras < 150 mm eram descartadas (para filtrar reflexos do corpo do robô).

**Efeito:** Com a lixeira a ~14 cm, leituras em torno de 140 mm eram ignoradas. O scan era tratado como “livre” e contribuía para o desbloqueio falso.

### 3. Desbloquear mesmo com obstáculo perto

**Problema:** Se o último obstáculo registrado estava, por exemplo, a 0,3 m e depois apareciam 2 scans livres, o código desbloqueava mesmo assim.

**Consequência:** Era provável que o obstáculo ainda estivesse à frente; o sistema liberava o movimento incorretamente.

## Correções implementadas

| Arquivo | Mudança |
|---------|---------|
| `lidar_c1_reader.py` | `CONSECUTIVE_CLEAR_TO_UNBLOCK = 5` (antes 2) |
| `lidar_c1_reader.py` | `UNBLOCK_MIN_PREV_DIST_M = 0.8` — só desbloquear se o último obstáculo estava > 0,8 m |
| `lidar_c1_reader.py` | Zona frontal estrita (350°–10°) com `STRICT_FRONT_MIN_IGNORE_M = 0.05` — continua detectando obstáculos a 50 mm |
| `lidar_c1_reader.py` | `_min_ignore_for_point()` usa 50 mm só na zona 350°–10°; parachoques continuam em 220 mm |

## Comportamento esperado após correções

- **Detecção:** Lixeira a partir de ~50 mm na zona frontal estrita.
- **Desbloqueio:** Só depois de 5 scans consecutivos livres **e** último obstáculo > 0,8 m.
- **Obstáculo perto:** Se o último obstáculo estava < 0,8 m, não desbloqueia mesmo com vários scans livres; mantém o bloqueio.

## Atualização 18/03 — Novos testes, novos achados

### Logs do dia 18/03 16:43

- **distância frontal = 0.77 m** — LIDAR reportou “livre” com lixeira a ~70 cm.
- **POI alcançado (só ida, 15 cm)** — Navegador declarou chegada; em um teste o robô parou **depois** de atropelar.

### Causas adicionais

1. **Distância de parada (60 cm)** — Com o robô a 0,3 m/s, em 1 s são percorridos 30 cm. Parar aos 60 cm dá pouca margem se o cone deixar de detectar em alguns scans.
2. **Cone 180°** — Lixeira pode ficar um pouco fora do cone em curvas ou leves desvios.
3. **Declaração de chegada sem checagem de LIDAR** — Com “15 cm do alvo” a odometria podia declarar “chegada” mesmo com lixeira bloqueando, levando ao atropelo seguido de parada.

### Correções adicionais (18/03)

| Arquivo | Mudança |
|---------|---------|
| `config.py` | `LIDAR_OBSTACLE_MIN_DISTANCE = 0.85` (antes 0,60 m) — parar antes |
| `lidar_c1_reader.py` | `FRONT_WIDTH_DEG = 200` (antes 180°) — cone mais amplo |
| `robot_navigator.py` | Na regra “15 cm, só ida”, não declarar chegada se obstáculo < 40 cm à frente (possível lixeira) |

### Falha de segmentação

Ao encerrar o sistema aparece `Falha de segmentação`. Hipótese: desligamento do C1 (rplidarc1) em momento inadequado ou condição de corrida ao fechar conexão serial. Ainda sem causa definida; não afeta navegação durante execução.

## Próximos passos

1. Testar na Raspberry com `main.py` e lixeira em várias posições.
2. Confirmar parada antes da lixeira e ausência de atropelo.
3. Se continuar sem detectar, revisar calibração física do C1 (0° = frente do robô) com `tools/calibracao_c1_orientacao.py`.
