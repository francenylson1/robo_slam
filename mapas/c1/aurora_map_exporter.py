#!/usr/bin/env python3
"""
aurora_map_exporter.py — Exporta mapa 2D do Slamtec Aurora para PGM + YAML.

OPÇÃO A: usa o mapa de ocupância gerado pelo próprio Aurora (visual-inercial 3D)
e converte para o formato PGM P5 compatível com o scan matching do robô.

FLUXO DE USO
────────────
1. Ligue o Aurora e conecte o Raspberry Pi à mesma rede.
2. Guie o robô MANUALMENTE por toda a sala (> 30 s de exploração).
3. Execute este script:

       python mapas/c1/aurora_map_exporter.py 192.168.1.212

4. Abra o arquivo .pgm gerado (ex: em GIMP ou eog) e verifique se:
   - Paredes aparecem como linhas pretas
   - Interior aparece branco (espaço livre)
   - Norte está no TOPO da imagem
5. Se o mapa estiver rotacionado, reexecute com --rotate 90 (ou 180 / 270).
6. Se estiver espelhado, use --flip-x ou --flip-y.
7. Atualize src/core/config.py com os novos caminhos PGM/YAML.

SISTEMA DE COORDENADAS DO ROBÔ
───────────────────────────────
  • X cresce para LESTE  (colunas do PGM, esquerda→direita)
  • Y cresce para SUL    (linhas do PGM, cima→baixo)
  • Ângulo 0° = Leste, 270° = Norte
  • Sala Maker: 6.26 m × 12.00 m

ALINHAMENTO COM O AURORA
─────────────────────────
O Aurora cria seu próprio sistema de coordenadas relativo à pose inicial.
Se o robô começa no canto NW (x=0, y=0) e --start-x/y=0:
  • origin_yaml = (0, 0) → pixel (0,0) = mundo (0,0) = canto NW
Caso contrário, passe --start-x e --start-y com a pose inicial do robô
(em metros no mundo do robô) para calcular o origin_yaml correto.

REQUISITOS
──────────
  pip install Pillow numpy

O SDK do Aurora deve estar em py_aurora_remote-main/ na raiz do projeto.
"""

import argparse
import math
import os
import sys
import time
from datetime import datetime

import numpy as np

# ── Localiza raiz do projeto e SDK ──────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
SDK_PATH = os.path.join(PROJECT_ROOT, "py_aurora_remote-main", "python_bindings")
sys.path.insert(0, SDK_PATH)

try:
    from slamtec_aurora_sdk import AuroraSDK
    from slamtec_aurora_sdk.data_types import GridMapGenerationOptions, Rect
    from slamtec_aurora_sdk.utils import wait_for_map_data
except ImportError as e:
    print(f"ERRO: Não foi possível importar o SDK Aurora: {e}")
    print(f"  Verifique se py_aurora_remote-main/ existe em: {PROJECT_ROOT}")
    sys.exit(1)


# ── Dimensões padrão da Sala Maker ──────────────────────────────────────────
ROOM_W = 6.26   # leste–oeste (eixo X do robô)
ROOM_H = 12.00  # norte–sul   (eixo Y do robô)

# Conversão de valores Aurora l2p → PGM do robô
# Aurora l2p: 255 = ocupado, 127 = livre, 0 = desconhecido
# PGM robô:     0 = ocupado,  254 = livre, 205 = desconhecido
_L2P_TO_PGM = np.zeros(256, dtype=np.uint8)
_L2P_TO_PGM[255] = 0    # ocupado → preto
_L2P_TO_PGM[127] = 254  # livre   → branco
# resto permanece 205 (desconhecido → cinza) — preenchimento abaixo
_UNKNOWN_MASK_VALUE = 205


def _build_l2p_lut() -> np.ndarray:
    """LUT para conversão Aurora l2p → PGM."""
    lut = np.full(256, _UNKNOWN_MASK_VALUE, dtype=np.uint8)
    lut[255] = 0    # ocupado → preto
    lut[127] = 254  # livre   → branco
    return lut


_LUT = _build_l2p_lut()


def _rotate_pgm(arr: np.ndarray, degrees: int) -> np.ndarray:
    """Rotaciona o array PGM em múltiplos de 90°."""
    k = (degrees // 90) % 4
    return np.rot90(arr, k=k)


def _save_pgm_p5(arr: np.ndarray, path: str) -> None:
    """Salva array uint8 como PGM P5 binário (formato compatível com lidar_pose_corrector)."""
    h, w = arr.shape
    with open(path, "wb") as f:
        f.write(b"P5\n")
        f.write(f"{w} {h}\n".encode())
        f.write(b"255\n")
        f.write(arr.tobytes())


def _save_yaml(pgm_filename: str, yaml_path: str,
               resolution: float, origin_x: float, origin_y: float) -> None:
    """
    Salva YAML compatível com lidar_pose_corrector.py.

    origin_x/y = coordenadas do mundo que correspondem ao pixel (col=0, row=0)
    do PGM, no sistema de coordenadas do ROBÔ (X→Leste, Y→Sul).
    """
    content = (
        f"image: {pgm_filename}\n"
        f"resolution: {resolution}\n"
        f"origin:\n"
        f"- {origin_x}\n"
        f"- {origin_y}\n"
        f"- 0.0\n"
        f"negate: 0\n"
        f"occupied_thresh: 0.65\n"
        f"free_thresh: 0.196\n"
    )
    with open(yaml_path, "w") as f:
        f.write(content)


def _cleanup_isolated_blobs(pgm: np.ndarray,
                             min_blob_px: int = 5) -> np.ndarray:
    """
    Remove regiões ocupadas pequenas e isoladas do PGM.

    Paredes e móveis formam regiões grandes e conectadas (centenas de pixels).
    O rastro do operador forma pontos espalhados e isolados (1–10 pixels).
    Este filtro mantém apenas blobs com área >= min_blob_px pixels.

    Requer scipy. Se não disponível, retorna o PGM sem modificação e avisa.

    Args:
        pgm        : array PGM (0=ocupado, 254=livre, 205=desconhecido)
        min_blob_px: tamanho mínimo em pixels para manter um blob (padrão: 5)
                     ≈ 12.5 cm² a 5 cm/px. Perna de mesa típica = 4–16 px.

    Returns:
        PGM limpo
    """
    if min_blob_px <= 1:
        return pgm

    try:
        from scipy import ndimage
    except ImportError:
        print("  ⚠  scipy não instalado — limpeza de blobs desativada.")
        print("     Instale com: pip install scipy")
        return pgm

    occupied = (pgm == 0)
    if not occupied.any():
        return pgm

    labeled, num = ndimage.label(occupied,
                                  structure=np.ones((3, 3), dtype=bool))
    if num == 0:
        return pgm

    sizes = np.bincount(labeled.ravel())   # sizes[0] = background
    sizes[0] = min_blob_px                 # garante que background não seja removido

    large_mask = sizes[labeled] >= min_blob_px

    result  = pgm.copy()
    removed = int(occupied.sum()) - int((occupied & large_mask).sum())
    if removed > 0:
        print(f"  Limpeza de blobs: {removed} px removidos "
              f"(blobs < {min_blob_px} px, "
              f"≈ {removed * 0.05 * 0.05 * 1e4:.0f} cm²)")
    result[occupied & ~large_mask] = _UNKNOWN_MASK_VALUE
    return result


def _print_stats(arr: np.ndarray, resolution: float) -> None:
    total = arr.size
    occ   = int(np.sum(arr == 0))
    free  = int(np.sum(arr == 254))
    unk   = int(np.sum(arr == _UNKNOWN_MASK_VALUE))
    h, w  = arr.shape
    print(f"  Dimensões: {w} × {h} px  "
          f"({w * resolution:.2f} m × {h * resolution:.2f} m)")
    print(f"  Ocupado  (preto)    : {occ:>8,}  ({100*occ/total:5.1f}%)")
    print(f"  Livre    (branco)   : {free:>8,}  ({100*free/total:5.1f}%)")
    print(f"  Desconhecido (cinza): {unk:>8,}  ({100*unk/total:5.1f}%)")
    if occ / total < 0.05:
        print("  ⚠  < 5% ocupado — verifique se o robô explorou a sala inteira.")
    if free / total < 0.10:
        print("  ⚠  < 10% livre — interior pode não ter sido mapeado.")


def _crop_or_pad_to_room(pgm: np.ndarray,
                         origin_x: float, origin_y: float,
                         resolution: float,
                         room_w: float = ROOM_W,
                         room_h: float = ROOM_H) -> tuple:
    """
    Ajusta o PGM para cobrir exatamente a área [0, room_w] × [0, room_h] no
    sistema de coordenadas do robô, com origin=(0, 0).

    Regras:
      • Se o mapa Aurora excede as bordas da sala → corta o excesso.
      • Se o mapa não chega a cobrir toda a sala  → preenche com cinza (205).
      • Sempre retorna origin=(0.0, 0.0) ao final.

    O ajuste usa o origin calculado de (start_rx, start_ry) para determinar
    onde a sala começa dentro do mapa Aurora. Se origin já for (0,0) e o mapa
    cobrir a sala inteira, nenhuma operação é realizada.

    Retorna: (pgm_ajustado, 0.0, 0.0)
    """
    res = resolution
    target_cols = int(round(room_w / res))
    target_rows = int(round(room_h / res))

    h_src, w_src = pgm.shape

    # Pixel no mapa atual que corresponde ao mundo (0,0) = canto NW da sala
    # pixel_nw_col = (world_x=0 - origin_x) / res
    nw_col = int(round(-origin_x / res))   # col no mapa atual = x=0
    nw_row = int(round(-origin_y / res))   # row no mapa atual = y=0

    # Cria mapa destino preenchido com cinza
    result = np.full((target_rows, target_cols), _UNKNOWN_MASK_VALUE, dtype=np.uint8)

    # Região de origem (fonte) a copiar
    src_col0 = max(0, nw_col)
    src_row0 = max(0, nw_row)
    src_col1 = min(w_src, nw_col + target_cols)
    src_row1 = min(h_src, nw_row + target_rows)

    # Região de destino correspondente
    dst_col0 = src_col0 - nw_col
    dst_row0 = src_row0 - nw_row
    dst_col1 = dst_col0 + (src_col1 - src_col0)
    dst_row1 = dst_row0 + (src_row1 - src_row0)

    if src_col1 > src_col0 and src_row1 > src_row0:
        result[dst_row0:dst_row1, dst_col0:dst_col1] = \
            pgm[src_row0:src_row1, src_col0:src_col1]

    clipped_w = max(0, -nw_col) + max(0, nw_col + target_cols - w_src)
    clipped_h = max(0, -nw_row) + max(0, nw_row + target_rows - h_src)
    if clipped_w > 0 or clipped_h > 0:
        print(f"  ℹ  Mapa Aurora não cobriu toda a sala: "
              f"{clipped_w} colunas e {clipped_h} linhas preenchidas com cinza.")
        print(f"     Certifique-se de que o robô percorreu a sala inteira durante o mapeamento.")

    return result, 0.0, 0.0


class AuroraMapExporter:
    """
    Exporta o mapa 2D de ocupância do Slamtec Aurora para PGM + YAML.

    Transformação de coordenadas Aurora → Robô
    ───────────────────────────────────────────
    O Aurora usa: X = frente do robô ao iniciar, Y = esquerda, Z = cima.
    O robô usa:   X = Leste, Y = Sul.

    Após gerar o mapa 2D e aplicar flipud (Y Aurora vira para cima), as convenções
    ficam alinhadas SE o robô iniciou o mapeamento apontando para Leste (theta=0°).
    Para outras orientações iniciais, use --rotate.

    Cálculo do origin_yaml
    ─────────────────────
    O YAML origin = (origin_x, origin_y) é a coordenada de MUNDO (sistema robô)
    do pixel (col=0, row=0) do PGM.

    Com flipud aplicado ao mapa Aurora:
      pixel (col=c, row=r) → Aurora world (min_x + c·res, max_y - r·res)

    Se Aurora world (0,0) = Robô world (start_rx, start_ry), então:
      robot_x = start_rx + aurora_x
      robot_y = start_ry - aurora_y     ← Aurora Y vai para Norte (−Y robô)

    Para col=0, row=0:
      origin_x = start_rx + dim.min_x
      origin_y = start_ry - dim.max_y
    """

    def __init__(self, ip: str, resolution: float = 0.05,
                 height_min: float = 0.05, height_max: float = 1.80,
                 canvas_m: float = 50.0):
        self.ip         = ip
        self.resolution = resolution
        self.height_min = height_min
        self.height_max = height_max
        self.canvas_m   = canvas_m
        self.sdk        = AuroraSDK()

    def connect(self) -> None:
        print(f"Conectando ao Aurora em {self.ip} ...")
        self.sdk.connect(connection_string=self.ip)
        print("  ✓ Conectado!")

    def disconnect(self) -> None:
        try:
            self.sdk.enable_map_data_syncing(False)
            self.sdk.disconnect()
        except Exception:
            pass

    def wait_for_map(self, min_keyframes: int = 15,
                     max_wait: float = 90.0) -> dict:
        """Aguarda dados mínimos sincronizados antes de gerar o mapa."""
        print("Habilitando sincronização de mapa...")
        self.sdk.enable_map_data_syncing(True)
        time.sleep(1.5)

        last_print = [0.0]

        def _progress(elapsed: float, status: dict) -> None:
            if elapsed - last_print[0] >= 5.0:
                last_print[0] = elapsed
                print(f"  {elapsed:5.0f}s  keyframes={status['total_kf_count']:3d}  "
                      f"sync={status['sync_ratio']*100:.0f}%")

        status = wait_for_map_data(
            self.sdk.data_provider,
            min_keyframes=min_keyframes,
            min_sync_ratio=0.80,
            max_wait_time=max_wait,
            progress_callback=_progress,
        )
        kf  = status["total_kf_count"]
        syn = status["sync_ratio"] * 100
        if status["is_sufficient"]:
            print(f"  ✓ Dados suficientes: {kf} keyframes, {syn:.0f}% sync.")
        else:
            print(f"  ⚠  Usando dados parciais: {kf} keyframes, {syn:.0f}% sync.")
        return status

    def generate_raw_grid(self) -> dict:
        """Gera o mapa 2D on-demand e retorna a grade Aurora + metadados."""
        opts = GridMapGenerationOptions()
        opts.resolution          = self.resolution
        opts.map_canvas_width    = self.canvas_m
        opts.map_canvas_height   = self.canvas_m
        opts.active_map_only     = 1
        opts.height_range_specified = 1
        opts.min_height          = self.height_min
        opts.max_height          = self.height_max

        print(f"\nGerando mapa 2D (res={self.resolution*100:.0f} cm, "
              f"altura {self.height_min:.2f}–{self.height_max:.2f} m)...")
        gmap = self.sdk.lidar_2d_map_builder.generate_fullmap_ondemand(
            opts, wait_for_data_sync=True, timeout_ms=90_000
        )

        dim = gmap.get_map_dimension()
        print(f"  Aurora dim: X=[{dim.min_x:.2f}, {dim.max_x:.2f}] m  "
              f"Y=[{dim.min_y:.2f}, {dim.max_y:.2f}] m")

        rect        = Rect()
        rect.x      = dim.min_x
        rect.y      = dim.min_y
        rect.width  = dim.max_x - dim.min_x
        rect.height = dim.max_y - dim.min_y

        # l2p_mapping=True: 255=ocupado, 127=livre, 0=desconhecido
        cell_data, info = gmap.read_cell_data(
            rect, resolution=self.resolution, l2p_mapping=True
        )
        raw = np.array(cell_data, dtype=np.uint8).reshape(
            info.cell_height, info.cell_width
        )
        print(f"  Grade Aurora: {info.cell_width} × {info.cell_height} px")
        return {"raw": raw, "dim": dim}

    def export(self, output_base: str,
               start_rx: float = 0.0, start_ry: float = 0.0,
               rotate_deg: int = 0,
               flip_x: bool = False, flip_y: bool = False,
               min_blob_px: int = 5,
               min_keyframes: int = 15,
               interactive: bool = False) -> bool:
        """
        Fluxo completo: conecta → aguarda mapa → gera → converte → salva.

        Parâmetros
        ──────────
        output_base : caminho sem extensão (ex: mapas/c1/sala_maker_aurora)
        start_rx    : posição X do robô no mundo quando o mapeamento começou (m)
        start_ry    : posição Y do robô no mundo quando o mapeamento começou (m)
        rotate_deg  : rotação adicional do mapa em graus (0, 90, 180, 270)
        flip_x      : espelhar horizontalmente após flipud + rotação
        flip_y      : espelhar verticalmente após flipud + rotação
        """
        self.connect()
        try:
            if interactive:
                print("\n" + "="*60)
                print("  Aurora conectado e mapeando.")
                print("  EMPURRE O ROBÔ por toda a sala agora.")
                print("  Quando terminar o percurso, pressione ENTER.")
                print("="*60 + "\n")
                input("  >>> Pressione ENTER para exportar o mapa: ")
                print()
            self.wait_for_map(min_keyframes=min_keyframes)
            data = self.generate_raw_grid()
        except Exception as exc:
            print(f"ERRO durante geração do mapa: {exc}")
            import traceback; traceback.print_exc()
            return False
        finally:
            self.disconnect()

        dim = data["dim"]
        raw = data["raw"]

        # ── 1. Converte l2p → PGM (antes de qualquer flip/rotação) ──────────
        pgm = _LUT[raw]  # vetorizado, eficiente

        # ── 2. flipud: Aurora row 0 = min_y (sul) → invertido = norte no topo ─
        pgm = np.flipud(pgm)

        # ── 3. Rotação adicional (para corrigir orientação do sensor) ─────────
        if rotate_deg:
            pgm = _rotate_pgm(pgm, rotate_deg)

        # ── 4. Espelhamento opcional ──────────────────────────────────────────
        if flip_x:
            pgm = np.fliplr(pgm)
        if flip_y:
            pgm = np.flipud(pgm)

        # ── 5. Calcula origin_yaml ─────────────────────────────────────────
        # Após flipud (sem rotação extra), pixel (col=0, row=0):
        #   aurora_x = dim.min_x,  aurora_y = dim.max_y
        #   robot_x  = start_rx + aurora_x
        #   robot_y  = start_ry - aurora_y   (Aurora Y→Norte = −robô Y)
        if rotate_deg == 0:
            origin_x = start_rx + dim.min_x
            origin_y = start_ry - dim.max_y
        else:
            # Com rotação, a origem muda — cálculo conservador: mantém centro do
            # mapa e imprime instruções para ajuste manual.
            cx_world = start_rx + (dim.min_x + dim.max_x) / 2.0
            cy_world = start_ry - (dim.max_y + dim.min_y) / 2.0
            h, w = pgm.shape
            origin_x = cx_world - (w / 2.0) * self.resolution
            origin_y = cy_world - (h / 2.0) * self.resolution
            print(f"\n  ⚠  Rotação aplicada: origin_yaml calculado pelo centro do mapa.")
            print(f"     Verifique visualmente e ajuste --start-x/--start-y se necessário.")

        # ── 6. Limpeza de blobs isolados (rastro do operador) ────────────────
        if min_blob_px > 1:
            pgm = _cleanup_isolated_blobs(pgm, min_blob_px)

        # ── 7. Crop/pad para dimensões exatas da sala (opcional) ─────────────
        # Se origin_x/y < 0 ou o mapa for menor que a sala, ajusta para cobrir
        # exatamente [origin_x .. origin_x + ROOM_W] × [origin_y .. origin_y + ROOM_H].
        pgm, origin_x, origin_y = _crop_or_pad_to_room(
            pgm, origin_x, origin_y, self.resolution
        )

        # ── 8. Salva arquivos ─────────────────────────────────────────────────
        os.makedirs(os.path.dirname(os.path.abspath(output_base)), exist_ok=True)
        pgm_path  = output_base + ".pgm"
        yaml_path = output_base + ".yaml"

        _save_pgm_p5(pgm, pgm_path)
        _save_yaml(
            pgm_filename=os.path.basename(pgm_path),
            yaml_path=yaml_path,
            resolution=self.resolution,
            origin_x=round(origin_x, 6),
            origin_y=round(origin_y, 6),
        )

        print(f"\n✓ PGM salvo : {pgm_path}")
        print(f"✓ YAML salvo: {yaml_path}")
        print(f"  origin_yaml: ({origin_x:.4f}, {origin_y:.4f})")
        _print_stats(pgm, self.resolution)

        print(f"\nPara usar no scan matching, atualize src/core/config.py:")
        print(f"  SCAN_MATCH_PGM_PATH  = r\"{pgm_path}\"")
        print(f"  SCAN_MATCH_YAML_PATH = r\"{yaml_path}\"")
        print(f"\n  Posição inicial do robô em relação ao mapa:")
        robot_x, robot_y = 5.7, 11.5   # posição padrão do robô
        col_px = (robot_x - origin_x) / self.resolution
        row_px = (robot_y - origin_y) / self.resolution
        print(f"  Robô em ({robot_x}, {robot_y}) m → pixel ({col_px:.0f}, {row_px:.0f})")
        return True


def _load_pgm_p5(path: str):
    """Lê um PGM P5 e retorna array uint8."""
    with open(path, "rb") as f:
        # Lê header ignorando comentários
        lines = []
        while len(lines) < 3:
            raw = f.readline()
            line = raw.decode("ascii", errors="ignore").strip()
            if line and not line.startswith("#"):
                lines.append(line)
        if lines[0] != "P5":
            raise ValueError(f"Formato PGM não suportado: {lines[0]}")
        w, h   = map(int, lines[1].split())
        _maxval = int(lines[2])
        data   = np.frombuffer(f.read(w * h), dtype=np.uint8).reshape((h, w))
    return data


def _load_yaml_origin(yaml_path: str):
    """Lê origin e resolution do YAML. Retorna (resolution, origin_x, origin_y)."""
    try:
        import yaml as _yaml
        with open(yaml_path) as f:
            meta = _yaml.safe_load(f)
        res = float(meta.get("resolution", 0.05))
        orig = meta.get("origin", [0.0, 0.0, 0.0])
        return res, float(orig[0]), float(orig[1])
    except Exception as exc:
        raise RuntimeError(f"Não foi possível ler {yaml_path}: {exc}")


def _recalc_origin(origin_x: float, origin_y: float,
                   resolution: float,
                   h_old: int, w_old: int,
                   rotate_deg: int,
                   flip_x: bool, flip_y: bool):
    """
    Recalcula (origin_x, origin_y) após rotação e flip.

    origin_x/y é a coordenada de MUNDO do pixel (col=0, row=0) do PGM.
    Convenção: col → X (Leste), row → Y (Sul).

    Para cada transformação, o pixel (0,0) do novo mapa corresponde a
    um pixel diferente do mapa original → calculamos as coordenadas de mundo
    desse pixel e as usamos como novo origin.
    """
    ox, oy = origin_x, origin_y
    res    = resolution
    h, w   = h_old, w_old

    # np.rot90(arr, k) onde k = rotate_deg // 90
    # k=1 (90° CCW): new[i][j] = old[j][w-1-i]  → new(0,0) = old[0][w-1]
    # k=2 (180°):    new[i][j] = old[h-1-i][w-1-j] → new(0,0) = old[h-1][w-1]
    # k=3 (270° CCW = 90° CW): new[i][j] = old[h-1-j][i] → new(0,0) = old[h-1][0]
    k = (rotate_deg // 90) % 4
    if k == 1:
        # new(0,0) ← old(row=0, col=w-1): mais à direita da linha do topo
        new_ox = ox + (w - 1) * res
        new_oy = oy
        h, w   = w_old, h_old   # shape trocada
    elif k == 2:
        # new(0,0) ← old(row=h-1, col=w-1): canto inferior direito
        new_ox = ox + (w - 1) * res
        new_oy = oy + (h - 1) * res
    elif k == 3:
        # new(0,0) ← old(row=h-1, col=0): canto inferior esquerdo
        new_ox = ox
        new_oy = oy + (h - 1) * res
        h, w   = w_old, h_old   # shape trocada
    else:
        new_ox, new_oy = ox, oy

    ox, oy = new_ox, new_oy

    # flip_x (np.fliplr): new(0,0) ← old(row=0, col=w-1)
    if flip_x:
        ox = ox + (w - 1) * res

    # flip_y (np.flipud): new(0,0) ← old(row=h-1, col=0)
    if flip_y:
        oy = oy + (h - 1) * res

    return ox, oy


def reprocess_pgm(pgm_path: str, output_base: str,
                  rotate_deg: int = 0,
                  flip_x: bool = False, flip_y: bool = False,
                  override_origin_x: float = None,
                  override_origin_y: float = None,
                  min_blob_px: int = 5) -> bool:
    """
    Reprocessa um PGM existente (sem conectar ao Aurora):
      • Aplica rotação e/ou flip
      • Recalcula o YAML origin automaticamente
      • Salva novos PGM + YAML

    Parâmetros
    ──────────
    pgm_path          : caminho do PGM gerado anteriormente
    output_base       : caminho base de saída sem extensão
    rotate_deg        : 0, 90, 180 ou 270 (graus, sentido anti-horário)
    flip_x / flip_y   : espelhar após rotação
    override_origin_* : se fornecidos, sobrescreve o origin calculado
    """
    yaml_path = os.path.splitext(pgm_path)[0] + ".yaml"
    if not os.path.exists(pgm_path):
        print(f"ERRO: PGM não encontrado: {pgm_path}")
        return False

    print(f"Carregando PGM: {pgm_path}")
    pgm = _load_pgm_p5(pgm_path)
    h_old, w_old = pgm.shape

    # Lê origin/resolution do YAML original (se existir)
    resolution = 0.05
    origin_x, origin_y = 0.0, 0.0
    if os.path.exists(yaml_path):
        resolution, origin_x, origin_y = _load_yaml_origin(yaml_path)
        print(f"YAML original: res={resolution} m/px  origin=({origin_x}, {origin_y})")
    else:
        print(f"  ⚠  YAML não encontrado ({yaml_path}), usando origin=(0,0).")

    # Aplica transformações geométricas
    if rotate_deg:
        pgm = _rotate_pgm(pgm, rotate_deg)
        print(f"  Rotação {rotate_deg}° CCW aplicada → novo shape: {pgm.shape}")
    if flip_x:
        pgm = np.fliplr(pgm)
        print("  Flip horizontal (X) aplicado.")
    if flip_y:
        pgm = np.flipud(pgm)
        print("  Flip vertical (Y) aplicado.")

    # Recalcula origin
    new_ox, new_oy = _recalc_origin(
        origin_x, origin_y, resolution,
        h_old, w_old, rotate_deg, flip_x, flip_y,
    )
    if override_origin_x is not None:
        new_ox = override_origin_x
    if override_origin_y is not None:
        new_oy = override_origin_y

    # Limpeza de blobs isolados
    if min_blob_px > 1:
        pgm = _cleanup_isolated_blobs(pgm, min_blob_px)

    # Crop/pad para dimensões exatas da sala
    pgm, new_ox, new_oy = _crop_or_pad_to_room(pgm, new_ox, new_oy, resolution)

    # Salva
    os.makedirs(os.path.dirname(os.path.abspath(output_base)) or ".", exist_ok=True)
    new_pgm_path  = output_base + ".pgm"
    new_yaml_path = output_base + ".yaml"

    _save_pgm_p5(pgm, new_pgm_path)
    _save_yaml(
        pgm_filename=os.path.basename(new_pgm_path),
        yaml_path=new_yaml_path,
        resolution=resolution,
        origin_x=round(new_ox, 6),
        origin_y=round(new_oy, 6),
    )

    print(f"\n✓ PGM ajustado : {new_pgm_path}")
    print(f"✓ YAML ajustado: {new_yaml_path}")
    print(f"  origin_yaml  : ({new_ox:.4f}, {new_oy:.4f})")
    _print_stats(pgm, resolution)

    print(f"\nPara usar no scan matching, atualize src/core/config.py:")
    print(f"  SCAN_MATCH_PGM_PATH  = r\"{new_pgm_path}\"")
    print(f"  SCAN_MATCH_YAML_PATH = r\"{new_yaml_path}\"")
    return True


def main() -> int:
    p = argparse.ArgumentParser(
        description="Exporta mapa 2D do Slamtec Aurora para PGM + YAML.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # ── Fonte dos dados: Aurora ao vivo OU PGM já existente ─────────────────
    src = p.add_mutually_exclusive_group()
    src.add_argument("device_ip", nargs="?", default=None,
                     help="IP do Aurora (ex: 192.168.1.212). "
                          "Omita se usar --from-pgm.")
    src.add_argument("--from-pgm", metavar="PGM_PATH",
                     help="Reprocessa um PGM já gerado SEM conectar ao Aurora. "
                          "Útil para testar --rotate / --flip-x / --flip-y "
                          "sem refazer o mapeamento.")

    p.add_argument("-o", "--output",
                   default=None,
                   help="Caminho base de saída sem extensão. "
                        "Padrão: mesmo diretório do PGM original com sufixo _adj, "
                        "ou mapas/c1/aurora_TIMESTAMP quando gerando do Aurora.")
    p.add_argument("-r", "--resolution", type=float, default=0.05,
                   help="Resolução em m/px (padrão: 0.05 = 5 cm)")
    p.add_argument("--height-min", type=float, default=0.05,
                   help="Altura mínima dos obstáculos a incluir (m, padrão: 0.05)")
    p.add_argument("--height-max", type=float, default=1.80,
                   help="Altura máxima dos obstáculos a incluir (m, padrão: 1.80)")
    p.add_argument("--start-x", type=float, default=0.0,
                   help="Posição X do robô (mundo) quando mapeamento começou (m)")
    p.add_argument("--start-y", type=float, default=0.0,
                   help="Posição Y do robô (mundo) quando mapeamento começou (m)")
    p.add_argument("--rotate", type=int, default=0, choices=[0, 90, 180, 270],
                   help="Rotação do mapa em graus anti-horários (padrão: 0)")
    p.add_argument("--flip-x", action="store_true",
                   help="Espelhar mapa horizontalmente")
    p.add_argument("--flip-y", action="store_true",
                   help="Espelhar mapa verticalmente")
    p.add_argument("--canvas", type=float, default=50.0,
                   help="Canvas de geração Aurora em metros (padrão: 50)")
    p.add_argument("--min-keyframes", type=int, default=15,
                   help="Keyframes mínimos antes de gerar (padrão: 15)")
    p.add_argument("--interactive", action="store_true",
                   help="Aguarda ENTER do operador antes de exportar. "
                        "Use para mapear manualmente: conecta, empurra o robô, "
                        "pressiona Enter quando terminar.")
    p.add_argument("--min-blob-size", type=int, default=5,
                   metavar="PX",
                   help="Remove blobs ocupados menores que PX pixels (padrão: 5). "
                        "Elimina rastros do operador sem apagar pernas de mesa. "
                        "Use 0 para desativar a limpeza.")
    args = p.parse_args()

    # ── Modo: reprocessar PGM existente ──────────────────────────────────────
    if args.from_pgm:
        base = args.from_pgm
        if base.endswith(".pgm"):
            base = base[:-4]
        output_base = args.output or (base + "_adj")
        return 0 if reprocess_pgm(
            pgm_path=args.from_pgm if args.from_pgm.endswith(".pgm")
                     else args.from_pgm + ".pgm",
            output_base=output_base,
            rotate_deg=args.rotate,
            flip_x=args.flip_x,
            flip_y=args.flip_y,
            override_origin_x=args.start_x if args.start_x != 0.0 else None,
            override_origin_y=args.start_y if args.start_y != 0.0 else None,
            min_blob_px=args.min_blob_size,
        ) else 1

    # ── Modo: gerar do Aurora ─────────────────────────────────────────────────
    if not args.device_ip:
        p.error("Informe o IP do Aurora (ex: 192.168.1.212) "
                "ou use --from-pgm para reprocessar um mapa existente.")

    if args.resolution <= 0:
        p.error("--resolution deve ser positivo")

    output_base = args.output or os.path.join(
        PROJECT_ROOT, "mapas", "c1",
        f"aurora_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )

    exporter = AuroraMapExporter(
        ip=args.device_ip,
        resolution=args.resolution,
        height_min=args.height_min,
        height_max=args.height_max,
        canvas_m=args.canvas,
    )

    ok = exporter.export(
        output_base=output_base,
        start_rx=args.start_x,
        start_ry=args.start_y,
        rotate_deg=args.rotate,
        flip_x=args.flip_x,
        flip_y=args.flip_y,
        min_blob_px=args.min_blob_size,
        min_keyframes=args.min_keyframes,
        interactive=args.interactive,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
