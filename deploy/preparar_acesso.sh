#!/bin/bash
# RODAR ANTES DE FECHAR O ROBO. Garante que a Pi continue alcancavel quando nao houver
# mais acesso facil ao hardware. Cada passo e idempotente.
set -uo pipefail
echo "########## PREPARAR ACESSO -- $(hostname) ##########"

echo; echo "== 1. SSH habilitado e ativo =="
sudo systemctl enable --now ssh
systemctl is-active ssh

echo; echo "== 2. Nome mDNS: achar a Pi mesmo se o IP mudar =="
if ! command -v avahi-daemon >/dev/null; then
  sudo apt-get install -y avahi-daemon || echo "  AVISO: instale avahi-daemon com rede disponivel"
fi
sudo systemctl enable --now avahi-daemon 2>/dev/null
echo "  a partir de outra maquina da rede: ssh $(whoami)@$(hostname).local"

echo; echo "== 3. Chave publica da maquina de desenvolvimento =="
if [ -s ~/.ssh/authorized_keys ]; then
  echo "  $(wc -l < ~/.ssh/authorized_keys) chave(s) autorizada(s) -- login sem senha OK"
else
  echo "  !! SEM CHAVE AUTORIZADA. Rode ISTO NA MAQUINA DE DESENVOLVIMENTO, antes de fechar:"
  echo "     ssh-copy-id $(whoami)@$(hostname -I | awk '{print $1}')"
fi

echo; echo "== 4. Watchdog de hardware: reinicia sozinha se o kernel travar =="
# Critico num robo fechado: sem isso um travamento exige acesso fisico ao botao.
if [ -e /dev/watchdog ]; then
  if ! grep -qE "^RuntimeWatchdogSec=" /etc/systemd/system.conf; then
    sudo cp /etc/systemd/system.conf /etc/systemd/system.conf.antes-watchdog
    sudo sed -i 's/^#*RuntimeWatchdogSec=.*/RuntimeWatchdogSec=15s/' /etc/systemd/system.conf
    grep -qE "^RuntimeWatchdogSec=" /etc/systemd/system.conf || echo "RuntimeWatchdogSec=15s" | sudo tee -a /etc/systemd/system.conf >/dev/null
    sudo systemctl daemon-reexec
    echo "  ativado: RuntimeWatchdogSec=15s (backup em system.conf.antes-watchdog)"
  else
    echo "  ja configurado: $(grep -E '^RuntimeWatchdogSec=' /etc/systemd/system.conf)"
  fi
else
  echo "  AVISO: /dev/watchdog ausente. Adicione 'dtparam=watchdog=on' em /boot/firmware/config.txt e reinicie."
fi

echo; echo "== 5. Journal persistente: sobreviver ao proximo travamento com log =="
if [ ! -d /var/log/journal ]; then
  sudo mkdir -p /var/log/journal
  sudo systemd-tmpfiles --create --prefix /var/log/journal
  sudo systemctl kill --kill-who=main --signal=SIGUSR1 systemd-journald
  echo "  ativado"
else
  echo "  ja era persistente ($(journalctl --list-boots 2>/dev/null | wc -l) boots gravados)"
fi

echo; echo "== 6. Dados para a reserva de DHCP no roteador =="
ip -o link show | awk '/link\/ether/ {print "  "$2" "$17}' | sed 's/://1'
echo "  IP atual: $(hostname -I)"
echo "  >> Reserve esse MAC no roteador para o IP fixo desejado (ex.: 192.168.0.199)."

echo; echo "== 7. TESTE DE FOGO -- nao feche o robo sem isso =="
cat <<'TESTE'
  Reinicie a Pi 3 vezes (sudo reboot) e, a cada volta, confirme DA OUTRA MAQUINA:
    1. ping <hostname>.local            -> responde
    2. ssh amd@<hostname>.local         -> entra sem senha
    3. as duas telas acendem com rosto e carrossel, na tela certa
    4. systemctl --user is-active vitrine-app vitrine-telas  -> active / active
  Se qualquer um falhar, resolva ANTES de fechar. Depois de fechado, o custo muda.
TESTE
echo; echo "########## FIM ##########"
