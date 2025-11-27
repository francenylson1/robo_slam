# 🧪 Como Testar o C1 Mapping - Guia Rápido

## 🚀 Teste Rápido (Recomendado)

Execute o script de teste automatizado que faz tudo:

```bash
# Teste completo (coleta 10 segundos)
python3 scripts/teste_pipeline_completo.py --duration 10
```

Este script:
1. ✅ Detecta o C1
2. ✅ Coleta scans
3. ✅ Processa e gera mapa
4. ✅ Exporta PGM/YAML
5. ✅ Valida tudo

---

## 📋 Teste Passo a Passo

### 1️⃣ Detectar C1
```bash
python3 src/main_c1_mapping.py detect --verbose
```
**Esperado**: ✅ C1 detectado via Serial

### 2️⃣ Coletar Scans
```bash
python3 src/main_c1_mapping.py collect --duration 10 --output mapas/c1/test
```
**Esperado**: ✅ Scans coletados, arquivo `scans_*.json` gerado

### 3️⃣ Processar Scans
```bash
python3 src/main_c1_mapping.py process \
  --input mapas/c1/test/scans_*.json \
  --output mapas/c1/test
```
**Esperado**: ✅ Mapa gerado, arquivo `map_*.npy` criado

### 4️⃣ Exportar Mapa
```bash
python3 src/main_c1_mapping.py export \
  --map mapas/c1/test/map_*.npy \
  --output mapas/c1/test \
  --name mapa_teste
```
**Esperado**: ✅ Arquivos `mapa_teste.pgm` e `mapa_teste.yaml` criados

### 5️⃣ Verificar Arquivos
```bash
# Verifica se arquivos foram criados
ls -lh mapas/c1/test/*.{pgm,yaml}

# Verifica conteúdo do YAML
cat mapas/c1/test/mapa_teste.yaml
```

---

## ✅ Checklist Antes de Usar no main.py

- [ ] C1 detectado e validado
- [ ] Scans coletados (arquivo JSON existe)
- [ ] Mapa processado (arquivo .npy existe)
- [ ] PGM/YAML exportados (arquivos existem e têm tamanho > 0)
- [ ] YAML contém campos: `image`, `resolution`, `origin`

---

## 🎯 Teste Rápido com Arquivo Existente

Se você já tem scans coletados:

```bash
# Pula coleta e usa arquivo existente
python3 scripts/teste_pipeline_completo.py \
  --skip-collection \
  --scan-file mapas/c1/test/scans_*.json
```

---

## 📖 Documentação Completa

Para mais detalhes, consulte:
- `docs/TESTE_PIPELINE_C1.md` - Guia completo de testes

---

## 💡 Próximo Passo

Quando todos os testes passarem:
1. Use os arquivos PGM/YAML gerados no `main.py`
2. Carregue o mapa na interface
3. Adicione POIs e áreas proibidas

