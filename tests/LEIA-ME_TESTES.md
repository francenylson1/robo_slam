# 🧪 Testes de Desvio de Áreas Proibidas

## 📦 Arquivos Criados

1. **`teste_desvio_areas_proibidas.py`** - Script principal com suíte completa de testes
2. **`teste_desvio_personalizado.py`** - Script para criar testes personalizados
3. **`GUIA_TESTE_DESVIO.md`** - Guia detalhado de uso
4. **`LEIA-ME_TESTES.md`** - Este arquivo (resumo rápido)

## 🚀 Como Usar

### Teste Rápido (Recomendado)
```bash
cd /home/amd/Área\ de\ trabalho/robo_slam
python tests/teste_desvio_areas_proibidas.py
```

Este comando:
- ✅ Executa 5 testes diferentes
- ✅ Gera relatório JSON em `data/teste_desvio_areas_proibidas_*.json`
- ✅ Mostra resumo no terminal

### Teste Personalizado
1. Edite `teste_desvio_personalizado.py`
2. Defina seus próprios pontos e áreas proibidas
3. Execute: `python tests/teste_desvio_personalizado.py`

## 📊 O Que Esperar

### ✅ Se Funcionar Corretamente:
- A* encontra caminhos
- Caminhos não passam por áreas proibidas
- Relatório mostra sucessos

### ❌ Se Houver Problemas:
- A* não encontra caminhos
- Caminhos passam por áreas proibidas
- Erros nos logs

## 📤 Enviando Resultados

Após executar, envie:
1. **Arquivo JSON** gerado em `data/teste_desvio_areas_proibidas_*.json`
2. **Logs do terminal** (copie e cole)
3. **Descrição** do que observou

## 🔍 Onde Estão os Resultados?

- **Relatório JSON**: `data/teste_desvio_areas_proibidas_YYYYMMDD_HHMMSS.json`
- **Logs**: Terminal onde executou o script

## 💡 Dicas

- Execute primeiro o teste completo para ver o estado geral
- Use o teste personalizado para casos específicos
- Verifique os logs para entender o que está acontecendo
- Se houver erros, copie as mensagens completas

## 📚 Mais Informações

Veja `GUIA_TESTE_DESVIO.md` para:
- Explicação detalhada de cada teste
- Como interpretar os resultados
- Dicas de debug
- Próximos passos

