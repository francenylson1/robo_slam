import platform
import os

# Configurações específicas do ambiente
GPIO_AVAILABLE = False  # Sempre False em desenvolvimento
LIDAR_AVAILABLE = False  # Sempre False em desenvolvimento

print("Executando em modo de desenvolvimento (simulação)")

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

# Mensagem de ambiente
if is_development():
    print("Executando em modo de desenvolvimento (simulação)")
else:
    print("Executando em Raspberry Pi")
    if not LIDAR_AVAILABLE:
        print("Aviso: Sensores LIDAR não disponíveis (modo simulado)")

# Exporta as variáveis
__all__ = ['GPIO_AVAILABLE', 'LIDAR_AVAILABLE', 'is_raspberry_pi', 'is_development'] 