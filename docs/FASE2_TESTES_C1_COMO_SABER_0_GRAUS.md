# Como saber onde está o 0° e medir a área livre — Testes do C1

**Objetivo:** Responder a três perguntas práticas:
1. **Onde está o ponto 0°?** (direção de referência do sensor)
2. **Quantos graus tem a área sem obstáculo fixo?** (área “livre” vs corpo do robô)
3. **Como fazer os testes?** (passo a passo)

---

## 1. Onde está o 0°?

### 1.1 Referência física (RPLidar A1/A2/C1)

Na família RPLidar (A1, A2, C1, S1), a referência angular é ligada à **posição do cabo**:

- **0°** é a direção para onde o **cabo preto** aponta.
- **Sentido horário** = ângulo aumenta (visto de cima).

Segundo a documentação (ex.: ArduPilot, datasheets): o sensor deve ser montado com o **cabo preto apontando para a traseira** do veículo. Nesse caso:
- 0° ≈ traseira do robô (onde o cabo sai)
- 180° ≈ frente do robô

### 1.2 E se o sensor estiver invertido ou rotacionado?

Se a montagem não seguir esse padrão:

- **0°** continua sendo “cabo preto”.
- Você precisa **medir** qual ângulo corresponde à direção de movimento do seu robô.

### 1.3 Como descobrir na prática (teste de diagnóstico)

Use o modo `--diagnose` do script:

```bash
python tools/teste_c1_isolado.py --diagnose --scans 2
```

O script:
- Divide os 360° em setores (ex.: 18 setores de 20°)
- Mostra a distância mínima em cada setor
- Setores com distância pequena (~96–150 mm) → provável **corpo do robô** ou obstáculo fixo
- Setores com distância maior → **área livre**

Com isso, você identifica:
- **Onde está o 0°** (eixo do cabo)
- **Qual ângulo corresponde à frente** do seu robô (em geral a direção com mais espaço livre)

---

## 2. Quantos graus tem a área sem obstáculo fixo?

### 2.1 O que é o “obstáculo fixo”?

- É o que gera leituras de ~96–98 mm ou pouco mais (~100–150 mm):
  - Corpo do robô
  - Suportes
  - Alcance mínimo do C1 (~50–80 mm)

### 2.2 Como medir a área “livre”

1. Defina um limite (ex.: 150 mm ou 200 mm).
2. “Área livre” = ângulos em que a distância mínima é **maior** que esse limite.
3. “Área ocupada” = ângulos em que a distância mínima é **menor** que o limite.

Exemplo:

```
Se em setores 0°–20° e 340°–360° a distância mínima ≈ 97 mm → corpo do robô (~40° ocupado)
→ Área livre ≈ 360° − 40° = 320°
```

O valor exato **depende da montagem** do seu robô. Só é possível medir com o `--diagnose`.

### 2.3 Interpretação típica

| Situação                     | Área ocupada (ex.) | Área livre (ex.) |
|-----------------------------|--------------------|------------------|
| C1 no centro, corpo pequeno | ~40–80°            | ~280–320°        |
| C1 descentrado ou corpo maior | ~80–160°         | ~200–280°        |
| Corredor, paredes perto     | Depende do ambiente | -              |

---

## 3. Plano de testes sugerido

### Teste 1 — Diagnóstico (descobrir 0° e área livre)

1. Coloque o robô em local aberto (longe de paredes).
2. Execute:
   ```bash
   python tools/teste_c1_isolado.py --diagnose --scans 2
   ```
3. Anote:
   - Setores com distância mínima pequena (corpo do robô)
   - Setor com maior distância mínima (provavelmente a frente)
   - Quantidade de graus ocupados vs livres

### Teste 2 — Validar faixa frontal

1. Aponte a **frente** do robô para a parede (ou obstáculo conhecido).
2. Execute:
   ```bash
   python tools/teste_c1_isolado.py --robot-model dev --scans 3
   ```
3. Compare:
   - Distância mínima frontal deve ser menor (perto da parede)
   - Se a “frente” no `--diagnose` não bater com o preset (ex.: dev = 200°), ajuste com `--front-center`:

   ```bash
   python tools/teste_c1_isolado.py --front-deg 200 --front-center 180 --scans 3
   ```

### Teste 3 — Aproximar obstáculo

1. Coloque um objeto à frente (ex.: caixa a ~30 cm).
2. Execute com filtro frontal:
   ```bash
   python tools/teste_c1_isolado.py --robot-model dev --scans 5
   ```
3. Confira se a distância mínima frontal cai quando o objeto se aproxima.

---

## 4. Resumo

| Pergunta                         | Resposta                                                  |
|----------------------------------|-----------------------------------------------------------|
| Onde está o 0°?                  | Direção do cabo preto (referência física). Use `--diagnose` para ver a distribuição angular. |
| Quantos graus sem obstáculo fixo?| Medido com `--diagnose`. Área livre = setores em que distância > limite (ex.: 150 mm). |
| Como testar?                     | 1) `--diagnose` para mapear ângulos; 2) `--robot-model dev` apontando para parede; 3) aproximar obstáculo e validar parada/alerta. |

---

## 5. Próximo passo (Etapa 2 do plano C1)

Depois de validar `--diagnose` e `--robot-model`:

- Definir `--min-stop` e `--min-warn` para parada (ex.: 0,35 m) e alerta (ex.: 0,50 m).
- Integrar o C1 ao fluxo de navegação (módulo `lidar_c1_reader.py`).
