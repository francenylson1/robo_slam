# 📡 Como Coletar Mapas com o C1

## ❌ Limitação: USB Necessário

**O sensor C1 precisa estar conectado via USB durante a coleta** porque:
- Os dados são transmitidos em tempo real via USB Serial
- O C1 não tem armazenamento interno para gravar scans
- O sistema precisa receber os dados continuamente

## ✅ Soluções Práticas

### Opção 1: Cabo USB Mais Longo (Recomendado)

**Use um cabo USB de 3-5 metros** para ter mais liberdade de movimento:

```bash
# Conecte o C1 com cabo USB longo
# Depois execute a coleta normalmente
python3 src/main_c1_mapping.py collect \
  --duration 120 \
  --output mapas/c1/completo/raw \
  --full-scans
```

**Vantagens**:
- ✅ Mais liberdade para mover o sensor
- ✅ Solução simples e barata
- ✅ Funciona imediatamente

**Recomendações**:
- Use cabo USB 2.0 ou 3.0 de boa qualidade
- Máximo recomendado: 5 metros
- Evite extensões USB passivas (use cabo direto)

### Opção 2: Notebook/Laptop Portátil

**Use um notebook** para ter mais mobilidade:

1. Conecte o C1 ao notebook via USB
2. Execute a coleta enquanto anda pela sala
3. O notebook pode ser carregado ou usar bateria

**Vantagens**:
- ✅ Totalmente móvel
- ✅ Pode mapear grandes áreas
- ✅ Não precisa de cabo longo

### Opção 3: Verificar SLAM Interno do C1

**Se o C1 tiver SLAM interno e estiver na rede**:

1. Mapeie usando o sistema interno do C1 (sem USB)
2. Depois baixe o mapa via API REST:

```bash
# Baixa mapa já processado do C1
python3 src/main_c1_mapping.py get-map \
  --output mapas/c1/final
```

**Vantagens**:
- ✅ Não precisa de USB durante mapeamento
- ✅ Mapa já processado pelo C1
- ✅ Funciona via rede WiFi/Ethernet

**Limitações**:
- ⚠️ Precisa que o C1 tenha SLAM interno
- ⚠️ Precisa estar na mesma rede
- ⚠️ Não coleta scans brutos

## 🎯 Recomendação para Sua Situação

Para mapear uma sala retangular (6m x 12m):

### Solução Ideal:
1. **Use cabo USB de 3-5 metros**
2. **Conecte o C1 ao notebook**
3. **Ande pela sala movendo o sensor lentamente**
4. **Colete por 120-240 segundos**

### Durante a Coleta:
- ✅ Mova o sensor ao longo das paredes
- ✅ Mantenha o sensor apontado para as paredes
- ✅ Ande em padrão retangular pela sala
- ✅ Evite apenas girar no centro

## 📋 Checklist

- [ ] Cabo USB longo (3-5m) ou notebook
- [ ] C1 conectado via USB
- [ ] Sensor alimentado (LED verde)
- [ ] Ambiente preparado (sala vazia ou com obstáculos conhecidos)
- [ ] Tempo disponível (2-4 minutos)

## 🚀 Comando de Coleta

```bash
# Coleta móvel (com cabo longo ou notebook)
python3 src/main_c1_mapping.py collect \
  --duration 120 \
  --output mapas/c1/completo/raw \
  --full-scans
```

---

**Resumo**: Para scans brutos, precisa de USB. Use cabo longo ou notebook para ter mobilidade!

