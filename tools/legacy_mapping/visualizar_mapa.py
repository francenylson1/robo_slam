"""
Script de Visualização de Mapas PGM
Visualiza e analisa mapas gerados pelo pipeline Aurora → C1.
"""

import numpy as np
from PIL import Image
import yaml
import sys
from pathlib import Path


def visualizar_mapa(pgm_path):
    """Visualiza mapa PGM gerado."""
    pgm_path = Path(pgm_path)
    
    if not pgm_path.exists():
        print(f"❌ Arquivo não encontrado: {pgm_path}")
        return
    
    print(f"📁 Carregando mapa: {pgm_path}")
    
    # Lê PGM
    try:
        img = Image.open(pgm_path)
        img_array = np.array(img)
    except Exception as e:
        print(f"❌ Erro ao ler arquivo PGM: {e}")
        return
    
    # Informações básicas
    print(f"\n📊 Informações do Mapa:")
    print(f"   Tamanho: {img_array.shape[1]} x {img_array.shape[0]} pixels")
    print(f"   Tipo: {img_array.dtype}")
    print(f"   Valores únicos: {sorted(np.unique(img_array))}")
    
    # Estatísticas
    ocupado = np.sum(img_array == 0)
    livre = np.sum(img_array == 255)
    desconhecido = np.sum(img_array == 205)
    total = img_array.size
    
    print(f"\n📈 Estatísticas:")
    print(f"   Ocupado (preto):     {ocupado:8d} pixels ({ocupado/total*100:6.2f}%)")
    print(f"   Livre (branco):      {livre:8d} pixels ({livre/total*100:6.2f}%)")
    print(f"   Desconhecido (cinza): {desconhecido:8d} pixels ({desconhecido/total*100:6.2f}%)")
    print(f"   Total:               {total:8d} pixels")
    
    # Lê YAML se disponível
    yaml_path = pgm_path.with_suffix('.yaml')
    if yaml_path.exists():
        try:
            with open(yaml_path, 'r') as f:
                metadata = yaml.safe_load(f)
            
            print(f"\n📋 Metadados (YAML):")
            print(f"   Resolução: {metadata.get('resolution', 'N/A')} m/pixel")
            print(f"   Origem: {metadata.get('origin', 'N/A')}")
            print(f"   Imagem: {metadata.get('image', 'N/A')}")
            
            # Calcula dimensões reais
            if 'resolution' in metadata:
                res = metadata['resolution']
                width_m = img_array.shape[1] * res
                height_m = img_array.shape[0] * res
                print(f"   Dimensões reais: {width_m:.2f} m x {height_m:.2f} m")
        except Exception as e:
            print(f"⚠️  Erro ao ler YAML: {e}")
    else:
        print(f"\n⚠️  Arquivo YAML não encontrado: {yaml_path}")
    
    # Cria versão colorida para visualização
    print(f"\n🎨 Gerando visualização colorida...")
    color_img = Image.new('RGB', img.size)
    pixels = color_img.load()
    
    for i in range(img.size[0]):
        for j in range(img.size[1]):
            val = img_array[j, i]
            if val == 0:  # Ocupado - vermelho
                pixels[i, j] = (255, 0, 0)
            elif val == 255:  # Livre - branco
                pixels[i, j] = (255, 255, 255)
            elif val == 205:  # Desconhecido - cinza
                pixels[i, j] = (128, 128, 128)
            else:  # Outros valores - amarelo (para debug)
                pixels[i, j] = (255, 255, 0)
    
    output_path = pgm_path.with_name(pgm_path.stem + '_colorido.png')
    color_img.save(output_path)
    print(f"✅ Mapa colorido salvo em: {output_path}")
    
    # Tenta abrir a imagem
    try:
        import os
        os.startfile(output_path)  # Windows
        print(f"✅ Imagem aberta no visualizador padrão")
    except:
        print(f"💡 Abra manualmente: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        visualizar_mapa(sys.argv[1])
    else:
        print("Uso: python visualizar_mapa.py <caminho_para_mapa.pgm>")
        print("\nExemplo:")
        print("  python visualizar_mapa.py mapas/otimizados/teste_sala_maker.pgm")

