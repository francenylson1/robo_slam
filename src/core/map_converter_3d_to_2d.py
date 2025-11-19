"""
Conversor de Mapas 3D para 2D
Converte nuvens de pontos 3D em mapas de ocupação 2D (occupancy grids).
"""

import numpy as np
from typing import Tuple, Optional, Dict
import logging

try:
    import open3d as o3d
    OPEN3D_AVAILABLE = True
except ImportError:
    OPEN3D_AVAILABLE = False
    logging.warning("Open3D não disponível. Funcionalidades limitadas.")

logger = logging.getLogger(__name__)


class MapConverter3DTo2D:
    """
    Converte nuvens de pontos 3D em mapas de ocupação 2D.
    
    Processo:
    1. Projeta pontos 3D no plano XY
    2. Cria grid de ocupação baseado em densidade de pontos
    3. Aplica filtros para remover ruído
    4. Gera mapa binário (livre/ocupado)
    """
    
    def __init__(self, resolution: float = 0.05, height_range: Tuple[float, float] = (0.0, 2.0)):
        """
        Inicializa o conversor.
        
        Args:
            resolution: Resolução do grid em metros (padrão: 5cm)
            height_range: Faixa de altura (min, max) em metros para considerar pontos
        """
        self.resolution = resolution
        self.height_range = height_range
        self.occupancy_grid = None
        self.origin = (0.0, 0.0)  # Origem do mapa em coordenadas do mundo
        
    def convert(self, point_cloud: np.ndarray, 
                method: str = "projection") -> np.ndarray:
        """
        Converte nuvem de pontos 3D em mapa 2D.
        
        Args:
            point_cloud: Array numpy (N, 3) com pontos [x, y, z]
            method: Método de conversão ("projection" ou "voxel")
            
        Returns:
            Array 2D numpy representando o mapa de ocupação
            Valores: 0 = livre, 100 = ocupado, -1 = desconhecido
        """
        if point_cloud is None or len(point_cloud) == 0:
            logger.error("Nuvem de pontos vazia")
            return None
        
        # Filtra pontos por altura
        z_min, z_max = self.height_range
        mask = (point_cloud[:, 2] >= z_min) & (point_cloud[:, 2] <= z_max)
        filtered_points = point_cloud[mask]
        
        if len(filtered_points) == 0:
            logger.warning("Nenhum ponto na faixa de altura especificada")
            return None
        
        logger.info(f"Convertendo {len(filtered_points)} pontos para mapa 2D")
        
        if method == "projection":
            return self._convert_projection(filtered_points)
        elif method == "voxel":
            return self._convert_voxel(filtered_points)
        else:
            logger.error(f"Método desconhecido: {method}")
            return None
    
    def _convert_projection(self, points: np.ndarray) -> np.ndarray:
        """
        Converte usando projeção simples no plano XY.
        
        Args:
            points: Pontos filtrados (N, 3)
            
        Returns:
            Mapa de ocupação 2D
        """
        # Calcula limites do mapa
        min_x, max_x = np.min(points[:, 0]), np.max(points[:, 0])
        min_y, max_y = np.min(points[:, 1]), np.max(points[:, 1])
        
        # Adiciona margem
        margin = 1.0  # 1 metro de margem
        min_x -= margin
        max_x += margin
        min_y -= margin
        max_y += margin
        
        # Calcula dimensões do grid
        width = int(np.ceil((max_x - min_x) / self.resolution))
        height = int(np.ceil((max_y - min_y) / self.resolution))
        
        # Define origem (canto inferior esquerdo)
        self.origin = (min_x, min_y)
        
        # Cria grid vazio (-1 = desconhecido)
        grid = np.full((height, width), -1, dtype=np.int8)
        
        # Projeta pontos no grid
        x_indices = ((points[:, 0] - min_x) / self.resolution).astype(int)
        y_indices = ((points[:, 1] - min_y) / self.resolution).astype(int)
        
        # Garante índices válidos
        x_indices = np.clip(x_indices, 0, width - 1)
        y_indices = np.clip(y_indices, 0, height - 1)
        
        # Marca células como ocupadas
        grid[y_indices, x_indices] = 100
        
        logger.info(f"Mapa 2D criado: {width}x{height} células, resolução {self.resolution}m")
        
        self.occupancy_grid = grid
        return grid
    
    def _convert_voxel(self, points: np.ndarray) -> np.ndarray:
        """
        Converte usando voxelização (requer Open3D).
        
        Args:
            points: Pontos filtrados (N, 3)
            
        Returns:
            Mapa de ocupação 2D
        """
        if not OPEN3D_AVAILABLE:
            logger.warning("Open3D não disponível, usando método de projeção")
            return self._convert_projection(points)
        
        try:
            # Cria nuvem de pontos Open3D
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(points)
            
            # Voxeliza
            voxel_size = self.resolution
            voxel_grid = o3d.geometry.VoxelGrid.create_from_point_cloud(pcd, voxel_size)
            
            # Projeta voxels no plano XY
            # TODO: Implementar projeção de voxels 3D para grid 2D
            # Por enquanto, usa projeção simples
            return self._convert_projection(points)
            
        except Exception as e:
            logger.error(f"Erro na voxelização: {e}")
            return self._convert_projection(points)
    
    def apply_morphology(self, grid: np.ndarray, 
                        kernel_size: int = 3) -> np.ndarray:
        """
        Aplica operações morfológicas para limpar o mapa.
        
        Args:
            grid: Mapa de ocupação
            kernel_size: Tamanho do kernel para operações morfológicas
            
        Returns:
            Mapa processado
        """
        try:
            from scipy import ndimage
            
            # Cria kernel circular
            kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
            
            # Aplica closing (dilatação seguida de erosão) para preencher buracos
            closed = ndimage.binary_closing(
                grid == 100, 
                structure=kernel
            ).astype(np.int8) * 100
            
            # Aplica opening (erosão seguida de dilatação) para remover ruído
            opened = ndimage.binary_opening(
                closed == 100,
                structure=kernel
            ).astype(np.int8) * 100
            
            # Mantém áreas desconhecidas
            result = np.where(grid == -1, -1, opened)
            
            logger.info("Operações morfológicas aplicadas")
            return result
            
        except ImportError:
            logger.warning("SciPy não disponível, pulando operações morfológicas")
            return grid
    
    def inflate_obstacles(self, grid: np.ndarray, 
                         inflation_radius: float = 0.2) -> np.ndarray:
        """
        Infla obstáculos para criar margem de segurança.
        
        Args:
            grid: Mapa de ocupação
            inflation_radius: Raio de inflação em metros
            
        Returns:
            Mapa com obstáculos inflados
        """
        if grid is None:
            return None
        
        try:
            from scipy import ndimage
            
            # Calcula tamanho do kernel em células
            kernel_size = int(np.ceil(inflation_radius / self.resolution) * 2 + 1)
            kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
            
            # Dilata obstáculos
            dilated = ndimage.binary_dilation(
                grid == 100,
                structure=kernel
            ).astype(np.int8) * 100
            
            # Mantém áreas desconhecidas
            result = np.where(grid == -1, -1, dilated)
            
            logger.info(f"Obstáculos inflados com raio {inflation_radius}m")
            return result
            
        except ImportError:
            logger.warning("SciPy não disponível, pulando inflação")
            return grid
    
    def get_origin(self) -> Tuple[float, float]:
        """
        Retorna a origem do mapa em coordenadas do mundo.
        
        Returns:
            Tupla (x, y) da origem
        """
        return self.origin
    
    def get_resolution(self) -> float:
        """Retorna a resolução do mapa."""
        return self.resolution


if __name__ == "__main__":
    # Teste básico
    logging.basicConfig(level=logging.INFO)
    
    # Cria nuvem de pontos de teste
    np.random.seed(42)
    points = np.random.rand(1000, 3) * 10  # 10m x 10m x 10m
    points[:, 2] = np.random.rand(1000) * 0.5  # Altura entre 0 e 0.5m
    
    converter = MapConverter3DTo2D(resolution=0.1, height_range=(0.0, 1.0))
    grid = converter.convert(points)
    
    if grid is not None:
        print(f"Mapa criado: {grid.shape}")
        print(f"Origem: {converter.get_origin()}")
        print(f"Resolução: {converter.get_resolution()}m")

