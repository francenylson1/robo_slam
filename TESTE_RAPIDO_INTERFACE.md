# 🧪 Guia de Teste Rápido - Funcionalidades da Interface

## ✅ Funcionalidades Implementadas

Todas as funcionalidades foram implementadas e testadas com sucesso!

## 🚀 Como Testar

### 1. Teste Automatizado (Recomendado)

Execute o script de teste automatizado:

```bash
python3 tests/teste_funcionalidades_interface.py
```

**Resultado esperado:**
```
✅ Todos os testes passaram!
Total: 3/3 testes passaram
```

### 2. Teste Manual na Interface Gráfica

#### 2.1. Carregar Mapa PGM

1. Abra a interface:
   ```bash
   python3 src/main.py
   ```

2. Na seção **"🗺️ Gerenciar Mapas"**, clique em **"🗺️ Carregar PGM"**

3. Selecione um arquivo `.pgm` (ex: `mapas/otimizados/sala-maker-1.pgm`)

4. O mapa deve aparecer como fundo no widget

5. O arquivo `.yaml` correspondente será carregado automaticamente

**Verificação:**
- ✅ Mapa aparece como fundo
- ✅ POIs e áreas aparecem sobre o mapa
- ✅ Coordenadas estão corretas

#### 2.2. Exportar POIs

1. Adicione alguns POIs no mapa (ou carregue um mapa existente com POIs)

2. Na seção **"📍 Pontos de Interesse"**, clique em **"💾 Exportar JSON"**

3. Escolha onde salvar (padrão: `mapas/pois/`)

4. Verifique se o arquivo foi criado

**Verificação:**
- ✅ Arquivo JSON criado
- ✅ Formato correto (verifique o conteúdo)
- ✅ Todos os POIs foram exportados

#### 2.3. Importar POIs

1. Na seção **"📍 Pontos de Interesse"**, clique em **"📥 Importar JSON"**

2. Selecione um arquivo JSON de POIs (ex: `mapas/pois/pois_*.json`)

3. Os POIs devem aparecer no mapa

**Verificação:**
- ✅ POIs aparecem no mapa
- ✅ Coordenadas corretas
- ✅ Tipos corretos

#### 2.4. Exportar Áreas Proibidas

1. Adicione algumas áreas proibidas no mapa (ou carregue um mapa existente)

2. Na seção **"🚫 Áreas Proibidas"**, clique em **"💾 Exportar JSON"**

3. Escolha onde salvar (padrão: `mapas/areas_proibidas/`)

4. Verifique se o arquivo foi criado

**Verificação:**
- ✅ Arquivo JSON criado
- ✅ Formato correto (verifique o conteúdo)
- ✅ Todas as áreas foram exportadas

#### 2.5. Importar Áreas Proibidas

1. Na seção **"🚫 Áreas Proibidas"**, clique em **"📥 Importar JSON"**

2. Selecione um arquivo JSON de áreas (ex: `mapas/areas_proibidas/areas_*.json`)

3. As áreas devem aparecer no mapa

**Verificação:**
- ✅ Áreas aparecem no mapa
- ✅ Coordenadas corretas
- ✅ Formato correto

## 📋 Checklist de Validação

### Carregamento de PGM
- [ ] Mapa PGM carrega corretamente
- [ ] YAML é carregado automaticamente
- [ ] Escala é ajustada automaticamente
- [ ] POIs aparecem sobre o mapa
- [ ] Áreas aparecem sobre o mapa

### Exportação de POIs
- [ ] Arquivo JSON é criado
- [ ] Formato está correto
- [ ] Todos os POIs foram exportados
- [ ] Metadados estão corretos

### Importação de POIs
- [ ] POIs são importados corretamente
- [ ] Coordenadas estão corretas
- [ ] Tipos estão corretos
- [ ] POIs aparecem no mapa

### Exportação de Áreas
- [ ] Arquivo JSON é criado
- [ ] Formato está correto
- [ ] Todas as áreas foram exportadas
- [ ] Coordenadas estão corretas

### Importação de Áreas
- [ ] Áreas são importadas corretamente
- [ ] Coordenadas estão corretas
- [ ] Áreas aparecem no mapa
- [ ] Formato está correto

## 🐛 Troubleshooting

### Problema: Mapa PGM não carrega

**Solução:**
- Verifique se o arquivo `.pgm` existe
- Verifique se o arquivo `.yaml` correspondente existe
- Verifique os logs no console para erros

### Problema: POIs não aparecem após importação

**Solução:**
- Verifique o formato do JSON
- Verifique se as coordenadas estão no formato correto
- Verifique os logs no console

### Problema: Áreas não aparecem após importação

**Solução:**
- Verifique se a área tem pelo menos 3 pontos
- Verifique o formato do JSON
- Verifique as coordenadas

## 📝 Notas

- Os arquivos JSON são salvos em `mapas/pois/` e `mapas/areas_proibidas/`
- O formato JSON é compatível com templates existentes
- A exportação/importação é adicional ao banco de dados (não substitui)

## ✅ Status dos Testes

**Última execução:** Todos os testes passaram (3/3)

- ✅ Carregamento PGM
- ✅ Exportação/Importação POIs
- ✅ Exportação/Importação Áreas

