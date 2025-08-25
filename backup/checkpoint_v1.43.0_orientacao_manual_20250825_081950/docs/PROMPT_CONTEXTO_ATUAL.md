# PROMPT PARA CONTINUAÇÃO - Robô SLAM - Correção de Direção

## 🎯 CONTEXTO DO PROJETO

Se comporte como um especialista em Python, Raspberry Pi, robótica e SLAM. Você está finalizando a depuração de um **robô garçom autônomo**. O projeto está em uma fase crítica onde a força, a velocidade e a sincronia entre a interface e o robô físico foram corrigidas, mas resta um último problema de inversão de direção.

- **Objetivo:** Robô que navega autonomamente para pontos de interesse.
- **Tecnologia:** Python, PyQt5, PID Control, Odometria, SLAM e Raspberry Pi 4

---

## ✅ O QUE JÁ ESTÁ FUNCIONANDO (NÃO ALTERAR)

Após uma longa sessão de depuração, alcançamos os seguintes marcos. **É crucial que estas partes do código não sejam alteradas**, pois já estão validadas:

### 1. Força e Velocidade Excelentes
- Os ganhos do PID foram calibrados manualmente para um ótimo desempenho.
- O limite de potência do PID foi aumentado para 90%.
- **Resultado:** Quando o robô se move, ele o faz com força e velocidade adequadas.
- **Local:** `src/core/robot_motor_controller.py`
- **Valores Atuais (NÃO ALTERAR):**
  ```python
  self.pid_left = PIDController(Kp=0.26, Ki=0.23, Kd=0.0, setpoint=0, output_limits=(-90, 90))
  self.pid_right = PIDController(Kp=0.26, Ki=0.23, Kd=0.0, setpoint=0, output_limits=(-90, 90))
  ```

### 2. Sincronia entre Robô Físico e Interface (UI)
- O movimento do robô físico é refletido com precisão na interface gráfica.
- **Resultado:** Se o robô físico gira para a direita, a UI também mostra um giro para a direita. A odometria está funcionando corretamente.
- **Local:** `src/core/robot_navigator.py` (método `_update_pose_with_odometry`)

### 3. Planejamento de Rota Correto
- O `PathFinder` (que gera a **linha azul** no mapa) calcula corretamente a rota mais eficiente do ponto A ao ponto B.

---

## ⚠️ O PROBLEMA PENDENTE (FOCO TOTAL)

O problema atual é um **conflito entre o plano e a execução**.

### Descrição Detalhada do Problema:
1.  O `PathFinder` calcula a rota correta (ex: a **linha azul** na UI mostra uma curva para a **esquerda**).
2.  O `RobotNavigator` (o "cérebro" que decide o movimento) lê essa rota, mas comanda os motores para irem para a **direita**.
3.  Como a UI e o físico estão sincronizados, ambos (robô físico e robô na UI) giram para a **direita**, se afastando da rota planejada.

### Sintoma Resultante:
O robô vira levemente para o lado **errado**, o sistema detecta um erro angular enorme em relação à rota correta, a lógica de controle reduz a velocidade de avanço para zero (para tentar corrigir o ângulo), e o robô **trava**, pois sua tentativa de "correção" só o afasta mais do caminho.

### Causa Raiz Identificada:
A fórmula da **cinemática diferencial** no método `_move_towards_target` do `RobotNavigator` está invertida. Ela está traduzindo a instrução "virar à esquerda" no comando de motor que fisicamente produz um giro "à direita".

---

## 🎯 TAREFA IMEDIATA E ÚNICA

**Objetivo:** Fazer o robô seguir a direção da **linha azul**.

**Ação:** Inverter a fórmula da cinemática diferencial no arquivo `src/core/robot_navigator.py`, especificamente nos métodos `_move_towards_target` e `_stable_final_approach` para consistência.

- **Arquivo a ser modificado:** `src/core/robot_navigator.py`
- **Alteração necessária:**

  - **DE (Código atual incorreto):**
    ```python
    left_wheel_speed_ms = v - (w * L) / 2.0
    right_wheel_speed_ms = v + (w * L) / 2.0
    ```

  - **PARA (Código corrigido):**
    ```python
    left_wheel_speed_ms = v + (w * L) / 2.0
    right_wheel_speed_ms = v - (w * L) / 2.0
    ```

### Regras Cruciais para a Próxima Ação:
1.  **NÃO ALTERE** a força, velocidade ou os ganhos de PID. Eles estão corretos.
2.  **NÃO ALTERE** a fórmula da odometria em `_update_pose_with_odometry`. Ela está correta.
3.  A **única alteração** necessária é na fórmula da **cinemática**, como descrito acima, para alinhar a execução do movimento com o plano.
