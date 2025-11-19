@echo off
REM Script para atualizar o Git com todas as mudanças
echo ========================================
echo Atualizando Git - Sistema Aurora → C1
echo ========================================
echo.

echo [1/4] Adicionando todos os arquivos...
git add -A
if errorlevel 1 (
    echo ERRO ao adicionar arquivos
    pause
    exit /b 1
)
echo OK
echo.

echo [2/4] Verificando status...
git status --short
echo.

echo [3/4] Fazendo commit...
git commit -m "Implementação completa: Sistema de processamento de mapas Aurora → C1 e interface para POIs/Áreas" -m "Novas funcionalidades:" -m "- Sistema completo de processamento de mapas do Aurora para C1" -m "- Módulos: aurora_connector, stcm_processor, map_converter_3d_to_2d, pgm_yaml_generator, slamware_c1_uploader" -m "- Pipeline completo aurora_to_c1_pipeline.py" -m "- Scripts de conversão: converter_bmp_para_mapa.py, converter_ply_para_mapa.py" -m "- Interface: Carregar mapa PGM como fundo no MapWidget" -m "- Interface: Exportar/Importar POIs e Áreas Proibidas em JSON" -m "- Documentação completa: guias de uso, fluxos, troubleshooting" -m "- Scripts auxiliares: visualizar_mapa.py, processar_mapa.bat, etc." -m "- Estrutura de pastas organizada: mapas/originais_aurora, mapas/otimizados, mapas/pois, mapas/areas_proibidas" -m "- Requirements atualizado com dependências (open3d, Pillow, PyYAML, requests)" -m "- Compatibilidade: Todas funcionalidades existentes mantidas, novas são opcionais"
if errorlevel 1 (
    echo ERRO ao fazer commit
    pause
    exit /b 1
)
echo OK
echo.

echo [4/4] Fazendo push para o repositório remoto...
git push origin v2.0-robo-com-3cm-do-chao-testes-em-linha-reta
if errorlevel 1 (
    echo ERRO ao fazer push
    echo Verifique sua conexão e autenticação
    pause
    exit /b 1
)
echo OK
echo.

echo ========================================
echo ✅ Git atualizado com sucesso!
echo ========================================
echo.
echo Você pode continuar no Ubuntu/Raspberry Pi com:
echo   git pull origin v2.0-robo-com-3cm-do-chao-testes-em-linha-reta
echo.
pause

