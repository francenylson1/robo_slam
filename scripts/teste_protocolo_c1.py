#!/usr/bin/env python3
"""
Teste de Protocolo do C1
Testa protocolo RPLIDAR com baudrate correto (460800).
"""

import sys
from pathlib import Path
import time
import struct

# Garante que o diretório raiz esteja no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    print("❌ Biblioteca 'pyserial' não disponível")
    sys.exit(1)


class C1ProtocolTester:
    """Testa protocolo RPLIDAR do C1."""
    
    # Comandos RPLIDAR conhecidos
    RPLIDAR_CMD_STOP = bytes([0xA5, 0x25])
    RPLIDAR_CMD_RESET = bytes([0xA5, 0x40])
    RPLIDAR_CMD_SCAN = bytes([0xA5, 0x20])
    RPLIDAR_CMD_FORCE_SCAN = bytes([0xA5, 0x21])
    RPLIDAR_CMD_GET_INFO = bytes([0xA5, 0x50])
    RPLIDAR_CMD_GET_HEALTH = bytes([0xA5, 0x52])
    RPLIDAR_CMD_GET_SAMPLERATE = bytes([0xA5, 0x59])
    
    # Baudrate correto do C1
    C1_BAUDRATE = 460800
    
    def __init__(self, port: str = '/dev/ttyUSB0'):
        self.port = port
        self.serial_conn = None
    
    def connect(self) -> bool:
        """Conecta à porta serial com configuração correta."""
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
            
            self.serial_conn = serial.Serial(
                self.port,
                baudrate=self.C1_BAUDRATE,  # Baudrate correto do C1!
                timeout=1.0,
                write_timeout=1.0,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            print(f"✅ Conectado à {self.port} (baudrate: {self.C1_BAUDRATE})")
            time.sleep(0.5)  # Aguarda estabilização
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            return False
    
    def disconnect(self):
        """Desconecta."""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("🔌 Desconectado")
    
    def send_command(self, cmd: bytes, cmd_name: str = "") -> bytes:
        """Envia comando e aguarda resposta."""
        try:
            self.serial_conn.reset_input_buffer()
            print(f"   → Enviando: {cmd_name or cmd.hex()}")
            self.serial_conn.write(cmd)
            self.serial_conn.flush()
            time.sleep(0.3)  # Aguarda resposta
            
            if self.serial_conn.in_waiting > 0:
                response = self.serial_conn.read(self.serial_conn.in_waiting)
                print(f"      ← Resposta: {len(response)} bytes")
                print(f"         Hex: {response.hex()[:100]}")
                return response
            else:
                print(f"      ← Sem resposta imediata")
                return b''
        except Exception as e:
            print(f"      ❌ Erro: {e}")
            return b''
    
    def test_initialization(self):
        """Testa sequência de inicialização do RPLIDAR."""
        print("\n" + "=" * 70)
        print("🔬 TESTE DE PROTOCOLO RPLIDAR C1")
        print("=" * 70)
        print(f"Porta: {self.port}")
        print(f"Baudrate: {self.C1_BAUDRATE} (correto para C1)")
        print("=" * 70)
        
        if not self.connect():
            return False
        
        print("\n📡 Testando comandos RPLIDAR:")
        print("-" * 70)
        
        # 1. Reset
        print("\n1. RESET")
        response = self.send_command(self.RPLIDAR_CMD_RESET, "RESET")
        if response:
            print("   ✅ C1 respondeu ao RESET!")
        time.sleep(1.0)  # Aguarda reset completar
        
        # 2. Get Health
        print("\n2. GET HEALTH")
        response = self.send_command(self.RPLIDAR_CMD_GET_HEALTH, "GET_HEALTH")
        if response:
            print("   ✅ C1 respondeu ao GET_HEALTH!")
            # Parse health response (formato: [0xA5 0x5A] [status] [error_code])
            if len(response) >= 3:
                status = response[2]
                if len(response) >= 4:
                    error_code = response[3]
                    print(f"      Status: 0x{status:02X}, Error: 0x{error_code:02X}")
        
        # 3. Get Info
        print("\n3. GET INFO")
        response = self.send_command(self.RPLIDAR_CMD_GET_INFO, "GET_INFO")
        if response:
            print("   ✅ C1 respondeu ao GET_INFO!")
            # Parse info response
            if len(response) >= 20:
                print(f"      Model: {response[2]}")
                print(f"      Firmware: {response[3]}.{response[4]}")
                print(f"      Hardware: {response[5]}")
                print(f"      Serial: {response[7:15].hex()}")
        
        # 4. Start Scan
        print("\n4. START SCAN")
        response = self.send_command(self.RPLIDAR_CMD_SCAN, "START_SCAN")
        if response:
            print("   ✅ C1 respondeu ao START_SCAN!")
        
        # 5. Monitora dados de scan
        print("\n5. MONITORANDO DADOS DE SCAN (5 segundos)...")
        print("   (O C1 deve enviar dados continuamente após START_SCAN)")
        start_time = time.time()
        total_bytes = 0
        packet_count = 0
        
        while time.time() - start_time < 5.0:
            if self.serial_conn.in_waiting > 0:
                data = self.serial_conn.read(self.serial_conn.in_waiting)
                total_bytes += len(data)
                packet_count += 1
                print(f"   📨 Pacote #{packet_count}: {len(data)} bytes - {data[:32].hex()}")
            time.sleep(0.1)
        
        if total_bytes > 0:
            print(f"\n   ✅ DADOS RECEBIDOS!")
            print(f"      Total: {total_bytes} bytes em {packet_count} pacotes")
            print(f"      Taxa: {total_bytes/5.0:.1f} bytes/s")
            return True
        else:
            print(f"\n   ⚠️  Nenhum dado recebido durante scan")
        
        # 6. Stop
        print("\n6. STOP")
        self.send_command(self.RPLIDAR_CMD_STOP, "STOP")
        
        self.disconnect()
        return total_bytes > 0


def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Testa protocolo RPLIDAR do C1")
    parser.add_argument('--port', '-p', type=str, default='/dev/ttyUSB0',
                       help='Porta serial (padrão: /dev/ttyUSB0)')
    
    args = parser.parse_args()
    
    tester = C1ProtocolTester(port=args.port)
    success = tester.test_initialization()
    
    if success:
        print("\n" + "=" * 70)
        print("✅ SUCESSO! C1 está funcionando e comunicando!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("⚠️  C1 não respondeu aos comandos")
        print("=" * 70)
        print("Verifique:")
        print("  - C1 está ligado (LED verde)?")
        print("  - Porta correta?")
        print("  - Driver CP2102 instalado?")
    
    tester.disconnect()


if __name__ == "__main__":
    main()

