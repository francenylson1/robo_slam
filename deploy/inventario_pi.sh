#!/bin/bash
# Inventario de uma Raspberry da frota do robo garcom.
# Rodar EM CADA Pi (a .179 de referencia e a .199 nova) e comparar as saidas.
# Somente leitura: nao altera nada.
echo "########## INVENTARIO $(hostname) $(date -Is) ##########"

echo; echo "===== 1. MAQUINA ====="
cat /proc/device-tree/model 2>/dev/null | tr -d '\0'; echo
echo "usuario: $(whoami)  home: $HOME"
echo "kernel: $(uname -r)"
grep PRETTY_NAME /etc/os-release
echo "serial: $(grep Serial /proc/cpuinfo | awk '{print $3}')"

echo; echo "===== 2. REDE (chave para nao perder acesso) ====="
ip -4 -o addr show | grep -v " lo "
echo "--- MACs (para reserva de DHCP no roteador) ---"
ip -o link show | grep -oE "^[0-9]+: [a-z0-9]+|link/ether [0-9a-f:]+" | paste - -
echo "--- wifi configurado? ---"
nmcli -t -f NAME,TYPE con show 2>/dev/null || echo "(sem nmcli)"
echo "--- mDNS (achar por nome se o IP mudar) ---"
systemctl is-active avahi-daemon 2>/dev/null; echo "hostname mDNS seria: $(hostname).local"
echo "--- ssh habilitado? ---"
systemctl is-enabled ssh 2>/dev/null
echo "--- chaves autorizadas ---"
wc -l < ~/.ssh/authorized_keys 2>/dev/null || echo "0 (SEM CHAVE: risco de perder acesso)"

echo; echo "===== 3. TELAS ====="
for out in /sys/class/drm/card*-HDMI*; do
  [ -e "$out/status" ] || continue
  echo "$(basename $out): $(cat $out/status)  modo=$(cat $out/modes 2>/dev/null | head -1)"
  echo "   EDID: $([ -s $out/edid ] && echo "presente ($(wc -c < $out/edid) bytes)" || echo "AUSENTE -- pode precisar de video= no cmdline")"
done
echo "--- cmdline (remendo de video e especifico de cada adaptador!) ---"
cat /boot/firmware/cmdline.txt 2>/dev/null
echo "--- kanshi / labwc (NAO copiar entre maquinas) ---"
for f in ~/.config/kanshi/config ~/.config/labwc/rc.xml; do
  echo "$f: $([ -f $f ] && echo "existe ($(wc -l < $f) linhas)" || echo "NAO existe")"
done
grep -oE 'identifier="[^"]*"' ~/.config/labwc/rc.xml 2>/dev/null | sed 's/^/   regra: /'

echo; echo "===== 4. SOFTWARE DO PROJETO ====="
echo "python: $(python3 --version 2>&1)"
for m in flask pygame serial smbus2 PyQt5 numpy; do
  python3 -c "import $m, sys; print('  $m OK', getattr($m,'__version__','?'))" 2>/dev/null || echo "  $m FALTA"
done
echo "--- repositorio ---"
if [ -d ~/robo_slam/.git ]; then
  cd ~/robo_slam
  echo "  branch: $(git rev-parse --abbrev-ref HEAD)  commit: $(git rev-parse --short HEAD)"
  echo "  remoto: $(git remote get-url origin 2>/dev/null)"
  echo "  sujo?: $(git status --porcelain | wc -l) arquivo(s) modificado(s)"
else
  echo "  ~/robo_slam NAO clonado"
fi

echo; echo "===== 5. HARDWARE DO ROBO ====="
echo "joystick: $(ls /dev/input/js* 2>/dev/null || echo nenhum)"
grep -E "^N: Name" /proc/bus/input/devices | sed 's/^/  /'
echo "USB (lidar/aurora):"; lsusb 2>/dev/null | sed 's/^/  /'
echo "I2C (BNO08x costuma responder em 0x4a/0x4b):"
i2cdetect -y 1 2>/dev/null | tail -9 || echo "  (i2c-tools ausente ou barramento desligado)"
echo "grupos do usuario: $(groups)"

echo; echo "===== 6. SERVICOS DA VITRINE ====="
for u in vitrine-app vitrine-telas robo-teleop; do
  printf "  %-14s enabled=%s active=%s\n" "$u" "$(systemctl --user is-enabled $u.service 2>/dev/null || echo -)" "$(systemctl --user is-active $u.service 2>/dev/null || echo -)"
done
echo "  linger: $(loginctl show-user $(whoami) 2>/dev/null | grep -i linger || echo '?')"
echo "  autostart XDG: $(ls ~/.config/autostart/ 2>/dev/null | tr '\n' ' ')"
echo "  portas ocupadas: $(ss -ltn 2>/dev/null | grep -oE ':(8080|8765)' | sort -u | tr '\n' ' ')"
echo "  banco proprio: $([ -f ~/robo_slam/vitrine/vitrine.db ] && echo "existe ($(stat -c%s ~/robo_slam/vitrine/vitrine.db) bytes) -- NAO sobrescrever" || echo "ausente (sera semeado no 1o boot)")"

echo; echo "===== 7. ESTABILIDADE (as quedas de 2026-09-12) ====="
echo "uptime: $(uptime -p)"
echo "throttled: $(vcgencmd get_throttled 2>/dev/null) (0x0 = sem subtensao desde o boot)"
echo "volts: $(vcgencmd measure_volts 2>/dev/null)  temp: $(vcgencmd measure_temp 2>/dev/null)"
echo "watchdog de hardware: $([ -e /dev/watchdog ] && echo "/dev/watchdog presente" || echo AUSENTE)"
echo "systemd watchdog: $(grep -E '^RuntimeWatchdogSec' /etc/systemd/system.conf 2>/dev/null || echo 'nao configurado (robo fechado deveria ter)')"
echo "journal persistente: $([ -d /var/log/journal ] && echo sim || echo 'nao -- perde o log do travamento')"
echo "boots gravados: $(journalctl --list-boots 2>/dev/null | wc -l)"
echo; echo "########## FIM ##########"
