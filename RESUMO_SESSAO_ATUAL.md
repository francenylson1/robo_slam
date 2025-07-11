# Resumo do Projeto e Próximos Passos (12/07/2025)

## 1. Visão Geral do Projeto

O objetivo é o desenvolvimento de um **robô garçom autônomo** utilizando uma **Raspberry Pi 4 (4GB)** como unidade de processamento principal. O sistema de controle de alto nível é gerenciado por uma interface gráfica (PyQt) em um PC, que lida com o mapa (SLAM), definição de destinos e monitoramento. A navegação autônoma é o objetivo final.

## 2. O Que Já Fizemos: A Saga da Calibração do Controle de Motores

A fase mais recente do projeto foi uma profunda e desafiadora jornada para estabilizar o controle de baixo nível dos motores do robô físico.

*   **Diagnóstico Inicial:** O robô não se movia corretamente. Identificamos problemas como lógica de direção invertida e ganhos PID ineficazes.
*   **Criação da Ferramenta de Calibração:** Desenvolvemos a `calibration_window.py` para permitir o ajuste fino e em tempo real dos ganhos PID (`Kp`, `Ki`, `Kd`).
*   **Investigação de Bugs e Instabilidade:**
    *   **Ruído Elétrico:** Descobrimos que o principal vilão era o **ruído elétrico** gerado pelos motores, que corrompia a leitura dos sensores Hall (encoders), gerando "tiques fantasmas" e leituras de velocidade falsamente altas.
    *   **Tentativas de Filtro:** Implementamos várias soluções de software para combater o ruído, incluindo `locks` para evitar condições de corrida, filtros `debounce` para ignorar pulsos falsos, e até mesmo alteramos a frequência do loop de controle.
*   **O Ponto de Virada (Insight Chave):** Após muita depuração, chegamos a duas conclusões críticas:
    1.  Uma versão específica do código (commit `f3f3a7a`), que opera com um loop de controle a **20Hz**, provou ser a mais estável.
    2.  Nesta configuração, a **menor velocidade estável e mensurável** que o sistema consegue atingir de forma confiável é **20 tps (tiques por segundo)**. Tentar forçar o sistema a um alvo menor (como os 15 tps que usávamos) causa instabilidade inevitável.

## 3. Estado Atual (Onde Estamos)

*   **Código Estável:** Revertemos o código para a versão estável de 20Hz (commit `f3f3a7a`), que contém o filtro debounce e os limites de potência seguros para o PID.
*   **Ganhos Ótimos Identificados:** Encontramos uma combinação de ganhos PID que produz um movimento **fluido e contínuo para frente**, estabilizando a velocidade em `20 tps`. Os ganhos são:
    *   `Kp = 0.11`
    *   `Ki = 0.05`
    *   `Kd = 0.0`
*   **Pronto para a Próxima Fase:** O controle de baixo nível está, pela primeira vez, previsível e funcional.

## 4. O Que Falta Fazer: A Transição para a Navegação Inteligente

Nossa pendência principal é adaptar a lógica de alto nível do robô para trabalhar **COM** a realidade do hardware, em vez de lutar contra ela.

**A Grande Transição: Adotar 20 tps como a Nova Realidade**

A tarefa agora é revisar a arquitetura de software para que ela use `20 tps` como uma velocidade base ou mínima, em vez dos `15 tps` arbitrários de antes.

**Plano de Ação Detalhado:**

*   **Etapa 1: Persistir os Ganhos Ótimos (Trabalho Rápido)**
    *   **Ação:** Atualizar os valores padrão na inicialização dos `PIDController` dentro do `src/core/robot_motor_controller.py` para `Kp=0.11`, `Ki=0.05`, `Kd=0.0`.

*   **Etapa 2: Análise e Adaptação da Lógica de Navegação (Trabalho Principal)**
    *   **Objetivo:** Encontrar onde o código de alto nível (provavelmente em `src/core/robot_navigator.py`) calcula as velocidades das rodas e as converte para tiques por segundo.
    *   **Hipótese:** Existe uma constante `MAX_TPS` ou uma fórmula de conversão de `m/s` para `tps` que precisa ser reavaliada.
    *   **Ação:** Precisamos garantir que, quando o navegador pedir um movimento lento, o comando enviado ao controlador de motor seja de, no mínimo, `20 tps`, ou um valor que o sistema possa executar de forma estável.

*   **Etapa 3: Teste de Navegação Completo**
    *   **Objetivo:** Validar a nova lógica em um cenário de uso real.
    *   **Ação:** Usar a interface principal para comandar o robô a navegar para um ponto específico no mapa. Observar se ele segue o caminho calculado com precisão e se o movimento é suave, sem hesitações ou tremedeiras, especialmente em baixas velocidades e ao iniciar o movimento. 