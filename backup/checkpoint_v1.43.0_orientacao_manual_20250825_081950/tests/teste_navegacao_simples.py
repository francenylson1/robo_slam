#!/usr/bin/env python3
"""
TESTE NAVEGAÇÃO SIMPLES - Isolar problema da sincronização
Testa apenas um comando simples de navegação para identificar onde está a inversão
"""

import sys
import os
import time

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.environment import GPIO_AVAILABLE
from src.core.robot_motor_controller import RobotMotorController

def test_simple_turn_command():
    """Testa comandos simples de giro usando o sistema PID"""
    print("🎯 TESTE NAVEGAÇÃO SIMPLES - Comando de Giro")
    print("🔍 Objetivo: Identificar onde está a inversão na navegação")
    print("=" * 60)
    
    if not GPIO_AVAILABLE:
        print("❌ ERRO: Teste requer Raspberry Pi com GPIO")
        return
    
    print("🚀 Inicializando controlador de motores...")
    motor_controller = RobotMotorController()
    
    try:
        print("✅ Controlador inicializado!")
        
        # TESTE 1: Comando direto set_speed (como botões manuais)
        print("\n" + "="*50)
        print("🔘 TESTE 1: COMANDO DIRETO (como botões manuais)")
        print("   ⚙️  Comando: set_speed(-15, 15) # ESQ-, DIR+")
        print("   🎯 EXPECTATIVA: Robô gira ESQUERDA")
        input("   ▶️  Pressione ENTER para EXECUTAR...")
        
        motor_controller.set_speed(-15, 15)  # Comando direto
        time.sleep(2)
        motor_controller.stop()
        
        print("   ❓ O robô girou para ESQUERDA? (s/n)")
        resultado_direto = input("   ➡️  Resposta: ").lower().strip()
        
        time.sleep(1)
        
        # TESTE 2: Comando via PID (como navegação autônoma)
        print("\n" + "="*50)
        print("🔘 TESTE 2: COMANDO VIA PID (como navegação)")
        print("   ⚙️  Comando: set_target_speed(-15, 15) # ESQ-, DIR+")
        print("   🎯 EXPECTATIVA: Robô gira ESQUERDA (igual ao teste 1)")
        input("   ▶️  Pressione ENTER para EXECUTAR...")
        
        motor_controller.set_target_speed(-15, 15)  # Via PID
        time.sleep(2)
        motor_controller.stop()
        
        print("   ❓ O robô girou para ESQUERDA? (s/n)")
        resultado_pid = input("   ➡️  Resposta: ").lower().strip()
        
        # ANÁLISE DOS RESULTADOS
        print("\n" + "="*60)
        print("📊 DIAGNÓSTICO DO PROBLEMA")
        print("="*60)
        
        direto_ok = resultado_direto.startswith('s')
        pid_ok = resultado_pid.startswith('s')
        
        print(f"📝 Comando DIRETO (set_speed): {'✅ CORRETO' if direto_ok else '❌ INCORRETO'}")
        print(f"📝 Comando PID (set_target_speed): {'✅ CORRETO' if pid_ok else '❌ INCORRETO'}")
        
        if direto_ok and pid_ok:
            print("\n🎉 AMBOS FUNCIONAM CORRETAMENTE!")
            print("   • Problema pode estar em nível mais alto (cinemática)")
            
        elif direto_ok and not pid_ok:
            print("\n🎯 PROBLEMA IDENTIFICADO: SISTEMA PID!")
            print("   • Comandos diretos funcionam ✅")
            print("   • Sistema PID está invertido ❌")
            print("   • SOLUÇÃO: Corrigir apenas o PID, não os comandos diretos")
            
        elif not direto_ok and pid_ok:
            print("\n🤔 SITUAÇÃO INCOMUM:")
            print("   • PID funciona mas comandos diretos não")
            print("   • Verificar hardware ou conexões")
            
        else:
            print("\n❌ AMBOS ESTÃO INCORRETOS:")
            print("   • Problema no hardware ou configuração base")
            
        print("\n💡 PRÓXIMOS PASSOS:")
        if direto_ok and not pid_ok:
            print("   1. Verificar robot_motor_controller.py - sistema PID")
            print("   2. NÃO mexer em comandos diretos (funcionam)")
            print("   3. Focar apenas na camada PID")
        elif direto_ok and pid_ok:
            print("   1. Problema está na cinemática diferencial")
            print("   2. Verificar _move_towards_target()")
            print("   3. Cálculo de left_wheel vs right_wheel")
        
    except Exception as e:
        print(f"❌ ERRO durante teste: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🧹 Finalizando teste...")
        motor_controller.cleanup()
        print("✅ Teste concluído!")

if __name__ == "__main__":
    test_simple_turn_command() 