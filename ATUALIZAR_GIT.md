# 📤 Atualizar Git - Instruções

## ✅ Conferir se a Raspberry está na mesma versão do desktop

**Referência:** compare o **hash do último commit** nos dois.

| Onde | Comando |
|------|---------|
| **Desktop** (após push) | `git log -1 --oneline` ou `git rev-parse HEAD` |
| **Raspberry** (após pull) | `git log -1 --oneline` ou `git rev-parse HEAD` |

Se o hash for **igual** nos dois, a Raspberry está na mesma versão.  
Detalhes: `docs/PROMPT_CONTINUACAO_BNO_E_INTEGRACAO_2026.md` → seção "Conferir se a Raspberry está na mesma versão do desktop".

**Branch atual (Fase 1 BNO):** `robo_slam_2026_1_bno_ok`

---

## 🪟 Windows (Atual)

Execute o script:
```powershell
.\atualizar_git.bat
```

Ou manualmente:
```powershell
git add -A
git commit -m "Implementação completa: Sistema Aurora → C1"
git push origin v2.0-robo-com-3cm-do-chao-testes-em-linha-reta
```

---

## 🐧 Ubuntu / Raspberry Pi (Próximo)

Após o push no Windows, no Ubuntu/Raspberry Pi:

```bash
# Atualizar código
git pull origin v2.0-robo-com-3cm-do-chao-testes-em-linha-reta

# Instalar dependências (se necessário)
pip3 install -r requirements.txt

# Ou apenas as novas dependências
pip3 install open3d Pillow PyYAML requests
```

---

## 📋 Resumo das Mudanças

### Arquivos Novos:
- Módulos de processamento de mapas (`src/core/aurora_*.py`, etc.)
- Scripts de conversão (`converter_*.py`)
- Scripts auxiliares (`visualizar_mapa.py`, `processar_mapa.bat`, etc.)
- Documentação completa (`docs/*.md`)
- Estrutura de pastas (`mapas/`)

### Arquivos Modificados:
- `src/interfaces/main_window.py` - Novos botões e funcionalidades
- `src/interfaces/map_widget.py` - Carregamento de PGM
- `requirements.txt` - Novas dependências

---

## ✅ Verificação

Após o pull no Ubuntu/Raspberry Pi, verifique:
```bash
# Ver arquivos novos
ls -la mapas/
ls -la src/core/aurora*.py

# Verificar dependências
pip3 list | grep -E "open3d|Pillow|PyYAML|requests"
```

---

**Execute o script `atualizar_git.bat` no Windows para concluir!** 🚀

