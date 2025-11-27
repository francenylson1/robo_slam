#!/bin/bash
# Script para gerar um mapa completo do C1
# Coleta scans, processa e exporta em um único comando

set -e  # Para em caso de erro

echo "🗺️  GERANDO MAPA COMPLETO DO C1"
echo "=================================="
echo ""

# Configurações
DURATION=${1:-60}  # Duração da coleta em segundos (padrão: 60)
OUTPUT_DIR="mapas/c1/completo"
MAP_NAME="mapa_completo_$(date +%Y%m%d_%H%M%S)"

echo "⏱️  Duração da coleta: ${DURATION}s"
echo "📁 Diretório de saída: ${OUTPUT_DIR}"
echo "🏷️  Nome do mapa: ${MAP_NAME}"
echo ""

# Cria diretórios
mkdir -p "${OUTPUT_DIR}/raw"
mkdir -p "${OUTPUT_DIR}/processed"
mkdir -p "${OUTPUT_DIR}/final"

# Passo 1: Detectar C1
echo "📋 PASSO 1: Detectando C1..."
if ! python3 src/main_c1_mapping.py detect > /dev/null 2>&1; then
    echo "❌ C1 não detectado! Verifique a conexão."
    exit 1
fi
echo "✅ C1 detectado"
echo ""

# Passo 2: Coletar scans
echo "📋 PASSO 2: Coletando scans (${DURATION}s)..."
echo "   💡 Mova o C1 lentamente durante a coleta para mapear uma área maior"
echo "   💡 Pressione Ctrl+C para parar antes do tempo"
echo ""

if ! python3 src/main_c1_mapping.py collect \
    --duration ${DURATION} \
    --output "${OUTPUT_DIR}/raw" \
    --full-scans; then
    echo "❌ Falha na coleta de scans"
    exit 1
fi

# Encontra o arquivo de scans mais recente
SCAN_FILE=$(ls -t "${OUTPUT_DIR}/raw"/scans_*.json 2>/dev/null | head -1)

if [ -z "$SCAN_FILE" ]; then
    echo "❌ Nenhum arquivo de scans encontrado"
    exit 1
fi

echo "✅ Scans coletados: ${SCAN_FILE}"
echo ""

# Passo 3: Processar scans
echo "📋 PASSO 3: Processando scans e gerando mapa..."
if ! python3 src/main_c1_mapping.py process \
    --input "${SCAN_FILE}" \
    --output "${OUTPUT_DIR}/processed" \
    --resolution 0.05; then
    echo "❌ Falha no processamento"
    exit 1
fi

# Encontra o arquivo de mapa mais recente
MAP_FILE=$(ls -t "${OUTPUT_DIR}/processed"/map_*.npy 2>/dev/null | head -1)

if [ -z "$MAP_FILE" ]; then
    echo "❌ Nenhum arquivo de mapa encontrado"
    exit 1
fi

echo "✅ Mapa processado: ${MAP_FILE}"
echo ""

# Passo 4: Exportar mapa
echo "📋 PASSO 4: Exportando mapa em PGM/YAML..."
if ! python3 src/main_c1_mapping.py export \
    --map "${MAP_FILE}" \
    --output "${OUTPUT_DIR}/final" \
    --name "${MAP_NAME}"; then
    echo "❌ Falha na exportação"
    exit 1
fi

PGM_FILE="${OUTPUT_DIR}/final/${MAP_NAME}.pgm"
YAML_FILE="${OUTPUT_DIR}/final/${MAP_NAME}.yaml"

if [ ! -f "$PGM_FILE" ] || [ ! -f "$YAML_FILE" ]; then
    echo "❌ Arquivos PGM/YAML não encontrados"
    exit 1
fi

echo "✅ Mapa exportado:"
echo "   PGM: ${PGM_FILE}"
echo "   YAML: ${YAML_FILE}"
echo ""

# Resumo final
echo "=================================="
echo "✅ MAPA COMPLETO GERADO COM SUCESSO!"
echo "=================================="
echo ""
echo "📁 Arquivos gerados:"
echo "   Scans: ${SCAN_FILE}"
echo "   Mapa processado: ${MAP_FILE}"
echo "   PGM: ${PGM_FILE}"
echo "   YAML: ${YAML_FILE}"
echo ""
echo "💡 Próximos passos:"
echo "   1. Abra o main.py: python3 src/main.py"
echo "   2. Clique em '🗺️ Carregar PGM'"
echo "   3. Selecione: ${PGM_FILE}"
echo "   4. Adicione POIs e áreas proibidas"
echo ""

