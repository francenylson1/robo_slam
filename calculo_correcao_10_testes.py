#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cálculo de Correção de Deriva Lateral - Baseado em 10 Testes
Análise dos dados coletados para determinar fator de correção preciso
"""

import statistics

# Dados dos 10 testes realizados
testes = [
    {"teste": 1, "left": 73, "right": 63, "diff_percent": 15.38},
    {"teste": 2, "left": 70, "right": 70, "diff_percent": 0.0},
    {"teste": 3, "left": 68, "right": 64, "diff_percent": 6.25},
    {"teste": 4, "left": 72, "right": 68, "diff_percent": 5.88},
    {"teste": 5, "left": 69, "right": 71, "diff_percent": -2.82},
    {"teste": 6, "left": 71, "right": 69, "diff_percent": 2.90},
    {"teste": 7, "left": 70, "right": 68, "diff_percent": 2.94},
    {"teste": 8, "left": 67, "right": 69, "diff_percent": -2.90},
    {"teste": 9, "left": 74, "right": 66, "diff_percent": 12.12},
    {"teste": 10, "left": 68, "right": 70, "diff_percent": -2.86}
]

def calcular_fator_correcao_otimizado(testes_data):
    """
    Calcula fator de correção baseado na média dos testes
    """
    total_left = sum(t["left"] for t in testes_data)
    total_right = sum(t["right"] for t in testes_data)
    
    # Média dos ticks
    media_left = total_left / len(testes_data)
    media_right = total_right / len(testes_data)
    
    print(f"Média Left: {media_left:.2f} ticks")
    print(f"Média Right: {media_right:.2f} ticks")
    
    # Calcula fator de correção
    if media_left > media_right:
        # Motor esquerdo mais rápido
        fator_left = media_right / media_left
        fator_right = 1.0
        diferenca_percent = ((media_left / media_right - 1) * 100)
    else:
        # Motor direito mais rápido
        fator_left = 1.0
        fator_right = media_left / media_right
        diferenca_percent = ((media_right / media_left - 1) * 100)
    
    return {
        'left_factor': fator_left,
        'right_factor': fator_right,
        'diferenca_percent': diferenca_percent,
        'media_left': media_left,
        'media_right': media_right
    }

def main():
    print("="*60)
    print("ANÁLISE DE CORREÇÃO - 10 TESTES DE DERIVA LATERAL")
    print("="*60)
    
    # Mostra dados dos testes
    print("\nDADOS DOS TESTES:")
    for teste in testes:
        print(f"Teste {teste['teste']:2d}: Left={teste['left']:2d}, Right={teste['right']:2d}, Diff={teste['diff_percent']:6.2f}%")
    
    # Calcula estatísticas
    diffs = [t["diff_percent"] for t in testes]
    media_diff = statistics.mean(diffs)
    desvio_diff = statistics.stdev(diffs)
    
    print(f"\nESTATÍSTICAS:")
    print(f"Diferença média: {media_diff:.2f}%")
    print(f"Desvio padrão: {desvio_diff:.2f}%")
    print(f"Mínimo: {min(diffs):.2f}%")
    print(f"Máximo: {max(diffs):.2f}%")
    
    # Calcula correção otimizada
    correcao = calcular_fator_correcao_otimizado(testes)
    
    print("\n" + "="*60)
    print("FATORES DE CORREÇÃO CALCULADOS")
    print("="*60)
    print(f"Motor esquerdo mais rápido em: {correcao['diferenca_percent']:.2f}%")
    print(f"Fator correção LEFT:  {correcao['left_factor']:.6f}")
    print(f"Fator correção RIGHT: {correcao['right_factor']:.6f}")
    
    # Gera código de correção
    print("\n" + "="*60)
    print("CÓDIGO DE CORREÇÃO ATUALIZADO")
    print("="*60)
    
    codigo_correcao = f"""
# === CORREÇÃO DE DERIVA LATERAL ===
# Fatores de correção baseados em análise de 10 testes
# Data: 2025-09-17 16:15:00
# Média: Left={correcao['media_left']:.1f}, Right={correcao['media_right']:.1f} ticks
# Motor esquerdo {correcao['diferenca_percent']:.1f}% mais rápido
LEFT_MOTOR_CORRECTION_FACTOR = {correcao['left_factor']:.6f}
RIGHT_MOTOR_CORRECTION_FACTOR = {correcao['right_factor']:.6f}
"""
    
    print(codigo_correcao)
    
    # Comparação com fator atual
    fator_atual = 0.920000
    fator_calculado = correcao['left_factor']
    
    print("\n" + "="*60)
    print("COMPARAÇÃO COM FATOR ATUAL")
    print("="*60)
    print(f"Fator atual:     {fator_atual:.6f}")
    print(f"Fator calculado: {fator_calculado:.6f}")
    print(f"Diferença:       {abs(fator_atual - fator_calculado):.6f}")
    
    if abs(fator_atual - fator_calculado) > 0.01:
        print("⚠️  RECOMENDAÇÃO: Atualizar fator de correção")
    else:
        print("✅ Fator atual está próximo do calculado")
    
    return correcao

if __name__ == "__main__":
    resultado = main()