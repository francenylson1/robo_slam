# deploy/ — levar o robô para outra Raspberry

Tudo aqui é **igual em todas as máquinas**. O que é específico de cada Pi ficou
deliberadamente fora: `rc.xml`, `kanshi/config`, `cmdline.txt`, `vitrine.db`,
uploads e a área segura da tela.

## Ordem de execução numa Pi nova

```bash
cd ~/robo_slam && git pull
./deploy/inventario_pi.sh > /tmp/inv.txt   # 1. o que esta maquina tem
./deploy/instalar.sh                       # 2. units, autostart, linger
./deploy/preparar_acesso.sh                # 3. SSH, mDNS, watchdog, journal
sudo reboot                                # 4. o unico teste que vale
```

## Por que cada peça existe

| Peça | Existe porque |
|---|---|
| `systemd/vitrine-app.service` | o Flask não subia no boot; usa `%h` para não amarrar `/home/amd` |
| `systemd/vitrine-telas.service` | as janelas não subiam; `oneshot` + `RemainAfterExit` porque o launcher termina e as janelas ficam |
| `bin/aguardar_vitrine.sh` | sem esperar o `/api/versao`, a janela abre em porta morta; é script porque o systemd expande `$` na unit |
| `bin/iniciar_telas_sessao.sh` | no labwc `graphical-session.target` fica **inactive**, então a unit precisa ser disparada pelo XDG autostart |
| `autostart/*.desktop.modelo` | `~/.config/labwc/autostart` **substituiria** o global e derrubaria `wf-panel-pi`, `pcmanfm` e o `kanshi` |
| `preparar_acesso.sh` | com o robô fechado, perder o SSH custa desmontar; watchdog + mDNS + chave são o seguro |

## O que NÃO copiar entre máquinas

- `~/.config/kanshi/config` — qual tela em qual saída HDMI, rotação e posição.
- `~/.config/labwc/rc.xml` — regras casam pelo **instance name** derivado da URL.
  Ao trocar uma URL, confira se ainda casa alguma regra.
- `/boot/firmware/cmdline.txt` — o `video=HDMI-A-2:1920x1080@60D` é remendo para um
  adaptador HDMI que não entregava EDID. Onde o EDID é lido, **não aplicar**.
- `vitrine/vitrine.db` e `vitrine/static/uploads/` — no `.gitignore`; cada Pi semeia o seu.
- Área segura (`mr/mt/mb/ml`) e `pxmm` — medir no painel daquela tela, em `/admin/config`.
