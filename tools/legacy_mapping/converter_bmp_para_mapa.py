"""
Script para converter arquivos BMP/PNG (mapas 2D do Aurora) para formato PGM/YAML
Útil quando o Aurora exporta diretamente o mapa 2D processado.
"""

import sys
from pathlib import Path
import numpy as np
from PIL import Image
import yaml
import logging

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.pgm_yaml_generator import PGMYAMLGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def converter_bmp_para_mapa(bmp_path, output_base, resolution=0.05, origin=(0.0, 0.0, 0.0)):
    """
    Converte arquivo BMP/PNG para mapa PGM/YAML.
    
    Args:
        bmp_path: Caminho para arquivo BMP ou PNG
        output_base: Nome base para arquivos de saída (sem extensão)
        resolution: Resolução do mapa em metros por pixel
        origin: Origem do mapa (x, y, yaw)
    """
    logger.info(f"Carregando imagem: {bmp_path}")
    
    # Carrega imagem
    try:
        img = Image.open(bmp_path)
        if img.mode != 'L':  # Se não for escala de cinza, converte
            img = img.convert('L')
        img_array = np.array(img)
    except Exception as e:
        logger.error(f"Erro ao carregar imagem: {e}")
        return False
    
    logger.info(f"Imagem carregada: {img_array.shape}")
    
    # Converte para occupancy grid
    # Em mapas BMP do Aurora:
    # - Branco (255) = área livre
    # - Preto (0) = área ocupada
    # - Cinza = área desconhecida
    
    # Cria grid de ocupação
    grid = np.full_like(img_array, -1, dtype=np.int8)  # -1 = desconhecido
    
    # Áreas brancas (livres) -> 0
    grid[img_array > 200] = 0
    
    # Áreas pretas (ocupadas) -> 100
    grid[img_array < 50] = 100
    
    # Áreas cinzas (desconhecidas) -> -1 (já está)
    # grid[(img_array >= 50) & (img_array <= 200)] = -1
    
    logger.info(f"Grid de ocupação criado")
    logger.info(f"  Ocupado: {np.sum(grid == 100)} pixels")
    logger.info(f"  Livre: {np.sum(grid == 0)} pixels")
    logger.info(f"  Desconhecido: {np.sum(grid == -1)} pixels")
    
    # Gera arquivos PGM + YAML
    logger.info("Gerando arquivos PGM + YAML...")
    generator = PGMYAMLGenerator(
        grid,
        resolution,
        origin
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
        description="Converte arquivo BMP/PNG (mapa 2D) para formato PGM/YAML"
    )
    parser.add_argument("input_file", help="Arquivo BMP ou PNG de entrada")
    parser.add_argument("--output", "-o", default=None,
                       help="Nome base para arquivos de saída (padrão: nome do arquivo)")
    parser.add_argument("--resolution", "-r", type=float, default=0.05,
                       help="Resolução do mapa em metros por pixel (padrão: 0.05)")
    parser.add_argument("--origin-x", type=float, default=0.0,
                       help="Coordenada X da origem")
    parser.add_argument("--origin-y", type=float, default=0.0,
                       help="Coordenada Y da origem")
    
    args = parser.parse_args()
    
    # Define nome de saída se não fornecido
    if args.output is None:
        args.output = Path(args.input_file).stem
    
    converter_bmp_para_mapa(
        args.input_file,
        args.output,
        resolution=args.resolution,
        origin=(args.origin_x, args.origin_y, 0.0)
    )

