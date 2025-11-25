"""Entry point do Aurora Mapping Studio."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Garante que o diretório raiz esteja no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from aurora_mapping.pipelines.workflows import PipelineContext, get_pipeline_choices, run_pipeline
from aurora_mapping.utils.config_loader import load_mapping_config


def _load_metadata(metadata_path: Optional[str]) -> Optional[Dict[str, Any]]:
    """Carrega metadados opcionais a partir de um arquivo JSON."""

    if not metadata_path:
        return None

    metadata_file = Path(metadata_path)
    if not metadata_file.exists():
        raise FileNotFoundError(f"Arquivo de metadados não encontrado: {metadata_file}")

    with metadata_file.open("r", encoding="utf-8") as handler:
        return json.load(handler)


def parse_args() -> argparse.Namespace:
    """Define e interpreta os argumentos da CLI."""

    parser = argparse.ArgumentParser(
        description="🗺️  Aurora Mapping Studio - Gerenciamento completo de mapas Aurora → C1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
📚 Exemplos de uso:

  # Abrir interface gráfica
  %(prog)s --gui
  # ou simplesmente:
  %(prog)s

  # Inventário de mapas (CLI)
  %(prog)s --pipeline inventory_snapshot --input mapas --output docs/mapping

  # Pipeline completo Aurora → C1 (CLI)
  %(prog)s --pipeline aurora_to_c1 \\
    --input mapas/legacy/originais_aurora \\
    --output data/pipeline_runs/meu_mapa \\
    --steps capture,refinement,map2d,annotation,export

  # Apenas etapas específicas (CLI)
  %(prog)s --pipeline aurora_to_c1 \\
    --input mapas/legacy/originais_aurora \\
    --output data/pipeline_runs/teste \\
    --steps capture,refinement

  # Com arquivo de configuração customizado (CLI)
  %(prog)s --pipeline aurora_to_c1 \\
    --input mapas/legacy/originais_aurora \\
    --output data/pipeline_runs/meu_mapa \\
    --metadata config/custom.json

  # Otimizar mapa do C1 (CLI)
  %(prog)s --pipeline c1_optimization \\
    --input mapas/c1/otimizados/sala-maker-1.pgm \\
    --output data/pipeline_runs/otimizado

📖 Para mais informações, consulte: docs/mapping/GUIA_USO_INICIAL.md
        """,
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Abre a interface gráfica (padrão se nenhum argumento for fornecido)",
    )
    parser.add_argument(
        "--pipeline",
        choices=list(get_pipeline_choices()),
        metavar="PIPELINE",
        help=f"Fluxo a ser executado. Opções: {', '.join(get_pipeline_choices())}",
    )
    parser.add_argument(
        "--input",
        metavar="CAMINHO",
        help="Arquivo ou diretório de entrada (ex.: mapas/legacy/originais_aurora)",
    )
    parser.add_argument(
        "--output",
        metavar="DIRETORIO",
        help="Diretório onde os resultados serão salvos (ex.: data/pipeline_runs/meu_mapa)",
    )
    parser.add_argument(
        "--metadata",
        metavar="ARQUIVO_JSON",
        help="Arquivo JSON opcional com configurações customizadas (ex.: config/custom.json)",
    )
    parser.add_argument(
        "--steps",
        metavar="ETAPAS",
        help="Lista de etapas específicas separadas por vírgula (ex.: capture,refinement,map2d). "
             "Se omitido, executa todas as etapas do pipeline.",
    )

    return parser.parse_args()


def main() -> None:
    """Função principal do módulo de mapas."""

    # Se não há argumentos, abre GUI
    if len(sys.argv) == 1:
        try:
            from src.interfaces.mapping_studio_window import run_gui
            run_gui()
            return
        except ImportError as e:
            print("🗺️  Aurora Mapping Studio")
            print("=" * 50)
            print("\n⚠️  Interface gráfica não disponível (PyQt5 não encontrado).\n")
            print("💡 Use a linha de comando:")
            print("   python src/main_mapping.py --help\n")
            print("📚 Exemplo mais simples (inventário):")
            print("   python src/main_mapping.py \\")
            print("     --pipeline inventory_snapshot \\")
            print("     --input mapas \\")
            print("     --output docs/mapping\n")
            print("📖 Guia completo: docs/mapping/GUIA_USO_INICIAL.md\n")
            sys.exit(1)

    args = parse_args()
    
    # Se --gui foi especificado ou nenhum argumento CLI foi fornecido, abre interface gráfica
    if args.gui or not args.pipeline:
        try:
            from src.interfaces.mapping_studio_window import run_gui
            run_gui()
            return
        except ImportError:
            print("❌ Erro: PyQt5 não está instalado. Use a linha de comando.")
            print("   Instale com: pip install PyQt5")
            sys.exit(1)

    # Modo CLI - valida argumentos obrigatórios
    if not args.input or not args.output:
        print("❌ Erro: Argumentos --input e --output são obrigatórios no modo CLI.")
        print("   Use --help para ver exemplos de uso.")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    overrides = _load_metadata(args.metadata)
    config = load_mapping_config(overrides)
    steps = [step.strip() for step in args.steps.split(",")] if args.steps else None

    context = PipelineContext(
        input_path=args.input,
        output_dir=str(output_dir),
        metadata=config,
        steps=steps,
    )

    run_pipeline(args.pipeline, context)


if __name__ == "__main__":
    main()
