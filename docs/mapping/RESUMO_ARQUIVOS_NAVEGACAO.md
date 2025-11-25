# 📁 Resumo: Arquivos Usados na Navegação

## 🎯 ARQUIVOS ESSENCIAIS

### 🔴 Para o Robô C1 (Navegação Física)

```
┌─────────────────────────────────────┐
│  Robô C1 (Hardware)                 │
│                                     │
│  Usa: .stcm                         │
│  └─ SEU_MAPA_clean.stcm            │
│     • Localização (SLAM)            │
│     • Navegação física              │
│     • Detecção de obstáculos        │
│                                     │
│  ⚠️  SEM ESTE ARQUIVO, O ROBÔ       │
│     NÃO CONSEGUE NAVEGAR!           │
└─────────────────────────────────────┘
```

**Arquivo**: `export/SEU_MAPA_clean_package/SEU_MAPA_clean.stcm`  
**Status**: ⭐ **CRÍTICO - OBRIGATÓRIO**

---

### 🟢 Para a Interface de Navegação (GUI)

```
┌─────────────────────────────────────┐
│  Interface de Navegação (GUI)       │
│                                     │
│  Usa 3 tipos de arquivos:           │
│                                     │
│  1. .pgm + .yaml                    │
│     └─ Fundo visual do mapa         │
│                                     │
│  2. *_pois.json                     │
│     └─ POIs (mesas, destinos)       │
│                                     │
│  ⚠️  SEM ESTES, A INTERFACE         │
│     FUNCIONA, MAS SEM VISUALIZAÇÃO  │
└─────────────────────────────────────┘
```

**Arquivos**:
1. `map2d/SEU_MAPA_clean.pgm` + `.yaml` - ⭐ **ESSENCIAL**
2. `annotation/SEU_MAPA_clean_pois.json` - ⭐ **RECOMENDADO**

---

## 📊 TABELA RESUMO

| Arquivo | Onde Usa | Para Que Serve | Essencial? |
|---------|----------|----------------|------------|
| **`.stcm`** | 🔴 Robô C1 | Navegação física | ⭐ **SIM** |
| **`.pgm`** | 🟢 Interface | Fundo visual | ⭐ **SIM** |
| **`.yaml`** | 🟢 Interface | Metadados do mapa | ⭐ **SIM** |
| **`*_pois.json`** | 🟢 Interface | POIs (destinos) | ⭐ **RECOMENDADO** |
| **`.ply`** | ❌ Nenhum | Intermediário | ❌ Não |
| **`*_preview.png`** | ❌ Nenhum | Visualização | ❌ Não |

---

## 🔄 FLUXO SIMPLIFICADO

```
1. Pipeline gera arquivos
   ↓
2. .stcm → Upload para C1 → Robô navega
   ↓
3. .pgm + .yaml → Carrega na interface → Visualização
   ↓
4. *_pois.json → Importa na interface → Destinos
```

---

## ✅ CHECKLIST: O Que Você Precisa

### Para Navegação Funcionar:
- [ ] ✅ `.stcm` carregado no C1
- [ ] ✅ `.pgm` + `.yaml` carregados na interface
- [ ] ✅ POIs importados (JSON ou criados manualmente)

### Arquivos Opcionais:
- [ ] `.ply` (não precisa)
- [ ] `*_preview.png` (não precisa)
- [ ] `*_layout.png` (não precisa)
- [ ] `metadata.json` (não precisa)

---

**Resumo**: Você precisa de **4 arquivos** para navegação completa:
1. `.stcm` (robô)
2. `.pgm` (interface)
3. `.yaml` (interface)
4. `*_pois.json` (interface)

