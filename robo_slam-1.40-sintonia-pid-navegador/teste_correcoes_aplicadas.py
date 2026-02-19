#!/usr/bin/env python3
"""
🧪 TESTE ESPECÍFICO: Verificação das correções aplicadas
- Teste 1: Verificar se curvas mantêm diferenças (sem piso)
- Teste 2: Verificar se direções estão corretas (sem inversão)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import time
from src.core.robot_motor_controller import RobotMotorController

def teste_correcoes():
    print("🧪 ===== TESTE DAS CORREÇÕES APLICADAS =====")
    print("🎯 Verificando se problemas de inversão foram resolvidos")
    
    # Inicializa APENAS o controlador de motores (evita conflito PWM)
    motor_controller = RobotMotorController()
    
    print("\n📊 TESTE 1: PRESERVAÇÃO DE DIFERENÇAS (sem piso)")
    print("   🎯 Simulando curva que antes era destruída pelo piso")
    
    # Simula valores que antes eram destruídos pelo piso
    left_tps_original = 17.1
    right_tps_original = 4.3
    
    print(f"   📥 INPUT: left={left_tps_original}, right={right_tps_original}")
    print(f"   📊 DIFERENÇA: {abs(left_tps_original - right_tps_original):.1f} TPS")
    
    # Testa se o controlador preserva as diferenças
    motor_controller.set_target_speed(left_tps_original, right_tps_original)
    
    # Verifica setpoints
    left_setpoint = motor_controller.pid_left.setpoint
    right_setpoint = motor_controller.pid_right.setpoint
    
    print(f"   📤 OUTPUT: left={left_setpoint}, right={right_setpoint}")
    print(f"   📊 DIFERENÇA PRESERVADA: {abs(left_setpoint - right_setpoint):.1f} TPS")
    
    diferenca_preservada = abs(left_setpoint - right_setpoint) > 5.0
    print(f"   ✅ PRESERVAÇÃO: {'SIM' if diferenca_preservada else 'NÃO'}")
    
    time.sleep(2)
    
    print("\n🔄 TESTE 2: LÓGICA DE DIREÇÃO UNIFORMIZADA")
    print("   🎯 Testando comandos básicos de rotação")
    
    # TESTE 2A: Rotação esquerda
    print("   🔄 2A. Rotação ESQUERDA: left=-15, right=+15")
    motor_controller.set_target_speed(-15, 15)
    time.sleep(1)
    
    # TESTE 2B: Rotação direita  
    print("   🔄 2B. Rotação DIREITA: left=+15, right=-15")
    motor_controller.set_target_speed(15, -15)
    time.sleep(1)
    
    # TESTE 2C: Movimento frente
    print("   ➡️ 2C. Movimento FRENTE: left=+20, right=+20")
    motor_controller.set_target_speed(20, 20)
    time.sleep(1)
    
    # Para motores
    motor_controller.stop_motors()
    
    print("\n🧪 ===== RESULTADOS DOS TESTES =====")
    print(f"   1️⃣ Preservação de diferenças: {'✅ OK' if diferenca_preservada else '❌ FALHOU'}")
    print(f"   2️⃣ Comandos de direção: ✅ ENVIADOS (verificar fisicamente)")
    
    if diferenca_preservada:
        print("\n🎉 CORREÇÕES APLICADAS COM SUCESSO!")
        print("   🎯 Piso de velocidade removido - curvas preservadas")
        print("   🔄 Lógica de direção uniformizada")
        print("   🧪 Teste físico necessário para confirmação final")
    else:
        print("\n⚠️ PROBLEMA DETECTADO!")
        print("   🔍 Diferenças ainda não estão sendo preservadas")
    
    return diferenca_preservada

if __name__ == "__main__":
    teste_correcoes() 