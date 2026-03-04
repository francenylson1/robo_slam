# Navegação melhor: patinação e uso do BNO

Quando as rodas **patinam**, a odometria (ticks) passa a **mentir**: ela integra rotação que não aconteceu de verdade (ou o contrário). O BNO (IMU) mede a **orientação real** do robô no espaço e não depende das rodas. Por isso, a solução para navegação mais estável é **usar BNO junto com a odometria**, principalmente para o **ângulo** (rumo).

---

## Estratégia em 3 níveis

### 1. Reduzir a patinação (comportamento e hardware)

- **Velocidade menor:** Usar TPS mais baixo em trechos críticos (ex.: `SPEED_SLOW_TPS` ou perfil “slow” no navegador). Menos aceleração → menos patinação.
- **Superfície:** Preferir piso aderente; evitar tapetes, pisos muito lisos ou sujos.
- **Rodas/contato:** Verificar pressão/borracha e que as duas rodas tenham bom contato com o chão.
- **Aceleração suave (futuro):** Se o controlador permitir, rampar a velocidade em vez de subir de 0 a TPS de uma vez.

Isso **diminui** a frequência dos “runs desorientados”, mas não elimina a patinação. A navegação precisa ser **robusta** mesmo quando as rodas patinam.

---

### 2. Integrar BNO no navegador (Fase 2) – principal melhoria

Hoje o **main.py** usa **só odometria** para posição e ângulo. Quando há patinação, o ângulo acumulado pelas rodas fica errado e o robô “acha” que está em um rumo diferente do real.

**O que fazer:** usar o BNO para o **ângulo (yaw)** no fluxo de navegação:

- **Linha reta:** Manter o rumo com correção BNO (como já fazemos no `teste_bno_suite.py`): `yaw_ref` no início, correção left/right com `BNO_STRAIGHT_KP` e `BNO_STRAIGHT_MAX_CORRECTION_TPS`.
- **Pose (posição + ângulo):** Em vez de atualizar o ângulo **só** pela odometria, usar o **yaw do BNO** (ou uma fusão simples: ex. ângulo = BNO, posição = odometria com o ângulo do BNO para direção). Assim, quando as rodas patinam, o rumo do robô no mapa continua correto e a navegação não “desorienta”.

Com isso, a navegação fica **melhor** mesmo com patinação ocasional: o robô mantém o rumo certo e os giros continuam alinhados ao mapa.

---

### 3. (Opcional) Detecção de patinação

Se quisermos ir além: quando, em um intervalo curto, a **odometria** indicar uma rotação grande e o **BNO** indicar rotação pequena, podemos considerar que houve patinação e:

- confiar mais no BNO para o ângulo, e/ou  
- reduzir temporariamente a velocidade.

Isso pode ser implementado depois da Fase 2, como refinamento.

---

## Ordem sugerida

1. **Curto prazo:** Continuar testes da Fase 1 (giros, anotar erros); em paralelo, usar TPS mais baixo ou piso mais aderente para reduzir patinação onde possível.
2. **Próximo passo central:** **Fase 2 – integrar BNO no main.py/navegador** (ângulo do BNO ou fusão simples ângulo BNO + posição odometria), seguindo o checklist em `docs/PROMPT_CONTINUACAO_BNO_E_INTEGRACAO_2026.md` e `docs/REVISAO_BNO_LINHA_RETA.md`.
3. **Depois:** Ajustar ganhos (Kp, max_correction) com base nos testes reais; opcionalmente adicionar detecção de patinação.

---

## Resumo em uma frase

**Para navegação melhor com rodas que patinam: reduzir patinação onde der (velocidade, piso) e, principalmente, usar o BNO para o ângulo no navegador (Fase 2), para que o rumo do robô não dependa só das rodas.**
