"""
Script para converter arquivos PLY/PCD (exportados do Aurora) para mapa 2D
Alternativa quando o formato .stcm não pode ser lido diretamente.
"""

import sys
import numpy as np
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.map_converter_3d_to_2d import MapConverter3DTo2D
from src.core.pgm_yaml_generator import PGMYAMLGenerator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def converter_ply_para_mapa(ply_path, output_base, resolution=0.05, height_range=(0.0, 2.0)):
    """
    Converte arquivo PLY/PCD para mapa 2D.
    
    Args:
        ply_path: Caminho para arquivo PLY ou PCD
        output_base: Nome base para arquivos de saída (sem extensão)
        resolution: Resolução do mapa em metros
        height_range: Faixa de altura para considerar pontos
    """
    try:
        import open3d as o3d
    except ImportError:
        logger.error("Open3D não está instalado. Instale com: py -m pip install open3d")
        return False
    
    logger.info(f"Carregando nuvem de pontos: {ply_path}")
    
    # Carrega nuvem de pontos
    pcd = o3d.io.read_point_cloud(str(ply_path))
    
    if len(pcd.points) == 0:
        logger.error("Nuvem de pontos vazia!")
        return False
    
    # Converte para numpy
    points = np.asarray(pcd.points)
    logger.info(f"Nuvem de pontos carregada: {len(points)} pontos")
    
    # Converte para mapa 2D
    logger.info("Convertendo para mapa 2D...")
    converter = MapConverter3DTo2D(resolution=resolution, height_range=height_range)
    grid = converter.convert(points, method="projection")
    
    if grid is None:
        logger.error("Falha na conversão")
        return False
    
    # Aplica processamento
    grid = converter.apply_morphology(grid)
    grid = converter.inflate_obstacles(grid, inflation_radius=0.2)
    
    # Gera arquivos PGM + YAML
    logger.info("Gerando arquivos PGM + YAML...")
    generator = PGMYAMLGenerator(
        grid,
        converter.get_resolution(),
        (*converter.get_origin(), 0.0)
    )
    
    output_dir = Path("mapas/otimizados")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / output_base
    success, pgm_path, yaml_path = generator.generate_both(str(output_path))
    
    if success:
        logger.info(f"✅ Mapa gerado com sucesso!")
        logger.info(f"   PGM: {pgm_path}")
        logger.info(f"   YAML: {yaml_path}")
        return True
    else:
        logger.error("Falha ao gerar arquivos")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Converte arquivo PLY/PCD para mapa 2D (PGM + YAML)"
    )
    parser.add_argument("input_file", help="Arquivo PLY ou PCD de entrada")
    parser.add_argument("--output", "-o", default="mapa_processado", 
                       help="Nome base para arquivos de saída")
    parser.add_argument("--resolution", "-r", type=float, default=0.05,
                       help="Resolução do mapa em metros (padrão: 0.05)")
    parser.add_argument("--height-min", type=float, default=0.0,
                       help="Altura mínima em metros")
    parser.add_argument("--height-max", type=float, default=2.0,
                       help="Altura máxima em metros")
    
    args = parser.parse_args()
    
    converter_ply_para_mapa(
        args.input_file,
        args.output,
        resolution=args.resolution,
        height_range=(args.height_min, args.height_max)
    )

