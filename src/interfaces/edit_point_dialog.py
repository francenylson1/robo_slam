from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QSpinBox, QComboBox)
from PyQt5.QtCore import Qt
import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.config import *

class EditPointDialog(QDialog):
    def __init__(self, parent=None, point_name="", position=(0, 0), point_type="Mesa"):
        super().__init__(parent)
        self.setWindowTitle("Editar Ponto de Interesse")
        self.setModal(True)
        
        # Armazena os dados iniciais
        self.initial_name = point_name
        self.initial_position = position
        self.initial_type = point_type
        
        # Configura a interface
        self._setup_ui()
        
    def _setup_ui(self):
        """Configura a interface do diálogo."""
        layout = QVBoxLayout(self)
        
        # Nome do ponto
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nome:"))
        self.name_edit = QLineEdit(self.initial_name)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Tipo do ponto
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Tipo:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Mesa", "Base", "Ponto de Parada"])
        self.type_combo.setCurrentText(self.initial_type)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
        # Coordenadas
        coords_layout = QHBoxLayout()
        
        # Coordenada X
        x_layout = QVBoxLayout()
        x_layout.addWidget(QLabel("X (metros):"))
        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, int(ENVIRONMENT_WIDTH * 100))
        self.x_spin.setSingleStep(10)  # 10cm
        self.x_spin.setValue(int(self.initial_position[0] * 100))
        x_layout.addWidget(self.x_spin)
        coords_layout.addLayout(x_layout)
        
        # Coordenada Y
        y_layout = QVBoxLayout()
        y_layout.addWidget(QLabel("Y (metros):"))
        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, int(ENVIRONMENT_HEIGHT * 100))
        self.y_spin.setSingleStep(10)  # 10cm
        self.y_spin.setValue(int(self.initial_position[1] * 100))
        y_layout.addWidget(self.y_spin)
        coords_layout.addLayout(y_layout)
        
        layout.addLayout(coords_layout)
        
        # Botões
        buttons_layout = QHBoxLayout()
        
        delete_button = QPushButton("Excluir")
        delete_button.clicked.connect(self._on_delete)
        buttons_layout.addWidget(delete_button)
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        ok_button = QPushButton("Salvar")
        ok_button.clicked.connect(self.accept)
        buttons_layout.addWidget(ok_button)
        
        layout.addLayout(buttons_layout)
        
    def get_edited_data(self):
        """Retorna os dados editados do ponto."""
        name = self.name_edit.text()
        position = (
            self.x_spin.value() / 100.0,  # Converte para metros
            self.y_spin.value() / 100.0
        )
        point_type = self.type_combo.currentText()
        return name, position, point_type
        
    def _on_delete(self):
        """Marca o ponto para exclusão."""
        self.delete_requested = True
        self.reject() 