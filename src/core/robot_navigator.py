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
        self.navigation_state = "IDLE"  # IDLE, ORIENTING_TO_TARGET, NAVIGATING, RETURNING, COMPLETED
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
        
        # NOVO: Controle para giros precisos
        self.precise_rotation_active = False
        
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
        
        # 🎯 CORREÇÃO CRÍTICA: Reset completo de todas as variáveis de estado
        self.current_position = ROBOT_INITIAL_POSITION
        self.current_angle = ROBOT_INITIAL_ANGLE
        self.current_target = None
        self.navigation_active = False
        self.is_returning_to_base = False
        self.is_adjusting_final_angle = False
        self.navigation_state = "IDLE"
        self.speed_multiplier = 1.0
        
        # 🎯 NOVA CORREÇÃO: Reset de variáveis de loop e timeout
        if hasattr(self, 'return_start_time'):
            delattr(self, 'return_start_time')
        if hasattr(self, 'last_positions'):
            delattr(self, 'last_positions')
        if hasattr(self, 'last_angles'):
            delattr(self, 'last_angles')
        
        # Reset de variáveis de navegação
        self.path = []
        self.path_index = 0
        self.current_path = []
        self.current_path_index = 0
        
        # Reset de variáveis de precisão
        self.precise_rotation_active = False
        self.final_approach_start_time = None
        self.arrival_time = None
        self.is_paused_at_destination = False
        
        # Reset de variáveis de controle
        self.emergency_stop_active = False
        self.last_position_update = time.time()
        self.navigation_start_time = None
        self.estimated_completion_time = None
        
        print("✅ RESET COMPLETO: Todas as variáveis de estado foram limpas")
        print(f"✅ Posição resetada: {self.current_position}")
        print(f"✅ Ângulo resetado: {self.current_angle}°")
        print(f"✅ Estado resetado: {self.navigation_state}")
        
    def set_speed_multiplier(self, multiplier: float):
        """
        Define o multiplicador de velocidade para a navegação.
        
        Args:
            multiplier: Fator a ser multiplicado pela velocidade base (ex: 1.0, 1.5, 2.0).
        """
        if 1.0 <= multiplier <= 1.3:  # MÁXIMO SEGURO: reduzido de 2.0 para 1.3 (130%) para evitar quebrar navegação
            self.speed_multiplier = multiplier
            print(f"Velocidade ajustada para {self.speed_multiplier * 100:.0f}%")
        else:
            print(f"AVISO: Tentativa de definir multiplicador de velocidade inválido: {multiplier}. Deve ser entre 1.0 e 1.3.")

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
        self._update_pose_with_odometry()

        if not self.navigation_active:
            return

        if self.navigation_state == "IDLE":
            return

        elif self.navigation_state == "ORIENTING_TO_TARGET":
            # 🎯 CORREÇÃO: Tratamento diferenciado para orientação durante retorno
            if self.is_returning_to_base:
                print(f"DEBUG: ORIENTAÇÃO RETORNO: Posição {self.current_position}, Ângulo {self.current_angle:.1f}°")
            self._orient_towards_target()

        elif self.navigation_state == "NAVIGATING_TO_DESTINATION":
            self._handle_navigation_to_destination()

        elif self.navigation_state == "FINAL_APPROACH_DESTINATION":
            if self._stable_final_approach(self.original_destination):
                self._transition_to_paused_at_destination()
        
        elif self.navigation_state == "PAUSED_AT_DESTINATION":
            self._handle_pause_at_destination()

        elif self.navigation_state == "RETURNING_TO_BASE":
            # 🎯 CORREÇÃO: Logs específicos para debug do retorno
            print(f"DEBUG: ESTADO RETURNING_TO_BASE: Posição {self.current_position}, Ângulo {self.current_angle:.1f}°")
            self._handle_return_to_base()

        elif self.navigation_state == "FINAL_APPROACH_BASE":
            if self._stable_final_approach(self.path[-1]):
                self._start_final_angle_adjustment()

        elif self.navigation_state == "ADJUSTING_FINAL_ANGLE":
            self._adjust_final_angle()

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
        
    def _return_to_base_direct(self):
        """🎯 SOLUÇÃO GENIAL: Retorno direto à base usando coordenadas conhecidas com sincronia melhorada"""
        print("DEBUG: === RETORNO DIRETO À BASE ===")
        print(f"DEBUG: Posição atual: {self.current_position}")
        print(f"DEBUG: Base conhecida: {ROBOT_INITIAL_POSITION}")
        print(f"DEBUG: Ângulo final desejado: {ROBOT_INITIAL_ANGLE}°")
        
        # 🎯 CORREÇÃO CRÍTICA: Reset completo do estado para evitar loops
        print("🔄 RESET_COMPLETO: Limpando estado anterior para evitar loops")
        self.motors.stop()  # Para qualquer movimento em andamento
        time.sleep(0.5)     # Pausa para estabilizar
        
        # 🎯 RESET TOTAL: Limpa todas as variáveis de estado
        self.current_target = None
        self.path_index = 0
        self.final_approach_start_time = None
        self.is_adjusting_final_angle = False
        self.is_paused_at_destination = False
        
        # 🎯 FASE 1: Calcular ângulo direto para a base (sem PathFinder!)
        dx = ROBOT_INITIAL_POSITION[0] - self.current_position[0]
        dy = ROBOT_INITIAL_POSITION[1] - self.current_position[1]
        target_angle = math.degrees(math.atan2(dy, dx))
        
        # 🎯 NORMALIZA ângulo para -180 a +180
        while target_angle > 180:
            target_angle -= 360
        while target_angle < -180:
            target_angle += 360
        
        print(f"🧭 CÁLCULO_DIRETO: Ângulo para base = {target_angle:.1f}°")
        
        # 🎯 FASE 2: Configurar navegação direta (sem waypoints intermediários!)
        self.is_returning_to_base = True
        self.current_target = ROBOT_INITIAL_POSITION
        self.path = [self.current_position, ROBOT_INITIAL_POSITION]  # Caminho direto!
        self.path_index = 0
        
        # 🎯 CORREÇÃO CRÍTICA: Usar estado correto para retorno!
        # ANTES: navigation_state = "NAVIGATING_TO_DESTINATION" ← ESTADO INCORRETO!
        # AGORA: navigation_state = "RETURNING_TO_BASE" ← ESTADO CORRETO!
        print("🚀 NAVEGAÇÃO_DIRETA: Indo direto à base com estado RETURNING_TO_BASE!")
        self.navigation_state = "RETURNING_TO_BASE"
        
        # 🎯 VERIFICAÇÃO FINAL: Confirma que o estado está correto
        print(f"✅ ESTADO_CONFIRMADO: {self.navigation_state}")
        print(f"✅ RETORNANDO: {self.is_returning_to_base}")
        print(f"✅ ALVO: {self.current_target}")
        print(f"✅ CAMINHO: {self.path}")
        print(f"✅ ÂNGULO_ALVO: {target_angle:.1f}°")
        
        # 🎯 NOVO: Verifica se precisa de orientação prévia
        angle_error = abs((target_angle - self.current_angle + 180) % 360 - 180)
        if angle_error > 90:  # Se está muito desalinhado
            print(f"⚠️ ORIENTAÇÃO_PRÉVIA: Robô {angle_error:.1f}° desalinhado, iniciando orientação")
            self.navigation_state = "ORIENTING_TO_TARGET"
        else:
            print(f"✅ ORIENTAÇÃO_OK: Robô {angle_error:.1f}° alinhado, navegação direta")
            self.navigation_state = "RETURNING_TO_BASE"

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

    def set_autonomous_mode(self, autonomous):
        """Alterna entre modo autônomo e manual"""
        self.is_autonomous = autonomous
        if not autonomous:
            self.motors.stop()  # Para o robô ao sair do modo autônomo

    def set_forbidden_areas(self, areas: List[List[Tuple[float, float]]]):
        """Define as áreas proibidas para o navegador"""
        self.forbidden_areas = areas
        self.path_finder.set_forbidden_areas(areas)
        print(f"DEBUG: {len(areas)} áreas proibidas configuradas no navegador")

    def navigate_to_destination_only(self, destination: Tuple[float, float]) -> None:
        """Navega apenas até o destino e para lá (sem retorno automático)"""
        print(f"DEBUG: ===== NAVEGAÇÃO APENAS AO DESTINO =====")
        print(f"DEBUG: Destino: {destination}")
        print(f"DEBUG: Posição atual: {self.current_position}, Ângulo atual: {self.current_angle}°")
        
        self.reset_to_initial_state()
        
        self.navigation_active = True
        self.start_time = time.time()
        self.is_returning_to_base = False
        self.should_return_to_base = False
        self.final_approach_start_time = None
        
        path_to_destination = self.path_finder.find_path(self.current_position, destination)
        if not path_to_destination or len(path_to_destination) < 2:
            print("DEBUG: ERRO - Não foi possível encontrar caminho para o destino")
            self.navigation_active = False
            return

        self.path = path_to_destination
        self.path_index = 0
        
        self.original_destination = destination
        self.destination_index = len(path_to_destination) - 1
        
        self.current_target = self.path[0]
        
        print(f"DEBUG: Caminho calculado com {len(self.path)} pontos.")
        
        # 🎯 CORREÇÃO CIRÚRGICA: Verificação inteligente para pular orientação desnecessária
        dx = self.current_target[0] - self.current_position[0]
        dy = self.current_target[1] - self.current_position[1]
        target_angle = math.degrees(math.atan2(dy, dx))
        angle_error = abs((target_angle - self.current_angle + 180) % 360 - 180)
        
        # 🎯 CORREÇÃO FINAL: Tolerância ultra-permissiva para máxima precisão
        # Se o robô já está bem alinhado (tolerância de 25°), pula a orientação
        if angle_error < 25.0:
            print(f"🎯 PULO INTELIGENTE: Destino já alinhado (erro: {angle_error:.1f}°), iniciando navegação direta")
            self.navigation_state = "NAVIGATING_TO_DESTINATION"
        else:
            print(f"🔄 MUDANÇA DE FASE: IDLE → ORIENTING_TO_TARGET (erro: {angle_error:.1f}°)")
            self.navigation_state = "ORIENTING_TO_TARGET"

    def navigate_to_and_return(self, destination: Tuple[float, float]) -> None:
        """🎯 NAVEGAÇÃO INTELIGENTE: Usa A* se houver áreas proibidas, senão usa navegação direta"""
        print(f"DEBUG: ===== NAVEGAÇÃO INTELIGENTE =====")
        print(f"DEBUG: Destino: {destination}")
        print(f"DEBUG: Posição atual: {self.current_position}, Ângulo atual: {self.current_angle}°")
        print(f"DEBUG: Áreas proibidas configuradas: {len(self.forbidden_areas)}")

        self.reset_to_initial_state()

        self.navigation_active = True
        self.start_time = time.time()
        self.is_returning_to_base = False
        self.should_return_to_base = False  # 🎯 DESATIVA retorno automático
        self.final_approach_start_time = None

        # 🎯 VERIFICAÇÃO SEGURA: Se houver áreas proibidas, tenta usar A*
        if len(self.forbidden_areas) > 0:
            print(f"🎯 ÁREAS PROIBIDAS DETECTADAS: Tentando usar PathFinder A*...")
            try:
                path_to_destination = self.path_finder.find_path(self.current_position, destination)
                if path_to_destination and len(path_to_destination) >= 2:
                    self.path = path_to_destination
                    self.path_index = 0
                    self.original_destination = destination
                    self.destination_index = len(path_to_destination) - 1
                    self.current_target = self.path[0]
                    print(f"✅ A* SUCESSO: Caminho calculado com {len(self.path)} pontos")
                    print(f"✅ CAMINHO RESPEITA ÁREAS PROIBIDAS!")
                else:
                    print(f"⚠️ A* falhou, usando navegação direta (fallback)")
                    self._setup_direct_navigation(destination)
            except Exception as e:
                print(f"⚠️ ERRO no PathFinder: {e}. Usando navegação direta (fallback)")
                self._setup_direct_navigation(destination)
        else:
            print(f"🎯 SEM ÁREAS PROIBIDAS: Usando navegação direta para máxima velocidade")
            self._setup_direct_navigation(destination)

        # 🎯 Cálculo do ângulo para o primeiro target
        dx = self.current_target[0] - self.current_position[0]
        dy = self.current_target[1] - self.current_position[1]
        target_angle = math.degrees(math.atan2(dy, dx))
        angle_error = abs((target_angle - self.current_angle + 180) % 360 - 180)

        # 🎯 FORÇA navegação direta SEM orientação prévia
        print(f"🚀 NAVEGAÇÃO INICIADA: Indo ao destino!")
        self.navigation_state = "NAVIGATING_TO_DESTINATION"

    def _setup_direct_navigation(self, destination: Tuple[float, float]) -> None:
        """Configura navegação direta (método auxiliar para manter código limpo)"""
        self.path = [self.current_position, destination]
        self.path_index = 0
        self.original_destination = destination
        self.destination_index = 1
        self.current_target = destination
        print(f"🎯 NAVEGAÇÃO DIRETA: Caminho simplificado com apenas 2 pontos (atual → destino)")

    def get_navigation_status(self) -> dict:
        """Retorna o status atual da navegação"""
        if not self.navigation_active:
            return {
                "state": "IDLE", "progress": 0.0, "estimated_time_remaining": 0.0,
                "current_target": None, "position": self.current_position, "angle": self.current_angle
            }
            
        if len(self.path) > 1:
            progress = (self.path_index - 1) / (len(self.path) - 1)
        else:
            progress = 0.0
            
        time_remaining = 0.0
        if self.estimated_completion_time:
            time_remaining = max(0.0, self.estimated_completion_time - time.time())
            
        current_state = self.navigation_state
        if self.is_paused_at_destination:
            current_state = "PAUSED_AT_DESTINATION"
        elif self.is_adjusting_final_angle:
            current_state = "ADJUSTING_FINAL_ANGLE"
            
        return {
            "state": current_state, "progress": progress, "estimated_time_remaining": time_remaining,
            "current_target": self.current_target, "position": self.current_position,
            "angle": self.current_angle, "is_returning_to_base": self.is_returning_to_base,
            "is_paused_at_destination": self.is_paused_at_destination
        }

    def _calculate_distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calcula a distância entre dois pontos"""
        return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2) 

    def _orient_towards_target(self):
        if self.current_target is None:
            return

        # 🎯 CORREÇÃO CRÍTICA: Sistema anti-travamento durante orientação
        current_time = time.time()
        if not hasattr(self, 'orientation_start_time'):
            self.orientation_start_time = current_time
            self.orientation_attempts = 0
            print("🔄 ORIENTAÇÃO: Iniciando contador de tempo")
        
        # 🎯 TIMEOUT DE ORIENTAÇÃO: Se demorar mais de 10s, força movimento
        if current_time - self.orientation_start_time > 10.0:
            print("⚠️ TIMEOUT ORIENTAÇÃO: Demorou mais de 10s, forçando movimento!")
            self._force_orientation_movement()
            return

        # 🎯 CORREÇÃO CRÍTICA: Contador de tentativas para quebrar loop infinito
        if not hasattr(self, 'orientation_attempts'):
            self.orientation_attempts = 0
        
        # 🎯 QUEBRA LOOP INFINITO: Após 3 tentativas, força movimento direto
        if self.orientation_attempts >= 3:
            print("🚨 LOOP INFINITO DETECTADO: 3 tentativas de orientação, forçando movimento direto!")
            self._force_direct_movement()
            return

        dx = self.current_target[0] - self.current_position[0]
        dy = self.current_target[1] - self.current_position[1]
        target_angle = math.degrees(math.atan2(dy, dx))
        angle_error = (target_angle - self.current_angle + 180) % 360 - 180

        # 🎯 CORREÇÃO DEFINITIVA: Tolerância ULTRA-EXPANDIDA diferenciada para ida vs retorno
        if self.is_returning_to_base:
            # RETORNO: Tolerância MASSIVAMENTE expandida para eliminar loops totalmente
            angle_tolerance = 45.0  # ULTRA tolerante - permite quase qualquer orientação
            print(f"🔄 ORIENTAÇÃO RETORNO: Erro {angle_error:.1f}°, Tolerância {angle_tolerance}° (Tentativa {self.orientation_attempts + 1}/3)")
        else:
            # IDA: Mantém tolerância original para preservar precisão
            angle_tolerance = 20.0  # Mantém ida funcionando
            
        if abs(angle_error) < angle_tolerance:
            self.motors.stop()
            if self.is_returning_to_base:
                # 🎯 CORREÇÃO CRÍTICA: Para retorno, vai direto para navegação
                print(f"🔄 RETORNO: Orientação OK ({abs(angle_error):.1f}° < {angle_tolerance}°), indo para RETURNING_TO_BASE")
                self.navigation_state = "RETURNING_TO_BASE"
                # 🎯 RESET: Limpa timer de orientação e contador de tentativas
                if hasattr(self, 'orientation_start_time'):
                    delattr(self, 'orientation_start_time')
                if hasattr(self, 'orientation_attempts'):
                    delattr(self, 'orientation_attempts')
            else:
                # IDA: Mantém comportamento original
                state_key = "NAVIGATING_TO_DESTINATION"
                context = "IDA - PRECISA"
                print(f"🔄 MUDANÇA DE FASE: ORIENTING_TO_TARGET → {state_key} ({context}: {abs(angle_error):.1f}° < {angle_tolerance}°)")
                self.navigation_state = state_key
            return

        # 🎯 INCREMENTA CONTADOR DE TENTATIVAS
        self.orientation_attempts += 1

        # 🎯 CORREÇÃO CRÍTICA RETORNO: Força AINDA mais reduzida para eliminação total dos loops
        # ANTES: angular_speed_rads = math.radians(angle_error) * 5.0  ← Era muito forte!
        # V1: angular_speed_rads = math.radians(angle_error) * 1.5  ← Ainda causava 1 loop
        # V2: angular_speed_rads = math.radians(angle_error) * 1.0  ← Ainda causava desvios
        # V3: angular_speed_rads = math.radians(angle_error) * 0.7  ← Ainda causava loops no retorno
        # V4 CRÍTICA: Força ultra-reduzida ESPECIAL para retorno (90% menos força que original)
        if self.is_returning_to_base:
            angular_speed_rads = math.radians(angle_error) * 0.4  # EXTRA suave para retorno
        else:
            angular_speed_rads = math.radians(angle_error) * 0.7  # Mantém ida funcionando 
        angular_speed_rads = max(-MAX_ANGULAR_SPEED_RADS, min(MAX_ANGULAR_SPEED_RADS, angular_speed_rads))

        v = 0.0  # Velocidade linear é zero durante a orientação
        w = angular_speed_rads
        L = ROBOT_WHEEL_BASE_M
        
        left_wheel_speed_ms = v + (w * L) / 2.0
        right_wheel_speed_ms = v - (w * L) / 2.0
        
        left_tps = (left_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps = (right_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        
        # 🎯 CORREÇÃO CRÍTICA RETORNO: MIN_TURN_TPS diferenciado para ida vs retorno
        # ANTES: MIN_TURN_TPS = 20.0  ← Era muito forte para ajustes sutis!
        # V1: MIN_TURN_TPS = 12.0  ← Ainda causava 1 loop em 7 testes
        # V2: MIN_TURN_TPS = 8.0  ← Ainda causava desvios de 100-120cm
        # V3: MIN_TURN_TPS = 5.0  ← Ainda causava loops no retorno
        # V4 CRÍTICA: MIN_TURN_TPS EXTRA-suave para retorno
        if self.is_returning_to_base:
            MIN_TURN_TPS = 3.0  # EXTRA suave para retorno (85% menos força que original)
        else:
            MIN_TURN_TPS = 5.0  # Mantém ida funcionando
        if 0 < abs(left_tps) < MIN_TURN_TPS:
            left_tps = MIN_TURN_TPS * (1 if left_tps > 0 else -1)
        if 0 < abs(right_tps) < MIN_TURN_TPS:
            right_tps = MIN_TURN_TPS * (1 if right_tps > 0 else -1)
        
        print(f"🔄 ORIENTAÇÃO SUAVE: erro={angle_error:.1f}°, left_tps={left_tps:.1f}, right_tps={right_tps:.1f}")
        self.motors.set_target_speed(left_tps, right_tps)

    def _force_orientation_movement(self):
        """🚨 MOVIMENTO FORÇADO: Força o robô a sair do travamento durante orientação"""
        print("🚨 FORÇANDO MOVIMENTO DURANTE ORIENTAÇÃO!")
        
        # Para qualquer movimento atual
        self.motors.stop()
        time.sleep(0.5)
        
        # Calcula direção para o alvo
        dx = self.current_target[0] - self.current_position[0]
        dy = self.current_target[1] - self.current_position[1]
        target_angle = math.degrees(math.atan2(dy, dx))
        angle_error = (target_angle - self.current_angle + 180) % 360 - 180
        
        print(f"🚨 FORÇA: Ângulo para alvo: {target_angle:.1f}°, Erro: {angle_error:.1f}°")
        
        # Força movimento com velocidade baixa
        if abs(angle_error) < 30:  # Se está mais ou menos apontado
            print("🚨 FORÇA: Movendo direto para o alvo")
            # Velocidade baixa para frente
            force_speed = 10  # 10% da potência máxima
            self.motors.set_speed(force_speed, force_speed)
        else:
            print("🚨 FORÇA: Girando para alinhar")
            # Gira para alinhar com velocidade baixa
            if angle_error > 0:
                self.motors.set_speed(15, -15)  # Gira direita
            else:
                self.motors.set_speed(-15, 15)  # Gira esquerda
        
        # Reseta o timer de orientação
        self.orientation_start_time = time.time()

    def _force_direct_movement(self):
        """🚨 MOVIMENTO DIRETO: Força o robô a ir direto para o alvo sem orientação"""
        print("🚨 FORÇANDO MOVIMENTO DIRETO - QUEBRANDO LOOP INFINITO!")
        
        # Para qualquer movimento atual
        self.motors.stop()
        time.sleep(0.5)
        
        # Calcula direção para o alvo
        dx = self.current_target[0] - self.current_position[0]
        dy = self.current_target[1] - self.current_position[1]
        target_angle = math.degrees(math.atan2(dy, dx))
        angle_error = (target_angle - self.current_angle + 180) % 360 - 180
        
        print(f"🚨 MOVIMENTO DIRETO: Ângulo para alvo: {target_angle:.1f}°, Erro: {angle_error:.1f}°")
        
        # Se o erro de ângulo for muito grande, faz uma correção rápida
        if abs(angle_error) > 60:
            print("🚨 MOVIMENTO DIRETO: Erro muito grande, corrigindo ângulo rapidamente")
            correction_time = abs(angle_error) / 90.0  # Tempo baseado no erro
            if angle_error > 0:
                self.motors.set_speed(25, -25)  # Gira direita
            else:
                self.motors.set_speed(-25, 25)  # Gira esquerda
            time.sleep(correction_time)
            self.motors.stop()
        
        # Agora move direto para o alvo
        print("🚨 MOVIMENTO DIRETO: Indo direto para o alvo")
        direct_speed = 20  # 20% da potência máxima
        self.motors.set_speed(direct_speed, direct_speed)
        
        # Reseta todos os timers e contadores
        if hasattr(self, 'orientation_start_time'):
            delattr(self, 'orientation_start_time')
        if hasattr(self, 'orientation_attempts'):
            delattr(self, 'orientation_attempts')
        
        # Força mudança para navegação direta
        self.navigation_state = "RETURNING_TO_BASE"

    def _move_towards_target(self):
        if self.current_target is None:
            self.motors.set_target_speed(0, 0)
            return

        dx = self.current_target[0] - self.current_position[0]
        dy = self.current_target[1] - self.current_position[1]
        target_angle = math.degrees(math.atan2(dy, dx))
        angle_error = (target_angle - self.current_angle + 180) % 360 - 180

        # 🎯 NOVA CORREÇÃO: Sistema de detecção de padrões circulares
        if self.is_returning_to_base:
            if not hasattr(self, 'last_positions'):
                self.last_positions = []
                self.last_angles = []
            
            # Armazena as últimas 5 posições e ângulos
            self.last_positions.append(self.current_position)
            self.last_angles.append(self.current_angle)
            
            if len(self.last_positions) > 5:
                self.last_positions.pop(0)
                self.last_angles.pop(0)
            
            # 🎯 DETECÇÃO DE LOOP: Se as posições se repetem, há um loop
            if len(self.last_positions) == 5:
                # Calcula se está girando em círculo
                center_x = sum(pos[0] for pos in self.last_positions) / 5
                center_y = sum(pos[1] for pos in self.last_positions) / 5
                radius = sum(math.sqrt((pos[0] - center_x)**2 + (pos[1] - center_y)**2) for pos in self.last_positions) / 5
                
                if radius < 0.3:  # Se o raio for menor que 30cm, provavelmente está em loop
                    print(f"⚠️ ALERTA LOOP DETECTADO: Raio {radius:.2f}m < 0.3m - Forçando orientação!")
                    self.navigation_state = "ORIENTING_TO_TARGET"
                    self.motors.stop()
                    return

        # 🎯 VERIFICAÇÃO DE SEGURANÇA: Evita loops circulares durante retorno
        if self.is_returning_to_base and abs(angle_error) > 90:
            print(f"⚠️ ALERTA: Ângulo de erro muito grande ({angle_error:.1f}°) durante retorno!")
            print(f"⚠️ Posição atual: {self.current_position}, Alvo: {self.current_target}")
            print(f"⚠️ Ângulo atual: {self.current_angle:.1f}°, Ângulo alvo: {target_angle:.1f}°")
            
            # 🎯 CORREÇÃO: Força orientação antes de mover para evitar loops
            print("🔄 CORREÇÃO: Forçando orientação antes do movimento para evitar loops")
            self.navigation_state = "ORIENTING_TO_TARGET"
            return

        angle_factor = max(0.0, math.cos(math.radians(angle_error)))
        linear_speed_ms = MAX_LINEAR_SPEED_MS * self.speed_multiplier * angle_factor
        
        # 🎯 CORREÇÃO DEFINITIVA: Movimento angular diferenciado para ida vs retorno
        if self.is_returning_to_base:
            # RETORNO: Angular ULTRA suave para eliminar loops totalmente
            angular_speed_rads = math.radians(angle_error) * 0.2  # Reduzido de 1.8 para 0.2 (11x mais suave!)
            print(f"🔄 RETORNO SUAVE: Angular reduzido drasticamente (fator 0.2) para erro {angle_error:.1f}°")
        else:
            # IDA: Mantém controle angular normal para preservar precisão
            angular_speed_rads = math.radians(angle_error) * 1.8
        
        angular_speed_rads = max(-MAX_ANGULAR_SPEED_RADS, min(MAX_ANGULAR_SPEED_RADS, angular_speed_rads))

        v = linear_speed_ms
        w = angular_speed_rads
        L = ROBOT_WHEEL_BASE_M
        
        left_wheel_speed_ms = v + (w * L) / 2.0
        right_wheel_speed_ms = v - (w * L) / 2.0
        
        left_tps = (left_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps = (right_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        
        self.motors.set_target_speed(left_tps, right_tps)

    def _stable_final_approach(self, final_target: Tuple[float, float]):
        if final_target is None:
            self.motors.stop()
            return True

        current_time = time.time()
        if self.final_approach_start_time is None:
            self.final_approach_start_time = current_time

        if current_time - self.final_approach_start_time > self.final_approach_timeout:
            self.motors.stop()
            self.final_approach_start_time = None
            return True 
            
        dx = final_target[0] - self.current_position[0]
        dy = final_target[1] - self.current_position[1]
        total_distance = math.sqrt(dx**2 + dy**2)
        target_angle = math.degrees(math.atan2(dy, dx))
        angle_diff = (target_angle - self.current_angle + 180) % 360 - 180

        if total_distance <= 0.25:  # Aumentado de 0.15 para 0.25 metros (25cm)
            self.motors.stop()
            self.final_approach_start_time = None
            return True

        linear_speed_ms = 0.0 if abs(angle_diff) > 5.0 else min(MAX_LINEAR_SPEED_MS * 0.85, total_distance / 1.5)  # Aumentado de 0.7 para 0.85
        
        angular_speed_rads = math.radians(angle_diff) * 2.5
        angular_speed_rads = max(-MAX_ANGULAR_SPEED_RADS, min(MAX_ANGULAR_SPEED_RADS, angular_speed_rads))

        v = linear_speed_ms
        w = angular_speed_rads
        L = ROBOT_WHEEL_BASE_M
        left_wheel_speed_ms = v + (w * L) / 2.0
        right_wheel_speed_ms = v - (w * L) / 2.0

        left_tps = (left_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps = (right_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION

        self.motors.set_target_speed(left_tps, right_tps)
        return False

    def _adjust_final_angle(self):
        """🎯 CORREÇÃO: Ajuste preciso do ângulo final para 270° na base com sincronia melhorada"""
        angle_diff = (ROBOT_INITIAL_ANGLE - self.current_angle + 180) % 360 - 180
        
        print(f"🎯 AJUSTE_FINAL: Ângulo atual {self.current_angle:.1f}°, Alvo {ROBOT_INITIAL_ANGLE}°, Diferença {angle_diff:.1f}°")
        
        # 🎯 TOLERÂNCIA mais restritiva para máxima precisão
        if abs(angle_diff) > 0.5:  # Reduzido de 1.0° para 0.5° para maior precisão
            # 🎯 CORREÇÃO: Cálculo mais preciso da velocidade de giro
            if abs(angle_diff) > 45: 
                turn_value = min(0.5, abs(angle_diff) / 45.0)  # Mais suave para giros grandes
            elif abs(angle_diff) > 20: 
                turn_value = min(0.4, abs(angle_diff) / 40.0)  # Suave para giros médios
            elif abs(angle_diff) > 5: 
                turn_value = min(0.35, abs(angle_diff) / 35.0)  # Preciso para ajustes finos
            else: 
                turn_value = min(0.25, abs(angle_diff) / 30.0)  # Muito preciso para ajustes mínimos
                
            # 🎯 CORREÇÃO: Direção do giro corrigida com logs detalhados
            if angle_diff > 0:
                # Precisa girar no sentido horário (para a direita)
                left_speed = turn_value * 100
                right_speed = -turn_value * 100
                print(f"🔄 GIRANDO_DIREITA: left={left_speed:.0f}, right={right_speed:.0f} (ângulo: +{angle_diff:.1f}°)")
            else:
                # Precisa girar no sentido anti-horário (para a esquerda)
                left_speed = -turn_value * 100
                right_speed = turn_value * 100
                print(f"🔄 GIRANDO_ESQUERDA: left={left_speed:.0f}, right={right_speed:.0f} (ângulo: {angle_diff:.1f}°)")
                
            # 🎯 APLICA movimento com controle de tempo para precisão
            self.motors.set_speed(left_speed, right_speed)
            
            # 🎯 CALCULA tempo de giro baseado no ângulo e velocidade
            # Fórmula: tempo = ângulo / (velocidade_angular * fator_correção)
            base_turn_time = abs(angle_diff) / (turn_value * 100 * 0.8)  # Fator 0.8 para compensar atrito
            turn_time = max(0.1, min(2.0, base_turn_time))  # Limita entre 0.1s e 2.0s
            
            print(f"🎯 TEMPO_GIRO: {turn_time:.2f}s para {abs(angle_diff):.1f}° com velocidade {turn_value:.2f}")
            
            # 🎯 PARA automaticamente após o tempo calculado
            import threading
            def stop_after_time():
                time.sleep(turn_time)
                self.motors.stop()
                # 🎯 VERIFICA se o ângulo está correto após o giro
                final_angle_diff = (ROBOT_INITIAL_ANGLE - self.current_angle + 180) % 360 - 180
                if abs(final_angle_diff) <= 0.5:
                    print(f"✅ ÂNGULO_FINAL_CORRETO: {self.current_angle:.1f}° (diferença: {final_angle_diff:.1f}°)")
                    self._finalize_navigation()
                else:
                    print(f"⚠️ ÂNGULO_FINAL_INCORRETO: {self.current_angle:.1f}° (diferença: {final_angle_diff:.1f}°) - tentando novamente")
                    # 🎯 TENTA ajuste novamente se necessário
                    time.sleep(0.5)  # Pausa para estabilizar
                    self._adjust_final_angle()
            
            # 🚀 INICIA thread para parada automática
            threading.Thread(target=stop_after_time, daemon=True).start()
            
        else:
            print(f"✅ ÂNGULO_FINAL_CORRETO: {self.current_angle:.1f}° (diferença: {angle_diff:.1f}°)")
            self._finalize_navigation()

    def _get_next_waypoint_info(self):
        if not self.path or self.path_index >= len(self.path):
            return None
        return self.path_index, self.current_target, len(self.path)

    def _update_pose_with_odometry(self):
        """
        Atualiza a posição e ângulo do robô baseado na odometria.
        Durante giros precisos, atualiza apenas o ângulo para manter sincronização correta.
        """
        ticks_data = self.motors.get_and_reset_ticks()
        if not ticks_data:
            return

        left_ticks, right_ticks = ticks_data.get('left', 0), ticks_data.get('right', 0)
        dist_left = (left_ticks / TICKS_PER_REVOLUTION) * ROBOT_WHEEL_CIRCUMFERENCE_M
        dist_right = (right_ticks / TICKS_PER_REVOLUTION) * ROBOT_WHEEL_CIRCUMFERENCE_M
        delta_distance = (dist_left + dist_right) / 2.0
        delta_angle_rad = (dist_left - dist_right) / ROBOT_WHEEL_BASE_M
        delta_angle_deg = math.degrees(delta_angle_rad)

        # SEMPRE atualiza o ângulo (necessário para giros precisos)
        self.current_angle += delta_angle_deg
        if self.current_angle > 180: self.current_angle -= 360
        elif self.current_angle < -180: self.current_angle += 360

        # CONDICIONALMENTE atualiza a posição
        if not self.precise_rotation_active:
            # NAVEGAÇÃO NORMAL: Atualiza posição E ângulo
            angle_rad = math.radians(self.current_angle)
            delta_x = delta_distance * math.cos(angle_rad)
            delta_y = delta_distance * math.sin(angle_rad)
            self.current_position = (self.current_position[0] + delta_x, self.current_position[1] + delta_y)
        else:
            # GIRO PRECISO: Atualiza APENAS o ângulo (posição permanece fixa)
            # Durante giros precisos, a posição não é modificada para manter sincronização correta
            pass

        self.last_position_update = time.time()
        self.position_updated.emit(self.current_position[0], self.current_position[1], self.current_angle)

    def get_motor_controller(self):
        return self.motors

    def start_precise_rotation(self):
        """Inicia modo de giro preciso - desabilita atualização de posição."""
        print("🔄 PRECISE_ROTATION: Modo ativado - posição será fixa durante giros")
        self.precise_rotation_active = True

    def stop_precise_rotation(self):
        """Para modo de giro preciso - reabilita atualização de posição."""
        print("🔄 PRECISE_ROTATION: Modo desativado - posição volta a ser atualizada")
        self.precise_rotation_active = False

    def stop(self):
        print("INFO: Comando de parada recebido pelo navegador.")
        self._finalize_navigation()
        
    def _handle_navigation_to_destination(self):
        if self.current_target is None or self.current_position is None:
            self._finalize_navigation()
            return

        distance_to_target = self._calculate_distance(self.current_position, self.current_target)

        is_near_final_destination = (self.path_index >= len(self.path) - 1)

        if is_near_final_destination and distance_to_target < 0.15:
            self.navigation_state = "FINAL_APPROACH_DESTINATION"
            self.current_target = self.original_destination
            return

        if distance_to_target < 0.12:
            self.path_index += 1
            if self.path_index < len(self.path):
                self.current_target = self.path[self.path_index]
            else:
                self.navigation_state = "FINAL_APPROACH_DESTINATION"
                self.current_target = self.original_destination
            return
        
        self._move_towards_target()

    def _handle_return_to_base(self):
        """🎯 MANIPULADOR ROBUSTO DE RETORNO: Evita loops de 360° com verificações de segurança"""
        if self.current_target is None or self.current_position is None or not self.path:
            print("DEBUG: _handle_return_to_base: Parâmetros inválidos, finalizando navegação")
            self._finalize_navigation()
            return

        # 🎯 NOVA CORREÇÃO: Sistema de timeout para prevenir loops infinitos
        current_time = time.time()
        if not hasattr(self, 'return_start_time'):
            self.return_start_time = current_time
            print("🔄 RETORNO: Iniciando contador de tempo")
        
        # 🎯 VERIFICAÇÃO DE TIMEOUT: Se demorar mais de 30s, força parada para evitar loop
        if current_time - self.return_start_time > 30.0:
            print("⚠️ TIMEOUT RETORNO: Demorou mais de 30s, forçando parada para evitar loop")
            self.motors.stop()
            self._finalize_navigation()
            return

        # 🎯 CORREÇÃO CRÍTICA: Sistema anti-paralisia
        if not hasattr(self, 'last_position_check'):
            self.last_position_check = self.current_position
            self.last_position_check_time = current_time
            self.stuck_counter = 0
        
        # Verifica se está parado no mesmo lugar
        position_change = self._calculate_distance(self.current_position, self.last_position_check)
        time_since_last_check = current_time - self.last_position_check_time
        
        if time_since_last_check > 2.0:  # A cada 2 segundos
            if position_change < 0.01:  # Se moveu menos de 1cm
                self.stuck_counter += 1
                print(f"⚠️ ALERTA PARALISIA: Robô parado há {self.stuck_counter * 2}s (movimento: {position_change:.3f}m)")
                
                if self.stuck_counter >= 3:  # Se ficou parado por 6+ segundos
                    print("🚨 PARALISIA DETECTADA: Forçando movimento de emergência!")
                    self._force_movement_emergency()
                    self.stuck_counter = 0
            else:
                self.stuck_counter = 0
                print(f"✅ MOVIMENTO DETECTADO: {position_change:.3f}m em {time_since_last_check:.1f}s")
            
            self.last_position_check = self.current_position
            self.last_position_check_time = current_time

        distance_to_target = self._calculate_distance(self.current_position, self.current_target)
        is_near_base = (self.path_index >= len(self.path) - 1)
        
        print(f"DEBUG: RETORNO: Distância à base: {distance_to_target:.3f}m, Próximo da base: {is_near_base}")

        # 🎯 VERIFICAÇÃO DE SEGURANÇA: Evita loops infinitos
        if distance_to_target < 0.05:  # Se chegou muito perto (5cm)
            print("DEBUG: RETORNO: Chegou muito perto da base, iniciando aproximação final")
            self.navigation_state = "FINAL_APPROACH_BASE"
            self.current_target = self.path[-1]
            self.final_approach_start_time = None 
            return

        if is_near_base and distance_to_target < 0.15:
            print("DEBUG: RETORNO: Iniciando aproximação final à base")
            self.navigation_state = "FINAL_APPROACH_BASE"
            self.current_target = self.path[-1]
            self.final_approach_start_time = None 
            return

        if distance_to_target < NAVIGATION_GOAL_TOLERANCE:
            print(f"DEBUG: RETORNO: Chegou ao waypoint {self.path_index}, próximo: {self.path_index + 1}")
            self.path_index += 1
            if self.path_index < len(self.path):
                self.current_target = self.path[self.path_index]
                print(f"DEBUG: RETORNO: Novo alvo: {self.current_target}")
            else:
                print("DEBUG: RETORNO: Todos os waypoints completados, iniciando ajuste de ângulo final")
                self._start_final_angle_adjustment()
            return
        
        # 🎯 MOVIMENTO DIRETO: Sem orientação prévia para evitar loops
        print(f"DEBUG: RETORNO: Movendo direto à base (distância: {distance_to_target:.3f}m)")
        self._move_towards_target()

    def _force_movement_emergency(self):
        """🚨 MOVIMENTO DE EMERGÊNCIA: Força o robô a sair da paralisia"""
        print("🚨 INICIANDO MOVIMENTO DE EMERGÊNCIA!")
        
        # Para qualquer movimento atual
        self.motors.stop()
        time.sleep(0.5)
        
        # Calcula direção para a base
        dx = self.current_target[0] - self.current_position[0]
        dy = self.current_target[1] - self.current_position[1]
        target_angle = math.degrees(math.atan2(dy, dx))
        angle_error = (target_angle - self.current_angle + 180) % 360 - 180
        
        print(f"🚨 EMERGÊNCIA: Ângulo para base: {target_angle:.1f}°, Erro: {angle_error:.1f}°")
        
        # Força movimento direto com velocidade baixa
        if abs(angle_error) < 45:  # Se está mais ou menos apontado para a base
            print("🚨 EMERGÊNCIA: Movendo direto para a base")
            # Velocidade baixa para frente
            emergency_speed = 15  # 15% da potência máxima
            self.motors.set_speed(emergency_speed, emergency_speed)
        else:
            print("🚨 EMERGÊNCIA: Girando para alinhar com a base")
            # Gira para alinhar
            if angle_error > 0:
                self.motors.set_speed(20, -20)  # Gira direita
            else:
                self.motors.set_speed(-20, 20)  # Gira esquerda
        
        # Reseta o timeout para dar tempo do movimento de emergência
        self.return_start_time = time.time()

    def _transition_to_paused_at_destination(self):
        self.motors.stop()
        self.navigation_state = "PAUSED_AT_DESTINATION"
        self.arrival_time = time.time()
        self.is_paused_at_destination = True

    def _handle_pause_at_destination(self):
        """🎯 MANIPULADOR DE PAUSA: Controla a transição para retorno à base"""
        if self.arrival_time is None:
            print("DEBUG: PAUSA: arrival_time não definido")
            return
            
        time_elapsed = time.time() - self.arrival_time
        print(f"DEBUG: PAUSA: Tempo decorrido: {time_elapsed:.1f}s / {self.arrival_pause_time}s")
        
        if time_elapsed > self.arrival_pause_time:
            print("DEBUG: PAUSA: Tempo de pausa concluído, verificando se deve retornar")
            self.is_paused_at_destination = False
            
            if self.should_return_to_base:
                print("🎯 INICIANDO RETORNO AUTOMÁTICO: Chamando _return_to_base_direct()")
                self._return_to_base_direct()  # 🎯 SUA SOLUÇÃO GENIAL: Retorno direto!
            else:
                print("DEBUG: PAUSA: Retorno automático desabilitado, finalizando navegação")
                self._finalize_navigation()
        else:
            # Ainda em pausa
            remaining_time = self.arrival_pause_time - time_elapsed
            print(f"DEBUG: PAUSA: Aguardando mais {remaining_time:.1f}s antes do retorno")

    def manual_turn_left(self):
        """🔄 GIRO MANUAL ESQUERDA: Gira o robô 22° para a esquerda"""
        print("🔄 GIRO MANUAL: Girando 22° para a esquerda")
        
        # Para qualquer movimento atual
        self.motors.stop()
        time.sleep(0.2)
        
        # 🎯 CORREÇÃO: Força aumentada para giro efetivo
        turn_angle = 22.0  # graus
        
        # 🎯 CORREÇÃO CRÍTICA: Direção INVERTIDA para sincronização
        # Para girar ESQUERDA: motor esquerdo para trás, direito para frente (INVERTIDO)
        left_speed = -60  # Motor esquerdo para TRÁS (INVERTIDO)
        right_speed = 60  # Motor direito para FRENTE (INVERTIDO)
        
        print(f"🔄 GIRO MANUAL: Aplicando velocidade {left_speed}/{right_speed} para giro de {turn_angle}°")
        self.motors.set_speed(left_speed, right_speed)
        
        # 🎯 CORREÇÃO: Tempo reduzido para 22° preciso
        turn_time = 0.5  # Tempo reduzido para giro mais preciso
        print(f"🔄 GIRO MANUAL: Tempo de giro: {turn_time}s")
        
        # Aguarda o tempo calculado
        time.sleep(turn_time)
        
        # Para os motores
        self.motors.stop()
        
        # Atualiza o ângulo do robô
        self.current_angle = (self.current_angle - turn_angle) % 360
        print(f"🔄 GIRO MANUAL: Giro concluído. Novo ângulo: {self.current_angle:.1f}°")

    def manual_turn_right(self):
        """🔄 GIRO MANUAL DIREITA: Gira o robô 22° para a direita"""
        print("🔄 GIRO MANUAL: Girando 22° para a direita")
        
        # Para qualquer movimento atual
        self.motors.stop()
        time.sleep(0.2)
        
        # 🎯 CORREÇÃO: Força aumentada para giro efetivo
        turn_angle = 22.0  # graus
        
        # 🎯 CORREÇÃO CRÍTICA: Direção INVERTIDA para sincronização
        # Para girar DIREITA: motor esquerdo para frente, direito para trás (INVERTIDO)
        left_speed = 60   # Motor esquerdo para FRENTE (INVERTIDO)
        right_speed = -60 # Motor direito para TRÁS (INVERTIDO)
        
        print(f"🔄 GIRO MANUAL: Aplicando velocidade {left_speed}/{right_speed} para giro de {turn_angle}°")
        self.motors.set_speed(left_speed, right_speed)
        
        # 🎯 CORREÇÃO: Tempo reduzido para 22° preciso
        turn_time = 0.5  # Tempo reduzido para giro mais preciso
        print(f"🔄 GIRO MANUAL: Tempo de giro: {turn_time}s")
        
        # Aguarda o tempo calculado
        time.sleep(turn_time)
        
        # Para os motores
        self.motors.stop()
        
        # Atualiza o ângulo do robô
        self.current_angle = (self.current_angle + turn_angle) % 360
        print(f"🔄 GIRO MANUAL: Giro concluído. Novo ângulo: {self.current_angle:.1f}°")

    def manual_turn_custom(self, angle_degrees, direction='left'):
        """🔄 GIRO MANUAL PERSONALIZADO: Gira o robô um ângulo específico"""
        print(f"🔄 GIRO MANUAL: Girando {angle_degrees}° para {direction}")
        
        # Para qualquer movimento atual
        self.motors.stop()
        time.sleep(0.2)
        
        # 🎯 CORREÇÃO: Força aumentada para giro efetivo
        # 🎯 VELOCIDADE AUMENTADA: 60% da potência máxima para giro efetivo
        
        # 🎯 CORREÇÃO CRÍTICA: Direção INVERTIDA para sincronização
        # Aplica giro na direção especificada
        if direction.lower() == 'left':
            # Para girar ESQUERDA: motor esquerdo para trás, direito para frente (INVERTIDO)
            left_speed = -60  # Motor esquerdo para TRÁS (INVERTIDO)
            right_speed = 60  # Motor direito para FRENTE (INVERTIDO)
            self.current_angle = (self.current_angle - abs(angle_degrees)) % 360
        else:  # right
            # Para girar DIREITA: motor esquerdo para frente, direito para trás (INVERTIDO)
            left_speed = 60   # Motor esquerdo para FRENTE (INVERTIDO)
            right_speed = -60 # Motor direito para TRÁS (INVERTIDO)
            self.current_angle = (self.current_angle + abs(angle_degrees)) % 360
        
        print(f"🔄 GIRO MANUAL: Aplicando velocidade {left_speed}/{right_speed} para giro de {angle_degrees}°")
        self.motors.set_speed(left_speed, right_speed)
        
        # 🎯 TEMPO CALCULADO: Baseado na velocidade real dos motores
        # Para ângulos maiores, tempo proporcional
        base_time = 0.8  # Tempo base para 22°
        turn_time = (abs(angle_degrees) / 22.0) * base_time
        print(f"🔄 GIRO MANUAL: Tempo de giro: {turn_time:.2f}s")
        
        # Aguarda o tempo calculado
        time.sleep(turn_time)
        
        # Para os motores
        self.motors.stop()
        
        print(f"🔄 GIRO MANUAL: Giro concluído. Novo ângulo: {self.current_angle:.1f}°")

    def return_to_base_manual(self):
        """🏠 RETORNO MANUAL: Navega para a base após giro manual com debug completo"""
        print("🏠 RETORNO_MANUAL: Método chamado - iniciando verificação")
        print(f"🏠 RETORNO_MANUAL: Estado atual: {self.navigation_state}")
        print(f"🏠 RETORNO_MANUAL: Posição atual: {self.current_position}")
        print(f"🏠 RETORNO_MANUAL: Ângulo atual: {self.current_angle:.1f}°")
        
        # Verifica se o robô está em um estado válido para retorno
        if self.navigation_state in ["IDLE", "PAUSED_AT_DESTINATION"]:
            print("✅ RETORNO_MANUAL: Estado válido, iniciando retorno à base")
            # Inicia o retorno à base
            self._return_to_base_direct()
        else:
            print("⚠️ RETORNO_MANUAL: Robô não está em estado válido para retorno")
            print(f"   Estado atual: {self.navigation_state}")
            print("🔄 RETORNO_MANUAL: Forçando reset para estado válido")
            # Força reset para estado válido
            self.reset_to_initial_state()
            print(f"🔄 RETORNO_MANUAL: Estado após reset: {self.navigation_state}")
            self._return_to_base_direct()
        
        print(f"🏠 RETORNO_MANUAL: Método concluído - Estado final: {self.navigation_state}")
