# 📊 Resumo da Análise de Qualidade

## ⚠️ PROBLEMAS IDENTIFICADOS

### 1. Cobertura do Mapa 2D Muito Baixa
- **Apenas 7.9%** do mapa tem informação
- **92.1%** é desconhecido
- **0%** de áreas livres (CRÍTICO para navegação)

### 2. Perda Excessiva de Área
- Point cloud original: **269 m²**
- Mapa 2D: **34.78 m²**
- **87% da área foi perdida**

### 3. Filtros Muito Agressivos
- Redução de **68%** (537 → 172 pontos)
- Muita informação útil removida

---

## ✅ AJUSTES APLICADOS

### Filtros Menos Agressivos:
- `voxel_size`: 0.05 → **0.08** (menos agressivo)
- `max_voxel_increase_factor`: 2.0 → **1.5** (limite menor)
- `statistical_nb_neighbors`: 20 → **15** (menos restritivo)
- `statistical_std_ratio`: 2.0 → **2.5** (menos agressivo)
- `plane_distance_threshold`: 0.05 → **0.08** (menos restritivo)

### Projeção 3D → 2D Melhorada:
- `padding_m`: 0.5 → **1.0** (mais margem)
- `height_min`: -0.2 → **-0.5** (mais range)
- `height_max`: 2.0 → **2.5** (mais range)
- `occupied_thresh`: 0.65 → **0.5** (mais sensível)
- `free_thresh`: 0.15 → **0.2** (melhor detecção de áreas livres)

---

## 🎯 PRÓXIMO PASSO

**Re-executar o pipeline** com os novos parâmetros e comparar resultados.

```bash
python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora/sala-maker-1.stcm \
  --output data/pipeline_runs/validacao_ajustada
```

---

## 📊 RESULTADOS ESPERADOS

| Métrica | Antes | Esperado (Ajustado) |
|---------|-------|---------------------|
| **Map Points (limpo)** | 172 | 300-400 |
| **Cobertura 2D** | 7.9% | 40-60% |
| **Áreas livres** | 0% | 30-50% |
| **Área coberta** | 24.5 m² | 150-200 m² |

