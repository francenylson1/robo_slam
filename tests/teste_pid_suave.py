#!/usr/bin/env python3
"""
TESTE PID SUAVE - Correção de Vibração e Instabilidade
Data: 2025-01-27

PROBLEMA IDENTIFICADO:
- Robô vibra muito e desvia 45° para direita na navegação autônoma
- Botões manuais funcionam corretamente (esquerda=esquerda, direita=direita)
- PID atual muito agressivo: Kp=0.35-0.40, Ki=0.25-0.30, Kd=0.03-0.05

CAUSAS PROVÁVEIS:
1. Parâmetros PID muito altos causando oscilação
2. Múltiplas correções conflitantes (fatores + wheelbase + cinemática)
3. Frequência de controle muito alta (20Hz) para motores potentes

SOLUÇÃO PROPOSTA:
- PID mais suave: Kp reduzido 50%, Ki reduzido 60%, Kd reduzido 40%
- Frequência de controle reduzida para 10Hz
- Teste temporário sem fatores de correção
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.core.config import *

# ===== CONFIGURAÇÕES PID SUAVES =====
# Redução significativa para eliminar vibração
PID_PROFILES_SUAVE = {
    'slow': {
        'Kp': 0.20,  # Reduzido de 0.40 (50% menos)
        'Ki': 0.12,  # Reduzido de 0.30 (60% menos)
        'Kd': 0.03,  # Reduzido de 0.05 (40% menos)
        'output_limits': (-8, 8),
        'tps': SPEED_SLOW_TPS,
        'description': 'PID SUAVE - Precisão sem vibração'
    },
    'normal': {
        'Kp': 0.18,  # Reduzido de 0.35 (48% menos)
        'Ki': 0.10,  # Reduzido de 0.25 (60% menos)
        'Kd': 0.02,  # Reduzido de 0.03 (33% menos)
        'output_limits': (-12, 12),
        'tps': SPEED_NORMAL_TPS,
        'description': 'PID SUAVE - Navegação estável'
    },
    'fast': {
        'Kp': 0.15,  # Reduzido de 0.30 (50% menos)
        'Ki': 0.08,  # Reduzido de 0.20 (60% menos)
        'Kd': 0.01,  # Mantido (já baixo)
        'output_limits': (-15, 15),
        'tps': SPEED_FAST_TPS,
        'description': 'PID SUAVE - Velocidade controlada'
    }
}

# ===== TESTE SEM FATORES DE CORREÇÃO =====
# Para isolar se o problema é dos fatores ou do PID
LEFT_MOTOR_CORRECTION_FACTOR_TEST = 1.000000   # SEM correção
RIGHT_MOTOR_CORRECTION_FACTOR_TEST = 1.000000  # SEM correção

# ===== FREQUÊNCIA DE CONTROLE REDUZIDA =====
PID_CONTROL_FREQUENCY_HZ = 10  # Reduzido de 20Hz para 10Hz
PID_CONTROL_SLEEP_TIME = 0.1   # 100ms em vez de 50ms

# ===== INSTRUÇÕES DE TESTE =====
print("""\n🔧 TESTE PID SUAVE - INSTRUÇÕES:

1. BACKUP DO ARQUIVO ORIGINAL:
   cp src/core/config.py src/core/config.py.backup_antes_pid_suave

2. APLICAR CONFIGURAÇÕES SUAVES:
   - Substituir PID_PROFILES por PID_PROFILES_SUAVE
   - Comentar fatores de correção temporariamente
   - Reduzir frequência de controle PID

3. TESTAR NA RASPBERRY:
   - Navegação em linha reta (deve eliminar vibração)
   - Verificar se ainda desvia 45° para direita
   - Testar botões manuais (devem continuar funcionando)

4. ANÁLISE DOS RESULTADOS:
   - Se vibração parar: PID era muito agressivo
   - Se ainda desviar 45°: Problema na cinemática ou wheelbase
   - Se botões pararem: Problema nos fatores de correção

5. AJUSTES INCREMENTAIS:
   - Se muito lento: Aumentar Kp gradualmente (+0.02)
   - Se ainda vibrar: Reduzir Ki mais (-0.02)
   - Se impreciso: Ajustar Kd (+0.005)

⚠️  IMPORTANTE:
- Testar sempre em área segura
- Manter botão de emergência próximo
- Fazer backup antes de qualquer alteração
- Não exceder 15% de potência dos motores

📊 VALORES COMPARATIVOS:
   ORIGINAL vs SUAVE:
   Kp: 0.35 -> 0.18 (48% redução)
   Ki: 0.25 -> 0.10 (60% redução)
   Kd: 0.03 -> 0.02 (33% redução)
   Freq: 20Hz -> 10Hz (50% redução)
""")

if __name__ == "__main__":
    print("\n✅ Configurações PID suaves carregadas com sucesso!")
    print(f"\n📋 Perfis disponíveis: {list(PID_PROFILES_SUAVE.keys())}")
    
    for profile_name, profile in PID_PROFILES_SUAVE.items():
        print(f"\n🔧 {profile_name.upper()}:")
        print(f"   Kp: {profile['Kp']:.2f}")
        print(f"   Ki: {profile['Ki']:.2f}")
        print(f"   Kd: {profile['Kd']:.3f}")
        print(f"   Limites: {profile['output_limits']}")
        print(f"   Descrição: {profile['description']}")