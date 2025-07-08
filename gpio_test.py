import RPi.GPIO as GPIO
import time

# --- Pinos dos Sensores Hall ---
HALL_PIN_ESQUERDO = 16
HALL_PIN_DIREITO = 17

def main():
    """
    Script de teste para ler e imprimir o estado dos pinos dos sensores Hall.
    """
    print("Iniciando teste dos sensores Hall...")
    print(f"Pino Esquerdo: {HALL_PIN_ESQUERDO}")
    print(f"Pino Direito: {HALL_PIN_DIREITO}")
    print("\nPressione Ctrl+C para sair.")
    
    # Configuracao do GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Configura os pinos como entrada com resistor pull-down
    GPIO.setup(HALL_PIN_ESQUERDO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(HALL_PIN_DIREITO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
    try:
        # Loop para ler e imprimir o estado dos pinos
        while True:
            estado_esquerdo = GPIO.input(HALL_PIN_ESQUERDO)
            estado_direito = GPIO.input(HALL_PIN_DIREITO)
            
            # Imprime na mesma linha usando o carriage return '\r'
            print(f"Estado dos Pinos -> Esquerdo (16): {estado_esquerdo} | Direito (17): {estado_direito}   ", end='\r')
            
            # Pequeno delay para nao sobrecarregar o processador
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        # Lida com a saida via Ctrl+C
        print("\n\nTeste interrompido pelo usuario.")
        
    finally:
        # Limpa o GPIO ao sair, garantindo que os pinos sejam liberados
        print("Limpando a configuracao do GPIO.")
        GPIO.cleanup()

if __name__ == '__main__':
    main() 