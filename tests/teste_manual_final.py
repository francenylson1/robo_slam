#!/usr/bin/env python3
"""
TESTE MANUAL FINAL - Verificação da Correção do move_manual()
Testa apenas o comando manual para confirmar se a sincronização foi alcançada
"""

import sys
import os
import time

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.environment import GPIO_AVAILABLE
from src.core.robot_navigator import RobotNavigator

def test_manual_fixed():
    """Testa se o move_manual agora está sincronizado"""
    print("🎯 TESTE MANUAL FINAL - Verificação da Correção")
    print("🔍 Objetivo: Confirmar se move_manual() está sincronizado")
    print("=" * 60)
    
    if not GPIO_AVAILABLE:
        print("❌ ERRO: Teste requer Raspberry Pi com GPIO")
        return
    
    print("🚀 Inicializando navegador...")
    navigator = RobotNavigator()
    
    try:
        print("✅ Navegador inicializado!")
        
        # TESTE COMANDO MANUAL CORRIGIDO
        print("\n" + "="*50)
        print("🔘 TESTE: COMANDO MANUAL CORRIGIDO")
        print("   ⚙️  Comando: navigator.move_manual(0, -0.3)")
        print("   🎯 EXPECTATIVA: Robô gira ESQUERDA")
        print("   🔧 USANDO: Fórmulas corrigidas sincronizadas")
        input("   ▶️  Pressione ENTER para EXECUTAR...")
        
        navigator.move_manual(0, -0.3)  # forward=0, turn=-0.3 (esquerda)
        time.sleep(2)
        navigator.move_manual(0, 0)  # Para
        
        print("   ❓ O robô girou para ESQUERDA? (s/n)")
        resultado = input("   ➡️  Resposta: ").lower().strip()
        
        # ANÁLISE DO RESULTADO
        print("\n" + "="*60)
        print("📊 RESULTADO FINAL DA SINCRONIZAÇÃO")
        print("="*60)
        
        if resultado.startswith('s'):
            print("🎉 SUCESSO TOTAL! PROBLEMA RESOLVIDO!")
            print("   ✅ Comando manual funciona")
            print("   ✅ Navegação autônoma funciona (confirmado no teste anterior)")
            print("   ✅ SINCRONIZAÇÃO COMPLETA ALCANÇADA!")
            print("\n🚀 SISTEMA PRONTO PARA USO:")
            print("   1. ✅ Botões manuais da interface")
            print("   2. ✅ Navegação autônoma")
            print("   3. ✅ Interface e robô físico sincronizados")
            print("   4. ✅ Fim do tremor")
            print("\n💡 PRÓXIMO PASSO:")
            print("   → Testar interface completa (main.py)")
        else:
            print("❌ PROBLEMA PERSISTE:")
            print("   • Comando manual ainda não funciona")
            print("   • Navegação autônoma funciona")
            print("   🔍 INVESTIGAÇÃO NECESSÁRIA:")
            print("     - Verificar se há outras camadas de conversão")
            print("     - Analisar logs de debug para entender discrepância")
        
    except Exception as e:
        print(f"❌ ERRO durante teste: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🧹 Finalizando teste...")
        navigator.cleanup()
        print("✅ Teste concluído!")

if __name__ == "__main__":
    test_manual_fixed() 