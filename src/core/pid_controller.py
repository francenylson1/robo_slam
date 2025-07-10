import time

class PIDController:
    """
    Uma implementacao de um controlador Proporcional-Integral-Derivativo (PID).
    """
    def __init__(self, Kp, Ki, Kd, setpoint=0, sample_time=0.01, output_limits=(-100, 100)):
        """
        Inicializa o controlador PID.

        Args:
            Kp (float): Ganho Proporcional.
            Ki (float): Ganho Integral.
            Kd (float): Ganho Derivativo.
            setpoint (float): O valor desejado que o controlador tentara alcancar.
            sample_time (float): O intervalo de tempo entre as atualizacoes do controlador.
            output_limits (tuple): Uma tupla (min, max) para limitar a saida do controlador.
        """
        self.Kp, self.Ki, self.Kd = Kp, Ki, Kd
        self.setpoint = setpoint
        self.sample_time = sample_time
        self.output_limits = output_limits

        self._proportional_term = 0
        self._integral_term = 0
        self._derivative_term = 0
        
        self._last_error = 0
        self._last_output = 0
        self._last_time = time.time()
        
        self.reset()

    def update(self, process_variable):
        """
        Calcula a saida do controlador PID com base no valor atual do processo.
        """
        current_time = time.time()
        dt = current_time - self._last_time

        if dt <= self.sample_time:
            return self._last_output

        error = self.setpoint - process_variable
        
        # --- Termo Proporcional ---
        self._proportional_term = self.Kp * error
        
        # --- Termo Integral (com anti-windup implÃ­cito pela limitaÃ§Ã£o da saÃ­da) ---
        self._integral_term += error * dt
        
        # --- Termo Derivativo (evita "derivative kick" na primeira iteraÃ§Ã£o) ---
        if self._last_error != 0:
            delta_error = error - self._last_error
            self._derivative_term = self.Kd * (delta_error / dt)
        else:
            self._derivative_term = 0
        
        # --- Saida Final ---
        output = self._proportional_term + (self.Ki * self._integral_term) + self._derivative_term

        # Limita a saÃ­da
        if self.output_limits is not None:
            output = max(self.output_limits[0], min(self.output_limits[1], output))

        # Guarda os valores para a prÃ³xima iteraÃ§Ã£o
        self._last_error = error
        self._last_time = current_time
        self._last_output = output
        
        return output

    def set_setpoint(self, setpoint):
        """Atualiza o valor desejado."""
        self.setpoint = setpoint
        self.reset()

    def set_gains(self, Kp, Ki, Kd):
        """
        Permite ajustar os ganhos do PID em tempo real.
        """
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.reset()

    def reset(self):
        """Reseta o estado do controlador PID."""
        self._proportional_term = 0
        self._integral_term = 0
        self._derivative_term = 0
        self._last_error = 0
        self._last_output = 0
        self._last_time = time.time()