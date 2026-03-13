# Fase 2 — RP Lidar C1

## Objetivo

Integrar o sensor RP Lidar C1 (360°) para:
1. **Nível 1:** Detecção de obstáculos — parar antes de colidir
2. **Nível 2:** Localização — corrigir pose usando mapa do Aurora
3. **Nível 3:** SLAM (futuro)

## Teste isolado do C1

Antes de integrar na navegação, valide o sensor em modo isolado:

```bash
# Na Raspberry Pi, com o C1 conectado via USB:
python tools/teste_c1_isolado.py

# Opções:
python tools/teste_c1_isolado.py --port /dev/ttyUSB0   # porta padrão
python tools/teste_c1_isolado.py --baud 460800        # C1 pode usar 460800
python tools/teste_c1_isolado.py --scans 5            # apenas 5 varreduras
```

### O que o script exibe

- Informações do sensor (modelo, firmware, etc.)
- Saúde do sensor (Good/Warning/Error)
- Varreduras: quantidade de pontos, amostras (qualidade, ângulo°, distância mm)
- Obstáculo mais próximo em cada varredura

### Porta serial

No Raspberry Pi, o C1 geralmente aparece como:
- `/dev/ttyUSB0` (adaptador USB-serial)
- `/dev/ttyACM0` (dispositivo CDC)

Verifique com: `ls /dev/ttyUSB* /dev/ttyACM*`

### Permissões

Se aparecer "Permission denied":
```bash
sudo usermod -a -G dialout $USER
# Depois faça logout/login ou reinicie
```

## Atualização na Raspberry Pi

```bash
cd ~/robo_slam
git fetch --all
git checkout robo_slam_2026_lidar_c1
git pull origin robo_slam_2026_lidar_c1   # ou: git pull

# Instalar dependência do C1
source venv/bin/activate
pip install rplidar

# Testar o sensor
python tools/teste_c1_isolado.py
```

## Próximos passos (após validar o C1)

1. Integrar leitura do C1 em thread separada
2. Detectar obstáculos na direção do movimento
3. Parar o robô quando obstáculo < distância segura (ex: 0.35 m)
4. (Futuro) Fusão com odometria para localização
