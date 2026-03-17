# Diagnóstico: Lixeira não detectada pelo C1 (robô atropela)

**Data:** 17 de março de 2026

---

## Problema

Robô não para e atropela a lixeira colocada à frente, apesar do C1 estar ativo.

---

## Causas prováveis

### 1. **Cone frontal estreito (60°) — CORRIGIDO**

O cone frontal era de apenas **60°** (centro 350°, faixa 320°–20°). Em trajetórias curvas ou com a lixeira ligeiramente lateral, o obstáculo ficava **fora do cone** e não era detectado.

**Correção:** `FRONT_WIDTH_DEG = 120°` no `lidar_c1_reader.py`. O cone agora cobre 290°–50°, excluindo o corpo (120°–240°).

### 2. **Material da lixeira**

Lixeiras pretas ou plástico escuro absorvem infravermelho e podem ser quase invisíveis ao Lidar até bem perto. Sugestão: usar caixa de papelão ou objeto claro para testes.

### 3. **C1 não conectou**

Se aparecer no log "Lidar C1 não disponível" ou não houver "Lidar C1 ativo", o sensor não iniciou. Verificar:
- Cabo USB em `/dev/ttyUSB0`
- C1 ligado
- `ls /dev/ttyUSB*` para confirmar a porta

### 4. **Logs ausentes**

Se não surgem mensagens "Lidar C1: obstáculo..." ou "Lidar C1 diagnóstico:", o `set_target_speed` pode não estar sendo chamado ou o Lidar pode não estar integrado. Procurar no log por "Lidar C1 ativo" e "Lidar C1 integrado aos motores" na inicialização.

---

## Teste de validação antes da navegação

```bash
# 1. Teste isolado com lixeira à frente
python tools/teste_c1_isolado.py --port /dev/ttyUSB0 --front-deg 120 --front-center 350 --scans 5
```

Coloque a lixeira a ~40 cm à frente do robô. O teste deve indicar distância mínima < 450 mm (PARAR ou ALERTA). Se indicar "livre", o C1 não está vendo a lixeira (material ou ângulo).

---

## Próximos passos após atualização

1. Fazer `git pull` na Raspberry Pi
2. Conferir logs: "Lidar C1 ativo: cone 120° (centro 350°)"
3. Repetir o Teste 1 com a lixeira
4. Se ainda não parar: testar com caixa de papelão em vez da lixeira (verificar material)
