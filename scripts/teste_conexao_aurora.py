#!/usr/bin/env python3
"""
Script simples para testar conexão com o dispositivo Aurora.
"""

import sys
from pathlib import Path

# Adiciona SDK ao path
workspace_root = Path(__file__).parent.parent
sdk_path = workspace_root / "py_aurora_remote-main" / "python_bindings"

if not sdk_path.exists():
    print(f"❌ SDK do Aurora não encontrado em: {sdk_path}")
    sys.exit(1)

if str(sdk_path) not in sys.path:
    sys.path.insert(0, str(sdk_path))

try:
    from slamtec_aurora_sdk import AuroraSDK
    from slamtec_aurora_sdk.exceptions import AuroraSDKError, ConnectionError
except ImportError as e:
    print(f"❌ Não foi possível importar o SDK do Aurora: {e}")
    sys.exit(1)

def test_connection():
    """Testa conexão com o Aurora"""
    print("🔌 Teste de Conexão com Aurora")
    print("=" * 50)
    
    # Carrega configuração
    import json
    config_path = workspace_root / "config" / "mapping.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        aurora_config = config.get("aurora", {})
    else:
        aurora_config = {
            "ip": "192.168.11.1",
            "port": 7447,
            "auto_discover": True
        }
    
    print(f"\n📋 Configuração:")
    print(f"   IP: {aurora_config.get('ip', 'N/A')}")
    print(f"   Porta: {aurora_config.get('port', 'N/A')}")
    print(f"   Auto-discover: {aurora_config.get('auto_discover', True)}")
    
    sdk = AuroraSDK()
    
    try:
        print(f"\n🔍 Tentando conectar...")
        
        # Tenta conectar
        if aurora_config.get("auto_discover", True):
            print(f"   Modo: Descoberta automática")
            devices = sdk.discover_devices(timeout=5.0)
            
            if not devices:
                print(f"   ❌ Nenhum dispositivo encontrado")
                return False
            
            print(f"   ✅ {len(devices)} dispositivo(s) encontrado(s):")
            for i, device in enumerate(devices):
                print(f"      Dispositivo {i}: {device.get('device_name', 'Unknown')}")
                for j, option in enumerate(device.get('options', [])):
                    print(f"        Opção {j}: {option.get('protocol', 'N/A')}://{option.get('address', 'N/A')}:{option.get('port', 'N/A')}")
            
            print(f"\n   Conectando ao primeiro dispositivo...")
            sdk.connect(device_info=devices[0])
        else:
            ip = aurora_config.get("ip", "192.168.11.1")
            port = aurora_config.get("port", 7447)
            # Tenta diferentes formatos de connection string
            connection_strings = [
                f"tcp://{ip}:{port}",  # Formato completo
                f"{ip}:{port}",        # Formato simples
                ip                     # Apenas IP
            ]
            print(f"   Modo: Conexão direta")
            print(f"   IP: {ip}, Porta: {port}")
            
            connected = False
            for conn_str in connection_strings:
                try:
                    print(f"   Tentando: {conn_str}...")
                    sdk.connect(connection_string=conn_str)
                    connected = True
                    print(f"   ✅ Conectado usando: {conn_str}")
                    break
                except Exception as e:
                    print(f"   ❌ Falhou: {e}")
                    continue
            
            if not connected:
                raise ConnectionError("Não foi possível conectar com nenhum formato de connection string")
        
        print(f"   ✅ Conectado com sucesso!")
        
        # Obtém informações do dispositivo
        print(f"\n📱 Informações do Dispositivo:")
        try:
            device_name = sdk.controller.get_device_name()
            print(f"   Nome: {device_name}")
        except:
            pass
        
        try:
            device_model = sdk.controller.get_device_model()
            print(f"   Modelo: {device_model}")
        except:
            pass
        
        try:
            firmware_version = sdk.controller.get_firmware_version()
            print(f"   Firmware: {firmware_version}")
        except:
            pass
        
        # Testa obtenção de pose
        print(f"\n🧪 Testando funcionalidades:")
        try:
            position, rotation, timestamp = sdk.get_current_pose(use_se3=True)
            if position and len(position) >= 3:
                print(f"   ✅ Pose atual: pos=({position[0]:.3f}, {position[1]:.3f}, {position[2]:.3f})")
        except Exception as e:
            # Tenta formato alternativo
            try:
                pose = sdk.get_current_pose(use_se3=False)
                if pose and len(pose) >= 3:
                    print(f"   ✅ Pose atual: pos=({pose[0]:.3f}, {pose[1]:.3f}, {pose[2]:.3f})")
            except:
                print(f"   ⚠️  Não foi possível obter pose: {e}")
        
        # Testa informações de mapa
        try:
            sdk.controller.enable_map_data_syncing(True)
            global_info = sdk.data_provider.get_global_mapping_info()
            kf_count = global_info.get('total_kf_count', 0)
            mp_count = global_info.get('total_mp_count', 0)
            print(f"   ✅ Informações de mapa: {kf_count} keyframes, {mp_count} map points")
        except Exception as e:
            print(f"   ⚠️  Não foi possível obter informações de mapa: {e}")
        
        print(f"\n✅ Teste de conexão concluído com sucesso!")
        return True
        
    except ConnectionError as e:
        print(f"\n❌ Erro de conexão: {e}")
        return False
    except AuroraSDKError as e:
        print(f"\n❌ Erro do SDK: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            if sdk.is_connected():
                sdk.disconnect()
                print(f"\n🔌 Desconectado")
            sdk.release()
        except:
            pass

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

