"""
Cliente USB/API para comunicação com Slamtec C1 Lidar
Suporta detecção via USB Serial, API REST e USB direto.
"""

import sys
from pathlib import Path
from typing import Dict, Optional
import logging
import time

# Garante que o diretório raiz esteja no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from src.core.slamware_c1_uploader import SlamwareC1Uploader

logger = logging.getLogger(__name__)


class C1USBClient:
    """
    Cliente para comunicação com Slamtec C1 via USB/API.
    
    Suporta múltiplos métodos de conexão:
    - API REST (SLAMWARE) - via rede
    - USB Serial - via porta serial
    - USB direto - via protocolo USB (futuro)
    """
    
    # IDs USB conhecidos do C1 (Vendor ID / Product ID)
    # Slamtec C1 pode usar diferentes chips USB-UART
    C1_USB_VIDS = [
        0x10C4,  # Silicon Labs CP210x
        0x0403,  # FTDI
        0x1A86,  # CH340
    ]
    
    # Características específicas do C1
    # C1 usa protocolo RPLIDAR com baudrate 460800
    C1_BAUDRATES = [460800, 115200, 230400, 921600]  # 460800 é o padrão do C1
    C1_DEFAULT_BAUDRATE = 460800  # Baudrate correto do C1
    
    # Comandos RPLIDAR para identificação do C1
    C1_RPLIDAR_CMD_GET_HEALTH = bytes([0xA5, 0x52])
    C1_RPLIDAR_CMD_GET_INFO = bytes([0xA5, 0x50])
    C1_IDENTIFICATION_COMMANDS = [
        C1_RPLIDAR_CMD_GET_HEALTH,  # Comando RPLIDAR Get Health
        C1_RPLIDAR_CMD_GET_INFO,    # Comando RPLIDAR Get Info
    ]
    
    # Portas padrão da API
    DEFAULT_API_IP = "192.168.1.101"
    DEFAULT_API_PORT = 1445
    
    def __init__(self, api_ip: Optional[str] = None, api_port: int = None):
        """
        Inicializa o cliente C1.
        
        Args:
            api_ip: Endereço IP para API REST (padrão: 192.168.1.101)
            api_port: Porta da API REST (padrão: 1445)
        """
        self.api_ip = api_ip or self.DEFAULT_API_IP
        self.api_port = api_port or self.DEFAULT_API_PORT
        self.api_client: Optional[SlamwareC1Uploader] = None
        self.serial_port: Optional[serial.Serial] = None
        self.connection_type: Optional[str] = None
        self.connected = False
    
    def detect_c1(self) -> Dict:
        """
        Detecta C1 conectado via diferentes métodos.
        
        Returns:
            Dicionário com informações de detecção:
            {
                'found': bool,
                'type': str,  # 'api', 'serial', 'usb' ou None
                'port': str,  # Porta/endereço detectado
                'info': dict  # Informações adicionais
            }
        """
        detection = {
            'found': False,
            'type': None,
            'port': None,
            'info': {}
        }
        
        # Método 1: Tentar API REST
        logger.info("Tentando detectar C1 via API REST...")
        api_detected = self._detect_via_api()
        if api_detected:
            detection['found'] = True
            detection['type'] = 'api'
            detection['port'] = f"{self.api_ip}:{self.api_port}"
            detection['info'] = api_detected
            logger.info(f"✅ C1 detectado via API em {detection['port']}")
            return detection
        
        # Método 2: Tentar USB Serial
        if SERIAL_AVAILABLE:
            logger.info("Tentando detectar C1 via USB Serial...")
            serial_detected = self._detect_via_serial()
            if serial_detected:
                detection['found'] = True
                detection['type'] = 'serial'
                detection['port'] = serial_detected.get('port', 'unknown')
                detection['info'] = serial_detected
                logger.info(f"✅ C1 detectado via Serial em {detection['port']}")
                return detection
        
        # Método 3: Tentar USB direto (futuro)
        # TODO: Implementar detecção USB direta quando necessário
        
        logger.warning("❌ C1 não detectado em nenhum método")
        return detection
    
    def _detect_via_api(self) -> Optional[Dict]:
        """
        Detecta C1 via API REST com validação detalhada.
        
        Returns:
            Dicionário com informações do dispositivo ou None
        """
        try:
            if not REQUESTS_AVAILABLE:
                logger.warning("Biblioteca 'requests' não disponível")
                return None
            
            api_client = SlamwareC1Uploader(self.api_ip, self.api_port)
            
            # Validação detalhada
            validation = {
                'connection_ok': False,
                'device_info_ok': False,
                'api_endpoints_ok': False,
                'device_type': None
            }
            
            if api_client.check_connection():
                validation['connection_ok'] = True
                
                # Obtém informações do dispositivo
                info = api_client.get_device_info()
                if info:
                    validation['device_info_ok'] = True
                    validation['device_type'] = info.get('device_type') or info.get('model')
                    
                    # Verifica se é realmente um C1
                    device_str = str(info).upper()
                    if 'C1' in device_str or 'SLAMTEC' in device_str:
                        validation['c1_confirmed'] = True
                
                # Testa endpoints específicos do C1
                endpoints_to_test = [
                    '/api/v1/status',
                    '/api/v1/device/info',
                    '/api/v1/maps'
                ]
                
                working_endpoints = []
                for endpoint in endpoints_to_test:
                    try:
                        response = api_client.session.get(
                            f"{api_client.base_url}{endpoint}",
                            timeout=2
                        )
                        if response.status_code == 200:
                            working_endpoints.append(endpoint)
                    except:
                        pass
                
                validation['api_endpoints_ok'] = len(working_endpoints) > 0
                validation['working_endpoints'] = working_endpoints
                
                return {
                    'method': 'api',
                    'ip': self.api_ip,
                    'port': self.api_port,
                    'device_info': info or {},
                    'validated': True,
                    'validation_details': validation
                }
        except Exception as e:
            logger.debug(f"Erro ao detectar via API: {e}")
        
        return None
    
    def _detect_via_serial(self) -> Optional[Dict]:
        """
        Detecta C1 via porta serial USB com validação específica.
        
        Returns:
            Dicionário com informações da porta e validação ou None
        """
        if not SERIAL_AVAILABLE:
            return None
        
        try:
            ports = serial.tools.list_ports.comports()
            candidates = []
            
            # Fase 1: Identificar portas candidatas
            for port in ports:
                # Verifica se é dispositivo USB Serial compatível
                if port.vid in self.C1_USB_VIDS or 'USB' in port.description.upper():
                    candidates.append(port)
            
            if not candidates:
                logger.debug("Nenhuma porta USB Serial encontrada")
                return None
            
            # Fase 2: Validar cada candidato
            for port in candidates:
                validation_result = self._validate_c1_serial_port(port)
                if validation_result:
                    return {
                        'method': 'serial',
                        'port': port.device,
                        'description': port.description,
                        'vid': port.vid,
                        'pid': port.pid,
                        'serial_number': port.serial_number,
                        'validated': True,
                        'validation_details': validation_result
                    }
            
            # Se nenhum foi validado, retorna o primeiro candidato como possível
            if candidates:
                port = candidates[0]
                logger.warning(f"Porta {port.device} detectada mas não validada como C1")
                return {
                    'method': 'serial',
                    'port': port.device,
                    'description': port.description,
                    'vid': port.vid,
                    'pid': port.pid,
                    'serial_number': port.serial_number,
                    'validated': False,
                    'validation_details': {'note': 'Dispositivo detectado mas não validado como C1'}
                }
        except Exception as e:
            logger.debug(f"Erro ao detectar via Serial: {e}")
        
        return None
    
    def _validate_c1_serial_port(self, port) -> Optional[Dict]:
        """
        Valida se uma porta serial é realmente um C1.
        
        Args:
            port: Objeto de porta serial
        
        Returns:
            Dicionário com detalhes de validação ou None
        """
        validation_details = {
            'port_accessible': False,
            'baudrate_tested': None,
            'response_received': False,
            'c1_signature_found': False
        }
        
        test_serial = None
        try:
            # Testa diferentes baudrates
            for baudrate in self.C1_BAUDRATES:
                try:
                    test_serial = serial.Serial(
                        port.device,
                        baudrate=baudrate,
                        timeout=0.5,
                        write_timeout=0.5
                    )
                    validation_details['port_accessible'] = True
                    validation_details['baudrate_tested'] = baudrate
                    
                    # Limpa buffer
                    test_serial.reset_input_buffer()
                    test_serial.reset_output_buffer()
                    
                    # Tenta enviar comando de identificação RPLIDAR
                    for cmd in self.C1_IDENTIFICATION_COMMANDS:
                        try:
                            test_serial.reset_input_buffer()
                            test_serial.write(cmd)
                            test_serial.flush()
                            
                            # Aguarda resposta (RPLIDAR responde rápido)
                            time.sleep(0.3)
                            if test_serial.in_waiting > 0:
                                response = test_serial.read(test_serial.in_waiting)
                                validation_details['response_received'] = True
                                
                                # Verifica se resposta contém assinatura RPLIDAR (0xA5 0x5A)
                                if self._check_c1_signature(response):
                                    validation_details['c1_signature_found'] = True
                                    test_serial.close()
                                    return validation_details
                        except Exception:
                            continue
                    
                    # Se chegou aqui, porta está acessível mas não respondeu como C1
                    test_serial.close()
                    return validation_details if validation_details['port_accessible'] else None
                    
                except (serial.SerialException, OSError) as e:
                    if test_serial:
                        try:
                            test_serial.close()
                        except:
                            pass
                    continue
            
            return None
        except Exception as e:
            logger.debug(f"Erro ao validar porta {port.device}: {e}")
            if test_serial:
                try:
                    test_serial.close()
                except:
                    pass
            return None
    
    def _check_c1_signature(self, data: bytes) -> bool:
        """
        Verifica se os dados recebidos contêm assinatura do C1 (RPLIDAR).
        
        Args:
            data: Dados recebidos
        
        Returns:
            True se assinatura encontrada
        """
        if not data or len(data) < 2:
            return False
        
        # Header RPLIDAR: 0xA5 0x5A
        if data[:2] == bytes([0xA5, 0x5A]):
            return True
        
        # Verifica se contém header RPLIDAR em qualquer posição
        if bytes([0xA5, 0x5A]) in data:
            return True
        
        return False
    
    def connect(self, connection_type: Optional[str] = None) -> bool:
        """
        Conecta ao C1 usando o método detectado ou especificado.
        
        Args:
            connection_type: Tipo de conexão ('api', 'serial' ou None para auto)
        
        Returns:
            True se conexão bem-sucedida
        """
        if self.connected:
            logger.warning("Já está conectado ao C1")
            return True
        
        # Se tipo não especificado, detecta automaticamente
        if connection_type is None:
            detection = self.detect_c1()
            if not detection['found']:
                logger.error("Não foi possível detectar C1")
                return False
            connection_type = detection['type']
        
        # Conecta usando o método apropriado
        if connection_type == 'api':
            return self._connect_api()
        elif connection_type == 'serial':
            return self._connect_serial()
        else:
            logger.error(f"Tipo de conexão não suportado: {connection_type}")
            return False
    
    def _connect_api(self) -> bool:
        """Conecta via API REST."""
        try:
            self.api_client = SlamwareC1Uploader(self.api_ip, self.api_port)
            if self.api_client.check_connection():
                self.connection_type = 'api'
                self.connected = True
                logger.info(f"Conectado ao C1 via API em {self.api_ip}:{self.api_port}")
                return True
        except Exception as e:
            logger.error(f"Erro ao conectar via API: {e}")
        
        return False
    
    def _connect_serial(self, port: Optional[str] = None, baudrate: int = None) -> bool:
        """
        Conecta via porta serial USB.
        
        Args:
            port: Porta serial (None para auto-detectar)
            baudrate: Velocidade de transmissão (None para usar padrão do C1: 460800)
        """
        if not SERIAL_AVAILABLE:
            logger.error("Biblioteca 'pyserial' não disponível")
            return False
        
        try:
            # Se porta não especificada, detecta
            if port is None:
                detection = self._detect_via_serial()
                if not detection:
                    logger.error("Não foi possível detectar porta serial")
                    return False
                port = detection['port']
            
            # Usa baudrate padrão do C1 se não especificado
            if baudrate is None:
                baudrate = self.C1_DEFAULT_BAUDRATE
            
            self.serial_port = serial.Serial(
                port,
                baudrate=baudrate,
                timeout=1.0
            )
            self.connection_type = 'serial'
            self.connected = True
            logger.info(f"Conectado ao C1 via Serial em {port}")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar via Serial: {e}")
            return False
    
    def disconnect(self):
        """Desconecta do C1."""
        if not self.connected:
            return
        
        if self.connection_type == 'api':
            self.api_client = None
        elif self.connection_type == 'serial' and self.serial_port:
            try:
                self.serial_port.close()
            except Exception as e:
                logger.warning(f"Erro ao fechar porta serial: {e}")
            self.serial_port = None
        
        self.connection_type = None
        self.connected = False
        logger.info("Desconectado do C1")
    
    def is_connected(self) -> bool:
        """Verifica se está conectado."""
        return self.connected
    
    def get_connection_type(self) -> Optional[str]:
        """Retorna o tipo de conexão atual."""
        return self.connection_type
    
    def get_api_client(self) -> Optional[SlamwareC1Uploader]:
        """Retorna o cliente API (se conectado via API)."""
        return self.api_client if self.connection_type == 'api' else None

