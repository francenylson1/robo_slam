@echo off
REM Script para processar mapa do Aurora (BMP ou PLY/PCD)
REM Uso: processar_mapa.bat nome_do_arquivo [formato]
REM Exemplo: processar_mapa.bat sala-maker-1 bmp

if "%1"=="" (
    echo Uso: processar_mapa.bat nome_do_arquivo [formato]
    echo Formatos: bmp, ply, pcd
    echo Exemplo: processar_mapa.bat sala-maker-1 bmp
    exit /b 1
)

set NOME=%1
set FORMATO=%2

if "%FORMATO%"=="" set FORMATO=bmp

echo ========================================
echo Processando mapa: %NOME%
echo Formato: %FORMATO%
echo ========================================
echo.

if "%FORMATO%"=="bmp" (
    echo [1/3] Convertendo BMP para PGM+YAML...
    py converter_bmp_para_mapa.py mapas/originais_aurora/%NOME%.bmp --output %NOME%
    if errorlevel 1 (
        echo ERRO: Falha na conversao
        exit /b 1
    )
) else if "%FORMATO%"=="ply" (
    echo [1/3] Convertendo PLY para PGM+YAML...
    py converter_ply_para_mapa.py mapas/originais_aurora/%NOME%.ply --output %NOME%
    if errorlevel 1 (
        echo ERRO: Falha na conversao
        exit /b 1
    )
) else if "%FORMATO%"=="pcd" (
    echo [1/3] Convertendo PCD para PGM+YAML...
    py converter_ply_para_mapa.py mapas/originais_aurora/%NOME%.pcd --output %NOME%
    if errorlevel 1 (
        echo ERRO: Falha na conversao
        exit /b 1
    )
) else (
    echo ERRO: Formato desconhecido: %FORMATO%
    echo Formatos suportados: bmp, ply, pcd
    exit /b 1
)

echo.
echo [2/3] Visualizando mapa gerado...
py visualizar_mapa.py mapas/otimizados/%NOME%.pgm

echo.
echo [3/3] Verificando arquivos gerados...
if exist "mapas\otimizados\%NOME%.pgm" (
    echo [OK] PGM: mapas\otimizados\%NOME%.pgm
) else (
    echo [ERRO] Arquivo PGM nao encontrado
)

if exist "mapas\otimizados\%NOME%.yaml" (
    echo [OK] YAML: mapas\otimizados\%NOME%.yaml
) else (
    echo [ERRO] Arquivo YAML nao encontrado
)

echo.
echo ========================================
echo Processamento concluido!
echo Mapa pronto em: mapas\otimizados\%NOME%.pgm
echo ========================================
pause

