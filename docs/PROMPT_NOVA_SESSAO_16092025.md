# PROMPT PARA NOVA SESSÃO - Robô SLAM v1.43.4

## 🎯 **CONTEXTO DO PROJETO**

Você está trabalhando em um **robô garçom autônomo** com navegação SLAM. O projeto está em uma fase avançada onde a navegação básica já funciona, mas há problemas específicos de controle angular em curvas e implementação de giros manuais.

## 📋 **O QUE O PROJETO FAZ**

**Objetivo:** Robô que navega autonomamente para pontos de interesse (POI) e retorna à base  
**Tecnologia:** Raspberry Pi + Python + PyQt5 + PID Control + Odometria  
**Funcionalidade:** Interface gráfica permite selecionar pontos no mapa, robô navega até o ponto e retorna à base

## ✅ **STATUS ATUAL - O QUE JÁ ESTÁ FUNCIONANDO**

### **Navegação Completa Funcionando:**
1. ✅ **Navegação em linha reta** - Robô vai ao destino sem se perder
2. ✅ **Chegada ao destino** - Para corretamente no ponto selecionado
3. ✅ **Sistema look-ahead** - Segue caminho traçado com 30cm de antecipação
4. ✅ **Velocidade mínima** - 60% para evitar travamento em curvas
5. ✅ **Detecção de obstáculos** - Para quando encontra obstáculo

### **Configurações Estáveis (NÃO ALTERAR):**
Os valores do PID e as velocidades estão ajustadas de maneira que permite o robô fazer uma navegação estável até o POI, se corrigindo se necessário.

**IMPORTANTE:** Esses valores garantem navegação estável. NÃO altere sem testar cuidadosamente nada sobre velocidade, pois o motor que usamos é muito potente e usamos apenas 12 a 15% da potência total do motor. NÃO PODEMOS PASSAR DISSO.

## ⚠️ **PROBLEMAS ATUAIS A SEREM CORRIGIDOS**

### **1. CONTROLE ANGULAR EM CURVAS**
- **Status:** PARCIALMENTE RESOLVIDO
- **Problema:** Controle angular muito agressivo (-221°) causando instabilidade
- **Última correção:** Reduzido fator de 3.0 para 2.0 (commit pendente)
- **Próximo passo:** Testar na Raspberry Pi e ajustar se necessário

### **2. GIROS MANUAIS NÃO FUNCIONAM**
- **Status:** PENDENTE
- **Problema:** Botões esquerda/direita não fazem giro de ±180° no POI
- **Localização:** `src/interfaces/main_window.py` e `src/core/robot_navigator.py`
- **Funções:** `manual_turn_left()` e `manual_turn_right()`

### **3. CURVAS FECHADAS (30-45°)**
- **Status:** EM ANÁLISE
- **Problema:** Robô se perde em curvas muito fechadas e segue reto
- **Possível solução:** Ajustar look-ahead distance ou suavizar curvas

## 🔧 **ARQUIVOS PRINCIPAIS**

### **Arquivos de navegação:**
- `src/core/robot_navigator.py` - Lógica principal de navegação
- `src/core/robot_motor_controller.py` - Controle dos motores
- `src/core/config.py` - Configurações globais

### **Arquivos de interface:**
- `src/interfaces/main_window.py` - Interface principal com botões
- `src/interfaces/map_widget.py` - Widget do mapa

### **Arquivos de teste:**
- `gpio_test.py` - Teste direto dos motores (funciona corretamente)
- `tests/` - Diversos testes específicos

## 🏷️ **VERSÃO ATUAL**

**Versão:** v1.43.4 (em desenvolvimento)  
**Último commit:** Ajuste controle angular de 3.0 para 2.0 (PENDENTE COMMIT)  
**Branch:** main

## 🚀 **FLUXO DE DESENVOLVIMENTO**

### **1. DESENVOLVIMENTO NO DESKTOP**
```bash
# Diretório de trabalho
cd d:\robo_slam

# Fazer alterações nos arquivos
# Testar localmente quando possível
```

### **2. COMMIT DAS ALTERAÇÕES**
```bash
# Adicionar arquivos modificados
git add .

# Commit com mensagem descritiva
git commit -m "🎯 DESCRIÇÃO: Detalhes da correção v1.43.x"

# Push para repositório
git push
```

### **3. TESTE NA RASPBERRY PI**
```bash
# Na Raspberry Pi, baixar alterações
git pull

# Executar o robô
python3 src/main.py

# Observar logs para verificar correções
```

## 📝 **LOGS IMPORTANTES PARA MONITORAR**

### **Navegação em curvas:**
```
🎯 CURVA: Controle balanceado - Linear: 0.18, Angular: -147.2°
🎯 LOOK-AHEAD: Seguindo ponto 2/5 a 0.36m
```

### **Velocidades esperadas:**
- **Linear:** 0.12-0.18 m/s (mínimo 60%)
- **Angular:** -150° a +150° (balanceado)

## 🔍 **PRÓXIMOS PASSOS PRIORITÁRIOS**

### **1. ALTA PRIORIDADE**
1. **Commit da correção angular** (fator 2.0)
2. **Testar na Raspberry Pi** a navegação em curvas
3. **Implementar giros manuais** nos botões esquerda/direita

### **2. MÉDIA PRIORIDADE**
1. **Ajustar curvas fechadas** (look-ahead ou suavização)
2. **Melhorar retorno à base** (orientação final)

## 🎯 **OBJETIVO FINAL**

Robô garçom funcional que:
1. ✅ Navega conforme seleção de destinos (POI) pelo usuário
2. ✅ Para no POI corretamente
3. ⚠️ **Permite giros manuais** para orientação (PENDENTE)
4. ✅ Tem funcionalidade "voltar para base" (botão já existe)
5. ⚠️ **Faz curvas fechadas** sem se perder (EM ANÁLISE)

## 📊 **HISTÓRICO DE CORREÇÕES RECENTES**

### **v1.43.3 - Controle Angular Agressivo**
- Aumentou fator de 1.5 para 3.0
- Resultado: Muito agressivo (-221°)
- Status: Corrigido para 2.0

### **v1.43.2 - Velocidade em Curvas**
- Aumentou velocidade mínima de 30% para 60%
- Removeu multiplicador 0.8
- Status: Funcionando

### **v1.43.1 - Sistema Look-ahead**
- Implementou seguimento de caminho
- Look-ahead de 30cm
- Status: Funcionando

## 🚨 **REGRAS IMPORTANTES**

1. **SEMPRE fazer commit** antes de testar na Raspberry
2. **SEMPRE fazer git push** após commit
3. **SEMPRE fazer git pull** na Raspberry antes de testar
4. **NÃO alterar velocidades** sem extremo cuidado
5. **Manter navegação estável** (não quebrar o que funciona)
6. **Testar sempre** antes de commitar

## 🔧 **COMANDOS ÚTEIS**

### **Desktop (Desenvolvimento):**
```bash
git status
git add .
git commit -m "mensagem"
git push
```

### **Raspberry Pi (Teste):**
```bash
git pull
python3 src/main.py
# Observar logs no terminal
```

---

**Status:** ✅ Navegação estável e funcional (vai até o POI selecionado e para)  
**Próximo passo:** Commit da correção angular e implementação dos giros manuais  
**Versão alvo:** v1.44.0 - Navegação completa com giros manuais funcionais