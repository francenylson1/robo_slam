"""Orquestra pipelines (Aurora→C1, C1→C1, etc.)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from aurora_mapping.annotation.poi_editor import run_annotation_step
from aurora_mapping.c1_converter.sdk_bridge import run_c1_conversion_step
from aurora_mapping.capture.aurora_client import run_capture_step
from aurora_mapping.export.packager import run_export_step
from aurora_mapping.map2d.occupancy_builder import run_map2d_step
from aurora_mapping.refinement.pointcloud_filters import run_refinement_step
from aurora_mapping.utils.paths import run_inventory_pipeline


class PipelineType(str, Enum):
    """Enum com os fluxos suportados pela aplicação de mapas."""

    AURORA_TO_C1 = "aurora_to_c1"
    C1_OPTIMIZATION = "c1_optimization"
    INVENTORY_SNAPSHOT = "inventory_snapshot"


@dataclass
class PipelineContext:
    """Container de parâmetros usados durante a execução das pipelines."""

    input_path: str
    output_dir: str
    metadata: Optional[Dict[str, Any]] = None
    steps: Optional[List[str]] = None


def get_pipeline_choices() -> Iterable[str]:
    """Retorna os nomes válidos de pipeline para consumo externo."""

    return [pipeline.value for pipeline in PipelineType]


def run_pipeline(pipeline_name: str, context: PipelineContext) -> None:
    """Executa o fluxo solicitado."""

    try:
        pipeline = PipelineType(pipeline_name)
    except ValueError as exc:
        raise ValueError(
            f"Pipeline '{pipeline_name}' não suportada. "
            f"Opções válidas: {', '.join(get_pipeline_choices())}"
        ) from exc

    if pipeline is PipelineType.AURORA_TO_C1:
        _run_aurora_to_c1(context)
        return

    if pipeline is PipelineType.C1_OPTIMIZATION:
        _run_c1_optimization(context)
        return

    if pipeline is PipelineType.INVENTORY_SNAPSHOT:
        _run_inventory_snapshot(context)
        return

    raise RuntimeError(f"Pipeline {pipeline.value} não implementada.")


def _run_aurora_to_c1(context: PipelineContext) -> None:
    """Executa todas as camadas do fluxo Aurora → C1."""

    steps: Sequence[Tuple[str, Callable[[PipelineContext], None]]] = [
        ("capture", run_capture_step),
        ("refinement", run_refinement_step),
        ("map2d", run_map2d_step),
        ("c1_conversion", run_c1_conversion_step),
        ("annotation", run_annotation_step),
        ("export", run_export_step),
    ]

    _execute_steps("Aurora → C1", steps, context)


def _run_c1_optimization(context: PipelineContext) -> None:
    """Fluxo de melhoria de mapas já gerados no C1."""

    from pathlib import Path
    from aurora_mapping.utils.paths import get_output_subdir
    import shutil
    import json

    input_path = Path(context.input_path)
    opt_dir = Path(context.output_dir) / get_output_subdir(
        context.metadata, "c1_optimization"
    )
    opt_dir.mkdir(parents=True, exist_ok=True)

    config = (context.metadata or {}).get("c1_optimization", {})

    # Se entrada é STCM do C1, precisa exportar para PGM/YAML primeiro
    if input_path.suffix.lower() == ".stcm":
        print(f"[C1 Optimization] Arquivo STCM detectado: {input_path.name}")
        print(
            "[C1 Optimization] ⚠️  Exporte o STCM para PGM/YAML primeiro usando o SDK do C1"
        )
        print(
            "[C1 Optimization]    Ou forneça diretamente arquivos PGM/YAML como entrada"
        )
        # Copia STCM para pasta de otimização
        dest_stcm = opt_dir / input_path.name
        if not dest_stcm.exists():
            shutil.copy2(input_path, dest_stcm)
        return

    # Se entrada é PGM/YAML, processa diretamente
    if input_path.suffix.lower() in [".pgm", ".yaml"]:
        # Assume que há par correspondente
        base_name = input_path.stem
        if input_path.suffix == ".pgm":
            yaml_path = input_path.with_suffix(".yaml")
        else:
            yaml_path = input_path
            pgm_path = input_path.with_suffix(".pgm")

        if not yaml_path.exists() or not input_path.with_suffix(".pgm").exists():
            raise FileNotFoundError(
                f"Arquivos PGM/YAML correspondentes não encontrados para {input_path}"
            )

        # Copia arquivos para pasta de otimização
        opt_pgm = opt_dir / f"{base_name}_optimized.pgm"
        opt_yaml = opt_dir / f"{base_name}_optimized.yaml"

        if config.get("apply_filters", True):
            # Aqui poderia aplicar filtros de imagem (morphology, etc.)
            # Por enquanto, apenas copia
            print(f"[C1 Optimization] Copiando mapa para otimização...")
            shutil.copy2(input_path.with_suffix(".pgm"), opt_pgm)
            shutil.copy2(yaml_path, opt_yaml)
            print(f"[C1 Optimization] Mapa copiado: {opt_pgm.name}")

        # Reprocessa POIs se necessário
        if config.get("reprocess_pois", True):
            pois_template = {
                "map_id": base_name,
                "pois": [],
                "forbidden_areas": [],
                "metadata": {
                    "optimized": True,
                    "source": str(input_path.name),
                },
            }
            pois_path = opt_dir / f"{base_name}_pois.json"
            with pois_path.open("w", encoding="utf-8") as f:
                json.dump(pois_template, f, indent=2)
            print(f"[C1 Optimization] Template de POIs criado: {pois_path.name}")

        print(f"[C1 Optimization] ✅ Mapa otimizado salvo em: {opt_dir}")
        return

    # Se entrada é diretório, processa todos os mapas
    if input_path.is_dir():
        pgm_files = list(input_path.glob("*.pgm"))
        if not pgm_files:
            raise FileNotFoundError(
                f"Nenhum arquivo PGM encontrado em {input_path}"
            )

        for pgm_file in pgm_files:
            yaml_file = pgm_file.with_suffix(".yaml")
            if yaml_file.exists():
                # Processa cada mapa
                temp_context = PipelineContext(
                    input_path=str(pgm_file),
                    output_dir=str(opt_dir),
                    metadata=context.metadata,
                    steps=context.steps,
                )
                _run_c1_optimization(temp_context)

        print(f"[C1 Optimization] ✅ {len(pgm_files)} mapa(s) processado(s)")
        return

    raise ValueError(
        f"Formato de entrada não suportado: {input_path}. "
        "Use arquivo .stcm, .pgm/.yaml ou diretório com mapas."
    )


def _run_inventory_snapshot(context: PipelineContext) -> None:
    """Executa o inventário de arquivos de mapas."""

    run_inventory_pipeline(context.input_path, context.output_dir)


def _execute_steps(
    pipeline_label: str,
    steps: Sequence[Tuple[str, Callable[[PipelineContext], None]]],
    context: PipelineContext,
) -> None:
    """Percorre a lista de etapas e executa conforme filtros do usuário."""

    selected_steps = {step.lower() for step in context.steps} if context.steps else None

    for step_name, handler in steps:
        if selected_steps is not None and step_name.lower() not in selected_steps:
            continue

        print(f"[{pipeline_label}] Executando etapa '{step_name}'...")
        handler(context)
