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

    # --mode existe só para o autostart, que não tem ninguém para clicar no diálogo.
    # SEM argumento o fluxo é exatamente o de sempre: o diálogo de escolha aparece.
    modo_arg = None
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a.startswith('--mode='):
            modo_arg = a.split('=', 1)[1]
        elif a == '--mode':
            if i + 1 >= len(args):
                print("ERRO: --mode exige um valor (semi-teleop ou autonomous)",
                      file=sys.stderr)
                sys.exit(2)
            modo_arg = args[i + 1]

    if modo_arg is None:
        dlg = ModeSelectionDialog()
        if dlg.exec_() != QDialog.Accepted:
            sys.exit(0)
        mode = dlg.selected_mode()
    else:
        escolhas = {'semi-teleop': AppMode.SEMI_TELEOP, 'autonomous': AppMode.AUTONOMOUS}
        mode = escolhas.get(modo_arg.strip().lower())
        if mode is None:
            print(f"ERRO: --mode inválido: {modo_arg!r}. Use: {', '.join(escolhas)}",
                  file=sys.stderr)
            sys.exit(2)
        print(f"Modo vindo da linha de comando: {modo_arg} (diálogo pulado)")

    if mode is None:
        sys.exit(0)
    if mode == AppMode.SEMI_TELEOP:
        sys.exit(run_semi_teleop_session())

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())