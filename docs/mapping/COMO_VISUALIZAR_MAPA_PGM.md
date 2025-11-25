# 🗺️ Como Visualizar Mapa PGM (Imagem 2D) no main.py

**Data**: 25/11/2025

---

## ⚠️ PROBLEMA

Ao executar `main.py` e carregar um mapa, você está vendo **nuvens de pontos** ou **grid vazio** ao invés do **mapa 2D (imagem PGM)**.

---

## ✅ SOLUÇÃO

### Use o Botão Correto: **"🗺️ Carregar PGM"**

Existem **DOIS botões diferentes** para carregar mapas:

1. **"📂 Carregar"** (botão antigo):
   - Carrega mapas **legados** do banco de dados
   - **NÃO mostra imagem PGM**
   - Mostra apenas pontos de interesse e áreas proibidas
   - ⚠️ **NÃO USE** para mapas do pipeline Aurora

2. **"🗺️ Carregar PGM"** (botão novo):
   - Carrega mapas **PGM** (imagem 2D) gerados pelo pipeline
   - **Mostra a imagem do mapa** como fundo
   - ✅ **USE ESTE** para mapas do pipeline Aurora

---

## 📋 PASSO A PASSO

### 1. Execute o main.py

```bash
python3 src/main.py
```

### 2. Ao Abrir, Selecione "Carregar PGM"

Quando a interface abrir, uma janela aparecerá perguntando qual mapa carregar. Selecione um mapa PGM da lista.

### 3. Ou Clique no Botão "🗺️ Carregar PGM"

Se a janela não aparecer, clique no botão **"🗺️ Carregar PGM"** na interface.

### 4. Selecione o Mapa PGM

Você verá uma lista de mapas disponíveis:
- Mapas em `mapas/otimizados/`
- Mapas em `data/pipeline_runs/*/map2d/`
- Mapas em `data/pipeline_runs/*/annotation/`

Selecione um mapa da lista.

### 5. Ou Navegue Manualmente

Se não houver mapas na lista, clique em **"Abrir arquivo..."** e navegue até:
- `data/pipeline_runs/[data]/map2d/*.pgm`

---

## 🔍 ONDE ESTÃO OS MAPAS PGM?

Os mapas PGM são gerados pelo pipeline em:

```
data/pipeline_runs/[data]/
├── map2d/
│   ├── mapa.pgm          ← Mapa 2D (imagem)
│   └── mapa.yaml         ← Metadados (resolução, origem)
└── annotation/
    ├── mapa.pgm          ← Cópia do mapa (para anotação)
    └── mapa.yaml
```

---

## 🖼️ VISUALIZAÇÃO ALTERNATIVA: Preview PNG

Se você quiser ver uma **preview PNG** (imagem colorida) ao invés do PGM (escala de cinza):

### Opção 1: Abrir PNG em Visualizador Externo

Os previews PNG são gerados em:
```
data/pipeline_runs/[data]/
├── refinement/
│   └── mapa_preview.png  ← Preview da nuvem de pontos
└── map2d/
    └── mapa_preview.png  ← Preview do mapa 2D (se gerado)
```

Abra esses arquivos em qualquer visualizador de imagens.

### Opção 2: Adicionar Suporte a PNG no main.py (Futuro)

Podemos adicionar suporte para carregar PNG como fundo, mas por enquanto o PGM é o formato padrão.

---

## ⚠️ DIFERENÇAS VISUAIS

### Com Mapa PGM Carregado (✅ Correto):
- ✅ **Imagem do mapa** visível como fundo
- ✅ Paredes, obstáculos e áreas livres visíveis
- ✅ Pontos de interesse sobrepostos na imagem
- ✅ Robô posicionado no mapa

### Sem Mapa PGM (❌ Incorreto):
- ❌ Apenas **grid vazio** ou pontos soltos
- ❌ Sem imagem de fundo
- ❌ Apenas pontos de interesse visíveis
- ❌ Difícil de navegar

---

## 🔧 TROUBLESHOOTING

### Problema: Não vejo o botão "🗺️ Carregar PGM"

**Solução**: Verifique se você está usando a versão mais recente do código. O botão deve estar na barra de ferramentas.

### Problema: Lista de mapas está vazia

**Solução**: 
1. Execute o pipeline primeiro para gerar mapas:
   ```bash
   python3 src/main_mapping.py --pipeline aurora_to_c1 --input ... --output ...
   ```
2. Ou navegue manualmente clicando em "Abrir arquivo..."

### Problema: Mapa PGM não carrega

**Solução**:
1. Verifique se o arquivo `.pgm` existe
2. Verifique se o arquivo `.yaml` correspondente existe (mesmo nome, extensão `.yaml`)
3. Verifique os logs no terminal para mensagens de erro

### Problema: Mapa aparece muito pequeno ou muito grande

**Solução**: O sistema ajusta automaticamente. Se necessário, ajuste o zoom da interface.

---

## 📚 REFERÊNCIAS

- `docs/mapping/FLUXO_COMPLETO_AURORA_C1.md` - Como gerar mapas PGM
- `docs/mapping/QUAL_PGM_CARREGAR.md` - Qual arquivo PGM carregar

---

## 💡 DICA

**Sempre use "🗺️ Carregar PGM" para mapas do pipeline Aurora!**

O botão "📂 Carregar" é apenas para mapas legados do banco de dados antigo.

---

**Resumo: Use o botão "🗺️ Carregar PGM" ao invés de "📂 Carregar" para ver a imagem do mapa!**

