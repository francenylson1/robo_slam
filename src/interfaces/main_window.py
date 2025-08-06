from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QComboBox, QMessageBox,
                             QGroupBox, QGridLayout, QInputDialog, QProgressBar, QSlider)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QCursor
import sys
import os
import time
import json

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.robot_navigator import RobotNavigator
from src.core.config import *
from src.interfaces.add_point_dialog import AddPointDialog
from src.interfaces.map_widget import MapWidget
from src.core.map_manager import MapManager
import math
from src.interfaces.edit_point_dialog import EditPointDialog
from src.interfaces.calibration_window import CalibrationWindow # <-- 1. IMPORTAR

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Inicializa atributos
        self.current_map = None
        self.selected_destination = None
        self.navigation_active = False
        
        # Atributos para autosave
        self.has_unsaved_changes = False
        self.autosave_enabled = True
        self.last_autosave_time = None
        
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
        
        # Lista de áreas proibidas
        self.forbidden_areas_combo = QComboBox()
        forbidden_layout.addWidget(QLabel("Áreas proibidas:"))
        forbidden_layout.addWidget(self.forbidden_areas_combo)
        
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
        autosave_btn = QPushButton("Autosave: ON")
        autosave_btn.clicked.connect(self._toggle_autosave)
        self.autosave_button = autosave_btn  # Referência para atualizar o texto

        # --- 2. ADICIONAR O BOTÃO ---
        calibrate_btn = QPushButton("Calibrar PID")
        calibrate_btn.clicked.connect(self._open_calibration_window)

        map_management_layout.addWidget(save_map_btn, 0, 0)
        map_management_layout.addWidget(load_map_btn, 0, 1)
        map_management_layout.addWidget(autosave_btn, 1, 0)
        map_management_layout.addWidget(calibrate_btn, 1, 1) # <-- Adiciona o botão ao layout
        map_management_group.setLayout(map_management_layout)
        
        # Grupo de Navegação Melhorado
        nav_group = QGroupBox("Navegação")
        nav_layout = QVBoxLayout()
        
        # Campo de seleção de destino
        destination_layout = QHBoxLayout()
        destination_layout.addWidget(QLabel("Destino:"))
        self.destination_combo = QComboBox()
        destination_layout.addWidget(self.destination_combo)
        nav_layout.addLayout(destination_layout)

        # Status da navegação
        self.nav_status_label = QLabel("Status: Parado")
        nav_layout.addWidget(self.nav_status_label)
        
        # Barra de progresso da navegação
        self.nav_progress_bar = QProgressBar()
        self.nav_progress_bar.setVisible(False)
        nav_layout.addWidget(self.nav_progress_bar)
        
        # Informações da navegação
        self.nav_info_label = QLabel("")
        self.nav_info_label.setVisible(False)
        nav_layout.addWidget(self.nav_info_label)

        # Controle de velocidade
        speed_control_layout = QHBoxLayout()
        self.speed_label = QLabel("Velocidade: 100%")
        speed_control_layout.addWidget(self.speed_label)
        
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(100)
        self.speed_slider.setMaximum(200)
        self.speed_slider.setValue(100)
        self.speed_slider.valueChanged.connect(self._on_speed_slider_changed)
        speed_control_layout.addWidget(self.speed_slider)
        nav_layout.addLayout(speed_control_layout)

        nav_buttons = QGridLayout()
        start_nav_btn = QPushButton("Iniciar Navegação")
        start_nav_btn.clicked.connect(self._start_navigation)
        stop_nav_btn = QPushButton("Parar")
        stop_nav_btn.clicked.connect(self._stop_robot)
        
        nav_buttons.addWidget(start_nav_btn, 0, 0)
        nav_buttons.addWidget(stop_nav_btn, 0, 1)
        nav_layout.addLayout(nav_buttons)
        nav_group.setLayout(nav_layout)
        
        # Grupo de Controles Manuais
        manual_control_group = QGroupBox("Controles Manuais")
        manual_layout = QVBoxLayout()
        
        # Informação sobre controles manuais
        manual_info = QLabel("Use os controles abaixo para girar o robô manualmente\napós chegar ao destino:")
        manual_info.setWordWrap(True)
        manual_info.setStyleSheet("color: #666; font-style: italic;")
        manual_layout.addWidget(manual_info)
        
        # Grid de botões direcionais
        direction_grid = QGridLayout()
        
        # Botão FRENTE (↑)
        self.btn_forward = QPushButton("⬆️\nFRENTE")
        self.btn_forward.setMinimumSize(80, 60)
        self.btn_forward.clicked.connect(lambda: self._manual_rotate("forward"))
        direction_grid.addWidget(self.btn_forward, 0, 1)
        
        # Botão ESQUERDA (←)
        self.btn_left = QPushButton("⬅️\nESQUERDA\n(-10°)")
        self.btn_left.setMinimumSize(80, 60)
        self.btn_left.clicked.connect(lambda: self._manual_rotate("left"))
        direction_grid.addWidget(self.btn_left, 1, 0)
        
        # Botão DIREITA (→)
        self.btn_right = QPushButton("➡️\nDIREITA\n(+10°)")
        self.btn_right.setMinimumSize(80, 60)
        self.btn_right.clicked.connect(lambda: self._manual_rotate("right"))
        direction_grid.addWidget(self.btn_right, 1, 2)
        
        # Botão TRÁS (↓)
        self.btn_backward = QPushButton("⬇️\nTRÁS\n(180°)")
        self.btn_backward.setMinimumSize(80, 60)
        self.btn_backward.clicked.connect(lambda: self._manual_rotate("backward"))
        direction_grid.addWidget(self.btn_backward, 2, 1)
        
        manual_layout.addLayout(direction_grid)
        
        # Botões de ação
        action_buttons = QHBoxLayout()
        
        self.btn_set_new_position = QPushButton("📍 Definir Nova Partida")
        self.btn_set_new_position.clicked.connect(self._set_new_starting_position)
        action_buttons.addWidget(self.btn_set_new_position)
        
        self.btn_return_base = QPushButton("🏠 Voltar à Base")
        self.btn_return_base.clicked.connect(self._return_to_base)
        action_buttons.addWidget(self.btn_return_base)
        
        manual_layout.addLayout(action_buttons)
        manual_control_group.setLayout(manual_layout)
        
        # Adiciona todos os grupos ao painel de controle
        control_layout.addWidget(poi_group)
        control_layout.addWidget(forbidden_group)
        control_layout.addWidget(map_management_group)
        control_layout.addWidget(nav_group)
        control_layout.addWidget(manual_control_group) # Adiciona o novo grupo
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
        print(f"DEBUG: Navegador inicializado - Posição: {self.navigator.current_position}, Ângulo: {self.navigator.current_angle}°")
        
        # Conecta o sinal de atualização de posição do navegador ao slot da UI
        self.navigator.position_updated.connect(self._update_robot_position_on_map)

        # Configura callbacks do mapa
        self.map_widget.area_clicked_callback = self._on_area_clicked
        
        # Configura timer para autosave periódico (a cada 30 segundos)
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self._check_periodic_autosave)
        self.autosave_timer.start(30000)  # 30 segundos
        
        # Tenta carregar o último mapa ativo ao iniciar
        self._load_active_map()
        
        # Inicia o timer de atualização
        self._update()

        # Timer para diagnóstico
        self.diag_timer = QTimer()
        self.diag_timer.timeout.connect(self._update_speed_feedback)

        # Carrega e aplica os ganhos do PID salvos
        self._load_and_apply_pid_gains()

    def _load_and_apply_pid_gains(self):
        """Carrega os ganhos do PID do banco de dados e os aplica ao controlador."""
        print("DEBUG: Carregando e aplicando ganhos PID salvos...")
        saved_gains = self.map_manager.get_pid_gains()
        if saved_gains:
            print(f"DEBUG: Ganhos encontrados no DB: {saved_gains}")
            motor_controller = self.navigator.get_motor_controller()
            if motor_controller:
                motor_controller.set_pid_gains('left', saved_gains['left']['kp'], saved_gains['left']['ki'], saved_gains['left']['kd'])
                motor_controller.set_pid_gains('right', saved_gains['right']['kp'], saved_gains['right']['ki'], saved_gains['right']['kd'])
                print("DEBUG: Ganhos do PID aplicados com sucesso ao controlador.")
        else:
            print("DEBUG: Nenhum ganho PID salvo encontrado. Usando valores padrão do código.")

    def _update_robot_position_on_map(self, x: float, y: float, angle: float):
        """
        Slot para receber a atualização de posição do navegador e atualizar o widget do mapa.
        """
        self.map_widget.update_robot_position(x, y, angle)

    # --- 3. CRIAR A FUNÇÃO DE ABERTURA ---
    def _open_calibration_window(self):
        """Abre a janela de calibração do PID."""
        # A janela de calibração precisa da referência do controlador de motor
        motor_controller = self.navigator.get_motor_controller()
        if motor_controller:
            # Passa a referência do motor_controller e o 'self' como pai
            self.calibration_win = CalibrationWindow(motor_controller, self)
            self.calibration_win.show()
        else:
            QMessageBox.warning(self, "Erro", "Controlador de motor não está disponível.")

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
                    points_of_interest, forbidden_areas, _, _ = self.map_manager.load_active_map()
                    
                    map_data = {
                        'points_of_interest': points_of_interest,
                        'forbidden_areas': forbidden_areas
                    }
                    self.map_widget.load_map(map_data)
                    self._update_points_list()
                    self._update_destination_combo()
                    self._reload_forbidden_areas()
                    self.status_label.setText(f"Mapa carregado: {active_map['nome']}")
                    self._reset_robot_to_base()
                else:
                    self.status_label.setText("Nenhum mapa ativo encontrado")
            else:
                # Se o usuário cancelar, carrega o mapa ativo
                active_map = self.map_manager.get_active_map()
                if active_map:
                    self.current_map = active_map
                    points_of_interest, forbidden_areas, _, _ = self.map_manager.load_active_map()

                    map_data = {
                        'points_of_interest': points_of_interest,
                        'forbidden_areas': forbidden_areas
                    }
                    self.map_widget.load_map(map_data)
                    self._update_points_list()
                    self._update_destination_combo()
                    self._reload_forbidden_areas()
                    self.status_label.setText(f"Mapa carregado: {active_map['nome']}")
                    self._reset_robot_to_base()
                else:
                    self.status_label.setText("Nenhum mapa ativo encontrado")
        else:
            self.status_label.setText("Nenhum mapa encontrado. Crie um novo mapa.")
            
    def _reset_robot_to_base(self):
        """Reseta o robô para a posição base (5.7, 11.5) com ângulo 270°"""
        print("DEBUG: Resetando robô para posição base após carregamento do mapa")
        self.navigator.reset_to_initial_state()
        # Atualiza a interface imediatamente
        self.map_widget.update_robot_position(ROBOT_INITIAL_POSITION[0], ROBOT_INITIAL_POSITION[1], ROBOT_INITIAL_ANGLE)
        print(f"DEBUG: Robô resetado para posição base: {ROBOT_INITIAL_POSITION}, ângulo: {ROBOT_INITIAL_ANGLE}°")
        
    def _update_points_list(self):
        """Atualiza a lista de pontos de interesse."""
        self.poi_combo.clear()
        print(f"DEBUG: Atualizando lista de pontos - {len(self.map_widget.points_of_interest)} pontos")
        for name, point_data in self.map_widget.points_of_interest.items():
            x, y, point_type = point_data
            self.poi_combo.addItem(f"{name} ({x:.2f}, {y:.2f}) - {point_type}")
            
    def _update_destination_combo(self):
        """Atualiza o combo box de destino."""
        self.destination_combo.clear()
        print(f"DEBUG: Atualizando combo de destino - {len(self.map_widget.points_of_interest)} pontos")
        for name, point_data in self.map_widget.points_of_interest.items():
            x, y, point_type = point_data
            self.destination_combo.addItem(f"{name} ({x:.2f}, {y:.2f}) - {point_type}")
            print(f"DEBUG: Adicionando ao combo: '{name} ({x:.2f}, {y:.2f}) - {point_type}'")
            
    def _update(self):
        """Atualiza o estado da interface e do robô"""
        # Atualiza o navegador se a navegação estiver ativa
        if self.navigation_active:
            print(f"DEBUG: update() - Navegação ativa, chamando navigator.update()")
            self.navigator.update()
            
            # Atualiza o status da navegação
            nav_status = self.navigator.get_navigation_status()
            print(f"DEBUG: update() - Status da navegação: {nav_status}")
            
            # Atualiza a barra de progresso
            progress = int(nav_status["progress"] * 100)
            self.nav_progress_bar.setValue(progress)
            
            # Atualiza as informações da navegação
            state_text = nav_status["state"]
            time_remaining = nav_status["estimated_time_remaining"]
            
            if nav_status.get("is_paused_at_destination", False):
                info_text = f"Estado: {state_text} | Pausado no destino para entrega"
            elif time_remaining > 0:
                info_text = f"Estado: {state_text} | Tempo restante: {time_remaining:.1f}s"
            else:
                info_text = f"Estado: {state_text}"
                
            self.nav_info_label.setText(info_text)
            
            # Verifica se a navegação foi concluída
            if nav_status["state"] == "COMPLETED" or nav_status["state"] == "IDLE":
                print("DEBUG: ===== NAVEGAÇÃO CONCLUÍDA =====")
                print("DEBUG: update() - Chamando reset completo da interface")
                
                # Faz reset completo da interface
                self._complete_navigation_and_reset()
                
                # Informa o usuário que a navegação foi concluída
                QMessageBox.information(self, "Navegação", "Navegação concluída! Sistema resetado e pronto para nova navegação.")
                print("DEBUG: ===== FIM DA NAVEGAÇÃO =====")
                # PARA COMPLETAMENTE A ATUALIZAÇÃO - NÃO AGENDA PRÓXIMA
                return
                
        # Atualiza a posição do robô no mapa
        robot_position = self.navigator.current_position
        robot_angle = self.navigator.current_angle
        print(f"DEBUG: Atualizando posição do robô - Posição: {robot_position}, Ângulo: {robot_angle}°")
        self.map_widget.update_robot_position(robot_position[0], robot_position[1], robot_angle)
        
        # Agenda a próxima atualização APENAS se a navegação não foi concluída
        if self.navigation_active:
            QTimer.singleShot(100, self._update)  # Atualiza a cada 100ms
        else:
            print("DEBUG: Navegação concluída - parando atualizações automáticas")
        
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
        # ETAPA DE VALIDAÇÃO: Verifica se o ponto está em uma área proibida ANTES de abrir o diálogo.
        path_finder = self.navigator.path_finder
        grid_x = int(x / path_finder.grid_size)
        grid_y = int(y / path_finder.grid_size)

        if path_finder._is_in_forbidden_area(grid_x, grid_y):
            QMessageBox.warning(
                self, 
                "Ponto Inválido", 
                "Não é possível criar um ponto de interesse dentro ou muito perto de uma área proibida."
            )
            # Restaura o cursor e o modo, pois a operação foi cancelada.
            self.map_widget.setCursor(Qt.CursorShape.ArrowCursor)
            self.status_label.setText("Modo: Manual" if not self.navigator.is_autonomous else "Modo: Autônomo")
            self.map_widget.add_point_mode = False
            self.map_widget.point_clicked_callback = None
            return

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
                self._mark_unsaved_changes()  # Marca alterações não salvas
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
                self._mark_unsaved_changes()  # Marca alterações não salvas
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
        
        # Salva a área proibida automaticamente no banco de dados
        if len(self.map_widget.current_forbidden_area) >= 3:
            # Gera um nome para a área
            area_count = len(self.map_widget.forbidden_areas) + 1
            area_name = f"Área Proibida {area_count}"
            
            print(f"DEBUG: Salvando área proibida com {len(self.map_widget.current_forbidden_area)} pontos")
            
            # Salva no banco de dados
            success = self.map_manager.save_forbidden_area(
                self.map_widget.current_forbidden_area, 
                area_name
            )
            
            if success:
                # Limpa a área temporária
                self.map_widget.current_forbidden_area = []
                # Recarrega as áreas proibidas do banco para obter o ID
                self._reload_forbidden_areas()
                self._mark_unsaved_changes()  # Marca alterações não salvas
                QMessageBox.information(self, "Sucesso", f"Área proibida '{area_name}' salva automaticamente!")
            else:
                QMessageBox.warning(self, "Erro", "Erro ao salvar área proibida no banco de dados!")
        else:
            QMessageBox.warning(self, "Aviso", "Área proibida deve ter pelo menos 3 pontos!")

    def _reload_forbidden_areas(self):
        """Recarrega as áreas proibidas do banco de dados."""
        print("DEBUG: Iniciando recarregamento de áreas proibidas")
        
        # Obtém o mapa ativo do banco se não tiver um carregado
        if not self.current_map:
            print("DEBUG: Nenhum mapa atual, obtendo mapa ativo do banco")
            self.current_map = self.map_manager.get_active_map()
            if not self.current_map:
                print("DEBUG: Nenhum mapa ativo encontrado para recarregar áreas proibidas")
                return
            else:
                print(f"DEBUG: Mapa ativo obtido: {self.current_map}")
            
        print(f"DEBUG: Usando mapa ID: {self.current_map['id']}")
        
        # Obtém as áreas proibidas com IDs do banco
        areas_with_ids = self.map_manager.get_forbidden_areas_with_ids(self.current_map['id'])
        print(f"DEBUG: Recarregando {len(areas_with_ids)} áreas proibidas do banco")
        
        # Atualiza o MapWidget
        print(f"DEBUG: Atualizando MapWidget com {len(areas_with_ids)} áreas")
        self.map_widget.forbidden_areas = areas_with_ids
        self.map_widget.update()
        
        # Atualiza a lista de áreas proibidas
        print("DEBUG: Atualizando lista de áreas proibidas")
        self._update_forbidden_areas_list()
        
        # **CORREÇÃO CRÍTICA**: Sincroniza as áreas com o navegador IMEDIATAMENTE.
        # Isto garante que o PathFinder sempre tenha a informação mais recente.
        areas_for_navigator = [area['coordenadas'] for area in areas_with_ids]
        self.navigator.set_forbidden_areas(areas_for_navigator)
        
        print("DEBUG: Recarregamento de áreas proibidas concluído")
        
    def _update_forbidden_areas_list(self):
        """Atualiza a lista de áreas proibidas no combo box."""
        print(f"DEBUG: Atualizando lista de áreas proibidas - {len(self.map_widget.forbidden_areas)} áreas")
        self.forbidden_areas_combo.clear()
        for area_data in self.map_widget.forbidden_areas:
            if isinstance(area_data, dict):
                area_id = area_data.get('id', 0)
                area_name = area_data.get('nome', f'Área {area_id}')
                item_text = f"{area_name} (ID: {area_id})"
                self.forbidden_areas_combo.addItem(item_text)
                print(f"DEBUG: Adicionando área à lista: {item_text}")
        print(f"DEBUG: Lista atualizada com {self.forbidden_areas_combo.count()} itens")

    def _delete_forbidden_area(self):
        """Remove uma área proibida."""
        print("DEBUG: Iniciando exclusão de área proibida")
        print(f"DEBUG: Áreas disponíveis no MapWidget: {len(self.map_widget.forbidden_areas)}")
        
        if not self.map_widget.forbidden_areas:
            QMessageBox.warning(self, "Aviso", "Não há áreas proibidas para excluir!")
            return
            
        # Verifica se há uma área selecionada
        selected_area = self.map_widget.get_selected_area()
        print(f"DEBUG: Área selecionada: {selected_area}")
        
        if selected_area:
            area_id = selected_area.get('id', 0)
            area_name = selected_area.get('nome', f'Área {area_id}')
            print(f"DEBUG: Usando área selecionada - ID: {area_id}, Nome: {area_name}")
        else:
            # Se não há área selecionada, usa a primeira da lista
            if self.forbidden_areas_combo.currentText():
                # Extrai o ID da string do combo box
                combo_text = self.forbidden_areas_combo.currentText()
                print(f"DEBUG: Texto do combo: '{combo_text}'")
                try:
                    area_id = int(combo_text.split("ID: ")[1].rstrip(")"))
                    area_name = combo_text.split(" (ID:")[0]
                    print(f"DEBUG: Extraído do combo - ID: {area_id}, Nome: {area_name}")
                except Exception as e:
                    print(f"DEBUG: Erro ao extrair ID do combo: {e}")
                    QMessageBox.warning(self, "Erro", "Erro ao identificar área selecionada!")
                    return
            else:
                print("DEBUG: Nenhuma área selecionada no combo")
                QMessageBox.warning(self, "Aviso", "Selecione uma área para excluir!")
                return
        
        # Confirma a exclusão
        reply = QMessageBox.question(
            self, 'Confirmar Exclusão',
            f'Tem certeza que deseja excluir a área "{area_name}"?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            print(f"DEBUG: Confirmada exclusão da área {area_id}")
            # Remove do banco de dados
            success = self.map_manager.delete_forbidden_area(area_id)
            print(f"DEBUG: Resultado da exclusão no banco: {success}")
            
            if success:
                # Recarrega as áreas proibidas
                print("DEBUG: Recarregando áreas proibidas...")
                self._reload_forbidden_areas()
                self._mark_unsaved_changes()  # Marca alterações não salvas
                QMessageBox.information(self, "Sucesso", f"Área '{area_name}' excluída com sucesso!")
            else:
                QMessageBox.warning(self, "Erro", f"Erro ao excluir a área '{area_name}'!")
        else:
            print("DEBUG: Exclusão cancelada pelo usuário")

    def _save_map(self):
        """Salva o mapa atual no banco de dados."""
        map_name, ok = QInputDialog.getText(self, "Salvar Mapa", "Nome do Mapa:")
        if ok and map_name:
            self.map_manager.save_map(
                map_name,
                self.map_widget.points_of_interest,
                self.map_widget.forbidden_areas
            )
            self.has_unsaved_changes = False  # Limpa alterações não salvas
            QMessageBox.information(self, "Salvar Mapa", f"Mapa '{map_name}' salvo com sucesso!")
        elif not map_name and ok:
            QMessageBox.warning(self, "Aviso", "O nome do mapa não pode ser vazio!")

    def _start_navigation(self):
        """Inicia a navegação autônoma com feedback melhorado"""
        print("🚀 ===== INICIANDO NOVA NAVEGAÇÃO =====")
        print(f"🔍 Status atual da navegação: {self.navigation_active}")
        
        # Verifica se já há uma navegação ativa
        if self.navigation_active:
            print("❌ DEBUG: Navegação já está ativa, ignorando novo comando.")
            QMessageBox.information(self, "Navegação", "O robô já está navegando. Aguarde o término do percurso atual.")
            return
            
        # Verifica se o navegador está em estado IDLE
        nav_status = self.navigator.get_navigation_status()
        print(f"🔍 Estado do navegador: {nav_status['state']}")
        print(f"🔍 Posição atual: {nav_status.get('position', 'Desconhecida')}")
        print(f"🔍 is_returning_to_base: {getattr(self.navigator, 'is_returning_to_base', 'Não definido')}")
        
        # **FORÇA RESET COMPLETO SEMPRE PARA GARANTIR ESTADO LIMPO**
        print(f"🔄 FORÇANDO RESET COMPLETO INDEPENDENTE DO ESTADO ATUAL")
        print(f"🔍 Estado antes do reset: {nav_status['state']}")
        
        # PARA TUDO PRIMEIRO
        self.navigator.navigation_active = False
        self.navigator.motors.stop()
        self.navigation_active = False
        
        # RESET COMPLETO FORÇADO
        self.navigator.reset_to_initial_state()
        
        # LIMPA QUALQUER ESTADO REMANESCENTE
        self.navigator.is_adjusting_final_angle = False
        self.navigator.is_returning_to_base = False
        self.navigator.navigation_state = "IDLE"
        self.navigator.current_target = None
        self.navigator.path = []
        self.navigator.path_index = 0
        
        # Verifica se o reset funcionou
        nav_status_after = self.navigator.get_navigation_status()
        print(f"✅ Estado após reset FORÇADO: {nav_status_after['state']}")
        print(f"✅ is_returning_to_base após reset: {getattr(self.navigator, 'is_returning_to_base', 'Não definido')}")
        print(f"✅ navigation_active após reset: {getattr(self.navigator, 'navigation_active', 'Não definido')}")
            
        print(f"DEBUG: current_map: {self.current_map}")
        print(f"DEBUG: destination_combo.currentText(): '{self.destination_combo.currentText()}'")
        print(f"DEBUG: points_of_interest: {list(self.map_widget.points_of_interest.keys())}")
        
        if not self.current_map:
            # Se nenhum mapa estiver carregado, cria um mapa temporário
            # com o estado atual da interface para permitir a navegação.
            print("DEBUG: Nenhum mapa carregado. Criando mapa temporário com o estado atual.")
            self.current_map = {
                'id': -1,  # ID temporário, pois não vem do banco de dados
                'nome': 'Mapa Atual (Não Salvo)'
            }
            
        if not self.destination_combo.currentText():
            print("DEBUG: ERRO - Nenhum destino selecionado")
            QMessageBox.warning(self, "Erro", "Selecione um destino para navegar.")
            return
            
        # Obtém o destino selecionado - extrai apenas o nome do ponto
        destination_text = self.destination_combo.currentText()
        destination_name = destination_text.split(" (")[0]  # Remove coordenadas e tipo
        print(f"DEBUG: Texto do combo: '{destination_text}'")
        print(f"DEBUG: Nome extraído: '{destination_name}'")
        
        destination = self.map_widget.points_of_interest.get(destination_name)
        print(f"DEBUG: Destino encontrado: {destination}")
        
        if not destination:
            print(f"DEBUG: ERRO - Destino '{destination_name}' não encontrado")
            print(f"DEBUG: Pontos disponíveis: {list(self.map_widget.points_of_interest.keys())}")
            QMessageBox.warning(self, "Erro", f"Destino '{destination_name}' não encontrado.")
            return
            
        print(f"DEBUG: Destino selecionado: {destination_name} em {destination}")
        
        # Inicia a navegação
        print("🎯 ===== INICIANDO CHAMADA DE NAVEGAÇÃO =====")
        print(f"🎯 Destino: {destination}")
        print(f"🎯 Base: {ROBOT_INITIAL_POSITION}")
        print(f"🎯 Estado do navegador antes da chamada: {self.navigator.get_navigation_status()['state']}")
        print(f"🎯 Chamando navigate_to_destination_only...")
        
        # VERIFICA SE A FUNÇÃO VAI SER EXECUTADA
        try:
            print("⚡ EXECUTANDO navigate_to_destination_only...")
            self.navigator.navigate_to_destination_only(destination)
            print("✅ navigate_to_destination_only EXECUTOU SEM ERRO")
        except Exception as e:
            print(f"❌ ERRO na execução de navigate_to_destination_only: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # VERIFICA SE O ESTADO MUDOU APÓS A CHAMADA
        nav_status_after_call = self.navigator.get_navigation_status()
        print(f"🔍 Estado após navigate_to_destination_only: {nav_status_after_call['state']}")
        print(f"🔍 navigation_active do navegador: {getattr(self.navigator, 'navigation_active', 'UNDEFINED')}")
        print(f"🔍 path do navegador: {len(getattr(self.navigator, 'path', []))} pontos")
        
        print("✅ Função navigate_to_destination_only chamada com sucesso")
        self.navigation_active = True
        print(f"✅ navigation_active DA INTERFACE definido como: {self.navigation_active}")
        
        # NOVO: Exibe o percurso calculado no mapa
        if hasattr(self.navigator, 'path') and self.navigator.path:
            print(f"🗺️ Exibindo percurso calculado com {len(self.navigator.path)} pontos")
            self.map_widget.set_current_path(self.navigator.path)
            print("✅ Percurso exibido no mapa (linha azul)")
        
        # Atualiza interface
        self.nav_status_label.setText("Status: Navegando...")
        self.nav_progress_bar.setVisible(True)
        self.nav_progress_bar.setValue(0)
        self.nav_info_label.setVisible(True)
        self.status_label.setText("Navegando...")
        
        # Reinicia o loop de atualização
        self._update()
        
        # --- NOVO: Visualização do Caminho ---
        # Após iniciar a navegação, obtém o caminho calculado e o envia para o widget do mapa.
        current_path = self.navigator.get_current_path()
        self.map_widget.set_current_path(current_path)
        
        print("DEBUG: Navegação iniciada com sucesso")
        print("DEBUG: ===== FIM DA INICIALIZAÇÃO =====")
            
    def _stop_robot(self):
        """Para o robô e atualiza a interface."""
        self.navigator.motors.stop()
        self.navigation_active = False
        
        # Atualiza interface
        self.nav_status_label.setText("Status: Parado")
        self.nav_progress_bar.setVisible(False)
        self.nav_info_label.setVisible(False)
        self.status_label.setText("Modo: Manual")
        
        print("DEBUG: Robô parado")

    def _mark_unsaved_changes(self):
        """Marca que há alterações não salvas."""
        self.has_unsaved_changes = True
        # Atualiza o status para mostrar que há alterações não salvas
        current_status = self.status_label.text()
        if "(*)" not in current_status:
            self.status_label.setText(f"{current_status} (*)")
        print("DEBUG: Alterações não salvas detectadas")
        
    def _perform_autosave(self, show_message=False):
        """Executa o autosave automático."""
        if not self.autosave_enabled or not self.has_unsaved_changes:
            return
            
        try:
            # Obtém o nome do mapa atual ou cria um nome padrão
            if self.current_map:
                map_name = self.current_map['nome']
            else:
                map_name = f"Mapa_Auto_{int(time.time())}"
                
            # Salva o mapa
            self.map_manager.save_map(
                map_name,
                self.map_widget.points_of_interest,
                self.map_widget.forbidden_areas
            )
            
            self.has_unsaved_changes = False
            self.last_autosave_time = time.time()
            
            # Remove o indicador de alterações não salvas do status
            current_status = self.status_label.text()
            if "(*)" in current_status:
                self.status_label.setText(current_status.replace(" (*)", ""))
            
            if show_message:
                QMessageBox.information(self, "Autosave", f"Mapa '{map_name}' salvo automaticamente!")
            else:
                print(f"DEBUG: Autosave executado - Mapa '{map_name}'")
                
        except Exception as e:
            print(f"DEBUG: Erro no autosave: {e}")
            if show_message:
                QMessageBox.warning(self, "Erro no Autosave", f"Erro ao salvar automaticamente: {str(e)}")
                
    def _check_unsaved_changes(self) -> bool:
        """Verifica se há alterações não salvas e pergunta ao usuário."""
        if not self.has_unsaved_changes:
            return True
            
        # Se autosave está habilitado, salva automaticamente sem perguntar
        if self.autosave_enabled:
            print("DEBUG: Autosave habilitado - salvando automaticamente")
            self._perform_autosave(show_message=False)
            return True
            
        # Se autosave está desabilitado, pergunta ao usuário
        reply = QMessageBox.question(
            self, 'Alterações Não Salvas',
            'Existem alterações não salvas. Deseja salvar antes de sair?',
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save
        )
        
        if reply == QMessageBox.Save:
            self._perform_autosave(show_message=True)
            return True
        elif reply == QMessageBox.Discard:
            return True
        else:  # Cancel
            return False
            
    def _toggle_autosave(self):
        """Alterna o estado do autosave."""
        self.autosave_enabled = not self.autosave_enabled
        status = "ON" if self.autosave_enabled else "OFF"
        self.autosave_button.setText(f"Autosave: {status}")
        QMessageBox.information(self, "Autosave", f"Autosave {status.lower()}!")
        print(f"DEBUG: Autosave {status.lower()}")
            
    def closeEvent(self, event):
        """Limpa recursos ao fechar a janela."""
        # Verifica alterações não salvas
        if not self._check_unsaved_changes():
            event.ignore()
            return
            
        # Executa autosave final se habilitado
        if self.autosave_enabled and self.has_unsaved_changes:
            self._perform_autosave(show_message=False)
            
        self.navigator.motors.cleanup()
        self.map_manager.close()
        event.accept()

    def _check_periodic_autosave(self):
        """Executa o autosave periódico."""
        if self.autosave_enabled and self.has_unsaved_changes:
            # Só executa autosave se passou pelo menos 30 segundos desde o último
            current_time = time.time()
            if (self.last_autosave_time is None or 
                current_time - self.last_autosave_time >= 30):
                print("DEBUG: Executando autosave periódico...")
                self._perform_autosave(show_message=False)

    def _on_area_clicked(self, area_id: int):
        """Callback para quando uma área proibida é clicada."""
        print(f"DEBUG: Área proibida {area_id} clicada")
        # Aqui você pode adicionar lógica adicional, como mostrar detalhes da área

    def _on_speed_slider_changed(self, value):
        """Atualiza a velocidade do robô quando o slider é movido."""
        speed_percentage = value
        self.speed_label.setText(f"Velocidade: {speed_percentage}%")
        
        # Converte o valor do slider (100-200) para um multiplicador (1.0-2.0)
        multiplier = speed_percentage / 100.0
        self.navigator.set_speed_multiplier(multiplier)

    def _update_speed_feedback(self):
        # Implemente a lógica para atualizar o feedback da velocidade
        pass

    def _complete_navigation_and_reset(self):
        """Completa a navegação e faz reset completo da interface para permitir nova navegação"""
        print("🔄 ===== INICIANDO RESET COMPLETO DA INTERFACE =====")
        
        # 1. Para a navegação e motores
        self.navigation_active = False
        self.navigator.navigation_active = False
        self.navigator.motors.stop()
        
        # 2. Limpa o percurso anterior do mapa
        print("🧹 Limpando percurso anterior do mapa")
        self.map_widget.set_current_path([])  # Remove linha azul do percurso
        
        # 3. NOVO: Mantém a posição atual como nova partida (não reseta para inicial)
        print("📍 Mantendo posição atual como nova partida")
        current_pos = self.navigator.current_position
        current_angle = self.navigator.current_angle
        print(f"📍 Nova posição de partida: {current_pos}")
        print(f"📍 Novo ângulo de partida: {current_angle}°")
        
        # 4. Reseta o navegador para estado inicial MAS preserva posição atual
        print("🔄 Resetando navegador (preservando posição atual)")
        self.navigator.reset_to_initial_state()
        
        # 5. Restaura a posição atual após o reset
        print("🎯 Restaurando posição atual após reset")
        self.navigator.current_position = current_pos
        self.navigator.current_angle = current_angle
        
        # 6. Atualiza elementos da interface
        print("🖥️ Atualizando interface")
        self.nav_status_label.setText("Status: Pronto (nova partida)")
        self.nav_progress_bar.setVisible(False)
        self.nav_info_label.setVisible(False)
        self.status_label.setText("Modo: Manual")
        
        # 7. Força redesenho do mapa com posição atual
        self.map_widget.update_robot_position(
            current_pos[0], 
            current_pos[1], 
            current_angle
        )
        
        print("✅ Reset completo da interface concluído")
        print(f"✅ Posição do robô (nova partida): {self.navigator.current_position}")
        print(f"✅ Ângulo do robô (nova partida): {self.navigator.current_angle}°")
        print("✅ Sistema pronto para nova navegação a partir da posição atual")

    def _manual_rotate(self, direction: str):
        """Executa rotação manual do robô na direção especificada"""
        print(f"🎮 ===== CONTROLE MANUAL: {direction.upper()} =====")
        
        # Verifica se não há navegação ativa
        if self.navigation_active:
            QMessageBox.warning(self, "Aviso", "Não é possível usar controles manuais durante a navegação automática.")
            return
        
        # Define o ângulo de rotação (10 graus para cada direção)
        rotation_angle = 10  # CORRIGIDO: 10 graus em vez de 90
        current_angle = self.navigator.current_angle
        
        # NOVO: Implementar rotação física real
        if direction == "forward":
            # Não gira, apenas mantém direção atual
            target_angle = current_angle
            print(f"🎮 FRENTE: Mantendo ângulo atual {current_angle}°")
            # Não executa rotação física
            
        elif direction == "right":
            target_angle = (current_angle + rotation_angle) % 360
            print(f"🎮 DIREITA: {current_angle}° → {target_angle}° (+{rotation_angle}°)")
            
            # NOVO: Executa rotação física para direita (horário)
            print(f"🔧 Executando rotação física: DIREITA (+{rotation_angle}°)")
            self._execute_physical_rotation("clockwise", rotation_angle)
            
        elif direction == "backward":
            target_angle = (current_angle + 180) % 360
            print(f"🎮 TRÁS: {current_angle}° → {target_angle}° (180°)")
            
            # NOVO: Executa rotação física de 180° (pode ser horário ou anti-horário)
            print(f"🔧 Executando rotação física: TRÁS (180°)")
            self._execute_physical_rotation("clockwise", 180)
            
        elif direction == "left":
            target_angle = (current_angle - rotation_angle) % 360
            print(f"🎮 ESQUERDA: {current_angle}° → {target_angle}° (-{rotation_angle}°)")
            
            # NOVO: Executa rotação física para esquerda (anti-horário)
            print(f"🔧 Executando rotação física: ESQUERDA (-{rotation_angle}°)")
            self._execute_physical_rotation("counterclockwise", rotation_angle)
            
        else:
            print(f"❌ Direção inválida: {direction}")
            return
        
        # Atualiza o ângulo do robô (simulação)
        self.navigator.current_angle = target_angle
        
        # Atualiza a visualização no mapa
        self.map_widget.update_robot_position(
            self.navigator.current_position[0],
            self.navigator.current_position[1], 
            target_angle
        )
        
        print(f"✅ Rotação manual concluída. Novo ângulo: {target_angle}°")

    def _execute_physical_rotation(self, direction: str, angle_degrees: float):
        """Executa rotação física real nos motores"""
        print(f"⚙️ === ROTAÇÃO FÍSICA: {direction.upper()} {angle_degrees}° ===")
        
        # Calcula tempo de rotação baseado no ângulo
        # Assumindo velocidade de rotação de ~30°/segundo
        rotation_speed = 30.0  # graus por segundo
        rotation_time = angle_degrees / rotation_speed
        
        print(f"⚙️ Tempo de rotação calculado: {rotation_time:.2f}s")
        
        try:
            if direction == "clockwise":
                # Giro horário: motor esquerdo para frente, direito para trás
                print("🔴 SYNC_DEBUG: INTERFACE → DIREITA | Comando: set_speed(30, -30)")
                self.navigator.motors.set_speed(30, -30)  # ESQ+, DIR-
                
            elif direction == "counterclockwise":
                # Giro anti-horário: motor esquerdo para trás, direito para frente  
                print("🟢 SYNC_DEBUG: INTERFACE → ESQUERDA | Comando: set_speed(-30, 30)")
                self.navigator.motors.set_speed(-30, 30)  # ESQ-, DIR+
                
            # Aguarda o tempo de rotação
            import time
            print(f"⚙️ Executando rotação por {rotation_time:.2f}s...")
            time.sleep(rotation_time)
            
            # Para os motores
            print("⚙️ Parando motores após rotação")
            self.navigator.motors.stop()
            
            print(f"✅ Rotação física concluída: {direction} {angle_degrees}°")
            
        except Exception as e:
            print(f"❌ Erro na rotação física: {e}")
            # Para os motores em caso de erro
            try:
                self.navigator.motors.stop()
            except:
                pass

    def _set_new_starting_position(self):
        """Define a posição atual como nova posição de partida"""
        print("📍 ===== DEFININDO NOVA POSIÇÃO DE PARTIDA =====")
        
        current_pos = self.navigator.current_position
        current_angle = self.navigator.current_angle
        
        # Confirma com o usuário
        reply = QMessageBox.question(
            self, 
            "Definir Nova Partida",
            f"Definir posição atual como nova partida?\n\n"
            f"Posição: ({current_pos[0]:.2f}, {current_pos[1]:.2f})\n"
            f"Ângulo: {current_angle:.1f}°\n\n"
            f"Esta será a nova referência para cálculos de percurso.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Atualiza a posição de partida no navegador
            print(f"📍 Nova posição de partida: {current_pos}")
            print(f"📍 Novo ângulo de partida: {current_angle}°")
            
            # Limpa qualquer percurso anterior
            self.map_widget.set_current_path([])
            
            # Faz reset completo do navegador mantendo posição atual
            self.navigator.reset_to_initial_state()
            self.navigator.current_position = current_pos
            self.navigator.current_angle = current_angle
            
            # Atualiza visualização no mapa
            self.map_widget.update_robot_position(current_pos[0], current_pos[1], current_angle)
            
            QMessageBox.information(
                self, 
                "Nova Partida Definida",
                f"Posição de partida atualizada!\n\n"
                f"Posição: ({current_pos[0]:.2f}, {current_pos[1]:.2f})\n"
                f"Ângulo: {current_angle:.1f}°\n\n"
                f"O sistema agora calculará novos percursos a partir desta posição."
            )
            
            print("✅ Nova posição de partida definida com sucesso")

    def _return_to_base(self):
        """Inicia navegação de retorno para a base original"""
        print("🏠 ===== RETORNO À BASE ORIGINAL =====")
        
        # Verifica se não há navegação ativa
        if self.navigation_active:
            QMessageBox.warning(self, "Aviso", "Aguarde o término da navegação atual.")
            return
        
        base_position = ROBOT_INITIAL_POSITION
        current_pos = self.navigator.current_position
        
        print(f"🏠 Posição atual: {current_pos}")
        print(f"🏠 Base original: {base_position}")
        
        # Verifica se já está na base
        distance_to_base = ((current_pos[0] - base_position[0])**2 + 
                           (current_pos[1] - base_position[1])**2)**0.5
        
        print(f"🏠 Distância para base: {distance_to_base:.2f}m")
        
        if distance_to_base < 0.3:  # 30cm de tolerância
            QMessageBox.information(self, "Retorno à Base", "O robô já está próximo à base original!")
            return
        
        # Confirma o retorno
        reply = QMessageBox.question(
            self, 
            "Retornar à Base",
            f"Iniciar navegação de retorno à base original?\n\n"
            f"De: ({current_pos[0]:.2f}, {current_pos[1]:.2f})\n"
            f"Para: ({base_position[0]:.2f}, {base_position[1]:.2f})\n"
            f"Distância: {distance_to_base:.2f}m",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            print(f"🏠 Iniciando retorno de {current_pos} para {base_position}")
            
            # CORREÇÃO: Fazer reset completo antes de iniciar nova navegação
            print("🔄 Fazendo reset antes do retorno à base")
            self.navigator.reset_to_initial_state()
            
            # Restaura posição atual
            self.navigator.current_position = current_pos
            self.navigator.current_angle = self.navigator.current_angle
            
            # Usa o método de navegação apenas ao destino para ir à base
            try:
                print(f"🚀 Chamando navigate_to_destination_only para base: {base_position}")
                self.navigator.navigate_to_destination_only(base_position)
                
                # Atualiza interface para navegação ativa
                self.navigation_active = True
                self.nav_status_label.setText("Status: Retornando à base...")
                self.nav_progress_bar.setVisible(True)
                self.nav_progress_bar.setValue(0)
                self.nav_info_label.setVisible(True)
                self.nav_info_label.setText("Estado: Retornando à base original")
                
                # NOVO: Exibe o percurso calculado no mapa
                if hasattr(self.navigator, 'path') and self.navigator.path:
                    print(f"🗺️ Exibindo percurso de retorno com {len(self.navigator.path)} pontos")
                    self.map_widget.set_current_path(self.navigator.path)
                    print("✅ Percurso de retorno exibido no mapa (linha azul)")
                
                print("✅ Navegação de retorno à base iniciada com sucesso")
                
                # IMPORTANTE: Inicia o loop de atualização
                self._update()
                
            except Exception as e:
                print(f"❌ Erro ao iniciar retorno: {e}")
                import traceback
                traceback.print_exc()
                QMessageBox.warning(self, "Erro", f"Erro ao iniciar retorno à base:\n{e}")
                
                # Limpa estados em caso de erro
                self.navigation_active = False
                self.nav_status_label.setText("Status: Erro")
                self.nav_progress_bar.setVisible(False)
                self.nav_info_label.setVisible(False)
