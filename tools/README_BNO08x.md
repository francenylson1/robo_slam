# Teste do IMU BNO08x (BNO085/BNO080)

Fiação usada no projeto:
- **I2C:** SDA, SCL (e alimentação 3V3, GND)
- **GPIO 27:** INT (interrupto – opcional, uso futuro)
- **RST (GPIO 26):** o script coloca em HIGH no início para o sensor sair do reset (evita "device not found" e dispensa `raspi-gpio set 26 op dh`). O pino não é passado à biblioteca (evita ruído).

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

## "No I2C device at address: 0x4a"

O script faz **varredura I2C** (lista dispositivos no barramento) e tenta **0x4A e 0x4B**. (RST não é usado no nosso setup.)

- Se a varredura **não mostrar nenhum endereço**: confira alimentação (3V3, GND), SDA e SCL. PS0/PS1 do BNO08x devem estar no nível correto para modo I2C.
- Se mostrar outro endereço (ex.: 0x4B): o script tenta 0x4B automaticamente. Em `config.py` você pode fixar `BNO08X_I2C_ADDRESS = 0x4B` se o seu módulo for BNO080 ou tiver o jumper ADR.
- No nosso projeto **RST não é usado** (desconectado por ruído). Para resetar o sensor, desligue e ligue a alimentação (3V3).

## Sobre as mensagens "Erro na leitura" e dump de pacotes (DBG::)

- **Bloco "Packet / DBG::"**: era saída de debug da biblioteca (pacotes SHTP). O script agora usa `debug=False` para não imprimir isso.
- **"Erro na leitura: 255", "0", "Input/output error", "Unprocessable Batch bytes"**: o BNO08x envia vários tipos de pacote (dados de sensor, timestamp, metadados). Às vezes a biblioteca lê um pacote que não é acelerômetro/giro/quaternion e gera exceção; a próxima leitura volta ao normal. Isso é **normal** em I2C com BNO08x. O script ignora essas leituras e segue; se quiser menos avisos, eles aparecem só de 5 em 5.

## Configuração

Pinos e endereço I2C estão em `src/core/config.py`:
- `BNO08X_GPIO_RST = None` (não usado), `BNO08X_GPIO_INT`, `BNO08X_I2C_ADDRESS`
