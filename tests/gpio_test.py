import sys
import RPi.GPIO as GPIO
import time

# Pinos de Controle
dir_E, break_E, speed_E = 5, 6, 18
dir_D, break_D, speed_D = 23, 24, 12

# Logica de Movimento para FRENTE (a ser validada)
# Esquerda = HIGH (igual ao robo SLAM, confirmado correto no robo garcom).
#
# Direita: testado HIGH e LOW (ver docs/resumo_diagnostico_rodas_hoverboard_2)
# e a roda direita girou para tras nos dois casos -> o nivel do pino DIR nao
# esta mudando o sentido de giro da roda direita. Isso descarta polaridade
# de software como causa isolada; suspeita agora e fiacao de fase do motor
# direito invertida (2 das 3 fases trocadas durante os testes cruzados) ou
# fio de DIR direito nao chegando no canal certo da controladora. Usar
# test_right_wheel_isolated() abaixo para confirmar.
DIR_E_FORWARD = GPIO.HIGH
DIR_D_FORWARD = GPIO.HIGH
TEST_SPEED = 25
HOLD_SECONDS = 3

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


def test_right_wheel_isolated():
    """
    Testa SOMENTE a roda direita, alternando DIR_D em HIGH e depois LOW,
    com a roda esquerda travada (freio sempre em HIGH) para nao interferir
    na observacao. Objetivo: confirmar se o nivel do pino DIR direito (BCM 23)
    tem QUALQUER efeito no sentido de giro da roda direita.

    Se as duas fases girarem para o MESMO lado -> o DIR nao esta controlando
    a direcao direita (suspeita: fiacao de fase do motor trocada, ou fio de
    DIR nao chegando no canal certo da controladora). Nesse caso, com o
    equipamento DESLIGADO, meça a tensao no pino DIR na entrada da
    controladora (lado direito) durante cada fase para confirmar se o sinal
    esta de fato mudando ali.
    """
    print("--- TESTE ISOLADO: RODA DIREITA (DIR HIGH depois LOW) ---")
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.cleanup()

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        control_pins = [dir_E, break_E, speed_E, dir_D, break_D, speed_D]
        for pin in control_pins:
            GPIO.setup(pin, GPIO.OUT)

        pwm_D = GPIO.PWM(speed_D, 20)
        pwm_D.start(0)

        # Esquerda travada o tempo todo (freio em HIGH = acionado)
        GPIO.output(break_E, GPIO.HIGH)
        GPIO.output(dir_E, GPIO.LOW)

        for label, level in (("HIGH", GPIO.HIGH), ("LOW", GPIO.LOW)):
            print(f"\nFase DIR_D = {label}: observe/anote o sentido da roda direita.")
            print("Se tiver multimetro no pino DIR da controladora direita, meça agora.")
            GPIO.output(break_D, GPIO.HIGH)  # freio direito acionado antes de trocar DIR
            GPIO.output(dir_D, level)
            time.sleep(0.3)
            GPIO.output(break_D, GPIO.LOW)   # libera freio direito
            pwm_D.ChangeDutyCycle(TEST_SPEED)
            time.sleep(HOLD_SECONDS)
            pwm_D.ChangeDutyCycle(0)
            GPIO.output(break_D, GPIO.HIGH)
            time.sleep(1)

        print("\n--- TESTE ISOLADO CONCLUIDO ---")
        print("Compare o sentido observado nas duas fases. Se foi igual nas duas,")
        print("o DIR nao esta controlando a roda direita (ver hipoteses no topo do arquivo).")

    except Exception as e:
        print(f"\nERRO CRITICO DURANTE O TESTE: {e}")
    finally:
        print("Executando limpeza final do GPIO...")
        GPIO.cleanup()
        print("Limpeza concluida.")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "right":
        test_right_wheel_isolated()
    else:
        test_forward_movement()
