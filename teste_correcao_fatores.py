#!/usr/bin/env python3
"""
Teste de Correção dos Fatores de Deriva
Testa diferentes configurações de fatores de correção para corrigir deriva para direita

BASEADO NOS RESULTADOS:
- Todos os testes mostraram curva para direita
- Fatores atuais: L=0.965812 (mais lento), R=1.000000
- Contradição: motor esquerdo mais lento deveria causar curva para esquerda
"""

import sys
import os
import time

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.robot_navigator import RobotNavigator
from src.core.config import (
    LEFT_MOTOR_CORRECTION_FACTOR,
    RIGHT_MOTOR_CORRECTION_FACTOR
)

def test_correction_factors():
    """
    Testa diferentes fatores de correção para identificar configuração correta
    """
    
    print("=" * 60)
    print("TESTE DE CORREÇÃO DOS FATORES DE DERIVA")
    print("=" * 60)
    
    print(f"\n📊 FATORES ATUAIS:")
    print(f"   Motor Esquerdo: {LEFT_MOTOR_CORRECTION_FACTOR:.6f}")
    print(f"   Motor Direito: {RIGHT_MOTOR_CORRECTION_FACTOR:.6f}")
    print(f"   Resultado: Curva para DIREITA (todos os testes)")
    
    # Calcular novos fatores
    current_diff = RIGHT_MOTOR_CORRECTION_FACTOR - LEFT_MOTOR_CORRECTION_FACTOR
    print(f"   Diferença atual: {current_diff:.6f} (R-L)")
    
    print(f"\n🧪 CONFIGURAÇÕES DE TESTE:")
    
    # Teste 1: Fatores invertidos
    test1_left = RIGHT_MOTOR_CORRECTION_FACTOR
    test1_right = LEFT_MOTOR_CORRECTION_FACTOR
    print(f"\n1️⃣  FATORES INVERTIDOS:")
    print(f"    L: {test1_left:.6f}, R: {test1_right:.6f}")
    print(f"    Expectativa: Curva para ESQUERDA")
    
    # Teste 2: Corrigir motor direito (diminuir velocidade)
    test2_left = LEFT_MOTOR_CORRECTION_FACTOR
    test2_right = LEFT_MOTOR_CORRECTION_FACTOR  # Igualar ao esquerdo
    print(f"\n2️⃣  IGUALAR FATORES:")
    print(f"    L: {test2_left:.6f}, R: {test2_right:.6f}")
    print(f"    Expectativa: Movimento mais reto")
    
    # Teste 3: Aumentar correção do direito
    test3_left = LEFT_MOTOR_CORRECTION_FACTOR
    test3_right = LEFT_MOTOR_CORRECTION_FACTOR - 0.02  # Diminuir mais 2%
    print(f"\n3️⃣  AUMENTAR CORREÇÃO DIREITO:")
    print(f"    L: {test3_left:.6f}, R: {test3_right:.6f}")
    print(f"    Expectativa: Compensar deriva para direita")
    
    # Teste 4: Correção baseada na observação
    # Se curva para direita, motor direito está mais rápido
    # Então devemos diminuir fator do direito ou aumentar do esquerdo
    test4_left = 1.000000  # Motor esquerdo sem correção
    test4_right = 0.965812  # Motor direito com correção (invertido)
    print(f"\n4️⃣  CORREÇÃO LÓGICA:")
    print(f"    L: {test4_left:.6f}, R: {test4_right:.6f}")
    print(f"    Lógica: Se curva direita, motor direito mais rápido")
    print(f"    Expectativa: Movimento reto")
    
    return {
        'test1': (test1_left, test1_right),
        'test2': (test2_left, test2_right), 
        'test3': (test3_left, test3_right),
        'test4': (test4_left, test4_right)
    }

def apply_correction_test(test_name, left_factor, right_factor):
    """
    Aplica temporariamente novos fatores de correção e testa movimento
    """
    print(f"\n🔧 EXECUTANDO {test_name.upper()}")
    print(f"Fatores: L={left_factor:.6f}, R={right_factor:.6f}")
    
    try:
        # Importar e modificar temporariamente
        import src.core.robot_motor_controller as motor_module
        
        # Salvar valores originais
        original_left = motor_module.LEFT_MOTOR_CORRECTION_FACTOR
        original_right = motor_module.RIGHT_MOTOR_CORRECTION_FACTOR
        
        # Aplicar novos valores
        motor_module.LEFT_MOTOR_CORRECTION_FACTOR = left_factor
        motor_module.RIGHT_MOTOR_CORRECTION_FACTOR = right_factor
        
        print(f"✅ Fatores aplicados temporariamente")
        print(f"\n⚠️  EXECUTE AGORA: python3 src/main.py")
        print(f"   1. Selecione um ponto próximo (1-2 metros)")
        print(f"   2. Observe se robô vai reto ou curva")
        print(f"   3. Anote o resultado")
        
        input("\nPressione ENTER após testar para restaurar fatores originais...")
        
        # Restaurar valores originais
        motor_module.LEFT_MOTOR_CORRECTION_FACTOR = original_left
        motor_module.RIGHT_MOTOR_CORRECTION_FACTOR = original_right
        
        print(f"✅ Fatores originais restaurados")
        
        # Perguntar resultado
        result = input("\nResultado do teste (reto/esquerda/direita): ").lower().strip()
        return result
        
    except Exception as e:
        print(f"❌ Erro ao aplicar correção: {e}")
        return "erro"

def run_interactive_test():
    """
    Executa teste interativo com diferentes fatores
    """
    print(f"\n🎯 TESTE INTERATIVO DE FATORES")
    print(f"Este teste modifica temporariamente os fatores de correção")
    print(f"Você deve executar o robô e observar o comportamento")
    
    tests = test_correction_factors()
    results = {}
    
    for test_name, (left_factor, right_factor) in tests.items():
        print(f"\n" + "="*40)
        proceed = input(f"Executar {test_name}? (s/n): ").lower().strip()
        if proceed == 's':
            result = apply_correction_test(test_name, left_factor, right_factor)
            results[test_name] = result
        else:
            results[test_name] = "pulado"
    
    # Análise dos resultados
    print(f"\n" + "="*60)
    print(f"ANÁLISE DOS RESULTADOS")
    print(f"="*60)
    
    for test_name, result in results.items():
        left_f, right_f = tests[test_name]
        print(f"\n{test_name.upper()}:")
        print(f"  Fatores: L={left_f:.6f}, R={right_f:.6f}")
        print(f"  Resultado: {result}")
        
        if result == "reto":
            print(f"  ✅ SUCESSO! Estes fatores corrigem a deriva")
        elif result == "esquerda":
            print(f"  ⚠️  Correção excessiva - ajustar fatores")
        elif result == "direita":
            print(f"  ❌ Ainda deriva para direita")
    
    # Recomendação
    straight_tests = [name for name, result in results.items() if result == "reto"]
    if straight_tests:
        best_test = straight_tests[0]
        left_f, right_f = tests[best_test]
        print(f"\n🎯 RECOMENDAÇÃO:")
        print(f"Usar fatores do {best_test.upper()}:")
        print(f"LEFT_MOTOR_CORRECTION_FACTOR = {left_f:.6f}")
        print(f"RIGHT_MOTOR_CORRECTION_FACTOR = {right_f:.6f}")
    else:
        print(f"\n⚠️  Nenhum teste resultou em movimento reto")
        print(f"Problema pode ser mecânico ou wheelbase incorreto")

if __name__ == "__main__":
    test_correction_factors()
    
    # Só executa teste interativo se estiver na Raspberry Pi
    try:
        from src.core.environment import GPIO_AVAILABLE
        if GPIO_AVAILABLE:
            print(f"\n" + "="*60)
            interactive = input("Executar teste interativo? (s/n): ").lower().strip()
            if interactive == 's':
                run_interactive_test()
        else:
            print(f"\n💻 Teste interativo só disponível na Raspberry Pi")
            print(f"Execute este arquivo na Raspberry Pi para testar")
    except:
        print(f"\n💻 Teste interativo só disponível na Raspberry Pi")