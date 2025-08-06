import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import time
import math
from typing import List, Tuple, Optional
from PyQt5.QtCore import QObject, pyqtSignal
from .slamtec_manager import SlamtecManager
from .robot_motor_controller import RobotMotorController
from .config import *
from src.core.environment import GPIO_AVAILABLE, is_raspberry_pi
from .path_finder import PathFinder

class RobotNavigator(QObject):

    # Sinal para notificar a UI sobre a atualização da posição e ângulo do robô
    position_updated = pyqtSignal(float, float, float)
    # Sinal para notificar a UI sobre a atualização do estado da navegação
    navigation_status_updated = pyqtSignal(dict)
    # Sinal para notificar a UI quando a navegação for finalizada ou interrompida
    navigation_completed = pyqtSignal(str)


    def __init__(self):
        """Inicializa o navegador do robô."""
        super().__init__()  # Essencial para inicializar o QObject
        self.slamtec = SlamtecManager()
        self.motors = RobotMotorController()
        
        print("DEBUG: Inicializando RobotNavigator...")
        print(f"DEBUG: ROBOT_INITIAL_POSITION configurado como: {ROBOT_INITIAL_POSITION}")
        print(f"DEBUG: ROBOT_INITIAL_ANGLE configurado como: {ROBOT_INITIAL_ANGLE}°")
        
        self.current_position = ROBOT_INITIAL_POSITION
        self.current_angle = ROBOT_INITIAL_ANGLE
        self.current_target = None
        self.navigation_active = False
        self.is_returning_to_base = False
        self.base_position = ROBOT_INITIAL_POSITION
        self.is_adjusting_final_angle = False
        self.navigation_state = "IDLE"  # IDLE, NAVIGATING, RETURNING, COMPLETED
        self.speed_multiplier = 1.0  # Fator de velocidade inicial (100%)
        
        # Inicializa o PathFinder com as dimensões do mapa do config e grid size consistente
        self.path_finder = PathFinder(
            width=int(MAP_WIDTH / MAP_GRID_SIZE),
            height=int(MAP_HEIGHT / MAP_GRID_SIZE),
            grid_size=MAP_GRID_SIZE
        )
        
        self.forbidden_areas = []
        self.is_autonomous = False
        self.current_path = []
        self.current_path_index = 0
        
        # Novos atributos para navegação melhorada
        self.path_smoothing_enabled = True
        self.obstacle_avoidance_enabled = True
        self.emergency_stop_active = False
        self.last_position_update = time.time()
        self.navigation_start_time = None
        self.estimated_completion_time = None
        
        # Atributos para precisão na chegada
        self.arrival_pause_time = 2.0  # segundos de pausa ao chegar no destino
        self.arrival_time = None
        self.is_paused_at_destination = False
        
        self.is_returning_to_initial_angle = False  # Nova flag para controle do retorno ao ângulo inicial
        
        # NOVO: Atributo para controlar o tipo de navegação
        self.should_return_to_base = True  # True = ida e volta, False = apenas ao destino
        
        # Sistema de timeout para evitar travamento na aproximação final
        self.final_approach_start_time = None
        self.final_approach_timeout = 25.0  # Aumentado de 15s para 25s para dar mais tempo ao PID
        
        print(f"DEBUG: Posição inicial definida: {self.current_position}")
        print(f"DEBUG: Ângulo inicial definido: {self.current_angle}°")
        print(f"DEBUG: Base position definida: {self.base_position}")
        print(f"DEBUG: ROBOT_INITIAL_ANGLE importado: {ROBOT_INITIAL_ANGLE}°")
        print(f"DEBUG: ROBOT_INITIAL_POSITION importado: {ROBOT_INITIAL_POSITION}")
        
        print(f"DEBUG: Área proibida configurada no navegador")
        
    def reset_to_initial_state(self):
        """Reseta o robô para o estado inicial"""
        print("🔄 ===== RESETANDO ROBÔ PARA ESTADO INICIAL =====")
        print(f"🔄 Posição alvo: {ROBOT_INITIAL_POSITION}, ângulo alvo: {ROBOT_INITIAL_ANGLE}°")
        print(f"🔄 Estado anterior - navigation_active: {self.navigation_active}")
        print(f"🔄 Estado anterior - is_returning_to_base: {self.is_returning_to_base}")
        print(f"🔄 Estado anterior - navigation_state: {self.navigation_state}")
        
        # Preserva as áreas proibidas durante o reset
        preserved_forbidden_areas = self.forbidden_areas.copy()
        
        # ETAPA 2: Correção do "Pulo" - NÃO reseta a posição/ângulo.
        # A nova navegação deve começar da posição final real da navegação anterior.
        # self.current_position = ROBOT_INITIAL_POSITION
        # self.current_angle = ROBOT_INITIAL_ANGLE
        
        # Reseta variáveis de navegação
        self.navigation_active = False
        self.current_target = None
        self.path = []
        self.path_index = 0
        self.is_adjusting_final_angle = False
        self.is_returning_to_base = False  # RESETA ESTE VALOR
        self.navigation_state = "IDLE"
        self.progress = 0.0
        self.start_time = None
        self.estimated_time_remaining = 0.0
        self.is_paused_at_destination = False
        
        # Reset de variáveis específicas
        if hasattr(self, 'original_destination'):
            delattr(self, 'original_destination')
        self.final_approach_start_time = None
        
        # Restaura as áreas proibidas
        self.forbidden_areas = preserved_forbidden_areas
        self.path_finder.set_forbidden_areas(preserved_forbidden_areas)
        
        # Para os motores
        self.motors.stop()
        
        print("✅ ===== RESET CONCLUÍDO =====")
        print(f"✅ Posição resetada: {self.current_position}, Ângulo: {self.current_angle}°")
        print(f"✅ navigation_active: {self.navigation_active}")
        print(f"✅ is_returning_to_base: {self.is_returning_to_base}")
        print(f"✅ navigation_state: {self.navigation_state}")
        print(f"✅ Áreas proibidas preservadas: {len(self.forbidden_areas)}")
        print("=" * 60)
        
    def set_speed_multiplier(self, multiplier: float):
        """
        Define o multiplicador de velocidade para a navegação.
        
        Args:
            multiplier: Fator a ser multiplicado pela velocidade base (ex: 1.0, 1.5, 2.0).
        """
        if 1.0 <= multiplier <= 2.0:
            self.speed_multiplier = multiplier
            print(f"Velocidade ajustada para {self.speed_multiplier * 100:.0f}%")
        else:
            print(f"AVISO: Tentativa de definir multiplicador de velocidade inválido: {multiplier}. Deve ser entre 1.0 e 2.0.")

    def set_path(self, path: List[Tuple[float, float]]):
        """
        Define um novo caminho para o robô seguir.
        
        Args:
            path: Lista de pontos (x, y) que formam o caminho
        """
        self.current_path = self._smooth_path(path) if self.path_smoothing_enabled else path
        self.current_path_index = 0
        print(f"DEBUG: Caminho definido com {len(self.current_path)} pontos")
        
    def _smooth_path(self, path: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Suaviza o caminho para movimentos mais naturais"""
        if len(path) < 3:
            return path
            
        smoothed_path = [path[0]]  # Mantém o ponto inicial
        
        for i in range(1, len(path) - 1):
            prev_point = path[i - 1]
            current_point = path[i]
            next_point = path[i + 1]
            
            # Calcula o ponto médio ponderado
            smoothed_x = (prev_point[0] + 2 * current_point[0] + next_point[0]) / 4
            smoothed_y = (prev_point[1] + 2 * current_point[1] + next_point[1]) / 4
            
            smoothed_path.append((smoothed_x, smoothed_y))
            
        smoothed_path.append(path[-1])  # Mantém o ponto final
        return smoothed_path
        
    def update(self):
        """Atualiza o estado do robô usando uma máquina de estados clara."""
        if not self.navigation_active:
            return

        # --- CORREÇÃO DEFINITIVA ---
        # A odometria baseada em ticks agora funciona para hardware real E para simulação.
        # Removemos a condição `if GPIO_AVAILABLE` para que a posição seja sempre
        # atualizada com base nos ticks (reais ou simulados).
        self._update_pose_with_odometry()

        # --- Máquina de Estados de Navegação ---

        if self.navigation_state == "IDLE":
            # Não faz nada, aguardando comando
            return

        elif self.navigation_state == "NAVIGATING_TO_DESTINATION":
            print("DEBUG: update() - Estado: NAVIGATING_TO_DESTINATION")
            
            if self.current_target is None or self.current_position is None:
                print("DEBUG: ERRO - Alvo ou posição atual nulos em NAVIGATING_TO_DESTINATION")
                self._finalize_navigation()
                return

            # Verifica se está no ponto anterior ao destino final
            is_near_final_destination_waypoint = (self.path_index == self.destination_index - 1)
            
            distance_to_target = self._calculate_distance(self.current_position, self.current_target)

            # Se chegou ao waypoint anterior ao destino, muda para aproximação final
            if is_near_final_destination_waypoint and distance_to_target < 0.15: # 15cm
                print("🔄 MUDANÇA DE FASE: NAVIGATING_TO_DESTINATION → FINAL_APPROACH_DESTINATION")
                self.navigation_state = "FINAL_APPROACH_DESTINATION"
                # O alvo da aproximação final é sempre o 'original_destination'
                self.current_target = self.original_destination
                return

            # Se chegou a um waypoint intermediário (que não é o pré-destino)
            if distance_to_target < 0.12: # 12cm para pontos intermediários
                print(f"DEBUG: Chegou ao ponto intermediário {self.path_index}: {self.current_target}")
                self.path_index += 1
                if self.path_index < len(self.path):
                    self.current_target = self.path[self.path_index]
                    print(f"DEBUG: Próximo alvo: {self.current_target}")
                else:
                    print("DEBUG: ERRO - Fim do caminho alcançado inesperadamente.")
                    self._finalize_navigation()
                return
            
            # Se não chegou, continua se movendo
            self._move_towards_target()

        elif self.navigation_state == "FINAL_APPROACH_DESTINATION":
            print("DEBUG: update() - Estado: FINAL_APPROACH_DESTINATION")
            # _stable_final_approach gerencia seu próprio movimento
            if self._stable_final_approach(self.original_destination):
                # Chegou ao destino com sucesso
                print("🔄 MUDANÇA DE FASE: FINAL_APPROACH_DESTINATION → PAUSED_AT_DESTINATION")
                self.motors.stop()
                self.navigation_state = "PAUSED_AT_DESTINATION"
                self.arrival_time = time.time()
                self.is_paused_at_destination = True
        
        elif self.navigation_state == "PAUSED_AT_DESTINATION":
            print("DEBUG: update() - Estado: PAUSED_AT_DESTINATION")
            if self.arrival_time is not None and (time.time() - self.arrival_time > self.arrival_pause_time):
                self.is_paused_at_destination = False
                
                # NOVA LÓGICA: Verifica se deve retornar à base ou finalizar
                if self.should_return_to_base:
                    print("DEBUG: Navegação completa - Calculando ângulo para retornar à base...")
                    self._calculate_and_execute_return_angle()
                else:
                    print("DEBUG: Navegação apenas ao destino - Finalizando navegação")
                    self._finalize_navigation()
                return

        elif self.navigation_state == "RETURNING_TO_BASE":
            print("DEBUG: update() - Estado: RETURNING_TO_BASE")
            if self.current_target is None or self.current_position is None or not self.path:
                print("DEBUG: ERRO - Estado inválido em RETURNING_TO_BASE")
                self._finalize_navigation()
                return

            # Verifica se está no ponto ANTERIOR à base
            is_near_base_waypoint = (self.path_index == len(self.path) - 2)
            distance_to_target = self._calculate_distance(self.current_position, self.current_target)
            
            # Se chegou ao penúltimo ponto, muda para o estado de aproximação final da base
            if is_near_base_waypoint and distance_to_target < 0.15:
                print("🔄 MUDANÇA DE FASE: RETURNING_TO_BASE → FINAL_APPROACH_BASE")
                self.navigation_state = "FINAL_APPROACH_BASE"
                self.current_target = self.path[-1]  # O alvo agora é o último ponto (base)
                # Zera o timeout da aproximação final para a base
                self.final_approach_start_time = None 
                return

            # Lógica para pontos intermediários do caminho de volta
            if distance_to_target < NAVIGATION_GOAL_TOLERANCE:
                self.path_index += 1
                if self.path_index < len(self.path):
                    self.current_target = self.path[self.path_index]
                    print(f"DEBUG: Próximo alvo do retorno: {self.current_target}")
                else:
                    print("DEBUG: ERRO - Fim inesperado do caminho em RETURNING_TO_BASE")
                    self._start_final_angle_adjustment()
                return
            
            self._move_towards_target()

        elif self.navigation_state == "FINAL_APPROACH_BASE":
            print("DEBUG: update() - Estado: FINAL_APPROACH_BASE")
            # Usa a aproximação lenta, tendo como alvo o último ponto do caminho
            if self._stable_final_approach(self.path[-1]):
                print("🏁 FINALIZOU FASE: Chegou na BASE")
                self._start_final_angle_adjustment()
                return

        elif self.navigation_state == "TURNING_TO_RETURN":
            # Executa o giro para retornar à base
            self._execute_return_turn()
            
        elif self.navigation_state == "ADJUSTING_FINAL_ANGLE":
            # A função _adjust_final_angle gerencia o estado e a finalização
            self._adjust_final_angle()

        # Atualiza o progresso para a UI
        if len(self.path) > 1:
            self.progress = self.path_index / (len(self.path) - 1)
        else:
            self.progress = 0.0

    def _finalize_navigation(self):
        """Finaliza completamente a navegação"""
        print("DEBUG: === FINALIZANDO NAVEGAÇÃO ===")
        self.motors.stop()
        self.navigation_active = False
        self.is_adjusting_final_angle = False
        self.navigation_state = "COMPLETED"
        self.current_target = None
        self.path = []
        self.path_index = 0
        print("DEBUG: === NAVEGAÇÃO FINALIZADA ===")
        
    def _calculate_and_execute_return_angle(self):
        """Calcula o ângulo necessário para retornar à base e inicia o giro"""
        print("DEBUG: === CALCULANDO ÂNGULO DE RETORNO ===")
        
        # Calcula o ângulo para a base
        dx = self.base_position[0] - self.current_position[0]
        dy = self.base_position[1] - self.current_position[1]
        target_angle = math.degrees(math.atan2(dy, dx))
        
        # Calcula a diferença de ângulo
        angle_diff = (target_angle - self.current_angle + 180) % 360 - 180
        
        print(f"DEBUG: Posição atual: {self.current_position}")
        print(f"DEBUG: Posição da base: {self.base_position}")
        print(f"DEBUG: Ângulo atual: {self.current_angle:.2f}°")
        print(f"DEBUG: Ângulo para base: {target_angle:.2f}°")
        print(f"DEBUG: Diferença calculada: {angle_diff:.2f}°")
        
        # Se a diferença for pequena, vai direto para o retorno
        if abs(angle_diff) < 5.0:
            print("DEBUG: Ângulo já está correto, iniciando retorno direto")
            self._start_return_navigation()
            return
            
        # Armazena o ângulo alvo para o giro
        self.return_target_angle = target_angle
        self.return_angle_diff = angle_diff
        
        # Inicia o estado de giro
        print("🔄 MUDANÇA DE FASE: PAUSED_AT_DESTINATION → TURNING_TO_RETURN")
        self.navigation_state = "TURNING_TO_RETURN"
        self.turn_start_time = time.time()
        
    def _execute_return_turn(self):
        """Executa o giro para retornar à base"""
        print(f"DEBUG: === EXECUTANDO GIRO DE RETORNO ===")
        print(f"DEBUG: Ângulo atual: {self.current_angle:.2f}°")
        print(f"DEBUG: Ângulo alvo: {self.return_target_angle:.2f}°")
        print(f"DEBUG: Diferença restante: {self.return_angle_diff:.2f}°")
        
        # Verifica timeout (10 segundos)
        if time.time() - self.turn_start_time > 10.0:
            print("DEBUG: TIMEOUT no giro de retorno, forçando continuação")
            self._start_return_navigation()
            return
            
        # Calcula a diferença atual
        current_diff = (self.return_target_angle - self.current_angle + 180) % 360 - 180
        
        # Se chegou próximo do ângulo alvo, inicia o retorno
        if abs(current_diff) < 5.0:
            print("DEBUG: Giro de retorno concluído, iniciando navegação de retorno")
            self._start_return_navigation()
            return
            
        # Executa o giro
        if abs(current_diff) > 30:
            turn_value = 0.08  # 8% para diferenças grandes
        elif abs(current_diff) > 10:
            turn_value = 0.06  # 6% para diferenças moderadas
        else:
            turn_value = 0.04  # 4% para ajustes finos
            
        # LÓGICA ORIGINAL RESTAURADA - Hardware está correto conforme teste físico
        if current_diff > 0:
            # Precisa girar no sentido horário
            left_speed = -turn_value * 100
            right_speed = turn_value * 100
            direction = "horário"
        else:
            # Precisa girar no sentido anti-horário
            left_speed = turn_value * 100
            right_speed = -turn_value * 100
            direction = "anti-horário"
            
        print(f"DEBUG: Comando de giro: {turn_value:.3f} - {direction}")
        print(f"DEBUG: Velocidades: L:{left_speed:.1f}% R:{right_speed:.1f}%")
        
        # Aplica o comando de giro ORIGINAL (sem inversão)
        print(f"DEBUG GIRO: COMANDO ORIGINAL RESTAURADO - Hardware testado e correto")
        self.motors.set_speed(left_speed, right_speed)  # RESTAURADO: lógica original
        
    def _start_return_navigation(self):
        """Inicia a navegação de retorno à base"""
        print("DEBUG: === INICIANDO NAVEGAÇÃO DE RETORNO DIRETO ===")
        
        # NOVA LÓGICA: Retorno direto à base sem waypoints intermediários
        # Isso força o robô a ir direto para a base, fazendo o giro de 180° necessário
        
        # Cria um caminho direto: posição atual -> base
        direct_path = [self.current_position, self.base_position]
        
        # Substitui o caminho atual pelo caminho direto
        self.path = direct_path
        self.path_index = 0
        self.current_target = self.path[1]  # O alvo é a base
        
        print(f"DEBUG: Caminho direto criado: {self.current_position} -> {self.base_position}")
        print("🔄 MUDANÇA DE FASE: TURNING_TO_RETURN → RETURNING_TO_BASE")
        self.navigation_state = "RETURNING_TO_BASE"
        self.is_returning_to_base = True
        
    def _start_final_angle_adjustment(self):
        """Inicia o ajuste do ângulo final"""
        print("DEBUG: === INICIANDO AJUSTE DE ÂNGULO FINAL ===")
        print(f"DEBUG: Destino original preservado: {getattr(self, 'original_destination', 'NÃO DEFINIDO')}")
        self.motors.stop()
        self.navigation_state = "ADJUSTING_FINAL_ANGLE"
        self.is_adjusting_final_angle = True
        self.current_target = None
        # NÃO limpa o path para preservar informações de debug
        # self.path = []  # <- REMOVIDO para preservar o destino original
        self.path_index = len(self.path)  # Marca como final do caminho
        
        # Inicia o ajuste de ângulo
        self._adjust_final_angle()
        
    def get_current_path(self) -> List[Tuple[float, float]]:
        """Retorna o caminho de navegação atual."""
        return self.path
        
    def _check_emergency_obstacles(self) -> bool:
        """Verifica se há obstáculos que requerem parada de emergência"""
        # Simulação de detecção de obstáculos próximos
        # Em um sistema real, isso viria dos sensores LIDAR
        current_time = time.time()
        
        # Simula detecção de obstáculos a cada 0.5 segundos
        if current_time - self.last_position_update > 0.5:
            # Verifica se há áreas proibidas muito próximas
            for area in self.forbidden_areas:
                if self._is_near_forbidden_area(area):
                    print("DEBUG: Área proibida detectada próxima - parada de emergência")
                    return True
                    
            self.last_position_update = current_time
            
        return False
        
    def _is_near_forbidden_area(self, area: List[Tuple[float, float]]) -> bool:
        """Verifica se o robô está muito próximo de uma área proibida"""
        # Calcula a distância mínima até a área proibida
        min_distance = float('inf')
        
        for i in range(len(area)):
            point1 = area[i]
            point2 = area[(i + 1) % len(area)]
            
            # Calcula a distância até o segmento de linha
            distance = self._distance_to_line_segment(point1, point2, self.current_position)
            min_distance = min(min_distance, distance)
            
        return min_distance < EMERGENCY_STOP_DISTANCE
        
    def _distance_to_line_segment(self, p1: Tuple[float, float], p2: Tuple[float, float], 
                                 point: Tuple[float, float]) -> float:
        """Calcula a distância de um ponto até um segmento de linha"""
        x, y = point
        x1, y1 = p1
        x2, y2 = p2
        
        # Calcula a distância até a linha infinita
        A = x - x1
        B = y - y1
        C = x2 - x1
        D = y2 - y1
        
        dot = A * C + B * D
        len_sq = C * C + D * D
        
        if len_sq == 0:
            return math.sqrt((x - x1) ** 2 + (y - y1) ** 2)
            
        param = dot / len_sq
        
        if param < 0:
            xx, yy = x1, y1
        elif param > 1:
            xx, yy = x2, y2
        else:
            xx = x1 + param * C
            yy = y1 + param * D
            
        return math.sqrt((x - xx) ** 2 + (y - yy) ** 2)
        
    def _emergency_stop(self):
        """Executa parada de emergência"""
        if not self.emergency_stop_active:
            print("DEBUG: PARADA DE EMERGÊNCIA ATIVADA!")
            self.motors.stop()
            self.emergency_stop_active = True
            self.navigation_state = "EMERGENCY_STOP"
            
        # Aguarda 2 segundos antes de tentar continuar
        if time.time() - self.last_position_update > 2.0:
            print("DEBUG: Tentando retomar navegação após parada de emergência")
            self.emergency_stop_active = False
            self.navigation_state = "NAVIGATING"
            self.last_position_update = time.time()

    def _calculate_movement(self, target: Optional[Tuple[float, float]], angle_error_rad: float) -> Tuple[float, float]:
        """Calcula os valores de movimento baseado no erro angular e distância"""
        if target is None:
            return 0.0, 0.0
            
        distance = self._calculate_distance(self.current_position, target)
        
        # Se a distância for muito pequena, o robô já está no ponto
        if distance < NAVIGATION_GOAL_TOLERANCE:
            forward_value = 0.0
            turn_value = 0.0
            print("DEBUG: Chegou ao destino, forward=0, turn=0")
        else:
            # Normaliza o erro angular para -180 a 180 graus
            angle_error_deg = math.degrees(angle_error_rad)
            if angle_error_deg > 180:
                angle_error_deg -= 360
            elif angle_error_deg < -180:
                angle_error_deg += 360
                
            # Calcula o valor de giro (mais suave)
            turn_value = math.sin(angle_error_rad) * ROBOT_TURN_SPEED
            
            # Velocidade de avanço baseada na distância e erro angular
            forward_value = min(distance * ROBOT_FORWARD_SPEED, ROBOT_MAX_SPEED)
            
            # Reduz a velocidade de avanço quando o erro angular é grande
            angle_factor = math.cos(angle_error_rad)  # 1 quando alinhado, 0 quando perpendicular
            forward_value *= max(0, angle_factor)  # Não permite velocidade negativa
            
            print(f"DEBUG: Distancia: {distance:.2f}m, Erro Angular: {angle_error_deg:.1f}°")
            print(f"DEBUG: Forward: {forward_value:.2f}, Turn: {turn_value:.2f}")
                
        # Converte para velocidades das rodas (limitando a -100 a 100)
        # CORREÇÃO FINAL: Sincroniza com correção da cinemática diferencial
        left_speed = max(-100, min(100, forward_value + turn_value))   # CORRIGIDO: Inverte para sincronizar
        right_speed = max(-100, min(100, forward_value - turn_value))  # CORRIGIDO: Inverte para sincronizar
            
        # Aplica os comandos aos motores
        if hasattr(self, 'motors'):
            # REVERTENDO: Voltando ao normal para evitar feedback loop
            print(f"DEBUG: Velocidades calculadas - ESQ: {left_speed:.2f}, DIR: {right_speed:.2f}")
            
            # VOLTA AO ORIGINAL: sem inversão por enquanto
            self.motors.set_speed(left_speed, right_speed)  # REVERTIDO para original
            print(f"DEBUG: Comandos enviados aos motores - ESQ: {left_speed:.2f}, DIR: {right_speed:.2f}")
            
        return forward_value, turn_value
        
    def _check_obstacles(self, obstacles: dict) -> bool:
        """Verifica se há obstáculos perigosos próximos."""
        if not obstacles or 'obstacles' not in obstacles:
            return False
            
        for obstacle in obstacles['obstacles']:
            x, y, _ = obstacle
            
            # Converte coordenadas do obstáculo para o referencial do robô
            # (apenas para verificação de proximidade, não para navegação)
            dx_world = x - self.current_position[0]
            dy_world = y - self.current_position[1]
            distance = math.sqrt(dx_world*dx_world + dy_world*dy_world)
            
            if distance < EMERGENCY_STOP_DISTANCE:
                print(f"Obstáculo detectado! Distância: {distance:.2f}m")
                return True
        return False
        
    def _update_position(self, forward_value: float, turn_value: float):
        """Atualiza a posição e orientação do robô baseado nos comandos com precisão extrema"""
        old_position = self.current_position
        
        # Atualiza orientação com precisão extrema
        angle_change = turn_value * ROBOT_TURN_SPEED * SIMULATION_TIMESTEP
        old_angle = self.current_angle
        self.current_angle = (self.current_angle + angle_change) % 360
        
        if turn_value != 0.0:
            print(f"DEBUG: _update_position - turn_value: {turn_value:.4f}, angle_change: {angle_change:.4f}°")
            print(f"DEBUG: _update_position - ângulo antigo: {old_angle:.2f}°, novo: {self.current_angle:.2f}°")
        
        # Atualiza posição com precisão extrema
        if forward_value != 0.0:
            distance = forward_value * ROBOT_SPEED * SIMULATION_TIMESTEP
            angle_rad = math.radians(self.current_angle)
            
            # Calcula os deslocamentos separadamente
            delta_x = distance * math.cos(angle_rad)
            delta_y = distance * math.sin(angle_rad)
            
            # Calcula a nova posição com precisão de 4 casas decimais
            new_x = self.current_position[0] + delta_x
            new_y = self.current_position[1] + delta_y
            
            # Debug detalhado do movimento
            print(f"DEBUG: _update_position - forward_value: {forward_value:.4f}")
            print(f"DEBUG: _update_position - distance: {distance:.4f}m")
            print(f"DEBUG: _update_position - angle_rad: {angle_rad:.4f} ({self.current_angle:.2f}°)")
            print(f"DEBUG: _update_position - delta_x: {delta_x:.4f}m, delta_y: {delta_y:.4f}m")
            print(f"DEBUG: _update_position - posição antiga: ({old_position[0]:.4f}, {old_position[1]:.4f})")
            print(f"DEBUG: _update_position - posição nova: ({new_x:.4f}, {new_y:.4f})")
            
            # Arredonda para 4 casas decimais para precisão extrema
            robot_radius = ROBOT_WIDTH / 2.0
            self.current_position = (
                    round(max(robot_radius, min(MAP_WIDTH - robot_radius, new_x)), 4),
                    round(max(robot_radius, min(MAP_HEIGHT - robot_radius, new_y)), 4)
            )
            
            print(f"DEBUG: _update_position - posição final (limitada): ({self.current_position[0]:.4f}, {self.current_position[1]:.4f})")
            
            # Verifica se houve alguma limitação pelos limites do mapa
            if new_x != self.current_position[0] or new_y != self.current_position[1]:
                print(f"DEBUG: ⚠️ Posição limitada pelos limites do mapa!")
                print(f"DEBUG: Limites: X(0-{MAP_WIDTH}), Y(0-{MAP_HEIGHT})")

    def _reached_target(self, target: Tuple[float, float]) -> bool:
        """Verifica se o robô chegou ao ponto alvo."""
        dx = target[0] - self.current_position[0]
        dy = target[1] - self.current_position[1]
        distance = math.sqrt(dx*dx + dy*dy)
        return distance < NAVIGATION_GOAL_TOLERANCE
        
    def toggle_autonomous(self):
        """Alterna entre modo autônomo e manual."""
        self.is_autonomous = not self.is_autonomous
        if not self.is_autonomous:
            self.motors.stop()
            
    def cleanup(self):
        """Limpa recursos."""
        self.motors.cleanup()

    def set_autonomous_mode(self, autonomous):
        """Alterna entre modo autônomo e manual"""
        self.is_autonomous = autonomous
        if not autonomous:
            self.motors.stop()  # Para o robô ao sair do modo autônomo
            
    def move_manual(self, forward_value, turn_value):
        """Controle manual do robô"""
        if self.is_autonomous:
            return  # Ignora comandos manuais em modo autônomo
            
        # Converte valores do joystick (-1 a 1) para velocidades dos motores
        # LÓGICA ORIGINAL - Hardware testado e funciona corretamente
        left_speed = (forward_value - turn_value) * 100
        right_speed = (forward_value + turn_value) * 100
        
        print(f"DEBUG JOYSTICK: COMANDO ORIGINAL RESTAURADO - Hardware testado e correto")
        self.motors.set_speed(left_speed, right_speed)  # RESTAURADO: lógica original
        
    def move_to_point(self, target_point):
        """Move o robô para um ponto específico (modo autônomo)"""
        if not self.is_autonomous:
            return  # Ignora comandos autônomos em modo manual
            
        # TODO: Implementar navegação autônoma
        pass 

    def set_forbidden_areas(self, areas: List[List[Tuple[float, float]]]):
        """Define as áreas proibidas para o navegador"""
        self.forbidden_areas = areas
        self.path_finder.set_forbidden_areas(areas)
        print(f"DEBUG: {len(areas)} áreas proibidas configuradas no navegador")
        
    def navigate_to_and_return(self, destination: Tuple[float, float], base_position: Tuple[float, float]) -> None:
        """Navega até o destino e retorna à base com planejamento otimizado"""
        # SEMPRE usa a posição inicial definida em config.py como base
        self.base_position = ROBOT_INITIAL_POSITION # Garante que a base seja a correta
        print(f"DEBUG: ===== INICIANDO NAVEGAÇÃO =====")
        print(f"DEBUG: Destino: {destination}")
        print(f"DEBUG: Base (config.py): {self.base_position}")
        print(f"DEBUG: Posição atual: {self.current_position}, Ângulo atual: {self.current_angle}°")
        
        # Reset completo para nova navegação (MANTÉM as áreas proibidas)
        self.reset_to_initial_state()
        
        # Configura a navegação
        self.navigation_active = True
        self.start_time = time.time()
        self.navigation_state = "NAVIGATING_TO_DESTINATION"
        self.is_returning_to_base = False
        self.should_return_to_base = True  # PRESERVA: Navegação completa (ida e volta)
        
        # Reset do timeout da aproximação final
        self.final_approach_start_time = None
        
        # Calcula o caminho APENAS para o destino
        path_to_destination = self.path_finder.find_path(self.current_position, destination)
        if not path_to_destination or len(path_to_destination) < 2:
            print("DEBUG: ERRO - Não foi possível encontrar caminho para o destino")
            self.navigation_active = False
            return

        # O caminho agora é APENAS para o destino. O retorno será calculado depois.
        self.path = path_to_destination
        self.path_index = 0
        
        self.original_destination = destination
        self.destination_index = len(path_to_destination) - 1
        
        # Define o primeiro alvo
        self.current_target = self.path[0]
        
        print(f"DEBUG: Caminho de ida calculado com {len(self.path)} pontos.")
        print(f"DEBUG: ===== NAVEGAÇÃO INICIADA =====")
        
    def navigate_to_destination_only(self, destination: Tuple[float, float]) -> None:
        """Navega apenas até o destino e para lá (sem retorno automático)"""
        print(f"DEBUG: ===== NAVEGAÇÃO APENAS AO DESTINO =====")
        print(f"DEBUG: Destino: {destination}")
        print(f"DEBUG: Posição atual: {self.current_position}, Ângulo atual: {self.current_angle}°")
        
        # Reset completo para nova navegação (MANTÉM as áreas proibidas)
        self.reset_to_initial_state()
        
        # Configura a navegação
        self.navigation_active = True
        self.start_time = time.time()
        self.navigation_state = "NAVIGATING_TO_DESTINATION"
        self.is_returning_to_base = False  # Importante: não vai retornar
        self.should_return_to_base = False  # NOVO: Navegação apenas ao destino
        
        # Reset do timeout da aproximação final
        self.final_approach_start_time = None
        
        # Calcula o caminho APENAS para o destino
        path_to_destination = self.path_finder.find_path(self.current_position, destination)
        if not path_to_destination or len(path_to_destination) < 2:
            print("DEBUG: ERRO - Não foi possível encontrar caminho para o destino")
            self.navigation_active = False
            return

        # O caminho é APENAS para o destino. Não haverá retorno.
        self.path = path_to_destination
        self.path_index = 0
        
        self.original_destination = destination
        self.destination_index = len(path_to_destination) - 1
        
        # Define o primeiro alvo
        self.current_target = self.path[0]
        
        print(f"DEBUG: Caminho calculado com {len(self.path)} pontos.")
        print(f"DEBUG: ===== NAVEGAÇÃO APENAS AO DESTINO INICIADA =====")

    def get_navigation_status(self) -> dict:
        """Retorna o status atual da navegação"""
        if not self.navigation_active:
            return {
                "state": "IDLE",
                "progress": 0.0,
                "estimated_time_remaining": 0.0,
                "current_target": None,
                "position": self.current_position,
                "angle": self.current_angle
            }
            
        # Calcula o progresso
        if len(self.path) > 1:
            progress = (self.path_index - 1) / (len(self.path) - 1)
        else:
            progress = 0.0
            
        # Calcula tempo restante
        time_remaining = 0.0
        if self.estimated_completion_time:
            time_remaining = max(0.0, self.estimated_completion_time - time.time())
            
        # Determina o estado atual
        current_state = self.navigation_state
        if self.is_paused_at_destination:
            current_state = "PAUSED_AT_DESTINATION"
        elif self.is_adjusting_final_angle:
            current_state = "ADJUSTING_FINAL_ANGLE"
            
        return {
            "state": current_state,
            "progress": progress,
            "estimated_time_remaining": time_remaining,
            "current_target": self.current_target,
            "position": self.current_position,
            "angle": self.current_angle,
            "is_returning_to_base": self.is_returning_to_base,
            "is_paused_at_destination": self.is_paused_at_destination
        }

    def _calculate_distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calcula a distância entre dois pontos"""
        return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2) 

    def _move_towards_target(self):
        """
        Move o robô em direção ao alvo usando o CONTROLE PID.
        Esta função calcula as velocidades linear e angular e as converte
        para a velocidade alvo de cada roda (em ticks por segundo).
        """
        if self.current_target is None:
            self.motors.set_target_speed(0, 0)
            return

        # --- 1. Calcular Erros ---
        dx = self.current_target[0] - self.current_position[0]
        dy = self.current_target[1] - self.current_position[1]
        distance_to_target = math.sqrt(dx**2 + dy**2)
        target_angle = math.degrees(math.atan2(dy, dx))
        angle_error = (target_angle - self.current_angle + 180) % 360 - 180

        # --- 2. Lógica de Controle Aprimorada (Girar Primeiro, Depois Mover) ---
        # Se o erro angular for grande, prioriza o giro no lugar.
        # Se estiver alinhado, move-se para frente.
        
        angle_threshold_deg = 20.0  # Limite de 20 graus para considerar "alinhado"
        
        if abs(angle_error) > angle_threshold_deg:
            # Erro angular grande: Foca em girar no lugar.
            linear_speed_ms = 0  # Não move para frente
            # A velocidade angular é proporcional ao erro, mas limitada.
            angular_speed_rads = math.radians(angle_error) * 1.5 # Ganho Proporcional para giro
            angular_speed_rads = max(-MAX_ANGULAR_SPEED_RADS, min(MAX_ANGULAR_SPEED_RADS, angular_speed_rads))
        else:
            # Erro angular pequeno: Foca em mover para frente com velocidade máxima.
            angular_speed_rads = 0 # Não gira mais
            # A velocidade linear agora é a máxima permitida, garantindo força.
            linear_speed_ms = MAX_LINEAR_SPEED_MS

        # --- 3. Converter para Velocidade das Rodas ---
        # CORREÇÃO CONSERVADORA: Reverter cinemática diferencial para original
        # Manter apenas correção no cálculo final de movimento
        v = linear_speed_ms
        w = angular_speed_rads
        L = ROBOT_WHEEL_BASE_M
        
        # Revertendo para a cinemática original para corrigir o feedback loop
        left_wheel_speed_ms = v - (w * L) / 2.0
        right_wheel_speed_ms = v + (w * L) / 2.0
        
        print(f"🧮 SYNC_DEBUG: CINEMÁTICA | v={v:.3f}, w={w:.3f} → left_ms={left_wheel_speed_ms:.3f}, right_ms={right_wheel_speed_ms:.3f}")

        # --- 4. Converter m/s para Ticks por Segundo (TPS) ---
        # TPS = (metros / segundo) / (metros / revolução) * (ticks / revolução)
        left_tps = (left_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps = (right_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        
        print(f"⚙️  SYNC_DEBUG: TPS FINAL | left_tps={left_tps:.1f}, right_tps={right_tps:.1f}")

        # --- REMOVIDO: PISO DE VELOCIDADE MÍNIMA ---
        # PROBLEMA: Este piso estava destruindo as curvas!
        # Forçava left=17.1, right=4.3 → ambos=20.0 (sem diferença = sem curva)
        # 
        # MIN_STABLE_TPS = 20.0
        # if 0 < abs(left_tps) < MIN_STABLE_TPS:
        #     left_tps = MIN_STABLE_TPS * (1 if left_tps > 0 else -1)
        # if 0 < abs(right_tps) < MIN_STABLE_TPS:
        #     right_tps = MIN_STABLE_TPS * (1 if right_tps > 0 else -1)

        # --- 5. Enviar Comando para o Controlador PID ---
        # SIMPLIFICAÇÃO: Usar valores originais + inversão simples no final
        final_left_tps = left_tps    # ORIGINAL
        final_right_tps = right_tps  # ORIGINAL
            
        # O log agora mostrará a velocidade alvo em TPS original
        print(f"DEBUG PID ORIGINAL: Target L:{final_left_tps:.1f}tps R:{final_right_tps:.1f}tps | Lin:{linear_speed_ms:.2f}m/s Ang:{angular_speed_rads:.2f}rad/s")
        
        # REVERTENDO: Voltando ao original para evitar feedback loop
        print(f"DEBUG PID: VOLTANDO AO ORIGINAL - sem inversão")  
        self.motors.set_target_speed(final_left_tps, final_right_tps)  # REVERTIDO para original
        
        # A odometria é sempre atualizada no loop principal 'update', não precisamos chamar aqui.
        # if not GPIO_AVAILABLE: self._update_position(...)

    def _stable_final_approach(self, final_target: Tuple[float, float]):
        """
        Executa uma aproximação final estável e precisa, parando ao chegar.
        """
        if final_target is None:
            print("AVISO: _stable_final_approach chamado com alvo nulo.")
            self.motors.stop()
            return True # Considera finalizado para não travar

        current_time = time.time()
        if self.final_approach_start_time is None:
            self.final_approach_start_time = current_time

        if current_time - self.final_approach_start_time > self.final_approach_timeout:
            print("TIMEOUT na aproximação final. Forçando parada.")
            self.motors.stop()
            self.final_approach_start_time = None
            return True 
            
        dx = final_target[0] - self.current_position[0]
        dy = final_target[1] - self.current_position[1]
        total_distance = math.sqrt(dx**2 + dy**2)
        target_angle = math.degrees(math.atan2(dy, dx))
        angle_diff = (target_angle - self.current_angle + 180) % 360 - 180

        final_tolerance = 0.15
        if total_distance <= final_tolerance:
            self.motors.stop()
            self.final_approach_start_time = None
            return True

        angle_tolerance_approach = 5.0
        if abs(angle_diff) > angle_tolerance_approach:
            linear_speed_ms = 0.0
        else:
            linear_speed_ms = min(MAX_LINEAR_SPEED_MS * 0.7, total_distance / 1.5)
        
        angular_gain = 2.5
        angular_speed_rads = math.radians(angle_diff) * angular_gain
        angular_speed_rads = max(-MAX_ANGULAR_SPEED_RADS, min(MAX_ANGULAR_SPEED_RADS, angular_speed_rads))

        v = linear_speed_ms
        w = angular_speed_rads
        L = ROBOT_WHEEL_BASE_M
        # Revertendo para a cinemática original
        left_wheel_speed_ms = v - (w * L) / 2.0
        right_wheel_speed_ms = v + (w * L) / 2.0

        left_tps = (left_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps = (right_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION

        # Não há necessidade de inverter o sinal aqui. O cálculo deve estar correto.
        self.motors.set_target_speed(left_tps, right_tps)

        return False

    def _adjust_final_angle(self):
        """Ajusta o ângulo final para 270°"""
        print(f"DEBUG: === AJUSTE DE ÂNGULO FINAL ===")
        print(f"DEBUG: Ângulo atual: {self.current_angle:.2f}°")
        print(f"DEBUG: Ângulo desejado: {ROBOT_INITIAL_ANGLE}°")
        
        # Calcula a diferença de ângulo para 270°
        angle_diff = (ROBOT_INITIAL_ANGLE - self.current_angle + 180) % 360 - 180
        
        print(f"DEBUG: Diferença calculada: {angle_diff:.2f}°")
        print(f"DEBUG: Tolerância: 1.0°")
        print(f"DEBUG: Deve girar? {abs(angle_diff) > 1.0}")
        
        if abs(angle_diff) > 1.0:  # Tolerância menor para precisão
            # Ajusta o ângulo para 270° com velocidade adaptativa
            if abs(angle_diff) > 30:
                turn_value = min(0.8, abs(angle_diff) / 25.0)  # Giro mais rápido para diferenças grandes
            elif abs(angle_diff) > 10:
                turn_value = min(0.6, abs(angle_diff) / 30.0)  # Giro moderado
            else:
                turn_value = min(0.4, abs(angle_diff) / 35.0)  # Giro suave para ajuste fino
                
            # Define a direção do giro baseado na diferença
            if angle_diff > 0:
                # Precisa girar no sentido horário (ângulo atual < 270°)
                # CORREÇÃO FINAL: Aplicando lógica dos botões que funcionam
                # BOTÃO DIREITA (horário): set_speed(+ESQ, -DIR)
                left_speed = turn_value * 100   # CORRIGIDO: era -turn_value * 100
                right_speed = -turn_value * 100 # CORRIGIDO: era turn_value * 100
                direction = "horário"
            else:
                # Precisa girar no sentido anti-horário (ângulo atual > 270°)
                # CORREÇÃO FINAL: Aplicando lógica dos botões que funcionam  
                # BOTÃO ESQUERDA (anti-horário): set_speed(-ESQ, +DIR)
                left_speed = -turn_value * 100  # CORRIGIDO: era turn_value * 100
                right_speed = turn_value * 100  # CORRIGIDO: era -turn_value * 100
                direction = "anti-horário"
                
            print(f"DEBUG: Comando de giro: {turn_value:.3f}")
            print(f"DEBUG: Direção do giro: {direction}")
            print(f"DEBUG: Velocidades: L:{left_speed:.1f}% R:{right_speed:.1f}%")
            print(f"DEBUG: Ângulo atual: {self.current_angle:.2f}°, objetivo: {ROBOT_INITIAL_ANGLE}°")
            
            # Aplica o comando de giro
            print(f"DEBUG ADJUST: VOLTANDO AO ORIGINAL - sem inversão")
            self.motors.set_speed(left_speed, right_speed)  # REVERTIDO para original
            
            # CORREÇÃO: NÃO chama _update_position aqui - deixa a odometria real funcionar
            # self._update_position(0.0, turn_value)  # REMOVIDO
            
            print(f"DEBUG: Comando de giro aplicado - aguardando odometria real...")
        else:
            print("DEBUG: === ÂNGULO AJUSTADO COM SUCESSO ===")
            print(f"DEBUG: Ângulo final: {self.current_angle:.2f}°")
            print(f"DEBUG: Diferença final: {(ROBOT_INITIAL_ANGLE - self.current_angle + 180) % 360 - 180:.2f}°")
            print("DEBUG: Robô na base com ângulo 270° (apontando para cima)")
            
            # Finaliza a navegação usando o método centralizado
            self._finalize_navigation()

    def _get_next_waypoint_info(self):
        """Obtém informações sobre o próximo waypoint no caminho."""
        if not self.path or self.path_index >= len(self.path):
            return None
        return self.path_index, self.current_target, len(self.path)

    def _update_pose_with_odometry(self):
        """
        Atualiza a posição (pose) do robô com base nos ticks dos encoders dos motores.
        Esta função é a fonte única da verdade para a odometria do robô.
        """
        # A função get_and_reset_ticks retorna os ticks acumulados e os zera.
        ticks_data = self.motors.get_and_reset_ticks()
        if not ticks_data:
            return

        left_ticks = ticks_data.get('left', 0)
        right_ticks = ticks_data.get('right', 0)

        # Calcula a distância percorrida por cada roda
        dist_left = (left_ticks / TICKS_PER_REVOLUTION) * ROBOT_WHEEL_CIRCUMFERENCE_M
        dist_right = (right_ticks / TICKS_PER_REVOLUTION) * ROBOT_WHEEL_CIRCUMFERENCE_M

        # Calcula a distância média percorrida pelo robô
        delta_distance = (dist_left + dist_right) / 2.0

        # Revertendo para a convenção padrão de odometria para alinhar com a cinemática.
        delta_angle_rad = (dist_right - dist_left) / ROBOT_WHEEL_BASE_M
        delta_angle_deg = math.degrees(delta_angle_rad)

        # Atualiza o ângulo do robô
        self.current_angle += delta_angle_deg

        # Garante que o ângulo permaneça no intervalo [-180, 180]
        if self.current_angle > 180:
            self.current_angle -= 360
        elif self.current_angle < -180:
            self.current_angle += 360

        # Calcula a nova posição (x, y)
        angle_rad = math.radians(self.current_angle)
        delta_x = delta_distance * math.cos(angle_rad)
        delta_y = delta_distance * math.sin(angle_rad)

        self.current_position = (self.current_position[0] + delta_x, self.current_position[1] + delta_y)
        
        # Atualiza o tempo da última atualização
        self.last_position_update = time.time()

        # >>>>> CORREÇÃO FUNDAMENTAL <<<<<
        # Emite o sinal com a nova posição e ângulo para que a UI possa ser atualizada.
        self.position_updated.emit(self.current_position[0], self.current_position[1], self.current_angle)

    def get_motor_controller(self):
        """Retorna a instância do controlador do motor."""
        return self.motors

    def stop(self):
        """Para a navegação e o robô."""
        print("INFO: Comando de parada recebido pelo navegador.")