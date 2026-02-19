#!/usr/bin/env python3
"""
Script de processamento de mapas BMP do Aurora Remote para formato PGM/YAML.
Converte mapas brutos do Aurora em mapas metrificados e corrigidos para uso na aplicação.
"""

import cv2
import numpy as np
from PIL import Image
from pathlib import Path
import argparse
import sys

# ------------------------------------------
# CONFIGURAÇÕES DO AMBIENTE
# ------------------------------------------
TARGET_WIDTH_METERS = 12.0   # eixo maior
TARGET_HEIGHT_METERS = 6.0   # eixo menor

# ------------------------------------------
# FUNÇÕES DE PROCESSAMENTO
# ------------------------------------------

def process_aurora_map(input_bmp: str, output_dir: str, map_name: str = "mapa_final"):
    """
    Processa mapa BMP do Aurora Remote e gera arquivos PGM, YAML e PNG.
    
    Args:
        input_bmp: Caminho para o arquivo BMP original
        output_dir: Diretório de saída (será criada subpasta com nome do mapa)
        map_name: Nome base para os arquivos gerados
    """
    input_path = Path(input_bmp)
    if not input_path.exists():
        print(f"❌ Erro: Arquivo não encontrado: {input_bmp}")
        return False
    
    # Cria diretório de saída
    output_path = Path(output_dir)
    map_subdir = output_path / map_name
    map_subdir.mkdir(parents=True, exist_ok=True)
    
    print(f"📂 Processando: {input_bmp}")
    print(f"📁 Saída: {map_subdir}")
    print()
    
    # ------------------------------------------
    # 1 — CARREGAR BMP ORIGINAL
    # ------------------------------------------
    print("1️⃣ Carregando BMP original...")
    img = cv2.imread(str(input_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"❌ Erro: Não foi possível carregar a imagem: {input_bmp}")
        return False
    print(f"   ✅ Imagem carregada: {img.shape[1]}x{img.shape[0]} pixels")
    
    # ------------------------------------------
    # 2 — CORREÇÃO DE ROTAÇÃO
    # ------------------------------------------
    print("2️⃣ Aplicando rotação (90° horário)...")
    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    print(f"   ✅ Rotacionado: {img.shape[1]}x{img.shape[0]} pixels")
    
    # ------------------------------------------
    # 3 — CORREÇÃO DE ESPELHAMENTO
    # ------------------------------------------
    print("3️⃣ Aplicando espelhamento horizontal...")
    img = cv2.flip(img, 1)
    print(f"   ✅ Espelhado")
    
    # ------------------------------------------
    # 4 — REMOVER BORDAS E ÁREAS CINZA
    # ------------------------------------------
    print("4️⃣ Removendo bordas e áreas cinza...")
    _, bin_map = cv2.threshold(img, 240, 255, cv2.THRESH_BINARY)
    print(f"   ✅ Binarização aplicada")
    
    # ------------------------------------------
    # 5 — DETECTAR CONTORNO PRINCIPAL
    # ------------------------------------------
    print("5️⃣ Detectando contorno principal e recortando...")
    contours, _ = cv2.findContours(bin_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        print("❌ Erro: Nenhum contorno encontrado na imagem")
        return False
    
    cnt = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(cnt)
    cropped = bin_map[y:y+h, x:x+w]
    print(f"   ✅ Recortado: {w}x{h} pixels (posição: {x}, {y})")
    
    # ------------------------------------------
    # 6 — REESCALAR PARA METRIFICAÇÃO
    # ------------------------------------------
    print("6️⃣ Calculando metrificação...")
    if w > h:
        px_per_meter = w / TARGET_WIDTH_METERS
    else:
        px_per_meter = h / TARGET_HEIGHT_METERS
    
    RESOLUTION = 1.0 / px_per_meter  # metros por pixel
    print(f"   ✅ Resolução: {RESOLUTION:.4f} m/pixel")
    print(f"   ✅ Dimensões: {w * RESOLUTION:.2f}m x {h * RESOLUTION:.2f}m")
    
    # ------------------------------------------
    # 7 — CONVERTER PARA PGM
    # ------------------------------------------
    print("7️⃣ Convertendo para PGM...")
    pgm_map = (255 - cropped).astype(np.uint8)
    pgm_path = map_subdir / f"{map_name}.pgm"
    Image.fromarray(pgm_map).save(str(pgm_path))
    print(f"   ✅ PGM salvo: {pgm_path}")
    
    # ------------------------------------------
    # 8 — GERAR YAML
    # ------------------------------------------
    print("8️⃣ Gerando arquivo YAML...")
    yaml_content = f"""image: {map_name}.pgm
resolution: {RESOLUTION:.6f}
origin: [0.0, 0.0, 0.0]
occupied_thresh: 0.65
free_thresh: 0.196
negate: 0
"""
    yaml_path = map_subdir / f"{map_name}.yaml"
    with open(yaml_path, "w") as f:
        f.write(yaml_content)
    print(f"   ✅ YAML salvo: {yaml_path}")
    
    # ------------------------------------------
    # 9 — GERAR PNG PARA VISUALIZAÇÃO
    # ------------------------------------------
    print("9️⃣ Gerando PNG para visualização...")
    png_path = map_subdir / f"{map_name}_refinado.png"
    Image.fromarray(cropped).save(str(png_path))
    print(f"   ✅ PNG salvo: {png_path}")
    
    # ------------------------------------------
    # RESUMO
    # ------------------------------------------
    print()
    print("=" * 60)
    print("✅ PROCESSAMENTO CONCLUÍDO!")
    print("=" * 60)
    print(f"📁 Diretório: {map_subdir}")
    print(f"📄 Arquivos gerados:")
    print(f"   - {map_name}.pgm")
    print(f"   - {map_name}.yaml")
    print(f"   - {map_name}_refinado.png")
    print()
    
    return True


def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(
        description="Processa mapas BMP do Aurora Remote para formato PGM/YAML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Processar mapa básico
  python src/c1_scanner/main_scanner.py mapa_original.bmp

  # Especificar diretório de saída e nome do mapa
  python src/c1_scanner/main_scanner.py mapa_original.bmp \\
    --output C1_mapas_processados \\
    --name c1_sala_maker

  # Processar com configurações customizadas
  python src/c1_scanner/main_scanner.py mapa.bmp \\
    --output mapas/processados \\
    --name meu_mapa
        """
    )
    
    parser.add_argument(
        "input_bmp",
        type=str,
        help="Caminho para o arquivo BMP original do Aurora Remote"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="src/c1_scanner/C1_mapas_processados",
        help="Diretório de saída (padrão: src/c1_scanner/C1_mapas_processados)"
    )
    parser.add_argument(
        "--name", "-n",
        type=str,
        default=None,
        help="Nome base para os arquivos gerados (padrão: nome do arquivo BMP sem extensão)"
    )
    
    args = parser.parse_args()
    
    # Determina nome do mapa se não fornecido
    if args.name is None:
        args.name = Path(args.input_bmp).stem
    
    # Processa o mapa
    success = process_aurora_map(
        input_bmp=args.input_bmp,
        output_dir=args.output,
        map_name=args.name
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()









