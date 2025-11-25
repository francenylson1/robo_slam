# 🚀 Guia de Uso Inicial - Aurora Mapping Studio

Este guia explica como começar a usar o Aurora Mapping Studio e realizar os primeiros testes.

---

## 📋 Pré-requisitos

### 1. Ambiente Python

Certifique-se de que o ambiente virtual está ativado e com as dependências instaladas:

```bash
# Ativar ambiente virtual (Linux/Mac)
source venv/bin/activate

# Ou no Windows
venv\Scripts\activate

# Verificar se Open3D está instalado
python -c "import open3d; print('Open3D OK')"
```

### 2. Estrutura de Pastas

O projeto deve ter a seguinte estrutura:

```
robo_slam/
├── src/
│   ├── main_mapping.py          # Entry point principal
│   └── aurora_mapping/          # Módulos do pipeline
├── config/
│   └── mapping.json             # Configurações
├── mapas/
│   ├── legacy/                  # Mapas antigos do Aurora
│   └── c1/                      # Mapas processados
└── data/
    └── pipeline_runs/           # Saídas dos pipelines
```

---

## 🧪 Teste 1: Inventário de Mapas (Mais Simples)

**Objetivo:** Verificar se o sistema está funcionando e listar mapas existentes.

### Comando:

```bash
venv/bin/python src/main_mapping.py \
  --pipeline inventory_snapshot \
  --input mapas \
  --output docs/mapping
```

### O que esperar:

- ✅ Arquivo `inventario_mapas.json` criado em `docs/mapping/`
- ✅ Arquivo `inventario_mapas.md` criado com tabela formatada
- ✅ Lista de todos os arquivos organizados por categoria

### Verificação:

```bash
# Ver o inventário gerado
cat docs/mapping/inventario_mapas.md
```

**Se funcionou:** Você verá uma tabela listando todos os mapas em `mapas/legacy/` e `mapas/c1/`.

---

## 🧪 Teste 2: Pipeline Completo (Aurora → C1)

**Objetivo:** Processar um mapa do Aurora até gerar o pacote final.

### Passo 1: Preparar dados de entrada

Certifique-se de ter pelo menos um arquivo `.ply` ou `.pcd` em `mapas/legacy/originais_aurora/`.

Se não tiver, crie um arquivo de teste:

```bash
# Criar nuvem de pontos sintética para teste
venv/bin/python - <<'PY'
import numpy as np
import open3d as o3d
from pathlib import Path

points = np.random.rand(15000, 3) * 10  # 15k pontos em área 10x10x10m
cloud = o3d.geometry.PointCloud()
cloud.points = o3d.utility.Vector3dVector(points)

Path('mapas/legacy/originais_aurora').mkdir(parents=True, exist_ok=True)
o3d.io.write_point_cloud('mapas/legacy/originais_aurora/teste_inicial.ply', cloud)
print('✅ Arquivo de teste criado: teste_inicial.ply')
PY
```

### Passo 2: Executar pipeline completo

```bash
venv/bin/python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora \
  --output data/pipeline_runs/teste_inicial \
  --steps capture,refinement,map2d,annotation,export
```

**Nota:** Estamos pulando `c1_conversion` porque requer SDK do C1 ou C1 conectado.

### O que esperar:

Você verá mensagens de progresso para cada etapa:

```
[Aurora → C1] Executando etapa 'capture'...
[capture] Copiado mapas/legacy/.../teste_inicial.ply → data/pipeline_runs/.../capture/teste_inicial.ply
[capture] Manifesto salvo em ...

[Aurora → C1] Executando etapa 'refinement'...
[refinement] Carregando nuvem ...
[refinement] Downsample voxel_size=0.02
[refinement] Remoção estatística de ruído ...
[refinement] Plano removido ...
[refinement] Nuvem limpa salva em ...
[refinement] Preview salvo em ...

[Aurora → C1] Executando etapa 'map2d'...
[map2d] Convertendo nuvem ...
[map2d] Grid salvo em .../teste_inicial_clean.pgm
[map2d] YAML salvo em .../teste_inicial_clean.yaml

[Aurora → C1] Executando etapa 'annotation'...
[annotation] Template de POIs criado ...
[annotation] Arquivo de POIs salvo: .../teste_inicial_clean_pois.json

[Aurora → C1] Executando etapa 'export'...
[export] Copiado POIs: ...
[export] Copiado preview: ...
[export] ✅ Pacote final criado em: .../export/teste_inicial_clean_package
```

### Passo 3: Verificar resultados

```bash
# Ver estrutura gerada
tree data/pipeline_runs/teste_inicial -L 3

# Ou listar arquivos
ls -R data/pipeline_runs/teste_inicial/
```

**Estrutura esperada:**

```
data/pipeline_runs/teste_inicial/
├── capture/
│   ├── teste_inicial.ply
│   └── capture_manifest.json
├── refinement/
│   ├── teste_inicial_clean.ply
│   └── teste_inicial_preview.png
├── map2d/
│   ├── teste_inicial_clean.pgm
│   └── teste_inicial_clean.yaml
├── annotation/
│   ├── teste_inicial_clean.pgm
│   ├── teste_inicial_clean.yaml
│   └── teste_inicial_clean_pois.json
└── export/
    └── teste_inicial_clean_package/
        ├── teste_inicial_clean_pois.json
        ├── teste_inicial_clean_layout.png
        ├── metadata.json
        └── README.md
```

### Verificar arquivos gerados:

```bash
# Ver preview do mapa 2D
# (Abra o arquivo PNG em um visualizador de imagens)
ls data/pipeline_runs/teste_inicial/refinement/*_preview.png

# Ver POIs gerados
cat data/pipeline_runs/teste_inicial/annotation/*_pois.json

# Ver metadados do pacote
cat data/pipeline_runs/teste_inicial/export/*/metadata.json
```

---

## 🧪 Teste 3: Executar Etapas Individuais

**Objetivo:** Testar cada etapa separadamente para debug.

### Apenas Captura:

```bash
venv/bin/python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora \
  --output data/pipeline_runs/teste_capture \
  --steps capture
```

### Apenas Refinamento:

```bash
venv/bin/python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora \
  --output data/pipeline_runs/teste_refinement \
  --steps capture,refinement
```

**Nota:** `refinement` precisa dos arquivos de `capture`, então inclua `capture` também.

### Apenas Map2D:

```bash
venv/bin/python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora \
  --output data/pipeline_runs/teste_map2d \
  --steps capture,refinement,map2d
```

---

## 🧪 Teste 4: Pipeline C1 Optimization

**Objetivo:** Processar um mapa já gerado no C1.

### Comando:

```bash
# Se você tem um arquivo PGM/YAML do C1
venv/bin/python src/main_mapping.py \
  --pipeline c1_optimization \
  --input mapas/c1/otimizados/sala-maker-1.pgm \
  --output data/pipeline_runs/otimizado
```

### O que esperar:

```
[C1 Optimization] Copiando mapa para otimização...
[C1 Optimization] Mapa copiado: sala-maker-1_optimized.pgm
[C1 Optimization] Template de POIs criado: sala-maker-1_pois.json
[C1 Optimization] ✅ Mapa otimizado salvo em: ...
```

---

## 🔧 Configuração Avançada

### Usar arquivo de metadados customizado:

Crie um arquivo JSON com configurações:

```json
{
  "refinement": {
    "voxel_size": 0.03,
    "statistical_nb_neighbors": 30
  },
  "map2d": {
    "resolution_m": 0.1,
    "dilation_pixels": 3
  },
  "c1_conversion": {
    "c1_ip": "192.168.1.101",
    "use_api": true
  }
}
```

Salve como `meu_config.json` e use:

```bash
venv/bin/python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora \
  --output data/pipeline_runs/teste \
  --metadata meu_config.json
```

---

## ⚠️ Troubleshooting

### Erro: "ModuleNotFoundError: No module named 'open3d'"

**Solução:**
```bash
venv/bin/python -m pip install open3d
```

### Erro: "Nenhum arquivo de nuvem encontrado"

**Causa:** Não há arquivos `.ply` ou `.pcd` na pasta de entrada.

**Solução:** 
- Verifique se há arquivos na pasta `--input`
- Ou crie um arquivo de teste (veja Teste 2, Passo 1)

### Erro: "malloc(): invalid size (unsorted)"

**Causa:** Bug conhecido do Open3D com `select_by_index` em algumas versões.

**Solução:** Já corrigido no código. Se persistir, tente:
```bash
venv/bin/python -m pip install --upgrade open3d
```

### Pipeline para na etapa c1_conversion

**Causa:** Requer SDK do C1 ou C1 conectado.

**Solução:** 
- Pule essa etapa: `--steps capture,refinement,map2d,annotation,export`
- Ou configure o SDK em `config/mapping.json`:
```json
{
  "c1_conversion": {
    "use_sdk": true,
    "sdk_path": "/caminho/para/sdk/c1_convert"
  }
}
```

### Arquivos não são copiados na etapa capture

**Causa:** Arquivos já existem e `overwrite: false`.

**Solução:**
- Delete a pasta de saída: `rm -rf data/pipeline_runs/teste`
- Ou configure em metadados: `{"capture": {"overwrite": true}}`

---

## ✅ Checklist de Validação

Após executar os testes, verifique:

- [ ] Inventário gerado com sucesso
- [ ] Pipeline completo executa sem erros
- [ ] Arquivos `.ply` são processados corretamente
- [ ] Preview PNG é gerado
- [ ] Arquivos PGM/YAML são criados
- [ ] POIs JSON é gerado
- [ ] Pacote final contém todos os arquivos
- [ ] README.md no pacote está completo

---

## 📚 Próximos Passos

1. **Processar mapas reais do Aurora:**
   - Exporte mapas do Aurora em formato PLY/PCD
   - Coloque em `mapas/legacy/originais_aurora/`
   - Execute o pipeline completo

2. **Editar POIs:**
   - Abra o arquivo `*_pois.json` gerado
   - Adicione mesas, destinos, áreas proibidas
   - Formato JSON é autoexplicativo

3. **Integrar com C1:**
   - Configure IP do C1 em `config/mapping.json`
   - Execute com etapa `c1_conversion` incluída
   - Ou faça upload manual via interface do C1

4. **Automatizar:**
   - Crie scripts shell para rotinas frequentes
   - Use `--metadata` para diferentes configurações
   - Integre com seu fluxo de trabalho

---

## 📞 Suporte

Para problemas ou dúvidas:
- Consulte `docs/mapping/FLUXO_COMPLETO_AURORA_C1.md`
- Verifique logs de erro no terminal
- Revise `config/mapping.json` para configurações

---

**Boa sorte com seus mapas! 🗺️**

