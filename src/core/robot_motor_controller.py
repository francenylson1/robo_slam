# modules/robot_motor_controller.py
import time
import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.environment import GPIO_AVAILABLE

class RobotMotorController:
    def __init__(self):
        self.left_speed = 0
        self.right_speed = 0
        self.is_moving = False
        print("Inicializando controlador de motores em modo simulado")
        
        # Inicializa GPIO apenas se estiver no Raspberry Pi
        if GPIO_AVAILABLE:
            try:
                import RPi.GPIO as GPIO
                self.GPIO = GPIO
                self.GPIO.setmode(GPIO.BCM)
                # Configuração dos pinos GPIO
                self.LEFT_MOTOR_PINS = (17, 18)  # Ajuste conforme seu hardware
                self.RIGHT_MOTOR_PINS = (22, 23)  # Ajuste conforme seu hardware
                
                # Configura os pinos como saída
                for pin in self.LEFT_MOTOR_PINS + self.RIGHT_MOTOR_PINS:
                    self.GPIO.setup(pin, self.GPIO.OUT)
            except ImportError:
                print("GPIO não disponível - modo simulado")
        else:
            print("Executando em modo simulado (sem GPIO)")

    def set_speed(self, left_speed, right_speed):
        """Define a velocidade dos motores (-100 a 100)"""
        self.left_speed = max(-100, min(100, left_speed))
        self.right_speed = max(-100, min(100, right_speed))
        self._simulate_movement()
    
    def _set_gpio_speed(self):
        """Controla os motores via GPIO"""
        # Implementação real do controle dos motores
        # Ajuste conforme seu hardware
        pass
    
    def _simulate_movement(self):
        """Simula o movimento dos motores"""
        if self.left_speed != 0 or self.right_speed != 0:
            self.is_moving = True
            print(f"Simulando movimento - Motor Esquerdo: {self.left_speed}%, Motor Direito: {self.right_speed}%")
        else:
            self.is_moving = False
            print("Robô parado")

    def stop(self):
        """Para os motores"""
        self.set_speed(0, 0)

    def cleanup(self):
        """Limpa os recursos"""
        self.stop()