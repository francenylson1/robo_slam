import RPi.GPIO as GPIO
import time

# Pinos de Controle
dir_E, break_E, speed_E = 5, 6, 18
dir_D, break_D, speed_D = 23, 24, 12

# Logica de Movimento para FRENTE (a ser validada)
# Esquerda = HIGH (igual ao robo SLAM). Direita = HIGH (invertido em relacao
# ao robo SLAM) - teste para o robo garcom: com DIR_D_FORWARD=LOW a roda
# direita ficava igual ao estado de repouso do pino (GPIO.OUT sem initial=
# comeca em LOW), entao "frente" nao mudava nada e ela girava pra tras.
DIR_E_FORWARD = GPIO.HIGH
DIR_D_FORWARD = GPIO.HIGH
TEST_SPEED = 25

def test_forward_movement():
    print("--- INICIANDO TESTE DE MOVIMENTO PARA FRENTE (v3) ---")
    try:
        # PASSO 1: Configuracao Inicial Limpa
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.cleanup()
        print("GPIO.cleanup() inicial executado.")
        
        # Re-configura o modo apos a limpeza
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        print("Modo GPIO configurado para BCM.")

        # PASSO 2: Configuracao dos Pinos
        control_pins = [dir_E, break_E, speed_E, dir_D, break_D, speed_D]
        print(f"Configurando os pinos {control_pins} como saida...")
        for pin in control_pins:
            GPIO.setup(pin, GPIO.OUT)
        print("Pinos configurados com sucesso.")

        # PASSO 3: Inicializacao do PWM
        pwm_E = GPIO.PWM(speed_E, 20)
        pwm_D = GPIO.PWM(speed_D, 20)
        pwm_E.start(0)
        pwm_D.start(0)
        print("PWM inicializado a 20Hz.")
        
        # PASSO 4: Execucao do Movimento
        print("Liberando freios...")
        GPIO.output(break_E, GPIO.LOW)
        GPIO.output(break_D, GPIO.LOW)
        time.sleep(0.5)

        print(f"Definindo direcao para FRENTE (E:{DIR_E_FORWARD}, D:{DIR_D_FORWARD})...")
        GPIO.output(dir_E, DIR_E_FORWARD)
        GPIO.output(dir_D, DIR_D_FORWARD)
        time.sleep(0.5)

        print(f"Acionando motores a {TEST_SPEED}% por 2 segundos...")
        pwm_E.ChangeDutyCycle(TEST_SPEED)
        pwm_D.ChangeDutyCycle(TEST_SPEED)
        time.sleep(2)

        print("Parando motores.")
        pwm_E.ChangeDutyCycle(0)
        pwm_D.ChangeDutyCycle(0)
        
        print("\n--- TESTE CONCLUIDO COM SUCESSO ---")

    except Exception as e:
        print(f"\nERRO CRITICO DURANTE O TESTE: {e}")
    finally:
        print("Executando limpeza final do GPIO...")
        GPIO.cleanup()
        print("Limpeza concluida.")

if __name__ == '__main__':
    test_forward_movement() 