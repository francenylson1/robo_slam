# Testes de validação — Correção FRONT_CENTER = 0° (Mar 2026)

**Contexto:** O C1 usa convenção SLAMTEC: **0° = frente** (seta no sensor), 180° = traseira (cabo). Estava configurado com FRONT_CENTER=180°, monitorando a região errada. Ajustado para FRONT_CENTER=0°.

---

## 1. Testes obrigatórios (Raspberry Pi)

### 1.1 Teste isolado com lixeira à frente

**Objetivo:** Confirmar que o obstáculo a ~50 cm é detectado.

```bash
cd ~/robo_slam
source venv/bin/activate
python tools/teste_c1_isolado.py --port /dev/ttyUSB0 --front-deg 180 --scans 5
```

**Passos:**
1. Coloque a lixeira a ~50 cm à frente do robô (na direção da seta do C1).
2. Execute o comando.
3. **Esperado:** Mensagem de PARAR ou ALERTA (obstáculo < 0,45 m ou 0,60 m).
4. **Anotar:** Distância mínima frontal reportada (deve estar em ~0,45–0,55 m).

---

### 1.2 Teste de navegação com obstáculo

**Objetivo:** Robô deve parar antes de atingir a lixeira.

```bash
# Na Raspberry, com main.py rodando
python src/main.py
```

**Passos:**
1. Na interface, escolha um ponto à frente.
2. Coloque a lixeira no caminho, a ~50 cm do robô.
3. Inicie a navegação.
4. **Esperado:** Robô para antes de tocar a lixeira (detecção via lidar_c1_reader).

---

### 1.3 Mapa visual (opcional)

```bash
python tools/c1_mapa_visual.py --port /dev/ttyUSB0 --scans 3 --front-deg 180 --save mapa_pos_correcao.png
```

**Esperado:** Pontos laranja (faixa frontal) na região da lixeira (~0,5 m à frente), com `frontal min` em torno de 0,50 m.

---

## 2. Critérios de sucesso

| Teste | Critério |
|-------|----------|
| Teste 1.1 | Distância mínima frontal ≤ 0,55 m com lixeira a 50 cm |
| Teste 1.2 | Robô para antes de colidir com a lixeira |
| Teste 1.3 | `frontal min` no mapa ~0,50 m com obstáculo à frente |

---

## 3. Se algo falhar

- Conferir se a seta do C1 aponta para a frente do robô.
- Rodar diagnóstico: `python tools/teste_c1_isolado.py --diagnose --scans 3`
- Verificar se o setor 0°–20° mostra ~500 mm com a lixeira à frente.
- Se 0°–20° mostrar valores distantes: possível rotação do sensor na montagem; testar `--front-center` com outros ângulos.
