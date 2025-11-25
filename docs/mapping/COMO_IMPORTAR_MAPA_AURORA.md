# 📥 Como Importar Mapa do Aurora

**Data**: 25/11/2025

---

## 🔍 RESUMO RÁPIDO

**Atualmente, a importação é MANUAL:**
1. Você precisa **exportar o mapa do Aurora** via interface web
2. **Salvar o arquivo** (`.stcm`, `.ply`, ou `.pcd`) em uma pasta local
3. **Executar o pipeline** apontando para essa pasta/arquivo

**NÃO é automático** - você precisa conectar ao Aurora e exportar manualmente.

---

## 📋 PROCESSO COMPLETO

### **ETAPA 1: Exportar Mapa do Aurora** 📤

#### Opção A: Via Interface Web (RECOMENDADO)

1. **Conecte ao Aurora**:
   - IP: `192.168.11.1`
   - Acesse no navegador: `http://192.168.11.1`

2. **Navegue até os mapas**:
   - Vá em **"Maps"** ou **"Mapas Salvos"**
   - Selecione o mapa que deseja exportar

3. **Exporte o mapa**:
   - Clique em **"Export"** ou **"Download"**
   - Escolha formato:
     - **`.stcm`** (formato nativo do Aurora) ⭐ RECOMENDADO
     - **`.ply`** ou **`.pcd`** (nuvem de pontos 3D)

4. **Salve o arquivo**:
   - Salve em: `mapas/legacy/originais_aurora/`
   - Nome sugerido: `mapa-YYYYMMDD.stcm` (ex: `mapa-20251125.stcm`)

#### Opção B: Via SDK (Avançado)

Se você tiver o SDK configurado, pode usar scripts Python para download automático, mas isso ainda não está integrado no pipeline principal.

---

### **ETAPA 2: Processar o Mapa** 🔄

Após exportar e salvar o arquivo, execute o pipeline:

```bash
# Pipeline completo (captura → refinamento → mapa 2D → conversão C1 → POIs → export)
python3 src/main_mapping.py \
    --pipeline aurora_to_c1 \
    --input mapas/legacy/originais_aurora/mapa-20251125.stcm \
    --output data/pipeline_runs/2025-11-25
```

**O que acontece:**
1. **`capture`**: Copia o arquivo `.stcm` para a pasta de saída
2. **`refinement`**: Converte `.stcm` → `.ply` (conecta ao Aurora se necessário)
3. **`map2d`**: Gera mapa 2D (`.pgm` + `.yaml`)
4. **`c1_conversion`**: Converte para formato C1 (`.stcm` compatível)
5. **`annotation`**: Cria template para POIs
6. **`export`**: Empacota tudo para deploy

---

## 🔧 DETALHES TÉCNICOS

### O que o `capture` faz?

O passo `capture` **NÃO conecta ao Aurora**. Ele apenas:
- Copia arquivos já existentes no sistema de arquivos
- Procura por arquivos `.stcm`, `.ply`, `.pcd`, `.bmp`, `.bin` na pasta de entrada
- Copia para a pasta de saída (`data/pipeline_runs/.../capture/`)

### Conversão `.stcm` → `.ply`

A conversão acontece no passo `refinement`:
- Se o arquivo for `.stcm`, o sistema tenta converter usando o SDK do Aurora
- **Isso requer conexão ao Aurora** (IP: `192.168.11.1`)
- O SDK conecta, faz upload do `.stcm` (se necessário), e extrai os map points

**Configuração necessária** (`config/mapping.json`):
```json
{
  "aurora": {
    "enabled": true,
    "ip": "192.168.11.1",
    "port": 7447,
    "auto_discover": true
  }
}
```

---

## ⚠️ IMPORTANTE

### Por que não é automático?

1. **Segurança**: Evita conexões automáticas não autorizadas
2. **Controle**: Você escolhe qual mapa exportar
3. **Flexibilidade**: Pode processar mapas antigos sem conectar ao Aurora

### Quando o Aurora precisa estar conectado?

- **NÃO precisa** para o passo `capture` (apenas copia arquivos)
- **PRECISA** para o passo `refinement` se o arquivo for `.stcm` (para converter)

### E se o Aurora não estiver conectado?

- Se você já tiver o arquivo `.ply` ou `.pcd`, pode pular a conversão
- Ou pode usar o parser heurístico (menos preciso) como fallback

---

## 📝 EXEMPLO PRÁTICO

### Cenário 1: Mapa novo (Aurora conectado)

```bash
# 1. Exporte o mapa via interface web do Aurora
#    Salve em: mapas/legacy/originais_aurora/mapa-novo.stcm

# 2. Execute o pipeline (Aurora precisa estar conectado para conversão)
python3 src/main_mapping.py \
    --pipeline aurora_to_c1 \
    --input mapas/legacy/originais_aurora/mapa-novo.stcm \
    --output data/pipeline_runs/2025-11-25
```

### Cenário 2: Mapa antigo (sem Aurora)

```bash
# 1. Você já tem o arquivo .ply ou .pcd

# 2. Execute o pipeline (não precisa do Aurora)
python3 src/main_mapping.py \
    --pipeline aurora_to_c1 \
    --input mapas/legacy/originais_aurora/mapa-antigo.ply \
    --output data/pipeline_runs/2025-11-25
```

### Cenário 3: Apenas reprocessar (sem captura)

```bash
# Pula o passo capture e refinement
python3 src/main_mapping.py \
    --pipeline aurora_to_c1 \
    --input data/pipeline_runs/2025-11-25/capture \
    --output data/pipeline_runs/2025-11-25-reprocesso \
    --steps map2d,export
```

---

## 🔄 FUTURAS MELHORIAS

Possíveis melhorias futuras:
- ✅ Download automático via SDK (sem interface web)
- ✅ Listagem de mapas disponíveis no Aurora
- ✅ Seleção interativa de qual mapa baixar
- ✅ Sincronização automática

**Por enquanto, o processo é manual via interface web do Aurora.**

---

## 📚 REFERÊNCIAS

- `docs/mapping/FLUXO_COMPLETO_AURORA_C1.md` - Fluxo completo detalhado
- `docs/mapping/GUIA_USO_INICIAL.md` - Guia de uso inicial
- `config/mapping.json` - Configurações do pipeline

---

**Resumo: Exporte manualmente via interface web do Aurora, depois execute o pipeline!**

