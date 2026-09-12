# Operação no dia do evento

Como alcançar e controlar cada robô da rede, o que fazer quando algo não sobe, e o que
**não** fazer com um robô fechado.

Para montar uma Raspberry nova, veja o [README.md](README.md) deste diretório.

---

## As cinco máquinas

| IP | Nome de rede | Placa | Painel de anúncios | Observação própria |
|---|---|---|---|---|
| `192.168.0.179` | `raspberry-179.local` | Pi 5 | `http://192.168.0.179:8080/admin` | **Bancada / desenvolvimento** |
| `192.168.0.199` | `raspberry-199.local` | Pi 5 | `http://192.168.0.199:8080/admin` | Fechado |
| `192.168.0.123` | `raspberry-123.local` | Pi 5 | `http://192.168.0.123:8080/admin` | Fechado. Única com remendo de vídeo |
| `192.168.0.185` | `raspberry-185.local` | Pi 5 | `http://192.168.0.185:8080/admin` | Fechado |
| `192.168.0.221` | `raspberry-221.local` | **Pi 4** | `http://192.168.0.221:8080/admin` | Fechado. Única Pi 4 da frota |

Cada robô se identifica na tela como **Robô 179**, **Robô 199**, **Robô 123**,
**Robô 185** e **Robô 221** — o número é o final do IP.

### MACs para reserva de DHCP no roteador

Os IPs acima são **dinâmicos** enquanto a reserva não for feita. Reservar é o que garante
achar cada robô sempre no mesmo endereço.

| Máquina | Wi-Fi (`wlan0`) | Cabo (`eth0`) |
|---|---|---|
| .179 | `88:a2:9e:74:3d:ca` | `88:a2:9e:74:3d:c9` |
| .199 | `88:a2:9e:74:3c:61` | `88:a2:9e:74:3c:60` |
| .123 | `88:a2:9e:74:3e:61` | `88:a2:9e:74:3e:60` |
| .185 | `88:a2:9e:74:3d:d0` | `88:a2:9e:74:3d:cf` |
| .221 | `dc:a6:32:7b:c7:ad` | `dc:a6:32:7b:c7:aa` |

Todos os robôs estão conectados por **Wi-Fi** (`wlan0`) — use essa coluna.

---

## Acesso

### Painel de anúncios, do celular

Não precisa de terminal. Abra no navegador:

```
http://192.168.0.199:8080/admin
```

De lá você cadastra e edita slides, e em **Configurações** ajusta o nome do robô e as
margens da tela. Ao salvar, **a tela do robô se atualiza sozinha em até 5 segundos** — não
precisa reiniciar nada.

O carrossel em si, se quiser ver no navegador: `http://192.168.0.199:8080/signage`

### Terminal

```bash
ssh amd@raspberry-199.local     # pelo nome
ssh amd@192.168.0.199           # pelo IP, sempre funciona
```

Entra sem senha (chave já instalada na máquina de desenvolvimento).

> **Nos primeiros ~3 minutos depois de ligar, o nome `.local` pode não funcionar.** O
> robô pode anunciar um número incrementado (`raspberry-200`) até um timer corrigir. **Se
> tiver pressa, use o IP.**

### Achar um robô cujo IP você não sabe

```bash
for i in $(seq 1 254); do (ping -c1 -W1 192.168.0.$i >/dev/null 2>&1 && echo 192.168.0.$i) & done; wait
```

Os robôs são os que respondem na porta 22 **e** na 8080.

---

## Comandos do dia

Rode dentro do robô, depois do `ssh`.

### Está tudo no ar?

```bash
systemctl --user is-active vitrine-app vitrine-telas robo-teleop
```

Espera-se **`active`** três vezes:

| Serviço | O que é |
|---|---|
| `vitrine-app` | O servidor dos anúncios (porta 8080) |
| `vitrine-telas` | As duas janelas: rosto no 7" e carrossel no 15" |
| `robo-teleop` | O rosto que reage ao joystick e o controle dos motores |

### As telas travaram ou estão na tela errada

```bash
systemctl --user restart vitrine-telas
```

Fecha e reabre as duas janelas, cada uma na sua tela. Leva ~20 segundos.

### Os anúncios não atualizam

```bash
systemctl --user restart vitrine-app && sleep 5 && systemctl --user restart vitrine-telas
```

### O joystick não responde

Primeiro, o mais comum: **os motores começam desarmados de propósito.** Aperte
**SELECT** no joystick para armar. O robô não anda antes disso — é proteção, não defeito.

Se mesmo assim não responder:

```bash
ls /dev/input/js0                      # o joystick está conectado?
systemctl --user restart robo-teleop   # reinicia o controle
```

### Reiniciar o robô inteiro

```bash
sudo reboot
```

Volta sozinho em ~40 segundos, com tudo subindo automaticamente.

---

## Quando algo dá errado

### As duas telas estão apagadas ou em preto

1. `systemctl --user is-active vitrine-telas` — se não estiver `active`, reinicie-o.
2. Se estiver `active` e as telas continuarem vazias, veja se o Chromium reclamou:
   ```bash
   tail -5 /tmp/cr_face.log /tmp/cr_vitrine.log
   ```
   Se aparecer **`Authorization required`**, é a autorização do X. Um `sudo reboot`
   resolve (o launcher se conserta sozinho no boot).

### O robô não aparece na rede

Vá pelo IP em vez do nome. Se o IP também não responder, o problema é elétrico, não de
software — veja a seção seguinte.

### A Raspberry está com a luz vermelha acesa e não liga

**A luz vermelha é a de alimentação e fica acesa em operação normal — ela não indica
erro.** Quem mostra atividade é a **verde**, que pisca ao ler o cartão.

- **Vermelha acesa + verde apagada** = tem energia, mas não está inicializando.
- Na Pi 5 isso é o estado de *standby*: ela espera o **botão de power** (ao lado do
  conector USB-C) ou o corte e retorno da alimentação.
- Se a verde nunca piscar em nenhuma tentativa: cartão SD mal encaixado, ou corrente
  insuficiente na alimentação (medir os 5 V **durante** a tentativa de ligar, não em
  repouso).

**Não existe reset remoto de uma Raspberry.** Sem rede, não há caminho por software: o
SSH precisa dela respondendo, e não há controlador de gerenciamento independente. O
caminho é sempre físico.

### Se travar sozinho

Cada robô tem **watchdog de hardware**: se o sistema congelar, ele reinicia em 15
segundos, sem ninguém intervir.

---

## O que NÃO fazer

**Nunca `sudo shutdown` num robô fechado.** Depois de um shutdown a Pi 5 fica em standby
com a luz vermelha acesa e **não volta sozinha** — exige o botão físico ou desligar a
alimentação. Com o robô montado, isso vira um problema difícil. Use sempre:

```bash
sudo reboot
```

**Nunca copiar arquivos de configuração de um robô para outro.** Parecem configuração do
projeto, mas são do hardware daquela máquina:

- `~/.config/kanshi/config` — qual tela está em qual saída HDMI, e a rotação
- `~/.config/labwc/rc.xml` — as regras que põem cada janela na sua tela
- `/boot/firmware/cmdline.txt` — **só a `.123`** precisa do remendo de vídeo; aplicar nas
  outras piora a imagem
- `vitrine/vitrine.db` — os anúncios são de cada robô; copiar sobrescreve os de outro

**Não editar a área segura de um robô com base na medida de outro.** Todos herdaram os
20 mm da `.179`, mas o que define o corte é o acabamento frontal de *cada* robô.

---

## Atualizar os cinco robôs

O repositório é público: `git pull` funciona sem senha nem token.

```bash
cd ~/robo_slam && git pull && ./deploy/instalar.sh && sudo reboot
```

O instalador é seguro de rodar quantas vezes quiser, e **não toca** em nada específico da
máquina (configs de tela e banco de anúncios ficam intactos).

### Ligar ou desligar o teleop num robô

```bash
mkdir -p ~/.config/robo && touch ~/.config/robo/teleop-no-boot   # liga
rm ~/.config/robo/teleop-no-boot                                 # desliga
sudo reboot
```

Com o teleop desligado, o robô mostra o rosto fixo e a vitrine, sem controle de motores.

---

## Checagem rápida antes do evento

Da máquina de desenvolvimento, com todos os robôs ligados:

```bash
for ip in 179 199 123 185 221; do
  printf "robô %s: " "$ip"
  ssh -o ConnectTimeout=5 amd@192.168.0.$ip \
    'systemctl --user is-active vitrine-app vitrine-telas robo-teleop | tr "\n" " "' \
    2>/dev/null || echo "NÃO RESPONDE"
  echo
done
```

Cada linha deve terminar com **`active active active`**.

Depois, em cada robô, confirme o que só o olho vê: o **rosto em tela cheia** no 7", o
**carrossel girando** no 15", e o **SELECT no joystick** movendo o robô.
