# Status: Extração de Map Points do Arquivo .stcm

## ✅ O Que Foi Implementado

### 1. Backup Automático ✅
- Sistema faz backup do mapa atual ANTES de fazer upload
- Backup salvo em `backup_aurora_maps/backup_mapa_atual_TIMESTAMP.stcm`
- Protege contra perda de dados

### 2. Estratégia de Extração em Múltiplas Camadas ✅
1. **Tenta extrair do mapa recém-enviado** (após upload)
2. **Tenta extrair do backup baixado** (se disponível)
3. **Tenta parser heurístico** no arquivo original

### 3. Parser Heurístico Melhorado ✅
- Implementado método baseado na estrutura `MapPointDesc` do SDK (44 bytes)
- Implementado método alternativo de busca por sequências de floats
- Validação de coordenadas razoáveis

## ❌ Problema Atual

### Parser Heurístico Não Está Funcionando

O arquivo `.stcm` parece usar um formato serializado complexo (possivelmente MessagePack ou formato proprietário), não estruturas binárias simples. O parser atual não consegue extrair os map points diretamente do arquivo.

### Evidências

1. **Estrutura do arquivo**: Contém metadados em texto (JSON-like) e dados binários
2. **Formato serializado**: Não são estruturas binárias consecutivas simples
3. **Parser atual**: Não encontra sequências válidas de coordenadas 3D

## 🔧 Soluções Implementadas (Parciais)

### Solução 1: Extração do Backup ✅ (Implementado, mas não testado)

Se o backup foi baixado e contém map points válidos, o sistema:
1. Faz upload temporário do backup
2. Extrai os map points
3. Restaura o arquivo original

**Status**: Código implementado, mas não testado (dispositivo não estava conectado no último teste)

### Solução 2: Parser Heurístico ❌ (Implementado, mas não funciona)

Tentativas de extrair diretamente do arquivo `.stcm`:
- Busca por estruturas `MapPointDesc` (44 bytes)
- Busca por sequências de floats (coordenadas 3D)
- Validação de ranges razoáveis

**Status**: Não consegue encontrar dados válidos no formato atual

## 🎯 Próximos Passos para Resolver

### Opção 1: Melhorar Parser Heurístico (Recomendado)

**Tarefas**:
1. Analisar formato serializado do arquivo (MessagePack, Protocol Buffers, etc.)
2. Identificar biblioteca de serialização usada
3. Deserializar dados corretamente
4. Extrair seção de map points

**Ferramentas úteis**:
- `msgpack` (se for MessagePack)
- Análise hex dump mais profunda
- Comparar com arquivos de exemplo do SDK

### Opção 2: Usar SDK para Extrair do Backup

**Tarefas**:
1. Testar extração do backup quando dispositivo estiver conectado
2. Verificar se backup contém map points válidos
3. Usar como solução temporária

### Opção 3: Contatar Suporte Slamtec

**Tarefas**:
1. Solicitar documentação do formato `.stcm`
2. Solicitar biblioteca/ferramenta para parsing offline
3. Solicitar exemplo de código para extrair map points

## 📋 Código Implementado

### Arquivos Modificados

1. **`src/aurora_mapping/refinement/pointcloud_filters.py`**:
   - Backup automático antes do upload
   - Tentativa de extração do backup
   - Múltiplas estratégias de fallback

2. **`src/core/stcm_processor.py`**:
   - Parser baseado em `MapPointDesc` (44 bytes)
   - Parser alternativo por sequências de floats
   - Validação de coordenadas

## 🔍 Análise do Arquivo .stcm

### Estrutura Identificada

```
[Header] (metadados em texto/JSON-like)
  - creation_time
  - description: "Aurora feature map"
  - name: "aurora_featuremap"
  - type: "feature_map"
  - version
  - kf_count: 21
  - mp_count: 309 (0x0135)
  - ...

[Dados Binários] (formato serializado)
  - Keyframes
  - Map Points
  - Calibração de câmera
  - ...
```

### Desafios

1. **Formato serializado**: Não é binário simples
2. **Estrutura complexa**: Múltiplas seções com diferentes formatos
3. **Falta de documentação**: Formato proprietário não documentado

## 📝 Recomendações

### Curto Prazo
1. **Testar extração do backup** quando dispositivo estiver conectado
2. **Investigar formato serializado** (MessagePack, etc.)
3. **Analisar exemplos do SDK** para entender estrutura

### Médio Prazo
1. **Implementar deserialização correta** do formato
2. **Criar parser robusto** baseado em análise reversa
3. **Adicionar testes** com diferentes arquivos `.stcm`

### Longo Prazo
1. **Solicitar documentação oficial** do formato
2. **Criar biblioteca de parsing** reutilizável
3. **Documentar formato** para futuros desenvolvedores

## 🔗 Referências

- Estrutura `MapPointDesc`: `py_aurora_remote-main/cpp_sdk/aurora_remote_public/include/aurora_pubsdk_objects.h`
- SDK Python: `py_aurora_remote-main/python_bindings/slamtec_aurora_sdk/`
- Exemplos: `py_aurora_remote-main/examples/`

