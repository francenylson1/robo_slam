# deploy/ — levar o robô para outra Raspberry

> **Para operar os robôs no dia do evento** — endereços, acessos, o que fazer quando algo
> não sobe e o que não fazer com um robô fechado — veja [OPERACAO.md](OPERACAO.md).

Tudo aqui é **igual em todas as máquinas**. O que é específico de cada Pi ficou
deliberadamente fora: `rc.xml`, `kanshi/config`, `cmdline.txt`, `vitrine.db`,
uploads e a área segura da tela.

## Ordem de execução numa Pi nova

Antes de tudo, **da maquina de desenvolvimento**, autorize a chave (pede a senha
da Pi uma unica vez):

```bash
ssh-copy-id amd@<ip-da-pi>
```

Depois, **na Pi**:

```bash
cd ~/robo_slam && git pull
./deploy/inventario_pi.sh > /tmp/inv.txt   # 1. o que esta maquina tem
./deploy/nomear_maquina.sh                 # 2. hostname raspberry-<octeto> + xauth
./deploy/instalar.sh                       # 3. units, autostart, linger
./deploy/preparar_acesso.sh                # 4. SSH, mDNS, watchdog, journal
sudo reboot                                # 5. o unico teste que vale
```

Depois do reboot, confirme **da outra maquina**: `ssh amd@raspberry-<octeto>.local`
entra sem senha, e `systemctl --user is-active vitrine-app vitrine-telas` devolve
`active` nas duas.

O que ainda e manual em cada Pi, porque depende do hardware dela: escrever o
`kanshi/config` e o `rc.xml` conforme **qual tela esta em qual saida HDMI**, medir a
area segura do painel em `/admin/config`, e reservar o MAC no roteador.

## Por que cada peça existe

| Peça | Existe porque |
|---|---|
| `systemd/vitrine-app.service` | o Flask não subia no boot; usa `%h` para não amarrar `/home/amd` |
| `systemd/vitrine-telas.service` | as janelas não subiam; `oneshot` + `RemainAfterExit` porque o launcher termina e as janelas ficam |
| `bin/aguardar_vitrine.sh` | sem esperar o `/api/versao`, a janela abre em porta morta; é script porque o systemd expande `$` na unit |
| `bin/iniciar_telas_sessao.sh` | no labwc `graphical-session.target` fica **inactive**, então a unit precisa ser disparada pelo XDG autostart |
| `autostart/*.desktop.modelo` | `~/.config/labwc/autostart` **substituiria** o global e derrubaria `wf-panel-pi`, `pcmanfm` e o `kanshi` |
| `preparar_acesso.sh` | com o robô fechado, perder o SSH custa desmontar; watchdog + mDNS + chave são o seguro |
| `nomear_maquina.sh` | padroniza `raspberry-<octeto>` para o mDNS, e recria a entrada `xauth` que a renomeação deixa órfã |

## O que NÃO copiar entre máquinas

- `~/.config/kanshi/config` — qual tela em qual saída HDMI, rotação e posição.
- `~/.config/labwc/rc.xml` — regras casam pelo **instance name** derivado da URL.
  Ao trocar uma URL, confira se ainda casa alguma regra.
- `/boot/firmware/cmdline.txt` — o `video=HDMI-A-2:1920x1080@60D` é remendo para um
  adaptador HDMI que não entregava EDID. Onde o EDID é lido, **não aplicar**.
- `vitrine/vitrine.db` e `vitrine/static/uploads/` — no `.gitignore`; cada Pi semeia o seu.
- Área segura (`mr/mt/mb/ml`) e `pxmm` — medir no painel daquela tela, em `/admin/config`.

## Teleop no boot (opt-in por maquina)

Nem toda Pi da frota tem joystick e motores, entao subir o teleop no boot e opcional:

```bash
mkdir -p ~/.config/robo && touch ~/.config/robo/teleop-no-boot
```

Com o marcador presente, a sessao grafica sobe `robo-teleop.service` antes das telas,
espera o rosto responder na porta 8765 e so entao abre as janelas — assim a janela do
7" aponta para o rosto **do teleop** (que reage ao joystick) em vez do arquivo
estatico. Sem o marcador, nada muda.

**Os motores nascem desarmados ate o SELECT** no joystick (`--arm-start` e opt-in),
por isso subir no boot nao faz o robo se mover.

### O que isso exige do rc.xml daquela maquina

A janela do rosto passa a vir de `http://127.0.0.1:8765/index.html`, e o instance que
o Chromium deriva dessa URL e `127.0.0.1__index.html` — que **nao** casa
`*robot_face*`. Sem uma regra para ele, a janela abre com decoracao e fora de lugar
(medido: 1023x599 em 0,62 em vez de 1024x600 em 0,0). Acrescente ao `rc.xml`:

```xml
<windowRule identifier="*__index.html*" serverDecoration="no">
  <action name="MoveToOutput" output="HDMI-A-1"/>
  <action name="ToggleFullscreen"/>
</windowRule>
```

Ajuste o `output` para a saida onde esta o 7" **naquela** maquina.

**Cuidado ao editar o rc.xml:** `--` nao e permitido dentro de comentario XML. Um
arquivo invalido e rejeitado em silencio e as janelas caem na tela errada. Validar com
`python3 -c 'import xml.dom.minidom; xml.dom.minidom.parse("/home/amd/.config/labwc/rc.xml")'`
antes do `kill -HUP $(pidof labwc)`.

### Como o main.py continua funcionando

`python3 src/main.py` **sem argumentos abre o dialogo de escolha de modo como sempre**.
O `--mode semi-teleop` existe so para o autostart, que nao tem quem clique. E o
`ROBO_TELEOP_NO_CHROMIUM=1`, definido apenas pela unit, evita o segundo Chromium em
`--kiosk` que brigaria pela tela primaria. Nada disso muda o uso manual.
