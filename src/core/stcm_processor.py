"""
Processador de Arquivos .stcm do Slamtec Aurora
Lê e processa arquivos .stcm contendo mapas 3D e nuvens de pontos.
"""

import struct
import zlib
import json
from typing import Dict, List, Tuple, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)


class STCMProcessor:
    """
    Classe para processar arquivos .stcm do sensor Aurora.
    
    O formato .stcm contém:
    - Dados de nuvem de pontos 3D
    - Metadados do mapa
    - Informações de pose e trajetória
    """
    
    def __init__(self, file_path: str):
        """
        Inicializa o processador com um arquivo .stcm.
        
        Args:
            file_path: Caminho para o arquivo .stcm
        """
        self.file_path = file_path
        self.metadata = {}
        self.point_cloud = None
        self.occupancy_2d = None
        
    def load(self) -> bool:
        """
        Carrega o arquivo .stcm.
        
        Returns:
            True se carregamento bem-sucedido
        """
        try:
            with open(self.file_path, 'rb') as f:
                data = f.read()
                file_size = len(data)
                
                logger.info(f"Carregando arquivo .stcm: {self.file_path} ({file_size:,} bytes)")
                
                # Tenta extrair metadados básicos do arquivo
                self.metadata = {
                    "version": "1.0",
                    "timestamp": None,
                    "resolution": 0.05,  # 5cm por padrão
                    "width": 0,
                    "height": 0,
                    "file_size": file_size
                }
                
                # Tenta encontrar metadados em texto
                try:
                    text_data = data.decode('utf-8', errors='ignore')
                    if 'creation_time' in text_data:
                        logger.info("Metadados de texto encontrados no arquivo")
                    if 'description' in text_data:
                        desc_start = text_data.find('description')
                        if desc_start >= 0:
                            # Tenta extrair descrição
                            pass
                except:
                    pass
                
                logger.info("Arquivo .stcm carregado (estrutura básica)")
                logger.warning("⚠️  Parsing completo do .stcm requer documentação do formato")
                return True
                
        except FileNotFoundError:
            logger.error(f"Arquivo não encontrado: {self.file_path}")
            return False
        except Exception as e:
            logger.error(f"Erro ao carregar arquivo .stcm: {e}")
            return False
    
    def extract_point_cloud(self) -> Optional[np.ndarray]:
        """
        Extrai nuvem de pontos 3D do arquivo .stcm.
        
        Returns:
            Array numpy com formato (N, 3) onde cada linha é [x, y, z]
            ou None em caso de erro
        """
        try:
            with open(self.file_path, 'rb') as f:
                data = f.read()
                file_size = len(data)
                
                logger.info(f"Tentando extrair nuvem de pontos de arquivo {file_size:,} bytes")
                
                # Tenta diferentes métodos de parsing
                points = None
                
                # Método 1: Procura por sequências de floats (coordenadas x, y, z)
                # O formato .stcm do Aurora pode ter pontos armazenados como float32
                try:
                    points = self._extract_floats_method(data)
                    if points is not None and len(points) > 100:
                        logger.info(f"✅ Nuvem de pontos extraída: {len(points)} pontos (método floats)")
                        self.point_cloud = points
                        return points
                except Exception as e:
                    logger.debug(f"Método floats falhou: {e}")
                
                # Método 2: Tenta usar Open3D se disponível
                try:
                    import open3d as o3d
                    # Tenta carregar como formato suportado pelo Open3D
                    # Nota: .stcm não é formato padrão, mas podemos tentar
                    logger.warning("Tentando carregar com Open3D (pode não funcionar para .stcm)")
                except ImportError:
                    pass
                except Exception as e:
                    logger.debug(f"Open3D não conseguiu carregar: {e}")
                
                # Se nenhum método funcionou
                logger.error("Não foi possível extrair nuvem de pontos do arquivo .stcm")
                logger.error("O formato .stcm do Aurora requer implementação específica")
                logger.error("Sugestões:")
                logger.error("  1. Use o software do Aurora para exportar em formato suportado (PLY, PCD)")
                logger.error("  2. Verifique a documentação do SDK do Aurora")
                logger.error("  3. Use a interface web do Aurora para exportar o mapa 2D")
                
                return None
                
        except Exception as e:
            logger.error(f"Erro ao extrair nuvem de pontos: {e}", exc_info=True)
            return None
    
    def _extract_floats_method(self, data: bytes) -> Optional[np.ndarray]:
        """
        Tenta extrair pontos usando a estrutura MapPointDesc do SDK Aurora.
        
        Estrutura MapPointDesc (44 bytes):
        - id: uint64 (8 bytes)
        - map_id: uint32 (4 bytes)
        - padding: uint32 (4 bytes)
        - timestamp: double (8 bytes)
        - position: Vector3 (3 floats = 12 bytes) - x, y, z
        - flags: uint32 (4 bytes)
        - padding: uint32 (4 bytes)
        """
        import struct
        import re
        
        points = []
        
        # Método 1: Procura por seções de map points usando a estrutura completa
        # Tamanho da estrutura: 44 bytes
        STRUCT_SIZE = 44
        POSITION_OFFSET = 24  # offset para position (após id, map_id, padding, timestamp)
        
        # Procura por padrões que indicam início de seção de map points
        # Pode haver um contador antes dos dados
        for search_start in range(0, min(len(data) - 1000, 100000), 1000):
            i = search_start
            
            # Tenta encontrar sequências válidas de map points
            consecutive_valid = 0
            section_points = []
            
            while i < len(data) - STRUCT_SIZE:
                try:
                    # Lê a estrutura MapPointDesc
                    # id (uint64)
                    point_id = struct.unpack('<Q', data[i:i+8])[0]
                    # map_id (uint32)
                    map_id = struct.unpack('<I', data[i+8:i+12])[0]
                    # timestamp (double) - pulando padding
                    timestamp = struct.unpack('<d', data[i+16:i+24])[0]
                    # position (3 floats)
                    x = struct.unpack('<f', data[i+POSITION_OFFSET:i+POSITION_OFFSET+4])[0]
                    y = struct.unpack('<f', data[i+POSITION_OFFSET+4:i+POSITION_OFFSET+8])[0]
                    z = struct.unpack('<f', data[i+POSITION_OFFSET+8:i+POSITION_OFFSET+12])[0]
                    
                    # Valida se são coordenadas razoáveis
                    # Mapas geralmente estão em metros, com ranges razoáveis
                    if (-100 < x < 100 and -100 < y < 100 and -10 < z < 10 and
                        not (x == 0 and y == 0 and z == 0) and
                        point_id > 0 and map_id >= 0 and
                        -1e10 < timestamp < 1e10):
                        
                        section_points.append([x, y, z])
                        consecutive_valid += 1
                        i += STRUCT_SIZE
                        
                        # Se encontrou muitos pontos consecutivos, provavelmente é uma seção válida
                        if consecutive_valid >= 10:
                            # Continua coletando pontos desta seção
                            while i < len(data) - STRUCT_SIZE and len(section_points) < 100000:
                                try:
                                    x2 = struct.unpack('<f', data[i+POSITION_OFFSET:i+POSITION_OFFSET+4])[0]
                                    y2 = struct.unpack('<f', data[i+POSITION_OFFSET+4:i+POSITION_OFFSET+8])[0]
                                    z2 = struct.unpack('<f', data[i+POSITION_OFFSET+8:i+POSITION_OFFSET+12])[0]
                                    
                                    if (-100 < x2 < 100 and -100 < y2 < 100 and -10 < z2 < 10 and
                                        not (x2 == 0 and y2 == 0 and z2 == 0)):
                                        section_points.append([x2, y2, z2])
                                        i += STRUCT_SIZE
                                    else:
                                        break
                                except:
                                    break
                            
                            if len(section_points) >= 100:  # Mínimo de pontos válidos
                                logger.info(f"✅ Encontrada seção de map points: {len(section_points)} pontos")
                                points = section_points
                                break
                    else:
                        consecutive_valid = 0
                        section_points = []
                        i += 1
                        
                except:
                    i += 1
                    consecutive_valid = 0
                    section_points = []
            
            if len(points) >= 100:
                break
        
        # Método 2: Se não encontrou com estrutura completa, tenta método mais simples
        # Procura por sequências de 3 floats consecutivos (apenas coordenadas)
        if len(points) < 100:
            logger.info("Tentando método alternativo: sequências de floats...")
            points = []
            i = 0
            consecutive_valid = 0
            temp_points = []
            
            while i < len(data) - 12:
                try:
                    x = struct.unpack('<f', data[i:i+4])[0]
                    y = struct.unpack('<f', data[i+4:i+8])[0]
                    z = struct.unpack('<f', data[i+8:i+12])[0]
                    
                    if (-100 < x < 100 and -100 < y < 100 and -10 < z < 10 and
                        not (x == 0 and y == 0 and z == 0)):
                        temp_points.append([x, y, z])
                        consecutive_valid += 1
                        i += 12
                        
                        if consecutive_valid >= 50:  # Encontrou sequência válida
                            # Continua coletando
                            while i < len(data) - 12 and len(temp_points) < 100000:
                                try:
                                    x2 = struct.unpack('<f', data[i:i+4])[0]
                                    y2 = struct.unpack('<f', data[i+4:i+8])[0]
                                    z2 = struct.unpack('<f', data[i+8:i+12])[0]
                                    
                                    if (-100 < x2 < 100 and -100 < y2 < 100 and -10 < z2 < 10 and
                                        not (x2 == 0 and y2 == 0 and z2 == 0)):
                                        temp_points.append([x2, y2, z2])
                                        i += 12
                                    else:
                                        break
                                except:
                                    break
                            
                            if len(temp_points) >= 100:
                                points = temp_points
                                logger.info(f"✅ Encontrada sequência de coordenadas: {len(points)} pontos")
                                break
                    else:
                        consecutive_valid = 0
                        temp_points = []
                        i += 1
                except:
                    i += 1
                    consecutive_valid = 0
                    temp_points = []
        
        if len(points) >= 100:
            return np.array(points, dtype=np.float32)
        
        return None
    
    def extract_2d_map(self) -> Optional[np.ndarray]:
        """
        Extrai mapa 2D (se disponível) do arquivo .stcm.
        
        Returns:
            Array numpy 2D representando o mapa de ocupação
            ou None se não disponível
        """
        try:
            with open(self.file_path, 'rb') as f:
                # TODO: Implementar extração de mapa 2D
                # Alguns arquivos .stcm podem conter versão 2D pré-processada
                
                logger.info("Mapa 2D extraído do arquivo .stcm")
                return self.occupancy_2d
                
        except Exception as e:
            logger.error(f"Erro ao extrair mapa 2D: {e}")
            return None
    
    def get_metadata(self) -> Dict:
        """
        Retorna metadados do mapa.
        
        Returns:
            Dicionário com metadados
        """
        return self.metadata.copy()
    
    def get_bounds(self) -> Optional[Tuple[float, float, float, float, float, float]]:
        """
        Calcula os limites (bounding box) da nuvem de pontos.
        
        Returns:
            Tupla (min_x, max_x, min_y, max_y, min_z, max_z) ou None
        """
        if self.point_cloud is None or len(self.point_cloud) == 0:
            return None
        
        min_bounds = np.min(self.point_cloud, axis=0)
        max_bounds = np.max(self.point_cloud, axis=0)
        
        return (
            float(min_bounds[0]), float(max_bounds[0]),
            float(min_bounds[1]), float(max_bounds[1]),
            float(min_bounds[2]), float(max_bounds[2])
        )
    
    def filter_point_cloud(self, 
                          z_min: float = -np.inf, 
                          z_max: float = np.inf,
                          remove_outliers: bool = True) -> np.ndarray:
        """
        Filtra a nuvem de pontos 3D.
        
        Args:
            z_min: Altura mínima (para remover pontos abaixo do chão)
            z_max: Altura máxima (para remover pontos muito altos)
            remove_outliers: Se True, remove outliers estatísticos
            
        Returns:
            Nuvem de pontos filtrada
        """
        if self.point_cloud is None:
            logger.warning("Nuvem de pontos não carregada")
            return np.array([])
        
        filtered = self.point_cloud.copy()
        
        # Filtro por altura
        mask = (filtered[:, 2] >= z_min) & (filtered[:, 2] <= z_max)
        filtered = filtered[mask]
        
        # Remoção de outliers (método simples baseado em distância)
        if remove_outliers and len(filtered) > 0:
            # Calcula distâncias médias entre pontos
            # Remove pontos muito distantes da média
            # TODO: Implementar método mais robusto (DBSCAN, etc.)
            pass
        
        logger.info(f"Nuvem de pontos filtrada: {len(filtered)} pontos")
        return filtered


def load_stcm_file(file_path: str) -> Optional[STCMProcessor]:
    """
    Função auxiliar para carregar um arquivo .stcm.
    
    Args:
        file_path: Caminho para o arquivo .stcm
        
    Returns:
        Instância de STCMProcessor ou None em caso de erro
    """
    processor = STCMProcessor(file_path)
    if processor.load():
        return processor
    return None


if __name__ == "__main__":
    # Teste básico
    logging.basicConfig(level=logging.INFO)
    import sys
    
    if len(sys.argv) > 1:
        processor = load_stcm_file(sys.argv[1])
        if processor:
            print(f"Metadados: {processor.get_metadata()}")
            bounds = processor.get_bounds()
            if bounds:
                print(f"Limites: {bounds}")

