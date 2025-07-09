import sys
import os
import time

# Adiciona o diretório raiz ao PYTHONPATH para permitir importações de 'src'
# Isso garante que o script possa ser executado do diretório raiz.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.core.robot_motor_controller import RobotMotorController
from src.core.environment import GPIO_AVAILABLE

def run_encoder_test():
    """
    Script de teste dedicado a verificar a funcionalidade dos encoders dos motores.
    Ele aciona os motores e imprime a contagem de ticks recebida.
    """
    if not GPIO_AVAILABLE:
        print("ERRO: Este teste é projetado para ser executado em uma Raspberry Pi com GPIOs.")
        print("A variável GPIO_AVAILABLE está como False. Saindo.")
        return

    print("--- INICIANDO TESTE DE MOTORES E ENCODERS ---")
    motors = None
    try:
        # 1. Inicializar o controlador de motores
        motors = RobotMotorController()
        print("INFO: Controlador de motores inicializado.")
        
        # Pausa para garantir que as threads internas (monitor de hall, PID) iniciem
        time.sleep(1)

        # 2. Acionar os motores para frente com uma potência fixa
        # Usamos set_speed para um controle direto, ignorando a lógica do PID por enquanto.
        # NOTA: set_speed só funciona se o PID não estiver ativo, o que é o caso
        # no início, antes de chamarmos set_target_speed.
        speed_percentage = 40.0  # Usando 40% de potência
        print(f"\nINFO: Acionando motores para frente com {speed_percentage}% de potência por 5 segundos...")
        motors.set_speed(speed_percentage, speed_percentage)

        # 3. Monitorar os ticks lidos por 5 segundos
        test_duration = 5
        start_time = time.time()
        print("INFO: Lendo ticks dos encoders...")
        while time.time() - start_time < test_duration:
            # A função que precisamos testar
            ticks = motors.get_and_reset_ticks()
            
            # Imprime os resultados
            print(f"   -> Ticks lidos: Esquerda={ticks.get('left', 'N/A')}, Direita={ticks.get('right', 'N/A')}")
            
            time.sleep(0.25)  # Imprime 4 vezes por segundo

        print("\nINFO: Período de teste concluído.")

    except Exception as e:
        print(f"\nERRO CRÍTICO: Ocorreu uma exceção durante o teste: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 4. Parar os motores e limpar os recursos, independentemente do que aconteceu
        if motors:
            print("INFO: Parando motores e limpando recursos GPIO...")
            motors.stop()
            motors.cleanup()
            print("INFO: Motores parados e limpeza concluída.")
        
        print("\n--- ANÁLISE DO RESULTADO ---")
        print("1. OBSERVE os valores de 'Ticks lidos' acima.")
        print("2. SE AS RODAS GIRARAM, mas os valores de ticks permaneceram em 0, o problema é 100% confirmado:")
        print("   -> A leitura dos sensores Hall (encoders) não está funcionando.")
        print("   -> VERIFIQUE: Fiação dos sensores, pinos GPIO corretos em `robot_motor_controller.py`, ou possível defeito de hardware.")
        print("3. SE OS VALORES AUMENTARAM, o hardware está funcionando e o problema é de integração de software.")


if __name__ == "__main__":
    run_encoder_test() 