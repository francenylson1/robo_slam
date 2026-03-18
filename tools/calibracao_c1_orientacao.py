#!/usr/bin/env python3
"""
Calibração de orientação do RP Lidar C1 — mapeia ângulos do sensor para posições do robô.

Objetivo: descobrir com precisão quais ângulos (0–360°) correspondem a:
  - FRENTE do robô (direção de movimento)
  - ESQUERDA 90°
  - DIREITA 90°
  - TRÁS
  - Quais ângulos "enxergam" o corpo do robô (para excluir da detecção)

Uso:
  # Modo assistido (wizard passo a passo)
  python tools/calibracao_c1_orientacao.py --port /dev/ttyUSB0 --wizard

  # Apenas mapa de referência (robô sozinho)
  python tools/calibracao_c1_orientacao.py --port /dev/ttyUSB0 --mapa-referencia --scans 5

  # Obstáculo em posição conhecida (você informa onde colocou)
  python tools/calibracao_c1_orientacao.py --port /dev/ttyUSB0 --obstaculo frente --distancia-cm 75 --scans 5

  # Exportar dados brutos (CSV) para análise
  python tools/calibracao_c1_orientacao.py --port /dev/ttyUSB0 --export-csv dados.csv --scans 3

  # Exportar resultado da calibração (JSON)
  python tools/calibracao_c1_orientacao.py --port /dev/ttyUSB0 --wizard --output calibracao.json

Requer: pip install rplidarc1 (Python 3.10+)
"""

import argparse
import asyncio
import csv
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_BAUD = 460800
SECTOR_DEG = 10  # Granularidade do mapa angular


def _norm_angle(deg: float) -> float:
    return deg % 360.0


@dataclass
class MapaSetores:
    """Mapa angular: por cada setor de SECTOR_DEG graus."""
    setores: List[dict] = field(default_factory=list)
    angulo_min_global: float = 0.0
    dist_min_global_mm: float = 0.0
    angulo_max_global: float = 0.0
    dist_max_global_mm: float = 0.0


@dataclass
class CalibracaoResultado:
    """Resultado da calibração para uso em config."""
    frente_graus: Optional[float] = None
    esquerda_graus: Optional[float] = None
    direita_graus: Optional[float] = None
    tras_graus: Optional[float] = None
    angulos_corpo: List[Tuple[float, float]] = field(default_factory=list)
    cone_frontal_sugerido: Optional[float] = None
    centro_frontal_sugerido: Optional[float] = None
    mapa_referencia: Optional[dict] = None
    observacoes: str = ""


async def coletar_scans(lidar, n_scans: int) -> List[dict]:
    """Coleta N varreduras completas do C1. Retorna lista de pontos {a_deg, d_mm}."""
    points = []
    scan_count = 0
    last_angle = None

    while True:
        try:
            data = await asyncio.wait_for(lidar.output_queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            if lidar.stop_event.is_set():
                break
            continue
        except Exception:
            if lidar.stop_event.is_set():
                break
            continue

        points.append(data)
        ang = data.get("a_deg", 0)

        if last_angle is not None and last_angle > 350 and ang < 10:
            scan_count += 1
            if n_scans > 0 and scan_count >= n_scans:
                lidar.stop_event.set()
                break
        last_angle = ang

    valid = [p for p in points if (p.get("d_mm") or 0) > 0]
    return valid


def construir_mapa_setores(points: List[dict], sector_deg: int = SECTOR_DEG) -> MapaSetores:
    """Constrói mapa angular por setores."""
    n = int(360 / sector_deg)
    sector_min = [float("inf")] * n
    sector_max = [0.0] * n
    sector_count = [0] * n
    sector_avg_sum = [0.0] * n

    for p in points:
        ang = p.get("a_deg", 0)
        d = p.get("d_mm") or 0
        if d <= 0:
            continue
        idx = min(int(ang / sector_deg) % n, n - 1)
        sector_min[idx] = min(sector_min[idx], d)
        sector_max[idx] = max(sector_max[idx], d)
        sector_count[idx] += 1
        sector_avg_sum[idx] += d

    setores = []
    global_min_mm = float("inf")
    global_max_mm = 0.0
    ang_min = 0.0
    ang_max = 0.0

    for i in range(n):
        lo = i * sector_deg
        hi = lo + sector_deg
        d_min = sector_min[i] if sector_min[i] != float("inf") else 0
        d_max = sector_max[i]
        n_pts = sector_count[i]
        avg = sector_avg_sum[i] / n_pts if n_pts > 0 else 0

        if d_min > 0 and d_min < global_min_mm:
            global_min_mm = d_min
            ang_min = (lo + hi) / 2
        if d_max > global_max_mm:
            global_max_mm = d_max
            ang_max = (lo + hi) / 2

        setores.append({
            "angulo_lo": lo,
            "angulo_hi": hi,
            "angulo_centro": (lo + hi) / 2,
            "min_mm": round(d_min, 1) if d_min != float("inf") else None,
            "max_mm": round(d_max, 1) if n_pts > 0 else None,
            "media_mm": round(avg, 1) if n_pts > 0 else None,
            "pontos": n_pts,
        })

    return MapaSetores(
        setores=setores,
        angulo_min_global=ang_min,
        dist_min_global_mm=global_min_mm if global_min_mm != float("inf") else 0,
        angulo_max_global=ang_max,
        dist_max_global_mm=global_max_mm,
    )


def encontrar_angulo_obstaculo(
    points: List[dict],
    dist_min_mm: float = 200,
    dist_max_mm: float = 2000,
    angulo_hint: Optional[float] = None,
) -> Optional[Tuple[float, float]]:
    """
    Encontra o ângulo do obstáculo mais PRÓXIMO na faixa [dist_min_mm, dist_max_mm].

    IMPORTANTE: Usa distância mínima, NÃO quantidade de pontos.
    O algoritmo anterior pegava o setor com MAIS pontos — paredes/móveis (muitos
    pontos a 1–2 m) sempre ganhavam da lixeira de calibração (~500 mm, poucos pontos).
    Para calibração, o objeto do usuário (50–80 cm) deve ser o mais PRÓXIMO.
    """
    candidatos = [
        p for p in points
        if dist_min_mm <= (p.get("d_mm") or 0) <= dist_max_mm
    ]
    if not candidatos:
        return None

    # Agrupa por setor de 20°
    sector_deg = 20
    n = int(360 / sector_deg)
    sector_dists = [[] for _ in range(n)]

    for p in candidatos:
        ang = p.get("a_deg", 0)
        d = p.get("d_mm") or 0
        idx = min(int(ang / sector_deg) % n, n - 1)
        sector_dists[idx].append(d)

    # Setor com obstáculo mais PRÓXIMO (dist mínima)
    # MIN_PONTOS_SETOR=2: lixeira/objeto pequeno pode ter só 2–4 pontos em 20°;
    # 5 era alto demais e fazia setor da lixeira ser ignorado, ganhando parede (muitos pts)
    MIN_PONTOS_SETOR = 2
    best_idx = -1
    best_min_dist = float("inf")
    best_avg = 0.0

    for i in range(n):
        if len(sector_dists[i]) < MIN_PONTOS_SETOR:
            continue
        dists = sector_dists[i]
        avg_d = sum(dists) / len(dists)
        min_d = min(dists)
        # Critério: menor distância MÍNIMA no setor (objeto mais próximo)
        if min_d < best_min_dist:
            best_min_dist = min_d
            best_idx = i
            best_avg = avg_d

    # Fallback: se nenhum setor qualificou (candidatos esparsos), use o ponto mais próximo
    if best_idx < 0 and candidatos:
        closest = min(candidatos, key=lambda p: p.get("d_mm") or float("inf"))
        ang = closest.get("a_deg", 0)
        d = closest.get("d_mm", 0)
        idx = min(int(ang / sector_deg) % n, n - 1)
        ang_centro = (idx * sector_deg) + sector_deg / 2
        return (ang_centro, d)

    if best_idx < 0:
        return None
    ang_centro = (best_idx * sector_deg) + sector_deg / 2
    return (ang_centro, best_avg)


def imprimir_mapa(mapa: MapaSetores, destaque_corpo_mm: float = 250) -> None:
    """Imprime o mapa angular de forma legível."""
    print("\n" + "=" * 70)
    print("MAPA ANGULAR — Distância mínima por setor (%d° por setor)" % SECTOR_DEG)
    print("=" * 70)
    print("   Ângulo      | min(mm) | max(mm) | pts | status")
    print("   " + "-" * 55)

    for s in mapa.setores:
        lo, hi = s["angulo_lo"], s["angulo_hi"]
        d_min = s["min_mm"] or 0
        d_max = s["max_mm"] or 0
        n = s["pontos"]
        if d_min > 0 and d_min < destaque_corpo_mm:
            status = "<-- provável corpo/estrutura"
        elif d_min > destaque_corpo_mm and d_min < 1000:
            status = "obstáculo próximo"
        elif d_min >= 1000:
            status = "livre"
        else:
            status = "sem dados"
        print("   {:3.0f}°–{:3.0f}°    | {:6.0f} | {:6.0f} | {:3} | {}".format(
            lo, hi, d_min, d_max, n, status
        ))

    print("   " + "-" * 55)
    print("   Mínimo global: {:.0f} mm em ~{:.0f}°".format(
        mapa.dist_min_global_mm, mapa.angulo_min_global
    ))
    print("   Máximo global: {:.0f} mm em ~{:.0f}°".format(
        mapa.dist_max_global_mm, mapa.angulo_max_global
    ))
    print("=" * 70)


def run_test(
    lidar,
    n_scans: int,
    sector_deg: int = SECTOR_DEG,
) -> Tuple[List[dict], MapaSetores]:
    """Executa coleta e retorna (pontos, mapa)."""
    points = asyncio.get_event_loop().run_until_complete(coletar_scans(lidar, n_scans))
    mapa = construir_mapa_setores(points, sector_deg)
    return points, mapa


def main_wizard(port: str, baud: int, n_scans: int, output_path: Optional[str]) -> int:
    """Modo wizard: guia o usuário passo a passo."""
    # Garantir path do projeto para import de tools.teste_c1_isolado
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    try:
        from rplidarc1.scanner import RPLidar
    except ImportError:
        try:
            from rplidarc1 import RPLidar
        except ImportError:
            print("❌ Pacote 'rplidarc1' não instalado. Execute: pip install rplidarc1")
            return 1

    resultado = CalibracaoResultado()

    print("\n" + "=" * 70)
    print("CALIBRAÇÃO DE ORIENTAÇÃO — RP Lidar C1")
    print("   Mapeia ângulos do sensor para posições do robô (frente, esq, dir, trás)")
    print("=" * 70)
    print("")
    print("   ATENÇÃO — Convenção de ângulos:")
    print("   O C1 pode usar ÂNGULOS NO SENTIDO ANTI-HORÁRIO (visto de cima):")
    print("   0°=frente | 90°=esquerda | 180°=trás | 270°=direita")
    print("   OU sentido horário (90°=direita, 270°=esquerda), conforme montagem.")
    print("   O wizard mostra o ângulo RAW reportado pelo sensor.")
    print("   Use FRONT_CENTER = valor da etapa FRENTE para lidar_c1_reader.")
    print("")

    try:
        # --- PASSO 1: Robô sozinho ---
        print("\n" + "-" * 70)
        print("PASSO 1: MAPA DE REFERÊNCIA (robô sozinho)")
        print("-" * 70)
        print("   Coloque o robô em área LIVRE (longe de paredes e obstáculos).")
        print("   Certifique-se de que NADA está à frente, atrás ou nas laterais.")
        input("   Pressione ENTER quando estiver pronto... ")

        # Usa a mesma lógica do teste_c1_isolado (que funciona) via collect_scan_points_sync
        _proj = Path(__file__).resolve().parent.parent
        if str(_proj) not in sys.path:
            sys.path.insert(0, str(_proj))
        try:
            from tools.teste_c1_isolado import collect_scan_points_sync
            collected = collect_scan_points_sync(port=port, baud=baud, n_scans=n_scans or 3)
        except ImportError:
            try:
                from teste_c1_isolado import collect_scan_points_sync
                collected = collect_scan_points_sync(port=port, baud=baud, n_scans=n_scans or 3)
            except ImportError:
                print("   ❌ Não foi possível importar collect_scan_points_sync.")
                print("   Execute a partir da raiz: cd ~/robo_slam && python tools/calibracao_c1_orientacao.py --wizard")
                return 1
        except Exception as e:
            print(f"\n   ❌ Erro ao coletar scans: {e}")
            if "sync" in str(e).lower() or "ValueError" in str(type(e).__name__):
                print("   → Desconecte o cabo USB do C1, espere 3 segundos e reconecte.")
            return 1

        if not collected:
            print("   ⚠️ Nenhum ponto válido coletado. Verifique a conexão.")
        else:
            mapa1 = construir_mapa_setores(collected)
            imprimir_mapa(mapa1)
            resultado.mapa_referencia = asdict(mapa1)

            # Ângulos com dist < 250mm = provável corpo
            angs_corpo = []
            for s in mapa1.setores:
                if s["min_mm"] and s["min_mm"] < 250:
                    angs_corpo.append((s["angulo_lo"], s["angulo_hi"]))
            resultado.angulos_corpo = angs_corpo

        # --- PASSO 2: Obstáculo na FRENTE ---
        print("\n" + "-" * 70)
        print("PASSO 2: OBSTÁCULO NA FRENTE")
        print("-" * 70)
        print("   Coloque um objeto (lixeira, caixa) EXATAMENTE na FRENTE do robô,")
        print("   na direção em que ele SE MOVE, a 50–80 cm de distância.")
        input("   Pressione ENTER quando estiver pronto... ")

        try:
            collected2 = collect_scan_points_sync(port=port, baud=baud, n_scans=n_scans or 2)
        except Exception as e:
            print(f"\n   ❌ Erro: {e}")
            collected2 = []

        res = encontrar_angulo_obstaculo(collected2, 300, 1500)
        if res:
            ang_frente, dist_frente = res
            resultado.frente_graus = round(ang_frente, 1)
            print("\n   ✓ FRENTE do robô ≈ {:.0f}° (obstáculo a ~{:.0f} mm)".format(ang_frente, dist_frente))
        else:
            print("\n   ⚠️ Não foi possível identificar obstáculo na faixa 300–1500 mm.")
            print("      Verifique se o objeto está visível e na distância correta.")

        # --- PASSO 3: Obstáculo à ESQUERDA ---
        print("\n" + "-" * 70)
        print("PASSO 3: OBSTÁCULO À ESQUERDA 90°")
        print("-" * 70)
        print("   RETIRE o objeto da frente. Coloque o MESMO objeto à ESQUERDA do robô,")
        print("   a 90° da frente (perpendicular), a ~50–80 cm.")
        input("   Pressione ENTER quando estiver pronto... ")

        try:
            collected3 = collect_scan_points_sync(port=port, baud=baud, n_scans=n_scans or 2)
        except Exception as e:
            print(f"\n   Erro: {e}")
            collected3 = []

        res = encontrar_angulo_obstaculo(collected3, 300, 1500)
        if res:
            ang_esq, _ = res
            resultado.esquerda_graus = round(ang_esq, 1)
            print("\n   ✓ ESQUERDA 90° ≈ {:.0f}°".format(ang_esq))

        # --- PASSO 4: Obstáculo à DIREITA ---
        print("\n" + "-" * 70)
        print("PASSO 4: OBSTÁCULO À DIREITA 90°")
        print("-" * 70)
        print("   RETIRE o objeto da esquerda. Coloque à DIREITA do robô (90° da frente).")
        input("   Pressione ENTER quando estiver pronto... ")

        try:
            collected4 = collect_scan_points_sync(port=port, baud=baud, n_scans=n_scans or 2)
        except Exception as e:
            print(f"\n   ❌ Erro: {e}")
            collected4 = []

        res = encontrar_angulo_obstaculo(collected4, 300, 1500)
        if res:
            ang_dir, _ = res
            resultado.direita_graus = round(ang_dir, 1)
            print("\n   ✓ DIREITA 90° ≈ {:.0f}°".format(ang_dir))
            # Validação: esquerda e direita NÃO podem ser o mesmo ângulo (impossível geometricamente)
            if resultado.esquerda_graus is not None:
                diff = abs(resultado.direita_graus - resultado.esquerda_graus)
                diff_wrap = min(diff, 360 - diff)  # menor arco entre os dois ângulos
                if diff_wrap < 90:
                    print("\n   ⚠️ INCONSISTÊNCIA: Esquerda ({:.0f}°) e Direita ({:.0f}°) muito próximas!")
                    print("      Geometricamente devem estar ~180° aparte (ex: 90° e 270°).")
                    print("      Possível causa: objeto não foi movido para o outro lado, ou confusão esq/dir.")
                    print("      Sugestão: repita o PASSO 4 — coloque o objeto no LADO OPOSTO ao do PASSO 3.")
                    resultado.direita_graus = None  # não confiar neste valor

        # --- PASSO 5: Obstáculo ATRÁS ---
        print("\n" + "-" * 70)
        print("PASSO 5: OBSTÁCULO ATRÁS")
        print("-" * 70)
        print("   RETIRE o objeto. Coloque ATRÁS do robô (na traseira), ~50–80 cm.")
        input("   Pressione ENTER quando estiver pronto... ")

        try:
            collected5 = collect_scan_points_sync(port=port, baud=baud, n_scans=n_scans or 2)
        except Exception as e:
            print(f"\n   ❌ Erro: {e}")
            collected5 = []

        res = encontrar_angulo_obstaculo(collected5, 300, 1500)
        if res:
            ang_tras, _ = res
            resultado.tras_graus = round(ang_tras, 1)
            print("\n   ✓ TRÁS ≈ {:.0f}°".format(ang_tras))

        # --- Sugestões ---
        if resultado.frente_graus is not None:
            resultado.centro_frontal_sugerido = resultado.frente_graus
            resultado.cone_frontal_sugerido = 60  # Começar estreito
            print("\n" + "=" * 70)
            print("RESUMO DA CALIBRAÇÃO")
            print("=" * 70)
            print("   (Ângulos RAW do sensor C1 — vide docs/CONVENCAO_ANGULOS_C1_MAR2026.md)")
            print("")
            print("   Frente (direção de movimento): {:.0f}°".format(resultado.frente_graus))
            if resultado.esquerda_graus is not None:
                print("   Esquerda (obst. à esq.):   {:.0f}°".format(resultado.esquerda_graus))
            if resultado.direita_graus is not None:
                print("   Direita (obst. à dir.):    {:.0f}°".format(resultado.direita_graus))
            if resultado.tras_graus is not None:
                print("   Trás:                      {:.0f}°".format(resultado.tras_graus))
            print("\n   Sugestão para lidar_c1_reader:")
            print("     FRONT_CENTER_DEG = {:.0f}".format(resultado.frente_graus))
            print("     FRONT_WIDTH_DEG = 60  (ou 80, 100 para mais cobertura)")
            print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n⚠️ Interrompido pelo usuário.")
    # Sem finally com lidar — cada passo usa collect_scan_points_sync (nova conexão por passo)

    if output_path:
        out = {}
        if resultado.frente_graus is not None:
            out["frente_graus"] = resultado.frente_graus
        if resultado.esquerda_graus is not None:
            out["esquerda_graus"] = resultado.esquerda_graus
        if resultado.direita_graus is not None:
            out["direita_graus"] = resultado.direita_graus
        if resultado.tras_graus is not None:
            out["tras_graus"] = resultado.tras_graus
        out["angulos_corpo"] = resultado.angulos_corpo
        out["centro_frontal_sugerido"] = resultado.centro_frontal_sugerido
        out["cone_frontal_sugerido"] = resultado.cone_frontal_sugerido
        if resultado.mapa_referencia:
            out["mapa_referencia"] = resultado.mapa_referencia

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print("\n   Salvo em:", output_path)

    return 0


def main_mapa_referencia(port: str, baud: int, n_scans: int) -> int:
    """Apenas mapa de referência (robô sozinho)."""
    try:
        from rplidarc1.scanner import RPLidar
    except ImportError:
        try:
            from rplidarc1 import RPLidar
        except ImportError:
            print("❌ Pacote 'rplidarc1' não instalado.")
            return 1

    lidar = RPLidar(port, baud, timeout=0.2)
    collected = []

    async def _run():
        nonlocal collected
        pts = []
        la = None
        cnt = 0
        while not lidar.stop_event.is_set():
            try:
                d = await asyncio.wait_for(lidar.output_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            pts.append(d)
            ang = d.get("a_deg", 0)
            if la is not None and la > 350 and ang < 10:
                cnt += 1
                if n_scans > 0 and cnt >= n_scans:
                    lidar.stop_event.set()
                    break
            la = ang
        collected = [p for p in pts if (p.get("d_mm") or 0) > 0]

    print("\nColetando %d varreduras (robô sozinho)..." % n_scans)
    lidar.stop_event.clear()
    if hasattr(asyncio, "TaskGroup"):
        async def _full():
            async with asyncio.TaskGroup() as tg:
                tg.create_task(lidar.simple_scan())
                await _run()
        asyncio.get_event_loop().run_until_complete(_full())
    else:
        t1 = asyncio.create_task(lidar.simple_scan())
        asyncio.get_event_loop().run_until_complete(_run())
        t1.cancel()

    if not collected:
        print("Nenhum ponto coletado.")
    else:
        mapa = construir_mapa_setores(collected)
        imprimir_mapa(mapa)

    try:
        lidar.stop_event.set()
        lidar.reset()
        lidar.shutdown()
    except Exception:
        pass
    return 0


def main_export_csv(port: str, baud: int, n_scans: int, csv_path: str) -> int:
    """Exporta pontos brutos (ângulo, distância) para CSV."""
    try:
        from rplidarc1.scanner import RPLidar
    except ImportError:
        try:
            from rplidarc1 import RPLidar
        except ImportError:
            print("❌ Pacote 'rplidarc1' não instalado.")
            return 1

    lidar = RPLidar(port, baud, timeout=0.2)
    collected = []

    async def _run():
        nonlocal collected
        pts = []
        la = None
        cnt = 0
        while not lidar.stop_event.is_set():
            try:
                d = await asyncio.wait_for(lidar.output_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            pts.append(d)
            ang = d.get("a_deg", 0)
            if la is not None and la > 350 and ang < 10:
                cnt += 1
                if n_scans > 0 and cnt >= n_scans:
                    lidar.stop_event.set()
                    break
            la = ang
        collected = [p for p in pts if (p.get("d_mm") or 0) > 0]

    print("Coletando %d varreduras para CSV..." % n_scans)
    lidar.stop_event.clear()
    if hasattr(asyncio, "TaskGroup"):
        async def _full():
            async with asyncio.TaskGroup() as tg:
                tg.create_task(lidar.simple_scan())
                await _run()
        asyncio.get_event_loop().run_until_complete(_full())
    else:
        t1 = asyncio.create_task(lidar.simple_scan())
        asyncio.get_event_loop().run_until_complete(_run())
        t1.cancel()

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["angulo_deg", "distancia_mm"])
        for p in collected:
            w.writerow([p.get("a_deg", 0), p.get("d_mm", 0)])
    print("Exportado %d pontos para %s" % (len(collected), csv_path))

    try:
        lidar.stop_event.set()
        lidar.reset()
        lidar.shutdown()
    except Exception:
        pass
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Calibração de orientação do RP Lidar C1 — mapeia ângulos para posições do robô.",
    )
    parser.add_argument("--port", "-p", default=DEFAULT_PORT, help="Porta serial")
    parser.add_argument("--baud", "-b", type=int, default=DEFAULT_BAUD, help="Baudrate")
    parser.add_argument("--scans", "-n", type=int, default=3, help="Varreduras por teste")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--wizard", "-w", action="store_true", help="Modo assistido passo a passo")
    mode.add_argument("--mapa-referencia", "-m", action="store_true", help="Apenas mapa de referência (robô sozinho)")
    mode.add_argument("--export-csv", metavar="ARQUIVO", help="Exportar pontos brutos para CSV")

    parser.add_argument("--output", "-o", metavar="ARQUIVO", help="Salvar resultado da calibração em JSON (com --wizard)")
    args = parser.parse_args()

    if args.wizard:
        return main_wizard(args.port, args.baud, args.scans, args.output)
    if args.mapa_referencia:
        return main_mapa_referencia(args.port, args.baud, args.scans)
    if args.export_csv:
        return main_export_csv(args.port, args.baud, args.scans, args.export_csv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
