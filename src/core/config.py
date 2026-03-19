"""
Arquivo de configuração do projeto Robô Garçom Autônomo.
"""

import platform
import os
import logging

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
LIDAR_AVAILABLE = False  # Legado — uso geral de Lidar
# C1 integrado à navegação: parada automática quando obstáculo < LIDAR_OBSTACLE_MIN_DISTANCE
# REATIVADO (16/03/2026): calibração definiu frente=350°, cone 60° (evita corpo 120°–240°)
LIDAR_C1_ENABLED = True  # True = tenta conectar C1 na Pi; False = desativa
LIDAR_OBSTACLE_MIN_DISTANCE = 0.85  # Parar motores se obstáculo < 85 cm (aumentado de 60cm; testes: lixeira às vezes não detectada)
# Backend do C1: "rplidarc1" ou "pyrplidarsdk" (SDK oficial SLAMTEC)
# pyrplidarsdk testado como alternativa — rplidarc1 apresentou parada inconsistente (Mar 2026)
# C1 exige baudrate 460800 (já configurado). Vide docs/INTEGRACAO_PYRPLIDARSDK_C1_MAR2026.md
LIDAR_C1_BACKEND = "pyrplidarsdk"  # SDK oficial; use "rplidarc1" para voltar à lib anterior

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

# Posição inicial do robô em coordenadas do mundo (metros reais).
# Origem física: X=3.40m da parede oeste, Y=4.24m da parede sul → pixel PGM (74, 162).
# Com YAML corrigido (0.047808 m/px): world = pixel × resolução → (74×0.047808, 162×0.047808) = (3.54, 7.74).
# ATENÇÃO: Este valor é sobrescrito por _set_robot_initial_position_from_pgm() ao carregar PGM.
# CORREÇÃO 19/03/2026: YAML _90 e _270 corrigidos de 0.023904 → 0.047808 m/px (estava na metade).
# Sala real: 6.26m × 12.00m. Com YAML correto a posição calculada será (~3.54, ~7.74).
ROBOT_INITIAL_POSITION = (3.54, 7.74)  # metros reais (atualizado após correção do YAML)
ROBOT_INITIAL_ANGLE = 270            # graus - apontando para cima

# Configurações de simulação
SIMULATION_TIMESTEP = 0.1  # segundos
SIMULATION_UPDATE_RATE = 10  # Hz

# Configurações de navegação
NAVIGATION_GOAL_TOLERANCE = 0.20  # 20cm - Distância para considerar que chegou
NAVIGATION_ANGLE_TOLERANCE = 5.0   # 5 graus - Força um alinhamento melhor antes de avançar
NAVIGATION_OBSTACLE_DISTANCE = 0.35  # 35cm - Reduzido para robô menor (era 0.5m)

# Configurações de ida/volta
# Tempo de pausa no destino antes de retornar à base.
# Para uso real (garçom): aumentar para 10–30s dependendo da operação.
ARRIVAL_PAUSE_TIME = 5.0           # segundos parado no POI antes de retornar

# Timeout máximo para a navegação de IDA (evita loop infinito se robô travar).
# 300s (5 min): permite múltiplas paradas para usuários se servirem (ex.: garçom).
# Watchdog só cancela se obstáculo C1 bloquear durante todo o tempo.
NAVIGATION_MAX_DURATION_S = 300.0  # segundos máximos para chegar ao POI

# Timeout máximo para a navegação de VOLTA (watchdog de retorno).
# Mesmo critério da ida: garante que o robô não fique preso retornando.
RETURN_MAX_DURATION_S = 300.0      # segundos máximos para retornar à base

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

def setup_logging():
    """Configura o sistema de logging centralizado do projeto."""
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

# Mensagem de ambiente (executada apenas quando o módulo é importado diretamente)
if __name__ == '__main__':
    setup_logging()
    if is_development():
        logging.info("Executando em modo de desenvolvimento (simulação)")
    else:
        logging.info("Executando em Raspberry Pi")
        if not LIDAR_AVAILABLE:
            logging.warning("Sensores LIDAR não disponíveis (modo simulado)")

# Configurações do RPLIDAR
RPLIDAR_PORT = "/dev/ttyUSB0"  # Porta padrão do RPLIDAR
RPLIDAR_BAUDRATE = 115200
RPLIDAR_TIMEOUT = 1.0  # segundos

# Configurações do IMU BNO08x (I2C: SDA, SCL + GPIO)
# RST em GPIO 26: o script deixa em HIGH no início (sensor sai do reset) e não passa o pino à lib (evita ruído).
# Se RST não estiver conectado, use None. Se "device not found", use 26 para o script driver RST em HIGH.
BNO08X_I2C_ADDRESS = 0x4B       # BNO085 default (0x4B para BNO080)
BNO08X_GPIO_RST = 26            # GPIO para RST: 26 = driver HIGH no início (sensor visível); None = não tocar no pino
BNO08X_GPIO_INT = 27            # Pino GPIO para interrupção (data ready - opcional, uso futuro)

# Correção de rumo (linha reta) com BNO08x - usada por teleop e testes
# Modo só correção: ganhos conservadores para evitar sobrecorreção (19/03/2026)
BNO_STRAIGHT_KP = 0.35          # Reduzido de 0.7 para correções mais suaves
BNO_STRAIGHT_MAX_CORRECTION_TPS = 8.0    # Limite de TPS (era 12)
# True = quando o robô curva para a esquerda, corrigir acelerando roda direita (convenção deste robô)
BNO_STRAIGHT_INVERT_CORRECTION = True
# TPS para giros no lugar (menu, teleop e testes BNO) - alinhado com navegação
TURN_TPS_DEFAULT = 12.0
# Timeout (s) para obter a primeira leitura válida de yaw antes de linha reta (evita "BNO sem leitura")
BNO_FIRST_READ_TIMEOUT = 2.5
# Navegação: False = BNO desligado (estado estável); True = BNO ativo
# BNO desativado: testes 19/03 (fusão e só correção) causaram deriva, passou do POI, parada inconsistente
USE_BNO_IN_NAVIGATION = False

# Fusão BNO na pose (só quando USE_BNO_IN_NAVIGATION=True)
USE_BNO_POSE_FUSION = False

# Filtro complementar BNO: peso do BNO na fusão de ângulo (só quando USE_BNO_POSE_FUSION=True)
BNO_FILTER_ALPHA = 0.15

# Rejeição de spike: ignora leitura BNO se variar mais que este valor entre ciclos (graus)
# Logs mostraram variação máxima de 0.2° → threshold de 5° nunca dispara em condições normais
BNO_SPIKE_THRESHOLD_DEG = 5.0
# Fase 1 – BNO só nas retas: quando True, ângulo da pose usa BNO apenas se |Δθ| < STRAIGHT_ANGLE_THRESHOLD_DEG
USE_BNO_ON_STRAIGHTS_ONLY = True
# 0.0 = BNO não sobrescreve o ângulo odométrico (evita travamento do ângulo virtual durante giros intencionais).
# O BNO continua sendo usado apenas para correção de trajetória em linha reta (_apply_bno_straight_correction).
# Problema identificado: threshold > 0 fazia o BNO bloquear o ângulo virtual durante correções lentas
# (< 3°/ciclo), impedindo que a odometria rastreasse giros físicos de 90-180°.
STRAIGHT_ANGLE_THRESHOLD_DEG = 0.0

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