"""Utilidades para inventariar arquivos de mapas."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

INVENTORY_FILES = ("inventario_mapas.json", "inventario_mapas.md")


@dataclass
class InventoryEntry:
    """Representa um arquivo de mapa e seus metadados básicos."""

    name: str
    path: str
    size_bytes: int
    modified_at: str


def _iter_category_items(category_path: Path, base_root: Path) -> Iterable[InventoryEntry]:
    """Percorre uma pasta e retorna as entradas válidas."""

    if not category_path.exists():
        return []

    entries: List[InventoryEntry] = []
    for file_path in sorted(category_path.rglob("*")):
        if not file_path.is_file():
            continue

        stats = file_path.stat()
        entries.append(
            InventoryEntry(
                name=file_path.name,
                path=str(file_path.relative_to(base_root)),
                size_bytes=stats.st_size,
                modified_at=datetime.fromtimestamp(stats.st_mtime).isoformat(),
            )
        )
    return entries


def build_inventory(base_dir: Path) -> Dict[str, List[InventoryEntry]]:
    """Coleta os arquivos das pastas relevantes."""

    categories: List[Tuple[str, Path]] = [
        ("legacy", base_dir / "legacy"),
        ("c1_otimizados", base_dir / "c1" / "otimizados"),
        ("c1_pois", base_dir / "c1" / "pois"),
        ("c1_areas_proibidas", base_dir / "c1" / "areas_proibidas"),
        ("deploy_ready", base_dir / "deploy_ready"),
    ]

    return {key: list(_iter_category_items(path, base_dir)) for key, path in categories}


def write_inventory(report: Dict[str, List[InventoryEntry]], output_dir: Path) -> None:
    """Gera arquivos JSON e Markdown com o inventário."""

    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.utcnow().isoformat()

    json_payload = {
        "generated_at": generated_at,
        "sections": {
            section: [asdict(entry) for entry in entries]
            for section, entries in report.items()
        },
    }

    (output_dir / INVENTORY_FILES[0]).write_text(
        json.dumps(json_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines = [
        "# Inventário de Mapas",
        f"_Gerado em {generated_at}_",
    ]

    for section, entries in report.items():
        lines.append(f"\n## {section}")
        if not entries:
            lines.append("- (vazio)")
            continue

        lines.append("| Arquivo | Tamanho (KB) | Modificado | Caminho |")
        lines.append("| --- | --- | --- | --- |")
        for entry in entries:
            size_kb = entry.size_bytes / 1024
            lines.append(
                f"| {entry.name} | {size_kb:.1f} | {entry.modified_at} | `{entry.path}` |"
            )

    (output_dir / INVENTORY_FILES[1]).write_text("\n".join(lines), encoding="utf-8")


def get_output_subdir(metadata: Dict | None, step_name: str, default: str | None = None) -> str:
    """Obtém o subdiretório de saída para uma etapa do pipeline."""

    if metadata is None:
        return default or step_name

    step_config = metadata.get(step_name, {})
    return step_config.get("output_subdir", default or step_name)


def run_inventory_pipeline(input_path: str, output_dir: str) -> None:
    """Executa a geração completa do inventário."""

    base_dir = Path(input_path)
    if not base_dir.exists():
        raise FileNotFoundError(f"Pasta base '{base_dir}' não encontrada.")

    report = build_inventory(base_dir)
    write_inventory(report, Path(output_dir))
