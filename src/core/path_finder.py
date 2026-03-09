import logging
import math
import heapq
from collections import deque
from typing import List, Tuple, Dict, Set, Optional

from shapely.geometry import Polygon, Point

from .config import FORBIDDEN_AREA_INFLATION_RADIUS, ROBOT_WIDTH

logger = logging.getLogger(__name__)


class PathFinder:
    def __init__(self, width: int = 100, height: int = 100, grid_size: float = 0.1,
                 map_origin: Tuple[float, float] = (0.0, 0.0)):
        self.width = width
        self.height = height
        self.grid_size = grid_size
        self.map_origin = map_origin
        self.forbidden_areas = []
        self.obstacle_grid: Set[Tuple[int, int]] = set()
        logger.debug(
            "PathFinder inicializado – %dx%d células, grid=%.2fm, origem=%s",
            width, height, grid_size, map_origin
        )

    def update_map_config(self, width: int, height: int, grid_size: float,
                          map_origin: Tuple[float, float]):
        """Atualiza a configuração do mapa (útil quando um mapa PGM é carregado)."""
        self.width = width
        self.height = height
        self.grid_size = grid_size
        self.map_origin = map_origin
        if self.forbidden_areas:
            self._update_obstacle_grid()
        logger.debug(
            "PathFinder atualizado – %dx%d células, grid=%.2fm, origem=%s",
            width, height, grid_size, map_origin
        )

    def set_forbidden_areas(self, areas: List[List[Tuple[float, float]]]):
        """Define as áreas proibidas e atualiza o cache de obstáculos."""
        self.forbidden_areas = areas
        self._update_obstacle_grid()
        logger.debug("Áreas proibidas definidas: %d áreas", len(areas))

    def _update_obstacle_grid(self):
        """
        Atualiza o cache de células de obstáculo usando Shapely com inflação de segurança.
        Também adiciona bordas do mapa como obstáculos.
        """
        self.obstacle_grid.clear()

        inflated_polygons = []
        for area in self.forbidden_areas:
            if len(area) >= 3:
                polygon = Polygon(area)
                inflated_polygons.append(polygon.buffer(FORBIDDEN_AREA_INFLATION_RADIUS))

        for grid_x in range(self.width):
            for grid_y in range(self.height):
                world_x = (grid_x + 0.5) * self.grid_size + self.map_origin[0]
                world_y = (grid_y + 0.5) * self.grid_size + self.map_origin[1]
                cell_point = Point(world_x, world_y)
                for inflated_polygon in inflated_polygons:
                    if cell_point.within(inflated_polygon):
                        self.obstacle_grid.add((grid_x, grid_y))
                        break

        robot_radius_cells = math.ceil((ROBOT_WIDTH / 2) / self.grid_size)
        for y in range(self.height):
            for i in range(robot_radius_cells):
                self.obstacle_grid.add((i, y))
                self.obstacle_grid.add((self.width - 1 - i, y))
        for x in range(self.width):
            for i in range(robot_radius_cells):
                self.obstacle_grid.add((x, i))
                self.obstacle_grid.add((x, self.height - 1 - i))

        logger.debug("Cache de obstáculos atualizado: %d células", len(self.obstacle_grid))

    def _is_in_forbidden_area(self, x: int, y: int) -> bool:
        """Verifica se uma célula da grade está na área proibida usando o cache."""
        return (x, y) in self.obstacle_grid

    def find_path(self, start: Tuple[float, float], goal: Tuple[float, float]) -> Optional[List[Tuple[float, float]]]:
        """Encontra um caminho do ponto inicial ao objetivo evitando áreas proibidas (A*)."""
        logger.debug("Calculando caminho de %s para %s", start, goal)

        start_relative_x = start[0] - self.map_origin[0]
        start_relative_y = start[1] - self.map_origin[1]
        goal_relative_x = goal[0] - self.map_origin[0]
        goal_relative_y = goal[1] - self.map_origin[1]

        start_grid = (int(start_relative_x / self.grid_size), int(start_relative_y / self.grid_size))
        goal_grid = (int(goal_relative_x / self.grid_size), int(goal_relative_y / self.grid_size))

        logger.debug(
            "Grade – início=%s fim=%s | mapa %dx%d células, grid=%.2fm",
            start_grid, goal_grid, self.width, self.height, self.grid_size
        )

        if not (0 <= start_grid[0] < self.width and 0 <= start_grid[1] < self.height):
            logger.error("Início fora dos limites do mapa: %s", start_grid)
            return None

        if not (0 <= goal_grid[0] < self.width and 0 <= goal_grid[1] < self.height):
            logger.error("Objetivo fora dos limites do mapa: %s", goal_grid)
            return None

        if self._is_in_forbidden_area(start_grid[0], start_grid[1]):
            logger.warning("Início %s em área proibida. Buscando ponto válido mais próximo...", start_grid)
            original_start_grid = start_grid
            start_grid = self._find_nearest_valid_point(original_start_grid)
            if start_grid is None:
                logger.error("Nenhum ponto válido encontrado perto do início %s.", original_start_grid)
                return None
            logger.debug("Novo início válido: %s", start_grid)

        if self._is_in_forbidden_area(goal_grid[0], goal_grid[1]):
            logger.warning("Objetivo %s em área proibida. Buscando ponto válido mais próximo...", goal_grid)
            original_goal_grid = goal_grid
            goal_grid = self._find_nearest_valid_point(original_goal_grid)
            if goal_grid is None:
                logger.error("Nenhum ponto válido encontrado perto do objetivo %s.", original_goal_grid)
                return None
            logger.debug("Novo objetivo válido: %s", goal_grid)

        path = self._astar_optimized(start_grid, goal_grid)

        if not path:
            logger.error(
                "A* não encontrou caminho de %s para %s (obstacle_grid: %d células)",
                start_grid, goal_grid, len(self.obstacle_grid)
            )
            return None

        # Converte de volta para coordenadas do mundo
        world_path = [
            (x * self.grid_size + self.map_origin[0], y * self.grid_size + self.map_origin[1])
            for x, y in path
        ]

        # Substitui o primeiro ponto pela posição atual exata (se for seguro)
        if len(world_path) > 0:
            if len(world_path) > 1 and self.forbidden_areas:
                if not self._line_intersects_obstacles(start, world_path[1]):
                    world_path[0] = start
                else:
                    logger.debug("Start exato criaria segmento inválido; mantendo ponto válido do A*.")
            else:
                world_path[0] = start

        # Garante que o último ponto seja o goal exato (se goal não está em área proibida)
        if len(world_path) > 0:
            if self.forbidden_areas:
                goal_gx = int(goal_relative_x / self.grid_size)
                goal_gy = int(goal_relative_y / self.grid_size)
                goal_in_obstacle = self._is_in_forbidden_area(goal_gx, goal_gy)
                if not goal_in_obstacle:
                    world_path[-1] = goal
                elif len(world_path) > 1 and not self._line_intersects_obstacles(world_path[-2], goal):
                    world_path[-1] = goal
                else:
                    logger.debug("Goal em área proibida com segmento inválido; mantendo ponto seguro.")
            else:
                world_path[-1] = goal

        # Validação final dos segmentos
        if self.forbidden_areas:
            goal_gx = int((goal[0] - self.map_origin[0]) / self.grid_size)
            goal_gy = int((goal[1] - self.map_origin[1]) / self.grid_size)
            goal_in_obstacle = self._is_in_forbidden_area(goal_gx, goal_gy)

            invalid_segments = []
            for i in range(len(world_path) - 1):
                if self._line_intersects_obstacles(world_path[i], world_path[i + 1]):
                    is_last_segment = (i == len(world_path) - 2)
                    if is_last_segment and not goal_in_obstacle:
                        # Último segmento até goal válido — robô chega na aproximação final
                        continue
                    invalid_segments.append(i)
                    logger.warning("Segmento %d (%s → %s) intersecta área proibida pós-simplificação.", i, world_path[i], world_path[i + 1])

            if invalid_segments:
                logger.error("%d segmento(s) inválido(s) detectado(s); caminho não é seguro.", len(invalid_segments))
                return None

        # Garantia final: último ponto = goal exato (se não em obstáculo)
        if self.forbidden_areas:
            goal_gx = int((goal[0] - self.map_origin[0]) / self.grid_size)
            goal_gy = int((goal[1] - self.map_origin[1]) / self.grid_size)
            if not self._is_in_forbidden_area(goal_gx, goal_gy) and world_path[-1] != goal:
                world_path[-1] = goal
        elif world_path[-1] != goal:
            world_path[-1] = goal

        logger.info("Caminho encontrado: %d pontos (%s → %s)", len(world_path), world_path[0], world_path[-1])
        return world_path

    def _find_nearest_valid_point(self, start_node: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Encontra o ponto válido mais próximo usando BFS."""
        if not self._is_in_forbidden_area(start_node[0], start_node[1]):
            return start_node

        q = deque([start_node])
        visited = {start_node}
        directions = [
            (0, 1), (1, 0), (0, -1), (-1, 0),
            (1, 1), (-1, 1), (1, -1), (-1, -1)
        ]

        while q:
            current_node = q.popleft()
            for dx, dy in directions:
                neighbor = (current_node[0] + dx, current_node[1] + dy)
                if neighbor in visited:
                    continue
                if not (0 <= neighbor[0] < self.width and 0 <= neighbor[1] < self.height):
                    continue
                visited.add(neighbor)
                if not self._is_in_forbidden_area(neighbor[0], neighbor[1]):
                    return neighbor
                q.append(neighbor)

        return None

    def _astar_optimized(self, start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """Implementação otimizada do A* com simplificação e suavização de curvas."""
        if self._is_in_forbidden_area(start[0], start[1]):
            logger.error("A*: start %s está em área proibida.", start)
            return None
        if self._is_in_forbidden_area(goal[0], goal[1]):
            logger.error("A*: goal %s está em área proibida.", goal)
            return None

        open_set = []
        closed_set: Set[Tuple[int, int]] = set()
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], float] = {start: 0.0}
        f_score: Dict[Tuple[int, int], float] = {start: self._heuristic(start, goal)}

        heapq.heappush(open_set, (f_score[start], start))

        directions = [
            (0, 1), (1, 0), (0, -1), (-1, 0),
            (1, 1), (-1, 1), (1, -1), (-1, -1)
        ]

        logger.debug("A* iniciado: %s → %s (%d células em obstacle_grid)", start, goal, len(self.obstacle_grid))

        while open_set:
            current_f, current = heapq.heappop(open_set)

            if current == goal:
                raw_path = self._reconstruct_path(came_from, current)
                simplified_path = self._simplify_path(raw_path)
                final_path = self._smooth_curves(simplified_path)
                logger.debug(
                    "A* concluído: %d → %d → %d pontos (raw→simplif→suaviz)",
                    len(raw_path), len(simplified_path), len(final_path)
                )
                return final_path

            closed_set.add(current)

            for dx, dy in directions:
                neighbor = (current[0] + dx, current[1] + dy)

                if not (0 <= neighbor[0] < self.width and 0 <= neighbor[1] < self.height):
                    continue
                if neighbor in self.obstacle_grid:
                    continue
                if neighbor in closed_set:
                    continue

                movement_cost = 1.4 if dx != 0 and dy != 0 else 1.0
                tentative_g_score = g_score[current] + movement_cost

                if neighbor not in [item[1] for item in open_set] or tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self._heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        logger.error(
            "A*: nenhum caminho encontrado de %s para %s (closed=%d nós)",
            start, goal, len(closed_set)
        )
        return None

    def _simplify_path(self, path: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Simplifica o caminho removendo waypoints desnecessários (verificação com Bresenham)."""
        if len(path) <= 2:
            return path

        simplified = [path[0]]
        current_idx = 0

        while current_idx < len(path) - 1:
            next_idx = current_idx + 1
            best_idx = next_idx

            for i in range(current_idx + 2, len(path)):
                if self._can_skip_points(path[current_idx], path[i]):
                    best_idx = i
                else:
                    break

            simplified.append(path[best_idx])
            current_idx = best_idx

            if current_idx >= len(path) - 1:
                break

        if simplified[-1] != path[-1]:
            simplified.append(path[-1])

        # Valida segmentos simplificados
        if self.forbidden_areas:
            for i in range(len(simplified) - 1):
                start_world = (
                    simplified[i][0] * self.grid_size + self.map_origin[0],
                    simplified[i][1] * self.grid_size + self.map_origin[1]
                )
                end_world = (
                    simplified[i + 1][0] * self.grid_size + self.map_origin[0],
                    simplified[i + 1][1] * self.grid_size + self.map_origin[1]
                )
                if self._line_intersects_obstacles(start_world, end_world):
                    logger.warning("Simplificação criou segmento %d inválido; revertendo para caminho original.", i)
                    return path

        return simplified

    def _smooth_curves(self, path: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Suaviza curvas agudas inserindo waypoints intermediários."""
        if len(path) <= 2:
            return path

        smoothed = [path[0]]

        for i in range(1, len(path) - 1):
            current = path[i]
            prev = path[i - 1]
            next_point = path[i + 1]

            angle = self._calculate_angle_between_points(prev, current, next_point)

            if angle < 45.0:
                intermediate_points = self._generate_intermediate_points(prev, current, next_point, angle)
                smoothed.extend(intermediate_points)
            else:
                smoothed.append(current)

        smoothed.append(path[-1])
        return smoothed

    def _calculate_angle_between_points(self, p1: Tuple[int, int], p2: Tuple[int, int], p3: Tuple[int, int]) -> float:
        """Calcula o ângulo entre três pontos (p2 é o vértice)."""
        p1w = (p1[0] * self.grid_size + self.map_origin[0], p1[1] * self.grid_size + self.map_origin[1])
        p2w = (p2[0] * self.grid_size + self.map_origin[0], p2[1] * self.grid_size + self.map_origin[1])
        p3w = (p3[0] * self.grid_size + self.map_origin[0], p3[1] * self.grid_size + self.map_origin[1])

        v1 = (p1w[0] - p2w[0], p1w[1] - p2w[1])
        v2 = (p3w[0] - p2w[0], p3w[1] - p2w[1])

        dot_product = v1[0] * v2[0] + v1[1] * v2[1]
        mag1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
        mag2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2)

        if mag1 == 0 or mag2 == 0:
            return 180.0

        cos_angle = max(-1.0, min(1.0, dot_product / (mag1 * mag2)))
        return math.degrees(math.acos(cos_angle))

    def _generate_intermediate_points(self, p1: Tuple[int, int], p2: Tuple[int, int], p3: Tuple[int, int],
                                       angle: float) -> List[Tuple[int, int]]:
        """Gera waypoints intermediários para suavizar curvas agudas."""
        p1w = (p1[0] * self.grid_size + self.map_origin[0], p1[1] * self.grid_size + self.map_origin[1])
        p2w = (p2[0] * self.grid_size + self.map_origin[0], p2[1] * self.grid_size + self.map_origin[1])
        p3w = (p3[0] * self.grid_size + self.map_origin[0], p3[1] * self.grid_size + self.map_origin[1])

        if angle < 30.0:
            num_points = 16
        elif angle < 45.0:
            num_points = 12
        else:
            num_points = 8

        intermediate_points = []

        for i in range(1, num_points + 1):
            t = i / (num_points + 1)
            if t <= 0.5:
                t_smooth = 2 * t * t
                x = p1w[0] + t_smooth * (p2w[0] - p1w[0])
                y = p1w[1] + t_smooth * (p2w[1] - p1w[1])
            else:
                t_smooth = 1 - 2 * (1 - t) * (1 - t)
                x = p2w[0] + t_smooth * (p3w[0] - p2w[0])
                y = p2w[1] + t_smooth * (p3w[1] - p2w[1])

            grid_x = int((x - self.map_origin[0]) / self.grid_size)
            grid_y = int((y - self.map_origin[1]) / self.grid_size)

            if (0 <= grid_x < self.width and 0 <= grid_y < self.height
                    and not self._is_in_forbidden_area(grid_x, grid_y)):
                intermediate_points.append((grid_x, grid_y))

        return intermediate_points

    def _can_skip_points(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        """Verifica se pode pular pontos intermediários usando Bresenham."""
        for point in self._bresenham_line(start, end):
            if self._is_in_forbidden_area(point[0], point[1]):
                return False
        return True

    def _calculate_world_distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calcula distância euclidiana entre dois pontos."""
        return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)

    def _heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """Heurística euclidiana para o A*."""
        return math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)

    def _reconstruct_path(self, came_from: Dict[Tuple[int, int], Tuple[int, int]],
                          current: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Reconstrói o caminho a partir do dicionário de predecessores."""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    def optimize_path(self, path: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Otimiza um caminho removendo pontos desnecessários."""
        if len(path) < 3:
            return path

        optimized_path = [path[0]]

        for i in range(1, len(path) - 1):
            prev_point = path[i - 1]
            next_point = path[i + 1]
            if self._line_intersects_obstacles(prev_point, next_point):
                optimized_path.append(path[i])

        optimized_path.append(path[-1])
        logger.debug("Caminho otimizado: %d → %d pontos", len(path), len(optimized_path))
        return optimized_path

    def _line_intersects_obstacles(self, start: Tuple[float, float], end: Tuple[float, float]) -> bool:
        """Verifica se uma linha intersecta alguma área proibida (via Bresenham na grade)."""
        if not self.forbidden_areas or not self.obstacle_grid:
            return False

        start_grid = (
            int((start[0] - self.map_origin[0]) / self.grid_size),
            int((start[1] - self.map_origin[1]) / self.grid_size)
        )
        end_grid = (
            int((end[0] - self.map_origin[0]) / self.grid_size),
            int((end[1] - self.map_origin[1]) / self.grid_size)
        )

        if not (0 <= start_grid[0] < self.width and 0 <= start_grid[1] < self.height):
            return False
        if not (0 <= end_grid[0] < self.width and 0 <= end_grid[1] < self.height):
            return False

        for point in self._bresenham_line(start_grid, end_grid):
            if point in self.obstacle_grid:
                return True

        return False

    def _bresenham_line(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Algoritmo de Bresenham para traçar todos os pontos de uma linha."""
        x0, y0 = start
        x1, y1 = end
        points = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            points.append((x0, y0))
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

        return points
