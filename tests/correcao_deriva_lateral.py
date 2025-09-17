import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import *

def calcular_fator_correcao(left_ticks, right_ticks):
    """
    Calcula o fator de correção baseado nos ticks medidos.
    
    Args:
        left_ticks: Ticks do motor esquerdo
        right_ticks: Ticks do motor direito
    
    Returns:
        dict: Fatores de correção para cada motor
    """
    if left_ticks == 0 or right_ticks == 0:
        return {'left': 1.0, 'right': 1.0, 'error': 'Dados inválidos'}
    
    # Calcula as distâncias
    left_distance = (left_ticks / TICKS_PER_REVOLUTION) * ROBOT_WHEEL_CIRCUMFERENCE_M
    right_distance = (right_ticks / TICKS_PER_REVOLUTION) * ROBOT_WHEEL_CIRCUMFERENCE_M
    
    # Determina qual motor está mais rápido
    if left_distance > right_distance:
        # Motor esquerdo mais rápido - precisa ser reduzido
        correction_factor = right_distance / left_distance
        return {
            'left': correction_factor,
            'right': 1.0,
            'analysis': f'Motor esquerdo {((left_distance/right_distance - 1) * 100):.1f}% mais rápido',
            'recommendation': f'Aplicar fator {correction_factor:.4f} ao motor esquerdo'
        }
    else:
        # Motor direito mais rápido - precisa ser reduzido
        correction_factor = left_distance / right_distance
        return {
            'left': 1.0,
            'right': correction_factor,
            'analysis': f'Motor direito {((right_distance/left_distance - 1) * 100):.1f}% mais rápido',
            'recommendation': f'Aplicar fator {correction_factor:.4f} ao motor direito'
        }

def gerar_config_corrigido(left_factor, right_factor):
    """
    Gera o código de correção para ser aplicado no robot_motor_controller.py
    """
    correction_code = f"""
# === CORREÇÃO DE DERIVA LATERAL ===
# Fatores de correção baseados em teste de calibração
# Data: {time.strftime('%Y-%m-%d %H:%M:%S')}
LEFT_MOTOR_CORRECTION_FACTOR = {left_factor:.6f}
RIGHT_MOTOR_CORRECTION_FACTOR = {right_factor:.6f}

# Aplicar na função set_target_speed:
# left_tps_corrected = left_tps * LEFT_MOTOR_CORRECTION_FACTOR
# right_tps_corrected = right_tps * RIGHT_MOTOR_CORRECTION_FACTOR
"""
    return correction_code

def main():
    print("="*60)
    print("CALCULADORA DE CORREÇÃO DE DERIVA LATERAL")
    print("="*60)
    print("Este script calcula fatores de correção baseados nos")
    print("resultados do teste de deriva lateral.")
    print()
    
    try:
        # Solicita os dados do teste
        print("Digite os resultados do teste de deriva lateral:")
        left_ticks = int(input("Ticks do motor esquerdo: "))
        right_ticks = int(input("Ticks do motor direito: "))
        
        # Calcula a correção
        correction = calcular_fator_correcao(left_ticks, right_ticks)
        
        if 'error' in correction:
            print(f"❌ Erro: {correction['error']}")
            return
        
        # Mostra os resultados
        print("\n" + "="*60)
        print("ANÁLISE DOS RESULTADOS")
        print("="*60)
        print(f"📊 {correction['analysis']}")
        print(f"💡 {correction['recommendation']}")
        
        print("\n" + "="*60)
        print("FATORES DE CORREÇÃO")
        print("="*60)
        print(f"Motor Esquerdo: {correction['left']:.6f}")
        print(f"Motor Direito:  {correction['right']:.6f}")
        
        # Gera o código de correção
        correction_code = gerar_config_corrigido(correction['left'], correction['right'])
        
        print("\n" + "="*60)
        print("CÓDIGO DE CORREÇÃO")
        print("="*60)
        print("Adicione este código ao robot_motor_controller.py:")
        print()
        print(correction_code)
        
        # Salva em arquivo
        with open('correcao_deriva_config.txt', 'w') as f:
            f.write(correction_code)
        
        print(f"\n✅ Código salvo em 'correcao_deriva_config.txt'")
        
        # Instruções de aplicação
        print("\n" + "="*60)
        print("INSTRUÇÕES DE APLICAÇÃO")
        print("="*60)
        print("1. Abra o arquivo src/core/robot_motor_controller.py")
        print("2. Adicione as constantes no início do arquivo")
        print("3. Modifique a função set_target_speed para aplicar os fatores:")
        print("   left_tps_corrected = left_tps * LEFT_MOTOR_CORRECTION_FACTOR")
        print("   right_tps_corrected = right_tps * RIGHT_MOTOR_CORRECTION_FACTOR")
        print("4. Use os valores corrigidos no resto da função")
        print("5. Teste novamente com o teste de deriva lateral")
        
    except ValueError:
        print("❌ Erro: Digite apenas números inteiros para os ticks.")
    except KeyboardInterrupt:
        print("\n\nOperação cancelada pelo usuário.")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    import time
    main()