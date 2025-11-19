"""
Gerador de Arquivos PGM e YAML
Gera arquivos no formato ROS map (PGM + YAML) compatível com Slamtec C1.
"""

import numpy as np
from PIL import Image
import yaml
from typing import Tuple, Optional, Dict
import os
import logging

logger = logging.getLogger(__name__)


class PGMYAMLGenerator:
    """
    Gera arquivos PGM (Portable Gray Map) e YAML para mapas de ocupação.
    
    Formato compatível com ROS e Slamtec SLAMWARE.
    """
    
    def __init__(self, occupancy_grid: np.ndarray, 
                 resolution: float,
                 origin: Tuple[float, float, float] = (0.0, 0.0, 0.0)):
        """
        Inicializa o gerador.
        
        Args:
            occupancy_grid: Array 2D com valores 0-100 (ocupação) e -1 (desconhecido)
            resolution: Resolução do mapa em metros por pixel
            origin: Origem do mapa (x, y, yaw) em coordenadas do mundo
        """
        self.occupancy_grid = occupancy_grid
        self.resolution = resolution
        self.origin = origin
        
    def generate_pgm(self, output_path: str, 
                    free_thresh: float = 0.196,
                    occupied_thresh: float = 0.65) -> bool:
        """
        Gera arquivo PGM a partir do grid de ocupação.
        
        Args:
            output_path: Caminho para salvar o arquivo .pgm
            free_thresh: Limiar para considerar célula livre (0-1)
            occupied_thresh: Limiar para considerar célula ocupada (0-1)
            
        Returns:
            True se geração bem-sucedida
        """
        try:
            # Converte valores de ocupação para escala 0-255
            # ROS: 0 = ocupado, 255 = livre, 205 = desconhecido
            pgm_data = np.zeros_like(self.occupancy_grid, dtype=np.uint8)
            
            # Áreas ocupadas (100) -> 0 (preto)
            pgm_data[self.occupancy_grid == 100] = 0
            
            # Áreas livres (0) -> 255 (branco)
            pgm_data[self.occupancy_grid == 0] = 255
            
            # Áreas desconhecidas (-1) -> 205 (cinza)
            pgm_data[self.occupancy_grid == -1] = 205
            
            # Inverte verticalmente (PGM tem origem no canto superior esquerdo)
            pgm_data = np.flipud(pgm_data)
            
            # Salva como PGM
            height, width = pgm_data.shape
            
            with open(output_path, 'wb') as f:
                # Header PGM
                f.write(b"P5\n")
                f.write(f"{width} {height}\n".encode())
                f.write(b"255\n")
                # Dados binários
                pgm_data.tofile(f)
            
            logger.info(f"Arquivo PGM gerado: {output_path} ({width}x{height})")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao gerar PGM: {e}")
            return False
    
    def generate_yaml(self, output_path: str, 
                     pgm_filename: str,
                     free_thresh: float = 0.196,
                     occupied_thresh: float = 0.65) -> bool:
        """
        Gera arquivo YAML com metadados do mapa.
        
        Args:
            output_path: Caminho para salvar o arquivo .yaml
            pgm_filename: Nome do arquivo PGM (relativo ao YAML)
            free_thresh: Limiar para considerar célula livre
            occupied_thresh: Limiar para considerar célula ocupada
            
        Returns:
            True se geração bem-sucedida
        """
        try:
            height, width = self.occupancy_grid.shape
            
            yaml_data = {
                'image': pgm_filename,
                'resolution': float(self.resolution),
                'origin': [float(self.origin[0]), float(self.origin[1]), float(self.origin[2])],  # [x, y, yaw]
                'negate': 0,  # 0 = não negar (padrão ROS)
                'occupied_thresh': float(occupied_thresh),
                'free_thresh': float(free_thresh)
            }
            
            with open(output_path, 'w') as f:
                yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Arquivo YAML gerado: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao gerar YAML: {e}")
            return False
    
    def generate_both(self, base_path: str,
                     free_thresh: float = 0.196,
                     occupied_thresh: float = 0.65) -> Tuple[bool, str, str]:
        """
        Gera ambos os arquivos PGM e YAML.
        
        Args:
            base_path: Caminho base (sem extensão) para os arquivos
            free_thresh: Limiar para considerar célula livre
            occupied_thresh: Limiar para considerar célula ocupada
            
        Returns:
            Tupla (sucesso, caminho_pgm, caminho_yaml)
        """
        pgm_path = f"{base_path}.pgm"
        yaml_path = f"{base_path}.yaml"
        pgm_filename = os.path.basename(pgm_path)
        
        success_pgm = self.generate_pgm(pgm_path, free_thresh, occupied_thresh)
        success_yaml = self.generate_yaml(yaml_path, pgm_filename, free_thresh, occupied_thresh)
        
        if success_pgm and success_yaml:
            logger.info(f"Mapa completo gerado: {base_path}")
            return (True, pgm_path, yaml_path)
        else:
            return (False, pgm_path, yaml_path)
    
    def convert_to_ros_format(self) -> np.ndarray:
        """
        Converte grid interno para formato ROS (0-100, -1 para desconhecido).
        
        Returns:
            Grid no formato ROS
        """
        # Já está no formato correto
        return self.occupancy_grid.copy()


def generate_map_files(occupancy_grid: np.ndarray,
                      resolution: float,
                      output_base_path: str,
                      origin: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                      free_thresh: float = 0.196,
                      occupied_thresh: float = 0.65) -> Tuple[bool, str, str]:
    """
    Função auxiliar para gerar arquivos PGM e YAML.
    
    Args:
        occupancy_grid: Grid de ocupação 2D
        resolution: Resolução em metros
        output_base_path: Caminho base para os arquivos
        origin: Origem do mapa (x, y, yaw)
        free_thresh: Limiar para livre
        occupied_thresh: Limiar para ocupado
        
    Returns:
        Tupla (sucesso, caminho_pgm, caminho_yaml)
    """
    generator = PGMYAMLGenerator(occupancy_grid, resolution, origin)
    return generator.generate_both(output_base_path, free_thresh, occupied_thresh)


if __name__ == "__main__":
    # Teste básico
    logging.basicConfig(level=logging.INFO)
    
    # Cria grid de teste
    grid = np.zeros((100, 100), dtype=np.int8)
    grid[20:80, 20:80] = 100  # Área ocupada no centro
    grid[0:10, :] = -1  # Área desconhecida no topo
    
    generator = PGMYAMLGenerator(grid, resolution=0.05, origin=(0.0, 0.0, 0.0))
    success, pgm_path, yaml_path = generator.generate_both("test_map")
    
    if success:
        print(f"✅ Arquivos gerados:")
        print(f"   PGM: {pgm_path}")
        print(f"   YAML: {yaml_path}")

