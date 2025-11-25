# 🔍 Análise: Mapa Quadrado vs Retangular

**Data**: 25/11/2025

---

## 📊 PROBLEMA IDENTIFICADO

### Situação:
- **Mapa real**: Retangular 12m × 6m
- **PGM gerado**: Quadrado (ex: 435×412 pixels, mas parece quadrado)
- **Dentro do quadrado**: Retângulo menor com o mapa real

---

## 🔍 CAUSA DO PROBLEMA

### Como o PGM é Gerado Atualmente:

1. **Bounding Box dos Pontos**:
   ```python
   min_xy = points_xy.min(axis=0) - padding  # Ponto mínimo - padding
   max_xy = points_xy.max(axis=0) + padding  # Ponto máximo + padding
   size = max_xy - min_xy  # Tamanho do grid
   ```

2. **Problema**:
   - O código usa os **pontos extremos** (min/max) dos map points
   - Se há map points nas **extremidades** (fora do retângulo real), o bounding box fica maior
   - Adiciona **padding** de 1.0m em todas as direções
   - Se os pontos extremos criarem um bounding box **quadrado**, o PGM será quadrado

### Exemplo:
- **Mapa real**: 12m (X) × 6m (Y)
- **Map points extremos**: 
  - X: de -10m a 2m (12m de largura) ✅
  - Y: de -11m a 9m (20m de altura) ❌ (maior que 6m!)
- **Com padding de 1.0m**:
  - X: 12m + 2m = 14m
  - Y: 20m + 2m = 22m
- **Resultado**: Grid de 14m × 22m (retangular, mas maior que o necessário)

**Mas se os pontos extremos forem simétricos:**
- X: de -10m a 10m (20m)
- Y: de -10m a 10m (20m)
- **Resultado**: Grid de 22m × 22m (QUADRADO!)

---

## 🎯 SOLUÇÕES POSSÍVEIS

### Opção 1: Filtrar Map Points Extremos (RECOMENDADO)
Remover map points que estão muito longe do centro antes de gerar o grid.

**Vantagens**:
- Mantém apenas pontos relevantes
- Gera mapa no tamanho real do ambiente
- Remove ruído/outliers

### Opção 2: Usar Tamanho Fixo
Gerar o mapa com tamanho fixo (12m × 6m) independente dos pontos.

**Vantagens**:
- Sempre gera mapa do tamanho correto
- Não depende de map points extremos

**Desvantagens**:
- Pode cortar pontos válidos se o ambiente for maior
- Precisa conhecer o tamanho exato do ambiente

### Opção 3: Reduzir Padding
Reduzir o `padding_m` de 1.0m para 0.2m ou 0.5m.

**Vantagens**:
- Simples de implementar
- Reduz área vazia

**Desvantagens**:
- Ainda depende dos pontos extremos
- Pode não resolver se os pontos extremos forem muito distantes

---

## 📋 ANÁLISE DO CÓDIGO ATUAL

### Função `_points_to_grid`:
```python
min_xy = points_xy.min(axis=0) - padding  # Linha 150
max_xy = points_xy.max(axis=0) + padding  # Linha 151
size = max_xy - min_xy                    # Linha 152
```

**Problema**: Usa TODOS os pontos, incluindo outliers/extremos.

### Configuração Atual:
```json
"map2d": {
  "padding_m": 1.0,  // 1 metro de padding em todas as direções
  ...
}
```

---

## ✅ RECOMENDAÇÃO

### Implementar Filtro de Outliers:
1. Calcular centro dos pontos (mediana ou média)
2. Calcular distância de cada ponto ao centro
3. Remover pontos muito distantes (ex: > 2 desvios padrão)
4. Gerar grid apenas com pontos filtrados

Isso garantirá que:
- O mapa seja gerado baseado nos pontos relevantes
- O tamanho seja próximo do ambiente real
- Map points extremos não afetem o tamanho

---

## 🔧 PRÓXIMOS PASSOS

1. **Analisar os map points**: Verificar se há pontos muito distantes
2. **Implementar filtro**: Adicionar filtro de outliers antes de gerar o grid
3. **Testar**: Gerar novo mapa e verificar se fica retangular (12m × 6m)

---

**O problema é que o código usa TODOS os map points, incluindo outliers nas extremidades!**

