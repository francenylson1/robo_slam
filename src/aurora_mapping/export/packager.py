"""Empacotamento final dos artefatos entregues ao robô."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from aurora_mapping.pipelines.workflows import PipelineContext

from aurora_mapping.utils.paths import get_output_subdir


def _locate_c1_stcm(conversion_dir: Path) -> Optional[Path]:
    """Localiza arquivo STCM gerado pela etapa c1_conversion."""

    stcm_files = list(conversion_dir.glob("*.stcm"))
    if not stcm_files:
        return None
    return max(stcm_files, key=lambda p: p.stat().st_mtime)


def _locate_pois(annotation_dir: Path) -> Optional[Path]:
    """Localiza arquivo de POIs gerado pela etapa annotation."""

    pois_files = list(annotation_dir.glob("*_pois.json"))
    if not pois_files:
        return None
    return max(pois_files, key=lambda p: p.stat().st_mtime)


def _locate_map_preview(map2d_dir: Path) -> Optional[Path]:
    """Localiza preview do mapa 2D."""

    preview_files = list(map2d_dir.glob("*_preview.png"))
    if not preview_files:
        # Tenta PGM como fallback
        pgm_files = list(map2d_dir.glob("*.pgm"))
        if pgm_files:
            return max(pgm_files, key=lambda p: p.stat().st_mtime)
        return None
    return max(preview_files, key=lambda p: p.stat().st_mtime)


def _create_metadata(
    stcm_path: Optional[Path],
    pois_path: Optional[Path],
    preview_path: Optional[Path],
    map_name: str,
) -> Dict[str, Any]:
    """Cria arquivo de metadados do pacote."""

    return {
        "package_version": "1.0",
        "created_at": datetime.now().isoformat(),
        "map_name": map_name,
        "files": {
            "stcm": stcm_path.name if stcm_path else None,
            "pois": pois_path.name if pois_path else None,
            "preview": preview_path.name if preview_path else None,
        },
        "notes": "Pacote gerado pelo Aurora Mapping Studio",
    }


def run_export_step(context: "PipelineContext") -> None:
    """Empacota todos os artefatos finais para deploy no robô."""

    conversion_dir = Path(context.output_dir) / get_output_subdir(
        context.metadata, "c1_conversion"
    )
    annotation_dir = Path(context.output_dir) / get_output_subdir(
        context.metadata, "annotation"
    )
    map2d_dir = Path(context.output_dir) / get_output_subdir(
        context.metadata, "map2d"
    )
    export_dir = Path(context.output_dir) / get_output_subdir(
        context.metadata, "export"
    )
    export_dir.mkdir(parents=True, exist_ok=True)

    # Localiza arquivos gerados nas etapas anteriores
    stcm_path = _locate_c1_stcm(conversion_dir)
    pois_path = _locate_pois(annotation_dir)
    preview_path = _locate_map_preview(map2d_dir)

    # Determina nome do mapa
    config = (context.metadata or {}).get("export", {})
    map_name = config.get("map_name")
    if not map_name:
        if stcm_path:
            map_name = stcm_path.stem
        elif pois_path:
            map_name = pois_path.stem.replace("_pois", "")
        else:
            map_name = "aurora_map"

    # Cria subdiretório para este pacote
    package_dir = export_dir / f"{map_name}_package"
    package_dir.mkdir(exist_ok=True)

    # Copia arquivos para o pacote
    copied_files = []
    if stcm_path and stcm_path.exists():
        dest = package_dir / stcm_path.name
        shutil.copy2(stcm_path, dest)
        copied_files.append(("STCM", dest.name))
        print(f"[export] Copiado STCM: {dest.name}")

    if pois_path and pois_path.exists():
        dest = package_dir / pois_path.name
        shutil.copy2(pois_path, dest)
        copied_files.append(("POIs", dest.name))
        print(f"[export] Copiado POIs: {dest.name}")

    if preview_path and preview_path.exists():
        dest = package_dir / f"{map_name}_layout.png"
        shutil.copy2(preview_path, dest)
        copied_files.append(("Preview", dest.name))
        print(f"[export] Copiado preview: {dest.name}")

    # Cria metadados do pacote
    metadata = _create_metadata(stcm_path, pois_path, preview_path, map_name)
    metadata_path = package_dir / "metadata.json"
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"[export] Metadados salvos: {metadata_path.name}")

    # Cria README do pacote
    readme_path = package_dir / "README.md"
    with readme_path.open("w", encoding="utf-8") as f:
        f.write(f"# Pacote de Mapa: {map_name}\n\n")
        f.write(f"Gerado em: {metadata['created_at']}\n\n")
        f.write("## Arquivos incluídos:\n\n")
        for file_type, file_name in copied_files:
            f.write(f"- **{file_type}**: `{file_name}`\n")
        f.write("\n## Instruções:\n\n")
        f.write("1. Copie o arquivo `.stcm` para o C1\n")
        f.write("2. Carregue o arquivo `*_pois.json` no sistema de navegação\n")
        f.write("3. Use `*_layout.png` como referência visual\n")
    print(f"[export] README criado: {readme_path.name}")

    print(f"\n[export] ✅ Pacote final criado em: {package_dir}")
    print(f"[export]    Arquivos prontos para deploy no robô C1")
