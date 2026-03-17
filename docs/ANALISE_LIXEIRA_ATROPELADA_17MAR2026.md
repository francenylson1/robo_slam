# Análise: Robô atropela lixeira — 17/03/2026

## Testes realizados

1. **Lixeira a 47 cm:** robô não iniciou navegação (esperado, pois 47 < 50 cm).
2. **Lixeira a 70 cm:** robô iniciou mas **não parou** e atropelou a lixeira.

## Problema

O Lidar C1 **não está detectando a lixeira** durante a navegação. Nos logs não aparecem:
- `Lidar C1 diagnóstico: distância frontal = X.XX m`
- `Lidar C1: obstáculo < 0.50 m — parando motores`

Isso indica que `has_obstacle()` nunca retornou `True` durante o movimento — o sensor reportou sempre distância ≥ 0,50 m ou `inf`.

## Hipóteses identificadas

### 1. Cone frontal estreito (120°)
- Cone atual: centro 350°, largura 120° → faixa 290°–50°.
- Durante curvas, a lixeira pode ficar **fora do cone**.
- **Correção:** cone ampliado para 180° (260°–80°).

### 2. Distância de parada insuficiente (0,50 m)
- Margem pequena entre detecção e parada com 0,50 m.
- **Correção:** limiar aumentado para 0,60 m para parar mais cedo.

### 3. Altura do plano de varredura vs. altura da lixeira
- O C1 é 2D: varre um único plano horizontal.
- Se o Lidar estiver montado alto e a lixeira for baixa, o plano pode passar **acima** da lixeira.
- **Ação sugerida:** conferir se o plano de varredura do C1 cruza a lixeira; ajustar altura do sensor se preciso.

### 4. Reflexão em lixeiras plásticas
- Plástico pode refletir pouco ou dispersar o feixe.
- No `teste_c1_isolado` a lixeira foi detectada (~287 mm), mas com robô parado e ângulo frontal.
- Em movimento, ângulos e vibrações podem reduzir a detecção.
- **Mitigação:** cone maior (180°) aumenta a chance de acertar algum ângulo que reflita bem.

### 5. Diagnóstico invisível nos logs
- Os logs mostram principalmente `print()` do widget do mapa.
- As mensagens de log do Lidar podem não aparecer no terminal se forem capturadas só de stdout.
- **Correção:** adicionado `print()` no `set_target_speed` para diagnóstico sempre visível no terminal.

## Correções implementadas

| Alteração | Arquivo | Descrição |
|-----------|---------|-----------|
| Cone 180° | `lidar_c1_reader.py` | `FRONT_WIDTH_DEG = 180` (era 120°) |
| Distância 0,60 m | `config.py` | `LIDAR_OBSTACLE_MIN_DISTANCE = 0.60` |
| Diagnóstico via print | `robot_motor_controller.py` | `print()` a cada 0,5 s com distância frontal para aparecer no terminal |
| Log quando obstáculo | `robot_motor_controller.py` | `print()` quando `has_obstacle()` bloqueia |

## Verificações no próximo teste

1. Aparecer no terminal algo como:
   ```
   📡 LIDAR C1: distância frontal = X.XX m (parar se < 0.60 m)
   ```
2. Ao se aproximar da lixeira, deve aparecer:
   ```
   🛑 LIDAR C1: OBSTÁCULO DETECTADO — parando motores (dist=0.XX m)
   ```
3. Se continuar sem detecção, conferir:
   - Altura do Lidar em relação à lixeira.
   - Executar novamente: `python tools/teste_c1_isolado.py --port /dev/ttyUSB0 --front-deg 180 --front-center 350 --scans 5` com a lixeira a ~60 cm.

---

## Reanálise com feedback do usuário

### Hipóteses descartadas (com suas respostas)

| Hipótese | Sua resposta | Conclusão |
|----------|--------------|-----------|
| **Freio / distância 50 cm** | Motor bem calibrado, desliga e para imediatamente | O problema não é o freio — é que o Lidar nunca envia o comando de parada. |
| **Altura do Lidar** | Lixeira 42 cm largura × 56 cm altura | Plano de varredura cruza o objeto. Hipótese de altura descartada. |
| **Reflexão** | `teste_c1_isolado` com cone 120° detecta a lixeira | O sensor enxerga a lixeira quando parado e em frente. Reflexão descartada. |

### Hipótese principal que permanece

**Geometria da trajetória durante a navegação**

- **Teste isolado:** robô parado, lixeira colocada à frente → ângulo ≈ 350° → dentro do cone 120° (290°–50°) → detectado.
- **Navegação:** robô segue waypoints e pode fazer curvas; a “frente” (350°) pode apontar para o próximo waypoint, não para a lixeira.
- **Se a lixeira estiver, por exemplo, a 270° (esquerda):** está fora do cone 120° (290°–50°), mas entra no cone 180° (260°–80°).

Ou seja: o cone 120° pode ter deixado a lixeira fora durante a maior parte da aproximação em curva.

### Alterações mantidas

1. **Cone 180°** – aumenta a chance de detectar a lixeira durante curvas.
2. **Distância 0,60 m** – não resolve falta de detecção, mas aumenta margem se a detecção começar a ocorrer.
3. **Print de diagnóstico** – permite ver no terminal o que o Lidar está reportando durante o movimento.
