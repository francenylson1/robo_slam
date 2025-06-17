from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont
from src.core.config import MAP_WIDTH, MAP_HEIGHT, MAP_SCALE, ROBOT_INITIAL_POSITION, ROBOT_INITIAL_ANGLE, DATABASE_PATH
import math
import sys
import os
import sqlite3
from typing import Dict, List, Tuple

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class MapWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.robot_position = ROBOT_INITIAL_POSITION
        self.robot_angle = ROBOT_INITIAL_ANGLE
        self.points_of_interest = {}  # nome -> (x, y)
        self.forbidden_areas = []     # lista de polígonos [(x1,y1), (x2,y2), ...]
        self.drawing_forbidden = False
        self.current_forbidden_area = []
        self.map_name = ""
        self.map_width = MAP_WIDTH
        self.map_height = MAP_HEIGHT
        self.setMinimumSize(800, 600)
        
    def update_robot_position(self, position, angle):
        """Atualiza a posição do robô no mapa"""
        self.robot_position = position
        self.robot_angle = angle
        self.update()
        
    def add_point_of_interest(self, name, position):
        """Adiciona um ponto de interesse ao mapa"""
        self.points_of_interest[name] = position
        self.update()
        
    def paintEvent(self, event):
        """Desenha o mapa, pontos de interesse e áreas proibidas"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Desenha o grid
        self._draw_grid(painter)
        
        # Desenha as áreas proibidas
        for area in self.forbidden_areas:
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.setBrush(QBrush(QColor(255, 0, 0, 50)))  # Vermelho semi-transparente
            points = [QPointF(self._world_to_screen_x(x), self._world_to_screen_y(y))
                     for x, y in area]
            painter.drawPolygon(points)
            
        # Desenha os pontos de interesse
        for name, (x, y) in self.points_of_interest.items():
            # Desenha o ponto
            painter.setPen(QPen(QColor(0, 0, 255), 2))
            painter.setBrush(QBrush(QColor(0, 0, 255)))
            screen_x = self._world_to_screen_x(x)
            screen_y = self._world_to_screen_y(y)
            painter.drawEllipse(QPointF(screen_x, screen_y), 5, 5)
            
            # Desenha o nome do ponto
            painter.setPen(QPen(QColor(0, 0, 0)))
            painter.setFont(QFont('Arial', 8))
            painter.drawText(QPointF(screen_x + 10, screen_y), name)
            
        # Desenha o robô
        painter.setPen(QPen(QColor(0, 255, 0), 2))
        painter.setBrush(QBrush(QColor(0, 255, 0)))
        robot_x = self._world_to_screen_x(self.robot_position[0])
        robot_y = self._world_to_screen_y(self.robot_position[1])
        painter.drawEllipse(QPointF(robot_x, robot_y), 8, 8)
        
        # Desenha a direção do robô
        angle_rad = math.radians(self.robot_angle)
        end_x = robot_x + 20 * math.cos(angle_rad)
        end_y = robot_y - 20 * math.sin(angle_rad)
        painter.drawLine(int(robot_x), int(robot_y), int(end_x), int(end_y))
        
        # Área sendo desenhada
        if self.drawing_forbidden and len(self.current_forbidden_area) > 1:
            painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.DashLine))
            points = [QPointF(self._world_to_screen_x(x), self._world_to_screen_y(y))
                     for x, y in self.current_forbidden_area]
            painter.drawPolyline(points)
        
    def _draw_grid(self, painter):
        """Desenha o grid do mapa com divisões de 0.5 metro."""
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        
        step = 0.5  # metros
        num_cols = int(MAP_WIDTH / step)
        num_rows = int(MAP_HEIGHT / step)
        
        # Linhas horizontais
        for i in range(num_rows + 1):
            y = i * step
            screen_y = self._world_to_screen_y(y)
            painter.drawLine(0, screen_y, self.width(), screen_y)
        
        # Linhas verticais
        for i in range(num_cols + 1):
            x = i * step
            screen_x = self._world_to_screen_x(x)
            painter.drawLine(screen_x, 0, screen_x, self.height())
        
        # Desenha números nas linhas do grid
        painter.setPen(QPen(QColor(100, 100, 100)))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        
        # Números horizontais (metros)
        for i in range(num_cols + 1):
            x = i * step
            screen_x = self._world_to_screen_x(x)
            painter.drawText(screen_x + 5, 15, f"{x:.1f}")
        
        # Números verticais (metros)
        for i in range(num_rows + 1):
            y = i * step
            screen_y = self._world_to_screen_y(y)
            painter.drawText(5, screen_y - 5, f"{y:.1f}")
            
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
        """Manipula eventos de clique do mouse."""
        if hasattr(self, 'add_point_mode') and self.add_point_mode:
            # Captura o clique para ponto de interesse
            world_x = self._screen_to_world_x(event.x())
            world_y = self._screen_to_world_y(event.y())
            if hasattr(self, 'point_clicked_callback') and self.point_clicked_callback:
                self.point_clicked_callback(world_x, world_y)
            self.add_point_mode = False
            self.point_clicked_callback = None
            return
        if self.drawing_forbidden:
            self.add_point_to_forbidden_area(event.x(), event.y())
            
    def mouseDoubleClickEvent(self, event):
        """Manipula eventos de duplo clique do mouse."""
        if self.drawing_forbidden:
            self.finish_forbidden_area()

    def load_map(self, map_data: Dict):
        """Carrega um mapa no widget"""
        self.map_name = map_data['nome']
        self.map_width = map_data['largura']
        self.map_height = map_data['comprimento']
        
        # Carrega pontos de interesse
        self.points_of_interest = {}
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT nome, x, y FROM pontos_interesse 
                    WHERE mapa_id = ?
                """, (map_data['id'],))
                for row in cursor.fetchall():
                    self.points_of_interest[row[0]] = (row[1], row[2])
        except Exception as e:
            print(f"Erro ao carregar pontos de interesse: {e}")
            
        # Carrega áreas proibidas
        self.forbidden_areas = []
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT coordenadas FROM areas_proibidas 
                    WHERE mapa_id = ? AND ativo = 1
                """, (map_data['id'],))
                for row in cursor.fetchall():
                    coords_str = row[0]
                    coords_list = eval(coords_str)
                    self.forbidden_areas.append([(float(x), float(y)) for x, y in coords_list])
        except Exception as e:
            print(f"Erro ao carregar áreas proibidas: {e}")
            
        self.update() 