# VERSÃO BASE ESTÁVEL v1.0

## 📋 Status Atual

**Tag:** `v1.0-estavel-base`  
**Branch:** `v1.0-estavel-base-branch`  
**Commit:** `d3727e0`

## ✅ Funcionalidades Implementadas

### 1. Navegação em Linha Reta
- ✅ Robô navega em linha reta com correções automáticas
- ✅ PID funcionando corretamente
- ✅ Odometria real baseada em ticks dos encoders
- ✅ Potência mínima configurada (MIN_POWER_FLOOR = 6.0%)

### 2. Chegada ao Destino
- ✅ Robô para corretamente ao chegar no ponto de interesse
- ✅ Aproximação final estável
- ✅ Pausa configurada no destino

### 3. Retorno à Base
- ✅ Robô retorna à posição inicial
- ✅ Navegação de retorno funcionando
- ✅ Chegada à base com sucesso

### 4. Ajuste Final de Ângulo
- ✅ Robô ajusta para 270° (ROBOT_INITIAL_ANGLE)
- ✅ Velocidade adaptativa (0.8, 0.6, 0.4)
- ✅ Lógica de direção corrigida
- ✅ Finalização completa da navegação

## ⚠️ Limitações Conhecidas

### Giro de Retorno (~90° em vez de 180°)
- **Problema:** Robô gira aproximadamente 90° em vez de 180° para retornar
- **Impacto:** Funciona, mas não é o comportamento ideal
- **Status:** A ser corrigido em versões futuras

## 🔧 Configurações Atuais

```python
# Configurações de Potência
MIN_POWER_THRESHOLD = 4.0
MIN_POWER_FLOOR = 6.0

# Configurações de Velocidade
ROBOT_SPEED = 0.25 m/s
MAX_LINEAR_SPEED_MS = 0.25 m/s

# Configurações de PID
Kp = 0.11
Ki = 0.05
Kd = 0.0
output_limits = (-70, 70)

# Configurações de Ângulo
ROBOT_INITIAL_ANGLE = 270°
```

## 🎯 Como Usar Esta Versão

### Para Voltar a Esta Versão:
```bash
# Opção 1: Usar a tag
git checkout v1.0-estavel-base

# Opção 2: Usar a branch
git checkout v1.0-estavel-base-branch

# Opção 3: Reset para o commit específico
git reset --hard d3727e0
```

### Para Sincronizar na Raspberry Pi:
```bash
git fetch origin
git checkout v1.0-estavel-base
```

## 📝 Próximos Passos

1. **Corrigir giro de 180°** - Melhorar a precisão do giro de retorno
2. **Otimizar velocidade de giro** - Ajustar parâmetros baseado em testes físicos
3. **Melhorar precisão de chegada** - Refinar tolerâncias de chegada

## 🏷️ Histórico de Versões

- **v1.0-estavel-base** - Versão base funcional (atual)
  - Navegação completa funcionando
  - Giro de ~90° (limitação conhecida)
  - Ajuste final para 270° funcionando

---
**Data:** $(date)  
**Status:** ✅ ESTÁVEL - PRONTA PARA USO 