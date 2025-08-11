import sys
import os
import time

# Adiciona o diretório raiz ao PYTHONPATH para encontrar os módulos do projeto
# Isso permite executar o script da raiz do projeto (ex: python3 teste_direcao_fisica.py)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.robot_motor_controller import RobotMotorController

def virar_esquerda(motors, potencia, duracao):
    """
    Comanda o robô para virar à esquerda (sentido anti-horário).
    - Roda direita para frente (potência positiva)
    - Roda esquerda para trás (potência negativa)
    """
    left_speed = -potencia
    right_speed = potencia
    print(f"\n--- Comando: Virar à Esquerda (anti-horário) ---")
    print(f"Enviando: motors.set_speed(left={left_speed}, right={right_speed}) por {duracao}s")
    motors.set_speed(left_speed, right_speed)
    time.sleep(duracao)
    motors.stop()
    print("Motores parados.")
    time.sleep(0.5)  # Pausa para garantir que os ticks sejam processados antes da leitura
    ticks = motors.get_and_reset_ticks()
    print(f"Ticks retornados: {ticks}")
    print("-------------------------------------------------")

def virar_direita(motors, potencia, duracao):
    """
    Comanda o robô para virar à direita (sentido horário).
    - Roda esquerda para frente (potência positiva)
    - Roda direita para trás (potência negativa)
    """
    left_speed = potencia
    right_speed = -potencia
    print(f"\n--- Comando: Virar à Direita (horário) ---")
    print(f"Enviando: motors.set_speed(left={left_speed}, right={right_speed}) por {duracao}s")
    motors.set_speed(left_speed, right_speed)
    time.sleep(duracao)
    motors.stop()
    print("Motores parados.")
    time.sleep(0.5)
    ticks = motors.get_and_reset_ticks()
    print(f"Ticks retornados: {ticks}")
    print("----------------------------------------------")

def main():
    """
    Função principal que executa o menu de teste interativo.
    """
    print("Iniciando script de teste de direção física...")
    motors = None
    try:
        motors = RobotMotorController()
        # Pausa para garantir que o RPi.GPIO e as threads inicializem completamente
        print("Aguardando inicialização do controlador de motores...")
        time.sleep(2)
        print("Controlador pronto.")

        while True:
            print("\nEscolha uma ação:")
            print("  'e' - Virar à Esquerda (1 segundo, 30% de potência)")
            print("  'd' - Virar à Direita (1 segundo, 30% de potência)")
            print("  's' - Sair do script")
            
            escolha = input("Opção: ").lower()

            if escolha == 'e':
                virar_esquerda(motors, potencia=30, duracao=1)
            elif escolha == 'd':
                virar_direita(motors, potencia=30, duracao=1)
            elif escolha == 's':
                print("Saindo do script.")
                break
            else:
                print("Opção inválida. Tente novamente.")

    except KeyboardInterrupt:
        print("\nInterrupção pelo usuário. Encerrando...")
    except Exception as e:
        print(f"\nOcorreu um erro inesperado: {e}")
    finally:
        if motors:
            print("Limpando recursos do controlador de motores...")
            motors.cleanup()
            print("Recursos limpos. Fim.")

if __name__ == "__main__":
    main()
