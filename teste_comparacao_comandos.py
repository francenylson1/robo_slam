#!/usr/bin/env python3
"""
TESTE COMPARAÇÃO COMANDOS - Compara botões vs navegação autônoma
Identifica exatamente qual diferença está causando a inversão
"""

import sys
import os
import time

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.environment import GPIO_AVAILABLE
from src.core.robot_motor_controller import RobotMotorController

def test_command_comparison():
    """Compara comandos dos botões vs navegação autônoma"""
    print("🔬 TESTE COMPARAÇÃO COMANDOS - Botões vs Navegação")
    print("🎯 Objetivo: Identificar diferença exata entre sistemas")
    print("=" * 60)
    
    if not GPIO_AVAILABLE:
        print("❌ ERRO: Teste requer Raspberry Pi com GPIO")
        return
    
    print("🚀 Inicializando controlador...")
    motor_controller = RobotMotorController()
    
    try:
        print("✅ Controlador inicializado!")
        
        # TESTE 1: Comando do botão ESQUERDA (sabemos que funciona)
        print("\n" + "="*55)
        print("🔘 TESTE 1: COMANDO BOTÃO ESQUERDA (funciona)")
        print("   📋 Interface: set_speed(-30, 30) # ESQ-, DIR+")
        print("   🎯 EXPECTATIVA: Robô gira ESQUERDA")
        input("   ▶️  Pressione ENTER para EXECUTAR...")
        
        motor_controller.set_speed(-30, 30)  # Exato comando do botão
        time.sleep(2)
        motor_controller.stop()
        
        print("   ❓ O robô girou para ESQUERDA? (s/n)")
        resultado_botao = input("   ➡️  Resposta: ").lower().strip()
        
        time.sleep(1)
        
        # TESTE 2: Comando equivalente via set_target_speed 
        print("\n" + "="*55)
        print("🔘 TESTE 2: MESMO COMANDO VIA set_target_speed()")
        print("   📋 Equivalente: set_target_speed(-15, 15) # ESQ-, DIR+")
        print("   🎯 EXPECTATIVA: Robô gira ESQUERDA (igual ao teste 1)")
        input("   ▶️  Pressione ENTER para EXECUTAR...")
        
        motor_controller.set_target_speed(-15, 15)  # Valores equivalentes
        time.sleep(2)
        motor_controller.stop()
        
        print("   ❓ O robô girou para ESQUERDA? (s/n)")
        resultado_pid = input("   ➡️  Resposta: ").lower().strip()
        
        # TESTE 3: Comando inverso via set_target_speed
        print("\n" + "="*55)
        print("🔘 TESTE 3: COMANDO INVERSO VIA set_target_speed()")
        print("   📋 Inverso: set_target_speed(15, -15) # ESQ+, DIR-")
        print("   🎯 EXPECTATIVA: Se há inversão, pode funcionar")
        input("   ▶️  Pressione ENTER para EXECUTAR...")
        
        motor_controller.set_target_speed(15, -15)  # Valores inversos
        time.sleep(2)
        motor_controller.stop()
        
        print("   ❓ O robô girou para ESQUERDA? (s/n)")
        resultado_inverso = input("   ➡️  Resposta: ").lower().strip()
        
        # ANÁLISE DOS RESULTADOS
        print("\n" + "="*60)
        print("📊 ANÁLISE COMPARATIVA DOS COMANDOS")
        print("="*60)
        
        botao_ok = resultado_botao.startswith('s')
        pid_ok = resultado_pid.startswith('s')
        inverso_ok = resultado_inverso.startswith('s')
        
        print(f"📝 Botão set_speed(-30, 30): {'✅ ESQUERDA' if botao_ok else '❌ NÃO ESQUERDA'}")
        print(f"📝 PID set_target_speed(-15, 15): {'✅ ESQUERDA' if pid_ok else '❌ NÃO ESQUERDA'}")
        print(f"📝 PID inverso set_target_speed(15, -15): {'✅ ESQUERDA' if inverso_ok else '❌ NÃO ESQUERDA'}")
        
        print("\n🔍 DIAGNÓSTICO:")
        
        if botao_ok and pid_ok:
            print("   ✅ AMBOS FUNCIONAM: Não há inversão no set_target_speed")
            print("   🎯 Problema deve estar na cinemática diferencial")
            
        elif botao_ok and not pid_ok and inverso_ok:
            print("   🚨 INVERSÃO CONFIRMADA NO set_target_speed!")
            print("   ✅ Solução: Inverter parâmetros left/right no set_target_speed")
            print("   🔧 Correção: Trocar left_tps ↔ right_tps nas chamadas")
            
        elif botao_ok and not pid_ok and not inverso_ok:
            print("   ❓ PID não funciona em nenhuma direção")
            print("   🔍 Problema pode ser configuração PID ou gains")
            
        else:
            print("   🤔 Padrão inesperado - investigação adicional necessária")
            
        print("\n💡 PRÓXIMOS PASSOS:")
        if botao_ok and not pid_ok and inverso_ok:
            print("   1. Implementar troca left ↔ right no set_target_speed")
            print("   2. Testar navegação autônoma completa")
            print("   3. Problema de inversão RESOLVIDO!")
        else:
            print("   1. Investigar outras camadas do sistema")
            print("   2. Verificar configurações PID")
            print("   3. Análise adicional necessária")
        
    except Exception as e:
        print(f"❌ ERRO durante teste: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🧹 Finalizando teste...")
        motor_controller.cleanup()
        print("✅ Teste concluído!")

if __name__ == "__main__":
    test_command_comparison() 