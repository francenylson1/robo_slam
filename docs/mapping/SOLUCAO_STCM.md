# Solução para Processamento de Arquivos .stcm

## Problema Identificado

O formato `.stcm` do Slamtec Aurora é um formato binário proprietário que não é diretamente suportado por bibliotecas padrão. A análise do arquivo mostra:

- Formato binário estruturado
- Metadados em texto (creation_time, description, name)
- Dados de nuvem de pontos em formato binário
- Tamanho típico: 4-5 MB

## Soluções Possíveis

### Opção 1: Exportar do Aurora em Formato Suportado (RECOMENDADO)

O Aurora geralmente permite exportar mapas em formatos mais comuns:

1. **Interface Web do Aurora:**
   - Acesse `http://<IP_DO_AURORA>`
   - Vá em "Map" ou "Export"
   - Exporte como:
     - **PLY** (Point Cloud) - formato suportado pelo Open3D
     - **PCD** (Point Cloud Data) - formato ROS
     - **BMP/PNG** - mapa 2D já processado

2. **Software do Aurora:**
   - Use o software oficial do Aurora
   - Exporte o mapa em formato suportado

### Opção 2: Usar SDK do Aurora

Se o Aurora fornece SDK:

1. Instale o SDK do Aurora
2. Use as funções do SDK para ler o arquivo .stcm
3. Exporte os dados em formato suportado

### Opção 3: Implementar Parser Customizado

Para implementar um parser completo do formato .stcm, é necessário:

1. **Documentação do formato:**
   - Obter documentação oficial do formato .stcm
   - Ou fazer engenharia reversa completa

2. **Análise detalhada:**
   - Usar hex editor para mapear estrutura
   - Identificar seções de dados
   - Entender codificação de coordenadas

3. **Implementação:**
   - Parser binário específico
   - Validação de dados
   - Tratamento de diferentes versões

## Solução Temporária Implementada

O código atual tenta extrair pontos usando métodos heurísticos, mas pode não funcionar para todos os arquivos.

### Como Usar Formato Alternativo

Se você exportar o mapa do Aurora em formato PLY ou PCD:

```python
# Para arquivo PLY
import open3d as o3d
pcd = o3d.io.read_point_cloud("mapa.ply")
points = np.asarray(pcd.points)

# Para arquivo PCD
pcd = o3d.io.read_point_cloud("mapa.pcd")
points = np.asarray(pcd.points)
```

Depois, use o conversor 3D→2D diretamente:

```python
from src.core.map_converter_3d_to_2d import MapConverter3DTo2D
from src.core.pgm_yaml_generator import PGMYAMLGenerator

converter = MapConverter3DTo2D(resolution=0.05)
grid = converter.convert(points)

generator = PGMYAMLGenerator(grid, 0.05, (0, 0, 0))
generator.generate_both("mapas/otimizados/mapa_processado")
```

## Próximos Passos

1. **Imediato:** Exportar mapa do Aurora em formato PLY/PCD
2. **Curto prazo:** Verificar se há SDK do Aurora disponível
3. **Longo prazo:** Implementar parser completo do .stcm (se necessário)

## Referências

- [Open3D - Formatos Suportados](http://www.open3d.org/docs/release/tutorial/geometry/pointcloud.html)
- Documentação do Slamtec Aurora (consultar manual do dispositivo)

