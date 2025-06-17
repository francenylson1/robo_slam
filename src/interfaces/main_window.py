from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QComboBox, QMessageBox,
                             QGroupBox, QGridLayout, QInputDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QCursor
import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.robot_navigator import RobotNavigator
from src.core.config import *
from src.interfaces.add_point_dialog import AddPointDialog
from src.interfaces.map_widget import MapWidget
from src.core.map_manager import MapManager
import math
from src.interfaces.edit_point_dialog import EditPointDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Inicializa atributos
        self.current_map = None
        self.selected_destination = None
        self.navigation_active = False
        
        # Inicializa o MapManager
        self.map_manager = MapManager()

        # Configuração da janela
        self.setWindowTitle("Robô Garçom Autônomo")
        self.setGeometry(100, 100, 1200, 800)
        
        # Layout principal
        main_layout = QHBoxLayout()
        
        # Área do mapa (lado esquerdo)
        map_layout = QVBoxLayout()
        self.map_widget = MapWidget()
        map_layout.addWidget(self.map_widget)
        
        # Barra de status do mapa
        map_status_layout = QHBoxLayout()
        self.status_label = QLabel("Modo: Manual")
        map_status_layout.addWidget(self.status_label)
        self.mode_button = QPushButton("Alternar Modo")
        self.mode_button.clicked.connect(self._toggle_mode)
        map_status_layout.addWidget(self.mode_button)
        map_layout.addLayout(map_status_layout)
        
        # Painel de controle (lado direito)
        control_panel = QGroupBox("Controles")
        control_layout = QVBoxLayout()
        
        # Grupo de Pontos de Interesse
        poi_group = QGroupBox("Pontos de Interesse")
        poi_layout = QVBoxLayout()
        
        # Lista de pontos
        self.poi_combo = QComboBox()
        poi_layout.addWidget(QLabel("Pontos disponíveis:"))
        poi_layout.addWidget(self.poi_combo)
        
        # Botões de pontos
        poi_buttons = QGridLayout()
        add_poi_btn = QPushButton("Adicionar Ponto")
        add_poi_btn.clicked.connect(self._add_point_of_interest)
        delete_poi_btn = QPushButton("Excluir Ponto")
        delete_poi_btn.clicked.connect(self._delete_point_of_interest)
        
        poi_buttons.addWidget(add_poi_btn, 0, 0)
        poi_buttons.addWidget(delete_poi_btn, 0, 1)
        poi_layout.addLayout(poi_buttons)
        poi_group.setLayout(poi_layout)
        
        # Grupo de Áreas Proibidas
        forbidden_group = QGroupBox("Áreas Proibidas")
        forbidden_layout = QVBoxLayout()
        
        forbidden_buttons = QGridLayout()
        add_forbidden_btn = QPushButton("Adicionar Área")
        add_forbidden_btn.clicked.connect(self._add_forbidden_area)
        delete_forbidden_btn = QPushButton("Excluir Área")
        delete_forbidden_btn.clicked.connect(self._delete_forbidden_area)
        
        forbidden_buttons.addWidget(add_forbidden_btn, 0, 0)
        forbidden_buttons.addWidget(delete_forbidden_btn, 0, 1)
        forbidden_layout.addLayout(forbidden_buttons)
        forbidden_group.setLayout(forbidden_layout)

        # Grupo de Gerenciamento de Mapas
        map_management_group = QGroupBox("Gerenciar Mapas")
        map_management_layout = QGridLayout()

        save_map_btn = QPushButton("Salvar Mapa")
        save_map_btn.clicked.connect(self._save_map)
        load_map_btn = QPushButton("Carregar Último Mapa")
        load_map_btn.clicked.connect(self._load_active_map)

        map_management_layout.addWidget(save_map_btn, 0, 0)
        map_management_layout.addWidget(load_map_btn, 0, 1)
        map_management_group.setLayout(map_management_layout)
        
        # Grupo de Navegação
        nav_group = QGroupBox("Navegação")
        nav_layout = QVBoxLayout()
        
        # Campo de seleção de destino
        destination_layout = QHBoxLayout()
        destination_layout.addWidget(QLabel("Destino:"))
        self.destination_combo = QComboBox()
        destination_layout.addWidget(self.destination_combo)
        nav_layout.addLayout(destination_layout)

        nav_buttons = QGridLayout()
        start_nav_btn = QPushButton("Iniciar Navegação")
        start_nav_btn.clicked.connect(self._start_navigation)
        stop_nav_btn = QPushButton("Parar")
        stop_nav_btn.clicked.connect(self._stop_robot)
        
        nav_buttons.addWidget(start_nav_btn, 0, 0)
        nav_buttons.addWidget(stop_nav_btn, 0, 1)
        nav_layout.addLayout(nav_buttons)
        nav_group.setLayout(nav_layout)
        
        # Adiciona todos os grupos ao painel de controle
        control_layout.addWidget(poi_group)
        control_layout.addWidget(forbidden_group)
        control_layout.addWidget(map_management_group)
        control_layout.addWidget(nav_group)
        control_layout.addStretch()
        control_panel.setLayout(control_layout)
        
        # Adiciona os painéis ao layout principal
        main_layout.addLayout(map_layout, stretch=2)
        main_layout.addWidget(control_panel, stretch=1)
        
        # Define o layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Inicializa o navegador
        self.navigator = RobotNavigator()
        
        # Tenta carregar o último mapa ativo ao iniciar
        self._load_active_map()
        
        # Inicia o timer de atualização
        self._update()

    def _load_active_map(self):
        """Carrega o mapa ativo ou permite seleção de um mapa"""
        map_names = self.map_manager.get_all_map_names()
        
        if map_names:
            # Permite ao usuário selecionar um mapa
            map_name, ok = QInputDialog.getItem(
                self, "Carregar Mapa", "Selecione um mapa para carregar:", map_names, 0, False
            )
            if ok and map_name:
                # Carrega o mapa selecionado
                self.map_manager.load_map_by_name(map_name)
                active_map = self.map_manager.get_active_map()
                if active_map:
                    self.current_map = active_map
                    # Carrega os pontos de interesse e áreas proibidas
                    points_of_interest, forbidden_areas, _ = self.map_manager.load_active_map()
                    map_data = {
                        'points_of_interest': points_of_interest,
                        'forbidden_areas': forbidden_areas
                    }
                    print(f"DEBUG: Carregando dados do mapa: {map_data}")
                    self.map_widget.load_map(map_data)
                    self._update_points_list()
                    self._update_destination_combo()
                    self.status_label.setText(f"Mapa carregado: {active_map['nome']}")
                else:
                    self.status_label.setText("Erro ao carregar mapa")
            else:
                # Se o usuário cancelar, carrega o mapa ativo
                active_map = self.map_manager.get_active_map()
                if active_map:
                    self.current_map = active_map
                    # Carrega os pontos de interesse e áreas proibidas
                    points_of_interest, forbidden_areas, _ = self.map_manager.load_active_map()
                    map_data = {
                        'points_of_interest': points_of_interest,
                        'forbidden_areas': forbidden_areas
                    }
                    print(f"DEBUG: Carregando dados do mapa: {map_data}")
                    self.map_widget.load_map(map_data)
                    self._update_points_list()
                    self._update_destination_combo()
                    self.status_label.setText(f"Mapa carregado: {active_map['nome']}")
                else:
                    self.status_label.setText("Nenhum mapa ativo encontrado")
        else:
            self.status_label.setText("Nenhum mapa encontrado. Crie um novo mapa.")
            
    def _update_points_list(self):
        """Atualiza a lista de pontos de interesse."""
        self.poi_combo.clear()
        for name, point_data in self.map_widget.points_of_interest.items():
            x, y, point_type = point_data
            self.poi_combo.addItem(f"{name} ({x:.2f}, {y:.2f}) - {point_type}")
            
    def _update_destination_combo(self):
        """Atualiza o combo box de destino."""
        self.destination_combo.clear()
        for name, point_data in self.map_widget.points_of_interest.items():
            x, y, point_type = point_data
            self.destination_combo.addItem(f"{name} ({x:.2f}, {y:.2f}) - {point_type}")
            
    def _update(self):
        """Atualiza o estado do robô e a interface"""
        if self.navigation_active:
            print("DEBUG: Atualizando navegação...")
            # Atualiza o navegador
            self.navigator.update()
            
            # Atualiza a posição do robô no mapa
            self.map_widget.robot_position = self.navigator.current_position
            self.map_widget.robot_angle = self.navigator.current_angle
            self.map_widget.update()
            
            # Atualiza o status
            if not self.navigator.navigation_active:
                self.navigation_active = False
                self.status_label.setText("Navegação concluída")
                print("DEBUG: Navegação finalizada")
                
        # Agenda a próxima atualização
        QTimer.singleShot(100, self._update)  # 100ms = 10Hz
        
    def _toggle_mode(self):
        """Alterna entre modo manual e autônomo."""
        self.navigator.set_autonomous_mode(not self.navigator.is_autonomous)
        if self.navigator.is_autonomous:
            self.mode_button.setText("Modo Autônomo")
        else:
            self.mode_button.setText("Modo Manual")
            
    def _add_point_of_interest(self):
        """Ativa modo de adição de ponto de interesse pelo clique no mapa."""
        self.status_label.setText("Clique no mapa para definir o ponto de interesse.")
        self.map_widget.setCursor(Qt.CursorShape.CrossCursor)
        self.map_widget.add_point_mode = True
        self.map_widget.point_clicked_callback = self._on_map_point_clicked

    def _on_map_point_clicked(self, x, y):
        """Abre o diálogo de ponto de interesse já com as coordenadas preenchidas."""
        self.map_widget.setCursor(Qt.CursorShape.ArrowCursor)
        self.status_label.setText("Modo: Manual" if not self.navigator.is_autonomous else "Modo: Autônomo")
        self.map_widget.add_point_mode = False
        self.map_widget.point_clicked_callback = None
        
        dialog = AddPointDialog(self)
        # Preenche os campos de coordenadas (convertendo para centímetros)
        dialog.x_spin.setValue(int(x * 100))
        dialog.y_spin.setValue(int(y * 100))
        if dialog.exec_():
            name, position, point_type = dialog.get_point_data()
            if name:  # Verifica se o nome não está vazio
                print(f"DEBUG: Adicionando ponto {name} em ({x}, {y}) do tipo {point_type}")
                self.map_widget.points_of_interest[name] = (x, y, point_type)
                self.map_widget.update()  # Força a atualização do mapa
                self._update_points_list()
                self._update_destination_combo()
            else:
                QMessageBox.warning(self, "Aviso", "O nome do ponto não pode ser vazio!")
            
    def _delete_point_of_interest(self):
        """Exclui o ponto de interesse selecionado."""
        selected = self.poi_combo.currentText()
        if not selected:
            QMessageBox.warning(self, "Aviso", "Selecione um ponto para excluir!")
            return
            
        point_name = selected.split(" (")[0]
        reply = QMessageBox.question(
            self, 'Confirmar Exclusão',
            f'Tem certeza que deseja excluir o ponto "{point_name}"?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                del self.map_widget.points_of_interest[point_name]
                self.map_widget.update()  # Força a atualização imediata do mapa
                self._update_points_list()
                self._update_destination_combo()
                QMessageBox.information(self, "Sucesso", f"Ponto '{point_name}' excluído com sucesso!")
            except KeyError:
                QMessageBox.warning(self, "Erro", f"Erro ao excluir o ponto '{point_name}'!")
            
    def _add_forbidden_area(self):
        """Ativa modo de adição de área proibida pelo clique no mapa."""
        self.status_label.setText("Clique para marcar os vértices da área proibida. Dê duplo clique para finalizar.")
        self.map_widget.setCursor(Qt.CursorShape.CrossCursor)
        self.map_widget.start_drawing_forbidden_area()
        self.map_widget.area_finished_callback = self._on_area_finished

    def _on_area_finished(self):
        """Finaliza o modo de adição de área proibida."""
        self.map_widget.setCursor(Qt.CursorShape.ArrowCursor)
        self.status_label.setText("Modo: Manual" if not self.navigator.is_autonomous else "Modo: Autônomo")
        self.map_widget.area_finished_callback = None

    def _delete_forbidden_area(self):
        """Remove uma área proibida."""
        if not self.map_widget.forbidden_areas:
            QMessageBox.warning(self, "Aviso", "Não há áreas proibidas para excluir!")
            return
            
        # TODO: Implementar seleção visual da área a ser excluída
        # Por enquanto, remove a última área adicionada
        self.map_widget.forbidden_areas.pop()
        self.map_widget.update()

    def _save_map(self):
        """Salva o mapa atual no banco de dados."""
        map_name, ok = QInputDialog.getText(self, "Salvar Mapa", "Nome do Mapa:")
        if ok and map_name:
            self.map_manager.save_map(
                map_name,
                self.map_widget.points_of_interest,
                self.map_widget.forbidden_areas
            )
            QMessageBox.information(self, "Salvar Mapa", f"Mapa '{map_name}' salvo com sucesso!")
        elif not map_name and ok:
            QMessageBox.warning(self, "Aviso", "O nome do mapa não pode ser vazio!")

    def _start_navigation(self):
        """Inicia a navegação autônoma"""
        print("DEBUG: Iniciando navegação...")
        
        if not self.current_map:
            print("DEBUG: Erro - Nenhum mapa carregado")
            return
            
        if not self.destination_combo.currentText():
            print("DEBUG: Erro - Nenhum destino selecionado")
            return
            
        # Obtém o destino selecionado
        destination_name = self.destination_combo.currentText()
        destination = self.map_widget.points_of_interest.get(destination_name)
        
        if not destination:
            print(f"DEBUG: Erro - Destino '{destination_name}' não encontrado")
            return
            
        print(f"DEBUG: Destino selecionado: {destination_name} em {destination}")
        
        # Obtém as áreas proibidas do mapa atual
        forbidden_areas = self.map_manager.get_forbidden_areas(self.current_map['id'])
        print(f"DEBUG: Áreas proibidas carregadas: {len(forbidden_areas)}")
        
        # Configura as áreas proibidas no navegador
        self.navigator.set_forbidden_areas(forbidden_areas)
        
        # Inicia a navegação
        self.navigator.navigate_to_and_return(destination, ROBOT_INITIAL_POSITION)
        self.navigation_active = True
        self.status_label.setText("Navegando...")
        print("DEBUG: Navegação iniciada com sucesso")
            
    def _stop_robot(self):
        """Para o robô."""
        self.navigator.motors.stop()
            
    def closeEvent(self, event):
        """Limpa recursos ao fechar a janela."""
        self.navigator.motors.cleanup()
        self.map_manager.close()
        event.accept()

    def _navigate_to_destination(self):
        """Navega para o destino selecionado."""
        destination = self.destination_combo.currentText()
        if not destination:
            return
            
        point_name = destination.split(" (")[0]
        point_data = self.map_widget.points_of_interest[point_name]
        x, y, point_type = point_data
        
        self.navigator.set_destination((x, y))
        self.navigator.start_navigation() 