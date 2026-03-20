"""
lidar_pose_corrector.py — Correção de pose via scan matching (Abordagem C).

Compara o scan atual do C1 (360°, metros reais) com o mapa PGM (grade de ocupância)
e calcula o deslocamento (dx, dy, dθ) que melhor alinha os pontos lidos ao mapa.

Algoritmo: busca em grade com correlação de ocupância (Occupancy Grid Matching).
  - Para cada candidato (dx, dy, dθ) em torno da pose atual, projeta os pontos
    do scan no mapa e conta quantos caem em células ocupadas (paredes).
  - O candidato com mais acertos é a correção de pose.
  - Vetorizado com numpy → eficiente no Raspberry Pi 4.

Uso:
    corrector = LidarPoseCorrector(pgm_path, yaml_path)
    corrector.start()

    # A cada ciclo de odometria em robot_navigator:
    corrector.update_pose(x, y, theta_deg)
    corrector.update_scan(scan_points)   # lista de (angle_deg, dist_m)

    # Periodicamente (a cada ~2 s), pegar e aplicar correção:
    correction = corrector.get_latest_correction()
    if correction:
        dx, dy, dtheta_deg = correction
        # aplica na pose estimada

    corrector.stop()

Sistema de coordenadas (igual ao robot_navigator):
    - X cresce para leste (direita na tela)
    - Y cresce para sul (baixo na tela / topo do PGM)
    - Ângulo 0° = leste, 270° = norte (padrão trigonométrico, Y invertido)
    - ROBOT_INITIAL_ANGLE = 270° → aponta para norte (topo do mapa)
"""

import logging
import math
import os
import threading
import time
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ─── Parâmetros padrão da busca ───────────────────────────────────────────────
DEFAULT_XY_RANGE_M       = 0.20   # busca ±20 cm em x e y
DEFAULT_XY_STEP_M        = 0.05   # passo de 5 cm (9 valores por eixo)
DEFAULT_THETA_RANGE_DEG  = 3.0    # busca ±3° em ângulo
DEFAULT_THETA_STEP_DEG   = 1.0    # passo de 1° (7 valores)
DEFAULT_INTERVAL_S       = 1.0    # intervalo entre correções (s) — reduzido após otimização
DEFAULT_MIN_POINTS       = 15     # mínimo de pontos válidos para corrigir
DEFAULT_MAX_RANGE_M      = 8.0    # ignora pontos > 8 m (artefatos de scan)
DEFAULT_MIN_RANGE_M      = 0.18   # ignora pontos < 18 cm (reflexo do corpo)
DEFAULT_MIN_SCORE           = 0.12   # score mínimo para aceitar correção (0–1)
DEFAULT_POSITION_MIN_SCORE  = 0.20   # score mínimo para incluir dx/dy na correção (abordagem híbrida)
DEFAULT_MAX_CORR_M          = 0.20   # descarta correção > 20 cm (outlier)
DEFAULT_MAX_CORR_DEG     = 3.0    # descarta correção > 3° (outlier)
DEFAULT_MAX_SCAN_PTS     = 60     # subamostrar scan para no máximo 60 pontos (velocidade)

# Ângulo frontal do sensor C1 (FRONT_CENTER_DEG do lidar_c1_reader)
DEFAULT_SENSOR_FRONT_DEG = 350.0


class LidarPoseCorrector:
    """
    Corretor de pose via scan matching C1 ↔ mapa PGM.

    Roda em thread própria e calcula correções periodicamente.
    Thread-safe: usa lock interno para acesso a scan/pose/correção.
    """

    def __init__(
        self,
        pgm_path: str,
        yaml_path: str,
        sensor_front_deg: float      = DEFAULT_SENSOR_FRONT_DEG,
        xy_range_m: float            = DEFAULT_XY_RANGE_M,
        xy_step_m: float             = DEFAULT_XY_STEP_M,
        theta_range_deg: float       = DEFAULT_THETA_RANGE_DEG,
        theta_step_deg: float        = DEFAULT_THETA_STEP_DEG,
        correction_interval_s: float = DEFAULT_INTERVAL_S,
        min_scan_points: int         = DEFAULT_MIN_POINTS,
        max_range_m: float           = DEFAULT_MAX_RANGE_M,
        min_range_m: float           = DEFAULT_MIN_RANGE_M,
        min_score: float             = DEFAULT_MIN_SCORE,
        position_min_score: float    = DEFAULT_POSITION_MIN_SCORE,
        max_correction_m: float      = DEFAULT_MAX_CORR_M,
        max_correction_deg: float    = DEFAULT_MAX_CORR_DEG,
        max_scan_pts: int            = DEFAULT_MAX_SCAN_PTS,
    ):
        self.pgm_path              = pgm_path
        self.yaml_path             = yaml_path
        self.sensor_front_deg      = sensor_front_deg
        self.xy_range_m            = xy_range_m
        self.xy_step_m             = xy_step_m
        self.theta_range_deg       = theta_range_deg
        self.theta_step_deg        = theta_step_deg
        self.correction_interval_s = correction_interval_s
        self.min_scan_points       = min_scan_points
        self.max_range_m           = max_range_m
        self.min_range_m           = min_range_m
        self.min_score             = min_score
        self.position_min_score    = position_min_score
        self.max_correction_m      = max_correction_m
        self.max_correction_deg    = max_correction_deg
        self.max_scan_pts          = max_scan_pts

        # ── Mapa (carregado em _load_map) ────────────────────────────────────
        self._grid: Optional[np.ndarray] = None   # bool, True = ocupado
        self._resolution: float  = 0.05
        self._origin: Tuple[float, float] = (0.0, 0.0)
        self._map_w: int = 0
        self._map_h: int = 0
        self._map_loaded: bool = False

        # ── Estado compartilhado entre threads ───────────────────────────────
        self._lock = threading.Lock()
        self._current_scan: List[Tuple[float, float]] = []    # (angle_deg, dist_m)
        self._current_pose: Tuple[float, float, float] = (0.0, 0.0, 270.0)
        self._latest_correction: Optional[Tuple[float, float, float]] = None
        self._latest_score: float = 0.0
        self._correction_count: int = 0

        # ── Thread ──────────────────────────────────────────────────────────
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running: bool = False

        # Carrega mapa ao instanciar
        self._load_map()

    # ─────────────────────────────────────────────────────────────────────────
    # API pública
    # ─────────────────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Inicia a thread de correção periódica."""
        if self._running:
            return
        if not self._map_loaded:
            logger.warning("PoseCorrector: mapa não carregado — não iniciando thread.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._correction_loop,
            daemon=True,
            name="PoseCorrector",
        )
        self._thread.start()
        self._running = True
        logger.info(
            "PoseCorrector iniciado — mapa %dx%d px, res=%.5f m/px, "
            "busca ±%.0f cm / ±%.0f°, intervalo=%.1f s.",
            self._map_w, self._map_h, self._resolution,
            self.xy_range_m * 100, self.theta_range_deg,
            self.correction_interval_s,
        )

    def stop(self) -> None:
        """Para a thread de correção."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._running = False
        logger.info("PoseCorrector parado. Total de correções: %d.", self._correction_count)

    def update_pose(self, x: float, y: float, theta_deg: float) -> None:
        """
        Atualiza a pose estimada atual.
        Chamado pelo robot_navigator a cada ciclo de odometria.
        """
        with self._lock:
            self._current_pose = (x, y, theta_deg)

    def update_scan(self, scan_points: List[Tuple[float, float]]) -> None:
        """
        Atualiza o scan atual do C1.

        Args:
            scan_points: lista de (angle_deg, distance_m) em coordenadas do sensor.
                         Ângulo 0° = frente do sensor (sensor front = FRONT_CENTER_DEG).
                         Usar get_last_scan_points() do LidarC1Reader.
        """
        with self._lock:
            self._current_scan = scan_points

    def get_latest_correction(self) -> Optional[Tuple[float, float, float]]:
        """
        Retorna a última correção calculada (dx, dy, dtheta_deg) e limpa o buffer.

        Retorna None se nenhuma correção disponível desde a última chamada.
        O chamador deve verificar se os valores estão dentro de limites razoáveis
        antes de aplicar (SCAN_MATCH_MAX_CORRECTION_M / _DEG no config.py).
        """
        with self._lock:
            corr = self._latest_correction
            self._latest_correction = None
            return corr

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def map_loaded(self) -> bool:
        return self._map_loaded

    @property
    def correction_count(self) -> int:
        with self._lock:
            return self._correction_count

    # ─────────────────────────────────────────────────────────────────────────
    # Carregamento do mapa
    # ─────────────────────────────────────────────────────────────────────────

    def _load_map(self) -> bool:
        """Carrega PGM + YAML como grade de ocupância numpy (bool)."""
        try:
            import yaml as pyyaml
        except ImportError:
            logger.error("PoseCorrector: PyYAML não instalado. Execute: pip install pyyaml")
            return False

        pgm_file  = Path(self.pgm_path)
        yaml_file = Path(self.yaml_path)

        if not pgm_file.exists():
            logger.error("PoseCorrector: PGM não encontrado: %s", self.pgm_path)
            return False
        if not yaml_file.exists():
            logger.error("PoseCorrector: YAML não encontrado: %s", self.yaml_path)
            return False

        try:
            # ── Lê metadados do YAML ─────────────────────────────────────────
            with open(yaml_file, "r") as f:
                meta = pyyaml.safe_load(f)

            self._resolution = float(meta.get("resolution", 0.05))
            origin = meta.get("origin", [0.0, 0.0, 0.0])
            self._origin = (float(origin[0]), float(origin[1]))
            occupied_thresh = float(meta.get("occupied_thresh", 0.65))
            negate = int(meta.get("negate", 0))

            # ── Lê pixels do PGM binário (formato P5) ────────────────────────
            with open(pgm_file, "rb") as f:
                header_lines: list = []
                while len(header_lines) < 3:
                    raw_line = f.readline()
                    line = raw_line.decode("ascii", errors="ignore").strip()
                    if line and not line.startswith("#"):
                        header_lines.append(line)

                if header_lines[0] != "P5":
                    logger.error(
                        "PoseCorrector: formato PGM não suportado (%s). Esperado P5.",
                        header_lines[0],
                    )
                    return False

                w, h = map(int, header_lines[1].split())
                max_val = int(header_lines[2])
                raw = np.frombuffer(f.read(w * h), dtype=np.uint8).reshape((h, w))

            # ── Converte para grade de ocupância ────────────────────────────
            # Normaliza [0, 1]: 0=preto=ocupado (sem negate)
            normalized = raw.astype(np.float32) / float(max_val)
            if negate:
                normalized = 1.0 - normalized

            # Limiar ROS-padrão: valor < (1 - occupied_thresh) → ocupado
            # Sem negate: pixel 0 (preto) → normalized 0 → 0 < 0.35 → True (ocupado) ✓
            self._grid = normalized < (1.0 - occupied_thresh)
            self._map_w = w
            self._map_h = h
            self._map_loaded = True

            occupied_pct = 100.0 * self._grid.sum() / self._grid.size
            logger.info(
                "PoseCorrector: mapa carregado %dx%d px, res=%.5f m/px, "
                "origem=(%.2f, %.2f), ocupado=%.1f%%.",
                w, h, self._resolution,
                self._origin[0], self._origin[1],
                occupied_pct,
            )
            return True

        except Exception as exc:
            logger.error("PoseCorrector: erro ao carregar mapa: %s", exc, exc_info=True)
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # Scan matching
    # ─────────────────────────────────────────────────────────────────────────

    def _compute_correction(
        self,
        scan: List[Tuple[float, float]],
        pose: Tuple[float, float, float],
    ) -> Optional[Tuple[float, float, float, float]]:
        """
        Busca em grade: encontra (dx, dy, dθ) que maximiza acertos do scan no mapa.

        Retorna (dx_m, dy_m, dtheta_deg, score) ou None se scan insuficiente.
        Score = fração dos pontos projetados que caem em células ocupadas (0–1).
        """
        if self._grid is None or not self._map_loaded:
            return None

        # ── Prepara pontos do scan ───────────────────────────────────────────
        if len(scan) < self.min_scan_points:
            return None

        angles_deg = np.array([p[0] for p in scan], dtype=np.float32)
        dists_m    = np.array([p[1] for p in scan], dtype=np.float32)

        # Filtra por distância válida
        mask = (dists_m >= self.min_range_m) & (dists_m <= self.max_range_m)
        if mask.sum() < self.min_scan_points:
            return None

        angles_rad  = np.radians(angles_deg[mask])
        dists_valid = dists_m[mask]

        # Subamostrar para acelerar no Pi 4 (ex: 360 pts → 60 pts)
        n_pts = len(dists_valid)
        if n_pts > self.max_scan_pts:
            step = n_pts // self.max_scan_pts
            angles_rad  = angles_rad[::step]
            dists_valid = dists_valid[::step]

        # ── Grade de candidatos ──────────────────────────────────────────────
        # float64 evita erros de precisão nos limites (ex: -0.20 armazenado como -0.2000003 em float32)
        xy_offsets        = np.arange(-self.xy_range_m,
                                       self.xy_range_m + 1e-6,
                                       self.xy_step_m)
        theta_offsets_deg = np.arange(-self.theta_range_deg,
                                       self.theta_range_deg + 1e-6,
                                       self.theta_step_deg)

        x0, y0, theta0_deg = pose
        sensor_front_rad   = math.radians(self.sensor_front_deg)

        # Meshgrid de offsets dx/dy: shape (n_dx, n_dy)
        dx_grid, dy_grid = np.meshgrid(xy_offsets, xy_offsets, indexing='ij')

        best_score  = -1.0
        best_dx     = 0.0
        best_dy     = 0.0
        best_dtheta = 0.0

        for dtheta_deg in theta_offsets_deg:
            theta_rad    = math.radians(theta0_deg + dtheta_deg)
            world_angles = theta_rad + (angles_rad - sensor_front_rad)

            # Componentes cartesianas dos pontos (relativas ao robô): shape (n_pts,)
            base_dx = dists_valid * np.cos(world_angles)
            base_dy = dists_valid * np.sin(world_angles)

            # Posições world para todos os candidatos (dx, dy) de uma vez
            # robot_x/y: (n_dx, n_dy); base_dx/dy: (n_pts,) → (n_pts,1,1)
            robot_x = x0 + dx_grid            # (n_dx, n_dy)
            robot_y = y0 + dy_grid            # (n_dx, n_dy)
            wx = robot_x[np.newaxis, :, :] + base_dx[:, np.newaxis, np.newaxis]  # (n_pts, n_dx, n_dy)
            wy = robot_y[np.newaxis, :, :] + base_dy[:, np.newaxis, np.newaxis]  # (n_pts, n_dx, n_dy)

            # Pixels no mapa
            px_arr = ((wx - self._origin[0]) / self._resolution).astype(np.int32)
            py_arr = ((wy - self._origin[1]) / self._resolution).astype(np.int32)

            # Máscara de pixels dentro dos limites do mapa
            valid = (
                (px_arr >= 0) & (px_arr < self._map_w) &
                (py_arr >= 0) & (py_arr < self._map_h)
            )  # (n_pts, n_dx, n_dy)

            # Lookup na grade; pixels inválidos mapeados para (0,0) com máscara
            px_safe = np.where(valid, px_arr, 0)
            py_safe = np.where(valid, py_arr, 0)
            grid_hits = self._grid[py_safe, px_safe]          # (n_pts, n_dx, n_dy)
            grid_hits = np.where(valid, grid_hits, False)

            hits_per_cand   = grid_hits.sum(axis=0).astype(np.float32)  # (n_dx, n_dy)
            valid_per_cand  = valid.sum(axis=0).astype(np.float32)       # (n_dx, n_dy)

            with np.errstate(invalid='ignore', divide='ignore'):
                scores = np.where(valid_per_cand > 0,
                                  hits_per_cand / valid_per_cand, 0.0)

            best_idx = np.unravel_index(scores.argmax(), scores.shape)
            score_for_theta = float(scores[best_idx])

            if score_for_theta > best_score:
                best_score  = score_for_theta
                best_dx     = float(dx_grid[best_idx])
                best_dy     = float(dy_grid[best_idx])
                best_dtheta = float(dtheta_deg)

        return best_dx, best_dy, best_dtheta, best_score

    # ─────────────────────────────────────────────────────────────────────────
    # Thread de correção
    # ─────────────────────────────────────────────────────────────────────────

    def _correction_loop(self) -> None:
        """Loop principal da thread — calcula correção periodicamente."""
        logger.info("PoseCorrector: thread iniciada.")

        # Aquecimento: as primeiras 2 correções são descartadas sem serem publicadas.
        # Motivo: o robô acabou de iniciar o movimento e o scan ainda pode estar
        # capturando a posição de repouso ou o scan matching encontra falso ótimo
        # na posição inicial (ex: dx=-0.300 com score baixo corrompe o CTE inteiro).
        WARMUP_SKIP = 2
        warmup_done = 0

        while not self._stop_event.is_set():
            t_start = time.time()

            try:
                # Copia estado atual de forma thread-safe
                with self._lock:
                    scan = list(self._current_scan)
                    pose = self._current_pose

                if len(scan) >= self.min_scan_points:
                    result = self._compute_correction(scan, pose)

                    if result is not None:
                        dx, dy, dtheta, score = result
                        elapsed_ms = (time.time() - t_start) * 1000

                        # Filtra outliers antes de publicar
                        if (
                            score >= self.min_score
                            and abs(dx)     <= self.max_correction_m
                            and abs(dy)     <= self.max_correction_m
                            and abs(dtheta) <= self.max_correction_deg
                        ):
                            if warmup_done < WARMUP_SKIP:
                                warmup_done += 1
                                logger.info(
                                    "PoseCorrector: warmup %d/%d — descartando "
                                    "dx=%+.3f dy=%+.3f dθ=%+.1f° score=%.2f (%.0f ms)",
                                    warmup_done, WARMUP_SKIP,
                                    dx, dy, dtheta, score, elapsed_ms,
                                )
                            else:
                                # Abordagem híbrida: posição só quando score alto o suficiente.
                                # score >= position_min_score → correção completa (dx+dy+dθ)
                                # score <  position_min_score → só ângulo (dx=dy=0, posição=odometria)
                                use_position = (score >= self.position_min_score)
                                pub_dx = dx  if use_position else 0.0
                                pub_dy = dy  if use_position else 0.0

                                with self._lock:
                                    self._latest_correction = (pub_dx, pub_dy, dtheta)
                                    self._latest_score      = score
                                    self._correction_count += 1

                                if use_position:
                                    logger.info(
                                        "PoseCorrector #%d [FULL]: dx=%+.3f m  dy=%+.3f m  dθ=%+.1f°  "
                                        "score=%.2f  (%.0f ms)",
                                        self._correction_count,
                                        dx, dy, dtheta, score, elapsed_ms,
                                    )
                                else:
                                    logger.info(
                                        "PoseCorrector #%d [θ-only]: dθ=%+.1f°  score=%.2f  "
                                        "(%.0f ms) — dx/dy ignorados (score<%.2f)",
                                        self._correction_count,
                                        dtheta, score, elapsed_ms, self.position_min_score,
                                    )
                        else:
                            logger.info(
                                "PoseCorrector: rejeitado dx=%+.3f dy=%+.3f dθ=%+.1f° "
                                "score=%.2f (%.0f ms) — fora dos limites ou score baixo.",
                                dx, dy, dtheta, score, elapsed_ms,
                            )
                else:
                    logger.info(
                        "PoseCorrector: aguardando scan (%d pts, min=%d).",
                        len(scan), self.min_scan_points,
                    )

            except Exception as exc:
                logger.error(
                    "PoseCorrector: EXCEÇÃO na thread de correção: %s",
                    exc, exc_info=True,
                )

            # Aguarda próximo ciclo
            elapsed = time.time() - t_start
            wait    = max(0.1, self.correction_interval_s - elapsed)
            self._stop_event.wait(wait)

        logger.info("PoseCorrector: thread encerrada.")
