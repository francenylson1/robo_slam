# Navegação: odometria, mapa PGM e BNO

## Sua conclusão está correta

- **Só ida (19 testes):** Desconsiderar o 1º teste (1 giro de 360°) e considerar os 19 com precisão — procedimento adequado.
- **Desvio de orientação (20–40°) ao chegar no POI:** É esperado sem BNO/IMU. A odometria integra bem a posição (x, y), mas o ângulo acumula erro (patinação, diferença entre rodas). O BNO/IMU é quem corrige esse rumo.
- **Com retorno (5 testes):** Comportamento correto (ida → POI → giro 180° → retorno → giro 180°). Os desvios de orientação devem receber o mesmo tratamento: esperados sem BNO; BNO virá para corrigir.
- **Conclusão:** Com apenas odometria o resultado está muito bom; o único problema observado é a orientação, e a integração do BNO (primeiro só nas retas) é o próximo passo adequado.

---

## O robô está navegando só por odometria ou também pelos mapas PGM?

**Resposta direta:** A **pose** (posição e ângulo) do robô vem **apenas da odometria** (encoders das rodas). O mapa PGM **não** é usado para dizer “onde o robô está”.

Detalhando:

| O quê | Fonte |
|-------|--------|
| **Posição (x, y) e ângulo** | **Só odometria.** Atualizados em `_update_pose_with_odometry()` a partir dos ticks das rodas. Nenhum outro sensor ou mapa corrige a pose em tempo real. |
| **Mapa PGM** | Usado para: (1) **exibição** no widget do mapa, (2) **PathFinder**: dimensões do mundo (largura, altura, origem em metros) e sistema de coordenadas quando o PGM é carregado, (3) opcionalmente **posição inicial** do robô ao carregar o mapa. O PathFinder **não** lê pixels do PGM para obstáculos; ele usa apenas as **áreas proibidas** (polígonos definidos pelo usuário). |

Ou seja: **navegação = odometria para localização**. O PGM entra só para **visualização**, **tamanho/origem do mundo** e **planejamento** (evitar áreas proibidas), não para “onde estou”.

---

## Os mapas PGM têm dados de SLAM?

- **Formato do PGM:** São **mapas de ocupação** (grid: livre/ocupado/desconhecido). Em geral são **resultado** de um processo de mapeamento (ex.: pipeline Aurora, C1, ou mapa 2D a partir de nuvem de pontos). Ou seja, são “produto de SLAM/mapeamento”, não um “SLAM em tempo real”.
- **Nesta aplicação:** Não há **localização em tempo real** usando o mapa (sem scan matching, sem AMCL, sem fusão de pose com o PGM). O robô **não** se localiza no PGM; ele só usa odometria para pose e o PGM para desenho e configuração do PathFinder.

Resumo: os PGM podem ter sido **gerados** por SLAM, mas o app **não** usa o PGM para SLAM/localização agora — só odometria.

---

## Como a navegação está sendo feita hoje

- **Localização (onde estou):** **Só odometria** (encoders → dx, dy, dθ → `current_position`, `current_angle`).
- **Mapa PGM:** Apenas para **exibição**, **dimensões/origem** do PathFinder e **áreas proibidas** (polígonos) no planejamento.
- **Planejamento:** PathFinder usa `current_position` (odometria) e destino para calcular caminho (A*), evitando as áreas proibidas.

Em uma frase: **odometria (localização) + mapa PGM (visualização e planejamento de caminho, sem corrigir a pose)**.

---

## Próximo passo: BNO só nas retas (Fase 1)

**Sugestão:** Sim, ir para a **integração do BNO só nas retas**, conforme o plano em `docs/ESTRATEGIA_ODOMETRIA_E_BNO_GRADATIVO.md`.

- **Objetivo:** Corrigir a deriva de **rumo** em trechos retos (reduzir os 20–40° de desvio ao chegar no POI), sem alterar o comportamento em giros.
- **Implementação resumida:**  
  - Critério “reta”: por exemplo |ω| &lt; limiar (ou comando de avanço com rotação pequena).  
  - **Em retas:** ângulo da pose = fusão de odometria + BNO (com offset fixo ao mapa).  
  - **Em curvas/giros:** ângulo = só odometria.  
  - Posição (x, y) continua só odometria.

---

## Depois da integração do BNO (Fase 1): como fica a navegação

- **Localização:** **Odometria + BNO (apenas em retas)** para o ângulo; posição (x, y) continua só odometria.  
- **Mapa PGM:** Igual a hoje: exibição, dimensões/origem do PathFinder, áreas proibidas.  
- **Planejamento:** Igual: PathFinder com pose atual e destino.

Em uma frase: **odometria + BNO (só nas retas) para rumo + mapa PGM (visualização e planejamento)**.  
Não será “odometria + SLAM + BNO” porque não há localização por mapa (SLAM em tempo real) nesta aplicação; o PGM não corrige a pose.

---

## Resumo em uma tabela

| Etapa | Localização (pose) | Mapa PGM | Planejamento |
|-------|--------------------|----------|--------------|
| **Hoje (só odometria)** | Odometria (x, y, θ) | Visual + tamanho/origem + áreas proibidas | PathFinder com pose (odometria) |
| **Fase 1 (BNO só retas)** | Odometria (x, y) + BNO (θ em retas) | Igual | Igual |
| **Fase 2 (BNO nos giros)** | Odometria + BNO (θ também após giros) | Igual | Igual |

SLAM/localização no mapa não entra nessa tabela porque atualmente não é usado; quando/quando houver, seria um passo futuro (ex.: relocalização no PGM).
