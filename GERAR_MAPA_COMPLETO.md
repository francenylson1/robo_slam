# 🗺️ Como Gerar um Mapa Completo do C1

## 🎯 Objetivo

Gerar um mapa completo e detalhado do ambiente para testar:
- ✅ Gerenciamento de POIs
- ✅ Áreas proibidas
- ✅ Percursos de navegação

---

## 🚀 Método Rápido (Recomendado)

Execute o script automatizado:

```bash
# Coleta por 60 segundos (padrão)
./scripts/gerar_mapa_completo.sh

# Ou especifique a duração (em segundos)
./scripts/gerar_mapa_completo.sh 120  # 2 minutos
```

---

## 📋 Método Manual (Passo a Passo)

### 1️⃣ Coletar Scans

**IMPORTANTE**: Durante a coleta, mova o C1 lentamente pelo ambiente para mapear uma área maior.

```bash
# Coleta por 60 segundos (recomendado para mapa completo)
python3 src/main_c1_mapping.py collect \
  --duration 60 \
  --output mapas/c1/completo/raw \
  --full-scans
```

**Dicas**:
- ⏱️ **Duração mínima**: 30 segundos (mapa básico)
- ⏱️ **Duração recomendada**: 60-120 segundos (mapa completo)
- 🚶 **Movimento**: Mova o C1 lentamente em linha reta ou círculos
- 📍 **Área**: Quanto maior a área mapeada, melhor o mapa

### 2️⃣ Processar Scans

```bash
# Encontre o arquivo de scans mais recente
SCAN_FILE=$(ls -t mapas/c1/completo/raw/scans_*.json | head -1)

# Processa os scans
python3 src/main_c1_mapping.py process \
  --input "$SCAN_FILE" \
  --output mapas/c1/completo/processed \
  --resolution 0.05
```

### 3️⃣ Exportar Mapa

```bash
# Encontre o arquivo de mapa mais recente
MAP_FILE=$(ls -t mapas/c1/completo/processed/map_*.npy | head -1)

# Exporta em PGM/YAML
python3 src/main_c1_mapping.py export \
  --map "$MAP_FILE" \
  --output mapas/c1/completo/final \
  --name mapa_completo
```

---

## ✅ Verificar o Mapa Gerado

```bash
# Lista arquivos gerados
ls -lh mapas/c1/completo/final/*.{pgm,yaml}

# Verifica informações do mapa
cat mapas/c1/completo/final/mapa_completo.yaml
```

---

## 🎮 Usar o Mapa no main.py

1. **Abra a interface**:
   ```bash
   python3 src/main.py
   ```

2. **Carregue o mapa**:
   - Clique em "🗺️ Carregar PGM"
   - Selecione: `mapas/c1/completo/final/mapa_completo.pgm`

3. **Teste funcionalidades**:
   - ✅ Adicionar POIs (clique no mapa)
   - ✅ Criar áreas proibidas (desenhe polígonos)
   - ✅ Criar percursos (navegação)

---

## 📊 Qualidade do Mapa

### Mapa Básico (30s)
- ✅ Área pequena (2-3 metros)
- ✅ Poucos detalhes
- ✅ Bom para testes rápidos

### Mapa Completo (60-120s)
- ✅ Área maior (5-10 metros)
- ✅ Mais detalhes e obstáculos
- ✅ Ideal para testes de POIs e áreas proibidas

### Mapa Detalhado (120s+)
- ✅ Área muito grande (10+ metros)
- ✅ Muitos detalhes
- ✅ Ideal para ambientes complexos

---

## 🔧 Troubleshooting

### Mapa muito pequeno ou vazio
- **Solução**: Aumente a duração da coleta (--duration 120)
- **Solução**: Mova o C1 mais lentamente durante a coleta

### Mapa com muitos ruídos
- **Solução**: O processamento já aplica filtros automáticos
- **Solução**: Colete mais scans para melhorar a qualidade

### Arquivos não encontrados
- **Solução**: Verifique se os diretórios foram criados
- **Solução**: Execute os comandos na ordem correta

---

## 📁 Estrutura de Arquivos Gerados

```
mapas/c1/completo/
├── raw/
│   └── scans_*.json          # Scans coletados
├── processed/
│   ├── map_*.npy             # Mapa processado
│   └── map_*_metadata.json   # Metadados
└── final/
    ├── mapa_completo.pgm     # ⭐ Mapa final (usar no main.py)
    └── mapa_completo.yaml    # ⭐ Metadados (usar no main.py)
```

---

**Data**: 28/11/2025  
**Versão**: 1.0

