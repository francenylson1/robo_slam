# Scripts de Processamento de Mapas

Esta pasta contém scripts auxiliares para processamento de mapas.

## Scripts Disponíveis

### `process_aurora_map.py`
Script principal para processar mapas do Aurora e gerar arquivos para o C1.

**Uso:**
```bash
# Processar arquivo .stcm existente
python src/core/aurora_to_c1_pipeline.py --stcm mapas/originais_aurora/mapa.stcm --output-dir mapas/otimizados

# Baixar do Aurora e processar
python src/core/aurora_to_c1_pipeline.py --aurora-ip 192.168.1.100 --c1-ip 192.168.1.101

# Apenas gerar arquivos (sem upload)
python src/core/aurora_to_c1_pipeline.py --stcm mapa.stcm --no-upload
```

## Parâmetros

- `--stcm`: Caminho para arquivo .stcm (opcional, se não fornecido baixa do Aurora)
- `--aurora-ip`: IP do Aurora (padrão: 192.168.1.100)
- `--c1-ip`: IP do C1 (padrão: 192.168.1.101)
- `--output-dir`: Diretório de saída (padrão: mapas/otimizados)
- `--map-name`: Nome do mapa (padrão: aurora_map)
- `--resolution`: Resolução em metros (padrão: 0.05 = 5cm)
- `--no-upload`: Não fazer upload para o C1

