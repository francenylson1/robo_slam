# Estratégia: base odometria + BNO gradual

## Decisão

- **Voltar** à versão estável **só com odometria** (navegação física e virtual sincronizadas).
- **Abandonar** temporariamente o uso do BNO no laço de controle atual (não funcionou de forma confiável).
- **Reintroduzir o BNO em fases**: primeiro só nas retas, depois nos giros, depois etapas adicionais se fizer sentido.

---

## Opinião técnica

- **Reverter para só odometria** é a escolha certa: uma única fonte de verdade (encoders) evita giros infinitos e “virtual de ré”, e devolve um comportamento previsível.
- **Estratégia gradual** (1 → retas, 2 → giros, 3 → refinamentos) é a forma adequada de trazer o BNO de volta:
  - **Retas:** odometria erra principalmente no **rumo** (deriva); BNO corrige bem e não atrapalha o controle.
  - **Giros:** odometria pode errar no ângulo total do giro; BNO pode corrigir **depois** do giro, sem disputar o comando durante a curva.
- Assim evitamos usar BNO como **única** referência de ângulo no controle (que foi a causa dos problemas). O BNO entra como **correção** sobre a odometria, em situações bem definidas.

---

## Procedimentos

### 0. Onde está a “versão estável”

- **Commit de referência (só odometria no navegador):** `645b278` (Docs: análise CSV linha reta 04/03…).
- O commit seguinte, `d9e7b45`, é o “Fase 2: integrar BNO no navegador” — a partir daí o BNO entrou no laço de controle.

Você pode:
- usar `645b278` como base para um branch estável, ou
- no branch atual, desligar o BNO no navegador (pose = só odometria) e manter o resto do código (recomendado para evoluir em fases).

---

### 1. Estabelecer a base só odometria

**Opção A – Branch a partir do commit estável (histórico limpo)**  
- Criar branch, por exemplo: `robo_slam_2026_odometry_stable`.  
- `git checkout -b robo_slam_2026_odometry_stable 645b278`  
- Trabalhar e testar nesse branch. O branch atual (`robo_slam_2026_1_bno_com_odometria`) fica como referência do que foi feito com BNO.

**Opção B – Manter branch atual e “desligar” BNO no navegador (recomendado)**  
- No branch atual, um **único flag** em `config.py` desliga o BNO no navegador:
  - `USE_BNO_IN_NAVIGATION = False`: pose e controle usam só odometria; BNO não é inicializado no navegador.
  - `USE_BNO_IN_NAVIGATION = True`: comportamento anterior (BNO na pose e correção de rumo), para Fases 1/2.
- Ferramentas (bno08x_test, teleop, etc.) não usam esse flag e continuam iguais para testes.
- Vantagem: não perde commits recentes e reativar BNO por fases é só mudar o flag e a lógica (ex.: BNO só em retas).

**Validação (obrigatória)**  
- Testar na Raspberry: **só ida** e **com retorno**.  
- Confirmar: robô físico e virtual sincronizados, sem giros infinitos no POI e sem “volta de ré” do virtual.

---

### 2. Fase 1 – BNO só nas retas

**Objetivo:** Corrigir deriva de rumo em trechos retos; não mexer no comportamento em giros.

**Critério “reta”:**
- Comando do controlador: avanço (v > 0) e rotação pequena, por exemplo `|ω| < limiar` (ex.: 0.15–0.2 rad/s), **ou**
- Velocidade angular medida (odometria) abaixo de um limiar por um tempo mínimo (ex.: 0.5 s).

**Lógica:**
- **Durante “reta”:**  
  - Posição: só odometria.  
  - Ângulo: atualizar com BNO (com offset fixo em relação ao mapa), por exemplo fusão suave (complementar ou média ponderada) entre ângulo odometria e BNO.
- **Fora de “reta” (curva/giro):**  
  - Ângulo: **só odometria** (BNO não entra no controle nem na pose exibida durante o giro).

**Implementação sugerida:**
- Flag ou config: `use_bno_on_straights_only = True`.
- Em `_update_pose_with_odometry`: depois de integrar odometria, se `use_bno_on_straights_only` e “reta” (critério acima), substituir ou misturar o ângulo da pose com o BNO (offset aplicado uma vez, por exemplo ao carregar o mapa ou no início da navegação).

**Validação:**  
- Linha reta longa: virtual deve alinhar melhor com o trajeto (menos deriva).  
- Giro no POI: comportamento igual ao da base só odometria (sem piorar).

---

### 3. Fase 2 – BNO nos giros

**Objetivo:** Corrigir erro de ângulo acumulado nos giros, **sem** usar BNO durante o giro no laço de controle.

**Abordagem sugerida:**
- **Durante o giro:** ângulo continua só da odometria (como na Fase 1).
- **Ao sair do giro:** quando a rotação termina (ex.: `|ω|` cai e fica abaixo do limiar por um tempo), fazer uma **correção única** do ângulo da pose com o BNO (com o mesmo offset do mapa).  
  Opcional: limitar a correção a um máximo (ex.: 5–10°) para não “pular” a pose na tela.

**Implementação sugerida:**
- Flag ou config: `use_bno_after_turns = True`.
- Detectar “fim de giro” (ex.: `|ω|` < limiar por ≥ 0.3 s).
- Uma vez por “fim de giro”: `current_angle = normalize(bno_yaw + bno_offset)` (ou fusão suave).

**Validação:**  
- Giro de 90° ou 180°: após o giro, a seta do robô no mapa deve ficar mais alinhada com a direção real.  
- Navegação “só ida” e “com retorno” continuam estáveis.

---

### 4. Fase 3 – Refinamentos (conforme necessidade)

Possíveis etapas (a definir depois de validar Fases 1 e 2):

- **Fusão contínua:** usar BNO sempre, mas com ganho que depende do regime (reta vs giro): ganho alto nas retas, baixo ou zero nos giros.
- **Tolerâncias e timeouts:** ajustar limiares de “reta” e “fim de giro” com base em logs e testes.
- **Retorno à base:** garantir que o offset do BNO (ou a lógica de “reta”/“giro”) funcione também no trecho de retorno.

---

## Resumo dos passos práticos

| Ordem | Ação |
|-------|------|
| 1 | Decidir: Opção A (branch em 645b278) ou Opção B (branch atual com BNO desligado no navegador). |
| 2 | Aplicar a opção e garantir que a pose no navegador venha **só da odometria**. |
| 3 | Testar só ida e com retorno; confirmar sincronia físico/virtual. |
| 4 | Fase 1: implementar “BNO só nas retas”; testar retas longas e giros. |
| 5 | Fase 2: implementar “BNO após giros”; testar giros e rotas completas. |
| 6 | Fase 3: refinamentos (fusão contínua, limiares, retorno) conforme resultados. |

---

## Arquivos principais

- **Pose e BNO:** `src/core/robot_navigator.py` (`_update_pose_with_odometry`, uso de `current_angle` no controle).
- **Config:** `src/core/config.py` (flags como `use_bno_on_straights_only`, `use_bno_after_turns`, limiares).
- **Init BNO:** mantido para Fases 1 e 2; ferramentas em `tools/` continuam iguais para testes.

Documento alinhado com a decisão: voltar à versão estável só odometria e reintroduzir BNO de forma gradual (1 → retas, 2 → giros, 3 → refinamentos).
