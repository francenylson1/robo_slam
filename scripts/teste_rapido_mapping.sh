#!/bin/bash
# Script de teste rápido do Aurora Mapping Studio
# Uso: ./scripts/teste_rapido_mapping.sh

set -e  # Para na primeira erro

echo "🧪 Teste Rápido - Aurora Mapping Studio"
echo "========================================"
echo ""

# Verifica se está no diretório correto
if [ ! -f "src/main_mapping.py" ]; then
    echo "❌ Erro: Execute este script da raiz do projeto"
    exit 1
fi

# Verifica ambiente virtual
if [ ! -d "venv" ]; then
    echo "❌ Erro: Ambiente virtual não encontrado"
    echo "   Crie com: python3 -m venv venv"
    exit 1
fi

# Ativa ambiente virtual
source venv/bin/activate

# Verifica Open3D
echo "📦 Verificando dependências..."
python -c "import open3d" 2>/dev/null || {
    echo "⚠️  Open3D não encontrado. Instalando..."
    pip install open3d
}

echo "✅ Dependências OK"
echo ""

# Cria diretório de teste se não existir
mkdir -p mapas/legacy/originais_aurora
mkdir -p data/pipeline_runs

# Teste 1: Inventário
echo "📋 Teste 1: Inventário de Mapas"
echo "-------------------------------"
python src/main_mapping.py \
    --pipeline inventory_snapshot \
    --input mapas \
    --output docs/mapping

if [ -f "docs/mapping/inventario_mapas.md" ]; then
    echo "✅ Inventário gerado com sucesso"
    echo "   Ver: docs/mapping/inventario_mapas.md"
else
    echo "❌ Falha ao gerar inventário"
    exit 1
fi
echo ""

# Teste 2: Criar nuvem de teste se não existir
if [ ! -f "mapas/legacy/originais_aurora/teste_rapido.ply" ]; then
    echo "🔧 Criando arquivo de teste..."
    python - <<'PY'
import numpy as np
import open3d as o3d
from pathlib import Path

points = np.random.rand(15000, 3) * 10
cloud = o3d.geometry.PointCloud()
cloud.points = o3d.utility.Vector3dVector(points)

Path('mapas/legacy/originais_aurora').mkdir(parents=True, exist_ok=True)
o3d.io.write_point_cloud('mapas/legacy/originais_aurora/teste_rapido.ply', cloud)
print('✅ Arquivo de teste criado')
PY
fi

# Teste 3: Pipeline completo (sem c1_conversion)
echo "🔄 Teste 2: Pipeline Completo (Aurora → C1)"
echo "--------------------------------------------"
python src/main_mapping.py \
    --pipeline aurora_to_c1 \
    --input mapas/legacy/originais_aurora \
    --output data/pipeline_runs/teste_rapido \
    --steps capture,refinement,map2d,annotation,export

if [ -d "data/pipeline_runs/teste_rapido/export" ]; then
    echo "✅ Pipeline executado com sucesso"
    echo "   Resultados em: data/pipeline_runs/teste_rapido/"
    
    # Lista arquivos gerados
    echo ""
    echo "📁 Arquivos gerados:"
    find data/pipeline_runs/teste_rapido/export -type f | head -10
else
    echo "❌ Falha no pipeline"
    exit 1
fi
echo ""

# Resumo
echo "========================================"
echo "✅ Todos os testes passaram!"
echo ""
echo "📚 Próximos passos:"
echo "   1. Veja o guia completo: docs/mapping/GUIA_USO_INICIAL.md"
echo "   2. Processe seus mapas reais do Aurora"
echo "   3. Edite os POIs gerados em: data/pipeline_runs/teste_rapido/annotation/"
echo ""
echo "🎉 Sistema pronto para uso!"

