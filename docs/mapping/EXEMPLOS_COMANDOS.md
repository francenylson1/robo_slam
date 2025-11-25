# 📝 Exemplos de Comandos - main_mapping.py

**Data**: 25/11/2025

---

## ⚠️ IMPORTANTE

**NÃO use `...` no comando!** Substitua por caminhos reais.

---

## 📋 ARQUIVOS DISPONÍVEIS

Arquivos encontrados em `mapas/legacy/originais_aurora/`:
- `sala-maker-1.stcm` (formato nativo do Aurora)
- `teste_rapido.ply` (nuvem de pontos)
- `demo_cloud.ply` (nuvem de pontos de teste)

---

## 🚀 EXEMPLOS DE COMANDOS

### Exemplo 1: Pipeline Completo com Arquivo .stcm

```bash
python3 src/main_mapping.py \
    --pipeline aurora_to_c1 \
    --input mapas/legacy/originais_aurora/sala-maker-1.stcm \
    --output data/pipeline_runs/2025-11-25
```

**O que faz:**
- Processa o arquivo `.stcm` completo
- Converte para `.ply` (precisa do Aurora conectado)
- Gera mapa 2D, converte para C1, etc.

---

### Exemplo 2: Pipeline Completo com Arquivo .ply

```bash
python3 src/main_mapping.py \
    --pipeline aurora_to_c1 \
    --input mapas/legacy/originais_aurora/teste_rapido.ply \
    --output data/pipeline_runs/2025-11-25
```

**O que faz:**
- Processa o arquivo `.ply` diretamente
- Pula a conversão `.stcm` → `.ply`
- Gera mapa 2D, converte para C1, etc.

---

### Exemplo 3: Pipeline Completo com Pasta

```bash
python3 src/main_mapping.py \
    --pipeline aurora_to_c1 \
    --input mapas/legacy/originais_aurora \
    --output data/pipeline_runs/2025-11-25
```

**O que faz:**
- Processa TODOS os arquivos `.stcm`, `.ply`, `.pcd` na pasta
- Cria um pipeline run para cada arquivo

---

### Exemplo 4: Apenas Passos Específicos

```bash
# Apenas gerar mapa 2D (pula capture e refinement)
python3 src/main_mapping.py \
    --pipeline aurora_to_c1 \
    --input data/pipeline_runs/2025-11-25/capture \
    --output data/pipeline_runs/2025-11-25-reprocesso \
    --steps map2d,export
```

**O que faz:**
- Pula `capture` e `refinement`
- Executa apenas `map2d` e `export`
- Útil para reprocessar sem reconverter

---

### Exemplo 5: Inventário de Mapas

```bash
python3 src/main_mapping.py \
    --pipeline inventory_snapshot \
    --input mapas \
    --output docs/mapping
```

**O que faz:**
- Gera inventário de todos os mapas
- Cria `inventario_mapas.json` e `inventario_mapas.md`

---

### Exemplo 6: Interface Gráfica

```bash
# Abrir GUI
python3 src/main_mapping.py --gui

# Ou simplesmente:
python3 src/main_mapping.py
```

---

## 🔧 COMANDOS ÚTEIS

### Verificar Arquivos Disponíveis

```bash
# Listar arquivos .stcm, .ply, .pcd
find mapas/legacy/originais_aurora -type f \( -name "*.stcm" -o -name "*.ply" -o -name "*.pcd" \)

# Listar todos os arquivos
ls -lh mapas/legacy/originais_aurora/
```

### Verificar Saída do Pipeline

```bash
# Listar pipeline runs
ls -lh data/pipeline_runs/

# Ver conteúdo de um pipeline run
ls -lh data/pipeline_runs/2025-11-25/
```

---

## ⚠️ ERROS COMUNS

### Erro: `FileNotFoundError: Nenhum arquivo com extensões [...] encontrado em ...`

**Causa:** Caminho incorreto ou arquivo não existe.

**Solução:**
1. Verifique se o caminho está correto:
   ```bash
   ls -lh mapas/legacy/originais_aurora/sala-maker-1.stcm
   ```

2. Use caminho absoluto se necessário:
   ```bash
   python3 src/main_mapping.py \
       --pipeline aurora_to_c1 \
       --input /home/amd/Área\ de\ trabalho/robo_slam/mapas/legacy/originais_aurora/sala-maker-1.stcm \
       --output data/pipeline_runs/2025-11-25
   ```

3. Verifique se o arquivo tem a extensão correta (`.stcm`, `.ply`, `.pcd`)

---

## 📚 REFERÊNCIAS

- `src/main_mapping.py --help` - Ajuda completa
- `docs/mapping/FLUXO_COMPLETO_AURORA_C1.md` - Fluxo completo
- `docs/mapping/GUIA_USO_INICIAL.md` - Guia de uso inicial

---

**Lembre-se: Substitua `...` por caminhos reais!**

