"""
Visualizador de Mapas
Visualiza mapas de ocupação e scans LIDAR.
"""

import sys
from pathlib import Path
from typing import Optional, List, Tuple, Dict
import numpy as np
import logging

# Garante que o diretório raiz esteja no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

logger = logging.getLogger(__name__)


class MapVisualizer:
    """
    Visualizador de mapas de ocupação e scans LIDAR.
    """
    
    def __init__(self):
        """Inicializa o visualizador."""
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib não disponível. Visualização limitada.")
    
    def visualize_map(self, occupancy_grid: np.ndarray,
                     resolution: float,
                     origin: Tuple[float, float] = (0.0, 0.0),
                     output_path: Optional[str] = None,
                     show_scan_points: Optional[List[Dict]] = None,
                     title: str = "Mapa de Ocupação") -> bool:
        """
        Visualiza mapa de ocupação.
        
        Args:
            occupancy_grid: Grid de ocupação
            resolution: Resolução em metros
            origin: Origem do mapa (x, y)
            output_path: Caminho para salvar imagem (opcional)
            show_scan_points: Lista de scans para sobrepor (opcional)
            title: Título do gráfico
        
        Returns:
            True se visualização bem-sucedida
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.error("Matplotlib não disponível")
            return False
        
        try:
            fig, ax = plt.subplots(figsize=(12, 12))
            
            # Cria imagem colorida do mapa
            height, width = occupancy_grid.shape
            
            # Converte para imagem RGB
            img = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Ocupado (preto)
            occupied_mask = (occupancy_grid == 0) | (occupancy_grid == 100)
            img[occupied_mask] = [0, 0, 0]
            
            # Livre (branco)
            free_mask = (occupancy_grid == 254) | (occupancy_grid == 0)
            img[free_mask] = [255, 255, 255]
            
            # Desconhecido (cinza)
            unknown_mask = (occupancy_grid == 205) | (occupancy_grid == -1)
            img[unknown_mask] = [128, 128, 128]
            
            # Exibe mapa
            ax.imshow(img, origin='upper', extent=[
                origin[0],
                origin[0] + width * resolution,
                origin[1],
                origin[1] + height * resolution
            ])
            
            # Adiciona scans se fornecidos
            if show_scan_points:
                self._plot_scans(ax, show_scan_points, resolution, origin)
            
            ax.set_xlabel('X (metros)')
            ax.set_ylabel('Y (metros)')
            ax.set_title(title)
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal')
            
            if output_path:
                plt.savefig(output_path, dpi=150, bbox_inches='tight')
                logger.info(f"Visualização salva em: {output_path}")
            else:
                plt.show()
            
            plt.close()
            return True
            
        except Exception as e:
            logger.error(f"Erro ao visualizar mapa: {e}", exc_info=True)
            return False
    
    def _plot_scans(self, ax, scans: List[Dict], resolution: float, origin: Tuple[float, float]):
        """Plota scans sobre o mapa."""
        import math
        
        parser = None
        try:
            from src.c1_mapping.capture.rplidar_parser import RPLIDARParser
            parser = RPLIDARParser()
        except:
            return
        
        colors = plt.cm.tab10(np.linspace(0, 1, min(len(scans), 10)))
        
        for i, scan in enumerate(scans[:10]):  # Limita a 10 scans para não poluir
            if 'points' not in scan:
                continue
            
            points = scan['points']
            color = colors[i % len(colors)]
            
            # Converte pontos para coordenadas cartesianas
            x_coords = []
            y_coords = []
            
            for point in points:
                if not point.get('is_valid', True):
                    continue
                
                angle_rad = math.radians(point['angle'])
                distance = point['distance']
                
                x = distance * math.cos(angle_rad)
                y = distance * math.sin(angle_rad)
                
                x_coords.append(x)
                y_coords.append(y)
            
            if x_coords:
                ax.scatter(x_coords, y_coords, c=[color], s=1, alpha=0.5, label=f'Scan {i+1}')
        
        # Plota posição do robô (origem)
        ax.plot(0, 0, 'ro', markersize=10, label='Robô')
        ax.legend(loc='upper right', fontsize=8)
    
    def visualize_scan(self, scan: Dict, output_path: Optional[str] = None) -> bool:
        """
        Visualiza um único scan LIDAR.
        
        Args:
            scan: Dicionário com dados do scan
            output_path: Caminho para salvar imagem (opcional)
        
        Returns:
            True se visualização bem-sucedida
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.error("Matplotlib não disponível")
            return False
        
        try:
            import math
            
            if 'points' not in scan:
                logger.warning("Scan não tem pontos")
                return False
            
            points = scan['points']
            
            fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
            
            angles = []
            distances = []
            
            for point in points:
                if point.get('is_valid', True):
                    angles.append(math.radians(point['angle']))
                    distances.append(point['distance'])
            
            if angles:
                ax.scatter(angles, distances, s=1, alpha=0.6)
                ax.set_theta_zero_location('N')
                ax.set_theta_direction(-1)
                ax.set_title('Scan LIDAR')
                ax.set_ylabel('Distância (metros)')
                
                if output_path:
                    plt.savefig(output_path, dpi=150, bbox_inches='tight')
                    logger.info(f"Visualização salva em: {output_path}")
                else:
                    plt.show()
                
                plt.close()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao visualizar scan: {e}", exc_info=True)
            return False

