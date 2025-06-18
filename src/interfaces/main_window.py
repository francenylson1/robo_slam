from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QComboBox, QMessageBox,
                             QGroupBox, QGridLayout, QInputDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QCursor
import sys
import os
import time

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

        map_management_layout.addWidget(save_map_btn, 0, 0)
        map_management_layout.addWidget(load_map_btn, 0, 1)
        map_management_layout.addWidget(autosave_btn, 1, 0, 1, 2)  # Ocupa duas colunas
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
                    self._reload_forbidden_areas()  # Recarrega áreas proibidas com IDs
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
                    self._reload_forbidden_areas()  # Recarrega áreas proibidas com IDs
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
        # Obtém o mapa ativo do banco se não tiver um carregado
        if not self.current_map:
            self.current_map = self.map_manager.get_active_map()
            if not self.current_map:
                print("DEBUG: Nenhum mapa ativo encontrado para recarregar áreas proibidas")
                return
            
        # Obtém as áreas proibidas com IDs do banco
        areas_with_ids = self.map_manager.get_forbidden_areas_with_ids(self.current_map['id'])
        print(f"DEBUG: Recarregando {len(areas_with_ids)} áreas proibidas")
        
        # Atualiza o MapWidget
        self.map_widget.forbidden_areas = areas_with_ids
        self.map_widget.update()
        
        # Atualiza a lista de áreas proibidas
        self._update_forbidden_areas_list()
        
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
        if not self.map_widget.forbidden_areas:
            QMessageBox.warning(self, "Aviso", "Não há áreas proibidas para excluir!")
            return
            
        # Verifica se há uma área selecionada
        selected_area = self.map_widget.get_selected_area()
        if selected_area:
            area_id = selected_area.get('id', 0)
            area_name = selected_area.get('nome', f'Área {area_id}')
        else:
            # Se não há área selecionada, usa a primeira da lista
            if self.forbidden_areas_combo.currentText():
                # Extrai o ID da string do combo box
                combo_text = self.forbidden_areas_combo.currentText()
                try:
                    area_id = int(combo_text.split("ID: ")[1].rstrip(")"))
                    area_name = combo_text.split(" (ID:")[0]
                except:
                    QMessageBox.warning(self, "Erro", "Erro ao identificar área selecionada!")
                    return
            else:
                QMessageBox.warning(self, "Aviso", "Selecione uma área para excluir!")
                return
        
        # Confirma a exclusão
        reply = QMessageBox.question(
            self, 'Confirmar Exclusão',
            f'Tem certeza que deseja excluir a área "{area_name}"?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Remove do banco de dados
            success = self.map_manager.delete_forbidden_area(area_id)
            if success:
                # Recarrega as áreas proibidas
                self._reload_forbidden_areas()
                self._mark_unsaved_changes()  # Marca alterações não salvas
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
            self.has_unsaved_changes = False  # Limpa alterações não salvas
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
