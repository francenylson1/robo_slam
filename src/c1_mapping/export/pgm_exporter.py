"""
Exportador de Mapas PGM/YAML
Exporta mapas de ocupação em formato compatível com C1 e sistemas de navegação.
"""

import sys
from pathlib import Path
from typing import Tuple, Optional
import numpy as np
import logging

# Garante que o diretório raiz esteja no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import yaml
from src.core.pgm_yaml_generator import PGMYAMLGenerator

logger = logging.getLogger(__name__)


class PGMExporter:
    """
    Exportador de mapas em formato PGM/YAML.
    
    Formato compatível com:
    - Slamtec C1 (SLAMWARE)
    - ROS (Robot Operating System)
    - Sistemas de navegação padrão
    """
    
    def __init__(self, occupancy_grid: np.ndarray,
                 resolution: float,
                 origin: Tuple[float, float, float] = (0.0, 0.0, 0.0)):
        """
        Inicializa o exportador.
        
        Args:
            occupancy_grid: Grid de ocupação (valores: 0=ocupado, 254=livre, 205=desconhecido)
            resolution: Resolução em metros por pixel
            origin: Origem do mapa (x, y, yaw)
        """
        self.occupancy_grid = occupancy_grid
        self.resolution = resolution
        self.origin = origin
    
    def export(self, output_base_path: str,
               free_thresh: float = 0.196,
               occupied_thresh: float = 0.65) -> Tuple[bool, str, str]:
        """
        Exporta mapa em formato PGM + YAML.
        
        Args:
            output_base_path: Caminho base (sem extensão) para os arquivos
            free_thresh: Limiar para considerar célula livre
            occupied_thresh: Limiar para considerar célula ocupada
        
        Returns:
            Tupla (sucesso, caminho_pgm, caminho_yaml)
        """
        try:
            # Converte grid para formato padrão (0-100, -1 para desconhecido)
            standard_grid = self._convert_to_standard_format()
            
            # Usa gerador existente
            generator = PGMYAMLGenerator(
                standard_grid,
                self.resolution,
                self.origin
            )
            
            success, pgm_path, yaml_path = generator.generate_both(
                output_base_path,
                free_thresh,
                occupied_thresh
            )
            
            if success:
                logger.info(f"Mapa exportado:")
                logger.info(f"  PGM: {pgm_path}")
                logger.info(f"  YAML: {yaml_path}")
            
            return (success, pgm_path, yaml_path)
            
        except Exception as e:
            logger.error(f"Erro ao exportar mapa: {e}", exc_info=True)
            return (False, "", "")
    
    def _convert_to_standard_format(self) -> np.ndarray:
        """
        Converte grid para formato padrão (0-100 para ocupação, -1 para desconhecido).
        
        Returns:
            Grid no formato padrão
        """
        # Grid atual pode ter: 0=ocupado, 254=livre, 205=desconhecido
        # Formato padrão: 100=ocupado, 0=livre, -1=desconhecido
        
        standard_grid = np.zeros_like(self.occupancy_grid, dtype=np.int8)
        
        # Ocupado: 0 ou 100 -> 100
        occupied_mask = (self.occupancy_grid == 0) | (self.occupancy_grid == 100)
        standard_grid[occupied_mask] = 100
        
        # Livre: 254 -> 0
        free_mask = (self.occupancy_grid == 254)
        standard_grid[free_mask] = 0
        
        # Desconhecido: 205 ou -1 -> -1
        unknown_mask = (self.occupancy_grid == 205) | (self.occupancy_grid == -1)
        standard_grid[unknown_mask] = -1
        
        # Se ainda houver valores não mapeados, assume desconhecido
        unmapped_mask = ~(occupied_mask | free_mask | unknown_mask)
        standard_grid[unmapped_mask] = -1
        
        return standard_grid

