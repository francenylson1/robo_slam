import sys
import os
import logging
import time
import math
from typing import List, Tuple, Optional

from PyQt5.QtCore import QObject, pyqtSignal

from .slamtec_manager import SlamtecManager
from .robot_motor_controller import RobotMotorController
from .config import *
from src.core.environment import GPIO_AVAILABLE, is_raspberry_pi
from .path_finder import PathFinder

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = logging.getLogger(__name__)


class RobotNavigator(QObject):

    position_updated = pyqtSignal(float, float, float)
    navigation_status_updated = pyqtSignal(dict)
    navigation_completed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.slamtec = SlamtecManager()
        self.motors = RobotMotorController()

        self.current_position = ROBOT_INITIAL_POSITION
        self.current_angle = ROBOT_INITIAL_ANGLE
        self.current_target = None
        self.navigation_active = False
        self.is_returning_to_base = False
        self.base_position = ROBOT_INITIAL_POSITION
        self.is_adjusting_final_angle = False
        self.navigation_state = "IDLE"
        self.speed_multiplier = 1.0

        self.path_finder = PathFinder(
            width=int(MAP_WIDTH / MAP_GRID_SIZE),
            height=int(MAP_HEIGHT / MAP_GRID_SIZE),
            grid_size=MAP_GRID_SIZE,
            map_origin=(0.0, 0.0)
        )

        self.forbidden_areas = []
        self.is_autonomous = False
        self.current_path = []
        self.current_path_index = 0

        self.path_smoothing_enabled = True
        self.obstacle_avoidance_enabled = True
        self.emergency_stop_active = False
        self.last_position_update = time.time()
        self.navigation_start_time = None
        self.estimated_completion_time = None

        self.precise_rotation_active = False

        self.arrival_pause_time = ARRIVAL_PAUSE_TIME
        self.arrival_time = None
        self.is_paused_at_destination = False

        self.is_returning_to_initial_angle = False

        self.should_return_to_base = True

        self.final_approach_start_time = None
        self.final_approach_timeout = 10.0

        # Watchdog de navegação: evita loop infinito nos estados NAVIGATING e RETURNING
        self._nav_start_time: Optional[float] = None
        self._nav_max_duration = NAVIGATION_MAX_DURATION_S
        self._return_start_time: Optional[float] = None
        self._last_progress_pos = None     # posição na última verificação de progresso
        self._last_progress_time: Optional[float] = None
        self._progress_check_interval = 5.0  # verifica progresso a cada 5 s
        self._stuck_threshold = 0.05       # considera preso se moveu < 5 cm em 5 s
        self._cancelled_by_obstacle = False  # True quando watchdog cancela por obstáculo C1

        # Timeout para estado ORIENTING_TO_TARGET (evita giro infinito por BNO)
        self._orient_start_time: Optional[float] = None

        # C1 bloqueou o caminho (watchdog timeout) — UI exibe mensagem específica
        self._cancelled_by_obstacle = False

        self.use_direct_navigation = True

        # BNO08x: filtro complementar (USE_BNO_IN_NAVIGATION no config)
        self._get_bno_yaw = None
        self._bno_yaw_ref = None
        self._bno_yaw_offset = None
        self._bno_prev_yaw = None
        if is_raspberry_pi() and USE_BNO_IN_NAVIGATION:
            try:
                from tools.bno08x_init import init_bno
                _bno, self._get_bno_yaw = init_bno(do_reset_cycle=False, verbose=False)
                if self._get_bno_yaw is not None:
                    mode = "correção de rumo + fusão na pose" if USE_BNO_POSE_FUSION else "só correção de rumo (pose=odometria)"
                    logger.info("BNO08x integrado ao navegador (%s).", mode)
                else:
                    self._get_bno_yaw = None
            except Exception as e:
                logger.warning("BNO08x não disponível no navegador: %s", e)
                self._get_bno_yaw = None

        # ── Scan matching — Abordagem C (LidarPoseCorrector) ─────────────────
        self._pose_corrector = None
        if USE_SCAN_MATCHING:
            try:
                from .lidar_pose_corrector import LidarPoseCorrector
                self._pose_corrector = LidarPoseCorrector(
                    pgm_path              = SCAN_MATCH_PGM_PATH,
                    yaml_path             = SCAN_MATCH_YAML_PATH,
                    xy_range_m            = SCAN_MATCH_XY_RANGE_M,
                    xy_step_m             = SCAN_MATCH_XY_STEP_M,
                    theta_range_deg       = SCAN_MATCH_THETA_RANGE_DEG,
                    theta_step_deg        = SCAN_MATCH_THETA_STEP_DEG,
                    correction_interval_s = SCAN_MATCH_INTERVAL_S,
                    min_score             = SCAN_MATCH_MIN_SCORE,
                    max_correction_m      = SCAN_MATCH_MAX_CORR_M,
                    max_correction_deg    = SCAN_MATCH_MAX_CORR_DEG,
                    max_scan_pts          = SCAN_MATCH_MAX_SCAN_PTS,
                )
                if self._pose_corrector.map_loaded:
                    logger.info("PoseCorrector (scan matching) carregado — será iniciado na navegação.")
                else:
                    logger.warning("PoseCorrector: mapa não carregado — scan matching desativado.")
                    self._pose_corrector = None
            except Exception as exc:
                logger.warning("PoseCorrector não disponível: %s", exc)
                self._pose_corrector = None

        logger.info(
            "Navegador inicializado – posição=%s, ângulo=%s°, base=%s",
            self.current_position, self.current_angle, self.base_position
        )

    def reset_to_initial_state(self, preserve_position: bool = False):
        """Reseta o robô para o estado inicial."""
        preserved_forbidden_areas = self.forbidden_areas.copy()
        preserved_base_position = self.base_position

        # Re-anclar BNO ao referencial do mapa na próxima atualização de pose
        self._bno_yaw_offset = None
        self._bno_yaw_ref = None
        self._bno_prev_yaw = None

        self.navigation_active = False
        self.current_target = None
        self.path = []
        self.path_index = 0
        self.is_adjusting_final_angle = False
        self.is_returning_to_base = False
        self.navigation_state = "IDLE"
        self.progress = 0.0
        self.start_time = None
        self.estimated_time_remaining = 0.0
        self.is_paused_at_destination = False

        if hasattr(self, 'original_destination'):
            delattr(self, 'original_destination')
        self.final_approach_start_time = None

        if hasattr(self, '_orient_stability_counter'):
            self._orient_stability_counter = 0
        self._orient_start_time = None
        self._fa_entry_distance = None
        self._nav_start_time = None
        self._return_start_time = None

        self.forbidden_areas = preserved_forbidden_areas
        self.path_finder.set_forbidden_areas(preserved_forbidden_areas)
        self.base_position = preserved_base_position

        self.motors.stop()

    def set_pose(self, x: float, y: float, angle_deg: float):
        """Define posição e ângulo do robô (ex.: ao carregar mapa PGM)."""
        self.current_position = (float(x), float(y))
        self.current_angle = self._normalize_angle_deg(float(angle_deg))
        self._bno_yaw_offset = None
        self._bno_yaw_ref = None
        self._bno_prev_yaw = None

    def set_speed_multiplier(self, multiplier: float):
        """Define o multiplicador de velocidade (1.0 a 1.3)."""
        if 1.0 <= multiplier <= 1.3:
            self.speed_multiplier = multiplier
            logger.info("Velocidade ajustada para %.0f%%", self.speed_multiplier * 100)
        else:
            logger.warning("Multiplicador de velocidade inválido: %.2f (deve ser entre 1.0 e 1.3).", multiplier)

    def set_path(self, path: List[Tuple[float, float]]):
        """Define um novo caminho para o robô seguir."""
        self.current_path = self._smooth_path(path) if self.path_smoothing_enabled else path
        self.current_path_index = 0
        logger.debug("Caminho definido com %d pontos", len(self.current_path))

    def _smooth_path(self, path: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Suaviza o caminho com média ponderada dos pontos vizinhos."""
        if len(path) < 3:
            return path

        smoothed_path = [path[0]]
        for i in range(1, len(path) - 1):
            prev_point = path[i - 1]
            current_point = path[i]
            next_point = path[i + 1]
            smoothed_x = (prev_point[0] + 2 * current_point[0] + next_point[0]) / 4
            smoothed_y = (prev_point[1] + 2 * current_point[1] + next_point[1]) / 4
            smoothed_path.append((smoothed_x, smoothed_y))
        smoothed_path.append(path[-1])
        return smoothed_path

    def update(self):
        """Atualiza o estado do robô usando uma máquina de estados."""
        self._update_pose_with_odometry()

        if not self.navigation_active:
            return

        if self.navigation_state == "IDLE":
            return

        elif self.navigation_state == "ORIENTING_TO_TARGET":
            self._orient_towards_target()

        elif self.navigation_state == "NAVIGATING_TO_DESTINATION":
            self._handle_navigation_to_destination()

        elif self.navigation_state == "FINAL_APPROACH_DESTINATION":
            if self._stable_final_approach(self.original_destination):
                self._transition_to_paused_at_destination()

        elif self.navigation_state == "PAUSED_AT_DESTINATION":
            self._handle_pause_at_destination()

        elif self.navigation_state == "RETURNING_TO_BASE":
            self._handle_return_to_base()

        elif self.navigation_state == "FINAL_APPROACH_BASE":
            base_target = self.base_position if self.use_direct_navigation else (self.path[-1] if self.path else self.base_position)
            if self._stable_final_approach(base_target):
                self._start_final_angle_adjustment()

        elif self.navigation_state == "ADJUSTING_FINAL_ANGLE":
            self._adjust_final_angle()

        elif self.navigation_state == "COMPLETED":
            if self.navigation_active:
                logger.warning("Estado COMPLETED mas navigation_active=True; forçando finalização.")
                self._finalize_navigation()

        if len(self.path) > 1:
            self.progress = self.path_index / (len(self.path) - 1)
        else:
            self.progress = 0.0

    def _finalize_navigation(self):
        """Finaliza completamente a navegação."""
        self.motors.stop()
        self.navigation_active = False
        self.is_adjusting_final_angle = False
        self.navigation_state = "COMPLETED"
        self.current_target = None
        self.path = []
        self.path_index = 0
        if hasattr(self, '_orient_stability_counter'):
            self._orient_stability_counter = 0
        # Para scan matching ao terminar a navegação
        if self._pose_corrector is not None and self._pose_corrector.is_running:
            self._pose_corrector.stop()
        logger.info("Navegação finalizada.")

    def _cancel_navigation_blocked_by_obstacle(self):
        """Cancela navegação quando obstáculo C1 bloqueou o caminho (watchdog timeout)."""
        self._cancelled_by_obstacle = True
        self._finalize_navigation()

    def _calculate_and_execute_return_angle(self):
        """
        Calcula o ângulo para retornar à base e inicia o retorno.
        Só executa se should_return_to_base for True.
        """
        if not self.should_return_to_base:
            logger.info("Retorno à base não solicitado — finalizando no destino.")
            self._finalize_navigation()
            return

        has_forbidden_areas = bool(self.forbidden_areas)

        if has_forbidden_areas:
            if len(self.path_finder.obstacle_grid) == 0:
                self.path_finder.set_forbidden_areas(self.forbidden_areas)

            path_to_base = self.path_finder.find_path(self.current_position, self.base_position)

            if not path_to_base or len(path_to_base) < 2:
                logger.error(
                    "Sem caminho de retorno seguro (pos=%s, base=%s). Abortando.",
                    self.current_position, self.base_position
                )
                self._finalize_navigation()
                return

            if len(path_to_base) == 2:
                if self._check_path_intersects_forbidden_areas(path_to_base[0], path_to_base[1]):
                    logger.error("PathFinder retornou caminho direto que passa por área proibida. Abortando.")
                    self._finalize_navigation()
                    return
            else:
                for i in range(len(path_to_base) - 1):
                    if self._check_path_intersects_forbidden_areas(path_to_base[i], path_to_base[i + 1]):
                        logger.error("Segmento %d do retorno passa por área proibida. Abortando.", i)
                        self._finalize_navigation()
                        return

            logger.info("Caminho de retorno com %d waypoints calculado.", len(path_to_base))

        elif self.use_direct_navigation:
            logger.info("Retorno direto à base (sem áreas proibidas).")
            self._initialize_bno_offset()
            self._return_start_time = time.time()
            self.path = [self.current_position, self.base_position]
            self.path_index = 0
            self.current_target = self.base_position
            self.is_returning_to_base = True

            dx = self.base_position[0] - self.current_position[0]
            dy = self.base_position[1] - self.current_position[1]
            target_angle = math.degrees(math.atan2(dy, dx))
            if target_angle < 0:
                target_angle += 360
            current_angle_normalized = self.current_angle if self.current_angle >= 0 else self.current_angle + 360
            angle_error = (target_angle - current_angle_normalized + 180) % 360 - 180

            self.navigation_state = "RETURNING_TO_BASE" if abs(angle_error) < 10.0 else "ORIENTING_TO_TARGET"
            return

        else:
            path_to_base = self.path_finder.find_path(self.current_position, self.base_position)
            if not path_to_base or len(path_to_base) < 2:
                logger.warning("PathFinder sem caminho de retorno; tentando direto.")
                path_to_base = [self.current_position, self.base_position]
            logger.info("Retorno via PathFinder: %d waypoints.", len(path_to_base))

        self._initialize_bno_offset()
        self._return_start_time = time.time()
        if len(path_to_base) > 0:
            path_to_base[0] = self.current_position
        if len(path_to_base) > 0:
            path_to_base[-1] = self.base_position

        self.path = path_to_base
        self.is_returning_to_base = True

        if len(self.path) > 1:
            self.path_index = 1
            first_waypoint = self.path[1]
        else:
            self.path_index = 0
            first_waypoint = self.base_position

        self.current_target = first_waypoint
        self.navigation_status_updated.emit(self.get_navigation_status())

        dx = first_waypoint[0] - self.current_position[0]
        dy = first_waypoint[1] - self.current_position[1]
        target_angle = math.degrees(math.atan2(dy, dx))
        if target_angle < 0:
            target_angle += 360
        current_angle_normalized = self.current_angle if self.current_angle >= 0 else self.current_angle + 360
        angle_error = (target_angle - current_angle_normalized + 180) % 360 - 180

        self.navigation_state = "RETURNING_TO_BASE" if abs(angle_error) < 20.0 else "ORIENTING_TO_TARGET"

    def _start_return_navigation(self):
        """Inicia a navegação de retorno direto à base."""
        self.path = [self.current_position, self.base_position]
        self.path_index = 0
        self.current_target = self.path[1]
        self.navigation_state = "RETURNING_TO_BASE"
        self.is_returning_to_base = True

    def _start_final_angle_adjustment(self):
        """Inicia o ajuste do ângulo final."""
        self.motors.stop()
        self.navigation_state = "ADJUSTING_FINAL_ANGLE"
        self.is_adjusting_final_angle = True
        self.current_target = None
        self.path_index = len(self.path)
        self.final_angle_adjustment_start_time = time.time()
        self._adjust_final_angle()

    def get_current_path(self) -> List[Tuple[float, float]]:
        """Retorna o caminho de navegação atual."""
        return self.path

    def set_autonomous_mode(self, autonomous):
        """Alterna entre modo autônomo e manual."""
        self.is_autonomous = autonomous
        if not autonomous:
            self.motors.stop()

    def set_forbidden_areas(self, areas: List[List[Tuple[float, float]]]):
        """Define as áreas proibidas para o navegador."""
        self.forbidden_areas = areas
        self.path_finder.set_forbidden_areas(areas)
        logger.debug("%d áreas proibidas configuradas no navegador.", len(areas))

    def navigate_to_and_return(self, destination: Tuple[float, float], should_return_to_base: bool = True) -> None:
        """
        Navega até o destino e opcionalmente retorna à base.
        Sempre usa PathFinder quando há áreas proibidas configuradas.
        """
        logger.info(
            "Iniciando navegação para %s (retorno=%s, modo=%s)",
            destination, should_return_to_base,
            "direto" if self.use_direct_navigation else "pathfinding"
        )

        self.reset_to_initial_state(preserve_position=True)
        self._cancelled_by_obstacle = False  # Reset ao iniciar nova navegação

        # Inicia scan matching se disponível
        if self._pose_corrector is not None and not self._pose_corrector.is_running:
            self._pose_corrector.start()

        self.navigation_active = True
        self.start_time = time.time()
        self.is_returning_to_base = False
        self.should_return_to_base = should_return_to_base
        self.final_approach_start_time = None
        self._navigation_had_return_to_base = should_return_to_base

        has_forbidden_areas = bool(self.forbidden_areas)

        if has_forbidden_areas:
            if len(self.path_finder.obstacle_grid) == 0:
                self.path_finder.set_forbidden_areas(self.forbidden_areas)

            path_to_destination = self.path_finder.find_path(self.current_position, destination)

            if not path_to_destination or len(path_to_destination) < 2:
                logger.error(
                    "PathFinder sem caminho válido para %s. Possíveis áreas proibidas bloqueando.",
                    destination
                )
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(None, "Erro de Navegação",
                    f"Não foi possível encontrar um caminho seguro até o destino.\n\n"
                    f"Possíveis causas:\n"
                    f"- Áreas proibidas bloqueando completamente o caminho\n"
                    f"- Destino inacessível\n\n"
                    f"Verifique as áreas proibidas e tente novamente.")
                self.navigation_active = False
                self.navigation_state = "IDLE"
                return

            if len(path_to_destination) == 2:
                if self._check_path_intersects_forbidden_areas(path_to_destination[0], path_to_destination[1]):
                    logger.error("Caminho direto retornado pelo PathFinder passa por área proibida. Abortando.")
                    self.navigation_active = False
                    return
            else:
                for i in range(len(path_to_destination) - 1):
                    if self._check_path_intersects_forbidden_areas(path_to_destination[i], path_to_destination[i + 1]):
                        logger.error("Segmento %d do caminho passa por área proibida. Abortando.", i)
                        self.navigation_active = False
                        return

        elif self.use_direct_navigation:
            self._navigate_direct_simple(destination)
            return

        else:
            path_to_destination = self.path_finder.find_path(self.current_position, destination)
            if not path_to_destination or len(path_to_destination) < 2:
                logger.error("PathFinder sem caminho para %s.", destination)
                self.navigation_active = False
                self.navigation_state = "IDLE"
                return

        self._setup_navigation_path(path_to_destination, destination)

    def _check_path_intersects_forbidden_areas(self, start: Tuple[float, float], end: Tuple[float, float]) -> bool:
        """Verifica se o segmento direto entre dois pontos passa por áreas proibidas."""
        if not self.forbidden_areas:
            return False
        if len(self.path_finder.obstacle_grid) == 0:
            self.path_finder.set_forbidden_areas(self.forbidden_areas)
        return self.path_finder._line_intersects_obstacles(start, end)

    def _navigate_direct_simple(self, destination: Tuple[float, float]) -> None:
        """
        Navegação direta simples.
        Usa PathFinder se houver áreas proibidas; caso contrário vai direto ao destino.
        """
        has_forbidden_areas = bool(self.forbidden_areas)

        if has_forbidden_areas:
            if len(self.path_finder.obstacle_grid) == 0:
                self.path_finder.set_forbidden_areas(self.forbidden_areas)

            path_to_destination = self.path_finder.find_path(self.current_position, destination)

            if not path_to_destination or len(path_to_destination) < 2:
                logger.error("Sem caminho seguro para %s com áreas proibidas. Abortando.", destination)
                self.navigation_active = False
                self.navigation_state = "IDLE"
                return

            if len(path_to_destination) == 2:
                if self._check_path_intersects_forbidden_areas(path_to_destination[0], path_to_destination[1]):
                    logger.error("PathFinder retornou caminho direto com área proibida. Abortando.")
                    self.navigation_active = False
                    return
            else:
                for i in range(len(path_to_destination) - 1):
                    if self._check_path_intersects_forbidden_areas(path_to_destination[i], path_to_destination[i + 1]):
                        logger.error("Segmento %d do caminho (direto) passa por área proibida. Abortando.", i)
                        self.navigation_active = False
                        return

            if len(path_to_destination) > 0:
                path_to_destination[0] = self.current_position
            if len(path_to_destination) > 0:
                path_to_destination[-1] = destination

            self._setup_navigation_path(path_to_destination, destination)
            return

        # Sem áreas proibidas: navegação direta
        current_angle_normalized = self.current_angle if self.current_angle >= 0 else self.current_angle + 360
        self.original_destination = destination
        self.current_target = destination
        self.path = [self.current_position, destination]
        # path_index = 1: "viemos de path[0] e vamos para path[1]"
        # Necessário para o CTE calcular desvio lateral desde o início.
        self.path_index = 1

        dx = destination[0] - self.current_position[0]
        dy = destination[1] - self.current_position[1]
        target_angle = math.degrees(math.atan2(dy, dx))
        if target_angle < 0:
            target_angle += 360
        angle_error = (target_angle - current_angle_normalized + 180) % 360 - 180

        logger.info(
            "Navegação direta: %s → %s (dist=%.2fm, erro_ang=%.1f°)",
            self.current_position, destination,
            math.sqrt(dx ** 2 + dy ** 2), angle_error
        )

        self._nav_start_time = time.time()
        self._initialize_bno_offset()
        self.navigation_state = "NAVIGATING_TO_DESTINATION" if abs(angle_error) < 10.0 else "ORIENTING_TO_TARGET"

    def _setup_navigation_path(self, path: List[Tuple[float, float]], destination: Tuple[float, float]):
        """Configura o caminho de navegação e determina o estado inicial."""
        self.path = path
        self.path_index = 0
        self.original_destination = destination
        self.destination_index = len(path) - 1

        if len(self.path) > 1:
            dist_to_first = math.sqrt(
                (self.path[0][0] - self.current_position[0]) ** 2 +
                (self.path[0][1] - self.current_position[1]) ** 2
            )
            if dist_to_first < 0.05:
                self.current_target = self.path[1]
                self.path_index = 1
            else:
                self.current_target = self.path[0]
        else:
            self.current_target = self.path[0] if self.path else destination

        dx = self.current_target[0] - self.current_position[0]
        dy = self.current_target[1] - self.current_position[1]
        target_angle = math.degrees(math.atan2(dy, dx))
        angle_error = abs((target_angle - self.current_angle + 180) % 360 - 180)

        logger.info(
            "Caminho configurado: %d pontos, primeiro alvo=%s, erro_angular=%.1f°",
            len(self.path), self.current_target, angle_error
        )

        self._nav_start_time = time.time()
        self._initialize_bno_offset()
        self.navigation_state = "NAVIGATING_TO_DESTINATION" if angle_error < 20.0 else "ORIENTING_TO_TARGET"

    def get_navigation_status(self) -> dict:
        """Retorna o status atual da navegação."""
        if self.navigation_state == "COMPLETED":
            return {
                "state": "COMPLETED", "progress": 1.0, "estimated_time_remaining": 0.0,
                "current_target": None, "position": self.current_position, "angle": self.current_angle,
                "is_returning_to_base": False, "is_paused_at_destination": False,
                "cancelled_by_obstacle": getattr(self, "_cancelled_by_obstacle", False)
            }

        if not self.navigation_active:
            return {
                "state": "IDLE", "progress": 0.0, "estimated_time_remaining": 0.0,
                "current_target": None, "position": self.current_position, "angle": self.current_angle,
                "is_returning_to_base": False, "is_paused_at_destination": False
            }

        if len(self.path) > 1:
            progress = (self.path_index - 1) / (len(self.path) - 1)
        else:
            progress = 0.0

        time_remaining = 0.0
        if self.estimated_completion_time:
            time_remaining = max(0.0, self.estimated_completion_time - time.time())

        current_state = self.navigation_state
        if self.is_paused_at_destination:
            current_state = "PAUSED_AT_DESTINATION"
        elif self.is_adjusting_final_angle:
            current_state = "ADJUSTING_FINAL_ANGLE"

        return {
            "state": current_state, "progress": progress, "estimated_time_remaining": time_remaining,
            "current_target": self.current_target, "position": self.current_position,
            "angle": self.current_angle, "is_returning_to_base": self.is_returning_to_base,
            "is_paused_at_destination": self.is_paused_at_destination
        }

    def _calculate_distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calcula a distância euclidiana entre dois pontos."""
        return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)

    def _orient_towards_target(self):
        """
        Orienta o robô para o alvo atual.
        Usa estabilidade: só avança de estado após N iterações consecutivas dentro da tolerância.
        """
        if self.current_target is None:
            return

        tolerance = 15.0
        stability_threshold = 5

        if not hasattr(self, '_orient_stability_counter'):
            self._orient_stability_counter = 0

        # Timeout: proteção contra giro infinito caso o ângulo virtual não convirja.
        if self._orient_start_time is None:
            self._orient_start_time = time.time()
        elif time.time() - self._orient_start_time > 5.0:
            elapsed = time.time() - self._orient_start_time
            logger.warning(
                "Timeout na orientação (%.0fs): forçando NAVIGATING (erro angular persistente).",
                elapsed
            )
            self.motors.stop()
            self._orient_start_time = None
            self._orient_stability_counter = 0
            state_key = "RETURNING_TO_BASE" if self.is_returning_to_base else "NAVIGATING_TO_DESTINATION"
            self.navigation_state = state_key
            return

        dx = self.current_target[0] - self.current_position[0]
        dy = self.current_target[1] - self.current_position[1]
        target_angle_raw = math.degrees(math.atan2(dy, dx))

        target_angle_normalized = target_angle_raw if target_angle_raw >= 0 else target_angle_raw + 360
        current_angle_normalized = self.current_angle if self.current_angle >= 0 else self.current_angle + 360
        angle_error = (target_angle_normalized - current_angle_normalized + 180) % 360 - 180

        if not hasattr(self, '_orient_log_counter'):
            self._orient_log_counter = 0
        self._orient_log_counter += 1

        if self._orient_log_counter % 20 == 0:
            logger.debug(
                "Orientação: atual=%.1f° alvo=%.1f° erro=%.1f° estab=%d/%d",
                current_angle_normalized, target_angle_normalized,
                angle_error, self._orient_stability_counter, stability_threshold
            )

        if abs(angle_error) < tolerance:
            self._orient_stability_counter += 1
            if self._orient_stability_counter >= stability_threshold:
                self.motors.stop()
                state_key = "RETURNING_TO_BASE" if self.is_returning_to_base else "NAVIGATING_TO_DESTINATION"
                logger.info(
                    "Alinhado (erro=%.1f° por %d iter.) → %s",
                    abs(angle_error), stability_threshold, state_key
                )
                self._orient_stability_counter = 0
                self._orient_start_time = None
                self.navigation_state = state_key
                return
            else:
                self.motors.stop()
                return
        else:
            self._orient_stability_counter = 0

        # Ganho adaptativo
        if abs(angle_error) < 20.0:
            gain = 0.8
        elif abs(angle_error) < 45.0:
            gain = 1.0
        else:
            gain = 1.2

        angular_speed_rads = math.radians(angle_error) * gain
        angular_speed_rads = max(-MAX_ANGULAR_SPEED_RADS, min(MAX_ANGULAR_SPEED_RADS, angular_speed_rads))

        v = 0.0
        w = angular_speed_rads
        L = ROBOT_WHEEL_BASE_M

        left_wheel_speed_ms = v + (w * L) / 2.0
        right_wheel_speed_ms = v - (w * L) / 2.0
        left_tps = (left_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps = (right_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION

        if abs(angle_error) < 15.0:
            MIN_TURN_TPS = 4.0
        elif abs(angle_error) < 30.0:
            MIN_TURN_TPS = 6.0
        else:
            MIN_TURN_TPS = 8.0

        if 0 < abs(left_tps) < MIN_TURN_TPS:
            left_tps = MIN_TURN_TPS * (1 if left_tps > 0 else -1)
        if 0 < abs(right_tps) < MIN_TURN_TPS:
            right_tps = MIN_TURN_TPS * (1 if right_tps > 0 else -1)

        self.motors.set_target_speed(left_tps, right_tps)

    def _normalize_angle_deg(self, deg):
        """Coloca ângulo em [-180, 180]."""
        while deg > 180:
            deg -= 360
        while deg < -180:
            deg += 360
        return deg

    def _initialize_bno_offset(self):
        """
        Fase 2: Inicializa o offset BNO a partir do ângulo ATUAL antes de qualquer
        movimento. Garante que a correção BNO (Fase 1) seja precisa desde o primeiro
        giro, evitando que a odometria durante a curva inicial contamine o offset.
        Deve ser chamado quando o ângulo é confiável (início de navegação).
        """
        if not USE_BNO_IN_NAVIGATION or self._get_bno_yaw is None:
            return
        yaw = self._get_bno_yaw()
        if yaw is not None:
            self._bno_yaw_offset = self._normalize_angle_deg(self.current_angle - yaw)
            self._bno_yaw_ref = None
            logger.info(
                "BNO Fase2: offset inicializado antes do 1º giro: offset=%.1f° "
                "(ângulo=%.1f°, BNO=%.1f°)",
                self._bno_yaw_offset, self.current_angle, yaw
            )

    def _ensure_bno_yaw_ref(self):
        """Obtém primeira leitura válida de yaw para uso como referência."""
        if self._get_bno_yaw is None or self._bno_yaw_ref is not None:
            return
        deadline = time.time() + BNO_FIRST_READ_TIMEOUT
        while time.time() < deadline:
            yaw = self._get_bno_yaw()
            if yaw is not None:
                self._bno_yaw_ref = yaw
                return
            time.sleep(0.05)

    def _apply_bno_straight_correction(self, left_tps, right_tps):
        """
        Aplica correção de rumo BNO quando há avanço (v>0), para manter linha reta.
        Em curvas fortes (angle_error>45°) a ref é limpa em _move_towards_target.
        """
        if not USE_BNO_IN_NAVIGATION or self._get_bno_yaw is None:
            return left_tps, right_tps
        self._ensure_bno_yaw_ref()
        if self._bno_yaw_ref is None:
            return left_tps, right_tps
        yaw_now = self._get_bno_yaw()
        if yaw_now is None:
            return left_tps, right_tps
        err = self._normalize_angle_deg(yaw_now - self._bno_yaw_ref)
        if BNO_STRAIGHT_INVERT_CORRECTION:
            err = -err
        corr = BNO_STRAIGHT_KP * err
        corr = max(-BNO_STRAIGHT_MAX_CORRECTION_TPS, min(BNO_STRAIGHT_MAX_CORRECTION_TPS, corr))
        base_tps = (left_tps + right_tps) / 2.0
        left_tps = base_tps - corr
        right_tps = base_tps + corr
        return left_tps, right_tps

    def _calculate_cte(self, position: Tuple[float, float],
                       path_start: Tuple[float, float],
                       path_end: Tuple[float, float]) -> float:
        """
        Cross-Track Error (CTE): distância perpendicular assinada do robô ao
        segmento de caminho entre path_start e path_end.
        Positivo = robô à esquerda da linha; negativo = robô à direita.
        """
        dx = path_end[0] - path_start[0]
        dy = path_end[1] - path_start[1]
        segment_len = math.sqrt(dx ** 2 + dy ** 2)
        if segment_len < 0.001:
            return 0.0
        # Produto cruzado 2D: (B-A) × (P-A) / |B-A|
        rx = position[0] - path_start[0]
        ry = position[1] - path_start[1]
        return (dx * ry - dy * rx) / segment_len

    def _move_towards_target(self):
        """
        Navega direto para o waypoint atual (current_target) com correção de
        trajetória transversal (CTE) para manter o robô no traçado planejado.
        """
        if self.current_target is None:
            self.motors.set_target_speed(0, 0)
            return

        dx = self.current_target[0] - self.current_position[0]
        dy = self.current_target[1] - self.current_position[1]
        distance = math.sqrt(dx ** 2 + dy ** 2)
        target_angle = math.degrees(math.atan2(dy, dx))

        if target_angle < 0:
            target_angle += 360
        current_angle_normalized = self.current_angle if self.current_angle >= 0 else self.current_angle + 360
        angle_error = (target_angle - current_angle_normalized + 180) % 360 - 180

        # --- Correção de trajetória transversal (CTE) ---
        # Calcula o desvio perpendicular do robô em relação ao segmento atual
        # e adiciona uma correção angular proporcional ao desvio.
        # Isso mantém o robô na linha planejada, não apenas mirando no waypoint.
        cte = 0.0
        if self.path and self.path_index > 0 and self.path_index < len(self.path):
            prev_waypoint = self.path[self.path_index - 1]
            cte = self._calculate_cte(self.current_position, prev_waypoint, self.current_target)
            # Converte CTE em correção angular (atan para suavidade)
            # Ganho 1.2: equilibrio entre correção eficaz e oscilação
            cte_correction_deg = math.degrees(math.atan2(1.2 * cte, max(distance, 0.10)))
            # Limita a correção lateral a ±20° para evitar sobreesterçamento
            # e conflito com a correção BNO perto do destino.
            cte_correction_deg = max(-20.0, min(20.0, cte_correction_deg))
            # CTE positivo (esquerda da linha) → corrige para a direita (subtrai)
            angle_error -= cte_correction_deg

        if not hasattr(self, '_move_log_counter'):
            self._move_log_counter = 0
        self._move_log_counter += 1
        if self._move_log_counter % 20 == 0:
            logger.debug(
                "move_towards: dist=%.2fm ang_err=%.1f° cte=%.2fm alvo=%s",
                distance, angle_error, cte, self.current_target
            )

        if abs(angle_error) > 90.0:
            linear_speed_ms = 0.0
        else:
            angle_factor = max(0.0, math.cos(math.radians(angle_error)))
            linear_speed_ms = MAX_LINEAR_SPEED_MS * self.speed_multiplier * angle_factor

        angular_speed_rads = math.radians(angle_error) * 1.8
        angular_speed_rads = max(-MAX_ANGULAR_SPEED_RADS, min(MAX_ANGULAR_SPEED_RADS, angular_speed_rads))

        v = linear_speed_ms
        w = angular_speed_rads
        L = ROBOT_WHEEL_BASE_M

        left_wheel_speed_ms = v + (w * L) / 2.0
        right_wheel_speed_ms = v - (w * L) / 2.0

        if left_wheel_speed_ms < 0 or right_wheel_speed_ms < 0:
            if abs(angle_error) > 10.0:
                linear_speed_ms = 0.0
                v = 0.0
                left_wheel_speed_ms = (w * L) / 2.0
                right_wheel_speed_ms = -(w * L) / 2.0
            else:
                left_wheel_speed_ms = 0.0
                right_wheel_speed_ms = 0.0

        left_tps = (left_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps = (right_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION

        # BNO: limpa referência ao girar muito; aplica correção ao avançar
        if abs(angle_error) > 45.0:
            self._bno_yaw_ref = None
        if linear_speed_ms > 0.0:
            left_tps, right_tps = self._apply_bno_straight_correction(left_tps, right_tps)

        self.motors.set_target_speed(left_tps, right_tps)

    def _stable_final_approach(self, final_target: Tuple[float, float]):
        """
        Aproximação final precisa com velocidade adaptativa.
        Retorna True quando o destino é considerado alcançado.
        """
        if final_target is None:
            self.motors.stop()
            return True

        current_time = time.time()
        if self.final_approach_start_time is None:
            self.final_approach_start_time = current_time
            self._bno_yaw_ref = None
            # Guarda distância de entrada para detectar falta de progresso.
            self._fa_entry_distance = None  # será definido no próximo bloco

        if current_time - self.final_approach_start_time > self.final_approach_timeout:
            self.motors.stop()
            self.final_approach_start_time = None
            self._fa_entry_distance = None
            logger.warning("Timeout na aproximação final (%.0fs). Considerando chegada.", self.final_approach_timeout)
            return True

        dx = final_target[0] - self.current_position[0]
        dy = final_target[1] - self.current_position[1]
        total_distance = math.sqrt(dx ** 2 + dy ** 2)

        # Registra distância inicial (primeiro ciclo após a entrada)
        if self._fa_entry_distance is None:
            self._fa_entry_distance = total_distance
            self._fa_min_distance = total_distance

        # Guarda menor distância alcançada (para detectar ultrapassagem do POI)
        self._fa_min_distance = min(getattr(self, '_fa_min_distance', total_distance), total_distance)

        # Detecção de ultrapassagem: passou pelo POI e está se afastando.
        min_dist = getattr(self, '_fa_min_distance', total_distance)
        if (not self.is_returning_to_base and
                min_dist < 0.35 and
                total_distance > min_dist + 0.08):
            self.motors.stop()
            self.final_approach_start_time = None
            self._fa_entry_distance = None
            self._fa_min_distance = None
            logger.info(
                "POI ultrapassado (estava a %.0f cm, agora a %.0f cm). Declarando chegada.",
                min_dist * 100, total_distance * 100
            )
            return True

        target_angle = math.degrees(math.atan2(dy, dx))
        angle_diff = (target_angle - self.current_angle + 180) % 360 - 180

        final_tolerance = 0.08  # 8 cm — usuário confirmou 5 cm aceitável
        if total_distance <= final_tolerance:
            self.motors.stop()
            self.final_approach_start_time = None
            self._fa_entry_distance = None
            logger.info("Destino alcançado: %.1f cm", total_distance * 100)
            return True

        elapsed_approach = current_time - self.final_approach_start_time

        # Regra "só ida": para no POI sem exigir alinhamento angular preciso.
        # NÃO declarar chegada se obstáculo muito perto (< 40 cm) — provavelmente lixeira/obstáculo, não o POI.
        if not self.is_returning_to_base and total_distance < 0.15 and elapsed_approach >= 1.0:
            ob = self.motors.lidar_reader
            if ob and ob.has_obstacle():
                d = ob.obstacle_distance()
                if d != float("inf") and d < 0.40:
                    # Obstáculo < 40 cm na frente — provavelmente atropelamos algo, não estamos no POI
                    logger.info(
                        "Obstáculo a %.0f cm na frente — não declarar chegada (possível lixeira). Aguardando.",
                        d * 100
                    )
                    return False
            self.motors.stop()
            self.final_approach_start_time = None
            self._fa_entry_distance = None
            logger.info("POI alcançado (só ida, %.0f cm): parando.", total_distance * 100)
            return True

        # Detecção de giro sem progresso (só ida):
        # Quando o robô físico já está no POI mas a posição virtual mostra deriva
        # de odometria, _stable_final_approach fica girando o robô fisicamente
        # por até 6s sem avançar. Esta regra para o robô após 2s se o progresso
        # em direção ao alvo virtual for menor que 10 cm.
        # Não aplicar se Lidar está bloqueando (obstáculo na frente) — aguardar liberar.
        # Usa "sticky": considera bloqueado se detectou obstáculo nos últimos 8 s (evita gaps de scan).
        lidar_blocking = self.motors.is_lidar_blocking_or_recent(window_sec=8.0)
        if not self.is_returning_to_base and elapsed_approach > 2.0 and not lidar_blocking:
            progress = (self._fa_entry_distance or total_distance) - total_distance
            if progress < 0.10:
                self.motors.stop()
                self.final_approach_start_time = None
                self._fa_entry_distance = None
                logger.info(
                    "Aproximação sem progresso (%.0f cm em %.1f s). Chegada declarada.",
                    total_distance * 100, elapsed_approach
                )
                return True

        # Override por tempo: se em modo "só ida" há mais de 6 s, declara chegada
        # independente da distância (evita giro infinito por deriva de odometria).
        # Não aplicar se Lidar está bloqueando — robô parou por obstáculo, aguardar liberar.
        if not self.is_returning_to_base and elapsed_approach > 6.0 and not lidar_blocking:
            self.motors.stop()
            self.final_approach_start_time = None
            logger.info("POI: timeout de 6 s atingido (%.0f cm). Declarando chegada.", total_distance * 100)
            return True

        # Timeouts progressivos (retorno à base e casos gerais)
        if total_distance < 0.06 and elapsed_approach > 5.0:
            self.motors.stop()
            self.final_approach_start_time = None
            return True
        if total_distance < 0.15 and elapsed_approach > 7.0:
            self.motors.stop()
            self.final_approach_start_time = None
            self._fa_entry_distance = None
            return True
        if total_distance < 0.50 and elapsed_approach > 8.0:
            self.motors.stop()
            self.final_approach_start_time = None
            self._fa_entry_distance = None
            return True
        if total_distance < 1.00 and elapsed_approach > 10.0:
            self.motors.stop()
            self.final_approach_start_time = None
            self._fa_entry_distance = None
            return True

        # Velocidade adaptativa conforme distância.
        # angle_tolerance: graus máximos permitidos antes de bloquear o avanço.
        # Valores maiores para distâncias maiores permitem aproximação mesmo com
        # leve desvio de odometria, evitando giro estacionário.
        if total_distance < 0.05:
            speed_factor, angle_tolerance = 0.25, 5.0
        elif total_distance < 0.10:
            speed_factor, angle_tolerance = 0.40, 8.0
        elif total_distance < 0.20:
            speed_factor, angle_tolerance = 0.60, 15.0
        elif total_distance < 0.40:
            speed_factor, angle_tolerance = 0.75, 20.0
        else:
            speed_factor, angle_tolerance = 0.80, 25.0

        if not hasattr(self, '_final_approach_log_counter'):
            self._final_approach_log_counter = 0
        self._final_approach_log_counter += 1
        if self._final_approach_log_counter % 20 == 0:
            logger.debug("Aprox. final: %.1f cm, vel=%.0f%%", total_distance * 100, speed_factor * 100)

        if total_distance < 0.05:
            distance_factor = total_distance / 0.05
            linear_speed_ms = 0.0 if abs(angle_diff) > angle_tolerance else min(
                MAX_LINEAR_SPEED_MS * speed_factor * distance_factor,
                total_distance / 0.8
            )
        else:
            linear_speed_ms = 0.0 if abs(angle_diff) > angle_tolerance else min(
                MAX_LINEAR_SPEED_MS * speed_factor,
                total_distance / 1.2
            )

        if total_distance < 0.05:
            angular_gain = 1.8
        elif total_distance < 0.08:
            angular_gain = 2.0
        else:
            angular_gain = 2.5

        angular_speed_rads = math.radians(angle_diff) * angular_gain
        angular_speed_rads = max(-MAX_ANGULAR_SPEED_RADS, min(MAX_ANGULAR_SPEED_RADS, angular_speed_rads))

        v = linear_speed_ms
        w = angular_speed_rads
        L = ROBOT_WHEEL_BASE_M
        left_wheel_speed_ms = v + (w * L) / 2.0
        right_wheel_speed_ms = v - (w * L) / 2.0

        left_tps = (left_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps = (right_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION

        # BNO não é aplicado na aproximação final:
        # o controle angular aqui é feito pelo angle_diff (atan2 direto ao alvo),
        # que é preciso e suficiente. Aplicar BNO causa conflito e gira o robô
        # na direção errada ao chegar ao POI.

        self.motors.set_target_speed(left_tps, right_tps)
        return False

    def _adjust_final_angle(self):
        """Ajuste do ângulo final ao retornar à base."""
        if not self.is_returning_to_base:
            self._finalize_navigation()
            return

        if hasattr(self, 'final_angle_adjustment_start_time'):
            elapsed_time = time.time() - self.final_angle_adjustment_start_time
            if elapsed_time > 6.0:
                logger.warning(
                    "Timeout no ajuste de ângulo final (%.0fs). Ângulo atual=%.1f°, desejado=%d°",
                    elapsed_time, self.current_angle, ROBOT_INITIAL_ANGLE
                )
                self._finalize_navigation()
                return

        angle_diff = (ROBOT_INITIAL_ANGLE - self.current_angle + 180) % 360 - 180

        if not hasattr(self, '_angle_adjustment_log_counter'):
            self._angle_adjustment_log_counter = 0
        self._angle_adjustment_log_counter += 1
        if self._angle_adjustment_log_counter % 50 == 0:
            logger.debug("Ajuste ângulo final: erro=%.1f°, atual=%.1f°, desejado=%d°",
                         angle_diff, self.current_angle, ROBOT_INITIAL_ANGLE)

        if abs(angle_diff) > 5.0:
            if abs(angle_diff) > 30:
                turn_value = min(0.8, abs(angle_diff) / 25.0)
            elif abs(angle_diff) > 10:
                turn_value = min(0.6, abs(angle_diff) / 30.0)
            else:
                turn_value = min(0.4, abs(angle_diff) / 35.0)

            if angle_diff > 0:
                left_speed = turn_value * 100
                right_speed = -turn_value * 100
            else:
                left_speed = -turn_value * 100
                right_speed = turn_value * 100
            self.motors.set_speed(left_speed, right_speed)
        else:
            logger.info("Ajuste de ângulo final concluído: erro=%.1f°", angle_diff)
            self._finalize_navigation()

    def _get_next_waypoint_info(self):
        if not self.path or self.path_index >= len(self.path):
            return None
        return self.path_index, self.current_target, len(self.path)

    def _update_pose_with_odometry(self):
        """
        Atualiza posição e ângulo com odometria + filtro complementar BNO.

        O filtro complementar funde odometria e BNO suavemente:
          angulo_final = angulo_odom + alpha * (angulo_bno - angulo_odom)
        Com alpha=BNO_FILTER_ALPHA (ex: 0.15), o BNO corrige deriva angular
        de forma gradual sem causar correções bruscas. Spikes de leitura do BNO
        são descartados via BNO_SPIKE_THRESHOLD_DEG.
        """
        ticks_data = self.motors.get_and_reset_ticks()
        if not ticks_data:
            return
        if self.navigation_state == "PAUSED_AT_DESTINATION":
            return

        left_ticks, right_ticks = ticks_data.get('left', 0), ticks_data.get('right', 0)
        dist_left = (left_ticks / TICKS_PER_REVOLUTION) * ROBOT_WHEEL_CIRCUMFERENCE_M
        dist_right = (right_ticks / TICKS_PER_REVOLUTION) * ROBOT_WHEEL_CIRCUMFERENCE_M
        delta_distance = (dist_left + dist_right) / 2.0
        delta_angle_rad = (dist_left - dist_right) / ROBOT_WHEEL_BASE_M
        delta_angle_deg = math.degrees(delta_angle_rad)

        # Passo 1: odometria pura (base de sempre)
        new_angle = self._normalize_angle_deg(self.current_angle + delta_angle_deg)

        # Passo 2: filtro complementar BNO — corrige deriva angular na pose (opcional)
        # USE_BNO_POSE_FUSION=False: pose 100% odometria; BNO só atua em _apply_bno_straight_correction
        # Desativado durante: giro preciso e orientação intencional para waypoint
        if (USE_BNO_IN_NAVIGATION
                and USE_BNO_POSE_FUSION
                and self._get_bno_yaw is not None
                and not self.precise_rotation_active
                and self.navigation_state != "ORIENTING_TO_TARGET"):
            yaw = self._get_bno_yaw()
            if yaw is not None:
                if self._bno_yaw_offset is None:
                    # Primeira leitura: inicializa referencial do BNO
                    self._bno_yaw_offset = self._normalize_angle_deg(new_angle - yaw)
                    self._bno_prev_yaw = yaw
                else:
                    # Rejeição de spike: descarta leitura anômala
                    prev = self._bno_prev_yaw if self._bno_prev_yaw is not None else yaw
                    yaw_delta = abs(self._normalize_angle_deg(yaw - prev))
                    if yaw_delta <= BNO_SPIKE_THRESHOLD_DEG:
                        # Converte yaw BNO para o referencial do robô
                        bno_angle = self._normalize_angle_deg(yaw + self._bno_yaw_offset)
                        # Blenda suavemente: odometria + fração do erro do BNO
                        angle_diff = self._normalize_angle_deg(bno_angle - new_angle)
                        new_angle = self._normalize_angle_deg(new_angle + BNO_FILTER_ALPHA * angle_diff)
                        self._bno_prev_yaw = yaw
                    # Spike detectado: mantém new_angle como odometria pura neste ciclo

        self.current_angle = new_angle

        if not self.precise_rotation_active:
            angle_rad = math.radians(self.current_angle)
            delta_x = delta_distance * math.cos(angle_rad)
            delta_y = delta_distance * math.sin(angle_rad)
            self.current_position = (self.current_position[0] + delta_x, self.current_position[1] + delta_y)

        # ── Scan matching — alimenta pose atual e aplica correção se disponível ──
        if self._pose_corrector is not None and self._pose_corrector.is_running:
            # Atualiza pose estimada no corrector
            self._pose_corrector.update_pose(
                self.current_position[0],
                self.current_position[1],
                self.current_angle,
            )
            # Alimenta scan atual (se C1 disponível)
            lidar = getattr(self.motors, "lidar_reader", None)
            if lidar is not None and hasattr(lidar, "get_last_scan_points"):
                scan_pts = lidar.get_last_scan_points()
                if scan_pts:
                    self._pose_corrector.update_scan(scan_pts)

            # Aplica correção calculada (se disponível e dentro dos limites)
            if not self.precise_rotation_active:
                correction = self._pose_corrector.get_latest_correction()
                if correction is not None:
                    dx, dy, dtheta = correction
                    self.current_position = (
                        self.current_position[0] + dx,
                        self.current_position[1] + dy,
                    )
                    self.current_angle = self._normalize_angle_deg(self.current_angle + dtheta)
                    logger.info(
                        "ScanMatching: pose corrigida dx=%+.3f m  dy=%+.3f m  dθ=%+.1f°  "
                        "→ pos=(%.3f, %.3f)  θ=%.1f°",
                        dx, dy, dtheta,
                        self.current_position[0], self.current_position[1],
                        self.current_angle,
                    )

        self.last_position_update = time.time()
        self.position_updated.emit(self.current_position[0], self.current_position[1], self.current_angle)

    def get_motor_controller(self):
        return self.motors

    def start_precise_rotation(self):
        """Inicia modo de giro preciso — desabilita atualização de posição."""
        logger.debug("Modo de giro preciso ativado.")
        self.precise_rotation_active = True

    def stop_precise_rotation(self):
        """Para modo de giro preciso — reabilita atualização de posição."""
        logger.debug("Modo de giro preciso desativado.")
        self.precise_rotation_active = False

    def stop(self):
        """Comando de parada do navegador."""
        logger.info("Comando de parada recebido.")
        if self.navigation_state == "ORIENTING_TO_TARGET" and self.current_target is not None:
            dx = self.current_target[0] - self.current_position[0]
            dy = self.current_target[1] - self.current_position[1]
            target_angle_raw = math.degrees(math.atan2(dy, dx))
            target_angle_normalized = target_angle_raw if target_angle_raw >= 0 else target_angle_raw + 360
            current_angle_normalized = self.current_angle if self.current_angle >= 0 else self.current_angle + 360
            angle_error = (target_angle_normalized - current_angle_normalized + 180) % 360 - 180

            if abs(angle_error) < 30.0:
                self.motors.stop()
                state_key = "RETURNING_TO_BASE" if self.is_returning_to_base else "NAVIGATING_TO_DESTINATION"
                logger.info("Parada: forçando transição de orientação para navegação (erro=%.1f°).", angle_error)
                self.navigation_state = state_key
                if hasattr(self, '_orient_stability_counter'):
                    self._orient_stability_counter = 0
                return

        self._finalize_navigation()

    def _handle_navigation_to_destination(self):
        """Gerencia a navegação por waypoints até o destino."""
        if self.current_target is None or self.current_position is None:
            self._finalize_navigation()
            return

        current_time = time.time()

        # Watchdog 1: timeout global de navegação (protege contra giro infinito em qualquer estado)
        # Se Lidar está bloqueando (obstáculo na frente), NÃO forçar chegada — cancelar navegação.
        if self._nav_start_time and not self.is_returning_to_base:
            elapsed_total = current_time - self._nav_start_time
            if elapsed_total > self._nav_max_duration:
                if self.motors.is_lidar_blocking_or_recent(window_sec=10.0):
                    logger.warning(
                        "Watchdog: timeout %.0fs com obstáculo C1 na frente. Cancelando navegação (não chegou ao POI).",
                        self._nav_max_duration
                    )
                    self._cancel_navigation_blocked_by_obstacle()
                    return
                logger.warning(
                    "Watchdog: timeout global de %.0fs atingido. Forçando chegada ao POI.",
                    self._nav_max_duration
                )
                self.motors.stop()
                self._transition_to_paused_at_destination()
                return

        # Watchdog 2: se virtual já está perto o suficiente do destino final,
        # força FINAL_APPROACH mesmo sem ter chegado ao waypoint atual.
        # Resolve o caso de deriva de odometria em caminhos diagonais.
        if self.original_destination and not self.is_returning_to_base:
            dist_to_final = math.sqrt(
                (self.original_destination[0] - self.current_position[0]) ** 2 +
                (self.original_destination[1] - self.current_position[1]) ** 2
            )
            if dist_to_final <= 0.50:
                logger.info(
                    "Virtual a %.0f cm do POI; forçando FINAL_APPROACH (deriva de odometria).",
                    dist_to_final * 100
                )
                self.navigation_state = "FINAL_APPROACH_DESTINATION"
                self.current_target = self.original_destination
                self.final_approach_start_time = None
                return

        distance_to_target = self._calculate_distance(self.current_position, self.current_target)
        is_direct_navigation = (not self.path or len(self.path) <= 2)

        if is_direct_navigation:
            # Para POI (só ida): entra em aproximação final com margem ampla
            # para que a regra "só ida" possa atuar antes de girar indefinidamente.
            entry_threshold = 0.50 if not self.is_returning_to_base else 0.20
            if distance_to_target > entry_threshold:
                pass
            elif distance_to_target > 0.08:
                self.navigation_state = "FINAL_APPROACH_DESTINATION"
                self.current_target = self.original_destination
                self.final_approach_start_time = None
                return
            else:
                if distance_to_target < 0.08:
                    self._transition_to_paused_at_destination()
                    return
            self._move_towards_target()
            return

        # Navegação com waypoints (pathfinding)
        if not self.path:
            self._finalize_navigation()
            return
        if self.path_index >= len(self.path):
            self.navigation_state = "FINAL_APPROACH_DESTINATION"
            self.current_target = self.original_destination
            return
        if self.current_target is None:
            self.current_target = self.path[self.path_index] if self.path_index < len(self.path) else self.original_destination

        is_near_final_destination = (self.path_index >= len(self.path) - 1)

        # Para POI: entra em aproximação final mais cedo (50 cm) para evitar giro
        final_approach_trigger = 0.50 if not self.is_returning_to_base else 0.15
        if is_near_final_destination and distance_to_target < final_approach_trigger:
            self.navigation_state = "FINAL_APPROACH_DESTINATION"
            self.current_target = self.original_destination
            return

        # Avança waypoint com tolerância maior (30 cm) para compensar deriva de odometria
        if distance_to_target < 0.30:
            self.path_index += 1
            if self.path_index < len(self.path):
                self.current_target = self.path[self.path_index]
                logger.debug("Waypoint avançado: %d/%d → alvo=%s", self.path_index, len(self.path), self.current_target)
            else:
                self.navigation_state = "FINAL_APPROACH_DESTINATION"
                self.current_target = self.original_destination
                logger.info("Último waypoint alcançado; entrando em aproximação final.")
            return

        self._move_towards_target()

    def _handle_return_to_base(self):
        """Gerencia a navegação de retorno à base por waypoints."""
        if self.current_target is None or self.current_position is None:
            self._finalize_navigation()
            return

        # Watchdog de retorno: se demorar demais, finaliza para evitar loop infinito.
        if self._return_start_time is not None:
            elapsed_return = time.time() - self._return_start_time
            if elapsed_return > RETURN_MAX_DURATION_S:
                logger.warning(
                    "Watchdog retorno: timeout de %.0fs atingido. Finalizando navegação.",
                    RETURN_MAX_DURATION_S
                )
                self.motors.stop()
                self._finalize_navigation()
                return

        distance_to_target = self._calculate_distance(self.current_position, self.current_target)
        is_direct_navigation = (not self.path or len(self.path) <= 2)

        if is_direct_navigation:
            if distance_to_target > 0.20:
                pass
            elif distance_to_target > 0.06:
                self.navigation_state = "FINAL_APPROACH_BASE"
                self.current_target = self.base_position
                self.final_approach_start_time = None
                return
            else:
                if distance_to_target < 0.03:
                    self.navigation_state = "FINAL_APPROACH_BASE"
                    self.final_approach_start_time = None
                    return
            self._move_towards_target()
            return

        # Navegação com waypoints (pathfinding)
        if not self.path:
            self._finalize_navigation()
            return
        if self.path_index < 1:
            self.path_index = 1
        if self.path_index >= len(self.path):
            self.navigation_state = "FINAL_APPROACH_BASE"
            self.current_target = self.base_position
            self.final_approach_start_time = None
            return
        if self.current_target is None or self.path_index < len(self.path):
            self.current_target = self.path[self.path_index]

        is_near_base = (self.path_index >= len(self.path) - 1)

        if is_near_base and distance_to_target < 0.15:
            self.navigation_state = "FINAL_APPROACH_BASE"
            self.current_target = self.base_position
            self.final_approach_start_time = None
            return

        if distance_to_target < 0.30:
            self.path_index += 1
            if self.path_index < len(self.path):
                self.current_target = self.path[self.path_index]
                logger.debug("Retorno: waypoint %d/%d → alvo=%s", self.path_index, len(self.path), self.current_target)
            else:
                self.navigation_state = "FINAL_APPROACH_BASE"
                self.current_target = self.base_position
                self.final_approach_start_time = None
                logger.info("Último waypoint de retorno alcançado; aproximação final da base.")
            return

        self._move_towards_target()

    def _transition_to_paused_at_destination(self):
        self.motors.stop()
        self.navigation_state = "PAUSED_AT_DESTINATION"
        self.arrival_time = time.time()
        self.is_paused_at_destination = True
        logger.info("Chegou ao destino. Pausando por %.1fs.", self.arrival_pause_time)

    def _handle_pause_at_destination(self):
        if self.arrival_time is not None and (time.time() - self.arrival_time > self.arrival_pause_time):
            self.is_paused_at_destination = False
            if self.should_return_to_base:
                self._calculate_and_execute_return_angle()
            else:
                self._finalize_navigation()
