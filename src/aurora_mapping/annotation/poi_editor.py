"""Ferramentas para edição/anotação de POIs e áreas especiais."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from aurora_mapping.pipelines.workflows import PipelineContext

from aurora_mapping.utils.paths import get_output_subdir


def _load_existing_pois(pois_path: Path) -> Dict[str, Any]:
    """Carrega POIs existentes ou retorna estrutura vazia."""

    if not pois_path.exists():
        return {"map_id": "", "pois": [], "forbidden_areas": []}

    try:
        with pois_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"map_id": "", "pois": [], "forbidden_areas": []}


def _locate_map2d_files(map2d_dir: Path) -> tuple[Optional[Path], Optional[Path]]:
    """Localiza arquivos PGM e YAML da etapa map2d."""

    pgm_files = list(map2d_dir.glob("*.pgm"))
    yaml_files = list(map2d_dir.glob("*.yaml"))

    if not pgm_files or not yaml_files:
        return None, None

    pgm = max(pgm_files, key=lambda p: p.stat().st_mtime)
    yaml = max(yaml_files, key=lambda p: p.stat().st_mtime)
    return pgm, yaml


def _create_default_pois_template(map_name: str) -> Dict[str, Any]:
    """Cria template básico de POIs."""

    return {
        "map_id": map_name,
        "pois": [
            {
                "id": "home",
                "name": "Ponto Inicial",
                "x": 0.0,
                "y": 0.0,
                "orientation": 0.0,
                "type": "home",
                "description": "Posição inicial do robô",
            }
        ],
        "forbidden_areas": [],
        "metadata": {
            "created_by": "Aurora Mapping Studio",
            "version": "1.0",
        },
    }


def run_annotation_step(context: "PipelineContext") -> None:
    """Cria/atualiza arquivo de POIs baseado no mapa 2D gerado."""

    map2d_dir = Path(context.output_dir) / get_output_subdir(
        context.metadata, "map2d"
    )
    annotation_dir = Path(context.output_dir) / get_output_subdir(
        context.metadata, "annotation"
    )
    annotation_dir.mkdir(parents=True, exist_ok=True)

    pgm_path, yaml_path = _locate_map2d_files(map2d_dir)
    if not pgm_path or not yaml_path:
        raise FileNotFoundError(
            f"Nenhum arquivo PGM/YAML encontrado em {map2d_dir} para anotação"
        )

    # Copia arquivos do mapa para a pasta de anotação
    annotation_pgm = annotation_dir / pgm_path.name
    annotation_yaml = annotation_dir / yaml_path.name
    if not annotation_pgm.exists():
        shutil.copy2(pgm_path, annotation_pgm)
    if not annotation_yaml.exists():
        shutil.copy2(yaml_path, annotation_yaml)

    # Determina nome do mapa
    map_name = pgm_path.stem
    pois_path = annotation_dir / f"{map_name}_pois.json"

    # Carrega POIs existentes ou cria template
    config = (context.metadata or {}).get("annotation", {})
    if pois_path.exists() and not config.get("overwrite", False):
        pois_data = _load_existing_pois(pois_path)
        print(f"[annotation] POIs existentes carregados de {pois_path.name}")
    else:
        pois_data = _create_default_pois_template(map_name)
        print(f"[annotation] Template de POIs criado para {map_name}")

    # Atualiza map_id se necessário
    pois_data["map_id"] = map_name

    # Salva arquivo de POIs
    with pois_path.open("w", encoding="utf-8") as f:
        json.dump(pois_data, f, indent=2, ensure_ascii=False)

    print(f"[annotation] Arquivo de POIs salvo: {pois_path}")
    print(
        f"[annotation] ⚠️  Edite manualmente {pois_path} para adicionar mesas, destinos e áreas proibidas"
    )
    print(f"[annotation]    Ou use interface gráfica futura para edição interativa")
