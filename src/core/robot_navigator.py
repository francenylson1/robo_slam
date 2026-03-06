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
        # 🎯 CORREÇÃO 3: base_position é definido apenas uma vez e NUNCA é alterado durante a navegação
        # Isso garante que o robô sempre retorne à posição base exata
        self.base_position = ROBOT_INITIAL_POSITION
        self.is_adjusting_final_angle = False
        self.navigation_state = "IDLE"  # IDLE, ORIENTING_TO_TARGET, NAVIGATING, RETURNING, COMPLETED
        self.speed_multiplier = 1.0  # Fator de velocidade inicial (100%)
        
        # Inicializa o PathFinder com as dimensões do mapa do config e grid size consistente
        # 🎯 ADAPTAÇÃO PARA MAPAS PGM: Inicializa com origem padrão (0,0), será atualizado quando PGM for carregado
        self.path_finder = PathFinder(
            width=int(MAP_WIDTH / MAP_GRID_SIZE),
            height=int(MAP_HEIGHT / MAP_GRID_SIZE),
            grid_size=MAP_GRID_SIZE,
            map_origin=(0.0, 0.0)  # Será atualizado quando mapa PGM for carregado
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
        
        # 🎯 NAVEGAÇÃO DIRETA SIMPLES: Flag para alternar entre navegação complexa e simples
        self.use_direct_navigation = True  # True = navegação direta simples, False = pathfinding
        
        # BNO08x: integração para correção de rumo e ângulo (Fase 2)
        self._get_bno_yaw = None
        self._bno_yaw_ref = None
        # Offset para alinhar BNO ao referencial do mapa (0° BNO = direção do mapa no 1º uso)
        self._bno_yaw_offset = None
        if is_raspberry_pi():
            try:
                from tools.bno08x_init import init_bno
                _bno, self._get_bno_yaw = init_bno(do_reset_cycle=False, verbose=False)
                if self._get_bno_yaw is not None:
                    print("DEBUG: BNO08x integrado ao navegador (correção de rumo e ângulo).")
                else:
                    self._get_bno_yaw = None
            except Exception as e:
                print(f"DEBUG: BNO08x não disponível no navegador: {e}")
                self._get_bno_yaw = None
        
        print(f"DEBUG: Posição inicial definida: {self.current_position}")
        print(f"DEBUG: Ângulo inicial definido: {self.current_angle}°")
        print(f"DEBUG: Base position definida: {self.base_position}")
        print(f"DEBUG: ROBOT_INITIAL_ANGLE importado: {ROBOT_INITIAL_ANGLE}°")
        print(f"DEBUG: ROBOT_INITIAL_POSITION importado: {ROBOT_INITIAL_POSITION}")
        
        print(f"DEBUG: Área proibida configurada no navegador")
        
    def reset_to_initial_state(self, preserve_position: bool = False):
        """
        Reseta o robô para o estado inicial.
        
        Args:
            preserve_position: Se True, preserva a posição atual do robô (útil quando usando mapas PGM)
        """
        print("🔄 ===== RESETANDO ROBÔ PARA ESTADO INICIAL =====")
        print(f"🔄 Posição atual antes do reset: {self.current_position}")
        print(f"🔄 Preservar posição: {preserve_position}")
        print(f"🔄 Estado anterior - navigation_active: {self.navigation_active}")
        print(f"🔄 Estado anterior - is_returning_to_base: {self.is_returning_to_base}")
        print(f"🔄 Estado anterior - navigation_state: {self.navigation_state}")
        
        # Preserva as áreas proibidas durante o reset
        preserved_forbidden_areas = self.forbidden_areas.copy()
        
        # 🎯 CORREÇÃO 3: Preserva base_position durante o reset (NUNCA altera)
        preserved_base_position = self.base_position
        
        # 🎯 ADAPTAÇÃO PARA MAPAS PGM: Preserva posição se solicitado
        if not preserve_position:
            # ETAPA 2: Correção do "Pulo" - NÃO reseta a posição/ângulo.
            # A nova navegação deve começar da posição final real da navegação anterior.
            # self.current_position = ROBOT_INITIAL_POSITION
            # self.current_angle = ROBOT_INITIAL_ANGLE
            pass
        else:
            print(f"🔄 Posição preservada: {self.current_position}")
        
        # Re-anclar BNO ao referencial do mapa na próxima atualização de pose
        self._bno_yaw_offset = None
        self._bno_yaw_ref = None
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
        
        # 🎯 CORREÇÃO: Reseta contador de estabilidade ao resetar estado
        if hasattr(self, '_orient_stability_counter'):
            self._orient_stability_counter = 0
        
        # Restaura as áreas proibidas
        self.forbidden_areas = preserved_forbidden_areas
        self.path_finder.set_forbidden_areas(preserved_forbidden_areas)
        
        # 🎯 CORREÇÃO 3: Restaura base_position (garante que nunca seja alterado)
        self.base_position = preserved_base_position
        
        # Para os motores
        self.motors.stop()
        
        print("✅ ===== RESET CONCLUÍDO =====")
        print(f"✅ Posição resetada: {self.current_position}, Ângulo: {self.current_angle}°")
        print(f"✅ navigation_active: {self.navigation_active}")
        print(f"✅ is_returning_to_base: {self.is_returning_to_base}")
        print(f"✅ navigation_state: {self.navigation_state}")
        print(f"✅ Áreas proibidas preservadas: {len(self.forbidden_areas)}")
        print("=" * 60)
        
    def set_pose(self, x: float, y: float, angle_deg: float):
        """
        Define posição e ângulo do robô (ex.: ao carregar mapa PGM ou "definir robô aqui").
        Re-ancla o BNO ao novo referencial na próxima atualização de pose.
        """
        self.current_position = (float(x), float(y))
        self.current_angle = self._normalize_angle_deg(float(angle_deg))
        self._bno_yaw_offset = None
        self._bno_yaw_ref = None

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
            self._orient_towards_target()

        elif self.navigation_state == "NAVIGATING_TO_DESTINATION":
            self._handle_navigation_to_destination()

        elif self.navigation_state == "FINAL_APPROACH_DESTINATION":
            if self._stable_final_approach(self.original_destination):
                self._transition_to_paused_at_destination()
        
        elif self.navigation_state == "PAUSED_AT_DESTINATION":
            self._handle_pause_at_destination()

        elif self.navigation_state == "RETURNING_TO_BASE":
            self._handle_return_to_base()

        elif self.navigation_state == "FINAL_APPROACH_BASE":
            # 🎯 CORREÇÃO: Usa base_position diretamente para consistência
            base_target = self.base_position if self.use_direct_navigation else (self.path[-1] if self.path else self.base_position)
            if self._stable_final_approach(base_target):
                self._start_final_angle_adjustment()

        elif self.navigation_state == "ADJUSTING_FINAL_ANGLE":
            self._adjust_final_angle()
        
        elif self.navigation_state == "COMPLETED":
            # 🎯 CORREÇÃO: Se o estado já é COMPLETED, garante que a navegação está finalizada
            if self.navigation_active:
                print("⚠️ AVISO: Estado COMPLETED mas navigation_active=True, forçando finalização")
                self._finalize_navigation()

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
        # 🎯 CORREÇÃO: Reseta contador de estabilidade ao finalizar navegação
        if hasattr(self, '_orient_stability_counter'):
            self._orient_stability_counter = 0
        print("DEBUG: === NAVEGAÇÃO FINALIZADA ===")
        
    def _calculate_and_execute_return_angle(self):
        """Calcula o ângulo necessário para retornar à base e inicia o giro.
        Só executa se should_return_to_base for True (evita retorno virtual/físico indesejado).
        """
        if not self.should_return_to_base:
            print("DEBUG: Retorno à base NÃO solicitado — finalizando navegação no destino.")
            self._finalize_navigation()
            return
        print("DEBUG: === CALCULANDO ÂNGULO DE RETORNO ===")
        print(f"🔍 RETORNO: Posição atual: {self.current_position}")
        print(f"🔍 RETORNO: Base position: {self.base_position}")
        print(f"🔍 RETORNO: Áreas proibidas configuradas: {len(self.forbidden_areas)}")
        
        # 🚫 CORREÇÃO CRÍTICA: SEMPRE verifica áreas proibidas no retorno, independente de use_direct_navigation
        # Isso garante que o robô nunca passe por áreas proibidas no retorno
        
        # 🎯 CORREÇÃO: Garante que o obstacle_grid está atualizado antes de verificar
        if self.forbidden_areas and len(self.forbidden_areas) > 0:
            # Força atualização do obstacle_grid se necessário
            if len(self.path_finder.obstacle_grid) == 0:
                print(f"⚠️ RETORNO: obstacle_grid vazio, forçando atualização...")
                self.path_finder.set_forbidden_areas(self.forbidden_areas)
        
        # 🎯 CORREÇÃO CRÍTICA: Se há áreas proibidas configuradas, SEMPRE usa PathFinder no retorno
        # Isso garante que o robô nunca passe por áreas proibidas, mesmo que a verificação falhe
        has_forbidden_areas = self.forbidden_areas and len(self.forbidden_areas) > 0
        
        if has_forbidden_areas:
            # Se há áreas proibidas, verifica se o caminho direto passa por elas
            path_intersects_forbidden = self._check_path_intersects_forbidden_areas(
                self.current_position, self.base_position
            )
        else:
            path_intersects_forbidden = False
        
        # 🎯 CORREÇÃO CRÍTICA: Se há áreas proibidas configuradas, SEMPRE usa PathFinder no retorno
        # Isso garante que o robô nunca passe por áreas proibidas, mesmo que a verificação falhe
        if has_forbidden_areas:
                print(f"🚫 ÁREA PROIBIDA CONFIGURADA - SEMPRE usando PathFinder no retorno!")
                print(f"🚫 Calculando caminho de retorno que evita áreas proibidas...")
                
                # 🎯 CORREÇÃO CRÍTICA: Garante que o obstacle_grid está atualizado ANTES de calcular o caminho
                if len(self.path_finder.obstacle_grid) == 0:
                    print(f"⚠️ RETORNO: obstacle_grid vazio, forçando atualização antes de calcular caminho...")
                    self.path_finder.set_forbidden_areas(self.forbidden_areas)
                    print(f"🔍 RETORNO: Após atualização, obstacle_grid tem {len(self.path_finder.obstacle_grid)} células")
                
                # Usa PathFinder para calcular caminho que evita áreas proibidas
                path_to_base = self.path_finder.find_path(self.current_position, self.base_position)
                
                if not path_to_base or len(path_to_base) < 2:
                    print(f"🚨 ERRO CRÍTICO: Não foi possível encontrar caminho de retorno que evite áreas proibidas!")
                    print(f"🚨 PathFinder retornou: {path_to_base}")
                    print(f"🚨 Posição atual: {self.current_position}, Base: {self.base_position}")
                    print(f"🚨 Áreas proibidas: {len(self.forbidden_areas)}")
                    print(f"🚨 obstacle_grid: {len(self.path_finder.obstacle_grid)} células")
                    # 🚫 NÃO PERMITE NAVEGAÇÃO DIRETA quando há áreas proibidas - isso seria perigoso!
                    print(f"🚨 ABORTANDO retorno - não é seguro navegar diretamente com áreas proibidas!")
                    self._finalize_navigation()
                    return
                
                # 🎯 VERIFICAÇÃO CRÍTICA: Verifica se o caminho retornado realmente evita áreas proibidas
                # Se o caminho tem apenas 2 pontos (start, goal), pode ser um caminho direto que passa por áreas proibidas
                if len(path_to_base) == 2:
                    # Verifica se o caminho direto passa por áreas proibidas
                    direct_path_intersects = self._check_path_intersects_forbidden_areas(
                        path_to_base[0], path_to_base[1]
                    )
                    if direct_path_intersects:
                        print(f"🚨 ERRO CRÍTICO: PathFinder retornou caminho direto que PASSA POR ÁREAS PROIBIDAS!")
                        print(f"🚨 Caminho: {path_to_base[0]} → {path_to_base[1]}")
                        print(f"🚨 Isso não deveria acontecer! PathFinder deveria ter evitado áreas proibidas.")
                        print(f"🚨 ABORTANDO retorno - caminho não é seguro!")
                        self._finalize_navigation()
                        return
                    else:
                        print(f"✅ Caminho direto verificado - não passa por áreas proibidas")
                else:
                    # Verifica cada segmento do caminho
                    path_has_obstacles = False
                    for i in range(len(path_to_base) - 1):
                        segment_intersects = self._check_path_intersects_forbidden_areas(
                            path_to_base[i], path_to_base[i + 1]
                        )
                        if segment_intersects:
                            print(f"🚨 ERRO CRÍTICO: Segmento {i} do caminho ({path_to_base[i]} → {path_to_base[i+1]}) PASSA POR ÁREAS PROIBIDAS!")
                            path_has_obstacles = True
                            break
                    
                    if path_has_obstacles:
                        print(f"🚨 ABORTANDO retorno - caminho calculado não é seguro!")
                        self._finalize_navigation()
                        return
                
                print(f"✅ Caminho de retorno calculado e VERIFICADO com {len(path_to_base)} waypoints evitando áreas proibidas")
                
                # Re-anclar BNO ao início do retorno para evitar deriva/caos na transição POI → base
                self._bno_yaw_offset = None
                self._bno_yaw_ref = None
                # 🎯 CORREÇÃO 1: Garante que o caminho comece na posição EXATA atual e termine na base EXATA
                # Substitui o primeiro ponto pela posição atual exata
                if len(path_to_base) > 0:
                    path_to_base[0] = self.current_position
                # Garante que o último ponto seja a base exata
                if len(path_to_base) > 0:
                    path_to_base[-1] = self.base_position
                
                # Configura navegação com pathfinding
                self.path = path_to_base
                self.is_returning_to_base = True
                
                # 🎯 CORREÇÃO: Inicia no primeiro waypoint real (índice 1), não na posição atual (índice 0)
                # Se o caminho tem apenas 2 pontos (posição atual + base), vai direto à base
                if len(self.path) > 2:
                    self.path_index = 1  # Começa no primeiro waypoint real
                    first_waypoint = self.path[1]
                elif len(self.path) > 1:
                    self.path_index = 1  # Vai direto à base (último ponto)
                    first_waypoint = self.path[1]
                else:
                    self.path_index = 0
                    first_waypoint = self.base_position
                
                # 🎯 CORREÇÃO: Atualiza current_target para o primeiro waypoint
                self.current_target = first_waypoint
                
                # 🎯 CORREÇÃO: Emite sinal para atualizar o caminho na interface
                # O caminho será atualizado automaticamente quando a UI verificar self.path
                print(f"🎯 RETORNO: Caminho de retorno configurado com {len(self.path)} waypoints")
                # Emite sinal de atualização de status para que a interface atualize o caminho
                self.navigation_status_updated.emit(self.get_navigation_status())
                
                dx = first_waypoint[0] - self.current_position[0]
                dy = first_waypoint[1] - self.current_position[1]
                target_angle = math.degrees(math.atan2(dy, dx))
                
                # Normaliza target_angle para [0, 360)
                if target_angle < 0:
                    target_angle += 360
                
                # Normaliza ângulo atual para [0, 360)
                current_angle_normalized = self.current_angle
                if current_angle_normalized < 0:
                    current_angle_normalized += 360
                
                # Calcula erro angular
                angle_error = (target_angle - current_angle_normalized + 180) % 360 - 180
                
                print(f"🚫 RETORNO COM DESVIO: Primeiro waypoint: {first_waypoint}")
                print(f"🚫 RETORNO COM DESVIO: target_angle={target_angle:.1f}°, erro={angle_error:.1f}°")
                
                # Define estado inicial
                if abs(angle_error) < 20.0:
                    print(f"🚫 RETORNO COM DESVIO: Já alinhado, iniciando navegação")
                    self.navigation_state = "RETURNING_TO_BASE"
                else:
                    print(f"🚫 RETORNO COM DESVIO: Orientando para primeiro waypoint")
                    self.navigation_state = "ORIENTING_TO_TARGET"
                
                return
        
        # Se não há áreas proibidas no caminho, verifica se deve usar navegação direta
        # 🎯 CORREÇÃO: Só usa navegação direta se use_direct_navigation estiver habilitado E não houver áreas proibidas
        if self.use_direct_navigation and not has_forbidden_areas:
            # Se não há áreas proibidas no caminho, usa navegação direta
            print(f"✅ Caminho de retorno direto livre de áreas proibidas - usando navegação direta")
            print("🎯 RETORNO DIRETA: Configurando navegação direta à base")
            self._bno_yaw_offset = None
            self._bno_yaw_ref = None
            # 🎯 CORREÇÃO 1: Garante que o caminho comece na posição EXATA atual e termine na base EXATA
            self.path = [self.current_position, self.base_position]
            self.path_index = 0
            self.current_target = self.base_position
            self.is_returning_to_base = True
            
            # Calcula direção direta para a base
            dx = self.base_position[0] - self.current_position[0]
            dy = self.base_position[1] - self.current_position[1]
            distance = math.sqrt(dx*dx + dy*dy)
            target_angle = math.degrees(math.atan2(dy, dx))
            
            # Normaliza target_angle para [0, 360)
            if target_angle < 0:
                target_angle += 360
            
            # Normaliza ângulo atual para [0, 360)
            current_angle_normalized = self.current_angle
            if current_angle_normalized < 0:
                current_angle_normalized += 360
            
            # Calcula erro angular
            angle_error = (target_angle - current_angle_normalized + 180) % 360 - 180
            
            print(f"🎯 RETORNO DIRETA: Base em {self.base_position}, Distância: {distance:.2f}m")
            print(f"🎯 RETORNO DIRETA: target_angle={target_angle:.1f}°, current={current_angle_normalized:.1f}°, erro={angle_error:.1f}°")
            
            # Se já está bem alinhado (tolerância de 10°), vai direto
            if abs(angle_error) < 10.0:
                print(f"🎯 RETORNO DIRETA: Já alinhado, iniciando movimento direto")
                self.navigation_state = "RETURNING_TO_BASE"
            else:
                print(f"🔄 RETORNO DIRETA: Giro necessário de {angle_error:.1f}°")
                self.navigation_state = "ORIENTING_TO_TARGET"
            return
        
        # Navegação com pathfinding (sempre usa quando há áreas proibidas ou quando use_direct_navigation está desabilitado)
        print(f"🔍 RETORNO: Usando PathFinder para calcular caminho de retorno...")
        path_to_base = self.path_finder.find_path(self.current_position, self.base_position)
        if not path_to_base or len(path_to_base) < 2:
            print("⚠️ ERRO: Não foi possível calcular o caminho de volta para a base.")
            print("⚠️ Tentando navegação direta mesmo assim...")
            # Fallback: tenta navegação direta mesmo com erro
            path_to_base = [self.current_position, self.base_position]
        else:
            print(f"✅ Caminho de retorno calculado com {len(path_to_base)} waypoints")
        
        self._bno_yaw_offset = None
        self._bno_yaw_ref = None
        # 🎯 CORREÇÃO 1: Garante que o caminho comece na posição EXATA atual e termine na base EXATA
        if len(path_to_base) > 0:
            path_to_base[0] = self.current_position
        if len(path_to_base) > 0:
            path_to_base[-1] = self.base_position
            
        self.path = path_to_base
        self.is_returning_to_base = True
        
        # 🎯 CORREÇÃO: Inicia no primeiro waypoint real (índice 1), não na posição atual (índice 0)
        if len(self.path) > 2:
            self.path_index = 1  # Começa no primeiro waypoint real
            self.current_target = self.path[1]
            first_waypoint = self.path[1]
        elif len(self.path) > 1:
            self.path_index = 1  # Vai direto à base (último ponto)
            self.current_target = self.path[1]
            first_waypoint = self.path[1]
        else:
            self.path_index = 0
            self.current_target = self.base_position
            first_waypoint = self.base_position
        
        # 🎯 CORREÇÃO: Emite sinal para atualizar o caminho na interface
        print(f"🎯 RETORNO: Caminho de retorno configurado com {len(self.path)} waypoints")
        self.navigation_status_updated.emit(self.get_navigation_status())
        
        dx = first_waypoint[0] - self.current_position[0]
        dy = first_waypoint[1] - self.current_position[1]
        target_angle = math.degrees(math.atan2(dy, dx))
        
        # Normaliza target_angle para [0, 360)
        if target_angle < 0:
            target_angle += 360
        
        # Normaliza ângulo atual para [0, 360)
        current_angle_normalized = self.current_angle
        if current_angle_normalized < 0:
            current_angle_normalized += 360
        
        # Calcula erro angular
        angle_error = (target_angle - current_angle_normalized + 180) % 360 - 180
        
        print(f"🚫 RETORNO COM PATHFINDER: Primeiro waypoint: {first_waypoint}")
        print(f"🚫 RETORNO COM PATHFINDER: target_angle={target_angle:.1f}°, erro={angle_error:.1f}°")
        
        # Define estado inicial
        if abs(angle_error) < 20.0:
            print(f"🚫 RETORNO COM PATHFINDER: Já alinhado, iniciando navegação")
            self.navigation_state = "RETURNING_TO_BASE"
        else:
            print(f"🚫 RETORNO COM PATHFINDER: Orientando para primeiro waypoint")
            self.navigation_state = "ORIENTING_TO_TARGET"

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
        
        # 🎯 CORREÇÃO: Inicializa timer para timeout do ajuste de ângulo
        if not hasattr(self, 'final_angle_adjustment_start_time'):
            self.final_angle_adjustment_start_time = time.time()
        else:
            self.final_angle_adjustment_start_time = time.time()
        
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

    def navigate_to_and_return(self, destination: Tuple[float, float], should_return_to_base: bool = True) -> None:
        """
        Navega até o destino e opcionalmente retorna à base (compatível com mapas PGM)
        
        Args:
            destination: Coordenadas do destino (x, y) em metros
            should_return_to_base: Se True, retorna à base após chegar ao destino.
                                  Se False, para no destino e aguarda novo comando.
        """
        print(f"DEBUG: ===== NAVEGAÇÃO {'DIRETA SIMPLES' if self.use_direct_navigation else 'INTELIGENTE'} =====")
        print(f"DEBUG: Destino: {destination}")
        print(f"DEBUG: Posição atual: {self.current_position}, Ângulo atual: {self.current_angle}°")
        print(f"DEBUG: Base position: {self.base_position}")
        print(f"DEBUG: Retorno automático: {'SIM' if should_return_to_base else 'NÃO'}")
        
        # Preserva a posição atual ao fazer reset (importante para mapas PGM)
        self.reset_to_initial_state(preserve_position=True)
        
        self.navigation_active = True
        self.start_time = time.time()
        self.is_returning_to_base = False
        self.should_return_to_base = should_return_to_base  # 🎯 Usa o parâmetro do usuário (checkbox)
        self.final_approach_start_time = None
        self._navigation_had_return_to_base = should_return_to_base  # para mensagem ao concluir
        
        # 🚫 CORREÇÃO CRÍTICA: Se há áreas proibidas configuradas, SEMPRE usa PathFinder
        # Isso garante que o robô nunca passe por áreas proibidas, independente de use_direct_navigation
        has_forbidden_areas = self.forbidden_areas and len(self.forbidden_areas) > 0
        
        if has_forbidden_areas:
            # Se há áreas proibidas, SEMPRE usa PathFinder (não importa use_direct_navigation)
            print(f"🚫 ÁREAS PROIBIDAS CONFIGURADAS - SEMPRE usando PathFinder para navegação!")
            print(f"🚫 Calculando caminho que evita áreas proibidas...")
            
            # 🎯 CORREÇÃO CRÍTICA: Garante que o obstacle_grid está atualizado ANTES de calcular o caminho
            if len(self.path_finder.obstacle_grid) == 0:
                print(f"⚠️ NAVEGAÇÃO: obstacle_grid vazio, forçando atualização antes de calcular caminho...")
                self.path_finder.set_forbidden_areas(self.forbidden_areas)
                print(f"🔍 NAVEGAÇÃO: Após atualização, obstacle_grid tem {len(self.path_finder.obstacle_grid)} células")
            
            path_to_destination = self.path_finder.find_path(self.current_position, destination)
            
            # 🎯 VERIFICAÇÃO CRÍTICA: Verifica se o caminho retornado realmente evita áreas proibidas
            if not path_to_destination or len(path_to_destination) < 2:
                print(f"🚨 ERRO CRÍTICO: PathFinder não retornou caminho válido!")
                print(f"🚨 PathFinder retornou: {path_to_destination}")
                print(f"🚨 Isso pode significar que não há caminho possível entre a posição atual e o destino.")
                print(f"🚨 Verifique se há áreas proibidas bloqueando completamente o caminho.")
                # Mostra mensagem de erro ao usuário
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(None, "Erro de Navegação", 
                    f"Não foi possível encontrar um caminho seguro até o destino.\n\n"
                    f"Possíveis causas:\n"
                    f"- Áreas proibidas bloqueando completamente o caminho\n"
                    f"- Destino inacessível\n"
                    f"- Configuração incorreta do PathFinder\n\n"
                    f"Verifique as áreas proibidas e tente novamente.")
                self.navigation_active = False
                # 🎯 CORREÇÃO: Define estado para IDLE mas marca que foi erro (não conclusão)
                self.navigation_state = "IDLE"
                # Não chama _finalize_navigation para evitar mensagem de "navegação concluída"
                return
            
            # Verifica se o caminho realmente evita áreas proibidas
            if len(path_to_destination) == 2:
                # Caminho direto - verifica se não passa por áreas proibidas
                direct_path_intersects = self._check_path_intersects_forbidden_areas(
                    path_to_destination[0], path_to_destination[1]
                )
                if direct_path_intersects:
                    print(f"🚨 ERRO CRÍTICO: PathFinder retornou caminho direto que PASSA POR ÁREAS PROIBIDAS!")
                    print(f"🚨 ABORTANDO navegação - caminho não é seguro!")
                    self.navigation_active = False
                    return
            else:
                # Verifica cada segmento do caminho
                for i in range(len(path_to_destination) - 1):
                    segment_intersects = self._check_path_intersects_forbidden_areas(
                        path_to_destination[i], path_to_destination[i + 1]
                    )
                    if segment_intersects:
                        print(f"🚨 ERRO CRÍTICO: Segmento {i} do caminho PASSA POR ÁREAS PROIBIDAS!")
                        print(f"🚨 ABORTANDO navegação - caminho não é seguro!")
                        self.navigation_active = False
                        return
            
            print(f"✅ Caminho VERIFICADO com {len(path_to_destination)} waypoints evitando áreas proibidas")
        elif self.use_direct_navigation:
            # Se não há áreas proibidas E use_direct_navigation está habilitado, usa navegação direta
            self._navigate_direct_simple(destination)
            return
        else:
            # Navegação com pathfinding (código original - quando não há áreas proibidas e use_direct_navigation está desabilitado)
            path_to_destination = self.path_finder.find_path(self.current_position, destination)
            if not path_to_destination or len(path_to_destination) < 2:
                print("🚨 ERRO CRÍTICO - Não foi possível encontrar caminho para o destino")
                self.navigation_active = False
                # 🎯 CORREÇÃO: Define estado para IDLE mas marca que foi erro (não conclusão)
                self.navigation_state = "IDLE"
                # Não chama _finalize_navigation para evitar mensagem de "navegação concluída"
                return

        self.path = path_to_destination
        self.path_index = 0
        
        self.original_destination = destination
        self.destination_index = len(path_to_destination) - 1
        
        # 🎯 CORREÇÃO CRÍTICA: Se o caminho tem apenas 2 pontos (start e goal), 
        # e o primeiro ponto é a posição atual, usa o goal como target
        # Caso contrário, usa o próximo waypoint (índice 1) se disponível
        if len(self.path) > 1:
            # Se o primeiro ponto é muito próximo da posição atual (provavelmente é o start exato),
            # usa o segundo ponto como target inicial
            dist_to_first = math.sqrt((self.path[0][0] - self.current_position[0])**2 + 
                                     (self.path[0][1] - self.current_position[1])**2)
            if dist_to_first < 0.05:  # Menos de 5cm de distância
                self.current_target = self.path[1]  # Usa o próximo waypoint
                self.path_index = 1  # Começa no segundo ponto
            else:
                self.current_target = self.path[0]  # Usa o primeiro ponto
        else:
            self.current_target = self.path[0] if len(self.path) > 0 else destination
        
        print(f"DEBUG: Caminho calculado com {len(self.path)} pontos.")
        
        # 🎯 CORREÇÃO CIRÚRGICA: Verificação inteligente para pular orientação desnecessária
        dx = self.current_target[0] - self.current_position[0]
        dy = self.current_target[1] - self.current_position[1]
        target_angle = math.degrees(math.atan2(dy, dx))
        angle_error = abs((target_angle - self.current_angle + 180) % 360 - 180)
        
        # 🎯 CORREÇÃO APRIMORADA: Tolerância ainda mais permissiva para evitar loops
        # Se o robô já está bem alinhado (tolerância de 20°), pula a orientação
        if angle_error < 20.0:
            print(f"🎯 PULO INTELIGENTE: Destino já alinhado (erro: {angle_error:.1f}°), iniciando navegação direta")
            self.navigation_state = "NAVIGATING_TO_DESTINATION"
        else:
            print(f"🔄 MUDANÇA DE FASE: IDLE → ORIENTING_TO_TARGET (erro: {angle_error:.1f}°)")
            self.navigation_state = "ORIENTING_TO_TARGET"
    
    def _check_path_intersects_forbidden_areas(self, start: Tuple[float, float], end: Tuple[float, float]) -> bool:
        """
        Verifica se o caminho direto entre dois pontos passa por áreas proibidas.
        
        Args:
            start: Ponto inicial (x, y) em coordenadas do mundo
            end: Ponto final (x, y) em coordenadas do mundo
            
        Returns:
            True se o caminho intersecta áreas proibidas, False caso contrário
        """
        # Se não há áreas proibidas, o caminho está livre
        if not self.forbidden_areas or len(self.forbidden_areas) == 0:
            print(f"🔍 VERIFICAÇÃO ÁREAS PROIBIDAS: Nenhuma área proibida configurada")
            return False
        
        print(f"🔍 VERIFICAÇÃO ÁREAS PROIBIDAS: Verificando caminho de {start} para {end}")
        print(f"🔍 VERIFICAÇÃO ÁREAS PROIBIDAS: {len(self.forbidden_areas)} áreas proibidas configuradas")
        print(f"🔍 VERIFICAÇÃO ÁREAS PROIBIDAS: obstacle_grid tem {len(self.path_finder.obstacle_grid)} células marcadas")
        
        # 🎯 CORREÇÃO: Garante que o obstacle_grid está atualizado
        if len(self.path_finder.obstacle_grid) == 0:
            print(f"⚠️ VERIFICAÇÃO ÁREAS PROIBIDAS: obstacle_grid vazio! Forçando atualização...")
            self.path_finder.set_forbidden_areas(self.forbidden_areas)
            print(f"🔍 VERIFICAÇÃO ÁREAS PROIBIDAS: Após atualização, obstacle_grid tem {len(self.path_finder.obstacle_grid)} células")
        
        # Usa o método do PathFinder para verificar interseção com obstáculos
        intersects = self.path_finder._line_intersects_obstacles(start, end)
        
        if intersects:
            print(f"🚫 VERIFICAÇÃO ÁREAS PROIBIDAS: Caminho INTERSECTA áreas proibidas!")
        else:
            print(f"✅ VERIFICAÇÃO ÁREAS PROIBIDAS: Caminho NÃO intersecta áreas proibidas (livre)")
        
        return intersects
    
    def _navigate_direct_simple(self, destination: Tuple[float, float]) -> None:
        """
        🎯 NAVEGAÇÃO DIRETA SIMPLES COM DESVIO DE ÁREAS PROIBIDAS:
        - Verifica se o caminho direto passa por áreas proibidas
        - Se sim, usa PathFinder para calcular caminho que evita áreas
        - Se não, usa navegação direta (mais rápida)
        """
        print(f"🎯 NAVEGAÇÃO DIRETA SIMPLES ATIVADA (COM DESVIO DE ÁREAS PROIBIDAS)")
        print(f"🔍 DEBUG: Destino direto: {destination}")
        print(f"🔍 DEBUG: Posição atual: {self.current_position}")
        print(f"🔍 DEBUG: Ângulo atual: {self.current_angle}°")
        print(f"🔍 DEBUG: Origem do mapa (PathFinder): {self.path_finder.map_origin}")
        print(f"🔍 DEBUG: Áreas proibidas configuradas: {len(self.forbidden_areas)}")
        
        # 🚫 CORREÇÃO CRÍTICA: Se há áreas proibidas configuradas, SEMPRE usa PathFinder
        # Não confia apenas na verificação - se há áreas proibidas, sempre usa PathFinder
        has_forbidden_areas = self.forbidden_areas and len(self.forbidden_areas) > 0
        
        if has_forbidden_areas:
            print(f"🚫 ÁREAS PROIBIDAS CONFIGURADAS - SEMPRE usando PathFinder!")
            print(f"🚫 Calculando caminho que evita áreas proibidas...")
            
            # 🎯 CORREÇÃO CRÍTICA: Garante que o obstacle_grid está atualizado ANTES de calcular o caminho
            if len(self.path_finder.obstacle_grid) == 0:
                print(f"⚠️ NAVEGAÇÃO: obstacle_grid vazio, forçando atualização antes de calcular caminho...")
                self.path_finder.set_forbidden_areas(self.forbidden_areas)
                print(f"🔍 NAVEGAÇÃO: Após atualização, obstacle_grid tem {len(self.path_finder.obstacle_grid)} células")
            
            # Usa PathFinder para calcular caminho que evita áreas proibidas
            path_to_destination = self.path_finder.find_path(self.current_position, destination)
            
            if not path_to_destination or len(path_to_destination) < 2:
                print(f"🚨 ERRO CRÍTICO: Não foi possível encontrar caminho que evite áreas proibidas!")
                print(f"🚨 PathFinder retornou: {path_to_destination}")
                print(f"🚨 Posição atual: {self.current_position}, Destino: {destination}")
                print(f"🚨 Áreas proibidas: {len(self.forbidden_areas)}")
                print(f"🚨 obstacle_grid: {len(self.path_finder.obstacle_grid)} células")
                # 🚫 NÃO PERMITE NAVEGAÇÃO DIRETA quando há áreas proibidas - isso seria perigoso!
                print(f"🚨 ABORTANDO navegação - não é seguro navegar diretamente com áreas proibidas!")
                self.navigation_active = False
                # 🎯 CORREÇÃO: Define estado para IDLE mas marca que foi erro (não conclusão)
                self.navigation_state = "IDLE"
                # Não chama _finalize_navigation para evitar mensagem de "navegação concluída"
                return
            
            # 🎯 VERIFICAÇÃO CRÍTICA: Verifica se o caminho retornado realmente evita áreas proibidas
            # Se o caminho tem apenas 2 pontos (start, goal), pode ser um caminho direto que passa por áreas proibidas
            if len(path_to_destination) == 2:
                # Verifica se o caminho direto passa por áreas proibidas
                direct_path_intersects = self._check_path_intersects_forbidden_areas(
                    path_to_destination[0], path_to_destination[1]
                )
                if direct_path_intersects:
                    print(f"🚨 ERRO CRÍTICO: PathFinder retornou caminho direto que PASSA POR ÁREAS PROIBIDAS!")
                    print(f"🚨 Caminho: {path_to_destination[0]} → {path_to_destination[1]}")
                    print(f"🚨 Isso não deveria acontecer! PathFinder deveria ter evitado áreas proibidas.")
                    print(f"🚨 ABORTANDO navegação - caminho não é seguro!")
                    self.navigation_active = False
                    return
                else:
                    print(f"✅ Caminho direto verificado - não passa por áreas proibidas")
            else:
                # Verifica cada segmento do caminho
                path_has_obstacles = False
                for i in range(len(path_to_destination) - 1):
                    segment_intersects = self._check_path_intersects_forbidden_areas(
                        path_to_destination[i], path_to_destination[i + 1]
                    )
                    if segment_intersects:
                        print(f"🚨 ERRO CRÍTICO: Segmento {i} do caminho ({path_to_destination[i]} → {path_to_destination[i+1]}) PASSA POR ÁREAS PROIBIDAS!")
                        path_has_obstacles = True
                        break
                
                if path_has_obstacles:
                    print(f"🚨 ABORTANDO navegação - caminho calculado não é seguro!")
                    self.navigation_active = False
                    return
            
            print(f"✅ Caminho calculado e VERIFICADO com {len(path_to_destination)} waypoints evitando áreas proibidas")
            
            # 🎯 CORREÇÃO 1: Garante que o caminho comece na posição EXATA atual e termine no destino EXATO
            # Substitui o primeiro ponto pela posição atual exata
            if len(path_to_destination) > 0:
                path_to_destination[0] = self.current_position
            # Garante que o último ponto seja o destino exato
            if len(path_to_destination) > 0:
                path_to_destination[-1] = destination
            
            # Configura navegação com pathfinding
            self.path = path_to_destination
            self.original_destination = destination
            
            # 🎯 CORREÇÃO: Inicia no primeiro waypoint real (índice 1), não na posição atual (índice 0)
            # Se o caminho tem apenas 2 pontos (posição atual + destino), vai direto ao destino
            if len(self.path) > 2:
                self.path_index = 1  # Começa no primeiro waypoint real
                self.current_target = self.path[1]
                first_waypoint = self.path[1]
            elif len(self.path) > 1:
                self.path_index = 1  # Vai direto ao destino (último ponto)
                self.current_target = self.path[1]
                first_waypoint = self.path[1]
            else:
                self.path_index = 0
                self.current_target = destination
                first_waypoint = destination
            
            dx = first_waypoint[0] - self.current_position[0]
            dy = first_waypoint[1] - self.current_position[1]
            target_angle = math.degrees(math.atan2(dy, dx))
            
            # Normaliza target_angle para [0, 360)
            if target_angle < 0:
                target_angle += 360
            
            # Normaliza ângulo atual para [0, 360)
            current_angle_normalized = self.current_angle
            if current_angle_normalized < 0:
                current_angle_normalized += 360
            
            # Calcula erro angular
            angle_error = (target_angle - current_angle_normalized + 180) % 360 - 180
            
            print(f"🚫 NAVEGAÇÃO COM DESVIO: Primeiro waypoint: {first_waypoint}")
            print(f"🚫 NAVEGAÇÃO COM DESVIO: target_angle={target_angle:.1f}°, erro={angle_error:.1f}°")
            
            # Define estado inicial
            if abs(angle_error) < 20.0:
                print(f"🚫 NAVEGAÇÃO COM DESVIO: Já alinhado, iniciando navegação")
                self.navigation_state = "NAVIGATING_TO_DESTINATION"
            else:
                print(f"🚫 NAVEGAÇÃO COM DESVIO: Orientando para primeiro waypoint")
                self.navigation_state = "ORIENTING_TO_TARGET"
            
            return
        
        # Se não há áreas proibidas no caminho, usa navegação direta (código original)
        print(f"✅ Caminho direto livre de áreas proibidas - usando navegação direta")
        
        # 🎯 UNIFICAÇÃO: Normaliza o ângulo atual para [0, 360) para cálculos corretos
        # O ângulo pode estar em [-180, 180] devido à normalização da odometria
        current_angle_normalized = self.current_angle
        if current_angle_normalized < 0:
            current_angle_normalized += 360
        
        # 🎯 CORREÇÃO 1: Garante que o caminho comece na posição EXATA atual e termine no destino EXATO
        # Define o destino como alvo único (sem waypoints intermediários)
        self.original_destination = destination
        self.current_target = destination
        # Caminho mínimo: origem EXATA -> destino EXATO
        self.path = [self.current_position, destination]
        self.path_index = 0
        
        # 🎯 UNIFICAÇÃO: Calcula direção direta para o destino
        # 🎯 CRÍTICO: Usa coordenadas do mundo diretamente (mesma lógica dos mapas não-PGM)
        # As coordenadas já estão em metros do mundo, independente do tipo de mapa
        dx = destination[0] - self.current_position[0]
        dy = destination[1] - self.current_position[1]
        distance = math.sqrt(dx*dx + dy*dy)
        target_angle = math.degrees(math.atan2(dy, dx))
        
        # Normaliza target_angle para [0, 360)
        if target_angle < 0:
            target_angle += 360
        
        # Calcula erro angular considerando ambos os ângulos em [0, 360)
        angle_error = (target_angle - current_angle_normalized + 180) % 360 - 180
        
        print(f"🔍 CÁLCULO DE DIREÇÃO (UNIFICADO - MESMA LÓGICA DOS MAPAS NÃO-PGM):")
        print(f"   Posição atual: ({self.current_position[0]:.3f}, {self.current_position[1]:.3f})m")
        print(f"   Destino: ({destination[0]:.3f}, {destination[1]:.3f})m")
        print(f"   dx = {dx:.3f}m (destino_x - atual_x)")
        print(f"   dy = {dy:.3f}m (destino_y - atual_y)")
        print(f"   atan2({dy:.3f}, {dx:.3f}) = {target_angle:.2f}° (normalizado)")
        print(f"   Distância até destino: {distance:.2f}m")
        print(f"   Ângulo alvo calculado: {target_angle:.1f}°")
        print(f"   Ângulo atual do robô: {self.current_angle:.1f}° (raw) -> {current_angle_normalized:.1f}° (normalizado)")
        print(f"   Erro angular: {angle_error:.1f}°")
        
        # 🎯 DIAGNÓSTICO: Verifica se o erro angular está muito grande (sugere problema de coordenadas)
        if abs(angle_error) > 150:
            print(f"⚠️ ATENÇÃO: Erro angular muito grande ({angle_error:.1f}°)!")
            print(f"⚠️ Isso sugere que o sistema de coordenadas pode estar invertido")
            print(f"⚠️ Ou o ângulo inicial do robô está incorreto")
            print(f"⚠️ Verificando se há problema de origem do mapa...")
            print(f"⚠️ Origem do mapa: {self.path_finder.map_origin}")
            print(f"⚠️ Posição atual: {self.current_position}")
            print(f"⚠️ Destino: {destination}")
            print(f"⚠️ Diferença: dx={dx:.3f}m, dy={dy:.3f}m")
        
        # 🎯 UNIFICAÇÃO: Usa a mesma tolerância que funciona nos mapas não-PGM
        # Se já está bem alinhado (tolerância de 10°), vai direto
        if abs(angle_error) < 10.0:
            print(f"🎯 JÁ ALINHADO: Iniciando movimento direto (erro: {angle_error:.1f}°)")
            self.navigation_state = "NAVIGATING_TO_DESTINATION"
        else:
            print(f"🔄 ORIENTANDO: Giro necessário de {angle_error:.1f}°")
            if angle_error > 0:
                print(f"   → Girar para DIREITA (sentido horário)")
            else:
                print(f"   → Girar para ESQUERDA (sentido anti-horário)")
            self.navigation_state = "ORIENTING_TO_TARGET"

    def get_navigation_status(self) -> dict:
        """Retorna o status atual da navegação"""
        # 🎯 CORREÇÃO CRÍTICA: Se o estado é COMPLETED, sempre retorna COMPLETED
        # Isso permite que a interface detecte a conclusão mesmo após navigation_active = False
        if self.navigation_state == "COMPLETED":
            return {
                "state": "COMPLETED", "progress": 1.0, "estimated_time_remaining": 0.0,
                "current_target": None, "position": self.current_position, "angle": self.current_angle,
                "is_returning_to_base": False, "is_paused_at_destination": False
            }
        
        if not self.navigation_active:
            return {
                "state": "IDLE", "progress": 0.0, "estimated_time_remaining": 0.0,
                "current_target": None, "position": self.current_position, "angle": self.current_angle,
                "is_returning_to_base": False, "is_paused_at_destination": False
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
        """
        🎯 LÓGICA SIMPLES DE ORIENTAÇÃO COM ESTABILIDADE:
        1. Qual minha direção atual? -> current_angle_normalized
        2. Qual a direção que devo ir? -> target_angle_normalized  
        3. Qual a diferença entre elas? -> angle_error
        4. O que devo fazer: girar para esquerda ou direita?
           - Se angle_error > 0: girar para direita (sentido horário)
           - Se angle_error < 0: girar para esquerda (sentido anti-horário)
        5. CORREÇÃO: Adiciona estabilidade para evitar oscilação
        """
        if self.current_target is None:
            return

        # 🎯 CORREÇÃO: Define tolerância ANTES de usar
        tolerance = 15.0  # Tolerância aumentada para evitar oscilação (era 10°)
        stability_threshold = 5  # Número de iterações consecutivas dentro da tolerância
        
        # Inicializa contador de estabilidade se não existir
        if not hasattr(self, '_orient_stability_counter'):
            self._orient_stability_counter = 0

        # 1. Calcula direção para o alvo
        dx = self.current_target[0] - self.current_position[0]
        dy = self.current_target[1] - self.current_position[1]
        target_angle_raw = math.degrees(math.atan2(dy, dx))
        
        # Normaliza target_angle para [0, 360)
        target_angle_normalized = target_angle_raw
        if target_angle_normalized < 0:
            target_angle_normalized += 360
        
        # 2. Normaliza direção atual para [0, 360)
        current_angle_normalized = self.current_angle
        if current_angle_normalized < 0:
            current_angle_normalized += 360
        
        # 3. Calcula diferença angular (erro)
        # Retorna o menor caminho entre os dois ângulos [-180, 180]
        angle_error = (target_angle_normalized - current_angle_normalized + 180) % 360 - 180
        
        # Log detalhado (apenas a cada 10 chamadas para não poluir)
        if not hasattr(self, '_orient_log_counter'):
            self._orient_log_counter = 0
        self._orient_log_counter += 1
        
        if self._orient_log_counter % 10 == 0 or abs(angle_error) < tolerance:
            print(f"🔄 ORIENTAÇÃO SIMPLES:")
            print(f"   Direção atual: {self.current_angle:.1f}° (raw) -> {current_angle_normalized:.1f}° (normalizado)")
            print(f"   Direção alvo: {target_angle_raw:.1f}° (raw) -> {target_angle_normalized:.1f}° (normalizado)")
            print(f"   Diferença (erro): {angle_error:.1f}°")
            print(f"   Contador de estabilidade: {self._orient_stability_counter}/{stability_threshold}")
            if angle_error > 0:
                print(f"   Ação: Girar para DIREITA (sentido horário) {abs(angle_error):.1f}°")
            elif angle_error < 0:
                print(f"   Ação: Girar para ESQUERDA (sentido anti-horário) {abs(angle_error):.1f}°")
            else:
                print(f"   Ação: Já alinhado!")

        # 🎯 CORREÇÃO: Verifica estabilidade antes de mudar de estado
        # Só muda de estado se o erro estiver dentro da tolerância por várias iterações consecutivas
        if abs(angle_error) < tolerance:
            self._orient_stability_counter += 1
            if self._orient_stability_counter >= stability_threshold:
                # Estável! Pode mudar de estado
                self.motors.stop()
                state_key = "RETURNING_TO_BASE" if self.is_returning_to_base else "NAVIGATING_TO_DESTINATION"
                print(f"✅ ALINHADO E ESTÁVEL: Erro {abs(angle_error):.1f}° < {tolerance}° por {stability_threshold} iterações → Iniciando navegação")
                self._orient_stability_counter = 0  # Reset contador
                self.navigation_state = state_key
                return
            else:
                # Ainda não estável, mas está dentro da tolerância - para de girar mas não muda de estado
                self.motors.stop()
                return
        else:
            # Erro fora da tolerância - reset contador e continua girando
            self._orient_stability_counter = 0

        # 4. Calcula velocidade angular proporcional ao erro
        # 🎯 CORREÇÃO: Ganho reduzido para evitar overshoot e oscilação
        # Ganho adaptativo: menor quando o erro é pequeno
        if abs(angle_error) < 20.0:
            gain = 0.8  # Ganho baixo para ajustes finos
        elif abs(angle_error) < 45.0:
            gain = 1.0  # Ganho médio
        else:
            gain = 1.2  # Ganho normal para erros grandes
        
        angular_speed_rads = math.radians(angle_error) * gain
        angular_speed_rads = max(-MAX_ANGULAR_SPEED_RADS, min(MAX_ANGULAR_SPEED_RADS, angular_speed_rads))

        # Velocidade linear é zero durante a orientação
        v = 0.0
        w = angular_speed_rads
        L = ROBOT_WHEEL_BASE_M
        
        # Calcula velocidades das rodas
        left_wheel_speed_ms = v + (w * L) / 2.0
        right_wheel_speed_ms = v - (w * L) / 2.0
        
        # Converte para TPS
        left_tps = (left_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps = (right_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        
        # 🎯 CORREÇÃO: Velocidade mínima adaptativa - menor quando o erro é pequeno
        if abs(angle_error) < 15.0:
            MIN_TURN_TPS = 4.0  # Velocidade muito baixa para ajustes finos
        elif abs(angle_error) < 30.0:
            MIN_TURN_TPS = 6.0  # Velocidade baixa
        else:
            MIN_TURN_TPS = 8.0  # Velocidade normal
        
        if 0 < abs(left_tps) < MIN_TURN_TPS:
            left_tps = MIN_TURN_TPS * (1 if left_tps > 0 else -1)
        if 0 < abs(right_tps) < MIN_TURN_TPS:
            right_tps = MIN_TURN_TPS * (1 if right_tps > 0 else -1)
        
        if self._orient_log_counter % 10 == 0:
            print(f"   Velocidades: left_tps={left_tps:.1f}, right_tps={right_tps:.1f} (ganho={gain:.2f}, min_tps={MIN_TURN_TPS:.1f})")
        self.motors.set_target_speed(left_tps, right_tps)

    def _normalize_angle_deg(self, deg):
        """Coloca ângulo em [-180, 180]."""
        while deg > 180:
            deg -= 360
        while deg < -180:
            deg += 360
        return deg

    def _ensure_bno_yaw_ref(self):
        """Obtém primeira leitura válida de yaw para uso como referência (até BNO_FIRST_READ_TIMEOUT)."""
        if self._get_bno_yaw is None or self._bno_yaw_ref is not None:
            return
        deadline = time.time() + BNO_FIRST_READ_TIMEOUT
        while time.time() < deadline:
            yaw = self._get_bno_yaw()
            if yaw is not None:
                self._bno_yaw_ref = yaw
                return
            time.sleep(0.05)

    def _apply_bno_straight_correction(self, left_tps, right_tps):
        """
        Aplica correção de rumo BNO quando em linha reta (movimento para frente).
        Retorna (left_tps, right_tps) corrigidos ou inalterados se BNO indisponível.
        Usa ganhos de config: BNO_STRAIGHT_KP, BNO_STRAIGHT_MAX_CORRECTION_TPS, BNO_STRAIGHT_INVERT_CORRECTION.
        """
        if self._get_bno_yaw is None:
            return left_tps, right_tps
        self._ensure_bno_yaw_ref()
        if self._bno_yaw_ref is None:
            return left_tps, right_tps
        yaw_now = self._get_bno_yaw()
        if yaw_now is None:
            return left_tps, right_tps
        err = self._normalize_angle_deg(yaw_now - self._bno_yaw_ref)
        if BNO_STRAIGHT_INVERT_CORRECTION:
            err = -err
        corr = BNO_STRAIGHT_KP * err
        corr = max(-BNO_STRAIGHT_MAX_CORRECTION_TPS, min(BNO_STRAIGHT_MAX_CORRECTION_TPS, corr))
        base_tps = (left_tps + right_tps) / 2.0
        left_tps = base_tps - corr
        right_tps = base_tps + corr
        return left_tps, right_tps

    def _move_towards_target(self):
        """
        🎯 NAVEGAÇÃO SIMPLIFICADA E ESTÁVEL:
        - Navega direto para o waypoint atual (current_target)
        - Não tenta seguir a linha exata entre waypoints (isso causa instabilidade)
        - Quando chega perto do waypoint, avança para o próximo (lógica em _handle_navigation_to_destination)
        - Isso garante que o robô passe pelos waypoints e siga o caminho de forma estável
        """
        if self.current_target is None:
            self.motors.set_target_speed(0, 0)
            return

        # 🎯 NAVEGAÇÃO SIMPLES: Vai direto ao waypoint atual (current_target)
        # A lógica de avanço de waypoints está em _handle_navigation_to_destination
        dx = self.current_target[0] - self.current_position[0]
        dy = self.current_target[1] - self.current_position[1]
        distance = math.sqrt(dx*dx + dy*dy)
        target_angle = math.degrees(math.atan2(dy, dx))
        
        # 🎯 CORREÇÃO: Normaliza target_angle para [0, 360) para cálculos consistentes
        if target_angle < 0:
            target_angle += 360
        
        # Normaliza ângulo atual para [0, 360) também
        current_angle_normalized = self.current_angle
        if current_angle_normalized < 0:
            current_angle_normalized += 360
        
        # Calcula erro angular (diferença mínima entre os dois ângulos)
        angle_error = (target_angle - current_angle_normalized + 180) % 360 - 180

        # 🎯 NAVEGAÇÃO DIRETA SIMPLES: Logs detalhados para debug
        if self.use_direct_navigation:
            print(f"🎯 NAV_DIRETA: dist={distance:.2f}m, target_ang={target_angle:.1f}°, curr_ang={current_angle_normalized:.1f}° (orig={self.current_angle:.1f}°), err={angle_error:.1f}°")

        # 🎯 CRÍTICO: Se o erro angular for muito grande (>90°), não move para frente
        # Isso evita movimento para trás
        if abs(angle_error) > 90.0:
            print(f"⚠️ ERRO ANGULAR GRANDE ({angle_error:.1f}°): Apenas girando, sem movimento linear")
            linear_speed_ms = 0.0
        else:
            angle_factor = max(0.0, math.cos(math.radians(angle_error)))
            linear_speed_ms = MAX_LINEAR_SPEED_MS * self.speed_multiplier * angle_factor
        
        angular_speed_rads = math.radians(angle_error) * 1.8
        angular_speed_rads = max(-MAX_ANGULAR_SPEED_RADS, min(MAX_ANGULAR_SPEED_RADS, angular_speed_rads))

        v = linear_speed_ms
        w = angular_speed_rads
        L = ROBOT_WHEEL_BASE_M
        
        left_wheel_speed_ms = v + (w * L) / 2.0
        right_wheel_speed_ms = v - (w * L) / 2.0
        
        # 🎯 CRÍTICO: Garantir que as velocidades das rodas não sejam negativas
        # Se forem negativas, significa que o robô tentaria ir para trás
        if left_wheel_speed_ms < 0 or right_wheel_speed_ms < 0:
            print(f"⚠️ VELOCIDADE NEGATIVA DETECTADA: left={left_wheel_speed_ms:.3f}, right={right_wheel_speed_ms:.3f}")
            # Se há erro angular significativo, apenas gira
            if abs(angle_error) > 10.0:
                linear_speed_ms = 0.0
                v = 0.0
                left_wheel_speed_ms = (w * L) / 2.0
                right_wheel_speed_ms = -(w * L) / 2.0
            else:
                # Se o erro é pequeno mas ainda há velocidade negativa, para tudo
                left_wheel_speed_ms = 0.0
                right_wheel_speed_ms = 0.0
        
        left_tps = (left_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps = (right_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        
        # BNO: ao girar muito, limpa referência para próximo trecho em linha reta
        if abs(angle_error) > 45.0:
            self._bno_yaw_ref = None
        # BNO: correção de rumo quando avançando (linha reta)
        if linear_speed_ms > 0.0:
            left_tps, right_tps = self._apply_bno_straight_correction(left_tps, right_tps)
        
        if self.use_direct_navigation:
            print(f"🎯 NAV_DIRETA: v={v:.3f}m/s, w={w:.3f}rad/s, left_tps={left_tps:.1f}, right_tps={right_tps:.1f}")
        
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

        # 🎯 AJUSTE FINO DE PRECISÃO: Tolerância reduzida para chegar mais perto (3cm)
        final_tolerance = 0.03  # 3cm - precisão máxima ultra-fina
        if total_distance <= final_tolerance:
            precision_percent = (1.0 - (total_distance / 0.08)) * 100  # Calcula % de precisão (baseado em 8cm = 100%)
            print(f"🎯 DESTINO ALCANÇADO COM PRECISÃO MÁXIMA ULTRA-FINA:")
            print(f"   Distância: {total_distance*100:.1f}cm (tolerância: {final_tolerance*100:.0f}cm)")
            print(f"   Precisão: {precision_percent:.1f}%")
            print(f"   Posição robô: ({self.current_position[0]:.3f}, {self.current_position[1]:.3f})")
            print(f"   Destino: ({final_target[0]:.3f}, {final_target[1]:.3f})")
            self.motors.stop()
            self.final_approach_start_time = None
            return True

        # 🎯 Evita giros em 360° quando muito perto: considera chegada se já está na aproximação final há tempo suficiente
        elapsed_approach = current_time - self.final_approach_start_time
        if total_distance < 0.06 and elapsed_approach > 8.0:
            print(f"🎯 DESTINO CONSIDERADO ALCANÇADO (muito perto há >8s, evita giros contínuos): {total_distance*100:.1f}cm")
            self.motors.stop()
            self.final_approach_start_time = None
            return True
        # Considera chegada se perto (<15cm) há >10s (evita ficar girando no lugar sem chegar a 6cm)
        if total_distance < 0.15 and elapsed_approach > 10.0:
            print(f"🎯 DESTINO CONSIDERADO ALCANÇADO (perto há >10s, evita giros prolongados): {total_distance*100:.1f}cm")
            self.motors.stop()
            self.final_approach_start_time = None
            return True
        # Considera chegada se <50cm há >12s ou <1m há >15s (evita 1 giro de 360° e dezenas no retorno)
        if total_distance < 0.50 and elapsed_approach > 12.0:
            print(f"🎯 DESTINO CONSIDERADO ALCANÇADO (<50cm há >12s): {total_distance*100:.1f}cm")
            self.motors.stop()
            self.final_approach_start_time = None
            return True
        if total_distance < 1.00 and elapsed_approach > 15.0:
            print(f"🎯 DESTINO CONSIDERADO ALCANÇADO (<1m há >15s, evita giros em loop): {total_distance*100:.1f}cm")
            self.motors.stop()
            self.final_approach_start_time = None
            return True

        # 🎯 VELOCIDADE ADAPTATIVA ULTRA-PRECISA: Reduz velocidade conforme se aproxima
        # Quanto mais perto, mais devagar para maior precisão (ajustado para 3cm)
        if total_distance < 0.05:  # Ultra perto (< 5cm) - velocidade muito baixa
            speed_factor = 0.25  # 25% da velocidade máxima - muito conservador
            angle_tolerance = 2.0  # Tolerância angular muito restritiva
        elif total_distance < 0.08:  # Muito perto (5-8cm)
            speed_factor = 0.35  # 35% da velocidade máxima
            angle_tolerance = 2.5  # Tolerância angular restritiva
        elif total_distance < 0.12:  # Próximo (8-12cm)
            speed_factor = 0.50  # 50% da velocidade máxima
            angle_tolerance = 3.0
        elif total_distance < 0.18:  # Aproximando (12-18cm)
            speed_factor = 0.65  # 65% da velocidade máxima
            angle_tolerance = 4.0
        else:  # Ainda longe (> 18cm)
            speed_factor = 0.80  # 80% da velocidade máxima
            angle_tolerance = 5.0

        # Log periódico para monitorar aproximação (a cada 20 iterações)
        if not hasattr(self, '_final_approach_log_counter'):
            self._final_approach_log_counter = 0
        self._final_approach_log_counter += 1
        if self._final_approach_log_counter % 20 == 0:
            precision_percent = (1.0 - (total_distance / 0.20)) * 100  # % baseado em 20cm = 100%
            print(f"🎯 APROXIMAÇÃO FINAL ULTRA-PRECISA: Distância {total_distance*100:.1f}cm, Precisão: {max(0, precision_percent):.1f}%, Velocidade: {speed_factor*100:.0f}%")

        # 🎯 VELOCIDADE LINEAR ULTRA-PRECISA: Reduz ainda mais quando muito perto
        # Usa distância como fator adicional para suavizar ainda mais a aproximação
        if total_distance < 0.05:
            # Ultra perto: velocidade baseada na distância restante (muito conservador)
            distance_factor = total_distance / 0.05  # Normaliza para 0-1
            linear_speed_ms = 0.0 if abs(angle_diff) > angle_tolerance else min(
                MAX_LINEAR_SPEED_MS * speed_factor * distance_factor, 
                total_distance / 0.8  # Divisor menor = velocidade mais baixa
            )
        else:
            # Normal: velocidade padrão adaptativa
            linear_speed_ms = 0.0 if abs(angle_diff) > angle_tolerance else min(
                MAX_LINEAR_SPEED_MS * speed_factor, 
                total_distance / 1.2
            )
        
        # 🎯 VELOCIDADE ANGULAR ULTRA-PRECISA: Ganho reduzido quando muito perto
        if total_distance < 0.05:
            angular_gain = 1.8  # Ganho mais baixo para ajustes finos
        elif total_distance < 0.08:
            angular_gain = 2.0  # Ganho moderado
        else:
            angular_gain = 2.5  # Ganho normal
        
        angular_speed_rads = math.radians(angle_diff) * angular_gain
        angular_speed_rads = max(-MAX_ANGULAR_SPEED_RADS, min(MAX_ANGULAR_SPEED_RADS, angular_speed_rads))

        v = linear_speed_ms
        w = angular_speed_rads
        L = ROBOT_WHEEL_BASE_M
        left_wheel_speed_ms = v + (w * L) / 2.0
        right_wheel_speed_ms = v - (w * L) / 2.0

        left_tps = (left_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps = (right_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION

        # BNO: correção de rumo na aproximação final quando avançando
        if linear_speed_ms > 0.0:
            left_tps, right_tps = self._apply_bno_straight_correction(left_tps, right_tps)

        self.motors.set_target_speed(left_tps, right_tps)
        return False

    def _adjust_final_angle(self):
        # Só ajusta ângulo final quando foi retorno à base (evita girar em modo "só ida")
        if not self.is_returning_to_base:
            self._finalize_navigation()
            return
        # 🎯 Timeout para evitar giros prolongados (máximo 6 segundos)
        if hasattr(self, 'final_angle_adjustment_start_time'):
            elapsed_time = time.time() - self.final_angle_adjustment_start_time
            if elapsed_time > 6.0:
                print(f"⚠️ TIMEOUT: Ajuste de ângulo final excedeu 6 segundos, finalizando navegação")
                print(f"⚠️ Ângulo atual: {self.current_angle:.1f}°, Ângulo desejado: {ROBOT_INITIAL_ANGLE}°")
                self._finalize_navigation()
                return
        
        angle_diff = (ROBOT_INITIAL_ANGLE - self.current_angle + 180) % 360 - 180
        
        # 🎯 Tolerância de 5° (evita giros de 10s quando falta 1–2° por ruído do BNO)
        if not hasattr(self, '_angle_adjustment_log_counter'):
            self._angle_adjustment_log_counter = 0
        self._angle_adjustment_log_counter += 1
        if self._angle_adjustment_log_counter % 50 == 0:
            print(f"🔄 AJUSTE ÂNGULO FINAL: Erro={angle_diff:.1f}°, Atual={self.current_angle:.1f}°, Desejado={ROBOT_INITIAL_ANGLE}°")
        
        if abs(angle_diff) > 5.0:
            if abs(angle_diff) > 30: turn_value = min(0.8, abs(angle_diff) / 25.0)
            elif abs(angle_diff) > 10: turn_value = min(0.6, abs(angle_diff) / 30.0)
            else: turn_value = min(0.4, abs(angle_diff) / 35.0)
                
            if angle_diff > 0:
                left_speed = turn_value * 100
                right_speed = -turn_value * 100
            else:
                left_speed = -turn_value * 100
                right_speed = turn_value * 100
            self.motors.set_speed(left_speed, right_speed)
        else:
            print(f"✅ AJUSTE DE ÂNGULO FINAL CONCLUÍDO: Erro={angle_diff:.1f}° (dentro da tolerância de 5°)")
            self._finalize_navigation()

    def _get_next_waypoint_info(self):
        if not self.path or self.path_index >= len(self.path):
            return None
        return self.path_index, self.current_target, len(self.path)

    def _update_pose_with_odometry(self):
        """
        Atualiza a posição e ângulo do robô baseado na odometria.
        Quando BNO está disponível, usa o ângulo do BNO (reduz erro por patinação).
        Durante giros precisos, atualiza apenas o ângulo para manter sincronização correta.
        Em PAUSED_AT_DESTINATION não atualiza pose (evita virtual "voltar de ré" e deriva para o retorno).
        """
        ticks_data = self.motors.get_and_reset_ticks()
        if not ticks_data:
            return
        if self.navigation_state == "PAUSED_AT_DESTINATION":
            return

        left_ticks, right_ticks = ticks_data.get('left', 0), ticks_data.get('right', 0)
        dist_left = (left_ticks / TICKS_PER_REVOLUTION) * ROBOT_WHEEL_CIRCUMFERENCE_M
        dist_right = (right_ticks / TICKS_PER_REVOLUTION) * ROBOT_WHEEL_CIRCUMFERENCE_M
        delta_distance = (dist_left + dist_right) / 2.0
        delta_angle_rad = (dist_left - dist_right) / ROBOT_WHEEL_BASE_M
        delta_angle_deg = math.degrees(delta_angle_rad)

        # Ângulo: BNO se disponível, mas alinhado ao referencial do mapa (evita seta para direita / giro em loop)
        use_bno_angle = (
            self._get_bno_yaw is not None
            and not self.precise_rotation_active
        )
        if use_bno_angle:
            yaw = self._get_bno_yaw()
            if yaw is not None:
                # Primeira vez: fixa offset para que ângulo do mapa não mude (BNO 0° ≠ necessariamente "direita" no mapa)
                if self._bno_yaw_offset is None:
                    self._bno_yaw_offset = self._normalize_angle_deg(self.current_angle - yaw)
                self.current_angle = self._normalize_angle_deg(yaw + self._bno_yaw_offset)
            else:
                self.current_angle += delta_angle_deg
                self.current_angle = self._normalize_angle_deg(self.current_angle)
        else:
            self.current_angle += delta_angle_deg
            if self.current_angle > 180:
                self.current_angle -= 360
            elif self.current_angle < -180:
                self.current_angle += 360

        # CONDICIONALMENTE atualiza a posição
        if not self.precise_rotation_active:
            angle_rad = math.radians(self.current_angle)
            delta_x = delta_distance * math.cos(angle_rad)
            delta_y = delta_distance * math.sin(angle_rad)
            self.current_position = (self.current_position[0] + delta_x, self.current_position[1] + delta_y)

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
        # 🎯 CORREÇÃO: Se estiver em orientação e o erro for pequeno, força transição para navegação
        if self.navigation_state == "ORIENTING_TO_TARGET" and self.current_target is not None:
            dx = self.current_target[0] - self.current_position[0]
            dy = self.current_target[1] - self.current_position[1]
            target_angle_raw = math.degrees(math.atan2(dy, dx))
            target_angle_normalized = target_angle_raw
            if target_angle_normalized < 0:
                target_angle_normalized += 360
            current_angle_normalized = self.current_angle
            if current_angle_normalized < 0:
                current_angle_normalized += 360
            angle_error = (target_angle_normalized - current_angle_normalized + 180) % 360 - 180
            
            # Se o erro for pequeno (< 30°), força transição para navegação
            if abs(angle_error) < 30.0:
                print(f"🔄 PARAR: Forçando transição de orientação para navegação (erro: {angle_error:.1f}°)")
                self.motors.stop()
                state_key = "RETURNING_TO_BASE" if self.is_returning_to_base else "NAVIGATING_TO_DESTINATION"
                self.navigation_state = state_key
                if hasattr(self, '_orient_stability_counter'):
                    self._orient_stability_counter = 0
                return
        
        self._finalize_navigation()
        
    def _handle_navigation_to_destination(self):
        if self.current_target is None or self.current_position is None:
            self._finalize_navigation()
            return

        distance_to_target = self._calculate_distance(self.current_position, self.current_target)

        # 🎯 NAVEGAÇÃO DIRETA SIMPLES OU COM PATHFINDING: Verifica se há waypoints
        # Se o caminho tem apenas 2 pontos (início e fim), é navegação direta
        # Se tem mais pontos, é navegação com pathfinding (desvio de áreas proibidas)
        is_direct_navigation = (not self.path or len(self.path) <= 2)
        
        if is_direct_navigation:
            # Na navegação direta, o destino é sempre self.original_destination
            # Não há waypoints intermediários, então vamos direto ao destino
            
            # 🎯 AJUSTE FINO DE PRECISÃO ULTRA-FINA: Tolerância reduzida para chegar mais perto do POI (3cm)
            # Fase 1: Quando está longe (> 0.20m), usa tolerância normal
            # Fase 2: Quando está perto (< 0.20m), entra em aproximação final ultra-precisa
            if distance_to_target > 0.20:
                # Ainda longe, continua navegação normal
                pass
            elif distance_to_target > 0.06:
                # Próximo (6-20cm), entra em aproximação final ultra-precisa
                print(f"🎯 APROXIMAÇÃO FINAL ULTRA-PRECISA: Distância {distance_to_target*100:.1f}cm, entrando em modo preciso")
                self.navigation_state = "FINAL_APPROACH_DESTINATION"
                self.current_target = self.original_destination
                self.final_approach_start_time = None
                return
            else:
                # Muito perto (< 6cm), verifica se chegou (tolerância 3cm)
                arrival_tolerance = 0.03  # 3cm - tolerância final ultra-fina
                if distance_to_target < arrival_tolerance:
                    precision_percent = (1.0 - (distance_to_target / 0.08)) * 100
                    print(f"🎯 DESTINO ALCANÇADO COM PRECISÃO ULTRA-FINA: Distância {distance_to_target*100:.1f}cm < {arrival_tolerance*100:.0f}cm, Precisão: {precision_percent:.1f}%")
                    self._transition_to_paused_at_destination()
                    return
            
            # Log periódico para debug (a cada 10 atualizações)
            if not hasattr(self, '_nav_log_counter'):
                self._nav_log_counter = 0
            self._nav_log_counter += 1
            if self._nav_log_counter % 10 == 0:
                print(f"🎯 NAV_DIRETA: Distância até destino: {distance_to_target:.3f}m (tolerância: {arrival_tolerance}m)")
            
            # Move direto ao destino (sem waypoints intermediários)
            self._move_towards_target()
            return

        # Navegação com pathfinding (desvio de áreas proibidas)
        # 🎯 CORREÇÃO: Garante que current_target está sempre definido corretamente
        if not self.path or len(self.path) == 0:
            print("⚠️ ERRO: Caminho vazio durante navegação!")
            self._finalize_navigation()
            return
        
        # Garante que path_index está dentro dos limites
        if self.path_index >= len(self.path):
            print(f"⚠️ ERRO: path_index ({self.path_index}) >= len(path) ({len(self.path)})")
            self.navigation_state = "FINAL_APPROACH_DESTINATION"
            self.current_target = self.original_destination
            return
        
        # Garante que current_target está definido
        if self.current_target is None:
            if self.path_index < len(self.path):
                self.current_target = self.path[self.path_index]
            else:
                self.current_target = self.original_destination
        
        is_near_final_destination = (self.path_index >= len(self.path) - 1)

        if is_near_final_destination and distance_to_target < 0.15:
            self.navigation_state = "FINAL_APPROACH_DESTINATION"
            self.current_target = self.original_destination
            return

        # 🎯 CORREÇÃO: Avança para o próximo waypoint quando chega perto (tolerância de 20cm para evitar paradas)
        if distance_to_target < 0.20:  # Tolerância aumentada para evitar paradas e giros em loop
            self.path_index += 1
            if self.path_index < len(self.path):
                self.current_target = self.path[self.path_index]
                print(f"🎯 AVANÇANDO WAYPOINT: {self.path_index-1} → {self.path_index}, Novo alvo: {self.current_target}")
            else:
                # Chegou ao último waypoint, vai para aproximação final
                self.navigation_state = "FINAL_APPROACH_DESTINATION"
                self.current_target = self.original_destination
                print(f"🎯 ÚLTIMO WAYPOINT ALCANÇADO, indo para aproximação final: {self.original_destination}")
            return
        
        self._move_towards_target()

    def _handle_return_to_base(self):
        if self.current_target is None or self.current_position is None:
            self._finalize_navigation()
            return

        distance_to_target = self._calculate_distance(self.current_position, self.current_target)
        
        # 🎯 NAVEGAÇÃO DIRETA SIMPLES OU COM PATHFINDING: Verifica se há waypoints
        # Se o caminho tem apenas 2 pontos (início e fim), é navegação direta
        # Se tem mais pontos, é navegação com pathfinding (desvio de áreas proibidas)
        is_direct_navigation = (not self.path or len(self.path) <= 2)
        
        if is_direct_navigation:
            # Na navegação direta, o destino de retorno é sempre self.base_position
            # Não há waypoints intermediários, então vamos direto à base
            
            # 🎯 AJUSTE FINO DE PRECISÃO ULTRA-FINA: Mesma lógica de precisão para retorno à base (3cm)
            if distance_to_target > 0.20:
                # Ainda longe, continua navegação normal
                pass
            elif distance_to_target > 0.06:
                # Próximo (6-20cm), entra em aproximação final ultra-precisa
                print(f"🎯 APROXIMAÇÃO FINAL BASE ULTRA-PRECISA: Distância {distance_to_target*100:.1f}cm, entrando em modo preciso")
                self.navigation_state = "FINAL_APPROACH_BASE"
                self.current_target = self.base_position
                self.final_approach_start_time = None
                return
            else:
                # Muito perto (< 6cm), verifica se chegou (tolerância 3cm)
                arrival_tolerance = 0.03  # 3cm - tolerância final ultra-fina
                if distance_to_target < arrival_tolerance:
                    precision_percent = (1.0 - (distance_to_target / 0.08)) * 100
                    print(f"🎯 BASE ALCANÇADA COM PRECISÃO ULTRA-FINA: Distância {distance_to_target*100:.1f}cm < {arrival_tolerance*100:.0f}cm, Precisão: {precision_percent:.1f}%")
                    self.navigation_state = "FINAL_APPROACH_BASE"
                    self.final_approach_start_time = None
                    return
            
            # Log periódico para debug (a cada 10 atualizações)
            if not hasattr(self, '_return_log_counter'):
                self._return_log_counter = 0
            self._return_log_counter += 1
            if self._return_log_counter % 10 == 0:
                print(f"🎯 RETORNO_BASE: Distância até base: {distance_to_target:.3f}m (tolerância: {arrival_tolerance}m)")
            
            # Move direto à base (sem waypoints intermediários)
            self._move_towards_target()
            return

        # Navegação com pathfinding (desvio de áreas proibidas)
        # 🎯 CORREÇÃO: Garante que current_target está sempre definido corretamente
        if not self.path or len(self.path) == 0:
            print("⚠️ ERRO: Caminho vazio durante retorno!")
            self._finalize_navigation()
            return
        
        # Garante que path_index está dentro dos limites válidos (>= 1, pois índice 0 é a posição atual)
        if self.path_index < 1:
            self.path_index = 1
        if self.path_index >= len(self.path):
            print(f"🎯 ÚLTIMO WAYPOINT DE RETORNO ALCANÇADO, indo para aproximação final")
            self.navigation_state = "FINAL_APPROACH_BASE"
            self.current_target = self.base_position
            self.final_approach_start_time = None
            return
        
        # Garante que current_target está definido
        if self.current_target is None or self.path_index < len(self.path):
            self.current_target = self.path[self.path_index]
            
        is_near_base = (self.path_index >= len(self.path) - 1)

        if is_near_base and distance_to_target < 0.15:
            self.navigation_state = "FINAL_APPROACH_BASE"
            self.current_target = self.base_position
            self.final_approach_start_time = None 
            return

        # 🎯 CORREÇÃO: Avança para o próximo waypoint quando chega perto (tolerância de 20cm para evitar paradas)
        if distance_to_target < 0.20:  # Tolerância aumentada para evitar paradas e giros
            self.path_index += 1
            if self.path_index < len(self.path):
                self.current_target = self.path[self.path_index]
                print(f"🎯 RETORNO: Avançando waypoint {self.path_index-1} → {self.path_index}, Novo alvo: {self.current_target}")
            else:
                # Chegou ao último waypoint, vai para aproximação final
                self.navigation_state = "FINAL_APPROACH_BASE"
                self.current_target = self.base_position
                self.final_approach_start_time = None
                print(f"🎯 RETORNO: Último waypoint alcançado, indo para aproximação final da base")
            return
        
        self._move_towards_target()

    def _transition_to_paused_at_destination(self):
        self.motors.stop()
        self.navigation_state = "PAUSED_AT_DESTINATION"
        self.arrival_time = time.time()
        self.is_paused_at_destination = True

    def _handle_pause_at_destination(self):
        if self.arrival_time is not None and (time.time() - self.arrival_time > self.arrival_pause_time):
            self.is_paused_at_destination = False
            if self.should_return_to_base:
                self._calculate_and_execute_return_angle()
            else:
                self._finalize_navigation()
