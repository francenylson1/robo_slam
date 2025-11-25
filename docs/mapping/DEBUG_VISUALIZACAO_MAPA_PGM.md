# 🔍 Debug: Visualização do Mapa PGM

**Data**: 25/11/2025

---

## 🐛 PROBLEMA

Ao carregar um mapa PGM no `main.py`, você vê **"pequenos quadrados pretos"** ao invés da **imagem do mapa 2D**.

---

## 🔍 ANÁLISE

### Possíveis Causas:

1. **Grid sendo desenhado por cima do mapa**
   - O grid pode estar sendo desenhado mesmo quando o PGM está carregado
   - Solução: Grid deve ser desabilitado quando PGM é carregado ✅ (já implementado)

2. **Imagem PGM não está sendo desenhada**
   - A função `_draw_pgm_map` pode não estar sendo chamada
   - A imagem pode estar sendo desenhada mas muito pequena ou fora da área visível
   - Solução: Adicionados logs de debug ✅

3. **Formato PGM com valores invertidos**
   - PGM pode ter `negate: 1` (cores invertidas)
   - Valores: 0 = branco, 255 = preto (invertido)
   - Solução: Verificar e aplicar inversão se necessário ✅

4. **Imagem sendo desenhada mas muito pequena**
   - Escala pode estar muito pequena
   - Mapa pode estar sendo desenhado fora da área visível
   - Solução: Ajuste automático de escala ✅

---

## ✅ CORREÇÕES IMPLEMENTADAS

### 1. Logs de Debug Detalhados

Agora o sistema mostra:
- Se a imagem foi carregada
- Tamanho da imagem original
- Tamanho em metros
- Escala calculada
- Tamanho na tela
- Posição do mapa no widget

### 2. Conversão de Formato

- Converte PGM para RGB32 para garantir compatibilidade
- Verifica e aplica inversão de cores se `negate: 1` no YAML

### 3. Fundo Branco

- Preenche fundo branco antes de desenhar o mapa
- Garante que áreas vazias sejam brancas

### 4. Inversão Vertical

- PGM tem Y crescendo para baixo
- Sistema inverte verticalmente para exibir corretamente

---

## 🔧 COMO TESTAR

### 1. Execute o main.py

```bash
python3 src/main.py
```

### 2. Carregue um Mapa PGM

- Clique em **"🗺️ Carregar PGM"**
- Selecione um mapa da lista

### 3. Verifique os Logs

Você verá logs como:
```
✅ DEBUG: Imagem PGM carregada: 435x412, formato: ...
🔍 DEBUG PGM: Desenhando mapa
   Imagem original: 435x412 pixels
   Tamanho em metros: 21.75m x 20.60m
   Escala: 50.00 pixels/m
   Tamanho na tela: 1087x1030 pixels
   Widget: 784x1200 pixels
   Posição do mapa: (-151, 85)
✅ DEBUG PGM: Mapa desenhado em (-151, 85) com tamanho 1087x1030
```

### 4. Se Ainda Não Funcionar

Verifique:
- **Posição do mapa**: Se `x_pos` ou `y_pos` são negativos, o mapa está fora da área visível
- **Tamanho na tela**: Se `display_width` ou `display_height` são muito pequenos (< 100px), o mapa está muito pequeno
- **Escala**: Se `scale` é muito pequeno (< 10), ajuste manualmente

---

## 🔍 DIAGNÓSTICO

### Se você vê "pequenos quadrados pretos":

1. **São pontos de interesse?**
   - Verifique se há POIs sendo desenhados
   - POIs são desenhados como círculos vermelhos, não quadrados

2. **É o grid?**
   - Verifique se `show_grid` está `False` quando PGM é carregado
   - Grid deve ser desabilitado automaticamente

3. **É a imagem PGM?**
   - Verifique os logs para ver se a imagem está sendo desenhada
   - Verifique se a posição está dentro da área visível

---

## 💡 SOLUÇÃO ALTERNATIVA: Visualizar PNG

Se o PGM não funcionar, você pode visualizar o preview PNG:

```bash
# Abrir preview PNG em visualizador externo
xdg-open data/pipeline_runs/[data]/refinement/mapa_preview.png
```

Ou adicionar suporte para carregar PNG no `main.py` (futuro).

---

## 📋 PRÓXIMOS PASSOS

1. Execute o `main.py` novamente
2. Carregue um mapa PGM
3. Verifique os logs no terminal
4. Me envie os logs para análise

---

**Execute novamente e me envie os logs de debug para análise mais detalhada!**

