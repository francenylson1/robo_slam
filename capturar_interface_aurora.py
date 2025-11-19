"""
Script para ajudar a identificar elementos na interface do Aurora
Fornece perguntas guiadas para localizar o menu de exportação.
"""

def guia_interativo():
    """
    Guia interativo para encontrar o menu de exportação.
    """
    print("=" * 60)
    print("🔍 GUIA INTERATIVO: Encontrar Exportação no Aurora")
    print("=" * 60)
    print()
    print("Vou fazer algumas perguntas para te ajudar a encontrar o menu.")
    print()
    
    # Pergunta 1: Menu principal
    print("1️⃣  No topo da página, você vê algum menu horizontal?")
    print("    (Ex: Home, Map, Settings, About, etc.)")
    resposta = input("    Digite os nomes dos menus que você vê (ou 'não'): ").strip().lower()
    
    if 'map' in resposta or 'mapa' in resposta:
        print("\n✅ Ótimo! Clique em 'Map' ou 'Mapa'")
        print("   Depois me diga o que aparece na tela.")
    elif resposta != 'não' and resposta:
        print(f"\n💡 Você mencionou: {resposta}")
        print("   Procure por algo relacionado a 'Map' ou 'Maps'")
        print("   Ou me diga qual menu parece mais relacionado a mapas.")
    
    # Pergunta 2: Menu lateral
    print("\n2️⃣  No lado esquerdo da tela, há um menu vertical?")
    print("    (Ex: lista de opções, ícones, etc.)")
    resposta = input("    Digite o que você vê (ou 'não'): ").strip().lower()
    
    if 'map' in resposta or 'mapa' in resposta:
        print("\n✅ Perfeito! Clique nessa opção de mapa.")
    elif resposta != 'não' and resposta:
        print(f"\n💡 Você vê: {resposta}")
        print("   Procure por algo relacionado a mapas nessa lista.")
    
    # Pergunta 3: Conteúdo central
    print("\n3️⃣  No centro da tela, o que você vê?")
    print("    a) Um mapa visual")
    print("    b) Uma lista de mapas")
    print("    c) Informações do dispositivo")
    print("    d) Outro")
    resposta = input("    Escolha a, b, c ou d: ").strip().lower()
    
    if resposta == 'a':
        print("\n💡 Você vê um mapa visual!")
        print("   Procure por:")
        print("   - Botões ao redor do mapa")
        print("   - Menu de contexto (botão direito)")
        print("   - Ícone de download/exportar")
        print("   - Menu no canto superior direito do mapa")
    elif resposta == 'b':
        print("\n✅ Perfeito! Você vê uma lista de mapas!")
        print("   Agora:")
        print("   1. Clique no mapa que deseja exportar")
        print("   2. Procure por botões como:")
        print("      - 'Export' ou 'Exportar'")
        print("      - 'Download'")
        print("      - Três pontos (...) → menu com opções")
        print("   3. Ou clique com botão direito no mapa")
    elif resposta == 'c':
        print("\n💡 Você está na página de informações.")
        print("   Procure por um menu ou link para 'Maps' ou 'Mapas'")
    else:
        print("\n💡 Descreva o que você vê no centro da tela.")
    
    # Pergunta 4: Botões visíveis
    print("\n4️⃣  Você vê algum destes botões/ícones na tela?")
    print("    - 📥 Download (seta para baixo)")
    print("    - 💾 Save/Save As")
    print("    - 📤 Export/Exportar")
    print("    - ☰ Menu (três linhas)")
    print("    - ⚙️ Settings/Configurações")
    resposta = input("    Digite quais você vê (ou 'nenhum'): ").strip().lower()
    
    if 'download' in resposta or 'export' in resposta:
        print("\n✅ Perfeito! Clique nesse botão!")
    elif 'menu' in resposta or '☰' in resposta:
        print("\n💡 Clique no menu (☰) e procure por 'Map' ou 'Maps'")
    elif 'settings' in resposta or 'config' in resposta:
        print("\n💡 Clique em Settings e procure por 'Maps' ou 'Map Management'")
    elif resposta != 'nenhum':
        print(f"\n💡 Você vê: {resposta}")
        print("   Tente clicar e ver o que acontece!")
    
    print("\n" + "=" * 60)
    print("📋 RESUMO DO QUE FAZER:")
    print("=" * 60)
    print("1. Procure por qualquer menu/link que diga 'Map', 'Maps' ou 'Mapa'")
    print("2. Clique nele")
    print("3. Procure por uma lista de mapas salvos")
    print("4. Clique no mapa desejado")
    print("5. Procure por botão 'Export', 'Download' ou três pontos (...)")
    print("6. Escolha formato PLY ou PCD")
    print("7. Salve em: D:\\robo_slam\\mapas\\originais_aurora\\")
    print()
    print("💡 Se ainda não encontrar, me diga:")
    print("   - Quais menus/opções você vê na tela")
    print("   - Ou tire uma captura de tela")
    print("=" * 60)


if __name__ == "__main__":
    try:
        guia_interativo()
    except KeyboardInterrupt:
        print("\n\n👋 Guia interrompido. Boa sorte!")

