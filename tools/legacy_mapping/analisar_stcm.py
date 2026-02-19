"""
Script para analisar a estrutura de arquivos .stcm do Aurora
Ajuda a entender o formato do arquivo para implementar o parser correto.
"""

import sys
import struct
from pathlib import Path

def analisar_stcm(file_path):
    """Analisa a estrutura de um arquivo .stcm."""
    print(f"📁 Analisando arquivo: {file_path}")
    print("=" * 60)
    
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"❌ Arquivo não encontrado: {file_path}")
        return
    
    file_size = file_path.stat().st_size
    print(f"📊 Tamanho do arquivo: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
    print()
    
    with open(file_path, 'rb') as f:
        # Lê os primeiros bytes para identificar o formato
        header = f.read(100)
        f.seek(0)
        
        print("🔍 Primeiros 100 bytes (hex):")
        print(header.hex()[:200])  # Primeiros 200 caracteres hex
        print()
        
        print("🔍 Primeiros 100 bytes (tentativa de texto):")
        try:
            text_part = header.decode('utf-8', errors='ignore')
            print(repr(text_part[:100]))
        except:
            print("Não é texto UTF-8")
        print()
        
        # Verifica se é um arquivo comprimido (gzip, zlib)
        if header[:2] == b'\x1f\x8b':
            print("📦 Formato: GZIP comprimido")
        elif header[:2] == b'PK':
            print("📦 Formato: ZIP (possivelmente)")
        else:
            print("📦 Formato: Binário ou texto")
        print()
        
        # Procura por padrões conhecidos
        f.seek(0)
        data = f.read(min(10000, file_size))  # Lê primeiros 10KB
        
        # Procura por strings JSON
        try:
            text = data.decode('utf-8', errors='ignore')
            if '{' in text or '[' in text:
                print("🔍 Possível conteúdo JSON encontrado")
                # Tenta encontrar início de JSON
                start = text.find('{')
                if start >= 0:
                    print(f"   JSON começa no byte: {start}")
                    print(f"   Preview: {text[start:start+200]}")
        except:
            pass
        print()
        
        # Verifica magic numbers comuns
        f.seek(0)
        magic = f.read(4)
        print(f"🔍 Magic number (primeiros 4 bytes): {magic.hex()} = {repr(magic)}")
        
        # Verifica se tem assinatura STCM
        f.seek(0)
        if data[:4] == b'STCM' or data[:4] == b'stcm':
            print("✅ Assinatura STCM encontrada!")
        else:
            print("⚠️  Assinatura STCM não encontrada nos primeiros bytes")
        print()
        
        # Analisa estrutura de blocos
        print("📦 Análise de estrutura:")
        f.seek(0)
        
        # Tenta ler como estrutura de blocos
        try:
            # Lê possíveis cabeçalhos de blocos
            block_headers = []
            for i in range(min(10, file_size // 16)):
                pos = i * 16
                f.seek(pos)
                block = f.read(16)
                if len(block) == 16:
                    # Tenta interpretar como tamanho de bloco
                    size = struct.unpack('<I', block[:4])[0]
                    if 0 < size < file_size:
                        block_headers.append((pos, size, block.hex()[:32]))
            
            if block_headers:
                print("   Possíveis cabeçalhos de blocos encontrados:")
                for pos, size, hex_data in block_headers[:5]:
                    print(f"   Offset {pos:6d}: tamanho={size:8d} bytes, hex={hex_data}")
        except Exception as e:
            print(f"   Erro ao analisar blocos: {e}")
        print()
        
        # Verifica se tem dados de ponto flutuante (nuvem de pontos)
        print("🔍 Procurando por padrões de nuvem de pontos:")
        f.seek(0)
        sample = f.read(min(1000, file_size))
        
        # Conta sequências de floats
        float_count = 0
        for i in range(0, len(sample) - 12, 4):
            try:
                # Tenta ler como float32
                val = struct.unpack('<f', sample[i:i+4])[0]
                if -1000 < val < 1000:  # Valores razoáveis para coordenadas
                    float_count += 1
            except:
                pass
        
        print(f"   Possíveis valores float encontrados: {float_count}")
        print()
        
        # Salva amostra para análise manual
        f.seek(0)
        sample_file = file_path.with_suffix('.sample.bin')
        with open(sample_file, 'wb') as sf:
            sf.write(f.read(min(10000, file_size)))
        print(f"💾 Amostra dos primeiros 10KB salva em: {sample_file}")
        print()
        
        print("=" * 60)
        print("💡 Próximos passos:")
        print("   1. Verifique a documentação do Aurora sobre formato .stcm")
        print("   2. Use ferramentas hex editor para análise detalhada")
        print("   3. Tente abrir no software oficial do Aurora")
        print("   4. Verifique se há SDK do Aurora disponível")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        analisar_stcm(sys.argv[1])
    else:
        print("Uso: python analisar_stcm.py <arquivo.stcm>")
        print("\nExemplo:")
        print("  python analisar_stcm.py mapas/originais_aurora/sala-maker-1.stcm")

