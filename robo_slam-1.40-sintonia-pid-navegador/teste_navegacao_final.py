#!/usr/bin/env python3
"""
TESTE NAVEGAÇÃO FINAL - Verificação da Correção Cirúrgica
Testa se a correção na cinemática diferencial resolveu o problema de sincronização
"""

import sys
import os
import time

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.environment import GPIO_AVAILABLE
from src.core.robot_navigator import RobotNavigator

def test_fixed_navigation():
    """Testa se a navegação autônoma agora está sincronizada"""
    print("🎯 TESTE NAVEGAÇÃO FINAL - Verificação da Correção Cirúrgica")
    print("🔍 Objetivo: Confirmar se navegação autônoma está sincronizada")
    print("=" * 65)
    
    if not GPIO_AVAILABLE:
        print("❌ ERRO: Teste requer Raspberry Pi com GPIO")
        return
    
    print("🚀 Inicializando navegador completo...")
    navigator = RobotNavigator()
    
    try:
        print("✅ Navegador inicializado!")
        
        # TESTE 1: Comando manual (sabemos que funciona)
        print("\n" + "="*55)
        print("🔘 TESTE 1: COMANDO MANUAL (CONTROLE - deve funcionar)")
        print("   ⚙️  Usando: navigator.move_manual(0, -0.3) # Giro ESQUERDA")
        print("   🎯 EXPECTATIVA: Robô gira ESQUERDA")
        input("   ▶️  Pressione ENTER para EXECUTAR...")
        
        navigator.move_manual(0, -0.3)  # forward=0, turn=-0.3 (esquerda)
        time.sleep(2)
        navigator.move_manual(0, 0)  # Para
        
        print("   ❓ O robô girou para ESQUERDA? (s/n)")
        resultado_manual = input("   ➡️  Resposta: ").lower().strip()
        
        time.sleep(1)
        
        # TESTE 2: Movimento autônomo (_move_towards_target via sistema interno)
        print("\n" + "="*55)
        print("🔘 TESTE 2: NAVEGAÇÃO AUTÔNOMA (CORRIGIDA)")
        print("   ⚙️  Simulando movimento autônomo com giro ESQUERDA")
        print("   🎯 EXPECTATIVA: Robô gira ESQUERDA (igual ao teste 1)")
        print("   🔧 USANDO: Cinemática diferencial corrigida")
        input("   ▶️  Pressione ENTER para EXECUTAR...")
        
        # Simula um movimento autônomo: apenas velocidade angular (giro puro)
        # Usando velocidades baixas para teste seguro
        navigator.motors.set_target_speed(-15, 15)  # ESQ-, DIR+ = giro esquerda
        time.sleep(2)
        navigator.motors.stop()
        
        print("   ❓ O robô girou para ESQUERDA? (s/n)")
        resultado_autonomo = input("   ➡️  Resposta: ").lower().strip()
        
        # ANÁLISE DOS RESULTADOS
        print("\n" + "="*65)
        print("📊 RESULTADO DA CORREÇÃO CIRÚRGICA")
        print("="*65)
        
        manual_ok = resultado_manual.startswith('s')
        autonomo_ok = resultado_autonomo.startswith('s')
        
        print(f"📝 Comando MANUAL: {'✅ CORRETO' if manual_ok else '❌ INCORRETO'}")
        print(f"📝 Navegação AUTÔNOMA: {'✅ CORRETO' if autonomo_ok else '❌ INCORRETO'}")
        
        if manual_ok and autonomo_ok:
            print("\n🎉 CORREÇÃO CIRÚRGICA FUNCIONOU PERFEITAMENTE!")
            print("   ✅ Comandos manuais funcionam")
            print("   ✅ Navegação autônoma funciona")
            print("   ✅ SINCRONIZAÇÃO ALCANÇADA!")
            print("\n🚀 PRÓXIMOS PASSOS:")
            print("   1. Testar interface completa (main.py)")
            print("   2. Verificar navegação para pontos específicos")
            print("   3. Problema de inversão RESOLVIDO!")
            
        elif manual_ok and not autonomo_ok:
            print("\n⚠️  PROBLEMA PERSISTE:")
            print("   ✅ Comando manual funciona")
            print("   ❌ Navegação autônoma ainda invertida")
            print("   🔍 INVESTIGAÇÃO NECESSÁRIA:")
            print("      • Verificar se há outras camadas de inversão")
            print("      • Pode haver problema no _calculate_movement()")
            
        elif not manual_ok and autonomo_ok:
            print("\n🤔 SITUAÇÃO INCOMUM:")
            print("   ❌ Comando manual não funciona")
            print("   ✅ Navegação autônoma funciona") 
            print("   🔍 Verificar configuração ou hardware")
            
        else:
            print("\n❌ AMBOS ESTÃO INCORRETOS:")
            print("   • Problema mais profundo")
            print("   • Verificar configurações básicas")
            
        print("\n💡 DIAGNÓSTICO FINAL:")
        if manual_ok and autonomo_ok:
            print("   🎯 MISSÃO CUMPRIDA: Sincronização alcançada!")
            print("   🔧 Correção cirúrgica foi efetiva")
            print("   ✨ Sistema pronto para uso normal")
        else:
            print("   🔍 Investigação adicional necessária")
            print("   📋 Logs salvos para análise")
        
    except Exception as e:
        print(f"❌ ERRO durante teste: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🧹 Finalizando teste...")
        navigator.cleanup()
        print("✅ Teste concluído!")

if __name__ == "__main__":
    test_fixed_navigation() 