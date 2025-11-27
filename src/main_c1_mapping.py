#!/usr/bin/env python3
"""
C1 Mapping Studio - Entry Point

Sistema completo para gerar mapas diretamente do sensor Slamtec C1 Lidar.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Garante que o diretório raiz esteja no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Agora pode importar módulos do src
from src.c1_mapping.capture.c1_usb_client import C1USBClient
from src.c1_mapping.capture.scan_collector import ScanCollector
from src.c1_mapping.capture.c1_map_reader import C1MapReader
from src.c1_mapping.slam.slam_processor import SLAMProcessor
from src.c1_mapping.export.pgm_exporter import PGMExporter
from src.c1_mapping.export.visualizer import MapVisualizer
from src.core.slamware_c1_uploader import SlamwareC1Uploader
import json
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def detect_c1(verbose: bool = False):
    """
    Detecta e exibe informações detalhadas do C1.
    
    Args:
        verbose: Se True, exibe informações detalhadas de validação
    """
    print("🔍 Detectando C1...")
    print("=" * 70)
    print()
    
    client = C1USBClient()
    detection = client.detect_c1()
    
    if detection['found']:
        print(f"✅ C1 DETECTADO!")
        print(f"   Método: {detection['type'].upper()}")
        print(f"   Porta/Endereço: {detection['port']}")
        print()
        
        info = detection.get('info', {})
        
        # Informações específicas por tipo
        if detection['type'] == 'api':
            print("📡 Informações da API:")
            if info.get('device_info'):
                device_info = info['device_info']
                print(f"   - IP: {info.get('ip', 'N/A')}")
                print(f"   - Porta: {info.get('port', 'N/A')}")
                if device_info.get('device_type'):
                    print(f"   - Tipo: {device_info['device_type']}")
                if device_info.get('firmware_version'):
                    print(f"   - Firmware: {device_info['firmware_version']}")
            
            if verbose and info.get('validation_details'):
                val = info['validation_details']
                print()
                print("   🔬 Validação:")
                print(f"      - Conexão: {'✅' if val.get('connection_ok') else '❌'}")
                print(f"      - Info do dispositivo: {'✅' if val.get('device_info_ok') else '❌'}")
                print(f"      - Endpoints API: {'✅' if val.get('api_endpoints_ok') else '❌'}")
                if val.get('working_endpoints'):
                    print(f"      - Endpoints funcionando: {len(val['working_endpoints'])}")
                    for ep in val['working_endpoints']:
                        print(f"        • {ep}")
        
        elif detection['type'] == 'serial':
            print("🔌 Informações Serial:")
            print(f"   - Porta: {info.get('port', 'N/A')}")
            print(f"   - Descrição: {info.get('description', 'N/A')}")
            print(f"   - VID: 0x{info.get('vid', 0):04X}")
            print(f"   - PID: 0x{info.get('pid', 0):04X}")
            if info.get('serial_number'):
                print(f"   - Serial Number: {info['serial_number']}")
            
            if verbose and info.get('validation_details'):
                val = info['validation_details']
                print()
                print("   🔬 Validação:")
                validated = info.get('validated', False)
                print(f"      - Validado como C1: {'✅ SIM' if validated else '⚠️  NÃO'}")
                if val.get('port_accessible'):
                    print(f"      - Porta acessível: ✅")
                    print(f"      - Baudrate testado: {val.get('baudrate_tested', 'N/A')}")
                    print(f"      - Resposta recebida: {'✅' if val.get('response_received') else '❌'}")
                    print(f"      - Assinatura C1: {'✅' if val.get('c1_signature_found') else '❌'}")
                else:
                    print(f"      - Porta acessível: ❌")
                
                if not validated:
                    print()
                    print("   ⚠️  ATENÇÃO: Dispositivo detectado mas não validado como C1.")
                    print("      Pode ser outro dispositivo USB Serial.")
        
        print()
        print("💡 Próximos passos:")
        if detection['type'] == 'api':
            print("   - Execute: python3 src/main_c1_mapping.py list-maps")
            print("   - Execute: python3 src/main_c1_mapping.py get-map --output mapas/c1/final")
        elif detection['type'] == 'serial':
            print("   - Execute: python3 scripts/teste_c1_diagnostico.py (para diagnóstico completo)")
            print("   - Verifique se o dispositivo é realmente o C1")
        
        return True
    else:
        print("❌ C1 NÃO DETECTADO")
        print()
        print("💡 Verifique:")
        print("   - C1 está conectado via USB ou rede?")
        print("   - C1 está ligado?")
        print("   - Drivers USB instalados?")
        print("   - C1 está na mesma rede? (para API REST)")
        print()
        print("🔬 Para diagnóstico completo, execute:")
        print("   python3 scripts/teste_c1_diagnostico.py")
        return False


def get_map_from_c1(output_dir: str, map_name: Optional[str] = None):
    """
    Obtém mapa do C1 (se ele tiver SLAM interno).
    
    Args:
        output_dir: Diretório para salvar mapa
        map_name: Nome do mapa (None = mapa ativo)
    """
    print("📥 Obtendo mapa do C1...")
    print("=" * 50)
    
    # Conecta via API
    api_client = SlamwareC1Uploader()
    if not api_client.check_connection():
        print("❌ Não foi possível conectar ao C1 via API")
        print("💡 Verifique se o C1 está acessível via rede")
        return False
    
    # Cria leitor
    reader = C1MapReader(api_client)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Obtém mapa
    if map_name:
        result = reader.get_map_by_name(map_name, output_path)
    else:
        result = reader.get_active_map(output_path)
    
    if result:
        print("\n✅ Mapa obtido com sucesso!")
        if result.get('pgm'):
            print(f"   PGM: {result['pgm']}")
        if result.get('yaml'):
            print(f"   YAML: {result['yaml']}")
        return True
    else:
        print("\n❌ Não foi possível obter mapa")
        print("💡 O C1 pode não ter SLAM interno ou o mapa pode não existir")
        return False


def collect_scans(output_dir: str, duration: float = 60.0, full_scans: bool = True):
    """
    Coleta varreduras brutas do C1.
    
    Args:
        output_dir: Diretório para salvar scans
        duration: Duração da coleta em segundos
        full_scans: Se True, coleta scans completos (360°). Se False, coleta continuamente.
    """
    print("🔄 Coletando varreduras do C1...")
    print("=" * 70)
    
    # Conecta
    client = C1USBClient()
    detection = client.detect_c1()
    
    if not detection['found']:
        print("❌ C1 não detectado")
        return False
    
    if detection['type'] != 'serial':
        print("❌ Coleta de scans requer conexão Serial (RPLIDAR)")
        return False
    
    if not client.connect('serial'):
        print("❌ Não foi possível conectar ao C1")
        return False
    
    # Cria coletor
    output_path = Path(output_dir)
    collector = ScanCollector(client, output_path)
    
    # Coleta
    mode = "scans completos (360°)" if full_scans else "dados contínuos"
    print(f"\n⏱️  Coletando por {duration}s")
    print(f"   Modo: {mode}")
    print("   Pressione Ctrl+C para parar antes do tempo\n")
    
    collector.start_collection(duration=duration, collect_full_scans=full_scans)
    
    print(f"\n✅ Coleta finalizada!")
    print(f"   Scans coletados: {collector.get_scan_count()}")
    print(f"   Salvos em: {output_path}")
    
    client.disconnect()
    return True


def list_maps():
    """Lista mapas disponíveis no C1."""
    print("📋 Listando mapas do C1...")
    print("=" * 50)
    
    api_client = SlamwareC1Uploader()
    if not api_client.check_connection():
        print("❌ Não foi possível conectar ao C1 via API")
        return False
    
    maps = api_client.list_maps()
    
    if maps:
        print(f"\n✅ {len(maps)} mapa(s) encontrado(s):")
        for i, map_name in enumerate(maps, 1):
            print(f"   {i}. {map_name}")
    else:
        print("\nℹ️  Nenhum mapa encontrado")
    
    return True


def process_scans(input_file: str, output_dir: str, resolution: float = 0.05):
    """
    Processa scans coletados e gera mapa de ocupação.
    
    Args:
        input_file: Arquivo JSON com scans coletados
        output_dir: Diretório para salvar mapa processado
        resolution: Resolução do mapa em metros (padrão: 0.05 = 5cm)
    """
    print("🗺️  Processando scans e gerando mapa...")
    print("=" * 70)
    
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ Arquivo não encontrado: {input_file}")
        return False
    
    # Carrega scans
    print(f"📂 Carregando scans de: {input_file}")
    try:
        with open(input_path, 'r') as f:
            scan_data = json.load(f)
    except Exception as e:
        print(f"❌ Erro ao carregar arquivo: {e}")
        return False
    
    scans = scan_data.get('scans', [])
    if not scans:
        print("❌ Nenhum scan encontrado no arquivo")
        return False
    
    print(f"   {len(scans)} scans encontrados")
    
    # Processa scans
    print(f"\n🔬 Processando scans com resolução {resolution}m...")
    processor = SLAMProcessor(resolution=resolution)
    
    grid = processor.process_scans(scans)
    
    if grid is None:
        print("❌ Falha ao processar scans")
        return False
    
    # Refina mapa
    print("\n✨ Refinando mapa...")
    processor.refine_map(
        noise_reduction=True,
        hole_filling=True,
        dilation=2,
        erosion=1
    )
    
    # Informações do mapa
    map_info = processor.get_map_info()
    print("\n📊 Informações do Mapa:")
    print(f"   Dimensões: {map_info['width']}x{map_info['height']} pixels")
    print(f"   Tamanho: {map_info['size_meters'][0]:.2f}m x {map_info['size_meters'][1]:.2f}m")
    print(f"   Resolução: {map_info['resolution']:.4f}m")
    print(f"   Ocupado: {map_info['occupied_percent']:.1f}%")
    print(f"   Livre: {map_info['free_percent']:.1f}%")
    print(f"   Desconhecido: {map_info['unknown_percent']:.1f}%")
    
    # Salva mapa processado
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    map_name = input_path.stem.replace('scans_', 'map_')
    map_file = output_path / f"{map_name}.npy"
    
    np.save(map_file, processor.occupancy_grid)
    
    # Salva metadados
    metadata = {
        'map_info': map_info,
        'processor_config': {
            'resolution': resolution,
            'max_range': processor.max_range
        },
        'source_file': str(input_path)
    }
    
    metadata_file = output_path / f"{map_name}_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n✅ Mapa processado salvo em: {map_file}")
    print(f"   Metadados: {metadata_file}")
    
    return True


def visualize_map(map_file: str, output_image: Optional[str] = None):
    """
    Visualiza mapa de ocupação.
    
    Args:
        map_file: Arquivo .npy com mapa processado ou arquivo JSON com scans
        output_image: Caminho para salvar imagem (opcional)
    """
    print("👁️  Visualizando mapa...")
    print("=" * 70)
    
    map_path = Path(map_file)
    if not map_path.exists():
        print(f"❌ Arquivo não encontrado: {map_file}")
        return False
    
    visualizer = MapVisualizer()
    
    # Tenta carregar como mapa processado (.npy)
    if map_path.suffix == '.npy':
        print(f"📂 Carregando mapa processado: {map_file}")
        try:
            grid = np.load(map_path)
            
            # Tenta carregar metadados
            metadata_file = map_path.parent / f"{map_path.stem}_metadata.json"
            resolution = 0.05
            origin = (0.0, 0.0)
            
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    map_info = metadata.get('map_info', {})
                    resolution = map_info.get('resolution', 0.05)
                    origin_tuple = map_info.get('origin', (0.0, 0.0))
                    origin = (origin_tuple[0], origin_tuple[1]) if isinstance(origin_tuple, (list, tuple)) else (0.0, 0.0)
            
            title = f"Mapa de Ocupação - {map_path.stem}"
            success = visualizer.visualize_map(
                grid, resolution, origin,
                output_path=output_image,
                title=title
            )
            
            if success:
                print("✅ Visualização concluída")
            return success
            
        except Exception as e:
            print(f"❌ Erro ao carregar mapa: {e}")
            return False
    
    # Tenta carregar como arquivo de scans (.json)
    elif map_path.suffix == '.json':
        print(f"📂 Carregando scans de: {map_file}")
        try:
            with open(map_path, 'r') as f:
                scan_data = json.load(f)
            
            scans = scan_data.get('scans', [])
            if not scans:
                print("❌ Nenhum scan encontrado")
                return False
            
            # Processa primeiro scan para visualizar
            if scans and 'points' in scans[0]:
                success = visualizer.visualize_scan(scans[0], output_path=output_image)
                if success:
                    print("✅ Visualização concluída")
                return success
            
        except Exception as e:
            print(f"❌ Erro ao carregar scans: {e}")
            return False
    
    else:
        print(f"❌ Formato de arquivo não suportado: {map_path.suffix}")
        return False


def export_map(map_file: str, output_dir: str, map_name: Optional[str] = None):
    """
    Exporta mapa processado em formato PGM/YAML compatível com C1.
    
    Args:
        map_file: Arquivo .npy com mapa processado
        output_dir: Diretório para salvar arquivos PGM/YAML
        map_name: Nome do mapa (padrão: nome do arquivo)
    """
    print("📤 Exportando mapa em formato PGM/YAML...")
    print("=" * 70)
    
    map_path = Path(map_file)
    if not map_path.exists():
        print(f"❌ Arquivo não encontrado: {map_file}")
        return False
    
    if map_path.suffix != '.npy':
        print("❌ Arquivo deve ser .npy (mapa processado)")
        return False
    
    # Carrega mapa
    print(f"📂 Carregando mapa: {map_file}")
    try:
        grid = np.load(map_path)
    except Exception as e:
        print(f"❌ Erro ao carregar mapa: {e}")
        return False
    
    # Carrega metadados
    metadata_file = map_path.parent / f"{map_path.stem}_metadata.json"
    resolution = 0.05
    origin = (0.0, 0.0, 0.0)
    
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
            map_info = metadata.get('map_info', {})
            resolution = map_info.get('resolution', 0.05)
            origin_tuple = map_info.get('origin', (0.0, 0.0))
            if isinstance(origin_tuple, (list, tuple)):
                origin = (origin_tuple[0], origin_tuple[1], 0.0)
    
    # Exporta
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    if map_name is None:
        map_name = map_path.stem.replace('map_', '')
    
    base_path = output_path / map_name
    
    print(f"\n📤 Exportando para: {base_path}")
    exporter = PGMExporter(grid, resolution, origin)
    success, pgm_path, yaml_path = exporter.export(str(base_path))
    
    if success:
        print(f"\n✅ Mapa exportado com sucesso!")
        print(f"   PGM: {pgm_path}")
        print(f"   YAML: {yaml_path}")
        print(f"\n💡 Este mapa pode ser usado:")
        print(f"   - Na interface de navegação (main.py)")
        print(f"   - Para upload no C1 (se compatível)")
        print(f"   - Para adicionar POIs e áreas proibidas")
        return True
    else:
        print("❌ Falha ao exportar mapa")
        return False


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="C1 Mapping Studio - Gerador de mapas do Slamtec C1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Detectar C1
  python3 src/main_c1_mapping.py detect

  # Obter mapa do C1
  python3 src/main_c1_mapping.py get-map --output mapas/c1/final

  # Coletar varreduras brutas
  python3 src/main_c1_mapping.py collect --output mapas/c1/raw --duration 60

  # Listar mapas disponíveis
  python3 src/main_c1_mapping.py list-maps

  # Processar scans coletados e gerar mapa
  python3 src/main_c1_mapping.py process --input mapas/c1/raw/scans_*.json --output mapas/c1/processed

  # Visualizar mapa
  python3 src/main_c1_mapping.py visualize --map mapas/c1/processed/map_*.npy

  # Exportar mapa em PGM/YAML
  python3 src/main_c1_mapping.py export --map mapas/c1/processed/map_*.npy --output mapas/c1/final
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comando a executar')
    
    # Comando: detect
    detect_parser = subparsers.add_parser('detect', help='Detecta C1 conectado')
    detect_parser.add_argument('--verbose', '-v', action='store_true',
                              help='Exibe informações detalhadas de validação')
    
    # Comando: get-map
    get_map_parser = subparsers.add_parser('get-map', help='Obtém mapa do C1')
    get_map_parser.add_argument('--output', '-o', type=str, default='mapas/c1/final',
                               help='Diretório de saída (padrão: mapas/c1/final)')
    get_map_parser.add_argument('--map-name', type=str, default=None,
                               help='Nome do mapa (padrão: mapa ativo)')
    
    # Comando: collect
    collect_parser = subparsers.add_parser('collect', help='Coleta varreduras brutas')
    collect_parser.add_argument('--output', '-o', type=str, default='mapas/c1/raw',
                               help='Diretório de saída (padrão: mapas/c1/raw)')
    collect_parser.add_argument('--duration', '-d', type=float, default=60.0,
                               help='Duração em segundos (padrão: 60)')
    collect_parser.add_argument('--full-scans', action='store_true', default=True,
                               help='Coleta scans completos (360°) - padrão')
    collect_parser.add_argument('--continuous', action='store_true',
                               help='Coleta dados contínuos (não agrupa em scans completos)')
    
    # Comando: list-maps
    subparsers.add_parser('list-maps', help='Lista mapas disponíveis no C1')
    
    # Comando: process
    process_parser = subparsers.add_parser('process', help='Processa scans e gera mapa')
    process_parser.add_argument('--input', '-i', type=str, required=True,
                               help='Arquivo JSON com scans coletados')
    process_parser.add_argument('--output', '-o', type=str, default='mapas/c1/processed',
                               help='Diretório de saída (padrão: mapas/c1/processed)')
    process_parser.add_argument('--resolution', '-r', type=float, default=0.05,
                               help='Resolução do mapa em metros (padrão: 0.05)')
    
    # Comando: visualize
    visualize_parser = subparsers.add_parser('visualize', help='Visualiza mapa ou scans')
    visualize_parser.add_argument('--map', '-m', type=str, required=True,
                                 help='Arquivo .npy (mapa) ou .json (scans)')
    visualize_parser.add_argument('--output', '-o', type=str, default=None,
                                 help='Caminho para salvar imagem (opcional)')
    
    # Comando: export
    export_parser = subparsers.add_parser('export', help='Exporta mapa em PGM/YAML')
    export_parser.add_argument('--map', '-m', type=str, required=True,
                              help='Arquivo .npy com mapa processado')
    export_parser.add_argument('--output', '-o', type=str, default='mapas/c1/final',
                              help='Diretório de saída (padrão: mapas/c1/final)')
    export_parser.add_argument('--name', '-n', type=str, default=None,
                              help='Nome do mapa (padrão: nome do arquivo)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Executa comando
    if args.command == 'detect':
        detect_c1(verbose=args.verbose if hasattr(args, 'verbose') else False)
    elif args.command == 'get-map':
        get_map_from_c1(args.output, args.map_name)
    elif args.command == 'collect':
        full_scans = not args.continuous if hasattr(args, 'continuous') else True
        collect_scans(args.output, args.duration, full_scans)
    elif args.command == 'list-maps':
        list_maps()
    elif args.command == 'process':
        process_scans(args.input, args.output, args.resolution)
    elif args.command == 'visualize':
        visualize_map(args.map, args.output)
    elif args.command == 'export':
        export_map(args.map, args.output, args.name)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

