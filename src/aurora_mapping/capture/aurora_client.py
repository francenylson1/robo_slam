"""Funções de conexão e captura do sensor Aurora."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from aurora_mapping.pipelines.workflows import PipelineContext

DEFAULT_EXTENSIONS: Sequence[str] = (".stcm", ".ply", ".pcd", ".bmp", ".bin")
MANIFEST_NAME = "capture_manifest.json"


def run_capture_step(context: "PipelineContext") -> None:
    """Simula a etapa de captura copiando os arquivos brutos do Aurora."""

    input_path = Path(context.input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Entrada não encontrada: {input_path}")

    capture_config = (context.metadata or {}).get("capture", {})
    extensions = _normalize_extensions(capture_config.get("extensions"))
    overwrite = bool(capture_config.get("overwrite", False))
    output_subdir = capture_config.get("output_subdir", "capture")

    capture_dir = Path(context.output_dir) / output_subdir
    capture_dir.mkdir(parents=True, exist_ok=True)

    candidates = list(_collect_files(input_path, extensions))
    if not candidates:
        raise FileNotFoundError(
            f"Nenhum arquivo com extensões {extensions} encontrado em {input_path}"
        )

    manifest = []
    for file_path in candidates:
        destination = capture_dir / file_path.name
        if destination.exists() and not overwrite:
            print(f"[capture] Pulando {destination} (arquivo já existe).")
            continue

        shutil.copy2(file_path, destination)
        manifest.append(
            {
                "source": str(file_path),
                "destination": str(destination),
                "copied_at": datetime.utcnow().isoformat(),
                "size_bytes": file_path.stat().st_size,
            }
        )
        print(f"[capture] Copiado {file_path} → {destination}")

    if not manifest:
        print("[capture] Nenhum arquivo novo copiado; reutilizando arquivos existentes.")
        manifest = _summarize_existing_files(capture_dir, extensions)

    manifest_path = capture_dir / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[capture] Manifesto salvo em {manifest_path}")


def _normalize_extensions(extensions_config: Iterable[str] | None) -> List[str]:
    extensions = list(extensions_config or DEFAULT_EXTENSIONS)
    normalized = []
    for ext in extensions:
        normalized.append(ext if ext.startswith(".") else f".{ext}")
    return normalized


def _collect_files(input_path: Path, extensions: Iterable[str]) -> Iterable[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() in extensions:
            yield input_path
        return

    for ext in extensions:
        yield from input_path.rglob(f"*{ext}")


def _summarize_existing_files(base_dir: Path, extensions: Iterable[str]) -> List[dict]:
    manifest = []
    for ext in extensions:
        for file_path in base_dir.glob(f"*{ext}"):
            manifest.append(
                {
                    "source": str(file_path),
                    "destination": str(file_path),
                    "copied_at": None,
                    "size_bytes": file_path.stat().st_size,
                }
            )
    if not manifest:
        raise RuntimeError(
            "Nenhum arquivo existente encontrado no diretório de captura. "
            "Considere habilitar overwrite ou verificar as extensões configuradas."
        )
    return manifest
