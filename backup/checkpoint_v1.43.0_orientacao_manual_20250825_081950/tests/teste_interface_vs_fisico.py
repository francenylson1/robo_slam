#!/usr/bin/env python3
"""
TESTE INTERFACE vs FÍSICO - Comparação Direta
Replica exatamente os comandos que a interface envia para o robô físico
"""

import sys
import os
import time

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.environment import GPIO_AVAILABLE
from src.core.robot_motor_controller import RobotMotorController

def print_analysis():
    """Mostra análise técnica baseada no código da interface"""
    print("🔍 ANÁLISE TÉCNICA ENCONTRADA NO CÓDIGO:")
    print("=" * 60)
    print("📍 INTERFACE (main_window.py - linha 1055):")
    print("   Botão ESQUERDA → set_speed(-30, 30)  # ESQ-, DIR+")
    print("📍 INTERFACE (main_window.py - linha 1060):")  
    print("   Botão DIREITA  → set_speed(30, -30)  # ESQ+, DIR-")
    print("=" * 60)
    print("📍 ESTE TESTE:")
    print("   Comando ESQUERDA → set_speed(-30, 30)  # MESMA LÓGICA")
    print("   Comando DIREITA  → set_speed(30, -30)  # MESMA LÓGICA")
    print("=" * 60)
    print("🎯 CONCLUSÃO: Se interface e teste usam mesma lógica,")
    print("   qualquer discrepância indica problema no HARDWARE!")
    print("=" * 60)

def test_interface_commands(motor_controller):
    """Replica exatamente os comandos da interface gráfica"""
    print("\n🔄 TESTE: COMANDOS IDÊNTICOS À INTERFACE")
    print("=" * 50)
    
    # TESTE 1: Comando ESQUERDA da interface
    print("\n📍 REPLICANDO: Botão ESQUERDA da Interface")
    print("   🖱️  Equivale a clicar: ⬅️ ESQUERDA (-10°)")
    print("   ⚙️  Comando físico: set_speed(-30, 30)")
    print("   🎯 EXPECTATIVA: Robô deve girar para ESQUERDA")
    input("   ▶️  Pressione ENTER para EXECUTAR...")
    
    # Usa set_speed (método legado) exatamente como a interface
    motor_controller.set_speed(-30, 30)  # IDÊNTICO à interface
    time.sleep(3)
    motor_controller.stop()
    
    print("   ❓ O robô girou para ESQUERDA? (s/n)")
    resultado_esq = input("   ➡️  Resposta: ").lower().strip()
    
    time.sleep(1)  # Pausa entre testes
    
    # TESTE 2: Comando DIREITA da interface  
    print("\n📍 REPLICANDO: Botão DIREITA da Interface")
    print("   🖱️  Equivale a clicar: ➡️ DIREITA (+10°)")
    print("   ⚙️  Comando físico: set_speed(30, -30)")
    print("   🎯 EXPECTATIVA: Robô deve girar para DIREITA")
    input("   ▶️  Pressione ENTER para EXECUTAR...")
    
    # Usa set_speed (método legado) exatamente como a interface
    motor_controller.set_speed(30, -30)  # IDÊNTICO à interface
    time.sleep(3)
    motor_controller.stop()
    
    print("   ❓ O robô girou para DIREITA? (s/n)")
    resultado_dir = input("   ➡️  Resposta: ").lower().strip()
    
    return resultado_esq, resultado_dir

def analyze_results(resultado_esq, resultado_dir):
    """Analisa os resultados e fornece diagnóstico"""
    print("\n" + "="*60)
    print("📊 DIAGNÓSTICO TÉCNICO FINAL")
    print("="*60)
    
    esq_ok = resultado_esq.startswith('s')
    dir_ok = resultado_dir.startswith('s')
    
    print(f"📝 Comando INTERFACE ESQUERDA → Físico: {'✅ CORRETO' if esq_ok else '❌ INVERTIDO'}")
    print(f"📝 Comando INTERFACE DIREITA → Físico: {'✅ CORRETO' if dir_ok else '❌ INVERTIDO'}")
    
    if esq_ok and dir_ok:
        print("\n🎉 RESULTADO: INTERFACE E HARDWARE SINCRONIZADOS")
        print("=" * 60)
        print("✅ Os comandos da interface funcionam corretamente")
        print("✅ O problema reportado pode ter sido resolvido")
        print("🔍 POSSÍVEIS CAUSAS DO PROBLEMA ANTERIOR:")
        print("   • Problema temporário de hardware")
        print("   • Erro na interpretação dos movimentos")
        print("   • Bug corrigido em versão anterior")
        
    elif not esq_ok and not dir_ok:
        print("\n🔧 RESULTADO: HARDWARE INVERTIDO CONFIRMADO")
        print("=" * 60)
        print("❌ Comandos físicos estão 100% invertidos")
        print("❌ Interface espera uma direção, hardware faz o oposto")
        print("🎯 SOLUÇÃO NECESSÁRIA:")
        print("   1. Inverter lógica de direção no robot_motor_controller.py")
        print("   2. OU verificar fiação dos motores")
        print("   3. OU inverter sinais HIGH/LOW nos GPIOs")
        
    else:
        print("\n⚠️ RESULTADO: COMPORTAMENTO INCONSISTENTE")
        print("=" * 60)
        print("⚠️ Apenas um dos comandos funciona corretamente")
        print("⚠️ Possível problema em um motor específico")
        print("🔍 INVESTIGAR:")
        print("   • Fiação de um dos motores")
        print("   • Driver de motor defeituoso")
        print("   • Problema em GPIO específico")
        
    print("\n🎯 PRÓXIMAS AÇÕES RECOMENDADAS:")
    if esq_ok and dir_ok:
        print("   1. Testar interface completa para confirmar funcionamento")
        print("   2. Verificar se problema persiste durante navegação")
        print("   3. Monitorar comportamento em uso normal")
    else:
        print("   1. Implementar correção de hardware/software")
        print("   2. Re-executar este teste após correção")
        print("   3. Validar funcionamento da interface")

def main():
    print("🔄 TESTE: INTERFACE vs ROBÔ FÍSICO")
    print("🎯 Replica comandos EXATOS da interface gráfica")
    print("=" * 60)
    
    if not GPIO_AVAILABLE:
        print("❌ ERRO: Teste requer Raspberry Pi com GPIO")
        return
    
    print_analysis()
    
    print("\n🚀 Inicializando controlador de motores...")
    motor_controller = RobotMotorController()
    
    try:
        print("✅ Controlador inicializado!")
        print("\n📋 IMPORTANTE:")
        print("   • Este teste usa EXATAMENTE os mesmos comandos da interface")
        print("   • Se interface gira errado, este teste também girará errado")
        print("   • Objetivo: Confirmar se problema é no hardware ou na interpretação")
        
        input("\n🎯 Pressione ENTER quando robô estiver em local seguro...")
        
        resultado_esq, resultado_dir = test_interface_commands(motor_controller)
        analyze_results(resultado_esq, resultado_dir)
        
    except Exception as e:
        print(f"❌ ERRO durante teste: {e}")
    
    finally:
        print("\n🧹 Finalizando teste...")
        motor_controller.cleanup()
        print("✅ Teste concluído!")

if __name__ == "__main__":
    main() 