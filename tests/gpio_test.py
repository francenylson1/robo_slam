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
        # NOTA (2026-09-03): confirmado que o BRK esta conectado nos dois
        # canais (direita e esquerda) - a suspeita anterior de fio solto
        # foi descartada. O comportamento erratico observado entre testes
        # (ora so a direita gira, ora so a esquerda, ora nenhuma, sem
        # correlacao clara com mudancas de codigo) segue sem explicacao por
        # software - hipoteses abertas: conexao intermitente (mau contato
        # em algum conector apos as trocas repetidas durante o diagnostico)
        # ou queda de tensao na alimentacao compartilhada quando os dois
        # motores puxam corrente ao mesmo tempo. Ordem freio->DIR abaixo
        # mantida (e valida, ja que o BRK realmente chega na controladora).
        print("Acionando freios antes de definir a direcao...")
        GPIO.output(break_E, GPIO.HIGH)
        GPIO.output(break_D, GPIO.HIGH)

        print(f"Definindo direcao para FRENTE (E:{DIR_E_FORWARD}, D:{DIR_D_FORWARD})...")
        GPIO.output(dir_E, DIR_E_FORWARD)
        GPIO.output(dir_D, DIR_D_FORWARD)
        time.sleep(0.3)

        print("Liberando freios...")
        GPIO.output(break_E, GPIO.LOW)
        GPIO.output(break_D, GPIO.LOW)
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


def test_left_wheel_isolated():
    """
    Espelho de test_right_wheel_isolated(): testa SOMENTE a roda esquerda,
    alternando DIR_E em HIGH e depois LOW, com a roda direita travada
    (freio sempre em HIGH). Objetivo (2026-09-03): a saida de DIR da
    esquerda nunca foi medida isolada - so vimos ela cair para perto de
    0V no teste COMBINADO (com a direita tambem ativa), apos confirmar
    que nao ha curto entre os dois fios de DIR. Este teste diz se a queda
    e um problema proprio do canal esquerdo (aparece aqui tambem, sozinho)
    ou so acontece por interacao quando os dois canais operam juntos.
    """
    print("--- TESTE ISOLADO: RODA ESQUERDA (DIR HIGH depois LOW) ---")
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.cleanup()

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        control_pins = [dir_E, break_E, speed_E, dir_D, break_D, speed_D]
        for pin in control_pins:
            GPIO.setup(pin, GPIO.OUT)

        pwm_E = GPIO.PWM(speed_E, 20)
        pwm_E.start(0)

        # Direita travada o tempo todo (freio em HIGH = acionado)
        GPIO.output(break_D, GPIO.HIGH)
        GPIO.output(dir_D, GPIO.LOW)

        for label, level in (("HIGH", GPIO.HIGH), ("LOW", GPIO.LOW)):
            print(f"\nFase DIR_E = {label}: observe/anote o sentido da roda esquerda.")
            print("Se tiver multimetro no pino DIR da controladora esquerda, meça agora.")
            GPIO.output(break_E, GPIO.HIGH)  # freio esquerdo acionado antes de trocar DIR
            GPIO.output(dir_E, level)
            time.sleep(0.3)
            GPIO.output(break_E, GPIO.LOW)   # libera freio esquerdo
            pwm_E.ChangeDutyCycle(TEST_SPEED)
            time.sleep(HOLD_SECONDS)
            pwm_E.ChangeDutyCycle(0)
            GPIO.output(break_E, GPIO.HIGH)
            time.sleep(1)

        print("\n--- TESTE ISOLADO CONCLUIDO ---")
        print("DIR_E_FORWARD = HIGH, entao a fase HIGH deveria medir ~5V (frente).")
        print("Se mesmo aqui, com a direita travada, a fase HIGH nao chegar a ~5V,")
        print("o defeito e do proprio canal esquerdo - nao de interacao com a direita.")

    except Exception as e:
        print(f"\nERRO CRITICO DURANTE O TESTE: {e}")
    finally:
        print("Executando limpeza final do GPIO...")
        try:
            pwm_E.stop()
            del pwm_E
        except NameError:
            pass
        GPIO.cleanup()
        print("Limpeza concluida.")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "right":
        test_right_wheel_isolated()
    elif len(sys.argv) > 1 and sys.argv[1] == "left":
        test_left_wheel_isolated()
    else:
        test_forward_movement()
