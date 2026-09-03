import sys
import RPi.GPIO as GPIO
import time

# Pinos de Controle
dir_E, break_E, speed_E = 5, 6, 18
dir_D, break_D, speed_D = 23, 24, 12

# Logica de Movimento para FRENTE
# Esquerda = HIGH (igual ao robo SLAM, confirmado correto no robo garcom).
#
# Direita: test_right_wheel_isolated() confirmou que o DIR_D CONTROLA a
# direcao (ao contrario do teste anterior, que tinha indicado "sem efeito"):
# fase HIGH girou para tras, fase LOW girou para frente. Logo, ao contrario
# da esquerda, a polaridade correta da direita e LOW = frente.
DIR_E_FORWARD = GPIO.HIGH
DIR_D_FORWARD = GPIO.LOW
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
        control_pins = [break_E, speed_E, break_D, speed_D]
        print(f"Configurando os pinos {control_pins} como saida...")
        for pin in control_pins:
            GPIO.setup(pin, GPIO.OUT)
        # Pinos DIR nascem no nivel OPOSTO ao de "frente": sem isso, quando
        # DIR_x_FORWARD coincide com o repouso padrao do GPIO.setup() (LOW),
        # o comando de frente nao gera nenhuma transicao real no pino - so
        # aplica um nivel que ja estava la. Isso reproduziu o sintoma da
        # roda direita parada quando DIR_D_FORWARD virou LOW: a controladora
        # parece exigir uma borda no DIR, nao so o nivel final.
        GPIO.setup(dir_E, GPIO.OUT, initial=(GPIO.LOW if DIR_E_FORWARD == GPIO.HIGH else GPIO.HIGH))
        GPIO.setup(dir_D, GPIO.OUT, initial=(GPIO.LOW if DIR_D_FORWARD == GPIO.HIGH else GPIO.HIGH))
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
        # 'del' (nao so stop()) ANTES do GPIO.cleanup(): isso forca o
        # __del__ do PWM a rodar agora, com o handle do lgpio ainda aberto.
        # Se deixarmos o objeto morrer sozinho depois do cleanup(), o
        # __del__ acha o handle ja fechado e o script termina com um
        # TypeError inofensivo mas confuso.
        try:
            pwm_E.stop()
            del pwm_E
        except NameError:
            pass
        try:
            pwm_D.stop()
            del pwm_D
        except NameError:
            pass
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

    RESULTADO (2026-09-03): as fases giraram em sentidos DIFERENTES (HIGH =
    para tras, LOW = para frente). Ou seja, o DIR direito controla sim a
    direcao; a polaridade correta e o oposto da esquerda (LOW = frente,
    ja aplicado em DIR_D_FORWARD acima).
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
        try:
            pwm_D.stop()
            del pwm_D
        except NameError:
            pass
        GPIO.cleanup()
        print("Limpeza concluida.")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "right":
        test_right_wheel_isolated()
    else:
        test_forward_movement()
