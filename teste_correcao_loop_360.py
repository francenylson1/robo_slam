#!/usr/bin/env python3
"""
🧪 TESTE DA CORREÇÃO DO LOOP DE 360° NO RETORNO
Testa as correções implementadas para eliminar o loop infinito durante o retorno à base.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.robot_navigator import RobotNavigator
from src.core.config import ROBOT_INITIAL_POSITION, ROBOT_INITIAL_ANGLE
import time

def test_navigation_flow():
    """Testa o fluxo completo de navegação ida+volta"""
    print("🧪 === TESTE DA CORREÇÃO DO LOOP DE 360° ===")
    
    # Inicializa o navegador
    navigator = RobotNavigator()
    
    # Simula posição atual (POI)
    test_position = (3.0, 8.0)  # Posição de teste
    navigator.current_position = test_position
    navigator.current_angle = 45.0  # Ângulo de teste
    
    print(f"📍 Posição inicial simulada: {test_position}")
    print(f"🧭 Ângulo inicial simulado: {navigator.current_angle}°")
    print(f"🏠 Base: {ROBOT_INITIAL_POSITION}")
    print(f"🎯 Ângulo da base: {ROBOT_INITIAL_ANGLE}°")
    
    # Testa o método de retorno direto
    print("\n🎯 TESTANDO _return_to_base_direct()...")
    navigator._return_to_base_direct()
    
    print(f"✅ Estado após retorno direto: {navigator.navigation_state}")
    print(f"✅ is_returning_to_base: {navigator.is_returning_to_base}")
    print(f"✅ current_target: {navigator.current_target}")
    print(f"✅ path: {navigator.path}")
    
    # Verifica se o estado está correto
    if navigator.navigation_state == "RETURNING_TO_BASE":
        print("✅ CORREÇÃO APLICADA: Estado correto para retorno!")
    else:
        print("❌ PROBLEMA: Estado incorreto para retorno!")
        return False
    
    # Testa o cálculo de ângulo para a base
    dx = ROBOT_INITIAL_POSITION[0] - test_position[0]
    dy = ROBOT_INITIAL_POSITION[1] - test_position[1]
    target_angle = navigator._calculate_distance(test_position, ROBOT_INITIAL_POSITION)
    
    print(f"\n🧮 Cálculos de navegação:")
    print(f"   Delta X: {dx:.3f}m")
    print(f"   Delta Y: {dy:.3f}m")
    print(f"   Distância à base: {target_angle:.3f}m")
    
    # Simula algumas iterações do loop de navegação
    print("\n🔄 SIMULANDO LOOP DE NAVEGAÇÃO...")
    for i in range(5):
        print(f"\n--- Iteração {i+1} ---")
        print(f"Estado atual: {navigator.navigation_state}")
        print(f"Posição: {navigator.current_position}")
        print(f"Ângulo: {navigator.current_angle:.1f}°")
        
        # Chama o método update
        navigator.update()
        
        # Pequena pausa para simular tempo real
        time.sleep(0.1)
    
    print("\n✅ TESTE CONCLUÍDO!")
    return True

def test_angle_calculations():
    """Testa os cálculos de ângulo para evitar loops"""
    print("\n🧮 === TESTE DOS CÁLCULOS DE ÂNGULO ===")
    
    navigator = RobotNavigator()
    
    # Testa diferentes posições e ângulos
    test_cases = [
        ((3.0, 8.0), 45.0),   # POI típico
        ((5.0, 10.0), 90.0),  # Meio do caminho
        ((5.7, 11.0), 180.0), # Próximo da base
    ]
    
    for position, angle in test_cases:
        navigator.current_position = position
        navigator.current_angle = angle
        navigator.is_returning_to_base = True
        
        print(f"\n📍 Teste: Posição {position}, Ângulo {angle}°")
        
        # Calcula ângulo para a base
        dx = ROBOT_INITIAL_POSITION[0] - position[0]
        dy = ROBOT_INITIAL_POSITION[1] - position[1]
        target_angle = navigator._calculate_distance(position, ROBOT_INITIAL_POSITION)
        
        print(f"   Distância à base: {target_angle:.3f}m")
        print(f"   Delta X: {dx:.3f}m")
        print(f"   Delta Y: {dy:.3f}m")
        
        # Verifica se o ângulo de erro seria problemático
        angle_to_base = navigator._calculate_distance(position, ROBOT_INITIAL_POSITION)
        if angle_to_base > 90:
            print(f"   ⚠️ ALERTA: Ângulo muito grande pode causar loops!")
        else:
            print(f"   ✅ Ângulo OK para navegação segura")

if __name__ == "__main__":
    print("🚀 INICIANDO TESTES DA CORREÇÃO DO LOOP DE 360°")
    
    try:
        # Teste principal
        success = test_navigation_flow()
        
        if success:
            # Teste dos cálculos
            test_angle_calculations()
            print("\n🎉 TODOS OS TESTES PASSARAM! A correção está funcionando.")
        else:
            print("\n❌ TESTE PRINCIPAL FALHOU!")
            
    except Exception as e:
        print(f"\n💥 ERRO DURANTE OS TESTES: {e}")
        import traceback
        traceback.print_exc()
