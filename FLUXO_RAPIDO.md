# ⚡ Fluxo Rápido - Aurora → C1

## 🎯 Processo em 3 Passos

### 1️⃣ **Aurora: Gravar e Exportar**
- Gravar mapa no Aurora
- Exportar como **BMP** → Salvar em `mapas/originais_aurora/nome.bmp`

### 2️⃣ **Processar (Um Comando)**
```powershell
processar_mapa.bat nome bmp
```

Ou manualmente:
```powershell
py converter_bmp_para_mapa.py mapas/originais_aurora/nome.bmp --output nome
```

### 3️⃣ **Usar**
- Arquivos prontos em: `mapas/otimizados/nome.pgm` e `nome.yaml`
- Use no sistema de navegação ou faça upload para C1

---

## 📋 Checklist Rápido

- [ ] Mapa gravado no Aurora
- [ ] BMP exportado → `mapas/originais_aurora/`
- [ ] Processado → `processar_mapa.bat nome bmp`
- [ ] Validado → Visualizar mapa
- [ ] Pronto para uso → `mapas/otimizados/`

---

## 🚀 Scripts Disponíveis

| Script | Uso |
|--------|-----|
| `processar_mapa.bat nome bmp` | Processa BMP (mais comum) |
| `processar_mapa.bat nome ply` | Processa PLY/PCD |
| `py visualizar_mapa.py mapas/otimizados/nome.pgm` | Visualiza mapa |

---

**Documentação completa:** `docs/FLUXO_COMPLETO_AURORA_C1.md`

