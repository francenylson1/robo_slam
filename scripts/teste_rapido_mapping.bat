@echo off
REM Script de teste rápido do Aurora Mapping Studio (Windows)
REM Uso: scripts\teste_rapido_mapping.bat

echo 🧪 Teste Rápido - Aurora Mapping Studio
echo ========================================
echo.

REM Verifica se está no diretório correto
if not exist "src\main_mapping.py" (
    echo ❌ Erro: Execute este script da raiz do projeto
    exit /b 1
)

REM Verifica ambiente virtual
if not exist "venv" (
    echo ❌ Erro: Ambiente virtual não encontrado
    echo    Crie com: python -m venv venv
    exit /b 1
)

REM Ativa ambiente virtual
call venv\Scripts\activate.bat

REM Verifica Open3D
echo 📦 Verificando dependências...
python -c "import open3d" 2>nul
if errorlevel 1 (
    echo ⚠️  Open3D não encontrado. Instalando...
    pip install open3d
)

echo ✅ Dependências OK
echo.

REM Cria diretórios de teste
if not exist "mapas\legacy\originais_aurora" mkdir mapas\legacy\originais_aurora
if not exist "data\pipeline_runs" mkdir data\pipeline_runs

REM Teste 1: Inventário
echo 📋 Teste 1: Inventário de Mapas
echo -------------------------------
python src\main_mapping.py --pipeline inventory_snapshot --input mapas --output docs\mapping

if exist "docs\mapping\inventario_mapas.md" (
    echo ✅ Inventário gerado com sucesso
    echo    Ver: docs\mapping\inventario_mapas.md
) else (
    echo ❌ Falha ao gerar inventário
    exit /b 1
)
echo.

REM Teste 2: Criar nuvem de teste se não existir
if not exist "mapas\legacy\originais_aurora\teste_rapido.ply" (
    echo 🔧 Criando arquivo de teste...
    python -c "import numpy as np; import open3d as o3d; from pathlib import Path; points = np.random.rand(15000, 3) * 10; cloud = o3d.geometry.PointCloud(); cloud.points = o3d.utility.Vector3dVector(points); Path('mapas/legacy/originais_aurora').mkdir(parents=True, exist_ok=True); o3d.io.write_point_cloud('mapas/legacy/originais_aurora/teste_rapido.ply', cloud); print('✅ Arquivo de teste criado')"
)

REM Teste 3: Pipeline completo
echo 🔄 Teste 2: Pipeline Completo (Aurora → C1)
echo --------------------------------------------
python src\main_mapping.py --pipeline aurora_to_c1 --input mapas\legacy\originais_aurora --output data\pipeline_runs\teste_rapido --steps capture,refinement,map2d,annotation,export

if exist "data\pipeline_runs\teste_rapido\export" (
    echo ✅ Pipeline executado com sucesso
    echo    Resultados em: data\pipeline_runs\teste_rapido\
) else (
    echo ❌ Falha no pipeline
    exit /b 1
)
echo.

REM Resumo
echo ========================================
echo ✅ Todos os testes passaram!
echo.
echo 📚 Próximos passos:
echo    1. Veja o guia completo: docs\mapping\GUIA_USO_INICIAL.md
echo    2. Processe seus mapas reais do Aurora
echo    3. Edite os POIs gerados em: data\pipeline_runs\teste_rapido\annotation\
echo.
echo 🎉 Sistema pronto para uso!
pause

