#!/bin/bash
# Sobe as duas janelas de exibicao: rosto/7" em HDMI-A-1 e vitrine/15" em HDMI-A-2.
# Uso: lancar_telas.sh [url_7pol] [url_15pol]
export DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000

URL7="${1:-file:///home/amd/robo_slam/display/robot_face/alinhamento.html?pxcm=66.4&nome=TELA%207pol&ref=6}"
URL15="${2:-file:///home/amd/vitrine_teste/alinhamento.html?pxcm=55.8&nome=TELA%2015pol&ref=10}"

# IMPORTANTE: matar por padrao com colchetes E sem o literal na propria linha de comando,
# senao o pkill -f mata o proprio script.
PADRAO='chromium.*cr'"_"'(face|vitrine)'
pkill -f "$PADRAO" 2>/dev/null
sleep 2
rm -rf /tmp/cr_face /tmp/cr_vitrine

# A regra do labwc casa pelo instance name (derivado do caminho do arquivo) OU pela --class.
# O caminho do arquivo do 7" precisa conter robot_face e nao conter vitrine.
chromium --ozone-platform=x11 --class=robot_face --user-data-dir=/tmp/cr_face \
  --no-first-run --disable-infobars --window-position=0,0 --window-size=1024,600 \
  --app="$URL7" >/tmp/cr_face.log 2>&1 &
sleep 5
chromium --ozone-platform=x11 --class=vitrine --user-data-dir=/tmp/cr_vitrine \
  --no-first-run --disable-infobars --window-position=1024,0 --window-size=1080,1920 \
  --app="$URL15" >/tmp/cr_vitrine.log 2>&1 &
sleep 6
echo "janelas ativas: $(ps ax | grep -c '[c]hromium --ozone')"
