# Plano de Teste e Investigação - Extração de Map Points

## 📋 Status Atual

### ✅ Implementado e Pronto para Teste

1. **Backup Automático**: Sistema faz backup do mapa atual antes do upload
2. **Estratégia Multi-Camadas**: Tenta extrair map points de várias fontes
3. **Parser Heurístico Melhorado**: Baseado na estrutura do SDK

### ⏳ Aguardando Teste Físico

O dispositivo Aurora não está acessível no momento. Quando estiver conectado, testar:

## 🧪 Teste 1: Com Dispositivo Conectado

### Objetivo
Verificar se a extração do backup funciona quando o dispositivo está disponível.

### Passos

1. **Verificar conectividade**:
   ```bash
   ping 192.168.11.1
   # ou verificar IP correto do dispositivo
   ```

2. **Executar teste completo**:
   ```bash
   python src/main_mapping.py \
     --pipeline aurora_to_c1 \
     --input mapas/legacy/originais_aurora/sala-maker-1.stcm \
     --output data/pipeline_runs/teste_completo \
     --steps capture,refinement
   ```

3. **Verificar resultados**:
   - ✅ Backup foi criado em `backup_aurora_maps/`
   - ✅ Upload foi concluído
   - ✅ Map points foram extraídos (do backup ou do mapa enviado)
   - ✅ Arquivo `.ply` foi gerado

### O Que Observar

1. **Se backup contém map points válidos**:
   - Sistema deve fazer upload do backup temporariamente
   - Extrair map points
   - Restaurar arquivo original
   - Salvar `.ply`

2. **Se backup não contém map points**:
   - Sistema deve tentar parser heurístico
   - Se falhar, investigar formato do arquivo

## 🔍 Investigação: Formato .stcm (Quando Dispositivo Não Disponível)

### Análise Inicial Realizada

1. **Estrutura identificada**:
   - Metadados em texto (JSON-like)
   - Dados binários serializados
   - Referências a "mp_count", "kf_count", etc.

2. **Tentativas de parsing**:
   - Estrutura `MapPointDesc` (44 bytes) - não encontrou dados válidos
   - Sequências de floats - valores inválidos
   - Formato parece ser serializado (MessagePack, Protocol Buffers, etc.)

### Próximos Passos de Investigação

#### 1. Identificar Formato de Serialização

```python
# Testar diferentes bibliotecas de serialização
import msgpack  # MessagePack
import pickle   # Python pickle
import json     # JSON (improvável, mas testar)
```

**Comandos para testar**:
```bash
# Verificar se é MessagePack
python3 -c "import msgpack; data=open('mapas/legacy/originais_aurora/sala-maker-1.stcm','rb').read(); msgpack.unpackb(data[:1000], raw=False)"

# Verificar padrões de serialização
hexdump -C mapas/legacy/originais_aurora/sala-maker-1.stcm | head -50
```

#### 2. Analisar Estrutura Binária

- Procurar por magic numbers (identificadores de formato)
- Identificar seções de dados (headers, tamanhos, etc.)
- Mapear estrutura de metadados vs dados binários

#### 3. Comparar com Exemplos do SDK

- Verificar se há exemplos de parsing de `.stcm` no SDK
- Analisar código C++ do SDK para entender formato
- Verificar se há ferramentas de conversão incluídas

#### 4. Engenharia Reversa

- Analisar múltiplos arquivos `.stcm` para identificar padrões
- Comparar arquivos de diferentes tamanhos
- Identificar campos fixos vs variáveis

## 📊 Resultados Esperados do Teste

### Cenário 1: Backup Contém Map Points ✅

**Resultado**: Sistema extrai map points do backup e salva `.ply`

**Ação**: 
- ✅ Solução funcionando
- Documentar processo
- Otimizar se necessário

### Cenário 2: Backup Não Contém Map Points ❌

**Resultado**: Sistema não consegue extrair map points

**Ação**:
- 🔍 Investigar formato do arquivo `.stcm`
- 🔍 Melhorar parser heurístico
- 🔍 Considerar contatar suporte Slamtec

### Cenário 3: Dispositivo Não Disponível ⏳

**Resultado**: Não é possível testar com dispositivo

**Ação**:
- 🔍 Focar em investigação do formato
- 🔍 Melhorar parser heurístico
- 🔍 Preparar para teste quando dispositivo estiver disponível

## 🎯 Prioridades

### Imediato (Quando Dispositivo Disponível)
1. ✅ Testar backup automático
2. ✅ Testar extração de map points do backup
3. ✅ Verificar se arquivo `.ply` é gerado corretamente

### Curto Prazo
1. 🔍 Investigar formato de serialização do `.stcm`
2. 🔍 Melhorar parser heurístico baseado em descobertas
3. 🔍 Testar com múltiplos arquivos `.stcm`

### Médio Prazo
1. 📚 Documentar formato `.stcm` (se descoberto)
2. 🔧 Criar parser robusto e reutilizável
3. ✅ Adicionar testes automatizados

## 📝 Checklist de Teste

Quando dispositivo estiver disponível:

- [ ] Dispositivo acessível na rede
- [ ] IP correto configurado em `config/mapping.json`
- [ ] SDK do Aurora funcionando
- [ ] Backup automático funcionando
- [ ] Upload de arquivo `.stcm` funcionando
- [ ] Extração de map points do backup funcionando
- [ ] Arquivo `.ply` gerado com pontos válidos
- [ ] Arquivo `.ply` pode ser visualizado/processado

## 🔗 Arquivos Relacionados

- `src/aurora_mapping/refinement/pointcloud_filters.py` - Lógica de conversão
- `src/core/stcm_processor.py` - Parser heurístico
- `config/mapping.json` - Configuração do Aurora
- `docs/mapping/STATUS_EXTRACAO_MAP_POINTS.md` - Status detalhado

