# 🗺️ Sistema de Gestão de Mapas - Robô Garçom Autônomo

Esta pasta contém toda a estrutura para gerenciamento, otimização e processamento de mapas para navegação autônoma do robô.

## 📁 Estrutura de Pastas

### `legacy/originais_aurora/`
Repositório frio com varreduras brutas geradas pelo sensor Aurora. Estes dados não são usados diretamente pelo robô e servem apenas como referência para reconstruções futuras.

**Formato esperado:**
- Arquivos de varredura LIDAR
- Nuvens de pontos
- Dados brutos de sensoriamento

**Convenção de nomenclatura:**
```
mapa_aurora_YYYYMMDD_HHMMSS.extensão
Exemplo: mapa_aurora_20251119_143000.dat
```

### `c1/otimizados/`
Mapas já convertidos para o ecossistema Slamtec C1 e prontos para testes internos, incluindo:
- Redução de ruído
- Interpolação de pontos
- Calibração de escala
- Ajustes de precisão

**Formato esperado:**
- Arquivos JSON ou formato binário otimizado
- Incluem metadados de processamento

**Convenção de nomenclatura:**
```
mapa_opt_[nome_ambiente]_v[versao].json
Exemplo: mapa_opt_salao_principal_v1.json
```

### `c1/pois/`
Pontos de Interesse (POIs) - Localizações importantes para navegação:
- Mesas
- Pontos de entrega
- Estação de carregamento
- Ponto inicial (home)
- Áreas de espera

**Formato de arquivo (JSON):**
```json
{
  "map_id": "salao_principal_v1",
  "pois": [
    {
      "id": "mesa_01",
      "name": "Mesa 1",
      "x": 100.5,
      "y": 250.3,
      "orientation": 90.0,
      "type": "delivery",
      "description": "Mesa próxima à janela"
    }
  ]
}
```

### `c1/areas_proibidas/`
Definições de zonas onde o robô não deve navegar:
- Áreas de risco
- Zonas reservadas
- Obstáculos permanentes
- Áreas de circulação restrita

**Formato de arquivo (JSON):**
```json
{
  "map_id": "salao_principal_v1",
  "forbidden_areas": [
    {
      "id": "area_cozinha",
      "name": "Entrada da Cozinha",
      "type": "polygon",
      "points": [
        {"x": 50.0, "y": 100.0},
        {"x": 50.0, "y": 150.0},
        {"x": 80.0, "y": 150.0},
        {"x": 80.0, "y": 100.0}
      ],
      "priority": "high"
    }
  ]
}
```

### `deploy_ready/`
Pacotes finais aprovados para envio ao robô. Cada diretório deve conter o trio:
- `mapa_c1.stcm`
- `pois.json`
- `layout.png`

## 🔄 Fluxo de Trabalho

```
1. Sensor Aurora → `legacy/originais_aurora/`
2. Pipeline Aurora Mapping Studio → `c1/otimizados/`
3. Editor de POIs/Áreas → `c1/pois/` e `c1/areas_proibidas/`
4. Validação C1 → `deploy_ready/`
5. Integração → Sistema de Navegação
```

## 📊 Formatos de Arquivo Suportados

- **Mapas originais:** `.dat`, `.lidar`, `.pcd` (nuvem de pontos)
- **Mapas otimizados:** `.json`, `.map`
- **Configurações:** `.json`

## 🛠️ Scripts de Processamento

Scripts relacionados ao processamento de mapas devem ser criados em:
- `src/core/map_processor.py` - Processamento principal
- `src/core/map_optimizer.py` - Otimização de mapas
- `tests/teste_processamento_mapas.py` - Testes

## 📝 Metadados

Cada mapa otimizado deve incluir metadados:
```json
{
  "metadata": {
    "version": "1.0",
    "created_at": "2025-11-19T14:30:00",
    "source_file": "mapa_aurora_20251119_143000.dat",
    "processed_by": "map_optimizer v2.0",
    "dimensions": {
      "width": 500,
      "height": 300,
      "unit": "cm"
    },
    "resolution": 1.0,
    "coordinate_system": "cartesian"
  }
}
```

## ⚙️ Integração com o Sistema

Os mapas desta pasta são carregados pelo sistema através de:
- `src/core/map_manager.py` - Gerenciador de mapas
- `src/interfaces/map_widget.py` - Visualização de mapas

## 🔐 Boas Práticas

1. **Versionamento:** Sempre versione mapas otimizados
2. **Backup:** Mantenha cópias dos mapas originais
3. **Documentação:** Documente alterações significativas
4. **Validação:** Teste mapas antes de usar em produção
5. **Nomenclatura:** Siga as convenções estabelecidas

## 📞 Suporte

Para dúvidas sobre processamento de mapas, consulte a documentação em `docs/`.

