# Como atualizar a Raspberry com o código do desktop

Sempre que fizer **commit e push** no desktop, use estes passos na Raspberry para puxar as alterações (incluindo a **Fase 1 – BNO só nas retas** e a **tag de checkpoint**).

---

## 1. Se você tiver alterações locais (ex.: `data/robot.db`)

Guarde-as com stash, puxe o remoto e depois reaplique:

```bash
cd ~/robo_slam
git stash -m "local"
git pull origin robo_slam_2026_1_bno_com_odometria
git stash pop
```

Se **não** tiver alterações locais, basta:

```bash
cd ~/robo_slam
git pull origin robo_slam_2026_1_bno_com_odometria
```

---

## 2. Trazer a tag do checkpoint (opcional)

Para ter a tag **checkpoint-antes-fase1-bno-retas** na Raspberry (útil para reverter se algo quebrar):

```bash
git fetch origin tag checkpoint-antes-fase1-bno-retas
```

(Se você já deu `git pull`, as tags do branch costumam vir junto; se não, use o `git fetch` acima.)

---

## 3. Conferir se está atualizado

```bash
git log -1 --oneline
```

Deve aparecer algo como: `1577efa feat(nav): Fase 1 - BNO só nas retas...`

---

## 4. Rodar o projeto

Com o venv ativado (ex.: `source venv/bin/activate`):

```bash
python3 src/main.py
# ou o comando que você usa para iniciar a interface
```

---

## Resumo rápido (copiar e colar)

**Com alterações locais (ex.: robot.db):**
```bash
cd ~/robo_slam
git stash -m "local"
git pull origin robo_slam_2026_1_bno_com_odometria
git stash pop
```

**Sem alterações locais:**
```bash
cd ~/robo_slam
git pull origin robo_slam_2026_1_bno_com_odometria
```

Depois: ativar o venv (se usar) e iniciar o app.
