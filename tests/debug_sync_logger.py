#!/usr/bin/env python3
"""
Debug Sync Logger - Adiciona logs específicos para rastrear problema de sincronização
Remove logs desnecessários e adiciona logs focados no problema da inversão
"""

import os

def add_sync_logs():
    """Adiciona logs específicos para rastrear sincronização"""
    
    # 1. LOGS NA INTERFACE (main_window.py)
    main_window_path = "src/interfaces/main_window.py"
    
    print("🔧 Adicionando logs de sincronização na interface...")
    
    # Encontrar e modificar _execute_physical_rotation
    with open(main_window_path, 'r') as f:
        content = f.read()
    
    # Adicionar log específico no _execute_physical_rotation
    old_rotation_code = '''        if direction == "clockwise": # Giro horário (DIREITA)
            self.navigator.motors.set_speed(30, -30)  # ESQ+, DIR-
        elif direction == "counterclockwise": # Giro anti-horário (ESQUERDA)
            self.navigator.motors.set_speed(-30, 30)  # ESQ-, DIR+'''
    
    new_rotation_code = '''        if direction == "clockwise": # Giro horário (DIREITA)
            print(f"🔴 SYNC_DEBUG: INTERFACE → DIREITA | Comando: set_speed(30, -30)")
            self.navigator.motors.set_speed(30, -30)  # ESQ+, DIR-
        elif direction == "counterclockwise": # Giro anti-horário (ESQUERDA)
            print(f"🟢 SYNC_DEBUG: INTERFACE → ESQUERDA | Comando: set_speed(-30, 30)")
            self.navigator.motors.set_speed(-30, 30)  # ESQ-, DIR+'''
    
    if old_rotation_code in content:
        content = content.replace(old_rotation_code, new_rotation_code)
        print("  ✅ Logs adicionados na interface")
    else:
        print("  ⚠️  Código da interface não encontrado - pode ter mudado")
    
    with open(main_window_path, 'w') as f:
        f.write(content)
    
    # 2. LOGS NO MOTOR CONTROLLER (robot_motor_controller.py)
    motor_controller_path = "src/core/robot_motor_controller.py"
    
    print("🔧 Adicionando logs no controle de motores...")
    
    with open(motor_controller_path, 'r') as f:
        content = f.read()
    
    # Adicionar log no set_speed (usado pelos botões)
    old_set_speed = '''    def set_speed(self, left_tps, right_tps):
        """Define velocidades diretas para ambos os motores (sem PID)"""
        if not GPIO_AVAILABLE:
            return'''
    
    new_set_speed = '''    def set_speed(self, left_tps, right_tps):
        """Define velocidades diretas para ambos os motores (sem PID)"""
        print(f"🎯 SYNC_DEBUG: set_speed(left={left_tps}, right={right_tps})")
        if not GPIO_AVAILABLE:
            return'''
    
    if old_set_speed in content:
        content = content.replace(old_set_speed, new_set_speed)
        print("  ✅ Logs adicionados no set_speed")
    else:
        print("  ⚠️  Código set_speed não encontrado")
    
    # Adicionar log no set_target_speed (usado pela navegação)
    old_set_target = '''    def set_target_speed(self, left_tps, right_tps):
        """Define velocidades alvo para controle PID"""
        if not GPIO_AVAILABLE:
            return'''
    
    new_set_target = '''    def set_target_speed(self, left_tps, right_tps):
        """Define velocidades alvo para controle PID"""
        print(f"🎯 SYNC_DEBUG: set_target_speed(left={left_tps:.1f}, right={right_tps:.1f})")
        if not GPIO_AVAILABLE:
            return'''
    
    if old_set_target in content:
        content = content.replace(old_set_target, new_set_target)
        print("  ✅ Logs adicionados no set_target_speed")
    else:
        print("  ⚠️  Código set_target_speed não encontrado")
    
    with open(motor_controller_path, 'w') as f:
        f.write(content)
    
    # 3. DESABILITAR LOGS DO PID (muito poluído)
    print("🧹 Desabilitando logs do PID...")
    
    # Comentar logs do PID que estão poluindo
    old_pid_debug = '''        if self.debug:
            print(f"DEBUG PID: Target L:{left_target:.1f}tps R:{right_target:.1f}tps | Real L:{left_real:.1f}tps R:{right_real:.1f}tps | Output L:{left_power:.1f}% R:{right_power:.1f}%")'''
    
    new_pid_debug = '''        if False:  # DESABILITADO para logs limpos
            print(f"DEBUG PID: Target L:{left_target:.1f}tps R:{right_target:.1f}tps | Real L:{left_real:.1f}tps R:{right_real:.1f}tps | Output L:{left_power:.1f}% R:{right_power:.1f}%")'''
    
    with open(motor_controller_path, 'r') as f:
        content = f.read()
    
    if old_pid_debug in content:
        content = content.replace(old_pid_debug, new_pid_debug)
        print("  ✅ Logs do PID desabilitados")
    
    with open(motor_controller_path, 'w') as f:
        f.write(content)
    
    # 4. LOGS NA CINEMÁTICA DIFERENCIAL (robot_navigator.py)
    navigator_path = "src/core/robot_navigator.py"
    
    print("🔧 Adicionando logs na cinemática diferencial...")
    
    with open(navigator_path, 'r') as f:
        content = f.read()
    
    # Adicionar log na cinemática diferencial
    old_kinematics = '''        # CORREÇÃO DEFINITIVA: Cinemática diferencial baseado em teste de laboratório
        # TESTE PROVOU: Para w>0 (esquerda), left deve ser negativo, right positivo
        left_wheel_speed_ms = v - (w * L) / 2.0   # DEFINITIVO: left SUBTRAI para giro esquerda correto
        right_wheel_speed_ms = v + (w * L) / 2.0  # DEFINITIVO: right SOMA para giro esquerda correto'''
    
    new_kinematics = '''        # CORREÇÃO DEFINITIVA: Cinemática diferencial baseado em teste de laboratório
        # TESTE PROVOU: Para w>0 (esquerda), left deve ser negativo, right positivo
        left_wheel_speed_ms = v - (w * L) / 2.0   # DEFINITIVO: left SUBTRAI para giro esquerda correto
        right_wheel_speed_ms = v + (w * L) / 2.0  # DEFINITIVO: right SOMA para giro esquerda correto
        
        print(f"🧮 SYNC_DEBUG: CINEMÁTICA | v={v:.3f}, w={w:.3f} → left_ms={left_wheel_speed_ms:.3f}, right_ms={right_wheel_speed_ms:.3f}")'''
    
    if old_kinematics in content:
        content = content.replace(old_kinematics, new_kinematics)
        print("  ✅ Logs adicionados na cinemática")
    
    with open(navigator_path, 'w') as f:
        f.write(content)
    
    # 5. LOG FINAL DO TPS
    old_tps_calc = '''        # --- 4. Converter m/s para Ticks por Segundo (TPS) ---
        # TPS = (metros / segundo) / (metros / revolução) * (ticks / revolução)
        left_tps = (left_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps = (right_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION'''
    
    new_tps_calc = '''        # --- 4. Converter m/s para Ticks por Segundo (TPS) ---
        # TPS = (metros / segundo) / (metros / revolução) * (ticks / revolução)
        left_tps = (left_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        right_tps = (right_wheel_speed_ms / ROBOT_WHEEL_CIRCUMFERENCE_M) * TICKS_PER_REVOLUTION
        
        print(f"⚙️  SYNC_DEBUG: TPS FINAL | left_tps={left_tps:.1f}, right_tps={right_tps:.1f}")'''
    
    with open(navigator_path, 'r') as f:
        content = f.read()
    
    if old_tps_calc in content:
        content = content.replace(old_tps_calc, new_tps_calc)
        print("  ✅ Logs TPS adicionados")
    
    with open(navigator_path, 'w') as f:
        f.write(content)
    
    print("\n🎯 LOGS DE SINCRONIZAÇÃO CONFIGURADOS!")
    print("📝 AGORA VOCÊ VERÁ APENAS:")
    print("   🟢 SYNC_DEBUG: INTERFACE → ESQUERDA/DIREITA")
    print("   🧮 SYNC_DEBUG: CINEMÁTICA (v,w → left_ms,right_ms)")
    print("   ⚙️  SYNC_DEBUG: TPS FINAL (left_tps, right_tps)")
    print("   🎯 SYNC_DEBUG: set_speed/set_target_speed")
    print("\n🚀 Execute main.py e teste os botões!")

if __name__ == "__main__":
    add_sync_logs() 