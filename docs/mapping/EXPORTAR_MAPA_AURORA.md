# 📤 Guia: Exportar Mapa do Aurora

## Passo a Passo Completo

### 1️⃣ Conectar ao Aurora

O Aurora está configurado no IP: **192.168.11.1**

#### Opção A: Usar o Script Automático

```powershell
py exportar_mapa_aurora.py --ip 192.168.11.1
```

O script irá:
- ✅ Verificar se o Aurora está acessível
- ✅ Abrir o navegador automaticamente na interface web
- ✅ Fornecer instruções detalhadas

#### Opção B: Acesso Manual

1. Abra seu navegador web
2. Acesse: `http://192.168.11.1`
3. Se não funcionar, tente: `https://192.168.11.1`

### 2️⃣ Localizar Menu de Exportação

Na interface web do Aurora, procure por:

- **Menu "Map"** ou **"Mapa"**
- **Menu "Export"** ou **"Exportar"**
- **Menu "Download"** ou **"Baixar"**
- **Menu "File"** → **"Export"**
- **Ícone de download** ou **seta para baixo**

### 3️⃣ Selecionar o Mapa

1. Se houver múltiplos mapas, selecione o desejado
2. Geralmente há uma lista de mapas salvos
3. O mapa pode ter um nome como "sala-maker-1" ou similar

### 4️⃣ Escolher Formato de Exportação

**Formatos Recomendados (em ordem de preferência):**

1. **PLY (Point Cloud)** ⭐ RECOMENDADO
   - Formato padrão para nuvens de pontos
   - Suportado pelo Open3D
   - Mantém informações 3D completas

2. **PCD (Point Cloud Data)**
   - Formato ROS
   - Também suportado pelo Open3D
   - Boa alternativa ao PLY

3. **BMP/PNG (Mapa 2D)**
   - Já processado em 2D
   - Pode ser usado diretamente
   - Perde informações 3D

4. **STCM** ⚠️ NÃO RECOMENDADO
   - Formato proprietário
   - Requer parser específico
   - Use apenas se outros formatos não estiverem disponíveis

### 5️⃣ Salvar o Arquivo

Salve o arquivo exportado em:

```
D:\robo_slam\mapas\originais_aurora\
```

**Nome sugerido:** `sala-maker-1.ply` (ou `.pcd`)

### 6️⃣ Processar o Arquivo Exportado

Após exportar, execute:

```powershell
# Para arquivo PLY
py converter_ply_para_mapa.py mapas/originais_aurora/sala-maker-1.ply --output sala-maker-1

# Para arquivo PCD
py converter_ply_para_mapa.py mapas/originais_aurora/sala-maker-1.pcd --output sala-maker-1
```

Isso irá:
- ✅ Carregar a nuvem de pontos
- ✅ Converter para mapa 2D
- ✅ Gerar arquivos PGM + YAML
- ✅ Salvar em `mapas/otimizados/`

### 7️⃣ Verificar Resultado

```powershell
# Visualizar o mapa gerado
py visualizar_mapa.py mapas/otimizados/sala-maker-1.pgm
```

## Troubleshooting

### Problema: Não consigo acessar a interface web

**Soluções:**
1. Verifique se o Aurora está ligado
2. Verifique se o cabo de rede está conectado
3. Verifique o IP do Aurora:
   ```powershell
   ping 192.168.11.1
   ```
4. Tente acessar via HTTPS: `https://192.168.11.1`
5. Verifique se há firewall bloqueando

### Problema: Não encontro o menu de exportação

**Soluções:**
1. Procure em diferentes menus (Map, File, Tools, Settings)
2. Verifique se há um botão de download no mapa visualizado
3. Consulte o manual do Aurora
4. Alguns modelos podem ter interface diferente

### Problema: Formato PLY/PCD não está disponível

**Soluções:**
1. Use BMP/PNG se disponível (mapa 2D)
2. Exporte STCM e tente processar (pode não funcionar)
3. Verifique se há atualização de firmware do Aurora
4. Use o software desktop do Aurora (se disponível)

### Problema: Arquivo exportado está vazio ou corrompido

**Soluções:**
1. Tente exportar novamente
2. Verifique o tamanho do arquivo (deve ser > 1MB para mapas reais)
3. Tente outro formato
4. Verifique se o mapa foi salvo corretamente no Aurora

## Verificação Rápida

Execute para verificar se há arquivos exportados:

```powershell
py exportar_mapa_aurora.py --verificar-arquivos
```

## Próximos Passos Após Exportação

1. ✅ Arquivo exportado em formato PLY/PCD
2. ✅ Processado com `converter_ply_para_mapa.py`
3. ✅ Arquivos PGM + YAML gerados
4. ✅ Mapa visualizado e validado
5. ⏭️ Upload para C1 (quando disponível)

## Referências

- Manual do Slamtec Aurora
- Interface web do Aurora: `http://192.168.11.1`
- Documentação: `docs/SOLUCAO_STCM.md`

