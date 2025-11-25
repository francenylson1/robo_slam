"""Abstração para interagir com o SDK oficial do Slamtec C1."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from aurora_mapping.pipelines.workflows import PipelineContext

# Importa o uploader existente
import sys
from pathlib import Path as PathLib

# Adiciona o diretório raiz ao path para importar módulos core
ROOT_DIR = PathLib(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from src.core.slamware_c1_uploader import SlamwareC1Uploader
except ImportError:
    SlamwareC1Uploader = None


def _locate_map2d_outputs(map2d_dir: Path) -> tuple[Optional[Path], Optional[Path]]:
    """Localiza os arquivos PGM e YAML gerados pela etapa map2d."""

    pgm_files = list(map2d_dir.glob("*.pgm"))
    yaml_files = list(map2d_dir.glob("*.yaml"))

    if not pgm_files or not yaml_files:
        return None, None

    # Pega o mais recente
    pgm = max(pgm_files, key=lambda p: p.stat().st_mtime)
    yaml = max(yaml_files, key=lambda p: p.stat().st_mtime)

    return pgm, yaml


def _try_sdk_conversion(
    pgm_path: Path, yaml_path: Path, output_stcm: Path, config: dict
) -> bool:
    """Tenta usar o SDK do C1 para converter PGM/YAML → STCM."""

    sdk_path = config.get("sdk_path")
    if not sdk_path:
        return False

    sdk_bin = Path(sdk_path)
    if not sdk_bin.exists():
        print(f"[c1_conversion] SDK não encontrado em {sdk_path}")
        return False

    try:
        # Tenta executar o SDK (ajustar comando conforme documentação)
        cmd = [
            str(sdk_bin),
            "convert",
            "--pgm",
            str(pgm_path),
            "--yaml",
            str(yaml_path),
            "--output",
            str(output_stcm),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"[c1_conversion] STCM gerado via SDK: {output_stcm}")
            return True
        else:
            print(f"[c1_conversion] SDK retornou erro: {result.stderr}")
            return False
    except Exception as e:
        print(f"[c1_conversion] Erro ao executar SDK: {e}")
        return False


def _try_api_upload(
    pgm_path: Path, yaml_path: Path, config: dict
) -> bool:
    """Tenta fazer upload via API REST do C1."""

    if SlamwareC1Uploader is None:
        return False

    c1_ip = config.get("c1_ip", "192.168.1.101")
    c1_port = config.get("c1_port", 1445)
    map_name = config.get("map_name", "aurora_map")

    try:
        uploader = SlamwareC1Uploader(ip_address=c1_ip, port=c1_port)
        if not uploader.check_connection():
            print(f"[c1_conversion] C1 não acessível em {c1_ip}:{c1_port}")
            return False

        success = uploader.upload_map(
            str(pgm_path), str(yaml_path), map_name=map_name
        )
        if success:
            print(f"[c1_conversion] Mapa enviado para C1 via API: {map_name}")
            return True
        else:
            print("[c1_conversion] Falha no upload via API")
            return False
    except Exception as e:
        print(f"[c1_conversion] Erro na API: {e}")
        return False


def _create_stcm_placeholder(
    pgm_path: Path, yaml_path: Path, output_stcm: Path
) -> bool:
    """Cria um placeholder STCM (será substituído quando SDK estiver disponível)."""

    try:
        # Por enquanto, apenas copia metadados
        # O STCM real precisa ser gerado pelo SDK do C1
        metadata = {
            "source_pgm": str(pgm_path.name),
            "source_yaml": str(yaml_path.name),
            "note": "STCM placeholder - requer SDK do C1 para conversão completa",
        }
        metadata_path = output_stcm.with_suffix(".metadata.json")
        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # Cria arquivo vazio como placeholder
        output_stcm.touch()
        print(
            f"[c1_conversion] Placeholder STCM criado: {output_stcm} (requer SDK do C1)"
        )
        return True
    except Exception as e:
        print(f"[c1_conversion] Erro ao criar placeholder: {e}")
        return False


def run_c1_conversion_step(context: "PipelineContext") -> None:
    """Invoca o SDK do C1 para gerar o .stcm compatível."""

    from aurora_mapping.utils.paths import get_output_subdir

    map2d_dir = Path(context.output_dir) / get_output_subdir(
        context.metadata, "map2d"
    )
    conversion_dir = Path(context.output_dir) / get_output_subdir(
        context.metadata, "c1_conversion"
    )
    conversion_dir.mkdir(parents=True, exist_ok=True)

    pgm_path, yaml_path = _locate_map2d_outputs(map2d_dir)
    if not pgm_path or not yaml_path:
        raise FileNotFoundError(
            f"Nenhum arquivo PGM/YAML encontrado em {map2d_dir}"
        )

    print(f"[c1_conversion] Convertendo {pgm_path.name} + {yaml_path.name} → STCM")

    config = (context.metadata or {}).get("c1_conversion", {})
    map_name = config.get("map_name") or pgm_path.stem
    output_stcm = conversion_dir / f"{map_name}.stcm"

    # Tenta múltiplas abordagens em ordem de prioridade
    success = False

    # 1. Tentar SDK do C1 (se configurado)
    if config.get("use_sdk", False):
        success = _try_sdk_conversion(pgm_path, yaml_path, output_stcm, config)
        if success:
            return

    # 2. Tentar upload via API REST (se C1 estiver acessível)
    if config.get("use_api", True):
        success = _try_api_upload(pgm_path, yaml_path, config)
        if success:
            # Mesmo com upload bem-sucedido, cria placeholder STCM local
            _create_stcm_placeholder(pgm_path, yaml_path, output_stcm)
            return

    # 3. Criar placeholder STCM (para continuar o pipeline)
    if config.get("create_placeholder", True):
        success = _create_stcm_placeholder(pgm_path, yaml_path, output_stcm)
        if success:
            print(
                "[c1_conversion] ⚠️  Placeholder criado. Configure SDK do C1 para conversão completa."
            )
            return

    if not success:
        raise RuntimeError(
            "Falha em todas as abordagens de conversão. "
            "Configure SDK do C1 ou conecte-se ao C1 via API."
        )
