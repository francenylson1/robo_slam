# Diagnóstico: obstáculo a 52 cm não detectado pelo C1

**Data:** Março 2026  
**Problema:** Objetos a ~50 cm na frente (lixeira, caixa, materiais/cores diversas) não são detectados. O teste reporta 1,44–1,56 m (mesa lateral / parede).

---

## 1. Hipóteses descartadas

| Hipótese | Motivo |
|----------|--------|
| **Altura** | Objeto 0–55 cm × 42 cm intercepta qualquer plano horizontal. |
| **Material/cor** | Testado com 3 objetos diferentes; nenhum foi detectado. |

---

## 2. Hipótese principal: oclusão pelos parachoques

O C1 está montado **sobre/atrás** dos parachoques (zona 120°–240°, ~105 mm).

Quando o feixe aponta para 180° (frente):
1. O feixe encontra primeiro os **parachoques** (~105 mm).
2. O Lidar retorna só esse valor (primeira reflexão).
3. Filtramos pontos &lt; 220 mm nessa zona → 105 mm é ignorado.
4. Não há retorno para o que está **atrás** dos parachoques (objeto a 50 cm).
5. O mínimo “válido” na faixa frontal passa a ser a mesa/parede lateral (~1,5 m).

Ou seja: o objeto a 50 cm fica **atrás** dos parachoques e o feixe não o alcança.

---

## 3. Passo 1: Rodar com `--breakdown` (objeto na frente)

```bash
python tools/teste_c1_isolado.py --port /dev/ttyUSB0 --front-deg 180 --front-center 180 --breakdown --scans 3
```

**O que checar:**
- Setores 165°–180° e 180°–195° com ~105 mm = parachoques; nada em ~520 mm sugere oclusão.
- Se algum setor mostrar ~520 mm, o objeto está sendo visto.

---

## 4. Passo 2: Exportar pontos brutos

```bash
python tools/teste_c1_isolado.py --port /dev/ttyUSB0 --front-deg 180 --front-center 180 --export-frontal frontal.csv --scans 3
```

Abra `frontal.csv` no Excel/Calc e filtre:
- `distancia_mm` entre 400 e 700 → deve aparecer se o objeto é detectado.
- `angulo_deg` → em quais ângulos há pontos.

---

## 5. Possíveis soluções (após confirmar oclusão)

| Solução | Descrição |
|---------|-----------|
| **Reposicionar o C1** | Subir ou inclinar o sensor para que o feixe passe acima dos parachoques. |
| **Reduzir zona de parachoques** | Se houver ângulos livres entre parachoques e objeto, ajustar `--parachoques-zone`. |
| **Sensor adicional** | Usar ultrassom ou outro sensor para detecção frontal. |

---

## 6. Teste alternativo: centro em 0°

Para verificar se a convenção de ângulo está invertida:

```bash
python tools/teste_c1_isolado.py --port /dev/ttyUSB0 --front-deg 120 --front-center 0 --breakdown --scans 3
```
