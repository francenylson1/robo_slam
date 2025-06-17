from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QSpinBox, QComboBox)
from PyQt5.QtCore import Qt
import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.config import *

class AddPointDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adicionar Ponto de Interesse")
        self.setModal(True)
        
        # Configura a interface
        self._setup_ui()
        
    def _setup_ui(self):
        """Configura a interface do diálogo."""
        layout = QVBoxLayout(self)
        
        # Nome do ponto
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nome:"))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Tipo do ponto
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Tipo:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Mesa", "Base", "Ponto de Parada"])
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
        x_layout.addWidget(self.x_spin)
        coords_layout.addLayout(x_layout)
        
        # Coordenada Y
        y_layout = QVBoxLayout()
        y_layout.addWidget(QLabel("Y (metros):"))
        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, int(ENVIRONMENT_HEIGHT * 100))
        self.y_spin.setSingleStep(10)  # 10cm
        y_layout.addWidget(self.y_spin)
        coords_layout.addLayout(y_layout)
        
        layout.addLayout(coords_layout)
        
        # Botões
        buttons_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        buttons_layout.addWidget(ok_button)
        
        layout.addLayout(buttons_layout)
        
    def get_point_data(self):
        """Retorna o nome e a posição do ponto de interesse."""
        name = self.name_edit.text()
        position = (
            self.x_spin.value() / 100.0,  # Converte para metros
            self.y_spin.value() / 100.0
        )
        return name, position 