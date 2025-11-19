"""
Script de Teste de Conexão com Aurora
Testa conectividade com o sensor Slamtec Aurora.
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.aurora_connector import AuroraConnector
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_aurora_connection(ip_address="192.168.1.100"):
    """Testa conexão com o Aurora."""
    print(f"🔌 Testando conexão com Aurora em {ip_address}...")
    print("-" * 50)
    
    # Teste 1: Ping básico
    print("\n1️⃣  Testando conectividade de rede...")
    import subprocess
    try:
        result = subprocess.run(
            ["ping", "-n", "2", ip_address],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("   ✅ Aurora responde ao ping")
        else:
            print("   ❌ Aurora não responde ao ping")
            print("   💡 Verifique:")
            print("      - Aurora está ligado?")
            print("      - Cabo de rede conectado?")
            print("      - IP correto?")
            return False
    except Exception as e:
        print(f"   ⚠️  Erro ao fazer ping: {e}")
        print("   💡 Continuando com teste de conexão Python...")
    
    # Teste 2: Conexão Python
    print("\n2️⃣  Testando conexão TCP/IP...")
    aurora = AuroraConnector(ip_address)
    
    if aurora.connect():
        print("   ✅ Conexão TCP estabelecida")
    else:
        print("   ❌ Não foi possível estabelecer conexão TCP")
        print("   💡 Verifique:")
        print("      - Porta TCP correta? (padrão: 1445)")
        print("      - Firewall bloqueando?")
        print("      - Protocolo correto?")
        return False
    
    # Teste 3: Informações do dispositivo
    print("\n3️⃣  Obtendo informações do dispositivo...")
    info = aurora.get_device_info()
    if info:
        print(f"   ✅ Informações obtidas:")
        for key, value in info.items():
            print(f"      {key}: {value}")
    else:
        print("   ⚠️  Não foi possível obter informações")
        print("   💡 O protocolo pode ser diferente do esperado")
    
    # Teste 4: Listar mapas
    print("\n4️⃣  Listando mapas disponíveis...")
    maps = aurora.get_map_list()
    if maps:
        print(f"   ✅ Mapas encontrados: {len(maps)}")
        for i, map_name in enumerate(maps, 1):
            print(f"      {i}. {map_name}")
    else:
        print("   ℹ️  Nenhum mapa encontrado (ou protocolo diferente)")
    
    # Limpeza
    aurora.disconnect()
    
    print("\n" + "=" * 50)
    print("✅ Teste de conexão concluído!")
    print("\n💡 Nota: Se alguns testes falharam, pode ser que:")
    print("   - O protocolo do Aurora seja diferente do esperado")
    print("   - Seja necessário usar interface web do Aurora")
    print("   - Os comandos precisem ser ajustados")
    print("   - Consulte a documentação oficial do Aurora")
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Testa conexão com Slamtec Aurora")
    parser.add_argument(
        "--ip",
        type=str,
        default="192.168.1.100",
        help="Endereço IP do Aurora (padrão: 192.168.1.100)"
    )
    
    args = parser.parse_args()
    
    test_aurora_connection(args.ip)

