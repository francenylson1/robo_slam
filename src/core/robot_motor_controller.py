# modules/robot_motor_controller.py
import time
import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.environment import GPIO_AVAILABLE

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
        
        if GPIO_AVAILABLE and GPIO:
            print("Inicializando controlador de motores em MODO REAL (Raspberry Pi).")
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # PINOS DO MOTOR ESQUERDO
            self.dir_E = 5      # Direção
            self.break_E = 6    # Freio
            self.speed_E = 18   # PWM para Velocidade

            # PINOS DO MOTOR DIREITO
            self.dir_D = 23     # Direção
            self.break_D = 24   # Freio
            self.speed_D = 12   # PWM para Velocidade
            
            # Configura todos os pinos como saída
            for pin in [self.dir_E, self.break_E, self.speed_E, self.dir_D, self.break_D, self.speed_D]:
                GPIO.setup(pin, GPIO.OUT)

            # Inicializa PWM a 20Hz para controle de velocidade suave
            self.pwm_D = GPIO.PWM(self.speed_D, 20)
            self.pwm_E = GPIO.PWM(self.speed_E, 20)
            self.pwm_D.start(0)
            self.pwm_E.start(0)

            # Ativa o freio dos motores como estado inicial seguro
            GPIO.output(self.break_D, GPIO.HIGH)
            GPIO.output(self.break_E, GPIO.HIGH)
        else:
            print("Inicializando controlador de motores em MODO SIMULADO.")

    def set_speed(self, left_speed: float, right_speed: float):
        """
        Define a velocidade dos motores.
        Valores de -100 a 100, onde > 0 é para frente e < 0 é para trás.
        """
        self.left_speed_percent = max(-100, min(100, left_speed))
        self.right_speed_percent = max(-100, min(100, right_speed))
        
        if GPIO_AVAILABLE and GPIO:
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

    def stop(self):
        """Para todos os motores e ativa os freios."""
        self.set_speed(0, 0)

    def cleanup(self):
        """Libera os recursos do GPIO ao encerrar."""
        if GPIO_AVAILABLE and GPIO:
            print("Limpando recursos do GPIO.")
            self.pwm_D.stop()
            self.pwm_E.stop()
            GPIO.cleanup()