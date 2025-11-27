"""
Parser de Protocolo RPLIDAR
Processa dados do protocolo RPLIDAR usado pelo C1.
"""

import struct
import time
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class RPLIDARParser:
    """
    Parser para protocolo RPLIDAR.
    
    O protocolo RPLIDAR usa:
    - Header: 0xA5 0x5A
    - Comandos: 2 bytes (0xA5 + comando)
    - Respostas: Header + tamanho + dados + checksum
    """
    
    # Headers RPLIDAR
    RPLIDAR_SYNC_BYTE = 0xA5
    RPLIDAR_SYNC_BYTE2 = 0x5A
    
    # Comandos RPLIDAR
    CMD_STOP = 0x25
    CMD_RESET = 0x40
    CMD_SCAN = 0x20
    CMD_FORCE_SCAN = 0x21
    CMD_GET_INFO = 0x50
    CMD_GET_HEALTH = 0x52
    CMD_GET_SAMPLERATE = 0x59
    
    # Tipos de resposta
    RSP_MEASUREMENT = 0x81
    RSP_MEASUREMENT_CAPSULED = 0x82
    RSP_MEASUREMENT_HQ = 0x83
    RSP_MEASUREMENT_DENSE_CAPSULED = 0x84
    
    def __init__(self):
        self.buffer = bytearray()
        self.current_scan_points = []
    
    def build_command(self, cmd: int) -> bytes:
        """
        Constrói comando RPLIDAR.
        
        Args:
            cmd: Código do comando
        
        Returns:
            Bytes do comando
        """
        return bytes([self.RPLIDAR_SYNC_BYTE, cmd])
    
    def parse_response_header(self, data: bytes) -> Optional[Dict]:
        """
        Parse do header de resposta RPLIDAR.
        
        Formato: [0xA5 0x5A] [size_low] [size_high] [cmd] [data...] [checksum]
        
        Args:
            data: Dados recebidos
        
        Returns:
            Dicionário com informações do pacote ou None
        """
        if len(data) < 5:
            return None
        
        # Verifica header
        if data[0] != self.RPLIDAR_SYNC_BYTE or data[1] != self.RPLIDAR_SYNC_BYTE2:
            return None
        
        # Lê tamanho (little-endian)
        size = data[2] | (data[3] << 8)
        cmd = data[4]
        
        if len(data) < 5 + size:
            return None  # Pacote incompleto
        
        payload = data[5:5+size]
        checksum = data[5+size] if len(data) > 5+size else None
        
        return {
            'size': size,
            'cmd': cmd,
            'payload': payload,
            'checksum': checksum,
            'total_size': 5 + size + (1 if checksum is not None else 0)
        }
    
    def parse_health_response(self, payload: bytes) -> Dict:
        """
        Parse resposta de GET_HEALTH.
        
        Formato: [status] [error_code]
        
        Args:
            payload: Payload da resposta
        
        Returns:
            Dicionário com informações de saúde
        """
        if len(payload) < 3:
            return {'status': 'unknown', 'error_code': 0}
        
        status = payload[0]
        error_code = payload[1] | (payload[2] << 8)
        
        status_map = {
            0: 'OK',
            1: 'WARNING',
            2: 'ERROR'
        }
        
        return {
            'status': status_map.get(status, 'UNKNOWN'),
            'status_code': status,
            'error_code': error_code
        }
    
    def parse_info_response(self, payload: bytes) -> Dict:
        """
        Parse resposta de GET_INFO.
        
        Args:
            payload: Payload da resposta
        
        Returns:
            Dicionário com informações do dispositivo
        """
        if len(payload) < 20:
            return {}
        
        return {
            'model': payload[0],
            'firmware_minor': payload[1],
            'firmware_major': payload[2],
            'hardware': payload[3],
            'serial_number': payload[7:15].hex()
        }
    
    def parse_scan_point(self, data: bytes, offset: int = 0) -> Optional[Dict]:
        """
        Parse um ponto de scan RPLIDAR.
        
        Formato varia conforme tipo de resposta:
        - Measurement: [sync_quality] [angle_q6] [distance_q2]
        - Measurement Capsuled: [sync_quality] [angle_q6] [distance_q2] [angle_q6] [distance_q2]
        
        Args:
            data: Dados do pacote
            offset: Offset no buffer
        
        Returns:
            Dicionário com dados do ponto ou None
        """
        if offset + 5 > len(data):
            return None
        
        # Lê sync_quality (primeiro byte)
        sync_quality = data[offset]
        
        # Verifica se é início de novo scan (bit 0 do sync_quality)
        is_new_scan = (sync_quality & 0x01) != 0
        quality = (sync_quality >> 2) & 0x3F
        
        # Lê ângulo (q6 = ângulo * 64)
        angle_q6 = data[offset + 1] | ((data[offset + 2] & 0x7F) << 8)
        angle = angle_q6 / 64.0  # Converte para graus
        
        # Lê distância (q2 = distância * 4)
        distance_q2 = data[offset + 3] | (data[offset + 4] << 8)
        distance = distance_q2 / 4.0  # Converte para mm (depois para metros)
        
        # Verifica se distância é válida (0 indica sem retorno)
        is_valid = distance > 0
        
        return {
            'angle': angle,  # Em graus
            'distance': distance / 1000.0,  # Converte mm para metros
            'quality': quality,
            'is_new_scan': is_new_scan,
            'is_valid': is_valid
        }
    
    def parse_scan_data(self, data: bytes) -> List[Dict]:
        """
        Parse dados de scan completos.
        
        Args:
            data: Dados brutos recebidos
        
        Returns:
            Lista de pontos de scan
        """
        points = []
        offset = 0
        
        # Procura por header de resposta
        while offset < len(data):
            # Procura por sync byte
            sync_pos = data.find(self.RPLIDAR_SYNC_BYTE, offset)
            if sync_pos == -1:
                break
            
            # Verifica se é header válido
            if sync_pos + 1 < len(data) and data[sync_pos + 1] == self.RPLIDAR_SYNC_BYTE2:
                # É um header de resposta, parse
                header = self.parse_response_header(data[sync_pos:])
                if header:
                    offset = sync_pos + header['total_size']
                    continue
            
            # Tenta parse como ponto de scan
            point = self.parse_scan_point(data, sync_pos)
            if point:
                points.append(point)
                offset = sync_pos + 5
            else:
                offset = sync_pos + 1
        
        return points
    
    def extract_complete_scan(self, data_stream: List[bytes]) -> List[Dict]:
        """
        Extrai um scan completo (360 graus) dos dados recebidos.
        
        Args:
            data_stream: Lista de pacotes de dados recebidos
        
        Returns:
            Lista de pontos do scan completo
        """
        all_points = []
        
        for packet in data_stream:
            points = self.parse_scan_data(packet)
            all_points.extend(points)
        
        # Agrupa pontos por scan (usando flag is_new_scan)
        if not all_points:
            return []
        
        # Encontra o último scan completo
        scan_points = []
        current_scan = []
        
        for point in all_points:
            if point['is_new_scan'] and current_scan:
                # Novo scan iniciado, salva o anterior
                if len(current_scan) > 10:  # Mínimo de pontos para considerar válido
                    scan_points = current_scan
                current_scan = [point]
            else:
                current_scan.append(point)
        
        # Adiciona último scan se tiver pontos suficientes
        if len(current_scan) > 10:
            scan_points = current_scan
        
        return scan_points
    
    def points_to_cartesian(self, points: List[Dict]) -> List[Tuple[float, float]]:
        """
        Converte pontos polares para coordenadas cartesianas.
        
        Args:
            points: Lista de pontos em formato polar (ângulo em graus, distância em metros)
        
        Returns:
            Lista de tuplas (x, y) em metros
        """
        import math
        cartesian = []
        
        for point in points:
            if not point['is_valid']:
                continue
            
            angle_rad = math.radians(point['angle'])
            distance = point['distance']
            
            x = distance * math.cos(angle_rad)
            y = distance * math.sin(angle_rad)
            
            cartesian.append((x, y))
        
        return cartesian

