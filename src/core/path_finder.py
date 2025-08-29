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
        """
        (CORRIGIDO) Atualiza o cache de células de obstáculo.
        Este método agora usa uma abordagem de força bruta mais robusta para garantir
        que as áreas proibidas sejam completamente preenchidas, incluindo uma margem de segurança.
        """
        self.obstacle_grid.clear()
        
        # Converte as áreas proibidas em polígonos Shapely para cálculos eficientes.
        # Infla os polígonos para criar uma margem de segurança.
        inflated_polygons = []
        for area in self.forbidden_areas:
            if len(area) >= 3:
                polygon = Polygon(area)
                inflated_polygons.append(polygon.buffer(FORBIDDEN_AREA_INFLATION_RADIUS))

        # Itera por TODAS as células do mapa.
        for grid_x in range(self.width):
            for grid_y in range(self.height):
                # Converte o centro da célula de grade para coordenadas do mundo.
                world_x = (grid_x + 0.5) * self.grid_size
                world_y = (grid_y + 0.5) * self.grid_size
                cell_point = Point(world_x, world_y)
                
                # Verifica se o ponto da célula está dentro de algum polígono inflado.
                for inflated_polygon in inflated_polygons:
                    if cell_point.within(inflated_polygon):
                        self.obstacle_grid.add((grid_x, grid_y))
                        break # Otimização: se já está em uma área, não precisa checar as outras.

        # Adiciona as bordas do mapa como obstáculos para segurança adicional.
        robot_radius_cells = math.ceil((ROBOT_WIDTH / 2) / self.grid_size)
        for y in range(self.height):
            for i in range(robot_radius_cells):
                self.obstacle_grid.add((i, y))
                self.obstacle_grid.add((self.width - 1 - i, y))
        for x in range(self.width):
            for i in range(robot_radius_cells):
                self.obstacle_grid.add((x, i))
                self.obstacle_grid.add((x, self.height - 1 - i))

        print(f"DEBUG: Cache de obstáculos (robusto) atualizado: {len(self.obstacle_grid)} células")
        
    def _is_in_forbidden_area(self, x: int, y: int) -> bool:
        """(CORRIGIDO) Verifica se uma célula da grade está na área proibida usando o cache."""
        return (x, y) in self.obstacle_grid
        
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
        """Implementação otimizada do algoritmo A* com caminhos simplificados"""
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
                raw_path = self._reconstruct_path(came_from, current)
                # 🎯 SOLUÇÃO B: Simplifica o caminho para reduzir waypoints
                simplified_path = self._simplify_path(raw_path)
                print(f"DEBUG: Caminho simplificado: {len(raw_path)} → {len(simplified_path)} pontos")
                
                # 🎯 SOLUÇÃO C: Suaviza curvas agudas para evitar travamentos
                final_path = self._smooth_curves(simplified_path)
                print(f"DEBUG: Caminho final suavizado: {len(simplified_path)} → {len(final_path)} pontos")
                
                return final_path
                
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
                
                # Se o vizinho não está na fila ou encontrou um caminho melhor
                if neighbor not in [item[1] for item in open_set] or tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self._heuristic(neighbor, goal)
                    
                    # Adiciona à fila de prioridade
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        print("DEBUG: Nenhum caminho encontrado pelo A*")
        return None

    def _simplify_path(self, path: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """🎯 SOLUÇÃO B: Simplifica o caminho removendo waypoints desnecessários"""
        if len(path) <= 2:
            return path
            
        simplified = [path[0]]  # Sempre mantém o início
        current_idx = 0
        
        while current_idx < len(path) - 1:
            # Procura o próximo ponto que não está em linha reta
            next_idx = current_idx + 1
            best_idx = next_idx
            
            # Verifica se pode "pular" pontos intermediários
            for i in range(current_idx + 2, len(path)):
                if self._can_skip_points(path[current_idx], path[i]):
                    best_idx = i
                else:
                    break
            
            simplified.append(path[best_idx])
            current_idx = best_idx
            
            if current_idx >= len(path) - 1:
                break
        
        # Sempre mantém o final
        if simplified[-1] != path[-1]:
            simplified.append(path[-1])
            
        return simplified

    def _smooth_curves(self, path: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """🎯 SOLUÇÃO C: Suaviza curvas agudas inserindo waypoints intermediários"""
        if len(path) <= 2:
            return path
            
        smoothed = [path[0]]  # Sempre mantém o início
        
        for i in range(1, len(path) - 1):
            current = path[i]
            prev = path[i - 1]
            next_point = path[i + 1]
            
            # Calcula ângulo entre os três pontos
            angle = self._calculate_angle_between_points(prev, current, next_point)
            
            # 🎯 DETECTA CURVAS AGRESSIVAS: Ângulos < 45° são muito fechados
            if angle < 45.0:
                print(f"🎯 CURVA AGRESSIVA DETECTADA: Ângulo {angle:.1f}° em waypoint {i}")
                
                # 🎯 INSERE WAYPOINTS INTERMEDIÁRIOS para suavizar a curva
                intermediate_points = self._generate_intermediate_points(prev, current, next_point, angle)
                
                # Adiciona pontos intermediários
                for inter_point in intermediate_points:
                    smoothed.append(inter_point)
                    print(f"🎯 WAYPOINT INTERMEDIÁRIO ADICIONADO: {inter_point}")
                
                print(f"🎯 CURVA SUAVIZADA: {len(intermediate_points)} pontos intermediários inseridos")
            else:
                # Ângulo aceitável, mantém o waypoint original
                smoothed.append(current)
        
        # Sempre mantém o final
        smoothed.append(path[-1])
        
        print(f"🎯 CAMINHO SUAVIZADO: {len(path)} → {len(smoothed)} pontos")
        return smoothed
    
    def _calculate_angle_between_points(self, p1: Tuple[int, int], p2: Tuple[int, int], p3: Tuple[int, int]) -> float:
        """Calcula o ângulo entre três pontos (p2 é o vértice)"""
        # Converte para coordenadas do mundo
        p1_world = (p1[0] * self.grid_size, p1[1] * self.grid_size)
        p2_world = (p2[0] * self.grid_size, p2[1] * self.grid_size)
        p3_world = (p3[0] * self.grid_size, p3[1] * self.grid_size)
        
        # Vetores dos dois lados
        v1 = (p1_world[0] - p2_world[0], p1_world[1] - p2_world[1])
        v2 = (p3_world[0] - p2_world[0], p3_world[1] - p2_world[1])
        
        # Produto escalar
        dot_product = v1[0] * v2[0] + v1[1] * v2[1]
        
        # Módulos dos vetores
        mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
        mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
        
        # Ângulo em radianos
        cos_angle = dot_product / (mag1 * mag2)
        cos_angle = max(-1.0, min(1.0, cos_angle))  # Evita erros numéricos
        
        angle_rad = math.acos(cos_angle)
        angle_deg = math.degrees(angle_rad)
        
        return angle_deg
    
    def _generate_intermediate_points(self, p1: Tuple[int, int], p2: Tuple[int, int], p3: Tuple[int, int], angle: float) -> List[Tuple[int, int]]:
        """Gera waypoints intermediários para suavizar curvas agudas"""
        # Converte para coordenadas do mundo
        p1_world = (p1[0] * self.grid_size, p1[1] * self.grid_size)
        p2_world = (p2[0] * self.grid_size, p2[1] * self.grid_size)
        p3_world = (p3[0] * self.grid_size, p3[1] * self.grid_size)
        
        # 🎯 SOLUÇÃO C MELHORADA: Dobrar pontos para navegação física
        # QUANTO MAIS FECHADA A CURVA, MAIS PONTOS INTERMEDIÁRIOS
        if angle < 30.0:
            num_points = 8  # Curva muito fechada: 8 pontos (DOBRADO de 4)
            print(f"🎯 CURVA MUITO FECHADA ({angle:.1f}°): 8 pontos intermediários")
        elif angle < 45.0:
            num_points = 6  # Curva fechada: 6 pontos (DOBRADO de 3)
            print(f"🎯 CURVA FECHADA ({angle:.1f}°): 6 pontos intermediários")
        else:
            num_points = 4  # Curva moderada: 4 pontos (DOBRADO de 2)
            print(f"🎯 CURVA MODERADA ({angle:.1f}°): 4 pontos intermediários")
        
        intermediate_points = []
        
        # 🎯 ALGORITMO DE CURVA SUAVE MELHORADO: Mais pontos para navegação física
        for i in range(1, num_points + 1):
            t = i / (num_points + 1)
            
            # 🎯 CURVA MAIS NATURAL: Usa interpolação quadrática
            # P1 → P2 → P3: Cria curva mais suave e redonda
            if t <= 0.5:
                # Primeira metade: P1 → P2 (mais suave)
                t_smooth = 2 * t * t  # Aceleração gradual
                x = p1_world[0] + t_smooth * (p2_world[0] - p1_world[0])
                y = p1_world[1] + t_smooth * (p2_world[1] - p1_world[1])
            else:
                # Segunda metade: P2 → P3 (mais suave)
                t_smooth = 1 - 2 * (1 - t) * (1 - t)  # Desaceleração gradual
                x = p2_world[0] + t_smooth * (p3_world[0] - p2_world[0])
                y = p2_world[1] + t_smooth * (p3_world[1] - p2_world[1])
            
            # Converte de volta para grid
            grid_x = int(x / self.grid_size)
            grid_y = int(y / self.grid_size)
            
            # Verifica se o ponto está dentro dos limites e não é obstáculo
            if (0 <= grid_x < self.width and 0 <= grid_y < self.height and 
                not self._is_in_forbidden_area(grid_x, grid_y)):
                intermediate_points.append((grid_x, grid_y))
        
        print(f"🎯 PONTOS INTERMEDIÁRIOS GERADOS: {len(intermediate_points)}/{num_points} válidos")
        return intermediate_points
    
    def _can_skip_points(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        """🎯 SOLUÇÃO B: Verifica se pode pular pontos intermediários (linha reta livre)"""
        # Converte para coordenadas do mundo
        start_world = (start[0] * self.grid_size, start[1] * self.grid_size)
        end_world = (end[0] * self.grid_size, end[1] * self.grid_size)
        
        # Verifica se a linha reta entre os pontos não passa por áreas proibidas
        # Usa amostragem para verificar pontos intermediários
        num_samples = max(3, int(self._calculate_world_distance(start_world, end_world) / (self.grid_size * 2)))
        
        for i in range(1, num_samples):
            t = i / num_samples
            sample_x = start_world[0] + t * (end_world[0] - start_world[0])
            sample_y = start_world[1] + t * (end_world[1] - start_world[1])
            
            # Converte de volta para grid
            sample_grid = (int(sample_x / self.grid_size), int(sample_y / self.grid_size))
            
            # Verifica se está em área proibida
            if self._is_in_forbidden_area(sample_grid[0], sample_grid[1]):
                return False
                
        return True
    
    def _calculate_world_distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calcula distância entre dois pontos em coordenadas do mundo"""
        return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
        
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