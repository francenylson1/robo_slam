# 📐 Configuração de Resolução - Aurora Mapping Studio

## 🔍 Relação entre Resolução do Aurora e Parâmetros do Pipeline

### Resolução do Aurora

O **Aurora Remote** permite configurar a **resolução do mapa** durante a geração:

- **Range**: 0.01m a 0.50m (1cm a 50cm)
- **Padrão recomendado**: 0.050m (5cm)
- **Max map size**: 500,000 x 500,000 pixels

### Impacto nos Parâmetros do Pipeline

A resolução do Aurora **afeta diretamente** os parâmetros de processamento:

#### 1. **Voxel Size (Refinement)**

O `voxel_size` usado no downsample da nuvem **deve ser compatível** com a resolução do Aurora:

| Resolução Aurora | Voxel Size Recomendado | Observação |
|-----------------|----------------------|------------|
| 0.01m (1cm) | 0.01m - 0.02m | Alta resolução, muitos pontos, processamento lento |
| **0.02m (2cm)** | **0.02m - 0.03m** | **Alta resolução, boa qualidade, processamento moderado** ⭐ |
| 0.05m (5cm) | 0.05m - 0.10m | **Padrão recomendado, equilíbrio qualidade/performance** |
| 0.10m (10cm) | 0.10m - 0.20m | Resolução média, processamento rápido |
| 0.50m (50cm) | 0.50m - 1.00m | Baixa resolução, menos pontos |

**⚠️ Regra importante:**
- `voxel_size` **não deve ser menor** que a resolução do Aurora
- Idealmente: `voxel_size >= aurora_resolution`
- Se menor, o sistema ajusta automaticamente (com aviso)

#### 2. **Map2D Resolution**

A resolução do mapa 2D final **deve corresponder** à resolução do Aurora:

```json
{
  "map2d": {
    "resolution_m": 0.05  // ← Deve ser igual à resolução do Aurora
  }
}
```

#### 3. **Plane Distance Threshold**

O threshold para remoção de plano também deve ser ajustado:

```json
{
  "refinement": {
    "plane_distance_threshold": 0.05  // ← Geralmente igual à resolução do Aurora
  }
}
```

---

## ⚙️ Configuração Recomendada

### Para Resolução Aurora = 0.02m (2cm) - **ALTA RESOLUÇÃO** ⭐

```json
{
  "refinement": {
    "aurora_resolution": 0.02,
    "voxel_size": 0.02,
    "plane_distance_threshold": 0.02,
    "auto_adjust_voxel_size": true,
    "statistical_nb_neighbors": 25,
    "statistical_std_ratio": 1.5
  },
  "map2d": {
    "resolution_m": 0.02
  }
}
```

**Vantagens:**
- ✅ Maior precisão e detalhamento do mapa
- ✅ Melhor detecção de obstáculos pequenos
- ✅ Mapas mais nítidos

**Desvantagens:**
- ⚠️ Mais pontos para processar (pode ser mais lento)
- ⚠️ Arquivos maiores
- ⚠️ Requer mais memória

**Quando usar:**
- Ambientes com muitos detalhes
- Quando precisar de alta precisão
- Quando o processamento mais lento é aceitável

**Uso rápido:**
```bash
python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora \
  --output data/pipeline_runs/meu_mapa \
  --metadata config/mapping_high_resolution.json
```

### Para Resolução Aurora = 0.05m (5cm) - **PADRÃO**

```json
{
  "refinement": {
    "aurora_resolution": 0.05,
    "voxel_size": 0.05,
    "plane_distance_threshold": 0.05,
    "auto_adjust_voxel_size": true
  },
  "map2d": {
    "resolution_m": 0.05
  }
}
```

### Para Resolução Aurora = 0.01m (1cm) - Alta Resolução

```json
{
  "refinement": {
    "aurora_resolution": 0.01,
    "voxel_size": 0.01,
    "plane_distance_threshold": 0.01,
    "auto_adjust_voxel_size": true
  },
  "map2d": {
    "resolution_m": 0.01
  }
}
```

**⚠️ Atenção:** Alta resolução gera mais pontos e requer mais processamento.

### Para Resolução Aurora = 0.10m (10cm) - Resolução Média

```json
{
  "refinement": {
    "aurora_resolution": 0.10,
    "voxel_size": 0.10,
    "plane_distance_threshold": 0.10,
    "auto_adjust_voxel_size": true
  },
  "map2d": {
    "resolution_m": 0.10
  }
}
```

---

## 🔧 Como Ajustar

### 1. Verificar Resolução do Aurora

No **Aurora Remote**, verifique a configuração:
- Vá em **Settings** → **Map Resolution**
- Anote o valor configurado (ex: 0.050)

### 2. Atualizar `config/mapping.json`

Edite o arquivo e ajuste os valores:

```json
{
  "refinement": {
    "aurora_resolution": 0.050,  // ← Valor do Aurora
    "voxel_size": 0.050,          // ← Igual ou ligeiramente maior
    "plane_distance_threshold": 0.050
  },
  "map2d": {
    "resolution_m": 0.050         // ← Igual à resolução do Aurora
  }
}
```

### 3. Usar Metadados Customizados

Crie um arquivo JSON com configurações específicas:

```json
{
  "refinement": {
    "aurora_resolution": 0.05,
    "voxel_size": 0.05
  },
  "map2d": {
    "resolution_m": 0.05
  }
}
```

Execute com:
```bash
python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora \
  --output data/pipeline_runs/meu_mapa \
  --metadata meu_config.json
```

---

## 🐛 Problemas Comuns

### Erro: "voxel_size is too small"

**Causa:** `voxel_size` menor que a escala real dos pontos na nuvem.

**Solução:**
1. Verifique a resolução configurada no Aurora
2. Ajuste `voxel_size` para ser >= `aurora_resolution`
3. Ou habilite `auto_adjust_voxel_size: true`

### Mapa com baixa qualidade

**Causa:** Resolução do Aurora muito baixa ou parâmetros incompatíveis.

**Solução:**
1. Aumente a resolução no Aurora (0.05m é recomendado)
2. Ajuste `voxel_size` e `resolution_m` para corresponder
3. Verifique se `plane_distance_threshold` está adequado

### Processamento muito lento

**Causa:** Resolução muito alta gera muitos pontos.

**Solução:**
1. Use resolução de 0.05m (padrão) ao invés de 0.01m
2. Aumente `voxel_size` para reduzir pontos processados
3. Ajuste `statistical_nb_neighbors` para valores menores

---

## 📊 Tabela de Referência Rápida

| Resolução Aurora | Voxel Size | Map2D Resolution | Pontos Esperados* | Qualidade | Performance |
|-----------------|-----------|------------------|-------------------|-----------|-------------|
| 0.01m (1cm) | 0.01m | 0.01m | Muito alto | Excelente | Lenta |
| **0.02m (2cm)** | **0.02m** | **0.02m** | **Alto** | **Muito Boa** ⭐ | **Moderada** |
| 0.05m (5cm) | 0.05m | 0.05m | Médio | Boa | Rápida |
| 0.10m (10cm) | 0.10m | 0.10m | Baixo | Média | Muito Rápida |
| 0.50m (50cm) | 0.50m | 0.50m | Muito baixo | Baixa | Muito Rápida |

*Para um ambiente de ~100m²

---

## ✅ Checklist

Antes de processar um mapa, verifique:

- [ ] Resolução configurada no Aurora Remote
- [ ] `aurora_resolution` em `config/mapping.json` corresponde
- [ ] `voxel_size` >= `aurora_resolution`
- [ ] `map2d.resolution_m` = `aurora_resolution`
- [ ] `plane_distance_threshold` ≈ `aurora_resolution`

---

## 📚 Referências

- [Guia de Uso Inicial](GUIA_USO_INICIAL.md)
- [Fluxo Completo Aurora → C1](FLUXO_COMPLETO_AURORA_C1.md)
- Documentação do Aurora Remote

