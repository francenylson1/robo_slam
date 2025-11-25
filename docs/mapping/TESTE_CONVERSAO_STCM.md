# Guia de Teste - Conversão .stcm para .ply com SDK do Aurora

## 📋 Pré-requisitos

1. **Dispositivo Aurora** ligado e acessível na rede
2. **SDK do Aurora** disponível em `py_aurora_remote-main/python_bindings/`
3. **Arquivo .stcm** para teste (exemplo: `mapas/legacy/originais_aurora/sala-maker-1.stcm`)

## 🔧 Configuração Inicial

### 1. Habilitar o SDK do Aurora

Edite `config/mapping.json` e configure a seção `aurora`:

```json
{
  "aurora": {
    "enabled": true,
    "ip": "192.168.11.1",  // Ajuste para o IP do seu dispositivo
    "port": 1445,
    "auto_discover": true,  // true = descobre automaticamente, false = usa IP fixo
    "sdk_path": null
  }
}
```

**Importante:**
- Se `auto_discover: true`, o sistema tentará descobrir o dispositivo automaticamente
- Se `auto_discover: false`, use o IP correto do seu dispositivo Aurora
- O IP padrão no arquivo é `192.168.11.1` - ajuste se necessário

### 2. Verificar Conexão com o Dispositivo

Teste se o dispositivo está acessível:

```bash
# Linux/Mac
ping 192.168.11.1

# Ou teste a porta
telnet 192.168.11.1 1445
```

## 🧪 Testes

### Teste 1: Conversão de Arquivo .stcm Local (Upload)

Este teste converte um arquivo `.stcm` que está no seu computador.

**Passo 1:** Certifique-se de que o arquivo `.stcm` existe:
```bash
ls -lh mapas/legacy/originais_aurora/sala-maker-1.stcm
```

**Passo 2:** Execute o pipeline apenas com as etapas `capture` e `refinement`:
```bash
python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora/sala-maker-1.stcm \
  --output data/pipeline_runs/teste_stcm_sdk \
  --steps capture,refinement
```

**O que deve acontecer:**
1. ✅ Conecta ao dispositivo Aurora
2. ✅ Detecta que o arquivo `.stcm` está local
3. ✅ Faz upload do arquivo para o dispositivo
4. ✅ Extrai os map points (nuvem de pontos)
5. ✅ Salva como `.ply` em `data/pipeline_runs/teste_stcm_sdk/refinement/`

**Verificar resultado:**
```bash
ls -lh data/pipeline_runs/teste_stcm_sdk/refinement/*.ply
```

### Teste 2: Conversão de Mapa Ativo no Dispositivo (Sem Upload)

Este teste obtém dados diretamente do mapa ativo no dispositivo Aurora.

**Passo 1:** Certifique-se de que há um mapa ativo no dispositivo Aurora

**Passo 2:** Execute o pipeline (sem arquivo .stcm local):
```bash
# Crie um diretório vazio ou com apenas um arquivo dummy
mkdir -p data/pipeline_runs/teste_mapa_ativo/capture
touch data/pipeline_runs/teste_mapa_ativo/capture/dummy.txt

python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input data/pipeline_runs/teste_mapa_ativo/capture \
  --output data/pipeline_runs/teste_mapa_ativo \
  --steps refinement
```

**O que deve acontecer:**
1. ✅ Conecta ao dispositivo Aurora
2. ✅ Detecta que não há arquivo `.stcm` local
3. ✅ Obtém dados diretamente do mapa ativo no dispositivo
4. ✅ Salva como `.ply`

### Teste 3: Via Interface Gráfica (GUI)

**Passo 1:** Abra a GUI:
```bash
python src/main_mapping.py --gui
```

**Passo 2:** Configure:
- Pipeline: `Aurora → C1`
- Input: `mapas/legacy/originais_aurora/sala-maker-1.stcm`
- Output: `data/pipeline_runs/teste_gui`
- Steps: Selecione apenas `capture` e `refinement`

**Passo 3:** Execute e observe os logs na interface

## 🔍 Verificação dos Resultados

### 1. Verificar Arquivo .ply Gerado

```bash
# Listar arquivos gerados
ls -lh data/pipeline_runs/teste_stcm_sdk/refinement/

# Verificar tamanho do arquivo (deve ser > 0)
du -h data/pipeline_runs/teste_stcm_sdk/refinement/*.ply
```

### 2. Visualizar o Arquivo .ply (Opcional)

Se tiver o Open3D instalado, pode visualizar:
```python
import open3d as o3d
cloud = o3d.io.read_point_cloud("data/pipeline_runs/teste_stcm_sdk/refinement/sala-maker-1_clean.ply")
print(f"Pontos: {len(cloud.points)}")
o3d.visualization.draw_geometries([cloud])
```

### 3. Verificar Logs

Os logs devem mostrar:
- `✅ Conectado ao Aurora`
- `Arquivo .stcm encontrado localmente` (se aplicável)
- `Fazendo upload do arquivo .stcm para o dispositivo...` (se aplicável)
- `✅ Upload concluído` (se aplicável)
- `Extraindo nuvem de pontos...`
- `X pontos encontrados`
- `✅ Arquivo .ply salvo`

## ❌ Troubleshooting

### Erro: "SDK do Aurora não encontrado"

**Solução:**
```bash
# Verifique se o SDK existe
ls -la py_aurora_remote-main/python_bindings/slamtec_aurora_sdk/
```

### Erro: "Nenhum dispositivo Aurora encontrado"

**Soluções:**
1. Verifique se o dispositivo está ligado
2. Verifique a conexão de rede
3. Teste com `auto_discover: false` e IP específico
4. Verifique firewall/antivírus

### Erro: "Upload falhou"

**Soluções:**
1. Verifique se o arquivo `.stcm` é válido
2. Verifique espaço no dispositivo
3. Tente novamente após alguns segundos
4. Verifique logs do dispositivo Aurora

### Erro: "Nenhum map point encontrado"

**Soluções:**
1. Verifique se o mapa foi gerado corretamente no Aurora
2. Aguarde mais tempo para sincronização
3. Verifique se o mapa está ativo no dispositivo

### Erro: "ConnectionError"

**Soluções:**
1. Verifique IP e porta na configuração
2. Teste conectividade: `ping <IP_DO_AURORA>`
3. Verifique se o dispositivo está na mesma rede
4. Verifique se a porta 1445 está aberta

## 📊 Teste Rápido (Script)

Use o script de teste rápido:

```bash
# Linux/Mac
bash scripts/teste_conversao_stcm.sh

# Windows
scripts\teste_conversao_stcm.bat
```

## 🎯 Checklist de Teste

- [ ] Dispositivo Aurora ligado e acessível
- [ ] Configuração `aurora.enabled: true` em `config/mapping.json`
- [ ] IP correto configurado (ou `auto_discover: true`)
- [ ] Arquivo `.stcm` disponível para teste
- [ ] Pipeline executado com sucesso
- [ ] Arquivo `.ply` gerado e com tamanho > 0
- [ ] Logs mostram sucesso em todas as etapas

## 📝 Notas

- O processo de upload pode levar alguns segundos dependendo do tamanho do arquivo
- A sincronização dos dados do mapa também pode levar alguns segundos
- Se o SDK falhar, o sistema tentará usar o parser heurístico como fallback
- Para mapas grandes, o processo pode demorar mais

