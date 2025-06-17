# PROJETO: Robô Garçom Autônomo - Navegação Inteligente

## CONTEXTO DO PROJETO:
Sou professor de robótica educacional (Projeto Aluno Maker Digital desde 2018). 
Tenho um robô garçom funcionando com Raspberry Pi 4 (4GB) controlado por joystick via GPIO em Python.

## OBJETIVO:
Transformar controle manual → navegação autônoma mantendo opção de alternar entre modos.

## ⚠️ SITUAÇÃO ATUAL DOS SENSORES:
- **NÃO temos os sensores ainda**: Lidar Aurora e C1 Slamtec ainda não chegaram
- **Estratégia**: Integrar SDK Slamtec desde o início com fallback para dados simulados
- **Vantagem**: Quando sensores chegarem, apenas ativar hardware (sem refatoração)

## ESPECIFICAÇÕES TÉCNICAS:
- **Hardware atual**: Raspberry Pi 4 (4GB), motores GPIO já funcionando
- **Sensores futuros**: Lidar Aurora (mapeamento) + C1 Slamtec (navegação/obstáculos)
- **SDK**: Slamtec C++ integrado ao Python via ctypes/bindings
- **Linguagem**: Python (NÃO usar ROS)
- **Interface**: PyQt para desenho de mapas e rotas
- **Banco**: SQLite para persistência
- **Precisão**: Centímetros

## AMBIENTE DE TESTE:
- **Dimensões**: 6m largura × 12m comprimento (Sala Maker real)
- **Sistema coordenadas**: Origem (0,0) na porta, X cresce para esquerda, Y para frente
- **Posição inicial robô**: (0.5, 0.5)
- **Dados simulados**: Estrutura idêntica aos dados reais do SDK Slamtec

## FUNCIONALIDADES REQUERIDAS:
1. **Integração SDK Slamtec**: Preparar desde o início com detecção de hardware
2. **Mapa simulado**: Ambiente virtual 6×12m com obstáculos fixos predefinidos
3. **Interface PyQt**: Canvas para desenhar rotas, gerenciar pontos de interesse
4. **Navegação**: Pathfinding A* com curvas suavizadas
5. **Pontos interesse**: Adicionar/editar/excluir (ex: "Mesa 01", "Base")
6. **Áreas proibidas**: Zonas que robô deve evitar
7. **Controle dual**: Toggle joystick ↔ autônomo
8. **Integração motores**: Manter código GPIO existente

## ESTRUTURA BANCO SQLite:
- mapas (id, nome, largura, comprimento, ativo)
- pontos_interesse (id, mapa_id, nome, x, y, tipo, raio)
- rotas (id, nome, mapa_id, ativa)
- pontos_rota (id, rota_id, sequencia, x, y, velocidade)
- areas_proibidas (id, mapa_id, coordenadas, ativa, motivo)
- obstaculos_fixos (id, mapa_id, nome, x, y, largura, altura)

## ARQUITETURA CLASSES PRINCIPAIS:
- **RobotNavigator**: Coordenador principal do sistema
- **SlamtecManager**: Integração SDK C++ → Python (com fallback simulado)
- **PathFinder**: Algoritmo A* com curvas suavizadas
- **MotorController**: Integração GPIO existente + controle PID
- **SafetyLayer**: Segurança/emergência + detecção obstáculos
- **MapManager**: Gerencia mapas e persistência SQLite
- **PyQtInterface**: Interface gráfica completa

## ESTRATÉGIA DE INTEGRAÇÃO SDK SLAMTEC:
```python
class SlamtecManager:
    def __init__(self):
        self.sdk_available = self._detect_slamtec_sdk()
        self.hardware_connected = self._detect_hardware()
    
    def get_lidar_scan(self):
        if self.sdk_available and self.hardware_connected:
            return self._real_lidar_scan()  # Dados reais do Aurora
        else:
            return self._mock_lidar_scan()  # Dados simulados realistas
    
    def detect_obstacles(self):
        if self.sdk_available and self.hardware_connected:
            return self._real_obstacle_detection()  # C1 real
        else:
            return self._mock_obstacles()  # Simulação
FASES DE DESENVOLVIMENTO:
DESENVOLVIMENTO ÚNICO (SMART APPROACH):

✅ SDK Slamtec integrado desde o início
✅ Detecção automática de hardware disponível
✅ Fallback inteligente para dados simulados
✅ Transição transparente quando sensores chegarem
✅ Arquitetura consistente e sem refatoração futura

ESTRUTURA DE DADOS SLAMTEC (Para Mock Realista):
Aurora Lidar Data:
pythonlidar_scan = {
    'timestamp': time.time(),
    'points': [(distance, angle), ...],  # Array de pontos polares
    'quality': [0-255, ...],             # Qualidade de cada ponto
    'scan_frequency': 10.0               # Hz
}
C1 Obstacle Data:
pythonobstacles = {
    'timestamp': time.time(),
    'obstacles': [(x, y, confidence), ...],  # Coordenadas cartesianas
    'detection_range': 12.0,                 # Alcance em metros
    'update_frequency': 20.0                 # Hz
}
REQUISITOS TÉCNICOS:

Preparar integração ctypes para SDK C++
Criar estrutura de dados compatível com formato Slamtec
Implementar detecção automática de hardware
Fallback robusto para modo simulação
Interface pronta para dados reais

Crie a estrutura completa do projeto já preparada para o SDK Slamtec, mas funcionando perfeitamente em modo simulado até os sensores chegarem.
