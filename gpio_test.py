import RPi.GPIO as GPIO
import time

# Pinos de Controle
dir_E, break_E, speed_E = 5, 6, 18
dir_D, break_D, speed_D = 23, 24, 12

# Logica de Movimento para FRENTE (a ser validada)
# Esquerda = HIGH, Direita = LOW
DIR_E_FORWARD = GPIO.HIGH
DIR_D_FORWARD = GPIO.LOW
TEST_SPEED = 25
DURATION = 2  # segundos

def setup_gpio():
    """Configura os pinos GPIO para o modo BCM e inicializa os pinos de controle."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.cleanup()
    time.sleep(0.1) # Pequena pausa apos a limpeza
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    control_pins = [dir_E, break_E, speed_E, dir_D, break_D, speed_D]
    for pin in control_pins:
        GPIO.setup(pin, GPIO.OUT)
        
    pwm_E = GPIO.PWM(speed_E, 20)
    pwm_D = GPIO.PWM(speed_D, 20)
    pwm_E.start(0)
    pwm_D.start(0)
    
    return pwm_E, pwm_D

def release_brakes():
    """Libera os freios dos motores."""
    GPIO.output(break_E, GPIO.LOW)
    GPIO.output(break_D, GPIO.LOW)
    time.sleep(0.1)

def stop_motors(pwm_E, pwm_D):
    """Para os motores."""
    pwm_E.ChangeDutyCycle(0)
    pwm_D.ChangeDutyCycle(0)
    # Aciona os freios para uma parada mais efetiva
    GPIO.output(break_E, GPIO.HIGH)
    GPIO.output(break_D, GPIO.HIGH)

def move_forward(pwm_E, pwm_D):
    """Move o robo para frente."""
    print(f"Movendo para FRENTE a {TEST_SPEED}% por {DURATION}s...")
    release_brakes()
    GPIO.output(dir_E, DIR_E_FORWARD)
    GPIO.output(dir_D, DIR_D_FORWARD)
    pwm_E.ChangeDutyCycle(TEST_SPEED)
    pwm_D.ChangeDutyCycle(TEST_SPEED)
    time.sleep(DURATION)
    stop_motors(pwm_E, pwm_D)

def turn_left(pwm_E, pwm_D):
    """Gira o robo para a esquerda."""
    print(f"Girando para a ESQUERDA a {TEST_SPEED}% por {DURATION}s...")
    release_brakes()
    # Para girar para a esquerda, o motor direito vai para frente e o esquerdo para tras
    GPIO.output(dir_E, not DIR_E_FORWARD) # Inverte a direcao da roda esquerda
    GPIO.output(dir_D, DIR_D_FORWARD)   # Mantem a direcao da roda direita
    pwm_E.ChangeDutyCycle(TEST_SPEED)
    pwm_D.ChangeDutyCycle(TEST_SPEED)
    time.sleep(DURATION)
    stop_motors(pwm_E, pwm_D)

def turn_right(pwm_E, pwm_D):
    """Gira o robo para a direita."""
    print(f"Girando para a DIREITA a {TEST_SPEED}% por {DURATION}s...")
    release_brakes()
    # Para girar para a direita, o motor esquerdo vai para frente e o direito para tras
    GPIO.output(dir_E, DIR_E_FORWARD)     # Mantem a direcao da roda esquerda
    GPIO.output(dir_D, not DIR_D_FORWARD) # Inverte a direcao da roda direita
    pwm_E.ChangeDutyCycle(TEST_SPEED)
    pwm_D.ChangeDutyCycle(TEST_SPEED)
    time.sleep(DURATION)
    stop_motors(pwm_E, pwm_D)

def main_test():
    """Menu principal para teste dos motores."""
    try:
        pwm_E, pwm_D = setup_gpio()
        
        while True:
            print("\n--- MENU DE TESTE DE MOTORES ---")
            print("1. Mover para Frente")
            print("2. Girar para Esquerda")
            print("3. Girar para Direita")
            print("q. Sair")
            
            choice = input("Escolha uma opcao: ").lower()
            
            if choice == '1':
                move_forward(pwm_E, pwm_D)
            elif choice == '2':
                turn_left(pwm_E, pwm_D)
            elif choice == '3':
                turn_right(pwm_E, pwm_D)
            elif choice == 'q':
                print("Encerrando testes.")
                break
            else:
                print("Opcao invalida. Tente novamente.")
            
            time.sleep(1) # Pausa entre os testes

    except Exception as e:
        print(f"\nERRO CRITICO DURANTE O TESTE: {e}")
    finally:
        print("Executando limpeza final do GPIO...")
        GPIO.cleanup()
        print("Limpeza concluida.")


if __name__ == '__main__':
    main_test() 