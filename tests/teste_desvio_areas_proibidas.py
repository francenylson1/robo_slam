#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Teste: Desvio de Áreas Proibidas
===========================================

Este script testa o sistema de desvio de áreas proibidas:
1. Configura áreas proibidas de teste
2. Tenta navegar entre pontos
3. Coleta logs detalhados do A*
4. Gera relatório de resultados

Uso:
    python tests/teste_desvio_areas_proibidas.py
"""

import sys
import os
import json
from datetime import datetime
from typing import List, Tuple

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.path_finder import PathFinder
from src.core.config import (
    MAP_WIDTH, MAP_HEIGHT, MAP_GRID_SIZE,
    FORBIDDEN_AREA_INFLATION_RADIUS, ROBOT_WIDTH,
    ROBOT_INITIAL_POSITION
)


class TesteDesvioAreasProibidas:
    """Classe para testar o desvio de áreas proibidas"""
    
    def __init__(self):
        """Inicializa o teste"""
        self.resultados = {
            'timestamp': datetime.now().isoformat(),
            'testes': [],
            'resumo': {
                'total_testes': 0,
                'sucessos': 0,
                'falhas': 0,
                'erros': []
            }
        }
        
        # Inicializa PathFinder
        self.path_finder = PathFinder(
            width=int(MAP_WIDTH / MAP_GRID_SIZE),
            height=int(MAP_HEIGHT / MAP_GRID_SIZE),
            grid_size=MAP_GRID_SIZE,
            map_origin=(0.0, 0.0)  # Será atualizado se necessário
        )
        
        print("=" * 80)
        print("🧪 TESTE DE DESVIO DE ÁREAS PROIBIDAS")
        print("=" * 80)
        print(f"📐 Dimensões do mapa: {MAP_WIDTH}m x {MAP_HEIGHT}m")
        print(f"📐 Grid size: {MAP_GRID_SIZE}m")
        print(f"📐 Dimensões do grid: {self.path_finder.width}x{self.path_finder.height} células")
        print(f"📐 Raio de inflação: {FORBIDDEN_AREA_INFLATION_RADIUS}m")
        print(f"📐 Largura do robô: {ROBOT_WIDTH}m")
        print("=" * 80)
    
    def criar_area_proibida_teste(self, nome: str, pontos: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Cria uma área proibida de teste"""
        print(f"\n📦 Criando área proibida: {nome}")
        print(f"   Pontos: {pontos}")
        return pontos
    
    def executar_teste(self, nome: str, start: Tuple[float, float], goal: Tuple[float, float], 
                      areas_proibidas: List[List[Tuple[float, float]]], 
                      descricao: str = ""):
        """
        Executa um teste de navegação com áreas proibidas
        
        Args:
            nome: Nome do teste
            start: Ponto inicial (x, y) em metros
            goal: Ponto final (x, y) em metros
            areas_proibidas: Lista de áreas proibidas (cada área é uma lista de pontos)
            descricao: Descrição do teste
        """
        print("\n" + "=" * 80)
        print(f"🧪 TESTE: {nome}")
        if descricao:
            print(f"📝 {descricao}")
        print("=" * 80)
        
        resultado_teste = {
            'nome': nome,
            'descricao': descricao,
            'start': start,
            'goal': goal,
            'areas_proibidas': areas_proibidas,
            'sucesso': False,
            'caminho_encontrado': False,
            'caminho': None,
            'num_waypoints': 0,
            'logs': [],
            'erros': []
        }
        
        try:
            # Configura áreas proibidas
            print(f"\n🚫 Configurando {len(areas_proibidas)} área(s) proibida(s)...")
            self.path_finder.set_forbidden_areas(areas_proibidas)
            
            # Verifica obstacle_grid
            num_celulas_obstaculo = len(self.path_finder.obstacle_grid)
            print(f"📊 Células marcadas como obstáculo: {num_celulas_obstaculo}")
            resultado_teste['num_celulas_obstaculo'] = num_celulas_obstaculo
            
            # Converte coordenadas para grid
            start_relative_x = start[0] - self.path_finder.map_origin[0]
            start_relative_y = start[1] - self.path_finder.map_origin[1]
            goal_relative_x = goal[0] - self.path_finder.map_origin[0]
            goal_relative_y = goal[1] - self.path_finder.map_origin[1]
            
            start_grid = (int(start_relative_x / MAP_GRID_SIZE), int(start_relative_y / MAP_GRID_SIZE))
            goal_grid = (int(goal_relative_x / MAP_GRID_SIZE), int(goal_relative_y / MAP_GRID_SIZE))
            
            print(f"\n📍 Coordenadas:")
            print(f"   Start (world): {start} m")
            print(f"   Goal (world): {goal} m")
            print(f"   Start (grid): {start_grid}")
            print(f"   Goal (grid): {goal_grid}")
            print(f"   Origem do mapa: {self.path_finder.map_origin}")
            
            # Verifica se start/goal estão dentro dos limites
            if not (0 <= start_grid[0] < self.path_finder.width and 0 <= start_grid[1] < self.path_finder.height):
                erro = f"Start fora dos limites: {start_grid} (limites: 0-{self.path_finder.width}, 0-{self.path_finder.height})"
                print(f"❌ ERRO: {erro}")
                resultado_teste['erros'].append(erro)
                self.resultados['testes'].append(resultado_teste)
                self.resultados['resumo']['falhas'] += 1
                return resultado_teste
            
            if not (0 <= goal_grid[0] < self.path_finder.width and 0 <= goal_grid[1] < self.path_finder.height):
                erro = f"Goal fora dos limites: {goal_grid} (limites: 0-{self.path_finder.width}, 0-{self.path_finder.height})"
                print(f"❌ ERRO: {erro}")
                resultado_teste['erros'].append(erro)
                self.resultados['testes'].append(resultado_teste)
                self.resultados['resumo']['falhas'] += 1
                return resultado_teste
            
            # Verifica se start/goal estão em áreas proibidas
            start_em_obstaculo = self.path_finder._is_in_forbidden_area(start_grid[0], start_grid[1])
            goal_em_obstaculo = self.path_finder._is_in_forbidden_area(goal_grid[0], goal_grid[1])
            
            print(f"\n🔍 Verificações:")
            print(f"   Start em obstáculo: {start_em_obstaculo}")
            print(f"   Goal em obstáculo: {goal_em_obstaculo}")
            
            if start_em_obstaculo:
                print(f"⚠️  Start está em área proibida! Tentando encontrar ponto válido próximo...")
                novo_start = self.path_finder._find_nearest_valid_point(start_grid)
                if novo_start:
                    print(f"✅ Novo start encontrado: {novo_start}")
                    start_grid = novo_start
                else:
                    erro = "Não foi possível encontrar ponto válido próximo ao start"
                    print(f"❌ ERRO: {erro}")
                    resultado_teste['erros'].append(erro)
                    self.resultados['testes'].append(resultado_teste)
                    self.resultados['resumo']['falhas'] += 1
                    return resultado_teste
            
            if goal_em_obstaculo:
                print(f"⚠️  Goal está em área proibida! Tentando encontrar ponto válido próximo...")
                novo_goal = self.path_finder._find_nearest_valid_point(goal_grid)
                if novo_goal:
                    print(f"✅ Novo goal encontrado: {novo_goal}")
                    goal_grid = novo_goal
                else:
                    erro = "Não foi possível encontrar ponto válido próximo ao goal"
                    print(f"❌ ERRO: {erro}")
                    resultado_teste['erros'].append(erro)
                    self.resultados['testes'].append(resultado_teste)
                    self.resultados['resumo']['falhas'] += 1
                    return resultado_teste
            
            # Tenta encontrar caminho
            print(f"\n🔍 Executando A* de {start} para {goal}...")
            caminho = self.path_finder.find_path(start, goal)
            
            if caminho:
                print(f"✅ CAMINHO ENCONTRADO!")
                print(f"   Número de waypoints: {len(caminho)}")
                print(f"   Primeiro ponto: {caminho[0]}")
                print(f"   Último ponto: {caminho[-1]}")
                
                # Verifica se o caminho realmente evita áreas proibidas
                caminho_valido = True
                for i in range(len(caminho) - 1):
                    intersecta = self.path_finder._line_intersects_obstacles(caminho[i], caminho[i + 1])
                    if intersecta:
                        print(f"❌ ERRO: Segmento {i} ({caminho[i]} → {caminho[i+1]}) intersecta área proibida!")
                        caminho_valido = False
                        resultado_teste['erros'].append(f"Segmento {i} intersecta área proibida")
                
                if caminho_valido:
                    print(f"✅ Caminho verificado: Nenhum segmento intersecta áreas proibidas")
                    resultado_teste['sucesso'] = True
                    resultado_teste['caminho_encontrado'] = True
                    resultado_teste['caminho'] = caminho
                    resultado_teste['num_waypoints'] = len(caminho)
                    self.resultados['resumo']['sucessos'] += 1
                else:
                    resultado_teste['caminho_encontrado'] = True
                    resultado_teste['caminho'] = caminho
                    resultado_teste['num_waypoints'] = len(caminho)
                    self.resultados['resumo']['falhas'] += 1
            else:
                print(f"❌ CAMINHO NÃO ENCONTRADO!")
                resultado_teste['erros'].append("A* não encontrou caminho")
                self.resultados['resumo']['falhas'] += 1
            
        except Exception as e:
            erro = f"Exceção durante teste: {str(e)}"
            print(f"❌ ERRO: {erro}")
            import traceback
            traceback.print_exc()
            resultado_teste['erros'].append(erro)
            self.resultados['resumo']['falhas'] += 1
        
        self.resultados['testes'].append(resultado_teste)
        self.resultados['resumo']['total_testes'] += 1
        return resultado_teste
    
    def executar_suite_teste(self):
        """Executa uma suíte completa de testes"""
        print("\n" + "=" * 80)
        print("🚀 INICIANDO SUÍTE DE TESTES")
        print("=" * 80)
        
        # TESTE 1: Sem áreas proibidas (deve funcionar)
        print("\n" + "=" * 80)
        print("TESTE 1: Navegação sem áreas proibidas")
        print("=" * 80)
        start1 = (1.0, 1.0)
        goal1 = (5.0, 5.0)
        self.executar_teste(
            "Sem áreas proibidas",
            start1, goal1,
            [],
            "Teste básico sem áreas proibidas - deve encontrar caminho direto"
        )
        
        # TESTE 2: Com uma área proibida no meio (deve desviar)
        print("\n" + "=" * 80)
        print("TESTE 2: Navegação com área proibida no meio")
        print("=" * 80)
        start2 = (1.0, 1.0)
        goal2 = (5.0, 5.0)
        area_proibida_meio = self.criar_area_proibida_teste(
            "Área no meio",
            [(2.5, 2.5), (3.5, 2.5), (3.5, 3.5), (2.5, 3.5)]  # Quadrado 1x1m no meio
        )
        self.executar_teste(
            "Área proibida no meio",
            start2, goal2,
            [area_proibida_meio],
            "Teste com área proibida bloqueando caminho direto - deve desviar"
        )
        
        # TESTE 3: Start próximo à área proibida
        print("\n" + "=" * 80)
        print("TESTE 3: Start próximo à área proibida")
        print("=" * 80)
        start3 = (2.0, 2.0)  # Próximo à área proibida
        goal3 = (5.0, 5.0)
        area_proibida_proxima = self.criar_area_proibida_teste(
            "Área próxima ao start",
            [(2.2, 2.2), (2.8, 2.2), (2.8, 2.8), (2.2, 2.8)]  # Quadrado pequeno
        )
        self.executar_teste(
            "Start próximo à área proibida",
            start3, goal3,
            [area_proibida_proxima],
            "Teste com start próximo à área proibida - deve encontrar ponto válido"
        )
        
        # TESTE 4: Múltiplas áreas proibidas
        print("\n" + "=" * 80)
        print("TESTE 4: Múltiplas áreas proibidas")
        print("=" * 80)
        start4 = (1.0, 1.0)
        goal4 = (5.0, 5.0)
        area1 = self.criar_area_proibida_teste("Área 1", [(2.0, 2.0), (2.5, 2.0), (2.5, 2.5), (2.0, 2.5)])
        area2 = self.criar_area_proibida_teste("Área 2", [(3.5, 3.5), (4.0, 3.5), (4.0, 4.0), (3.5, 4.0)])
        self.executar_teste(
            "Múltiplas áreas proibidas",
            start4, goal4,
            [area1, area2],
            "Teste com múltiplas áreas proibidas - deve desviar de todas"
        )
        
        # TESTE 5: Caminho bloqueado completamente
        print("\n" + "=" * 80)
        print("TESTE 5: Caminho completamente bloqueado")
        print("=" * 80)
        start5 = (1.0, 1.0)
        goal5 = (5.0, 1.0)  # Mesma linha Y
        area_bloqueio = self.criar_area_proibida_teste(
            "Bloqueio total",
            [(2.0, 0.0), (4.0, 0.0), (4.0, 3.0), (2.0, 3.0)]  # Bloqueia toda a linha
        )
        self.executar_teste(
            "Caminho bloqueado",
            start5, goal5,
            [area_bloqueio],
            "Teste com caminho completamente bloqueado - deve falhar graciosamente"
        )
    
    def gerar_relatorio(self, arquivo_saida: str = None):
        """Gera relatório dos testes"""
        if arquivo_saida is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_saida = f"data/teste_desvio_areas_proibidas_{timestamp}.json"
        
        # Cria diretório se não existir
        os.makedirs(os.path.dirname(arquivo_saida), exist_ok=True)
        
        # Salva JSON
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(self.resultados, f, indent=2, ensure_ascii=False)
        
        # Imprime resumo
        print("\n" + "=" * 80)
        print("📊 RELATÓRIO DE TESTES")
        print("=" * 80)
        print(f"Total de testes: {self.resultados['resumo']['total_testes']}")
        print(f"✅ Sucessos: {self.resultados['resumo']['sucessos']}")
        print(f"❌ Falhas: {self.resultados['resumo']['falhas']}")
        print(f"\n📁 Relatório salvo em: {arquivo_saida}")
        
        # Detalhes dos testes
        print("\n" + "-" * 80)
        print("DETALHES DOS TESTES:")
        print("-" * 80)
        for i, teste in enumerate(self.resultados['testes'], 1):
            status = "✅ SUCESSO" if teste['sucesso'] else "❌ FALHA"
            print(f"\n{i}. {teste['nome']} - {status}")
            if teste['caminho_encontrado']:
                print(f"   Caminho encontrado: {teste['num_waypoints']} waypoints")
            else:
                print(f"   Caminho não encontrado")
            if teste['erros']:
                print(f"   Erros: {', '.join(teste['erros'])}")
        
        return arquivo_saida


def main():
    """Função principal"""
    teste = TesteDesvioAreasProibidas()
    
    # Executa suíte de testes
    teste.executar_suite_teste()
    
    # Gera relatório
    arquivo_relatorio = teste.gerar_relatorio()
    
    print("\n" + "=" * 80)
    print("✅ TESTES CONCLUÍDOS")
    print("=" * 80)
    print(f"📁 Verifique o relatório em: {arquivo_relatorio}")
    print("\n💡 Dica: Envie o arquivo JSON do relatório para análise detalhada")


if __name__ == '__main__':
    main()

