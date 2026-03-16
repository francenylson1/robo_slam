# Faixa frontal do C1 — Diferentes modelos de robô

**Referência:** `tools/teste_c1_isolado.py` (Etapa 1 do plano C1)

---

## 1. Conceito

O sensor C1 retorna ângulos de **0° a 360°**:
- **0°** = frente do sensor (direção de movimento)
- Sentido **horário** = ângulo aumenta (90° = direita, 180° = costas, 270° = esquerda)

A **faixa frontal** é um cone centrado na frente, definido por:
- **Centro:** ângulo central (padrão 0°)
- **Largura:** total em graus (ex: 200° = ±100° em relação ao centro)

---

## 2. Modelo em desenvolvimento — 200° frontal

O robô usado neste desenvolvimento tem faixa frontal de **200°**:
- **Largura total:** 200°
- **Extensão:** ±100° em relação à frente (0°)
- **Intervalo angular:** de **260°** até **100°** (via 0°)

### Cálculo

```
centro = 0°
largura = 200°
metade = 100°

Faixa: [centro - metade, centro + metade]
     = [-100°, +100°]

Em coordenadas 0–360° (com wrap):
     = [260°, 360°) ∪ [0°, 100°]
     = 260° → 270° → … → 360°(=0°) → … → 100°
```

Ou seja: **100° para a esquerda da frente + frente + 100° para a direita** = 200° no total.

### Uso no script

```bash
# Via preset do modelo
python tools/teste_c1_isolado.py --robot-model dev --scans 3

# Via largura explícita
python tools/teste_c1_isolado.py --front-deg 200 --scans 3
```

---

## 3. Presets por modelo de robô

| Preset       | Largura | ± do centro | Uso típico                                      |
|--------------|---------|-------------|--------------------------------------------------|
| `narrow`     | 60°     | ±30°        | Robôs compactos, corredores estreitos           |
| `medium`     | 90°     | ±45°        | Padrão moderado                                  |
| `wide`       | 120°    | ±60°        | Ambientes abertos                               |
| **`dev`**    | **200°**| **±100°**   | **Modelo atual em desenvolvimento**               |
| `hemi`       | 180°    | ±90°        | Hemisfério frontal (meia circunferência)         |
| `panoramic`  | 270°    | ±135°       | Quase 360°, robôs com sensores rotativos         |

---

## 4. Possibilidades de uso

### 4.1 Escolher preset do modelo
```bash
python tools/teste_c1_isolado.py --robot-model dev
python tools/teste_c1_isolado.py --robot-model narrow
```

### 4.2 Largura customizada
```bash
python tools/teste_c1_isolado.py --front-deg 75
```

### 4.3 Centro deslocado (sensor rotacionado)
Se o sensor não estiver alinhado com a frente do robô:
```bash
python tools/teste_c1_isolado.py --front-deg 200 --front-center 15
```

### 4.4 Modo 360° (sem filtro)
```bash
python tools/teste_c1_isolado.py
# Ou explicitamente sem --front-deg e sem --robot-model
```

### 4.5 Prioridade
`--robot-model` tem prioridade sobre `--front-deg`:
```bash
python tools/teste_c1_isolado.py --robot-model wide --front-deg 60
# → usa wide (120°)
```

---

## 5. Saída quando há filtro frontal

Com `--front-deg` ou `--robot-model`, o script exibe:
- **frontal (N pts):** mínimo na faixa frontal
- **360° min:** mínimo em toda a varredura (referência)

Exemplo:
```
Scan 1: 487 pts | frontal (271 pts): min=350 mm (0.35 m) | 360° min=97 mm
```

---

## 6. Adicionando novos presets

Edite `ROBOT_MODEL_PRESETS` em `tools/teste_c1_isolado.py`:

```python
ROBOT_MODEL_PRESETS = {
    "narrow":   60,
    "medium":   90,
    "wide":    120,
    "dev":     200,
    "hemi":    180,
    "panoramic": 270,
    "custom":   150,  # Novo modelo
}
```

Depois use: `--robot-model custom`.
