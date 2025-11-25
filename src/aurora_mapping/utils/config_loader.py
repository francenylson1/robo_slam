"""Carrega o arquivo central de configuração do Aurora Mapping Studio."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "mapping.json"


def load_base_config(config_path: Path | None = None) -> Dict[str, Any]:
    """Lê o arquivo JSON padrão de configuração."""

    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as handler:
        return json.load(handler)


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Mescla dicionários recursivamente."""

    result = deepcopy(base)
    for key, value in override.items():
        if (
            isinstance(value, dict)
            and isinstance(result.get(key), dict)
        ):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def load_mapping_config(overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Retorna a configuração final já com sobrescrições aplicadas."""

    base = load_base_config()
    if not overrides:
        return base

    return merge_configs(base, overrides)
