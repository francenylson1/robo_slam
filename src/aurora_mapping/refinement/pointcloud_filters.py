"""Rotinas de limpeza, filtros e segmentação da nuvem 3D."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Sequence, Tuple, TYPE_CHECKING

import numpy as np

os.environ.setdefault("OPEN3D_CPU_ONLY", "true")

try:
    import open3d as o3d
except ImportError as exc:  # pragma: no cover - dependency check
    raise RuntimeError(
        "Open3D não está instalado. Execute `pip install open3d` no ambiente de desenvolvimento."
    ) from exc

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover - optional dependency
    plt = None

if TYPE_CHECKING:
    from aurora_mapping.pipelines.workflows import PipelineContext


def _convert_stcm_to_ply_with_sdk(stcm_path: Path, output_ply_path: Path, aurora_config: dict) -> bool:
    """
    Converte arquivo .stcm do Aurora para .ply usando o SDK oficial do Aurora.
    
    Requer conexão com dispositivo Aurora. O processo:
    1. Conecta ao dispositivo Aurora
    2. Faz upload do arquivo .stcm para o dispositivo
    3. Extrai os map points (nuvem de pontos 3D) usando get_map_data
    4. Converte para Open3D PointCloud e salva como .ply
    
    Args:
        stcm_path: Caminho para arquivo .stcm
        output_ply_path: Caminho onde salvar o arquivo .ply
        aurora_config: Configuração do Aurora (ip, port, auto_discover, etc.)
        
    Returns:
        True se conversão bem-sucedida, False caso contrário
    """
    try:
        import sys
        import time
        
        # Adiciona o SDK do Aurora ao path
        workspace_root = Path(__file__).parent.parent.parent.parent
        sdk_path = workspace_root / "py_aurora_remote-main" / "python_bindings"
        
        if not sdk_path.exists():
            print(f"[refinement] ⚠️  SDK do Aurora não encontrado em: {sdk_path}")
            return False
        
        if str(sdk_path) not in sys.path:
            sys.path.insert(0, str(sdk_path))
        
        # Importa o SDK do Aurora
        try:
            from slamtec_aurora_sdk import AuroraSDK
            from slamtec_aurora_sdk.exceptions import AuroraSDKError, ConnectionError
        except ImportError as e:
            print(f"[refinement] ❌ Não foi possível importar o SDK do Aurora: {e}")
            print(f"[refinement]    Verifique se o SDK está instalado corretamente em: {sdk_path}")
            return False
        
        print(f"[refinement] 🔌 Conectando ao Aurora para converter .stcm...")
        
        # Inicializa o SDK
        sdk = AuroraSDK()
        
        try:
            # Conecta ao dispositivo
            if aurora_config.get("auto_discover", True):
                print(f"[refinement]    Descobrindo dispositivos Aurora...")
                devices = sdk.discover_devices(timeout=5.0)
                if not devices:
                    print(f"[refinement] ❌ Nenhum dispositivo Aurora encontrado")
                    return False
                print(f"[refinement]    Dispositivo encontrado: {devices[0].get('device_name', 'Unknown')}")
                sdk.connect(device_info=devices[0])
            else:
                ip = aurora_config.get("ip", "192.168.1.212")
                port = aurora_config.get("port", 1445)
                connection_string = f"{ip}:{port}"
                print(f"[refinement]    Conectando a {connection_string}...")
                sdk.connect(connection_string=connection_string)
            
            print(f"[refinement] ✅ Conectado ao Aurora")
            
            # Verifica se o arquivo .stcm existe localmente
            stcm_exists_locally = stcm_path.exists() and stcm_path.is_file()
            map_manager = sdk.map_manager
            backup_map_path = None
            
            if stcm_exists_locally:
                # Arquivo está no computador: PRIMEIRO faz backup do mapa atual
                print(f"[refinement]    Arquivo .stcm encontrado localmente: {stcm_path.name}")
                print(f"[refinement]    ⚠️  IMPORTANTE: O Aurora mantém apenas o mapa atual")
                print(f"[refinement]    Fazendo backup do mapa atual antes do upload...")
                
                # Cria caminho para backup do mapa atual
                backup_dir = stcm_path.parent / "backup_aurora_maps"
                backup_dir.mkdir(parents=True, exist_ok=True)
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_map_path = backup_dir / f"backup_mapa_atual_{timestamp}.stcm"
                
                # Faz download do mapa atual (backup)
                try:
                    if map_manager.start_download_session(str(backup_map_path)):
                        print(f"[refinement]    Fazendo backup do mapa atual...")
                        while map_manager.is_session_active():
                            try:
                                status = map_manager.query_session_status()
                                print(f"\r[refinement]    Backup: {status.progress:.1f}%", end="", flush=True)
                                time.sleep(0.5)
                            except:
                                time.sleep(0.5)
                        
                        backup_status = map_manager.query_session_status()
                        if backup_status.is_finished():
                            print(f"\n[refinement] ✅ Backup do mapa atual concluído: {backup_map_path.name}")
                        else:
                            print(f"\n[refinement] ⚠️  Backup falhou, mas continuando...")
                    else:
                        print(f"[refinement] ⚠️  Não foi possível iniciar backup, mas continuando...")
                except Exception as e:
                    print(f"[refinement] ⚠️  Erro ao fazer backup: {e}, mas continuando...")
                
                # Agora faz upload do arquivo .stcm
                print(f"[refinement]    Fazendo upload do arquivo .stcm para o dispositivo...")
                
                if not map_manager.start_upload_session(str(stcm_path)):
                    print(f"[refinement] ❌ Falha ao iniciar sessão de upload")
                    return False
                
                # Monitora o progresso do upload
                while map_manager.is_session_active():
                    try:
                        status = map_manager.query_session_status()
                        print(f"\r[refinement]    Upload: {status.progress:.1f}%", end="", flush=True)
                        time.sleep(0.5)
                    except Exception as e:
                        print(f"\n[refinement] ⚠️  Erro ao consultar status: {e}")
                        break
                
                # Verifica resultado do upload
                final_status = map_manager.query_session_status()
                if not final_status.is_finished():
                    print(f"\n[refinement] ❌ Upload falhou: {final_status.get_status_string()}")
                    return False
                
                print(f"\n[refinement] ✅ Upload concluído")
            else:
                # Arquivo não existe localmente: assume que o mapa já está no dispositivo
                print(f"[refinement]    Arquivo .stcm não encontrado localmente")
                print(f"[refinement]    Assumindo que o mapa já está no dispositivo Aurora")
                print(f"[refinement]    Obtendo dados do mapa ativo no dispositivo...")
            
            # Habilita sincronização de dados do mapa
            print(f"[refinement]    Sincronizando dados do mapa...")
            sdk.controller.enable_map_data_syncing(True)
            sdk.controller.resync_map_data()
            
            # Aguarda sincronização (máximo 30 segundos após upload)
            max_wait = 30.0 if stcm_exists_locally else 10.0
            start_time = time.time()
            print(f"[refinement]    Aguardando processamento do mapa (até {max_wait:.0f}s)...")
            synced_keyframes = 0
            synced_points = 0
            while time.time() - start_time < max_wait:
                try:
                    global_info = sdk.data_provider.get_global_mapping_info()
                    total_points = global_info.get('total_mp_count_fetched', 0)
                    total_kf = global_info.get('total_kf_count_fetched', 0)
                    if total_points > 0 or total_kf > 0:
                        synced_keyframes = total_kf
                        synced_points = total_points
                        print(f"[refinement]    Mapa sincronizado: {total_points} pontos, {total_kf} keyframes")
                        break
                    elapsed = time.time() - start_time
                    if int(elapsed) % 5 == 0 and elapsed > 0:
                        print(f"[refinement]    Aguardando... ({elapsed:.0f}s/{max_wait:.0f}s)")
                    time.sleep(1.0)
                except Exception as e:
                    time.sleep(1.0)
            
            # Extrai os map points (nuvem de pontos 3D)
            print(f"[refinement]    Extraindo nuvem de pontos...")
            # IMPORTANTE: Busca SEM especificar map_ids para pegar o mapa ativo
            # Quando especificamos map_ids, pode não retornar os dados corretamente
            map_data = sdk.get_map_data(fetch_mp=True, fetch_kf=True, fetch_mapinfo=False)
            
            # Se ainda não encontrou, tenta novamente após pequeno delay
            if not map_data.get('map_points') and not map_data.get('keyframes'):
                print(f"[refinement]    Primeira tentativa não retornou dados, aguardando mais 2s...")
                time.sleep(2.0)
                map_data = sdk.get_map_data(fetch_mp=True, fetch_kf=True, fetch_mapinfo=False)
            
            map_points = map_data.get('map_points', [])
            keyframes = map_data.get('keyframes', [])
            
            # Se não há map points, tenta usar posições dos keyframes como fallback
            if not map_points and keyframes:
                print(f"[refinement] ⚠️  Nenhum map point encontrado, usando posições dos keyframes como fallback")
                print(f"[refinement]    {len(keyframes)} keyframes disponíveis")
                # Usa as posições dos keyframes como pontos (aproximação)
                map_points = [{'position': kf['position']} for kf in keyframes]
            
            # Se encontrou poucos map points (< 500), tenta usar o backup que pode ter mais
            # O backup contém o mapa que estava no dispositivo, que pode ter map points válidos
            min_points_threshold = 500  # Se tiver menos que isso, tenta backup
            use_backup = (len(map_points) < min_points_threshold) and backup_map_path and backup_map_path.exists()
            
            if use_backup:
                print(f"[refinement] ⚠️  Apenas {len(map_points)} map points extraídos do mapa enviado")
                print(f"[refinement]    Tentando extrair do backup do mapa anterior: {backup_map_path.name}")
                print(f"[refinement]    (O backup foi baixado ANTES do upload e pode conter mais map points)")
                
                # Faz upload do backup temporariamente para extrair os map points
                try:
                    # Salva o caminho do arquivo original
                    original_stcm = stcm_path
                    
                    # Tenta fazer upload do backup e extrair
                    print(f"[refinement]    Fazendo upload temporário do backup para extrair map points...")
                    if map_manager.start_upload_session(str(backup_map_path)):
                        # Aguarda upload
                        while map_manager.is_session_active():
                            try:
                                status = map_manager.query_session_status()
                                print(f"\r[refinement]    Upload backup: {status.progress:.1f}%", end="", flush=True)
                                time.sleep(0.5)
                            except:
                                time.sleep(0.5)
                        print()
                        
                        # Sincroniza e aguarda mais tempo
                        sdk.controller.resync_map_data()
                        print(f"[refinement]    Aguardando sincronização do backup (até 15s)...")
                        max_wait_backup = 15.0
                        start_time = time.time()
                        while time.time() - start_time < max_wait_backup:
                            try:
                                global_info = sdk.data_provider.get_global_mapping_info()
                                total_points = global_info.get('total_mp_count_fetched', 0)
                                if total_points > 0:
                                    print(f"[refinement]    Backup sincronizado: {total_points} map points detectados")
                                    break
                                time.sleep(1.0)
                            except:
                                time.sleep(1.0)
                        
                        # Primeiro, obtém informações dos mapas disponíveis
                        map_info_data = sdk.get_map_data(fetch_mp=False, fetch_kf=False, fetch_mapinfo=True)
                        map_info = map_info_data.get('map_info', {})
                        
                        if map_info:
                            print(f"[refinement]    Mapas disponíveis: {list(map_info.keys())}")
                            total_points_in_maps = sum(info.get('point_count', 0) for info in map_info.values())
                            print(f"[refinement]    Total de pontos nos mapas: {total_points_in_maps}")
                        
                        # Tenta extrair map points do backup (múltiplas tentativas)
                        # Usa map_ids=[] para buscar de TODOS os mapas
                        backup_points = []
                        backup_keyframes = []
                        for attempt in range(3):
                            # Busca de todos os mapas usando map_ids=[]
                            backup_map_data = sdk.get_map_data(map_ids=[], fetch_mp=True, fetch_kf=True, fetch_mapinfo=False)
                            backup_points = backup_map_data.get('map_points', [])
                            backup_keyframes = backup_map_data.get('keyframes', [])
                            
                            if backup_points and len(backup_points) > 100:
                                break
                            
                            if attempt < 2:
                                print(f"[refinement]    Tentativa {attempt+1}: {len(backup_points)} pontos, aguardando mais 2s...")
                                time.sleep(2.0)
                        
                        if backup_points and len(backup_points) > len(map_points):
                            print(f"[refinement] ✅ Encontrados {len(backup_points)} map points no backup!")
                            print(f"[refinement]    Usando map points do backup (melhor que os {len(map_points)} do arquivo original)")
                            map_points = backup_points
                        elif backup_keyframes and not map_points:
                            print(f"[refinement] ⚠️  Usando {len(backup_keyframes)} keyframes do backup como fallback")
                            map_points = [{'position': kf['position']} for kf in backup_keyframes]
                        
                        # Restaura o arquivo original fazendo upload novamente
                        if map_points:
                            print(f"[refinement]    Restaurando arquivo original no dispositivo...")
                            if map_manager.start_upload_session(str(original_stcm)):
                                while map_manager.is_session_active():
                                    try:
                                        status = map_manager.query_session_status()
                                        print(f"\r[refinement]    Restaurando: {status.progress:.1f}%", end="", flush=True)
                                        time.sleep(0.5)
                                    except:
                                        time.sleep(0.5)
                                print()
                    else:
                        print(f"[refinement] ⚠️  Não foi possível fazer upload do backup")
                except Exception as e:
                    print(f"[refinement] ⚠️  Erro ao processar backup: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Se ainda não encontrou, tenta extrair diretamente do arquivo .stcm original
            if not map_points:
                print(f"[refinement] ⚠️  Não foi possível extrair map points do dispositivo ou backup")
                print(f"[refinement]    Tentando extrair diretamente do arquivo .stcm original...")
                print(f"[refinement]    Keyframes sincronizados: {synced_keyframes}, Map points: {synced_points}")
                print(f"[refinement]    Mas get_map_data() não retornou dados - problema conhecido do SDK")
                return False
            
            print(f"[refinement]    {len(map_points):,} pontos encontrados")
            
            # Converte map points para array NumPy
            points_array = np.array([[mp['position'][0], mp['position'][1], mp['position'][2]] 
                                     for mp in map_points])
            
            # Remove pontos inválidos (NaN, Inf, zeros)
            valid_mask = np.all(np.isfinite(points_array), axis=1)
            valid_mask &= np.any(points_array != 0, axis=1)
            points_array = points_array[valid_mask]
            
            if len(points_array) == 0:
                print(f"[refinement] ❌ Nenhum ponto válido após filtragem")
                return False
            
            print(f"[refinement]    {len(points_array):,} pontos válidos")
            
            # Cria nuvem Open3D
            cloud = o3d.geometry.PointCloud()
            cloud.points = o3d.utility.Vector3dVector(points_array)
            
            # Salva como PLY
            o3d.io.write_point_cloud(str(output_ply_path), cloud)
            print(f"[refinement] ✅ Arquivo .ply salvo: {output_ply_path}")
            
            return True
            
        finally:
            # Desconecta do dispositivo
            try:
                sdk.controller.enable_map_data_syncing(False)
                sdk.disconnect()
                sdk.release()
            except:
                pass
                
    except ConnectionError as e:
        print(f"[refinement] ❌ Erro de conexão com Aurora: {e}")
        return False
    except AuroraSDKError as e:
        print(f"[refinement] ❌ Erro do SDK do Aurora: {e}")
        return False
    except Exception as e:
        print(f"[refinement] ❌ Erro ao converter .stcm para .ply com SDK: {e}")
        import traceback
        traceback.print_exc()
        return False


def _convert_stcm_to_ply_heuristic(stcm_path: Path, output_ply_path: Path) -> bool:
    """
    Converte arquivo .stcm do Aurora para .ply usando parser heurístico (fallback).
    
    Args:
        stcm_path: Caminho para arquivo .stcm
        output_ply_path: Caminho onde salvar o arquivo .ply
        
    Returns:
        True se conversão bem-sucedida, False caso contrário
    """
    try:
        # Importa STCMProcessor
        import sys
        
        # Adiciona src ao path se necessário
        src_path = Path(__file__).parent.parent.parent
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        try:
            from core.stcm_processor import STCMProcessor
        except ImportError:
            print(f"[refinement] ⚠️  STCMProcessor não encontrado. Tentando importar de src.core...")
            try:
                from src.core.stcm_processor import STCMProcessor
            except ImportError:
                print(f"[refinement] ❌ Não foi possível importar STCMProcessor")
                return False
        
        print(f"[refinement]    Tentando conversão com parser heurístico...")
        
        # Carrega arquivo STCM
        processor = STCMProcessor(str(stcm_path))
        if not processor.load():
            print(f"[refinement] ❌ Erro ao carregar arquivo .stcm: {stcm_path}")
            return False
        
        # Extrai nuvem de pontos
        points = processor.extract_point_cloud()
        if points is None or len(points) == 0:
            return False
        
        print(f"[refinement] ✅ Nuvem de pontos extraída: {len(points):,} pontos")
        
        # Cria nuvem Open3D
        cloud = o3d.geometry.PointCloud()
        cloud.points = o3d.utility.Vector3dVector(points)
        
        # Salva como PLY
        o3d.io.write_point_cloud(str(output_ply_path), cloud)
        print(f"[refinement] ✅ Arquivo .ply salvo: {output_ply_path}")
        
        return True
        
    except Exception as e:
        return False


def _convert_stcm_to_ply(stcm_path: Path, output_ply_path: Path, aurora_config: dict = None) -> bool:
    """
    Converte arquivo .stcm do Aurora para .ply.
    
    Tenta primeiro usar o SDK oficial do Aurora (se configurado e disponível),
    depois tenta o parser heurístico como fallback.
    
    Args:
        stcm_path: Caminho para arquivo .stcm
        output_ply_path: Caminho onde salvar o arquivo .ply
        aurora_config: Configuração do Aurora (opcional)
        
    Returns:
        True se conversão bem-sucedida, False caso contrário
    """
    print(f"[refinement] Convertendo .stcm para .ply: {stcm_path.name}")
    
    # Tenta primeiro com o SDK do Aurora (se configurado)
    if aurora_config and aurora_config.get("enabled", False):
        if _convert_stcm_to_ply_with_sdk(stcm_path, output_ply_path, aurora_config):
            return True
        print(f"[refinement] ⚠️  Conversão com SDK falhou, tentando parser heurístico...")
    
    # Fallback: parser heurístico
    if _convert_stcm_to_ply_heuristic(stcm_path, output_ply_path):
        return True
    
    # Se ambos falharam
    print(f"[refinement] ❌ Não foi possível converter arquivo .stcm para .ply")
    print(f"[refinement]    O formato .stcm do Aurora é proprietário.")
    print(f"[refinement]")
    print(f"[refinement]    ⚠️  IMPORTANTE: O Aurora SOMENTE exporta em formato .stcm (não há opção PLY/PCD)")
    print(f"[refinement]")
    print(f"[refinement]    📋 SOLUÇÕES POSSÍVEIS:")
    print(f"[refinement]       1. Configure o SDK do Aurora em config/mapping.json (seção 'aurora')")
    print(f"[refinement]       2. Conecte um dispositivo Aurora e habilite 'aurora.enabled: true'")
    print(f"[refinement]       3. Melhore o STCMProcessor para fazer engenharia reversa do formato")
    print(f"[refinement]       4. Contate o suporte Slamtec para documentação do formato .stcm")
    return False


def run_refinement_step(context: "PipelineContext") -> None:
    """Processa a nuvem 3D para remover ruídos e normalizar o mapa."""

    refinement_config = (context.metadata or {}).get("refinement", {})
    capture_config = (context.metadata or {}).get("capture", {})
    aurora_config = (context.metadata or {}).get("aurora", {})

    capture_dir = Path(context.output_dir) / capture_config.get("output_subdir", "capture")
    output_dir = Path(context.output_dir) / refinement_config.get("output_subdir", "refinement")
    output_dir.mkdir(parents=True, exist_ok=True)

    extensions = _normalize_exts(refinement_config.get("input_extensions", [".ply", ".pcd"]))
    
    # Verifica se há arquivo .stcm que precisa ser convertido
    stcm_files = list(capture_dir.glob("*.stcm"))
    source_cloud = None
    
    if stcm_files:
        # Procura por arquivo .ply correspondente
        stcm_file = max(stcm_files, key=lambda p: p.stat().st_mtime)
        ply_candidate = capture_dir / f"{stcm_file.stem}.ply"
        
        # Se não há .ply válido, converte .stcm para .ply
        if not ply_candidate.exists() or ply_candidate.stat().st_size < 500:
            print(f"[refinement] Arquivo .stcm detectado: {stcm_file.name}")
            print(f"[refinement] Convertendo .stcm para .ply...")
            
            if _convert_stcm_to_ply(stcm_file, ply_candidate, aurora_config):
                print(f"[refinement] ✅ Conversão concluída: {ply_candidate.name}")
                source_cloud = ply_candidate
            else:
                # Conversão falhou - precisa exportar do Aurora Remote
                raise ValueError(
                    f"❌ Não foi possível converter arquivo .stcm para .ply: {stcm_file.name}\n\n"
                    f"   O Aurora SOMENTE exporta mapas em formato .stcm (proprietário).\n"
                    f"   Tanto o SDK quanto o parser heurístico não conseguiram extrair os pontos.\n\n"
                    f"   ⚠️  IMPORTANTE: O Aurora NÃO tem opção de exportar em PLY ou PCD.\n\n"
                    f"   📋 SOLUÇÕES POSSÍVEIS:\n"
                    f"   1. Configure o SDK do Aurora em config/mapping.json (seção 'aurora')\n"
                    f"   2. Conecte um dispositivo Aurora e habilite 'aurora.enabled: true'\n"
                    f"   3. Melhore o STCMProcessor para fazer engenharia reversa do formato\n"
                    f"   4. Contate o suporte Slamtec para documentação do formato .stcm\n\n"
                    f"   O parser atual é heurístico e pode não funcionar para todos os arquivos .stcm."
                )
        else:
            # .ply já existe e é válido, usa ele
            source_cloud = ply_candidate
    
    # Se ainda não encontrou, procura .ply/.pcd normalmente
    if source_cloud is None:
        try:
            source_cloud = _locate_latest_cloud(capture_dir, extensions)
        except FileNotFoundError:
            # Se não encontrou .ply/.pcd e há .stcm, tenta converter
            if stcm_files:
                stcm_file = max(stcm_files, key=lambda p: p.stat().st_mtime)
                ply_candidate = capture_dir / f"{stcm_file.stem}.ply"
                print(f"[refinement] Nenhum arquivo .ply/.pcd encontrado. Convertendo .stcm...")
                if _convert_stcm_to_ply(stcm_file, ply_candidate):
                    source_cloud = ply_candidate
                else:
                    raise ValueError(
                        f"❌ Nenhum arquivo de nuvem de pontos encontrado em {capture_dir}\n"
                        f"   Arquivo .stcm encontrado ({stcm_file.name}) mas conversão falhou.\n\n"
                        f"   ⚠️  IMPORTANTE: O Aurora SOMENTE exporta em formato .stcm (não há opção PLY/PCD).\n"
                        f"   O parser heurístico não conseguiu extrair os pontos do arquivo.\n\n"
                        f"   📋 SOLUÇÕES POSSÍVEIS:\n"
                        f"   1. Use o SDK do Aurora (se disponível) para converter .stcm → .ply antes\n"
                        f"   2. Melhore o STCMProcessor para fazer engenharia reversa do formato\n"
                        f"   3. Contate o suporte Slamtec para documentação do formato .stcm\n\n"
                        f"   O parser atual é heurístico e pode não funcionar para todos os arquivos .stcm."
                    )
            else:
                raise

    # Valida arquivo PLY antes de tentar ler
    if source_cloud.suffix.lower() == '.ply':
        print(f"[refinement] Validando arquivo PLY: {source_cloud}")
        _validate_ply_file(source_cloud)
    elif source_cloud.suffix.lower() == '.stcm':
        # Se ainda é .stcm, não conseguimos converter - avisa o usuário
        raise ValueError(
            f"❌ Arquivo .stcm não pôde ser convertido: {source_cloud}\n"
            f"   O Aurora SOMENTE exporta mapas em formato .stcm (não há opção PLY/PCD).\n"
            f"   O parser heurístico não conseguiu extrair os pontos do arquivo.\n\n"
            f"   📋 SOLUÇÕES POSSÍVEIS:\n"
            f"   1. Use o SDK do Aurora (se disponível) para converter .stcm → .ply\n"
            f"   2. Melhore o STCMProcessor para fazer engenharia reversa do formato\n"
            f"   3. Verifique se o arquivo .stcm não está corrompido\n"
            f"   4. Contate o suporte Slamtec para documentação do formato .stcm"
        )

    print(f"[refinement] Carregando nuvem {source_cloud}")
    cloud = o3d.io.read_point_cloud(str(source_cloud))
    initial_points = len(cloud.points)
    print(f"[refinement] Nuvem original: {initial_points} pontos")
    
    # Validação adicional: verifica se os pontos não são todos zeros
    if initial_points > 0:
        points = np.asarray(cloud.points)
        x_range = points[:, 0].max() - points[:, 0].min()
        y_range = points[:, 1].max() - points[:, 1].min()
        z_range = points[:, 2].max() - points[:, 2].min()
        
        # Se todas as coordenadas são zero ou muito próximas de zero, o arquivo pode estar corrompido
        if x_range < 0.01 and y_range < 0.01 and z_range < 0.01:
            raise ValueError(
                f"❌ Arquivo PLY parece estar corrompido ou vazio: {source_cloud}\n"
                f"   A nuvem foi carregada com {initial_points} pontos, mas todas as coordenadas são zero ou muito próximas de zero.\n"
                f"   Range X: {x_range:.6f}m, Y: {y_range:.6f}m, Z: {z_range:.6f}m\n\n"
                f"   Possíveis causas:\n"
                f"   - Arquivo PLY foi exportado incorretamente pelo Aurora Remote\n"
                f"   - Arquivo corrompido durante transferência\n"
                f"   - Formato do arquivo não é compatível\n\n"
                f"   Solução: Reexporte o mapa no Aurora Remote e verifique se o arquivo tem dados válidos."
            )
    
    if initial_points == 0:
        raise ValueError(
            f"❌ Nuvem de entrada está vazia: {source_cloud}\n"
            f"   O arquivo foi carregado mas não contém pontos.\n\n"
            f"   Possíveis causas:\n"
            f"   - Arquivo PLY está vazio ou corrompido\n"
            f"   - Formato do arquivo não é compatível\n\n"
            f"   Solução: Reexporte o mapa no Aurora Remote e verifique se o arquivo tem dados válidos."
        )
    
    if initial_points < refinement_config.get("min_points", 1000):
        print(
            f"[refinement] ⚠️  Aviso: Nuvem possui poucos pontos ({initial_points}). "
            "Processamento pode ter qualidade reduzida."
        )
    
    # Guarda cópia da nuvem original para fallback
    original_cloud = o3d.geometry.PointCloud(cloud)

    # Resolução do Aurora (usada como referência)
    aurora_resolution = float(refinement_config.get("aurora_resolution", 0.05))
    voxel_size = float(refinement_config.get("voxel_size", aurora_resolution))
    auto_adjust_voxel = refinement_config.get("auto_adjust_voxel_size", True)
    max_voxel_increase = float(refinement_config.get("max_voxel_increase_factor", 2.0))
    
    # Validação: voxel_size não deve ser muito menor que a resolução do Aurora
    if voxel_size < aurora_resolution * 0.5:
        print(
            f"[refinement] ⚠️  Aviso: voxel_size ({voxel_size:.3f}m) é menor que a resolução do Aurora "
            f"({aurora_resolution:.3f}m). Isso pode causar problemas. "
            f"Recomendado: voxel_size >= {aurora_resolution:.3f}m"
        )
        if auto_adjust_voxel:
            voxel_size = aurora_resolution
            print(f"[refinement] Ajustando voxel_size para {voxel_size:.3f}m (resolução do Aurora)")
    
    if voxel_size > 0:
        original_voxel_size = voxel_size
        was_adjusted = False
        
        # Calcula voxel_size apropriado se auto-ajuste estiver habilitado
        if auto_adjust_voxel:
            voxel_size, was_adjusted = _calculate_appropriate_voxel_size(
                cloud, voxel_size, max_voxel_increase
            )
            
            if was_adjusted:
                increase_factor = voxel_size / original_voxel_size
                print(
                    f"[refinement] ⚠️  Voxel_size ajustado de {original_voxel_size:.6f} para {voxel_size:.6f} "
                    f"(x{increase_factor:.2f}) - muito pequeno para a escala da nuvem"
                )
                if increase_factor > 2.0:
                    print(
                        f"[refinement] ⚠️  ATENÇÃO: Aumento significativo pode reduzir resolução do mapa. "
                        "Considere verificar a escala da nuvem de entrada."
                    )
        
        try:
            points_before_downsample = len(cloud.points)
            cloud = cloud.voxel_down_sample(voxel_size)
            points_after_downsample = len(cloud.points)
            reduction_ratio = 1.0 - (points_after_downsample / points_before_downsample)
            print(f"[refinement] Downsample voxel_size={voxel_size:.6f} ({points_before_downsample} → {points_after_downsample} pontos, -{reduction_ratio:.1%})")
            
            # Validação: se downsample removeu quase todos os pontos, pode ser problema
            if points_after_downsample < points_before_downsample * 0.01:  # Menos de 1% restou
                print(
                    f"[refinement] ⚠️  ATENÇÃO: Downsample removeu {reduction_ratio:.1%} dos pontos. "
                    "Voxel_size pode estar muito grande."
                )
        except RuntimeError as e:
            if "too small" in str(e).lower() or "voxel_size" in str(e).lower():
                # Tenta com um voxel_size maior (apenas se auto-ajuste permitir)
                if auto_adjust_voxel:
                    fallback_voxel_size = min(voxel_size * 1.5, original_voxel_size * max_voxel_increase)
                    print(
                        f"[refinement] ⚠️  Erro com voxel_size {voxel_size:.6f}. "
                        f"Tentando com {fallback_voxel_size:.6f}..."
                    )
                    try:
                        cloud = cloud.voxel_down_sample(fallback_voxel_size)
                        print(f"[refinement] Downsample voxel_size={fallback_voxel_size:.6f} (fallback)")
                    except RuntimeError:
                        print(
                            f"[refinement] ⚠️  Pulando downsample (voxel_size inadequado). "
                            "Continuando com nuvem original (pode afetar performance)."
                        )
                else:
                    raise ValueError(
                        f"Voxel_size {voxel_size:.6f} muito pequeno para a nuvem. "
                        "Habilite 'auto_adjust_voxel_size' ou ajuste manualmente."
                    ) from e
            else:
                raise

    # Filtro estatístico adaptativo
    nb_neighbors = int(refinement_config.get("statistical_nb_neighbors", 20))
    std_ratio = float(refinement_config.get("statistical_std_ratio", 2.0))
    adaptive_filtering = refinement_config.get("adaptive_statistical_filter", True)
    
    points_before_stat = len(cloud.points)
    cloud_before_stat = o3d.geometry.PointCloud(cloud)
    
    # Ajusta parâmetros se nuvem for pequena
    if adaptive_filtering and points_before_stat < 5000:
        nb_neighbors = min(nb_neighbors, max(5, points_before_stat // 200))
        std_ratio = max(std_ratio, 2.5)
        print(f"[refinement] Ajustando filtro estatístico para nuvem pequena (neighbors={nb_neighbors}, std={std_ratio})")
    
    try:
        cloud, _ = cloud.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)
        points_after_stat = len(cloud.points)
        reduction_ratio = 1.0 - (points_after_stat / points_before_stat) if points_before_stat > 0 else 0
        print(f"[refinement] Remoção estatística de ruído (neighbors={nb_neighbors}, std={std_ratio})")
        print(f"[refinement] Pontos após filtro estatístico: {points_before_stat} → {points_after_stat} (-{reduction_ratio:.1%})")
        
        # Validação: se filtro removeu quase todos os pontos, tenta com parâmetros mais suaves
        if points_after_stat < points_before_stat * 0.1 and points_after_stat > 0:  # Menos de 10% restou
            print(f"[refinement] ⚠️  ATENÇÃO: Filtro removeu {reduction_ratio:.1%} dos pontos. Tentando com parâmetros mais suaves...")
            cloud, _ = cloud_before_stat.remove_statistical_outlier(
                nb_neighbors=max(5, nb_neighbors // 2),
                std_ratio=std_ratio * 2.0
            )
            points_after_stat = len(cloud.points)
            if points_after_stat > 0:
                print(f"[refinement] Filtro suave aplicado: {points_after_stat} pontos restantes")
            else:
                print(f"[refinement] ⚠️  Filtro suave também removeu todos os pontos. Usando nuvem antes do filtro estatístico.")
                cloud = cloud_before_stat
                points_after_stat = len(cloud.points)
        
        if points_after_stat == 0:
            print(f"[refinement] ⚠️  Filtro estatístico removeu todos os pontos. Usando nuvem antes do filtro.")
            cloud = cloud_before_stat
    except Exception as e:
        print(f"[refinement] ⚠️  Erro no filtro estatístico: {e}. Continuando sem filtro estatístico.")
        cloud = cloud_before_stat

    # Remoção de plano (piso/teto)
    skip_plane_on_fail = refinement_config.get("skip_plane_removal_if_fails", True)
    plane_threshold = float(refinement_config.get("plane_distance_threshold", 0.02))
    ransac_n = int(refinement_config.get("plane_ransac_n", 3))
    iterations = int(refinement_config.get("plane_num_iterations", 1000))
    
    num_points = len(cloud.points)
    if num_points < ransac_n:
        if skip_plane_on_fail:
            print(
                f"[refinement] ⚠️  Aviso: Nuvem possui apenas {num_points} pontos após filtros, "
                f"insuficiente para segmentação de plano (mínimo: {ransac_n}). "
                "Pulando remoção de plano (pode deixar ruído no mapa)."
            )
        else:
            raise ValueError(
                f"Nuvem possui apenas {num_points} pontos, insuficiente para remoção de plano. "
                "Ajuste os parâmetros de filtro ou habilite 'skip_plane_removal_if_fails'."
            )
    else:
        try:
            plane_model, inliers = cloud.segment_plane(
                distance_threshold=plane_threshold,
                ransac_n=ransac_n,
                num_iterations=iterations,
            )
            a, b, c, d = plane_model
            normal = (a, b, c)
            inlier_count = len(inliers)
            inlier_ratio = inlier_count / num_points
            
            print(f"[refinement] Plano removido normal={normal} d={d:.4f} ({inlier_count} pontos, {inlier_ratio:.1%})")
            
            # Validação: se muito poucos pontos foram identificados como plano, pode ser ruído
            if inlier_ratio < 0.01:  # Menos de 1% dos pontos
                print(
                    f"[refinement] ⚠️  Aviso: Poucos pontos identificados como plano ({inlier_ratio:.1%}). "
                    "Pode ser ruído. Removendo mesmo assim."
                )
            
            cloud_after_plane = _select_by_mask(cloud, inliers, invert=True)
            points_after_plane = len(cloud_after_plane.points)
            
            # Validação: se remoção de plano removeu quase todos os pontos, pode ser que a nuvem seja principalmente plano
            if points_after_plane < num_points * 0.1:  # Menos de 10% restou
                print(
                    f"[refinement] ⚠️  ATENÇÃO: Remoção de plano removeu {1.0 - (points_after_plane/num_points):.1%} dos pontos. "
                    "A nuvem pode ser principalmente plano (piso). Mantendo plano removido."
                )
            
            cloud = cloud_after_plane
            print(f"[refinement] Pontos após remoção de plano: {num_points} → {points_after_plane}")
        except RuntimeError as e:
            if skip_plane_on_fail and ("ransac_n" in str(e).lower() or "points" in str(e).lower()):
                print(
                    f"[refinement] ⚠️  Aviso: Erro ao segmentar plano: {e}. "
                    "Continuando sem remoção de plano (pode deixar ruído no mapa)."
                )
            else:
                raise

    # Validação final com fallback
    final_points = len(cloud.points)
    if final_points == 0:
        print(
            f"[refinement] ❌ ERRO: Nuvem ficou vazia após processamento. "
            f"Tentando usar nuvem original ({len(original_cloud.points)} pontos)..."
        )
        
        # Tenta usar nuvem original apenas com downsample (se aplicável)
        if len(original_cloud.points) > 0:
            print("[refinement] Usando nuvem original sem filtros adicionais.")
            cloud = original_cloud
            
            # Aplica apenas downsample se voxel_size foi configurado
            if voxel_size > 0:
                try:
                    cloud = cloud.voxel_down_sample(voxel_size)
                    print(f"[refinement] Aplicado apenas downsample: {len(cloud.points)} pontos")
                except Exception:
                    print("[refinement] Pulando downsample na nuvem original.")
            
            final_points = len(cloud.points)
            
            if final_points == 0:
                raise ValueError(
                    f"Nuvem ficou vazia mesmo usando original. "
                    f"Nuvem original tinha {len(original_cloud.points)} pontos. "
                    "Verifique a qualidade do arquivo de entrada."
                )
        else:
            raise ValueError(
                "Nuvem ficou vazia após processamento e nuvem original também está vazia. "
                "Verifique o arquivo de entrada."
            )
    
    min_points = refinement_config.get("min_points", 5000)
    if final_points < min_points:
        print(
            f"[refinement] ⚠️  Aviso: Nuvem final possui apenas {final_points} pontos "
            f"(recomendado: {min_points}+). O mapa pode ter baixa qualidade."
        )

    clean_name = f"{source_cloud.stem}_clean.ply"
    clean_path = output_dir / clean_name
    o3d.io.write_point_cloud(str(clean_path), cloud)
    print(f"[refinement] Nuvem limpa salva em {clean_path} ({final_points} pontos)")

    if bool(refinement_config.get("preview_image", True)):
        _save_preview(cloud, output_dir / f"{source_cloud.stem}_preview.png")


def _calculate_appropriate_voxel_size(
    cloud: "o3d.geometry.PointCloud", desired_voxel_size: float, max_increase_factor: float = 3.0
) -> Tuple[float, bool]:
    """
    Calcula um voxel_size apropriado baseado na escala da nuvem.
    
    Returns:
        (voxel_size, was_adjusted): Tupla com o voxel_size e se foi ajustado
    """

    if len(cloud.points) == 0:
        return desired_voxel_size, False

    points = np.asarray(cloud.points)
    
    # Calcula a extensão da nuvem em cada eixo
    min_bounds = points.min(axis=0)
    max_bounds = points.max(axis=0)
    extent = max_bounds - min_bounds
    
    # Calcula uma estimativa da distância mínima entre pontos
    # Baseado na densidade de pontos
    volume = np.prod(extent[extent > 0])
    if volume > 0:
        # Densidade de pontos por unidade de volume
        density = len(points) / volume
        # Distância média estimada entre pontos vizinhos
        avg_distance = (1.0 / density) ** (1.0 / 3.0)
    else:
        # Fallback: usa a menor extensão não-zero
        avg_distance = np.min(extent[extent > 0]) / (len(points) ** (1.0 / 3.0))
    
    # Voxel_size mínimo necessário (conservador: apenas 1.5x a distância média)
    min_voxel_size = max(avg_distance * 1.5, 1e-5)
    
    # Limita o aumento máximo para preservar qualidade
    max_allowed_voxel_size = desired_voxel_size * max_increase_factor
    
    # Se o voxel_size desejado é muito pequeno, ajusta conservadoramente
    if desired_voxel_size < min_voxel_size:
        adjusted = min(min_voxel_size * 1.2, max_allowed_voxel_size)  # Aumento conservador
        return adjusted, True
    
    return desired_voxel_size, False


def _normalize_exts(extensions: Iterable[str]) -> Sequence[str]:
    return [ext if ext.startswith(".") else f".{ext}" for ext in extensions]


def _validate_ply_file(file_path: Path) -> None:
    """
    Valida se um arquivo PLY está completo e tem dados válidos.
    
    Raises:
        ValueError: Se o arquivo estiver vazio, corrompido ou incompleto.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
    
    file_size = file_path.stat().st_size
    
    # Verifica se o arquivo é muito pequeno (apenas header)
    if file_size < 500:  # Header típico tem ~100-200 bytes, dados começam depois
        raise ValueError(
            f"❌ Arquivo PLY parece estar vazio ou incompleto: {file_path}\n"
            f"   Tamanho: {file_size} bytes (muito pequeno para conter dados de pontos)\n"
            f"   Possíveis causas:\n"
            f"   - Exportação interrompida do Aurora Remote\n"
            f"   - Arquivo corrompido durante transferência\n"
            f"   - Erro durante salvamento\n\n"
            f"   Solução: Reexporte o mapa no Aurora Remote e verifique se o arquivo tem tamanho adequado (> 100 KB)."
        )
    
    # Para arquivos PLY binários, verifica se há dados após o header
    if file_path.suffix.lower() == '.ply':
        try:
            with open(file_path, 'rb') as f:
                # Lê header
                header_lines = []
                while True:
                    line = f.readline()
                    header_lines.append(line)
                    if b'end_header' in line:
                        break
                
                header_size = sum(len(l) for l in header_lines)
                
                # Verifica se há dados após o header
                f.seek(0, 2)  # Vai para o fim do arquivo
                total_size = f.tell()
                
                data_size = total_size - header_size
                
                # Lê header para verificar quantos vértices são esperados
                header_str = b''.join(header_lines).decode('ascii', errors='ignore')
                vertex_count = 0
                for line in header_str.split('\n'):
                    if line.startswith('element vertex'):
                        try:
                            vertex_count = int(line.split()[-1])
                        except (ValueError, IndexError):
                            pass
                
                # Calcula tamanho esperado (assumindo float32 = 12 bytes por vértice)
                if vertex_count > 0:
                    expected_size = vertex_count * 12  # 3 floats * 4 bytes cada
                    
                    if data_size < expected_size * 0.1:  # Menos de 10% do esperado
                        raise ValueError(
                            f"❌ Arquivo PLY incompleto: {file_path}\n"
                            f"   Header indica {vertex_count:,} vértices, mas arquivo tem apenas {data_size:,} bytes de dados\n"
                            f"   (esperado: ~{expected_size:,} bytes para {vertex_count:,} vértices)\n"
                            f"   Tamanho total: {file_size:,} bytes\n\n"
                            f"   Possíveis causas:\n"
                            f"   - Exportação interrompida do Aurora Remote\n"
                            f"   - Arquivo corrompido durante transferência\n"
                            f"   - Erro durante salvamento\n\n"
                            f"   Solução: Reexporte o mapa no Aurora Remote e verifique se o arquivo tem tamanho adequado."
                        )
        except (UnicodeDecodeError, IOError) as e:
            # Se não conseguir ler o header, pode ser corrompido
            raise ValueError(
                f"❌ Não foi possível ler o header do arquivo PLY: {file_path}\n"
                f"   Erro: {e}\n"
                f"   O arquivo pode estar corrompido.\n\n"
                f"   Solução: Reexporte o mapa no Aurora Remote."
            ) from e


def _locate_latest_cloud(base_dir: Path, extensions: Sequence[str]) -> Path:
    if not base_dir.exists():
        raise FileNotFoundError(f"Pasta de captura não encontrada: {base_dir}")

    candidates = [
        path for ext in extensions for path in base_dir.glob(f"*{ext}")
    ]
    if not candidates:
        raise FileNotFoundError(
            f"Nenhum arquivo de nuvem encontrado em {base_dir} com extensões {extensions}"
        )

    return max(candidates, key=lambda path: path.stat().st_mtime)


def _save_preview(cloud: "o3d.geometry.PointCloud", output_path: Path) -> None:
    if plt is None:
        print("[refinement] matplotlib não disponível; preview não será gerado.")
        return

    points = np.asarray(cloud.points)
    if points.size == 0:
        print("[refinement] Nuvem sem pontos; preview não será gerado.")
        return

    plt.figure(figsize=(6, 6))
    plt.scatter(points[:, 0], points[:, 1], s=0.3, c=points[:, 2], cmap="viridis")
    plt.axis("equal")
    plt.title("Aurora Clean Projection (XY)")
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"[refinement] Preview salvo em {output_path}")


def _select_by_mask(
    cloud: "o3d.geometry.PointCloud",
    indices: Sequence[int],
    invert: bool = False,
) -> "o3d.geometry.PointCloud":
    total_points = len(cloud.points)
    if total_points == 0:
        return cloud

    indices = np.asarray(indices, dtype=int)
    mask = np.ones(total_points, dtype=bool) if invert else np.zeros(total_points, dtype=bool)
    if invert:
        mask[indices] = False
    else:
        mask[indices] = True

    points = np.asarray(cloud.points)[mask]
    filtered = o3d.geometry.PointCloud()
    filtered.points = o3d.utility.Vector3dVector(points)

    if cloud.has_colors():
        filtered.colors = o3d.utility.Vector3dVector(np.asarray(cloud.colors)[mask])
    if cloud.has_normals():
        filtered.normals = o3d.utility.Vector3dVector(np.asarray(cloud.normals)[mask])

    return filtered
