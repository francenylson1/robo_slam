from typing import List, Tuple, Dict, Set, Optional
import math
import heapq
from collections import deque
from .config import FORBIDDEN_AREA_INFLATION_RADIUS, ROBOT_WIDTH
from shapely.geometry import Polygon, Point

class PathFinder:
    def __init__(self, width: int = 100, height: int = 100, grid_size: float = 0.1):
        """
        Inicializa o PathFinder
        
        Args:
            width: Largura do mapa em células
            height: Altura do mapa em células
            grid_size: Tamanho de cada célula em metros
        """
        self.width = width
        self.height = height
        self.grid_size = grid_size
        self.forbidden_areas = []
        self.obstacle_grid = set()  # Cache para células com obstáculos
        print(f"DEBUG: PathFinder inicializado - Dimensões: {width}x{height}, Grid: {grid_size}m")
        
    def set_forbidden_areas(self, areas: List[List[Tuple[float, float]]]):
        """Define as áreas proibidas e atualiza o cache de obstáculos"""
        self.forbidden_areas = areas
        self._update_obstacle_grid()
        print(f"DEBUG: Áreas proibidas definidas: {len(areas)} áreas")
        
    def _update_obstacle_grid(self):
        """Atualiza o cache de células com obstáculos usando inflação geométrica e adicionando as bordas do mapa."""
        self.obstacle_grid.clear()
        
        # 1. Adicionar as áreas proibidas infladas
        for area in self.forbidden_areas:
            if len(area) < 3:
                continue # Um polígono precisa de pelo menos 3 pontos

            # Cria um polígono Shapely a partir da área
            original_polygon = Polygon(area)
            
            # Infla o polígono usando um buffer. Isso cria a margem de segurança
            inflated_polygon = original_polygon.buffer(FORBIDDEN_AREA_INFLATION_RADIUS)

            # Simplificação: assume que o resultado é um único polígono
            # Esta parte pode precisar de revisão se as áreas proibidas forem complexas
            if inflated_polygon.geom_type in ['Polygon', 'MultiPolygon']:
                # Extrai as coordenadas exteriores
                inflated_area_coords = list(inflated_polygon.exterior.coords)
                area_cells = self._area_to_grid_cells(inflated_area_coords)
                self.obstacle_grid.update(area_cells)

        # 2. Adicionar as bordas do mapa como obstáculos
        robot_radius_cells = math.ceil((ROBOT_WIDTH / 2) / self.grid_size)
        
        # Bordas verticais (esquerda e direita)
        for y in range(self.height):
            for i in range(robot_radius_cells):
                self.obstacle_grid.add((i, y))  # Borda esquerda
                self.obstacle_grid.add((self.width - 1 - i, y)) # Borda direita

        # Bordas horizontais (superior e inferior)
        for x in range(self.width):
            for i in range(robot_radius_cells):
                self.obstacle_grid.add((x, i)) # Borda inferior
                self.obstacle_grid.add((x, self.height - 1 - i)) # Borda superior

        print(f"DEBUG: Cache de obstáculos atualizado: {len(self.obstacle_grid)} células (incluindo áreas e bordas)")
        
    def _area_to_grid_cells(self, area: List[Tuple[float, ...]]) -> Set[Tuple[int, int]]:
        """Converte uma área poligonal em um conjunto de células da grade."""
        cells = set()
        
        # Encontra os limites da área
        min_x = min(point[0] for point in area)
        max_x = max(point[0] for point in area)
        min_y = min(point[1] for point in area)
        max_y = max(point[1] for point in area)
        
        # Converte para coordenadas da grade
        min_grid_x = max(0, int(min_x / self.grid_size))
        max_grid_x = min(self.width - 1, int(max_x / self.grid_size))
        min_grid_y = max(0, int(min_y / self.grid_size))
        max_grid_y = min(self.height - 1, int(max_y / self.grid_size))
        
        # Verifica cada célula dentro do retângulo delimitador do polígono
        for grid_x in range(min_grid_x, max_grid_x + 1):
            for grid_y in range(min_grid_y, max_grid_y + 1):
                # Usamos o centro da célula para verificar se está dentro do polígono
                world_x = (grid_x + 0.5) * self.grid_size
                world_y = (grid_y + 0.5) * self.grid_size
                
                if Point(world_x, world_y).within(Polygon(area)):
                    cells.add((grid_x, grid_y))
                    
        return cells
        
    def _is_point_in_forbidden_area(self, point: Tuple[float, float]) -> bool:
        """Verifica se um ponto está dentro de alguma área proibida"""
        for area in self.forbidden_areas:
            if self._point_in_polygon(point, area):
                return True
        return False
        
    def _point_in_polygon(self, point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
        """Verifica se um ponto está dentro de um polígono usando ray casting"""
        x, y = point
        n = len(polygon)
        inside = False
        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside
        
    def find_path(self, start: Tuple[float, float], goal: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Encontra um caminho do ponto inicial ao objetivo evitando áreas proibidas usando A* otimizado"""
        print(f"DEBUG: Calculando caminho de {start} para {goal}")
        
        # Converte coordenadas do mundo para coordenadas da grade
        start_grid = (int(start[0] / self.grid_size), int(start[1] / self.grid_size))
        goal_grid = (int(goal[0] / self.grid_size), int(goal[1] / self.grid_size))
        
        print(f"DEBUG: Coordenadas da grade - Início: {start_grid}, Fim: {goal_grid}")
        
        # Verifica se o objetivo está dentro dos limites do mapa
        if not (0 <= goal_grid[0] < self.width and 0 <= goal_grid[1] < self.height):
            print(f"DEBUG: Objetivo fora dos limites do mapa: {goal_grid}")
            return [start, goal]  # Retorna caminho direto se objetivo estiver fora do mapa
            
        # Verifica se o objetivo está em uma área proibida. Se sim, encontra o ponto válido mais próximo.
        if self._is_in_forbidden_area(goal_grid[0], goal_grid[1]):
            print(f"DEBUG: ⚠️ Objetivo {goal_grid} em área proibida. Procurando ponto válido mais próximo...")
            original_goal_grid = goal_grid
            goal_grid = self._find_nearest_valid_point(original_goal_grid)
            
            if goal_grid is None:
                print(f"DEBUG: ⛔ Não foi possível encontrar um ponto válido perto de {original_goal_grid}. Retornando caminho direto.")
                return [start, goal] # Desiste se não houver ponto válido
                
            print(f"DEBUG: ✅ Novo objetivo válido encontrado: {goal_grid}")
            
        # Executa o algoritmo A* otimizado
        path = self._astar_optimized(start_grid, goal_grid)
        
        if path:
            # Converte de volta para coordenadas do mundo
            world_path = [(x * self.grid_size, y * self.grid_size) for x, y in path]
            print(f"DEBUG: Caminho encontrado com {len(world_path)} pontos")
            return world_path
        else:
            print("DEBUG: Nenhum caminho encontrado, retornando caminho direto")
            return [start, goal]  # Retorna caminho direto se não encontrar um caminho válido
        
    def _find_nearest_valid_point(self, start_node: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Encontra o ponto válido mais próximo usando uma busca em largura (BFS)."""
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
                
                # Verifica se está nos limites
                if not (0 <= neighbor[0] < self.width and 0 <= neighbor[1] < self.height):
                    continue
                
                visited.add(neighbor)

                # Se não for um obstáculo, encontramos o ponto válido mais próximo
                if not self._is_in_forbidden_area(neighbor[0], neighbor[1]):
                    return neighbor
                
                q.append(neighbor)
                
        return None # Nenhum ponto válido encontrado

    def _astar_optimized(self, start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """Implementação otimizada do algoritmo A*"""
        # Estruturas de dados otimizadas
        open_set = []  # Fila de prioridade (heap)
        closed_set = set()
        came_from = {}
        g_score: Dict[Tuple[int, int], float] = {start: 0.0}
        f_score: Dict[Tuple[int, int], float] = {start: self._heuristic(start, goal)}
        
        # Adiciona o ponto inicial à fila de prioridade
        heapq.heappush(open_set, (f_score[start], start))
        
        # Direções de movimento (8 direções)
        directions = [
            (0, 1), (1, 0), (0, -1), (-1, 0),  # Cardinal
            (1, 1), (-1, 1), (1, -1), (-1, -1)  # Diagonal
        ]
        
        while open_set:
            # Remove o nó com menor f_score
            current_f, current = heapq.heappop(open_set)
            
            # Verifica se chegou ao objetivo
            if current == goal:
                print("DEBUG: Caminho encontrado pelo A*!")
                return self._reconstruct_path(came_from, current)
                
            # Adiciona à lista de nós visitados
            closed_set.add(current)
            
            # Explora os vizinhos
            for dx, dy in directions:
                neighbor = (current[0] + dx, current[1] + dy)
                
                # Verifica se o vizinho é válido
                if not (0 <= neighbor[0] < self.width and 0 <= neighbor[1] < self.height):
                    continue
                    
                # Verifica se está em área proibida (usando cache)
                if neighbor in self.obstacle_grid:
                    continue
                    
                # Verifica se já foi visitado
                if neighbor in closed_set:
                    continue
                    
                # Calcula o custo do movimento
                movement_cost = 1.4 if dx != 0 and dy != 0 else 1.0
                tentative_g_score = g_score[current] + movement_cost
                
                # Verifica se encontrou um caminho melhor
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    # Atualiza os scores
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = g_score[neighbor] + self._heuristic(neighbor, goal)
                    
                    # Adiciona à fila de prioridade
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
                    
        # Nenhum caminho encontrado
        return None
        
    def _is_in_forbidden_area(self, x: int, y: int) -> bool:
        """Verifica se um ponto da grade está em uma área proibida (usando cache)"""
        return (x, y) in self.obstacle_grid
        
    def _is_point_in_polygon(self, point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
        """Verifica se um ponto está dentro de um polígono usando ray casting"""
        x, y = point
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
            
        return inside 

    def _heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """
        Calcula a distância heurística entre dois pontos usando distância euclidiana
        """
        return math.sqrt((b[0] - a[0])**2 + (b[1] - a[1])**2)
        
    def _reconstruct_path(self, came_from: Dict[Tuple[int, int], Tuple[int, int]], 
                         current: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Reconstrói o caminho a partir do dicionário de predecessores
        """
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
        
    def optimize_path(self, path: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Otimiza um caminho removendo pontos desnecessários"""
        if len(path) < 3:
            return path
            
        optimized_path = [path[0]]
        
        for i in range(1, len(path) - 1):
            prev_point = path[i - 1]
            current_point = path[i]
            next_point = path[i + 1]
            
            # Verifica se o ponto atual pode ser removido
            if not self._line_intersects_obstacles(prev_point, next_point):
                # Ponto pode ser removido, continua
                continue
            else:
                # Ponto é necessário, mantém
                optimized_path.append(current_point)
                
        optimized_path.append(path[-1])
        
        print(f"DEBUG: Caminho otimizado: {len(path)} -> {len(optimized_path)} pontos")
        return optimized_path
        
    def _line_intersects_obstacles(self, start: Tuple[float, float], end: Tuple[float, float]) -> bool:
        """Verifica se uma linha intersecta alguma área proibida"""
        # Converte para coordenadas da grade
        start_grid = (int(start[0] / self.grid_size), int(start[1] / self.grid_size))
        end_grid = (int(end[0] / self.grid_size), int(end[1] / self.grid_size))
        
        # Usa o algoritmo de Bresenham para verificar todos os pontos da linha
        points = self._bresenham_line(start_grid, end_grid)
        
        for point in points:
            if point in self.obstacle_grid:
                return True
                
        return False
        
    def _bresenham_line(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Implementa o algoritmo de Bresenham para traçar uma linha"""
        x0, y0 = start
        x1, y1 = end
        
        points = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        
        if x0 < x1:
            sx = 1
        else:
            sx = -1
            
        if y0 < y1:
            sy = 1
        else:
            sy = -1
            
        err = dx - dy
        
        while True:
            points.append((x0, y0))
            
            if x0 == x1 and y0 == y1:
                break
                
            e2 = 2 * err
            if e2 > -dy:
                err = err - dy
                x0 = x0 + sx
            if e2 < dx:
                err = err + dx
                y0 = y0 + sy
                
        return points 