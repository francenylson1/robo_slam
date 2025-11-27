#!/usr/bin/env python3
"""
Script de Diagnóstico Detalhado do C1 Mapping Studio
Realiza testes completos de detecção, conexão e validação do sensor C1.
"""

import sys
from pathlib import Path
import json
from typing import Dict, List
from datetime import datetime

# Garante que o diretório raiz esteja no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.c1_mapping.capture.c1_usb_client import C1USBClient
from src.core.slamware_c1_uploader import SlamwareC1Uploader
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class C1Diagnostic:
    """Sistema de diagnóstico completo para o C1."""
    
    def __init__(self):
        self.results = {
            'timestamp': None,
            'api_tests': {},
            'serial_tests': {},
            'overall_status': 'unknown',
            'recommendations': []
        }
    
    def run_full_diagnostic(self) -> Dict:
        """Executa diagnóstico completo."""
        print("=" * 70)
        print("🔬 DIAGNÓSTICO COMPLETO - C1 MAPPING STUDIO")
        print("=" * 70)
        print()
        
        # Teste 1: Detecção via API
        print("📡 TESTE 1: Detecção via API REST")
        print("-" * 70)
        api_result = self._test_api_detection()
        self.results['api_tests'] = api_result
        print()
        
        # Teste 2: Detecção via Serial
        print("🔌 TESTE 2: Detecção via USB Serial")
        print("-" * 70)
        serial_result = self._test_serial_detection()
        self.results['serial_tests'] = serial_result
        print()
        
        # Teste 3: Validação de conexão
        print("✅ TESTE 3: Validação de Conexão")
        print("-" * 70)
        connection_result = self._test_connection()
        self.results['connection_tests'] = connection_result
        print()
        
        # Resumo final
        print("=" * 70)
        print("📊 RESUMO DO DIAGNÓSTICO")
        print("=" * 70)
        self._print_summary()
        print()
        
        return self.results
    
    def _test_api_detection(self) -> Dict:
        """Testa detecção via API REST."""
        result = {
            'tested': True,
            'success': False,
            'details': {}
        }
        
        # Testa IP padrão
        default_ip = "192.168.1.101"
        print(f"   Testando IP padrão: {default_ip}:1445")
        
        client = C1USBClient(api_ip=default_ip)
        api_detection = client._detect_via_api()
        
        if api_detection:
            result['success'] = True
            result['details'] = api_detection
            print(f"   ✅ C1 detectado via API em {default_ip}:1445")
            if api_detection.get('validation_details'):
                val = api_detection['validation_details']
                print(f"      - Conexão: {'✅' if val.get('connection_ok') else '❌'}")
                print(f"      - Info do dispositivo: {'✅' if val.get('device_info_ok') else '❌'}")
                print(f"      - Endpoints API: {'✅' if val.get('api_endpoints_ok') else '❌'}")
                if val.get('working_endpoints'):
                    print(f"      - Endpoints funcionando: {', '.join(val['working_endpoints'])}")
        else:
            print(f"   ❌ C1 não detectado via API em {default_ip}:1445")
            result['details']['error'] = "Não foi possível conectar"
        
        # Testa outros IPs comuns
        common_ips = ["192.168.1.100", "192.168.0.101", "10.0.0.101"]
        result['details']['other_ips_tested'] = []
        
        for ip in common_ips:
            print(f"   Testando IP alternativo: {ip}:1445")
            test_client = C1USBClient(api_ip=ip)
            test_detection = test_client._detect_via_api()
            if test_detection:
                result['details']['other_ips_tested'].append({
                    'ip': ip,
                    'found': True
                })
                print(f"      ✅ C1 encontrado em {ip}:1445")
            else:
                result['details']['other_ips_tested'].append({
                    'ip': ip,
                    'found': False
                })
        
        return result
    
    def _test_serial_detection(self) -> Dict:
        """Testa detecção via USB Serial."""
        result = {
            'tested': True,
            'success': False,
            'devices_found': [],
            'validated_devices': []
        }
        
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            
            print(f"   Portas USB Serial encontradas: {len(ports)}")
            
            if not ports:
                print("   ⚠️  Nenhuma porta USB Serial encontrada")
                return result
            
            client = C1USBClient()
            serial_detection = client._detect_via_serial()
            
            if serial_detection:
                result['success'] = True
                result['devices_found'].append(serial_detection)
                
                print(f"   ✅ Dispositivo detectado:")
                print(f"      - Porta: {serial_detection['port']}")
                print(f"      - Descrição: {serial_detection['description']}")
                print(f"      - VID: 0x{serial_detection['vid']:04X}")
                print(f"      - PID: 0x{serial_detection['pid']:04X}")
                
                if serial_detection.get('validated'):
                    result['validated_devices'].append(serial_detection)
                    print(f"      - ✅ Validado como C1")
                    if serial_detection.get('validation_details'):
                        val = serial_detection['validation_details']
                        print(f"        - Porta acessível: {'✅' if val.get('port_accessible') else '❌'}")
                        print(f"        - Baudrate testado: {val.get('baudrate_tested', 'N/A')}")
                        print(f"        - Resposta recebida: {'✅' if val.get('response_received') else '❌'}")
                        print(f"        - Assinatura C1: {'✅' if val.get('c1_signature_found') else '❌'}")
                else:
                    print(f"      - ⚠️  Dispositivo detectado mas NÃO validado como C1")
                    print(f"        (Pode ser outro dispositivo USB Serial)")
            else:
                print("   ❌ Nenhum dispositivo C1 detectado via Serial")
            
            # Lista todas as portas encontradas
            print(f"\n   📋 Todas as portas USB Serial:")
            for i, port in enumerate(ports, 1):
                print(f"      {i}. {port.device}")
                print(f"         - {port.description or 'N/A'}")
                if port.vid is not None and port.pid is not None:
                    print(f"         - VID: 0x{port.vid:04X} | PID: 0x{port.pid:04X}")
                if port.serial_number:
                    print(f"         - Serial: {port.serial_number}")
        
        except ImportError:
            print("   ❌ Biblioteca 'pyserial' não disponível")
            result['error'] = "pyserial not available"
        except Exception as e:
            print(f"   ❌ Erro ao testar Serial: {e}")
            result['error'] = str(e)
        
        return result
    
    def _test_connection(self) -> Dict:
        """Testa conexão real com o C1."""
        result = {
            'tested': True,
            'api_connection': False,
            'serial_connection': False,
            'details': {}
        }
        
        client = C1USBClient()
        detection = client.detect_c1()
        
        if not detection['found']:
            print("   ❌ Nenhum C1 detectado - não é possível testar conexão")
            return result
        
        print(f"   C1 detectado via: {detection['type']}")
        
        # Tenta conectar
        if client.connect(detection['type']):
            print(f"   ✅ Conexão estabelecida via {detection['type']}")
            
            if detection['type'] == 'api':
                result['api_connection'] = True
                api_client = client.get_api_client()
                if api_client:
                    # Testa funcionalidades da API
                    maps = api_client.list_maps()
                    result['details']['maps_available'] = len(maps)
                    print(f"      - Mapas disponíveis: {len(maps)}")
                    if maps:
                        print(f"      - Lista: {', '.join(maps[:5])}")
            
            elif detection['type'] == 'serial':
                result['serial_connection'] = True
                print(f"      - Porta: {detection['port']}")
            
            client.disconnect()
        else:
            print(f"   ❌ Falha ao estabelecer conexão")
            result['details']['error'] = "Connection failed"
        
        return result
    
    def _print_summary(self):
        """Imprime resumo do diagnóstico."""
        api_ok = self.results['api_tests'].get('success', False)
        serial_ok = self.results['serial_tests'].get('success', False)
        connection_ok = (
            self.results.get('connection_tests', {}).get('api_connection', False) or
            self.results.get('connection_tests', {}).get('serial_connection', False)
        )
        
        print(f"📡 API REST:        {'✅ OK' if api_ok else '❌ Não detectado'}")
        print(f"🔌 USB Serial:      {'✅ OK' if serial_ok else '❌ Não detectado'}")
        print(f"🔗 Conexão:         {'✅ OK' if connection_ok else '❌ Falhou'}")
        print()
        
        # Status geral
        if connection_ok:
            self.results['overall_status'] = 'ready'
            print("✅ STATUS: Sistema pronto para uso!")
        elif api_ok or serial_ok:
            self.results['overall_status'] = 'partial'
            print("⚠️  STATUS: C1 detectado mas conexão não estabelecida")
        else:
            self.results['overall_status'] = 'not_found'
            print("❌ STATUS: C1 não detectado")
        
        # Recomendações
        print("\n💡 RECOMENDAÇÕES:")
        if not api_ok and not serial_ok:
            self.results['recommendations'].append("Verifique se o C1 está conectado e ligado")
            self.results['recommendations'].append("Verifique se os drivers USB estão instalados")
            print("   - Verifique se o C1 está conectado e ligado")
            print("   - Verifique se os drivers USB estão instalados")
        
        if not api_ok:
            self.results['recommendations'].append("Verifique se o C1 está na mesma rede")
            self.results['recommendations'].append("Verifique o endereço IP do C1")
            print("   - Verifique se o C1 está na mesma rede")
            print("   - Verifique o endereço IP do C1 (padrão: 192.168.1.101)")
        
        if serial_ok and not connection_ok:
            self.results['recommendations'].append("Dispositivo detectado mas não validado - pode não ser o C1")
            print("   - Dispositivo detectado mas não validado - pode não ser o C1")
        
        if connection_ok:
            print("   - Sistema pronto! Você pode usar os comandos do main_c1_mapping.py")


def main():
    """Função principal."""
    diagnostic = C1Diagnostic()
    results = diagnostic.run_full_diagnostic()
    
    # Salva resultados em arquivo JSON
    output_file = Path("data/diagnostic_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    results['timestamp'] = datetime.now().isoformat()
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Resultados salvos em: {output_file}")


if __name__ == "__main__":
    main()

