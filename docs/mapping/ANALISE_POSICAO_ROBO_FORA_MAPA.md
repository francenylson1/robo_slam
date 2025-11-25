# 🔍 Análise: Robô Aparecendo Fora do Mapa

**Data**: 25/11/2025

---

## 🐛 PROBLEMA IDENTIFICADO

O robô está aparecendo **fora do quadro do mapa** mesmo com a posição configurada como `(5.7, 11.0)`.

---

## 🔍 CAUSA PROVÁVEL

### 1. Origem do Mapa PGM
O mapa PGM tem uma **origem** definida no arquivo YAML (ex: `origin: [-4.65, -3.64, 0.0]`).

**Significado:**
- A origem define onde o pixel (0,0) do PGM está no sistema de coordenadas do mundo
- Se a origem é `(-4.65, -3.64)`, o mapa cobre aproximadamente:
  - X: de -4.65m a (largura_em_pixels * resolução - 4.65)m
  - Y: de -3.64m a (altura_em_pixels * resolução - 3.64)m

### 2. Posição do Robô
A posição `(5.7, 11.0)` pode estar **fora dos limites do mapa** se:
- O mapa não cobre essa área
- A origem do mapa é diferente do esperado

---

## ✅ CORREÇÕES APLICADAS

### 1. Logs Detalhados Adicionados
Agora o sistema mostra:
- Origem do mapa
- Limites do mapa (X e Y)
- Posição do robô
- Se o robô está dentro ou fora do mapa

### 2. Verificação ao Carregar Mapa
Quando um mapa PGM é carregado, o sistema verifica se a posição do robô está dentro dos limites e mostra um aviso se estiver fora.

### 3. Verificação ao Desenhar Robô
Ao desenhar o robô, o sistema mostra logs detalhados sobre:
- Posição do robô em metros
- Origem e resolução do mapa
- Limites do mapa
- Se o robô está visível na tela

---

## 📋 COMO VERIFICAR

### 1. Execute a Interface
```bash
python src/main.py
```

### 2. Carregue um Mapa PGM
- Selecione um arquivo `.pgm` quando solicitado

### 3. Verifique os Logs
Procure por:
```
🔍 DEBUG MAPA: Mapa carregado - Origem: (...), Tamanho: ...x...m
🔍 DEBUG MAPA: Limites: X=[...], Y=[...]m
🔍 DEBUG MAPA: Posição do robô: (5.70, 11.00)m
```

### 4. Se o Robô Estiver Fora
Você verá:
```
⚠️  AVISO: Posição do robô (5.70, 11.00)m está FORA do mapa!
⚠️  AVISO: O mapa cobre X=[...], Y=[...]m
💡 SUGESTÃO: Ajuste ROBOT_INITIAL_POSITION em config.py para uma posição dentro do mapa
```

---

## 🔧 SOLUÇÃO

### Opção 1: Ajustar Posição do Robô
Se o mapa não cobre `(5.7, 11.0)`, ajuste `ROBOT_INITIAL_POSITION` em `config.py` para uma posição dentro do mapa.

**Exemplo:**
Se o mapa cobre X=[-4.65, 1.85]m e Y=[-3.64, 1.71]m:
```python
ROBOT_INITIAL_POSITION = (0.0, 0.0)  # Centro do mapa
```

### Opção 2: Usar POI "Base"
1. Crie um POI chamado "base" clicando dentro do mapa
2. Quando perguntar, confirme para usar como posição inicial
3. O sistema atualizará `config.py` automaticamente

---

## 📊 EXEMPLO DE LOGS ESPERADOS

### Quando o Robô Está Dentro do Mapa:
```
🔍 DEBUG MAPA: Mapa carregado - Origem: (-4.65, -3.64), Tamanho: 6.50x5.35m
🔍 DEBUG MAPA: Limites: X=[-4.65, 1.85]m, Y=[-3.64, 1.71]m
🔍 DEBUG MAPA: Posição do robô: (0.00, 0.00)m
✅ Robô está dentro do mapa
```

### Quando o Robô Está Fora do Mapa:
```
🔍 DEBUG MAPA: Mapa carregado - Origem: (-4.65, -3.64), Tamanho: 6.50x5.35m
🔍 DEBUG MAPA: Limites: X=[-4.65, 1.85]m, Y=[-3.64, 1.71]m
🔍 DEBUG MAPA: Posição do robô: (5.70, 11.00)m
⚠️  AVISO: Posição do robô (5.70, 11.00)m está FORA do mapa!
⚠️  AVISO: O mapa cobre X=[-4.65, 1.85]m, Y=[-3.64, 1.71]m
💡 SUGESTÃO: Ajuste ROBOT_INITIAL_POSITION em config.py para uma posição dentro do mapa
```

---

## 🎯 PRÓXIMOS PASSOS

1. **Execute a interface** e carregue um mapa
2. **Verifique os logs** para ver os limites do mapa
3. **Ajuste a posição** do robô se necessário:
   - Opção A: Edite `config.py` manualmente
   - Opção B: Crie POI "base" dentro do mapa

---

**Execute a interface e verifique os logs para identificar o problema!** 🔍

