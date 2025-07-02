import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import time
import math
from typing import List, Tuple, Optional
from .slamtec_manager import SlamtecManager
from .robot_motor_controller import RobotMotorController
from .config import *
from src.core.environment import GPIO_AVAILABLE, is_raspberry_pi
from .path_finder import PathFinder

class RobotNavigator:
    def __init__(self):
        """Inicializa o navegador do robô."""
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
        
        # Sistema de timeout para evitar travamento na aproximação final
        self.final_approach_start_time = None
        self.final_approach_timeout = 15.0  # Aumentado para 15s para dar mais margem
        
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
        
        # Sempre usa a posição inicial definida em config.py
        self.current_position = ROBOT_INITIAL_POSITION
        self.current_angle = ROBOT_INITIAL_ANGLE
        
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
                print("🔄 MUDANÇA DE FASE: NAVIGATING_TO_DESTINATION → FINAL_APPROACH")
                self.navigation_state = "FINAL_APPROACH"
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

        elif self.navigation_state == "FINAL_APPROACH":
            print("DEBUG: update() - Estado: FINAL_APPROACH")
            # _stable_final_approach gerencia seu próprio movimento
            if self._stable_final_approach():
                # Chegou ao destino com sucesso
                print("🔄 MUDANÇA DE FASE: FINAL_APPROACH → PAUSED_AT_DESTINATION")
                self.motors.stop()
                self.navigation_state = "PAUSED_AT_DESTINATION"
                self.arrival_time = time.time()
                self.is_paused_at_destination = True
        
        elif self.navigation_state == "PAUSED_AT_DESTINATION":
            print("DEBUG: update() - Estado: PAUSED_AT_DESTINATION")
            if self.arrival_time is not None and (time.time() - self.arrival_time > self.arrival_pause_time):
                self.is_paused_at_destination = False
                # Avança para o próximo ponto, que é o início do caminho de volta
                self.path_index = self.destination_index + 1
                if self.path_index < len(self.path):
                    self.current_target = self.path[self.path_index]
                    print("🔄 MUDANÇA DE FASE: PAUSED_AT_DESTINATION → RETURNING_TO_BASE")
                    self.navigation_state = "RETURNING_TO_BASE"
                    self.is_returning_to_base = True
                else:
                    # Caso estranho: não há caminho de volta, então finaliza.
                    print("DEBUG: Não há caminho de volta, ajustando ângulo final.")
                    self._start_final_angle_adjustment()

        elif self.navigation_state == "RETURNING_TO_BASE":
            print("DEBUG: update() - Estado: RETURNING_TO_BASE")
            if self.current_target is None or self.current_position is None:
                print("DEBUG: ERRO - Alvo ou posição atual nulos em RETURNING_TO_BASE")
                self._finalize_navigation()
                return

            distance_to_target = self._calculate_distance(self.current_position, self.current_target)
            
            if distance_to_target < NAVIGATION_GOAL_TOLERANCE: # 15cm
                self.path_index += 1
                if self.path_index >= len(self.path):
                    # Chegou ao fim do caminho de volta (base)
                    print("🏁 FINALIZOU FASE: RETURNING_TO_BASE")
                    self._start_final_angle_adjustment()
                    return
                else:
                    self.current_target = self.path[self.path_index]
                    print(f"DEBUG: Próximo alvo do retorno: {self.current_target}")
            
            self._move_towards_target()

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
        """
        (LEGADO E PERIGOSO) - Calcula os valores de movimento.
        Esta função foi substituída por _move_towards_target para um controle mais seguro.
        """
        print("AVISO DE SEGURANÇA: A função legada _calculate_movement foi chamada!")
        # Retorna valores seguros para parar o robô caso seja chamada por engano.
        self.motors.stop()
        return 0.0, 0.0

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
        left_speed = (forward_value - turn_value) * 100
        right_speed = (forward_value + turn_value) * 100
        
        self.motors.set_speed(left_speed, right_speed)
        
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
        actual_base_position = ROBOT_INITIAL_POSITION
        print(f"DEBUG: ===== INICIANDO NAVEGAÇÃO =====")
        print(f"DEBUG: Destino: {destination}")
        print(f"DEBUG: Base (config.py): {actual_base_position}")
        print(f"DEBUG: Posição atual: {self.current_position}, Ângulo atual: {self.current_angle}°")
        print(f"DEBUG: Áreas proibidas configuradas: {len(self.forbidden_areas)}")
        
        # Debug das áreas proibidas
        for i, area in enumerate(self.forbidden_areas):
            print(f"DEBUG: Área proibida {i}: {len(area)} pontos")
            for j, point in enumerate(area):
                print(f"DEBUG:   Ponto {j}: {point}")
        
        # Reset completo para nova navegação (MANTÉM as áreas proibidas)
        self.reset_to_initial_state()
        
        # Configura a navegação
        self.navigation_active = True
        self.start_time = time.time()
        self.navigation_state = "NAVIGATING_TO_DESTINATION"
        self.is_returning_to_base = False
        
        # 📍 LOG INICIAL DA NAVEGAÇÃO AO DESTINO
        print("🚀 INICIANDO FASE: NAVIGATING_TO_DESTINATION")
        print("=" * 80)
        print(f"📍 POSIÇÃO INICIAL (início da ida ao destino):")
        print(f"  🤖 Coordenadas X,Y: ({self.current_position[0]:.4f}, {self.current_position[1]:.4f})")
        print(f"  🧭 Ângulo inicial: {self.current_angle:.2f}°")
        print(f"  🎯 Destino alvo: {destination}")
        print(f"  📊 Distância até destino: {self._calculate_distance(self.current_position, destination):.4f}m")
        print("=" * 80)
        
        # Reset do timeout da aproximação final
        self.final_approach_start_time = None
        
        # Calcula o caminho completo: base -> destino -> base
        print(f"DEBUG: Calculando caminho completo: base -> destino -> base")
        
        # Caminho da base até o destino
        path_to_destination = self.path_finder.find_path(self.current_position, destination)
        if not path_to_destination:
            print("DEBUG: ERRO - Não foi possível encontrar caminho para o destino")
            self.navigation_active = False
            return
            
        # Caminho do destino até a base
        path_to_base = self.path_finder.find_path(destination, actual_base_position)
        if not path_to_base:
            print("DEBUG: ERRO - Não foi possível encontrar caminho de retorno à base")
            self.navigation_active = False
            return
            
        # Combina os caminhos: base -> destino -> base
        self.path = path_to_destination + path_to_base[1:]  # Remove duplicação do destino
        self.path_index = 0
        
        # **CORREÇÃO CRÍTICA: SEMPRE USA O DESTINO EXATO SOLICITADO**
        self.original_destination = destination  # GARANTE que seja exatamente o destino solicitado
        self.destination_index = len(path_to_destination) - 1  # Índice do destino no path combinado
        
        print("=" * 80)
        print("🎯 MAPEAMENTO DO DESTINO IDENTIFICADO:")
        print(f"📍 Destino original identificado: {self.original_destination}")
        print(f"📊 Caminho total: {len(self.path)} pontos")
        print(f"🎯 Índice do destino: {self.destination_index}")
        print(f"📊 Caminho de ida: {len(path_to_destination)} pontos")
        print(f"📊 Caminho de volta: {len(path_to_base)} pontos")
        print("📋 Caminho completo:")
        for i, point in enumerate(self.path):
            if i == self.destination_index:
                print(f"  {i}: {point} ⭐ <- DESTINO FINAL")
            elif i < len(path_to_destination):
                print(f"  {i}: {point} (ida)")
            else:
                print(f"  {i}: {point} (volta)")
        print("=" * 80)
        
        # Define o primeiro alvo
        if len(self.path) > 0:
            self.current_target = self.path[0]
        else:
            print("DEBUG: ERRO - Caminho vazio")
            self.navigation_active = False
            return
        
        print(f"DEBUG: Caminho completo calculado com {len(self.path)} pontos")
        for i, point in enumerate(self.path):
            print(f"DEBUG:   Ponto {i}: {point}")
        print(f"DEBUG: Primeiro alvo: {self.current_target}")
        print(f"DEBUG: Navegação ativa: {self.navigation_active}")
        print(f"DEBUG: ===== NAVEGAÇÃO INICIADA =====")
        
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
        """Move o robô em direção ao alvo atual, gerenciando velocidade e rotação."""
        if self.current_target is None:
            return

        # Calcula a distância e o ângulo para o alvo
        dx = self.current_target[0] - self.current_position[0]
        dy = self.current_target[1] - self.current_position[1]
        distance = math.sqrt(dx**2 + dy**2)
        target_angle = math.degrees(math.atan2(dy, dx))
        angle_diff = (target_angle - self.current_angle + 180) % 360 - 180

        forward_value = 0
        turn_value = 0

        # Lógica de movimento dividida por fases para maior controle
        if self.navigation_state == "NAVIGATING_TO_DESTINATION" or self.navigation_state == "RETURNING_TO_BASE":
            angle_tolerance = NAVIGATION_ANGLE_TOLERANCE

            if abs(angle_diff) > angle_tolerance:
                # Gira primeiro se o ângulo for muito grande
                turn_value = min(0.5, abs(angle_diff) / 30.0)
                if angle_diff < 0:
                    turn_value = -turn_value
            else:
                # Movimento para frente com ajuste de rotação
                # Aplica o multiplicador de velocidade
                base_speed = ROBOT_SPEED * self.speed_multiplier
                forward_value = min(base_speed, distance / 1.5)

                if abs(angle_diff) > 1.5:  # Pequeno ajuste de curva
                    turn_value = min(0.1, abs(angle_diff) / 40.0)
                    if angle_diff < 0:
                        turn_value = -turn_value
        
        elif self.navigation_state == "FINAL_APPROACH":
             # Lógica para aproximação final (mais lenta e cuidadosa)
            if abs(angle_diff) > NAVIGATION_ULTRA_PRECISION_ANGLE_TOLERANCE:
                turn_value = min(0.15, abs(angle_diff) / 60.0)
                if angle_diff < 0:
                    turn_value = -turn_value
            else:
                # Na aproximação final, não usamos o multiplicador para segurança
                forward_value = min(0.1, distance)

        # Aplica os comandos de movimento
        if forward_value > 0 or abs(turn_value) > 0:
            left_speed = (forward_value - turn_value) * 100 
            right_speed = (forward_value + turn_value) * 100
            
            # --- DISJUNTOR DE SEGURANÇA ---
            # Limita a velocidade máxima absoluta enviada aos motores.
            # Este é o último ponto de controle para evitar excesso de velocidade.
            HARD_SPEED_LIMIT = 30.0 # NUNCA exceder 30% da potência do motor em modo autônomo
            
            left_speed = max(-HARD_SPEED_LIMIT, min(HARD_SPEED_LIMIT, left_speed))
            right_speed = max(-HARD_SPEED_LIMIT, min(HARD_SPEED_LIMIT, right_speed))
            
            print(f"DEBUG: Motores - L:{left_speed:.1f} R:{right_speed:.1f} | Fwd:{forward_value:.2f} Turn:{turn_value:.2f} Mult:{self.speed_multiplier:.2f}")
            self.motors.set_speed(left_speed, right_speed)
        else:
            self.motors.stop()
        
        # Atualiza a posição (simulado)
        self._update_position(forward_value, turn_value)

    def _stable_final_approach(self):
        """
        Executa uma aproximação final estável e precisa, parando ao chegar.
        """
        # **CORREÇÃO CRÍTICA: USA O DESTINO ORIGINAL, NÃO O CURRENT_TARGET**
        if not hasattr(self, 'original_destination') or self.original_destination is None:
            print("DEBUG: ⚠️ Destino original não definido na aproximação final")
            return False
            
        # **SISTEMA DE TIMEOUT PARA EVITAR TRAVAMENTO**
        current_time = time.time()
        if self.final_approach_start_time is None:
            self.final_approach_start_time = current_time
            print("DEBUG: Iniciando timeout da aproximação final")
        elif current_time - self.final_approach_start_time > self.final_approach_timeout:
            print(f"DEBUG: ⚠️ TIMEOUT DA APROXIMAÇÃO FINAL ({self.final_approach_timeout}s)")
            print("DEBUG: Considerando destino alcançado por timeout")
            self.motors.stop()
            self.final_approach_start_time = None
            return True # Considera como sucesso para não travar
        
        # **USA O DESTINO ORIGINAL REAL**
        if self.original_destination is None or self.current_position is None:
            print("DEBUG: ⚠️ Posição ou destino não definidos")
            return False
            
        dx = self.original_destination[0] - self.current_position[0]
        dy = self.original_destination[1] - self.current_position[1]
        total_distance = math.sqrt(dx*dx + dy*dy)
        
        elapsed_time = current_time - self.final_approach_start_time
        print("🎯 APROXIMAÇÃO FINAL DETALHADA:")
        print("=" * 80)
        print(f"⏱️ Tempo de aproximação: {elapsed_time:.1f}s (timeout em {self.final_approach_timeout}s)")
        print(f"📍 POSIÇÕES:")
        print(f"  🤖 Robô: ({self.current_position[0]:.4f}, {self.current_position[1]:.4f})")
        print(f"  🎯 Destino REAL: ({self.original_destination[0]:.4f}, {self.original_destination[1]:.4f})")
        print(f"📏 DISTÂNCIAS:")
        print(f"  📊 Erro total: {total_distance:.4f}m ({total_distance*100:.1f}cm)")
        print(f"  📊 Erro X: {abs(dx):.4f}m ({abs(dx)*100:.1f}cm)")
        print(f"  📊 Erro Y: {abs(dy):.4f}m ({abs(dy)*100:.1f}cm)")
        print(f"  🎯 Tolerância final: 5.0cm")
        print("=" * 80)
        
        # **TOLERÂNCIA MAIS REALISTA PARA EVITAR OSCILAÇÃO**
        final_tolerance = 0.05  # 5cm - mais realista e estável
        
        # Verifica tolerâncias individuais por eixo para debug
        tolerance_x = abs(dx) <= 0.03  # 3cm em X
        tolerance_y = abs(dy) <= 0.03  # 3cm em Y
        
        print(f"DEBUG: Tolerâncias - X: {'✅' if tolerance_x else '❌'} ({abs(dx)*100:.1f}cm), Y: {'✅' if tolerance_y else '❌'} ({abs(dy)*100:.1f}cm)")
        
        if total_distance <= final_tolerance:
            print("🎉 DESTINO FINAL ALCANÇADO COM SUCESSO!")
            print("=" * 80)
            print("🏆 MAPEAMENTO FINAL - ROBÔ CHEGOU AO DESTINO:")
            print(f"📍 Destino esperado: {self.original_destination}")
            print(f"🤖 Posição final do robô: ({self.current_position[0]:.4f}, {self.current_position[1]:.4f})")
            print(f"🎯 Destino REAL usado: ({self.original_destination[0]:.4f}, {self.original_destination[1]:.4f})")
            print("📊 PRECISÃO ALCANÇADA:")
            print(f"  ✅ Erro total: {total_distance*100:.1f}cm (tolerância: 5.0cm)")
            print(f"  ✅ Precisão X: {abs(dx)*100:.1f}cm")
            print(f"  ✅ Precisão Y: {abs(dy)*100:.1f}cm")
            print(f"  ⏱️ Tempo de aproximação: {elapsed_time:.1f}s")
            print("📋 COMPARAÇÃO COM DESTINO ORIGINAL:")
            if hasattr(self, 'original_destination') and self.original_destination is not None:
                orig_error_x = abs(self.current_position[0] - self.original_destination[0])
                orig_error_y = abs(self.current_position[1] - self.original_destination[1])
                orig_total_error = math.sqrt(orig_error_x**2 + orig_error_y**2)
                print(f"  📏 Erro vs destino original: {orig_total_error*100:.1f}cm")
                print(f"  📊 Erro X vs original: {orig_error_x*100:.1f}cm")
                print(f"  📊 Erro Y vs original: {orig_error_y*100:.1f}cm")
            print("=" * 80)
            self.motors.stop()
            self.final_approach_start_time = None
            return True # Sinaliza sucesso para a máquina de estados

        # **APROXIMAÇÃO DIRETA SEM CORREÇÃO POR EIXO**
        # Calcula ângulo direto para o destino
        target_angle = math.degrees(math.atan2(dy, dx))
        target_angle = (target_angle + 360) % 360
        angle_diff = (target_angle - self.current_angle + 180) % 360 - 180
        
        print(f"DEBUG: Ângulo para destino: {target_angle:.2f}°")
        print(f"DEBUG: Ângulo atual: {self.current_angle:.2f}°")
        print(f"DEBUG: Diferença angular: {angle_diff:.2f}°")
        
        forward_value = 0.0
        turn_value = 0.0
        
        # **ESTRATÉGIA MELHORADA PARA CORREÇÃO DO EIXO Y**
        # Verifica se o problema é principalmente no eixo Y
        distance_x = abs(dx)
        distance_y = abs(dy)
        
        print(f"DEBUG: Erro por eixo - X: {distance_x*100:.1f}cm, Y: {distance_y*100:.1f}cm")
        
        # Se o erro Y é maior que o erro X, prioriza a correção Y
        if distance_y > distance_x and distance_y > 0.02:  # Erro Y > 2cm e maior que X
            print(f"DEBUG: 🎯 PRIORIZANDO CORREÇÃO DO EIXO Y (erro: {distance_y*100:.1f}cm)")
            # Calcula ângulo específico para o eixo Y
            if dy > 0:
                target_angle_y = 90  # Subir (Y positivo)
            else:
                target_angle_y = 270  # Descer (Y negativo)
            
            angle_diff_y = (target_angle_y - self.current_angle + 180) % 360 - 180
            
            if abs(angle_diff_y) > 1.0:  # Precisa ajustar ângulo para Y
                turn_value = min(0.12, abs(angle_diff_y) / 50.0)
                if angle_diff_y < 0:
                    turn_value = -turn_value
                print(f"DEBUG: Ajustando para eixo Y: turn = {turn_value:.4f} (ângulo alvo: {target_angle_y}°)")
            else:
                # Move no eixo Y com velocidade proporcional ao erro
                forward_value = min(0.1, distance_y / 0.6)
                print(f"DEBUG: Movendo no eixo Y: forward = {forward_value:.4f}")
        
        elif abs(angle_diff) > 2.0:  # Tolerância angular relaxada
            # Primeiro alinha com o destino
            turn_value = min(0.1, abs(angle_diff) / 60.0)  # Giro muito suave
            if angle_diff < 0:
                turn_value = -turn_value
            print(f"DEBUG: Alinhando suavemente: turn = {turn_value:.4f}")
        else:
            # Move diretamente para o destino com velocidade proporcional
            forward_value = min(0.08, total_distance / 0.8)  # Velocidade muito baixa e proporcional
            print(f"DEBUG: Movimento final direto: forward = {forward_value:.4f}")
            
            # Correção angular mínima durante movimento
            if abs(angle_diff) > 0.5:
                turn_value = min(0.05, abs(angle_diff) / 80.0)
                if angle_diff < 0:
                    turn_value = -turn_value
                print(f"DEBUG: Correção angular mínima: turn = {turn_value:.4f}")
        
        # **APLICAÇÃO DOS COMANDOS COM LIMITAÇÃO EXTRA**
        if forward_value > 0 or turn_value != 0:
            left_speed = (forward_value - turn_value) * 100
            right_speed = (forward_value + turn_value) * 100
            
            # Limitação mais restritiva para evitar oscilação
            left_speed = max(-15, min(15, left_speed))
            right_speed = max(-15, min(15, right_speed))
            
            print(f"DEBUG: Comandos finais suaves - L: {left_speed:.1f}%, R: {right_speed:.1f}%")
            self.motors.set_speed(left_speed, right_speed)
            
            # Atualiza posição
            self._update_position(forward_value, turn_value)
        else:
            print("DEBUG: Parando motores na aproximação final")
            self.motors.stop()
            
        return False # Ainda não chegou

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
            # Usa a velocidade de ajuste fino definida no config.py
            turn_value = ROBOT_ADJUSTMENT_TURN_SPEED
                
            # Define a direção do giro baseado na diferença
            if angle_diff < 0:
                # Se a diferença é negativa, o giro deve ser no sentido anti-horário
                turn_value = -turn_value
                
            print(f"DEBUG: Comando de giro suave: {turn_value:.3f}")
            
            # Aplica o comando de giro (esquerda, direita)
            # Para girar no lugar, uma roda vai para frente e outra para trás
            self.motors.set_speed(-turn_value * 100, turn_value * 100)
            self._update_position(0.0, turn_value)
            
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
        return self.path[self.path_index] 