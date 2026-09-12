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
for u in vitrine-app vitrine-telas; do
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

echo; echo "== Pronto. Verificar com: =="
echo "  systemctl --user status vitrine-app"
echo "  systemctl --user start vitrine-telas   # ou reiniciar a Pi para testar o boot"
