#!/usr/bin/env python3
"""
Script de Teste Completo do Pipeline C1 Mapping
Testa todo o pipeline: Detecção → Coleta → Processamento → Exportação → Validação
"""

import sys
from pathlib import Path
import json
import time

# Garante que o diretório raiz esteja no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.c1_mapping.capture.c1_usb_client import C1USBClient
from src.c1_mapping.capture.scan_collector import ScanCollector
from src.c1_mapping.slam.slam_processor import SLAMProcessor
from src.c1_mapping.export.pgm_exporter import PGMExporter
from src.c1_mapping.export.visualizer import MapVisualizer
import numpy as np
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class PipelineTester:
    """Testa o pipeline completo do C1 Mapping."""
    
    def __init__(self):
        self.test_results = {
            'detection': False,
            'collection': False,
            'processing': False,
            'export': False,
            'validation': False
        }
        self.test_files = {}
    
    def run_all_tests(self, duration: float = 10.0):
        """Executa todos os testes do pipeline."""
        print("=" * 70)
        print("🧪 TESTE COMPLETO DO PIPELINE C1 MAPPING")
        print("=" * 70)
        print()
        
        # Teste 1: Detecção
        print("📋 TESTE 1: Detecção do C1")
        print("-" * 70)
        if self.test_detection():
            print("✅ Detecção: PASSOU\n")
        else:
            print("❌ Detecção: FALHOU\n")
            return False
        
        # Teste 2: Coleta
        print("📋 TESTE 2: Coleta de Scans")
        print("-" * 70)
        if self.test_collection(duration):
            print("✅ Coleta: PASSOU\n")
        else:
            print("❌ Coleta: FALHOU\n")
            return False
        
        # Teste 3: Processamento
        print("📋 TESTE 3: Processamento SLAM")
        print("-" * 70)
        if self.test_processing():
            print("✅ Processamento: PASSOU\n")
        else:
            print("❌ Processamento: FALHOU\n")
            return False
        
        # Teste 4: Exportação
        print("📋 TESTE 4: Exportação PGM/YAML")
        print("-" * 70)
        if self.test_export():
            print("✅ Exportação: PASSOU\n")
        else:
            print("❌ Exportação: FALHOU\n")
            return False
        
        # Teste 5: Validação
        print("📋 TESTE 5: Validação dos Arquivos")
        print("-" * 70)
        if self.test_validation():
            print("✅ Validação: PASSOU\n")
        else:
            print("❌ Validação: FALHOU\n")
            return False
        
        # Resumo final
        self.print_summary()
        return True
    
    def test_detection(self) -> bool:
        """Testa detecção do C1."""
        try:
            client = C1USBClient()
            detection = client.detect_c1()
            
            if detection['found']:
                print(f"   ✅ C1 detectado via {detection['type']}")
                print(f"      Porta: {detection['port']}")
                self.test_results['detection'] = True
                return True
            else:
                print("   ❌ C1 não detectado")
                return False
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            return False
    
    def test_collection(self, duration: float) -> bool:
        """Testa coleta de scans."""
        try:
            output_dir = Path("mapas/c1/test")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            client = C1USBClient()
            detection = client.detect_c1()
            
            if not detection['found'] or detection['type'] != 'serial':
                print("   ❌ C1 não detectado ou não é Serial")
                return False
            
            if not client.connect('serial'):
                print("   ❌ Falha ao conectar")
                return False
            
            collector = ScanCollector(client, output_dir)
            print(f"   ⏳ Coletando scans por {duration}s...")
            
            collector.start_collection(duration=duration, collect_full_scans=True)
            
            scan_count = collector.get_scan_count()
            if scan_count > 0:
                # Encontra arquivo gerado
                scan_files = list(output_dir.glob("scans_*.json"))
                if scan_files:
                    self.test_files['scans'] = scan_files[0]
                    print(f"   ✅ {scan_count} scans coletados")
                    print(f"      Arquivo: {scan_files[0]}")
                    self.test_results['collection'] = True
                    client.disconnect()
                    return True
            
            client.disconnect()
            print("   ❌ Nenhum scan coletado")
            return False
            
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_processing(self) -> bool:
        """Testa processamento SLAM."""
        try:
            if 'scans' not in self.test_files:
                print("   ❌ Arquivo de scans não encontrado")
                return False
            
            scan_file = self.test_files['scans']
            print(f"   📂 Processando: {scan_file.name}")
            
            # Carrega scans
            with open(scan_file, 'r') as f:
                scan_data = json.load(f)
            
            scans = scan_data.get('scans', [])
            if not scans:
                print("   ❌ Nenhum scan no arquivo")
                return False
            
            # Processa
            processor = SLAMProcessor(resolution=0.05)
            grid = processor.process_scans(scans)
            
            if grid is None:
                print("   ❌ Falha ao processar")
                return False
            
            # Refina
            processor.refine_map()
            
            # Salva
            output_dir = Path("mapas/c1/test")
            output_dir.mkdir(parents=True, exist_ok=True)
            map_file = output_dir / f"map_{scan_file.stem.replace('scans_', '')}.npy"
            np.save(map_file, processor.occupancy_grid)
            
            # Salva metadados
            map_info = processor.get_map_info()
            metadata_file = output_dir / f"{map_file.stem}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump({'map_info': map_info}, f, indent=2)
            
            self.test_files['map'] = map_file
            self.test_files['metadata'] = metadata_file
            
            print(f"   ✅ Mapa gerado: {map_info['width']}x{map_info['height']} pixels")
            print(f"      Arquivo: {map_file}")
            self.test_results['processing'] = True
            return True
            
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_export(self) -> bool:
        """Testa exportação PGM/YAML."""
        try:
            if 'map' not in self.test_files:
                print("   ❌ Arquivo de mapa não encontrado")
                return False
            
            map_file = self.test_files['map']
            print(f"   📂 Exportando: {map_file.name}")
            
            # Carrega mapa
            grid = np.load(map_file)
            
            # Carrega metadados
            metadata_file = self.test_files.get('metadata')
            resolution = 0.05
            origin = (0.0, 0.0, 0.0)
            
            if metadata_file and metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    map_info = metadata.get('map_info', {})
                    resolution = map_info.get('resolution', 0.05)
                    origin_tuple = map_info.get('origin', (0.0, 0.0))
                    if isinstance(origin_tuple, (list, tuple)):
                        origin = (origin_tuple[0], origin_tuple[1], 0.0)
            
            # Exporta
            output_dir = Path("mapas/c1/test")
            output_dir.mkdir(parents=True, exist_ok=True)
            base_name = map_file.stem.replace('map_', '')
            base_path = output_dir / base_name
            
            exporter = PGMExporter(grid, resolution, origin)
            success, pgm_path, yaml_path = exporter.export(str(base_path))
            
            if success:
                self.test_files['pgm'] = Path(pgm_path)
                self.test_files['yaml'] = Path(yaml_path)
                print(f"   ✅ Arquivos exportados:")
                print(f"      PGM: {pgm_path}")
                print(f"      YAML: {yaml_path}")
                self.test_results['export'] = True
                return True
            else:
                print("   ❌ Falha na exportação")
                return False
                
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_validation(self) -> bool:
        """Valida arquivos gerados."""
        try:
            print("   🔍 Validando arquivos gerados...")
            
            # Valida PGM
            if 'pgm' in self.test_files:
                pgm_file = self.test_files['pgm']
                if pgm_file.exists() and pgm_file.stat().st_size > 0:
                    print(f"   ✅ PGM válido: {pgm_file.stat().st_size} bytes")
                else:
                    print(f"   ❌ PGM inválido ou vazio")
                    return False
            
            # Valida YAML
            if 'yaml' in self.test_files:
                yaml_file = self.test_files['yaml']
                if yaml_file.exists():
                    with open(yaml_file, 'r') as f:
                        yaml_data = json.load(f) if yaml_file.suffix == '.json' else None
                    if yaml_file.suffix == '.yaml':
                        import yaml as yaml_lib
                        with open(yaml_file, 'r') as f:
                            yaml_data = yaml_lib.safe_load(f)
                    
                    if yaml_data and 'image' in yaml_data:
                        print(f"   ✅ YAML válido")
                        print(f"      Resolução: {yaml_data.get('resolution', 'N/A')}m")
                        print(f"      Origem: {yaml_data.get('origin', 'N/A')}")
                    else:
                        print(f"   ❌ YAML inválido")
                        return False
                else:
                    print(f"   ❌ YAML não encontrado")
                    return False
            
            # Verifica compatibilidade com main.py
            print("\n   🔍 Verificando compatibilidade com main.py...")
            if self.check_main_py_compatibility():
                print("   ✅ Arquivos compatíveis com main.py")
            else:
                print("   ⚠️  Alguns arquivos podem não ser compatíveis")
            
            self.test_results['validation'] = True
            return True
            
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def check_main_py_compatibility(self) -> bool:
        """Verifica se os arquivos são compatíveis com main.py."""
        try:
            # Verifica se main.py existe e pode carregar PGM
            main_py = Path("src/main.py")
            if not main_py.exists():
                print("      ⚠️  main.py não encontrado")
                return False
            
            # Verifica se map_widget.py existe (usado para carregar mapas)
            map_widget = Path("src/interfaces/map_widget.py")
            if map_widget.exists():
                print("      ✅ map_widget.py encontrado")
                return True
            else:
                print("      ⚠️  map_widget.py não encontrado")
                return False
                
        except Exception as e:
            print(f"      ⚠️  Erro ao verificar: {e}")
            return False
    
    def print_summary(self):
        """Imprime resumo dos testes."""
        print("=" * 70)
        print("📊 RESUMO DOS TESTES")
        print("=" * 70)
        print()
        
        all_passed = all(self.test_results.values())
        
        for test_name, passed in self.test_results.items():
            status = "✅ PASSOU" if passed else "❌ FALHOU"
            print(f"   {test_name.upper():15} {status}")
        
        print()
        
        if all_passed:
            print("✅ TODOS OS TESTES PASSARAM!")
            print()
            print("📁 Arquivos gerados:")
            for file_type, file_path in self.test_files.items():
                if isinstance(file_path, Path) and file_path.exists():
                    print(f"   {file_type:12} {file_path}")
            print()
            print("💡 Próximos passos:")
            print("   1. Verifique os arquivos gerados em mapas/c1/test/")
            print("   2. Teste carregar o PGM no main.py")
            print("   3. Adicione POIs e áreas proibidas no main.py")
        else:
            print("❌ ALGUNS TESTES FALHARAM")
            print("   Verifique os erros acima e corrija antes de usar no main.py")
        
        print()


def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Testa pipeline completo do C1 Mapping")
    parser.add_argument('--duration', '-d', type=float, default=10.0,
                       help='Duração da coleta de scans em segundos (padrão: 10)')
    parser.add_argument('--skip-collection', action='store_true',
                       help='Pula coleta (usa arquivo existente)')
    parser.add_argument('--scan-file', type=str, default=None,
                       help='Arquivo de scans para usar (se --skip-collection)')
    
    args = parser.parse_args()
    
    tester = PipelineTester()
    
    if args.skip_collection and args.scan_file:
        # Usa arquivo existente
        tester.test_files['scans'] = Path(args.scan_file)
        tester.test_results['detection'] = True
        tester.test_results['collection'] = True
        
        # Testa apenas processamento, exportação e validação
        if tester.test_processing() and tester.test_export() and tester.test_validation():
            tester.print_summary()
        else:
            print("❌ Testes falharam")
    else:
        # Executa todos os testes
        tester.run_all_tests(duration=args.duration)


if __name__ == "__main__":
    main()

