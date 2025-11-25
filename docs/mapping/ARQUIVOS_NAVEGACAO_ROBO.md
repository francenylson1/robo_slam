# 📁 Arquivos Gerados pelo Pipeline e Uso na Navegação

**Data**: 25/11/2025  
**Pipeline**: `main_mapping.py` → Aurora → C1

---

## 📋 ARQUIVOS GERADOS PELO PIPELINE

Quando você executa `main_mapping.py`, o pipeline gera vários arquivos em diferentes etapas:

```
data/pipeline_runs/SEU_MAPA/
├── capture/
│   ├── SEU_MAPA.stcm              # Cópia do arquivo original
│   ├── SEU_MAPA.ply               # Point cloud extraído do SDK
│   └── backup_aurora_maps/        # Backups do mapa atual
│
├── refinement/
│   ├── SEU_MAPA_clean.ply         # Point cloud limpo (após filtros)
│   └── SEU_MAPA_preview.png       # Preview visual do point cloud
│
├── map2d/
│   ├── SEU_MAPA_clean.pgm         # ⭐ MAPA 2D (imagem) - USADO NA INTERFACE
│   └── SEU_MAPA_clean.yaml        # ⭐ METADADOS do mapa 2D - USADO NA INTERFACE
│
├── c1_converter/
│   └── SEU_MAPA_clean.stcm        # ⭐ STCM para o robô C1 - USADO PELO ROBÔ
│
├── annotation/
│   └── SEU_MAPA_clean_pois.json   # ⭐ POIs (Pontos de Interesse) - USADO NA INTERFACE
│
└── export/
    └── SEU_MAPA_clean_package/    # ⭐ PACOTE FINAL
        ├── SEU_MAPA_clean.stcm    # ⭐ USADO PELO ROBÔ
        ├── SEU_MAPA_clean_pois.json  # ⭐ USADO NA INTERFACE
        ├── SEU_MAPA_clean_layout.png  # Apenas visualização
        ├── metadata.json          # Apenas documentação
        └── README.md              # Apenas documentação
```

---

## 🎯 QUAIS ARQUIVOS SÃO USADOS NA NAVEGAÇÃO?

### 🔴 ARQUIVOS USADOS PELO ROBÔ C1 (Navegação Real)

#### 1. **`.stcm` (formato C1)** ⭐ **CRÍTICO - USADO PELO ROBÔ**
- **Localização**: 
  - `c1_converter/SEU_MAPA_clean.stcm`
  - `export/SEU_MAPA_clean_package/SEU_MAPA_clean.stcm`
- **Uso**: **Upload para o robô C1 via SLAMWARE API**
- **Função**: Mapa principal que o robô usa para **localização e navegação física**
- **Como é usado**: 
  - Upload via `slamware_c1_uploader.py` (função `upload_map()`)
  - Carregado no sistema SLAMWARE do C1
  - Usado pelo robô para:
    - **Localização simultânea (SLAM)**
    - **Navegação autônoma**
    - **Detecção de obstáculos**
    - **Planejamento de trajetória**
- **Status**: ⚠️ Atualmente é um **placeholder** (arquivo vazio) se C1 não estiver conectado durante o pipeline
- **Código que usa**: `src/core/slamware_c1_uploader.py`

---

### 🟢 ARQUIVOS USADOS PELA INTERFACE DE NAVEGAÇÃO (GUI)

#### 2. **`.pgm` + `.yaml` (Mapa 2D)** ⭐ **ESSENCIAL - USADO NA INTERFACE**
- **Localização**: `map2d/SEU_MAPA_clean.pgm` e `map2d/SEU_MAPA_clean.yaml`
- **Uso**: **Fundo visual na interface de navegação**
- **Função**: Mostra o mapa como imagem de fundo na GUI
- **Como é usado**:
  - Carregado por `map_widget.py` via função `load_pgm_map()`
  - Exibido como fundo na interface (`main_window.py`)
  - POIs, robô e trajetórias são desenhados **sobre** o mapa
  - Usuário interage visualmente com o mapa
- **Formato**:
  - `.pgm`: Imagem em escala de cinza
    - `0` = ocupado (obstáculo/preto)
    - `205` = desconhecido (cinza)
    - `254` = livre (branco)
  - `.yaml`: Metadados (resolução, origem, etc.)
    ```yaml
    image: SEU_MAPA_clean.pgm
    resolution: 0.05
    origin: [-3.25, -2.675, 0.0]
    ```
- **Código que usa**: 
  - `src/interfaces/map_widget.py` (função `load_pgm_map()`)
  - `src/interfaces/main_window.py` (botão "🗺️ Carregar PGM")

#### 3. **`*_pois.json` (POIs)** ⭐ **ESSENCIAL - USADO NA INTERFACE**
- **Localização**: 
  - `annotation/SEU_MAPA_clean_pois.json`
  - `export/SEU_MAPA_clean_package/SEU_MAPA_clean_pois.json`
- **Uso**: **Pontos de Interesse para navegação**
- **Função**: Define destinos, mesas, áreas importantes
- **Como é usado**:
  - Importado pela interface via botão "📥 Importar JSON" (`main_window.py`)
  - Carregado na função `_import_pois_json()`
  - POIs são adicionados ao banco de dados SQLite (`map_manager.py`)
  - Exibidos no mapa como marcadores
  - Usados para definir destinos de navegação
- **Formato**:
```json
{
  "map_id": "sala-maker-1_clean",
  "pois": [
    {
      "id": "mesa_01",
      "name": "Mesa 1",
      "x": 100.5,
      "y": 250.3,
      "orientation": 90.0,
      "type": "delivery",
      "description": "Mesa próxima à janela"
    }
  ],
  "forbidden_areas": []
}
```
- **Código que usa**: 
  - `src/interfaces/main_window.py` (função `_import_pois_json()`)
  - `src/core/map_manager.py` (salva no banco de dados SQLite)

---

### 🟡 ARQUIVOS OPCIONAIS (Apenas Visualização)

#### 4. **`*_layout.png` (Preview)** ⭐ **OPCIONAL**
- **Localização**: `export/SEU_MAPA_clean_package/SEU_MAPA_clean_layout.png`
- **Uso**: **Referência visual**
- **Função**: Preview do mapa para visualização rápida
- **Status**: ❌ **NÃO é carregado** automaticamente pelo sistema
- **Como usar**: Abrir manualmente para visualizar

#### 5. **`*_preview.png` (Preview do Point Cloud)** ⭐ **OPCIONAL**
- **Localização**: `refinement/SEU_MAPA_preview.png`
- **Uso**: **Visualização durante processamento**
- **Status**: ❌ **NÃO é usado** pela aplicação de navegação

---

---

### ❌ ARQUIVOS INTERMEDIÁRIOS (NÃO usados na navegação)

#### 6. **`.ply` (Point Clouds)**
- **Localização**: `capture/SEU_MAPA.ply` e `refinement/SEU_MAPA_clean.ply`
- **Uso**: **Apenas durante processamento**
- **Função**: Dados intermediários do pipeline (conversão .stcm → .ply → .pgm)
- **Status**: ❌ **NÃO são usados** pela aplicação de navegação
- **Nota**: São necessários durante o pipeline, mas não são carregados pela interface ou robô

#### 7. **`metadata.json`**
- **Localização**: `export/SEU_MAPA_clean_package/metadata.json`
- **Uso**: **Apenas para referência/documentação**
- **Status**: ❌ **NÃO é usado** pela aplicação de navegação

---

## 🔄 FLUXO COMPLETO DE USO NA NAVEGAÇÃO

### Passo 1: Upload do Mapa para o Robô C1
```
SEU_MAPA_clean.stcm 
  → Upload via SLAMWARE API (slamware_c1_uploader.py)
  → Robô C1 (sistema SLAMWARE)
  → Robô usa para localização e navegação física
```
- O arquivo `.stcm` é enviado para o robô C1
- O C1 carrega o mapa no sistema SLAMWARE
- O robô usa este mapa para:
  - **Localização simultânea (SLAM)**
  - **Navegação autônoma**
  - **Detecção de obstáculos**
  - **Planejamento de trajetória**

### Passo 2: Carregar Mapa na Interface de Navegação
```
SEU_MAPA_clean.pgm + .yaml 
  → map_widget.load_pgm_map()
  → Interface de Navegação (fundo visual)
```
- A interface carrega o `.pgm` como fundo visual
- O `.yaml` fornece metadados (resolução, origem)
- O usuário vê o mapa como imagem de fundo

### Passo 3: Carregar POIs na Interface
```
SEU_MAPA_clean_pois.json
  → main_window._import_pois_json()
  → map_manager.save_map()
  → Banco de dados SQLite
  → Exibidos no mapa como marcadores
```
- Os POIs são importados do JSON
- Salvos no banco de dados SQLite
- Exibidos no mapa como marcadores
- Usuário pode selecionar destinos

### Passo 4: Navegação (Integração)
```
┌─────────────────────────────────────────┐
│  Robô C1 (Hardware)                     │
│  └─ Usa: .stcm                          │
│     • Localização (SLAM)                │
│     • Navegação física                  │
│     • Detecção de obstáculos            │
└──────────────┬──────────────────────────┘
               │ Comunicação via SLAMWARE API
               │
┌──────────────▼──────────────────────────┐
│  Interface de Navegação (GUI)           │
│  └─ Usa: .pgm + .yaml + POIs (JSON)    │
│     • Visualização do mapa              │
│     • Seleção de destinos               │
│     • Monitoramento do robô             │
│     • Controle manual                   │
└─────────────────────────────────────────┘
```
- O robô navega usando o `.stcm` carregado
- A interface mostra visualmente usando `.pgm` + POIs
- Usuário interage via interface para enviar comandos ao robô

---

## 📊 RESUMO: ARQUIVOS POR USO

| Arquivo | Usado pelo C1? | Usado pela Interface? | Essencial? | Onde está |
|---------|----------------|----------------------|------------|-----------|
| **`.stcm`** | ✅ **SIM** (navegação física) | ❌ Não | ⭐ **CRÍTICO** | `c1_converter/` ou `export/*/` |
| **`.pgm`** | ❌ Não | ✅ **SIM** (fundo visual) | ⭐ **ESSENCIAL** | `map2d/` |
| **`.yaml`** | ❌ Não | ✅ **SIM** (metadados) | ⭐ **ESSENCIAL** | `map2d/` |
| **`*_pois.json`** | ❌ Não | ✅ **SIM** (destinos) | ⭐ **ESSENCIAL** | `annotation/` ou `export/*/` |
| **`.ply`** | ❌ Não | ❌ Não | ❌ Intermediário | `capture/`, `refinement/` |
| **`*_preview.png`** | ❌ Não | ❌ Não | ❌ Opcional | `refinement/` |
| **`*_layout.png`** | ❌ Não | ❌ Não | ❌ Opcional | `export/*/` |
| **`metadata.json`** | ❌ Não | ❌ Não | ❌ Documentação | `export/*/` |

---

## 🎯 ARQUIVOS MÍNIMOS PARA NAVEGAÇÃO

### Para o Robô C1 Navegar:
1. ✅ **`.stcm`** - **OBRIGATÓRIO**
   - Mapa que o robô usa para localização e navegação física
   - Sem este arquivo, o robô não consegue navegar

### Para a Interface de Navegação Funcionar:
2. ✅ **`.pgm` + `.yaml`** - **RECOMENDADO**
   - Permite visualizar o mapa na interface
   - Sem estes, a interface funciona, mas sem fundo visual

3. ✅ **`*_pois.json`** - **RECOMENDADO**
   - Permite importar POIs (mesas, destinos)
   - Sem este, você precisa criar POIs manualmente na interface

### Resumo:
- **Mínimo absoluto**: Apenas `.stcm` (robô navega, mas interface sem visualização)
- **Recomendado**: `.stcm` + `.pgm` + `.yaml` + `*_pois.json` (experiência completa)

---

## 📝 ONDE COLOCAR OS ARQUIVOS

### Para o Robô C1:
```
Arquivo: export/SEU_MAPA_clean_package/SEU_MAPA_clean.stcm
Ação: Upload via SLAMWARE API
Como:
  1. Conecte o C1 à rede
  2. Configure IP do C1 em config/mapping.json
  3. Re-execute pipeline com etapa c1_conversion
  4. Ou faça upload manual via SDK do C1
```

### Para a Interface de Navegação:
```
Opção 1: Usar diretamente do pipeline
  → map2d/SEU_MAPA_clean.pgm
  → map2d/SEU_MAPA_clean.yaml
  → annotation/SEU_MAPA_clean_pois.json

Opção 2: Copiar para estrutura organizada
  → mapas/c1/otimizados/SEU_MAPA_clean.pgm
  → mapas/c1/otimizados/SEU_MAPA_clean.yaml
  → mapas/c1/pois/SEU_MAPA_clean_pois.json
```

### Como Carregar na Interface:
1. **Carregar Mapa PGM**:
   - Botão "🗺️ Carregar PGM" na interface
   - Selecione o arquivo `.pgm`
   - O `.yaml` será carregado automaticamente

2. **Importar POIs**:
   - Botão "📥 Importar JSON" na interface
   - Selecione o arquivo `*_pois.json`
   - POIs serão adicionados ao mapa

---

## 🔍 VERIFICAÇÃO

### Como verificar se arquivos estão corretos:

1. **`.stcm`**:
   ```bash
   ls -lh data/pipeline_runs/SEU_MAPA/export/*/SEU_MAPA_clean.stcm
   # Deve ter tamanho > 0 (não vazio)
   ```

2. **`.pgm`**:
   ```bash
   # Abrir com visualizador de imagens
   xdg-open data/pipeline_runs/SEU_MAPA/map2d/SEU_MAPA_clean.pgm
   ```

3. **`*_pois.json`**:
   ```bash
   cat data/pipeline_runs/SEU_MAPA/annotation/SEU_MAPA_clean_pois.json
   # Deve ser JSON válido
   ```

---

## ⚠️ NOTAS IMPORTANTES

1. **`.stcm` é placeholder se C1 não estiver conectado**: 
   - Se o C1 não estiver conectado durante o pipeline, o `.stcm` gerado será um arquivo vazio (placeholder)
   - **Solução**: 
     - Conecte o C1 e re-execute a etapa `c1_conversion`
     - Ou faça upload manual via SDK do C1
     - Ou use a API REST do SLAMWARE diretamente

2. **POIs precisam ser editados**: 
   - O arquivo `*_pois.json` gerado é apenas um template (contém apenas "home")
   - **Solução**: 
     - Editar manualmente o JSON para adicionar mesas, destinos, etc.
     - Ou usar a interface de navegação para criar POIs visualmente
     - Ou importar POIs existentes de outro mapa

3. **`.pgm` e `.yaml` devem estar juntos**: 
   - A interface precisa de ambos os arquivos para carregar o mapa corretamente
   - O `.yaml` contém metadados essenciais (resolução, origem)
   - Se o `.yaml` não existir, a interface usa valores padrão (pode não funcionar corretamente)

4. **Banco de dados SQLite**: 
   - A interface salva POIs e áreas proibidas em um banco de dados SQLite
   - O arquivo JSON é apenas para importação
   - Após importar, os POIs ficam no banco de dados (`data/mapas.db`)
   - O banco de dados é o que realmente é usado pela interface

---

**Última Atualização**: 25/11/2025

