# modules/robot_motor_controller.py
import time
import sys
import os
import logging
import threading
from PyQt5.QtCore import QObject, pyqtSignal

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.environment import GPIO_AVAILABLE, is_raspberry_pi
from src.core.pid_controller import PIDController
from src.core.config import (TICKS_PER_REVOLUTION, MANUAL_CONTROL_MAX_TPS,
                            PID_PROFILES, SAFETY_MAX_MOTOR_POWER_PERCENT,
                            SAFETY_POWER_MONITOR_INTERVAL, SAFETY_POWER_VIOLATION_TIMEOUT,
                            LIDAR_C1_ENABLED, LIDAR_OBSTACLE_MIN_DISTANCE)

logger = logging.getLogger(__name__)

# === CORREÇÃO DE DERIVA LATERAL ===
# Motor esquerdo reduzido para compensar deriva à direita.
# Ajuste fino: ver docs/AFINACAO_DESVIO_NAVEGACAO.md
LEFT_MOTOR_CORRECTION_FACTOR = 0.9600000
RIGHT_MOTOR_CORRECTION_FACTOR = 1.000000

if GPIO_AVAILABLE:
    try:
        import RPi.GPIO as GPIO
    except (ImportError, RuntimeError):
        logger.warning("RPi.GPIO não pôde ser importada. Motores não funcionarão.")
        GPIO_AVAILABLE = False
else:
    GPIO = None

class RobotMotorController(QObject):
    """
    Controla os motores do robô, abstraindo a complexidade do hardware.
    Pode operar em modo real (com Raspberry Pi e RPi.GPIO) ou em modo simulado.
    """
    pid_data_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.left_speed_percent = 0
        self.right_speed_percent = 0
        self.is_moving = False

        self.ticks_lock = threading.Lock()

        self.last_emit_time = 0
        self.emit_interval = 0.2  # segundos

        self.precise_rotation_left_direction = None
        self.precise_rotation_right_direction = None
        self.precise_rotation_mode = False

        self.simulated_left_tps = 0.0
        self.simulated_right_tps = 0.0
        self.last_sim_time = time.time()

        self.current_speed_profile = 'normal'
        self._initialize_pid_controllers()
        self.pid_enabled = False

        self.safety_monitor_enabled = True
        self.last_safety_check = time.time()
        self.power_violation_start_time = None

        self.left_hall_ticks = 0
        self.right_hall_ticks = 0
        self.last_speed_check_time = time.time()
        self.current_left_tps = 0.0
        self.current_right_tps = 0.0

        self.left_ticks_for_odometry = 0
        self.right_ticks_for_odometry = 0

        self.shutdown_event = threading.Event()

        if GPIO_AVAILABLE and GPIO:
            logger.info("Controlador de motores: MODO REAL (Raspberry Pi).")
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # PINOS DO MOTOR ESQUERDO
            self.dir_E = 5
            self.break_E = 6
            self.speed_E = 18
            self.hall_E = 16

            # PINOS DO MOTOR DIREITO
            self.dir_D = 23
            self.break_D = 24
            self.speed_D = 12
            self.hall_D = 17

            for pin in [self.dir_E, self.break_E, self.speed_E, self.dir_D, self.break_D, self.speed_D]:
                GPIO.setup(pin, GPIO.OUT)

            GPIO.setup(self.hall_E, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(self.hall_D, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

            self.last_hall_E_state = GPIO.input(self.hall_E)
            self.last_hall_D_state = GPIO.input(self.hall_D)

            self.pwm_D = GPIO.PWM(self.speed_D, 20)
            self.pwm_E = GPIO.PWM(self.speed_E, 20)
            self.pwm_D.start(0)
            self.pwm_E.start(0)

            monitor_thread = threading.Thread(target=self._hall_sensor_monitor_thread, daemon=True)
            monitor_thread.start()

            pid_control_thread = threading.Thread(target=self._pid_control_loop, daemon=True)
            pid_control_thread.start()

            GPIO.output(self.break_D, GPIO.HIGH)
            GPIO.output(self.break_E, GPIO.HIGH)
        else:
            logger.info("Controlador de motores: MODO SIMULADO.")

        # Lidar C1: parada automática quando obstáculo < LIDAR_OBSTACLE_MIN_DISTANCE (Etapa 3)
        self.lidar_reader = None
        self._last_obstacle_detected_at: float = 0.0  # Timestamp da última detecção (para blocking "sticky")
        self._last_lidar_diag_log_time: float = 0.0  # Throttle para log diagnóstico (a cada 2 s quando em movimento)
        if GPIO_AVAILABLE and LIDAR_C1_ENABLED:
            try:
                from src.core.lidar_c1_reader import LidarC1Reader
                self.lidar_reader = LidarC1Reader(min_stop_m=LIDAR_OBSTACLE_MIN_DISTANCE)
                self.lidar_reader.start()
            except Exception as e:
                logger.warning("Lidar C1 não disponível: %s. Parada por obstáculo desativada.", e)
                self.lidar_reader = None

    def _hall_sensor_monitor_thread(self):
        """Thread de polling dos sensores Hall."""
        if not GPIO_AVAILABLE or not GPIO:
            return

        debug_counter = 0
        last_debug_time = time.time()

        while not self.shutdown_event.is_set():
            try:
                current_state_E = GPIO.input(self.hall_E)
                if current_state_E == 1 and self.last_hall_E_state == 0:
                    debounce_time = 0.002 if self.precise_rotation_mode else 0.01
                    time.sleep(debounce_time)
                    if GPIO.input(self.hall_E) == 1:
                        with self.ticks_lock:
                            self.left_hall_ticks += 1
                            self.left_ticks_for_odometry += 1
                self.last_hall_E_state = current_state_E

                current_state_D = GPIO.input(self.hall_D)
                if current_state_D == 1 and self.last_hall_D_state == 0:
                    debounce_time = 0.002 if self.precise_rotation_mode else 0.01
                    time.sleep(debounce_time)
                    if GPIO.input(self.hall_D) == 1:
                        with self.ticks_lock:
                            self.right_hall_ticks += 1
                            self.right_ticks_for_odometry += 1
                self.last_hall_D_state = current_state_D

            except RuntimeError:
                break

            # Log de encoder a cada ~5s para diagnóstico (somente em DEBUG)
            debug_counter += 1
            if debug_counter >= 1000:
                current_time = time.time()
                if current_time - last_debug_time > 5.0:
                    with self.ticks_lock:
                        logger.debug(
                            "Encoder: L=%d ticks, R=%d ticks | Estados: L=%s, R=%s",
                            self.left_hall_ticks, self.right_hall_ticks,
                            current_state_E, current_state_D
                        )
                    last_debug_time = current_time
                debug_counter = 0

            time.sleep(0.001)  # Poll ~1000 Hz

    def _pid_control_loop(self):
        """Thread de controle PID contínuo."""
        if not GPIO_AVAILABLE:
            return

        while not self.shutdown_event.is_set():
            if not self.pid_enabled:
                time.sleep(0.1)
                continue

            self._update_current_speed()

            left_power = self.pid_left.update(self.current_left_tps)
            right_power = self.pid_right.update(self.current_right_tps)

            if self.safety_monitor_enabled:
                self._safety_power_check(left_power, right_power)

            current_time = time.time()
            if current_time - self.last_emit_time > self.emit_interval:
                combined_data = {
                    'left': {'setpoint': self.pid_left.setpoint, 'real_speed': self.current_left_tps, 'output': left_power},
                    'right': {'setpoint': self.pid_right.setpoint, 'real_speed': self.current_right_tps, 'output': right_power}
                }
                self.pid_data_updated.emit(combined_data)
                self.last_emit_time = current_time

            if GPIO_AVAILABLE and GPIO:
                if left_power >= 0:
                    GPIO.output(self.dir_E, GPIO.HIGH)
                else:
                    GPIO.output(self.dir_E, GPIO.LOW)
                self.pwm_E.ChangeDutyCycle(min(abs(left_power), 100))

                # Motor direito tem lógica de direção invertida por design físico
                if right_power >= 0:
                    GPIO.output(self.dir_D, GPIO.LOW)
                else:
                    GPIO.output(self.dir_D, GPIO.HIGH)
                self.pwm_D.ChangeDutyCycle(min(abs(right_power), 100))

                if abs(left_power) > 0.1 or abs(right_power) > 0.1:
                    GPIO.output(self.break_E, GPIO.LOW)
                    GPIO.output(self.break_D, GPIO.LOW)
                else:
                    GPIO.output(self.break_E, GPIO.HIGH)
                    GPIO.output(self.break_D, GPIO.HIGH)

            time.sleep(0.1)  # 10 Hz

    def _update_current_speed(self):
        """Calcula e atualiza a velocidade instantânea (ticks/s) para uso no PID."""
        current_time = time.time()
        delta_time = current_time - self.last_speed_check_time

        if delta_time > 0.1:
            with self.ticks_lock:
                self.current_left_tps = self.left_hall_ticks / delta_time
                self.current_right_tps = self.right_hall_ticks / delta_time

                if self.left_hall_ticks > 0 or self.right_hall_ticks > 0:
                    logger.debug(
                        "Speed update: L=%d ticks, R=%d ticks em %.3fs → L=%.1f tps, R=%.1f tps",
                        self.left_hall_ticks, self.right_hall_ticks,
                        delta_time, self.current_left_tps, self.current_right_tps
                    )

                self.left_hall_ticks = 0
                self.right_hall_ticks = 0

            self.last_speed_check_time = current_time

    def set_target_speed(self, left_tps: float, right_tps: float):
        """
        Define a velocidade alvo para o controle PID em ticks por segundo (tps).
        Aplica correção de deriva lateral baseada em calibração.
        Se Lidar C1 detectar obstáculo < limite, força velocidade 0 (parada automática).
        """
        # Diagnóstico: a cada 2 s quando movendo, logar distância frontal (antes de potential overwrite)
        if self.lidar_reader and (left_tps != 0 or right_tps != 0):
            t = time.time()
            if t - getattr(self, '_last_lidar_diag_log_time', 0) >= 2.0:
                self._last_lidar_diag_log_time = t
                d = self.lidar_reader.obstacle_distance()
                d_str = f"{d:.2f}" if d != float("inf") else "livre"
                logger.info("Lidar C1 diagnóstico: distância frontal = %s m (parar se < %.2f m)", d_str, LIDAR_OBSTACLE_MIN_DISTANCE)

        if self.lidar_reader and self.lidar_reader.has_obstacle():
            if left_tps != 0 or right_tps != 0:
                logger.info("Lidar C1: obstáculo < %.2f m — parando motores.", LIDAR_OBSTACLE_MIN_DISTANCE)
                self._last_obstacle_detected_at = time.time()
                self.disable_pid_control()  # Parada imediata com freio (não esperar PID)
            left_tps = 0.0
            right_tps = 0.0

        left_tps_corrected = left_tps * LEFT_MOTOR_CORRECTION_FACTOR
        right_tps_corrected = right_tps * RIGHT_MOTOR_CORRECTION_FACTOR

        logger.debug(
            "set_target_speed: L=%.1f→%.1f, R=%.1f→%.1f (fatores E=%.4f D=%.4f)",
            left_tps, left_tps_corrected, right_tps, right_tps_corrected,
            LEFT_MOTOR_CORRECTION_FACTOR, RIGHT_MOTOR_CORRECTION_FACTOR
        )

        if not self.pid_enabled:
            self.enable_pid_control()

        self.pid_left.set_setpoint(left_tps_corrected)
        self.pid_right.set_setpoint(right_tps_corrected)

        if not GPIO_AVAILABLE:
            self.simulated_left_tps = left_tps_corrected
            self.simulated_right_tps = right_tps_corrected

    def is_lidar_blocking_or_recent(self, window_sec: float = 5.0) -> bool:
        """
        Retorna True se Lidar está bloqueando AGORA ou bloqueou recentemente (janela em segundos).
        Usado pelo navegador para não declarar chegada por timeout quando obstáculo parou o robô.
        """
        if not self.lidar_reader:
            return False
        if self.lidar_reader.has_obstacle():
            return True
        if self._last_obstacle_detected_at > 0 and (time.time() - self._last_obstacle_detected_at) < window_sec:
            return True
        return False

    def _initialize_pid_controllers(self):
        """Inicializa os controladores PID com o perfil atual."""
        profile = PID_PROFILES[self.current_speed_profile]

        self.pid_left = PIDController(
            Kp=profile['Kp'],
            Ki=profile['Ki'],
            Kd=profile['Kd'],
            setpoint=0,
            output_limits=profile['output_limits']
        )
        self.pid_right = PIDController(
            Kp=profile['Kp'],
            Ki=profile['Ki'],
            Kd=profile['Kd'],
            setpoint=0,
            output_limits=profile['output_limits']
        )

        logger.debug(
            "PID perfil '%s': Kp=%.2f Ki=%.2f Kd=%.2f limites=%s tps=%s",
            self.current_speed_profile, profile['Kp'], profile['Ki'], profile['Kd'],
            profile['output_limits'], profile['tps']
        )

    def set_speed_profile(self, profile_name: str):
        """Altera o perfil de velocidade (slow/normal/fast) com PID otimizado."""
        if profile_name not in PID_PROFILES:
            logger.error("Perfil '%s' não existe. Usando 'normal'.", profile_name)
            profile_name = 'normal'

        if profile_name != self.current_speed_profile:
            self.current_speed_profile = profile_name
            self._initialize_pid_controllers()
            profile = PID_PROFILES[profile_name]
            logger.info("Perfil de velocidade alterado para '%s': %s", profile_name, profile['description'])
            return True
        return False

    def get_current_speed_profile(self) -> dict:
        """Retorna informações do perfil de velocidade atual."""
        profile = PID_PROFILES[self.current_speed_profile]
        return {
            'name': self.current_speed_profile,
            'tps': profile['tps'],
            'description': profile['description'],
            'gains': {'Kp': profile['Kp'], 'Ki': profile['Ki'], 'Kd': profile['Kd']},
            'limits': profile['output_limits']
        }

    def set_pid_gains(self, side, Kp, Ki, Kd):
        """Atualiza os ganhos do PID para um dos motores."""
        if side == 'left':
            self.pid_left.set_gains(Kp, Ki, Kd)
            logger.debug("PID left: Kp=%.2f Ki=%.2f Kd=%.2f", Kp, Ki, Kd)
        elif side == 'right':
            self.pid_right.set_gains(Kp, Ki, Kd)
            logger.debug("PID right: Kp=%.2f Ki=%.2f Kd=%.2f", Kp, Ki, Kd)

    def enable_pid_control(self):
        """Ativa o loop de controle PID."""
        logger.debug("Controle PID ativado.")
        self.pid_enabled = True

    def disable_pid_control(self):
        """Desativa o loop de controle PID e reseta os controladores."""
        logger.debug("Controle PID desativado.")
        self.pid_enabled = False
        if GPIO_AVAILABLE and GPIO:
            self.pwm_E.ChangeDutyCycle(0)
            self.pwm_D.ChangeDutyCycle(0)
            GPIO.output(self.break_E, GPIO.HIGH)
            GPIO.output(self.break_D, GPIO.HIGH)
        self.pid_left.reset()
        self.pid_right.reset()

    def set_speed(self, left_speed: float, right_speed: float):
        """
        Método de compatibilidade: converte porcentagem de velocidade para TPS e usa PID.
        Se zero, para os motores.
        """
        logger.debug("set_speed: L=%.1f%% R=%.1f%%", left_speed, right_speed)
        if left_speed == 0 and right_speed == 0:
            self.stop_motors()
        else:
            left_tps = (left_speed / 100.0) * MANUAL_CONTROL_MAX_TPS
            right_tps = (right_speed / 100.0) * MANUAL_CONTROL_MAX_TPS
            self.set_target_speed(left_tps, right_tps)

    def _set_motor_speed_real(self, motor: str, speed_percent: float):
        """Controla um motor específico via GPIO."""
        if not GPIO_AVAILABLE or not GPIO:
            return

        if motor == "left":
            pwm = self.pwm_E
            pin_dir = self.dir_E
            pin_break = self.break_E
        elif motor == "right":
            pwm = self.pwm_D
            pin_dir = self.dir_D
            pin_break = self.break_D
        else:
            return

        if abs(speed_percent) < 1:
            pwm.ChangeDutyCycle(0)
            GPIO.output(pin_break, GPIO.HIGH)
            return

        GPIO.output(pin_break, GPIO.LOW)

        if speed_percent > 0:
            # Esquerda: HIGH=frente / Direita: LOW=frente (design físico)
            direction = GPIO.HIGH if motor == "left" else GPIO.LOW
        else:
            direction = GPIO.LOW if motor == "left" else GPIO.HIGH

        GPIO.output(pin_dir, direction)
        pwm.ChangeDutyCycle(abs(speed_percent))

    def _simulate_movement(self):
        """Simula o movimento do robô para depuração sem hardware."""
        self.is_moving = self.left_speed_percent != 0 or self.right_speed_percent != 0

    def get_and_reset_ticks(self) -> dict:
        """
        Retorna os ticks acumulados e os zera (coração da odometria).
        - Em modo real: aplica sinal com base na direção do setpoint do PID.
        - Em giros precisos: usa direção forçada manualmente.
        - Em modo simulado: calcula ticks pela velocidade alvo e tempo.
        """
        if GPIO_AVAILABLE:
            with self.ticks_lock:
                if self.precise_rotation_left_direction is not None and self.precise_rotation_right_direction is not None:
                    left_direction = self.precise_rotation_left_direction
                    right_direction = self.precise_rotation_right_direction
                else:
                    left_direction = 1 if self.pid_left.setpoint >= 0 else -1
                    right_direction = 1 if self.pid_right.setpoint >= 0 else -1

                ticks_to_return = {
                    "left": self.left_ticks_for_odometry * left_direction,
                    "right": self.right_ticks_for_odometry * right_direction
                }
                self.left_ticks_for_odometry = 0
                self.right_ticks_for_odometry = 0
            return ticks_to_return
        else:
            current_time = time.time()
            delta_t = current_time - self.last_sim_time
            simulated_left_ticks = self.simulated_left_tps * delta_t
            simulated_right_ticks = self.simulated_right_tps * delta_t
            self.last_sim_time = current_time
            return {
                "left": simulated_left_ticks,
                "right": simulated_right_ticks
            }

    def get_real_time_speed(self) -> dict:
        """Retorna a velocidade em tempo real (TPS) de cada motor."""
        return {"left": self.current_left_tps, "right": self.current_right_tps}

    def stop(self):
        """Para os motores usando o sistema PID."""
        self.stop_motors()

    def stop_motors(self):
        """Para ambos os motores e o controle PID de forma segura."""
        self.set_target_speed(0, 0)
        self.disable_pid_control()

    def set_precise_rotation_direction(self, left_direction: int, right_direction: int):
        """
        Define a direção dos ticks durante giros precisos.
        Args:
            left_direction: -1 (trás) ou +1 (frente) para motor esquerdo
            right_direction: -1 (trás) ou +1 (frente) para motor direito
        """
        self.precise_rotation_left_direction = left_direction
        self.precise_rotation_right_direction = right_direction
        self.precise_rotation_mode = True

    def clear_precise_rotation_direction(self):
        """Limpa a direção forçada, voltando ao modo normal (PID setpoint)."""
        self.precise_rotation_left_direction = None
        self.precise_rotation_right_direction = None
        self.precise_rotation_mode = False

    def _safety_power_check(self, left_power: float, right_power: float):
        """Verifica se a potência está dentro dos limites seguros (≤15%)."""
        current_time = time.time()

        if current_time - self.last_safety_check < SAFETY_POWER_MONITOR_INTERVAL:
            return

        self.last_safety_check = current_time
        max_power = max(abs(left_power), abs(right_power))

        if max_power > SAFETY_MAX_MOTOR_POWER_PERCENT:
            if self.power_violation_start_time is None:
                self.power_violation_start_time = current_time
                logger.warning(
                    "SEGURANÇA: Potência %.1f%% excede limite de %.1f%%",
                    max_power, SAFETY_MAX_MOTOR_POWER_PERCENT
                )
            elif (current_time - self.power_violation_start_time) > SAFETY_POWER_VIOLATION_TIMEOUT:
                logger.error(
                    "PARADA DE EMERGÊNCIA: Potência %.1f%% acima do limite por %.1fs! Reduzindo para perfil 'slow'.",
                    max_power, SAFETY_POWER_VIOLATION_TIMEOUT
                )
                self.stop_motors()
                self.set_speed_profile('slow')
                self.power_violation_start_time = None
        else:
            if self.power_violation_start_time is not None:
                self.power_violation_start_time = None

    def get_safety_status(self) -> dict:
        """Retorna o status atual do sistema de segurança."""
        return {
            'monitor_enabled': self.safety_monitor_enabled,
            'max_power_limit': SAFETY_MAX_MOTOR_POWER_PERCENT,
            'current_profile': self.current_speed_profile,
            'violation_active': self.power_violation_start_time is not None,
            'violation_duration': (time.time() - self.power_violation_start_time) if self.power_violation_start_time else 0
        }

    def cleanup(self):
        """Limpa os recursos do GPIO de forma segura."""
        if self.lidar_reader:
            try:
                self.lidar_reader.stop()
            except Exception as e:
                logger.warning("Erro ao parar Lidar C1: %s", e)
            self.lidar_reader = None
        if GPIO_AVAILABLE and GPIO:
            logger.info("Iniciando limpeza dos recursos do RobotMotorController...")
            self.shutdown_event.set()
            time.sleep(0.1)
            self.stop()
            GPIO.cleanup()
            logger.info("Limpeza do GPIO concluída.")
