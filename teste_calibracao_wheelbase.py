#!/usr/bin/env python3
"""
Teste de Calibração do Wheelbase e Fatores de Correção
Diagnóstica problemas de deriva lateral através de testes específicos

Resultados dos testes anteriores:
- Teste 1 (atual): curva leve para direita
- Teste 2 (sem correção): curva menor para direita  
- Teste 3 (cinemática original): curva leve para direita
- Teste 4 (sem nada): curva leve para direita

CONCLUSÃO: Problema mecânico/calibração, não software
"""

import sys
import os
import time

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.robot_motor_controller import RobotMotorController
from src.core.config import (
    ROBOT_WHEEL_BASE_M, 
    LEFT_MOTOR_CORRECTION_FACTOR,
    RIGHT_MOTOR_CORRECTION_FACTOR,
    TICKS_PER_REVOLUTION,
    ROBOT_WHEEL_CIRCUMFERENCE_M
)

def test_wheelbase_calibration():
    """
    Testa diferentes configurações de wheelbase e fatores de correção
    para identificar a causa da deriva para direita
    """
    
    print("=" * 60)
    print("TESTE DE CALIBRAÇÃO - WHEELBASE E FATORES DE CORREÇÃO")
    print("=" * 60)
    
    print(f"\n📊 CONFIGURAÇÕES ATUAIS:")
    print(f"   Wheelbase: {ROBOT_WHEEL_BASE_M}m ({ROBOT_WHEEL_BASE_M*100:.1f}cm)")
    print(f"   Fator Motor Esquerdo: {LEFT_MOTOR_CORRECTION_FACTOR:.6f}")
    print(f"   Fator Motor Direito: {RIGHT_MOTOR_CORRECTION_FACTOR:.6f}")
    print(f"   Ticks por Revolução: {TICKS_PER_REVOLUTION}")
    print(f"   Circunferência Roda: {ROBOT_WHEEL_CIRCUMFERENCE_M}m")
    
    # Análise dos fatores
    left_slower = LEFT_MOTOR_CORRECTION_FACTOR < RIGHT_MOTOR_CORRECTION_FACTOR
    factor_diff = abs(LEFT_MOTOR_CORRECTION_FACTOR - RIGHT_MOTOR_CORRECTION_FACTOR)
    
    print(f"\n🔍 ANÁLISE DOS FATORES:")
    if left_slower:
        print(f"   ⚠️  Motor ESQUERDO é {factor_diff*100:.2f}% mais LENTO")
        print(f"   ➡️  Isso deveria causar curva para ESQUERDA")
        print(f"   ❌ MAS o robô curva para DIREITA - CONTRADIÇÃO!")
    else:
        print(f"   ⚠️  Motor DIREITO é {factor_diff*100:.2f}% mais LENTO")
        print(f"   ➡️  Isso deveria causar curva para DIREITA")
        print(f"   ✅ Robô curva para DIREITA - COERENTE")
    
    print(f"\n🧪 TESTES PROPOSTOS:")
    
    # Teste 1: Inverter fatores de correção
    print(f"\n1️⃣  TESTE: Inverter fatores de correção")
    print(f"    Atual: L={LEFT_MOTOR_CORRECTION_FACTOR:.6f}, R={RIGHT_MOTOR_CORRECTION_FACTOR:.6f}")
    print(f"    Novo:  L={RIGHT_MOTOR_CORRECTION_FACTOR:.6f}, R={LEFT_MOTOR_CORRECTION_FACTOR:.6f}")
    print(f"    Expectativa: Se problema for nos fatores, robô deve curvar para ESQUERDA")
    
    # Teste 2: Aumentar correção do motor direito
    new_right_factor = RIGHT_MOTOR_CORRECTION_FACTOR - (factor_diff * 2)
    print(f"\n2️⃣  TESTE: Aumentar correção do motor direito")
    print(f"    Atual: L={LEFT_MOTOR_CORRECTION_FACTOR:.6f}, R={RIGHT_MOTOR_CORRECTION_FACTOR:.6f}")
    print(f"    Novo:  L={LEFT_MOTOR_CORRECTION_FACTOR:.6f}, R={new_right_factor:.6f}")
    print(f"    Expectativa: Robô deve andar mais reto")
    
    # Teste 3: Verificar wheelbase
    wheelbase_cm = ROBOT_WHEEL_BASE_M * 100
    print(f"\n3️⃣  TESTE: Verificar wheelbase")
    print(f"    Atual: {wheelbase_cm:.1f}cm")
    print(f"    ⚠️  SUSPEITA: {wheelbase_cm:.1f}cm parece MUITO PEQUENO")
    print(f"    Sugestão: Medir fisicamente a distância entre centros das rodas")
    print(f"    Wheelbase típico para robô: 15-25cm")
    
    # Teste 4: Problema mecânico
    print(f"\n4️⃣  VERIFICAÇÃO: Problemas mecânicos")
    print(f"    ✓ Verificar se rodas estão alinhadas")
    print(f"    ✓ Verificar se rodas têm mesmo diâmetro")
    print(f"    ✓ Verificar se não há atrito diferencial")
    print(f"    ✓ Verificar se encoders estão calibrados igualmente")
    
    print(f"\n📋 PRÓXIMOS PASSOS:")
    print(f"1. Medir fisicamente o wheelbase (distância entre centros das rodas)")
    print(f"2. Testar com fatores de correção invertidos")
    print(f"3. Verificar alinhamento mecânico das rodas")
    print(f"4. Calibrar encoders individualmente")
    
    print(f"\n" + "=" * 60)
    print(f"DIAGNÓSTICO: Problema provavelmente MECÂNICO ou WHEELBASE incorreto")
    print(f"=" * 60)

def test_motor_individual():
    """
    Testa cada motor individualmente para verificar calibração
    """
    print(f"\n🔧 TESTE INDIVIDUAL DOS MOTORES")
    print(f"Executando teste de 2 segundos para cada motor...")
    
    controller = RobotMotorController()
    
    try:
        # Teste motor esquerdo
        print(f"\n⬅️  Testando MOTOR ESQUERDO (2s)...")
        controller.set_target_speed(20, 0)  # Só motor esquerdo
        time.sleep(2)
        controller.stop()
        
        left_ticks = controller.get_and_reset_ticks()
        print(f"    Ticks motor esquerdo: {left_ticks['left']}")
        
        time.sleep(1)
        
        # Teste motor direito
        print(f"\n➡️  Testando MOTOR DIREITO (2s)...")
        controller.set_target_speed(0, 20)  # Só motor direito
        time.sleep(2)
        controller.stop()
        
        right_ticks = controller.get_and_reset_ticks()
        print(f"    Ticks motor direito: {right_ticks['right']}")
        
        # Análise
        if left_ticks['left'] > 0 and right_ticks['right'] > 0:
            ratio = left_ticks['left'] / right_ticks['right']
            print(f"\n📊 ANÁLISE:")
            print(f"    Ratio L/R: {ratio:.4f}")
            if ratio > 1.05:
                print(f"    ⚠️  Motor ESQUERDO {((ratio-1)*100):.1f}% mais rápido")
            elif ratio < 0.95:
                print(f"    ⚠️  Motor DIREITO {((1/ratio-1)*100):.1f}% mais rápido")
            else:
                print(f"    ✅ Motores balanceados")
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
    finally:
        controller.cleanup()

if __name__ == "__main__":
    test_wheelbase_calibration()
    
    # Só executa teste individual se estiver na Raspberry Pi
    try:
        from src.core.environment import GPIO_AVAILABLE
        if GPIO_AVAILABLE:
            input("\nPressione ENTER para executar teste individual dos motores...")
            test_motor_individual()
        else:
            print("\n💻 Teste individual só disponível na Raspberry Pi")
    except:
        print("\n💻 Teste individual só disponível na Raspberry Pi")