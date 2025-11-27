"""
Leitor de Mapas do C1
Obtém mapas processados do Slamtec C1 via API.
"""

import sys
from pathlib import Path
from typing import Optional, Dict
import logging

# Garante que o diretório raiz esteja no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import requests
import yaml

from src.core.slamware_c1_uploader import SlamwareC1Uploader

logger = logging.getLogger(__name__)


class C1MapReader:
    """
    Leitor de mapas processados do C1.
    
    Obtém mapas já processados pelo SLAM interno do C1 via API REST.
    """
    
    def __init__(self, api_client: Optional[SlamwareC1Uploader] = None):
        """
        Inicializa o leitor de mapas.
        
        Args:
            api_client: Cliente API do C1 (se None, cria novo)
        """
        self.api_client = api_client or SlamwareC1Uploader()
        self.base_url = self.api_client.base_url
    
    def get_active_map(self, output_dir: Path) -> Optional[Dict]:
        """
        Obtém o mapa ativo do C1.
        
        Args:
            output_dir: Diretório para salvar os arquivos do mapa
        
        Returns:
            Dicionário com caminhos dos arquivos salvos:
            {
                'pgm': str,
                'yaml': str,
                'map_name': str
            }
            ou None se erro
        """
        try:
            # Obtém nome do mapa ativo
            active_map_name = self._get_active_map_name()
            if not active_map_name:
                logger.error("Não foi possível obter nome do mapa ativo")
                return None
            
            logger.info(f"Obtendo mapa ativo: {active_map_name}")
            return self.get_map_by_name(active_map_name, output_dir)
        except Exception as e:
            logger.error(f"Erro ao obter mapa ativo: {e}")
            return None
    
    def get_map_by_name(self, map_name: str, output_dir: Path) -> Optional[Dict]:
        """
        Obtém mapa específico do C1 pelo nome.
        
        Args:
            map_name: Nome do mapa
            output_dir: Diretório para salvar os arquivos
        
        Returns:
            Dicionário com caminhos dos arquivos salvos ou None
        """
        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Tenta baixar PGM
            pgm_path = self._download_pgm(map_name, output_dir)
            
            # Tenta baixar YAML
            yaml_path = self._download_yaml(map_name, output_dir)
            
            if not pgm_path and not yaml_path:
                logger.error(f"Não foi possível baixar mapa '{map_name}'")
                return None
            
            result = {
                'map_name': map_name,
                'pgm': str(pgm_path) if pgm_path else None,
                'yaml': str(yaml_path) if yaml_path else None
            }
            
            logger.info(f"Mapa '{map_name}' obtido com sucesso")
            return result
        except Exception as e:
            logger.error(f"Erro ao obter mapa '{map_name}': {e}")
            return None
    
    def list_available_maps(self) -> list:
        """
        Lista mapas disponíveis no C1.
        
        Returns:
            Lista de nomes de mapas
        """
        try:
            maps = self.api_client.list_maps()
            return maps
        except Exception as e:
            logger.error(f"Erro ao listar mapas: {e}")
            return []
    
    def _get_active_map_name(self) -> Optional[str]:
        """
        Obtém o nome do mapa ativo.
        
        Returns:
            Nome do mapa ativo ou None
        """
        try:
            # Tenta endpoint específico para mapa ativo
            response = self.api_client.session.get(
                f"{self.base_url}/api/v1/maps/active",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('name') or data.get('map_name')
            
            # Fallback: pega primeiro mapa da lista
            maps = self.list_available_maps()
            if maps:
                return maps[0]
            
            return None
        except Exception as e:
            logger.debug(f"Erro ao obter mapa ativo: {e}")
            # Fallback: pega primeiro mapa da lista
            maps = self.list_available_maps()
            return maps[0] if maps else None
    
    def _download_pgm(self, map_name: str, output_dir: Path) -> Optional[Path]:
        """
        Baixa arquivo PGM do mapa.
        
        Args:
            map_name: Nome do mapa
            output_dir: Diretório de saída
        
        Returns:
            Caminho do arquivo salvo ou None
        """
        try:
            # Tenta diferentes endpoints possíveis
            endpoints = [
                f"/api/v1/maps/{map_name}/pgm",
                f"/api/v1/maps/{map_name}",
                f"/api/v1/maps/{map_name}/download"
            ]
            
            for endpoint in endpoints:
                try:
                    response = self.api_client.session.get(
                        f"{self.base_url}{endpoint}",
                        timeout=10,
                        stream=True
                    )
                    
                    if response.status_code == 200:
                        pgm_path = output_dir / f"{map_name}.pgm"
                        with open(pgm_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        logger.info(f"PGM baixado: {pgm_path}")
                        return pgm_path
                except Exception as e:
                    logger.debug(f"Erro ao baixar PGM de {endpoint}: {e}")
                    continue
            
            logger.warning(f"Não foi possível baixar PGM do mapa '{map_name}'")
            return None
        except Exception as e:
            logger.error(f"Erro ao baixar PGM: {e}")
            return None
    
    def _download_yaml(self, map_name: str, output_dir: Path) -> Optional[Path]:
        """
        Baixa arquivo YAML do mapa.
        
        Args:
            map_name: Nome do mapa
            output_dir: Diretório de saída
        
        Returns:
            Caminho do arquivo salvo ou None
        """
        try:
            # Tenta diferentes endpoints possíveis
            endpoints = [
                f"/api/v1/maps/{map_name}/yaml",
                f"/api/v1/maps/{map_name}/metadata",
                f"/api/v1/maps/{map_name}"
            ]
            
            for endpoint in endpoints:
                try:
                    response = self.api_client.session.get(
                        f"{self.base_url}{endpoint}",
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        # Verifica se é JSON (metadados) ou YAML
                        content_type = response.headers.get('Content-Type', '')
                        
                        if 'application/json' in content_type:
                            # Converte JSON para YAML
                            data = response.json()
                            yaml_path = output_dir / f"{map_name}.yaml"
                            with open(yaml_path, 'w') as f:
                                yaml.dump(data, f, default_flow_style=False)
                        else:
                            # Assume que já é YAML
                            yaml_path = output_dir / f"{map_name}.yaml"
                            with open(yaml_path, 'wb') as f:
                                f.write(response.content)
                        
                        logger.info(f"YAML baixado: {yaml_path}")
                        return yaml_path
                except Exception as e:
                    logger.debug(f"Erro ao baixar YAML de {endpoint}: {e}")
                    continue
            
            logger.warning(f"Não foi possível baixar YAML do mapa '{map_name}'")
            return None
        except Exception as e:
            logger.error(f"Erro ao baixar YAML: {e}")
            return None

