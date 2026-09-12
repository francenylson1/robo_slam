#!/bin/bash
# Disparado pelo XDG autostart da sessao labwc (~/.config/autostart/vitrine-telas.desktop),
# que o /etc/xdg/labwc/autostart processa via lxsession-xdg-autostart.
#
# Por que nao graphical-session.target: no labwc esse target fica inactive (verificado
# em 2026-09-12 na .179 e na .199), entao uma unit habilitada nele nunca dispara no boot.
# Por que NAO criar ~/.config/labwc/autostart: o arquivo do usuario SUBSTITUI o global,
# derrubando wf-panel-pi, pcmanfm e kanshi -- e o kanshi e quem posiciona as duas telas.

# Sem isto o systemd --user nao conhece DISPLAY/XAUTHORITY e o Chromium nao acha a tela.
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XDG_RUNTIME_DIR XDG_SESSION_TYPE XAUTHORITY

PORTA_ROSTO="${ROBO_FACE_HTTP_PORT:-8765}"

# Teleop no boot e OPT-IN por maquina: nem toda Pi da frota tem joystick e motores,
# e algumas sao so vitrine. Para ligar nesta maquina:
#   mkdir -p ~/.config/robo && touch ~/.config/robo/teleop-no-boot
# Os motores nascem DESARMADOS ate o SELECT no joystick, entao subir no boot nao
# faz o robo se mover.
if [ -f "$HOME/.config/robo/teleop-no-boot" ]; then
  systemctl --user start --no-block robo-teleop.service
  # Espera o rosto do teleop responder, para o lancar_telas.sh apontar a janela do
  # 7" para ele em vez do arquivo estatico. Se nao subir, segue com o estatico.
  for _ in $(seq 1 25); do
    curl -sf -o /dev/null --max-time 1 "http://127.0.0.1:${PORTA_ROSTO}/index.html" && break
    sleep 1
  done
fi

# --no-block: nao travar a sessao grafica enquanto o ExecStartPre espera o Flask.
exec systemctl --user start --no-block vitrine-telas.service
