# Robô Garçom Autônomo

Projeto de robô garçom autônomo desenvolvido para navegação inteligente em ambientes controlados.

## 🚀 Características

- Navegação autônoma com detecção de obstáculos
- Interface gráfica para controle e monitoramento
- Mapeamento do ambiente em tempo real
- Sistema de pontos de interesse
- Áreas proibidas configuráveis
- Alternância entre modo manual e autônomo

## 🛠️ Requisitos

- Python 3.8+
- Raspberry Pi 4 (4GB)
- Sensores LIDAR (Aurora e C1 Slamtec)
- Motores controlados via GPIO

## 📦 Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/robo_slam.git
cd robo_slam
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

## 🎮 Uso

1. Execute o programa principal:
```bash
python src/main.py
```

2. Na interface gráfica:
   - Use o modo manual para controle via joystick
   - Configure pontos de interesse no mapa
   - Defina áreas proibidas
   - Ative o modo autônomo para navegação automática

## 📝 Estrutura do Projeto

```
robo_slam/
├── src/
│   ├── core/           # Núcleo do sistema
│   ├── interfaces/     # Interface gráfica
│   └── main.py         # Ponto de entrada
├── data/              # Dados do mapa e configurações
├── logs/              # Logs do sistema
└── tests/             # Testes unitários
```

## 🤝 Contribuindo

1. Faça um Fork do projeto
2. Crie uma Branch para sua Feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a Branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## ✨ Agradecimentos

- Projeto Aluno Maker Digital
- Comunidade de robótica educacional
- Contribuidores e testadores 