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

### **Sincronização robô da interface e robô físico / real:**
1. Problema principal : O robô da interface gira para esquerda e o robô físico gira para direita ou seja estão invertidos;
2. Desenvolver um script utilizando toda lógica já existente MAS que utilize apenas o robô físico para que possamos isolar o problema(inicialmente sem interface). Esse script vai dar prints esquerda quando der o comando físico para esquerda e direita quando der os comandos físicos para direita. Vou testar, observar e retornar as informações dos logs paravc. Apartir dessas informações vamos partir para interface junta com o robô físico.
3. Observe se a direção do giro na interface corresponde ao robô físico
4. Não podemos comprometer o que já funciona. O robô navega em linha reta muito bem e se corrige para continua em linha reta. isso não podemos quebrar.

## 🚀 **COMO TESTAR**

### **Comandos na Raspberry Pi:**
```bash
# Sincronizar com versão estável
git fetch origin
git reset --hard origin/fix/corrigir-inversao-giro

# Executar o robô
python3 src/main.py
```



## 📝 **REGRAS IMPORTANTES**

1. **NÃO altere** `MIN_POWER_THRESHOLD = 4.0` e `MIN_POWER_FLOOR = 7.0`
2. **Sempre teste** antes de commitar
3. **Crie backup** antes de modificações grandes
4. **Mantenha** a navegação estável (não quebre o que funciona)


## 🎯 **OBJETIVO FINAL**