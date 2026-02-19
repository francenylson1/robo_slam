# Contexto do Projeto: Desvio de Áreas Proibidas

## 📋 Estado Atual do Projeto

**Branch:** `robo-slam-v.3.1-aurora_bmp-c1_pgm`  
**Último Commit:** `6d61415` - "robo-slam-v.3.1-aurora_bmp-c1_pgm - navegando ate o POI sem obstaculos corretamente e em linha reta"  
**Data:** Dezembro 2025

---

## ✅ O Que Foi Realizado

### 1. Navegação Básica Funcionando
- ✅ Robô navega corretamente até POIs selecionados
- ✅ Navegação em linha reta funcionando perfeitamente
- ✅ Robô retorna à posição base inicial após chegar ao POI
- ✅ Aguarda 2 segundos no POI antes de retornar
- ✅ Precisão de chegada ao POI: ~3cm (muito boa)
- ✅ Mensagem "Navegação Concluída" exibida ao final de cada navegação
- ✅ Sistema interativo e intuitivo para o usuário

### 2. Integração com Mapas PGM
- ✅ Carregamento de mapas PGM gerados pelo Aurora
- ✅ Processamento correto de coordenadas (sem inversões)
- ✅ PathFinder configurado para trabalhar com mapas PGM
- ✅ Sistema de coordenadas unificado (world meters)

### 3. Estrutura de Áreas Proibidas (Parcialmente Implementada)
- ✅ Interface para adicionar/editar áreas proibidas no mapa
- ✅ Exportação/importação de áreas proibidas em JSON
- ✅ PathFinder possui método `set_forbidden_areas()` implementado
- ✅ PathFinder possui método `_update_obstacle_grid()` que marca células proibidas
- ✅ Algoritmo A* implementado no PathFinder
- ✅ Verificação de interseção de linhas com áreas proibidas (`_line_intersects_obstacles`)

### 4. Correções e Melhorias Recentes
- ✅ Correção do loop infinito na finalização da navegação
- ✅ Sincronização correta entre `navigation_active` (interface) e `navigator.navigation_active`
- ✅ Correção da função `get_navigation_status()` para retornar estado COMPLETED corretamente
- ✅ Timeout de 10 segundos no ajuste de ângulo final para evitar loops infinitos
- ✅ Logs detalhados para debug

---

## ❌ O Que NÃO Está Funcionando

### 🚫 Desvio de Áreas Proibidas (CRÍTICO - PRÓXIMO PASSO)

**Status:** Implementação parcial - **NÃO FUNCIONA**

**O que existe:**
- PathFinder tem estrutura para áreas proibidas
- Método `find_path()` existe e usa A*
- Verificação de interseção de caminhos com áreas proibidas existe
- Lógica em `robot_navigator.py` tenta usar PathFinder quando há áreas proibidas

**O que NÃO funciona:**
- ❌ O A* não encontra caminhos válidos (retorna `None`)
- ❌ Quando o A* falha, o sistema aborta a navegação em vez de usar caminho direto
- ❌ O `obstacle_grid` pode não estar sendo atualizado corretamente
- ❌ A navegação não desvia das áreas proibidas na prática

**Arquivos Relevantes:**
- `src/core/path_finder.py` - Implementação do A* e gerenciamento de obstáculos
- `src/core/robot_navigator.py` - Lógica de navegação que chama o PathFinder
- `src/core/config.py` - `FORBIDDEN_AREA_INFLATION_RADIUS = 0.40` (40cm de margem)

**Problemas Identificados nos Logs:**
```
DEBUG: Nenhum caminho encontrado pelo A*
🚨 ERRO: A* não encontrou caminho de (14, 50) para (26, 37)
```

**O que precisa ser feito:**
1. Investigar por que o A* não encontra caminhos
2. Verificar se o `obstacle_grid` está sendo populado corretamente
3. Verificar se as coordenadas estão sendo convertidas corretamente (world → grid)
4. Testar o A* isoladamente para garantir que funciona
5. Implementar fallback seguro quando A* não encontra caminho
6. Garantir que o robô realmente desvia das áreas proibidas durante a navegação

---

## 🎯 Próximos Passos (Prioridade)

### 1. **IMPLEMENTAR DESVIO DE ÁREAS PROIBIDAS** (ALTA PRIORIDADE)
   - **Status:** Parcialmente implementado, mas não funciona
   - **Objetivo:** Fazer o robô desviar automaticamente de áreas proibidas durante a navegação
   - **Arquivos principais:**
     - `src/core/path_finder.py` - Algoritmo A* e gerenciamento de obstáculos
     - `src/core/robot_navigator.py` - Lógica de navegação
   - **Tarefas:**
     - [ ] Debug do A* para entender por que não encontra caminhos
     - [ ] Verificar conversão de coordenadas (world → grid)
     - [ ] Verificar se `obstacle_grid` está sendo populado corretamente
     - [ ] Testar A* com casos simples primeiro
     - [ ] Implementar fallback quando A* falha
     - [ ] Testar navegação com áreas proibidas reais
     - [ ] Garantir que o robô realmente desvia (não passa por cima)

### 2. **IMPLEMENTAR SENSOR C1 RPLIDAR** (MÉDIA PRIORIDADE)
   - **Status:** Não implementado
   - **Objetivo:** Integrar o sensor LIDAR C1 RPlidar para detecção de obstáculos em tempo real
   - **Arquivos relevantes:**
     - `src/c1_scanner/` - Estrutura existe mas precisa ser integrada
     - `src/core/slamtec_manager.py` - Gerenciador de sensores SLAMTEC
   - **Tarefas:**
     - [ ] Integrar leitura do sensor C1 RPlidar
     - [ ] Processar dados do LIDAR em tempo real
     - [ ] Usar dados do LIDAR para detecção de obstáculos dinâmicos
     - [ ] Combinar dados do LIDAR com áreas proibidas estáticas
     - [ ] Atualizar pathfinding em tempo real com obstáculos detectados

### 3. **IMPLEMENTAR IMU** (MÉDIA PRIORIDADE)
   - **Status:** Não implementado
   - **Objetivo:** Integrar IMU (Inertial Measurement Unit) para melhorar precisão de orientação
   - **Tarefas:**
     - [ ] Integrar leitura do IMU
     - [ ] Usar dados do IMU para correção de deriva angular
     - [ ] Combinar dados do IMU com odometria
     - [ ] Melhorar precisão de orientação durante navegação

---

## 📁 Estrutura de Arquivos Relevantes

### Navegação e Pathfinding
```
src/core/
├── robot_navigator.py      # Lógica principal de navegação
├── path_finder.py          # Algoritmo A* e gerenciamento de obstáculos
└── config.py               # Configurações (FORBIDDEN_AREA_INFLATION_RADIUS = 0.40m)
```

### Interface
```
src/interfaces/
├── main_window.py          # Interface principal (gerencia áreas proibidas)
└── map_widget.py           # Widget do mapa (desenha áreas proibidas)
```

### Sensores (A Implementar)
```
src/c1_scanner/             # Scanner C1 (estrutura existe)
src/core/slamtec_manager.py # Gerenciador de sensores SLAMTEC
```

---

## 🔧 Configurações Importantes

### Configurações de Navegação (`src/core/config.py`)
```python
FORBIDDEN_AREA_INFLATION_RADIUS = 0.40  # 40cm de margem de segurança
ROBOT_WIDTH = 0.6                        # 60cm de largura
MAP_GRID_SIZE = 0.1                      # 10cm por célula do grid
NAVIGATION_GOAL_TOLERANCE = 0.15         # 15cm de tolerância de chegada
```

### Estados de Navegação
- `IDLE` - Robô parado, aguardando comando
- `ORIENTING_TO_TARGET` - Orientando-se para o alvo
- `NAVIGATING_TO_DESTINATION` - Navegando até o POI
- `FINAL_APPROACH_DESTINATION` - Aproximação final ao POI
- `PAUSED_AT_DESTINATION` - Pausado no POI (2 segundos)
- `RETURNING_TO_BASE` - Retornando à base
- `FINAL_APPROACH_BASE` - Aproximação final à base
- `ADJUSTING_FINAL_ANGLE` - Ajustando ângulo final
- `COMPLETED` - Navegação concluída

---

## 🐛 Problemas Conhecidos

### 1. A* Não Encontra Caminhos
**Sintoma:** Logs mostram "Nenhum caminho encontrado pelo A*"  
**Possíveis causas:**
- Conversão incorreta de coordenadas world → grid
- `obstacle_grid` não está sendo populado corretamente
- Start ou goal estão em células marcadas como obstáculo
- Grid muito pequeno ou dimensões incorretas

### 2. Navegação Aborta Quando Há Áreas Proibidas
**Sintoma:** Sistema mostra erro "Não foi possível encontrar caminho seguro"  
**Causa:** Quando A* retorna `None`, navegação é abortada  
**Solução necessária:** Implementar fallback ou corrigir A*

---

## 📝 Notas Técnicas

### Como o PathFinder Funciona (Teoricamente)
1. Recebe áreas proibidas como polígonos (lista de coordenadas)
2. Converte polígonos para células do grid usando `FORBIDDEN_AREA_INFLATION_RADIUS`
3. Marca células proibidas no `obstacle_grid`
4. Quando `find_path(start, goal)` é chamado:
   - Converte coordenadas world → grid
   - Verifica se start/goal estão em obstáculos
   - Executa A* para encontrar caminho
   - Retorna caminho como lista de coordenadas world

### Como a Navegação Deveria Funcionar com Áreas Proibidas
1. Usuário seleciona POI e inicia navegação
2. `robot_navigator.navigate_to_and_return()` verifica se há áreas proibidas
3. Se houver, chama `path_finder.find_path(current_position, destination)`
4. PathFinder retorna caminho que evita áreas proibidas
5. Robô navega waypoint por waypoint seguindo o caminho

### O Que Está Acontecendo Agora (Sem Desvio)
1. Usuário seleciona POI e inicia navegação
2. Sistema tenta usar PathFinder
3. A* retorna `None` (não encontra caminho)
4. Sistema aborta navegação com erro
5. **OU** sistema usa navegação direta e passa por cima das áreas proibidas

---

## 🚀 Como Iniciar a Implementação do Desvio

### Passo 1: Debug do A*
1. Adicionar logs detalhados no `path_finder.py`:
   - Log das coordenadas de entrada (start, goal) em world
   - Log das coordenadas convertidas para grid
   - Log do tamanho do `obstacle_grid`
   - Log de quantas células estão marcadas como obstáculo
   - Log se start/goal estão em obstáculos

### Passo 2: Testar A* Isoladamente
1. Criar teste simples:
   - Mapa pequeno (10x10 células)
   - 1 área proibida no meio
   - Start e goal em lados opostos
   - Verificar se A* encontra caminho ao redor

### Passo 3: Verificar Conversão de Coordenadas
1. Verificar se `world_to_grid()` está correto
2. Verificar se `grid_to_world()` está correto
3. Testar com coordenadas conhecidas

### Passo 4: Verificar População do obstacle_grid
1. Adicionar logs em `_update_obstacle_grid()`
2. Verificar se polígonos estão sendo inflados corretamente
3. Verificar se células estão sendo marcadas corretamente

### Passo 5: Implementar Fallback
1. Se A* não encontrar caminho, tentar:
   - Reduzir `FORBIDDEN_AREA_INFLATION_RADIUS` temporariamente
   - Usar caminho direto se não houver interseção
   - Mostrar aviso ao usuário

---

## 📚 Referências Úteis

### Arquivos de Código
- `src/core/path_finder.py` - Linha 948: `get_navigation_status()`
- `src/core/path_finder.py` - Linha 227: `_astar_optimized()`
- `src/core/path_finder.py` - Linha 100: `_update_obstacle_grid()`
- `src/core/robot_navigator.py` - Linha 600: `navigate_to_and_return()`
- `src/core/robot_navigator.py` - Linha 274: `_calculate_and_execute_return_angle()`

### Configurações
- `FORBIDDEN_AREA_INFLATION_RADIUS = 0.40` (40cm)
- `ROBOT_WIDTH = 0.6` (60cm)
- `MAP_GRID_SIZE = 0.1` (10cm por célula)

---

## ✅ Checklist para Implementação

### Desvio de Áreas Proibidas
- [ ] Debug do A* - entender por que não encontra caminhos
- [ ] Verificar conversão de coordenadas (world ↔ grid)
- [ ] Verificar população do `obstacle_grid`
- [ ] Testar A* com casos simples
- [ ] Implementar fallback quando A* falha
- [ ] Testar navegação real com áreas proibidas
- [ ] Validar que robô realmente desvia (não passa por cima)

### Sensor C1 RPlidar
- [ ] Integrar leitura do sensor
- [ ] Processar dados em tempo real
- [ ] Detecção de obstáculos dinâmicos
- [ ] Integração com pathfinding

### IMU
- [ ] Integrar leitura do IMU
- [ ] Correção de deriva angular
- [ ] Integração com odometria

---

**Última Atualização:** Dezembro 2025  
**Próximo Foco:** Implementar desvio de áreas proibidas (A* não está funcionando)


