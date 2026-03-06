# Análise dos logs – Fase 1: giro de 360° no POI e desvio para a direita

## O que os logs mostram

- **"DESTINO CONSIDERADO ALCANÇADO (<1m há >15s, evita giros em loop): 78.0cm"**  
  Ou seja: o robô estava a **78 cm** do POI e, depois de **mais de 15 s** em aproximação final, o sistema considerou “chegada” e parou.
- Durante esses **15+ segundos** o robô ficou **só girando** (não avançando), daí o giro de ~360–370° que você viu.

---

## Por que o robô fica girando ~360° no POI

1. **Transição para aproximação final**  
   Quando o robô chega perto do POI (ex.: &lt; 20 cm ou entra em FINAL_APPROACH), o controle passa a usar `_stable_final_approach`.

2. **Lógica da aproximação final**  
   - Calcula `target_angle` = direção **para o POI** (atan2(dy, dx)).  
   - Exige que o robô esteja **alinhado** (erro de ângulo &lt; 2–5°) para **avançar** (v &gt; 0).  
   - Se não estiver alinhado, manda **só rotação** (v = 0, ω ≠ 0) até alinhar.

3. **Fase 1: ângulo só da odometria no giro**  
   Com `USE_BNO_ON_STRAIGHTS_ONLY = True`, o ângulo da pose usa BNO **só quando** |Δθ| &lt; 2° (reta). **Durante o giro** no POI, |Δθ| é grande → o ângulo vem **só da odometria**.

4. **Efeito**  
   Se a odometria **subestima** o giro (patinação, assimetria das rodas), o software “acha” que ainda falta ângulo para alinhar e continua mandando “girar”. O robô gira no lugar (até ~360° ou mais) até a regra **“&lt; 1 m há &gt; 15 s”** considerar chegada e parar. Por isso você vê: chega no POI → gira ~360–370° → para.

Resumo: o **giro de 360°** não é um bug aleatório; é o controle tentando alinhar usando **só odometria** no giro, que não “vê” o alinhamento, e a parada acontece só pelo **tempo** (15 s a &lt; 1 m).

---

## Por que “BNO não está corrigindo a rota” e o desvio para a direita

- **Na reta:** o BNO entra na **pose** só quando |Δθ| &lt; 2° por ciclo; nos **motores** entra via `_apply_bno_straight_correction` quando há avanço (v &gt; 0).
- **Desvio para a direita** pode ser:
  1. **Limiar 2° muito apertado:** em trechos com curva muito suave (&gt; 2° por ciclo), o ângulo da pose fica só da odometria → deriva acumula e o controle não corrige direito → trajetória pende para a direita.
  2. **Correção de rumo BNO:** ganho baixo (`BNO_STRAIGHT_KP`) ou **sinal invertido** (`BNO_STRAIGHT_INVERT_CORRECTION`) faz a correção não compensar (ou piorar) o desvio.

Ou seja: o BNO “não corrigir a rota” e o “leve desvio para direita” batem com: BNO pouco usado na pose (2° restritivo) e/ou correção de rumo com ganho/sinal inadequados.

---

## O que foi corrigido (sem tentativas aleatórias)

1. **Giro de 360° no POI**  
   - **Causa:** Regra “&lt; 1 m há &gt; 15 s” permitia até **15 s** de giro no lugar.  
   - **Correção:** Considerar chegada quando **&lt; 1 m há &gt; 8 s** (em vez de 15 s). Assim limitamos o tempo de giro no POI e reduzimos a quantidade de rotação (ex.: ~1 giro em vez de 1+ giro prolongado).

2. **Desvio para a direita (dar mais chance ao BNO)**  
   - **Causa provável:** Limiar 2° faz o BNO ser usado na pose em poucos ciclos; em curvas suaves a odometria domina e deriva.  
   - **Correção:** Aumentar `STRAIGHT_ANGLE_THRESHOLD_DEG` de **2° para 3°**. Em mais ciclos o ângulo da pose usa BNO, o que pode reduzir a deriva para a direita.  
   - **Se ainda desviar:** ajustar em **config** (sem mexer na lógica):  
     - `BNO_STRAIGHT_INVERT_CORRECTION` (testar True/False conforme o robô curvar para um lado),  
     - `BNO_STRAIGHT_KP` (aumentar um pouco se a correção estiver fraca).

Nenhuma outra lógica foi alterada; só essa regra de tempo e o limiar de “reta”.

---

## Resumo

| Sintoma | Causa (análise) | Ajuste feito |
|--------|-----------------|--------------|
| Giro ~360° ao chegar no POI | Alinhamento só por odometria no giro; regra &lt;1 m há 15 s permitia 15 s de giro | Considerar chegada se &lt; 1 m há **8 s** (em vez de 15 s) |
| Desvio para a direita na rota | BNO pouco usado na pose (2° restritivo); possível ganho/sinal da correção de rumo | Limiar “reta” de 2° para **3°**; conferir depois BNO_STRAIGHT_KP e INVERT no config |

Depois de testar, se o desvio continuar, o próximo passo é só **config**: inverter `BNO_STRAIGHT_INVERT_CORRECTION` e/ou aumentar um pouco `BNO_STRAIGHT_KP`, sem mudar mais a lógica.
