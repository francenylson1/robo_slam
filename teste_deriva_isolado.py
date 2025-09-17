#!/usr/bin/env python3
"""
🔧 TESTE DE ISOLAMENTO: Deriva Lateral vs Cinemática Diferencial

Este teste verifica se o problema de curva para direita é causado por:
1. Correção de deriva lateral (LEFT_MOTOR_CORRECTION_FACTOR = 0.965812)
2. Cinemática diferencial invertida
3. Combinação de ambos

Data: 2025-01-27
Objetivo: Isolar a causa da deriva lateral na navegação em linha reta
"""

import sys
import os
import time
import math

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.environment import GPIO_AVAILABLE
from src.core.robot_motor_controller import RobotMotorController
from src.core.config import ROBOT_WHEEL_BASE_M, ROBOT_WHEEL_CIRCUMFERENCE_M, TICKS_PER_REVOLUTION

def test_drift_isolation():
    """
    Testa navegação em linha reta com diferentes configurações:
    1. Com correção de deriva (atual)
    2. Sem correção de deriva (temporário)
    3. Com cinemática diferencial original
    4. Com cinemática diferencial invertida
    """
    
    print("🔧 TESTE DE ISOLAMENTO: Deriva Lateral")
    print("="*60)
    print("📋 OBJETIVO: Identificar causa da curva para direita")
    print("🎯 MÉTODO: Testar diferentes configurações isoladamente")
    print("⚠️  IMPORTANTE: Observe CUIDADOSAMENTE a direção do movimento")
    
    if not GPIO_AVAILABLE:
        print("❌ ERRO: Este teste precisa ser executado na Raspberry Pi")
        return
    
    motor_controller = RobotMotorController()
    
    try:
        print("\n📍 POSICIONE o robô em linha reta com espaço livre à frente")
        input("📍 Pressione ENTER quando estiver pronto...")
        
        # TESTE 1: Configuração atual (com correção de deriva)
        print("\n" + "="*50)
        print("🔘 TESTE 1: CONFIGURAÇÃO ATUAL (COM CORREÇÃO DE DERIVA)")
        print("   📋 LEFT_MOTOR_CORRECTION_FACTOR = 0.965812")
        print("   📋 RIGHT_MOTOR_CORRECTION_FACTOR = 1.000000")
        print("   📋 Cinemática diferencial: INVERTIDA")
        print("   🎯 COMANDO: Movimento em linha reta (v=0.3, w=0)")
        input("\n   ▶️  Pressione ENTER para EXECUTAR teste 1...")
        
        # Simula comando de linha reta da navegação
        v = 0.3  # m/s
        w = 0.0  # rad/s (sem rotação)
        L = ROBOT_WHEEL_BASE_M
        
        # Cinemática diferencial INVERTIDA (atual)
        left_wheel_speed_ms = v - (w * L) / 2.0
        right_wheel_speed_ms = v + (w * L) / 2.0
        
        left_tps = (left_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps = (right_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        
        print(f"   📊 Velocidades calculadas: left={left_tps:.1f}, right={right_tps:.1f} tps")
        
        # Aplica correção de deriva (como no código atual)
        LEFT_CORRECTION = 0.965812
        RIGHT_CORRECTION = 1.000000
        
        left_tps_corrected = left_tps * LEFT_CORRECTION
        right_tps_corrected = right_tps * RIGHT_CORRECTION
        
        print(f"   📊 Após correção deriva: left={left_tps_corrected:.1f}, right={right_tps_corrected:.1f} tps")
        
        motor_controller.set_target_speed(left_tps, right_tps)  # Usa valores originais (correção é aplicada internamente)
        time.sleep(3.0)
        motor_controller.stop()
        
        print("\n   👀 OBSERVE: O robô foi em linha reta ou curvou?")
        print("   📝 ANOTE: Direção da curva (esquerda/direita/reto)")
        resultado_1 = input("   ➡️  Movimento (reto/esquerda/direita): ").lower().strip()
        
        time.sleep(2)
        
        # TESTE 2: Sem correção de deriva (modificação temporária)
        print("\n" + "="*50)
        print("🔘 TESTE 2: SEM CORREÇÃO DE DERIVA (TEMPORÁRIO)")
        print("   📋 LEFT_MOTOR_CORRECTION_FACTOR = 1.000000 (DESABILITADO)")
        print("   📋 RIGHT_MOTOR_CORRECTION_FACTOR = 1.000000")
        print("   📋 Cinemática diferencial: INVERTIDA")
        print("   🎯 COMANDO: Mesmo movimento em linha reta")
        input("\n   ▶️  Pressione ENTER para EXECUTAR teste 2...")
        
        # Temporariamente modifica os fatores de correção
        original_left_factor = motor_controller.__class__.LEFT_MOTOR_CORRECTION_FACTOR if hasattr(motor_controller.__class__, 'LEFT_MOTOR_CORRECTION_FACTOR') else None
        original_right_factor = motor_controller.__class__.RIGHT_MOTOR_CORRECTION_FACTOR if hasattr(motor_controller.__class__, 'RIGHT_MOTOR_CORRECTION_FACTOR') else None
        
        # Desabilita correção temporariamente
        import src.core.robot_motor_controller as rmc_module
        rmc_module.LEFT_MOTOR_CORRECTION_FACTOR = 1.000000
        rmc_module.RIGHT_MOTOR_CORRECTION_FACTOR = 1.000000
        
        print(f"   📊 Velocidades sem correção: left={left_tps:.1f}, right={right_tps:.1f} tps")
        
        motor_controller.set_target_speed(left_tps, right_tps)
        time.sleep(3.0)
        motor_controller.stop()
        
        print("\n   👀 OBSERVE: O robô foi em linha reta ou curvou DESTA VEZ?")
        print("   📝 ANOTE: Diferença em relação ao teste 1")
        resultado_2 = input("   ➡️  Movimento (reto/esquerda/direita): ").lower().strip()
        
        # Restaura fatores originais
        if original_left_factor is not None:
            rmc_module.LEFT_MOTOR_CORRECTION_FACTOR = original_left_factor
        if original_right_factor is not None:
            rmc_module.RIGHT_MOTOR_CORRECTION_FACTOR = original_right_factor
        
        time.sleep(2)
        
        # TESTE 3: Cinemática diferencial original (não invertida)
        print("\n" + "="*50)
        print("🔘 TESTE 3: CINEMÁTICA DIFERENCIAL ORIGINAL (NÃO INVERTIDA)")
        print("   📋 LEFT_MOTOR_CORRECTION_FACTOR = 0.965812 (RESTAURADO)")
        print("   📋 RIGHT_MOTOR_CORRECTION_FACTOR = 1.000000")
        print("   📋 Cinemática diferencial: ORIGINAL (não invertida)")
        print("   🎯 COMANDO: Mesmo movimento, fórmulas originais")
        input("\n   ▶️  Pressione ENTER para EXECUTAR teste 3...")
        
        # Cinemática diferencial ORIGINAL (antes da inversão)
        left_wheel_speed_ms_orig = v + (w * L) / 2.0  # ORIGINAL
        right_wheel_speed_ms_orig = v - (w * L) / 2.0  # ORIGINAL
        
        left_tps_orig = (left_wheel_speed_ms_orig / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps_orig = (right_wheel_speed_ms_orig / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        
        print(f"   📊 Velocidades (fórmula original): left={left_tps_orig:.1f}, right={right_tps_orig:.1f} tps")
        
        motor_controller.set_target_speed(left_tps_orig, right_tps_orig)
        time.sleep(3.0)
        motor_controller.stop()
        
        print("\n   👀 OBSERVE: O robô foi em linha reta ou curvou com fórmula ORIGINAL?")
        resultado_3 = input("   ➡️  Movimento (reto/esquerda/direita): ").lower().strip()
        
        # ANÁLISE DOS RESULTADOS
        print("\n" + "="*60)
        print("📊 ANÁLISE DOS RESULTADOS")
        print("="*60)
        print(f"🔘 TESTE 1 (atual - com correção deriva + invertida): {resultado_1}")
        print(f"🔘 TESTE 2 (sem correção deriva + invertida): {resultado_2}")
        print(f"🔘 TESTE 3 (com correção deriva + original): {resultado_3}")
        
        print("\n💡 DIAGNÓSTICO:")
        
        if resultado_1 == "direita" and resultado_2 == "reto":
            print("   🎯 CAUSA IDENTIFICADA: Correção de deriva lateral")
            print("   🔧 SOLUÇÃO: Ajustar LEFT_MOTOR_CORRECTION_FACTOR")
            print("   📊 RECOMENDAÇÃO: Aumentar fator de 0.965812 para ~0.98-1.0")
            
        elif resultado_1 == "direita" and resultado_3 == "reto":
            print("   🎯 CAUSA IDENTIFICADA: Cinemática diferencial invertida")
            print("   🔧 SOLUÇÃO: Reverter inversão da cinemática")
            print("   📊 RECOMENDAÇÃO: Usar fórmulas originais")
            
        elif resultado_1 == "direita" and resultado_2 == "direita" and resultado_3 == "direita":
            print("   🎯 CAUSA IDENTIFICADA: Problema mecânico ou calibração")
            print("   🔧 SOLUÇÃO: Verificar alinhamento físico das rodas")
            print("   📊 RECOMENDAÇÃO: Recalibrar ticks por revolução")
            
        else:
            print("   ❓ PADRÃO INESPERADO: Análise manual necessária")
            print("   🔍 INVESTIGAR: Outros fatores podem estar envolvidos")
        
        print("\n🎯 PRÓXIMOS PASSOS:")
        print("   1. 📝 Anotar resultados deste teste")
        print("   2. 🔧 Aplicar correção identificada")
        print("   3. 🧪 Testar navegação completa")
        print("   4. ✅ Validar correção")
        
    except Exception as e:
        print(f"❌ ERRO durante teste: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🧹 Finalizando teste...")
        motor_controller.cleanup()
        print("✅ Teste concluído!")

if __name__ == "__main__":
    test_drift_isolation()