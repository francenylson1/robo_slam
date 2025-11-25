# 📍 Quando e Onde Criar POIs, Áreas Proibidas e Configurações

**Data**: 25/11/2025

---

## 🎯 RESPOSTA RÁPIDA

### ✅ **SIM, você cria DEPOIS de processar com `main_mapping.py`**

### ✅ **SIM, é na MESMA interface do `main.py` (navegação)**

---

## 🔄 FLUXO COMPLETO DE TRABALHO

### Passo 1: Processar Mapa com `main_mapping.py`

```bash
# Gera os arquivos base (.pgm, .yaml, .stcm)
python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora/SEU_MAPA.stcm \
  --output data/pipeline_runs/meu_mapa
```

**Resultado**: Arquivos gerados em `data/pipeline_runs/meu_mapa/`

---

### Passo 2: Abrir Interface de Navegação (`main.py`)

```bash
# Abre a interface onde você vai criar POIs, áreas, etc.
python src/main.py
```

**Esta é a interface onde você vai trabalhar!**

---

### Passo 3: Carregar Mapa PGM na Interface

Na interface do `main.py`:

1. Clique em **"🗺️ Carregar PGM"**
2. Selecione: `data/pipeline_runs/meu_mapa/map2d/SEU_MAPA_clean.pgm`
3. O mapa aparecerá como fundo visual

**Agora você vê o mapa na interface!**

---

### Passo 4: Criar POIs (Pontos de Interesse)

Na interface do `main.py`:

1. **Seção "Pontos de Interesse"** (painel direito)
2. Clique em **"➕ Adicionar"**
3. **Clique no mapa** onde quer criar o POI
4. Preencha o diálogo:
   - **Nome**: Ex: "Mesa 1", "Cozinha", "Entrada"
   - **Tipo**: Mesa, Base, Ponto de Parada
   - **Coordenadas**: Preenchidas automaticamente (ou ajuste manualmente)
5. Clique em **"OK"**

**POI criado e salvo automaticamente no banco de dados!**

---

### Passo 5: Criar Áreas Proibidas

Na interface do `main.py`:

1. **Seção "Áreas Proibidas"** (painel direito)
2. Clique em **"➕ Adicionar"**
3. **Clique no mapa** para marcar os vértices da área
4. **Duplo clique** para finalizar
5. A área será salva automaticamente

**Área proibida criada!**

---

### Passo 6: Definir Posição Inicial do Robô

#### Opção 1: Usar Configuração Padrão
- A posição inicial está definida em `src/core/config.py`
- Variáveis: `ROBOT_INITIAL_POSITION` e `ROBOT_INITIAL_ANGLE`

#### Opção 2: Ajustar na Interface
- O robô aparece na posição inicial automaticamente
- Você pode mover o robô manualmente (modo manual)
- A posição atual vira a nova posição inicial

---

### Passo 7: Definir Percurso (Trajetória)

O percurso é definido **automaticamente** quando você:

1. Seleciona um **destino** no combo box "Destino"
2. Clica em **"▶️ Iniciar Navegação"**
3. O sistema calcula o caminho automaticamente (A*)
4. O percurso aparece como linha no mapa

**Você não precisa criar o percurso manualmente!**

---

## 📋 RESUMO: O QUE CRIAR E ONDE

| Item | Quando Criar | Onde Criar | Como Criar |
|------|--------------|------------|------------|
| **Mapa base** | Primeiro | `main_mapping.py` | Pipeline completo |
| **POIs** | Depois | `main.py` (interface) | Botão "➕ Adicionar" → Clicar no mapa |
| **Áreas Proibidas** | Depois | `main.py` (interface) | Botão "➕ Adicionar" → Desenhar polígono |
| **Posição Inicial** | Depois | `main.py` ou `config.py` | Automático ou ajustar manualmente |
| **Percurso** | Automático | `main.py` (interface) | Selecionar destino → Iniciar navegação |

---

## 🎯 INTERFACE DO `main.py` - ONDE TUDO ACONTECE

### Seções Disponíveis:

1. **🗺️ Gerenciar Mapas**
   - 💾 Salvar
   - 📂 Carregar
   - 🗺️ **Carregar PGM** ← Use este para carregar seu mapa!

2. **📍 Pontos de Interesse**
   - ➕ **Adicionar** ← Cria POIs clicando no mapa
   - 🗑️ Excluir
   - 💾 Exportar JSON
   - 📥 Importar JSON ← Pode importar do pipeline

3. **🚫 Áreas Proibidas**
   - ➕ **Adicionar** ← Desenha áreas proibidas
   - 🗑️ Excluir
   - 💾 Exportar JSON
   - 📥 Importar JSON

4. **🎯 Navegação**
   - Selecionar destino
   - ▶️ Iniciar Navegação
   - ⏸️ Pausar
   - ⏹️ Parar

---

## 🔄 FLUXO RECOMENDADO (Passo a Passo)

### 1️⃣ Processar Mapa
```bash
python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora/meu_mapa.stcm \
  --output data/pipeline_runs/meu_mapa
```

### 2️⃣ Abrir Interface de Navegação
```bash
python src/main.py
```

### 3️⃣ Carregar Mapa PGM
- Botão "🗺️ Carregar PGM"
- Selecionar: `data/pipeline_runs/meu_mapa/map2d/meu_mapa_clean.pgm`

### 4️⃣ (Opcional) Importar POIs do Pipeline
- Botão "📥 Importar JSON" (seção POIs)
- Selecionar: `data/pipeline_runs/meu_mapa/annotation/meu_mapa_clean_pois.json`
- **Nota**: O JSON do pipeline só tem "home", você precisa adicionar mais POIs

### 5️⃣ Criar POIs Adicionais
- Botão "➕ Adicionar" (seção POIs)
- Clicar no mapa onde quer cada POI
- Preencher nome e tipo

### 6️⃣ Criar Áreas Proibidas
- Botão "➕ Adicionar" (seção Áreas Proibidas)
- Clicar no mapa para desenhar polígono
- Duplo clique para finalizar

### 7️⃣ Ajustar Posição Inicial (se necessário)
- Mover robô manualmente para posição desejada
- Ou editar `src/core/config.py`

### 8️⃣ Salvar Tudo
- Botão "💾 Salvar" (seção Gerenciar Mapas)
- Tudo é salvo no banco de dados SQLite

### 9️⃣ Navegar!
- Selecionar destino
- Clicar "▶️ Iniciar Navegação"
- O percurso é calculado automaticamente!

---

## 💡 DICAS IMPORTANTES

### ✅ POIs do Pipeline são Apenas Template

O arquivo `*_pois.json` gerado pelo pipeline contém apenas:
```json
{
  "pois": [
    {
      "id": "home",
      "name": "Ponto Inicial",
      "x": 0.0,
      "y": 0.0
    }
  ]
}
```

**Você precisa adicionar mais POIs manualmente na interface!**

### ✅ Tudo é Salvo Automaticamente

- POIs e áreas são salvos no banco de dados SQLite (`data/mapas.db`)
- Você pode exportar para JSON se quiser
- O autosave está ativado por padrão

### ✅ Posição Inicial do Robô

- Definida em `src/core/config.py`:
  ```python
  ROBOT_INITIAL_POSITION = (2.5, 2.5)  # (x, y) em metros
  ROBOT_INITIAL_ANGLE = 0.0  # Ângulo em graus
  ```
- Você pode ajustar na interface movendo o robô manualmente

### ✅ Percurso é Automático

- Você **não precisa** criar o percurso manualmente
- O sistema calcula automaticamente usando algoritmo A*
- Basta selecionar um destino e iniciar navegação

---

## 🎯 RESUMO FINAL

### Quando Criar?
**DEPOIS** de processar com `main_mapping.py`

### Onde Criar?
**NA MESMA INTERFACE** do `main.py` (navegação)

### Como Criar?
1. Carregar mapa PGM
2. Usar botões "➕ Adicionar" para POIs e áreas
3. Tudo é salvo automaticamente

### O Que Criar?
- ✅ POIs (mesas, destinos)
- ✅ Áreas proibidas
- ✅ Posição inicial (opcional, já tem padrão)
- ❌ Percurso (automático, não precisa criar)

---

**Pronto! Agora você sabe exatamente quando e onde criar tudo!** 🎉

