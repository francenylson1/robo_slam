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
3. **Não consegue fazer o giro para Retorno à base** - Volta à posição inicial
4. **Não consegue fazer o giro para o Ajuste final** - Ajusta para posição inicial (270°)

### **Configurações Estáveis (NÃO ALTERAR):**
Os valores do PID e as velocidades estão ajustadas de maneira que permite o robô fazer uma navegação estável até o POI, se corrigindo se necessário.

**IMPORTANTE:** Esses valores garantem navegação estável. NÃO altere sem testar cuidadosamente nada sobre velocidade, pois o motor que usamos é muito potente e usamos apenas 12 a 15% da potência total do motor. NÃO PODEMOS PASSAR DISSO.


## ⚠️ **PROBLEMA ESPECÍFICO A SER CORRIGIDO**

###1.** NAVEGAÇÃO COM CURVAS MAIS FECHADAS DE 30, 45 GRAUS O ROBÔ NÃO CONSEGUE FAZER, SE PERDE E SEGUE EM LINHA RETA NÃO CHEGANDO AO DESTINO POI. MUITO CUIDADO AO TENTAR CORRIGIR ESSE PROBLEMA E NÃO ALTERAR A NAVEGAÇÃO EM LINHA RETA E CURVAS SUAVES QUE ESTÁ SENDO FUNCIONAL E PERFEITA.

### - **Ao chegar no destino POI, o robô precisa fazer um giro MANUAL de +- 180 graus através dos botões esquerda/direita. Esse giro não está funcionando.

## 🔧 **ARQUIVOS PRINCIPAIS**

### **Arquivos de referência:**
- `src/core/config.py` - Configurações globais
- `gpio_test.py` - Teste direto dos motores (funciona corretamente)

## 🏷️ **VERSÕES DISPONÍVEIS**

**Manter** a navegação estável (não quebrar o que já funciona)

## 🚀 **COMO TESTAR**

### **1. Fazer commit, e git push sempre;
### **2. pull na raspberry, sempre orientar os comandos para Raspberry

# Executar o robô
python3 src/main.py

## 📝 **REGRAS IMPORTANTES**

1. **Sempre teste** antes de commitar
3. **Crie backup** antes de modificações grandes
4. **Mantenha** a navegação estável (não quebre o que funciona)

## 🔍 **DICAS TÉCNICAS**
Desenvolvimento aqui no desktop e teste real na Raspberry

## 🎯 **OBJETIVO FINAL**
Robô garçon funcional que navega conforme seleção de destinos(POI) pelo usuário, parar no POI, Giros manuais para retornar a base e ter  a funcionalidade de "voltar para base"(botão já existe)

**Status:** ✅ Navegação estável e funcional(vai até o POi selecionado e pára). 
Se o pOI tiver curvas mais fechadas o robõ se perde e não consegue fazer a curva e segue reto deixando de chegar ao destino.  
**Próximo passo:**
1. Corrigir e deixar o robõ hábil para fazer curvas ou deixar as curvas mais arredondadas ao criar o percurso com linha azul9já funcionando0.
2. Fazer os botões esquerda/direita funcionarem ao serem clicados para fazer o giro de +- 18i graus, para possibilitar uma orientação correta para retorno á base;
 