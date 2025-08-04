#!/usr/bin/env python3
"""
TESTE CINEMÁTICA DIFERENCIAL - Testa as fórmulas de conversão v,w → left,right
Identifica se o problema está na conversão de velocidades linear/angular
"""

import sys
import os
import time
import math

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.environment import GPIO_AVAILABLE
from src.core.robot_motor_controller import RobotMotorController
from src.core.config import ROBOT_WHEEL_BASE_M, ROBOT_WHEEL_CIRCUMFERENCE_M, TICKS_PER_REVOLUTION

def test_differential_kinematics():
    """Testa a cinemática diferencial diretamente"""
    print("🧮 TESTE CINEMÁTICA DIFERENCIAL - Conversão v,w → left,right")
    print("🎯 Objetivo: Testar fórmulas de conversão da navegação autônoma")
    print("=" * 70)
    
    if not GPIO_AVAILABLE:
        print("❌ ERRO: Teste requer Raspberry Pi com GPIO")
        return
    
    print("🚀 Inicializando controlador...")
    motor_controller = RobotMotorController()
    
    try:
        print("✅ Controlador inicializado!")
        print("\n" + "="*70)
        print("📋 CONFIGURAÇÕES:")
        print(f"• ROBOT_WHEEL_BASE_M = {ROBOT_WHEEL_BASE_M}")
        print(f"• ROBOT_WHEEL_CIRCUMFERENCE_M = {ROBOT_WHEEL_CIRCUMFERENCE_M}")
        print(f"• TICKS_PER_REVOLUTION = {TICKS_PER_REVOLUTION}")
        print("=" * 70)
        
        input("📍 Pressione ENTER quando estiver pronto para começar...")
        
        # TESTE 1: Giro puro ESQUERDA usando cinemática diferencial
        print("\n" + "="*55)
        print("🔘 TESTE 1: GIRO PURO ESQUERDA via CINEMÁTICA DIFERENCIAL")
        print("   📋 Simula exatamente o que a navegação autônoma faz")
        print("   📖 Parâmetros: v=0 (sem movimento linear), w>0 (giro esquerda)")
        print("   🧮 Cinemática Diferencial:")
        
        # Parâmetros para giro puro esquerda
        v = 0.0  # Velocidade linear zero (giro puro)
        w = 1.0  # Velocidade angular para esquerda (rad/s)
        L = ROBOT_WHEEL_BASE_M
        
        print(f"      v = {v} m/s (linear)")
        print(f"      w = {w} rad/s (angular, positivo = esquerda)")
        print(f"      L = {L} m (wheelbase)")
        
        # APLICANDO AS FÓRMULAS CORRIGIDAS
        right_wheel_speed_ms = v - (w * L) / 2.0  # Fórmula corrigida
        left_wheel_speed_ms = v + (w * L) / 2.0   # Fórmula corrigida
        
        print(f"   🔧 FÓRMULAS APLICADAS:")
        print(f"      right_wheel = v - (w*L)/2 = {v} - ({w}*{L})/2 = {right_wheel_speed_ms:.3f} m/s")
        print(f"      left_wheel = v + (w*L)/2 = {v} + ({w}*{L})/2 = {left_wheel_speed_ms:.3f} m/s")
        
        # Convertendo para TPS
        left_tps = (left_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps = (right_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        
        print(f"   ⚙️  CONVERSÃO PARA TPS:")
        print(f"      left_tps = {left_tps:.1f} tps")
        print(f"      right_tps = {right_tps:.1f} tps")
        print(f"   🎯 RESULTADO ESPERADO: Robô deve girar ESQUERDA (anti-horário)")
        input("\n   ▶️  Pressione ENTER para EXECUTAR o teste 1...")
        
        motor_controller.set_target_speed(left_tps, right_tps)
        time.sleep(2.5)
        motor_controller.stop()
        
        print("\n   👀 OBSERVE: Para qual direção o robô girou?")
        print("   🔄 ESQUERDA = anti-horário (sentido contrário dos ponteiros)")
        print("   🔄 DIREITA = horário (mesmo sentido dos ponteiros)")
        print("   ❓ O robô girou para ESQUERDA (anti-horário)? (s/n)")
        resultado_cinematica = input("   ➡️  Sua resposta: ").lower().strip()
        
        time.sleep(2)
        
        # TESTE 2: Comparação com comando direto conhecido
        print("\n" + "="*55)
        print("🔘 TESTE 2: COMPARAÇÃO COM COMANDO DIRETO")
        print("   📋 Usamos o comando que sabemos que funciona")
        print("   ⚙️  Comando: set_target_speed(-15, 15)")
        print("   🎯 RESULTADO ESPERADO: Robô deve girar ESQUERDA igual ao teste 1")
        input("\n   ▶️  Pressione ENTER para EXECUTAR o teste 2...")
        
        motor_controller.set_target_speed(-15, 15)  # Comando que sabemos que funciona
        time.sleep(2.5)
        motor_controller.stop()
        
        print("\n   👀 OBSERVE: Para qual direção o robô girou DESTA VEZ?")
        print("   ❓ O robô girou para ESQUERDA (anti-horário) como no teste 1? (s/n)")
        resultado_direto = input("   ➡️  Sua resposta: ").lower().strip()
        
        # ANÁLISE DOS RESULTADOS
        print("\n" + "="*70)
        print("📊 ANÁLISE DA CINEMÁTICA DIFERENCIAL")
        print("="*70)
        
        cinematica_ok = resultado_cinematica.startswith('s')
        direto_ok = resultado_direto.startswith('s')
        
        print("📝 RESUMO DOS TESTES:")
        print(f"   1️⃣ Cinemática diferencial left={left_tps:.1f}, right={right_tps:.1f}: {'✅ ESQUERDA' if cinematica_ok else '❌ NÃO ESQUERDA'}")
        print(f"   2️⃣ Comando direto left=-15, right=15: {'✅ ESQUERDA' if direto_ok else '❌ NÃO ESQUERDA'}")
        
        print(f"\n🔍 DIAGNÓSTICO DETALHADO:")
        print(f"📊 VALORES CALCULADOS:")
        print(f"   • Cinemática: left_tps={left_tps:.1f}, right_tps={right_tps:.1f}")
        print(f"   • Esperado para ESQUERDA: left negativo, right positivo")
        print(f"   • Sinal correto? left={left_tps:.1f} {'< 0' if left_tps < 0 else '>= 0'}, right={right_tps:.1f} {'> 0' if right_tps > 0 else '<= 0'}")
        
        if cinematica_ok and direto_ok:
            print("\n🎉 RESULTADO: CINEMÁTICA DIFERENCIAL FUNCIONA CORRETAMENTE!")
            print("   ✅ Fórmulas de conversão estão corretas")
            print("   ✅ Problema deve estar em outro lugar")
            print("   🔍 INVESTIGAR: Cálculo de v,w na navegação real")
            
        elif not cinematica_ok and direto_ok:
            print("\n🚨 RESULTADO: PROBLEMA NA CINEMÁTICA DIFERENCIAL!")
            print("   ❌ Fórmulas de conversão estão incorretas")
            print("   ✅ Comando direto funciona")
            print("   🔧 SOLUÇÃO: Corrigir fórmulas de conversão")
            
            # Análise dos sinais
            if left_tps > 0 and right_tps < 0:
                print("   📊 DIAGNÓSTICO: Sinais estão trocados!")
                print("   🔧 CORREÇÃO: Trocar sinais - left deve ser negativo, right positivo")
            elif abs(left_tps) != abs(right_tps):
                print("   📊 DIAGNÓSTICO: Magnitudes incorretas!")
                print("   🔧 CORREÇÃO: Verificar cálculo de velocidades")
                
        else:
            print("\n❓ RESULTADO: Padrão inesperado")
            print("   📋 Investigação manual necessária")
            
        print("\n💡 PRÓXIMOS PASSOS ESPECÍFICOS:")
        if cinematica_ok and direto_ok:
            print("   1. ✅ CINEMÁTICA OK: Investigar cálculo de v,w")
            print("   2. 🔍 VERIFICAR: Como navegação calcula velocidades")
            print("   3. 🧪 TESTAR: Navegação real com debug detalhado")
        elif not cinematica_ok and direto_ok:
            print("   1. 🔧 CORRIGIR: Fórmulas da cinemática diferencial")
            print("   2. 🧪 TESTAR: Navegação após correção")
            print("   3. 🎉 RESOLVER: Problema de sincronização!")
        
    except Exception as e:
        print(f"❌ ERRO durante teste: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🧹 Finalizando teste...")
        motor_controller.cleanup()
        print("✅ Teste concluído!")

if __name__ == "__main__":
    test_differential_kinematics() 