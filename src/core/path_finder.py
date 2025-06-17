from typing import List, Tuple, Dict
import math

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
        print(f"DEBUG: PathFinder inicializado - Dimensões: {width}x{height}, Grid: {grid_size}m")
        
    def set_forbidden_areas(self, areas: List[List[Tuple[float, float]]]):
        """Define as áreas proibidas"""
        self.forbidden_areas = areas
        print(f"DEBUG: Áreas proibidas definidas: {len(areas)} áreas")
        
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
        """Encontra um caminho do ponto inicial ao objetivo evitando áreas proibidas"""
        print(f"DEBUG: Calculando caminho de {start} para {goal}")
        
        # Converte coordenadas do mundo para coordenadas da grade
        start_grid = (int(start[0] / self.grid_size), int(start[1] / self.grid_size))
        goal_grid = (int(goal[0] / self.grid_size), int(goal[1] / self.grid_size))
        
        print(f"DEBUG: Coordenadas da grade - Início: {start_grid}, Fim: {goal_grid}")
        
        # Verifica se o objetivo está dentro dos limites do mapa
        if not (0 <= goal_grid[0] < self.width and 0 <= goal_grid[1] < self.height):
            print(f"DEBUG: Objetivo fora dos limites do mapa: {goal_grid}")
            return [start, goal]  # Retorna caminho direto se objetivo estiver fora do mapa
            
        # Verifica se o objetivo está em uma área proibida
        if self._is_in_forbidden_area(goal_grid[0], goal_grid[1]):
            print(f"DEBUG: Objetivo dentro de área proibida: {goal_grid}")
            return [start, goal]  # Retorna caminho direto se objetivo estiver em área proibida
            
        # Inicializa as estruturas de dados
        open_set = {start_grid}
        closed_set = set()
        came_from = {}
        g_score = {start_grid: 0}
        f_score = {start_grid: self._heuristic(start_grid, goal_grid)}
        
        while open_set:
            # Encontra o nó com menor f_score
            current = min(open_set, key=lambda x: f_score.get(x, float('inf')))
            
            if current == goal_grid:
                print("DEBUG: Caminho encontrado!")
                path = self._reconstruct_path(came_from, current)
                # Converte de volta para coordenadas do mundo
                world_path = [(x * self.grid_size, y * self.grid_size) for x, y in path]
                print(f"DEBUG: Caminho final: {world_path}")
                return world_path
                
            open_set.remove(current)
            closed_set.add(current)
            
            # Explora os vizinhos
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)]:
                neighbor = (current[0] + dx, current[1] + dy)
                
                # Verifica se o vizinho é válido
                if not (0 <= neighbor[0] < self.width and 0 <= neighbor[1] < self.height):
                    continue
                    
                if self._is_in_forbidden_area(neighbor[0], neighbor[1]):
                    continue
                    
                if neighbor in closed_set:
                    continue
                    
                # Calcula o novo g_score
                tentative_g_score = g_score[current] + (1.4 if dx != 0 and dy != 0 else 1.0)
                
                if neighbor not in open_set:
                    open_set.add(neighbor)
                elif tentative_g_score >= g_score.get(neighbor, float('inf')):
                    continue
                    
                # Atualiza os scores
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = g_score[neighbor] + self._heuristic(neighbor, goal_grid)
                
        print("DEBUG: Nenhum caminho encontrado, retornando caminho direto")
        return [start, goal]  # Retorna caminho direto se não encontrar um caminho válido
        
    def _astar(self, start: Tuple[int, int], goal: Tuple[int, int], grid: Dict[Tuple[int, int], int]) -> List[Tuple[int, int]]:
        """Implementação do algoritmo A*"""
        # ... resto do código A* existente ... 

    def _is_in_forbidden_area(self, x: int, y: int) -> bool:
        """Verifica se um ponto da grade está em uma área proibida"""
        point = (x * self.grid_size, y * self.grid_size)
        for area in self.forbidden_areas:
            if self._is_point_in_polygon(point, area):
                return True
        return False
        
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