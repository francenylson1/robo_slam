# Processamento de Mapas: Aurora → C1

## Visão Geral

Este documento descreve o sistema de processamento de mapas que converte dados 3D do sensor Slamtec Aurora em mapas 2D compatíveis com o Slamtec C1.

## Arquitetura

O sistema é composto por 5 módulos principais:

1. **AuroraConnector** (`src/core/aurora_connector.py`)
   - Conecta-se ao Aurora via cabo de rede
   - Baixa mapas .stcm do sensor
   - Obtém nuvens de pontos em tempo real

2. **STCMProcessor** (`src/core/stcm_processor.py`)
   - Processa arquivos .stcm do Aurora
   - Extrai nuvens de pontos 3D
   - Extrai metadados do mapa

3. **MapConverter3DTo2D** (`src/core/map_converter_3d_to_2d.py`)
   - Converte nuvens de pontos 3D em mapas 2D
   - Gera occupancy grids
   - Aplica filtros e processamento

4. **PGMYAMLGenerator** (`src/core/pgm_yaml_generator.py`)
   - Gera arquivos PGM (Portable Gray Map)
   - Gera arquivos YAML com metadados
   - Formato compatível com ROS e SLAMWARE

5. **SlamwareC1Uploader** (`src/core/slamware_c1_uploader.py`)
   - Faz upload de mapas para o C1 via API SLAMWARE
   - Gerencia mapas no C1
   - Define mapa ativo

## Pipeline Completo

O módulo `AuroraToC1Pipeline` (`src/core/aurora_to_c1_pipeline.py`) integra todos os componentes:

```
Aurora (.stcm) → STCMProcessor → Point Cloud 3D
                                        ↓
                            MapConverter3DTo2D
                                        ↓
                            Occupancy Grid 2D
                                        ↓
                            PGMYAMLGenerator
                                        ↓
                            PGM + YAML Files
                                        ↓
                            SlamwareC1Uploader
                                        ↓
                                    C1 (SLAMWARE)
```

## Uso Básico

### Processar arquivo .stcm existente

```python
from src.core.aurora_to_c1_pipeline import AuroraToC1Pipeline

pipeline = AuroraToC1Pipeline(
    c1_ip="192.168.1.101",
    resolution=0.05  # 5cm
)

success = pipeline.run_full_pipeline(
    stcm_path="mapas/originais_aurora/mapa.stcm",
    output_dir="mapas/otimizados",
    map_name="salao_principal",
    upload_to_c1=True
)
```

### Via linha de comando

```bash
# Processar arquivo .stcm
python src/core/aurora_to_c1_pipeline.py \
    --stcm mapas/originais_aurora/mapa.stcm \
    --output-dir mapas/otimizados \
    --map-name salao_principal \
    --c1-ip 192.168.1.101

# Baixar do Aurora e processar
python src/core/aurora_to_c1_pipeline.py \
    --aurora-ip 192.168.1.100 \
    --c1-ip 192.168.1.101 \
    --map-name novo_mapa
```

## Configuração

### Endereços IP Padrão

- **Aurora**: `192.168.1.100` (porta TCP: 1445)
- **C1**: `192.168.1.101` (porta HTTP: 1445)

### Parâmetros de Conversão

- **Resolução**: 0.05m (5cm) - recomendado para navegação precisa
- **Altura**: 0.0 a 2.0m - faixa para considerar pontos (ajustar conforme ambiente)
- **Inflação de obstáculos**: 0.2m - margem de segurança

## Formato de Arquivos

### Arquivo .stcm (Aurora)

Formato proprietário do Slamtec Aurora contendo:
- Nuvem de pontos 3D
- Metadados do mapa
- Informações de pose

### Arquivo .pgm (Portable Gray Map)

Formato de imagem em escala de cinza:
- **0** (preto) = área ocupada
- **255** (branco) = área livre
- **205** (cinza) = área desconhecida

### Arquivo .yaml

Metadados do mapa no formato YAML:

```yaml
image: mapa.pgm
resolution: 0.05
origin: [0.0, 0.0, 0.0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.196
```

## Processamento Avançado

### Filtragem de Nuvem de Pontos

```python
from src.core.stcm_processor import STCMProcessor

processor = STCMProcessor("mapa.stcm")
processor.load()

# Filtra por altura (remove pontos abaixo do chão e muito altos)
filtered = processor.filter_point_cloud(
    z_min=0.0,      # Altura mínima
    z_max=2.0,      # Altura máxima
    remove_outliers=True
)
```

### Conversão com Processamento

```python
from src.core.map_converter_3d_to_2d import MapConverter3DTo2D

converter = MapConverter3DTo2D(resolution=0.05, height_range=(0.0, 2.0))
grid = converter.convert(point_cloud, method="projection")

# Aplica operações morfológicas (fecha buracos, remove ruído)
grid = converter.apply_morphology(grid, kernel_size=3)

# Infla obstáculos para margem de segurança
grid = converter.inflate_obstacles(grid, inflation_radius=0.2)
```

## Troubleshooting

### Erro de Conexão com Aurora

1. Verifique se o Aurora está ligado e conectado via cabo de rede
2. Verifique o endereço IP do Aurora (pode usar interface web do Aurora)
3. Verifique firewall/antivírus bloqueando conexão

### Erro de Conexão com C1

1. Verifique se o C1 está ligado e na mesma rede
2. Verifique o endereço IP do C1
3. Verifique se a API SLAMWARE está habilitada no C1

### Mapa com Muito Ruído

1. Ajuste a faixa de altura (`height_range`)
2. Aumente o tamanho do kernel nas operações morfológicas
3. Filtre outliers na nuvem de pontos

### Mapa com Obstáculos Faltando

1. Verifique se a resolução não está muito alta (células muito pequenas)
2. Reduza o limiar de ocupação (`occupied_thresh`)
3. Verifique se os pontos estão na faixa de altura correta

## Próximos Passos

- [ ] Implementar parsing completo do formato .stcm
- [ ] Adicionar suporte para múltiplos mapas no C1
- [ ] Implementar visualização 3D da nuvem de pontos
- [ ] Adicionar validação de qualidade do mapa
- [ ] Implementar calibração automática de parâmetros

## Referências

- [Documentação Slamtec Aurora](https://www.slamtec.com/)
- [Documentação SLAMWARE API](https://www.slamtec.com/)
- [Formato ROS Map](http://wiki.ros.org/map_server)

