# 🧪 Guia de Teste: Desvio de Áreas Proibidas

## 📋 Como Executar

### Opção 1: Executar o script de teste
```bash
cd /home/amd/Área\ de\ trabalho/robo_slam
python tests/teste_desvio_areas_proibidas.py
```

### Opção 2: Executar via interface (teste real)
1. Abra a interface: `python src/main.py`
2. Carregue um mapa PGM
3. Adicione áreas proibidas no mapa
4. Selecione um POI e inicie navegação
5. Observe os logs no terminal

## 🎯 O Que o Script de Teste Faz

O script executa 5 testes diferentes:

1. **Teste 1: Sem áreas proibidas**
   - Verifica se a navegação básica funciona
   - Deve encontrar caminho direto

2. **Teste 2: Área proibida no meio**
   - Coloca uma área proibida bloqueando o caminho direto
   - Deve desviar ao redor da área

3. **Teste 3: Start próximo à área proibida**
   - Start muito próximo a uma área proibida
   - Deve encontrar ponto válido próximo

4. **Teste 4: Múltiplas áreas proibidas**
   - Várias áreas proibidas no caminho
   - Deve desviar de todas

5. **Teste 5: Caminho bloqueado**
   - Caminho completamente bloqueado
   - Deve falhar graciosamente (não travar)

## 📊 Resultados Esperados

### ✅ Sucesso
- A* encontra caminho
- Caminho não intersecta áreas proibidas
- Número razoável de waypoints

### ❌ Problemas Comuns

1. **A* não encontra caminho**
   - Verifique se start/goal estão dentro dos limites do mapa
   - Verifique se `obstacle_grid` está sendo populado
   - Verifique se `map_origin` está correto

2. **Caminho passa por áreas proibidas**
   - Verifique se `FORBIDDEN_AREA_INFLATION_RADIUS` está adequado
   - Verifique se `_line_intersects_obstacles` está funcionando

3. **Start/Goal em área proibida**
   - Verifique se `_find_nearest_valid_point` está funcionando
   - Verifique se há espaço suficiente ao redor

## 📁 Arquivos Gerados

O script gera um arquivo JSON com os resultados:
- Localização: `data/teste_desvio_areas_proibidas_YYYYMMDD_HHMMSS.json`
- Contém: resultados detalhados de cada teste, logs, erros

## 🔍 O Que Observar nos Logs

### Logs Importantes:

1. **Configuração do PathFinder:**
   ```
   DEBUG: PathFinder inicializado - Dimensões: ...
   DEBUG: Áreas proibidas definidas: ...
   DEBUG: Cache de obstáculos atualizado: ... células
   ```

2. **Conversão de Coordenadas:**
   ```
   DEBUG: Coordenadas relativas - Início: ...
   DEBUG: Coordenadas da grade - Início: ...
   ```

3. **Execução do A*:**
   ```
   🔍 A* INICIADO: Start=..., Goal=...
   DEBUG: Caminho encontrado pelo A*!
   ```

4. **Erros:**
   ```
   🚨 ERRO: A* não encontrou caminho
   🚨 ERRO: Start fora dos limites
   ```

## 💡 Dicas para Debug

1. **Se A* não encontra caminho:**
   - Verifique se `obstacle_grid` tem células marcadas
   - Verifique se start/goal estão em obstáculos
   - Tente reduzir `FORBIDDEN_AREA_INFLATION_RADIUS` temporariamente

2. **Se caminho passa por áreas proibidas:**
   - Verifique se `_update_obstacle_grid()` está sendo chamado
   - Verifique se polígonos estão sendo inflados corretamente
   - Verifique se `_line_intersects_obstacles()` está funcionando

3. **Se start/goal estão fora dos limites:**
   - Verifique se `map_origin` está correto
   - Verifique se dimensões do mapa estão corretas
   - Verifique se coordenadas estão em metros (não pixels)

## 📤 Enviando Resultados

Após executar os testes, envie:
1. O arquivo JSON gerado (`data/teste_desvio_areas_proibidas_*.json`)
2. Logs do terminal (se houver erros)
3. Descrição do que observou durante os testes

## 🎯 Próximos Passos Após os Testes

Com base nos resultados:
1. Se todos os testes passarem → Sistema funcionando! ✅
2. Se alguns testes falharem → Analisar logs e corrigir problemas
3. Se todos falharem → Debug mais profundo necessário

