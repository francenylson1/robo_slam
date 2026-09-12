#!/bin/bash
# Instala o autostart da Vitrine nesta Raspberry. Idempotente: rode de novo apos cada git pull.
# NAO toca em nada especifico da maquina (rc.xml, kanshi, cmdline.txt, vitrine.db).
set -euo pipefail
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "== repositorio: $RAIZ"

echo; echo "== 1. Pre-requisitos =="
python3 -c "import flask" 2>/dev/null && echo "  Flask OK" || { echo "  ERRO: Flask ausente -> sudo apt install python3-flask"; exit 1; }
[ -f "$RAIZ/vitrine/app.py" ] || { echo "  ERRO: $RAIZ/vitrine/app.py nao existe"; exit 1; }
command -v chromium >/dev/null || echo "  AVISO: chromium nao esta no PATH"

echo; echo "== 2. Units systemd (symlink: git pull ja atualiza) =="
mkdir -p ~/.config/systemd/user
for u in vitrine-app vitrine-telas robo-teleop; do
  ln -sfn "$RAIZ/deploy/systemd/$u.service" ~/.config/systemd/user/$u.service
  echo "  $u.service -> repo"
done
systemctl --user daemon-reload

echo; echo "== 3. Gatilho da sessao grafica =="
mkdir -p ~/.config/autostart
sed "s|__HOME__|$HOME|g" "$RAIZ/deploy/autostart/vitrine-telas.desktop.modelo" > ~/.config/autostart/vitrine-telas.desktop
echo "  ~/.config/autostart/vitrine-telas.desktop gerado"

echo; echo "== 4. Habilitar =="
# Só o Flask sobe por target. As janelas sao disparadas pelo .desktop, dentro da sessao.
systemctl --user enable vitrine-app.service
sudo loginctl enable-linger "$(whoami)"
echo "  linger: $(loginctl show-user "$(whoami)" | grep -i '^Linger' || echo '?')"

echo; echo "== 5. O que NAO foi instalado (especifico desta maquina) =="
cat <<'AVISO'
  Conferir a mao, um a um -- copiar entre Pis quebra a maquina destino:
   - ~/.config/labwc/rc.xml     regras de janela; casam pelo INSTANCE NAME da URL
   - ~/.config/kanshi/config    qual tela em qual saida HDMI, rotacao e posicao
   - /boot/firmware/cmdline.txt remendo de video= para adaptador HDMI sem EDID
   - vitrine/vitrine.db         banco de slides: cada Pi semeia o seu (esta no .gitignore)
   - area segura (mr/mt/mb/ml) e pxmm: medir no painel DESTA tela, em /admin/config
AVISO

# A unit do teleop foi registrada, mas so sobe no boot se esta maquina pedir.
if [ -f "$HOME/.config/robo/teleop-no-boot" ]; then
  echo "  teleop no boot: LIGADO nesta maquina"
  # Sem esta regra o rosto vindo da porta 8765 abre com decoracao e fora de posicao:
  # o instance da URL e 127.0.0.1__index.html, que nao casa *robot_face*.
  if ! grep -q "__index.html" "$HOME/.config/labwc/rc.xml" 2>/dev/null; then
    echo "  !! FALTA no rc.xml a regra do rosto do teleop. Acrescente em <windowRules>:"
    echo '     <windowRule identifier="*__index.html*" serverDecoration="no">'
    echo '       <action name="MoveToOutput" output="HDMI-A-1"/>'
    echo '       <action name="ToggleFullscreen"/>'
    echo '     </windowRule>'
    echo "     (ajuste o output para a saida do 7\" NESTA maquina)"
  fi
else
  echo "  teleop no boot: desligado (para ligar: mkdir -p ~/.config/robo && touch ~/.config/robo/teleop-no-boot)"
fi

echo; echo "== Pronto. Verificar com: =="
echo "  systemctl --user status vitrine-app"
echo "  systemctl --user start vitrine-telas   # ou reiniciar a Pi para testar o boot"
