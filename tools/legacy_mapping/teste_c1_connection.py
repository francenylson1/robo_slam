"""
Script de Teste de Conexão com C1
Testa conectividade e API do Slamtec C1.
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.slamware_c1_uploader import SlamwareC1Uploader
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_c1_connection(ip_address="192.168.1.101"):
    """Testa conexão com o C1."""
    print(f"🔌 Testando conexão com C1 em {ip_address}...")
    print("-" * 50)
    
    uploader = SlamwareC1Uploader(ip_address)
    
    # Teste 1: Conexão básica
    print("\n1️⃣  Testando conectividade...")
    if uploader.check_connection():
        print("   ✅ C1 está acessível")
    else:
        print("   ❌ Não foi possível conectar ao C1")
        print("   💡 Verifique:")
        print("      - C1 está ligado?")
        print("      - IP correto?")
        print("      - Mesma rede?")
        print("      - Firewall bloqueando?")
        return False
    
    # Teste 2: Informações do dispositivo
    print("\n2️⃣  Obtendo informações do dispositivo...")
    info = uploader.get_device_info()
    if info:
        print(f"   ✅ Informações obtidas:")
        for key, value in info.items():
            print(f"      {key}: {value}")
    else:
        print("   ⚠️  Não foi possível obter informações")
        print("   💡 A API pode ter endpoints diferentes")
    
    # Teste 3: Listar mapas
    print("\n3️⃣  Listando mapas disponíveis...")
    maps = uploader.list_maps()
    if maps:
        print(f"   ✅ Mapas encontrados: {len(maps)}")
        for i, map_name in enumerate(maps, 1):
            print(f"      {i}. {map_name}")
    else:
        print("   ℹ️  Nenhum mapa encontrado (ou API diferente)")
    
    print("\n" + "=" * 50)
    print("✅ Teste de conexão concluído!")
    print("\n💡 Nota: Se alguns testes falharam, pode ser que:")
    print("   - A API SLAMWARE tenha endpoints diferentes")
    print("   - Seja necessário autenticação")
    print("   - O protocolo seja diferente do esperado")
    print("   - Consulte a documentação oficial do C1")
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Testa conexão com Slamtec C1")
    parser.add_argument(
        "--ip",
        type=str,
        default="192.168.1.101",
        help="Endereço IP do C1 (padrão: 192.168.1.101)"
    )
    
    args = parser.parse_args()
    
    test_c1_connection(args.ip)

