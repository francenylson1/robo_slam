from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QComboBox, QMessageBox,
                             QGroupBox, QGridLayout, QInputDialog, QProgressBar, QSlider,
                             QScrollArea, QFrame, QSizePolicy, QApplication, QFileDialog, QCheckBox)
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
        
        # Área do mapa (lado esquerdo) dentro de QScrollArea para ver mapa completo e rolar (ex.: Raspberry)
        map_layout = QVBoxLayout()
        self.map_scroll = QScrollArea()
        self.map_scroll.setWidgetResizable(False)  # widget do mapa define seu próprio tamanho
        self.map_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.map_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.map_scroll.setFrameShape(QFrame.StyledPanel)
        self.map_widget = MapWidget()
        self.map_scroll.setWidget(self.map_widget)
        map_layout.addWidget(self.map_scroll)
        
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
        
        # 🎯 NOVO: Checkbox para escolher se retorna à base automaticamente
        self.return_to_base_checkbox = QCheckBox("Retornar à base automaticamente")
        self.return_to_base_checkbox.setChecked(True)  # Padrão: marcado (comportamento atual)
        self.return_to_base_checkbox.setToolTip("Se marcado, o robô retorna à base após chegar ao destino.\nSe desmarcado, o robô para no destino e aguarda novo comando.")
        nav_layout.addWidget(self.return_to_base_checkbox)
        
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
        
        # Botão GIRO ESQUERDA — ângulo definido pelo slider abaixo
        self.btn_rotate_manual_left = QPushButton("↺ 90° ESQ" if self.is_small_screen else "↺ 90° ESQUERDA")
        self.btn_rotate_manual_left.setFixedSize(rotate_width, rotate_height)
        self.btn_rotate_manual_left.clicked.connect(lambda: self._execute_precise_rotation("left"))
        if self.is_small_screen:
            self.btn_rotate_manual_left.setStyleSheet("font-size: 9px; font-weight: bold; background-color: #2196F3; color: white;")
        else:
            self.btn_rotate_manual_left.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        direction_grid.addWidget(self.btn_rotate_manual_left, 1, 0)

        # Botão GIRO DIREITA — ângulo definido pelo slider abaixo
        self.btn_rotate_manual_right = QPushButton("↻ 90° DIR" if self.is_small_screen else "↻ 90° DIREITA")
        self.btn_rotate_manual_right.setFixedSize(rotate_width, rotate_height)
        self.btn_rotate_manual_right.clicked.connect(lambda: self._execute_precise_rotation("right"))
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

        # Slider de ângulo: controla o giro dos botões ↺ e ↻ (15° a 180°)
        angle_layout = QHBoxLayout()
        angle_layout.addWidget(QLabel("Ângulo:"))
        self.angle_slider = QSlider(Qt.Orientation.Horizontal)
        self.angle_slider.setRange(15, 180)  # 15° a 180°
        self.angle_slider.setValue(90)       # Padrão: 90°
        self.angle_slider.setTickPosition(QSlider.TicksBelow)
        self.angle_slider.setTickInterval(45)
        self.angle_slider.valueChanged.connect(self._on_angle_slider_changed)
        angle_layout.addWidget(self.angle_slider)
        self.angle_label = QLabel("90°")
        self.angle_label.setMinimumWidth(35)
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
        
        # Callback para atualizar PathFinder quando mapa PGM é carregado
        self._path_finder_initialized = False
        
        # Conecta o sinal de atualização de posição do navegador ao slot da UI
        self.navigator.position_updated.connect(self._update_robot_position_on_map)

        # Configura callbacks do mapa
        self.map_widget.area_clicked_callback = self._on_area_clicked
        
        # Timer para autosave periódico
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self._check_periodic_autosave)
        self.autosave_timer.start(30000)
        
        # NOVO: Ao iniciar, pede para selecionar mapa PGM diretamente
        # Não carrega mapas antigos do banco de dados
        self._prompt_load_pgm_on_startup()
        
        # 🎯 CORREÇÃO: Se um mapa PGM foi carregado, NÃO força ROBOT_INITIAL_POSITION
        # A posição já foi definida por _set_robot_initial_position_from_pgm()
        print(f"🔍 DEBUG INICIAL: Posição inicial do robô configurada: {ROBOT_INITIAL_POSITION}")
        print(f"🔍 DEBUG INICIAL: Posição do robô no widget: {self.map_widget.robot_position}")
        print(f"🔍 DEBUG INICIAL: Mapa PGM carregado? {self.map_widget.map_image is not None}")
        
        # 🎯 UNIFICAÇÃO: Garante que o PathFinder e o robô estejam configurados corretamente
        if self.map_widget.map_image is None:
            # Mapa NÃO PGM: Usa configuração padrão do config.py
            print(f"🔧 Mapa NÃO PGM detectado - usando configuração padrão")
            if self.map_widget.robot_position != ROBOT_INITIAL_POSITION:
                print(f"⚠️  AVISO: Posição do robô no widget ({self.map_widget.robot_position}) difere da config ({ROBOT_INITIAL_POSITION})")
                print(f"🔧 CORREÇÃO: Atualizando posição do robô no widget para {ROBOT_INITIAL_POSITION}")
                self.map_widget.robot_position = ROBOT_INITIAL_POSITION
                self.map_widget.base_position = ROBOT_INITIAL_POSITION
                self.navigator.current_position = ROBOT_INITIAL_POSITION
                self.navigator.base_position = ROBOT_INITIAL_POSITION
                self.map_widget.update()
            
            # Garante que o PathFinder está usando a configuração padrão
            from src.core.config import MAP_WIDTH, MAP_HEIGHT, MAP_GRID_SIZE
            print(f"🔧 PathFinder configurado para mapa NÃO PGM:")
            print(f"   Dimensões: {int(MAP_WIDTH / MAP_GRID_SIZE)}x{int(MAP_HEIGHT / MAP_GRID_SIZE)} células")
            print(f"   Tamanho: {MAP_WIDTH}m x {MAP_HEIGHT}m")
            print(f"   Grid size: {MAP_GRID_SIZE}m/célula")
            print(f"   Origem: (0.0, 0.0)")
        else:
            # Mapa PGM: Já foi configurado por _update_path_finder_for_pgm_map()
            print(f"✅ Mapa PGM carregado - usando posição calculada do PGM: {self.map_widget.robot_position}")
            print(f"✅ PathFinder já atualizado para mapa PGM")
        
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

    def _prompt_load_pgm_on_startup(self):
        """Ao iniciar, pede para selecionar mapa PGM diretamente."""
        # Limpa qualquer mapa anterior
        self.map_widget.clear_pgm_map()
        self.map_widget.points_of_interest = {}
        self.map_widget.forbidden_areas = []
        
        # Chama diretamente a função de carregar PGM
        self._load_pgm_map()
    
    def _load_active_map(self):
        """Carrega mapas antigos do banco de dados (legado - não recomendado)."""
        from pathlib import Path
        
        # Lista mapas do banco de dados
        db_map_names = self.map_manager.get_all_map_names()
        
        if db_map_names:
            map_name, ok = QInputDialog.getItem(
                self, 
                "Carregar Mapa (Legado)", 
                "⚠️ Mapas antigos do banco de dados.\n\n"
                "Recomendado: Use '🗺️ Carregar PGM' para mapas do pipeline.\n\n"
                "Selecione um mapa legado:",
                db_map_names, 
                0, 
                False
            )
            if ok and map_name:
                # É um mapa do banco de dados
                self.map_manager.load_map_by_name(map_name)
                active_map = self.map_manager.get_active_map()
                if active_map:
                    self.current_map = active_map
                    points_of_interest, forbidden_areas, _, _ = self.map_manager.load_active_map()
                    
                    map_data = {
                        'points_of_interest': points_of_interest,
                        'forbidden_areas': forbidden_areas
                    }
                    # Limpa PGM antes de carregar mapa legado
                    self.map_widget.clear_pgm_map()
                    self.map_widget.load_map(map_data)
                    self._update_points_list()
                    self._update_destination_combo()
                    self._reload_forbidden_areas()
                    self.status_label.setText(f"Mapa legado carregado: {active_map['nome']}")
                    self._reset_robot_to_base()
        else:
            # Se não houver mapas legados, sugere carregar PGM
            reply = QMessageBox.question(
                self,
                "Nenhum Mapa Legado",
                "Nenhum mapa antigo encontrado no banco de dados.\n\n"
                "Deseja carregar um mapa PGM do pipeline?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._load_pgm_map()
            
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

        # 🎯 CORREÇÃO CRÍTICA: Verifica estado COMPLETED ANTES de verificar navigation_active
        # Isso garante que a mensagem seja exibida mesmo se navigation_active já foi desativado
        nav_status = self.navigator.get_navigation_status()
        state_text = nav_status.get("state", "IDLE")
        
        # Se o estado é COMPLETED, processa a conclusão ANTES de verificar navigation_active
        if state_text == "COMPLETED":
            # 🎯 CORREÇÃO CRÍTICA: Se o estado é COMPLETED, sempre finaliza a navegação
            if self.navigation_active:
                print("🔄 SINCRONIZAÇÃO: Estado COMPLETED detectado, finalizando navegação na interface")
                self.navigation_active = False
            
            # 🎯 CORREÇÃO: Garante que a mensagem seja mostrada apenas uma vez por navegação
            if not hasattr(self, '_navigation_completed_shown'):
                self._navigation_completed_shown = False
            
            if not self._navigation_completed_shown:
                print("✅ NAVEGAÇÃO CONCLUÍDA: Exibindo mensagem ao usuário")
                self._navigation_completed_shown = True
                # Finaliza navegação na interface
                self._complete_navigation_and_reset()
                # Mensagem conforme tipo de conclusão
                cancelled_by_obstacle = nav_status.get("cancelled_by_obstacle", False)
                if cancelled_by_obstacle:
                    msg = (
                        "⚠️ Navegação cancelada\n\n"
                        "O robô parou por obstáculo detectado pelo Lidar C1\n"
                        "e não conseguiu chegar ao POI em até 45 segundos.\n\n"
                        "Remova o obstáculo e inicie nova navegação."
                    )
                    QMessageBox.warning(self, "⚠️ Navegação cancelada", msg)
                elif getattr(self.navigator, '_navigation_had_return_to_base', True):
                    msg = (
                        "🎉 Navegação concluída com sucesso!\n\n"
                        "O robô completou todo o percurso:\n"
                        "• Navegou até o POI de destino\n"
                        "• Aguardou 2 segundos no destino\n"
                        "• Retornou à posição base inicial\n\n"
                        "O sistema está pronto para uma nova navegação."
                    )
                else:
                    msg = (
                        "🎉 Navegação concluída com sucesso!\n\n"
                        "O robô chegou ao POI de destino e parou.\n"
                        "Não foi solicitado retorno à base.\n\n"
                        "O sistema está pronto para uma nova navegação."
                    )
                QMessageBox.information(self, "✅ Navegação Concluída", msg)
                # Reseta o estado para IDLE após mostrar mensagem
                self.navigator.navigation_state = "IDLE"
            return
        
        # 🎯 CORREÇÃO CRÍTICA: Sincroniza navigation_active ANTES de verificar
        # Se o navegador finalizou a navegação, atualiza a flag da interface
        if not self.navigator.navigation_active and self.navigation_active:
            print("🔄 SINCRONIZAÇÃO: Navegador finalizou navegação, atualizando flag da interface")
            self.navigation_active = False

        if not self.navigation_active:
            return
        
        # Reutiliza nav_status já obtido acima (não precisa obter novamente)
        progress = int(nav_status.get("progress", 0) * 100)
        self.nav_progress_bar.setValue(progress)

        time_remaining = nav_status.get("estimated_time_remaining", 0)

        # 🎯 CORREÇÃO: Atualiza o caminho na interface quando o retorno inicia
        # Isso garante que o caminho de retorno seja desenhado corretamente
        # IMPORTANTE: Só atualiza se o robô ESTÁ retornando (is_returning_to_base = True)
        # Não atualiza durante a navegação até o destino para evitar mostrar o caminho completo
        if state_text == "RETURNING_TO_BASE" or (state_text == "ORIENTING_TO_TARGET" and getattr(self.navigator, 'is_returning_to_base', False)):
            if hasattr(self.navigator, 'path') and self.navigator.path:
                # 🎯 CORREÇÃO: Sempre atualiza o caminho quando o retorno inicia (não apenas se mudou)
                # Isso garante que o caminho de retorno seja mostrado mesmo que o comprimento seja o mesmo
                # 🎯 CORREÇÃO: Garante que o caminho de retorno termina na base exata
                path_to_display = list(self.navigator.path)
                if hasattr(self.navigator, 'base_position') and self.navigator.base_position:
                    base_exact = self.navigator.base_position
                    if len(path_to_display) > 0:
                        last_point = path_to_display[-1]
                        dist_to_base = math.sqrt(
                            (last_point[0] - base_exact[0])**2 + 
                            (last_point[1] - base_exact[1])**2
                        )
                        if dist_to_base > 0.01:  # Mais de 1cm de diferença
                            print(f"🔧 INTERFACE: Adicionando base exata ao caminho de retorno (distância: {dist_to_base*100:.2f}cm)")
                            path_to_display.append(base_exact)
                self.map_widget.set_current_path(path_to_display)
                print(f"🎯 INTERFACE: Caminho de retorno atualizado na interface: {len(path_to_display)} pontos")
        
        # 🎯 CORREÇÃO CRÍTICA: Durante a navegação até o destino, garante que apenas o caminho de ida seja mostrado
        # Isso evita que o caminho completo (ida + volta) seja mostrado desde o início
        elif state_text in ["NAVIGATING_TO_DESTINATION", "ORIENTING_TO_TARGET", "FINAL_APPROACH_DESTINATION"]:
            if hasattr(self.navigator, 'path') and self.navigator.path and not getattr(self.navigator, 'is_returning_to_base', False):
                # Garante que apenas o caminho de ida seja mostrado
                if hasattr(self.navigator, 'destination_index') and self.navigator.destination_index is not None:
                    max_index = min(self.navigator.destination_index + 1, len(self.navigator.path))
                    path_to_display = list(self.navigator.path[:max_index])
                    
                    # 🎯 CORREÇÃO: Adiciona o destino exato se necessário
                    destination_exact = None
                    if hasattr(self.navigator, 'original_destination') and self.navigator.original_destination:
                        destination_exact = self.navigator.original_destination
                    
                    if destination_exact and len(path_to_display) > 0:
                        last_point = path_to_display[-1]
                        dist_to_destination = math.sqrt(
                            (last_point[0] - destination_exact[0])**2 + 
                            (last_point[1] - destination_exact[1])**2
                        )
                        if dist_to_destination > 0.01:  # Mais de 1cm de diferença
                            path_to_display.append(destination_exact)
                    
                    # Só atualiza se o caminho mudou
                    current_path_length = len(self.map_widget.current_path) if self.map_widget.current_path else 0
                    if len(path_to_display) != current_path_length:
                        self.map_widget.set_current_path(path_to_display)
                        print(f"🔍 INTERFACE: Atualizando caminho de IDA durante navegação: {len(path_to_display)} pontos")
        
        # 🎯 Quando o robô chega ao destino (PAUSED_AT_DESTINATION): só limpa o caminho se for retornar à base
        # (evita sumir o traço e dar impressão de “volta” quando o usuário não pediu retorno)
        elif state_text == "PAUSED_AT_DESTINATION":
            if getattr(self.navigator, 'should_return_to_base', False) and self.map_widget.current_path:
                print(f"🔍 INTERFACE: Robô chegou ao destino, limpando caminho de ida para preparar retorno")
                self.map_widget.clear_current_path()

        if nav_status.get("is_paused_at_destination", False):
            info_text = f"Estado: {state_text} | Pausado no destino"
        elif time_remaining > 0:
            info_text = f"Estado: {state_text} | Tempo: {time_remaining:.1f}s"
        else:
            info_text = f"Estado: {state_text}"
            
        self.nav_info_label.setText(info_text)
        
        # Nota: A verificação de COMPLETED já foi feita no início da função (linha 647)
        # e retorna imediatamente após processar, então não precisa repetir aqui

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
        # x e y são coordenadas do mundo em metros (já convertidas pelo map_widget)
        print(f"DEBUG: POI - Clique recebido em ({x:.2f}, {y:.2f})m (coordenadas do mundo)")
        
        # Verifica se está em área proibida usando coordenadas do mundo
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
        # Converte metros para centímetros (o SpinBox trabalha em centímetros)
        # IMPORTANTE: Usa as coordenadas EXATAS do clique (x, y), não grid
        dialog.x_spin.setValue(int(x * 100))
        dialog.y_spin.setValue(int(y * 100))
        print(f"DEBUG: POI - Diálogo preenchido com ({x*100:.0f}, {y*100:.0f})cm")
        
        if dialog.exec_():
            name, position, point_type = dialog.get_point_data()
            if name:
                # Usa as coordenadas do diálogo (já em metros)
                # O usuário pode ter ajustado manualmente, mas por padrão usa as coordenadas do clique
                poi_x, poi_y = position
                print(f"DEBUG: POI - Salvando '{name}' em ({poi_x:.2f}, {poi_y:.2f})m, tipo: {point_type}")
                self.map_widget.points_of_interest[name] = (poi_x, poi_y, point_type)
                self.map_widget.update()
                self._update_points_list()
                self._update_destination_combo()
                self._mark_unsaved_changes()
                
                # Se o POI se chama "base" ou "Base", oferece atualizar posição inicial do robô
                if name.lower() == "base":
                    reply = QMessageBox.question(
                        self,
                        "POI 'Base' Criado",
                        f"POI '{name}' criado em:\n"
                        f"X: {poi_x:.2f}m\n"
                        f"Y: {poi_y:.2f}m\n\n"
                        f"💡 Essas coordenadas são em METROS.\n\n"
                        f"Deseja usar esta posição como posição inicial do robô?\n"
                        f"(Isso atualizará config.py)",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    if reply == QMessageBox.Yes:
                        self._update_robot_initial_position(poi_x, poi_y)
                else:
                    # Mostra mensagem com coordenadas em metros
                    QMessageBox.information(
                        self,
                        "POI Criado",
                        f"POI '{name}' criado em:\n"
                        f"X: {poi_x:.2f}m\n"
                        f"Y: {poi_y:.2f}m\n\n"
                        f"💡 Essas coordenadas são em METROS no sistema do mundo."
                    )
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
            # Remove do widget local primeiro (mesma lógica dos POIs)
            widget_removed = self.map_widget.remove_forbidden_area(area_id)
            
            # Remove do banco de dados
            db_removed = self.map_manager.delete_forbidden_area(area_id)
            
            if widget_removed and db_removed:
                # Atualiza a interface
                self._reload_forbidden_areas()
                self._mark_unsaved_changes()
                QMessageBox.information(self, "Sucesso", f"Área '{area_name}' excluída com sucesso!")
            elif widget_removed:
                # Se removeu do widget mas não do banco, ainda considera sucesso parcial
                # e recarrega do banco para sincronizar
                self._reload_forbidden_areas()
                self._mark_unsaved_changes()
                QMessageBox.warning(self, "Aviso", f"Área '{area_name}' removida da interface, mas houve problema ao remover do banco de dados.")
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
        
        # Lista mapas PGM disponíveis em múltiplas pastas
        pgm_maps = []
        pgm_map_paths = {}  # Dicionário para mapear nome -> caminho completo
        
        # Procura em src/c1_scanner/C1_mapas_processados/*/ (mapas processados do C1)
        c1_processed_dir = Path("src/c1_scanner/C1_mapas_processados")
        if c1_processed_dir.exists():
            for map_subdir in c1_processed_dir.iterdir():
                if map_subdir.is_dir():
                    for pgm_file in map_subdir.glob("*.pgm"):
                        map_name = f"C1/{map_subdir.name}/{pgm_file.stem}"  # Prefixo C1 para identificação
                        pgm_maps.append(map_name)
                        pgm_map_paths[map_name] = pgm_file
        
        # Procura em mapas/otimizados (padrão legado)
        pgm_dir_default = Path("mapas/otimizados")
        if pgm_dir_default.exists():
            for pgm_file in pgm_dir_default.glob("*.pgm"):
                map_name = pgm_file.stem
                if map_name not in pgm_map_paths:  # Evita duplicatas
                    pgm_maps.append(map_name)
                    pgm_map_paths[map_name] = pgm_file
        
        # Procura em mapas/c1/otimizados e mapas/c1/final (mesma estrutura desktop e Raspberry)
        for subdir in ("mapas/c1/otimizados", "mapas/c1/final", "mapas/c1/test", "mapas/c1/completo/final"):
            pgm_dir_c1 = Path(subdir)
            if pgm_dir_c1.exists():
                for pgm_file in pgm_dir_c1.glob("*.pgm"):
                    map_name = pgm_file.stem
                    if map_name not in pgm_map_paths:
                        pgm_maps.append(map_name)
                        pgm_map_paths[map_name] = pgm_file
        
        # Procura na raiz de mapas/ (ex.: sala-maker-1.pgm)
        mapas_root = Path("mapas")
        if mapas_root.exists():
            for pgm_file in mapas_root.glob("*.pgm"):
                map_name = pgm_file.stem
                if map_name not in pgm_map_paths:
                    pgm_maps.append(map_name)
                    pgm_map_paths[map_name] = pgm_file
        
        # Procura em data/pipeline_runs/*/map2d (gerados pelo pipeline)
        pipeline_runs_dir = Path("data/pipeline_runs")
        if pipeline_runs_dir.exists():
            for run_dir in pipeline_runs_dir.iterdir():
                if run_dir.is_dir():
                    map2d_dir = run_dir / "map2d"
                    if map2d_dir.exists():
                        for pgm_file in map2d_dir.glob("*.pgm"):
                            map_name = f"{run_dir.name}/{pgm_file.stem}"  # Inclui nome da pasta
                            pgm_maps.append(map_name)
                            pgm_map_paths[map_name] = pgm_file
        
        # Procura em data/pipeline_runs/*/annotation (cópias na pasta de anotação)
        if pipeline_runs_dir.exists():
            for run_dir in pipeline_runs_dir.iterdir():
                if run_dir.is_dir():
                    annotation_dir = run_dir / "annotation"
                    if annotation_dir.exists():
                        for pgm_file in annotation_dir.glob("*.pgm"):
                            map_name = f"{run_dir.name}/annotation/{pgm_file.stem}"
                            if map_name not in pgm_map_paths:  # Evita duplicatas
                                pgm_maps.append(map_name)
                                pgm_map_paths[map_name] = pgm_file
        
        if pgm_maps:
            # Mostra lista de mapas disponíveis
            map_name, ok = QInputDialog.getItem(
                self, 
                "Carregar Mapa PGM", 
                "Selecione um mapa PGM para carregar:\n\n"
                "💡 Dica: Use 'Abrir arquivo...' para navegar em outras pastas.",
                pgm_maps, 
                0, 
                False
            )
            if ok and map_name:
                pgm_path = pgm_map_paths[map_name]
                yaml_path = pgm_path.with_suffix('.yaml')
                
                # Autosave do mapa anterior antes de carregar novo
                if self.has_unsaved_changes and self.autosave_enabled:
                    self._perform_autosave(show_message=False)
                
                # Limpa mapa anterior completamente antes de carregar novo
                self.map_widget.clear_pgm_map()
                self.map_widget.points_of_interest = {}
                self.map_widget.forbidden_areas = []
                
                if self.map_widget.load_pgm_map(str(pgm_path), str(yaml_path) if yaml_path.exists() else None):
                    # Define o nome do mapa no widget para uso no autosave
                    map_name = pgm_path.stem
                    self.map_widget.map_name = map_name
                    
                    # Atualiza PathFinder com as dimensões e origem do mapa PGM
                    self._update_path_finder_for_pgm_map()
                    
                    # Tenta carregar POIs e áreas proibidas do banco de dados
                    try:
                        # Carrega dados do banco usando o nome do mapa (sem ativar)
                        points_of_interest, forbidden_areas, map_id = self.map_manager.get_map_data_by_name(map_name)
                        
                        if points_of_interest or forbidden_areas:
                            # Se encontrou dados salvos, carrega no widget
                            map_data = {
                                'points_of_interest': points_of_interest,
                                'forbidden_areas': forbidden_areas
                            }
                            self.map_widget.load_map(map_data)
                            self._update_points_list()
                            self._update_destination_combo()
                            self._reload_forbidden_areas()
                            print(f"✅ Carregados do banco: {len(points_of_interest)} POIs e {len(forbidden_areas)} áreas proibidas")
                        else:
                            print(f"ℹ️  Nenhum dado salvo encontrado para o mapa '{map_name}'")
                        
                        # Define current_map com o ID do banco se encontrado
                        if map_id:
                            self.current_map = {'nome': map_name, 'id': map_id}
                        else:
                            self.current_map = {'nome': map_name, 'id': None}
                    except Exception as e:
                        print(f"⚠️  Erro ao carregar dados do banco: {e}")
                        import traceback
                        traceback.print_exc()
                        # Continua mesmo se houver erro ao carregar do banco
                        self.current_map = {'nome': map_name, 'id': None}
                    
                    self.status_label.setText(f"Mapa PGM carregado: {map_name}")
                    # Reseta flag de alterações não salvas ao carregar novo mapa
                    self.has_unsaved_changes = False
                    # Define posição inicial do robô baseada no mapa PGM
                    # Pixel (74, 162) = físico: X=3.40m da parede oeste, Y=4.24m da parede sul
                    # Conversão: px_x = 3.40/(6.0/131)=74, px_y = (12.0-4.24)/(12.0/251)=162
                    # Coord. virtuais resultantes: (1.77, 3.87)m no sistema interno (resolução YAML)
                    self._set_robot_initial_position_from_pgm(74, 162)
                    # Não mostra mensagem de sucesso para não interromper o fluxo
                    # Apenas atualiza o status
                else:
                    QMessageBox.warning(self, "Erro", "Não foi possível carregar o mapa PGM.")
                return
        
        # Se não houver mapas na lista, ou se o usuário quiser navegar manualmente
        # Abre diálogo de arquivo em pasta que exista (desktop e Raspberry)
        project_root = Path.cwd()
        for candidate in (Path("mapas/c1/otimizados"), pgm_dir_default, Path("mapas"), project_root):
            if candidate.exists():
                default_dir = str(candidate.absolute())
                break
        else:
            default_dir = str(project_root)
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Carregar Mapa PGM - Navegue até a pasta desejada",
            default_dir,
            "Arquivos PGM (*.pgm);;Todos os arquivos (*.*)"
        )
        
        if file_path:
            # Autosave do mapa anterior antes de carregar novo
            if self.has_unsaved_changes and self.autosave_enabled:
                self._perform_autosave(show_message=False)
            
            # Limpa mapa anterior completamente antes de carregar novo
            self.map_widget.clear_pgm_map()
            self.map_widget.points_of_interest = {}
            self.map_widget.forbidden_areas = []
            
            # Tenta encontrar arquivo YAML correspondente
            pgm_file = Path(file_path)
            yaml_file = pgm_file.with_suffix('.yaml')
            
            # Carrega no MapWidget
            if self.map_widget.load_pgm_map(str(pgm_file), str(yaml_file) if yaml_file.exists() else None):
                # Define o nome do mapa no widget para uso no autosave
                map_name = pgm_file.stem
                self.map_widget.map_name = map_name
                
                # 🎯 CRÍTICO: Atualiza o PathFinder ANTES de carregar POIs e áreas proibidas
                # Isso garante que o PathFinder está configurado corretamente para o mapa PGM
                self._update_path_finder_for_pgm_map()
                
                # Tenta carregar POIs e áreas proibidas do banco de dados
                try:
                    # Carrega dados do banco usando o nome do mapa
                    points_of_interest, forbidden_areas, loaded_map_name, map_id = self.map_manager.load_map_by_name(map_name)
                    
                    if points_of_interest or forbidden_areas:
                        # Se encontrou dados salvos, carrega no widget
                        map_data = {
                            'points_of_interest': points_of_interest,
                            'forbidden_areas': forbidden_areas
                        }
                        self.map_widget.load_map(map_data)
                        self._update_points_list()
                        self._update_destination_combo()
                        self._reload_forbidden_areas()
                        print(f"✅ Carregados do banco: {len(points_of_interest)} POIs e {len(forbidden_areas)} áreas proibidas")
                    else:
                        print(f"ℹ️  Nenhum dado salvo encontrado para o mapa '{map_name}'")
                    
                    # Define current_map com o ID do banco se encontrado
                    if map_id:
                        self.current_map = {'nome': map_name, 'id': map_id}
                    else:
                        self.current_map = {'nome': map_name, 'id': None}
                except Exception as e:
                    print(f"⚠️  Erro ao carregar dados do banco: {e}")
                    # Continua mesmo se houver erro ao carregar do banco
                    self.current_map = {'nome': map_name, 'id': None}
                
                self.status_label.setText(f"Mapa PGM carregado: {map_name}")
                # Reseta flag de alterações não salvas ao carregar novo mapa
                self.has_unsaved_changes = False
                # Define posição inicial do robô baseada no mapa PGM
                # Pixel (74, 162) = físico: X=3.40m da parede oeste, Y=4.24m da parede sul
                # Conversão: px_x = 3.40/(6.0/131)=74, px_y = (12.0-4.24)/(12.0/251)=162
                # Coord. virtuais resultantes: (1.77, 3.87)m no sistema interno (resolução YAML)
                self._set_robot_initial_position_from_pgm(74, 162)
                # Não mostra mensagem de sucesso para não interromper o fluxo
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar o mapa PGM.")
    
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
        
        # Sincroniza posição atual do widget com o navegador antes de iniciar
        # Isso garante que a posição do robô no navegador está correta
        widget_pos = self.map_widget.robot_position
        widget_angle = self.map_widget.robot_angle
        widget_base = self.map_widget.base_position
        
        print(f"🚀 NAVEGAÇÃO: Sincronizando posição antes de iniciar...")
        print(f"🚀 NAVEGAÇÃO: Widget - Posição: {widget_pos}, Ângulo: {widget_angle}°, Base: {widget_base}")
        print(f"🚀 NAVEGAÇÃO: Navegador ANTES - Posição: {self.navigator.current_position}, Ângulo: {self.navigator.current_angle}°, Base: {self.navigator.base_position}")
        
        self.navigator.current_position = widget_pos
        self.navigator.current_angle = widget_angle
        self.navigator.base_position = widget_base
        
        print(f"🚀 NAVEGAÇÃO: Navegador APÓS - Posição: {self.navigator.current_position}, Ângulo: {self.navigator.current_angle}°, Base: {self.navigator.base_position}")
        
        # Preserva a posição atual ao fazer reset (importante para mapas PGM)
        # 🎯 ADAPTAÇÃO: A versão estável suporta preserve_position
        self.navigator.reset_to_initial_state(preserve_position=True)
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
        
        # Extrai coordenadas do destino (pode ser tupla de 2 ou 3 elementos)
        if isinstance(destination, tuple):
            if len(destination) >= 2:
                dest_x, dest_y = destination[0], destination[1]
                destination = (dest_x, dest_y)
        
        print(f"🚀 NAVEGAÇÃO: Destino selecionado: {destination}")
        print(f"🚀 NAVEGAÇÃO: Posição atual: {self.navigator.current_position}")
        print(f"🚀 NAVEGAÇÃO: Base position: {self.navigator.base_position}")
        print(f"🚀 NAVEGAÇÃO: Mapa PGM carregado? {self.map_widget.map_image is not None}")
        if self.map_widget.map_image:
            print(f"🚀 NAVEGAÇÃO: Origem do mapa PGM: {self.map_widget.map_origin}")
            print(f"🚀 NAVEGAÇÃO: Resolução do mapa PGM: {self.map_widget.map_resolution}m/pixel")
        print(f"🚀 NAVEGAÇÃO: PathFinder - Origem: {self.navigator.path_finder.map_origin}, Grid: {self.navigator.path_finder.grid_size}m")
            
        try:
            # 🎯 NOVO: Obtém a escolha do usuário sobre retorno automático
            should_return = self.return_to_base_checkbox.isChecked()
            return_text = "ida + volta" if should_return else "apenas ida"
            print(f"🚀 NAVEGAÇÃO: Modo selecionado - {return_text}")
            
            # 🚀 NOVA FASE: Navegação automática (ida + volta ou apenas ida)
            print(f"🚀 CHAMANDO navigate_to_and_return com destino: {destination}, should_return_to_base: {should_return}")
            print(f"🚀 Estado ANTES: navigation_active={self.navigator.navigation_active}, state={self.navigator.navigation_state}")
            # 🎯 CORREÇÃO: Reseta flag de conclusão antes de iniciar nova navegação
            self._navigation_completed_shown = False
            self.navigator.navigate_to_and_return(destination, should_return_to_base=should_return)
            print(f"🚀 Estado DEPOIS: navigation_active={self.navigator.navigation_active}, state={self.navigator.navigation_state}")
            self.navigation_active = True
            
            if hasattr(self.navigator, 'path') and self.navigator.path:
                # 🎯 CORREÇÃO CRÍTICA: Mostra apenas o caminho de IDA inicialmente
                # O caminho de volta será mostrado apenas quando o robô chegar ao destino
                # Isso evita mostrar o caminho completo (ida + volta) desde o início
                
                print(f"🔍 DEBUG INTERFACE: path length={len(self.navigator.path)}, is_returning_to_base={getattr(self.navigator, 'is_returning_to_base', False)}, destination_index={getattr(self.navigator, 'destination_index', None)}")
                
                # Obtém o destino exato (POI) - pode ser original_destination ou destination
                destination_exact = None
                if hasattr(self.navigator, 'original_destination') and self.navigator.original_destination:
                    destination_exact = self.navigator.original_destination
                    print(f"🔍 INTERFACE: Usando original_destination: {destination_exact}")
                elif destination:  # Usa o destination passado para navigate_to_and_return
                    destination_exact = destination
                    print(f"🔍 INTERFACE: Usando destination: {destination_exact}")
                
                # Se o robô ainda não está retornando, mostra apenas o caminho até o destino
                if not getattr(self.navigator, 'is_returning_to_base', False):
                    # Usa destination_index para limitar o caminho apenas até o destino
                    if hasattr(self.navigator, 'destination_index') and self.navigator.destination_index is not None:
                        # Mostra apenas os pontos até o destino (incluindo o destino)
                        # 🎯 CORREÇÃO: Garante que destination_index não exceda o tamanho do caminho
                        max_index = min(self.navigator.destination_index + 1, len(self.navigator.path))
                        path_to_display = list(self.navigator.path[:max_index])
                        print(f"🔍 INTERFACE: Mostrando apenas caminho de IDA até destino (índice {self.navigator.destination_index}, max_index={max_index}): {len(path_to_display)} pontos de {len(self.navigator.path)} totais")
                        print(f"🔍 DEBUG: Primeiro ponto: {path_to_display[0] if path_to_display else 'N/A'}, Último ponto: {path_to_display[-1] if path_to_display else 'N/A'}")
                    else:
                        # Se não tem destination_index, usa todo o caminho (mas não deveria ter caminho de volta ainda)
                        path_to_display = list(self.navigator.path)
                        print(f"⚠️ INTERFACE: destination_index não disponível, usando caminho completo: {len(path_to_display)} pontos")
                        print(f"⚠️ DEBUG: Primeiro ponto: {path_to_display[0] if path_to_display else 'N/A'}, Último ponto: {path_to_display[-1] if path_to_display else 'N/A'}")
                    
                    # 🎯 CORREÇÃO CRÍTICA: Se temos um destino exato e o caminho não termina nele, adiciona o destino exato
                    # Isso garante que o traçado azul chegue exatamente ao POI
                    if destination_exact and len(path_to_display) > 0:
                        # Compara com tolerância de 1cm para evitar problemas de precisão de ponto flutuante
                        last_point = path_to_display[-1]
                        dist_to_destination = math.sqrt(
                            (last_point[0] - destination_exact[0])**2 + 
                            (last_point[1] - destination_exact[1])**2
                        )
                        
                        print(f"🔍 INTERFACE: Último ponto do caminho: {last_point}, Destino exato: {destination_exact}, Distância: {dist_to_destination*100:.2f}cm")
                        
                        if dist_to_destination > 0.01:  # Mais de 1cm de diferença
                            print(f"🔧 INTERFACE: Último ponto do caminho ({last_point}) está a {dist_to_destination*100:.2f}cm do destino exato ({destination_exact}), adicionando destino exato")
                            path_to_display.append(destination_exact)
                        else:
                            print(f"✅ INTERFACE: Último ponto do caminho já está no destino exato (distância: {dist_to_destination*100:.2f}cm)")
                    elif not destination_exact:
                        print(f"⚠️ INTERFACE: Não foi possível obter destino exato! original_destination={getattr(self.navigator, 'original_destination', None)}, destination={destination}")
                else:
                    # Se o robô está retornando, mostra o caminho completo (já atualizado para retorno)
                    path_to_display = list(self.navigator.path)
                    print(f"🔍 INTERFACE: Robô retornando, mostrando caminho de retorno: {len(path_to_display)} pontos")
                
                self.map_widget.set_current_path(path_to_display)
                print(f"🎯 INTERFACE: Caminho passado para interface: {len(path_to_display)} pontos, último ponto: {path_to_display[-1] if path_to_display else 'N/A'}")
            else:
                print(f"⚠️ INTERFACE: Nenhum caminho disponível no navegador! path existe? {hasattr(self.navigator, 'path')}, path length? {len(self.navigator.path) if hasattr(self.navigator, 'path') else 0}")
            
            # 🎯 NOVO: Atualiza status baseado na escolha do usuário
            status_text = "Navegação automática (ida + volta)..." if should_return else "Navegação automática (apenas ida)..."
            self.nav_status_label.setText(f"Status: {status_text}")
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
        # Permite salvar mesmo se autosave estiver desabilitado (útil ao fechar)
        if not self.has_unsaved_changes:
            print("💾 Autosave: Nenhuma alteração para salvar")
            return
            
        try:
            # Tenta usar o nome do mapa atual ou do mapa PGM carregado
            if self.current_map:
                map_name = self.current_map['nome']
            elif self.map_widget.map_name:
                map_name = self.map_widget.map_name
            else:
                # Usa o nome do arquivo PGM se disponível, ou gera um nome automático
                map_name = f"Mapa_Auto_{int(time.time())}"
                print(f"💾 Autosave: Usando nome automático: {map_name}")
            
            print(f"💾 Autosave: Salvando mapa '{map_name}'...")
            print(f"   POIs: {len(self.map_widget.points_of_interest)}")
            print(f"   Áreas proibidas: {len(self.map_widget.forbidden_areas)}")
                
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
            
            print(f"✅ Autosave: Mapa '{map_name}' salvo com sucesso!")
            
            if show_message:
                QMessageBox.information(self, "Autosave", f"Mapa '{map_name}' salvo automaticamente!")
                
        except Exception as e:
            print(f"❌ Erro no Autosave: {str(e)}")
            import traceback
            traceback.print_exc()
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
        # Primeiro, tenta salvar automaticamente se houver alterações
        if self.has_unsaved_changes:
            if self.autosave_enabled:
                # Autosave habilitado: salva automaticamente
                print("💾 Autosave: Salvando alterações antes de fechar...")
                self._perform_autosave(show_message=False)
            else:
                # Autosave desabilitado: pergunta ao usuário
                if not self._check_unsaved_changes():
                    event.ignore()
                    return
        
        # Limpa recursos
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
    
    def _update_path_finder_for_pgm_map(self):
        """
        Atualiza o PathFinder com as dimensões e origem do mapa PGM carregado.
        UNIFICAÇÃO: Garante que o PathFinder funcione igual para mapas PGM e não PGM.
        """
        if self.map_widget.map_image is None:
            print("⚠️  AVISO: Mapa PGM não carregado, PathFinder não atualizado")
            print("🔧 PathFinder usando configuração padrão do config.py")
            return
        
        # Calcula dimensões do mapa em metros
        map_width_m = self.map_widget.map_image.width() * self.map_widget.map_resolution
        map_height_m = self.map_widget.map_image.height() * self.map_widget.map_resolution
        
        # 🎯 UNIFICAÇÃO: Usa o mesmo grid_size do config.py para consistência
        # Isso garante que a navegação funcione igual para mapas PGM e não PGM
        from src.core.config import MAP_GRID_SIZE
        grid_size = MAP_GRID_SIZE  # Usa 0.1m (10cm) como padrão, não a resolução do PGM
        
        # Calcula dimensões em células usando o grid_size unificado
        width_cells = int(map_width_m / grid_size)
        height_cells = int(map_height_m / grid_size)
        
        # 🎯 CRÍTICO: Para mapas PGM, a origem pode ser diferente de (0,0)
        # Mas vamos garantir que as coordenadas sejam consistentes
        map_origin = self.map_widget.map_origin
        
        # Atualiza o PathFinder
        self.navigator.path_finder.update_map_config(
            width=width_cells,
            height=height_cells,
            grid_size=grid_size,
            map_origin=map_origin
        )
        
        print(f"🔧 PathFinder atualizado para mapa PGM (UNIFICADO):")
        print(f"   Dimensões: {width_cells}x{height_cells} células")
        print(f"   Tamanho físico: {map_width_m:.2f}m x {map_height_m:.2f}m")
        print(f"   Grid size: {grid_size}m/célula (UNIFICADO - mesmo dos mapas não PGM)")
        print(f"   Origem do mapa: {map_origin}")
        print(f"   Resolução PGM: {self.map_widget.map_resolution}m/pixel (apenas para visualização)")
    
    def _set_robot_initial_position_from_pgm(self, pgm_x: int, pgm_y: int):
        """
        Define a posição inicial do robô baseada em coordenadas de pixels do mapa PGM.
        
        Args:
            pgm_x: Coordenada X em pixels do mapa PGM
            pgm_y: Coordenada Y em pixels do mapa PGM
        """
        if self.map_widget.map_image is None:
            print("⚠️  AVISO: Mapa PGM não carregado, usando posição padrão")
            return
        
        # Converte pixels do PGM para coordenadas do mundo
        # 🎯 CORREÇÃO: O mapa PGM já foi processado pelo main_scanner.py
        # e está na orientação correta (Y crescendo para cima, como nosso sistema)
        # NÃO precisamos inverter Y!
        world_x = self.map_widget.map_origin[0] + (pgm_x * self.map_widget.map_resolution)
        world_y = self.map_widget.map_origin[1] + (pgm_y * self.map_widget.map_resolution)
        
        print(f"🔧 Definindo posição inicial do robô:")
        print(f"   PGM pixels: ({pgm_x}, {pgm_y})")
        print(f"   Mundo: ({world_x:.2f}, {world_y:.2f})m")
        print(f"   ✅ Sem inversão de Y (mapa já processado pelo main_scanner.py)")
        print(f"   Resolução: {self.map_widget.map_resolution}m/pixel")
        print(f"   Origem do mapa: {self.map_widget.map_origin}")
        
        # 🎯 VERIFICAÇÃO CRÍTICA: Testa a conversão reversa (mundo -> tela)
        # Isso garante que a posição visual corresponde à posição usada na navegação
        screen_x, screen_y = self.map_widget._world_to_screen_with_origin(world_x, world_y)
        print(f"🔧 VERIFICAÇÃO REVERSA (mundo -> tela):")
        print(f"   Mundo: ({world_x:.2f}, {world_y:.2f})m")
        print(f"   Tela: ({screen_x}, {screen_y})px")
        print(f"   Tamanho do widget: {self.map_widget.width()}x{self.map_widget.height()}px")
        
        # 🎯 VERIFICAÇÃO: Compara com a posição esperada visualmente
        # Se o usuário vê o robô em uma posição diferente, isso indica problema de conversão
        print(f"🔧 COMPARAÇÃO COM MAPAS NÃO-PGM:")
        from src.core.config import ROBOT_INITIAL_POSITION
        print(f"   Posição base em mapas não-PGM: {ROBOT_INITIAL_POSITION}m")
        print(f"   Posição base em mapas PGM: ({world_x:.2f}, {world_y:.2f})m")
        print(f"   Diferença: ({world_x - ROBOT_INITIAL_POSITION[0]:.2f}, {world_y - ROBOT_INITIAL_POSITION[1]:.2f})m")
        
        # 🎯 VERIFICAÇÃO: Garante que a posição está dentro dos limites do mapa
        map_width_m = self.map_widget.map_image.width() * self.map_widget.map_resolution
        map_height_m = self.map_widget.map_image.height() * self.map_widget.map_resolution
        map_min_x = self.map_widget.map_origin[0]
        map_max_x = map_min_x + map_width_m
        map_min_y = self.map_widget.map_origin[1]
        map_max_y = map_min_y + map_height_m
        
        # Verifica se a posição está dentro do mapa
        if world_x < map_min_x or world_x > map_max_x or world_y < map_min_y or world_y > map_max_y:
            print(f"⚠️  AVISO: Posição inicial ({world_x:.2f}, {world_y:.2f})m está FORA do mapa!")
            print(f"⚠️  Limites do mapa: X=[{map_min_x:.2f}, {map_max_x:.2f}]m, Y=[{map_min_y:.2f}, {map_max_y:.2f}]m")
            print(f"⚠️  Ajustando para o centro do mapa...")
            # Ajusta para o centro do mapa
            world_x = map_min_x + (map_width_m / 2.0)
            world_y = map_min_y + (map_height_m / 2.0)
            print(f"✅ Posição ajustada para: ({world_x:.2f}, {world_y:.2f})m")
        
        # Atualiza posição do robô em TODOS os lugares
        print(f"🔧 ANTES da atualização:")
        print(f"   map_widget.robot_position: {self.map_widget.robot_position}")
        print(f"   navigator.current_position: {self.navigator.current_position}")
        print(f"   navigator.base_position: {self.navigator.base_position}")
        
        self.map_widget.robot_position = (world_x, world_y)
        self.map_widget.base_position = (world_x, world_y)
        self.navigator.base_position = (world_x, world_y)
        # Usa set_pose para alinhar BNO ao referencial do mapa (evita seta errada / giro em loop)
        from src.core.config import ROBOT_INITIAL_ANGLE
        initial_angle_normalized = ROBOT_INITIAL_ANGLE
        if initial_angle_normalized > 180:
            initial_angle_normalized -= 360
        self.navigator.set_pose(world_x, world_y, initial_angle_normalized)
        
        self.map_widget.robot_angle = initial_angle_normalized
        
        print(f"🔧 Ângulo inicial (UNIFICADO): {ROBOT_INITIAL_ANGLE}° -> {initial_angle_normalized}° (normalizado para [-180, 180])")
        print(f"🔧 Posição inicial (UNIFICADA): ({world_x:.2f}, {world_y:.2f})m")
        print(f"🔧 Origem do mapa: {self.map_widget.map_origin}")
        
        print(f"🔧 DEPOIS da atualização:")
        print(f"   map_widget.robot_position: {self.map_widget.robot_position}")
        print(f"   navigator.current_position: {self.navigator.current_position}")
        print(f"   navigator.base_position: {self.navigator.base_position}")
        
        self.map_widget.update()
        
        print(f"✅ Posição inicial do robô definida: ({world_x:.2f}, {world_y:.2f})m")
        print(f"✅ Ângulo inicial do robô definido: {ROBOT_INITIAL_ANGLE}°")
        print(f"✅ Verificação: Posição dentro do mapa? X: {map_min_x <= world_x <= map_max_x}, Y: {map_min_y <= world_y <= map_max_y}")

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
        self.navigator._cancelled_by_obstacle = False  # Reset para próxima navegação
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
        
        # Tempos calibrados por faixa de ângulo (escala linear a partir de 90°)
        if angle_per_click <= 15:
            rotation_time = 0.25
        elif angle_per_click <= 30:
            rotation_time = 0.45
        elif angle_per_click <= 45:
            rotation_time = 0.85
        elif angle_per_click <= 60:
            rotation_time = 0.85
        elif angle_per_click <= 90:
            rotation_time = 1.25
        elif angle_per_click <= 120:
            rotation_time = 1.65   # 120° ≈ 1.33× o tempo de 90°
        elif angle_per_click <= 150:
            rotation_time = 2.05   # 150° ≈ 1.67× o tempo de 90°
        else:
            rotation_time = 2.50   # 180° ≈ 2× o tempo de 90°

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
        """Mantido para compatibilidade — delega ao sistema unificado de giro."""
        self._execute_precise_rotation("left")

    def _manual_turn_right(self):
        """Mantido para compatibilidade — delega ao sistema unificado de giro."""
        self._execute_precise_rotation("right")

    def _on_angle_slider_changed(self, value: int):
        """Atualiza o ângulo de rotação e os labels dos botões de giro."""
        self.angle_label.setText(f"{value}°")
        label_short = f"{value}°"
        if hasattr(self, 'btn_rotate_manual_left'):
            if self.is_small_screen:
                self.btn_rotate_manual_left.setText(f"↺ {label_short} ESQ")
            else:
                self.btn_rotate_manual_left.setText(f"↺ {label_short} ESQUERDA")
        if hasattr(self, 'btn_rotate_manual_right'):
            if self.is_small_screen:
                self.btn_rotate_manual_right.setText(f"↻ {label_short} DIR")
            else:
                self.btn_rotate_manual_right.setText(f"↻ {label_short} DIREITA")

    def _set_new_starting_position(self):
        """Define a posição atual como nova posição de partida com seleção de ângulo de referência."""
        current_pos = self.navigator.current_position
        current_angle = self.navigator.current_angle

        # Passo 1: confirmação de posição
        reply = QMessageBox.question(
            self,
            "Definir Nova Partida",
            f"Definir posição atual como nova partida?\n\n"
            f"Posição: ({current_pos[0]:.2f}, {current_pos[1]:.2f})\n"
            f"Ângulo odométrico atual: {current_angle:.1f}°\n\n"
            f"No próximo passo você poderá corrigir o ângulo de orientação\n"
            f"para que o robô virtual fique alinhado com o robô físico.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Passo 2: seleção do ângulo real do robô físico
        angle_options = [
            f"Manter odometria ({current_angle:.1f}°)",
            "0°   — apontando para LESTE  (→)",
            "90°  — apontando para NORTE  (↑) sul do mapa",
            "180° — apontando para OESTE  (←)",
            "270° — apontando para SUL    (↓) padrão da base",
        ]
        from PyQt5.QtWidgets import QInputDialog
        choice, ok = QInputDialog.getItem(
            self,
            "Orientação do Robô Físico",
            f"Para qual direção o robô físico está apontando agora?\n"
            f"(Odometria registrou: {current_angle:.1f}°)\n\n"
            f"Selecione o ângulo real:",
            angle_options,
            0,   # padrão: manter odometria
            False
        )
        if not ok:
            return

        angle_map = {
            angle_options[0]: current_angle,
            angle_options[1]: 0.0,
            angle_options[2]: 90.0,
            angle_options[3]: 180.0,
            angle_options[4]: 270.0,
        }
        new_angle = angle_map.get(choice, current_angle)

        # Aplica nova posição, ângulo e base
        self.map_widget.set_current_path([])
        self.navigator.reset_to_initial_state()
        self.navigator.current_position = current_pos
        self.navigator.current_angle = new_angle
        self.navigator.base_position = current_pos   # novo ponto de retorno

        self.map_widget.update_robot_position(current_pos[0], current_pos[1], new_angle)

        angle_corrected = f" (corrigido de {current_angle:.1f}°)" if abs(new_angle - current_angle) > 1.0 else ""
        QMessageBox.information(
            self,
            "Nova Partida Definida",
            f"Posição de partida atualizada!\n\n"
            f"Posição: ({current_pos[0]:.2f}, {current_pos[1]:.2f})\n"
            f"Ângulo: {new_angle:.1f}°{angle_corrected}\n\n"
            f"Esta posição também é a nova base de retorno."
        )
        print(f"📍 NOVA_PARTIDA: pos={current_pos}, ângulo={new_angle:.1f}°{angle_corrected}, base atualizada")

    def _return_to_base(self):
        """Inicia navegação de retorno para a base original com sincronia melhorada e debug"""
        print("🏠 RETORNO_BASE: Método chamado - iniciando verificação")
        
        if self.navigation_active:
            print("⚠️ RETORNO_BASE: Navegação já ativa, bloqueando retorno")
            QMessageBox.warning(self, "Aviso", "Aguarde o término da navegação atual.")
            return
        
        # 🎯 CORREÇÃO: Usa base_position do widget/navegador (pode ser diferente para mapas PGM)
        base_position = self.map_widget.base_position if hasattr(self.map_widget, 'base_position') and self.map_widget.base_position else ROBOT_INITIAL_POSITION
        if hasattr(self.navigator, 'base_position') and self.navigator.base_position:
            base_position = self.navigator.base_position
        
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
                # 🔄 RESET do estado para garantir navegação limpa (preserva posição para mapas PGM)
                print("🏠 RETORNO_BASE: Resetando estado do navegador")
                self.navigator.reset_to_initial_state(preserve_position=True)
                
                # 🔧 GARANTE que posição e ângulo atuais estão corretos
                print("🏠 RETORNO_BASE: Sincronizando posição e ângulo atuais")
                self.navigator.current_position = current_pos
                self.navigator.current_angle = current_angle
                self.navigator.base_position = base_position
                
                print(f"🏠 RETORNO_BASE: Estado após reset - Posição: {self.navigator.current_position}, Ângulo: {self.navigator.current_angle:.1f}°")
                
                # 🚀 INICIA retorno usando método da versão estável
                print("🏠 RETORNO_BASE: Calculando caminho de retorno...")
                path_to_base = self.navigator.path_finder.find_path(current_pos, base_position)
                if path_to_base and len(path_to_base) >= 2:
                    self.navigator.path = path_to_base
                    self.navigator.path_index = 0
                    self.navigator.current_target = self.navigator.path[0]
                    self.navigator.is_returning_to_base = True
                    self.navigator.navigation_state = "ORIENTING_TO_TARGET"
                    self.navigator.navigation_active = True
                    print(f"🏠 RETORNO_BASE: Caminho calculado com {len(path_to_base)} pontos")
                else:
                    print("⚠️ RETORNO_BASE: Erro ao calcular caminho de retorno")
                    QMessageBox.warning(self, "Erro", "Não foi possível calcular o caminho de retorno à base.")
                    return
                
                print(f"🏠 RETORNO_BASE: Navegação de retorno iniciada - Estado: {self.navigator.navigation_state}")
                
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
    
    def _update_robot_initial_position(self, x: float, y: float):
        """Atualiza a posição inicial do robô em config.py."""
        import re
        from pathlib import Path
        
        config_path = Path("src/core/config.py")
        if not config_path.exists():
            QMessageBox.warning(self, "Erro", "Arquivo config.py não encontrado!")
            return
        
        try:
            # Lê o arquivo
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Substitui a linha ROBOT_INITIAL_POSITION
            pattern = r'ROBOT_INITIAL_POSITION\s*=\s*\([^)]+\)'
            replacement = f'ROBOT_INITIAL_POSITION = ({x:.2f}, {y:.2f})  # Atualizado pela interface'
            new_content = re.sub(pattern, replacement, content)
            
            # Salva o arquivo
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # Atualiza a posição do robô na interface
            from src.core.config import ROBOT_INITIAL_POSITION, ROBOT_INITIAL_ANGLE
            # Recarrega o módulo para pegar o novo valor
            import importlib
            import src.core.config as config_module
            importlib.reload(config_module)
            
            # Atualiza o robô na interface
            self.navigator.current_position = (x, y)
            self.navigator.base_position = (x, y)
            self.map_widget.robot_position = (x, y)
            self.map_widget.base_position = (x, y)
            self.map_widget.update()
            
            QMessageBox.information(
                self,
                "Posição Atualizada",
                f"Posição inicial do robô atualizada para:\n"
                f"X: {x:.2f}m\n"
                f"Y: {y:.2f}m\n\n"
                f"✅ Arquivo config.py atualizado.\n"
                f"✅ Robô reposicionado na interface."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao atualizar config.py:\n{str(e)}"
            )
