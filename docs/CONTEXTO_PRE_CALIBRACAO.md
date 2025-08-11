### **Assunto:** Ponto de Controle e Contexto do Projeto (Pré-Calibração PID)

#### **1. Situação Atual**

O projeto está em uma fase crucial de transição da simulação para a realidade. A lógica de navegação de alto nível, validada no robô virtual, não está sendo executada com precisão pelo robô real. O objetivo principal é sincronizar o comportamento de ambos.

#### **2. Funcionalidades Validadas (O que já funciona)**

*   **Navegação Virtual:** O robô virtual, usando o `RobotNavigator`, executa perfeitamente o ciclo de navegação completo (`IDA -> PAUSA -> VOLTA`) em um ambiente simulado. Isso valida a lógica de planejamento de trajetória.
*   **Controle Básico do Hardware:**
    *   A lógica de direção dos motores (`HIGH`/`LOW` para frente/trás) foi corrigida no `_pid_control_loop` para corresponder à fiação física do robô.
    *   A potência do controlador PID foi aumentada (`output_limits=(-40, 40)`), garantindo que os motores tenham força suficiente para vencer a inércia e o atrito iniciais.
*   **Infraestrutura:** O fluxo de trabalho usando `git` para atualizar o código na Raspberry Pi está estabelecido e funcional.

#### **3. Principal Desafio Pendente (A Causa do Desvio)**

O robô real não consegue seguir uma trajetória reta, desviando para a direita. A hipótese central é que as inevitáveis **assimetrias físicas do hardware** (diferenças entre motores, atrito, distribuição de peso) não estão sendo compensadas pelo controlador PID.

Os ganhos atuais do PID (`Kp`, `Ki`, `Kd`) são ineficazes, resultando em um controle de baixo nível que não consegue forçar as rodas a manterem a mesma velocidade para seguir a rota ditada pelo navegador.

#### **4. Plano de Ação Imediato (Próxima Fase: Calibração)**

Conforme decidido, a estratégia é pausar o desenvolvimento da navegação principal para criar uma **ferramenta de calibração do PID dedicada**. O plano consiste em:
1.  **Desenvolver uma nova interface gráfica (`PyQt`)** que servirá como um painel de controle.
2.  **Equipar a interface com:**
    *   Sliders ou campos de texto para ajustar os ganhos `Kp`, `Ki`, `Kd` de cada motor em tempo real.
    *   Gráficos para visualizar, para cada roda: a velocidade alvo (setpoint), a velocidade real (feedback do encoder) e a potência de saída do PID.
    *   Botões para acionar movimentos de teste padronizados (andar reto, girar).
3.  **Modificar o `RobotMotorController`** para permitir a alteração dos ganhos do PID em tempo real e para expor os dados necessários para os gráficos.
4.  **Executar a calibração** de forma metódica até que o robô real consiga seguir os comandos de velocidade com precisão.

#### **5. Objetivo Pós-Calibração**

Após a conclusão bem-sucedida da calibração, o robô real deverá ser capaz de executar trajetórias retas e curvas com alta fidelidade, replicando o comportamento do robô virtual. Com isso alcançado, o desenvolvimento da ferramenta de calibração será mesclado e o foco retornará às funcionalidades de navegação de alto nível. 