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

        self.arrival_pause_time = 2.0
        self.arrival_time = None
        self.is_paused_at_destination = False

        self.is_returning_to_initial_angle = False

        self.should_return_to_base = True

        self.final_approach_start_time = None
        self.final_approach_timeout = 10.0

        self.use_direct_navigation = True

        # BNO08x: integração opcional (USE_BNO_IN_NAVIGATION no config)
        self._get_bno_yaw = None
        self._bno_yaw_ref = None
        self._bno_yaw_offset = None
        if is_raspberry_pi() and USE_BNO_IN_NAVIGATION:
            try:
                from tools.bno08x_init import init_bno
                _bno, self._get_bno_yaw = init_bno(do_reset_cycle=False, verbose=False)
                if self._get_bno_yaw is not None:
                    logger.info("BNO08x integrado ao navegador (correção de rumo e ângulo).")
                else:
                    self._get_bno_yaw = None
            except Exception as e:
                logger.warning("BNO08x não disponível no navegador: %s", e)
                self._get_bno_yaw = None

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
        logger.info("Navegação finalizada.")

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
            self._bno_yaw_offset = None
            self._bno_yaw_ref = None
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

        self._bno_yaw_offset = None
        self._bno_yaw_ref = None
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
        self.path_index = 0

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

        self.navigation_state = "NAVIGATING_TO_DESTINATION" if angle_error < 20.0 else "ORIENTING_TO_TARGET"

    def get_navigation_status(self) -> dict:
        """Retorna o status atual da navegação."""
        if self.navigation_state == "COMPLETED":
            return {
                "state": "COMPLETED", "progress": 1.0, "estimated_time_remaining": 0.0,
                "current_target": None, "position": self.current_position, "angle": self.current_angle,
                "is_returning_to_base": False, "is_paused_at_destination": False
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

    def _move_towards_target(self):
        """
        Navega direto para o waypoint atual (current_target).
        Controle proporcional de velocidade linear e angular combinado.
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

        if not hasattr(self, '_move_log_counter'):
            self._move_log_counter = 0
        self._move_log_counter += 1
        if self._move_log_counter % 20 == 0:
            logger.debug(
                "move_towards: dist=%.2fm ang_err=%.1f° alvo=%s",
                distance, angle_error, self.current_target
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

        if current_time - self.final_approach_start_time > self.final_approach_timeout:
            self.motors.stop()
            self.final_approach_start_time = None
            logger.warning("Timeout na aproximação final (%.0fs). Considerando chegada.", self.final_approach_timeout)
            return True

        dx = final_target[0] - self.current_position[0]
        dy = final_target[1] - self.current_position[1]
        total_distance = math.sqrt(dx ** 2 + dy ** 2)
        target_angle = math.degrees(math.atan2(dy, dx))
        angle_diff = (target_angle - self.current_angle + 180) % 360 - 180

        final_tolerance = 0.08  # 8 cm — usuário confirmou 5 cm aceitável
        if total_distance <= final_tolerance:
            self.motors.stop()
            self.final_approach_start_time = None
            logger.info("Destino alcançado: %.1f cm", total_distance * 100)
            return True

        elapsed_approach = current_time - self.final_approach_start_time

        # Regra "só ida": para no POI sem exigir alinhamento angular preciso.
        # 15 cm / 1 s — aceitável para o garçom (usuário confirmou 5-10 cm ok).
        if not self.is_returning_to_base and total_distance < 0.15 and elapsed_approach >= 1.0:
            self.motors.stop()
            self.final_approach_start_time = None
            logger.info("POI alcançado (só ida, %.0f cm): parando.", total_distance * 100)
            return True

        # Override por tempo: se em modo "só ida" há mais de 6 s, declara chegada
        # independente da distância (evita giro infinito por deriva de odometria).
        if not self.is_returning_to_base and elapsed_approach > 6.0:
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
            return True
        if total_distance < 0.50 and elapsed_approach > 8.0:
            self.motors.stop()
            self.final_approach_start_time = None
            return True
        if total_distance < 1.00 and elapsed_approach > 4.0:
            self.motors.stop()
            self.final_approach_start_time = None
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

        if linear_speed_ms > 0.0:
            left_tps, right_tps = self._apply_bno_straight_correction(left_tps, right_tps)

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
        Atualiza posição e ângulo do robô com base na odometria.
        Usa BNO para o ângulo em trechos retos (Fase 1) se configurado.
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

        use_bno_angle = (
            USE_BNO_IN_NAVIGATION
            and self._get_bno_yaw is not None
            and not self.precise_rotation_active
        )
        # Fase 1: BNO só em trechos retos
        if use_bno_angle and USE_BNO_ON_STRAIGHTS_ONLY:
            use_bno_angle = use_bno_angle and (abs(delta_angle_deg) < STRAIGHT_ANGLE_THRESHOLD_DEG)

        if use_bno_angle:
            yaw = self._get_bno_yaw()
            if yaw is not None:
                if self._bno_yaw_offset is None:
                    self._bno_yaw_offset = self._normalize_angle_deg(self.current_angle - yaw)
                self.current_angle = self._normalize_angle_deg(yaw + self._bno_yaw_offset)
            else:
                self.current_angle = self._normalize_angle_deg(self.current_angle + delta_angle_deg)
        else:
            self.current_angle += delta_angle_deg
            if self.current_angle > 180:
                self.current_angle -= 360
            elif self.current_angle < -180:
                self.current_angle += 360

        if not self.precise_rotation_active:
            angle_rad = math.radians(self.current_angle)
            delta_x = delta_distance * math.cos(angle_rad)
            delta_y = delta_distance * math.sin(angle_rad)
            self.current_position = (self.current_position[0] + delta_x, self.current_position[1] + delta_y)

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
