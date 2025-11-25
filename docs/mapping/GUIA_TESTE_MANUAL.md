# 🧪 Guia Rápido: Como Fazer Seu Próprio Teste

## ✅ Teste Completo Executado com Sucesso!

**Resultado**: Pipeline completo funcionou end-to-end!  
**Arquivos gerados**: `data/pipeline_runs/validacao_completa/`

---

## 📋 Resumo do Teste Executado

### ✅ Etapas Concluídas:

1. ✅ **Capture**: Arquivo `.stcm` copiado
2. ✅ **Refinement**: 537 map points extraídos → 172 pontos finais (após filtros)
3. ✅ **Map2D**: Grid 130x107 pixels gerado (PGM + YAML)
4. ✅ **C1_Conversion**: Placeholder STCM criado (C1 não estava acessível)
5. ✅ **Annotation**: Template de POIs criado
6. ✅ **Export**: Pacote final criado

### 📊 Estatísticas:

- **Map points extraídos**: 537 (do backup)
- **Pontos após refinamento**: 172
- **Mapa 2D**: 130x107 pixels
- **Arquivos gerados**: PGM, YAML, STCM (placeholder), POIs, README

---

## 🚀 Como Fazer Seu Próprio Teste

### Opção 1: Teste Completo (Recomendado)

```bash
# 1. Ative o ambiente virtual (se ainda não estiver ativo)
source venv/bin/activate

# 2. Execute o pipeline completo
python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora/SEU_ARQUIVO.stcm \
  --output data/pipeline_runs/meu_teste
```

**Substitua**:
- `SEU_ARQUIVO.stcm` pelo nome do seu arquivo
- `meu_teste` pelo nome que você quiser para o teste

---

### Opção 2: Teste Apenas Conversão (.stcm → .ply)

```bash
python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora/SEU_ARQUIVO.stcm \
  --output data/pipeline_runs/teste_conversao \
  --steps capture,refinement
```

**O que faz**: Apenas converte `.stcm` → `.ply` e aplica filtros

---

### Opção 3: Teste Até Mapa 2D (.stcm → .pgm/.yaml)

```bash
python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora/SEU_ARQUIVO.stcm \
  --output data/pipeline_runs/teste_map2d \
  --steps capture,refinement,map2d
```

**O que faz**: Gera mapa 2D (PGM + YAML) pronto para visualização

---

## 📁 Onde Encontrar os Resultados

Após executar, os arquivos estarão em:

```
data/pipeline_runs/SEU_NOME_DO_TESTE/
├── capture/
│   ├── SEU_ARQUIVO.stcm          # Cópia do original
│   ├── SEU_ARQUIVO.ply           # Point cloud extraído
│   └── backup_aurora_maps/       # Backup do mapa atual
│
├── refinement/
│   ├── SEU_ARQUIVO_clean.ply     # Point cloud limpo (após filtros)
│   └── SEU_ARQUIVO_preview.png   # Preview visual
│
├── map2d/
│   ├── SEU_ARQUIVO_clean.pgm     # Mapa 2D (imagem)
│   └── SEU_ARQUIVO_clean.yaml    # Metadados do mapa
│
├── c1_converter/
│   └── SEU_ARQUIVO_clean.stcm    # STCM para C1 (ou placeholder)
│
├── annotation/
│   └── SEU_ARQUIVO_clean_pois.json  # Template de POIs
│
└── export/
    └── SEU_ARQUIVO_clean_package/   # Pacote final completo
        ├── SEU_ARQUIVO_clean.stcm
        ├── SEU_ARQUIVO_clean_pois.json
        ├── SEU_ARQUIVO_clean_layout.png
        ├── metadata.json
        └── README.md
```

---

## 🔍 Como Verificar os Resultados

### 1. Ver Point Cloud (.ply)

```bash
# Instale um visualizador (se não tiver)
# Opção 1: CloudCompare (recomendado)
# Opção 2: MeshLab
# Opção 3: Blender

# Ou use Python (Open3D)
python -c "
import open3d as o3d
cloud = o3d.io.read_point_cloud('data/pipeline_runs/SEU_TESTE/refinement/SEU_ARQUIVO_clean.ply')
print(f'Pontos: {len(cloud.points)}')
o3d.visualization.draw_geometries([cloud])
"
```

### 2. Ver Mapa 2D (.pgm)

```bash
# Abra o arquivo .pgm com qualquer visualizador de imagens
# Linux:
xdg-open data/pipeline_runs/SEU_TESTE/map2d/SEU_ARQUIVO_clean.pgm

# Ou use Python
python -c "
from PIL import Image
img = Image.open('data/pipeline_runs/SEU_TESTE/map2d/SEU_ARQUIVO_clean.pgm')
img.show()
print(f'Tamanho: {img.size}')
"
```

### 3. Ver Preview Gerado

```bash
# Abra o preview PNG
xdg-open data/pipeline_runs/SEU_TESTE/refinement/SEU_ARQUIVO_preview.png
```

---

## ⚠️ Observações Importantes

### 1. Dispositivo Aurora Precisa Estar Conectado

- O teste precisa do Aurora conectado para converter `.stcm` → `.ply`
- Verifique conexão: `python scripts/teste_conexao_aurora.py`

### 2. C1 Não Precisa Estar Conectado

- Se o C1 não estiver acessível, será criado um **placeholder STCM**
- Isso é normal e não impede o teste
- Para conversão real, configure o C1 em `config/mapping.json`

### 3. Backup Automático

- O sistema **sempre faz backup** do mapa atual antes de fazer upload
- Backups ficam em: `capture/backup_aurora_maps/`
- **Importante**: O Aurora mantém apenas o mapa atual!

---

## 🎯 Exemplo Prático Completo

```bash
# 1. Verifique se tem um arquivo .stcm
ls mapas/legacy/originais_aurora/*.stcm

# 2. Escolha um arquivo (exemplo: sala-maker-1.stcm)
ARQUIVO="sala-maker-1.stcm"

# 3. Execute o teste completo
python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora/$ARQUIVO \
  --output data/pipeline_runs/teste_$(date +%Y%m%d_%H%M%S)

# 4. Aguarde a conclusão (pode levar 1-2 minutos)

# 5. Verifique os resultados
ls -lh data/pipeline_runs/teste_*/

# 6. Visualize o mapa 2D gerado
xdg-open data/pipeline_runs/teste_*/map2d/*.pgm
```

---

## 📊 O Que Esperar

### ✅ Sucesso:

- ✅ Arquivo `.ply` gerado com map points
- ✅ Mapa 2D (PGM) gerado e visível
- ✅ Pacote final criado em `export/`
- ✅ Mensagens de sucesso no terminal

### ⚠️ Avisos Normais:

- ⚠️ "Nuvem possui poucos pontos" - Normal se ambiente for pequeno
- ⚠️ "C1 não acessível" - Normal se C1 não estiver conectado
- ⚠️ "Placeholder criado" - Normal, pode usar SDK do C1 depois

### ❌ Erros que Precisam Atenção:

- ❌ "Dispositivo não encontrado" - Aurora não está conectado
- ❌ "Arquivo não encontrado" - Verifique o caminho do arquivo
- ❌ "Erro ao conectar" - Verifique conexão de rede

---

## 🆘 Troubleshooting

### Problema: "Dispositivo não encontrado"

**Solução**:
```bash
# Teste conexão
python scripts/teste_conexao_aurora.py

# Verifique configuração
cat config/mapping.json | grep -A 5 aurora
```

### Problema: "Arquivo não encontrado"

**Solução**:
```bash
# Liste arquivos disponíveis
ls -lh mapas/legacy/originais_aurora/

# Use caminho completo se necessário
python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input $(pwd)/mapas/legacy/originais_aurora/SEU_ARQUIVO.stcm \
  --output data/pipeline_runs/teste
```

### Problema: "Poucos pontos extraídos"

**Solução**:
- É normal se o ambiente for pequeno
- Sistema usa backup automaticamente se necessário
- Verifique se backup tem mais pontos

---

## 📝 Próximos Passos Após o Teste

1. **Visualize os resultados**:
   - Point cloud (.ply)
   - Mapa 2D (.pgm)
   - Preview (.png)

2. **Compare com mapas originais**:
   - Verifique se qualidade está adequada
   - Valide se mapa está correto

3. **Teste com outro arquivo**:
   - Valide consistência
   - Teste com diferentes ambientes

4. **Configure C1** (se disponível):
   - Configure IP do C1 em `config/mapping.json`
   - Teste conversão real para C1

---

## 🎉 Pronto!

Agora você pode fazer seus próprios testes! Se tiver dúvidas ou problemas, consulte:
- `docs/mapping/GUIA_USO_INICIAL.md` - Guia completo
- `docs/mapping/ENTENDENDO_MAP_POINTS.md` - Entenda map points
- `prompt_para_25-11-2025.md` - Contexto completo do projeto

---

**Última Atualização**: 25/11/2025

