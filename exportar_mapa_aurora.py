"""
Script para ajudar a exportar mapas do Aurora
Conecta ao Aurora e fornece instruções para exportação.
"""

import sys
import requests
import webbrowser
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def verificar_aurora(ip_address="192.168.11.1"):
    """
    Verifica se o Aurora está acessível e tenta abrir a interface web.
    """
    print(f"🔍 Verificando conexão com Aurora em {ip_address}...")
    print("=" * 60)
    
    # Teste 1: Ping básico
    import subprocess
    try:
        result = subprocess.run(
            ["ping", "-n", "2", ip_address],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✅ Aurora responde ao ping")
        else:
            print("❌ Aurora não responde ao ping")
            print("   Verifique:")
            print("   - Aurora está ligado?")
            print("   - Cabo de rede conectado?")
            print("   - IP correto?")
            return False
    except Exception as e:
        print(f"⚠️  Erro ao fazer ping: {e}")
        print("   Continuando com teste HTTP...")
    
    # Teste 2: Interface Web HTTP
    print(f"\n🌐 Testando interface web HTTP...")
    urls = [
        f"http://{ip_address}",
        f"http://{ip_address}:80",
        f"http://{ip_address}:8080",
        f"https://{ip_address}",
    ]
    
    accessible = False
    for url in urls:
        try:
            response = requests.get(url, timeout=3, verify=False)
            if response.status_code == 200:
                print(f"✅ Interface web acessível em: {url}")
                accessible = True
                print(f"\n🚀 Abrindo navegador em: {url}")
                webbrowser.open(url)
                break
        except requests.exceptions.RequestException:
            continue
    
    if not accessible:
        print("⚠️  Interface web não encontrada nas URLs padrão")
        print(f"   Tente acessar manualmente: http://{ip_address}")
        print(f"   Ou: https://{ip_address}")
    
    return accessible


def instrucoes_exportacao():
    """
    Fornece instruções passo a passo para exportar o mapa.
    """
    print("\n" + "=" * 60)
    print("📋 INSTRUÇÕES PARA EXPORTAR MAPA DO AURORA")
    print("=" * 60)
    print()
    print("1️⃣  Acesse a interface web do Aurora no navegador")
    print("    (O navegador deve ter aberto automaticamente)")
    print()
    print("2️⃣  Procure por uma das seguintes opções:")
    print("    - Menu 'Map' ou 'Mapa'")
    print("    - Menu 'Export' ou 'Exportar'")
    print("    - Menu 'Download' ou 'Download'")
    print("    - Menu 'File' ou 'Arquivo' → 'Export'")
    print()
    print("3️⃣  Selecione o mapa que deseja exportar")
    print()
    print("4️⃣  Escolha o formato de exportação:")
    print("    ✅ PLY (Point Cloud) - RECOMENDADO")
    print("    ✅ PCD (Point Cloud Data)")
    print("    ✅ BMP/PNG (Mapa 2D)")
    print("    ⚠️  STCM (formato proprietário - não recomendado)")
    print()
    print("5️⃣  Salve o arquivo em:")
    print(f"    {Path('mapas/originais_aurora').absolute()}")
    print()
    print("6️⃣  Após exportar, execute:")
    print("    py converter_ply_para_mapa.py mapas/originais_aurora/seu_arquivo.ply")
    print()
    print("=" * 60)


def verificar_arquivo_exportado():
    """
    Verifica se há arquivos exportados na pasta.
    """
    pasta = Path("mapas/originais_aurora")
    pasta.mkdir(parents=True, exist_ok=True)
    
    arquivos = list(pasta.glob("*.ply")) + list(pasta.glob("*.pcd")) + list(pasta.glob("*.bmp")) + list(pasta.glob("*.png"))
    
    if arquivos:
        print("\n📁 Arquivos encontrados na pasta:")
        for arquivo in arquivos:
            tamanho = arquivo.stat().st_size / 1024 / 1024
            print(f"   ✅ {arquivo.name} ({tamanho:.2f} MB)")
        return arquivos
    else:
        print("\n📁 Nenhum arquivo PLY/PCD/BMP/PNG encontrado ainda")
        print(f"   Pasta: {pasta.absolute()}")
        return []


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ajuda a exportar mapas do Aurora")
    parser.add_argument(
        "--ip",
        type=str,
        default="192.168.11.1",
        help="Endereço IP do Aurora (padrão: 192.168.11.1)"
    )
    parser.add_argument(
        "--verificar-arquivos",
        action="store_true",
        help="Apenas verifica arquivos já exportados"
    )
    
    args = parser.parse_args()
    
    if args.verificar_arquivos:
        verificar_arquivo_exportado()
    else:
        if verificar_aurora(args.ip):
            instrucoes_exportacao()
        
        print("\n" + "=" * 60)
        print("⏳ Aguardando exportação...")
        print("   (Pressione Enter após exportar o arquivo)")
        print("=" * 60)
        
        input()
        
        arquivos = verificar_arquivo_exportado()
        if arquivos:
            print("\n✅ Arquivo exportado encontrado!")
            print("\n🔄 Para processar o arquivo, execute:")
            for arquivo in arquivos:
                if arquivo.suffix.lower() in ['.ply', '.pcd']:
                    print(f"   py converter_ply_para_mapa.py {arquivo} --output {arquivo.stem}")

