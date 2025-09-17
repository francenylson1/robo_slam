import sys
import os
import time
import math

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.robot_motor_controller import RobotMotorController
from src.core.config import TICKS_PER_REVOLUTION, ROBOT_WHEEL_CIRCUMFERENCE_M

def main():
    """
    Teste específico para diagnosticar deriva lateral do robô.
    Mede a diferença entre os motores durante movimento em linha reta.
    """
    print("="*60)
    print("TESTE DE DIAGNÓSTICO - DERIVA LATERAL")
    print("="*60)
    print("Este teste irá:")
    print("1. Mover o robô em linha reta por 3 segundos")
    print("2. Medir os ticks de cada motor")
    print("3. Calcular a diferença e sugerir correção")
    print("\nPressione Ctrl+C para sair.")
    
    try:
        # Inicializa o controlador de motores
        motor_controller = RobotMotorController()
        print("\nControlador de motores inicializado.")
        print("Aguardando 3 segundos para estabilização...")
        time.sleep(3)
        
        # Configurações do teste
        test_speed_tps = 30  # Velocidade moderada para teste
        test_duration = 3.0  # 3 segundos de movimento
        
        print(f"\n--- INICIANDO TESTE ---")
        print(f"Velocidade: {test_speed_tps} TPS")
        print(f"Duração: {test_duration} segundos")
        print(f"Configuração atual: TICKS_PER_REVOLUTION = {TICKS_PER_REVOLUTION}")
        print(f"Circunferência da roda: {ROBOT_WHEEL_CIRCUMFERENCE_M}m")
        
        # Zera os contadores antes do teste
        motor_controller.get_and_reset_ticks()
        
        # Inicia o movimento em linha reta
        print("\n🚀 INICIANDO MOVIMENTO...")
        motor_controller.set_target_speed(test_speed_tps, test_speed_tps)
        
        # Aguarda o tempo do teste
        time.sleep(test_duration)
        
        # Para o movimento
        motor_controller.stop()
        print("🛑 MOVIMENTO PARADO")
        
        # Aguarda estabilização
        time.sleep(1)
        
        # Coleta os dados finais
        ticks_data = motor_controller.get_and_reset_ticks()
        left_ticks = ticks_data.get('left', 0)
        right_ticks = ticks_data.get('right', 0)
        
        # Calcula as distâncias percorridas
        left_distance = (left_ticks / TICKS_PER_REVOLUTION) * ROBOT_WHEEL_CIRCUMFERENCE_M
        right_distance = (right_ticks / TICKS_PER_REVOLUTION) * ROBOT_WHEEL_CIRCUMFERENCE_M
        
        # Calcula a diferença
        tick_difference = left_ticks - right_ticks
        distance_difference = left_distance - right_distance
        percentage_difference = (abs(distance_difference) / max(left_distance, right_distance)) * 100 if max(left_distance, right_distance) > 0 else 0
        
        # Resultados
        print("\n" + "="*60)
        print("RESULTADOS DO TESTE")
        print("="*60)
        print(f"Motor Esquerdo:")
        print(f"  - Ticks: {left_ticks}")
        print(f"  - Distância: {left_distance:.4f}m")
        print(f"\nMotor Direito:")
        print(f"  - Ticks: {right_ticks}")
        print(f"  - Distância: {right_distance:.4f}m")
        print(f"\nDiferença:")
        print(f"  - Ticks: {tick_difference} (Esquerda - Direita)")
        print(f"  - Distância: {distance_difference:.4f}m")
        print(f"  - Percentual: {percentage_difference:.2f}%")
        
        # Diagnóstico
        print("\n" + "="*60)
        print("DIAGNÓSTICO")
        print("="*60)
        
        if abs(percentage_difference) < 2:
            print("✅ RESULTADO: Diferença aceitável (<2%)")
            print("   O problema pode estar na lógica de navegação.")
        elif abs(percentage_difference) < 5:
            print("⚠️  RESULTADO: Diferença moderada (2-5%)")
            print("   Calibração pode resolver o problema.")
        else:
            print("❌ RESULTADO: Diferença significativa (>5%)")
            print("   Problema mecânico ou de calibração grave.")
        
        if tick_difference > 0:
            print(f"\n🔍 ANÁLISE: Motor esquerdo gira mais que o direito")
            print(f"   Isso faz o robô virar para a DIREITA (como observado!)")
            print(f"   Sugestão: Reduzir velocidade do motor esquerdo ou")
            print(f"   aumentar velocidade do motor direito.")
        elif tick_difference < 0:
            print(f"\n🔍 ANÁLISE: Motor direito gira mais que o esquerdo")
            print(f"   Isso faz o robô virar para a ESQUERDA")
            print(f"   Sugestão: Reduzir velocidade do motor direito ou")
            print(f"   aumentar velocidade do motor esquerdo.")
        else:
            print(f"\n🔍 ANÁLISE: Motores giraram igualmente")
            print(f"   O problema pode estar na mecânica ou sensores.")
        
        # Sugestão de correção
        if abs(percentage_difference) >= 2:
            correction_factor = right_distance / left_distance if left_distance > 0 else 1.0
            print(f"\n💡 SUGESTÃO DE CORREÇÃO:")
            print(f"   Fator de correção para motor esquerdo: {correction_factor:.4f}")
            print(f"   Aplicar este fator multiplicando a velocidade do motor esquerdo")
            print(f"   ou dividindo a velocidade do motor direito por este valor.")
        
    except KeyboardInterrupt:
        print("\n\nCtrl+C detectado. Encerrando o programa.")
    
    finally:
        # Garante que os recursos sejam limpos
        if 'motor_controller' in locals():
            motor_controller.stop()
            motor_controller.cleanup()
        print("\nTeste de deriva lateral finalizado.")

if __name__ == "__main__":
    main()