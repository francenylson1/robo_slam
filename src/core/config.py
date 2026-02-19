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
EMERGENCY_STOP_DISTANCE = 0.15  # 15cm - Reduzido para robô menor (40cm de largura)
# A margem de segurança deve ser o RAIO do robô + uma folga.
# Raio (20cm para um robô de 40cm de largura) + Folga (11cm para permitir passagem entre áreas) = 31cm
# 🎯 AJUSTADO: Configurado para robô de 40cm de largura
# Espaço mínimo necessário entre áreas: 40cm (robô) + 2×31cm (inflação) = 102cm ≈ 1.0m
FORBIDDEN_AREA_INFLATION_RADIUS = 0.20 # 31cm de margem de segurança (raio 20cm + folga 11cm)

# Configurações do robô
ROBOT_WIDTH = 0.40                # Largura/Diâmetro do robô em metros (40cm)
ROBOT_SPEED = 0.30               # AUMENTADO 20% para teste (era 0.25, era 0.15 originalmente)
ROBOT_MAX_SPEED = 0.30           # Alinhado com ROBOT_SPEED (aumentado 20%)
SIMULATION_SPEED_FACTOR = 8.0    # Fator de multiplicação para a velocidade na simulação
ROBOT_TURN_SPEED = 27.0          # REDUZIDO para 30% do valor anterior (era 90.0). Velocidade de giro (graus/s).
ROBOT_ADJUSTMENT_TURN_SPEED = 0.25 # Velocidade de giro para ajustes finos (lenta e segura).

# Constante legada - Manter por compatibilidade, mas com valor seguro
ROBOT_FORWARD_SPEED = 0.30         # (LEGADO) Alinhado com ROBOT_SPEED (aumentado 20%)

ROBOT_INITIAL_POSITION = (5.7, 11.5)  # (x, y) em metros - posição base inicial do robô (ajustado para dentro do mapa)
ROBOT_INITIAL_ANGLE = 270            # graus - apontando para cima

# Configurações de simulação
SIMULATION_TIMESTEP = 0.1  # segundos
SIMULATION_UPDATE_RATE = 10  # Hz

# Configurações de navegação
NAVIGATION_GOAL_TOLERANCE = 0.20  # 20cm - Distância para considerar que chegou
NAVIGATION_ANGLE_TOLERANCE = 5.0   # 5 graus - Força um alinhamento melhor antes de avançar
NAVIGATION_OBSTACLE_DISTANCE = 0.35  # 35cm - Reduzido para robô menor (era 0.5m)

# Configurações de precisão avançada
NAVIGATION_ULTRA_PRECISION_TOLERANCE = 0.02  # 2cm - Máxima precisão para chegada ao destino
NAVIGATION_FINE_APPROACH_DISTANCE = 0.30  # 30cm - Reduzido para robô menor (era 0.5m)
NAVIGATION_PRECISION_APPROACH_DISTANCE = 0.10  # 10cm - Distância para aproximação precisa
NAVIGATION_ULTRA_PRECISION_ANGLE_TOLERANCE = 1.5  # graus - Tolerância de ângulo ultra-precisa

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

# Configurações do IMU BNO08x (I2C: SDA, SCL + GPIO)
# Fiação: SDA/SCL no I2C; GPIO 26 = RST (reset); GPIO 27 = INT (interrupto)
BNO08X_I2C_ADDRESS = 0x4A       # BNO085 default (0x4B para BNO080)
BNO08X_GPIO_RST = 26            # Pino GPIO para reset (obrigatório para inicialização)
BNO08X_GPIO_INT = 27            # Pino GPIO para interrupção (data ready - opcional, uso futuro)

# Configurações de simulação
SIMULATION_FREQUENCY = 10.0  # Hz
SIMULATION_OBSTACLE_COUNT = 3
SIMULATION_DEFAULT_DISTANCE = 5.0  # metros

# Configurações de segurança
MIN_SAFE_DISTANCE = 0.35  # 35cm - Reduzido para robô menor (era 0.5m)

# Configurações da interface
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
WINDOW_TITLE = "Robô Garçom Autônomo"

# Configuracoes do PID e caracteristicas fisicas do robo
ROBOT_WHEEL_BASE_M = 0.378  # CORRIGIDO: Medida real da distância entre rodas (37.8cm)
ROBOT_WHEEL_CIRCUMFERENCE_M = 0.525 # Circunferencia da roda em metros (medida em 52.5cm)
ROBOT_WHEEL_RADIUS_M = ROBOT_WHEEL_CIRCUMFERENCE_M / (2 * 3.1415926535) # Raio calculado a partir da circunferencia
TICKS_PER_REVOLUTION = 45 # VALOR CALIBRADO: Medido experimentalmente em 45 ticks por volta completa da roda.

# === SISTEMA DE VELOCIDADES SEGURAS ===
# Baseado no protocolo de segurança: máximo 12-15% potência direta dos motores

# Velocidades escalonadas (TPS) respeitando limites de segurança
SPEED_SLOW_TPS = 20      # Lenta - até 8% potência máxima  (precisão máxima)
SPEED_NORMAL_TPS = 35    # Média - até 12% potência máxima (navegação normal)  
SPEED_FAST_TPS = 50      # Alta - até 15% potência máxima  (trajetos longos)

# Velocidade padrão (compatibilidade com código legado)
MANUAL_CONTROL_MAX_TPS = SPEED_NORMAL_TPS  # Usa velocidade média como padrão

# Perfis PID otimizados para cada velocidade
# PID SUAVE - Correção de vibração e instabilidade (2025-01-27)
# Parâmetros reduzidos para eliminar oscilação em motores potentes
PID_PROFILES = {
    'slow': {
        'Kp': 0.20, 'Ki': 0.12, 'Kd': 0.03,  # Reduzido: Kp-50%, Ki-60%, Kd-40%
        'output_limits': (-8, 8),    # 8% potência máxima
        'tps': SPEED_SLOW_TPS,
        'description': 'PID SUAVE - Precisão sem vibração'
    },
    'normal': {
        'Kp': 0.18, 'Ki': 0.10, 'Kd': 0.02,  # Reduzido: Kp-48%, Ki-60%, Kd-33%
        'output_limits': (-12, 12),  # 12% potência máxima
        'tps': SPEED_NORMAL_TPS,
        'description': 'PID SUAVE - Navegação estável'
    },
    'fast': {
        'Kp': 0.15, 'Ki': 0.08, 'Kd': 0.01,  # Reduzido: Kp-50%, Ki-60%, Kd mantido
        'output_limits': (-15, 15),  # 15% potência máxima (LIMITE SEGURANÇA)
        'tps': SPEED_FAST_TPS,
        'description': 'PID SUAVE - Velocidade controlada'
    }
}

# Configurações de segurança para validação automática
SAFETY_MAX_MOTOR_POWER_PERCENT = 15.0  # NUNCA exceder 15% da potência total
SAFETY_POWER_MONITOR_INTERVAL = 0.1    # Verificar a cada 100ms
SAFETY_POWER_VIOLATION_TIMEOUT = 0.2   # Máximo 200ms acima do limite antes de parada de emergência

# Limites de velocidade para o PID
# A linha abaixo foi MODIFICADA para usar ROBOT_SPEED como fonte única de verdade.
# Isso garante que a velocidade máxima seja a mesma que a velocidade de navegação.
MAX_LINEAR_SPEED_MS = ROBOT_SPEED  # Velocidade maxima para frente em metros/segundo.
MAX_ANGULAR_SPEED_RADS = 0.5