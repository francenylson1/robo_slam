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

Concluímos a calibração do PID e agora estamos adaptando a lógica de navegação de alto nível para trabalhar **COM** as capacidades reais do hardware, em vez de lutar contra elas.

**Plano de Ação e Estado Atual:**

*   **Etapa 1: Persistir os Ganhos Ótimos (CONCLUÍDO)**
    *   **Ação Realizada:** Os ganhos ótimos (`Kp=0.11`, `Ki=0.05`, `Kd=0.0`) foram persistidos no `robot_motor_controller.py`.
    *   **Status:** Finalizado e enviado para o GitHub (commit `be98b98`).

*   **Etapa 2: Adaptação da Lógica de Navegação (EM ANDAMENTO)**
    *   **Análise (CONCLUÍDO):** Analisamos o `src/core/robot_navigator.py` e identificamos a função `_move_towards_target` como o local onde as velocidades são calculadas e enviadas ao controle PID.
    *   **Implementação (PENDENTE DE COMMIT):** Para resolver o problema de instabilidade em baixas velocidades, implementamos uma lógica de **"piso de velocidade mínima"**. Esta alteração garante que o navegador nunca comande uma velocidade abaixo do nosso mínimo estável de `20 tps`.
    *   **Arquivo Modificado:** `src/core/robot_navigator.py`.

*   **Etapa 3: Próximos Passos Imediatos (Início da Próxima Sessão)**
    *   **Ação 1: Finalizar o Commit:** Fazer o `commit` e `push` da alteração pendente no `src/core/robot_navigator.py`. A mensagem do commit deve ser: `"Feat: Implementa piso de velocidade mínima no navegador"`.
    *   **Ação 2: Sincronizar a Raspberry Pi:** Executar o procedimento seguro (`git fetch`, `git reset --hard`, `git clean -fd`) na Raspberry Pi para garantir que ela tenha a versão mais recente e corrigida.
    *   **Ação 3: Teste de Navegação Completo:** Com a lógica de navegação atualizada, realizar o teste definitivo: usar a interface principal para comandar o robô a um ponto no mapa. O critério de sucesso é um movimento **suave e contínuo**, sem as tremedeiras ou hesitações que víamos antes, especialmente ao iniciar o movimento e ao se aproximar do alvo. 