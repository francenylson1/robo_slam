#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Teste Personalizado: Desvio de Áreas Proibidas
==========================================================

Permite criar testes personalizados para casos específicos.

Uso:
    python tests/teste_desvio_personalizado.py
"""

import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from teste_desvio_areas_proibidas import TesteDesvioAreasProibidas


def main():
    """Função principal - personalize os testes aqui"""
    teste = TesteDesvioAreasProibidas()
    
    # ==========================================
    # PERSONALIZE SEUS TESTES AQUI
    # ==========================================
    
    # Exemplo 1: Teste simples
    print("\n" + "=" * 80)
    print("TESTE PERSONALIZADO 1: Exemplo básico")
    print("=" * 80)
    
    start = (1.0, 1.0)  # Ponto inicial (x, y) em metros
    goal = (5.0, 5.0)   # Ponto final (x, y) em metros
    
    # Define área proibida (lista de pontos formando um polígono)
    area_proibida = [
        (2.5, 2.5),  # Vértice 1
        (3.5, 2.5),  # Vértice 2
        (3.5, 3.5),  # Vértice 3
        (2.5, 3.5)   # Vértice 4
    ]
    
    teste.executar_teste(
        "Teste Personalizado 1",
        start, goal,
        [area_proibida],  # Lista de áreas proibidas
        "Descrição do teste personalizado"
    )
    
    # Exemplo 2: Teste com múltiplas áreas
    # Descomente para usar:
    """
    print("\n" + "=" * 80)
    print("TESTE PERSONALIZADO 2: Múltiplas áreas")
    print("=" * 80)
    
    start2 = (0.5, 0.5)
    goal2 = (5.5, 5.5)
    
    area1 = [(1.5, 1.5), (2.0, 1.5), (2.0, 2.0), (1.5, 2.0)]
    area2 = [(3.5, 3.5), (4.0, 3.5), (4.0, 4.0), (3.5, 4.0)]
    
    teste.executar_teste(
        "Teste Personalizado 2",
        start2, goal2,
        [area1, area2],
        "Teste com múltiplas áreas proibidas"
    )
    """
    
    # ==========================================
    # FIM DOS TESTES PERSONALIZADOS
    # ==========================================
    
    # Gera relatório
    arquivo_relatorio = teste.gerar_relatorio()
    
    print("\n" + "=" * 80)
    print("✅ TESTES PERSONALIZADOS CONCLUÍDOS")
    print("=" * 80)
    print(f"📁 Relatório salvo em: {arquivo_relatorio}")


if __name__ == '__main__':
    main()

