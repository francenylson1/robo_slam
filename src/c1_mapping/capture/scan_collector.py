"""
Coletor de Varreduras LIDAR
Coleta varreduras brutas do sensor C1 usando protocolo RPLIDAR.
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional
import time
import json
import logging

# Garante que o diretório raiz esteja no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from .c1_usb_client import C1USBClient
from .rplidar_parser import RPLIDARParser

logger = logging.getLogger(__name__)


class ScanCollector:
    """
    Coletor de varreduras LIDAR brutas do C1.
    
    Coleta dados de varreduras para processamento SLAM externo
    (caso o C1 não tenha SLAM interno ou seja necessário processar localmente).
    """
    
    def __init__(self, client: C1USBClient, output_dir: Path):
        """
        Inicializa o coletor de scans.
        
        Args:
            client: Cliente USB/API do C1
            output_dir: Diretório para salvar os scans coletados
        """
        self.client = client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.scans: List[Dict] = []
        self.collecting = False
        self.start_time: Optional[float] = None
        self.parser = RPLIDARParser()
        
        # Comandos RPLIDAR
        self.RPLIDAR_CMD_STOP = bytes([0xA5, 0x25])
        self.RPLIDAR_CMD_RESET = bytes([0xA5, 0x40])
        self.RPLIDAR_CMD_SCAN = bytes([0xA5, 0x20])
        self.RPLIDAR_CMD_GET_INFO = bytes([0xA5, 0x50])
        self.RPLIDAR_CMD_GET_HEALTH = bytes([0xA5, 0x52])
    
    def start_collection(self, duration: float = 60.0, collect_full_scans: bool = True):
        """
        Inicia coleta de varreduras do C1.
        
        Args:
            duration: Duração da coleta em segundos
            collect_full_scans: Se True, coleta scans completos (360°). Se False, coleta continuamente.
        """
        if not self.client.is_connected():
            logger.error("Cliente não está conectado ao C1")
            return
        
        if self.collecting:
            logger.warning("Coleta já está em andamento")
            return
        
        connection_type = self.client.get_connection_type()
        if connection_type != 'serial':
            logger.error("Coleta de scans requer conexão Serial (RPLIDAR)")
            return
        
        logger.info(f"Iniciando coleta de scans (duração: {duration}s)")
        
        self.collecting = True
        self.scans = []
        self.start_time = time.time()
        
        try:
            # Inicializa C1 para scan
            if not self._initialize_scan():
                logger.error("Falha ao inicializar scan do C1")
                return
            
            end_time = self.start_time + duration
            data_packets = []
            last_scan_time = time.time()
            
            logger.info("Coletando dados de scan...")
            
            while self.collecting and time.time() < end_time:
                # Lê dados disponíveis
                scan_data = self._collect_scan_data_continuous()
                if scan_data:
                    data_packets.extend(scan_data)
                
                # Processa dados periodicamente
                current_time = time.time()
                if current_time - last_scan_time > 0.5:  # Processa a cada 0.5s
                    if data_packets:
                        # Combina todos os pacotes em um único buffer
                        combined_data = b''.join(data_packets)
                        
                        if collect_full_scans:
                            # Tenta extrair scan completo
                            complete_scan = self.parser.extract_complete_scan(data_packets)
                            if complete_scan and len(complete_scan) > 50:  # Mínimo de pontos
                                scan_dict = {
                                    'timestamp': current_time,
                                    'points': complete_scan,
                                    'point_count': len(complete_scan),
                                    'source': 'rplidar'
                                }
                                self.scans.append(scan_dict)
                                logger.info(f"Scan completo #{len(self.scans)} coletado: {len(complete_scan)} pontos")
                                data_packets = []  # Limpa buffer após processar
                            else:
                                # Se não conseguiu scan completo, parse pontos individuais
                                all_points = []
                                for packet in data_packets:
                                    points = self.parser.parse_scan_data(packet)
                                    all_points.extend(points)
                                
                                if all_points and len(all_points) > 10:  # Mínimo de pontos
                                    scan_dict = {
                                        'timestamp': current_time,
                                        'points': all_points,
                                        'point_count': len(all_points),
                                        'source': 'rplidar'
                                    }
                                    self.scans.append(scan_dict)
                                    logger.info(f"Scan #{len(self.scans)} coletado: {len(all_points)} pontos")
                                    data_packets = []
                        else:
                            # Coleta contínua - parse todos os pontos
                            all_points = []
                            for packet in data_packets:
                                points = self.parser.parse_scan_data(packet)
                                all_points.extend(points)
                            
                            if all_points:
                                scan_dict = {
                                    'timestamp': current_time,
                                    'points': all_points,
                                    'point_count': len(all_points),
                                    'source': 'rplidar'
                                }
                                self.scans.append(scan_dict)
                                logger.info(f"Scan #{len(self.scans)} coletado: {len(all_points)} pontos")
                                data_packets = []
                    
                    last_scan_time = current_time
                
                time.sleep(0.01)  # Pequeno delay para não consumir CPU
            
            # Para scan
            self._stop_scan()
            
            # Salva scans coletados
            self._save_scans()
            
        except KeyboardInterrupt:
            logger.info("Coleta interrompida pelo usuário")
            self._stop_scan()
        except Exception as e:
            logger.error(f"Erro durante coleta: {e}", exc_info=True)
            self._stop_scan()
        finally:
            self.collecting = False
            logger.info(f"Coleta finalizada. Total de scans: {len(self.scans)}")
    
    def stop_collection(self):
        """Para a coleta de scans."""
        if self.collecting:
            logger.info("Parando coleta...")
            self.collecting = False
            self._stop_scan()
    
    def _collect_scan_via_api(self) -> Optional[Dict]:
        """
        Coleta scan via API REST.
        
        Returns:
            Dicionário com dados do scan ou None
        """
        try:
            api_client = self.client.get_api_client()
            if not api_client:
                return None
            
            # Tenta obter dados de scan via API
            # Endpoint pode variar conforme documentação do C1
            endpoints = [
                "/api/v1/lidar/scan",
                "/api/v1/scan",
                "/api/v1/sensor/scan"
            ]
            
            for endpoint in endpoints:
                try:
                    response = api_client.session.get(
                        f"{api_client.base_url}{endpoint}",
                        timeout=2
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            'timestamp': time.time(),
                            'data': data,
                            'source': 'api'
                        }
                except Exception:
                    continue
            
            logger.warning("Não foi possível obter scan via API")
            return None
        except Exception as e:
            logger.debug(f"Erro ao coletar scan via API: {e}")
            return None
    
    def _initialize_scan(self) -> bool:
        """
        Inicializa scan do C1 via protocolo RPLIDAR.
        
        Returns:
            True se inicialização bem-sucedida
        """
        try:
            serial_port = self.client.serial_port
            if not serial_port or not serial_port.is_open:
                logger.error("Porta serial não está aberta")
                return False
            
            # Reset
            logger.debug("Enviando comando RESET...")
            serial_port.reset_input_buffer()
            serial_port.write(self.RPLIDAR_CMD_RESET)
            serial_port.flush()
            time.sleep(1.0)  # Aguarda reset
            
            # Get Health
            logger.debug("Verificando saúde do C1...")
            serial_port.reset_input_buffer()
            serial_port.write(self.RPLIDAR_CMD_GET_HEALTH)
            serial_port.flush()
            time.sleep(0.3)
            
            if serial_port.in_waiting > 0:
                response = serial_port.read(serial_port.in_waiting)
                health = self.parser.parse_health_response(response[5:] if len(response) > 5 else response)
                logger.info(f"Status do C1: {health.get('status', 'unknown')}")
            
            # Start Scan
            logger.debug("Iniciando scan...")
            serial_port.reset_input_buffer()
            serial_port.write(self.RPLIDAR_CMD_SCAN)
            serial_port.flush()
            time.sleep(0.5)  # Aguarda scan iniciar
            
            logger.info("Scan iniciado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao inicializar scan: {e}")
            return False
    
    def _stop_scan(self):
        """Para o scan do C1."""
        try:
            serial_port = self.client.serial_port
            if serial_port and serial_port.is_open:
                logger.debug("Parando scan...")
                serial_port.write(self.RPLIDAR_CMD_STOP)
                serial_port.flush()
                time.sleep(0.2)
        except Exception as e:
            logger.warning(f"Erro ao parar scan: {e}")
    
    def _collect_scan_data_continuous(self) -> List[bytes]:
        """
        Coleta dados de scan continuamente.
        
        Returns:
            Lista de pacotes de dados recebidos
        """
        try:
            serial_port = self.client.serial_port
            if not serial_port or not serial_port.is_open:
                return []
            
            packets = []
            
            # Lê todos os dados disponíveis
            if serial_port.in_waiting > 0:
                data = serial_port.read(serial_port.in_waiting)
                if data:
                    # Divide em pacotes (cada pacote pode ter tamanho variável)
                    # Por enquanto, retorna como um único pacote
                    # O parser vai lidar com a divisão
                    packets.append(data)
            
            return packets
            
        except Exception as e:
            logger.debug(f"Erro ao coletar dados: {e}")
            return []
    
    def _save_scans(self):
        """Salva scans coletados em arquivo JSON."""
        if not self.scans:
            logger.warning("Nenhum scan para salvar")
            return
        
        try:
            timestamp = int(time.time())
            output_file = self.output_dir / f"scans_{timestamp}.json"
            
            # Prepara dados para serialização
            serializable_scans = []
            for scan in self.scans:
                serializable_scan = {
                    'timestamp': scan['timestamp'],
                    'source': scan['source']
                }
                
                if 'points' in scan:
                    # Scan processado com pontos
                    serializable_scan['point_count'] = scan['point_count']
                    serializable_scan['points'] = scan['points']
                elif 'raw_data' in scan:
                    # Dados brutos
                    serializable_scan['packet_count'] = scan['packet_count']
                    serializable_scan['raw_data'] = scan['raw_data']
                
                serializable_scans.append(serializable_scan)
            
            scan_data = {
                'metadata': {
                    'total_scans': len(self.scans),
                    'start_time': self.start_time,
                    'end_time': time.time(),
                    'duration': time.time() - (self.start_time or 0),
                    'format': 'rplidar'
                },
                'scans': serializable_scans
            }
            
            with open(output_file, 'w') as f:
                json.dump(scan_data, f, indent=2)
            
            logger.info(f"Scans salvos em: {output_file}")
            logger.info(f"  Total: {len(self.scans)} scans")
            if self.scans and 'point_count' in self.scans[0]:
                total_points = sum(s.get('point_count', 0) for s in self.scans)
                logger.info(f"  Total de pontos: {total_points}")
        except Exception as e:
            logger.error(f"Erro ao salvar scans: {e}")
    
    def get_scan_count(self) -> int:
        """Retorna número de scans coletados."""
        return len(self.scans)
    
    def get_scans(self) -> List[Dict]:
        """Retorna lista de scans coletados."""
        return self.scans.copy()

