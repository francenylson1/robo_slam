# Navegação: por que só odometria (main.py) pode parecer mais precisa que teste com IMU BNO08x

## O que o main.py faz (sem IMU)

- Usa **mapa**, **A\*** e **odometria** (ticks das rodas).
- Posição e ângulo do robô vêm **só da odometria**, atualizadas a cada leitura dos encoders.
- O navegador calcula: “ângulo desejado até o waypoint” e “distância”; manda **velocidade linear e angular** para o controlador.
- O **mesmo** PID dos motores e os **mesmos** fatores de correção (ex.: `LEFT_MOTOR_CORRECTION_FACTOR`) foram ajustados para esse fluxo.
- Ou seja: **uma única fonte de verdade** (odometria) e um laço fechado coerente (mapa → waypoint → velocidade → motores → odometria → mapa).

## O que o teste de linha reta com BNO faz

- Usa **BNO08x** para “manter o rumo” (yaw) em linha reta.
- A correção é um **controlador P** separado: `erro = yaw_atual - yaw_referência` → ajusta TPS esquerda/direita.
- Aqui existem **duas fontes de verdade**: odometria (ticks) e IMU (yaw). Se a convenção do yaw (sentido de giro) for diferente da convenção das rodas, ou se o BNO tiver atraso/ruído, a correção pode:
  - Aplicar no **sentido errado** (piorar a curva) → por isso existe `BNO_STRAIGHT_INVERT_CORRECTION`.
  - Ser **fraca** (ganho baixo) ou **atrasada** (amostragem lenta), e o robô já ter virado quando a correção age.

## Por que “só odometria” pode parecer mais precisa

1. **Consistência**: No main.py, posição e ângulo vêm só da odometria; não há conflito com outro sensor.
2. **Sintonia**: O PID e os fatores de correção dos motores foram afinados para esse uso (navegação no mapa).
3. **Referência global**: O mapa e o caminho dão uma referência estável; o robô “sabe” para onde ir e corrige em relação ao waypoint, não só ao último yaw do BNO.
4. **IMU no teste**: No teste de linha reta, o BNO entra como um laço extra. Se o **sentido da correção** estiver invertido (como era com `BNO_STRAIGHT_INVERT_CORRECTION = False`), o robô curva mais para um lado em vez de endireitar.

## O que foi ajustado

- **BNO_STRAIGHT_INVERT_CORRECTION = True** no `config.py`: para o seu robô, quando ele curva para a esquerda, a correção passa a acelerar a roda direita (e frear a esquerda), alinhando com a convenção física das rodas.
- Depois de testar de novo com `--no-turns`, se ainda curvar, ajuste `BNO_STRAIGHT_KP` ou `BNO_STRAIGHT_MAX_CORRECTION_TPS` no config.

## Próximo passo (integrar BNO ao main.py)

Para a navegação com mapa ficar ainda melhor com o BNO, o ideal é **usar o BNO dentro do mesmo laço do navegador**: por exemplo, atualizar o ângulo (ou a pose) com uma fusão odometria + BNO (complementar filter ou média ponderada), em vez de um controlador de “linha reta” separado. Assim continua uma única referência de pose, mas mais estável em retas longas.
