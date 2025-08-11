# 🔧 CORREÇÃO DE INVERSÃO - PRONTA PARA APLICAR

## 🚨 SE A DIREÇÃO AINDA ESTIVER INVERTIDA

Se após testar na Raspberry Pi:
- **Clicar "DIREITA" → Robô gira ESQUERDA**
- **Clicar "ESQUERDA" → Robô gira DIREITA**

Execute este comando para corrigir instantaneamente:

```bash
# 1. Aplique esta correção no arquivo src/interfaces/main_window.py
# Nas linhas ~1025-1030, TROQUE os sinais:

# DE (atual):
self.navigator.motors.set_speed(30, -30)  # ESQ+, DIR- (horário)
self.navigator.motors.set_speed(-30, 30)  # ESQ-, DIR+ (anti-horário)

# PARA (corrigido):  
self.navigator.motors.set_speed(-30, 30)  # ESQ-, DIR+ (horário CORRIGIDO)
self.navigator.motors.set_speed(30, -30)  # ESQ+, DIR- (anti-horário CORRIGIDO)
```

## 🔄 CORREÇÃO AUTOMÁTICA

Execute estes comandos na Raspberry Pi se a direção estiver invertida:

```bash
# 1. Corrigir arquivo
sed -i 's/self.navigator.motors.set_speed(30, -30)  # ESQ+, DIR-/TEMP_MARKER_1/g' src/interfaces/main_window.py
sed -i 's/self.navigator.motors.set_speed(-30, 30)  # ESQ-, DIR+/self.navigator.motors.set_speed(30, -30)  # ESQ+, DIR- (CORRIGIDO)/g' src/interfaces/main_window.py  
sed -i 's/TEMP_MARKER_1/self.navigator.motors.set_speed(-30, 30)  # ESQ-, DIR+ (CORRIGIDO)/g' src/interfaces/main_window.py

# 2. Commit da correção
git add src/interfaces/main_window.py
git commit -m "fix: Corrigir inversão de direção nos controles manuais"

# 3. Testar novamente
python3 src/main.py
```

## 📋 TESTE SISTEMÁTICO

**Sequência de teste**:
1. **Clicar "➡️ DIREITA"** → Robô deve girar **DIREITA** (horário)
2. **Clicar "⬅️ ESQUERDA"** → Robô deve girar **ESQUERDA** (anti-horário) 
3. **Clicar "⬇️ TRÁS"** → Robô deve girar **180°**

**Se direções estiverem certas**: ✅ Sucesso!
**Se direções estiverem trocadas**: Aplicar correção acima

## ⚙️ EXPLICAÇÃO TÉCNICA

**Robô diferencial** (duas rodas):
- **Giro DIREITA**: Roda esquerda gira mais rápido que direita
- **Giro ESQUERDA**: Roda direita gira mais rápido que esquerda

**Comandos corretos**:
- `set_speed(+ESQ, -DIR)` = Giro DIREITA
- `set_speed(-ESQ, +DIR)` = Giro ESQUERDA

**Se invertido**:
- Trocar sinais de ambos os comandos 