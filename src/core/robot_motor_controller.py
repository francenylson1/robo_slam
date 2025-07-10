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
        
        # --- NOVO: Atributos para o modo de simulação ---
        self.simulated_left_tps = 0.0
        self.simulated_right_tps = 0.0
        self.last_sim_time = time.time()
        
        # Atributos para feedback de velocidade
        self.left_hall_ticks = 0
        self.right_hall_ticks = 0
        self.last_speed_check_time = time.time()
        self.current_left_tps = 0.0
        self.current_right_tps = 0.0
        
        # --- NOVO: Evento para desligamento limpo das threads ---
        self.shutdown_event = threading.Event()
        
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
            # NOVOS GANHOS (MUITO MAIS CONSERVADORES) PARA ESTABILIZAR O ROBÔ EM BAIXA VELOCIDADE
            # O objetivo é eliminar o movimento circular.
            # AUMENTANDO O Ki PARA DAR MAIS "INSISTÊNCIA" AO ROBÔ NA APROXIMAÇÃO FINAL.
            # --- ATUALIZAÇÃO: Aumentando os limites de saída para dar mais força ao PID ---
            self.pid_left = PIDController(Kp=0.05, Ki=0.05, Kd=0.01, setpoint=0, output_limits=(-40, 40))
            self.pid_right = PIDController(Kp=0.05, Ki=0.05, Kd=0.01, setpoint=0, output_limits=(-40, 40))

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

        while not self.shutdown_event.is_set():
            # Leitura do sensor esquerdo
            try:
                current_state_E = GPIO.input(self.hall_E)
                if current_state_E == 1 and self.last_hall_E_state == 0:
                    self.left_hall_ticks += 1
                self.last_hall_E_state = current_state_E

                # Leitura do sensor direito
                current_state_D = GPIO.input(self.hall_D)
                if current_state_D == 1 and self.last_hall_D_state == 0:
                    self.right_hall_ticks += 1
                self.last_hall_D_state = current_state_D
            
            except RuntimeError:
                # Se o GPIO foi limpo, a thread deve parar.
                break
            
            # Pausa muito curta para evitar 100% de uso da CPU
            time.sleep(0.001) # Poll a ~1000Hz

    def _pid_control_loop(self):
        """
        Thread que executa o loop de controle PID continuamente.
        """
        if not GPIO_AVAILABLE:
            return
            
        while not self.shutdown_event.is_set():
            # --- NOVO: So executa o controle se o interruptor estiver ligado ---
            if not self.pid_enabled:
                time.sleep(0.1) # Dorme se desativado para nao usar CPU
                continue

            # 1. Calcula a velocidade real atual (ticks/s)
            self._update_current_speed()
            
            # 2. Calcula a saida de potencia usando o PID
            left_power = self.pid_left.update(self.current_left_tps)
            right_power = self.pid_right.update(self.current_right_tps)
            
            # 3. Aplica a potencia aos motores COM A LÓGICA DE DIREÇÃO CORRETA
            # Esta verificação garante que o código só rode no hardware real
            if GPIO_AVAILABLE and GPIO:
                # --- MOTOR ESQUERDO ---
                if left_power >= 0: # Para frente
                    GPIO.output(self.dir_E, GPIO.HIGH)
                else: # Para trás
                    GPIO.output(self.dir_E, GPIO.LOW)
                self.pwm_E.ChangeDutyCycle(min(abs(left_power), 100))

                # --- MOTOR DIREITO (CORRIGIDO) ---
                # A lógica de direção foi equalizada com o motor esquerdo (HIGH para frente).
                if right_power >= 0: # Para frente
                    GPIO.output(self.dir_D, GPIO.HIGH)
                else: # Para trás
                    GPIO.output(self.dir_D, GPIO.LOW)
                self.pwm_D.ChangeDutyCycle(min(abs(right_power), 100))

                # Libera os freios se houver qualquer potência
                if abs(left_power) > 0.1 or abs(right_power) > 0.1:
                    GPIO.output(self.break_E, GPIO.LOW)
                    GPIO.output(self.break_D, GPIO.LOW)
                else:
                    GPIO.output(self.break_E, GPIO.HIGH)
                    GPIO.output(self.break_D, GPIO.HIGH)
            
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
            # Em modo simulado, armazena a velocidade alvo para o cálculo de odometria
            print(f"Simulando velocidade alvo - Esquerda: {left_tps:.1f} tps, Direita: {right_tps:.1f} tps")
            self.simulated_left_tps = left_tps
            self.simulated_right_tps = right_tps


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
        
        # Correção: A condição anterior 'not hasattr(self, 'pid_left')' era sempre falsa.
        # A verificação correta é se o loop de controle PID está desabilitado.
        if GPIO_AVAILABLE and not self.pid_enabled:
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
            # Para frente - LÓGICA CORRETA restaurada com base na fiação do robô.
            # Esquerda = HIGH, Direita = LOW
            direction = GPIO.HIGH if motor == "left" else GPIO.LOW
        else:
            # Para trás - Lógica invertida da de cima.
            direction = GPIO.LOW if motor == "left" else GPIO.HIGH
        
        GPIO.output(pin_dir, direction)
        
        # Define a velocidade (Duty Cycle)
        duty_cycle = abs(speed_percent)
        pwm.ChangeDutyCycle(duty_cycle)

    def _simulate_movement(self):
        """Simula o movimento do robô para depuração sem hardware."""
        self.is_moving = self.left_speed_percent != 0 or self.right_speed_percent != 0
        # print(f"SIM: Movimento {'ativo' if self.is_moving else 'parado'}. "
        #       f"Velocidades: E={self.left_speed_percent}%, D={self.right_speed_percent}%")

    def get_and_reset_ticks(self) -> dict:
        """
        Retorna a contagem atual de ticks dos encoders e os zera.
        Esta função é crucial para o cálculo da odometria no RobotNavigator.
        Garante que os ticks sejam retornados como inteiros.
        """
        if GPIO_AVAILABLE:
            # Captura os ticks atuais de forma atômica (embora Python não tenha 'atomic' real,
            # a simplicidade da operação torna problemas de concorrência improváveis aqui)
            left_ticks = self.left_hall_ticks
            right_ticks = self.right_hall_ticks

            # Zera os contadores
            self.left_hall_ticks = 0
            self.right_hall_ticks = 0

            return {"left": int(left_ticks), "right": int(right_ticks)}
        else:
            # --- LÓGICA DE SIMULAÇÃO MELHORADA ---
            # Calcula o tempo decorrido desde a última chamada
            current_time = time.time()
            delta_time = current_time - self.last_sim_time
            self.last_sim_time = current_time
            
            # Calcula os ticks simulados com base na velocidade alvo e no tempo
            sim_left_ticks = self.simulated_left_tps * delta_time
            sim_right_ticks = self.simulated_right_tps * delta_time

            # Retorna os ticks simulados como inteiros
            return {"left": int(round(sim_left_ticks)), "right": int(round(sim_right_ticks))}


    def get_real_time_speed(self) -> dict:
        """
        Retorna a velocidade atual calculada em ticks por segundo (TPS).
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
        # --- NOVO: Zera também as velocidades simuladas ---
        self.simulated_left_tps = 0.0
        self.simulated_right_tps = 0.0

    def cleanup(self):
        """Limpa os recursos do GPIO de forma segura."""
        if GPIO_AVAILABLE and GPIO:
            print("INFO: Iniciando limpeza dos recursos do RobotMotorController...")
            # 1. Sinaliza para as threads pararem
            self.shutdown_event.set()
            
            # 2. Pequena pausa para permitir que as threads terminem seus loops
            time.sleep(0.1)
            
            # 3. Para os motores (garantia extra)
            self.stop()
            
            # 4. Limpa os pinos GPIO
            GPIO.cleanup()
            print("INFO: Limpeza do GPIO concluída.")