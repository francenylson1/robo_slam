#!/bin/bash
# Espera o Flask da vitrine responder, antes de abrir a janela do carrossel.
# Sem isso a janela /signage abre numa porta morta e fica presa na tela de erro.
# E um script (e nao um ExecStartPre inline) porque o systemd faz expansao propria
# de $ e engoliria o $(seq) e o $i de um loop escrito na unit.
PORTA="${ROBO_VITRINE_PORT:-8080}"
for _ in $(seq 1 60); do
  curl -sf -o /dev/null "http://127.0.0.1:${PORTA}/api/versao" && exit 0
  sleep 1
done
echo "vitrine nao respondeu em 60s na porta ${PORTA}" >&2
exit 1
