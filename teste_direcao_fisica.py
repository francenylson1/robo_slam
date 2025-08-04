#!/usr/bin/env python3
"""
SCRIPT DE DIAGNÓSTICO - Teste de Direção Robô Físico
Este script testa apenas o robô físico para identificar problemas de direção
sem interferência da interface gráfica.
"""

import sys
import os
import time

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.environment import GPIO_AVAILABLE
from src.core.robot_motor_controller import RobotMotorController

def print_header():
    """Imprime cabeçalho do teste"""
    print("=" * 60)
    print("🤖 TESTE DE DIAGNÓSTICO - DIREÇÃO DO ROBÔ FÍSICO")
    print("=" * 60)
    print(f"🔧 GPIO Disponível: {GPIO_AVAILABLE}")
    print(f"⚙️  Objetivo: Verificar se comandos físicos correspondem às direções")
    print("=" * 60)

def test_individual_motors(motor_controller):
    """Testa cada motor individualmente"""
    print("\n🔍 TESTE 1: MOTORES INDIVIDUAIS")
    print("-" * 40)
    
    # Teste motor esquerdo para frente
    print("📍 Testando MOTOR ESQUERDO - PARA FRENTE")
    print("   👁️  Observe: O robô deve se mover para FRENTE-ESQUERDA")
    motor_controller.set_target_speed(10, 0)  # Só motor esquerdo
    time.sleep(3)
    motor_controller.stop_motors()
    input("   ✅ Pressione ENTER para continuar...")
    
    # Teste motor esquerdo para trás
    print("\n📍 Testando MOTOR ESQUERDO - PARA TRÁS")
    print("   👁️  Observe: O robô deve se mover para TRÁS-ESQUERDA")
    motor_controller.set_target_speed(-10, 0)  # Motor esquerdo reverso
    time.sleep(3)
    motor_controller.stop_motors()
    input("   ✅ Pressione ENTER para continuar...")
    
    # Teste motor direito para frente
    print("\n📍 Testando MOTOR DIREITO - PARA FRENTE")
    print("   👁️  Observe: O robô deve se mover para FRENTE-DIREITA")
    motor_controller.set_target_speed(0, 10)  # Só motor direito
    time.sleep(3)
    motor_controller.stop_motors()
    input("   ✅ Pressione ENTER para continuar...")
    
    # Teste motor direito para trás
    print("\n📍 Testando MOTOR DIREITO - PARA TRÁS")
    print("   👁️  Observe: O robô deve se mover para TRÁS-DIREITA")
    motor_controller.set_target_speed(0, -10)  # Motor direito reverso
    time.sleep(3)
    motor_controller.stop_motors()
    input("   ✅ Pressione ENTER para continuar...")

def test_rotation_commands(motor_controller):
    """Testa comandos de rotação específicos"""
    print("\n🔄 TESTE 2: COMANDOS DE ROTAÇÃO")
    print("-" * 40)
    
    # Comando para girar para ESQUERDA (sentido anti-horário)
    print("📍 Comando: GIRAR PARA ESQUERDA (Anti-horário)")
    print("   🤖 FÍSICO: Motor direito para FRENTE + Motor esquerdo PARADO/REVERSO")
    print("   👁️  Observe: O robô deve girar para a ESQUERDA")
    motor_controller.set_target_speed(-8, 8)  # Esquerdo reverso, direito frente
    time.sleep(4)
    motor_controller.stop_motors()
    print("   ✅ COMANDO FÍSICO EXECUTADO: ESQUERDA")
    input("   ➡️  Pressione ENTER para próximo teste...")
    
    # Comando para girar para DIREITA (sentido horário)
    print("\n📍 Comando: GIRAR PARA DIREITA (Horário)")
    print("   🤖 FÍSICO: Motor esquerdo para FRENTE + Motor direito PARADO/REVERSO")
    print("   👁️  Observe: O robô deve girar para a DIREITA")
    motor_controller.set_target_speed(8, -8)  # Esquerdo frente, direito reverso
    time.sleep(4)
    motor_controller.stop_motors()
    print("   ✅ COMANDO FÍSICO EXECUTADO: DIREITA")
    input("   ➡️  Pressione ENTER para próximo teste...")

def test_forward_backward(motor_controller):
    """Testa movimento para frente e para trás"""
    print("\n⬆️ TESTE 3: MOVIMENTO LINEAR")
    print("-" * 40)
    
    # Frente
    print("📍 Comando: MOVER PARA FRENTE")
    print("   🤖 FÍSICO: Ambos motores para FRENTE")
    print("   👁️  Observe: O robô deve se mover para FRENTE")
    motor_controller.set_target_speed(12, 12)
    time.sleep(3)
    motor_controller.stop_motors()
    print("   ✅ COMANDO FÍSICO EXECUTADO: FRENTE")
    input("   ➡️  Pressione ENTER para teste reverso...")
    
    # Trás
    print("\n📍 Comando: MOVER PARA TRÁS")
    print("   🤖 FÍSICO: Ambos motores para TRÁS")
    print("   👁️  Observe: O robô deve se mover para TRÁS")
    motor_controller.set_target_speed(-12, -12)
    time.sleep(3)
    motor_controller.stop_motors()
    print("   ✅ COMANDO FÍSICO EXECUTADO: TRÁS")
    input("   ➡️  Pressione ENTER para finalizar...")

def test_physical_robot():
    """Função principal do teste"""
    print_header()
    
    if not GPIO_AVAILABLE:
        print("❌ ERRO: Este teste requer hardware GPIO (Raspberry Pi)")
        print("   Execute este script na Raspberry Pi para testar o robô físico")
        return
    
    print("🚀 Inicializando controlador de motores...")
    motor_controller = RobotMotorController()
    
    try:
        print("✅ Controlador inicializado com sucesso!")
        print("\n📋 INSTRUÇÕES IMPORTANTES:")
        print("   1. Certifique-se que o robô está em área segura")
        print("   2. Observe ATENTAMENTE a direção real dos movimentos")
        print("   3. Compare o que observa com os prints na tela")
        print("   4. Anote qualquer discrepância entre comando e movimento real")
        
        input("\n🎯 Pressione ENTER quando estiver pronto para iniciar os testes...")
        
        # Executa todos os testes
        test_individual_motors(motor_controller)
        test_rotation_commands(motor_controller)
        test_forward_backward(motor_controller)
        
        print("\n" + "=" * 60)
        print("✅ TESTES CONCLUÍDOS!")
        print("=" * 60)
        print("📝 RELATÓRIO:")
        print("   • Anote se os comandos físicos correspondem ao movimento observado")
        print("   • Se ESQUERDA física = movimento para direita → Há inversão")
        print("   • Se DIREITA física = movimento para esquerda → Há inversão")
        print("   • Compare com o comportamento da interface gráfica")
        
    except Exception as e:
        print(f"❌ ERRO durante teste: {str(e)}")
    
    finally:
        print("\n🧹 Limpando recursos...")
        motor_controller.cleanup()
        print("✅ Cleanup concluído!")

if __name__ == "__main__":
    test_physical_robot() 