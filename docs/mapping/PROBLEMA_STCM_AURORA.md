# Problema: Arquivos .stcm do Aurora

## Problema Identificado

⚠️ **IMPORTANTE**: O Aurora **SOMENTE** exporta mapas em formato `.stcm` (proprietário do Slamtec). **NÃO há opção de exportar em PLY ou PCD diretamente do Aurora Remote**.

O pipeline Aurora Mapping Studio precisa de arquivos em formato `.ply` ou `.pcd` para processar a nuvem de pontos, então é **necessário converter `.stcm` → `.ply`**.

### Por que isso acontece?

1. **Formato proprietário**: O formato `.stcm` do Aurora é binário e proprietário, não sendo suportado diretamente por bibliotecas padrão como Open3D.

2. **SDK necessário**: Para converter `.stcm` para outros formatos, é necessário o SDK específico do Aurora ou um parser customizado.

3. **Pipeline espera PLY/PCD**: O pipeline foi projetado para trabalhar com formatos padrão de nuvem de pontos (PLY, PCD) que são amplamente suportados.

## Solução: Converter .stcm para .ply

O sistema tenta converter automaticamente arquivos `.stcm` para `.ply`, mas isso requer:

### Opções de Conversão

**Opção 1: Conversão Automática (Atual)**
- O sistema detecta arquivos `.stcm` e tenta convertê-los automaticamente
- ⚠️ **Pode falhar** se o parser não conseguir extrair os pontos do formato proprietário

**Opção 2: SDK do Aurora (Recomendado)**
- Se você tiver acesso ao SDK do Aurora, use-o para converter `.stcm` → `.ply`
- Configure o SDK no sistema para conversão automática

**Opção 3: Parser Melhorado (Em desenvolvimento)**
- Melhorar o `STCMProcessor` para fazer engenharia reversa do formato
- Requer análise detalhada da estrutura binária do arquivo

### Usando Arquivo .stcm

O sistema aceita arquivos `.stcm` diretamente:

```bash
# Exemplo: executar pipeline com arquivo .stcm do Aurora
python src/main_mapping.py \
    --pipeline aurora_to_c1 \
    --input /caminho/para/mapa_aurora.stcm \
    --output data/pipeline_runs/meu_mapa
```

O sistema tentará converter automaticamente para `.ply` antes de processar.

## O que o Sistema Faz Automaticamente

O sistema detecta automaticamente arquivos `.stcm` e tenta convertê-los para `.ply`:

- ✅ **Detecção automática**: Se encontrar `.stcm`, tenta converter para `.ply`
- ⚠️ **Conversão pode falhar**: O formato `.stcm` é proprietário e o parser heurístico pode não funcionar
- 🔧 **Solução necessária**: Melhorar o parser ou usar SDK do Aurora

## Mensagens de Erro Comuns

### Erro: "Não foi possível converter arquivo .stcm para .ply"

**Causa**: O arquivo `.stcm` não pôde ser convertido automaticamente pelo parser heurístico.

**Soluções**:
1. **Use o SDK do Aurora** (se disponível) para converter `.stcm` → `.ply` antes de usar o pipeline
2. **Melhore o parser**: O `STCMProcessor` precisa ser melhorado para fazer engenharia reversa do formato
3. **Contate o suporte Slamtec**: Solicite documentação do formato `.stcm` ou ferramentas de conversão

### Erro: "Nuvem tem apenas 1 pontos após filtro de altura"

**Causa**: O arquivo `.stcm` foi convertido incorretamente para `.ply` (conversão falhou ou extraiu poucos pontos).

**Soluções**: 
1. Verifique se o arquivo `.stcm` não está corrompido
2. O parser `STCMProcessor` não está conseguindo extrair os pontos corretamente
3. **Necessário**: Melhorar o parser ou usar SDK do Aurora para conversão

### Erro: "Arquivo PLY parece estar vazio ou incompleto"

**Causa**: O arquivo PLY foi exportado incorretamente ou a exportação foi interrompida.

**Solução**:
1. Reexporte o mapa do Aurora Remote
2. Aguarde a conclusão completa da exportação
3. Verifique se o arquivo tem tamanho adequado (> 100 KB)

## Resumo

| Formato | Suportado? | Recomendado? | Notas |
|---------|-----------|--------------|-------|
| `.stcm` | ⚠️ Parcial | ⚠️ Necessário | **Único formato exportado pelo Aurora**. Conversão automática pode falhar |
| `.ply` | ✅ Sim | ✅ Sim | Formato padrão, amplamente suportado (resultado da conversão) |
| `.pcd` | ✅ Sim | ✅ Sim | Formato ROS, amplamente suportado (resultado da conversão) |

**Situação atual**: 
- ⚠️ O Aurora **SOMENTE** exporta em `.stcm`
- ⚠️ A conversão automática `.stcm` → `.ply` **pode falhar** (parser heurístico limitado)
- 🔧 **Necessário**: Melhorar o `STCMProcessor` ou usar SDK do Aurora para conversão confiável

