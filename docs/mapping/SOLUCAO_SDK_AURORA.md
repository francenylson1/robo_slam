# Solução: SDK do Aurora - Biblioteca C++ Não Encontrada

## 🔍 Problema Identificado

O SDK do Aurora requer a biblioteca C++ (`libslamtec_aurora_remote_sdk.so`) que está no submodule `cpp_sdk`, mas este submodule não foi baixado.

## ✅ Solução: Baixar o Submodule cpp_sdk

O SDK do Aurora usa um submodule Git para o código C++. Você precisa inicializar e baixar o submodule:

### Opção 1: Se py_aurora_remote-main é um repositório Git

```bash
cd py_aurora_remote-main

# Inicializar e baixar submodules
git submodule init
git submodule update

# Ou em um comando:
git submodule update --init --recursive
```

### Opção 2: Se py_aurora_remote-main NÃO é um repositório Git

Se você baixou o SDK como ZIP ou não tem acesso ao Git, você precisa:

1. **Baixar o cpp_sdk manualmente** do repositório oficial:
   - Repositório: https://github.com/Slamtec/py_aurora_remote
   - O submodule `cpp_sdk` deve estar em: `py_aurora_remote-main/cpp_sdk/`

2. **Ou baixar as bibliotecas pré-compiladas** (se disponíveis):
   - Verifique se há releases com bibliotecas pré-compiladas
   - Ou contate o suporte Slamtec

### Opção 3: Compilar o SDK

Se você tem acesso ao código-fonte C++, pode compilar:

```bash
cd py_aurora_remote-main

# Instalar dependências de build
pip install -r requirements-dev.txt

# Compilar para Linux x86_64
python tools/build_package.py --platforms linux_x86_64

# Instalar o wheel gerado
pip install wheels/slamtec_aurora_python_sdk_linux_x86_64-*.whl
```

## 🔍 Verificação

Após baixar o submodule, verifique se a biblioteca existe:

```bash
# Linux x86_64
ls -lh py_aurora_remote-main/cpp_sdk/aurora_remote_public/lib/linux_x86_64/libslamtec_aurora_remote_sdk.so

# Ou verificar todos os caminhos possíveis
find py_aurora_remote-main -name "*.so" -o -name "*.dll" -o -name "*.dylib"
```

## 📝 Estrutura Esperada

Após baixar o submodule, você deve ter:

```
py_aurora_remote-main/
├── cpp_sdk/
│   └── aurora_remote_public/
│       └── lib/
│           ├── linux_x86_64/
│           │   └── libslamtec_aurora_remote_sdk.so
│           ├── linux_aarch64/
│           │   └── libslamtec_aurora_remote_sdk.so
│           ├── win64/
│           │   └── slamtec_aurora_remote_sdk.dll
│           └── ...
└── python_bindings/
    └── ...
```

## 🚀 Após Resolver

Depois de ter a biblioteca disponível, execute o teste novamente:

```bash
python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input mapas/legacy/originais_aurora/sala-maker-1.stcm \
  --output data/pipeline_runs/teste_aurora_fisico \
  --steps capture,refinement
```

## 📚 Referências

- Repositório oficial: https://github.com/Slamtec/py_aurora_remote
- Documentação: `py_aurora_remote-main/README.md`
- Suporte Slamtec: Contate para obter bibliotecas pré-compiladas se necessário

