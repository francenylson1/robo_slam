#!/bin/bash
# Padroniza o hostname desta Pi como raspberry-<ultimo octeto do IP>, para o acesso
# por mDNS (nome.local) funcionar quando o robo estiver fechado e o IP mudar.
#
# Por que hifen e nao underscore: hostname com "_" nao e valido em DNS (RFC 1123) e
# varias resolucoes falham em silencio -- justamente o acesso que queremos garantir.
#
# Cuidado que este script resolve: o cookie do X fica registrado como
# <hostname>/unix:0. Renomear a maquina com a sessao grafica no ar deixa o cookie
# orfao e as janelas param de abrir (units "active", telas vazias). Por isso, ao
# renomear, ele ja acrescenta a entrada do nome novo.
set -uo pipefail

IP=$(hostname -I | awk '{print $1}')
OCT=${IP##*.}
NOVO="${1:-raspberry-$OCT}"
ANTIGO=$(hostname)

if [ "$NOVO" = "$ANTIGO" ]; then
  echo "hostname ja e $NOVO -- nada a fazer"
else
  echo "renomeando: $ANTIGO -> $NOVO  (IP $IP)"
  sudo hostnamectl set-hostname "$NOVO"
  # sem atualizar o /etc/hosts o sudo fica lento com "unable to resolve host"
  sudo sed -i "s/\b${ANTIGO}\b/${NOVO}/g" /etc/hosts
  sudo systemctl restart avahi-daemon
  echo "hostname agora: $(hostname)"
fi

# Fixa o nome no avahi. SEM isto o avahi, ao ver o registro antigo ainda vivo na
# rede (o cache dura ~2 min apos um reboot), considera o nome ocupado e se renomeia
# sozinho INCREMENTANDO o numero: raspberry-179 vira raspberry-180.local. O nome que
# voce anotou para alcancar o robo fechado deixa de existir em silencio -- e pode
# colidir com a Pi que de fato tiver aquele IP. Aconteceu na .179 em 2026-09-12.
CONF=/etc/avahi/avahi-daemon.conf
if [ -f "$CONF" ]; then
  [ -f "$CONF.antes-hostname-fixo" ] || sudo cp "$CONF" "$CONF.antes-hostname-fixo"
  if grep -qE "^host-name=" "$CONF"; then
    sudo sed -i "s/^host-name=.*/host-name=$(hostname)/" "$CONF"
  else
    sudo sed -i "s/^\[server\]/[server]\nhost-name=$(hostname)/" "$CONF"
  fi
  sudo systemctl restart avahi-daemon
  sleep 3
  PUBLICADO=$(journalctl -u avahi-daemon -b --no-pager 2>/dev/null | grep -i "Host name is" | tail -1 | grep -oE "[^ ]+\.local")
  echo "avahi publica: ${PUBLICADO:-?}  (esperado: $(hostname).local)"
fi

# Reaproveita o cookie do X para o nome atual, se a sessao grafica estiver no ar.
X="${XAUTHORITY:-$HOME/.Xauthority}"
if command -v xauth >/dev/null 2>&1 && [ -f "$X" ]; then
  if xauth -f "$X" list 2>/dev/null | grep -q "^$(hostname)/unix:0"; then
    echo "xauth: entrada para $(hostname) ja existe"
  else
    COOKIE=$(xauth -f "$X" list 2>/dev/null | awk '$2=="MIT-MAGIC-COOKIE-1"{print $3; exit}')
    if [ -n "$COOKIE" ]; then
      xauth -f "$X" add "$(hostname)/unix:0" MIT-MAGIC-COOKIE-1 "$COOKIE" \
        && echo "xauth: entrada criada para $(hostname)/unix:0"
    fi
  fi
fi

echo
echo ">> Da maquina de desenvolvimento, confirme:  ssh amd@$(hostname).local hostname"
echo ">> E reserve este MAC no roteador para o IP $IP:"
ip -o link show | awk '/link\/ether/ {print "     "$2" "$17}' | sed 's/://1'
