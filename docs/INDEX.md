# 📚 Índice da Documentação - Robô Garçom Autônomo

Este arquivo fornece uma visão geral de toda a documentação do projeto.

## 🎯 Documentação Principal

### Projeto e Visão Geral
- [README.md](README.md) - Visão geral do projeto
- [PROJETO_ROBO_GARCOM.md](PROJETO_ROBO_GARCOM.md) - Documentação completa do projeto
- [PROJETO Robô Garçom Autônomo.md](PROJETO%20Robô%20Garçom%20Autônomo.md) - Descrição detalhada

## 🏗️ Checkpoints e Versões Estáveis

### Checkpoints Principais
- [CHECKPOINT_SEGURANCA_v1.41.03.md](CHECKPOINT_SEGURANCA_v1.41.03.md)
- [CHECKPOINT_v1.42.0_ESTAVEL.md](CHECKPOINT_v1.42.0_ESTAVEL.md)
- [VERSION_BASE_ESTAVEL.md](VERSION_BASE_ESTAVEL.md)

### Marcos de Desenvolvimento
- [MARCO_v1.43.0_NAVEGACAO_POI_PERFEITA.md](MARCO_v1.43.0_NAVEGACAO_POI_PERFEITA.md)

## 🔧 Implementações e Melhorias

### Navegação e Orientação
- [IMPLEMENTACAO_ORIENTACAO_MANUAL_v1.43.0.md](IMPLEMENTACAO_ORIENTACAO_MANUAL_v1.43.0.md)
- [MELHORIAS_SINCRONIA_v1.44.0.md](MELHORIAS_SINCRONIA_v1.44.0.md)

### Correções
- [CORRECAO_INVERSAO_DIRECAO.md](CORRECAO_INVERSAO_DIRECAO.md)
- [CORRECAO_INVERSAO_DIRECAO_SINCRONIA.md](CORRECAO_INVERSAO_DIRECAO_SINCRONIA.md)
- [CORRECAO_LOOP_360_V1.44.0.md](CORRECAO_LOOP_360_V1.44.0.md)

### Melhorias Específicas
- [RESUMO_MELHORIAS_AREAS_PROIBIDAS.md](RESUMO_MELHORIAS_AREAS_PROIBIDAS.md)

## 🧪 Testes e Calibração

- [INSTRUCOES_TESTE_DIRECAO.md](INSTRUCOES_TESTE_DIRECAO.md)
- [INSTRUCOES_TESTE_RASPBERRY_PI.md](INSTRUCOES_TESTE_RASPBERRY_PI.md)
- [CALCULO_TPS_SEGURO.md](CALCULO_TPS_SEGURO.md)

## 📝 Prompts e Contextos de Desenvolvimento

### Prompts Principais
- [PROMPT_CONTEXTO_ATUAL.md](PROMPT_CONTEXTO_ATUAL.md)
- [PROMPT_NOVA_SESSAO_CONTEXTO.md](PROMPT_NOVA_SESSAO_CONTEXTO.md)
- [PROMPT_NOVA_SESSAO_16092025.md](PROMPT_NOVA_SESSAO_16092025.md)
- [prompt_inicial_trae.md](prompt_inicial_trae.md)
- [prompt_17-09-2025.md](prompt_17-09-2025.md)

### Prompts por Data - Junho 2025
- [prompt_23-06-2025.md](prompt_23-06-2025.md)
- [prompt_23-06-2025-1800.md](prompt_23-06-2025-1800.md)
- [prompt_23-06-2025-2000.md](prompt_23-06-2025-2000.md)
- [prompt_24-06-2025.md](prompt_24-06-2025.md)

### Prompts por Data - Julho 2025
- [prompt_07-07-2025-0857.md](prompt_07-07-2025-0857.md)

### Prompts por Data - Agosto 2025
- [PROMPT_NOVO_CHAT_01082025.md](PROMPT_NOVO_CHAT_01082025.md)
- [PROMPT_NOVO_CHAT_02082025.md](PROMPT_NOVO_CHAT_02082025.md)
- [PROMPT_NOVO_CHAT_04082025.md](PROMPT_NOVO_CHAT_04082025.md)
- [PROMPT_NOVO_CHAT_05082025.md](PROMPT_NOVO_CHAT_05082025.md)
- [prompt_11_08_2025.md](prompt_11_08_2025.md)
- [prompt_18-08-2025.md](prompt_18-08-2025.md)
- [PROMPT_22-08-2025.md](PROMPT_22-08-2025.md)
- [PROMPT_22-08-2025_RESTAURACAO_VERSAO_ESTAVEL.md](PROMPT_22-08-2025_RESTAURACAO_VERSAO_ESTAVEL.md)
- [PROMPT_25-08-2025.md](PROMPT_25-08-2025.md)
- [PROMPT_27-08-2025.md](PROMPT_27-08-2025.md)
- [referencia_para_18-08-2025.md](referencia_para_18-08-2025.md)

### Prompts Gerais
- [PROMPT_NOVO_CHAT.md](PROMPT_NOVO_CHAT.md)
- [prompt_proximos_passos.md](prompt_proximos_passos.md)

## 📊 Resumos e Contextos

- [RESUMO_AUTOSAVE.md](RESUMO_AUTOSAVE.md)
- [RESUMO_SESSAO_ATUAL.md](RESUMO_SESSAO_ATUAL.md)
- [CONTEXTO_PRE_CALIBRACAO.md](CONTEXTO_PRE_CALIBRACAO.md)

## 🎓 Tutoriais e Guias

- [Tutorial_Versionamento_Git.md](Tutorial_Versionamento_Git.md)
- [etapas_finais.md](etapas_finais.md)

## 📂 Estrutura de Pastas do Projeto

```
robo_slam/
├── docs/               # Documentação (você está aqui!)
├── mapas/              # Sistema de gestão de mapas
│   ├── originais_aurora/    # Mapas brutos do sensor
│   ├── otimizados/          # Mapas processados
│   ├── pois/                # Pontos de Interesse
│   ├── areas_proibidas/     # Áreas restritas
│   └── templates/           # Templates de configuração
├── src/                # Código fonte principal
│   ├── core/           # Módulos principais
│   └── interfaces/     # Interface gráfica
├── tests/              # Testes e scripts de calibração
├── data/               # Banco de dados
└── backup/             # Backups de versões anteriores
```

## 🔗 Links Úteis

- [Mapas - README](../mapas/README.md) - Documentação do sistema de mapas
- [Requirements](../requirements.txt) - Dependências do projeto

## 📅 Última Atualização

- **Data:** 19/11/2025
- **Versão do Projeto:** v2.0
- **Branch Atual:** v2.0-robo-com-3cm-do-chao-testes-em-linha-reta

---

**Nota:** Esta documentação é atualizada continuamente. Para contribuir, siga as diretrizes em [PROJETO_ROBO_GARCOM.md](PROJETO_ROBO_GARCOM.md).

