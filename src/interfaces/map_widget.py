from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QPointF, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont, QCursor, QPolygon
from src.core.config import MAP_WIDTH, MAP_HEIGHT, MAP_SCALE, ROBOT_INITIAL_POSITION, ROBOT_INITIAL_ANGLE, DATABASE_PATH, INTERFACE_ROBOT_SIZE, INTERFACE_DIRECTION_LENGTH
import math
import sys
import os
import sqlite3
from typing import Dict, List, Tuple, Callable, Optional

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class MapWidget(QWidget):
    def __init__(self, parent=None):
        """Inicializa o widget do mapa."""
        super().__init__(parent)
        self.setMinimumSize(600, 1200)  # Ajustado para melhor visualização dos grids maiores
        self.points_of_interest = {}  # {nome: (x, y, tipo)}
        self.forbidden_areas = []  # Lista de dicionários com id, nome, coordenadas
        self.robot_position = ROBOT_INITIAL_POSITION  # Usa a posição inicial definida em config.py
        self.robot_angle = ROBOT_INITIAL_ANGLE  # Usa o ângulo inicial definido em config.py
        self.scale = 56.66  # pixels por metro (ajustado para mostrar grids de 0.5m com 70% de aumento)
        self.add_point_mode = False
        self.point_clicked_callback: Optional[Callable[[float, float], None]] = None
        self.drawing_forbidden = False
        self.current_forbidden_area = []
        self.map_name = ""
        self.map_width = MAP_WIDTH
        self.map_height = MAP_HEIGHT
        self.add_point_mode = False
        self.edit_point_mode = False
        self.area_finished_callback: Optional[Callable[[], None]] = None
        self.selected_area_id = None  # ID da área selecionada
        self.area_clicked_callback: Optional[Callable[[int], None]] = None  # Callback para clique em área
        
    def update_robot_position(self, x: float, y: float, angle: float):
        """Atualiza a posição do robô no mapa."""
        self.robot_position = (x, y)
        self.robot_angle = angle
        self.update()
        
    def add_point_of_interest(self, name, position):
        """Adiciona um ponto de interesse ao mapa"""
        self.points_of_interest[name] = position
        self.update()
        
    def paintEvent(self, event):
        """Desenha o mapa, pontos de interesse e áreas proibidas"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Desenha o grid
        self._draw_grid(painter)
        
        # Desenha as áreas proibidas
        self._draw_forbidden_areas(painter)
        
        # Desenha a área proibida que está sendo criada
        self._draw_current_forbidden_area(painter)
        
        # Desenha os pontos de interesse
        for name, point_data in self.points_of_interest.items():
            x, y, point_type = point_data
            screen_x = int(x * self.scale)
            screen_y = int(y * self.scale)
            
            print(f"DEBUG: Desenhando ponto {name} em ({x}, {y}) -> ({screen_x}, {screen_y})")
            
            # Desenha o ponto
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.setBrush(QBrush(QColor(255, 0, 0)))
            painter.drawEllipse(screen_x - 5, screen_y - 5, 10, 10)
            
            # Desenha o nome e tipo
            painter.setPen(QPen(QColor(0, 0, 0)))
            painter.setFont(QFont('Arial', 8))
            painter.drawText(screen_x + 10, screen_y + 5, f"{name} ({point_type})")
            
        # Desenha o robô
        self._draw_robot(painter)
        
    def _draw_grid(self, painter: QPainter):
        """Desenha a grade do mapa."""
        painter.setPen(QPen(QColor(128, 128, 128), 1, Qt.PenStyle.DotLine))
        
        # Desenha linhas horizontais (12m de altura, grids de 0.5m)
        for y in range(0, 25):  # 12m / 0.5m = 24 linhas + 1
            screen_y = int(y * self.scale * 0.5)  # 0.5m por grid
            painter.drawLine(0, screen_y, self.width(), screen_y)
            
        # Desenha linhas verticais (6m de largura, grids de 0.5m)
        for x in range(0, 13):  # 6m / 0.5m = 12 linhas + 1
            screen_x = int(x * self.scale * 0.5)  # 0.5m por grid
            painter.drawLine(screen_x, 0, screen_x, self.height())
        
        # Desenha números nas linhas do grid
        self._draw_grid_numbers(painter)
            
    def _draw_grid_numbers(self, painter: QPainter):
        """Desenha os números da grade do mapa."""
        painter.setPen(QPen(QColor(0, 0, 0)))
        painter.setFont(QFont('Arial', 8))
        
        # Desenha números horizontais (0 a 6m)
        for x in range(0, 13):  # 6m / 0.5m = 12 linhas + 1
            screen_x = int(x * self.scale * 0.5)
            painter.drawText(screen_x + 5, 15, f"{x * 0.5:.1f}")
            
        # Desenha números verticais (0 a 12m)
        for y in range(0, 25):  # 12m / 0.5m = 24 linhas + 1
            screen_y = int(y * self.scale * 0.5)
            painter.drawText(5, screen_y - 5, f"{y * 0.5:.1f}")
        
    def _world_to_screen_x(self, x):
        """Converte coordenada X do mundo para tela."""
        return int(x * MAP_SCALE)
        
    def _world_to_screen_y(self, y):
        """Converte coordenada Y do mundo para tela."""
        return int(self.height() - y * MAP_SCALE)
        
    def _screen_to_world_x(self, screen_x):
        """Converte coordenada X da tela para mundo."""
        return screen_x / MAP_SCALE
        
    def _screen_to_world_y(self, screen_y):
        """Converte coordenada Y da tela para mundo."""
        return (self.height() - screen_y) / MAP_SCALE
        
    def start_drawing_forbidden_area(self):
        """Inicia o desenho de uma área proibida."""
        self.drawing_forbidden = True
        self.current_forbidden_area = []
        
    def add_point_to_forbidden_area(self, x, y):
        """Adiciona um ponto à área proibida sendo desenhada."""
        if self.drawing_forbidden:
            world_x = self._screen_to_world_x(x)
            world_y = self._screen_to_world_y(y)
            self.current_forbidden_area.append((world_x, world_y))
            self.update()
            
    def finish_forbidden_area(self):
        """Finaliza o desenho da área proibida e dispara o callback."""
        # A área não é mais adicionada diretamente aqui.
        # A responsabilidade é transferida para o main_window,
        # que a salvará no DB e depois atualizará o mapa.
        self.drawing_forbidden = False
        # Não limpa a current_forbidden_area aqui para que o main_window possa lê-la
        self.update()
        if self.area_finished_callback:
            self.area_finished_callback()
        # Limpa a área atual *depois* do callback ter sido processado
        self.current_forbidden_area = []
        
    def mousePressEvent(self, event):
        """Processa eventos de clique do mouse."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Converte as coordenadas do clique para coordenadas do mundo
            world_x = event.x() / self.scale
            world_y = event.y() / self.scale
            
            print(f"DEBUG: Clique em ({world_x}, {world_y})")
            
            if self.add_point_mode:
                if self.point_clicked_callback:
                    self.point_clicked_callback(world_x, world_y)
            elif self.drawing_forbidden:
                # Apenas adiciona o ponto. A finalização é com duplo clique.
                self.current_forbidden_area.append((world_x, world_y))
                self.update()
            else:
                # Verifica se clicou em uma área proibida
                clicked_area_id = self._check_area_click(world_x, world_y)
                if clicked_area_id is not None:
                    self.selected_area_id = clicked_area_id
                    self.update()
                    if self.area_clicked_callback:
                        self.area_clicked_callback(clicked_area_id)
                    print(f"DEBUG: Área {clicked_area_id} selecionada")
                else:
                    # Se clicou fora de qualquer área, deseleciona
                    if self.selected_area_id is not None:
                        self.selected_area_id = None
                        self.update()
                        print("DEBUG: Área deselecionada")
    
    def _check_area_click(self, world_x: float, world_y: float) -> Optional[int]:
        """Verifica se o clique foi dentro de uma área proibida."""
        from PyQt5.QtGui import QPolygon
        
        for area_data in self.forbidden_areas:
            if isinstance(area_data, dict):
                area_id = area_data.get('id', 0)
                coordinates = area_data.get('coordenadas', [])
            else:
                area_id = 0
                coordinates = area_data
            
            if not coordinates:
                continue
                
            # Cria um polígono com as coordenadas da área
            try:
                points = [QPoint(int(float(x) * self.scale), int(float(y) * self.scale)) for x, y in coordinates]
                polygon = QPolygon(points)
                
                # Verifica se o ponto está dentro do polígono
                if polygon.containsPoint(QPoint(int(world_x * self.scale), int(world_y * self.scale)), Qt.FillRule.OddEvenFill):
                    return area_id
            except (TypeError, ValueError) as e:
                print(f"DEBUG: Erro ao verificar clique em área {area_id}: {e}")
                continue
        
        return None

    def mouseDoubleClickEvent(self, event):
        """Processa eventos de duplo clique do mouse."""
        if event.button() == Qt.MouseButton.LeftButton and self.drawing_forbidden:
            if len(self.current_forbidden_area) >= 3:
                # Dispara o processo de finalização com duplo clique.
                self.finish_forbidden_area()

    def load_map(self, map_data: Dict):
        """Carrega os dados do mapa."""
        print(f"DEBUG: Carregando mapa: {map_data}")
        self.points_of_interest = {}
        for name, data in map_data.get('points_of_interest', {}).items():
            if isinstance(data, tuple):
                if len(data) == 2:
                    # Formato antigo: (x, y)
                    x, y = data
                    point_type = "Mesa"  # Tipo padrão
                else:
                    # Novo formato: (x, y, tipo)
                    x, y, point_type = data
                self.points_of_interest[name] = (float(x), float(y), point_type)
                print(f"DEBUG: Ponto carregado: {name} em ({x}, {y}) do tipo {point_type}")
                
        # Carrega áreas proibidas - suporta formato antigo e novo
        forbidden_areas = map_data.get('forbidden_areas', [])
        self.forbidden_areas = []
        
        for area in forbidden_areas:
            if isinstance(area, dict):
                # Novo formato: dicionário com id, nome, coordenadas
                self.forbidden_areas.append(area)
            else:
                # Formato antigo: lista de coordenadas - converte para novo formato
                area_dict = {
                    'id': 0,  # ID temporário
                    'nome': f'Área {len(self.forbidden_areas) + 1}',
                    'coordenadas': area
                }
                self.forbidden_areas.append(area_dict)
        
        self.update()

    def save_map(self) -> Dict:
        """Salva os dados do mapa."""
        # Converte áreas proibidas para formato compatível
        forbidden_areas_compat = []
        for area_data in self.forbidden_areas:
            if isinstance(area_data, dict):
                # Novo formato: extrai apenas as coordenadas para compatibilidade
                forbidden_areas_compat.append(area_data.get('coordenadas', []))
            else:
                # Formato antigo: mantém como está
                forbidden_areas_compat.append(area_data)
        
        return {
            'points_of_interest': self.points_of_interest,
            'forbidden_areas': forbidden_areas_compat
        }

    def _draw_robot(self, painter: QPainter):
        """Desenha o robô no mapa."""
        x, y = self.robot_position
        screen_x = int(x * self.scale)
        screen_y = int(y * self.scale)
        
        print(f"DEBUG: Desenhando robô em ({x}, {y}) -> ({screen_x}, {screen_y}) com ângulo {self.robot_angle}°")
        
        # Desenha o corpo do robô (círculo azul)
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.setBrush(QBrush(QColor(0, 0, 255)))
        robot_size = INTERFACE_ROBOT_SIZE
        painter.drawEllipse(screen_x - robot_size//2, screen_y - robot_size//2, robot_size, robot_size)
        
        # Desenha a direção do robô como uma linha com seta no final
        painter.setPen(QPen(QColor(255, 0, 0), 3))
        painter.setBrush(QBrush(QColor(255, 0, 0)))
        
        direction_length = INTERFACE_DIRECTION_LENGTH  # 30 pixels
        arrow_head_length = 8  # tamanho da cabeça da seta
        arrow_head_width = 6   # largura da cabeça da seta
        angle_rad = math.radians(self.robot_angle)
        
        # Calcula o ponto final da linha (antes da seta)
        line_end_x = screen_x + (direction_length - arrow_head_length) * math.cos(angle_rad)
        line_end_y = screen_y + (direction_length - arrow_head_length) * math.sin(angle_rad)
        
        # Desenha a linha principal
        painter.drawLine(screen_x, screen_y, int(line_end_x), int(line_end_y))
        
        # Calcula os pontos da seta triangular
        tip_x = screen_x + direction_length * math.cos(angle_rad)
        tip_y = screen_y + direction_length * math.sin(angle_rad)
        
        # Pontos da base da seta (perpendiculares à direção)
        base_angle1 = angle_rad + math.radians(90)
        base_angle2 = angle_rad - math.radians(90)
        base1_x = line_end_x + (arrow_head_width/2) * math.cos(base_angle1)
        base1_y = line_end_y + (arrow_head_width/2) * math.sin(base_angle1)
        base2_x = line_end_x + (arrow_head_width/2) * math.cos(base_angle2)
        base2_y = line_end_y + (arrow_head_width/2) * math.sin(base_angle2)
        
        # Desenha a seta triangular
        arrow = QPolygon([
            QPoint(int(tip_x), int(tip_y)),
            QPoint(int(base1_x), int(base1_y)),
            QPoint(int(base2_x), int(base2_y))
        ])
        painter.drawPolygon(arrow)

    def _draw_forbidden_areas(self, painter: QPainter):
        """Desenha as áreas proibidas no mapa."""
        for area_data in self.forbidden_areas:
            area_id = area_data.get('id')
            coordinates = area_data.get('coordenadas', [])
            
            if not coordinates or len(coordinates) < 2:
                continue

            # Converte as coordenadas do mundo para a tela
            screen_points = [QPoint(int(float(x) * self.scale), int(float(y) * self.scale)) for x, y in coordinates]
            
            # Define a cor e o pincel
            pen = QPen(QColor(255, 0, 0, 100), 2, Qt.PenStyle.SolidLine)
            brush = QBrush(QColor(255, 0, 0, 50))

            # Se a área estiver selecionada, muda a cor
            if self.selected_area_id == area_id:
                pen = QPen(QColor(0, 255, 0, 200), 3, Qt.PenStyle.SolidLine)
                brush = QBrush(QColor(0, 255, 0, 100))
            
            painter.setPen(pen)
            painter.setBrush(brush)
            
            # Cria e desenha o polígono
            polygon = QPolygon(screen_points)
            painter.drawPolygon(polygon)

    def _draw_current_forbidden_area(self, painter: QPainter):
        """Desenha a área proibida que está sendo criada pelo usuário."""
        if self.drawing_forbidden and len(self.current_forbidden_area) > 0:
            painter.setPen(QPen(QColor(0, 0, 255, 150), 2, Qt.PenStyle.DashLine))  # Azul para área em criação
            painter.setBrush(Qt.BrushStyle.NoBrush) # Sem preenchimento para a área em criação

            try:
                points = [QPoint(int(float(x) * self.scale), int(float(y) * self.scale)) for x, y in self.current_forbidden_area]
                
                # Desenha as linhas que conectam os pontos
                for i in range(len(points) - 1):
                    painter.drawLine(points[i], points[i+1])

                # Desenha os vértices da área em criação
                painter.setPen(QPen(QColor(0, 0, 255), 4)) # Pontos azuis maiores
                for point in points:
                    painter.drawPoint(point)

            except (TypeError, ValueError) as e:
                print(f"DEBUG: Erro ao desenhar a área proibida em andamento: {e}")

    def add_forbidden_area(self, area_data: Dict):
        """Adiciona uma área proibida com dados completos."""
        self.forbidden_areas.append(area_data)
        self.update()
        
    def remove_forbidden_area(self, area_id: int) -> bool:
        """Remove uma área proibida pelo ID."""
        for i, area_data in enumerate(self.forbidden_areas):
            if isinstance(area_data, dict) and area_data.get('id') == area_id:
                del self.forbidden_areas[i]
                if self.selected_area_id == area_id:
                    self.selected_area_id = None
                self.update()
                return True
        return False
        
    def get_selected_area(self) -> Optional[Dict]:
        """Retorna a área proibida selecionada."""
        if self.selected_area_id is None:
            return None
            
        for area_data in self.forbidden_areas:
            if isinstance(area_data, dict) and area_data.get('id') == self.selected_area_id:
                return area_data
        return None
        
    def get_forbidden_areas_list(self) -> List[Dict]:
        """Retorna lista de todas as áreas proibidas com dados completos."""
        return [area for area in self.forbidden_areas if isinstance(area, dict)] 