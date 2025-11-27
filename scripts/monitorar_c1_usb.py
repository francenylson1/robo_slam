#!/usr/bin/env python3
"""
Monitor de Dados USB do C1
Monitora continuamente a porta USB para capturar dados que o C1 envia.
"""

import sys
from pathlib import Path
import time
import struct
from datetime import datetime

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

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class C1USBMONITOR:
    """Monitor de dados USB do C1."""
    
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.running = False
        self.data_log = []
    
    def connect(self) -> bool:
        """Conecta à porta serial."""
        try:
            self.serial_conn = serial.Serial(
                self.port,
                baudrate=self.baudrate,
                timeout=0.1,  # Timeout curto para leitura não-bloqueante
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
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("\n🔌 Desconectado")
    
    def monitor_continuous(self, duration: float = 30.0):
        """
        Monitora dados continuamente.
        
        Args:
            duration: Duração do monitoramento em segundos (0 = infinito)
        """
        if not self.connect():
            return
        
        print("\n" + "=" * 70)
        print("📡 MONITORAMENTO CONTÍNUO DO C1")
        print("=" * 70)
        print(f"Porta: {self.port}")
        print(f"Baudrate: {self.baudrate}")
        print(f"Duração: {duration}s (0 = infinito, Ctrl+C para parar)")
        print("=" * 70)
        print()
        print("⏳ Aguardando dados do C1...")
        print("   (Pressione Ctrl+C para parar)\n")
        
        self.running = True
        start_time = time.time()
        last_data_time = start_time
        total_bytes = 0
        packet_count = 0
        last_packet_time = start_time
        
        try:
            while self.running:
                # Verifica timeout
                if duration > 0 and (time.time() - start_time) > duration:
                    break
                
                # Lê dados disponíveis
                if self.serial_conn.in_waiting > 0:
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    timestamp = time.time()
                    
                    if data:
                        total_bytes += len(data)
                        packet_count += 1
                        last_data_time = timestamp
                        
                        # Calcula intervalo entre pacotes
                        interval = timestamp - last_packet_time
                        last_packet_time = timestamp
                        
                        # Exibe dados recebidos
                        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] 📨 Pacote #{packet_count}")
                        print(f"   Tamanho: {len(data)} bytes")
                        print(f"   Intervalo: {interval*1000:.1f}ms")
                        print(f"   Hex (primeiros 64 bytes): {data[:64].hex()}")
                        
                        # Tenta identificar padrões
                        self._analyze_packet(data, packet_count)
                        
                        # Salva no log
                        self.data_log.append({
                            'timestamp': timestamp,
                            'data': data,
                            'size': len(data),
                            'interval': interval
                        })
                        
                        print()
                
                # Se não há dados, aguarda um pouco
                else:
                    # Verifica se há muito tempo sem dados
                    if time.time() - last_data_time > 5.0 and total_bytes > 0:
                        print(f"⏸️  Sem dados há {(time.time() - last_data_time):.1f}s...")
                        last_data_time = time.time()
                    
                    time.sleep(0.01)  # Pequeno delay para não consumir CPU
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrompido pelo usuário")
        
        finally:
            # Estatísticas finais
            elapsed = time.time() - start_time
            print("\n" + "=" * 70)
            print("📊 ESTATÍSTICAS")
            print("=" * 70)
            print(f"Tempo total: {elapsed:.1f}s")
            print(f"Pacotes recebidos: {packet_count}")
            print(f"Total de bytes: {total_bytes}")
            if packet_count > 0:
                print(f"Tamanho médio: {total_bytes/packet_count:.1f} bytes/pacote")
                print(f"Taxa: {packet_count/elapsed:.2f} pacotes/s")
                print(f"Throughput: {total_bytes/elapsed:.1f} bytes/s")
            
            if self.data_log:
                print(f"\n💾 Dados salvos em memória: {len(self.data_log)} pacotes")
                self._save_log()
            
            self.disconnect()
    
    def _analyze_packet(self, data: bytes, packet_num: int):
        """Analisa um pacote de dados."""
        # Verifica headers comuns
        if len(data) >= 2:
            header = data[:2]
            header_hex = header.hex()
            
            # Headers conhecidos
            known_headers = {
                'aa55': 'RPLIDAR/SLAMTEC comum',
                'a55a': 'Header alternativo',
                '5555': 'Header duplo',
            }
            
            if header_hex in known_headers:
                print(f"   🔍 Header identificado: {header_hex} ({known_headers[header_hex]})")
            
            # Verifica se parece ser ASCII
            try:
                ascii_part = data[:min(50, len(data))].decode('ascii', errors='ignore')
                if ascii_part.isprintable() and len(ascii_part) > 5:
                    print(f"   📝 ASCII: {ascii_part[:50]}")
            except:
                pass
            
            # Verifica tamanhos comuns de pacote LIDAR
            common_sizes = [360, 720, 1080, 1440, 1800]  # Tamanhos comuns para scans LIDAR
            if len(data) in common_sizes:
                print(f"   ⚠️  Tamanho comum de scan LIDAR: {len(data)} bytes")
            
            # Verifica padrões repetitivos (pode indicar dados de distância)
            if len(data) >= 4:
                # Verifica se há sequências repetitivas
                first_4 = data[:4]
                count = data.count(first_4)
                if count > len(data) / 8:  # Se aparece muitas vezes
                    print(f"   🔄 Padrão repetitivo detectado: {first_4.hex()}")
    
    def _save_log(self):
        """Salva log de dados em arquivo."""
        try:
            log_file = Path("data/c1_usb_monitor_log.json")
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            import json
            log_data = {
                'timestamp': datetime.now().isoformat(),
                'port': self.port,
                'baudrate': self.baudrate,
                'packets': [
                    {
                        'timestamp': p['timestamp'],
                        'size': p['size'],
                        'interval': p['interval'],
                        'data_hex': p['data'].hex()
                    }
                    for p in self.data_log
                ]
            }
            
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            print(f"   📄 Log salvo em: {log_file}")
        except Exception as e:
            print(f"   ⚠️  Erro ao salvar log: {e}")
    
    def test_different_baudrates(self):
        """Testa diferentes baudrates para encontrar o correto."""
        baudrates = [115200, 230400, 460800, 921600, 256000, 128000, 57600, 38400]
        
        print("\n" + "=" * 70)
        print("🔍 TESTE DE BAUDRATES")
        print("=" * 70)
        print()
        
        for baud in baudrates:
            print(f"Testando baudrate: {baud}")
            self.baudrate = baud
            
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
            
            if not self.connect():
                continue
            
            # Limpa buffer
            self.serial_conn.reset_input_buffer()
            
            # Monitora por 3 segundos
            start = time.time()
            data_received = []
            
            while time.time() - start < 3.0:
                if self.serial_conn.in_waiting > 0:
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    data_received.append(data)
                time.sleep(0.1)
            
            if data_received:
                total = sum(len(d) for d in data_received)
                print(f"   ✅ Dados recebidos: {total} bytes em {len(data_received)} pacotes")
                print(f"      Primeiros bytes: {data_received[0][:32].hex()}")
            else:
                print(f"   ❌ Nenhum dado recebido")
            
            print()
        
        self.disconnect()


def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitora dados USB do C1")
    parser.add_argument('--port', '-p', type=str, default='/dev/ttyUSB0',
                       help='Porta serial (padrão: /dev/ttyUSB0)')
    parser.add_argument('--baudrate', '-b', type=int, default=115200,
                       help='Baudrate (padrão: 115200)')
    parser.add_argument('--duration', '-d', type=float, default=30.0,
                       help='Duração do monitoramento em segundos (0 = infinito)')
    parser.add_argument('--test-baudrates', action='store_true',
                       help='Testa diferentes baudrates primeiro')
    
    args = parser.parse_args()
    
    monitor = C1USBMONITOR(port=args.port, baudrate=args.baudrate)
    
    if args.test_baudrates:
        monitor.test_different_baudrates()
    
    monitor.monitor_continuous(duration=args.duration)


if __name__ == "__main__":
    main()

