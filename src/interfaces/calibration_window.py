import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QSlider, QDialog, QGridLayout,
                             QGroupBox)
from PyQt5.QtCore import Qt
import pyqtgraph as pg
import time

class CalibrationWindow(QDialog):
    """
    Janela de calibração para ajuste fino dos parâmetros PID dos motores do robô.
    """
    def __init__(self, motor_controller, parent=None):
        super().__init__(parent)
        self.motor_controller = motor_controller

        self.setWindowTitle("Ferramenta de Calibração PID")
        self.setGeometry(150, 150, 1000, 700)  # Posição x, y, largura, altura

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self._create_widgets()
        self._connect_signals()

    def _create_widgets(self):
        """Cria os widgets da interface de calibração."""
        # Layout principal para os painéis
        panels_layout = QHBoxLayout()

        # --- Painel de Controle (Esquerda) ---
        control_panel_layout = QVBoxLayout()
        
        # Grupo para ambos os conjuntos de PID
        pid_groups_box = QGroupBox("Ajuste de Ganhos PID")
        pid_groups_layout = QHBoxLayout()
        self.left_pid_group, self.left_pid_sliders = self._create_pid_group("Motor Esquerdo")
        self.right_pid_group, self.right_pid_sliders = self._create_pid_group("Motor Direito")
        pid_groups_layout.addWidget(self.left_pid_group)
        pid_groups_layout.addWidget(self.right_pid_group)
        pid_groups_box.setLayout(pid_groups_layout)
        control_panel_layout.addWidget(pid_groups_box)

        # Grupo para botões de teste
        test_buttons_group = QGroupBox("Comandos de Teste")
        test_buttons_layout = QGridLayout()
        self.forward_button = QPushButton("Andar Reto (50cm)")
        self.turn_left_button = QPushButton("Girar Esquerda (90°)")
        self.turn_right_button = QPushButton("Girar Direita (90°)")
        self.stop_button = QPushButton("PARAR")
        self.stop_button.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold;")
        test_buttons_layout.addWidget(self.forward_button, 0, 0)
        test_buttons_layout.addWidget(self.turn_left_button, 1, 0)
        test_buttons_layout.addWidget(self.turn_right_button, 1, 1)
        test_buttons_layout.addWidget(self.stop_button, 0, 1)
        test_buttons_group.setLayout(test_buttons_layout)
        control_panel_layout.addWidget(test_buttons_group)
        
        control_panel_widget = QWidget()
        control_panel_widget.setLayout(control_panel_layout)
        panels_layout.addWidget(control_panel_widget, 1) # Proporção 1

        # --- Painel de Gráficos (Direita) ---
        charts_panel_widget = QWidget()
        charts_layout = QVBoxLayout()
        self.left_plot = pg.PlotWidget(title="Motor Esquerdo")
        self.right_plot = pg.PlotWidget(title="Motor Direito")
        charts_layout.addWidget(self.left_plot)
        charts_layout.addWidget(self.right_plot)
        charts_panel_widget.setLayout(charts_layout)
        panels_layout.addWidget(charts_panel_widget, 2) # Proporção 2 (mais largo)
        
        self.main_layout.addLayout(panels_layout)

        # Configura as linhas dos gráficos
        self._setup_plots()

    def _setup_plots(self):
        """Configura as plotagens iniciais para os gráficos."""
        # Linhas do Gráfico Esquerdo
        self.left_plot.addLegend()
        self.left_setpoint_line = self.left_plot.plot(pen='g', name='Alvo (Setpoint)')
        self.left_real_speed_line = self.left_plot.plot(pen='r', name='Velocidade Real')
        self.left_pid_output_line = self.left_plot.plot(pen='b', name='Saída PID')

        # Linhas do Gráfico Direito
        self.right_plot.addLegend()
        self.right_setpoint_line = self.right_plot.plot(pen='g', name='Alvo (Setpoint)')
        self.right_real_speed_line = self.right_plot.plot(pen='r', name='Velocidade Real')
        self.right_pid_output_line = self.right_plot.plot(pen='b', name='Saída PID')

        # Armazenamento de dados
        self.time_data = []
        self.left_setpoint_data, self.left_real_speed_data, self.left_pid_output_data = [], [], []
        self.right_setpoint_data, self.right_real_speed_data, self.right_pid_output_data = [], [], []
        self.start_time = time.time()

    def _create_pid_group(self, title):
        """Cria um grupo de widgets para o ajuste de PID de um motor."""
        group_box = QGroupBox(title)
        layout = QGridLayout()
        
        # Ganhos: Kp, Ki, Kd
        gains = ["Kp", "Ki", "Kd"]
        sliders = {}

        for i, gain in enumerate(gains):
            label = QLabel(f"{gain}:")
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 500)  # Representa 0.00 a 5.00
            slider.setValue(5)      # Valor inicial 0.05
            value_label = QLabel("0.05") # Label para mostrar o valor
            
            layout.addWidget(label, i, 0)
            layout.addWidget(slider, i, 1)
            layout.addWidget(value_label, i, 2)

            # Armazena os sliders e labels para acesso posterior
            sliders[gain] = (slider, value_label)

        group_box.setLayout(layout)
        return group_box, sliders

    def _connect_signals(self):
        """Conecta os sinais dos widgets às suas funções (slots)."""
        # Conecta os sliders do motor esquerdo
        for gain, (slider, label) in self.left_pid_sliders.items():
            slider.valueChanged.connect(lambda value, g=gain, l=label: self._update_pid_label(value, g, l, "left"))
        
        # Conecta os sliders do motor direito
        for gain, (slider, label) in self.right_pid_sliders.items():
            slider.valueChanged.connect(lambda value, g=gain, l=label: self._update_pid_label(value, g, l, "right"))
        
        # Conecta o sinal do motor_controller ao slot de atualização dos gráficos
        if self.motor_controller:
            self.motor_controller.pid_data_updated.connect(self._update_plots)

        # Conecta os botões de teste
        self.forward_button.clicked.connect(self._test_forward)
        self.stop_button.clicked.connect(self._test_stop)
        # TODO: Conectar os botões de giro

    def _update_pid_label(self, value, gain_name, label, motor_side):
        """Atualiza a label de valor do PID e envia os novos ganhos para o motor_controller."""
        # Atualiza a label visualmente
        float_value = value / 100.0
        label.setText(f"{float_value:.2f}")
        
        # Obtém todos os ganhos atuais do lado do motor que está sendo ajustado
        if motor_side == "left":
            sliders = self.left_pid_sliders
        else:
            sliders = self.right_pid_sliders

        # Lê os valores de todos os sliders para aquele lado
        kp = sliders['Kp'][0].value() / 100.0
        ki = sliders['Ki'][0].value() / 100.0
        kd = sliders['Kd'][0].value() / 100.0
        
        # Envia os 3 ganhos atualizados para o controlador do motor
        self.motor_controller.set_pid_gains(motor_side, kp, ki, kd)
        print(f"PID Aply: Lado={motor_side}, Kp={kp:.2f}, Ki={ki:.2f}, Kd={kd:.2f}")

    def _update_plots(self, side, setpoint, real_speed, output):
        """Recebe os dados do motor e atualiza os gráficos."""
        current_time = time.time() - self.start_time
        self.time_data.append(current_time)
        
        # Limita o tamanho dos dados para não consumir muita memória
        if len(self.time_data) > 200:
            self.time_data.pop(0)
            if side == "left": self.left_setpoint_data.pop(0); self.left_real_speed_data.pop(0); self.left_pid_output_data.pop(0)
            if side == "right": self.right_setpoint_data.pop(0); self.right_real_speed_data.pop(0); self.right_pid_output_data.pop(0)

        if side == "left":
            self.left_setpoint_data.append(setpoint)
            self.left_real_speed_data.append(real_speed)
            self.left_pid_output_data.append(output)
            self.left_setpoint_line.setData(self.time_data, self.left_setpoint_data)
            self.left_real_speed_line.setData(self.time_data, self.left_real_speed_data)
            self.left_pid_output_line.setData(self.time_data, self.left_pid_output_data)
        elif side == "right":
            self.right_setpoint_data.append(setpoint)
            self.right_real_speed_data.append(real_speed)
            self.right_pid_output_data.append(output)
            self.right_setpoint_line.setData(self.time_data, self.right_setpoint_data)
            self.right_real_speed_line.setData(self.time_data, self.right_real_speed_data)
            self.right_pid_output_line.setData(self.time_data, self.right_pid_output_data)

    def _test_forward(self):
        """Envia um comando para o robô andar reto."""
        print("Comando: Andar Reto")
        # Define uma velocidade alvo modesta em ticks por segundo para ambos os motores
        target_speed_tps = 15.0 
        self.motor_controller.set_target_speed(target_speed_tps, target_speed_tps)

    def _test_stop(self):
        """Envia um comando de parada para o robô."""
        print("Comando: PARAR")
        self.motor_controller.stop()

        # Limpa os dados dos gráficos ao parar
        self.time_data.clear()
        self.left_setpoint_data.clear(); self.left_real_speed_data.clear(); self.left_pid_output_data.clear()
        self.right_setpoint_data.clear(); self.right_real_speed_data.clear(); self.right_pid_output_data.clear()
        self.start_time = time.time()


# Bloco para teste independente da janela (opcional, mas útil)
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Para testar, precisaríamos de um 'motor_controller' fake.
    # Por enquanto, podemos passar None, mas a janela não será totalmente funcional.
    class MockMotorController:
        def __init__(self):
            print("MockMotorController inicializado.")
            # Simula o sinal de atualização dos gráficos
            self.pid_data_updated = self.emit_pid_data_updated

        def emit_pid_data_updated(self, side, setpoint, real_speed, output):
            print(f"MockMotorController: Emitindo sinal pid_data_updated para o gráfico. Lado: {side}, Setpoint: {setpoint}, Real Speed: {real_speed}, Output: {output}")

    mock_controller = MockMotorController()
    cal_window = CalibrationWindow(motor_controller=mock_controller)
    cal_window.show()
    
    sys.exit(app.exec_()) 