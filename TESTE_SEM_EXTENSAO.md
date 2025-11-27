# 🔌 Teste Sem Extensão USB

## ⚠️ Problema Identificado

Extensões USB podem causar problemas de comunicação com o C1, especialmente em altas velocidades (460800 baud).

## ✅ Solução

**Conecte o C1 diretamente ao computador** (sem extensão USB) e teste novamente.

---

## 🧪 Teste Rápido

### 1. Verificar Detecção

```bash
python3 src/main_c1_mapping.py detect --verbose
```

**Esperado**: ✅ C1 detectado e validado

### 2. Teste de Coleta Curta (10 segundos)

```bash
python3 src/main_c1_mapping.py collect \
  --duration 10 \
  --output mapas/c1/test \
  --full-scans
```

**Verifique**:
- ✅ Scans coletados: deve ter vários scans (não apenas 1)
- ✅ Pontos por scan: deve ter centenas de pontos

### 3. Se Funcionar, Gere Mapa Completo

```bash
# Coleta por 60-120 segundos
python3 src/main_c1_mapping.py collect \
  --duration 60 \
  --output mapas/c1/completo/raw \
  --full-scans
```

---

## 🔍 Verificar Qualidade da Conexão

Após conectar diretamente, verifique:

```bash
# Verifica porta serial
ls -l /dev/ttyUSB*

# Verifica permissões
groups | grep dialout

# Se necessário, adicione seu usuário ao grupo dialout
sudo usermod -a -G dialout $USER
# Depois faça logout e login novamente
```

---

## 📊 Comparação

| Com Extensão USB | Sem Extensão USB |
|------------------|------------------|
| ❌ Poucos scans | ✅ Muitos scans |
| ❌ Poucos pontos | ✅ Centenas de pontos |
| ❌ Dados incompletos | ✅ Dados completos |

---

## 💡 Dicas

1. **Use cabo USB curto** (máximo 1-2 metros)
2. **Evite hubs USB** intermediários
3. **Use porta USB 2.0 ou 3.0** diretamente na placa-mãe
4. **Verifique alimentação** - alguns cabos USB não fornecem energia suficiente

---

**Teste sem a extensão e me avise os resultados!**

