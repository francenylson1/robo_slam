# Solução Definitiva: Conversão .stcm → .ply

## 🎯 Problema Crítico Identificado

O Aurora mantém **apenas o mapa atual** na memória. Quando um novo mapa é gerado ou enviado via upload, ele **sobrescreve o mapa anterior**. Isso significa que:

1. ❌ **Perda de dados**: Se fizermos upload de um arquivo `.stcm`, o mapa atual é perdido
2. ❌ **Não podemos extrair map points**: Após upload, o SDK não retorna map points do mapa recém-enviado
3. ❌ **Risco de perda**: Se o processo falhar, perdemos o mapa original

## ✅ Solução Implementada

### Estratégia em 3 Etapas

#### 1. **Backup Automático do Mapa Atual** (ANTES do upload)
- Antes de fazer upload de um arquivo `.stcm`, o sistema faz **backup automático** do mapa atual
- O backup é salvo em `backup_aurora_maps/backup_mapa_atual_TIMESTAMP.stcm`
- Se o upload falhar ou os map points não forem extraídos, o mapa original pode ser restaurado

#### 2. **Upload do Arquivo .stcm**
- Após o backup, faz upload do arquivo `.stcm` para o dispositivo
- Monitora o progresso do upload

#### 3. **Extração de Map Points**
- Tenta extrair os map points do mapa recém-enviado
- Se não conseguir, tenta usar keyframes como fallback
- Se ainda assim falhar, tenta o parser heurístico no arquivo `.stcm` original

### Fluxo Completo

```
1. Arquivo .stcm local detectado
   ↓
2. Conecta ao Aurora
   ↓
3. Faz BACKUP do mapa atual (backup_aurora_maps/backup_*.stcm)
   ↓
4. Faz UPLOAD do arquivo .stcm
   ↓
5. Sincroniza dados do mapa (aguarda até 30s)
   ↓
6. Tenta extrair map points do dispositivo
   ↓
7. Se falhar, tenta usar keyframes como fallback
   ↓
8. Se ainda falhar, tenta parser heurístico no arquivo .stcm original
   ↓
9. Salva arquivo .ply
```

## 🔧 Implementação Técnica

### Código Atualizado

O arquivo `src/aurora_mapping/refinement/pointcloud_filters.py` foi atualizado para:

1. **Detectar arquivo .stcm local**
2. **Fazer backup automático** antes do upload
3. **Fazer upload** do arquivo
4. **Extrair map points** com múltiplas estratégias de fallback

### Estrutura de Backup

```
mapas/legacy/originais_aurora/
├── sala-maker-1.stcm
└── backup_aurora_maps/
    ├── backup_mapa_atual_20241119_143022.stcm
    ├── backup_mapa_atual_20241119_150145.stcm
    └── ...
```

## 📋 Limitações e Trabalhos Futuros

### Limitações Atuais

1. **Map Points após Upload**: O SDK não retorna map points imediatamente após upload
   - **Workaround**: Usar keyframes como fallback
   - **Solução futura**: Melhorar parser heurístico para extrair diretamente do `.stcm`

2. **Parser Heurístico**: Não funciona para todos os arquivos `.stcm`
   - **Solução futura**: Engenharia reversa do formato `.stcm` ou documentação oficial

3. **Restauração Manual**: O backup não é restaurado automaticamente
   - **Solução futura**: Implementar opção de restauração automática

### Melhorias Futuras

1. **Extração Direta do .stcm**: 
   - Melhorar `STCMProcessor` para extrair map points diretamente do arquivo
   - Evitar necessidade de upload

2. **Restauração Automática**:
   - Se extração falhar, restaurar mapa anterior automaticamente
   - Opção de configuração para habilitar/desabilitar

3. **Validação de Map Points**:
   - Verificar se map points extraídos são válidos antes de salvar
   - Comparar com keyframes para validar

## 🚀 Uso

O sistema funciona automaticamente. Quando um arquivo `.stcm` é processado:

```bash
python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora/sala-maker-1.stcm \
  --output data/pipeline_runs/teste \
  --steps capture,refinement
```

O sistema irá:
1. ✅ Fazer backup do mapa atual
2. ✅ Fazer upload do arquivo
3. ✅ Tentar extrair map points
4. ✅ Salvar arquivo .ply

## 📝 Notas Importantes

- **Backup é automático**: Não precisa configurar nada
- **Backups são preservados**: Não são deletados automaticamente
- **Restauração manual**: Se precisar restaurar, use o SDK para fazer upload do backup
- **Múltiplos backups**: Cada execução cria um novo backup com timestamp

## 🔗 Referências

- Documentação do SDK: `py_aurora_remote-main/README.md`
- Exemplo de upload/download: `py_aurora_remote-main/examples/vslam_map_saveload.py`
- Parser heurístico: `src/core/stcm_processor.py`

