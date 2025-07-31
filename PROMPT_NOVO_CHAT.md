# PROMPT PARA NOVO CHAT - Robô SLAM

## 🎯 **CONTEXTO DO PROJETO**

Você está trabalhando em um **robô garçom autônomo** com navegação SLAM. O projeto está em uma fase avançada onde a navegação básica já funciona, mas há um problema específico de sincronização entre a interface gráfica e o robô físico.

## 📋 **O QUE O PROJETO FAZ**

**Objetivo:** Robô que navega autonomamente para pontos de interesse e retorna à base  
**Tecnologia:** Raspberry Pi + Python + PyQt5 + PID Control + Odometria  
**Funcionalidade:** Interface gráfica permite selecionar pontos no mapa, robô navega até o ponto e retorna à base

## ✅ **O QUE JÁ ESTÁ FUNCIONANDO**

### **Navegação Completa Funcionando:**
1. **Navegação em linha reta** - Robô vai ao destino sem se perder
2. **Chegada ao destino** - Para corretamente no ponto selecionado
3. **Retorno à base** - Volta à posição inicial
4. **Ajuste final** - Ajusta para posição inicial (270°)

### **Configurações Estáveis (NÃO ALTERAR):**
```python
MIN_POWER_THRESHOLD = 4.0
MIN_POWER_FLOOR = 7.0
```
**IMPORTANTE:** Esses valores garantem navegação estável. NÃO altere sem testar cuidadosamente.

## ⚠️ **PROBLEMA ESPECÍFICO A SER CORRIGIDO**

### **Sincronização de Direção (PRIORIDADE ALTA)**
- **Problema:** Interface mostra giro para **direita**, robô físico gira para **esquerda**
- **Impacto:** Comportamento confuso e inconsistente
- **Status:** A ser corrigido AGORA

### **Limitações Menores (A SEREM OTIMIZADAS DEPOIS):**
- Giro de ~170° em vez de 180°
- Ajuste final para ~260° em vez de 270°

## 🔧 **ARQUIVOS PRINCIPAIS**

### **Arquivos a serem modificados:**
- `src/core/robot_navigator.py` - Método `_move_towards_target()`
- `src/core/robot_motor_controller.py` - Lógica de direção dos motores

### **Arquivos de referência:**
- `src/core/config.py` - Configurações globais
- `gpio_test.py` - Teste direto dos motores (funciona corretamente)

## 🏷️ **VERSÕES DISPONÍVEIS**

### **v1.1-giro-170-graus** (f6dcd96) - **VERSÃO ATUAL ESTÁVEL**
- Navegação completa funcionando
- Giro de ~170° (funciona, mas não é 180°)
- Ajuste final para ~260° (funciona, mas não é 270°)

## 🎯 **TAREFA ESPECÍFICA**

### **Corrigir a Sincronização de Direção:**
1. **Identificar** onde está a inversão de direção
2. **Corrigir** a cinemática diferencial ou lógica de direção
3. **Testar** para garantir que interface e robô físico giram na mesma direção
4. **Manter** a navegação estável (não quebrar o que já funciona)

### **O que precisa ser corrigido:**
- **Cinemática diferencial** - Fórmulas de conversão de velocidades
- **Lógica de direção** - Comandos de giro
- **Sincronização interface/robô** - Alinhar simulação com realidade

## 🚀 **COMO TESTAR**

### **Comandos na Raspberry Pi:**
```bash
# Sincronizar com versão estável
git checkout v1.1-giro-170-graus

# Executar o robô
python3 src/main.py
```

### **Teste de Sincronização:**
1. Execute o robô
2. Selecione um ponto no mapa
3. Observe se a direção do giro na interface corresponde ao robô físico
4. Se não corresponder, há inversão a ser corrigida

## 📝 **REGRAS IMPORTANTES**

1. **NÃO altere** `MIN_POWER_THRESHOLD = 4.0` e `MIN_POWER_FLOOR = 7.0`
2. **Sempre teste** antes de commitar
3. **Crie backup** antes de modificações grandes
4. **Mantenha** a navegação estável (não quebre o que funciona)
5. **Foque** apenas na sincronização de direção por enquanto

## 🔍 **DICAS TÉCNICAS**

- O problema está na **cinemática diferencial** ou **lógica de direção dos motores**
- Compare com `gpio_test.py` que funciona corretamente
- A interface usa PyQt5 e mostra o robô girando
- O robô físico usa GPIO para controlar os motores
- A inversão pode estar nas fórmulas de conversão de velocidades

## 🎯 **OBJETIVO FINAL**

**Interface e robô físico devem girar na mesma direção:**
- Interface mostra giro para direita → Robô físico gira para direita
- Interface mostra giro para esquerda → Robô físico gira para esquerda

---

**Status:** ✅ Navegação estável, foco na sincronização de direção  
**Próximo passo:** Corrigir inversão entre interface e robô físico 