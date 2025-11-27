#!/usr/bin/env python3
"""
Script de Teste de Comunicação com C1
Testa diferentes protocolos e comandos para identificar como o C1 se comunica.
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

from src.c1_mapping.capture.c1_usb_client import C1USBClient
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class C1CommunicationTester:
    """Testa comunicação com o C1 via Serial."""
    
    # Comandos comuns para LIDAR/SLAM
    TEST_COMMANDS = {
        'info': [
            b'INFO\r\n',
            b'GETINFO\r\n',
            b'VERSION\r\n',
            b'STATUS\r\n',
            b'?\r\n',
        ],
        'start': [
            b'START\r\n',
            b'START_SCAN\r\n',
            b'SCAN\r\n',
        ],
        'stop': [
            b'STOP\r\n',
            b'STOP_SCAN\r\n',
        ],
        'reset': [
            b'RESET\r\n',
            b'RESTART\r\n',
        ],
        'binary': [
            bytes([0xAA, 0x55]),  # Header comum
            bytes([0xA5, 0x5A]),  # Header alternativo
            bytes([0x55, 0xAA, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00]),  # Comando de info
        ]
    }
    
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
    
    def connect(self) -> bool:
        """Conecta à porta serial."""
        try:
            self.serial_conn = serial.Serial(
                self.port,
                baudrate=self.baudrate,
                timeout=1.0,
                write_timeout=1.0
            )
            print(f"✅ Conectado à {self.port} (baudrate: {self.baudrate})")
            time.sleep(0.5)  # Aguarda estabilização
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            return False
    
    def disconnect(self):
        """Desconecta da porta serial."""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("🔌 Desconectado")
    
    def test_communication(self):
        """Testa comunicação com diferentes comandos."""
        if not self.connect():
            return
        
        print("\n" + "=" * 70)
        print("🔬 TESTE DE COMUNICAÇÃO COM C1")
        print("=" * 70)
        print()
        
        # Limpa buffer
        self.serial_conn.reset_input_buffer()
        self.serial_conn.reset_output_buffer()
        
        # Testa leitura passiva (dados que o C1 envia automaticamente)
        print("📥 TESTE 1: Leitura Passiva (aguardando dados do C1)")
        print("-" * 70)
        self._test_passive_read()
        print()
        
        # Testa comandos de texto
        print("⌨️  TESTE 2: Comandos de Texto")
        print("-" * 70)
        self._test_text_commands()
        print()
        
        # Testa comandos binários
        print("🔢 TESTE 3: Comandos Binários")
        print("-" * 70)
        self._test_binary_commands()
        print()
        
        # Testa diferentes baudrates
        print("⚡ TESTE 4: Diferentes Baudrates")
        print("-" * 70)
        self._test_baudrates()
        print()
        
        self.disconnect()
    
    def _test_passive_read(self, duration: float = 3.0):
        """Testa leitura passiva de dados."""
        print(f"   Aguardando dados por {duration} segundos...")
        print("   (Alguns LIDARs enviam dados continuamente)")
        
        start_time = time.time()
        data_received = []
        
        while time.time() - start_time < duration:
            if self.serial_conn.in_waiting > 0:
                data = self.serial_conn.read(self.serial_conn.in_waiting)
                data_received.append(data)
                print(f"   📨 Dados recebidos: {len(data)} bytes")
                print(f"      Hex: {data.hex()[:100]}...")
                print(f"      ASCII: {self._safe_decode(data[:50])}")
            time.sleep(0.1)
        
        if data_received:
            print(f"\n   ✅ Total de dados recebidos: {sum(len(d) for d in data_received)} bytes")
            print(f"   📊 Pacotes recebidos: {len(data_received)}")
            
            # Analisa padrões
            self._analyze_data_patterns(data_received)
        else:
            print("   ⚠️  Nenhum dado recebido (C1 pode não enviar dados automaticamente)")
    
    def _test_text_commands(self):
        """Testa comandos de texto."""
        for category, commands in self.TEST_COMMANDS.items():
            if category == 'binary':
                continue
            
            print(f"\n   Testando comandos '{category}':")
            for cmd in commands:
                try:
                    # Limpa buffer
                    self.serial_conn.reset_input_buffer()
                    
                    # Envia comando
                    print(f"      → Enviando: {cmd} ({self._safe_decode(cmd)})")
                    self.serial_conn.write(cmd)
                    self.serial_conn.flush()
                    
                    # Aguarda resposta
                    time.sleep(0.2)
                    
                    if self.serial_conn.in_waiting > 0:
                        response = self.serial_conn.read(self.serial_conn.in_waiting)
                        print(f"         ← Resposta: {len(response)} bytes")
                        print(f"            Hex: {response.hex()[:80]}")
                        print(f"            ASCII: {self._safe_decode(response[:50])}")
                    else:
                        print(f"         ← Sem resposta")
                    
                    time.sleep(0.3)
                except Exception as e:
                    print(f"         ❌ Erro: {e}")
    
    def _test_binary_commands(self):
        """Testa comandos binários."""
        for cmd in self.TEST_COMMANDS['binary']:
            try:
                # Limpa buffer
                self.serial_conn.reset_input_buffer()
                
                # Envia comando
                print(f"   → Enviando binário: {cmd.hex()}")
                self.serial_conn.write(cmd)
                self.serial_conn.flush()
                
                # Aguarda resposta
                time.sleep(0.3)
                
                if self.serial_conn.in_waiting > 0:
                    response = self.serial_conn.read(self.serial_conn.in_waiting)
                    print(f"      ← Resposta: {len(response)} bytes")
                    print(f"         Hex: {response.hex()[:100]}")
                    
                    # Tenta interpretar como estrutura comum
                    if len(response) >= 2:
                        header = response[:2]
                        print(f"         Header: {header.hex()}")
                else:
                    print(f"      ← Sem resposta")
                
                time.sleep(0.3)
            except Exception as e:
                print(f"      ❌ Erro: {e}")
    
    def _test_baudrates(self):
        """Testa diferentes baudrates."""
        baudrates = [115200, 230400, 460800, 921600, 256000, 128000]
        
        for baud in baudrates:
            print(f"\n   Testando baudrate: {baud}")
            try:
                # Reconecta com novo baudrate
                self.disconnect()
                self.baudrate = baud
                if not self.connect():
                    continue
                
                # Limpa buffer
                self.serial_conn.reset_input_buffer()
                
                # Aguarda dados
                time.sleep(0.5)
                
                if self.serial_conn.in_waiting > 0:
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    print(f"      ✅ Dados recebidos: {len(data)} bytes")
                    print(f"         Hex: {data.hex()[:60]}")
                else:
                    print(f"      ⚠️  Nenhum dado recebido")
                
            except Exception as e:
                print(f"      ❌ Erro: {e}")
    
    def _analyze_data_patterns(self, data_list):
        """Analisa padrões nos dados recebidos."""
        if not data_list:
            return
        
        print("\n   🔍 Análise de Padrões:")
        
        # Verifica headers comuns
        all_data = b''.join(data_list)
        if len(all_data) >= 2:
            headers = set()
            for i in range(min(100, len(all_data) - 1)):
                headers.add(all_data[i:i+2])
            
            print(f"      Headers encontrados: {len(headers)}")
            for header in list(headers)[:10]:
                print(f"         - {header.hex()}")
        
        # Verifica tamanhos de pacote
        sizes = [len(d) for d in data_list]
        if sizes:
            print(f"      Tamanhos de pacote: min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)/len(sizes):.1f}")
    
    def _safe_decode(self, data: bytes) -> str:
        """Decodifica bytes de forma segura."""
        try:
            decoded = data.decode('utf-8', errors='replace')
            # Remove caracteres não imprimíveis
            return ''.join(c if c.isprintable() else f'\\x{ord(c):02x}' for c in decoded)
        except:
            return f"<binary: {len(data)} bytes>"


def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Testa comunicação com C1 via Serial")
    parser.add_argument('--port', '-p', type=str, default='/dev/ttyUSB0',
                       help='Porta serial (padrão: /dev/ttyUSB0)')
    parser.add_argument('--baudrate', '-b', type=int, default=115200,
                       help='Baudrate (padrão: 115200)')
    
    args = parser.parse_args()
    
    # Detecta porta automaticamente se não especificada
    if args.port == '/dev/ttyUSB0':
        client = C1USBClient()
        detection = client.detect_c1()
        if detection['found'] and detection['type'] == 'serial':
            args.port = detection['port']
            print(f"🔍 Porta detectada automaticamente: {args.port}")
        else:
            print(f"⚠️  Usando porta padrão: {args.port}")
    
    tester = C1CommunicationTester(port=args.port, baudrate=args.baudrate)
    tester.test_communication()


if __name__ == "__main__":
    main()

