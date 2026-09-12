#!/bin/bash
# Sobe as janelas de exibicao: rosto/7" em HDMI-A-1 e vitrine/15" em HDMI-A-2.
# Uso: lancar_telas.sh [url_7pol] [url_15pol]
#
# Restricoes de Wayland/labwc que moldam este script (custaram varias tentativas):
#  1. --ozone-platform=x11 e obrigatorio: em Wayland nativo o Chromium ignora
#     --window-position silenciosamente. Sob XWayland as duas telas viram um
#     desktop unico e o posicionamento funciona.
#  2. --kiosk e --start-fullscreen SOBREPOEM a posicao e sempre abrem na tela
#     primaria. Nao usar. Tela cheia sem decoracao vem de regra do labwc.
#  3. A regra do labwc casa pelo INSTANCE NAME (derivado da URL/caminho), nao pelo
#     titulo. Ao trocar uma URL, conferir se o instance ainda casa alguma regra
#     em ~/.config/labwc/rc.xml.
export DISPLAY="${DISPLAY:-:0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
# XAUTHORITY e obrigatorio onde o XWayland sobe com -auth (caso da .199): sem o
# cookie o Chromium morre com "Authorization required" e nenhuma janela abre.
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PORTA="${ROBO_VITRINE_PORT:-8080}"

URL7="${1:-file://${RAIZ}/display/robot_face/index.html}"
URL15="${2:-http://127.0.0.1:${PORTA}/signage}"

# IMPORTANTE: o padrao e montado por concatenacao para o pkill -f nao casar a
# propria linha de comando deste script e se matar antes de relancar.
PADRAO='chromium.*cr'"_"'(face|vitrine)'
pkill -f "$PADRAO" 2>/dev/null
sleep 2
rm -rf /tmp/cr_face /tmp/cr_vitrine

lancar() { # $1=perfil  $2=classe  $3=posicao  $4=tamanho  $5=url
  chromium --ozone-platform=x11 --class="$2" --user-data-dir="/tmp/cr_$1" \
    --no-first-run --disable-infobars \
    --window-position="$3" --window-size="$4" \
    --app="$5" >"/tmp/cr_$1.log" 2>&1 &
}

# So abre o rosto se a saida do 7" tiver tela conectada.
if [ -z "$ROBO_SEM_ROSTO" ]; then
  lancar face robot_face 0,0 1024,600 "$URL7"
  sleep 5
fi
lancar vitrine vitrine 1024,0 1080,1920 "$URL15"
sleep 6
echo "janelas ativas: $(pgrep -fc 'user-data-dir=/tmp/cr')"
