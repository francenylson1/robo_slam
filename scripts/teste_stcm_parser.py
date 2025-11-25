#!/usr/bin/env python3
"""
Script para testar diferentes métodos de parsing do arquivo .stcm
"""

import sys
import struct
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_messagepack(file_path):
    """Testa se o arquivo é MessagePack"""
    try:
        import msgpack
        with open(file_path, 'rb') as f:
            data = f.read(10000)  # Lê primeiros 10KB
            try:
                result = msgpack.unpackb(data, raw=False)
                print("✅ É MessagePack!")
                print(f"   Tipo: {type(result)}")
                if isinstance(result, dict):
                    print(f"   Chaves: {list(result.keys())[:10]}")
                return True
            except:
                return False
    except ImportError:
        print("⚠️  MessagePack não instalado (pip install msgpack)")
        return False

def test_binary_structure(file_path):
    """Analisa estrutura binária do arquivo"""
    with open(file_path, 'rb') as f:
        data = f.read()
    
    print(f"\n=== Análise Binária ===")
    print(f"Tamanho: {len(data):,} bytes")
    
    # Procura por magic numbers comuns
    magic_numbers = {
        b'STCM': 'STCM magic',
        b'\x89PNG': 'PNG',
        b'PK\x03\x04': 'ZIP',
        b'\x1f\x8b': 'GZIP',
    }
    
    for magic, name in magic_numbers.items():
        if data.startswith(magic):
            print(f"Magic number encontrado: {name}")
    
    # Procura por padrões de serialização
    # MessagePack geralmente começa com bytes específicos
    if data[0] in [0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f]:
        print("⚠️  Possível MessagePack (primeiro byte indica formato)")
    
    # Procura por seções de dados
    # Geralmente há tamanhos antes de seções de dados
    print(f"\n=== Procurando seções de dados ===")
    for i in range(0, min(100000, len(data) - 4), 1000):
        try:
            size = struct.unpack('<I', data[i:i+4])[0]
            if 1000 < size < 10000000 and i + 4 + size < len(data):
                print(f"Possível seção em offset {i}: tamanho={size:,} bytes")
        except:
            pass

def main():
    if len(sys.argv) < 2:
        print("Uso: python teste_stcm_parser.py <arquivo.stcm>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not Path(file_path).exists():
        print(f"❌ Arquivo não encontrado: {file_path}")
        sys.exit(1)
    
    print(f"🔍 Analisando: {file_path}")
    print("=" * 60)
    
    # Testa MessagePack
    print("\n1. Testando MessagePack...")
    if test_messagepack(file_path):
        print("   ✅ Arquivo parece ser MessagePack!")
    else:
        print("   ❌ Não é MessagePack ou erro ao deserializar")
    
    # Analisa estrutura binária
    print("\n2. Analisando estrutura binária...")
    test_binary_structure(file_path)
    
    # Testa parser heurístico
    print("\n3. Testando parser heurístico...")
    try:
        from core.stcm_processor import STCMProcessor
        processor = STCMProcessor(file_path)
        if processor.load():
            points = processor.extract_point_cloud()
            if points is not None:
                print(f"   ✅ Parser heurístico extraiu {len(points)} pontos!")
            else:
                print("   ❌ Parser heurístico não conseguiu extrair pontos")
    except Exception as e:
        print(f"   ❌ Erro: {e}")

if __name__ == "__main__":
    main()

