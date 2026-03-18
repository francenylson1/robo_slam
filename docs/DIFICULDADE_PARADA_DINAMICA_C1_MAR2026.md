# Dificuldade de Parada Dinâmica — LIDAR C1 (Mar 2026)

## Resumo do problema

- **Comportamento atual:** Robô para às vezes, não para outras. Sem padrão claro.
- **Exemplo:** Lixeira a ~120 cm → robô parou a 20 cm dela (ok). Em outros casos, não para ou atropela.
- **Comportamento binário:** Obstáculo < 85 cm → PARA. Sem obstáculo → SEGUE. Não há transição suave.

## Objetivo

Robô **dinâmico** e **seguro**: diante de obstáculo (lixeira, criança, idoso), o robô **sempre** para.

---

## Por que é difícil parar de forma dinâmica e consistente?

### 1. Detecção intermitente do RP Lidar C1

O C1 é um sensor 2D que varre 360° em rotações (~5–10 Hz). A detecção depende de:

| Fator | Efeito |
|-------|--------|
| **Ângulo da superfície** | Superfícies oblíquas ou curvas refletem menos. Lixeira redonda ou pessoa de lado podem não ser vistas em certos ângulos. |
| **Cor/material** | Superfícies escuras ou absorventes refletem menos que brancas. |
| **Posição no cone** | O código usa um cone frontal (0°±100°). Obstáculo ligeiramente fora do cone = não detectado. |
| **Variação de montagem** | Se 0° do sensor não aponta exatamente para a frente do robô, o cone “erra” parte do espaço. |
| **Leituras inválidas** | Distâncias < 150 mm (corpo do robô) são ignoradas; faixa 120°–240° é descartada. |

**Resultado:** Em alguns momentos o LIDAR vê o obstáculo; em outros, não. Daí o “às vezes para, às vezes não”.

---

### 2. Arquitetura atual é reativa e binária

O fluxo hoje é:

```
Navegador envia: (velocidade_frente, velocidade_lateral)
     ↓
Motor Controller: tem obstáculo < 85 cm?
     SIM → força velocidade = 0
     NÃO → aplica a velocidade pedida
```

Não há:

- **Redução gradual** de velocidade quando o obstáculo se aproxima
- **Fusão** com outros sensores (bumpers, ultrassom)
- **Predição** de trajetória (obstáculo pode entrar no caminho)

Ou seja: é só “bloqueia/não bloqueia”, o que causa o comportamento “PARA ou SEGUE”.

---

### 3. Janela entre detecção e parada

- Velocidade atual: ~0,30 m/s
- LIDAR: ~5–10 varreduras/s → ~100–200 ms entre leituras
- Em 200 ms o robô percorre ~6 cm

Se em uma varredura o LIDAR não vê o obstáculo, o robô continua; na próxima varredura pode já estar mais perto. Quanto mais perto e mais rápido, mais crítico esse atraso.

---

### 4. Desbloqueio conservador

Para evitar desbloqueio falso (e atropelo), o código exige:

- 5 scans consecutivos “livres”
- Último obstáculo registrado > 0,8 m

Isso reduz falsos desbloqueios, mas o problema principal continua: **quando o LIDAR não detecta**, o robô nunca entra em modo de bloqueio.

---

## Opções para resolver

### Opção A — Parada sempre garantida (mais simples, menos dinâmico)

**Ideia:** Priorizar segurança. Qualquer suspeita de obstáculo → parar.

| Ação | Descrição |
|------|-----------|
| A1. Aumentar distância de parada | Ex.: 1,2 m em vez de 0,85 m. Margem maior, mas robô para mais longe. |
| A2. Expandir o cone | Ex.: 240° ou 270°. Mais cobertura, mais risco de falsos positivos (paredes, corpo). |
| A3. Eliminar desbloqueio automático | Enquanto navega, nunca “desbloquear” sozinho. Só após comando do usuário ou cancelamento. |
| A4. Velocidade reduzida por padrão | Ex.: 0,20 m/s. Menos distância percorrida entre varreduras, mais tempo para reagir. |

**Prós:** Implementação simples, maior segurança.  
**Contras:** Comportamento ainda binário; pode parar em excesso.

---

### Opção B — Parada dinâmica (velocidade proporcional à distância)

**Ideia:** Velocidade depende da distância ao obstáculo.

```
Distância d ao obstáculo:
  d >= 1,0 m  → velocidade normal (0,30 m/s)
  d 0,6–1,0 m → reduzir 50% (0,15 m/s)
  d 0,4–0,6 m → reduzir 80% (0,06 m/s)
  d < 0,4 m   → PARAR (0)
```

| Ação | Descrição |
|------|-----------|
| B1. Modificar `set_target_speed` | Antes de aplicar velocidade, usar `obstacle_distance()` e escalar linearmente. |
| B2. Zonas de velocidade | Várias faixas de distância com fatores diferentes (como acima). |
| B3. Velocidade mínima segura | Nunca passar de `v_max * (d / d_safe)` com limite inferior 0. |

**Prós:** Comportamento mais suave e “dinâmico”.  
**Contras:** Só funciona quando o LIDAR detecta; se não detectar, o robô segue em velocidade cheia.

---

### Opção C — Melhorar detecção (raiz do problema)

**Ideia:** Garantir que o LIDAR veja o obstáculo na maior parte do tempo.

| Ação | Descrição |
|------|-----------|
| C1. Calibração de ângulo | Confirmar com `calibracao_c1_orientacao.py` que 0° aponta para a frente do robô. |
| C2. Cone 360° (sem exclusão de trás) | Monitorar todos os ângulos; parar se obstáculo < limite em qualquer direção. Cuidado com corpo do robô. |
| C3. Segundo sensor | Adicionar ultrassom ou sensor IR na frente como redundância. |
| C4. Reduzir `min_ignore` na zona frontal | Já feito (50 mm em 350°–10°). Revisar outras zonas se necessário. |

**Prós:** Trata a causa da detecção intermitente.  
**Contras:** Exige testes e possivelmente hardware extra.

---

### Opção D — Camada de segurança em hardware (recomendado para pessoas)

**Ideia:** Não depender só do LIDAR para garantir parada em caso de pessoa.

| Ação | Descrição |
|------|-----------|
| D1. Bumpers como backup | Sensores de impacto que cortam motores mesmo se o LIDAR falhar. |
| D2. Sensor ultrassom frontal | Boa detecção de tecido, pele, superfícies não ideais para LIDAR. |
| D3. Parada por timeout | Se LIDAR não atualizar em X segundos, tratar como “obstáculo” e parar. |

**Prós:** Aumenta muito a segurança para uso com pessoas.  
**Contras:** Alterações de hardware e integração.

---

## Recomendações práticas (ordem de prioridade)

1. **Curto prazo (software):**
   - Implementar **Opção B** (velocidade proporcional à distância).
   - Reduzir velocidade padrão para 0,25 m/s (Opção A4).
   - Garantir que desbloqueio automático seja bem restrito (Opção A3).

2. **Médio prazo (calibração):**
   - Executar **Opção C1** e validar o alinhamento 0° do C1.

3. **Longo prazo (segurança para pessoas):**
   - Avaliar **Opção D** (bumpers e/ou ultrassom).

---

## Dados complementares que ajudariam

Para orientar melhor os ajustes, estes dados são úteis:

| Dado | Para quê |
|------|----------|
| **Log com mensagens do LIDAR** | Ver distâncias reportadas em cada momento (buscar "LIDAR C1: distância" e "OBSTÁCULO"). |
| **Ângulo exato do C1 em relação ao robô** | Saber se o cone está correto. Resultado da calibração (0° = frente?). |
| **Descrição da lixeira** | Altura, cor, formato (cilíndrica, retangular etc.). |
| **Distâncias nas quais o robô parou** | Ex.: "parou a 20 cm", "parou a 1 m", "não parou". |
| **Posição da lixeira em relação ao robô** | Sempre à frente? À esquerda/direita? Em curva? |
| **Presença de bumpers** | Se existem e se estão integrados ao firmware. |

---

## Próximos passos sugeridos

1. Rodar um teste com log completo e filtrar por "LIDAR" para ver o que o C1 reporta durante a navegação.
2. Escolher entre:
   - **Opção A** (mais segura, menos dinâmica), ou
   - **Opção B** (dinâmica, mas depende da detecção).
3. Se quiser **Opção B**, o próximo passo é implementar velocidade escalada por distância em `robot_motor_controller.py`.
