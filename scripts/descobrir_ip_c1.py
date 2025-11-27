#!/usr/bin/env python3
"""
Script para descobrir o IP do C1 na rede
Varre a rede local procurando pelo C1 via API REST.
"""

import sys
from pathlib import Path
import socket
import subprocess
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Garante que o diretório raiz esteja no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️  Biblioteca 'requests' não disponível. Instale com: pip install requests")

from src.core.slamware_c1_uploader import SlamwareC1Uploader


def get_local_network():
    """Obtém a rede local."""
    try:
        # Obtém IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # Obtém máscara de rede
        result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'default' in line or local_ip in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'src' and i + 1 < len(parts):
                        # Tenta obter máscara
                        break
        
        # Assume /24 por padrão
        network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        return network
    except Exception as e:
        print(f"⚠️  Erro ao obter rede local: {e}")
        # Fallback para rede comum
        return ipaddress.IPv4Network("192.168.1.0/24", strict=False)


def check_c1_ip(ip: str, timeout: float = 2.0) -> dict:
    """
    Verifica se um IP responde como C1.
    
    Args:
        ip: Endereço IP para testar
        timeout: Timeout em segundos
    
    Returns:
        Dicionário com resultado do teste
    """
    result = {
        'ip': ip,
        'found': False,
        'info': None,
        'error': None
    }
    
    if not REQUESTS_AVAILABLE:
        return result
    
    try:
        api_client = SlamwareC1Uploader(ip_address=ip, port=1445)
        
        # Tenta conectar
        if api_client.check_connection():
            result['found'] = True
            
            # Obtém informações do dispositivo
            info = api_client.get_device_info()
            result['info'] = info
            
            # Tenta listar mapas
            try:
                maps = api_client.list_maps()
                result['maps'] = maps
            except:
                pass
            
            return result
    except Exception as e:
        result['error'] = str(e)
    
    return result


def discover_c1_network_scan():
    """Varre a rede procurando pelo C1."""
    print("=" * 70)
    print("🔍 DESCOBRINDO IP DO C1 NA REDE")
    print("=" * 70)
    print()
    
    # Obtém rede local
    network = get_local_network()
    print(f"📡 Varrendo rede: {network}")
    print(f"   Total de IPs a testar: {network.num_addresses - 2}")  # -2 para network e broadcast
    print()
    
    # Lista de IPs para testar
    hosts = [str(ip) for ip in network.hosts()]
    
    print("⏳ Testando IPs... (isso pode levar alguns minutos)")
    print()
    
    found_devices = []
    
    # Testa em paralelo (máximo 20 threads)
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_c1_ip, ip): ip for ip in hosts}
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            if completed % 10 == 0:
                print(f"   Progresso: {completed}/{len(hosts)} IPs testados...", end='\r')
            
            result = future.result()
            if result['found']:
                found_devices.append(result)
                print(f"\n   ✅ C1 encontrado em: {result['ip']}")
    
    print(f"\n   ✅ Varredura concluída: {completed} IPs testados")
    print()
    
    return found_devices


def main():
    """Função principal."""
    if not REQUESTS_AVAILABLE:
        print("❌ Biblioteca 'requests' necessária para este script")
        print("   Instale com: pip install requests")
        return
    
    # Varre rede
    devices = discover_c1_network_scan()
    
    # Resultados
    print("=" * 70)
    print("📊 RESULTADOS")
    print("=" * 70)
    print()
    
    if devices:
        print(f"✅ {len(devices)} dispositivo(s) C1 encontrado(s):\n")
        for i, device in enumerate(devices, 1):
            print(f"{i}. IP: {device['ip']}:1445")
            if device.get('info'):
                info = device['info']
                print(f"   - Informações do dispositivo:")
                for key, value in info.items():
                    print(f"     • {key}: {value}")
            if device.get('maps'):
                print(f"   - Mapas disponíveis: {len(device['maps'])}")
                for map_name in device['maps'][:5]:
                    print(f"     • {map_name}")
            print()
        
        print("💡 Para usar o C1, configure o IP em config/c1_mapping.json ou use:")
        print(f"   python3 src/main_c1_mapping.py detect")
        print()
        print("   Ou edite o código para usar o IP descoberto.")
    else:
        print("❌ Nenhum C1 encontrado na rede")
        print()
        print("💡 Verifique:")
        print("   - C1 está ligado e conectado à rede?")
        print("   - C1 está na mesma rede que este computador?")
        print("   - Firewall não está bloqueando a porta 1445?")
        print("   - C1 pode estar usando um IP diferente")
        print()
        print("   Você pode tentar conectar manualmente:")
        print("   - Verifique o IP do C1 no display/interface do dispositivo")
        print("   - Ou use: python3 src/main_c1_mapping.py detect")


if __name__ == "__main__":
    main()

