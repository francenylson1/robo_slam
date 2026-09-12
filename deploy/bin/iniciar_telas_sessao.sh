#!/bin/bash
# Disparado pelo XDG autostart da sessao labwc (~/.config/autostart/vitrine-telas.desktop),
# que o /etc/xdg/labwc/autostart processa via lxsession-xdg-autostart.
#
# Por que nao graphical-session.target: no labwc esse target fica inactive (verificado
# em 2026-09-12 na .179), entao uma unit habilitada nele nunca dispara no boot.
# Por que NAO criar ~/.config/labwc/autostart: o arquivo do usuario SUBSTITUI o global,
# derrubando wf-panel-pi, pcmanfm e kanshi -- e o kanshi e quem posiciona as duas telas.
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XDG_RUNTIME_DIR XDG_SESSION_TYPE XAUTHORITY
# --no-block: nao travar a sessao grafica enquanto o ExecStartPre espera o Flask.
exec systemctl --user start --no-block vitrine-telas.service
