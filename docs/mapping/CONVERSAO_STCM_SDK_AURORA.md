# Conversão de .stcm para .ply usando o SDK do Aurora

## Visão Geral

O Aurora Mapping Studio agora suporta conversão de arquivos `.stcm` (formato proprietário do Aurora) para `.ply` usando o SDK oficial do Aurora. Esta é a solução recomendada para extrair nuvens de pontos 3D de mapas do Aurora.

## Como Funciona

O processo de conversão funciona da seguinte forma:

1. **Conexão com o Dispositivo**: O sistema conecta-se a um dispositivo Aurora (via rede)
2. **Verificação da Origem do Arquivo**:
   - **Se o arquivo `.stcm` está no computador (local)**: Faz upload do arquivo para o dispositivo Aurora
   - **Se o arquivo `.stcm` não está local (já está no dispositivo)**: Obtém os dados diretamente do mapa ativo no dispositivo
3. **Extração de Dados**: O SDK extrai os "map points" (nuvem de pontos 3D) do mapa
4. **Conversão para PLY**: Os pontos são convertidos para formato Open3D e salvos como `.ply`

**Nota**: Se você tem um arquivo `.stcm` que foi exportado do Aurora Remote e está no seu computador, o sistema fará upload para o dispositivo antes de extrair os pontos. Se o mapa já está no dispositivo Aurora, o sistema obterá os dados diretamente sem necessidade de upload.

## Configuração

### 1. Habilitar o SDK do Aurora

Edite o arquivo `config/mapping.json` e configure a seção `aurora`:

```json
{
  "aurora": {
    "enabled": true,
    "ip": "192.168.1.212",
    "port": 1445,
    "auto_discover": true,
    "sdk_path": null
  }
}
```

**Parâmetros:**
- `enabled`: `true` para habilitar o uso do SDK, `false` para desabilitar
- `ip`: Endereço IP do dispositivo Aurora (usado se `auto_discover` for `false`)
- `port`: Porta do dispositivo Aurora (padrão: 1445)
- `auto_discover`: `true` para descobrir automaticamente dispositivos na rede, `false` para usar IP fixo
- `sdk_path`: Caminho para o SDK (deixe `null` para usar o SDK em `py_aurora_remote-main/`)

### 2. Verificar o SDK

O SDK do Aurora deve estar disponível em:
```
robo_slam/py_aurora_remote-main/python_bindings/
```

Se o SDK estiver em outro local, ajuste o código em `src/aurora_mapping/refinement/pointcloud_filters.py`.

## Uso

### Via CLI

Execute o pipeline normalmente. Se houver um arquivo `.stcm` no diretório de captura, o sistema tentará convertê-lo automaticamente:

```bash
python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora/mapa-24112025-0-02.stcm \
  --output data/pipeline_runs/teste
```

### Via GUI

1. Abra a GUI: `python src/main_mapping.py --gui`
2. Selecione o pipeline `Aurora → C1`
3. Escolha o arquivo `.stcm` como entrada
4. Execute o pipeline

## Comportamento de Fallback

O sistema tenta a conversão na seguinte ordem:

1. **SDK do Aurora** (se `aurora.enabled: true` e dispositivo disponível)
2. **Parser Heurístico** (fallback se o SDK falhar ou não estiver configurado)

Se ambos falharem, o pipeline será interrompido com uma mensagem de erro explicativa.

## Requisitos

- **Dispositivo Aurora**: Deve estar ligado e acessível na rede
- **SDK do Aurora**: Deve estar disponível em `py_aurora_remote-main/python_bindings/`
- **Conexão de Rede**: O computador deve conseguir se conectar ao dispositivo Aurora

## Troubleshooting

### Erro: "SDK do Aurora não encontrado"

**Solução**: Verifique se o SDK está em `py_aurora_remote-main/python_bindings/`. Se estiver em outro local, ajuste o código.

### Erro: "Nenhum dispositivo Aurora encontrado"

**Soluções**:
1. Verifique se o dispositivo está ligado
2. Verifique a conexão de rede
3. Tente usar `auto_discover: false` e especifique o IP manualmente
4. Verifique se o dispositivo está na mesma rede

### Erro: "Upload falhou"

**Soluções**:
1. Verifique se o arquivo `.stcm` é válido
2. Verifique se há espaço suficiente no dispositivo
3. Tente novamente após alguns segundos
4. **Nota**: Se o mapa já está no dispositivo, você pode copiar o arquivo `.stcm` para o diretório de captura e o sistema tentará fazer upload. Alternativamente, se o mapa já está ativo no dispositivo, o sistema tentará obter os dados diretamente.

### Erro: "Nenhum map point encontrado"

**Soluções**:
1. Verifique se o arquivo `.stcm` contém dados de mapa válidos
2. Aguarde mais tempo para a sincronização dos dados
3. Verifique se o mapa foi gerado corretamente no Aurora

## Limitações

- **Requer Dispositivo**: A conversão via SDK requer um dispositivo Aurora físico conectado
- **Tempo de Processamento**: O upload e sincronização podem levar alguns segundos
- **Dependência de Rede**: Requer conexão de rede estável com o dispositivo

## Alternativas

Se não houver um dispositivo Aurora disponível, o sistema tentará usar o parser heurístico como fallback. No entanto, este parser pode não funcionar para todos os arquivos `.stcm`, pois o formato é proprietário e não documentado publicamente.

## Referências

- SDK do Aurora: `py_aurora_remote-main/`
- Exemplos do SDK: `py_aurora_remote-main/examples/`
- Documentação do SDK: `py_aurora_remote-main/docs/`

