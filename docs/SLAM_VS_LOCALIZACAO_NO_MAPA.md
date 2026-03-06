# SLAM vs localização no mapa PGM — quando vale a pena

## 1. O que é o quê (para não confundir)

| Termo | Significado no seu contexto |
|-------|------------------------------|
| **SLAM** (strict) | Construir o mapa **enquanto** o robô se localiza (mapa novo, em tempo real). Não é o que vocês usam na navegação hoje. |
| **Mapa PGM que vocês têm** | Mapa **já pronto** (gerado antes, por outro processo: Aurora, C1, pipeline de mapeamento). É um “produto de SLAM/mapeamento”, mas estático. |
| **Localização no mapa conhecido** | O robô **já tem** o mapa (PGM). Usar sensores (ex.: LIDAR) para **estimar/corrigir a pose (x, y, θ)** comparando o que o sensor vê com o mapa. Muitas vezes as pessoas chamam isso de “usar SLAM” ou “localização tipo SLAM”, mas tecnicamente é **localização em mapa conhecido**. |

No seu sistema hoje: **não há localização no mapa**. A pose vem só da odometria; o PGM é usado para desenho e planejamento (áreas proibidas, tamanho do mundo), não para “onde estou”.

---

## 2. Usar o PGM para “SLAM” (na prática: localização no mapa) — melhora ou não?

**Resposta direta:** usar o PGM para **localização** (estimar/corrigir a pose com base no que o robô “vê” no ambiente) **pode melhorar bastante** a precisão e a robustez da navegação. **Não** é algo que “não altera nada”.

- **Odometria sozinha:** a pose (x, y, θ) **deriva** com o tempo (patinação, erros nas rodas). Em percursos longos ou muitos giros, o robô “acha” que está num lugar e na verdade está em outro.
- **Localização no mapa:** de tempos em tempos (ou em tempo contínuo) o sistema compara o que o sensor (ex.: LIDAR) vê com o mapa PGM e **corrige** a pose. Assim:
  - **Posição (x, y):** deixa de acumular erro indefinidamente; o mapa “puxa” a estimativa para o lugar certo.
  - **Orientação (θ):** também pode ser refinada quando o casamento scan–mapa for bom.

Ou seja: **sim, usar o PGM para localização tende a aumentar a precisão** (desde que o algoritmo e o sensor estejam integrados e afinados). Não é “não altera em nada”.

---

## 3. Para o robô garçom em mesas específicas: usar “SLAM”/localização no mapa acrescenta?

**Sim. Para um robô garçom que deve ir a mesas específicas em um mapa, localização no mapa PGM acrescenta muito.**

- **Só odometria (e depois odometria + BNO):**
  - BNO melhora o **rumo** (ângulo), mas a **posição (x, y)** continua derivando.
  - Em várias idas e voltas, o robô pode “achar” que a mesa 5 está 20–30 cm para o lado, ou que ele já chegou quando ainda falta um pouco. Para “ir à mesa X” de forma confiável, isso é um limite.

- **Com localização no mapa (LIDAR vs PGM):**
  - O sistema sabe “onde o robô está **no mapa**” (em qual corredor, perto de qual parede, em qual mesa).
  - O planejamento “vá à mesa 5” é feito em coordenadas do mapa; a pose é **corrigida** pelo casamento com o mapa, então o robô realmente tende a chegar na mesa 5 e não numa posição derivada.
  - Ou seja: **localização no PGM é muito útil** para “navegar em mesas específicas” de forma repetível e precisa.

Resumo: para o plano de ter o garçom navegando em mesas específicas no mapa, **usar o PGM para localização (o que muitos chamam de “usar SLAM”) não só pode como costuma acrescentar bastante** em precisão e confiabilidade.

---

## 4. O que seria preciso para “usar o PGM para SLAM” (localização no mapa)?

Na prática, “usar o PGM para SLAM” aqui significa: **localização em mapa conhecido** usando o PGM.

- **Sensor:** em geral **LIDAR** (ou outro sensor de distância 2D/3D) que varre o ambiente e produz “scans” (nuvem de pontos ou distâncias por ângulo).
- **Algoritmo:** algo que compare o scan atual com o mapa PGM (ocupação) e estime a pose (x, y, θ). Exemplos:
  - **Filtro de partículas (estilo AMCL):** várias hipóteses de pose; cada uma é avaliada pelo “quão bem o scan combina com o mapa”; as melhores sobrevivem e a pose estimada é uma média/ponderada.
  - **Scan matching (ex.: ICP, ou matching em grid):** ajusta (x, y, θ) para maximizar o casamento entre o scan e o mapa.
- **Integração:** essa pose estimada (ou uma fusão com odometria/BNO) vira a `current_position` e `current_angle` usadas na navegação.

No seu projeto hoje: o **SlamtecManager** existe mas o LIDAR real no fluxo de navegação ainda não está integrado (retorna mock). Então “implementar SLAM” nesse sentido = **integrar LIDAR** + **implementar ou integrar um algoritmo de localização no PGM** (AMCL ou similar). É um passo maior do que só ligar o BNO nas retas.

---

## 5. Ordem sugerida (minha opinião)

- **Agora (curto prazo):**  
  - **BNO só nas retas (Fase 1)** — melhora o ângulo com pouco esforço e sem LIDAR.  
  - Isso **já melhora** a precisão da navegação (menos desvio de 20–40°), mas a posição (x, y) continua só odometria.

- **Depois (médio prazo), se o objetivo é garçom em mesas específicas:**  
  - **Localização no mapa PGM** (LIDAR + algoritmo tipo AMCL ou scan matching) para corrigir (x, y) e refinar θ.  
  - Aí sim você passa a “usar o PGM para SLAM” no sentido que as pessoas costumam dar: o mapa entra na **localização**, não só na visualização e no planejamento.  
  - Para “ir à mesa X” de forma confiável, esse passo **acrescenta muito**.

Em uma frase: **sim, usar o PGM para localização (SLAM/localização em mapa conhecido) tende a melhorar a precisão e é muito útil para o garçom em mesas específicas; não é algo que “não altera nada”.** Vale a pena como próximo passo depois do BNO, quando houver LIDAR integrado e tempo para implementar ou integrar o algoritmo de localização no mapa.
