"""Conversão da nuvem limpa em mapas 2D navegáveis."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Optional, Sequence, TYPE_CHECKING, Tuple

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation

import open3d as o3d

if TYPE_CHECKING:
    from aurora_mapping.pipelines.workflows import PipelineContext


def run_map2d_step(context: "PipelineContext") -> None:
    """Gera o mapa 2D a partir da nuvem refinada."""

    metadata = context.metadata or {}
    refine_cfg = metadata.get("refinement", {})
    map_cfg = metadata.get("map2d", {})

    refinement_dir = Path(context.output_dir) / refine_cfg.get("output_subdir", "refinement")
    output_dir = Path(context.output_dir) / map_cfg.get("output_subdir", "map2d")
    output_dir.mkdir(parents=True, exist_ok=True)

    source_cloud = _locate_clean_cloud(refinement_dir)
    print(f"[map2d] Convertendo nuvem {source_cloud}")
    cloud = o3d.io.read_point_cloud(str(source_cloud))
    points = np.asarray(cloud.points)
    if points.size == 0:
        raise ValueError("Nuvem refinada vazia; não é possível gerar mapa 2D.")

    # Validação inicial da nuvem
    if np.any(np.isnan(points)) or np.any(np.isinf(points)):
        print("[map2d] ⚠️  Aviso: Nuvem contém valores NaN ou Inf. Removendo...")
        valid_mask = ~(np.isnan(points).any(axis=1) | np.isinf(points).any(axis=1))
        points = points[valid_mask]
        if points.size == 0:
            raise ValueError("Nuvem ficou vazia após remover valores inválidos (NaN/Inf).")

    # Diagnóstico: mostra distribuição dos pontos antes do filtro
    z_values = points[:, 2]
    z_min_actual = float(z_values.min())
    z_max_actual = float(z_values.max())
    z_median = float(np.median(z_values))
    print(f"[map2d] Diagnóstico da nuvem:")
    print(f"[map2d]   Total de pontos: {len(points):,}")
    print(f"[map2d]   Altura (Z) - Min: {z_min_actual:.3f}m, Max: {z_max_actual:.3f}m, Mediana: {z_median:.3f}m")
    print(f"[map2d]   Range X: {points[:, 0].max() - points[:, 0].min():.3f}m")
    print(f"[map2d]   Range Y: {points[:, 1].max() - points[:, 1].min():.3f}m")
    
    z_min = float(map_cfg.get("height_min", -0.2))
    z_max = float(map_cfg.get("height_max", 2.0))
    print(f"[map2d] Filtro de altura: Z entre {z_min:.3f}m e {z_max:.3f}m")
    
    mask = (points[:, 2] >= z_min) & (points[:, 2] <= z_max)
    filtered = points[mask]
    
    if filtered.size == 0:
        raise ValueError(
            f"Nenhum ponto ficou dentro do intervalo de altura configurado ({z_min:.3f}m a {z_max:.3f}m).\n"
            f"Altura dos pontos: Min={z_min_actual:.3f}m, Max={z_max_actual:.3f}m, Mediana={z_median:.3f}m.\n"
            f"Ajuste 'height_min' e 'height_max' em config/mapping.json para incluir os pontos."
        )
    
    print(f"[map2d] Pontos após filtro de altura: {len(filtered):,} ({len(filtered)/len(points)*100:.1f}%)")
    
    # Validação: verifica se há pontos suficientes e se não são todos iguais
    if len(filtered) < 3:
        raise ValueError(
            f"Nuvem tem apenas {len(filtered)} pontos após filtro de altura. "
            "Necessário pelo menos 3 pontos para gerar mapa 2D."
        )
    
    # Verifica se pontos não são todos colineares (mesma coordenada X ou Y)
    points_xy = filtered[:, :2]
    x_range = points_xy[:, 0].max() - points_xy[:, 0].min()
    y_range = points_xy[:, 1].max() - points_xy[:, 1].min()
    
    print(f"[map2d] Range após filtro: X={x_range:.6f}m, Y={y_range:.6f}m")
    
    if x_range < 1e-6 or y_range < 1e-6:
        # Diagnóstico detalhado
        x_values = points_xy[:, 0]
        y_values = points_xy[:, 1]
        x_unique = len(np.unique(x_values))
        y_unique = len(np.unique(y_values))
        
        error_msg = (
            f"Pontos são colineares após filtro de altura:\n"
            f"  X range: {x_range:.6f}m (valores únicos: {x_unique})\n"
            f"  Y range: {y_range:.6f}m (valores únicos: {y_unique})\n"
            f"  Total de pontos: {len(filtered):,}\n"
            f"  Altura (Z) dos pontos filtrados: Min={filtered[:, 2].min():.3f}m, Max={filtered[:, 2].max():.3f}m\n"
        )
        
        # Sugestões de correção
        suggestions = []
        if y_range < 1e-6:
            suggestions.append(
                f"  ⚠️  PROBLEMA: Todos os pontos têm a mesma coordenada Y!\n"
                f"     Isso pode indicar:\n"
                f"     1. Problema na conversão .stcm → .ply (pontos em um plano)\n"
                f"     2. Filtro de altura muito restritivo (todos os pontos em uma linha)\n"
                f"     3. Nuvem de pontos corrompida ou incompleta\n"
            )
            # Tenta ajustar automaticamente o filtro de altura
            if z_min_actual < z_max_actual:
                suggested_z_min = max(z_min_actual - 0.5, z_min)
                suggested_z_max = min(z_max_actual + 0.5, z_max)
                suggestions.append(
                    f"  💡 SUGESTÃO: Tente ajustar o filtro de altura:\n"
                    f"     height_min: {suggested_z_min:.3f}m (atual: {z_min:.3f}m)\n"
                    f"     height_max: {suggested_z_max:.3f}m (atual: {z_max:.3f}m)\n"
                )
        
        if x_range < 1e-6:
            suggestions.append(
                f"  ⚠️  PROBLEMA: Todos os pontos têm a mesma coordenada X!\n"
            )
        
        suggestions.append(
            f"  💡 AÇÃO: Verifique a nuvem de pontos original:\n"
            f"     1. Abra o arquivo .ply no passo de refinement\n"
            f"     2. Verifique se os pontos estão distribuídos em 3D\n"
            f"     3. Se necessário, reexecute o passo de refinement\n"
        )
        
        raise ValueError(error_msg + "\n" + "".join(suggestions))

    # Filtro de outliers: remove pontos muito distantes do centro (evita mapas quadrados desnecessários)
    filter_outliers = map_cfg.get("filter_outliers", True)
    outlier_percentile = float(map_cfg.get("outlier_percentile", 99.0))  # Remove 1% mais extremo
    
    if filter_outliers and len(points_xy) > 100:  # Só filtra se houver pontos suficientes
        print(f"[map2d] Aplicando filtro de outliers (percentil {outlier_percentile}%)...")
        points_before = len(points_xy)
        
        # Calcula centro (mediana é mais robusta que média)
        center_x = np.median(points_xy[:, 0])
        center_y = np.median(points_xy[:, 1])
        
        # Calcula distâncias ao centro
        distances = np.sqrt((points_xy[:, 0] - center_x)**2 + (points_xy[:, 1] - center_y)**2)
        
        # Remove pontos além do percentil especificado
        threshold = np.percentile(distances, outlier_percentile)
        outlier_mask = distances <= threshold
        points_xy = points_xy[outlier_mask]
        
        # Atualiza filtered para refletir a remoção de outliers
        filtered = filtered[outlier_mask]
        
        points_removed = points_before - len(points_xy)
        if points_removed > 0:
            print(f"[map2d] Removidos {points_removed} pontos outliers ({points_removed/points_before:.1%})")
            print(f"[map2d] Centro: ({center_x:.2f}, {center_y:.2f})m, Threshold: {threshold:.2f}m")
            
            # Recalcula ranges após filtro
            x_range = points_xy[:, 0].max() - points_xy[:, 0].min()
            y_range = points_xy[:, 1].max() - points_xy[:, 1].min()
            print(f"[map2d] Range após filtro: X={x_range:.2f}m, Y={y_range:.2f}m")

    resolution = float(map_cfg.get("resolution_m", 0.05))
    if resolution <= 0 or np.isnan(resolution) or np.isinf(resolution):
        raise ValueError(f"Resolução inválida: {resolution}. Deve ser um número positivo.")
    
    padding = float(map_cfg.get("padding_m", 0.5))
    occupied_value = int(map_cfg.get("occupied_value", 0))
    free_value = int(map_cfg.get("free_value", 254))
    unknown_value = int(map_cfg.get("unknown_value", 205))

    grid, origin, actual_resolution = _points_to_grid(
        points_xy, resolution, padding, occupied_value, unknown_value
    )
    
    # Usa a resolução ajustada (pode ter sido modificada se grid era muito grande)
    if actual_resolution != resolution:
        print(f"[map2d] Resolução final usada: {actual_resolution:.4f}m (original: {resolution:.4f}m)")

    dilation_pixels = int(map_cfg.get("dilation_pixels", 0))
    if dilation_pixels > 0:
        structure = _disk_kernel(dilation_pixels)
        dilated = binary_dilation(grid == occupied_value, structure=structure)
        grid = np.where(dilated, occupied_value, grid)
        print(f"[map2d] Dilatação aplicada com raio {dilation_pixels} px")

    pgm_path = output_dir / f"{source_cloud.stem}.pgm"
    yaml_path = output_dir / f"{source_cloud.stem}.yaml"

    Image.fromarray(grid.astype(np.uint8), mode="L").save(pgm_path)
    print(f"[map2d] Grid salvo em {pgm_path}")

    yaml_content = _build_yaml(
        pgm_path.name,
        actual_resolution,  # Usa resolução ajustada
        origin,
        occupied_thresh=float(map_cfg.get("occupied_thresh", 0.65)),
        free_thresh=float(map_cfg.get("free_thresh", 0.15)),
    )
    yaml_path.write_text(yaml_content, encoding="utf-8")
    print(f"[map2d] YAML salvo em {yaml_path}")


def _locate_clean_cloud(refinement_dir: Path) -> Path:
    if not refinement_dir.exists():
        raise FileNotFoundError(f"Pasta de refinamento não encontrada: {refinement_dir}")

    candidates = sorted(refinement_dir.glob("*_clean.ply"))
    if not candidates:
        raise FileNotFoundError(
            f"Nenhuma nuvem limpa (*_clean.ply) encontrada em {refinement_dir}. "
            "Garanta que o passo de refinamento foi executado."
        )
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _points_to_grid(
    points_xy: np.ndarray,
    resolution: float,
    padding: float,
    occupied_value: int,
    unknown_value: int,
) -> Tuple[np.ndarray, Tuple[float, float, float], float]:
    # Validação de entrada
    if points_xy.size == 0:
        raise ValueError("Nenhum ponto fornecido para gerar grid.")
    
    if resolution <= 0 or np.isnan(resolution) or np.isinf(resolution):
        raise ValueError(f"Resolução inválida: {resolution}")
    
    # Remove valores inválidos
    valid_mask = ~(np.isnan(points_xy).any(axis=1) | np.isinf(points_xy).any(axis=1))
    if not valid_mask.all():
        print(f"[map2d] ⚠️  Removendo {np.sum(~valid_mask)} pontos inválidos (NaN/Inf)")
        points_xy = points_xy[valid_mask]
        if points_xy.size == 0:
            raise ValueError("Nenhum ponto válido após remover NaN/Inf.")
    
    min_xy = points_xy.min(axis=0) - padding
    max_xy = points_xy.max(axis=0) + padding
    size = max_xy - min_xy
    
    # Validação: verifica se size é válido
    if np.any(np.isnan(size)) or np.any(np.isinf(size)):
        raise ValueError(
            f"Tamanho do grid inválido (NaN/Inf): {size}. "
            "Verifique se os pontos têm coordenadas válidas."
        )
    
    if np.any(size <= 0):
        raise ValueError(
            f"Tamanho do grid inválido (<= 0): {size}. "
            "Pontos podem ser colineares ou ter coordenadas inválidas."
        )

    # Calcula dimensões do grid (verifica NaN antes de converter para int)
    width_float = size[0] / resolution
    height_float = size[1] / resolution
    
    if np.isnan(width_float) or np.isnan(height_float) or np.isinf(width_float) or np.isinf(height_float):
        raise ValueError(
            f"Cálculo de dimensões resultou em valores inválidos: "
            f"width={width_float}, height={height_float}. "
            f"Size: {size}, Resolution: {resolution}"
        )
    
    # Validação de tamanho máximo do grid
    # NumPy tem limites práticos: grids muito grandes são impraticáveis
    MAX_GRID_DIMENSION = 50000  # Máximo de 50.000 pixels por dimensão
    MAX_TOTAL_PIXELS = 2_000_000_000  # Máximo de 2 bilhões de pixels total
    
    # Calcula dimensões iniciais
    width = max(1, int(math.ceil(width_float)))
    height = max(1, int(math.ceil(height_float)))
    total_pixels = width * height
    
    # Ajusta resolução se grid for muito grande
    original_resolution = resolution
    
    # Verifica dimensão individual primeiro
    if width > MAX_GRID_DIMENSION or height > MAX_GRID_DIMENSION:
        max_dimension = max(width, height)
        scale_factor = max_dimension / MAX_GRID_DIMENSION
        resolution = resolution * scale_factor
        
        print(
            f"[map2d] ⚠️  ATENÇÃO: Grid muito grande ({width}x{height} pixels, {total_pixels:,} total). "
            f"Ajustando resolução de {original_resolution:.4f}m para {resolution:.4f}m."
        )
        
        # Recalcula com resolução ajustada
        width_float = size[0] / resolution
        height_float = size[1] / resolution
        width = max(1, int(math.ceil(width_float)))
        height = max(1, int(math.ceil(height_float)))
        total_pixels = width * height
        
        print(f"[map2d] Grid ajustado: {width}x{height} pixels ({total_pixels:,} total, resolução: {resolution:.4f}m)")
    
    # Verifica total de pixels (após ajuste de dimensão)
    if total_pixels > MAX_TOTAL_PIXELS:
        scale_factor = math.sqrt(total_pixels / MAX_TOTAL_PIXELS)
        resolution = resolution * scale_factor
        
        print(
            f"[map2d] ⚠️  ATENÇÃO: Grid ainda tem muitos pixels ({total_pixels:,}). "
            f"Ajustando resolução para {resolution:.4f}m."
        )
        
        width_float = size[0] / resolution
        height_float = size[1] / resolution
        width = max(1, int(math.ceil(width_float)))
        height = max(1, int(math.ceil(height_float)))
        total_pixels = width * height
        
        print(f"[map2d] Grid ajustado: {width}x{height} pixels ({total_pixels:,} total, resolução: {resolution:.4f}m)")
    
    # Validação final (inteiros não podem ser NaN, então só verificamos <= 0)
    if width <= 0 or height <= 0:
        raise ValueError(
            f"Dimensões do grid inválidas: width={width}, height={height}. "
            f"Size: {size}, Resolution: {resolution}"
        )
    
    print(f"[map2d] Criando grid: {width}x{height} pixels ({width*height:,} total)")
    
    try:
        grid = np.full((height, width), unknown_value, dtype=np.uint8)
    except (ValueError, MemoryError) as e:
        raise ValueError(
            f"Não foi possível criar grid de {width}x{height} pixels ({width*height:,} total). "
            f"Ambiente muito grande ({size[0]:.1f}m x {size[1]:.1f}m) para resolução {resolution:.4f}m. "
            f"Erro: {e}. Considere aumentar a resolução ou reduzir o tamanho do ambiente."
        ) from e

    coords = ((points_xy - min_xy) / resolution).astype(int)
    coords[:, 0] = np.clip(coords[:, 0], 0, width - 1)
    coords[:, 1] = np.clip(coords[:, 1], 0, height - 1)
    grid[height - coords[:, 1] - 1, coords[:, 0]] = occupied_value

    origin = (float(min_xy[0]), float(min_xy[1]), 0.0)
    return grid, origin, resolution


def _disk_kernel(radius: int) -> np.ndarray:
    size = radius * 2 + 1
    y, x = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    mask = x * x + y * y <= radius * radius
    return mask.astype(np.uint8)


def _build_yaml(
    image_name: str,
    resolution: float,
    origin: Tuple[float, float, float],
    occupied_thresh: float,
    free_thresh: float,
) -> str:
    return (
        f"image: {image_name}\n"
        f"resolution: {resolution}\n"
        f"origin: [{origin[0]}, {origin[1]}, {origin[2]}]\n"
        f"negate: 0\n"
        f"occupied_thresh: {occupied_thresh}\n"
        f"free_thresh: {free_thresh}\n"
    )
