# Orientações para teste na Raspberry Pi — Correções LIDAR C1 (Mar 2026)

## 1. Atualizar o código na Raspberry

```bash
cd /caminho/do/robo_slam   # ou onde está o projeto
git fetch origin
git checkout robo_slam_2026_lidar_c1
git pull origin robo_slam_2026_lidar_c1
```

## 2. Conferir dependências

```bash
pip install -r requirements.txt
# O pacote rplidarc1 deve estar instalado para o C1
```

## 3. Executar o main.py

```bash
python main.py
```

## 4. Roteiro de teste (validação das correções)

### Cenário A — Lixeira parada à frente
1. Coloque a lixeira a **~70 cm** à frente do robô.
2. Inicie a navegação para um POI na direção da lixeira.
3. **Esperado:** Robô para ao detectar (distância < 0,60 m).
4. **Não mover a lixeira.** Aguarde alguns segundos.
5. **Esperado:** Robô continua parado (não desbloqueia com obstáculo perto).

### Cenário B — Lixeira muito perto (~45 cm)
1. Posicione a lixeira a **~45 cm** à frente.
2. Navegue em direção a ela.
3. **Esperado:** Robô para; permanece parado (não desbloqueia).

### Cenário C — Lixeira retirada (desbloqueio intencional)
1. Com o robô parado por obstáculo a **~70 cm**.
2. Retire a lixeira completamente da frente (> 1 m).
3. Aguarde alguns segundos (vários scans).
4. **Esperado:** Após 5 scans livres e último obstáculo > 0,8 m, o robô pode desbloquear e continuar. Se o último obstáculo estava < 0,8 m, mantém bloqueio até você mover o robô ou retirar o obstáculo por mais tempo.

### Cenário D — Lixeira a ~15 cm (região crítica antiga)
1. Coloque a lixeira bem perto (**~15 cm**).
2. Navegue em direção a ela.
3. **Esperado:** Robô para (zona frontal estrita agora usa 50 mm de min_ignore; antes 150 mm ignorava essa distância).

## 5. O que observar nos logs

- **"OBSTÁCULO < 0.60m → PARANDO MOTORES!"** — detecção e parada OK.
- **"distância frontal = X.XXm"** — diagnóstico periódico.
- **"5 scans consecutivos livres (últ. obst=Y.YYm) — desbloqueando"** — desbloqueio só quando último obstáculo > 0,8 m.
- **"5 scans livres mas último obstáculo perto (X.XXm < 0.80m) — mantém bloqueio"** — comportamento correto: não desbloqueia com lixeira próxima.

## 6. Se algo der errado

- **Robô não para:** Verifique se `LIDAR_C1_ENABLED=True` em `src/core/config.py`.
- **Robô desbloqueia com lixeira na frente:** Envie os logs; pode ser necessário aumentar `CONSECUTIVE_CLEAR_TO_UNBLOCK` ou ajustar `UNBLOCK_MIN_PREV_DIST_M`.
- **Robô trava sem conseguir desbloquear:** Se retirou o obstáculo e o robô não anda, o último obstáculo pode ter sido < 0,8 m. Solução: dar um pequeno recuo manual ou recarregar o mapa e reiniciar a navegação.

## 7. Parâmetros atuais (referência)

| Parâmetro | Valor | Local |
|-----------|-------|-------|
| Parar se obstáculo < | 0,60 m | `config.LIDAR_OBSTACLE_MIN_DISTANCE` |
| Scans livres para desbloquear | 5 | `lidar_c1_reader.CONSECUTIVE_CLEAR_TO_UNBLOCK` |
| Desbloquear só se último obst > | 0,80 m | `lidar_c1_reader.UNBLOCK_MIN_PREV_DIST_M` |
| min_ignore zona frontal (350°–10°) | 0,05 m (50 mm) | `lidar_c1_reader.STRICT_FRONT_MIN_IGNORE_M` |
