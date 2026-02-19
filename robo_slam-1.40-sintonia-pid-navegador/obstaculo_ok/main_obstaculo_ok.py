import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QCoreApplication

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
    # Inicializa o Qt
    app = init_qt()
    
    # Importa a janela principal após inicializar o Qt
    from src.interfaces.main_window import MainWindow
    
    # Cria e mostra a janela principal
    window = MainWindow()
    window.show()
    
    # Executa o loop principal
    sys.exit(app.exec_())