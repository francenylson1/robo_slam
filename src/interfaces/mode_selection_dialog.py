# -*- coding: utf-8 -*-
"""Diálogo inicial: modo semi-autônomo (joystick) vs navegação autônoma (mapa)."""

from __future__ import annotations

from enum import Enum, auto
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSizePolicy,
)
from PyQt5.QtCore import Qt


class AppMode(Enum):
    SEMI_TELEOP = auto()
    AUTONOMOUS = auto()


class ModeSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Robô SLAM — modo de operação")
        self.setModal(True)
        self._choice: AppMode | None = None

        layout = QVBoxLayout(self)
        title = QLabel("Escolha o modo de navegação")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title)

        hint = QLabel(
            "Semi-autônomo: joystick + rosto na tela (sem seleção de mapa).\n"
            "Autônomo: interface completa com mapas e POIs."
        )
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #444; margin-bottom: 16px;")
        layout.addWidget(hint)

        row = QHBoxLayout()
        self._btn_semi = QPushButton("Navegação\nsemi-autônoma")
        self._btn_auto = QPushButton("Navegação\nautônoma")
        for b in (self._btn_semi, self._btn_auto):
            b.setMinimumHeight(100)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setStyleSheet(
                "font-size: 16px; font-weight: bold; padding: 12px;"
            )
        self._btn_semi.clicked.connect(self._on_semi)
        self._btn_auto.clicked.connect(self._on_auto)
        row.addWidget(self._btn_semi)
        row.addWidget(self._btn_auto)
        layout.addLayout(row)

        self.resize(520, 260)

    def _on_semi(self):
        self._choice = AppMode.SEMI_TELEOP
        self.accept()

    def _on_auto(self):
        self._choice = AppMode.AUTONOMOUS
        self.accept()

    def selected_mode(self) -> Optional[AppMode]:
        return self._choice
