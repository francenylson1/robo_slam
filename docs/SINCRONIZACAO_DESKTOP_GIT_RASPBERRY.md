# Sincronização: Desktop → Git → Raspberry

Fluxo para manter **esta versão do desktop**, o **Git na nuvem** e a **Raspberry** sempre na mesma versão.

**POIs e áreas proibidas:** ficam no banco `data/robot.db`, que **está no Git** (é a exceção à pasta `data/` no .gitignore). Ao dar `git pull` na Raspberry, você recebe o mesmo `robot.db` do desktop. Para o app encontrar o banco, **execute sempre na raiz do projeto** (ex.: `cd ~/robo_slam` e depois `python src/main.py`).

---

## Visão geral

```
  DESKTOP (você desenvolve aqui)
       │
       │  git add + commit + push
       ▼
  GIT (GitHub – versão “oficial”)
       │
       │  git pull (na Raspberry)
       ▼
  RASPBERRY (roda o robô com a mesma versão)
```

- **Desktop:** fonte da verdade; você edita e testa aqui.
- **Git:** espelho na nuvem; você sobe as alterações com `push`.
- **Raspberry:** consome o que está no Git; você atualiza com `pull`.

---

## No DESKTOP (depois de desenvolver)

Sempre que quiser guardar no Git e deixar a Raspberry poder atualizar:

```bash
cd "/home/amd/Área de trabalho/robo_slam"

# 1) Ver o que mudou
git status

# 2) Incluir tudo e commitar
git add -A
git commit -m "Descrição do que você fez"

# 3) Enviar para o GitHub (usa o token configurado)
git push origin robo-slam-v.3.2-aurora_bmp-c1_pgm-navegando-ate-o-POI-com-obstaculos-corretamente-precisando-de-ajustes-finos
```

Se você configurou o **credential helper** (ver seção abaixo), o Git não vai pedir senha em todo push.

---

## Na RASPBERRY (para ficar igual ao desktop/Git)

Sempre que quiser que a Raspberry fique com a mesma versão que você subiu do desktop:

```bash
# 1) Ir para a pasta do projeto (ajuste o caminho se for diferente)
cd ~/robo_slam

# 2) (Opcional) Backup antes de atualizar
cp -r . ../robo_slam_backup_$(date +%Y%m%d_%H%M%S)

# 3) Buscar e puxar a versão do Git
git fetch origin
git checkout robo-slam-v.3.2-aurora_bmp-c1_pgm-navegando-ate-o-POI-com-obstaculos-corretamente-precisando-de-ajustes-finos
git pull origin robo-slam-v.3.2-aurora_bmp-c1_pgm-navegando-ate-o-POI-com-obstaculos-corretamente-precisando-de-ajustes-finos
```

Se já estiver nessa branch e só quiser atualizar:

```bash
cd ~/robo_slam
git pull origin robo-slam-v.3.2-aurora_bmp-c1_pgm-navegando-ate-o-POI-com-obstaculos-corretamente-precisando-de-ajustes-finos
```

---

## Configurar o token no DESKTOP (uso frequente)

**Já está configurado neste desktop:** o `origin` usa HTTPS e o token está no credential helper. Você pode usar `git push` e `git pull` sem digitar senha.

Se um dia trocar de máquina ou de token:

1. **Credential helper:** `git config credential.helper store` (na pasta do projeto).
2. **Remote em HTTPS:** `git remote set-url origin https://github.com/francenylson1/robo_slam.git`
3. Na primeira vez que rodar `git push`, use seu usuário do GitHub e o token como senha; o Git grava em `~/.git-credentials`.

---

## Resumo rápido

| Onde      | Ação |
|----------|------|
| **Desktop** | Desenvolver → `git add -A` → `git commit -m "..."` → `git push origin robo-slam-v.3.2-aurora_bmp-c1_pgm-navegando-ate-o-POI-com-obstaculos-corretamente-precisando-de-ajustes-finos` |
| **Raspberry** | `cd ~/robo_slam` → (opcional) backup → `git pull origin robo-slam-v.3.2-aurora_bmp-c1_pgm-navegando-ate-o-POI-com-obstaculos-corretamente-precisando-de-ajustes-finos` |

Assim você mantém desktop, Git e Raspberry em sincronia.
