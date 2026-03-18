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

## Próximos passos

1. Testar na Raspberry com `main.py` e lixeira em várias posições.
2. Confirmar que o robô não desbloqueia com a lixeira próxima.
3. Opcional: ajustar `UNBLOCK_MIN_PREV_DIST_M` ou `CONSECUTIVE_CLEAR_TO_UNBLOCK` conforme resultados práticos.
