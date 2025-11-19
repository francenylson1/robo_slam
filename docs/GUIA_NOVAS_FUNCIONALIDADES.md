# 🆕 Guia: Novas Funcionalidades - Carregar PGM e Gerenciar POIs/Áreas

## ✅ O Que Foi Implementado

### 1. **Carregar Mapa PGM como Fundo**
- Carrega mapas PGM gerados do Aurora como fundo do mapa
- Carrega automaticamente metadados do arquivo YAML
- Ajusta escala automaticamente para caber na tela
- Grid opcional (pode desabilitar quando houver PGM)

### 2. **Exportar POIs para JSON**
- Exporta todos os POIs para arquivo JSON
- Formato compatível com estrutura definida em `mapas/pois/`
- Salva em `mapas/pois/` por padrão

### 3. **Importar POIs de JSON**
- Importa POIs de arquivo JSON
- Adiciona ao mapa atual
- Mantém POIs existentes (sobrescreve se mesmo nome)

### 4. **Exportar Áreas Proibidas para JSON**
- Exporta todas as áreas proibidas para arquivo JSON
- Formato compatível com estrutura definida em `mapas/areas_proibidas/`
- Salva em `mapas/areas_proibidas/` por padrão

### 5. **Importar Áreas Proibidas de JSON**
- Importa áreas proibidas de arquivo JSON
- Adiciona ao mapa atual
- Mantém áreas existentes

---

## 🚀 Como Usar

### **Carregar Mapa PGM**

1. Na interface, vá em **"Gerenciar Mapas"**
2. Clique em **"🗺️ Carregar PGM"**
3. Selecione o arquivo `.pgm` (ex: `mapas/otimizados/sala-maker-1.pgm`)
4. O mapa será carregado como fundo
5. O arquivo `.yaml` correspondente será carregado automaticamente

**Resultado:**
- ✅ Mapa PGM aparece como fundo
- ✅ POIs, áreas e robô aparecem sobre o mapa
- ✅ Grid pode ser desabilitado (opcional)

---

### **Exportar POIs**

1. Vá em **"Pontos de Interesse"**
2. Clique em **"💾 Exportar JSON"**
3. Escolha onde salvar (padrão: `mapas/pois/`)
4. Digite o nome do arquivo
5. Clique em "Salvar"

**Arquivo gerado:**
```json
{
  "map_id": "mapa_atual",
  "version": "1.0",
  "created_at": "2025-11-19T16:30:00",
  "pois": [
    {
      "id": "mesa_01",
      "name": "Mesa 1",
      "x": 2.5,
      "y": 3.0,
      "orientation": 0.0,
      "type": "delivery",
      "description": "POI Mesa 1",
      "enabled": true,
      "priority": "normal"
    }
  ]
}
```

---

### **Importar POIs**

1. Vá em **"Pontos de Interesse"**
2. Clique em **"📥 Importar JSON"**
3. Selecione o arquivo JSON (ex: `mapas/pois/pois_sala-maker-1.json`)
4. Os POIs serão adicionados ao mapa

**Resultado:**
- ✅ POIs aparecem no mapa
- ✅ Lista de POIs atualizada
- ✅ Podem ser editados/excluídos normalmente

---

### **Exportar Áreas Proibidas**

1. Vá em **"Áreas Proibidas"**
2. Clique em **"💾 Exportar JSON"**
3. Escolha onde salvar (padrão: `mapas/areas_proibidas/`)
4. Digite o nome do arquivo
5. Clique em "Salvar"

**Arquivo gerado:**
```json
{
  "map_id": "mapa_atual",
  "version": "1.0",
  "created_at": "2025-11-19T16:30:00",
  "forbidden_areas": [
    {
      "id": "area_0",
      "name": "Área 1",
      "type": "polygon",
      "points": [
        {"x": 1.0, "y": 1.0},
        {"x": 2.0, "y": 1.0},
        {"x": 2.0, "y": 2.0},
        {"x": 1.0, "y": 2.0}
      ],
      "priority": "high",
      "enabled": true,
      "description": "Área proibida: Área 1"
    }
  ]
}
```

---

### **Importar Áreas Proibidas**

1. Vá em **"Áreas Proibidas"**
2. Clique em **"📥 Importar JSON"**
3. Selecione o arquivo JSON (ex: `mapas/areas_proibidas/areas_sala-maker-1.json`)
4. As áreas serão adicionadas ao mapa

**Resultado:**
- ✅ Áreas aparecem no mapa
- ✅ Lista de áreas atualizada
- ✅ Podem ser editadas/excluídas normalmente

---

## 📋 Fluxo Completo Recomendado

### **1. Processar Mapa do Aurora**
```powershell
# Exportar BMP do Aurora → mapas/originais_aurora/sala-maker-1.bmp
# Processar
py converter_bmp_para_mapa.py mapas/originais_aurora/sala-maker-1.bmp --output sala-maker-1
```

### **2. Carregar Mapa na Interface**
1. Abra a interface: `py src/main.py`
2. Clique em **"🗺️ Carregar PGM"**
3. Selecione: `mapas/otimizados/sala-maker-1.pgm`

### **3. Adicionar POIs e Áreas**
1. Use os botões existentes para adicionar POIs
2. Use os botões existentes para desenhar áreas proibidas
3. Tudo funciona normalmente sobre o mapa PGM

### **4. Exportar para JSON**
1. Clique em **"💾 Exportar JSON"** em POIs
2. Clique em **"💾 Exportar JSON"** em Áreas
3. Arquivos salvos em `mapas/pois/` e `mapas/areas_proibidas/`

### **5. Usar em Outras Sessões**
1. Abra a interface
2. Carregue o PGM
3. Importe POIs e Áreas dos arquivos JSON
4. Continue trabalhando!

---

## ✅ Compatibilidade

**Tudo que já funcionava continua funcionando:**
- ✅ Adicionar/editar/excluir POIs (banco SQLite)
- ✅ Desenhar/excluir áreas (banco SQLite)
- ✅ Navegação
- ✅ Calibração
- ✅ Autosave

**Novas funcionalidades são opcionais:**
- ⚪ Carregar PGM é opcional
- ⚪ Exportar JSON é opcional (adicional ao banco)
- ⚪ Importar JSON é opcional (adicional ao banco)

---

## 🎯 Resumo Rápido

| Funcionalidade | Onde | Botão |
|---------------|------|-------|
| Carregar PGM | Gerenciar Mapas | 🗺️ Carregar PGM |
| Exportar POIs | Pontos de Interesse | 💾 Exportar JSON |
| Importar POIs | Pontos de Interesse | 📥 Importar JSON |
| Exportar Áreas | Áreas Proibidas | 💾 Exportar JSON |
| Importar Áreas | Áreas Proibidas | 📥 Importar JSON |

---

## 📝 Notas Importantes

1. **Mapa PGM:** Se não carregar, interface funciona como antes (só grid)
2. **JSON:** Exportação/importação é adicional ao banco SQLite (não substitui)
3. **Coordenadas:** POIs e áreas usam coordenadas do mundo (metros)
4. **Formato:** JSON segue estrutura definida em `mapas/templates/`

---

**Pronto para usar!** 🚀

