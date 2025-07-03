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
ENVIRONMENT_WIDTH = 6  # metros
ENVIRONMENT_HEIGHT = 12  # metros
MAP_WIDTH = int(ENVIRONMENT_WIDTH)
MAP_HEIGHT = int(ENVIRONMENT_HEIGHT)
MAP_GRID_SIZE = 0.1 # Tamanho da célula da grade em metros (10cm)
MAP_SCALE = 56.66  # pixels por metro (ajustado para mostrar grids de 0.5m com 70% de aumento)

# Configurações de segurança
EMERGENCY_STOP_DISTANCE = 0.2  # 20cm
# A margem de segurança deve ser o RAIO do robô + uma folga.
# Raio (30cm para um robô de 60cm de diâmetro) + Folga (5cm) = 35cm
FORBIDDEN_AREA_INFLATION_RADIUS = 0.35 # 35cm de margem de segurança

# Configurações do robô
ROBOT_WIDTH = 0.35
ROBOT_SPEED = 0.08               # Velocidade base de avanço em navegação (m/s) - 33% do anterior
SIMULATION_SPEED_FACTOR = 8.0    # Fator de multiplicação para a velocidade na simulação
ROBOT_TURN_SPEED = 25.0          # Velocidade de giro em navegação (graus/s)
ROBOT_ADJUSTMENT_TURN_SPEED = 0.15 # Velocidade de giro para ajustes finos (lenta e segura)

# Constante legada - Manter por compatibilidade, mas com valor seguro
ROBOT_FORWARD_SPEED = 0.08         # (LEGADO) Usado em funções antigas, igual a ROBOT_SPEED

ROBOT_INITIAL_POSITION = (5.7, 11.5) # (x, y) em metros - posição central na parte inferior
ROBOT_INITIAL_ANGLE = 270            # graus - apontando para cima

# Configurações de simulação
SIMULATION_TIMESTEP = 0.1  # segundos
SIMULATION_UPDATE_RATE = 10  # Hz

# Configurações de navegação
NAVIGATION_GOAL_TOLERANCE = 0.05  # 5cm - Distância para considerar que chegou
NAVIGATION_ANGLE_TOLERANCE = 3.0  # 3 graus, tolerância para alinhamento de ângulo
NAVIGATION_OBSTACLE_DISTANCE = 0.5  # metros

# Configurações de precisão avançada
NAVIGATION_ULTRA_PRECISION_TOLERANCE = 0.03  # metros (3cm - precisão ultra-alta para destinos)
NAVIGATION_FINE_APPROACH_DISTANCE = 0.15  # 15cm
NAVIGATION_PRECISION_APPROACH_DISTANCE = 0.08  # 8cm
NAVIGATION_ULTRA_PRECISION_ANGLE_TOLERANCE = 0.5  # graus (tolerância de ângulo ultra-precisa)

# Configurações de interface
INTERFACE_UPDATE_RATE = 10  # Hz
INTERFACE_GRID_SIZE = 1  # metros
INTERFACE_POINT_SIZE = 15  # pixels (mesmo tamanho do robô para facilitar navegação)
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
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
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

# Margem de segurança para áreas proibidas
FORBIDDEN_AREA_INFLATION_RADIUS = 0.15 # 15cm de margem de segurança