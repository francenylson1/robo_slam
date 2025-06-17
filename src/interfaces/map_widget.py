from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QPointF, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont, QCursor, QPolygon
from src.core.config import MAP_WIDTH, MAP_HEIGHT, MAP_SCALE, ROBOT_INITIAL_POSITION, ROBOT_INITIAL_ANGLE, DATABASE_PATH
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
        self.forbidden_areas = []  # Lista de polígonos
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
        """Finaliza o desenho da área proibida."""
        if self.drawing_forbidden and len(self.current_forbidden_area) > 2:
            self.forbidden_areas.append(self.current_forbidden_area)
        self.drawing_forbidden = False
        self.current_forbidden_area = []
        self.update()
        if hasattr(self, 'area_finished_callback') and self.area_finished_callback:
            self.area_finished_callback()
        
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
                self.current_forbidden_area.append((world_x, world_y))
                self.update()
            
    def mouseDoubleClickEvent(self, event):
        """Processa eventos de duplo clique do mouse."""
        if event.button() == Qt.MouseButton.LeftButton and self.drawing_forbidden:
            if len(self.current_forbidden_area) >= 3:
                self.forbidden_areas.append(self.current_forbidden_area)
                self.current_forbidden_area = []
                self.drawing_forbidden = False
                if self.area_finished_callback:
                    self.area_finished_callback()
                self.update()

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
                
        self.forbidden_areas = map_data.get('forbidden_areas', [])
        self.update()

    def save_map(self) -> Dict:
        """Salva os dados do mapa."""
        return {
            'points_of_interest': self.points_of_interest,
            'forbidden_areas': self.forbidden_areas
        }

    def _draw_robot(self, painter: QPainter):
        """Desenha o robô no mapa."""
        x, y = self.robot_position
        screen_x = int(x * self.scale)
        screen_y = int(y * self.scale)
        
        print(f"DEBUG: Desenhando robô em ({x}, {y}) -> ({screen_x}, {screen_y}) com ângulo {self.robot_angle}")
        
        # Desenha o corpo do robô (círculo azul)
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.setBrush(QBrush(QColor(0, 0, 255)))
        robot_size = 20  # Tamanho do robô em pixels
        painter.drawEllipse(screen_x - robot_size//2, screen_y - robot_size//2, robot_size, robot_size)
        
        # Desenha a direção do robô (linha vermelha)
        painter.setPen(QPen(QColor(255, 0, 0), 3))
        angle_rad = math.radians(self.robot_angle)
        direction_length = robot_size * 0.8  # 80% do tamanho do robô
        end_x = screen_x + direction_length * math.cos(angle_rad)
        end_y = screen_y + direction_length * math.sin(angle_rad)
        painter.drawLine(screen_x, screen_y, int(end_x), int(end_y))

    def _draw_forbidden_areas(self, painter: QPainter):
        """Desenha as áreas proibidas no mapa."""
        # Desenha as áreas proibidas existentes
        painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.PenStyle.DashLine))
        painter.setBrush(QBrush(QColor(255, 0, 0, 50)))  # Vermelho semi-transparente
        
        for area in self.forbidden_areas:
            points = [QPoint(int(x * self.scale), int(y * self.scale)) for x, y in area]
            polygon = QPolygon(points)
            painter.drawPolygon(polygon)
            
        # Desenha a área sendo criada
        if self.drawing_forbidden and len(self.current_forbidden_area) > 0:
            points = [QPoint(int(x * self.scale), int(y * self.scale)) for x, y in self.current_forbidden_area]
            polygon = QPolygon(points)
            painter.drawPolygon(polygon) 