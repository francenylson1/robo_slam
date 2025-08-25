import sys
import os
import time
import threading

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.robot_motor_controller import RobotMotorController

def main():
    """
    Script de teste para calibrar o número de ticks por revolução da roda.
    Este script inicializa SOMENTE o controlador de motores, sem a GUI,
    para evitar conflitos e permitir uma medição limpa.
    """
    print("="*50)
    print("INICIANDO SCRIPT DE CALIBRAÇÃO DE TICKS")
    print("="*50)
    print("Pressione Ctrl+C para sair.")
    print("\nAVISO: Este script NÃO moverá os motores. A roda deve ser girada manualmente.")

    try:
        # 1. Inicializa o controlador de motores
        motor_controller = RobotMotorController()
        print("\nControlador de motores inicializado.")
        print("Aguardando 5 segundos para estabilização...")
        time.sleep(5)

        # 2. Loop principal para mostrar os ticks acumulados
        print("\n--- INÍCIO DA MEDIÇÃO ---")
        print("Gire uma das rodas manualmente e observe os ticks acumulados abaixo.")

        while True:
            # Pega os ticks acumulados SEM zerá-los (usando acesso direto para este teste)
            with motor_controller.ticks_lock:
                left_ticks = motor_controller.left_ticks_for_odometry
                right_ticks = motor_controller.right_ticks_for_odometry
            
            # Limpa a linha anterior e imprime os novos valores
            # O '\r' move o cursor para o início da linha
            print(f"\rTicks Acumulados -> Esquerda: {left_ticks} | Direita: {right_ticks}   ", end="")
            
            time.sleep(0.2) # Atualiza a tela 5x por segundo

    except KeyboardInterrupt:
        print("\n\nCtrl+C detectado. Encerrando o programa.")
    
    finally:
        # Garante que os recursos do GPIO sejam limpos ao sair
        if 'motor_controller' in locals():
            motor_controller.cleanup()
        print("Script de calibração finalizado.")

if __name__ == "__main__":
    main()
