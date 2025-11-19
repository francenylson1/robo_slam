"""
Uploader para Slamtec C1 via SLAMWARE API
Faz upload de mapas PGM/YAML para o sensor C1.
"""

import requests
import json
from typing import Optional, Dict, Tuple
import os
import logging

logger = logging.getLogger(__name__)


class SlamwareC1Uploader:
    """
    Classe para fazer upload de mapas para o Slamtec C1 via API SLAMWARE.
    
    O C1 utiliza a API REST do SLAMWARE para gerenciamento de mapas.
    """
    
    def __init__(self, ip_address: str = "192.168.1.101", port: int = 1445):
        """
        Inicializa o uploader.
        
        Args:
            ip_address: Endereço IP do C1
            port: Porta da API SLAMWARE (padrão: 1445)
        """
        self.ip_address = ip_address
        self.port = port
        self.base_url = f"http://{ip_address}:{port}"
        self.session = requests.Session()
        self.session.timeout = 10.0
        
    def check_connection(self) -> bool:
        """
        Verifica se o C1 está acessível.
        
        Returns:
            True se conectado
        """
        try:
            # Endpoint de status/health check
            response = self.session.get(f"{self.base_url}/api/v1/status", timeout=5)
            if response.status_code == 200:
                logger.info(f"Conectado ao C1 em {self.ip_address}")
                return True
            else:
                logger.warning(f"C1 respondeu com código {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao conectar ao C1: {e}")
            return False
    
    def get_device_info(self) -> Optional[Dict]:
        """
        Obtém informações do dispositivo C1.
        
        Returns:
            Dicionário com informações ou None
        """
        try:
            response = self.session.get(f"{self.base_url}/api/v1/device/info")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro ao obter informações: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Erro ao obter informações do C1: {e}")
            return None
    
    def upload_map(self, pgm_path: str, yaml_path: str, 
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
        if not os.path.exists(pgm_path):
            logger.error(f"Arquivo PGM não encontrado: {pgm_path}")
            return False
        
        if not os.path.exists(yaml_path):
            logger.error(f"Arquivo YAML não encontrado: {yaml_path}")
            return False
        
        try:
            # Lê arquivo YAML para obter metadados
            import yaml
            with open(yaml_path, 'r') as f:
                map_metadata = yaml.safe_load(f)
            
            # Prepara dados do mapa
            map_data = {
                "name": map_name,
                "metadata": map_metadata
            }
            
            # Faz upload do arquivo PGM
            with open(pgm_path, 'rb') as f:
                files = {
                    'map': (os.path.basename(pgm_path), f, 'image/x-portable-graymap')
                }
                data = {
                    'name': map_name,
                    'metadata': json.dumps(map_metadata)
                }
                
                # TODO: Ajustar endpoint conforme documentação da API SLAMWARE
                response = self.session.post(
                    f"{self.base_url}/api/v1/maps/upload",
                    files=files,
                    data=data
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"Mapa '{map_name}' enviado com sucesso para o C1")
                    return True
                else:
                    logger.error(f"Erro no upload: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Erro ao fazer upload do mapa: {e}")
            return False
    
    def list_maps(self) -> list:
        """
        Lista mapas disponíveis no C1.
        
        Returns:
            Lista de nomes de mapas
        """
        try:
            response = self.session.get(f"{self.base_url}/api/v1/maps")
            if response.status_code == 200:
                maps = response.json()
                return [m.get('name', 'unknown') for m in maps]
            else:
                logger.error(f"Erro ao listar mapas: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Erro ao listar mapas: {e}")
            return []
    
    def set_active_map(self, map_name: str) -> bool:
        """
        Define o mapa ativo no C1.
        
        Args:
            map_name: Nome do mapa a ativar
            
        Returns:
            True se sucesso
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/maps/active",
                json={"name": map_name}
            )
            if response.status_code == 200:
                logger.info(f"Mapa '{map_name}' definido como ativo")
                return True
            else:
                logger.error(f"Erro ao ativar mapa: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Erro ao ativar mapa: {e}")
            return False
    
    def delete_map(self, map_name: str) -> bool:
        """
        Remove um mapa do C1.
        
        Args:
            map_name: Nome do mapa a remover
            
        Returns:
            True se sucesso
        """
        try:
            response = self.session.delete(
                f"{self.base_url}/api/v1/maps/{map_name}"
            )
            if response.status_code in [200, 204]:
                logger.info(f"Mapa '{map_name}' removido")
                return True
            else:
                logger.error(f"Erro ao remover mapa: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Erro ao remover mapa: {e}")
            return False


def upload_map_to_c1(pgm_path: str, yaml_path: str,
                     c1_ip: str = "192.168.1.101",
                     map_name: str = "aurora_map") -> bool:
    """
    Função auxiliar para fazer upload de mapa para o C1.
    
    Args:
        pgm_path: Caminho para arquivo .pgm
        yaml_path: Caminho para arquivo .yaml
        c1_ip: Endereço IP do C1
        map_name: Nome do mapa
        
    Returns:
        True se upload bem-sucedido
    """
    uploader = SlamwareC1Uploader(c1_ip)
    if uploader.check_connection():
        return uploader.upload_map(pgm_path, yaml_path, map_name)
    else:
        logger.error("Não foi possível conectar ao C1")
        return False


if __name__ == "__main__":
    # Teste básico
    logging.basicConfig(level=logging.INFO)
    
    uploader = SlamwareC1Uploader()
    if uploader.check_connection():
        info = uploader.get_device_info()
        if info:
            print(f"✅ Informações do C1: {info}")
        
        maps = uploader.list_maps()
        print(f"Mapas disponíveis: {maps}")

