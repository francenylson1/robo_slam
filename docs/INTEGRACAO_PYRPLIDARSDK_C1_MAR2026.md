# Integração do pyrplidarsdk — RP Lidar C1 (Mar 2026)

## Visão geral

O **pyrplidarsdk** é um wrapper Python do SDK oficial SLAMTEC para RPLIDAR. Usa nanobind e o código C++ oficial, o que pode melhorar a estabilidade da detecção em comparação com a rplidarc1 (implementação comunitária em Python puro).

**Implementado em:** `src/core/lidar_c1_reader.py` — backend selecionável via `LIDAR_C1_BACKEND` em `config.py`.

---

## Passos para testar o pyrplidarsdk

### 1. Instalar o pyrplidarsdk

```bash
# Na Raspberry Pi
cd ~/robo_slam
source venv/bin/activate
pip install pyrplidarsdk
```

**Observação:** Na Raspberry Pi (aarch64), o PyPI pode não ter wheel pré-compilado. Se `pip install` falhar, será necessário compilar a partir do código-fonte:

```bash
# Dependências para compilação (Debian/Ubuntu)
sudo apt-get install -y build-essential cmake python3-dev

# Instalar do repositório
git clone --recursive https://github.com/dexmate-ai/pyrplidarsdk.git
cd pyrplidarsdk
pip install .

# Voltar ao projeto
cd ~/robo_slam
```

### 2. Configurar o backend

Edite `src/core/config.py`:

```python
# Trocar de "rplidarc1" para "pyrplidarsdk"
LIDAR_C1_BACKEND = "pyrplidarsdk"
```

### 3. Testar a navegação

```bash
python main.py
```

Verifique nos logs se aparece:

```
Lidar C1 conectado (pyrplidarsdk).
```

### 4. Voltar ao rplidarc1 (se necessário)

Se o pyrplidarsdk falhar ou não melhorar a detecção:

```python
# Em config.py
LIDAR_C1_BACKEND = "rplidarc1"
```

---

## Comparação dos backends

| Aspecto | rplidarc1 | pyrplidarsdk |
|--------|-----------|--------------|
| Protocolo | Implementação Python (terceiros) | SDK oficial C++ (SLAMTEC) |
| Instalação | `pip install rplidarc1` | `pip install pyrplidarsdk` (pode exigir build na Pi) |
| Baudrate C1 | 460800 ✓ | 460800 ✓ (via parâmetro) |
| API | Assíncrona (output_queue) | Síncrona (get_scan_data) |
| Shutdown | stop_event, reset, shutdown | stop_scan, disconnect |

---

## Possíveis erros e soluções

| Erro | Causa provável | Solução |
|------|----------------|---------|
| `ModuleNotFoundError: pyrplidarsdk` | Pacote não instalado | `pip install pyrplidarsdk` |
| Falha na compilação | Falta de build-essential, cmake | `sudo apt install build-essential cmake` |
| `Failed to connect` | Porta errada ou C1 ocupado | Verificar `/dev/ttyUSB0` e fechar outros programas que usem o C1 |
| Dados estranhos (ângulos/distâncias) | Unidades diferentes (rad vs deg, m vs mm) | O adaptador já converte; se persistir, conferir docs do pyrplidarsdk |

---

## Atualizar a Raspberry

```bash
cd ~/robo_slam
git pull origin robo_slam_2026_lidar_c1
source venv/bin/activate
pip install -r requirements.txt
```

Para testar o pyrplidarsdk: altere `LIDAR_C1_BACKEND` em `config.py` e rode `python main.py`.
