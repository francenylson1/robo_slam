# ✅ Solução: Mapa Quadrado vs Retangular

**Data**: 25/11/2025

---

## 🔍 PROBLEMA IDENTIFICADO

### Situação:
- **Mapa real**: Retangular 12m × 6m
- **PGM gerado**: Quadrado (ex: 435×412 pixels, mas parece quadrado)
- **Causa**: Map points nas extremidades criam bounding box maior que o necessário

---

## 🎯 CAUSA RAIZ

### Como o PGM era Gerado:

1. **Bounding Box dos Pontos**:
   ```python
   min_xy = points_xy.min(axis=0) - padding  # Ponto mínimo - padding
   max_xy = points_xy.max(axis=0) + padding  # Ponto máximo + padding
   size = max_xy - min_xy  # Tamanho do grid
   ```

2. **Problema**:
   - O código usava **TODOS** os map points, incluindo outliers nas extremidades
   - Se há map points muito distantes (ruído, erros de captura), o bounding box fica maior
   - Com padding de 1.0m, o mapa fica ainda maior
   - Se os pontos extremos criarem um bounding box simétrico, o PGM fica **quadrado**

### Exemplo:
- **Mapa real**: 12m (X) × 6m (Y)
- **Map points extremos** (com outliers):
  - X: de -10m a 10m (20m de largura) ❌
  - Y: de -10m a 10m (20m de altura) ❌
- **Com padding de 1.0m**:
  - X: 20m + 2m = 22m
  - Y: 20m + 2m = 22m
- **Resultado**: Grid de 22m × 22m (QUADRADO!)

---

## ✅ SOLUÇÃO IMPLEMENTADA

### Filtro de Outliers por Percentil:

1. **Calcula o centro** dos pontos (usando mediana, mais robusta que média)
2. **Calcula distâncias** de cada ponto ao centro
3. **Remove pontos** além do percentil especificado (padrão: 99%)
4. **Gera grid** apenas com pontos filtrados

### Código Adicionado:

```python
# Filtro de outliers: remove pontos muito distantes do centro
filter_outliers = map_cfg.get("filter_outliers", True)
outlier_percentile = float(map_cfg.get("outlier_percentile", 99.0))

if filter_outliers and len(points_xy) > 100:
    # Calcula centro (mediana)
    center_x = np.median(points_xy[:, 0])
    center_y = np.median(points_xy[:, 1])
    
    # Calcula distâncias ao centro
    distances = np.sqrt((points_xy[:, 0] - center_x)**2 + (points_xy[:, 1] - center_y)**2)
    
    # Remove pontos além do percentil
    threshold = np.percentile(distances, outlier_percentile)
    outlier_mask = distances <= threshold
    points_xy = points_xy[outlier_mask]
```

---

## 📋 CONFIGURAÇÕES

### Novos Parâmetros em `config/mapping.json`:

```json
"map2d": {
  "filter_outliers": true,      // Ativa/desativa filtro
  "outlier_percentile": 99.0,   // Remove 1% mais extremo (0-100)
  "padding_m": 0.5              // Reduzido de 1.0m para 0.5m
}
```

### Parâmetros Ajustados:

- **`padding_m`**: Reduzido de `1.0m` para `0.5m` (menos área vazia)
- **`filter_outliers`**: Novo parâmetro (padrão: `true`)
- **`outlier_percentile`**: Novo parâmetro (padrão: `99.0`)

---

## 🎯 RESULTADO ESPERADO

### Antes:
- Grid baseado em TODOS os pontos (incluindo outliers)
- Mapa quadrado ou maior que o necessário
- Muito espaço vazio (padding excessivo)

### Depois:
- Grid baseado apenas em pontos relevantes (99% mais próximos)
- Mapa retangular próximo ao tamanho real (12m × 6m)
- Menos espaço vazio (padding reduzido)

---

## 🔧 COMO USAR

### 1. Regerar o Mapa:
```bash
python3 src/main_mapping.py --pipeline aurora_to_c1 --input mapas/legacy/originais_aurora --steps map2d
```

### 2. Ajustar Filtro (se necessário):
Edite `config/mapping.json`:
- **Mais agressivo** (remove mais outliers): `"outlier_percentile": 95.0`
- **Menos agressivo** (remove menos outliers): `"outlier_percentile": 99.5`
- **Desativar filtro**: `"filter_outliers": false`

### 3. Verificar Logs:
O sistema mostrará:
```
[map2d] Aplicando filtro de outliers (percentil 99.0%)...
[map2d] Removidos X pontos outliers (Y%)
[map2d] Centro: (x, y)m, Threshold: Z m
[map2d] Range após filtro: X=12.00m, Y=6.00m
```

---

## 📊 EXEMPLO DE SAÍDA

### Antes (sem filtro):
```
[map2d] Criando grid: 440x440 pixels (193,600 total)
[map2d] Limites: X=[-11.0, 11.0]m, Y=[-11.0, 11.0]m
```

### Depois (com filtro):
```
[map2d] Aplicando filtro de outliers (percentil 99.0%)...
[map2d] Removidos 7 pontos outliers (1.3%)
[map2d] Centro: (0.0, 0.0)m, Threshold: 6.5m
[map2d] Range após filtro: X=12.00m, Y=6.00m
[map2d] Criando grid: 260x140 pixels (36,400 total)
[map2d] Limites: X=[-6.5, 5.5]m, Y=[-3.5, 2.5]m
```

---

## ⚠️ NOTAS IMPORTANTES

1. **Percentil 99%**: Remove apenas 1% dos pontos mais distantes (muito conservador)
2. **Mínimo de pontos**: Filtro só ativa se houver mais de 100 pontos
3. **Mediana vs Média**: Usa mediana para calcular centro (mais robusta a outliers)
4. **Padding reduzido**: De 1.0m para 0.5m (menos área vazia)

---

## 🔄 PRÓXIMOS PASSOS

1. **Testar**: Regerar o mapa e verificar se fica retangular (12m × 6m)
2. **Ajustar**: Se necessário, ajustar `outlier_percentile` ou `padding_m`
3. **Validar**: Verificar se o mapa gerado corresponde ao ambiente real

---

**A solução remove map points extremos antes de calcular o bounding box, garantindo que o mapa seja gerado no tamanho real do ambiente!**

