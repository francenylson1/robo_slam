# Análise: manter ou remover biblioteca rplidarc1

**Data:** 19/03/2026  
**Branch:** `robo_slam_2026_C1_obstaculo`  
**Contexto:** pyrplidarsdk está funcionando muito bem; rplidarc1 tinha parada inconsistente.

---

## Onde rplidarc1 é usado

| Arquivo | Uso |
|---------|-----|
| `src/core/lidar_c1_reader.py` | Backend alternativo (quando `LIDAR_C1_BACKEND="rplidarc1"`). Fallback se pyrplidarsdk falhar. |
| `tools/calibracao_c1_orientacao.py` | Calibração: lê C1 para medir ângulos frente/esq/dir. Usa rplidarc1 diretamente. |
| `tools/teste_c1_isolado.py` | Teste isolado do C1 (sem main.py). Usa rplidarc1. |
| `tools/c1_mapa_visual.py` | Mapa visual dos pontos do C1. Usa rplidarc1. |
| `requirements.txt` | `rplidarc1>=0.1.3` e `pyrplidarsdk>=0.1.2` |

---

## Recomendação: **manter** rplidarc1 por enquanto

### Motivos

1. **Custo baixo:** Ocupa pouco espaço e não interfere no funcionamento atual. O `main.py` usa pyrplidarsdk por padrão.
2. **Fallback:** Se o pyrplidarsdk falhar em algum ambiente (ex.: Pi antiga, build quebrado), ainda há alternativa.
3. **Ferramentas:** `calibracao_c1_orientacao.py`, `teste_c1_isolado.py` e `c1_mapa_visual.py` usam rplidarc1. Migrar tudo para pyrplidarsdk daria trabalho e não é urgente.
4. **Config:** `config.py` permite trocar o backend sem mexer no código.

### Quando considerar remoção

- Se for prioridade simplificar o código e reduzir dependências.
- Se as ferramentas forem migradas para pyrplidarsdk de forma consistente.

---

## Opção: remover rplidarc1 (orientação se optar)

Se decidir remover, os passos seriam:

### 1. `src/core/lidar_c1_reader.py`

- Remover import de `asyncio` (se usado só por rplidarc1).
- Remover bloco `if backend == "pyrplidarsdk"` e deixar apenas `_run_pyrplidarsdk_scan()`.
- Remover `_run_async_scan()` e toda a lógica assíncrona do rplidarc1.
- Remover variável `backend` e chamar diretamente `_run_pyrplidarsdk_scan()`.
- Em `stop()`, simplificar — pyrplidarsdk usa `stop_scan()`/`disconnect()`.

### 2. `src/core/config.py`

- Remover `LIDAR_C1_BACKEND` (ou deixar só como referência interna).

### 3. `requirements.txt`

- Remover a linha `rplidarc1>=0.1.3`.

### 4. Ferramentas (calibracao, teste_c1_isolado, c1_mapa_visual)

- Opção A: Migrar para pyrplidarsdk (reescrever lógica de leitura).
- Opção B: Manter rplidarc1 apenas nas ferramentas — nesse caso, continuar listando `rplidarc1` no `requirements.txt`.

---

## Resumo

| Ação | Recomendação |
|------|---------------|
| **Agora** | Manter rplidarc1 como está (backend alternativo + ferramentas). |
| **Futuro** | Avaliar remoção após migrar as ferramentas para pyrplidarsdk (se desejar um único backend). |
