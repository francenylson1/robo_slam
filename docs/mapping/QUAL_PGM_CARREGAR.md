# 📍 Qual Arquivo .pgm Carregar no main.py?

**Data**: 25/11/2025

---

## 🎯 RESPOSTA RÁPIDA

### ✅ **Use o arquivo da pasta `map2d/`**

**Caminho correto:**
```
data/pipeline_runs/SEU_MAPA/map2d/SEU_MAPA_clean.pgm
data/pipeline_runs/SEU_MAPA/map2d/SEU_MAPA_clean.yaml
```

---

## 📁 ONDE OS ARQUIVOS SÃO GERADOS

### Pasta `map2d/` (ORIGINAL - Use este!)
```
data/pipeline_runs/SEU_MAPA/map2d/
├── SEU_MAPA_clean.pgm    ✅ ORIGINAL - Use este!
└── SEU_MAPA_clean.yaml   ✅ ORIGINAL - Use este!
```

**Quando é gerado**: Durante a etapa `map2d` do pipeline  
**O que contém**: Mapa 2D gerado diretamente do point cloud refinado  
**Status**: ⭐ **ARQUIVO PRINCIPAL**

---

### Pasta `annotation/` (CÓPIA - Opcional)
```
data/pipeline_runs/SEU_MAPA/annotation/
├── SEU_MAPA_clean.pgm    ⚠️ CÓPIA (mesmo arquivo)
├── SEU_MAPA_clean.yaml   ⚠️ CÓPIA (mesmo arquivo)
└── SEU_MAPA_clean_pois.json
```

**Quando é gerado**: Durante a etapa `annotation` do pipeline  
**O que contém**: Cópia do `.pgm` e `.yaml` + arquivo de POIs  
**Status**: ⚠️ **CÓPIA** (para referência durante anotação)

---

## 🔍 POR QUE EXISTEM DUAS PASTAS?

### Fluxo do Pipeline:

```
1. map2d/ → Gera .pgm + .yaml (ORIGINAL)
   ↓
2. annotation/ → Copia .pgm + .yaml + cria _pois.json
   ↓
3. export/ → Empacota tudo para deploy
```

**Razão**: A pasta `annotation/` copia os arquivos para facilitar a edição de POIs, mas o arquivo original (e correto) está em `map2d/`.

---

## ✅ QUAL USAR?

### Use `map2d/` (Recomendado)

**Vantagens:**
- ✅ Arquivo original gerado pelo pipeline
- ✅ Garantia de que é a versão mais atual
- ✅ Estrutura padrão do pipeline

**Caminho:**
```
data/pipeline_runs/SEU_MAPA/map2d/SEU_MAPA_clean.pgm
```

---

### Pode usar `annotation/` (Funciona, mas não recomendado)

**Quando usar:**
- ⚠️ Se você já está trabalhando na pasta `annotation/`
- ⚠️ Se quiser manter tudo junto com os POIs

**Caminho:**
```
data/pipeline_runs/SEU_MAPA/annotation/SEU_MAPA_clean.pgm
```

**Nota**: É o mesmo arquivo, mas é uma cópia. Prefira usar o original em `map2d/`.

---

## 🎯 COMO CARREGAR NA INTERFACE

### Opção 1: Lista de Mapas (Automático)

1. Clique em **"🗺️ Carregar PGM"** na interface
2. Se aparecer uma lista, selecione o mapa desejado
3. A interface procura automaticamente em:
   - `mapas/otimizados/`
   - `data/pipeline_runs/*/map2d/`
   - `data/pipeline_runs/*/annotation/`

---

### Opção 2: Navegar Manualmente

1. Clique em **"🗺️ Carregar PGM"**
2. Se não aparecer lista, clique em **"Cancelar"** ou **"Abrir arquivo..."**
3. Navegue até: `data/pipeline_runs/SEU_MAPA/map2d/`
4. Selecione o arquivo `.pgm`
5. O arquivo `.yaml` será carregado automaticamente (se estiver na mesma pasta)

---

## 📋 RESUMO

| Pasta | Arquivo | Quando Usar |
|-------|---------|-------------|
| **`map2d/`** | ✅ **ORIGINAL** | ⭐ **SEMPRE** (recomendado) |
| `annotation/` | ⚠️ CÓPIA | Apenas se já estiver trabalhando lá |

---

## 🔧 CORREÇÃO APLICADA

A interface do `main.py` foi atualizada para:

1. ✅ Procurar mapas em múltiplas pastas automaticamente
2. ✅ Mostrar lista de mapas encontrados
3. ✅ Permitir navegação manual para qualquer pasta
4. ✅ Carregar `.yaml` automaticamente quando encontrar `.pgm`

**Agora você pode carregar mapas de qualquer pasta!** 🎉

---

## 💡 DICA

**Sempre use o arquivo de `map2d/`** - é o original e garante que você está usando a versão mais atual do mapa gerado pelo pipeline.

