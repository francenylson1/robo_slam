"""
Leitor do RP Lidar C1 integrado à navegação — Etapa 3 da Fase 2.

Fornece detecção de obstáculo frontal/lateral para parada automática dos motores.
Usa a mesma lógica do teste_c1_isolado (faixa 200°, zona parachoques 120°-240°).

Requer: pip install rplidarc1 (Python 3.10+)
Uso: apenas em Raspberry Pi, quando LIDAR_C1_ENABLED=True.
"""

import asyncio
import logging
import threading
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Parâmetros calibrados via tools/calibracao_c1_orientacao.py (Mar/2026)
# Frente do robô = 350° | corpo/estrutura = 120°–240° (95mm)
# FRONT_WIDTH_DEG: 120° (era 60°) — cone 60° era estreito demais, lixeira fora do cone não era detectada
FRONT_CENTER_DEG = 350.0
FRONT_WIDTH_DEG = 120.0
PARACHOQUES_ZONE = (120.0, 240.0)  # Ignorar reflexos do corpo do robô
MIN_IGNORE_M = 0.15
PARACHOQUES_MIN_IGNORE_M = 0.22
DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_BAUD = 460800
# Se o 1º scan não completar em 5 s, consideramos livre para não bloquear navegação indefinidamente
FIRST_SCAN_TIMEOUT_SEC = 5.0


def _norm_angle(deg: float) -> float:
    """Normaliza ângulo para [0, 360)."""
    return deg % 360.0


def _is_in_frontal_cone(angle_deg: float, center_deg: float, width_deg: float) -> bool:
    """Verifica se o ângulo está dentro do cone frontal."""
    if width_deg >= 360:
        return True
    half = width_deg / 2.0
    a = _norm_angle(angle_deg)
    c = _norm_angle(center_deg)
    diff = abs(a - c)
    if diff > 180:
        diff = 360 - diff
    return diff <= half


class LidarC1Reader:
    """
    Leitor do C1 em background para decisão de obstáculo.
    Atualiza _obstacle_distance_m a cada varredura completa.
    """

    def __init__(
        self,
        port: str = DEFAULT_PORT,
        baud: int = DEFAULT_BAUD,
        min_stop_m: float = 0.45,
        front_center: float = FRONT_CENTER_DEG,
        front_width: float = FRONT_WIDTH_DEG,
        parachoques_zone: Tuple[float, float] = PARACHOQUES_ZONE,
        parachoques_min_ignore_m: float = PARACHOQUES_MIN_IGNORE_M,
        min_ignore_m: float = MIN_IGNORE_M,
    ):
        self.port = port
        self.baud = baud
        self.min_stop_m = min_stop_m
        self.front_center = front_center
        self.front_width = front_width
        self.parachoques_zone = parachoques_zone
        self.parachoques_min_ignore_m = parachoques_min_ignore_m
        self.min_ignore_m = min_ignore_m

        # Inicialmente 0 m: bloqueia movimento até o primeiro scan (segurança).
        self._obstacle_distance_m: float = 0.0
        self._first_scan_done: bool = False  # Para log único do 1º scan
        # Não sobrescrever obstáculo com inf em um único scan (evita "perder" detecção)
        self._consecutive_clear_scans: int = 0
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self._lidar = None

    def has_obstacle(self) -> bool:
        """Retorna True se obstáculo < min_stop_m na faixa frontal (considerando zona parachoques)."""
        with self._lock:
            return self._obstacle_distance_m < self.min_stop_m

    def obstacle_distance(self) -> float:
        """Retorna a distância mínima (m) do obstáculo mais próximo na faixa válida, ou inf."""
        with self._lock:
            return self._obstacle_distance_m

    def _min_ignore_for_point(self, angle_deg: float) -> float:
        """Retorna o min_ignore em metros conforme zona (parachoques vs lateral)."""
        a = _norm_angle(angle_deg)
        lo, hi = self.parachoques_zone
        if lo <= a <= hi:
            return self.parachoques_min_ignore_m
        return self.min_ignore_m

    def _thread_run(self):
        """Entry point da thread: cria event loop e executa scan."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            self._run_async_scan(loop)
        finally:
            loop.close()

    def _run_async_scan(self, loop):
        """Executa o loop de scan assíncrono."""
        try:
            from rplidarc1.scanner import RPLidar
        except ImportError:
            try:
                from rplidarc1 import RPLidar
            except ImportError:
                logger.warning("rplidarc1 não instalado. Lidar C1 desativado.")
                return

        try:
            self._lidar = RPLidar(self.port, self.baud, timeout=0.2)
        except Exception as e:
            logger.warning("Não foi possível conectar ao C1 em %s: %s. Lidar desativado.", self.port, e)
            return

        try:
            _ = self._lidar.healthcheck()
            logger.info("Lidar C1 conectado.")
        except Exception:
            pass

        points = []
        last_angle = None

        async def consume():
            nonlocal points, last_angle
            while not self._stop_event.is_set():
                try:
                    data = await asyncio.wait_for(self._lidar.output_queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    if self._stop_event.is_set():
                        break
                    continue

                points.append(data)
                ang = data.get("a_deg", 0)

                # Via rápida: se ponto frontal está perto, atualiza imediatamente (parar mais eficiente)
                d_mm = data.get("d_mm") or 0
                if d_mm > 0 and _is_in_frontal_cone(ang, self.front_center, self.front_width):
                    min_ignore_mm = int(self._min_ignore_for_point(ang) * 1000)
                    if d_mm >= min_ignore_mm:
                        d_m = d_mm / 1000.0
                        if d_m < self.min_stop_m:
                            with self._lock:
                                if d_m < self._obstacle_distance_m or self._obstacle_distance_m == float("inf"):
                                    self._obstacle_distance_m = d_m

                if last_angle is not None and last_angle > 350 and ang < 10:
                    d_obst = self._process_scan_points(points)
                    with self._lock:
                        prev = self._obstacle_distance_m
                        if d_obst != float("inf"):
                            # Nova distância válida: atualiza e reseta contador
                            self._obstacle_distance_m = d_obst
                            self._consecutive_clear_scans = 0
                        else:
                            # Scan retornou "livre" — não sobrescrever imediatamente se há obstáculo detectado
                            # (corrige bug: varredura completa perdia lixeira e limpava via rápida)
                            if prev < self.min_stop_m:
                                self._consecutive_clear_scans += 1
                                if self._consecutive_clear_scans >= 2:
                                    self._obstacle_distance_m = float("inf")
                                    self._consecutive_clear_scans = 0
                                    logger.debug("Lidar C1: 2 scans consecutivos livres — desbloqueando.")
                            else:
                                self._obstacle_distance_m = float("inf")
                                self._consecutive_clear_scans = 0
                        if prev == 0.0:  # Primeiro scan após init
                            d_str = f"{d_obst:.2f} m" if d_obst != float("inf") else "livre (inf)"
                            logger.info("Lidar C1: primeiro scan OK — distância frontal = %s", d_str)
                    points = []

                last_angle = ang

        async def first_scan_timeout():
            """Se o 1º scan não completar em N s, desbloqueia (evita travamento eterno)."""
            await asyncio.sleep(FIRST_SCAN_TIMEOUT_SEC)
            with self._lock:
                if self._obstacle_distance_m == 0.0:
                    self._obstacle_distance_m = float("inf")
                    logger.warning(
                        "Lidar C1: 1º scan não completou em %.0f s — desbloqueando (distância=inf).",
                        FIRST_SCAN_TIMEOUT_SEC,
                    )

        async def main():
            t1 = asyncio.create_task(self._lidar.simple_scan())
            t2 = asyncio.create_task(consume())
            t3 = asyncio.create_task(first_scan_timeout())
            try:
                await asyncio.gather(t1, t2, t3)
            except asyncio.CancelledError:
                pass
            finally:
                self._lidar.stop_event.set()

        try:
            loop.run_until_complete(main())
        except Exception as e:
            logger.error("Erro no loop do Lidar C1: %s", e, exc_info=True)
        finally:
            try:
                if self._lidar:
                    self._lidar.stop_event.set()
                    self._lidar.reset()
                    self._lidar.shutdown()
            except Exception:
                pass
            self._lidar = None

    def _process_scan_points(self, points: list) -> float:
        """Processa pontos de uma varredura e retorna distância mínima (m) do obstáculo válido."""
        valid = [p for p in points if (p.get("d_mm") or 0) > 0]
        if not valid:
            return float("inf")

        obst_raw = [
            p for p in valid
            if _is_in_frontal_cone(p.get("a_deg", 0), self.front_center, self.front_width)
        ]

        obst = []
        for p in obst_raw:
            d_mm = p.get("d_mm") or 0
            min_ignore_mm = int(self._min_ignore_for_point(p.get("a_deg", 0)) * 1000)
            if d_mm >= min_ignore_mm:
                obst.append(p)

        if not obst:
            return float("inf")
        return min((p.get("d_mm") or 0) for p in obst) / 1000.0

    def start(self) -> bool:
        """Inicia a thread de leitura. Retorna True se iniciou com sucesso."""
        if self._running:
            return True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._thread_run, daemon=True)
        self._thread.start()
        self._running = True
        logger.info(
            "Lidar C1 ativo: cone %.0f° (centro %.0f°), parar se < %.2f m.",
            self.front_width, self.front_center, self.min_stop_m
        )
        return True

    def stop(self):
        """Para a thread de leitura e desconecta o sensor."""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        if self._lidar:
            try:
                self._lidar.stop_event.set()
                self._lidar.reset()
                self._lidar.shutdown()
            except Exception:
                pass
            self._lidar = None
        logger.info("Lidar C1 reader parado.")
