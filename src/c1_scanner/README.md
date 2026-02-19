# 📁 C1 Scanner - Processamento de Mapas

Este módulo contém as ferramentas para processar mapas BMP do Aurora Remote e convertê-los para o formato PGM/YAML usado pela aplicação.

## 📂 Estrutura de Pastas

```
src/c1_scanner/
├── __init__.py
├── main_scanner.py                    # Script principal de processamento
├── README.md                          # Este arquivo
└── C1_mapas_processados/              # Mapas processados
    └── c1_sala_maker/                 # Subpasta com conjunto de arquivos
        ├── mapa_final_refinado.pgm    # Mapa de ocupação
        ├── mapa_final_refinado.yaml   # Metadados do mapa
        └── mapa_final_refinado.png    # Visualização
```

## 🚀 Como Usar

### Processar um Mapa BMP

```bash
# Processar mapa básico
python src/c1_scanner/main_scanner.py mapa_original.bmp

# Especificar diretório de saída e nome do mapa
python src/c1_scanner/main_scanner.py mapa_original.bmp \
  --output src/c1_scanner/C1_mapas_processados \
  --name c1_sala_maker
```

### O que o Script Faz

1. **Carrega** o BMP original do Aurora Remote
2. **Aplica correções**:
   - Rotação de 90° no sentido horário
   - Espelhamento horizontal
3. **Remove** bordas e áreas cinza
4. **Detecta** o contorno principal do ambiente
5. **Recorta** automaticamente
6. **Metrifica** o mapa (12m x 6m padrão)
7. **Gera** três arquivos:
   - `.pgm` - Mapa de ocupação (usado pela aplicação)
   - `.yaml` - Metadados (resolução, origem, etc.)
   - `_refinado.png` - Visualização

## 📋 Estrutura de Arquivos

Cada mapa processado deve estar em sua própria subpasta dentro de `C1_mapas_processados/`. Cada subpasta contém:

- **`.pgm`** - Mapa de ocupação em formato PGM
- **`.yaml`** - Arquivo de metadados com:
  - `image`: Nome do arquivo PGM
  - `resolution`: Resolução em metros por pixel
  - `origin`: Origem do mapa [x, y, theta]
  - `occupied_thresh`: Limiar para células ocupadas
  - `free_thresh`: Limiar para células livres
  - `negate`: Se deve negar a imagem (0 ou 1)

## 🎯 Uso na Aplicação

Quando você executar `main.py`, os mapas em `C1_mapas_processados/` aparecerão automaticamente na lista de mapas disponíveis ao clicar em "🗺️ Carregar PGM".

Os mapas são identificados com o prefixo `C1/` seguido do nome da subpasta, por exemplo:
- `C1/c1_sala_maker/mapa_final_refinado`

## ⚙️ Configurações

As configurações padrão do ambiente podem ser ajustadas no início do `main_scanner.py`:

```python
TARGET_WIDTH_METERS = 12.0   # eixo maior
TARGET_HEIGHT_METERS = 6.0   # eixo menor
```

## 📝 Notas

- O script assume que o mapa BMP vem do Aurora Remote com rotação e espelhamento incorretos
- A metrificação é calculada automaticamente baseada nas dimensões do contorno detectado
- O mapa PGM usa valores invertidos (255 - valor) para compatibilidade com ROS/AMCL









