# Checkpoint antes da Fase 1 (BNO só nas retas)

Foi criada a **tag** `checkpoint-antes-fase1-bno-retas` no commit em que a base está só com odometria e os docs do percurso estão atualizados, **antes** de qualquer alteração da Fase 1.

## Como voltar a esse ponto (se algo quebrar)

**Opção 1 – Só ver o código naquele ponto (sem mudar branch):**
```bash
git checkout checkpoint-antes-fase1-bno-retas
```
(Você ficará em "detached HEAD". Para voltar ao branch: `git checkout robo_slam_2026_1_bno_com_odometria`.)

**Opção 2 – Descartar as alterações da Fase 1 e voltar ao checkpoint:**
```bash
git reset --hard checkpoint-antes-fase1-bno-retas
```
(Cuidado: isso apaga commits e alterações locais depois do checkpoint.)

**Opção 3 – Criar um branch de backup a partir do checkpoint e continuar no atual:**
```bash
git branch backup-antes-fase1 checkpoint-antes-fase1-bno-retas
```
(Assim você pode sempre voltar com `git checkout backup-antes-fase1`.)

## Listar tags

```bash
git tag -l
git show checkpoint-antes-fase1-bno-retas
```
