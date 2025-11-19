# 🚀 Início Rápido - Teste do Sistema Aurora → C1

## ⚡ Teste Rápido (5 minutos)

### ⚠️ Windows: Use `py` em vez de `python`!

### 1. Instale as dependências
```powershell
# Windows
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

# Linux/Mac
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### 2. Execute o teste básico
```powershell
# Windows
py tests/teste_aurora_pipeline.py

# Linux/Mac
python3 tests/teste_aurora_pipeline.py
```

### 3. Visualize o mapa gerado
```powershell
# Windows
py visualizar_mapa.py mapas/otimizados/teste_sala_maker.pgm

# Linux/Mac
python3 visualizar_mapa.py mapas/otimizados/teste_sala_maker.pgm
```

**Pronto!** Se funcionou, você tem o sistema básico funcionando. ✅

---

## 📖 Guia Completo

Para instruções detalhadas, consulte:
- **`docs/GUIA_TESTE_AURORA_C1.md`** - Guia completo passo a passo

## 🔧 Scripts Úteis

### Testar conexão com Aurora
```powershell
# Windows
py teste_aurora_connection.py --ip 192.168.1.100

# Linux/Mac
python3 teste_aurora_connection.py --ip 192.168.1.100
```

### Testar conexão com C1
```powershell
# Windows
py teste_c1_connection.py --ip 192.168.1.101

# Linux/Mac
python3 teste_c1_connection.py --ip 192.168.1.101
```

### Processar arquivo .stcm
```powershell
# Windows
py src/core/aurora_to_c1_pipeline.py --stcm mapas/originais_aurora/mapa.stcm --map-name meu_mapa

# Linux/Mac
python3 src/core/aurora_to_c1_pipeline.py --stcm mapas/originais_aurora/mapa.stcm --map-name meu_mapa
```

### Visualizar mapa
```powershell
# Windows
py visualizar_mapa.py mapas/otimizados/meu_mapa.pgm

# Linux/Mac
python3 visualizar_mapa.py mapas/otimizados/meu_mapa.pgm
```

---

## ⚠️ Problemas?

Consulte a seção **Troubleshooting** em `docs/GUIA_TESTE_AURORA_C1.md`

