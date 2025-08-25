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

### **Atualizar a interface para se adaptar a uma nova proposta de funcionamento da navegação:**
**Siga essas funções que o robô deve ter no seu funcionamento e na sua interface** 
1. Aproveitar a intercafe que já existe na qual podemos incluir e excluir pontos de interesse áreas proibidas;
2. mante a interface que já existe na qual podemos Gerenciar Mapas, Navegação, inclusive selecionar o Destino.
3. A nova funcionalidade é que o robô vai fazer a navegação APENAS até o destino e ficar lá parado aguardando novos comandos;
4. Lembrar que o robô ao navegar deve evitar áreas proibidas;
5. Crias botões para que o giro do robô (sobre o próprio eixo) para base ou para outros destinos sejam "manuais"(tipo left, right, up, down). O usuário vai fazer esse giro conforme o seu interesse. Apartir do momento que o usuário definir a nova posição de partida devemos criar um mecanismo para que o sistema registre essas coordenadas(O novo ponto de partida) para que o sistema possa fazer o cálculo do percurso conforme ele já faz MAS considerando o novo ponto de partida e não a posição base nesse caso;
6. Por enquanto eu penso que a cada parada ao chegar a um destino um novo ponto de partida deve ser registrado e a partir dele o sistema deve fazer novos cálculos conforme as novas coordenadas(novo destino e novo ponto de partida). Sempre desenhar os percursos calculados;
7. Verificar e ajustar se for o caso para o robô andar em linha reta e ir se corrigindo conforme a necessidade e o destino dele.
4. **Manter** a navegação em linha reta que está estável (não quebrar o que já funciona)
5. **NÃO ALTERAR MAIS NENHUMA FUNCIONALIDADE**

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