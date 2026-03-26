#!/usr/bin/env python3
"""
c1_slam_mapper.py — Mapeamento SLAM 2D manual com RPLidar C1 (Opção B).

Implementa Hector SLAM simplificado em Python puro:
  • Grade de ocupância com modelo log-odds (raycasting de Bresenham)
  • Rastreamento de pose por scan matching contínuo (scan → mapa atual)
  • Exportação PGM P5 + YAML compatível com lidar_pose_corrector.py

FLUXO DE USO
────────────
1. Conecte o C1 ao Raspberry Pi (USB → /dev/ttyUSB0).
2. Coloque o robô em posição conhecida (ex: canto NW = x=0.30, y=0.30).
3. Execute:

       # Posição inicial: 30 cm do canto NW, apontando para Norte (270°)
       python mapas/c1/c1_slam_mapper.py \\
           --init-x 0.30 --init-y 0.30 --init-theta 270

4. Guie o robô DEVAGAR por toda a sala (< 0.3 m/s).
   O mapa é construído automaticamente.
5. Pressione S para salvar a qualquer momento.
   Pressione Q (ou Ctrl+C) para encerrar e salvar.

SISTEMA DE COORDENADAS
───────────────────────
  • X cresce para LESTE  (colunas do PGM)
  • Y cresce para SUL    (linhas do PGM)
  • Ângulo 0° = Leste, 270° = Norte (igual ao lidar_pose_corrector)
  • Origem (0,0) = canto NW da sala → pixel (col=0, row=0)

PARÂMETROS DO SLAM
──────────────────
  • LOG-ODDS: cada raio do lidar vota livre/ocupado com evidência log-odds.
  • MATCH: antes de inserir cada scan, busca em grade ±20 cm / ±5° ao redor
    da pose estimada para corrigir drift de odometria.
  • MIN_SCORE: score de scan matching mínimo para aceitar a correção de pose.

REQUISITOS
──────────
  pip install numpy
  RPLidar C1 conectado e src/core disponível no PYTHONPATH (via PROJECT_ROOT).
"""

import argparse
import math
import os
import sys
import termios
import threading
import tty
import time
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np

# ── Localiza raiz do projeto ─────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

try:
    from core.lidar_c1_reader import LidarC1Reader, FRONT_CENTER_DEG
except ImportError as exc:
    print(f"ERRO: Não foi possível importar LidarC1Reader: {exc}")
    print(f"  Certifique-se de rodar a partir de: {PROJECT_ROOT}")
    sys.exit(1)

# ── Geometria da Sala Maker ──────────────────────────────────────────────────
ROOM_W = 6.26    # metros (leste–oeste)
ROOM_H = 12.00   # metros (norte–sul)

# ── Parâmetros do mapa ───────────────────────────────────────────────────────
RESOLUTION = 0.05     # m/px (5 cm)

# PGM: 0 = ocupado (preto), 254 = livre (branco), 205 = desconhecido (cinza)
PGM_OCC  = 0
PGM_FREE = 254
PGM_UNK  = 205

# ── Modelo log-odds ──────────────────────────────────────────────────────────
LOG_HIT  =  2.5    # evidência de ocupação por endpoint de raio
LOG_MISS = -0.5    # evidência de célula livre por raio passante
LOG_MIN  = -10.0
LOG_MAX  =  10.0
LOG_THRESH_OCC  =  0.8   # log-odds mínimo para marcar como ocupado
LOG_THRESH_FREE = -0.3   # log-odds máximo para marcar como livre

# ── Parâmetros de scan matching ──────────────────────────────────────────────
MATCH_XY_RANGE  = 0.20   # ±20 cm
MATCH_XY_STEP   = 0.05   # passo 5 cm
MATCH_TH_RANGE  = 5.0    # ±5°
MATCH_TH_STEP   = 1.0    # passo 1°
MATCH_MIN_SCORE = 0.10   # score mínimo para aceitar correção de pose
MATCH_MAX_PTS   = 80     # subamostrar scan para performance no Pi 4

# ── Parâmetros do lidar ──────────────────────────────────────────────────────
LIDAR_MAX_RANGE = 8.0    # m — ignora pontos > 8 m
LIDAR_MIN_RANGE = 0.18   # m — ignora pontos < 18 cm (reflexo do corpo)

# ── Mínimo de movimento para inserir novo scan ───────────────────────────────
MIN_TRAVEL_M   = 0.15   # 15 cm de deslocamento
MIN_TRAVEL_DEG = 8.0    # 8° de rotação


# ─────────────────────────────────────────────────────────────────────────────
# Grade de ocupância com log-odds
# ─────────────────────────────────────────────────────────────────────────────

class OccupancyGrid:
    """
    Grade de ocupância 2D com modelo log-odds.

    Sistema de coordenadas:
      col = (world_x - origin_x) / resolution   → X cresce para Leste
      row = (world_y - origin_y) / resolution   → Y cresce para Sul
    Pixel (col=0, row=0) corresponde ao ponto de mundo (origin_x, origin_y).
    """

    def __init__(self, width_m: float, height_m: float, resolution: float,
                 origin_x: float = 0.0, origin_y: float = 0.0):
        self.resolution = resolution
        self.origin_x   = origin_x
        self.origin_y   = origin_y
        self.cols       = int(math.ceil(width_m  / resolution))
        self.rows       = int(math.ceil(height_m / resolution))
        self._log       = np.zeros((self.rows, self.cols), dtype=np.float32)
        self._lock      = threading.Lock()

    # ── Conversão de coordenadas ──────────────────────────────────────────

    def world_to_pixel(self, wx: float, wy: float) -> Tuple[int, int]:
        col = int((wx - self.origin_x) / self.resolution)
        row = int((wy - self.origin_y) / self.resolution)
        return col, row

    def is_valid(self, col: int, row: int) -> bool:
        return 0 <= col < self.cols and 0 <= row < self.rows

    # ── Bresenham ─────────────────────────────────────────────────────────

    @staticmethod
    def _bresenham(c0: int, r0: int, c1: int, r1: int) -> List[Tuple[int, int]]:
        """Rasteriza o segmento (c0,r0)→(c1,r1) em células da grade."""
        cells = []
        dc = abs(c1 - c0)
        dr = abs(r1 - r0)
        sc = 1 if c0 < c1 else -1
        sr = 1 if r0 < r1 else -1
        err = dc - dr
        c, r = c0, r0
        while True:
            cells.append((c, r))
            if c == c1 and r == r1:
                break
            e2 = 2 * err
            if e2 > -dr:
                err -= dr
                c   += sc
            if e2 < dc:
                err += dc
                r   += sr
        return cells

    # ── Inserção de scan ──────────────────────────────────────────────────

    def insert_scan(self, robot_x: float, robot_y: float,
                    robot_theta_deg: float,
                    scan_points: List[Tuple[float, float]]) -> int:
        """
        Insere um scan na grade usando raycasting de Bresenham.

        Convenção de ângulo idêntica ao lidar_pose_corrector.py:
            world_angle = robot_theta_rad + (scan_angle_rad − sensor_front_rad)

        Retorna o número de pontos inseridos.
        """
        theta_rad        = math.radians(robot_theta_deg)
        sensor_front_rad = math.radians(FRONT_CENTER_DEG)

        c_robot, r_robot = self.world_to_pixel(robot_x, robot_y)
        inserted = 0

        with self._lock:
            for angle_deg, dist_m in scan_points:
                if not (LIDAR_MIN_RANGE <= dist_m <= LIDAR_MAX_RANGE):
                    continue

                world_angle = theta_rad + (math.radians(angle_deg) - sensor_front_rad)
                hit_x = robot_x + dist_m * math.cos(world_angle)
                hit_y = robot_y + dist_m * math.sin(world_angle)
                c_hit, r_hit = self.world_to_pixel(hit_x, hit_y)

                is_real_hit = dist_m < LIDAR_MAX_RANGE * 0.95

                cells = self._bresenham(c_robot, r_robot, c_hit, r_hit)

                # Células percorridas = livres (exceto o endpoint)
                for c, r in cells[:-1]:
                    if self.is_valid(c, r):
                        self._log[r, c] = float(np.clip(
                            self._log[r, c] + LOG_MISS, LOG_MIN, LOG_MAX
                        ))

                # Endpoint = ocupado (se for hit real)
                if is_real_hit and self.is_valid(c_hit, r_hit):
                    self._log[r_hit, c_hit] = float(np.clip(
                        self._log[r_hit, c_hit] + LOG_HIT, LOG_MIN, LOG_MAX
                    ))

                inserted += 1

        return inserted

    # ── Scan matching ─────────────────────────────────────────────────────

    def match_scan(self, scan_points: List[Tuple[float, float]],
                   init_x: float, init_y: float, init_theta_deg: float,
                   xy_range: float = MATCH_XY_RANGE,
                   xy_step:  float = MATCH_XY_STEP,
                   th_range: float = MATCH_TH_RANGE,
                   th_step:  float = MATCH_TH_STEP) -> Tuple[float, float, float, float]:
        """
        Scan matching vetorizado: encontra (x, y, theta) que maximiza acertos
        do scan nas células ocupadas da grade.

        Retorna (best_x, best_y, best_theta_deg, best_score).
        Score = fração de pontos que batem em células ocupadas (0–1).
        """
        # Filtra pontos válidos e subamostras
        valid = [(a, d) for a, d in scan_points
                 if LIDAR_MIN_RANGE <= d <= LIDAR_MAX_RANGE]
        if len(valid) < 15:
            return (init_x, init_y, init_theta_deg, 0.0)

        if len(valid) > MATCH_MAX_PTS:
            step = len(valid) // MATCH_MAX_PTS
            valid = valid[::step]

        angles_rad = np.array([math.radians(a) for a, _ in valid], dtype=np.float32)
        dists      = np.array([d            for _, d in valid], dtype=np.float32)
        sensor_fr  = math.radians(FRONT_CENTER_DEG)

        xy_offsets = np.arange(-xy_range, xy_range + 1e-9, xy_step, dtype=np.float32)
        th_offsets = np.arange(-th_range, th_range + 1e-9, th_step, dtype=np.float64)

        dx_g, dy_g = np.meshgrid(xy_offsets, xy_offsets, indexing="ij")

        best_score = -1.0
        best_pose  = (init_x, init_y, init_theta_deg)

        with self._lock:
            occ_map = self._log >= LOG_THRESH_OCC  # bool grid, não precisa copiar

            for dth in th_offsets:
                theta    = math.radians(init_theta_deg + dth)
                w_angles = theta + (angles_rad - sensor_fr)

                base_dx = (dists * np.cos(w_angles)).astype(np.float32)
                base_dy = (dists * np.sin(w_angles)).astype(np.float32)

                robot_x = (init_x + dx_g).astype(np.float32)  # (nx, ny)
                robot_y = (init_y + dy_g).astype(np.float32)

                # wx, wy shape: (n_pts, nx, ny)
                wx = robot_x[np.newaxis] + base_dx[:, np.newaxis, np.newaxis]
                wy = robot_y[np.newaxis] + base_dy[:, np.newaxis, np.newaxis]

                px = ((wx - self.origin_x) / self.resolution).astype(np.int32)
                py = ((wy - self.origin_y) / self.resolution).astype(np.int32)

                valid_m = (px >= 0) & (px < self.cols) & (py >= 0) & (py < self.rows)
                px_s    = np.where(valid_m, px, 0)
                py_s    = np.where(valid_m, py, 0)

                hits = np.where(valid_m, occ_map[py_s, px_s], False)

                n_valid = valid_m.sum(axis=0).astype(np.float32)
                n_hits  = hits.sum(axis=0).astype(np.float32)

                with np.errstate(invalid="ignore", divide="ignore"):
                    scores = np.where(n_valid > 0, n_hits / n_valid, 0.0)

                idx   = np.unravel_index(scores.argmax(), scores.shape)
                score = float(scores[idx])

                if score > best_score:
                    best_score = score
                    best_pose  = (
                        float(init_x + dx_g[idx]),
                        float(init_y + dy_g[idx]),
                        float(init_theta_deg + dth),
                    )

        return (*best_pose, best_score)

    # ── Exportação ────────────────────────────────────────────────────────

    def to_pgm_array(self) -> np.ndarray:
        """Converte log-odds em array PGM (0=occ, 254=free, 205=unk)."""
        with self._lock:
            log = self._log.copy()
        pgm = np.full((self.rows, self.cols), PGM_UNK, dtype=np.uint8)
        pgm[log >= LOG_THRESH_OCC]  = PGM_OCC
        pgm[log <= LOG_THRESH_FREE] = PGM_FREE
        return pgm

    def stats(self) -> dict:
        pgm   = self.to_pgm_array()
        total = pgm.size
        return {
            "occ"  : int(np.sum(pgm == PGM_OCC)),
            "free" : int(np.sum(pgm == PGM_FREE)),
            "unk"  : int(np.sum(pgm == PGM_UNK)),
            "total": total,
            "shape": pgm.shape,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Mapeador SLAM
# ─────────────────────────────────────────────────────────────────────────────

class C1SLAMMapper:
    """
    Mapeador SLAM 2D manual usando RPLidar C1.

    Rastreia a pose exclusivamente por scan matching contínuo
    (Hector SLAM simplificado) — sem odometria de encoder.

    A pose é atualizada a cada ciclo de mapeamento (SLAM_INTERVAL_S).
    O operador guia o robô fisicamente enquanto o mapa é construído.
    """

    # Intervalo entre ciclos de scan matching + inserção (segundos)
    SLAM_INTERVAL_S = 0.60

    # Primeiros N scans: insere sem matching (mapa vazio)
    BOOTSTRAP_SCANS = 3

    def __init__(self, port: str,
                 init_x: float, init_y: float, init_theta_deg: float,
                 output_dir: str):
        self.port        = port
        self.output_dir  = output_dir

        self.pose_x      = init_x
        self.pose_y      = init_y
        self.pose_theta  = init_theta_deg

        self.grid        = OccupancyGrid(ROOM_W, ROOM_H, RESOLUTION)
        self.lidar       = LidarC1Reader(port=port, min_stop_m=0.01)

        self._scan_count   = 0
        self._last_score   = 0.0
        self._last_pose    = (init_x, init_y, init_theta_deg)
        self._running      = False
        self._save_request = threading.Event()
        self._quit_request = threading.Event()

    # ── Ciclo de SLAM ─────────────────────────────────────────────────────

    def _slam_step(self) -> bool:
        """Executa um ciclo: scan matching → inserção na grade."""
        pts = self.lidar.get_last_scan_points()
        if not pts or len(pts) < 30:
            return False

        # Fase bootstrap: insere sem matching para construir mapa inicial
        if self._scan_count < self.BOOTSTRAP_SCANS:
            self.grid.insert_scan(self.pose_x, self.pose_y,
                                  self.pose_theta, pts)
            self._scan_count += 1
            self._last_score = 0.0
            return True

        # Scan matching para corrigir pose
        nx, ny, nth, score = self.grid.match_scan(
            pts, self.pose_x, self.pose_y, self.pose_theta
        )
        self._last_score = score

        if score >= MATCH_MIN_SCORE:
            # Verifica se houve movimento mínimo
            dx = nx - self._last_pose[0]
            dy = ny - self._last_pose[1]
            dth = abs(nth - self._last_pose[2])
            dist = math.hypot(dx, dy)
            if dist >= MIN_TRAVEL_M or dth >= MIN_TRAVEL_DEG:
                self.pose_x     = nx
                self.pose_y     = ny
                self.pose_theta = nth
        else:
            # Score insuficiente: mantém pose anterior
            nx, ny, nth = self.pose_x, self.pose_y, self.pose_theta

        self.grid.insert_scan(nx, ny, nth, pts)
        self._last_pose = (nx, ny, nth)
        self._scan_count += 1
        return True

    def _print_status(self) -> None:
        st = self.grid.stats()
        total = st["total"]
        print(
            f"  #{self._scan_count:4d}  pose=({self.pose_x:.2f}, {self.pose_y:.2f},"
            f" {self.pose_theta:.1f}°)  "
            f"score={self._last_score:.2f}  "
            f"occ={100*st['occ']/total:.1f}%  "
            f"free={100*st['free']/total:.1f}%"
        )

    # ── Mapeamento principal ──────────────────────────────────────────────

    def run(self) -> None:
        print("\n" + "=" * 60)
        print("  C1 SLAM MAPPER — MAPEAMENTO MANUAL ATIVO")
        print("=" * 60)
        print(f"  Pose inicial: ({self.pose_x:.2f}, {self.pose_y:.2f},"
              f" {self.pose_theta:.1f}°)")
        print(f"  Grade: {self.grid.cols} × {self.grid.rows} px "
              f"({ROOM_W:.1f} × {ROOM_H:.1f} m, res={RESOLUTION*100:.0f} cm)")
        print(f"  Arquivo de saída: {self.output_dir}/")
        print(f"\n  Teclas: [S] Salvar  [Q/Ctrl-C] Encerrar+Salvar  [R] Resetar")
        print("-" * 60)

        self.lidar.start()
        self._running = True

        # Aguarda primeiro scan
        print("  Aguardando primeiro scan do C1...")
        for _ in range(60):
            pts = self.lidar.get_last_scan_points()
            if pts and len(pts) > 50:
                break
            time.sleep(0.1)
        else:
            print("  ERRO: timeout aguardando scan do C1.")
            self.lidar.stop()
            return

        print(f"  ✓ Primeiro scan: {len(self.lidar.get_last_scan_points())} pontos.")
        print("  Guie o robô DEVAGAR por toda a sala agora...\n")

        # Thread de leitura de teclado (não-bloqueante)
        _start_keyboard_thread(self._save_request, self._quit_request)

        last_step  = 0.0
        last_print = 0.0

        try:
            while self._running and not self._quit_request.is_set():
                now = time.time()

                if now - last_step >= self.SLAM_INTERVAL_S:
                    self._slam_step()
                    last_step = now

                if self._save_request.is_set():
                    self._save_request.clear()
                    path = self.save_map()
                    print(f"  → Salvo em: {path}")

                if now - last_print >= 5.0:
                    self._print_status()
                    last_print = now

                time.sleep(0.05)

        except KeyboardInterrupt:
            pass

        print("\nEncerrando...")
        self._running = False
        self.lidar.stop()
        path = self.save_map()
        print(f"Mapa final salvo em: {path}")

    # ── Salvamento ────────────────────────────────────────────────────────

    def save_map(self, name: Optional[str] = None) -> str:
        """Salva PGM P5 + YAML compatíveis com lidar_pose_corrector.py."""
        if name is None:
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"sala_maker_c1_{ts}"

        os.makedirs(self.output_dir, exist_ok=True)
        base      = os.path.join(self.output_dir, name)
        pgm_path  = base + ".pgm"
        yaml_path = base + ".yaml"
        pgm_fname = os.path.basename(pgm_path)

        pgm = self.grid.to_pgm_array()
        h, w = pgm.shape

        # PGM P5 binário
        with open(pgm_path, "wb") as f:
            f.write(b"P5\n")
            f.write(f"{w} {h}\n".encode())
            f.write(b"255\n")
            f.write(pgm.tobytes())

        # YAML: origin=(0,0) → pixel (0,0) = mundo (0,0) = canto NW
        yaml_content = (
            f"image: {pgm_fname}\n"
            f"resolution: {RESOLUTION}\n"
            f"origin:\n"
            f"- {self.grid.origin_x}\n"
            f"- {self.grid.origin_y}\n"
            f"- 0.0\n"
            f"negate: 0\n"
            f"occupied_thresh: 0.65\n"
            f"free_thresh: 0.196\n"
        )
        with open(yaml_path, "w") as f:
            f.write(yaml_content)

        st    = self.grid.stats()
        total = st["total"]
        print(f"\n  PGM : {pgm_path}  ({w}×{h} px)")
        print(f"  YAML: {yaml_path}")
        print(f"  Occ={100*st['occ']/total:.1f}%  "
              f"Free={100*st['free']/total:.1f}%  "
              f"Unk={100*st['unk']/total:.1f}%")

        if st["occ"] / total < 0.05:
            print("  ⚠  < 5% ocupado — explore mais a sala antes de salvar.")

        print(f"\n  Para usar no scan matching, atualize src/core/config.py:")
        print(f"    SCAN_MATCH_PGM_PATH  = r\"{pgm_path}\"")
        print(f"    SCAN_MATCH_YAML_PATH = r\"{yaml_path}\"")

        return base

    def reset(self) -> None:
        """Reinicia o mapa do zero (mantém pose atual)."""
        self.grid        = OccupancyGrid(ROOM_W, ROOM_H, RESOLUTION)
        self._scan_count = 0
        self._last_score = 0.0
        print("  Mapa resetado.")


# ─────────────────────────────────────────────────────────────────────────────
# Leitura de teclado em thread separada (não-bloqueante, terminal Unix)
# ─────────────────────────────────────────────────────────────────────────────

def _start_keyboard_thread(save_ev: threading.Event,
                           quit_ev: threading.Event) -> None:
    """Lê teclas em background; S=salvar, Q=sair, R=resetar."""
    def _reader():
        fd = sys.stdin.fileno()
        try:
            old_settings = termios.tcgetattr(fd)
        except Exception:
            return  # stdin não é um terminal (pipe/redirect)
        try:
            tty.setcbreak(fd)
            while not quit_ev.is_set():
                try:
                    ch = sys.stdin.read(1).upper()
                    if ch == "S":
                        save_ev.set()
                    elif ch in ("Q", "\x03", "\x04"):
                        quit_ev.set()
                        break
                    elif ch == "R":
                        print("\n  [R] Resetar mapa? Pressione R novamente para confirmar.")
                        ch2 = sys.stdin.read(1).upper()
                        if ch2 == "R":
                            # sinaliza reset via save_ev com flag especial
                            # (simplificação: usa um arquivo temporário)
                            open("/tmp/_c1slam_reset", "w").close()
                except Exception:
                    break
        finally:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass

    t = threading.Thread(target=_reader, daemon=True, name="KeyReader")
    t.start()


# ─────────────────────────────────────────────────────────────────────────────
# Modo batch (sem stdin interativo — útil para testes no Pi sem teclado)
# ─────────────────────────────────────────────────────────────────────────────

def run_batch(mapper: "C1SLAMMapper", duration_s: float) -> None:
    """Coleta scans por `duration_s` segundos e salva automaticamente."""
    print(f"\nModo batch: {duration_s:.0f}s. Guie o robô pela sala agora!")
    mapper.lidar.start()

    print("  Aguardando primeiro scan...")
    for _ in range(60):
        if mapper.lidar.get_last_scan_points():
            break
        time.sleep(0.1)

    end_time   = time.time() + duration_s
    last_step  = 0.0
    last_print = 0.0

    try:
        while time.time() < end_time:
            now = time.time()
            if now - last_step >= mapper.SLAM_INTERVAL_S:
                mapper._slam_step()
                last_step = now
            if now - last_print >= 10.0:
                remaining = end_time - now
                mapper._print_status()
                print(f"    Tempo restante: {remaining:.0f}s")
                last_print = now
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass

    mapper.lidar.stop()
    mapper.save_map()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(
        description="C1 SLAM Mapper — mapeamento manual com RPLidar C1.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--port", default="/dev/ttyUSB0",
                   help="Porta serial do C1 (padrão: /dev/ttyUSB0)")
    p.add_argument("--init-x", type=float, default=0.30,
                   help="Posição X inicial do robô em metros (padrão: 0.30)")
    p.add_argument("--init-y", type=float, default=0.30,
                   help="Posição Y inicial do robô em metros (padrão: 0.30)")
    p.add_argument("--init-theta", type=float, default=270.0,
                   help="Ângulo inicial em graus (0=Leste, 270=Norte; padrão: 270)")
    p.add_argument("--output-dir", default=os.path.join(PROJECT_ROOT, "mapas", "c1"),
                   help="Diretório de saída para PGM + YAML")
    p.add_argument("--batch", action="store_true",
                   help="Modo batch: coleta por --duration segundos e salva")
    p.add_argument("--duration", type=float, default=180.0,
                   help="Duração em modo batch (segundos; padrão: 180)")
    p.add_argument("--room-w", type=float, default=ROOM_W,
                   help=f"Largura da sala em metros (padrão: {ROOM_W})")
    p.add_argument("--room-h", type=float, default=ROOM_H,
                   help=f"Altura da sala em metros (padrão: {ROOM_H})")
    args = p.parse_args()

    # Atualiza dimensões globais se fornecidas
    global ROOM_W, ROOM_H
    ROOM_W = args.room_w
    ROOM_H = args.room_h

    print(f"C1 SLAM Mapper")
    print(f"  Porta   : {args.port}")
    print(f"  Pose 0  : ({args.init_x:.2f}, {args.init_y:.2f}, {args.init_theta:.1f}°)")
    print(f"  Sala    : {ROOM_W:.2f} × {ROOM_H:.2f} m")
    print(f"  Saída   : {args.output_dir}")

    mapper = C1SLAMMapper(
        port=args.port,
        init_x=args.init_x,
        init_y=args.init_y,
        init_theta_deg=args.init_theta,
        output_dir=args.output_dir,
    )

    if args.batch:
        run_batch(mapper, args.duration)
    else:
        mapper.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
