# 🔧 Erro: Pontos Colineares (Y range = 0)

**Data**: 25/11/2025

---

## 🐛 ERRO

```
ValueError: Pontos são colineares (X range: 0.000491, Y range: 0.000000). 
Não é possível gerar mapa 2D válido.
```

---

## 🔍 CAUSA

O erro indica que **todos os pontos têm a mesma coordenada Y** após o filtro de altura. Isso pode acontecer por:

1. **Problema na conversão `.stcm` → `.ply`**:
   - Os map points podem estar todos em um plano horizontal
   - A extração do SDK pode ter falhado parcialmente

2. **Filtro de altura muito restritivo**:
   - O intervalo `height_min` a `height_max` pode estar capturando apenas uma linha de pontos
   - Todos os pontos filtrados estão na mesma altura (mesmo Y)

3. **Nuvem de pontos corrompida ou incompleta**:
   - A nuvem pode ter sido filtrada incorretamente no passo de refinement
   - Pode haver um problema na captura original

---

## ✅ SOLUÇÕES

### Solução 1: Ajustar Filtro de Altura (MAIS COMUM)

O filtro de altura pode estar muito restritivo. Ajuste em `config/mapping.json`:

```json
{
  "map2d": {
    "height_min": -1.0,   // Reduzir (mais negativo)
    "height_max": 3.0     // Aumentar (mais positivo)
  }
}
```

**Como descobrir os valores corretos:**
- Execute o pipeline novamente - agora ele mostrará diagnóstico detalhado:
  ```
  [map2d] Diagnóstico da nuvem:
  [map2d]   Altura (Z) - Min: X.XXXm, Max: Y.YYYm, Mediana: Z.ZZZm
  ```
- Use esses valores para ajustar `height_min` e `height_max`

### Solução 2: Verificar Conversão `.stcm` → `.ply`

Se o problema for na conversão, verifique:

1. **Aurora conectado?**
   - O passo `refinement` precisa do Aurora conectado para converter `.stcm`
   - Verifique: `config/mapping.json` → `aurora.enabled: true`

2. **Reexecutar refinement:**
   ```bash
   python3 src/main_mapping.py \
       --pipeline aurora_to_c1 \
       --input mapas/legacy/originais_aurora/seu-mapa.stcm \
       --output data/pipeline_runs/novo-teste \
       --steps refinement,map2d
   ```

3. **Verificar arquivo `.ply` gerado:**
   - Abra o arquivo em `data/pipeline_runs/.../refinement/*_clean.ply`
   - Use um visualizador de nuvem de pontos (MeshLab, CloudCompare)
   - Verifique se os pontos estão distribuídos em 3D

### Solução 3: Usar Arquivo `.ply` Diretamente

Se você já tem um arquivo `.ply` válido:

```bash
python3 src/main_mapping.py \
    --pipeline aurora_to_c1 \
    --input mapas/legacy/originais_aurora/seu-mapa.ply \
    --output data/pipeline_runs/novo-teste \
    --steps map2d
```

---

## 🔧 MELHORIAS IMPLEMENTADAS

### Diagnóstico Automático

Agora o sistema mostra informações detalhadas antes de falhar:

```
[map2d] Diagnóstico da nuvem:
[map2d]   Total de pontos: X,XXX
[map2d]   Altura (Z) - Min: X.XXXm, Max: Y.YYYm, Mediana: Z.ZZZm
[map2d]   Range X: A.AAAm
[map2d]   Range Y: B.BBBm
[map2d] Filtro de altura: Z entre X.XXXm e Y.YYYm
[map2d] Pontos após filtro de altura: X,XXX (XX.X%)
[map2d] Range após filtro: X=A.AAAm, Y=B.BBBm
```

### Sugestões Automáticas

Se o erro ocorrer, o sistema sugere:
- Valores ajustados para `height_min` e `height_max`
- Ações para verificar a nuvem de pontos
- Possíveis causas do problema

---

## 📋 EXEMPLO DE CORREÇÃO

### Antes (erro):
```json
{
  "map2d": {
    "height_min": -0.5,
    "height_max": 2.5
  }
}
```

### Depois (corrigido):
```json
{
  "map2d": {
    "height_min": -1.0,   // Ajustado baseado no diagnóstico
    "height_max": 3.0     // Ajustado baseado no diagnóstico
  }
}
```

---

## 🔍 DEBUGGING

### 1. Verificar Nuvem Original

```bash
# Listar arquivos gerados
ls -lh data/pipeline_runs/*/refinement/*.ply

# Verificar tamanho (arquivo muito pequeno = problema)
du -h data/pipeline_runs/*/refinement/*_clean.ply
```

### 2. Verificar Logs do Refinement

Procure por mensagens como:
- `[refinement] X pontos encontrados`
- `[refinement] X pontos válidos`
- `[refinement] Removidos X pontos outliers`

### 3. Testar com Arquivo Diferente

Se o problema persistir, teste com outro mapa:
```bash
python3 src/main_mapping.py \
    --pipeline aurora_to_c1 \
    --input mapas/legacy/originais_aurora/outro-mapa.stcm \
    --output data/pipeline_runs/teste-alternativo
```

---

## ⚠️ NOTAS IMPORTANTES

1. **Filtro de altura padrão**: `height_min: -0.5m, height_max: 2.5m`
   - Isso captura pontos do chão até ~2.5m de altura
   - Se seu ambiente tiver pontos fora desse intervalo, ajuste!

2. **Conversão `.stcm`**: Requer Aurora conectado
   - Verifique se o Aurora está online: `ping 192.168.11.1`
   - Verifique configuração: `config/mapping.json` → `aurora`

3. **Nuvem vazia ou corrompida**: 
   - Pode indicar problema na captura original
   - Tente reexportar o mapa do Aurora

---

## 📚 REFERÊNCIAS

- `config/mapping.json` - Configurações do pipeline
- `docs/mapping/FLUXO_COMPLETO_AURORA_C1.md` - Fluxo completo
- `docs/mapping/CONVERSAO_STCM_SDK_AURORA.md` - Conversão .stcm

---

**Execute novamente o pipeline - agora você verá diagnóstico detalhado que ajudará a identificar o problema!**

