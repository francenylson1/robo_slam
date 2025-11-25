"""Interface gráfica para o Aurora Mapping Studio."""

from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QLineEdit,
    QFileDialog,
    QGroupBox,
    QCheckBox,
    QProgressBar,
    QTextEdit,
    QMessageBox,
    QSplitter,
    QFrame,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QImage

# Adiciona o diretório raiz ao PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Adiciona também o diretório src (necessário para imports do aurora_mapping)
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Garante que estamos no diretório correto
os.chdir(ROOT_DIR)

from aurora_mapping.pipelines.workflows import PipelineContext, get_pipeline_choices, run_pipeline
from aurora_mapping.utils.config_loader import load_mapping_config


class PipelineWorker(QThread):
    """Worker thread para executar o pipeline sem travar a interface."""

    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, pipeline: str, context: PipelineContext):
        super().__init__()
        self.pipeline = pipeline
        self.context = context

    def run(self):
        """Executa o pipeline em thread separada."""

        try:
            # Captura prints durante execução
            import sys
            from io import StringIO

            class LogCapture:
                def __init__(self, worker):
                    self.worker = worker
                    self.buffer = StringIO()
                
                def write(self, text):
                    if text.strip():
                        self.worker.progress.emit(text.strip())
                    self.buffer.write(text)
                
                def flush(self):
                    pass

            log_capture = LogCapture(self)
            old_stdout = sys.stdout
            sys.stdout = log_capture

            run_pipeline(self.pipeline, self.context)

            sys.stdout = old_stdout
            output = log_capture.buffer.getvalue()

            self.finished.emit(True, output)
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)
            self.finished.emit(False, error_msg)


class MappingStudioWindow(QMainWindow):
    """Janela principal do Aurora Mapping Studio."""

    def __init__(self):
        super().__init__()
        self.worker: Optional[PipelineWorker] = None
        self.init_ui()

    def init_ui(self):
        """Inicializa a interface do usuário."""

        self.setWindowTitle("🗺️  Aurora Mapping Studio")
        self.setMinimumSize(900, 700)

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Título
        title = QLabel("🗺️  Aurora Mapping Studio")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)

        # Splitter horizontal
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Painel esquerdo - Configurações
        left_panel = self.create_config_panel()
        splitter.addWidget(left_panel)

        # Painel direito - Logs e Preview
        right_panel = self.create_output_panel()
        splitter.addWidget(right_panel)

        # Proporções do splitter
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        # Barra de status
        self.statusBar().showMessage("Pronto")

    def create_config_panel(self) -> QWidget:
        """Cria o painel de configurações."""

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        # Pipeline
        pipeline_group = QGroupBox("Pipeline")
        pipeline_layout = QVBoxLayout()
        self.pipeline_combo = QComboBox()
        self.pipeline_combo.addItems(list(get_pipeline_choices()))
        self.pipeline_combo.currentTextChanged.connect(self.on_pipeline_changed)
        pipeline_layout.addWidget(QLabel("Tipo de Pipeline:"))
        pipeline_layout.addWidget(self.pipeline_combo)
        pipeline_group.setLayout(pipeline_layout)
        layout.addWidget(pipeline_group)

        # Entrada
        input_group = QGroupBox("Entrada")
        input_layout = QVBoxLayout()
        input_hbox = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("mapas/legacy/originais_aurora")
        input_browse_btn = QPushButton("📁")
        input_browse_btn.setMaximumWidth(40)
        input_browse_btn.clicked.connect(self.browse_input)
        input_hbox.addWidget(self.input_edit)
        input_hbox.addWidget(input_browse_btn)
        input_layout.addLayout(input_hbox)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Saída
        output_group = QGroupBox("Saída")
        output_layout = QVBoxLayout()
        output_hbox = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("data/pipeline_runs/meu_mapa")
        output_browse_btn = QPushButton("📁")
        output_browse_btn.setMaximumWidth(40)
        output_browse_btn.clicked.connect(self.browse_output)
        output_hbox.addWidget(self.output_edit)
        output_hbox.addWidget(output_browse_btn)
        output_layout.addLayout(output_hbox)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # Etapas (apenas para aurora_to_c1)
        self.steps_group = QGroupBox("Etapas (Opcional)")
        steps_layout = QVBoxLayout()
        steps_layout.addWidget(QLabel("Marque as etapas a executar (deixe vazio para todas):"))
        
        self.step_capture = QCheckBox("capture")
        self.step_refinement = QCheckBox("refinement")
        self.step_map2d = QCheckBox("map2d")
        self.step_c1_conversion = QCheckBox("c1_conversion")
        self.step_annotation = QCheckBox("annotation")
        self.step_export = QCheckBox("export")

        steps_layout.addWidget(self.step_capture)
        steps_layout.addWidget(self.step_refinement)
        steps_layout.addWidget(self.step_map2d)
        steps_layout.addWidget(self.step_c1_conversion)
        steps_layout.addWidget(self.step_annotation)
        steps_layout.addWidget(self.step_export)

        self.steps_group.setLayout(steps_layout)
        layout.addWidget(self.steps_group)

        # Botões
        buttons_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("▶️  Executar Pipeline")
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.run_btn.clicked.connect(self.run_pipeline)
        buttons_layout.addWidget(self.run_btn)

        self.stop_btn = QPushButton("⏹️  Parar")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_pipeline)
        buttons_layout.addWidget(self.stop_btn)

        layout.addLayout(buttons_layout)

        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        layout.addStretch()

        return panel

    def create_output_panel(self) -> QWidget:
        """Cria o painel de saída (logs e preview)."""

        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Abas (simulado com GroupBoxes)
        tabs_group = QGroupBox("Saída")
        tabs_layout = QVBoxLayout()

        # Logs
        logs_label = QLabel("📋 Logs de Execução:")
        logs_label.setStyleSheet("font-weight: bold;")
        tabs_layout.addWidget(logs_label)

        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFont(QFont("Courier", 9))
        self.logs_text.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        tabs_layout.addWidget(self.logs_text)

        # Preview (será preenchido após execução)
        preview_label = QLabel("🖼️  Preview do Mapa:")
        preview_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        tabs_layout.addWidget(preview_label)

        self.preview_label = QLabel("Nenhum preview disponível")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                padding: 20px;
                background-color: #f9f9f9;
                color: #666;
            }
        """)
        self.preview_label.setMinimumHeight(200)
        tabs_layout.addWidget(self.preview_label)

        tabs_group.setLayout(tabs_layout)
        layout.addWidget(tabs_group)

        return panel

    def on_pipeline_changed(self, pipeline: str):
        """Atualiza interface quando pipeline muda."""

        # Mostra/oculta grupo de etapas apenas para aurora_to_c1
        if pipeline == "aurora_to_c1":
            self.steps_group.setVisible(True)
        else:
            self.steps_group.setVisible(False)

    def browse_input(self):
        """Abre diálogo para selecionar entrada."""

        pipeline = self.pipeline_combo.currentText()
        
        if pipeline == "inventory_snapshot":
            path = QFileDialog.getExistingDirectory(self, "Selecionar Diretório de Entrada")
        else:
            # Para outros pipelines, pode ser arquivo ou diretório
            path, _ = QFileDialog.getOpenFileName(
                self, "Selecionar Arquivo ou Diretório", "", "Todos os Arquivos (*)"
            )
            if not path:
                path = QFileDialog.getExistingDirectory(self, "Ou selecionar Diretório")

        if path:
            self.input_edit.setText(path)

    def browse_output(self):
        """Abre diálogo para selecionar saída."""

        path = QFileDialog.getExistingDirectory(self, "Selecionar Diretório de Saída")
        if path:
            self.output_edit.setText(path)

    def get_selected_steps(self) -> Optional[list[str]]:
        """Retorna lista de etapas selecionadas."""

        steps = []
        if self.step_capture.isChecked():
            steps.append("capture")
        if self.step_refinement.isChecked():
            steps.append("refinement")
        if self.step_map2d.isChecked():
            steps.append("map2d")
        if self.step_c1_conversion.isChecked():
            steps.append("c1_conversion")
        if self.step_annotation.isChecked():
            steps.append("annotation")
        if self.step_export.isChecked():
            steps.append("export")

        return steps if steps else None

    def log(self, message: str):
        """Adiciona mensagem aos logs."""

        self.logs_text.append(message)
        # Auto-scroll para o final
        self.logs_text.verticalScrollBar().setValue(
            self.logs_text.verticalScrollBar().maximum()
        )

    def run_pipeline(self):
        """Executa o pipeline."""

        # Validação
        pipeline = self.pipeline_combo.currentText()
        input_path = self.input_edit.text().strip()
        output_path = self.output_edit.text().strip()

        if not input_path:
            QMessageBox.warning(self, "Erro", "Por favor, selecione um caminho de entrada.")
            return

        if not output_path:
            QMessageBox.warning(self, "Erro", "Por favor, selecione um caminho de saída.")
            return

        # Limpa logs
        self.logs_text.clear()
        self.log("🚀 Iniciando pipeline...")
        self.log(f"Pipeline: {pipeline}")
        self.log(f"Entrada: {input_path}")
        self.log(f"Saída: {output_path}")

        # Prepara contexto
        steps = self.get_selected_steps()
        if steps:
            self.log(f"Etapas selecionadas: {', '.join(steps)}")

        config = load_mapping_config()
        context = PipelineContext(
            input_path=input_path,
            output_dir=output_path,
            metadata=config,
            steps=steps,
        )

        # Desabilita botão e mostra progresso
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminado

        # Cria e inicia worker
        self.worker = PipelineWorker(pipeline, context)
        self.worker.finished.connect(self.on_pipeline_finished)
        self.worker.error.connect(self.on_pipeline_error)
        self.worker.progress.connect(self.log)
        self.worker.start()

        # Timer para capturar prints (simulação)
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(lambda: None)
        self.log_timer.start(100)

    def stop_pipeline(self):
        """Para a execução do pipeline."""

        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.log("⏹️  Pipeline interrompido pelo usuário.")
            self.on_pipeline_finished(False, "Interrompido")

    def on_pipeline_finished(self, success: bool, output: str):
        """Callback quando pipeline termina."""

        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        if success:
            self.log("\n✅ Pipeline executado com sucesso!")
            self.statusBar().showMessage("Pipeline concluído com sucesso", 5000)
            
            # Tenta carregar preview
            self.load_preview()
        else:
            self.log(f"\n❌ Erro: {output}")
            self.statusBar().showMessage("Erro ao executar pipeline", 5000)

    def on_pipeline_error(self, error_msg: str):
        """Callback quando há erro no pipeline."""

        self.log(f"\n❌ Erro: {error_msg}")
        QMessageBox.critical(self, "Erro", f"Erro ao executar pipeline:\n\n{error_msg}")

    def load_preview(self):
        """Carrega preview do mapa gerado."""

        output_path = self.output_edit.text().strip()
        if not output_path:
            self.log("⚠️  Caminho de saída não especificado para carregar preview")
            return

        # Converte para Path absoluto
        output_dir = Path(output_path).resolve()
        
        if not output_dir.exists():
            self.log(f"⚠️  Diretório de saída não existe: {output_dir}")
            return

        self.log(f"🔍 Buscando preview em: {output_dir}")
        
        import glob
        
        # Lista de padrões para buscar (em ordem de prioridade)
        preview_patterns = [
            # Preview do refinement (point cloud) - mais comum
            str(output_dir / "refinement" / "*_preview.png"),
            # Layout do export
            str(output_dir / "export" / "*" / "*_layout.png"),
            # Preview do map2d (se houver)
            str(output_dir / "map2d" / "*_preview.png"),
            # Qualquer PNG no export
            str(output_dir / "export" / "*" / "*.png"),
        ]

        for pattern in preview_patterns:
            matches = glob.glob(pattern)
            if matches:
                preview_path = Path(matches[0])
                self.log(f"📸 Tentando carregar: {preview_path}")
                
                pixmap = QPixmap(str(preview_path))
                if not pixmap.isNull():
                    # Redimensiona se muito grande
                    if pixmap.width() > 600 or pixmap.height() > 400:
                        pixmap = pixmap.scaled(600, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.preview_label.setPixmap(pixmap)
                    self.preview_label.setText("")
                    self.log(f"✅ Preview carregado com sucesso: {preview_path.name}")
                    return
                else:
                    self.log(f"⚠️  Não foi possível carregar imagem (QPixmap retornou null): {preview_path}")

        # Se não encontrou, tenta buscar recursivamente
        self.log("🔍 Buscando recursivamente por arquivos de preview...")
        all_pngs = list(output_dir.rglob("*.png"))
        
        # Prioriza preview e layout
        for img_path in sorted(all_pngs):
            if 'preview' in img_path.name.lower() or 'layout' in img_path.name.lower():
                try:
                    self.log(f"📸 Tentando carregar (busca recursiva): {img_path}")
                    pixmap = QPixmap(str(img_path))
                    if not pixmap.isNull():
                        if pixmap.width() > 600 or pixmap.height() > 400:
                            pixmap = pixmap.scaled(600, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        self.preview_label.setPixmap(pixmap)
                        self.preview_label.setText("")
                        self.log(f"✅ Preview carregado (busca recursiva): {img_path.name}")
                        return
                except Exception as e:
                    self.log(f"⚠️  Erro ao carregar {img_path}: {e}")
                    continue

        # Se ainda não encontrou, mostra mensagem
        self.preview_label.setText("Nenhum preview disponível")
        self.preview_label.setPixmap(QPixmap())
        self.log("⚠️  Nenhum preview encontrado. Verifique se o pipeline gerou arquivos de preview.")
        self.log(f"   Diretório verificado: {output_dir}")


def run_gui():
    """Inicia a interface gráfica."""

    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Estilo moderno

    window = MappingStudioWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    run_gui()

