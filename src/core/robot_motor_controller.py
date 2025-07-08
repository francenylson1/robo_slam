# modules/robot_motor_controller.py
import time
import sys
import os
import threading

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.environment import GPIO_AVAILABLE
from src.core.pid_controller import PIDController
from src.core.config import TICKS_PER_REVOLUTION # Importa a constante necessária

if GPIO_AVAILABLE:
    try:
        import RPi.GPIO as GPIO
    except (ImportError, RuntimeError):
        print("AVISO: A biblioteca RPi.GPIO não pôde ser importada. Motores não funcionarão.")
        GPIO_AVAILABLE = False
else:
    GPIO = None

class RobotMotorController:
    """
    Controla os motores do robô, abstraindo a complexidade do hardware.
    Pode operar em modo real (com Raspberry Pi e RPi.GPIO) ou em modo simulado.
    """
    def __init__(self):
        self.left_speed_percent = 0
        self.right_speed_percent = 0
        self.is_moving = False
        
        # Atributos para feedback de velocidade
        self.left_hall_ticks = 0
        self.right_hall_ticks = 0
        self.last_speed_check_time = time.time()
        self.current_left_tps = 0.0
        self.current_right_tps = 0.0
        
        # --- NOVO: Interruptor para o controle PID ---
        self.pid_enabled = False

        if GPIO_AVAILABLE and GPIO:
            print("Inicializando controlador de motores em MODO REAL (Raspberry Pi).")
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # PINOS DO MOTOR ESQUERDO
            self.dir_E = 5      # Direção
            self.break_E = 6    # Freio
            self.speed_E = 18   # PWM para Velocidade
            self.hall_E = 16    # Sensor Hall (Encoder)

            # PINOS DO MOTOR DIREITO
            self.dir_D = 23     # Direção
            self.break_D = 24   # Freio
            self.speed_D = 12   # PWM para Velocidade
            self.hall_D = 17    # Sensor Hall (Encoder)
            
            # Configura pinos de saída
            for pin in [self.dir_E, self.break_E, self.speed_E, self.dir_D, self.break_D, self.speed_D]:
                GPIO.setup(pin, GPIO.OUT)

            # Configura pinos de entrada para os sensores Hall
            GPIO.setup(self.hall_E, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(self.hall_D, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            
            # Inicializa o estado anterior para o Polling
            self.last_hall_E_state = GPIO.input(self.hall_E)
            self.last_hall_D_state = GPIO.input(self.hall_D)

            # Inicializa PWM a 20Hz ANTES de iniciar as threads
            self.pwm_D = GPIO.PWM(self.speed_D, 20)
            self.pwm_E = GPIO.PWM(self.speed_E, 20)
            self.pwm_D.start(0)
            self.pwm_E.start(0)

            # Inicializa os controladores PID, mas o loop nao comeca a controlar ainda
            # Ganhos iniciais (precisarao de ajuste fino)
            # Kp: Aumentado para dar forca suficiente para o robo sair da inercia.
            # Ki: Aumentado para ajudar a vencer o atrito inicial.
            # Kd: Mantido baixo para evitar instabilidade.
            self.pid_left = PIDController(Kp=0.2, Ki=0.15, Kd=0.02, setpoint=0, output_limits=(-15, 15))
            self.pid_right = PIDController(Kp=0.2, Ki=0.15, Kd=0.02, setpoint=0, output_limits=(-15, 15))

            # Inicia a thread de monitoramento dos sensores Hall por Polling
            monitor_thread = threading.Thread(target=self._hall_sensor_monitor_thread, daemon=True)
            monitor_thread.start()

            # Inicia a thread de controle PID
            pid_control_thread = threading.Thread(target=self._pid_control_loop, daemon=True)
            pid_control_thread.start()

            # Ativa o freio dos motores como estado inicial seguro
            GPIO.output(self.break_D, GPIO.HIGH)
            GPIO.output(self.break_E, GPIO.HIGH)
        else:
            print("Inicializando controlador de motores em MODO SIMULADO.")

    def _hall_sensor_monitor_thread(self):
        """
        Thread que monitora os sensores Hall via Polling para evitar o uso
        de 'add_event_detect' que estava se mostrando instável.
        """
        # Garante que o GPIO esteja disponível antes de entrar no loop
        if not GPIO_AVAILABLE or not GPIO:
            return

        while True:
            # Leitura do sensor esquerdo
            current_state_E = GPIO.input(self.hall_E)
            if current_state_E == 1 and self.last_hall_E_state == 0:
                self.left_hall_ticks += 1
            self.last_hall_E_state = current_state_E

            # Leitura do sensor direito
            current_state_D = GPIO.input(self.hall_D)
            if current_state_D == 1 and self.last_hall_D_state == 0:
                self.right_hall_ticks += 1
            self.last_hall_D_state = current_state_D
            
            # Pausa muito curta para evitar 100% de uso da CPU
            time.sleep(0.001) # Poll a ~1000Hz

    def _pid_control_loop(self):
        """
        Thread que executa o loop de controle PID continuamente.
        """
        if not GPIO_AVAILABLE:
            return
            
        while True:
            # --- NOVO: So executa o controle se o interruptor estiver ligado ---
            if not self.pid_enabled:
                time.sleep(0.1) # Dorme se desativado para nao usar CPU
                continue

            # 1. Calcula a velocidade real atual (ticks/s)
            self._update_current_speed()
            
            # 2. Calcula a saida de potencia usando o PID
            left_power = self.pid_left.update(self.current_left_tps)
            right_power = self.pid_right.update(self.current_right_tps)
            
            # 3. Aplica a potencia aos motores
            self._set_motor_speed_real("left", left_power)
            self._set_motor_speed_real("right", right_power)
            
            # 4. Define a frequencia do loop de controle (ex: 20Hz)
            time.sleep(0.05)

    def _update_current_speed(self):
        """
        Calcula e atualiza a velocidade instantanea (ticks/s) para uso no PID.
        """
        current_time = time.time()
        delta_time = current_time - self.last_speed_check_time

        if delta_time > 0.01: # Atualiza em intervalos regulares
            self.current_left_tps = self.left_hall_ticks / delta_time
            self.current_right_tps = self.right_hall_ticks / delta_time

            self.left_hall_ticks = 0
            self.right_hall_ticks = 0
            self.last_speed_check_time = current_time

    def set_wheel_speeds_dps(self, left_dps: float, right_dps: float):
        """
        Define a velocidade alvo das rodas em graus por segundo (dps).
        Esta função serve como uma interface para o navegador, convertendo
        dps para tps (ticks por segundo) antes de passar para o controle PID.
        """
        # 1 volta = 360 graus
        # tps = (dps / 360) * ticks_per_revolution
        left_tps = (left_dps / 360.0) * TICKS_PER_REVOLUTION
        right_tps = (right_dps / 360.0) * TICKS_PER_REVOLUTION

        self.set_target_speed(left_tps, right_tps)

    def set_target_speed(self, left_tps: float, right_tps: float):
        """
        Define a velocidade alvo (em ticks/segundo) e ATIVA o controle PID.
        """
        if GPIO_AVAILABLE:
            if not self.pid_enabled:
                # Ao receber o primeiro comando de velocidade, ativa o PID
                self.pid_enabled = True
                print("DEBUG: Controle PID ATIVADO.")
            self.pid_left.set_setpoint(left_tps)
            self.pid_right.set_setpoint(right_tps)
        else:
            # Em modo simulado, apenas imprime a velocidade alvo
            print(f"Simulando velocidade alvo - Esquerda: {left_tps} tps, Direita: {right_tps} tps")

    def set_speed(self, left_speed: float, right_speed: float):
        """
        (LEGADO - Apenas para compatibilidade)
        Define a velocidade dos motores.
        Valores de -100 a 100, onde > 0 e para frente e < 0 e para tras.
        Para controle PID, use set_target_speed.
        """
        # Em modo PID, esta funcao deve ser usada com cuidado ou desativada
        # para nao interferir no loop de controle.
        # Por enquanto, mantemos para diagnostico.
        self.left_speed_percent = max(-100, min(100, left_speed))
        self.right_speed_percent = max(-100, min(100, right_speed))
        
        if GPIO_AVAILABLE and not hasattr(self, 'pid_left'): # So executa se o PID nao estiver ativo
            self._set_motor_speed_real("left", self.left_speed_percent)
            self._set_motor_speed_real("right", self.right_speed_percent)
        else:
            self._simulate_movement()

    def _set_motor_speed_real(self, motor: str, speed_percent: float):
        """Controla um motor específico via GPIO."""
        if not GPIO_AVAILABLE or not GPIO:
            return

        if motor == "left":
            pwm = self.pwm_E
            pin_dir = self.dir_E
            pin_break = self.break_E
        elif motor == "right":
            pwm = self.pwm_D
            pin_dir = self.dir_D
            pin_break = self.break_D
        else:
            return

        if abs(speed_percent) < 1:
            # Para o motor e ativa o freio
            pwm.ChangeDutyCycle(0)
            GPIO.output(pin_break, GPIO.HIGH)
            return

        # Libera o freio
        GPIO.output(pin_break, GPIO.LOW)
        
        # Define a direção
        if speed_percent > 0:
            # Para frente (Esquerdo: HIGH, Direito: LOW)
            direction = GPIO.HIGH if motor == "left" else GPIO.LOW
        else:
            # Para trás (Esquerdo: LOW, Direito: HIGH)
            direction = GPIO.LOW if motor == "left" else GPIO.HIGH
        
        GPIO.output(pin_dir, direction)
        
        # Define a velocidade (Duty Cycle)
        duty_cycle = abs(speed_percent)
        pwm.ChangeDutyCycle(duty_cycle)

    def _simulate_movement(self):
        """Simula o movimento dos motores para depuração."""
        if self.left_speed_percent != 0 or self.right_speed_percent != 0:
            self.is_moving = True
            print(f"Simulando movimento - Esquerda: {self.left_speed_percent}%, Direita: {self.right_speed_percent}%")
        else:
            self.is_moving = False
            print("Robô simulado parado")

    def get_and_reset_ticks(self) -> dict:
        """
        Fornece a contagem de ticks desde a última chamada e a zera.
        Esta é a "ponte" para o RobotNavigator usar a odometria.
        """
        ticks = {
            "left": self.left_hall_ticks,
            "right": self.right_hall_ticks
        }
        self.left_hall_ticks = 0
        self.right_hall_ticks = 0
        return ticks

    def get_real_time_speed(self) -> dict:
        """
        Retorna a velocidade atual calculada em ticks/segundo.
        """
        return {"left": self.current_left_tps, "right": self.current_right_tps}

    def stop(self):
        """
        Para todos os motores de forma definitiva, desativando o PID.
        """
        if hasattr(self, 'pid_left'):
            # --- NOVO: Desliga o interruptor do PID e corta a energia ---
            self.pid_enabled = False
            self.pid_left.reset()
            self.pid_right.reset()
            
            # Comando de parada definitivo, ignora o PID
            self._set_motor_speed_real("left", 0)
            self._set_motor_speed_real("right", 0)
            print("DEBUG: Controle PID DESATIVADO e motores parados.")
        else:
            self.set_speed(0, 0)

    def cleanup(self):
        """Libera os recursos do GPIO ao encerrar."""
        if GPIO_AVAILABLE and GPIO:
            print("Limpando recursos do GPIO.")
            self.pwm_D.stop()
            self.pwm_E.stop()
            GPIO.cleanup()