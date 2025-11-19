"""
Script de teste para validar funcionalidades da interface:
- Carregamento de PGM
- Exportação/importação de POIs
- Exportação/importação de áreas proibidas
"""

import sys
import os
from pathlib import Path
import json
import tempfile
import shutil

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.interfaces.map_widget import MapWidget
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

def test_load_pgm():
    """Testa carregamento de mapa PGM."""
    print("\n=== Teste 1: Carregamento de PGM ===")
    
    app = QApplication([])
    widget = MapWidget()
    
    pgm_path = "mapas/otimizados/sala-maker-1.pgm"
    yaml_path = "mapas/otimizados/sala-maker-1.yaml"
    
    if not Path(pgm_path).exists():
        print(f"❌ Arquivo PGM não encontrado: {pgm_path}")
        return False
    
    print(f"Carregando PGM: {pgm_path}")
    success = widget.load_pgm_map(pgm_path, yaml_path)
    
    if success:
        print(f"✅ PGM carregado com sucesso!")
        print(f"   Resolução: {widget.map_resolution}m/pixel")
        print(f"   Origem: {widget.map_origin}")
        print(f"   Dimensões: {widget.map_width}x{widget.map_height} metros")
        return True
    else:
        print("❌ Falha ao carregar PGM")
        return False

def test_export_import_pois():
    """Testa exportação e importação de POIs."""
    print("\n=== Teste 2: Exportação/Importação de POIs ===")
    
    app = QApplication([])
    widget = MapWidget()
    
    # Adiciona alguns POIs de teste
    widget.points_of_interest = {
        "Mesa 1": (2.5, 3.0, "Mesa"),
        "Mesa 2": (5.0, 4.0, "Mesa"),
        "Base": (0.0, 0.0, "Base")
    }
    
    print(f"POIs criados: {len(widget.points_of_interest)}")
    
    # Testa exportação
    temp_dir = Path(tempfile.mkdtemp())
    export_path = temp_dir / "test_pois.json"
    
    try:
        # Simula exportação (formato esperado)
        pois_data = {
            "map_id": "teste",
            "version": "1.0",
            "pois": []
        }
        
        for name, point_data in widget.points_of_interest.items():
            x, y, point_type = point_data
            pois_data["pois"].append({
                "id": name.lower().replace(" ", "_"),
                "name": name,
                "x": float(x),
                "y": float(y),
                "type": point_type
            })
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(pois_data, f, indent=2)
        
        print(f"✅ POIs exportados: {export_path}")
        
        # Testa importação
        widget.points_of_interest = {}  # Limpa
        
        with open(export_path, 'r', encoding='utf-8') as f:
            imported_data = json.load(f)
        
        imported_count = 0
        for poi in imported_data.get('pois', []):
            name = poi.get('name', poi.get('id', f"poi_{imported_count}"))
            x = float(poi.get('x', 0))
            y = float(poi.get('y', 0))
            point_type = poi.get('type', 'delivery')
            widget.points_of_interest[name] = (x, y, point_type)
            imported_count += 1
        
        print(f"✅ POIs importados: {imported_count}")
        
        # Verifica se foram importados corretamente
        if len(widget.points_of_interest) == 3:
            print("✅ Validação: Todos os POIs foram importados corretamente")
            return True
        else:
            print(f"❌ Validação falhou: Esperado 3, obtido {len(widget.points_of_interest)}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        shutil.rmtree(temp_dir)

def test_export_import_areas():
    """Testa exportação e importação de áreas proibidas."""
    print("\n=== Teste 3: Exportação/Importação de Áreas Proibidas ===")
    
    app = QApplication([])
    widget = MapWidget()
    
    # Adiciona algumas áreas de teste
    widget.forbidden_areas = [
        {
            'id': 1,
            'nome': 'Área 1',
            'coordenadas': [(1.0, 1.0), (2.0, 1.0), (2.0, 2.0), (1.0, 2.0)]
        },
        {
            'id': 2,
            'nome': 'Área 2',
            'coordenadas': [(3.0, 3.0), (4.0, 3.0), (4.0, 4.0), (3.0, 4.0)]
        }
    ]
    
    print(f"Áreas criadas: {len(widget.forbidden_areas)}")
    
    # Testa exportação
    temp_dir = Path(tempfile.mkdtemp())
    export_path = temp_dir / "test_areas.json"
    
    try:
        # Simula exportação (formato esperado)
        areas_data = {
            "map_id": "teste",
            "version": "1.0",
            "forbidden_areas": []
        }
        
        for area in widget.forbidden_areas:
            area_id = area.get('id', 0)
            area_name = area.get('nome', f"Área {area_id}")
            coordinates = area.get('coordenadas', [])
            
            if coordinates and len(coordinates) >= 3:
                areas_data["forbidden_areas"].append({
                    "id": f"area_{area_id}",
                    "name": area_name,
                    "type": "polygon",
                    "points": [{"x": float(x), "y": float(y)} for x, y in coordinates]
                })
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(areas_data, f, indent=2)
        
        print(f"✅ Áreas exportadas: {export_path}")
        
        # Testa importação
        widget.forbidden_areas = []  # Limpa
        
        with open(export_path, 'r', encoding='utf-8') as f:
            imported_data = json.load(f)
        
        imported_count = 0
        for area in imported_data.get('forbidden_areas', []):
            area_name = area.get('name', f"Área {imported_count}")
            points = area.get('points', [])
            
            if points and len(points) >= 3:
                coordinates = [(float(p['x']), float(p['y'])) for p in points]
                area_dict = {
                    'id': len(widget.forbidden_areas),
                    'nome': area_name,
                    'coordenadas': coordinates
                }
                widget.add_forbidden_area(area_dict)
                imported_count += 1
        
        print(f"✅ Áreas importadas: {imported_count}")
        
        # Verifica se foram importadas corretamente
        if len(widget.forbidden_areas) == 2:
            print("✅ Validação: Todas as áreas foram importadas corretamente")
            return True
        else:
            print(f"❌ Validação falhou: Esperado 2, obtido {len(widget.forbidden_areas)}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        shutil.rmtree(temp_dir)

def main():
    """Executa todos os testes."""
    print("=" * 60)
    print("TESTE DE FUNCIONALIDADES DA INTERFACE")
    print("=" * 60)
    
    results = []
    
    # Teste 1: Carregamento de PGM
    results.append(("Carregamento PGM", test_load_pgm()))
    
    # Teste 2: Exportação/Importação de POIs
    results.append(("Exportação/Importação POIs", test_export_import_pois()))
    
    # Teste 3: Exportação/Importação de Áreas
    results.append(("Exportação/Importação Áreas", test_export_import_areas()))
    
    # Resumo
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, r in results if r)
    
    print(f"\nTotal: {passed}/{total} testes passaram")
    
    if passed == total:
        print("✅ Todos os testes passaram!")
        return 0
    else:
        print("❌ Alguns testes falharam")
        return 1

if __name__ == "__main__":
    sys.exit(main())

