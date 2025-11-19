"""
Pipeline Completo: Aurora → C1
Pipeline integrado para processar mapas do Aurora e enviar para o C1.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, Tuple
import numpy as np

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.aurora_connector import AuroraConnector
from src.core.stcm_processor import STCMProcessor
from src.core.map_converter_3d_to_2d import MapConverter3DTo2D
from src.core.pgm_yaml_generator import PGMYAMLGenerator
from src.core.slamware_c1_uploader import SlamwareC1Uploader

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AuroraToC1Pipeline:
    """
    Pipeline completo para processar mapas do Aurora e enviar para o C1.
    
    Fluxo:
    1. Conecta ao Aurora (ou carrega arquivo .stcm)
    2. Extrai nuvem de pontos 3D
    3. Converte para mapa 2D (occupancy grid)
    4. Gera arquivos PGM + YAML
    5. Faz upload para o C1
    """
    
    def __init__(self, 
                 aurora_ip: Optional[str] = None,
                 c1_ip: str = "192.168.1.101",
                 resolution: float = 0.05,
                 height_range: Tuple[float, float] = (0.0, 2.0)):
        """
        Inicializa o pipeline.
        
        Args:
            aurora_ip: IP do Aurora (None para usar apenas arquivos .stcm)
            c1_ip: IP do C1
            resolution: Resolução do mapa em metros
            height_range: Faixa de altura para considerar pontos
        """
        self.aurora_ip = aurora_ip
        self.c1_ip = c1_ip
        self.resolution = resolution
        self.height_range = height_range
        
        self.aurora = None
        self.point_cloud = None
        self.occupancy_grid = None
        self.map_origin = (0.0, 0.0, 0.0)
        
    def connect_aurora(self) -> bool:
        """
        Conecta ao Aurora via rede.
        
        Returns:
            True se conexão bem-sucedida
        """
        if self.aurora_ip is None:
            logger.warning("IP do Aurora não configurado")
            return False
        
        try:
            self.aurora = AuroraConnector(self.aurora_ip)
            return self.aurora.connect()
        except Exception as e:
            logger.error(f"Erro ao conectar ao Aurora: {e}")
            return False
    
    def load_stcm_file(self, stcm_path: str) -> bool:
        """
        Carrega arquivo .stcm do Aurora.
        
        Args:
            stcm_path: Caminho para arquivo .stcm
            
        Returns:
            True se carregamento bem-sucedido
        """
        try:
            processor = STCMProcessor(stcm_path)
            if not processor.load():
                return False
            
            # Extrai nuvem de pontos
            self.point_cloud = processor.extract_point_cloud()
            if self.point_cloud is None:
                logger.error("Não foi possível extrair nuvem de pontos")
                return False
            
            logger.info(f"Nuvem de pontos carregada: {len(self.point_cloud)} pontos")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao carregar arquivo .stcm: {e}")
            return False
    
    def download_map_from_aurora(self, output_path: str) -> bool:
        """
        Baixa mapa do Aurora via rede.
        
        Args:
            output_path: Caminho para salvar o arquivo .stcm
            
        Returns:
            True se download bem-sucedido
        """
        if self.aurora is None or not self.aurora.connected:
            logger.error("Aurora não conectado")
            return False
        
        return self.aurora.download_map_stcm(output_path)
    
    def convert_to_2d(self, apply_morphology: bool = True,
                     inflate_obstacles: bool = True,
                     inflation_radius: float = 0.2) -> bool:
        """
        Converte nuvem de pontos 3D para mapa 2D.
        
        Args:
            apply_morphology: Se True, aplica operações morfológicas
            inflate_obstacles: Se True, infla obstáculos
            inflation_radius: Raio de inflação em metros
            
        Returns:
            True se conversão bem-sucedida
        """
        if self.point_cloud is None or len(self.point_cloud) == 0:
            logger.error("Nuvem de pontos não disponível")
            return False
        
        try:
            converter = MapConverter3DTo2D(
                resolution=self.resolution,
                height_range=self.height_range
            )
            
            # Converte para 2D
            grid = converter.convert(self.point_cloud, method="projection")
            if grid is None:
                return False
            
            # Aplica processamento
            if apply_morphology:
                grid = converter.apply_morphology(grid)
            
            if inflate_obstacles:
                grid = converter.inflate_obstacles(grid, inflation_radius)
            
            self.occupancy_grid = grid
            self.map_origin = (*converter.get_origin(), 0.0)
            
            logger.info(f"Mapa 2D criado: {grid.shape}, origem: {self.map_origin[:2]}")
            return True
            
        except Exception as e:
            logger.error(f"Erro na conversão 3D→2D: {e}")
            return False
    
    def generate_map_files(self, output_base_path: str) -> Tuple[bool, str, str]:
        """
        Gera arquivos PGM e YAML.
        
        Args:
            output_base_path: Caminho base (sem extensão) para os arquivos
            
        Returns:
            Tupla (sucesso, caminho_pgm, caminho_yaml)
        """
        if self.occupancy_grid is None:
            logger.error("Mapa 2D não disponível")
            return (False, "", "")
        
        try:
            generator = PGMYAMLGenerator(
                self.occupancy_grid,
                self.resolution,
                self.map_origin
            )
            
            return generator.generate_both(output_base_path)
            
        except Exception as e:
            logger.error(f"Erro ao gerar arquivos do mapa: {e}")
            return (False, "", "")
    
    def upload_to_c1(self, pgm_path: str, yaml_path: str, 
                    map_name: str = "aurora_map") -> bool:
        """
        Faz upload do mapa para o C1.
        
        Args:
            pgm_path: Caminho para arquivo .pgm
            yaml_path: Caminho para arquivo .yaml
            map_name: Nome do mapa no C1
            
        Returns:
            True se upload bem-sucedido
        """
        try:
            uploader = SlamwareC1Uploader(self.c1_ip)
            if not uploader.check_connection():
                logger.error("Não foi possível conectar ao C1")
                return False
            
            success = uploader.upload_map(pgm_path, yaml_path, map_name)
            if success:
                # Define como mapa ativo
                uploader.set_active_map(map_name)
            
            return success
            
        except Exception as e:
            logger.error(f"Erro ao fazer upload para o C1: {e}")
            return False
    
    def run_full_pipeline(self, 
                         stcm_path: Optional[str] = None,
                         output_dir: str = "mapas/otimizados",
                         map_name: str = "aurora_map",
                         upload_to_c1: bool = True) -> bool:
        """
        Executa o pipeline completo.
        
        Args:
            stcm_path: Caminho para arquivo .stcm (None para baixar do Aurora)
            output_dir: Diretório para salvar arquivos gerados
            map_name: Nome do mapa
            upload_to_c1: Se True, faz upload para o C1
            
        Returns:
            True se pipeline executado com sucesso
        """
        logger.info("=== Iniciando Pipeline Aurora → C1 ===")
        
        # 1. Carrega ou baixa mapa do Aurora
        if stcm_path:
            logger.info(f"Carregando arquivo .stcm: {stcm_path}")
            if not self.load_stcm_file(stcm_path):
                return False
        else:
            logger.info("Baixando mapa do Aurora...")
            if not self.connect_aurora():
                return False
            
            # Baixa mapa
            os.makedirs(output_dir, exist_ok=True)
            temp_stcm = os.path.join(output_dir, f"{map_name}_temp.stcm")
            if not self.download_map_from_aurora(temp_stcm):
                return False
            
            if not self.load_stcm_file(temp_stcm):
                return False
        
        # 2. Converte para 2D
        logger.info("Convertendo mapa 3D → 2D...")
        if not self.convert_to_2d():
            return False
        
        # 3. Gera arquivos PGM + YAML
        logger.info("Gerando arquivos PGM + YAML...")
        os.makedirs(output_dir, exist_ok=True)
        output_base = os.path.join(output_dir, map_name)
        success, pgm_path, yaml_path = self.generate_map_files(output_base)
        
        if not success:
            return False
        
        logger.info(f"✅ Arquivos gerados:")
        logger.info(f"   PGM: {pgm_path}")
        logger.info(f"   YAML: {yaml_path}")
        
        # 4. Upload para C1 (opcional)
        if upload_to_c1:
            logger.info("Fazendo upload para o C1...")
            if not self.upload_to_c1(pgm_path, yaml_path, map_name):
                logger.warning("Upload para C1 falhou, mas arquivos foram gerados")
                return False
            logger.info("✅ Upload para C1 concluído")
        
        logger.info("=== Pipeline concluído com sucesso ===")
        return True
    
    def cleanup(self):
        """Limpa recursos."""
        if self.aurora:
            self.aurora.disconnect()


def main():
    """Função principal para execução via linha de comando."""
    parser = argparse.ArgumentParser(
        description="Pipeline Aurora → C1: Processa mapas do Aurora e envia para o C1"
    )
    
    parser.add_argument(
        "--stcm",
        type=str,
        help="Caminho para arquivo .stcm (se não fornecido, baixa do Aurora)"
    )
    
    parser.add_argument(
        "--aurora-ip",
        type=str,
        default="192.168.1.100",
        help="Endereço IP do Aurora (padrão: 192.168.1.100)"
    )
    
    parser.add_argument(
        "--c1-ip",
        type=str,
        default="192.168.1.101",
        help="Endereço IP do C1 (padrão: 192.168.1.101)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="mapas/otimizados",
        help="Diretório para salvar arquivos gerados"
    )
    
    parser.add_argument(
        "--map-name",
        type=str,
        default="aurora_map",
        help="Nome do mapa"
    )
    
    parser.add_argument(
        "--resolution",
        type=float,
        default=0.05,
        help="Resolução do mapa em metros (padrão: 0.05 = 5cm)"
    )
    
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Não fazer upload para o C1 (apenas gerar arquivos)"
    )
    
    args = parser.parse_args()
    
    # Cria pipeline
    pipeline = AuroraToC1Pipeline(
        aurora_ip=args.aurora_ip if not args.stcm else None,
        c1_ip=args.c1_ip,
        resolution=args.resolution
    )
    
    try:
        # Executa pipeline
        success = pipeline.run_full_pipeline(
            stcm_path=args.stcm,
            output_dir=args.output_dir,
            map_name=args.map_name,
            upload_to_c1=not args.no_upload
        )
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("Pipeline interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)
    finally:
        pipeline.cleanup()


if __name__ == "__main__":
    main()

