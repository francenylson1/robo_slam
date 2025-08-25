# 🧮 CÁLCULO DE TPS SEGURO PARA VELOCIDADES

## 📊 **ANÁLISE ATUAL**

### **Relação TPS → Potência Motor:**
- **TPS Atual**: `MANUAL_CONTROL_MAX_TPS = 50`
- **Potência PID**: Até 90% (mas protocolo segurança exige ≤15%)
- **Conversão**: `tps = (velocidade_% / 100) * 50`

### **Protocolo de Segurança Estabelecido:**
- **LIMITE FÍSICO SEGURO**: 12-15% da potência total dos motores
- **PROBLEMA**: PID pode gerar até 90%, mas só é seguro até 15%

## 🔢 **CÁLCULO DE TPS SEGURO**

### **Premissas:**
1. **Potência PID máxima segura**: 15% 
2. **Ganhos PID atuais**: Kp=0.26, Ki=0.23, Kd=0.0
3. **Output limits PID**: (-90, 90) [ATUAL]

### **Estratégia de Segurança:**
- **Reduzir output_limits do PID** para (-15, 15) = MÁXIMO SEGURO
- **Recalcular TPS** para que PID funcione eficientemente dentro dos 15%
- **Criar níveis escalonados** respeitando sempre o limite

### **Níveis de Velocidade Propostos:**

#### **VELOCIDADE LENTA (Precision Mode)**
- **TPS Target**: 20 ticks/segundo
- **PID Output Range**: (-8, 8) = 8% potência máxima
- **Uso**: Aproximação final, áreas apertadas

#### **VELOCIDADE MÉDIA (Normal Mode)**  
- **TPS Target**: 35 ticks/segundo
- **PID Output Range**: (-12, 12) = 12% potência máxima
- **Uso**: Navegação normal, trajetos longos

#### **VELOCIDADE ALTA (Sport Mode)**
- **TPS Target**: 50 ticks/segundo  
- **PID Output Range**: (-15, 15) = 15% potência máxima
- **Uso**: Trajetos longos e retos, modo rápido

### **Ganhos PID Otimizados por Velocidade:**

#### **Para Velocidade LENTA (precisão máxima):**
```python
Kp=0.40, Ki=0.30, Kd=0.05, output_limits=(-8, 8)
```

#### **Para Velocidade MÉDIA (balanceado):**
```python  
Kp=0.35, Ki=0.25, Kd=0.03, output_limits=(-12, 12)
```

#### **Para Velocidade ALTA (resposta rápida):**
```python
Kp=0.30, Ki=0.20, Kd=0.01, output_limits=(-15, 15)  
```

## 🎯 **IMPLEMENTAÇÃO PROPOSTA**

### **1. Novas Constantes (config.py):**
```python
# Velocidades seguras escalonadas (TPS)
SPEED_SLOW_TPS = 20      # Lenta - 8% potência máxima
SPEED_NORMAL_TPS = 35    # Média - 12% potência máxima  
SPEED_FAST_TPS = 50      # Alta - 15% potência máxima

# Perfis PID por velocidade
PID_PROFILES = {
    'slow': {'Kp': 0.40, 'Ki': 0.30, 'Kd': 0.05, 'limits': (-8, 8)},
    'normal': {'Kp': 0.35, 'Ki': 0.25, 'Kd': 0.03, 'limits': (-12, 12)},
    'fast': {'Kp': 0.30, 'Ki': 0.20, 'Kd': 0.01, 'limits': (-15, 15)}
}
```

### **2. Sistema de Validação Automática:**
- Monitor em tempo real da potência PID
- Alarme se exceder 15% por mais de 100ms
- Auto-redução para modo seguro em caso de emergência

## ✅ **VANTAGENS DA ABORDAGEM:**

1. **Segurança Garantida**: Nunca excede 15% de potência
2. **Velocidades Escalonadas**: 3 níveis bem definidos
3. **PID Otimizado**: Ganhos ajustados para cada velocidade
4. **Retrocompatibilidade**: Mantém interfaces existentes
5. **Validação Automática**: Sistema de segurança ativo

---
**📝 Próximo passo**: Implementar as constantes e testar no ambiente de desenvolvimento.
