# Vitrine — tela de 15" do robô

Carrossel de propagandas na tela de 15" montada em retrato na frente do robô, com um
painel de cadastro que roda no navegador do celular pela rede local.

A tela de 7" continua com o rosto animado (`display/robot_face/`); esta aqui é a comercial.

```
/signage   -> vai na tela de 15" em kiosk (1080 x 1920)
/admin     -> painel de cadastro, aberto do celular ou do notebook
```

## Como subir

```bash
cd ~/robo_slam/vitrine
setsid python3 app.py > /tmp/vitrine.log 2>&1 &
```

Servidor em `0.0.0.0:8080`. O banco `vitrine.db` é criado e semeado no primeiro start.
**Não sobe sozinho no boot** — ver a seção "Pendências".

Depois, as duas janelas do Chromium:

```bash
~/lancar_telas.sh   # sem argumentos usa o rosto no 7" e o /signage no 15"
```

## Estrutura

| arquivo | o que faz |
|---|---|
| `app.py` | Flask + SQLite puro, sem ORM. Rotas, upload e configuração. |
| `static/render.js` | **Renderizador compartilhado.** Desenha o slide a partir da linha do banco. |
| `static/vitrine.css` | Design system dos slides (herdado do rosto de 7"). |
| `static/admin.css` | Painel. |
| `templates/signage.html` | O carrossel: busca `/api/slides`, monta, cicla e vigia `/api/versao`. |
| `templates/admin.html` | Lista de slides: reordenar, tirar do ar, editar, excluir. |
| `templates/form.html` | Cadastro com prévia ao vivo. |
| `templates/config.html` | Nome do robô, área segura e escala da tela. |
| `lancar_telas.sh` | Cópia versionada do launcher das duas janelas (o vivo fica em `~/`). |

### Por que o renderizador é compartilhado

O carrossel e a prévia do formulário chamam a mesma `Vitrine.slideHTML()`. Se a prévia
tivesse markup próprio, ela mentiria sobre o resultado na tela — principalmente sobre a
área segura, que é o detalhe que mais dói de errar.

### Por que a tela se atualiza sozinha

Toda escrita no painel grava um carimbo novo em `config.versao`. O `/signage` consulta
`/api/versao` a cada 5 s e recarrega quando muda. Sem isso, cada cadastro exigiria ir até
o robô reiniciar o Chromium.

## Tipos de slide

| tipo | campos usados | para quê |
|---|---|---|
| `frase` | chapéu, título, subtítulo | frase do momento, com autor |
| `instituicao` | chapéu, título, subtítulo, imagem | parceiro / órgão, com logo |
| `pessoa` | chapéu, título, subtítulo, imagem | aluno ou equipe: retrato redondo + escola |
| `promocao` | título, preço, preço antigo, rodapé, imagem | oferta da casa |
| `imagem` | título, imagem | arte pronta 1080 × 1920, sangrando na tela toda |

Sem imagem, `instituicao` mostra a moldura de logo e `pessoa` mostra a inicial do nome.

## Área segura — por que ela existe

O acabamento frontal do robô **cobre 20 mm da borda direita** da imagem. Medido na tela
real em 2026-09-11 com uma régua desenhada de 2 em 2 mm: o "18" saía cortado, o "20"
aparecia inteiro.

As margens ficam na tabela `config` (`mt`, `mr`, `mb`, `ml`, em milímetros) e são
aplicadas como `padding` do `.slide`, convertidas por `pxmm` (5,58 px/mm = 55,8 px/cm na
tela de 15"). Fundos e brilhos continuam sangrando até a borda física porque são
`position: absolute`.

**Esse número é desta máquina.** Outro robô, outro acabamento: medir de novo pelo painel,
em Configurações.

## Restrições de display (Wayland + labwc)

Custaram várias tentativas e não são deriváveis lendo os arquivos de config:

1. `--ozone-platform=x11` é obrigatório. Em Wayland nativo o Chromium ignora
   `--window-position` em silêncio.
2. `--kiosk` e `--start-fullscreen` sobrepõem a posição e abrem sempre na tela primária.
   Não usar: posicionar a janela e deixar o labwc cuidar do resto.
3. Tela cheia sem decoração vem de regra do labwc em `~/.config/labwc/rc.xml`, casando por
   `identifier`. **O identifier é o *instance name*, que o Chromium deriva da URL** —
   `http://127.0.0.1:8080/signage` vira `127.0.0.1__signage`, e por isso existe uma regra
   `*signage*` além da `*vitrine*`. Casar por `title` não funciona.
4. Layout das saídas no kanshi (`~/.config/kanshi/config`, perfil `duas_telas`):
   HDMI-A-1 = 7" a 1024x600; HDMI-A-2 = 15" a 1920x1080 com `transform 90` em 1024,0.
5. Recarregar o labwc com `kill -HUP $(pidof labwc)`.
6. Cuidado com `pkill -f`: ele mata o próprio shell se o padrão aparecer na linha de
   comando. Matar e lançar em chamadas separadas — é o que o `lancar_telas.sh` faz.

## Pendências

1. **Autostart.** Nada sobe sozinho: nem o Flask, nem as duas janelas. Em 2026-09-11 o Pi
   reiniciou e as duas telas ficaram no desktop vazio. Falta um serviço systemd de usuário
   para o `app.py` e outro para o `lancar_telas.sh`, com `Restart=on-failure`.
2. **Journal persistente** (`Storage=persistent`) para descobrir por que ele reiniciou.
3. **Fotos dos alunos** — os slides estão com a inicial do nome.
4. **Senha no `/admin`?** Hoje qualquer um na rede local cadastra slide.
5. **Nome do robô** — ainda `[NOME DO ROBÔ]`, editável em Configurações.
6. Escala da tela de 7" não confirmada (o quadrado de calibragem mediu 6,2 × 6,0 cm onde
   deveria dar 6,0 × 6,0). Padrão de teste em `display/robot_face/alinhamento.html`.
