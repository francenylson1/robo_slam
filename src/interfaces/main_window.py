from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QComboBox, QMessageBox,
                             QGroupBox, QGridLayout, QInputDialog, QProgressBar, QSlider,
                             QScrollArea, QFrame, QSizePolicy, QApplication, QFileDialog)
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

class CollapsibleGroupBox(QGroupBox):
    """
    Grupo colapsável que permite expandir/colapsar conteúdo para otimizar espaço em tela.
    """
    def __init__(self, title, icon="", collapsed=True):
        super().__init__()
        self.collapsed = collapsed
        self.title_text = title
        self.icon = icon
        
        # Layout principal
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(2)
        
        # Cabeçalho clicável
        self.header_btn = QPushButton()
        self.header_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                border: 1px solid #ccc;
                padding: 5px;
                background-color: #f0f0f0;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.header_btn.clicked.connect(self.toggle_collapsed)
        self.main_layout.addWidget(self.header_btn)
        
        # Container para conteúdo
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.addWidget(self.content_widget)
        
        # Atualiza o visual
        self.update_header()
        self.content_widget.setVisible(not collapsed)
    
    def update_header(self):
        """Atualiza o texto do cabeçalho com ícone de estado."""
        state_icon = "▼" if not self.collapsed else "▶"
        self.header_btn.setText(f"{state_icon} {self.icon} {self.title_text}")
    
    def toggle_collapsed(self):
        """Alterna entre expandido e colapsado."""
        self.collapsed = not self.collapsed
        self.content_widget.setVisible(not self.collapsed)
        self.update_header()
    
    def set_collapsed(self, collapsed):
        """Define o estado colapsado programaticamente."""
        self.collapsed = collapsed
        self.content_widget.setVisible(not collapsed)
        self.update_header()
    
    def get_content_layout(self):
        """Retorna o layout onde deve ser adicionado o conteúdo."""
        return self.content_layout

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

        # Configuração da janela com detecção automática de resolução
        self.setWindowTitle("Robô Garçom Autônomo")
        
        # Detecta resolução da tela para otimizar interface
        screen = QApplication.primaryScreen().geometry()
        screen_width = screen.width()
        screen_height = screen.height()
        
        # Adapta tamanho da janela baseado na resolução
        if screen_width <= 800 or screen_height <= 600:
            # Tela pequena (Raspberry Pi) - maximiza e otimiza espaço
            self.setGeometry(0, 0, screen_width, screen_height)
            self.is_small_screen = True
            self.showMaximized()
        else:
            # Tela grande (desenvolvimento) - janela padrão
            self.setGeometry(100, 100, 1200, 800)
            self.is_small_screen = False
            
        print(f"🖥️  Resolução detectada: {screen_width}x{screen_height} | Modo: {'Compacto' if self.is_small_screen else 'Desktop'}")
        
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
        
        # === PAINEL DE CONTROLE OTIMIZADO ===
        # Cria scroll area para adaptar a telas pequenas
        control_scroll = QScrollArea()
        control_scroll.setWidgetResizable(True)
        control_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        control_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Widget principal dos controles
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        control_layout.setSpacing(5)
        control_layout.setContentsMargins(5, 5, 5, 5)
        
        # Configura o scroll area
        control_scroll.setWidget(control_widget)
        control_scroll.setMinimumWidth(280 if self.is_small_screen else 350)
        control_scroll.setMaximumWidth(300 if self.is_small_screen else 400)
        
        # === 📍 PONTOS DE INTERESSE (Colapsável) ===
        poi_group = CollapsibleGroupBox("Pontos de Interesse", "📍", collapsed=True)
        poi_layout = poi_group.get_content_layout()
        
        # Lista de pontos
        self.poi_combo = QComboBox()
        poi_layout.addWidget(QLabel("Pontos disponíveis:"))
        poi_layout.addWidget(self.poi_combo)
        
        # Botões de pontos
        poi_buttons = QGridLayout()
        add_poi_btn = QPushButton("➕ Adicionar")
        add_poi_btn.clicked.connect(self._add_point_of_interest)
        delete_poi_btn = QPushButton("🗑️ Excluir")
        delete_poi_btn.clicked.connect(self._delete_point_of_interest)
        
        # Botões menores para tela pequena
        if self.is_small_screen:
            add_poi_btn.setMaximumHeight(30)
            delete_poi_btn.setMaximumHeight(30)
        
        poi_buttons.addWidget(add_poi_btn, 0, 0)
        poi_buttons.addWidget(delete_poi_btn, 0, 1)
        
        # NOVO: Botões de exportar/importar JSON
        export_poi_btn = QPushButton("💾 Exportar JSON")
        export_poi_btn.clicked.connect(self._export_pois_json)
        export_poi_btn.setToolTip("Exporta POIs para arquivo JSON")
        import_poi_btn = QPushButton("📥 Importar JSON")
        import_poi_btn.clicked.connect(self._import_pois_json)
        import_poi_btn.setToolTip("Importa POIs de arquivo JSON")
        
        if self.is_small_screen:
            export_poi_btn.setMaximumHeight(30)
            import_poi_btn.setMaximumHeight(30)
        
        poi_buttons.addWidget(export_poi_btn, 1, 0)
        poi_buttons.addWidget(import_poi_btn, 1, 1)
        
        poi_layout.addLayout(poi_buttons)
        
        # === 🚫 ÁREAS PROIBIDAS (Colapsável) ===
        forbidden_group = CollapsibleGroupBox("Áreas Proibidas", "🚫", collapsed=True)
        forbidden_layout = forbidden_group.get_content_layout()
        
        # Lista de áreas proibidas
        self.forbidden_areas_combo = QComboBox()
        forbidden_layout.addWidget(QLabel("Áreas proibidas:"))
        forbidden_layout.addWidget(self.forbidden_areas_combo)
        
        forbidden_buttons = QGridLayout()
        add_forbidden_btn = QPushButton("➕ Adicionar")
        add_forbidden_btn.clicked.connect(self._add_forbidden_area)
        delete_forbidden_btn = QPushButton("🗑️ Excluir")
        delete_forbidden_btn.clicked.connect(self._delete_forbidden_area)
        
        # Botões menores para tela pequena
        if self.is_small_screen:
            add_forbidden_btn.setMaximumHeight(30)
            delete_forbidden_btn.setMaximumHeight(30)
        
        forbidden_buttons.addWidget(add_forbidden_btn, 0, 0)
        forbidden_buttons.addWidget(delete_forbidden_btn, 0, 1)
        
        # NOVO: Botões de exportar/importar JSON para áreas
        export_area_btn = QPushButton("💾 Exportar JSON")
        export_area_btn.clicked.connect(self._export_areas_json)
        export_area_btn.setToolTip("Exporta áreas proibidas para arquivo JSON")
        import_area_btn = QPushButton("📥 Importar JSON")
        import_area_btn.clicked.connect(self._import_areas_json)
        import_area_btn.setToolTip("Importa áreas proibidas de arquivo JSON")
        
        if self.is_small_screen:
            export_area_btn.setMaximumHeight(30)
            import_area_btn.setMaximumHeight(30)
        
        forbidden_buttons.addWidget(export_area_btn, 1, 0)
        forbidden_buttons.addWidget(import_area_btn, 1, 1)
        
        forbidden_layout.addLayout(forbidden_buttons)

        # === 🗺️ GERENCIAMENTO DE MAPAS (Colapsável) ===
        map_management_group = CollapsibleGroupBox("Gerenciar Mapas", "🗺️", collapsed=True)
        map_management_layout = map_management_group.get_content_layout()

        # Grid de botões de mapa
        map_buttons_grid = QGridLayout()
        
        save_map_btn = QPushButton("💾 Salvar")
        save_map_btn.clicked.connect(self._save_map)
        load_map_btn = QPushButton("📂 Carregar")
        load_map_btn.clicked.connect(self._load_active_map)
        
        # NOVO: Botão para carregar mapa PGM
        load_pgm_btn = QPushButton("🗺️ Carregar PGM")
        load_pgm_btn.clicked.connect(self._load_pgm_map)
        load_pgm_btn.setToolTip("Carrega mapa PGM gerado do Aurora como fundo")
        
        autosave_btn = QPushButton("🔄 Autosave: ON")
        autosave_btn.clicked.connect(self._toggle_autosave)
        self.autosave_button = autosave_btn  # Referência para atualizar o texto

        calibrate_btn = QPushButton("⚙️ Calibrar PID")
        calibrate_btn.clicked.connect(self._open_calibration_window)

        # Botões menores para tela pequena
        map_buttons = [save_map_btn, load_map_btn, load_pgm_btn, autosave_btn, calibrate_btn]
        if self.is_small_screen:
            for btn in map_buttons:
                btn.setMaximumHeight(30)

        map_buttons_grid.addWidget(save_map_btn, 0, 0)
        map_buttons_grid.addWidget(load_map_btn, 0, 1)
        map_buttons_grid.addWidget(load_pgm_btn, 1, 0)
        map_buttons_grid.addWidget(autosave_btn, 1, 1)
        map_buttons_grid.addWidget(calibrate_btn, 2, 0, 1, 2)  # Ocupa 2 colunas
        map_management_layout.addLayout(map_buttons_grid)
        
        # === 🎯 NAVEGAÇÃO (Expansível, inicialmente aberto) ===
        nav_group = CollapsibleGroupBox("Navegação", "🎯", collapsed=False)
        nav_layout = nav_group.get_content_layout()
        
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

        # === NOVO SISTEMA DE CONTROLE DE VELOCIDADE ===
        speed_group = QGroupBox("Controle de Velocidade")
        speed_group_layout = QVBoxLayout()
        
        # Seletor de perfil de velocidade
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel("Modo:"))
        
        self.speed_profile_combo = QComboBox()
        self.speed_profile_combo.addItem("🐌 Lenta (Precisão)", "slow")
        self.speed_profile_combo.addItem("⚡ Normal (Balanceado)", "normal") 
        self.speed_profile_combo.addItem("🚀 Rápida (Velocidade)", "fast")
        self.speed_profile_combo.setCurrentIndex(1)  # Normal como padrão
        self.speed_profile_combo.currentTextChanged.connect(self._on_speed_profile_changed)
        profile_layout.addWidget(self.speed_profile_combo)
        speed_group_layout.addLayout(profile_layout)
        
        # Informações do perfil atual
        self.speed_info_label = QLabel("Normal: Navegação balanceada - uso geral")
        self.speed_info_label.setStyleSheet("color: #666; font-size: 10px;")
        speed_group_layout.addWidget(self.speed_info_label)
        
        # Slider de ajuste fino (multiplicador)
        fine_tune_layout = QHBoxLayout()
        fine_tune_layout.addWidget(QLabel("Ajuste:"))
        
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(80)   # 80% do perfil selecionado
        self.speed_slider.setMaximum(120)  # 120% do perfil selecionado (com validação de segurança)
        self.speed_slider.setValue(100)    # 100% = valor padrão do perfil
        self.speed_slider.valueChanged.connect(self._on_speed_slider_changed)
        fine_tune_layout.addWidget(self.speed_slider)
        
        self.speed_percent_label = QLabel("100%")
        fine_tune_layout.addWidget(self.speed_percent_label)
        speed_group_layout.addLayout(fine_tune_layout)
        
        # Status de segurança
        self.safety_status_label = QLabel("🟢 Sistema Seguro")
        self.safety_status_label.setStyleSheet("color: green; font-weight: bold;")
        speed_group_layout.addWidget(self.safety_status_label)
        
        speed_group.setLayout(speed_group_layout)
        nav_layout.addWidget(speed_group)

        nav_buttons = QGridLayout()
        start_nav_btn = QPushButton("🚀 Iniciar" if self.is_small_screen else "🚀 Iniciar Navegação")
        start_nav_btn.clicked.connect(self._start_navigation)
        stop_nav_btn = QPushButton("🛑 Parar")
        stop_nav_btn.clicked.connect(self._stop_robot)
        
        # Botões menores para tela pequena
        if self.is_small_screen:
            start_nav_btn.setMaximumHeight(35)
            stop_nav_btn.setMaximumHeight(35)
            start_nav_btn.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
            stop_nav_btn.setStyleSheet("font-weight: bold; background-color: #f44336; color: white;")
        
        nav_buttons.addWidget(start_nav_btn, 0, 0)
        nav_buttons.addWidget(stop_nav_btn, 0, 1)
        nav_layout.addLayout(nav_buttons)
        
        # === 🕹️ CONTROLES MANUAIS (Expansível, inicialmente aberto) ===
        manual_control_group = CollapsibleGroupBox("Controles Manuais", "🕹️", collapsed=False)
        manual_layout = manual_control_group.get_content_layout()

        # Grid de botões direcionais otimizado para tela pequena
        direction_grid = QGridLayout()
        direction_grid.setSpacing(3 if self.is_small_screen else 5)
        
        # Tamanhos adaptativos
        btn_size = 35 if self.is_small_screen else 40
        rotate_width = 60 if self.is_small_screen else 80
        rotate_height = 25 if self.is_small_screen else 40
        
        # Botão FRENTE (⬆️)
        self.btn_forward = QPushButton("⬆️")
        self.btn_forward.setFixedSize(btn_size, btn_size)
        self.btn_forward.pressed.connect(lambda: self._manual_move_start("forward"))
        self.btn_forward.released.connect(self._manual_move_stop)
        if self.is_small_screen:
            self.btn_forward.setStyleSheet("font-size: 14px; font-weight: bold;")
        direction_grid.addWidget(self.btn_forward, 0, 1)
        
        # Botão GIRO MANUAL ESQUERDA (22° padrão)
        self.btn_rotate_manual_left = QPushButton("↺ 180° ESQ" if self.is_small_screen else "↺ 180° ESQUERDA")
        self.btn_rotate_manual_left.setFixedSize(rotate_width, rotate_height)
        self.btn_rotate_manual_left.clicked.connect(self._manual_turn_left)
        if self.is_small_screen:
            self.btn_rotate_manual_left.setStyleSheet("font-size: 9px; font-weight: bold; background-color: #2196F3; color: white;")
        else:
            self.btn_rotate_manual_left.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        direction_grid.addWidget(self.btn_rotate_manual_left, 1, 0)
        
        # Botão GIRO MANUAL DIREITA (22° padrão)
        self.btn_rotate_manual_right = QPushButton("↻ 180° DIR" if self.is_small_screen else "↻ 180° DIREITA")
        self.btn_rotate_manual_right.setFixedSize(rotate_width, rotate_height)
        self.btn_rotate_manual_right.clicked.connect(self._manual_turn_right)
        if self.is_small_screen:
            self.btn_rotate_manual_right.setStyleSheet("font-size: 9px; font-weight: bold; background-color: #2196F3; color: white;")
        else:
            self.btn_rotate_manual_right.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        direction_grid.addWidget(self.btn_rotate_manual_right, 1, 2)
        
        # Botão TRÁS (⬇️)
        self.btn_backward = QPushButton("⬇️")
        self.btn_backward.setFixedSize(btn_size, btn_size)
        self.btn_backward.pressed.connect(lambda: self._manual_move_start("backward"))
        self.btn_backward.released.connect(self._manual_move_stop)
        if self.is_small_screen:
            self.btn_backward.setStyleSheet("font-size: 14px; font-weight: bold;")
        direction_grid.addWidget(self.btn_backward, 2, 1)

        # Adiciona o grid ao layout manual
        manual_layout.addLayout(direction_grid)

        # Slider para ângulo customizável (integrado ao layout principal)
        angle_layout = QHBoxLayout()
        angle_layout.addWidget(QLabel("Ângulo por clique:"))
        self.angle_slider = QSlider(Qt.Orientation.Horizontal)
        self.angle_slider.setRange(15, 90)  # 15° a 90° por clique
        self.angle_slider.setValue(45)      # Padrão: 45°
        self.angle_slider.valueChanged.connect(self._on_angle_slider_changed)
        angle_layout.addWidget(self.angle_slider)
        self.angle_label = QLabel("45°")
        angle_layout.addWidget(self.angle_label)
        manual_layout.addLayout(angle_layout)

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
        
        # === ORDEM OTIMIZADA PARA TELAS PEQUENAS ===
        # Prioritários (sempre visíveis) primeiro
        control_layout.addWidget(nav_group)
        control_layout.addWidget(manual_control_group)
        
        # Secundários (colapsáveis) depois
        control_layout.addWidget(poi_group)
        control_layout.addWidget(forbidden_group)
        control_layout.addWidget(map_management_group)
        
        control_layout.addStretch()  # Empurra tudo para o topo
        
        # Adiciona os painéis ao layout principal
        main_layout.addLayout(map_layout, stretch=2)
        main_layout.addWidget(control_scroll, stretch=1)
        
        # Define o layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Inicializa o navegador
        self.navigator = RobotNavigator()
        
        # Conecta o sinal de atualização de posição do navegador ao slot da UI
        self.navigator.position_updated.connect(self._update_robot_position_on_map)

        # Configura callbacks do mapa
        self.map_widget.area_clicked_callback = self._on_area_clicked
        
        # Timer para autosave periódico
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self._check_periodic_autosave)
        self.autosave_timer.start(30000)
        
        # Tenta carregar o último mapa ativo ao iniciar
        self._load_active_map()
        
        # Timer para o loop de atualização principal
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._main_update_loop)
        self.update_timer.start(100)  # 10 Hz (100ms)

        # Carrega e aplica os ganhos do PID salvos
        self._load_and_apply_pid_gains()
        
        # Timer para atualizar status de segurança
        self.safety_timer = QTimer()
        self.safety_timer.timeout.connect(self._update_safety_status)
        self.safety_timer.start(1000)  # Atualiza a cada 1 segundo

    def _load_and_apply_pid_gains(self):
        """Carrega os ganhos do PID do banco de dados e os aplica ao controlador."""
        saved_gains = self.map_manager.get_pid_gains()
        if saved_gains:
            motor_controller = self.navigator.get_motor_controller()
            if motor_controller:
                motor_controller.set_pid_gains('left', saved_gains['left']['kp'], saved_gains['left']['ki'], saved_gains['left']['kd'])
                motor_controller.set_pid_gains('right', saved_gains['right']['kp'], saved_gains['right']['ki'], saved_gains['right']['kd'])

    def _update_robot_position_on_map(self, x: float, y: float, angle: float):
        """
        Slot para receber a atualização de posição do navegador e atualizar o widget do mapa.
        """
        self.map_widget.update_robot_position(x, y, angle)

    def _open_calibration_window(self):
        """Abre a janela de calibração do PID."""
        motor_controller = self.navigator.get_motor_controller()
        if motor_controller:
            self.calibration_win = CalibrationWindow(motor_controller, self)
            self.calibration_win.show()
        else:
            QMessageBox.warning(self, "Erro", "Controlador de motor não está disponível.")

    def _load_active_map(self):
        """Carrega o mapa ativo ou permite seleção de um mapa"""
        from pathlib import Path
        
        # Lista mapas do banco de dados
        db_map_names = self.map_manager.get_all_map_names()
        
        # Lista mapas PGM disponíveis
        pgm_dir = Path("mapas/otimizados")
        pgm_maps = []
        if pgm_dir.exists():
            pgm_maps = [f.stem for f in pgm_dir.glob("*.pgm")]
        
        # Combina ambas as listas
        all_maps = []
        if db_map_names:
            all_maps.extend([f"🗄️ {name}" for name in db_map_names])
        if pgm_maps:
            all_maps.extend([f"🗺️ {name}" for name in pgm_maps])
        
        if all_maps:
            map_name, ok = QInputDialog.getItem(
                self, "Carregar Mapa", "Selecione um mapa para carregar:", all_maps, 0, False
            )
            if ok and map_name:
                # Verifica se é um mapa PGM ou do banco
                if map_name.startswith("🗺️ "):
                    # É um mapa PGM
                    pgm_name = map_name.replace("🗺️ ", "")
                    pgm_path = pgm_dir / f"{pgm_name}.pgm"
                    yaml_path = pgm_dir / f"{pgm_name}.yaml"
                    
                    if pgm_path.exists():
                        if self.map_widget.load_pgm_map(str(pgm_path), str(yaml_path) if yaml_path.exists() else None):
                            self.status_label.setText(f"Mapa PGM carregado: {pgm_name}")
                            QMessageBox.information(
                                self,
                                "Mapa Carregado",
                                f"Mapa PGM carregado com sucesso!\n\n"
                                f"Arquivo: {pgm_name}.pgm"
                            )
                        else:
                            QMessageBox.warning(self, "Erro", "Não foi possível carregar o mapa PGM.")
                    else:
                        QMessageBox.warning(self, "Erro", f"Arquivo PGM não encontrado: {pgm_path}")
                else:
                    # É um mapa do banco de dados
                    db_name = map_name.replace("🗄️ ", "")
                    self.map_manager.load_map_by_name(db_name)
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
            self.status_label.setText("Nenhum mapa encontrado. Crie um novo mapa ou processe um mapa do Aurora.")
            
    def _reset_robot_to_base(self):
        """Reseta o robô para a posição base com ângulo inicial."""
        self.navigator.reset_to_initial_state()
        self.map_widget.update_robot_position(ROBOT_INITIAL_POSITION[0], ROBOT_INITIAL_POSITION[1], ROBOT_INITIAL_ANGLE)
        
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
            
    def _main_update_loop(self):
        """
        Loop principal que roda continuamente para atualizar o estado do robô e da UI.
        """
        self.navigator.update()

        if not self.navigation_active:
            return

        nav_status = self.navigator.get_navigation_status()
        progress = int(nav_status.get("progress", 0) * 100)
        self.nav_progress_bar.setValue(progress)

        state_text = nav_status.get("state", "IDLE")
        time_remaining = nav_status.get("estimated_time_remaining", 0)

        if nav_status.get("is_paused_at_destination", False):
            info_text = f"Estado: {state_text} | Pausado no destino"
        elif time_remaining > 0:
            info_text = f"Estado: {state_text} | Tempo: {time_remaining:.1f}s"
        else:
            info_text = f"Estado: {state_text}"
            
        self.nav_info_label.setText(info_text)

        if state_text in ["COMPLETED", "IDLE"]:
            self._complete_navigation_and_reset()
            QMessageBox.information(self, "Navegação", "Navegação concluída!")

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
        path_finder = self.navigator.path_finder
        grid_x = int(x / path_finder.grid_size)
        grid_y = int(y / path_finder.grid_size)

        if path_finder._is_in_forbidden_area(grid_x, grid_y):
            QMessageBox.warning(
                self, 
                "Ponto Inválido", 
                "Não é possível criar um ponto de interesse dentro ou muito perto de uma área proibida."
            )
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
        dialog.x_spin.setValue(int(x * 100))
        dialog.y_spin.setValue(int(y * 100))
        if dialog.exec_():
            name, position, point_type = dialog.get_point_data()
            if name:
                self.map_widget.points_of_interest[name] = (x, y, point_type)
                self.map_widget.update()
                self._update_points_list()
                self._update_destination_combo()
                self._mark_unsaved_changes()
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
                self.map_widget.update()
                self._update_points_list()
                self._update_destination_combo()
                self._mark_unsaved_changes()
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
        
        if len(self.map_widget.current_forbidden_area) >= 3:
            area_count = len(self.map_widget.forbidden_areas) + 1
            area_name = f"Área Proibida {area_count}"
            
            success = self.map_manager.save_forbidden_area(
                self.map_widget.current_forbidden_area, 
                area_name
            )
            
            if success:
                self.map_widget.current_forbidden_area = []
                self._reload_forbidden_areas()
                self._mark_unsaved_changes()
                QMessageBox.information(self, "Sucesso", f"Área proibida '{area_name}' salva automaticamente!")
            else:
                QMessageBox.warning(self, "Erro", "Erro ao salvar área proibida no banco de dados!")
        else:
            QMessageBox.warning(self, "Aviso", "Área proibida deve ter pelo menos 3 pontos!")

    def _reload_forbidden_areas(self):
        """Recarrega as áreas proibidas do banco de dados."""
        if not self.current_map:
            self.current_map = self.map_manager.get_active_map()
            if not self.current_map:
                return
            
        areas_with_ids = self.map_manager.get_forbidden_areas_with_ids(self.current_map['id'])
        
        self.map_widget.forbidden_areas = areas_with_ids
        self.map_widget.update()
        
        self._update_forbidden_areas_list()
        
        areas_for_navigator = [area['coordenadas'] for area in areas_with_ids]
        self.navigator.set_forbidden_areas(areas_for_navigator)
        
    def _update_forbidden_areas_list(self):
        """Atualiza a lista de áreas proibidas no combo box."""
        self.forbidden_areas_combo.clear()
        for area_data in self.map_widget.forbidden_areas:
            if isinstance(area_data, dict):
                area_id = area_data.get('id', 0)
                area_name = area_data.get('nome', f'Área {area_id}')
                item_text = f"{area_name} (ID: {area_id})"
                self.forbidden_areas_combo.addItem(item_text)

    def _delete_forbidden_area(self):
        """Remove uma área proibida."""
        if not self.map_widget.forbidden_areas:
            QMessageBox.warning(self, "Aviso", "Não há áreas proibidas para excluir!")
            return
            
        selected_area = self.map_widget.get_selected_area()
        
        if selected_area:
            area_id = selected_area.get('id', 0)
            area_name = selected_area.get('nome', f'Área {area_id}')
        else:
            if self.forbidden_areas_combo.currentText():
                try:
                    combo_text = self.forbidden_areas_combo.currentText()
                    area_id = int(combo_text.split("ID: ")[1].rstrip(")"))
                    area_name = combo_text.split(" (ID:")[0]
                except Exception:
                    QMessageBox.warning(self, "Erro", "Erro ao identificar área selecionada!")
                    return
            else:
                QMessageBox.warning(self, "Aviso", "Selecione uma área para excluir!")
                return
        
        reply = QMessageBox.question(
            self, 'Confirmar Exclusão',
            f'Tem certeza que deseja excluir a área "{area_name}"?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = self.map_manager.delete_forbidden_area(area_id)
            
            if success:
                self._reload_forbidden_areas()
                self._mark_unsaved_changes()
                QMessageBox.information(self, "Sucesso", f"Área '{area_name}' excluída com sucesso!")
            else:
                QMessageBox.warning(self, "Erro", f"Erro ao excluir a área '{area_name}'!")

    def _save_map(self):
        """Salva o mapa atual no banco de dados."""
        map_name, ok = QInputDialog.getText(self, "Salvar Mapa", "Nome do Mapa:")
        if ok and map_name:
            self.map_manager.save_map(
                map_name,
                self.map_widget.points_of_interest,
                self.map_widget.forbidden_areas
            )
            self.has_unsaved_changes = False
            QMessageBox.information(self, "Salvar Mapa", f"Mapa '{map_name}' salvo com sucesso!")
        elif not map_name and ok:
            QMessageBox.warning(self, "Aviso", "O nome do mapa não pode ser vazio!")
    
    def _load_pgm_map(self):
        """Carrega mapa PGM como fundo do widget."""
        from pathlib import Path
        
        # Lista mapas PGM disponíveis
        pgm_dir = Path("mapas/otimizados")
        pgm_maps = []
        if pgm_dir.exists():
            pgm_maps = [f.stem for f in pgm_dir.glob("*.pgm")]
        
        if pgm_maps:
            # Mostra lista de mapas disponíveis
            map_name, ok = QInputDialog.getItem(
                self, "Carregar Mapa PGM", "Selecione um mapa PGM para carregar:", pgm_maps, 0, False
            )
            if ok and map_name:
                pgm_path = pgm_dir / f"{map_name}.pgm"
                yaml_path = pgm_dir / f"{map_name}.yaml"
                
                if self.map_widget.load_pgm_map(str(pgm_path), str(yaml_path) if yaml_path.exists() else None):
                    self.status_label.setText(f"Mapa PGM carregado: {map_name}")
                    QMessageBox.information(
                        self,
                        "Mapa Carregado",
                        f"Mapa PGM carregado com sucesso!\n\n"
                        f"Arquivo: {map_name}.pgm\n"
                        f"Tamanho: {self.map_widget.map_image.width()}x{self.map_widget.map_image.height()} pixels"
                    )
                else:
                    QMessageBox.warning(self, "Erro", "Não foi possível carregar o mapa PGM.")
        else:
            # Se não houver mapas na lista, abre diálogo de arquivo
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Carregar Mapa PGM",
                str(pgm_dir.absolute()) if pgm_dir.exists() else ".",
                "Arquivos PGM (*.pgm);;Todos os arquivos (*.*)"
            )
            
            if file_path:
                # Tenta encontrar arquivo YAML correspondente
                pgm_file = Path(file_path)
                yaml_file = pgm_file.with_suffix('.yaml')
                
                # Carrega no MapWidget
                if self.map_widget.load_pgm_map(str(pgm_file), str(yaml_file) if yaml_file.exists() else None):
                    self.status_label.setText(f"Mapa PGM carregado: {pgm_file.stem}")
                    QMessageBox.information(
                        self,
                        "Mapa Carregado",
                        f"Mapa PGM carregado com sucesso!\n\n"
                        f"Arquivo: {pgm_file.name}\n"
                        f"Tamanho: {self.map_widget.map_image.width()}x{self.map_widget.map_image.height()} pixels"
                    )
                else:
                    QMessageBox.warning(self, "Erro", "Não foi possível carregar o mapa PGM.")
            else:
                QMessageBox.information(
                    self,
                    "Nenhum Mapa",
                    "Nenhum mapa PGM encontrado em 'mapas/otimizados/'.\n\n"
                    "Processe um mapa do Aurora primeiro usando:\n"
                    "python3 converter_bmp_para_mapa.py"
                )
    
    def _export_pois_json(self):
        """Exporta POIs para arquivo JSON."""
        from pathlib import Path
        import json
        from datetime import datetime
        
        if not self.map_widget.points_of_interest:
            QMessageBox.warning(self, "Aviso", "Não há POIs para exportar.")
            return
        
        # Abre diálogo para salvar
        default_name = f"pois_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar POIs para JSON",
            str(Path("mapas/pois") / default_name),
            "Arquivos JSON (*.json);;Todos os arquivos (*.*)"
        )
        
        if file_path:
            try:
                # Prepara dados no formato JSON
                pois_data = {
                    "map_id": self.map_widget.map_name or "mapa_atual",
                    "version": "1.0",
                    "created_at": datetime.now().isoformat(),
                    "pois": []
                }
                
                for name, point_data in self.map_widget.points_of_interest.items():
                    if isinstance(point_data, tuple) and len(point_data) >= 2:
                        x, y = point_data[0], point_data[1]
                        point_type = point_data[2] if len(point_data) > 2 else "delivery"
                        
                        pois_data["pois"].append({
                            "id": name.lower().replace(" ", "_"),
                            "name": name,
                            "x": float(x),
                            "y": float(y),
                            "orientation": 0.0,
                            "type": point_type,
                            "description": f"POI {name}",
                            "enabled": True,
                            "priority": "normal"
                        })
                
                # Salva arquivo
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(pois_data, f, indent=2, ensure_ascii=False)
                
                QMessageBox.information(
                    self,
                    "Exportação Concluída",
                    f"POIs exportados com sucesso!\n\n"
                    f"Arquivo: {Path(file_path).name}\n"
                    f"Total: {len(pois_data['pois'])} POIs"
                )
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao exportar POIs:\n{str(e)}")
    
    def _import_pois_json(self):
        """Importa POIs de arquivo JSON."""
        from pathlib import Path
        import json
        
        # Abre diálogo para escolher arquivo
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Importar POIs de JSON",
            str(Path("mapas/pois").absolute()),
            "Arquivos JSON (*.json);;Todos os arquivos (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    pois_data = json.load(f)
                
                # Processa POIs
                imported_count = 0
                for poi in pois_data.get('pois', []):
                    name = poi.get('name', poi.get('id', f"poi_{imported_count}"))
                    x = float(poi.get('x', 0))
                    y = float(poi.get('y', 0))
                    point_type = poi.get('type', 'delivery')
                    
                    # Adiciona ao mapa (sobrescreve se já existir)
                    self.map_widget.points_of_interest[name] = (x, y, point_type)
                    imported_count += 1
                
                # Atualiza interface
                self._update_points_list()
                self.map_widget.update()
                
                QMessageBox.information(
                    self,
                    "Importação Concluída",
                    f"POIs importados com sucesso!\n\n"
                    f"Total: {imported_count} POIs"
                )
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao importar POIs:\n{str(e)}")
    
    def _export_areas_json(self):
        """Exporta áreas proibidas para arquivo JSON."""
        from pathlib import Path
        import json
        from datetime import datetime
        
        areas_list = self.map_widget.get_forbidden_areas_list()
        if not areas_list:
            QMessageBox.warning(self, "Aviso", "Não há áreas proibidas para exportar.")
            return
        
        # Abre diálogo para salvar
        default_name = f"areas_proibidas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Áreas Proibidas para JSON",
            str(Path("mapas/areas_proibidas") / default_name),
            "Arquivos JSON (*.json);;Todos os arquivos (*.*)"
        )
        
        if file_path:
            try:
                # Prepara dados no formato JSON
                areas_data = {
                    "map_id": self.map_widget.map_name or "mapa_atual",
                    "version": "1.0",
                    "created_at": datetime.now().isoformat(),
                    "forbidden_areas": []
                }
                
                for area in areas_list:
                    area_id = area.get('id', 0)
                    area_name = area.get('nome', f"Área {area_id}")
                    coordinates = area.get('coordenadas', [])
                    
                    if coordinates and len(coordinates) >= 3:
                        areas_data["forbidden_areas"].append({
                            "id": f"area_{area_id}",
                            "name": area_name,
                            "type": "polygon",
                            "points": [{"x": float(x), "y": float(y)} for x, y in coordinates],
                            "priority": "high",
                            "enabled": True,
                            "description": f"Área proibida: {area_name}"
                        })
                
                # Salva arquivo
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(areas_data, f, indent=2, ensure_ascii=False)
                
                QMessageBox.information(
                    self,
                    "Exportação Concluída",
                    f"Áreas proibidas exportadas com sucesso!\n\n"
                    f"Arquivo: {Path(file_path).name}\n"
                    f"Total: {len(areas_data['forbidden_areas'])} áreas"
                )
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao exportar áreas:\n{str(e)}")
    
    def _import_areas_json(self):
        """Importa áreas proibidas de arquivo JSON."""
        from pathlib import Path
        import json
        
        # Abre diálogo para escolher arquivo
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Importar Áreas Proibidas de JSON",
            str(Path("mapas/areas_proibidas").absolute()),
            "Arquivos JSON (*.json);;Todos os arquivos (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    areas_data = json.load(f)
                
                # Processa áreas
                imported_count = 0
                for area in areas_data.get('forbidden_areas', []):
                    area_name = area.get('name', f"Área {imported_count}")
                    points = area.get('points', [])
                    
                    if points and len(points) >= 3:
                        # Converte pontos para formato esperado
                        coordinates = [(float(p['x']), float(p['y'])) for p in points]
                        
                        # Adiciona ao mapa
                        area_dict = {
                            'id': len(self.map_widget.forbidden_areas),
                            'nome': area_name,
                            'coordenadas': coordinates
                        }
                        self.map_widget.add_forbidden_area(area_dict)
                        imported_count += 1
                
                # Atualiza interface
                self._update_forbidden_areas_list()
                self.map_widget.update()
                
                QMessageBox.information(
                    self,
                    "Importação Concluída",
                    f"Áreas proibidas importadas com sucesso!\n\n"
                    f"Total: {imported_count} áreas"
                )
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao importar áreas:\n{str(e)}")

    def _start_navigation(self):
        """Inicia a navegação autônoma com feedback melhorado"""
        if self.navigation_active:
            QMessageBox.information(self, "Navegação", "O robô já está navegando.")
            return
            
        self.navigator.reset_to_initial_state()
        self.navigator.is_adjusting_final_angle = False
        self.navigator.is_returning_to_base = False
        self.navigator.navigation_state = "IDLE"
        self.navigator.current_target = None
        self.navigator.path = []
        self.navigator.path_index = 0
            
        if not self.destination_combo.currentText():
            QMessageBox.warning(self, "Erro", "Selecione um destino para navegar.")
            return
            
        destination_text = self.destination_combo.currentText()
        destination_name = destination_text.split(" (")[0]
        
        destination = self.map_widget.points_of_interest.get(destination_name)
        
        if not destination:
            QMessageBox.warning(self, "Erro", f"Destino '{destination_name}' não encontrado.")
            return
            
        try:
            # 🚀 NOVA FASE: Navegação automática completa (ida + volta)
            self.navigator.navigate_to_and_return(destination)
            self.navigation_active = True
            
            if hasattr(self.navigator, 'path') and self.navigator.path:
                self.map_widget.set_current_path(self.navigator.path)
            
            self.nav_status_label.setText("Status: Navegação automática (ida + volta)...")
            self.nav_progress_bar.setVisible(True)
            self.nav_progress_bar.setValue(0)
            self.nav_info_label.setVisible(True)
            self.status_label.setText("Navegação automática ativa...")
            
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao iniciar navegação:\n{e}")
            
    def _stop_robot(self):
        """Para o robô e atualiza a interface."""
        self.navigator.motors.stop()
        self.navigation_active = False
        
        self.nav_status_label.setText("Status: Parado")
        self.nav_progress_bar.setVisible(False)
        self.nav_info_label.setVisible(False)
        self.status_label.setText("Modo: Manual")

    def _mark_unsaved_changes(self):
        """Marca que há alterações não salvas."""
        self.has_unsaved_changes = True
        current_status = self.status_label.text()
        if "(*)" not in current_status:
            self.status_label.setText(f"{current_status} (*)")
        
    def _perform_autosave(self, show_message=False):
        """Executa o autosave automático."""
        if not self.autosave_enabled or not self.has_unsaved_changes:
            return
            
        try:
            if self.current_map:
                map_name = self.current_map['nome']
            else:
                map_name = f"Mapa_Auto_{int(time.time())}"
                
            self.map_manager.save_map(
                map_name,
                self.map_widget.points_of_interest,
                self.map_widget.forbidden_areas
            )
            
            self.has_unsaved_changes = False
            self.last_autosave_time = time.time()
            
            current_status = self.status_label.text()
            if "(*)" in current_status:
                self.status_label.setText(current_status.replace(" (*)", ""))
            
            if show_message:
                QMessageBox.information(self, "Autosave", f"Mapa '{map_name}' salvo automaticamente!")
                
        except Exception as e:
            if show_message:
                QMessageBox.warning(self, "Erro no Autosave", f"Erro ao salvar automaticamente: {str(e)}")
                
    def _check_unsaved_changes(self) -> bool:
        """Verifica se há alterações não salvas e pergunta ao usuário."""
        if not self.has_unsaved_changes:
            return True
            
        if self.autosave_enabled:
            self._perform_autosave(show_message=False)
            return True
            
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
        else:
            return False
            
    def _toggle_autosave(self):
        """Alterna o estado do autosave."""
        self.autosave_enabled = not self.autosave_enabled
        status = "ON" if self.autosave_enabled else "OFF"
        self.autosave_button.setText(f"Autosave: {status}")
        QMessageBox.information(self, "Autosave", f"Autosave {status.lower()}!")
            
    def closeEvent(self, event):
        """Limpa recursos ao fechar a janela."""
        if not self._check_unsaved_changes():
            event.ignore()
            return
            
        if self.autosave_enabled and self.has_unsaved_changes:
            self._perform_autosave(show_message=False)
            
        self.navigator.motors.cleanup()
        self.map_manager.close()
        event.accept()

    def _check_periodic_autosave(self):
        """Executa o autosave periódico."""
        if self.autosave_enabled and self.has_unsaved_changes:
            current_time = time.time()
            if (self.last_autosave_time is None or 
                current_time - self.last_autosave_time >= 30):
                self._perform_autosave(show_message=False)

    def _on_area_clicked(self, area_id: int):
        """Callback para quando uma área proibida é clicada."""
        pass

    def _on_speed_profile_changed(self):
        """Chamado quando o perfil de velocidade é alterado."""
        profile_data = self.speed_profile_combo.currentData()
        if profile_data and self.navigator and self.navigator.motors:
            # Aplica o novo perfil no controlador de motores
            success = self.navigator.motors.set_speed_profile(profile_data)
            
            if success:
                # Atualiza informações na interface
                profile_info = self.navigator.motors.get_current_speed_profile()
                self.speed_info_label.setText(f"{profile_info['description']}")
                
                # Reseta o slider para 100% do novo perfil
                self.speed_slider.setValue(100)
                self.speed_percent_label.setText("100%")
                
                # Aplica o novo multiplicador
                self.navigator.set_speed_multiplier(1.0)
                
                print(f"✅ Perfil de velocidade alterado: {profile_info['name']} - {profile_info['tps']} TPS")

    def _on_speed_slider_changed(self, value):
        """Atualiza o ajuste fino da velocidade quando o slider é movido."""
        self.speed_percent_label.setText(f"{value}%")
        
        # Calcula o multiplicador baseado no slider (80% a 120% do perfil atual)
        multiplier = value / 100.0
        
        if self.navigator:
            self.navigator.set_speed_multiplier(multiplier)
            
            # Atualiza status de segurança se necessário
            self._update_safety_status()

    def _update_safety_status(self):
        """Atualiza o status do sistema de segurança na interface."""
        if self.navigator and self.navigator.motors:
            safety_status = self.navigator.motors.get_safety_status()
            
            if safety_status['violation_active']:
                # Sistema em violação
                duration = safety_status['violation_duration']
                self.safety_status_label.setText(f"🔴 AVISO: Excesso potência ({duration:.1f}s)")
                self.safety_status_label.setStyleSheet("color: red; font-weight: bold;")
            elif safety_status['monitor_enabled']:
                # Sistema funcionando normalmente
                profile = safety_status['current_profile']
                self.safety_status_label.setText(f"🟢 Sistema Seguro ({profile})")
                self.safety_status_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                # Monitor desabilitado
                self.safety_status_label.setText("🟡 Monitor Desabilitado")
                self.safety_status_label.setStyleSheet("color: orange; font-weight: bold;")

    def _complete_navigation_and_reset(self):
        """Completa a navegação e faz reset completo da interface para permitir nova navegação"""
        self.navigation_active = False
        self.navigator.navigation_active = False
        self.navigator.motors.stop()
        
        self.map_widget.set_current_path([])
        
        current_pos = self.navigator.current_position
        current_angle = self.navigator.current_angle
        
        self.navigator.reset_to_initial_state()
        
        self.navigator.current_position = current_pos
        self.navigator.current_angle = current_angle
        
        self.nav_status_label.setText("Status: Pronto (nova partida)")
        self.nav_progress_bar.setVisible(False)
        self.nav_info_label.setVisible(False)
        self.status_label.setText("Modo: Manual")
        
        self.map_widget.update_robot_position(
            current_pos[0], 
            current_pos[1], 
            current_angle
        )

    def _manual_move_start(self, direction: str):
        """Inicia o movimento manual contínuo."""
        if self.navigation_active:
            QMessageBox.warning(self, "Aviso", "Não é possível usar controles manuais durante a navegação automática.")
            return

        MANUAL_FORWARD_SPEED = 36  # AUMENTADO 20% para teste (era 30)
        MANUAL_BACKWARD_SPEED = 28  # CORRIGIDO: 20% menor que frente para evitar velocidade reversa muito alta
        MANUAL_TURN_SPEED = 14     # AUMENTADO 20% para teste (era 12)

        if direction == "forward":
            self.navigator.motors.set_speed(MANUAL_FORWARD_SPEED, MANUAL_FORWARD_SPEED)
        elif direction == "backward":
            self.navigator.motors.set_speed(-MANUAL_BACKWARD_SPEED, -MANUAL_BACKWARD_SPEED)
        elif direction == "left":
            self.navigator.motors.set_speed(-MANUAL_TURN_SPEED, MANUAL_TURN_SPEED)
        elif direction == "right":
            self.navigator.motors.set_speed(MANUAL_TURN_SPEED, -MANUAL_TURN_SPEED)

    def _manual_move_stop(self):
        """Para o movimento manual."""
        self.navigator.motors.stop()

    def _execute_precise_rotation(self, direction: str):
        """Executa rotação precisa baseada no ângulo configurado com sincronia melhorada."""
        if self.navigation_active:
            QMessageBox.warning(self, "Aviso", "Não é possível usar controles manuais durante a navegação automática.")
            return

        print(f"🔄 SYNC_START: Iniciando giro {direction} com sincronia melhorada")
        
        # 🔄 ATIVA modo de giro preciso no navegador para sincronia
        self.navigator.start_precise_rotation()
        
        # 🔧 SALVA o ângulo inicial para sincronização precisa
        self.initial_angle_for_sync = self.navigator.current_angle
        print(f"🔄 SYNC_INIT: Ângulo inicial para sincronia: {self.initial_angle_for_sync:.1f}°")
        
        # 🎯 NOVO: Salva a posição inicial para manter fixa durante giros
        self.initial_position_for_sync = self.navigator.current_position
        print(f"🔄 SYNC_INIT: Posição inicial para sincronia: ({self.initial_position_for_sync[0]:.2f}, {self.initial_position_for_sync[1]:.2f})")

        angle_per_click = self.angle_slider.value()
        
        # 🎯 TEMPOS CALIBRADOS para máxima precisão (baseado em testes)
        if angle_per_click <= 15:
            rotation_time = 0.25  # 15° em 0.25s (aumentado para mais precisão)
        elif angle_per_click <= 30:
            rotation_time = 0.45  # 30° em 0.45s (aumentado para mais precisão)
        elif angle_per_click <= 45:
            rotation_time = 0.85  # 45° em 0.85s (aumentado para mais precisão)
        elif angle_per_click <= 60:
            rotation_time = 0.85  # 60° em 0.85s
        elif angle_per_click <= 90:
            rotation_time = 1.25  # 90° em 1.25s (aumentado para mais precisão)
        else:
            rotation_time = 1.6   # Fallback para ângulos maiores (aumentado)

        # 🚀 BYPASS do PID com proteção de segurança máxima
        # 8% da potência total do motor (SEGURANÇA MÁXIMA - reduzido de 10%)
        TURN_SPEED_PERCENT = 8  # 8% da potência máxima (SEGURANÇA MÁXIMA)
        
        # 🛡️ VALIDAÇÃO DE SEGURANÇA BÁSICA
        MAX_SAFE_POWER = 15  # Limite máximo seguro (reduzido para maior segurança)
        if TURN_SPEED_PERCENT > MAX_SAFE_POWER:
            print(f"🚨 ERRO: Potência {TURN_SPEED_PERCENT}% excede limite seguro de {MAX_SAFE_POWER}%")
            QMessageBox.critical(self, "Erro de Segurança", f"Potência {TURN_SPEED_PERCENT}% excede limite seguro!")
            self.navigator.stop_precise_rotation()  # Restaura modo normal
            return
        
        print(f"🔄 SYNC_ENHANCED: Giro preciso {direction} com {TURN_SPEED_PERCENT}% - modo sincronização ativado")
        
        # 🔧 DEFINE direção correta dos ticks para odometria precisa
        if direction == "left":
            # Giro à esquerda: motor esquerdo trás (-1), motor direito frente (+1)
            self.navigator.motors.set_precise_rotation_direction(-1, +1)
            self.navigator.motors._set_motor_speed_real("left", -TURN_SPEED_PERCENT)
            self.navigator.motors._set_motor_speed_real("right", TURN_SPEED_PERCENT)
            print(f"🔄 SYNC_LEFT: Motor E={-TURN_SPEED_PERCENT}%, D={TURN_SPEED_PERCENT}%")
        else: # direction == "right"
            # Giro à direita: motor esquerdo frente (+1), motor direito trás (-1)
            self.navigator.motors.set_precise_rotation_direction(+1, -1)
            self.navigator.motors._set_motor_speed_real("left", TURN_SPEED_PERCENT)
            self.navigator.motors._set_motor_speed_real("right", -TURN_SPEED_PERCENT)
            print(f"🔄 SYNC_RIGHT: Motor E={TURN_SPEED_PERCENT}%, D={-TURN_SPEED_PERCENT}%")

        # 🔧 SALVA dados para sincronização precisa por tempo
        # 🎯 CORREÇÃO CRÍTICA: Sincronia real com o robô físico
        # O robô físico gira, a interface deve girar na MESMA direção
        
        if direction == "left":
            # 🎯 CORREÇÃO: Para esquerda, o robô físico diminui o ângulo
            # A interface deve diminuir o ângulo também (sincronia real)
            self.precise_rotation_target_angle = -angle_per_click  # Negativo para esquerda
            print(f"🔄 SYNC_LEFT_REAL: Giro para ESQUERDA - ângulo será diminuído")
        else:  # direction == "right"
            # 🎯 CORREÇÃO: Para direita, o robô físico aumenta o ângulo
            # A interface deve aumentar o ângulo também (sincronia real)
            self.precise_rotation_target_angle = angle_per_click   # Positivo para direita
            print(f"🔄 SYNC_RIGHT_REAL: Giro para DIREITA - ângulo será aumentado")
            
        self.precise_rotation_start_time = time.time()
        self.precise_rotation_direction = direction
        
        print(f"🔄 SYNC_DATA: Ângulo alvo: {self.precise_rotation_target_angle}°, Direção: {direction}, Tempo: {rotation_time:.2f}s")
        
        # 🎯 NOVO: Timer mais robusto com callback garantido
        self.rotation_timer = QTimer()
        self.rotation_timer.setSingleShot(True)
        self.rotation_timer.timeout.connect(self._stop_precise_rotation)
        self.rotation_timer.start(int(rotation_time * 1000))
        
        print(f"🔄 SYNC_TIMER: Timer iniciado para {rotation_time:.2f}s")

    def _stop_precise_rotation(self):
        """Para a rotação precisa com sincronia melhorada e robusta."""
        print("🔄 SYNC_STOP: Parando rotação e aplicando sincronia")
        
        # Para os motores
        self.navigator.motors.stop()
        
        # 🔧 SINCRONIZAÇÃO PRECISA por tempo como método principal
        if hasattr(self, 'precise_rotation_target_angle') and hasattr(self, 'initial_angle_for_sync'):
            # 🎯 CORREÇÃO CRÍTICA: Sincronia real com o robô físico
            # O robô físico gira, a interface deve girar na MESMA direção
            
            if hasattr(self, 'precise_rotation_direction'):
                if self.precise_rotation_direction == "left":
                    # 🎯 CORREÇÃO: Giro para ESQUERDA na interface
                    # Para esquerda: diminui o ângulo (sentido anti-horário)
                    # O robô físico diminui o ângulo, a interface deve diminuir também
                    final_angle = self.initial_angle_for_sync + self.precise_rotation_target_angle
                    print(f"🔄 SYNC_LEFT_REAL: Giro para ESQUERDA - {self.initial_angle_for_sync:.1f}° + ({self.precise_rotation_target_angle:.1f}°) = {final_angle:.1f}°")
                    print(f"🔄 SYNC_LEFT_REAL: Robô físico diminuiu ângulo, interface diminuiu também")
                else:  # direction == "right"
                    # 🎯 CORREÇÃO: Giro para DIREITA na interface
                    # Para direita: aumenta o ângulo (sentido horário)
                    # O robô físico aumenta o ângulo, a interface deve aumentar também
                    final_angle = self.initial_angle_for_sync + self.precise_rotation_target_angle
                    print(f"🔄 SYNC_RIGHT_REAL: Giro para DIREITA - {self.initial_angle_for_sync:.1f}° + {self.precise_rotation_target_angle:.1f}° = {final_angle:.1f}°")
                    print(f"🔄 SYNC_RIGHT_REAL: Robô físico aumentou ângulo, interface aumentou também")
            else:
                # Fallback para compatibilidade
                final_angle = self.initial_angle_for_sync + self.precise_rotation_target_angle
                print(f"🔄 SYNC_FALLBACK: Usando cálculo padrão")
            
            # Normaliza o ângulo (-180 a +180)
            while final_angle > 180:
                final_angle -= 360
            while final_angle < -180:
                final_angle += 360
            
            print(f"🔄 SYNC_CALCULATION: {self.initial_angle_for_sync:.1f}° → {final_angle:.1f}° (direção: {getattr(self, 'precise_rotation_direction', 'unknown')})")
            
            # 🎯 FORÇA a sincronização exata na interface
            self.navigator.current_angle = final_angle
            
            # 🔄 ATUALIZA a interface gráfica para refletir a nova posição
            if hasattr(self, 'map_widget'):
                # 🎯 CORREÇÃO CRÍTICA: Durante giros, usa a posição ORIGINAL (não a atual)
                # Isso garante que o robô virtual gire no próprio eixo, sem "andar para frente"
                original_pos = self.initial_position_for_sync if hasattr(self, 'initial_position_for_sync') else self.navigator.current_position
                
                # Atualiza APENAS o ângulo, mantendo a posição fixa
                self.map_widget.update_robot_position(original_pos[0], original_pos[1], final_angle)
                print(f"🔄 SYNC_UI: Interface atualizada - Posição ORIGINAL FIXA: ({original_pos[0]:.2f}, {original_pos[1]:.2f}), Ângulo NOVO: {final_angle:.1f}°")
                print(f"🔄 SYNC_UI: Robô virtual girou no próprio eixo (posição não mudou)")
                
                # 🎯 NOVO: Força atualização imediata da interface
                self.map_widget.repaint()
            
            print(f"🔧 SYNC_TIME_ENHANCED: Ângulo corrigido por tempo - {self.initial_angle_for_sync:.1f}° → {final_angle:.1f}°")
            
            # 🎯 VERIFICA se a sincronia está correta
            angle_diff = abs(final_angle - self.navigator.current_angle)
            if angle_diff < 1.0:
                print(f"✅ SYNC_SUCCESS: Sincronia perfeita alcançada (diferença: {angle_diff:.1f}°)")
            else:
                print(f"⚠️ SYNC_WARNING: Pequena diferença na sincronia (diferença: {angle_diff:.1f}°)")
        else:
            print("⚠️ SYNC_WARNING: Dados de sincronia não encontrados, usando método alternativo")
            # 🎯 MÉTODO ALTERNATIVO: Usa o ângulo atual do navegador
            if hasattr(self.navigator, 'current_angle'):
                current_angle = self.navigator.current_angle
                current_pos = self.navigator.current_position
                if hasattr(self, 'map_widget'):
                    self.map_widget.update_robot_position(current_pos[0], current_pos[1], current_angle)
                    self.map_widget.repaint()
                    print(f"🔄 SYNC_ALTERNATIVE: Interface atualizada com ângulo do navegador: {current_angle:.1f}°")
        
        # 🔧 LIMPA direção forçada dos ticks
        self.navigator.motors.clear_precise_rotation_direction()
        
        # 🔄 DESATIVA modo de giro preciso no navegador
        self.navigator.stop_precise_rotation()
        
        # 🎯 LOG de conclusão com informações detalhadas
        if hasattr(self, 'precise_rotation_direction'):
            print(f"🔄 SYNC_COMPLETE: Giro {self.precise_rotation_direction} finalizado - modo normal restaurado")
            # Limpa variáveis de sincronia
            if hasattr(self, 'precise_rotation_direction'):
                delattr(self, 'precise_rotation_direction')
        else:
            print("🔄 SYNC_COMPLETE: Giro preciso finalizado - modo normal restaurado")
        
        # 🎯 NOVO: Limpa timer se existir
        if hasattr(self, 'rotation_timer'):
            self.rotation_timer.stop()
            delattr(self, 'rotation_timer')
            print("🔄 SYNC_TIMER: Timer limpo")
        
        print("✅ SYNC_COMPLETE: Sincronia finalizada com sucesso")

    # 🚨 COMPLETAMENTE DESABILITADO: Método de sincronização com problemas
    # def _sync_robot_position_during_rotation(self):
    #     """Sincroniza a posição do robô na interface durante rotações precisas."""
    #     try:
    #         # Obtém a posição atual do robô físico (se disponível)
    #         if hasattr(self.navigator, 'current_position') and hasattr(self.navigator, 'current_angle'):
    #             current_pos = self.navigator.current_position
    #             current_angle = self.navigator.current_angle
    #             
    #             # Atualiza a interface com a posição real
    #             self.map_widget.update_robot_position(current_pos[0], current_pos[1], current_angle)
    #             
    #             # Debug da sincronização
    #             print(f"🔄 SYNC_DEBUG: Posição sincronizada - ({current_pos[0]:.2f}, {current_pos[1]:.2f}) @ {current_angle:.1f}°")
    #             
    #     except Exception as e:
    #         print(f"⚠️ SYNC_DEBUG: Erro na sincronização: {e}")

    def _manual_turn_left(self):
        """Executa giro manual de 180° para a esquerda"""
        if self.navigation_active:
            QMessageBox.warning(self, "Aviso", "Aguarde o término da navegação atual.")
            return
        
        try:
            print("🔄 INTERFACE: Executando giro manual esquerda de 180°")
            self.navigator.manual_turn_left()
            
            # Atualiza a posição do robô na interface
            current_pos = self.navigator.current_position
            current_angle = self.navigator.current_angle
            self.map_widget.update_robot_position(current_pos[0], current_pos[1], current_angle)
            
            print(f"🔄 INTERFACE: Giro manual concluído - Posição: ({current_pos[0]:.2f}, {current_pos[1]:.2f}), Ângulo: {current_angle:.1f}°")
            
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao executar giro manual:\n{e}")
            print(f"⚠️ INTERFACE: Erro no giro manual: {e}")

    def _manual_turn_right(self):
        """Executa giro manual de 180° para a direita"""
        if self.navigation_active:
            QMessageBox.warning(self, "Aviso", "Aguarde o término da navegação atual.")
            return
        
        try:
            print("🔄 INTERFACE: Executando giro manual direita de 180°")
            self.navigator.manual_turn_right()
            
            # Atualiza a posição do robô na interface
            current_pos = self.navigator.current_position
            current_angle = self.navigator.current_angle
            self.map_widget.update_robot_position(current_pos[0], current_pos[1], current_angle)
            
            print(f"🔄 INTERFACE: Giro manual concluído - Posição: ({current_pos[0]:.2f}, {current_pos[1]:.2f}), Ângulo: {current_angle:.1f}°")
            
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao executar giro manual:\n{e}")
            print(f"⚠️ INTERFACE: Erro no giro manual: {e}")

    def _on_angle_slider_changed(self, value: int):
        """Atualiza o ângulo de rotação por clique."""
        self.angle_label.setText(f"Ângulo por clique: {value}°")
        
        # Atualiza textos dos botões (mantém compatibilidade)
        if hasattr(self, 'btn_rotate_precise_left'):
            self.btn_rotate_precise_left.setText(f"↺ {value}° ESQUERDA")
        if hasattr(self, 'btn_rotate_precise_right'):
            self.btn_rotate_precise_right.setText(f"↻ {value}° DIREITA")

    def _set_new_starting_position(self):
        """Define a posição atual como nova posição de partida"""
        current_pos = self.navigator.current_position
        current_angle = self.navigator.current_angle
        
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
            self.map_widget.set_current_path([])
            
            self.navigator.reset_to_initial_state()
            self.navigator.current_position = current_pos
            self.navigator.current_angle = current_angle
            
            self.map_widget.update_robot_position(current_pos[0], current_pos[1], current_angle)
            
            QMessageBox.information(
                self, 
                "Nova Partida Definida",
                f"Posição de partida atualizada!\n\n"
                f"Posição: ({current_pos[0]:.2f}, {current_pos[1]:.2f})\n"
                f"Ângulo: {current_angle:.1f}°\n\n"
                f"O sistema agora calculará novos percursos a partir desta posição."
            )

    def _return_to_base(self):
        """Inicia navegação de retorno para a base original com sincronia melhorada e debug"""
        print("🏠 RETORNO_BASE: Método chamado - iniciando verificação")
        
        if self.navigation_active:
            print("⚠️ RETORNO_BASE: Navegação já ativa, bloqueando retorno")
            QMessageBox.warning(self, "Aviso", "Aguarde o término da navegação atual.")
            return
        
        base_position = ROBOT_INITIAL_POSITION
        current_pos = self.navigator.current_position
        current_angle = self.navigator.current_angle
        
        print(f"🏠 RETORNO_BASE: Posição atual: {current_pos}, Ângulo: {current_angle:.1f}°")
        print(f"🏠 RETORNO_BASE: Base alvo: {base_position}")
        
        distance_to_base = ((current_pos[0] - base_position[0])**2 + 
                           (current_pos[1] - base_position[1])**2)**0.5
        
        if distance_to_base < 0.3:
            print("🏠 RETORNO_BASE: Robô já próximo da base, cancelando")
            QMessageBox.information(self, "Retorno à Base", "O robô já está próximo à base original!")
            return
        
        # 🎯 VERIFICA se o robô está orientado corretamente para a base
        dx = base_position[0] - current_pos[0]
        dy = base_position[1] - current_pos[1]
        target_angle = math.degrees(math.atan2(dy, dx))
        angle_error = abs((target_angle - current_angle + 180) % 360 - 180)
        
        print(f"🏠 RETORNO_BASE: Ângulo para base: {target_angle:.1f}°, Erro: {angle_error:.1f}°")
        
        orientation_warning = ""
        if angle_error > 45:
            orientation_warning = f"\n\n⚠️ ATENÇÃO: O robô está {angle_error:.1f}° desalinhado com a base!"
            orientation_warning += "\nRecomenda-se usar os botões de giro para alinhar antes de iniciar."
        
        reply = QMessageBox.question(
            self, 
            "Retornar à Base",
            f"Iniciar navegação de retorno à base original?\n\n"
            f"De: ({current_pos[0]:.2f}, {current_pos[1]:.2f}) - Ângulo: {current_angle:.1f}°\n"
            f"Para: ({base_position[0]:.2f}, {base_position[1]:.2f}) - Ângulo Alvo: {ROBOT_INITIAL_ANGLE}°\n"
            f"Distância: {distance_to_base:.2f}m\n"
            f"Ângulo para base: {target_angle:.1f}° (erro: {angle_error:.1f}°){orientation_warning}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            print(f"🏠 RETORNO_BASE: Usuário confirmou - iniciando processo")
            
            try:
                # 🔄 RESET do estado para garantir navegação limpa
                print("🏠 RETORNO_BASE: Resetando estado do navegador")
                self.navigator.reset_to_initial_state()
                
                # 🔧 PRESERVA posição e ângulo atuais
                print("🏠 RETORNO_BASE: Preservando posição e ângulo atuais")
                self.navigator.current_position = current_pos
                self.navigator.current_angle = current_angle
                
                print(f"🏠 RETORNO_BASE: Estado após reset - Posição: {self.navigator.current_position}, Ângulo: {self.navigator.current_angle:.1f}°")
                
                # 🚀 INICIA retorno manual que chama _return_to_base_direct
                print("🏠 RETORNO_BASE: Chamando return_to_base_manual()")
                self.navigator.return_to_base_manual()
                
                print(f"🏠 RETORNO_BASE: return_to_base_manual() executado - Estado: {self.navigator.navigation_state}")
                
                # 🔄 ATIVA navegação e atualiza interface
                print("🏠 RETORNO_BASE: Ativando navegação na interface")
                self.navigation_active = True
                self.nav_status_label.setText("Status: Retornando à base...")
                self.nav_progress_bar.setVisible(True)
                self.nav_progress_bar.setValue(0)
                self.nav_info_label.setVisible(True)
                self.nav_info_label.setText("Estado: Retornando à base original")
                
                # 🎯 ATUALIZA caminho na interface se disponível
                if hasattr(self.navigator, 'path') and self.navigator.path:
                    print(f"🏠 RETORNO_BASE: Caminho disponível: {len(self.navigator.path)} pontos")
                    self.map_widget.set_current_path(self.navigator.path)
                    print(f"🏠 RETORNO_BASE: Caminho definido na interface: {len(self.navigator.path)} pontos")
                else:
                    print("⚠️ RETORNO_BASE: Nenhum caminho disponível no navegador")
                
                print(f"✅ RETORNO_BASE: Navegação iniciada com sucesso - Estado: {self.navigator.navigation_state}")
                print(f"✅ RETORNO_BASE: navigation_active = {self.navigation_active}")
                
            except Exception as e:
                error_msg = f"Erro ao iniciar retorno à base:\n{e}"
                print(f"🚨 RETORNO_BASE: EXCEÇÃO CAPTURADA: {error_msg}")
                import traceback
                traceback.print_exc()
                QMessageBox.warning(self, "Erro", error_msg)
                self.navigation_active = False
        else:
            print("🏠 RETORNO_BASE: Usuário cancelou o retorno")
