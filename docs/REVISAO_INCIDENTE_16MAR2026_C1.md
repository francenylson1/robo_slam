# Revisão do incidente 16/03/2026 — Lidar C1

**Data:** 16 de março de 2026  
**Branch:** `robo_slam_2026_lidar_c1`

---

## Resumo

Após testes de navegação com o Lidar C1 ativo, ocorreram três problemas:

1. Robô parou no obstáculo "empurrando um pouco"
2. Robô declarou chegada ao POI mesmo parado longe do destino
3. Após o teste, robô travou: apenas gira (L/R), não avança para frente

---

## Análise das causas

### 1. Parada com empurrão

- **Causa:** Distância de parada `LIDAR_OBSTACLE_MIN_DISTANCE = 0.45` m pode ser insuficiente para frear antes do contato.
- **Sugestão ao reativar:** Testar `0.35` m (35 cm) para parar mais cedo.

### 2. Declarou chegada ao POI parado

- **Causa:** O `robot_navigator` usa timeout de ~6 s como critério de "chegada estável". Se o Lidar bloqueou o robô perto do POI, após 6 s sem movimento o sistema considerou que chegou.
- **Status:** Já havia lógica `is_lidar_blocking_or_recent()` para não declarar chegada por timeout quando o Lidar está bloqueando. Pode ter havido condição de corrida ou o robô estava "suficientemente perto" para o critério de distância.

### 3. Travamento: só gira, não anda

- **Causa principal:** `_obstacle_distance_m` inicia em `0.0` m para bloquear até o primeiro scan (segurança). Se o primeiro scan nunca completar — ex.: C1 em estado ruim após fechar o app, serial ocupada, rplidarc1 em erro — `has_obstacle()` retorna sempre `True` e `set_target_speed()` força `(0, 0)` em qualquer avanço.
- **Motores:** Giro funciona porque `disable_pid_control()` é chamado apenas na condição de obstáculo; giros manuais podem usar caminho diferente ou o bloqueio pode afetar apenas avanço. Na prática, qualquer `left_tps != 0 or right_tps != 0` com `has_obstacle()` → `(0, 0)`.

---

## Correções implementadas

### 1. C1 desativado (config)

`LIDAR_C1_ENABLED = False` em `src/core/config.py`

- **Efeito:** Navegação volta ao comportamento anterior (sem Lidar). Robô anda e navega normalmente.
- **Para reativar:** Alterar para `True` em `config.py`.

### 2. Timeout de 5 segundos no 1º scan

Em `src/core/lidar_c1_reader.py`:

- Constante `FIRST_SCAN_TIMEOUT_SEC = 5.0`
- Tarefa assíncrona `first_scan_timeout()`: aguarda 5 s e, se `_obstacle_distance_m` ainda for `0.0`, define `_obstacle_distance_m = float("inf")` e registra aviso.
- **Efeito:** Evita bloqueio eterno quando o C1 não consegue completar o primeiro scan.

---

## Teste isolado do C1 (após o incidente)

```bash
python tools/teste_c1_isolado.py --port /dev/ttyUSB0 --scans 10
```

- **Saúde:** `None` (pode ser esperado em algumas versões do rplidarc1)
- **Obstáculo mais próximo:** ~96–97 mm (corpo/parachoques do robô)
- **Sensor desconectado:** Mensagem ao final do script (normal)

---

## Para reativar o C1 no futuro

1. Definir `LIDAR_C1_ENABLED = True` em `config.py`
2. Considerar `LIDAR_OBSTACLE_MIN_DISTANCE = 0.35` para parar mais cedo
3. Revisar zona de parachoques 120°–240° (~96 mm) — o teste isolado mostra ~96 mm como mínimo; o reader ignora < 220 mm nessa zona
4. Garantir que o app seja fechado corretamente para evitar estado ruim do C1 na próxima execução (a falha de segmentação ao fechar pode deixar a serial em estado inconsistente)

---

## Falha de segmentação ao fechar

- **Sintoma:** `Falha de segmentação` ao encerrar o app.
- **Provável causa:** Shutdown do rplidarc1 (reset, desconexão serial) em combinação com PyQt5/threading.
- **Mitigação:** Fechar o app de forma controlada. Em último caso, reiniciar o Raspberry Pi antes de um novo teste.

---

## Atualização 16/03/2026 (noite) — Watchdog e GPIO

### Problema: robô parava antes do POI (obstáculo) e após ~45 s declarava "chegada"

- **Causa:** Watchdog de 45 s forçava "chegada ao POI" mesmo com robô parado por obstáculo C1.
- **Correção:** Em `robot_navigator.py`, antes de forçar chegada no timeout, verificar `is_lidar_blocking_or_recent()`. Se obstáculo na frente → cancelar navegação (não declarar chegada).
- **Método:** `_cancel_navigation_blocked_by_obstacle()` → finaliza com flag `_cancelled_by_obstacle`.
- **UI:** `main_window` exibe "⚠️ Navegação cancelada — obstáculo bloqueou o caminho" em vez de "chegada com sucesso".

### Problema: Falha de segmentação / RuntimeError GPIO ao encerrar

- **Causa:** `disable_pid_control()` chamava `GPIO.output()` após `GPIO.cleanup()`.
- **Correção:** `try/except (RuntimeError, AttributeError)` em `disable_pid_control()` para evitar crash ao fechar app.

---

## Arquivos alterados

| Arquivo | Alteração |
|---------|-----------|
| `src/core/config.py` | `LIDAR_C1_ENABLED = False` (revertido para True em calibração posterior) |
| `src/core/lidar_c1_reader.py` | `FIRST_SCAN_TIMEOUT_SEC`, tarefa `first_scan_timeout()` |
| `src/core/robot_navigator.py` | Watchdog: checar Lidar antes de forçar chegada; `_cancel_navigation_blocked_by_obstacle()` |
| `src/core/robot_motor_controller.py` | `disable_pid_control`: try/except para GPIO |
| `src/interfaces/main_window.py` | Mensagem "Navegação cancelada" quando `cancelled_by_obstacle` |
