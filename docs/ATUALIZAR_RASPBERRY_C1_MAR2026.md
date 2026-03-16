# Como atualizar e testar o Lidar C1 na Raspberry Pi

**Data:** 16 de março de 2026  
**Branch:** `robo_slam_2026_lidar_c1`  
**Status:** C1 reativado com calibração 350° (frente), cone frontal 60°

---

## 1. Pré-requisitos na Raspberry Pi

- **C1 conectado:** cabo USB em `/dev/ttyUSB0`
- **Python 3.10+** (rplidarc1 exige TaskGroup)
- **Biblioteca:** `pip install rplidarc1` (ou `pip install -r requirements.txt`)

---

## 2. Atualizar o código do GitHub

### Sem alterações locais:
```bash
cd ~/robo_slam
git fetch origin
git checkout robo_slam_2026_lidar_c1
git pull origin robo_slam_2026_lidar_c1
```

### Com alterações locais (ex.: robot.db):
```bash
cd ~/robo_slam
git stash -m "local"
git checkout robo_slam_2026_lidar_c1
git pull origin robo_slam_2026_lidar_c1
git stash pop
```

### Conferir se está atualizado:
```bash
git log -1 --oneline
```

---

## 3. Teste isolado do C1 (antes da interface)

Para confirmar que o C1 está funcionando:

```bash
cd ~/robo_slam
source venv/bin/activate   # se usar venv
python tools/teste_c1_isolado.py --port /dev/ttyUSB0 --scans 5
```

**Esperado:**
- Varreduras completando normalmente
- Obstáculo mais próximo ~96–98 mm (corpo do robô)
- Sem erros "sync bytes" ou "Descriptor length mismatch"

---

## 4. Rodar a aplicação com C1 ativo

Com `LIDAR_C1_ENABLED = True` (já configurado):

```bash
python3 src/main.py
```

**Comportamento esperado:**
- Durante navegação, se obstáculo < 45 cm na frente (cone 320°–20°) → parada automática
- Timeout de 5 s no 1º scan: se o C1 não iniciar, permite avançar após 5 s (evita travamento)
- Corpo do robô (120°–240°) é ignorado na detecção

---

## 5. Teste de parada por obstáculo

1. Iniciar navegação para um POI
2. Colocar obstáculo à frente do robô (ex.: caixa a ~30 cm)
3. **Esperado:** robô para antes de encostar
4. Se o robô "empurrar" o obstáculo: reduzir `LIDAR_OBSTACLE_MIN_DISTANCE` em `config.py` para 0.35 m

---

## 6. Se algo der errado

### Robô não anda (só gira)
- **Causa provável:** C1 não completa o 1º scan e bloqueia o avanço
- **Solução imediata:** Em `src/core/config.py`, alterar `LIDAR_C1_ENABLED = False` e dar `git pull` novamente
- **Investigação:** Ver `docs/REVISAO_INCIDENTE_16MAR2026_C1.md`

### Falha de segmentação ao fechar o app
- Reiniciar a Raspberry Pi antes do próximo teste
- Fechar o app de forma controlada (evitar Ctrl+C abrupto)

---

## 7. Parâmetros calibrados (16/03/2026)

| Parâmetro | Valor | Arquivo |
|-----------|-------|---------|
| FRONT_CENTER_DEG | 350 | `src/core/lidar_c1_reader.py` |
| FRONT_WIDTH_DEG | 60 | `src/core/lidar_c1_reader.py` |
| PARACHOQUES_ZONE | (120, 240) | `src/core/lidar_c1_reader.py` |
| LIDAR_C1_ENABLED | True | `src/core/config.py` |
| LIDAR_OBSTACLE_MIN_DISTANCE | 0.45 m | `src/core/config.py` |

---

**Resumo:** `git checkout robo_slam_2026_lidar_c1` → `git pull` → `python tools/teste_c1_isolado.py` → `python3 src/main.py`
