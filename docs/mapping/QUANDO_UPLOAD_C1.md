# 📤 Quando Fazer Upload para o C1

**Data**: 25/11/2025

---

## 🎯 RESPOSTA RÁPIDA

### ✅ **Você pode fazer upload em 2 momentos:**

1. **Durante o pipeline** (`main_mapping.py`) - **AUTOMÁTICO** (se C1 estiver conectado)
2. **Depois do pipeline** - **MANUAL** (quando quiser atualizar o mapa)

---

## 🔄 OPÇÃO 1: Upload Automático Durante o Pipeline

### Quando acontece?
Durante a execução do `main_mapping.py`, na etapa `c1_conversion`.

### Como funciona?

```bash
python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora/meu_mapa.stcm \
  --output data/pipeline_runs/meu_mapa
```

**Se o C1 estiver conectado:**
- ✅ A etapa `c1_conversion` detecta o C1
- ✅ Faz upload automático via API REST
- ✅ O mapa fica disponível no C1 imediatamente

**Se o C1 NÃO estiver conectado:**
- ⚠️ Cria um placeholder `.stcm` (arquivo vazio)
- ⚠️ Você precisa fazer upload manual depois

---

### Pré-requisitos para Upload Automático:

1. **C1 conectado à rede**
2. **IP do C1 configurado** em `config/mapping.json`:
   ```json
   {
     "c1_conversion": {
       "c1_ip": "192.168.1.101",
       "c1_port": 1445,
       "use_api": true
     }
   }
   ```
3. **C1 acessível** (ping funciona)

---

## 🔄 OPÇÃO 2: Upload Manual Depois do Pipeline

### Quando fazer?
- ✅ Quando o C1 não estava conectado durante o pipeline
- ✅ Quando você quer atualizar o mapa no C1
- ✅ Quando você ajustou POIs/áreas e quer usar o mapa atualizado

---

### Como fazer upload manual?

#### Método 1: Re-executar apenas a etapa `c1_conversion`

```bash
python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora/meu_mapa.stcm \
  --output data/pipeline_runs/meu_mapa \
  --steps c1_conversion
```

**Vantagem**: Usa o mesmo código do pipeline, garante consistência.

---

#### Método 2: Script Python direto

```python
from src.core.slamware_c1_uploader import SlamwareC1Uploader

# Conecta ao C1
uploader = SlamwareC1Uploader(ip_address="192.168.1.101", port=1445)

# Verifica conexão
if uploader.check_connection():
    # Faz upload
    success = uploader.upload_map(
        pgm_path="data/pipeline_runs/meu_mapa/map2d/meu_mapa_clean.pgm",
        yaml_path="data/pipeline_runs/meu_mapa/map2d/meu_mapa_clean.yaml",
        map_name="meu_mapa"
    )
    
    if success:
        # Define como mapa ativo
        uploader.set_active_map("meu_mapa")
        print("✅ Mapa enviado e ativado no C1!")
    else:
        print("❌ Erro no upload")
else:
    print("❌ C1 não acessível")
```

---

#### Método 3: Via Interface Web do C1 (Manual)

1. Acesse a interface web do C1: `http://192.168.1.101:1445`
2. Vá em "Maps" ou "Map Management"
3. Clique em "Upload Map"
4. Selecione os arquivos:
   - `data/pipeline_runs/meu_mapa/map2d/meu_mapa_clean.pgm`
   - `data/pipeline_runs/meu_mapa/map2d/meu_mapa_clean.yaml`
5. Defina como mapa ativo

---

## 📋 FLUXO RECOMENDADO

### Cenário 1: C1 Conectado Durante o Pipeline

```
1. Conecte o C1 à rede
   ↓
2. Configure IP em config/mapping.json
   ↓
3. Execute main_mapping.py
   ↓
4. ✅ Upload automático acontece na etapa c1_conversion
   ↓
5. Mapa já está no C1!
```

**Vantagem**: Tudo automático, mapa já disponível no C1.

---

### Cenário 2: C1 NÃO Conectado Durante o Pipeline

```
1. Execute main_mapping.py (sem C1 conectado)
   ↓
2. Pipeline gera arquivos (.pgm, .yaml, .stcm placeholder)
   ↓
3. Crie POIs e áreas na interface (main.py)
   ↓
4. Conecte o C1 à rede
   ↓
5. Re-execute apenas c1_conversion OU faça upload manual
   ↓
6. ✅ Mapa enviado para o C1
```

**Vantagem**: Pode trabalhar offline, faz upload quando precisar.

---

## ⚠️ IMPORTANTE: O Que é Enviado para o C1?

### ✅ Arquivos Enviados:
- **`.pgm`** - Mapa 2D (imagem)
- **`.yaml`** - Metadados (resolução, origem)

### ❌ NÃO são enviados:
- **POIs** - Ficam apenas na interface (banco de dados local)
- **Áreas Proibidas** - Ficam apenas na interface (banco de dados local)
- **`.stcm`** - Não é usado para upload via API (só PGM/YAML)

**Por quê?**
- O C1 usa o mapa (`.pgm` + `.yaml`) para **localização e navegação física**
- POIs e áreas proibidas são gerenciados pela **interface de navegação** (`main.py`)
- A interface envia comandos de navegação para o C1, mas os POIs ficam na interface

---

## 🎯 QUANDO FAZER UPLOAD: Resumo

| Situação | Quando Fazer Upload |
|----------|---------------------|
| **Primeira vez usando o mapa** | ✅ Durante pipeline (automático) ou depois (manual) |
| **C1 não estava conectado** | ✅ Depois do pipeline, quando conectar |
| **Atualizou o mapa** | ✅ Re-executar `c1_conversion` ou upload manual |
| **Apenas ajustou POIs/áreas** | ❌ **NÃO precisa** fazer upload (POIs ficam na interface) |
| **Quer testar navegação** | ✅ Upload antes de testar |

---

## 🔍 VERIFICAÇÃO: Mapa Está no C1?

### Verificar via código:

```python
from src.core.slamware_c1_uploader import SlamwareC1Uploader

uploader = SlamwareC1Uploader(ip_address="192.168.1.101", port=1445)
maps = uploader.list_maps()
print(f"Mapas no C1: {maps}")
```

### Verificar via interface web:
1. Acesse: `http://192.168.1.101:1445`
2. Vá em "Maps"
3. Veja lista de mapas disponíveis

---

## 📝 CHECKLIST: Upload para C1

### Antes de Fazer Upload:
- [ ] C1 está conectado à rede
- [ ] IP do C1 está correto em `config/mapping.json`
- [ ] Arquivos `.pgm` e `.yaml` foram gerados pelo pipeline
- [ ] C1 está acessível (ping funciona)

### Durante/Depois do Upload:
- [ ] Upload foi bem-sucedido (sem erros)
- [ ] Mapa aparece na lista de mapas do C1
- [ ] Mapa foi definido como ativo (se necessário)
- [ ] Teste de navegação funciona

---

## 💡 DICAS IMPORTANTES

### ✅ Upload Automático vs Manual

**Upload Automático (durante pipeline):**
- ✅ Mais conveniente
- ✅ Garante que mapa está no C1 imediatamente
- ❌ Requer C1 conectado durante pipeline

**Upload Manual (depois do pipeline):**
- ✅ Pode trabalhar offline
- ✅ Mais controle sobre quando fazer upload
- ❌ Requer passo adicional

### ✅ POIs e Áreas Proibidas

**IMPORTANTE**: POIs e áreas proibidas **NÃO são enviados** para o C1!

- POIs ficam na interface (`main.py`)
- Áreas proibidas ficam na interface (`main.py`)
- O C1 só recebe o mapa (`.pgm` + `.yaml`)
- A interface envia comandos de navegação para o C1 baseados nos POIs

**Por isso**: Você pode ajustar POIs/áreas sem precisar fazer upload novamente!

---

## 🎯 RESUMO FINAL

### Quando Fazer Upload?

1. **Durante pipeline** (automático) - Se C1 estiver conectado
2. **Depois do pipeline** (manual) - Se C1 não estava conectado ou quer atualizar

### O Que é Enviado?

- ✅ `.pgm` + `.yaml` (mapa 2D)
- ❌ POIs (ficam na interface)
- ❌ Áreas proibidas (ficam na interface)

### Como Fazer?

1. **Automático**: Execute pipeline com C1 conectado
2. **Manual**: Re-execute `c1_conversion` ou use script Python

---

**Pronto! Agora você sabe exatamente quando fazer upload para o C1!** 🎉

