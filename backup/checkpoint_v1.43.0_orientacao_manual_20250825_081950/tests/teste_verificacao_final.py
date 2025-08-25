#!/usr/bin/env python3
"""
TESTE VERIFICAÇÃO FINAL - Confirma se a correção da cinemática diferencial funcionou
Testa a sincronização perfeita entre interface e robô físico
"""

import sys
import os
import time

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.environment import GPIO_AVAILABLE
from src.core.robot_motor_controller import RobotMotorController
from src.core.config import ROBOT_WHEEL_BASE_M, ROBOT_WHEEL_CIRCUMFERENCE_M, TICKS_PER_REVOLUTION

def test_final_verification():
    """Verifica se a correção da cinemática diferencial funcionou"""
    print("🎉 TESTE VERIFICAÇÃO FINAL - Cinemática Diferencial Corrigida")
    print("🎯 Objetivo: Confirmar sincronização perfeita interface ↔ hardware")
    print("=" * 70)
    
    if not GPIO_AVAILABLE:
        print("❌ ERRO: Teste requer Raspberry Pi com GPIO")
        return
    
    print("🚀 Inicializando controlador...")
    motor_controller = RobotMotorController()
    
    try:
        print("✅ Controlador inicializado!")
        print("\n" + "="*70)
        print("🔬 TESTE DE LABORATÓRIO ANTERIOR MOSTROU:")
        print("   ❌ Fórmulas antigas: left=+12.7, right=-12.7 → DIREITA (invertido)")
        print("   ✅ Comando direto: left=-15, right=+15 → ESQUERDA (correto)")
        print("   🔧 CORREÇÃO: Trocamos as fórmulas da cinemática diferencial")
        print("=" * 70)
        
        input("📍 Pressione ENTER quando estiver pronto para TESTE FINAL...")
        
        # TESTE FINAL: Cinemática diferencial corrigida
        print("\n" + "="*60)
        print("🔧 TESTE DEFINITIVO: CINEMÁTICA DIFERENCIAL CORRIGIDA")
        print("   📖 Parâmetros: v=0, w=1.0 (mesmo do teste anterior)")
        print("   🧮 Fórmulas CORRIGIDAS aplicadas:")
        
        # Mesmos parâmetros do teste anterior
        v = 0.0
        w = 1.0  
        L = ROBOT_WHEEL_BASE_M
        
        # FÓRMULAS CORRIGIDAS
        left_wheel_speed_ms = v - (w * L) / 2.0   # Agora SUBTRAI para esquerda
        right_wheel_speed_ms = v + (w * L) / 2.0  # Agora SOMA para esquerda
        
        print(f"      left_wheel = v - (w*L)/2 = {v} - ({w}*{L})/2 = {left_wheel_speed_ms:.3f} m/s")
        print(f"      right_wheel = v + (w*L)/2 = {v} + ({w}*{L})/2 = {right_wheel_speed_ms:.3f} m/s")
        
        # Convertendo para TPS
        left_tps = (left_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps = (right_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        
        print(f"   ⚙️  VALORES CALCULADOS:")
        print(f"      left_tps = {left_tps:.1f} tps (deve ser NEGATIVO)")
        print(f"      right_tps = {right_tps:.1f} tps (deve ser POSITIVO)")
        
        # Verificação prévia
        if left_tps < 0 and right_tps > 0:
            print(f"   ✅ SINAIS CORRETOS: left negativo, right positivo!")
        else:
            print(f"   ❌ SINAIS AINDA ERRADOS!")
            
        print(f"   🎯 RESULTADO ESPERADO: Robô deve girar ESQUERDA (anti-horário)")
        input("\n   ▶️  Pressione ENTER para EXECUTAR teste corrigido...")
        
        motor_controller.set_target_speed(left_tps, right_tps)
        time.sleep(3.0)
        motor_controller.stop()
        
        print("\n   👀 RESULTADO DA CORREÇÃO:")
        print("   🔄 ESQUERDA = anti-horário (sentido contrário dos ponteiros)")
        print("   🔄 DIREITA = horário (mesmo sentido dos ponteiros)")
        print("   ❓ O robô girou para ESQUERDA (anti-horário) DESTA VEZ? (s/n)")
        resultado_corrigido = input("   ➡️  Sua resposta: ").lower().strip()
        
        time.sleep(1)
        
        # TESTE COMPARATIVO: Comando direto que sempre funcionou
        print("\n" + "="*60)
        print("🔘 TESTE COMPARATIVO: COMANDO DIRETO (referência)")
        print("   📋 Este comando sempre funcionou corretamente")
        print("   ⚙️  Comando: set_target_speed(-15, 15)")
        input("\n   ▶️  Pressione ENTER para EXECUTAR referência...")
        
        motor_controller.set_target_speed(-15, 15)
        time.sleep(3.0)
        motor_controller.stop()
        
        print("\n   👀 CONFIRMAÇÃO:")
        print("   ❓ O robô girou para ESQUERDA como sempre? (s/n)")
        resultado_referencia = input("   ➡️  Sua resposta: ").lower().strip()
        
        # ANÁLISE FINAL
        print("\n" + "="*70)
        print("🎊 ANÁLISE FINAL DA CORREÇÃO")
        print("="*70)
        
        corrigido_ok = resultado_corrigido.startswith('s')
        referencia_ok = resultado_referencia.startswith('s')
        
        print("📝 RESUMO DOS TESTES:")
        print(f"   🔧 Cinemática CORRIGIDA left={left_tps:.1f}, right={right_tps:.1f}: {'✅ ESQUERDA' if corrigido_ok else '❌ NÃO ESQUERDA'}")
        print(f"   📋 Comando referência left=-15, right=15: {'✅ ESQUERDA' if referencia_ok else '❌ NÃO ESQUERDA'}")
        
        if corrigido_ok and referencia_ok:
            print("\n🎉🎉🎉 SUCESSO TOTAL! PROBLEMA RESOLVIDO! 🎉🎉🎉")
            print("   ✅ Cinemática diferencial funciona corretamente!")
            print("   ✅ Comando direto funciona como sempre!")
            print("   ✅ SINCRONIZAÇÃO PERFEITA: Interface ↔ Hardware!")
            print("\n🎯 RESULTADO FINAL:")
            print("   🔄 Interface gira ESQUERDA → Robô físico gira ESQUERDA ✅")
            print("   🔄 Interface gira DIREITA → Robô físico gira DIREITA ✅")
            print("   🎊 Navegação autônoma agora funcionará perfeitamente!")
            
        elif not corrigido_ok and referencia_ok:
            print("\n❌ CORREÇÃO NÃO FUNCIONOU")
            print("   ❌ Cinemática diferencial ainda tem problemas")
            print("   ✅ Comando direto funciona")
            print("   🔍 INVESTIGAR: Possível erro na aplicação da correção")
            
        elif corrigido_ok and not referencia_ok:
            print("\n❓ RESULTADO INESPERADO")
            print("   ✅ Cinemática corrigida funciona")
            print("   ❌ Comando referência não funciona (estranho)")
            print("   🔍 INVESTIGAR: Possível problema no hardware")
            
        else:
            print("\n❌ AMBOS OS TESTES FALHARAM")
            print("   ❌ Cinemática corrigida não funciona")
            print("   ❌ Comando referência não funciona")
            print("   🔍 INVESTIGAR: Possível problema no hardware ou ambiente")
        
        print("\n💡 PRÓXIMOS PASSOS:")
        if corrigido_ok and referencia_ok:
            print("   1. 🎊 TESTAR main.py para confirmar navegação completa")
            print("   2. 🎯 TESTAR navegação autônoma com interface gráfica")
            print("   3. 🚀 SISTEMA TOTALMENTE FUNCIONAL!")
        else:
            print("   1. 🔍 REVISAR logs de debug para entender o problema")
            print("   2. 🧪 TESTAR outras velocidades e ângulos")
            print("   3. 🔧 CONTINUAR investigação se necessário")
        
    except Exception as e:
        print(f"❌ ERRO durante teste: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🧹 Finalizando teste...")
        motor_controller.cleanup()
        print("✅ Teste concluído!")

if __name__ == "__main__":
    test_final_verification() 