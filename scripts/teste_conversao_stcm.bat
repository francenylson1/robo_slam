@echo off
REM Script de teste rápido para conversão .stcm → .ply usando SDK do Aurora

echo 🧪 Teste de Conversão .stcm → .ply com SDK do Aurora
echo ==================================================
echo.

REM Verifica se estamos no diretório correto
if not exist "src\main_mapping.py" (
    echo ❌ Erro: Execute este script a partir do diretório raiz do projeto
    exit /b 1
)

REM Verifica se o arquivo .stcm existe
set STCM_FILE=mapas\legacy\originais_aurora\sala-maker-1.stcm
if not exist "%STCM_FILE%" (
    echo ⚠️  Arquivo .stcm não encontrado: %STCM_FILE%
    echo    Procurando outros arquivos .stcm...
    for /r mapas %%f in (*.stcm) do (
        set STCM_FILE=%%f
        goto :found
    )
    echo ❌ Nenhum arquivo .stcm encontrado em mapas\
    exit /b 1
)
:found

echo ✅ Arquivo .stcm encontrado: %STCM_FILE%

REM Verifica configuração do Aurora
echo.
echo 📋 Verificando configuração...
findstr /C:"\"enabled\": true" config\mapping.json >nul
if %errorlevel% equ 0 (
    echo ✅ SDK do Aurora está habilitado
) else (
    echo ⚠️  SDK do Aurora está DESABILITADO em config\mapping.json
    echo    Configure "aurora.enabled: true" para usar o SDK
    set /p CONTINUE="   Deseja continuar mesmo assim? (s/N): "
    if /i not "%CONTINUE%"=="s" exit /b 1
)

REM Verifica se o SDK existe
set SDK_PATH=py_aurora_remote-main\python_bindings
if exist "%SDK_PATH%" (
    echo ✅ SDK do Aurora encontrado em: %SDK_PATH%
) else (
    echo ❌ SDK do Aurora não encontrado em: %SDK_PATH%
    exit /b 1
)

REM Diretório de saída
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set OUTPUT_DIR=data\pipeline_runs\teste_stcm_%datetime:~0,8%_%datetime:~8,6%
echo.
echo 📁 Diretório de saída: %OUTPUT_DIR%
echo.

REM Executa o teste
echo 🚀 Executando conversão...
echo    Pipeline: Aurora → C1
echo    Input: %STCM_FILE%
echo    Output: %OUTPUT_DIR%
echo    Steps: capture,refinement
echo.

python src\main_mapping.py --pipeline aurora_to_c1 --input "%STCM_FILE%" --output "%OUTPUT_DIR%" --steps capture,refinement

REM Verifica resultado
echo.
echo 🔍 Verificando resultados...

for /r "%OUTPUT_DIR%\refinement" %%f in (*.ply) do (
    set PLY_FILE=%%f
    goto :check_size
)

echo ❌ Erro: Arquivo .ply não foi gerado
echo    Verifique os logs acima para mais detalhes
exit /b 1

:check_size
if exist "%PLY_FILE%" (
    for %%A in ("%PLY_FILE%") do set SIZE=%%~zA
    if %SIZE% gtr 0 (
        echo ✅ Arquivo .ply gerado com sucesso!
        echo    Arquivo: %PLY_FILE%
        echo    Tamanho: %SIZE% bytes
        echo.
        echo ✅ Teste concluído com sucesso!
        exit /b 0
    )
)

echo ❌ Erro: Arquivo .ply está vazio
echo    Verifique os logs acima para mais detalhes
exit /b 1

