"""
Arquivo de configuração do projeto Robô Garçom Autônomo.
"""

import platform
import os

def is_raspberry_pi():
    """Verifica se está rodando em um Raspberry Pi."""
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().lower()
            return 'raspberry pi' in model
    except:
        return False

def is_development():
    """Verifica se está em ambiente de desenvolvimento."""
    return not is_raspberry_pi()

# Configurações específicas do ambiente
GPIO_AVAILABLE = is_raspberry_pi()
LIDAR_AVAILABLE = False  # Mude para True quando os sensores chegarem

# Configurações do ambiente
ENVIRONMENT_WIDTH = 6.0  # metros
ENVIRONMENT_HEIGHT = 12.0  # metros
MAP_WIDTH = int(ENVIRONMENT_WIDTH)  # metros
MAP_HEIGHT = int(ENVIRONMENT_HEIGHT)  # metros
MAP_SCALE = 56.66  # pixels por metro (ajustado para mostrar grids de 0.5m com 70% de aumento)

# Configurações do robô
ROBOT_INITIAL_POSITION = (5.7, 11.5)  # (x, y) em metros - posição central na parte inferior
ROBOT_INITIAL_ANGLE = 270  # graus - apontando para cima
ROBOT_SPEED = 2.0  # metros por segundo
ROBOT_TURN_SPEED = 300  # graus por segundo
ROBOT_FORWARD_SPEED = 2.0  # metros por segundo
ROBOT_MAX_SPEED = 3.0  # metros por segundo

# Configurações de simulação
SIMULATION_TIMESTEP = 0.1  # segundos
SIMULATION_UPDATE_RATE = 10  # Hz

# Configurações de navegação
NAVIGATION_GOAL_TOLERANCE = 0.1  # metros (aumentado para 10cm)
NAVIGATION_ANGLE_TOLERANCE = 10  # graus (aumentado para 10 graus)
NAVIGATION_OBSTACLE_DISTANCE = 0.5  # metros

# Configurações de segurança
EMERGENCY_STOP_DISTANCE = 0.3  # metros
MAX_SPEED = 1.0  # metros por segundo
MAX_TURN_SPEED = 90  # graus por segundo

# Configurações de interface
INTERFACE_UPDATE_RATE = 10  # Hz
INTERFACE_GRID_SIZE = 1  # metros
INTERFACE_POINT_SIZE = 10  # pixels
INTERFACE_ROBOT_SIZE = 15  # pixels
INTERFACE_DIRECTION_LENGTH = 30  # pixels

# Configurações de banco de dados
DATABASE_PATH = "data/robot.db"
DATABASE_VERSION = "1.0"

# Configurações de logging
LOG_LEVEL = "INFO"
LOG_FILE = "logs/robot.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Configurações de desenvolvimento
DEBUG = True
SIMULATION_MODE = True

# Configurações da interface
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
WINDOW_TITLE = "Robô Garçom Autônomo"

# Mensagem de ambiente (executada apenas quando o módulo é importado diretamente)
if __name__ == '__main__':
    if is_development():
        print("Executando em modo de desenvolvimento (simulação)")
    else:
        print("Executando em Raspberry Pi")
        if not LIDAR_AVAILABLE:
            print("Aviso: Sensores LIDAR não disponíveis (modo simulado)")

# Configurações do RPLIDAR
RPLIDAR_PORT = "/dev/ttyUSB0"  # Porta padrão do RPLIDAR
RPLIDAR_BAUDRATE = 115200
RPLIDAR_TIMEOUT = 1.0  # segundos

# Configurações de simulação
SIMULATION_FREQUENCY = 10.0  # Hz
SIMULATION_OBSTACLE_COUNT = 3
SIMULATION_DEFAULT_DISTANCE = 5.0  # metros

# Configurações de segurança
MIN_SAFE_DISTANCE = 0.5  # metros

# Configurações da interface
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
WINDOW_TITLE = "Robô Garçom Autônomo" 