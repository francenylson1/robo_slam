import sys
import os
from PyQt5.QtWidgets import QApplication, QDialog

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Tenta diferentes backends do Qt
def init_qt():
    # Lista de backends para tentar
    backends = ['xcb', 'wayland', 'offscreen']
    
    for backend in backends:
        try:
            os.environ['QT_QPA_PLATFORM'] = backend
            app = QApplication(sys.argv)
            return app
        except Exception as e:
            print(f"Falha ao inicializar backend {backend}: {str(e)}")
            continue
    
    # Se nenhum backend funcionar, tenta sem especificar
    try:
        app = QApplication(sys.argv)
        return app
    except Exception as e:
        print(f"Falha ao inicializar Qt: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    # Configura o logging centralizado antes de qualquer import do projeto
    from src.core.config import setup_logging
    setup_logging()

    # Inicializa o Qt
    app = init_qt()
    
    from src.interfaces.mode_selection_dialog import AppMode, ModeSelectionDialog
    from src.interfaces.main_window import MainWindow
    from src.core.semi_teleop_runner import run_semi_teleop_session

    dlg = ModeSelectionDialog()
    if dlg.exec_() != QDialog.Accepted:
        sys.exit(0)
    mode = dlg.selected_mode()
    if mode is None:
        sys.exit(0)
    if mode == AppMode.SEMI_TELEOP:
        sys.exit(run_semi_teleop_session())

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())