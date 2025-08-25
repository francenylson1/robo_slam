# 🍓 INSTRUÇÕES PARA TESTE NA RASPBERRY PI

## 📅 Data: 19/08/2025 - Sistema de Velocidades Seguras v1.41.04

---

## 🔄 **COMANDOS PARA ATUALIZAR O CÓDIGO NA RASPBERRY PI**

### **1. Acessar a Raspberry Pi e navegar para o projeto:**
```bash
cd ~/robo_slam
```

### **2. Verificar branch atual:**
```bash
git branch
git status
```

### **3. Fazer backup do estado atual (segurança):**
```bash
git stash  # Se houver alterações locais
```

### **4. Atualizar código com as novas funcionalidades:**
```bash
git pull origin v1.41.02-navegacao-autonoma-perfeita-frente-tras-funcionando-faltando-ajustes-finos-botoes-100-140-faltando-botoes-45-graus-por-clique-direita-esquerda
```

### **5. Verificar se tudo foi atualizado:**
```bash
git log --oneline -5
```

---

## 🚀 **COMANDOS PARA EXECUTAR E TESTAR**

### **1. Ativar ambiente virtual (se houver):**
```bash
source venv/bin/activate
```

### **2. Instalar dependências (se necessário):**
```bash
pip install -r requirements.txt
```

### **3. Executar a aplicação:**
```bash
python3 src/main.py
```

**OU**

```bash
cd src && python3 main.py
```

---

## 🧪 **TESTES A REALIZAR**

### **1. TESTE DA INTERFACE:**
✅ Verificar se o novo painel "Controle de Velocidade" aparece  
✅ Testar seletor de perfil: 🐌 Lenta, ⚡ Normal, 🚀 Rápida  
✅ Verificar se o slider de ajuste fino funciona (80% a 120%)  
✅ Observar status de segurança: "🟢 Sistema Seguro"  

### **2. TESTE DOS PERFIS DE VELOCIDADE:**

#### **A) Perfil LENTA (🐌):**
- Selecionar "Lenta (Precisão)" no combo
- Tentar navegação para um POI próximo
- **Esperado**: Movimento mais lento e preciso

#### **B) Perfil NORMAL (⚡):**
- Selecionar "Normal (Balanceado)" no combo  
- Tentar navegação para um POI médio
- **Esperado**: Velocidade balanceada (padrão atual melhorado)

#### **C) Perfil RÁPIDA (🚀):**
- Selecionar "Rápida (Velocidade)" no combo
- Tentar navegação para um POI distante
- **Esperado**: Movimento mais rápido (mas ainda seguro ≤15%)

### **3. TESTE DE SEGURANÇA:**
✅ Monitor se aparece "🔴 AVISO" se houver excesso de potência  
✅ Verificar auto-redução para perfil "Lenta" em caso de violação  
✅ Confirmar que nunca excede 15% de potência dos motores  

### **4. TESTE DE COMPATIBILIDADE:**
✅ Controle manual deve continuar funcionando normalmente  
✅ Navegação automática deve funcionar melhor que antes  
✅ Giros manuais (45°/90°) ainda podem ter problema (será próxima fase)  

---

## 📊 **MONITORAMENTO DURANTE TESTES**

### **Logs importantes a observar:**
```
🎯 PID Profile 'normal' aplicado: Kp=0.35, Ki=0.25, Kd=0.03, Limits=(-12, 12), TPS=35
✅ Perfil de velocidade alterado para 'fast': Velocidade máxima - trajetos longos
🟢 Sistema Seguro (fast)
```

### **Sinais de alerta (se aparecerem):**
```
⚠️ AVISO SEGURANÇA: Potência X% excede limite de 15%
🚨 PARADA DE EMERGÊNCIA: Potência X% acima do limite por 0.2s!
🚨 Reduzindo automaticamente para perfil 'slow' por segurança.
```

---

## 🔍 **COMANDOS DE DEBUG (se necessário)**

### **1. Testar apenas as configurações:**
```bash
python3 -c "from src.core.config import PID_PROFILES, SPEED_SLOW_TPS, SPEED_NORMAL_TPS, SPEED_FAST_TPS; print('Velocidades:', SPEED_SLOW_TPS, SPEED_NORMAL_TPS, SPEED_FAST_TPS); print('Perfis:', list(PID_PROFILES.keys()))"
```

### **2. Testar controlador de motores:**
```bash
python3 -c "from src.core.robot_motor_controller import RobotMotorController; controller = RobotMotorController(); profile = controller.get_current_speed_profile(); print('Perfil atual:', profile)"
```

### **3. Verificar logs em tempo real:**
```bash
tail -f logs/robot.log  # Se houver arquivo de log
```

---

## 🚨 **PROTOCOLO DE SEGURANÇA DURANTE TESTES**

### **⚠️ IMPORTANTE:**
1. **Área livre**: Teste em área ampla e sem obstáculos
2. **Supervisão constante**: Mantenha botão de parada sempre acessível
3. **Potência monitorada**: Sistema deve avisar se exceder 15%
4. **Parada imediata**: Se houver comportamento estranho, usar botão "Parar"

### **🛑 SE ALGO DER ERRADO:**
```bash
# Voltar para estado anterior seguro:
git checkout v1.41.03-checkpoint-antes-melhorias-velocidade-pid
python3 src/main.py
```

---

## 📈 **RESULTADOS ESPERADOS**

### **✅ MELHORIAS VISÍVEIS:**
- Interface mais intuitiva com controles claros
- Velocidades de navegação mais rápidas (perfis Normal/Rápida)
- Maior precisão na aproximação final (perfil Lenta)
- Sistema de segurança transparente com feedback visual

### **❓ AINDA PENDENTE (próxima fase):**
- Giros de 45°/90°/180° ainda podem estar lentos/travados
- Boost de torque para giros será implementado na Fase 2

---

**📞 SUPORTE:** Se houver problemas, documente os logs de erro e podemos investigar remotamente.

**🎯 OBJETIVO:** Validar que o sistema de velocidades está funcionando e é mais eficiente que antes, mantendo total segurança.
