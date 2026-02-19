# Teste do IMU BNO08x (BNO085/BNO080)

Fiação usada no projeto:
- **I2C:** SDA, SCL (e alimentação 3V3, GND)
- **GPIO 26:** RST (reset)
- **GPIO 27:** INT (interrupto – uso futuro)

## Pré-requisitos na Raspberry Pi

1. **Habilitar I2C**
   ```bash
   sudo raspi-config
   # Interface Options → I2C → Enable
   sudo reboot
   ```

2. **Opcional:** aumentar baudrate do I2C para 400 kHz (recomendado pelo fabricante)
   - Editar `/boot/config.txt` e adicionar: `dtparam=i2c_arm_baudrate=400000`
   - Reiniciar.

3. **Instalar dependências**
   ```bash
   cd ~/robo_slam
   pip install adafruit-blinka adafruit-circuitpython-bno08x
   # Se der erro "No Hardware I2C on (scl,sda)=(3, 2)", instale também:
   pip install adafruit-extended-bus
   # ou: pip install -r requirements.txt
   ```

## Executar o teste

Na raiz do projeto (`~/robo_slam`):

```bash
# Leitura contínua (acelerômetro, giro, yaw/pitch/roll)
python tools/bno08x_test.py

# Calibração (deixe o sensor parado e em superfície plana por 10–30 s)
python tools/bno08x_test.py --calibrate
```

## Calibração

- Se o status de calibração for &lt; 3, execute `--calibrate` com o sensor **parado e plano**.
- A calibração melhora a precisão do ângulo (yaw/pitch/roll) e do acelerômetro/giro.
- O BNO08x pode guardar calibração em memória não volátil (depende do modelo).

## Erro "No Hardware I2C on (scl,sda)=(3, 2)"

Em alguns Raspberry (ex.: Pi 5 ou certas versões do Blinka), o I2C com `board.SCL`/`board.SDA` falha. O script tenta, em ordem:
1. Pinagem explícita D3 (SCL) e D2 (SDA)
2. `board.I2C()`
3. **ExtendedI2C(1)** – abre `/dev/i2c-1` diretamente

Instale e rode de novo:
```bash
pip install adafruit-extended-bus
python tools/bno08x_test.py
```

## Configuração

Pinos e endereço I2C estão em `src/core/config.py`:
- `BNO08X_GPIO_RST`, `BNO08X_GPIO_INT`, `BNO08X_I2C_ADDRESS`
