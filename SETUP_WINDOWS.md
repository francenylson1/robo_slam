# 🪟 Configuração no Windows - Guia Rápido

## ⚠️ Importante: Comando Python no Windows

No Windows, use **`py`** em vez de **`python`** devido aos aliases do Microsoft Store.

## ✅ Verificação Rápida

Execute para verificar se o Python está instalado:

```powershell
py --version
```

Se mostrar uma versão (ex: `Python 3.11.9`), está tudo certo! ✅

---

## 🚀 Instalação Rápida

### 1. Atualize o pip

```powershell
py -m pip install --upgrade pip
```

### 2. Instale as dependências

```powershell
py -m pip install -r requirements.txt
```

### 3. Execute o teste básico

```powershell
py tests/teste_aurora_pipeline.py
```

### 4. Visualize o mapa gerado

```powershell
py visualizar_mapa.py mapas/otimizados/teste_sala_maker.pgm
```

---

## 📝 Comandos Corrigidos para Windows

Substitua todos os comandos `python` por `py`:

| Comando Original | Comando Windows |
|-----------------|-----------------|
| `python script.py` | `py script.py` |
| `python -m pip install` | `py -m pip install` |
| `python -c "..."` | `py -c "..."` |

---

## 🔧 Scripts de Teste (Windows)

### Teste básico
```powershell
py tests/teste_aurora_pipeline.py
```

### Testar conexão Aurora
```powershell
py teste_aurora_connection.py --ip 192.168.1.100
```

### Testar conexão C1
```powershell
py teste_c1_connection.py --ip 192.168.1.101
```

### Processar arquivo .stcm
```powershell
py src/core/aurora_to_c1_pipeline.py --stcm mapas/originais_aurora/mapa.stcm --map-name meu_mapa
```

### Visualizar mapa
```powershell
py visualizar_mapa.py mapas/otimizados/meu_mapa.pgm
```

---

## ⚙️ Se `py` também não funcionar

### Opção 1: Desabilitar alias do Microsoft Store

1. Abra **Configurações** do Windows
2. Vá em **Aplicativos** → **Configurações avançadas do aplicativo**
3. Desative **Aliases de execução do aplicativo**
4. Reinicie o PowerShell

### Opção 2: Usar caminho completo

Encontre onde o Python está instalado:

```powershell
where py
```

Depois use o caminho completo, por exemplo:
```powershell
C:\Python311\python.exe -m pip install -r requirements.txt
```

### Opção 3: Adicionar Python ao PATH

1. Encontre a pasta de instalação do Python (geralmente `C:\Python311\` ou `C:\Users\SeuUsuario\AppData\Local\Programs\Python\`)
2. Adicione ao PATH do Windows:
   - Configurações → Sistema → Variáveis de Ambiente
   - Edite a variável PATH
   - Adicione a pasta do Python e a pasta `Scripts`

---

## ✅ Verificação Final

Execute este comando para verificar se tudo está funcionando:

```powershell
py -c "import numpy, open3d, yaml, PIL; print('✅ Todas as dependências OK!')"
```

Se aparecer a mensagem de sucesso, está tudo pronto! 🎉

---

**Nota:** Todos os guias foram atualizados para usar `py` em vez de `python` quando executados no Windows.

