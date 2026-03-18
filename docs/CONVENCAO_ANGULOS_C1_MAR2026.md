# Convenção de ângulos — RP Lidar C1 vs projeto robô

**Data:** Março 2026  
**Objetivo:** Esclarecer a confusão entre as convenções do sensor C1 e do projeto.

---

## 1. Duas convenções possíveis

Existem **duas convenções** comuns para ângulos em robótica (vistos de cima):

| Direção | Convenção HORÁRIA (CW) | Convenção ANTI-HORÁRIA (CCW) |
|---------|------------------------|------------------------------|
| **0°**  | Frente                 | Frente                       |
| **90°** | Direita                | **Esquerda**                 |
| **180°**| Trás                   | Trás                         |
| **270°**| **Esquerda**           | Direita                      |

O **projeto** (interface, navegação, `ROBOT_INITIAL_ANGLE`) usa a convenção **horária**:
- 0° = frente
- 90° = direita
- 180° = trás
- **270° = esquerda**

---

## 2. O que o RP Lidar C1 usa?

O datasheet do C1 define **0° = frente** (seta no sensor) e **180° = traseira** (cabo). O **sentido** em que os ângulos aumentam (90° = esquerda ou direita) pode variar conforme:

- Versão do firmware
- Montagem (sensor rotacionado)
- Interpretação da biblioteca `rplidarc1`

**Não há garantia** de que o C1 use a mesma convenção que o projeto.

---

## 3. O que o wizard de calibração faz?

O wizard **não impõe** uma convenção. Ele apenas:

1. Pede para colocar o obstáculo à esquerda do robô.
2. Lê o ângulo **raw** que o sensor reporta.
3. Exibe: `ESQUERDA 90° ≈ XX°` — em que XX° é o valor reportado.

Então:
- **"ESQUERDA 90° ≈ 90°"** → com obstáculo à esquerda, o sensor reportou **90°** → nessa montagem, **90° = esquerda** (convenção CCW).
- **"ESQUERDA 90° ≈ 270°"** → com obstáculo à esquerda, o sensor reportou **270°** → nessa montagem, **270° = esquerda** (convenção CW, igual ao projeto).

---

## 4. Qual valor usar em `FRONT_CENTER_DEG`?

O único valor que **precisa** estar correto é o da **frente**:

- Use o ângulo da etapa **"OBSTÁCULO NA FRENTE"** como `FRONT_CENTER_DEG`.
- O `lidar_c1_reader` usa esse centro para o cone frontal; esquerda/direita servem só para conferência.

---

## 5. Se o wizard mostrar "ESQUERDA 90° ≈ 90°"

Isso indica que, nessa montagem, o C1 usa **convenção anti-horária**:

- 0° = frente  
- 90° = esquerda  
- 180° = trás  
- 270° = direita  

Ou seja, oposta à convenção horária do projeto (90° = direita, 270° = esquerda). Não há erro de configuração: são apenas referenciais diferentes.

---

## 6. Referências no código

- `lidar_c1_reader.py`: `FRONT_CENTER_DEG = 0` (quando a seta do C1 aponta para a frente do robô).
- `docs/FASE2_FAIXA_FRONTAL_C1.md`: descreve convenção horária do **projeto**; pode divergir do sensor conforme a montagem.
- Wizard: `tools/calibracao_c1_orientacao.py` — os ângulos exibidos são sempre os **raw** do sensor.

---

## 7. Resumo prático

| Situação | Ação |
|----------|------|
| Wizard mostra Esquerda ≈ 90° | Sensor usa CCW: 90° = esquerda. Nada a corrigir. |
| Wizard mostra Esquerda ≈ 270° | Sensor usa CW: 270° = esquerda, igual ao projeto. |
| Configure `FRONT_CENTER_DEG` | Use o valor da etapa "FRENTE" do wizard. |
| Dúvida sobre esquerda/direita | Consulte este documento; o cone frontal depende só da frente. |
