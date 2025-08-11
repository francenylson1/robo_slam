#!/usr/bin/env python3
"""
TESTE COMPARAÇÃO COMANDOS - Compara botões vs navegação autônoma
Identifica exatamente qual diferença está causando a inversão
"""

import sys
import os
import time

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.environment import GPIO_AVAILABLE
from src.core.robot_motor_controller import RobotMotorController

def test_command_comparison():
    """Compara comandos dos botões vs navegação autônoma"""
    print("🔬 TESTE COMPARAÇÃO COMANDOS - Botões vs Navegação")
    print("🎯 Objetivo: Identificar diferença exata entre sistemas")
    print("=" * 70)
    
    if not GPIO_AVAILABLE:
        print("❌ ERRO: Teste requer Raspberry Pi com GPIO")
        return
    
    print("🚀 Inicializando controlador...")
    motor_controller = RobotMotorController()
    
    try:
        print("✅ Controlador inicializado!")
        print("\n" + "="*70)
        print("📋 INSTRUÇÕES IMPORTANTES:")
        print("• Posicione o robô em local seguro")
        print("• Observe APENAS a direção do giro")
        print("• ESQUERDA = anti-horário (sentido contrário dos ponteiros)")
        print("• DIREITA = horário (mesmo sentido dos ponteiros)")
        print("• Ignore se o robô se mover um pouco para frente/trás")
        print("=" * 70)
        
        input("📍 Pressione ENTER quando estiver pronto para começar...")
        
        # TESTE 1: Comando do botão ESQUERDA (sabemos que funciona)
        print("\n" + "="*55)
        print("🔘 TESTE 1: COMANDO DO BOTÃO ESQUERDA")
        print("   📋 Este é o comando exato do botão da interface")
        print("   ⚙️  Comando: motor_controller.set_speed(-30, 30)")
        print("   📖 Significado: Motor esquerdo TRÁS, Motor direito FRENTE")
        print("   🎯 RESULTADO ESPERADO: Robô deve girar para ESQUERDA (anti-horário)")
        print("   ✅ SABEMOS que este comando FUNCIONA CORRETAMENTE")
        input("\n   ▶️  Pressione ENTER para EXECUTAR o teste 1...")
        
        motor_controller.set_speed(-30, 30)  # Exato comando do botão
        time.sleep(2.5)
        motor_controller.stop()
        
        print("\n   👀 OBSERVE: Para qual direção o robô girou?")
        print("   🔄 ESQUERDA = anti-horário (sentido contrário dos ponteiros)")
        print("   🔄 DIREITA = horário (mesmo sentido dos ponteiros)")
        print("   ❓ O robô girou para ESQUERDA (anti-horário)? (s/n)")
        resultado_botao = input("   ➡️  Sua resposta: ").lower().strip()
        
        time.sleep(2)
        
        # TESTE 2: Comando equivalente via set_target_speed 
        print("\n" + "="*55)
        print("🔘 TESTE 2: MESMO COMANDO VIA NAVEGAÇÃO AUTÔNOMA")
        print("   📋 Este comando simula o que a navegação autônoma faz")
        print("   ⚙️  Comando: motor_controller.set_target_speed(-15, 15)")
        print("   📖 Significado: Motor esquerdo TRÁS, Motor direito FRENTE")
        print("   🎯 RESULTADO ESPERADO: Deveria girar ESQUERDA igual ao teste 1")
        print("   ❓ PERGUNTA: Será que funciona igual ao botão?")
        input("\n   ▶️  Pressione ENTER para EXECUTAR o teste 2...")
        
        motor_controller.set_target_speed(-15, 15)  # Valores equivalentes
        time.sleep(2.5)
        motor_controller.stop()
        
        print("\n   👀 OBSERVE: Para qual direção o robô girou DESTA VEZ?")
        print("   🔄 ESQUERDA = anti-horário (sentido contrário dos ponteiros)")
        print("   🔄 DIREITA = horário (mesmo sentido dos ponteiros)")
        print("   ❓ O robô girou para ESQUERDA (anti-horário) como no teste 1? (s/n)")
        resultado_pid = input("   ➡️  Sua resposta: ").lower().strip()
        
        time.sleep(2)
        
        # TESTE 3: Comando inverso via set_target_speed
        print("\n" + "="*55)
        print("🔘 TESTE 3: COMANDO INVERSO VIA NAVEGAÇÃO AUTÔNOMA")
        print("   📋 Agora vamos testar o comando com parâmetros trocados")
        print("   ⚙️  Comando: motor_controller.set_target_speed(15, -15)")
        print("   📖 Significado: Motor esquerdo FRENTE, Motor direito TRÁS")
        print("   🤔 TEORIA: Se há inversão, este comando pode funcionar")
        print("   🎯 RESULTADO ESPERADO: Se há inversão, deveria girar ESQUERDA")
        input("\n   ▶️  Pressione ENTER para EXECUTAR o teste 3...")
        
        motor_controller.set_target_speed(15, -15)  # Valores inversos
        time.sleep(2.5)
        motor_controller.stop()
        
        print("\n   👀 OBSERVE: Para qual direção o robô girou DESTA VEZ?")
        print("   🔄 ESQUERDA = anti-horário (sentido contrário dos ponteiros)")
        print("   🔄 DIREITA = horário (mesmo sentido dos ponteiros)")
        print("   ❓ O robô girou para ESQUERDA (anti-horário)? (s/n)")
        resultado_inverso = input("   ➡️  Sua resposta: ").lower().strip()
        
        # ANÁLISE DOS RESULTADOS
        print("\n" + "="*70)
        print("📊 ANÁLISE COMPLETA DOS RESULTADOS")
        print("="*70)
        
        botao_ok = resultado_botao.startswith('s')
        pid_ok = resultado_pid.startswith('s')
        inverso_ok = resultado_inverso.startswith('s')
        
        print("📝 RESUMO DOS TESTES:")
        print(f"   1️⃣ Botão interface set_speed(-30, 30): {'✅ ESQUERDA' if botao_ok else '❌ NÃO ESQUERDA'}")
        print(f"   2️⃣ Navegação set_target_speed(-15, 15): {'✅ ESQUERDA' if pid_ok else '❌ NÃO ESQUERDA'}")
        print(f"   3️⃣ Navegação inverso set_target_speed(15, -15): {'✅ ESQUERDA' if inverso_ok else '❌ NÃO ESQUERDA'}")
        
        print("\n🔍 DIAGNÓSTICO DETALHADO:")
        
        if botao_ok and pid_ok and not inverso_ok:
            print("   🎉 RESULTADO: NAVEGAÇÃO AUTÔNOMA FUNCIONA CORRETAMENTE!")
            print("   ✅ Tanto botão quanto navegação giram corretamente para esquerda")
            print("   ✅ O comando inverso não funciona (como esperado)")
            print("   🎯 CONCLUSÃO: O problema NÃO está no set_target_speed()")
            print("   🔍 INVESTIGAR: Problema deve estar na cinemática diferencial")
            
        elif botao_ok and not pid_ok and inverso_ok:
            print("   🚨 RESULTADO: INVERSÃO CONFIRMADA NA NAVEGAÇÃO AUTÔNOMA!")
            print("   ✅ Botão funciona corretamente")
            print("   ❌ Navegação normal está invertida")
            print("   ✅ Navegação com parâmetros trocados funciona")
            print("   🎯 CONCLUSÃO: Parâmetros left/right estão trocados no set_target_speed()")
            print("   🔧 SOLUÇÃO: Inverter left_tps ↔ right_tps nas chamadas")
            
        elif botao_ok and not pid_ok and not inverso_ok:
            print("   ❓ RESULTADO: NAVEGAÇÃO AUTÔNOMA NÃO FUNCIONA EM NENHUMA DIREÇÃO")
            print("   ✅ Botão funciona corretamente")
            print("   ❌ Navegação não funciona nem normal nem invertida")
            print("   🎯 CONCLUSÃO: Problema não é simples inversão")
            print("   🔍 INVESTIGAR: Configuração PID, gains ou outra camada")
            
        elif not botao_ok:
            print("   ⚠️  RESULTADO INESPERADO: BOTÃO NÃO FUNCIONOU")
            print("   ❌ Problema no teste ou configuração básica")
            print("   🔧 VERIFICAR: Hardware, conexões ou configuração")
            
        else:
            print("   🤔 RESULTADO: Padrão não reconhecido")
            print("   📋 Investigação manual necessária")
            
        print("\n💡 PRÓXIMOS PASSOS ESPECÍFICOS:")
        if botao_ok and not pid_ok and inverso_ok:
            print("   1. ✅ PROBLEMA IDENTIFICADO: Inversão left/right no set_target_speed()")
            print("   2. 🔧 IMPLEMENTAR: Trocar parâmetros nas chamadas set_target_speed()")
            print("   3. 🧪 TESTAR: Navegação autônoma completa")
            print("   4. 🎉 RESOLVER: Problema de sincronização!")
        elif botao_ok and pid_ok:
            print("   1. ✅ PID FUNCIONANDO: Investigar cinemática diferencial")
            print("   2. 🔍 VERIFICAR: Fórmulas de conversão v,w → left,right")
            print("   3. 🧪 TESTAR: Navegação com pontos específicos")
        else:
            print("   1. 🔍 INVESTIGAR: Configurações PID e gains")
            print("   2. 📋 ANALISAR: Logs de debug do sistema")
            print("   3. 🧪 TESTAR: Componentes individuais")
        
    except Exception as e:
        print(f"❌ ERRO durante teste: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🧹 Finalizando teste...")
        motor_controller.cleanup()
        print("✅ Teste concluído!")

if __name__ == "__main__":
    test_command_comparison() 