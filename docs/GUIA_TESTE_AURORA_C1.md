# 🧪 Guia Passo a Passo: Teste do Sistema Aurora → C1

Este guia fornece instruções detalhadas para testar o sistema de processamento de mapas do Aurora para o C1.

## 📋 Pré-requisitos

### Software Necessário
- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- Git (para clonar/atualizar o repositório)

### Hardware (Opcional para testes iniciais)
- Sensor Slamtec Aurora (conectado via cabo de rede)
- Sensor Slamtec C1 (conectado na mesma rede)
- Notebook/PC na mesma rede dos sensores

---

## 🔧 Passo 1: Instalação das Dependências

### 1.1. Navegue até a pasta do projeto

```bash
cd D:\robo_slam
```

### 1.2. Atualize o pip (recomendado)

```bash
python -m pip install --upgrade pip
```

### 1.3. Instale as dependências

```bash
pip install -r requirements.txt
```

**Dependências principais que serão instaladas:**
- `numpy` - Processamento numérico
- `open3d` - Processamento de nuvens de pontos 3D
- `Pillow` - Manipulação de imagens
- `PyYAML` - Leitura/escrita de arquivos YAML
- `requests` - Comunicação HTTP
- `scipy` - Operações científicas (morfologia)
- Outras dependências do projeto

### 1.4. Verifique a instalação

```bash
python -c "import open3d; import numpy; import yaml; import PIL; print('✅ Todas as dependências instaladas!')"
```

Se aparecer a mensagem de sucesso, continue. Se houver erro, verifique qual pacote falhou e instale manualmente.

---

## 🧪 Passo 2: Teste Básico (Sem Hardware)

Este teste cria uma nuvem de pontos simulada e gera um mapa 2D, sem precisar do hardware.

### 2.1. Execute o teste básico

```bash
python tests/teste_aurora_pipeline.py
```

### 2.2. O que deve acontecer

O script irá:
1. ✅ Criar uma nuvem de pontos 3D simulada (sala 6m x 12m)
2. ✅ Converter para mapa 2D (occupancy grid)
3. ✅ Aplicar processamento (morfologia, inflação)
4. ✅ Gerar arquivos PGM + YAML em `mapas/otimizados/`

### 2.3. Verifique os arquivos gerados

```bash
dir mapas\otimizados\teste_sala_maker.*
```

Você deve ver:
- `teste_sala_maker.pgm` - Imagem do mapa
- `teste_sala_maker.yaml` - Metadados do mapa

### 2.4. Visualize o mapa PGM (Opcional)

Você pode abrir o arquivo `.pgm` com:
- **Windows**: Paint, Visual Studio Code (com extensão de imagem)
- **Online**: Qualquer visualizador de imagens
- **Python**: Ver seção de visualização abaixo

**Resultado esperado:**
- Áreas brancas = espaço livre
- Áreas pretas = obstáculos/paredes
- Áreas cinzas = desconhecido

---

## 📁 Passo 3: Teste com Arquivo .stcm (Quando Disponível)

Quando você tiver um arquivo .stcm do Aurora, siga estes passos:

### 3.1. Coloque o arquivo .stcm na pasta correta

```bash
# Copie seu arquivo .stcm para:
mapas\originais_aurora\meu_mapa.stcm
```

### 3.2. Execute o pipeline

```bash
python src/core/aurora_to_c1_pipeline.py ^
    --stcm mapas/originais_aurora/meu_mapa.stcm ^
    --output-dir mapas/otimizados ^
    --map-name meu_mapa_processado ^
    --resolution 0.05
```

**Parâmetros explicados:**
- `--stcm`: Caminho para seu arquivo .stcm
- `--output-dir`: Onde salvar os arquivos gerados
- `--map-name`: Nome do mapa (sem extensão)
- `--resolution`: Resolução em metros (0.05 = 5cm)

### 3.3. Verifique os arquivos gerados

```bash
dir mapas\otimizados\meu_mapa_processado.*
```

### 3.4. Verifique o conteúdo do YAML

```bash
type mapas\otimizados\meu_mapa_processado.yaml
```

Deve conter algo como:
```yaml
image: meu_mapa_processado.pgm
resolution: 0.05
origin: [0.0, 0.0, 0.0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.196
```

---

## 🔌 Passo 4: Teste de Conexão com Aurora (Hardware Conectado)

### 4.1. Verifique a conexão de rede

1. Conecte o Aurora ao notebook via cabo de rede
2. Verifique o endereço IP do Aurora:
   - Acesse a interface web do Aurora (geralmente `http://192.168.1.100`)
   - Ou verifique nas configurações de rede do Windows

### 4.2. Teste a conectividade

```bash
ping 192.168.1.100
```

(Substitua pelo IP real do seu Aurora)

### 4.3. Teste a conexão Python

Crie um script de teste rápido:

```bash
python -c "from src.core.aurora_connector import test_connection; test_connection('192.168.1.100')"
```

(Substitua pelo IP real do seu Aurora)

### 4.4. Baixe um mapa do Aurora

```bash
python src/core/aurora_to_c1_pipeline.py ^
    --aurora-ip 192.168.1.100 ^
    --output-dir mapas/otimizados ^
    --map-name mapa_aurora_$(Get-Date -Format 'yyyyMMdd_HHmmss') ^
    --no-upload
```

**Nota:** O parâmetro `--no-upload` evita tentar fazer upload para o C1 nesta etapa.

---

## 📤 Passo 5: Teste de Upload para C1 (Hardware Conectado)

### 5.1. Verifique a conexão com o C1

```bash
ping 192.168.1.101
```

(Substitua pelo IP real do seu C1)

### 5.2. Teste a API do C1

Crie um script de teste:

```python
# teste_c1_connection.py
from src.core.slamware_c1_uploader import SlamwareC1Uploader
import logging

logging.basicConfig(level=logging.INFO)

uploader = SlamwareC1Uploader("192.168.1.101")  # Ajuste o IP
if uploader.check_connection():
    info = uploader.get_device_info()
    print(f"✅ C1 conectado: {info}")
    maps = uploader.list_maps()
    print(f"Mapas disponíveis: {maps}")
else:
    print("❌ Não foi possível conectar ao C1")
```

Execute:
```bash
python teste_c1_connection.py
```

### 5.3. Faça upload de um mapa

```bash
python src/core/aurora_to_c1_pipeline.py ^
    --stcm mapas/originais_aurora/meu_mapa.stcm ^
    --c1-ip 192.168.1.101 ^
    --map-name salao_principal
```

O sistema irá:
1. Processar o arquivo .stcm
2. Gerar PGM + YAML
3. Fazer upload para o C1
4. Definir como mapa ativo

---

## 🎨 Passo 6: Visualização do Mapa (Opcional)

### 6.1. Script de visualização Python

Crie um arquivo `visualizar_mapa.py`:

```python
import numpy as np
from PIL import Image
import yaml
import sys

def visualizar_mapa(pgm_path):
    """Visualiza mapa PGM gerado."""
    # Lê PGM
    img = Image.open(pgm_path)
    img_array = np.array(img)
    
    # Converte para visualização
    # 0 = ocupado (preto), 255 = livre (branco), 205 = desconhecido (cinza)
    print(f"Tamanho do mapa: {img_array.shape}")
    print(f"Valores únicos: {np.unique(img_array)}")
    
    # Mostra estatísticas
    ocupado = np.sum(img_array == 0)
    livre = np.sum(img_array == 255)
    desconhecido = np.sum(img_array == 205)
    total = img_array.size
    
    print(f"\nEstatísticas:")
    print(f"  Ocupado: {ocupado} ({ocupado/total*100:.1f}%)")
    print(f"  Livre: {livre} ({livre/total*100:.1f}%)")
    print(f"  Desconhecido: {desconhecido} ({desconhecido/total*100:.1f}%)")
    
    # Salva versão colorida para visualização
    color_img = Image.new('RGB', img.size)
    pixels = color_img.load()
    
    for i in range(img.size[0]):
        for j in range(img.size[1]):
            val = img_array[j, i]
            if val == 0:  # Ocupado - vermelho
                pixels[i, j] = (255, 0, 0)
            elif val == 255:  # Livre - branco
                pixels[i, j] = (255, 255, 255)
            else:  # Desconhecido - cinza
                pixels[i, j] = (128, 128, 128)
    
    output_path = pgm_path.replace('.pgm', '_colorido.png')
    color_img.save(output_path)
    print(f"\n✅ Mapa colorido salvo em: {output_path}")
    
    # Lê YAML
    yaml_path = pgm_path.replace('.pgm', '.yaml')
    with open(yaml_path, 'r') as f:
        metadata = yaml.safe_load(f)
    
    print(f"\nMetadados:")
    print(f"  Resolução: {metadata['resolution']} m/pixel")
    print(f"  Origem: {metadata['origin']}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        visualizar_mapa(sys.argv[1])
    else:
        print("Uso: python visualizar_mapa.py <caminho_para_mapa.pgm>")
```

### 6.2. Execute a visualização

```bash
python visualizar_mapa.py mapas/otimizados/teste_sala_maker.pgm
```

---

## 🔍 Passo 7: Verificação e Validação

### 7.1. Verifique a estrutura de pastas

```bash
tree /F mapas
```

Deve mostrar:
```
mapas/
├── originais_aurora/
├── otimizados/
│   ├── teste_sala_maker.pgm
│   └── teste_sala_maker.yaml
├── pois/
├── areas_proibidas/
└── templates/
```

### 7.2. Verifique os logs

Durante a execução, os logs mostram:
- ✅ Conexões estabelecidas
- ✅ Arquivos carregados
- ✅ Processamento concluído
- ✅ Arquivos gerados

### 7.3. Valide o formato dos arquivos

**PGM:**
- Deve abrir em visualizadores de imagem
- Tamanho razoável (não vazio, não gigante)

**YAML:**
- Formato válido YAML
- Campos obrigatórios presentes
- Valores numéricos válidos

---

## ⚠️ Troubleshooting

### Problema: Erro ao instalar dependências

**Solução:**
```bash
# Instale uma por uma para identificar o problema
pip install open3d
pip install Pillow
pip install PyYAML
pip install requests
```

### Problema: "ModuleNotFoundError"

**Solução:**
```bash
# Verifique se está na pasta correta
cd D:\robo_slam

# Reinstale as dependências
pip install -r requirements.txt
```

### Problema: Erro de conexão com Aurora

**Verificações:**
1. Aurora está ligado?
2. Cabo de rede conectado?
3. IP correto? (verifique na interface web do Aurora)
4. Firewall bloqueando conexão?

**Teste:**
```bash
ping <IP_DO_AURORA>
```

### Problema: Erro de conexão com C1

**Verificações:**
1. C1 está ligado?
2. Na mesma rede?
3. API SLAMWARE habilitada?
4. IP correto?

**Teste:**
```bash
# Tente acessar a interface web do C1
start http://<IP_DO_C1>
```

### Problema: Arquivo .stcm não é reconhecido

**Possíveis causas:**
- Formato do arquivo diferente do esperado
- Arquivo corrompido
- Versão do formato não suportada

**Solução:**
- Verifique se o arquivo é realmente .stcm do Aurora
- Tente com outro arquivo .stcm
- O parsing do .stcm precisa ser ajustado conforme formato real

### Problema: Mapa gerado está vazio ou incorreto

**Ajustes:**
1. Ajuste a resolução:
   ```bash
   --resolution 0.1  # Tente 10cm
   ```

2. Ajuste a faixa de altura (no código):
   ```python
   height_range=(0.0, 2.0)  # Ajuste conforme necessário
   ```

3. Verifique a nuvem de pontos original

---

## 📊 Checklist de Testes

Marque conforme for testando:

### Testes Básicos
- [ ] Dependências instaladas
- [ ] Teste básico executado com sucesso
- [ ] Arquivos PGM + YAML gerados
- [ ] Mapa visualizado corretamente

### Testes com Hardware
- [ ] Conexão com Aurora testada
- [ ] Arquivo .stcm processado
- [ ] Conexão com C1 testada
- [ ] Upload para C1 realizado
- [ ] Mapa ativo no C1

### Validação
- [ ] Mapa tem qualidade adequada
- [ ] Obstáculos estão corretos
- [ ] Áreas livres estão corretas
- [ ] Resolução adequada para navegação

---

## 📞 Próximos Passos

Após validar os testes básicos:

1. **Ajustar parâmetros** conforme seu ambiente
2. **Processar mapas reais** do Aurora
3. **Integrar com sistema de navegação** existente
4. **Otimizar processamento** para mapas grandes
5. **Adicionar POIs e áreas proibidas** aos mapas

---

## 📝 Notas Importantes

- ⚠️ O parsing do formato .stcm precisa ser validado com arquivos reais
- ⚠️ A API SLAMWARE do C1 pode ter endpoints diferentes - ajustar conforme documentação oficial
- ⚠️ IPs padrão (192.168.1.100/101) devem ser ajustados conforme sua rede
- ✅ Testes básicos funcionam sem hardware
- ✅ Estrutura está pronta para integração

---

**Última atualização:** 19/11/2025
**Versão:** 1.0

