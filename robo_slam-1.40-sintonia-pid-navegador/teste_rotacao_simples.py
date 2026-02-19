#!/usr/bin/env python3
"""
TESTE SIMPLES - Diagnóstico de Rotação Física
Script focado apenas em comandos de rotação para identificar inversão
"""

import sys
import os
import time

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.environment import GPIO_AVAILABLE
from src.core.robot_motor_controller import RobotMotorController

def main():
    print("🔄 TESTE SIMPLES - ROTAÇÃO FÍSICA DO ROBÔ")
    print("=" * 50)
    
    if not GPIO_AVAILABLE:
        print("❌ ERRO: Requer Raspberry Pi com GPIO")
        return
    
    print("🚀 Inicializando controlador...")
    motor_controller = RobotMotorController()
    
    try:
        print("✅ Pronto! Posicione o robô em local seguro.")
        input("📍 Pressione ENTER para começar...")
        
        # TESTE 1: Comando para ESQUERDA
        print("\n" + "="*50)
        print("🔄 TESTE 1: COMANDO PARA ESQUERDA")
        print("   🎯 EXPECTATIVA: Robô deve girar para ESQUERDA (anti-horário)")
        print("   ⚙️  COMANDO FÍSICO: Motor direito FRENTE + Motor esquerdo TRÁS")
        input("   ▶️  Pressione ENTER para EXECUTAR...")
        
        motor_controller.set_target_speed(-10, 10)  # Esquerdo reverso, direito frente
        time.sleep(3)
        motor_controller.stop_motors()
        
        print("   ✅ COMANDO EXECUTADO!")
        print("   ❓ O robô girou para ESQUERDA? (s/n)")
        resposta1 = input("   ➡️  Sua resposta: ").lower().strip()
        
        # TESTE 2: Comando para DIREITA
        print("\n" + "="*50)
        print("🔄 TESTE 2: COMANDO PARA DIREITA")
        print("   🎯 EXPECTATIVA: Robô deve girar para DIREITA (horário)")
        print("   ⚙️  COMANDO FÍSICO: Motor esquerdo FRENTE + Motor direito TRÁS")
        input("   ▶️  Pressione ENTER para EXECUTAR...")
        
        motor_controller.set_target_speed(10, -10)  # Esquerdo frente, direito reverso
        time.sleep(3)
        motor_controller.stop_motors()
        
        print("   ✅ COMANDO EXECUTADO!")
        print("   ❓ O robô girou para DIREITA? (s/n)")
        resposta2 = input("   ➡️  Sua resposta: ").lower().strip()
        
        # ANÁLISE DOS RESULTADOS
        print("\n" + "="*50)
        print("📊 ANÁLISE DOS RESULTADOS")
        print("="*50)
        
        if resposta1.startswith('s') and resposta2.startswith('s'):
            print("✅ RESULTADO: Comandos físicos estão CORRETOS")
            print("   📝 Comando ESQUERDA → Movimento para esquerda: ✅")
            print("   📝 Comando DIREITA → Movimento para direita: ✅")
            print("   🔍 CONCLUSÃO: O problema está na interface, não no hardware")
        elif resposta1.startswith('n') and resposta2.startswith('n'):
            print("🔄 RESULTADO: Comandos físicos estão INVERTIDOS")
            print("   📝 Comando ESQUERDA → Movimento para direita: ❌")
            print("   📝 Comando DIREITA → Movimento para esquerda: ❌")
            print("   🔍 CONCLUSÃO: Inversão nos comandos físicos dos motores")
        else:
            print("⚠️  RESULTADO: Comportamento inconsistente")
            print(f"   📝 Comando ESQUERDA funcionou: {'✅' if resposta1.startswith('s') else '❌'}")
            print(f"   📝 Comando DIREITA funcionou: {'✅' if resposta2.startswith('s') else '❌'}")
            print("   🔍 CONCLUSÃO: Verifique hardware ou conexões")
        
        print("\n🎯 PRÓXIMOS PASSOS:")
        if resposta1.startswith('s') and resposta2.startswith('s'):
            print("   1. O hardware está OK - investigar lógica da interface")
            print("   2. Verificar como a interface converte cliques em comandos")
            print("   3. Comparar orientação do robô na interface vs. física")
        else:
            print("   1. Corrigir lógica de direção nos motores físicos")
            print("   2. Verificar fiação dos motores")
            print("   3. Ajustar robot_motor_controller.py se necessário")
            
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
    
    finally:
        print("\n🧹 Finalizando...")
        motor_controller.cleanup()
        print("✅ Teste concluído!")

if __name__ == "__main__":
    main() 