# 📋 Plano de Integração: Nova Funcionalidade na Interface Existente

## ✅ O QUE JÁ TEMOS (Será MANTIDO)

### Interface Principal (`main_window.py`)
- ✅ **Painéis colapsáveis** (CollapsibleGroupBox)
- ✅ **Seção de Pontos de Interesse** com:
  - Lista de POIs (ComboBox)
  - Botão "Adicionar POI"
  - Botão "Excluir POI"
  - Botão "Editar POI"
- ✅ **Seção de Áreas Proibidas** com:
  - Botão "Desenhar Área Proibida"
  - Botão "Excluir Área"
- ✅ **Navegação** (botões de controle)
- ✅ **Calibração** (janela de calibração)
- ✅ **Autosave** (salvamento automático)
- ✅ **Integração com banco SQLite**

### MapWidget (`map_widget.py`)
- ✅ **Desenho de grid** (grade do mapa)
- ✅ **Desenho de POIs** (pontos vermelhos com nomes)
- ✅ **Desenho de áreas proibidas** (polígonos vermelhos)
- ✅ **Desenho do robô** (círculo azul com direção)
- ✅ **Desenho de caminho de navegação** (linha azul tracejada)
- ✅ **Modo de adicionar POI** (clicar no mapa)
- ✅ **Modo de desenhar área** (clicar para criar polígono)
- ✅ **Seleção de áreas** (clicar para selecionar)

### Funcionalidades Existentes
- ✅ Adicionar POI (diálogo `AddPointDialog`)
- ✅ Editar POI (diálogo `EditPointDialog`)
- ✅ Excluir POI
- ✅ Desenhar área proibida (cliques + duplo clique para finalizar)
- ✅ Excluir área proibida
- ✅ Salvar no banco SQLite
- ✅ Carregar do banco SQLite

---

## 🆕 O QUE VAMOS ADICIONAR (Sem Quebrar Nada)

### 1. Carregar Mapa PGM como Fundo
**Onde:** `MapWidget.paintEvent()`
- ✅ **ADICIONAR:** Desenhar imagem PGM como fundo
- ✅ **MANTER:** Todo o resto (grid, POIs, áreas, robô) continua funcionando
- ✅ **COMPATIBILIDADE:** Se não houver PGM, desenha só o grid (como antes)

### 2. Menu para Carregar Mapa PGM
**Onde:** `MainWindow` (novo menu ou botão)
- ✅ **ADICIONAR:** Botão "Carregar Mapa PGM" na interface
- ✅ **FUNCIONALIDADE:** Abre diálogo para escolher arquivo `.pgm`
- ✅ **INTEGRAÇÃO:** Carrega também o `.yaml` correspondente para metadados

### 3. Salvar POIs/Áreas em JSON
**Onde:** `MainWindow` (novo botão ou opção)
- ✅ **ADICIONAR:** Botão "Exportar POIs/Áreas para JSON"
- ✅ **MANTER:** Continua salvando no banco SQLite (como antes)
- ✅ **FORMATO:** Salva em `mapas/pois/` e `mapas/areas_proibidas/` (estrutura já definida)

### 4. Carregar POIs/Áreas de JSON
**Onde:** `MainWindow` (novo botão)
- ✅ **ADICIONAR:** Botão "Importar POIs/Áreas de JSON"
- ✅ **FUNCIONALIDADE:** Carrega JSON e adiciona ao mapa atual
- ✅ **INTEGRAÇÃO:** Funciona junto com dados do banco

---

## 🔧 COMO SERÁ FEITO (Técnico)

### Modificações no `MapWidget`:

```python
# ADICIONAR atributos:
self.map_image = None  # Imagem PGM carregada
self.map_resolution = 0.05  # Resolução do mapa
self.map_origin = (0.0, 0.0)  # Origem do mapa

# ADICIONAR método:
def load_pgm_map(self, pgm_path: str, yaml_path: str = None):
    """Carrega mapa PGM como fundo"""
    # Carrega imagem PGM
    # Carrega metadados do YAML
    # Ajusta escala/origem se necessário

# MODIFICAR paintEvent (ADICIONAR no início):
def paintEvent(self, event):
    # NOVO: Desenha imagem PGM como fundo (se carregada)
    if self.map_image:
        painter.drawImage(...)
    
    # MANTER: Todo o resto continua igual
    self._draw_grid(painter)  # Grid (pode ficar opcional)
    self._draw_forbidden_areas(painter)
    # ... resto do código existente
```

### Modificações no `MainWindow`:

```python
# ADICIONAR botões na interface:
- "🗺️ Carregar Mapa PGM" (nova seção ou menu)
- "💾 Exportar POIs/Áreas" (na seção de POIs)
- "📥 Importar POIs/Áreas" (na seção de POIs)

# ADICIONAR métodos:
def _load_pgm_map(self):
    """Abre diálogo para carregar mapa PGM"""
    # Abre file dialog
    # Chama map_widget.load_pgm_map()
    
def _export_pois_areas(self):
    """Exporta POIs e áreas para JSON"""
    # Lê do banco ou do map_widget
    # Salva em mapas/pois/ e mapas/areas_proibidas/
    
def _import_pois_areas(self):
    """Importa POIs e áreas de JSON"""
    # Abre file dialog
    # Carrega JSON
    # Adiciona ao map_widget
```

---

## ✅ GARANTIAS (O Que NÃO Vai Quebrar)

1. **✅ Tudo que funciona continua funcionando:**
   - Adicionar POI → Continua funcionando
   - Editar POI → Continua funcionando
   - Excluir POI → Continua funcionando
   - Desenhar área → Continua funcionando
   - Navegação → Continua funcionando
   - Banco SQLite → Continua funcionando

2. **✅ Compatibilidade retroativa:**
   - Se não carregar PGM → Interface funciona como antes (só grid)
   - Se não exportar JSON → Continua salvando só no banco
   - Se não importar JSON → Continua usando só o banco

3. **✅ Funcionalidades opcionais:**
   - Carregar PGM é **opcional** (não obrigatório)
   - Exportar JSON é **opcional** (adicional ao banco)
   - Importar JSON é **opcional** (adicional ao banco)

---

## 📊 Resumo Visual

### ANTES (Atual):
```
Interface
├── MapWidget
│   ├── Grid (sempre visível)
│   ├── POIs (do banco)
│   ├── Áreas (do banco)
│   └── Robô
└── Painéis
    ├── POIs (adicionar/editar/excluir)
    └── Áreas (desenhar/excluir)
```

### DEPOIS (Com Novas Funcionalidades):
```
Interface
├── MapWidget
│   ├── 🆕 Mapa PGM (fundo, opcional)
│   ├── Grid (opcional, se não houver PGM)
│   ├── POIs (do banco + JSON)
│   ├── Áreas (do banco + JSON)
│   └── Robô
└── Painéis
    ├── 🆕 "Carregar Mapa PGM"
    ├── POIs (adicionar/editar/excluir)
    │   └── 🆕 "Exportar para JSON"
    │   └── 🆕 "Importar de JSON"
    └── Áreas (desenhar/excluir)
```

---

## 🎯 Resposta Direta à Sua Pergunta

**SIM, vou:**
1. ✅ **MANTER** todos os elementos existentes
2. ✅ **ADICIONAR** as novas funcionalidades
3. ✅ **NÃO QUEBRAR** nada que já funciona
4. ✅ **COMPATIBILIDADE** retroativa garantida

**As novas funcionalidades serão:**
- **Opcionais** (você escolhe usar ou não)
- **Aditivas** (não substituem nada)
- **Integradas** (funcionam junto com o existente)

---

## ❓ Confirmação

Posso prosseguir com essa abordagem?
- ✅ Manter tudo que existe
- ✅ Adicionar carregamento de PGM
- ✅ Adicionar exportação/importação JSON
- ✅ Garantir que nada quebra

