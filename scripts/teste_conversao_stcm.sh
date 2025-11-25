#!/bin/bash
# Script de teste rápido para conversão .stcm → .ply usando SDK do Aurora

set -e  # Para na primeira erro

echo "🧪 Teste de Conversão .stcm → .ply com SDK do Aurora"
echo "=================================================="
echo ""

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verifica se estamos no diretório correto
if [ ! -f "src/main_mapping.py" ]; then
    echo -e "${RED}❌ Erro: Execute este script a partir do diretório raiz do projeto${NC}"
    exit 1
fi

# Verifica se o arquivo .stcm existe
STCM_FILE="mapas/legacy/originais_aurora/sala-maker-1.stcm"
if [ ! -f "$STCM_FILE" ]; then
    echo -e "${YELLOW}⚠️  Arquivo .stcm não encontrado: $STCM_FILE${NC}"
    echo "   Usando qualquer arquivo .stcm encontrado..."
    STCM_FILE=$(find mapas -name "*.stcm" -type f | head -1)
    if [ -z "$STCM_FILE" ]; then
        echo -e "${RED}❌ Nenhum arquivo .stcm encontrado em mapas/${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Usando: $STCM_FILE${NC}"
else
    echo -e "${GREEN}✅ Arquivo .stcm encontrado: $STCM_FILE${NC}"
fi

# Verifica configuração do Aurora
echo ""
echo "📋 Verificando configuração..."
if grep -q '"enabled": true' config/mapping.json; then
    echo -e "${GREEN}✅ SDK do Aurora está habilitado${NC}"
else
    echo -e "${YELLOW}⚠️  SDK do Aurora está DESABILITADO em config/mapping.json${NC}"
    echo "   Configure 'aurora.enabled: true' para usar o SDK"
    read -p "   Deseja continuar mesmo assim? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 1
    fi
fi

# Verifica se o SDK existe
SDK_PATH="py_aurora_remote-main/python_bindings"
if [ -d "$SDK_PATH" ]; then
    echo -e "${GREEN}✅ SDK do Aurora encontrado em: $SDK_PATH${NC}"
else
    echo -e "${RED}❌ SDK do Aurora não encontrado em: $SDK_PATH${NC}"
    exit 1
fi

# Diretório de saída
OUTPUT_DIR="data/pipeline_runs/teste_stcm_$(date +%Y%m%d_%H%M%S)"
echo ""
echo "📁 Diretório de saída: $OUTPUT_DIR"
echo ""

# Executa o teste
echo "🚀 Executando conversão..."
echo "   Pipeline: Aurora → C1"
echo "   Input: $STCM_FILE"
echo "   Output: $OUTPUT_DIR"
echo "   Steps: capture,refinement"
echo ""

python src/main_mapping.py \
  --pipeline aurora_to_c1 \
  --input "$STCM_FILE" \
  --output "$OUTPUT_DIR" \
  --steps capture,refinement

# Verifica resultado
echo ""
echo "🔍 Verificando resultados..."

PLY_FILE=$(find "$OUTPUT_DIR/refinement" -name "*.ply" -type f 2>/dev/null | head -1)

if [ -n "$PLY_FILE" ] && [ -s "$PLY_FILE" ]; then
    FILE_SIZE=$(du -h "$PLY_FILE" | cut -f1)
    echo -e "${GREEN}✅ Arquivo .ply gerado com sucesso!${NC}"
    echo "   Arquivo: $PLY_FILE"
    echo "   Tamanho: $FILE_SIZE"
    
    # Conta pontos (se possível)
    if command -v python3 &> /dev/null; then
        POINT_COUNT=$(python3 -c "
import sys
try:
    import open3d as o3d
    cloud = o3d.io.read_point_cloud('$PLY_FILE')
    print(len(cloud.points))
except:
    print('N/A')
" 2>/dev/null)
        if [ "$POINT_COUNT" != "N/A" ]; then
            echo "   Pontos: $(printf "%'d" $POINT_COUNT)"
        fi
    fi
    
    echo ""
    echo -e "${GREEN}✅ Teste concluído com sucesso!${NC}"
    exit 0
else
    echo -e "${RED}❌ Erro: Arquivo .ply não foi gerado ou está vazio${NC}"
    echo "   Verifique os logs acima para mais detalhes"
    exit 1
fi

