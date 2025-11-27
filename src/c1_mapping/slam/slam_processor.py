"""
Processador SLAM 2D
Converte scans LIDAR em mapas de ocupação (occupancy grid).
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np
import math
import logging

# Garante que o diretório raiz esteja no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scipy.ndimage import binary_dilation, binary_erosion
from src.c1_mapping.capture.rplidar_parser import RPLIDARParser

logger = logging.getLogger(__name__)


class SLAMProcessor:
    """
    Processador SLAM 2D para gerar mapas de ocupação a partir de scans LIDAR.
    
    Usa algoritmo de occupancy grid mapping incremental.
    """
    
    def __init__(self, resolution: float = 0.05, 
                 max_range: float = 12.0,
                 occupied_value: int = 0,
                 free_value: int = 254,
                 unknown_value: int = 205):
        """
        Inicializa o processador SLAM.
        
        Args:
            resolution: Resolução do grid em metros por pixel (padrão: 5cm)
            max_range: Alcance máximo do LIDAR em metros
            occupied_value: Valor para células ocupadas (0-255)
            free_value: Valor para células livres (0-255)
            unknown_value: Valor para células desconhecidas (0-255)
        """
        self.resolution = resolution
        self.max_range = max_range
        self.occupied_value = occupied_value
        self.free_value = free_value
        self.unknown_value = unknown_value
        
        self.occupancy_grid = None
        self.origin = (0.0, 0.0)  # Origem do mapa (x, y)
        self.grid_width = 0
        self.grid_height = 0
        
        # Histórico de poses do robô (para SLAM completo)
        self.robot_poses = []
        
    def process_scans(self, scans: List[Dict], 
                     robot_poses: Optional[List[Tuple[float, float, float]]] = None) -> np.ndarray:
        """
        Processa múltiplos scans e gera mapa de ocupação.
        
        Args:
            scans: Lista de scans (cada scan tem 'points' com ângulo, distância, qualidade)
            robot_poses: Lista de poses do robô (x, y, theta) para cada scan (opcional)
        
        Returns:
            Grid de ocupação 2D
        """
        if not scans:
            logger.warning("Nenhum scan fornecido")
            return None
        
        logger.info(f"Processando {len(scans)} scans...")
        
        # Se não há poses, assume que robô está na origem para todos os scans
        if robot_poses is None:
            robot_poses = [(0.0, 0.0, 0.0)] * len(scans)
        
        # Converte todos os pontos para coordenadas cartesianas globais
        all_occupied_points = []
        all_free_points = []
        
        parser = RPLIDARParser()
        
        for i, scan in enumerate(scans):
            if 'points' not in scan:
                continue
            
            points = scan['points']
            pose = robot_poses[i] if i < len(robot_poses) else (0.0, 0.0, 0.0)
            
            # Converte pontos para coordenadas cartesianas locais
            local_points = []
            for point in points:
                if not point.get('is_valid', True):
                    continue
                
                angle_rad = math.radians(point['angle'])
                distance = point['distance']
                
                # Coordenadas locais (relativas ao robô)
                x_local = distance * math.cos(angle_rad)
                y_local = distance * math.sin(angle_rad)
                
                # Transforma para coordenadas globais
                x_global, y_global = self._transform_point(x_local, y_local, pose)
                
                local_points.append((x_global, y_global, distance))
            
            # Separa pontos ocupados (obstáculos) e livres (espaço livre)
            # Filtra pontos muito próximos ou muito distantes (ruído)
            min_distance = 0.1  # 10cm mínimo
            max_distance = min(self.max_range, 10.0)  # Máximo 10m para salas
            
            for x, y, dist in local_points:
                # Filtra distâncias válidas
                if min_distance < dist < max_distance:
                    all_occupied_points.append((x, y))
                    
                    # Adiciona pontos livres ao longo do raio
                    num_free_points = int(dist / self.resolution)
                    for j in range(1, num_free_points):
                        ratio = j / num_free_points
                        free_x = pose[0] + (x - pose[0]) * ratio
                        free_y = pose[1] + (y - pose[1]) * ratio
                        all_free_points.append((free_x, free_y))
        
        # Cria grid de ocupação
        if not all_occupied_points:
            logger.warning("Nenhum ponto ocupado encontrado")
            return None
        
        grid = self._create_occupancy_grid(all_occupied_points, all_free_points)
        
        self.occupancy_grid = grid
        logger.info(f"Mapa gerado: {self.grid_width}x{self.grid_height} células")
        
        return grid
    
    def _transform_point(self, x: float, y: float, pose: Tuple[float, float, float]) -> Tuple[float, float]:
        """
        Transforma ponto de coordenadas locais para globais.
        
        Args:
            x, y: Coordenadas locais
            pose: Pose do robô (x, y, theta)
        
        Returns:
            Coordenadas globais (x, y)
        """
        cos_theta = math.cos(pose[2])
        sin_theta = math.sin(pose[2])
        
        x_global = pose[0] + x * cos_theta - y * sin_theta
        y_global = pose[1] + x * sin_theta + y * cos_theta
        
        return (x_global, y_global)
    
    def _create_occupancy_grid(self, 
                               occupied_points: List[Tuple[float, float]],
                               free_points: List[Tuple[float, float]]) -> np.ndarray:
        """
        Cria grid de ocupação a partir de pontos ocupados e livres.
        
        Args:
            occupied_points: Lista de pontos ocupados (obstáculos)
            free_points: Lista de pontos livres
        
        Returns:
            Grid de ocupação 2D
        """
        if not occupied_points:
            return None
        
        # Calcula limites do mapa
        all_points = occupied_points + free_points
        all_x = [p[0] for p in all_points]
        all_y = [p[1] for p in all_points]
        
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        # Adiciona margem
        margin = 1.0  # 1 metro de margem
        min_x -= margin
        max_x += margin
        min_y -= margin
        max_y += margin
        
        # Calcula dimensões do grid
        width = int(math.ceil((max_x - min_x) / self.resolution))
        height = int(math.ceil((max_y - min_y) / self.resolution))
        
        # Limita tamanho máximo do grid (evita problemas de memória)
        MAX_PIXELS = 10_000_000  # 10M pixels
        if width * height > MAX_PIXELS:
            scale = math.sqrt(MAX_PIXELS / (width * height))
            self.resolution = self.resolution / scale
            width = int(math.ceil((max_x - min_x) / self.resolution))
            height = int(math.ceil((max_y - min_y) / self.resolution))
            logger.warning(f"Grid muito grande, ajustando resolução para {self.resolution:.4f}m")
        
        self.grid_width = width
        self.grid_height = height
        self.origin = (min_x, min_y)
        
        # Cria grid inicializado como desconhecido
        grid = np.full((height, width), self.unknown_value, dtype=np.uint8)
        
        # Agrupa pontos próximos para formar linhas (paredes)
        # Isso ajuda a detectar estruturas lineares mesmo com ruído
        occupied_points_array = np.array(occupied_points)
        
        # Marca pontos ocupados com agrupamento espacial
        for x, y in occupied_points:
            col = int((x - min_x) / self.resolution)
            row = int((y - min_y) / self.resolution)
            
            if 0 <= col < width and 0 <= row < height:
                # Inverte Y (grid tem origem no canto superior esquerdo)
                grid[height - row - 1, col] = self.occupied_value
        
        # Aplica filtro para conectar pontos próximos (ajuda a formar linhas)
        # Isso é especialmente útil quando o sensor está girando no mesmo lugar
        # e deveria detectar paredes retas
        
        # Marca pontos livres
        for x, y in free_points:
            col = int((x - min_x) / self.resolution)
            row = int((y - min_y) / self.resolution)
            
            if 0 <= col < width and 0 <= row < height:
                grid[height - row - 1, col] = self.free_value
        
        # Aplica dilatação aos obstáculos (para segurança e conectar pontos próximos)
        # Isso ajuda a formar linhas contínuas quando o sensor está girando no mesmo lugar
        dilation_pixels = max(2, int(0.15 / self.resolution))  # 15cm de dilatação (aumentado)
        if dilation_pixels > 0:
            occupied_mask = (grid == self.occupied_value)
            structure = self._disk_kernel(dilation_pixels)
            dilated = binary_dilation(occupied_mask, structure=structure)
            grid[dilated] = self.occupied_value
        
        # Aplica erosão leve para manter apenas estruturas sólidas
        # Remove pontos isolados mas mantém linhas (paredes)
        erosion_pixels = max(1, int(0.05 / self.resolution))  # 5cm de erosão
        if erosion_pixels > 0:
            occupied_mask = (grid == self.occupied_value)
            structure = self._disk_kernel(erosion_pixels)
            # Erosão apenas em áreas muito pequenas (remove ruído)
            from scipy.ndimage import label
            labeled, num_features = label(occupied_mask)
            for i in range(1, num_features + 1):
                component = (labeled == i)
                if component.sum() < 5:  # Remove componentes com menos de 5 pixels
                    grid[component] = self.unknown_value
        
        logger.info(f"Grid criado: {width}x{height} pixels, resolução {self.resolution:.4f}m")
        logger.info(f"  Pontos ocupados: {len(occupied_points)}")
        logger.info(f"  Pontos livres: {len(free_points)}")
        
        return grid
    
    def _disk_kernel(self, radius: int) -> np.ndarray:
        """Cria kernel circular para dilatação."""
        size = radius * 2 + 1
        kernel = np.zeros((size, size), dtype=bool)
        center = radius
        
        for i in range(size):
            for j in range(size):
                dist = math.sqrt((i - center)**2 + (j - center)**2)
                if dist <= radius:
                    kernel[i, j] = True
        
        return kernel
    
    def refine_map(self, 
                   noise_reduction: bool = True,
                   hole_filling: bool = True,
                   dilation: int = 1,
                   erosion: int = 1) -> np.ndarray:
        """
        Refina o mapa aplicando filtros e operações morfológicas.
        
        Args:
            noise_reduction: Remove ruído
            hole_filling: Preenche pequenos buracos
            dilation: Pixels de dilatação
            erosion: Pixels de erosão
        
        Returns:
            Grid refinado
        """
        if self.occupancy_grid is None:
            logger.warning("Nenhum mapa para refinar")
            return None
        
        grid = self.occupancy_grid.copy()
        
        # Redução de ruído (remove células isoladas)
        if noise_reduction:
            occupied_mask = (grid == self.occupied_value)
            # Remove células ocupadas isoladas
            from scipy.ndimage import label
            labeled, num_features = label(occupied_mask)
            for i in range(1, num_features + 1):
                component = (labeled == i)
                if component.sum() < 5:  # Remove componentes com menos de 5 pixels
                    grid[component] = self.unknown_value
        
        # Preenchimento de buracos
        if hole_filling:
            # Preenche pequenos buracos em áreas ocupadas
            free_mask = (grid == self.free_value)
            from scipy.ndimage import label
            labeled, num_features = label(free_mask)
            for i in range(1, num_features + 1):
                component = (labeled == i)
                if component.sum() < 10:  # Preenche buracos com menos de 10 pixels
                    grid[component] = self.occupied_value
        
        # Operações morfológicas
        if dilation > 0:
            occupied_mask = (grid == self.occupied_value)
            structure = self._disk_kernel(dilation)
            dilated = binary_dilation(occupied_mask, structure=structure)
            grid[dilated] = self.occupied_value
        
        if erosion > 0:
            occupied_mask = (grid == self.occupied_value)
            structure = self._disk_kernel(erosion)
            eroded = binary_erosion(occupied_mask, structure=structure)
            grid[~eroded & (grid == self.occupied_value)] = self.free_value
        
        self.occupancy_grid = grid
        logger.info("Mapa refinado")
        
        return grid
    
    def get_map_info(self) -> Dict:
        """Retorna informações do mapa."""
        if self.occupancy_grid is None:
            return {}
        
        height, width = self.occupancy_grid.shape
        
        occupied_count = np.sum(self.occupancy_grid == self.occupied_value)
        free_count = np.sum(self.occupancy_grid == self.free_value)
        unknown_count = np.sum(self.occupancy_grid == self.unknown_value)
        total = width * height
        
        return {
            'width': width,
            'height': height,
            'resolution': self.resolution,
            'origin': self.origin,
            'size_meters': (width * self.resolution, height * self.resolution),
            'occupied_pixels': int(occupied_count),
            'free_pixels': int(free_count),
            'unknown_pixels': int(unknown_count),
            'occupied_percent': float(occupied_count / total * 100),
            'free_percent': float(free_count / total * 100),
            'unknown_percent': float(unknown_count / total * 100)
        }

