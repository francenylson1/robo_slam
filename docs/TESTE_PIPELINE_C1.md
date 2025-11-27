# 🧪 Guia de Testes - C1 Mapping Studio

## 📋 Visão Geral

Este guia explica como testar o sistema C1 Mapping antes de integrar com o `main.py`.

---

## 🎯 Pipeline Completo

O pipeline completo consiste em 4 etapas:

```
1. DETECÇÃO → 2. COLETA → 3. PROCESSAMENTO → 4. EXPORTAÇÃO
     ↓              ↓              ↓                ↓
  Detecta C1   Coleta scans   Gera mapa      Exporta PGM/YAML
```

---

## 🧪 TESTE 1: Detecção do C1

**Objetivo**: Verificar se o C1 está sendo detectado corretamente.

```bash
# Teste básico
python3 src/main_c1_mapping.py detect

# Teste detalhado (verbose)
python3 src/main_c1_mapping.py detect --verbose
```

**Resultado esperado**:
- ✅ C1 detectado via Serial
- ✅ Porta: /dev/ttyUSB0 (ou similar)
- ✅ Validado como C1: SIM

**Se falhar**:
- Verifique se o C1 está conectado e ligado (LED verde)
- Verifique se os drivers USB estão instalados
- Execute: `python3 scripts/teste_c1_diagnostico.py`

---

## 🧪 TESTE 2: Coleta de Scans

**Objetivo**: Coletar dados de varredura do C1.

```bash
# Coleta rápida (10 segundos)
python3 src/main_c1_mapping.py collect --duration 10 --output mapas/c1/test

# Coleta completa (60 segundos)
python3 src/main_c1_mapping.py collect --duration 60 --output mapas/c1/test
```

**Resultado esperado**:
- ✅ Scan iniciado com sucesso
- ✅ Scans coletados: X scans
- ✅ Arquivo salvo: `mapas/c1/test/scans_*.json`

**Verificar arquivo gerado**:
```bash
# Lista arquivos gerados
ls -lh mapas/c1/test/scans_*.json

# Verifica conteúdo (primeiras linhas)
head -30 mapas/c1/test/scans_*.json
```

**Se falhar**:
- Verifique se o C1 está conectado
- Verifique se a porta está acessível
- Execute: `python3 scripts/teste_protocolo_c1.py`

---

## 🧪 TESTE 3: Processamento SLAM

**Objetivo**: Converter scans em mapa de ocupação.

```bash
# Processa scans coletados
python3 src/main_c1_mapping.py process \
  --input mapas/c1/test/scans_*.json \
  --output mapas/c1/test \
  --resolution 0.05
```

**Resultado esperado**:
- ✅ X scans encontrados
- ✅ Mapa gerado: WIDTHxHEIGHT pixels
- ✅ Arquivo salvo: `mapas/c1/test/map_*.npy`
- ✅ Metadados: `mapas/c1/test/map_*_metadata.json`

**Verificar arquivos gerados**:
```bash
# Lista arquivos
ls -lh mapas/c1/test/map_*

# Verifica metadados
cat mapas/c1/test/map_*_metadata.json
```

**Informações importantes**:
- Dimensões do mapa (pixels)
- Tamanho real (metros)
- Percentual ocupado/livre/desconhecido

---

## 🧪 TESTE 4: Exportação PGM/YAML

**Objetivo**: Exportar mapa em formato compatível com navegação.

```bash
# Exporta mapa processado
python3 src/main_c1_mapping.py export \
  --map mapas/c1/test/map_*.npy \
  --output mapas/c1/test \
  --name mapa_teste
```

**Resultado esperado**:
- ✅ Mapa exportado com sucesso
- ✅ PGM: `mapas/c1/test/mapa_teste.pgm`
- ✅ YAML: `mapas/c1/test/mapa_teste.yaml`

**Verificar arquivos**:
```bash
# Verifica tamanho dos arquivos
ls -lh mapas/c1/test/*.{pgm,yaml}

# Verifica conteúdo do YAML
cat mapas/c1/test/mapa_teste.yaml

# Verifica formato do PGM
file mapas/c1/test/mapa_teste.pgm
```

**Formato esperado**:
- PGM: Netpbm image data, greymap
- YAML: Contém `image`, `resolution`, `origin`

---

## 🧪 TESTE 5: Validação dos Arquivos

**Objetivo**: Verificar se os arquivos são válidos e compatíveis.

### 5.1. Validar PGM

```bash
# Verifica se é um PGM válido
file mapas/c1/test/mapa_teste.pgm

# Tenta abrir com visualizador (se disponível)
# No Linux:
xdg-open mapas/c1/test/mapa_teste.pgm
```

**Resultado esperado**:
- Arquivo existe e tem tamanho > 0
- Formato: Netpbm image data, greymap
- Pode ser aberto em visualizador de imagens

### 5.2. Validar YAML

```bash
# Verifica conteúdo do YAML
cat mapas/c1/test/mapa_teste.yaml

# Valida estrutura JSON (se converter)
python3 -c "import yaml; yaml.safe_load(open('mapas/c1/test/mapa_teste.yaml'))"
```

**Resultado esperado**:
- YAML válido e bem formatado
- Contém campos: `image`, `resolution`, `origin`
- `image` aponta para o arquivo PGM correto

### 5.3. Verificar Compatibilidade com main.py

```bash
# Verifica se main.py pode carregar o mapa
python3 -c "
from pathlib import Path
from src.interfaces.map_widget import MapWidget
from PyQt5.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
widget = MapWidget()
pgm_path = Path('mapas/c1/test/mapa_teste.pgm')
if pgm_path.exists():
    try:
        widget.load_pgm_map(str(pgm_path))
        print('✅ Mapa carregado com sucesso no MapWidget')
    except Exception as e:
        print(f'❌ Erro ao carregar: {e}')
else:
    print('❌ Arquivo PGM não encontrado')
"
```

---

## 🚀 TESTE AUTOMATIZADO COMPLETO

**Script de teste completo** que executa todos os testes automaticamente:

```bash
# Executa todos os testes (coleta 10s)
python3 scripts/teste_pipeline_completo.py --duration 10

# Executa todos os testes (coleta 60s)
python3 scripts/teste_pipeline_completo.py --duration 60

# Pula coleta e usa arquivo existente
python3 scripts/teste_pipeline_completo.py \
  --skip-collection \
  --scan-file mapas/c1/test/scans_*.json
```

**O que o script faz**:
1. ✅ Testa detecção do C1
2. ✅ Coleta scans (ou usa arquivo existente)
3. ✅ Processa scans e gera mapa
4. ✅ Exporta em PGM/YAML
5. ✅ Valida arquivos gerados
6. ✅ Verifica compatibilidade com main.py

**Resultado**:
- Resumo completo dos testes
- Lista de arquivos gerados
- Próximos passos sugeridos

---

## 📊 Checklist de Validação

Antes de usar no `main.py`, verifique:

- [ ] **C1 detectado e validado**
  ```bash
  python3 src/main_c1_mapping.py detect --verbose
  ```

- [ ] **Scans coletados com sucesso**
  ```bash
  ls -lh mapas/c1/test/scans_*.json
  # Deve ter tamanho > 0 e conter scans
  ```

- [ ] **Mapa processado gerado**
  ```bash
  ls -lh mapas/c1/test/map_*.npy
  cat mapas/c1/test/map_*_metadata.json
  ```

- [ ] **Arquivos PGM/YAML exportados**
  ```bash
  ls -lh mapas/c1/test/*.{pgm,yaml}
  file mapas/c1/test/*.pgm
  cat mapas/c1/test/*.yaml
  ```

- [ ] **Arquivos podem ser carregados no main.py**
  - Teste manualmente carregando o PGM na interface

---

## 🔍 Testes Individuais

### Testar apenas detecção:
```bash
python3 src/main_c1_mapping.py detect --verbose
```

### Testar apenas coleta:
```bash
python3 src/main_c1_mapping.py collect --duration 10 --output mapas/c1/test
```

### Testar apenas processamento (com arquivo existente):
```bash
python3 src/main_c1_mapping.py process \
  --input mapas/c1/test/scans_*.json \
  --output mapas/c1/test
```

### Testar apenas exportação (com mapa existente):
```bash
python3 src/main_c1_mapping.py export \
  --map mapas/c1/test/map_*.npy \
  --output mapas/c1/test
```

### Testar apenas visualização:
```bash
python3 src/main_c1_mapping.py visualize \
  --map mapas/c1/test/map_*.npy \
  --output mapa_teste.png
```

---

## 🐛 Solução de Problemas

### Problema: C1 não detectado
**Solução**:
1. Verifique conexão USB
2. Verifique se LED verde está ligado
3. Execute diagnóstico: `python3 scripts/teste_c1_diagnostico.py`
4. Verifique drivers: `lsusb | grep -i "10c4\|CP210"`

### Problema: Nenhum scan coletado
**Solução**:
1. Verifique se C1 está respondendo: `python3 scripts/teste_protocolo_c1.py`
2. Verifique baudrate (deve ser 460800)
3. Tente coletar por mais tempo: `--duration 30`

### Problema: Mapa vazio ou muito pequeno
**Solução**:
1. Colete mais scans (aumente `--duration`)
2. Mova o C1 durante a coleta
3. Verifique se há obstáculos no ambiente

### Problema: Erro ao processar
**Solução**:
1. Verifique se arquivo JSON é válido: `python3 -m json.tool mapas/c1/test/scans_*.json`
2. Verifique se há scans no arquivo
3. Tente com resolução maior: `--resolution 0.10`

### Problema: Arquivos PGM/YAML inválidos
**Solução**:
1. Verifique se mapa foi processado corretamente
2. Verifique tamanho dos arquivos (não devem estar vazios)
3. Tente exportar novamente

---

## ✅ Pronto para main.py

Quando todos os testes passarem:

1. **Arquivos prontos**:
   - `mapas/c1/test/mapa_teste.pgm`
   - `mapas/c1/test/mapa_teste.yaml`

2. **No main.py**:
   - Use o botão "🗺️ Carregar PGM"
   - Selecione o arquivo `.pgm`
   - O `.yaml` será carregado automaticamente

3. **Adicionar POIs e áreas proibidas**:
   - Use a interface do `main.py`
   - Clique no mapa para adicionar POIs
   - Desenhe áreas proibidas

---

## 📝 Exemplo Completo

```bash
# 1. Detectar C1
python3 src/main_c1_mapping.py detect --verbose

# 2. Coletar scans (30 segundos)
python3 src/main_c1_mapping.py collect --duration 30 --output mapas/c1/test

# 3. Processar scans
python3 src/main_c1_mapping.py process \
  --input mapas/c1/test/scans_*.json \
  --output mapas/c1/test

# 4. Exportar mapa
python3 src/main_c1_mapping.py export \
  --map mapas/c1/test/map_*.npy \
  --output mapas/c1/test \
  --name meu_mapa

# 5. Visualizar (opcional)
python3 src/main_c1_mapping.py visualize \
  --map mapas/c1/test/map_*.npy \
  --output mapas/c1/test/visualizacao.png

# 6. Verificar arquivos
ls -lh mapas/c1/test/*.{pgm,yaml}
cat mapas/c1/test/meu_mapa.yaml

# 7. Testar no main.py
# Abra main.py e carregue o PGM gerado
```

---

**Data**: 28/11/2025  
**Versão**: 1.0

