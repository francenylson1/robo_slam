# PROMPT PARA NOVO CHAT - Robô SLAM

## 🎯 **CONTEXTO DO PROJETO**

Se comporte como um especialista em Python, Raspberry, tecnologia slam,odometris, sensores Lidar, Robótica. Você está trabalhando em um **robô garçom autônomo** com navegação SLAM. O projeto está em uma fase avançada onde a navegação básica já funciona, mas há um problema específico de sincronização entre a interface gráfica e o robô físico. Temos ajustes no funcionamento da interface.

## 📋 **O QUE O PROJETO FAZ**

**Objetivo:** Robô que navega autonomamente para pontos de interesse, retorna à base e se reposiciona em 270 graus(seta para cima).  
**Tecnologia:** Raspberry Pi + Python + PyQt5 + PID Control + Odometria + SLAM  
**Funcionalidade:** Interface gráfica permite selecionar pontos no mapa, robô navega até o ponto e retorna à base

## ✅ **O QUE JÁ ESTÁ FUNCIONANDO**

### **Navegação Completa Funcionando:**
1. **OK** Navegação em linha reta** - Robô vai ao destino se corrigindo para se manter reto em direção ao ponto de interesse
2. **OK** Chegada ao destino** - Pára corretamente no ponto selecionado
3. **AJUSTES** Faz um giro de 165 graus +- . o esperado seria 180 graus para retornar a base ou o giro necessário para retornar a base(nem sempre seria 180 graus)
4. **AJUSTES** Retorno à base** - Não volta com precisão à posição inicial se perde um pouco. Penso que seja em decorrência de não fazer o giro de 180 graus completo. Está fazendo 165+- graus.
5. **Ajuste final** - Ajusta para posição inicial (270°)
6. **OK** A interface funciona bem com relação a criar e excluir pontos de interesse ou áreas proibidas
7. **AJUSTES NA INTERFACE** Ao executar a main.py a interface funciona bem. Ao selecionar um ponto de interesse e iniciar uma navegação o funcionamento está OK. MAS após concluir a primeira navegação e iniciar uma segunda navegação a interface se desconfigura, cria um percurso aleatório e o robô da interface não se posiciona na posição inicial de ROBOT_INITIAL_POSITION = (5.7, 11.5) # (x, y) e ROBOT_INITIAL_ANGLE = 270. Para voltar a funcionar corretamente temos que fechar toda aplicação. E fazer uma nova execução do main.py para voltar a funcionar. Ou seja, precisamos corrigir para que a interface que ao concluir uma navegação o sistema seja 1) resetado e zerado; 2) o robô volte para posição inicial de ROBOT_INITIAL_POSITION = (5.7, 11.5) # (x, y) e ROBOT_INITIAL_ANGLE = 270; 3) o percurso anterior criado em linha azul seja apagado; 4) deixar o sistema disponível para nova navegação.

### **Configurações Estáveis (NÃO ALTERAR):**
```python
MIN_POWER_THRESHOLD = 4.0
MIN_POWER_FLOOR = 7.0
```
**IMPORTANTE:** Esses valores garantem navegação estável. NÃO altere sem testar cuidadosamente.

## ⚠️ **PROBLEMA ESPECÍFICO A SER CORRIGIDO**

### **Sincronização de Direção (1a. PRIORIDADE ALTA)**
- **Problema:** Ajustes na interface para iniciar uma navegação concluir, resetar para posição iniciar, limpar os dados e deixar o sistema disponivel para nova navegação
- **Impacto:** Atualmente temos que iniciar o main.py configurar uma navegação e ao concluir a navegação temos que fechar a aplicação e abrir novamente a aplicação para uma segunda aplicação pois o sitema fica com um comportamento confuso e inconsistente NA SEGUNDA NAVEGAÇÃO.
- **Status:** A PRIORIDADE PARA SER CORRIGIDA

### **Sincronização de Direção (2a. PRIORIDADE ALTA)**
- **Problema:** Interface mostra giro para **direita**, robô físico gira para **esquerda** ou vice-versa
- **Impacto:** Comportamento confuso e inconsistente
- **Status:** A PRIORIDADE PARA SER CORRIGIDA

### **Limitações Menores (A SEREM OTIMIZADAS DEPOIS):**
- Giro de ~170° em vez de 180°
- Ajuste final para ~260° em vez de 270°

## 🔧 **ARQUIVOS PRINCIPAIS**

### **Arquivos a serem modificados:**
- `src/core/robot_navigator.py` - Método `_move_towards_target()`
- `src/core/robot_motor_controller.py` - Lógica de direção dos motores
- ou qualquer outro arquivo do projeto

### **Arquivos de referência:**
- `src/core/config.py` - Configurações globais
- `gpio_test.py` - Teste direto dos motores (funciona corretamente)

## 🏷️ **VERSÕES DISPONÍVEIS**

### **v1.2-estavel-referencia-protegida** (cefdefb) - **VERSÃO ATUAL ESTÁVEL**
- Navegação completa funcionando
- Giro de ~170° (funciona, mas não é 180°)
- Ajuste final para ~260° (funciona, mas não é 270°)

## 🎯 **1a. TAREFA ESPECÍFICA**

### **Corrigir a interface para resetar a interface após uma navegação:**
1. **Identificar** porque está ficando desconfigurada a segunda navegação
2. **Corrigir** fazer um reset total na interface após a conclusão de uma navegação: reposicionar o robô na posição inicial de ROBOT_INITIAL_POSITION = (5.7, 11.5) # (x, y) e ROBOT_INITIAL_ANGLE = 270 e apagar o percurso anterior que foi criado em linha azul
3. **Testar** para garantir que interface está resetando os parâmetros e disponibilizando o sistema para uma nova navegação
4. **Manter** a navegação estável (não quebrar o que já funciona)
5. **MANTER AS DEMAIS FUNÇÕES** Focar apenas na interface que possibilite iniciar as navegações com o sistema limpo e livre das informações da navegação anterior
6. **NÃO ALTERAR MAIS NENHUMA FUNCIONALIDADE**


## 🎯 **2a. TAREFA ESPECÍFICA**

### **Corrigir a Sincronização de Direção:**
1. **Identificar** onde está a inversão de direção
2. **Corrigir** a cinemática diferencial ou lógica de direção
3. **Testar** para garantir que interface e robô físico giram na mesma direção
4. **Manter** a navegação estável (não quebrar o que já funciona)
5. **MANTER AS DEMAIS FUNÇÕES** Focar apenas na sincronização e fazer com que o robô da interface faça faça um giro para mesma direção que o robô físico/real. **NÃO ALTERAR MAIS NENHUMA FUNCIONALIDADE**

### **O que precisa ser corrigido:**
- **Cinemática diferencial** - Fórmulas de conversão de velocidades
- **Lógica de direção** - Comandos de giro
- **Sincronização interface/robô** - Alinhar simulação com realidade

## 🚀 **COMO TESTAR**

### **Comandos na Raspberry Pi:**
```bash
# Sincronizar com versão estável
git fetch origin
git reset --hard origin/fix/corrigir-inversao-giro

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


## 🎯 **OBJETIVO FINAL**

**Interface que se reseta das informações da navegação concluída e limpa o sistema para nova navegação**

**Interface e robô físico devem girar na mesma direção:**
- Interface mostra giro para direita → Robô físico gira para direita
- Interface mostra giro para esquerda → Robô físico gira para esquerda

---

**Status:** ✅ Navegação estável, foco na sincronização de direção  
**Próximo passo** Interface que permite fazer navegações novas após a conclusão de uma navegação
**Próximo passo:** Corrigir inversão entre interface e robô físico 