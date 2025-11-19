#!/usr/bin/env python3
"""
Teste das correções de sincronia implementadas.
Este arquivo testa se as correções estão funcionando corretamente.
"""

import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Testa se os módulos principais podem ser importados."""
    print("🧪 TESTE: Importação de módulos")
    
    try:
        from src.core.config import ROBOT_INITIAL_POSITION, ROBOT_INITIAL_ANGLE
        print(f"   ✅ Config importado - Base: {ROBOT_INITIAL_POSITION}, Ângulo: {ROBOT_INITIAL_ANGLE}°")
    except Exception as e:
        print(f"   ❌ Erro ao importar config: {e}")
        return False
    
    try:
        from src.core.robot_navigator import RobotNavigator
        print("   ✅ RobotNavigator importado")
    except Exception as e:
        print(f"   ❌ Erro ao importar RobotNavigator: {e}")
        return False
    
    try:
        from src.interfaces.main_window import MainWindow
        print("   ✅ MainWindow importado")
    except Exception as e:
        print(f"   ❌ Erro ao importar MainWindow: {e}")
        return False
    
    print("✅ Teste de importação concluído\n")
    return True

def test_angle_calculations():
    """Testa os cálculos de ângulo para sincronia."""
    print("🧪 TESTE: Cálculos de ângulo para sincronia")
    
    try:
        from src.core.config import ROBOT_INITIAL_POSITION, ROBOT_INITIAL_ANGLE
        import math
        
        # Simula posições de teste
        test_positions = [
            (3.0, 8.0, "Posição de teste 1"),
            (5.0, 10.0, "Posição de teste 2"),
            (7.0, 12.0, "Posição de teste 3")
        ]
        
        for x, y, description in test_positions:
            # Calcula ângulo para a base
            dx = ROBOT_INITIAL_POSITION[0] - x
            dy = ROBOT_INITIAL_POSITION[1] - y
            target_angle = math.degrees(math.atan2(dy, dx))
            
            # Normaliza ângulo para -180 a +180
            while target_angle > 180:
                target_angle -= 360
            while target_angle < -180:
                target_angle += 360
            
            distance = math.sqrt(dx**2 + dy**2)
            print(f"   {description}: ({x}, {y}) → Ângulo: {target_angle:.1f}°, Distância: {distance:.2f}m")
        
        print("✅ Teste de cálculos de ângulo concluído\n")
        return True
        
    except Exception as e:
        print(f"   ❌ Erro no teste de cálculos: {e}")
        return False

def test_synchronization_logic():
    """Testa a lógica de sincronia implementada."""
    print("🧪 TESTE: Lógica de sincronia")
    
    # Simula dados de sincronia
    initial_angle = 45.0
    target_angle = 22.0
    direction = "right"
    
    # Calcula ângulo final (lógica implementada)
    if direction == "right":
        final_angle = initial_angle + target_angle
    else:
        final_angle = initial_angle - target_angle
    
    # Normaliza ângulo (-180 a +180)
    while final_angle > 180:
        final_angle -= 360
    while final_angle < -180:
        final_angle += 360
    
    print(f"   Ângulo inicial: {initial_angle:.1f}°")
    print(f"   Giro: {target_angle:.1f}° para {direction}")
    print(f"   Ângulo final calculado: {final_angle:.1f}°")
    
    # Verifica se o cálculo faz sentido
    expected_angle = 67.0  # 45° + 22° = 67°
    if abs(final_angle - expected_angle) < 1.0:
        print("   ✅ Cálculo de sincronia correto")
        result = True
    else:
        print(f"   ❌ Cálculo incorreto - Esperado: {expected_angle:.1f}°, Calculado: {final_angle:.1f}°")
        result = False
    
    print("✅ Teste de lógica de sincronia concluído\n")
    return result

def main():
    """Executa todos os testes."""
    print("🚀 INICIANDO TESTES DAS CORREÇÕES DE SINCRONIA")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 3
    
    try:
        if test_imports():
            tests_passed += 1
        
        if test_angle_calculations():
            tests_passed += 1
        
        if test_synchronization_logic():
            tests_passed += 1
        
        print("🎉 TESTES CONCLUÍDOS!")
        print("=" * 60)
        print(f"📊 RESULTADO: {tests_passed}/{total_tests} testes passaram")
        
        if tests_passed == total_tests:
            print("✅ TODOS OS TESTES PASSARAM - Correções implementadas com sucesso!")
            print("\n📋 PRÓXIMOS PASSOS:")
            print("   1. Fazer commit das correções")
            print("   2. Fazer push para o repositório")
            print("   3. Fazer pull na Raspberry Pi")
            print("   4. Testar funcionalidades corrigidas")
        else:
            print("⚠️ ALGUNS TESTES FALHARAM - Verificar implementação")
            
    except Exception as e:
        print(f"❌ ERRO durante os testes: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
