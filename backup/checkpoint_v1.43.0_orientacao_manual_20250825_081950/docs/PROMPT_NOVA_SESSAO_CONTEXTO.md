# Contexto da Sessão Atual - Foco em Sincronia de Rotação

## Versão Base de Trabalho
O projeto foi restaurado para um estado funcional e estável, baseado na versão **`v1.33-teste-forca-giro`**. Estamos trabalhando na branch **`v1.4.1-direcao-corrigida-recomeco`**.

## O Que Está Funcionando
- **Navegação de Ponto a Ponto:** O robô consegue navegar de sua posição inicial até um Ponto de Interesse (POI) selecionado.
- **Sincronia de Direção:** O robô físico e o robô da interface giram para o mesmo lado (esquerda/direita) de forma consistente.

## Problema Prioritário
Existe uma **dessincronização na escala da rotação dos botões left, right, uo, down**.
- **Sintoma:** Quando o robô físico executa um giro de **90 graus** através dos botões, o robô na interface gira apenas a metade, aproximadamente **45 graus**.
- **Impacto:** A representação visual do robô no mapa torna-se imprecisa, comprometendo a odometria e a confiança do operador na interface.

## Objetivo Imediato
- **Ajustar e sincronizar a escala do giro:** Modificar o cálculo da odometria para que a rotação na interface seja um reflexo 1:1 da rotação do robô físico.

## Restrições Críticas
- **Foco Cirúrgico:** As alterações devem se limitar estritamente a corrigir o cálculo do ângulo de rotação.
- **Não alterar outras funcionalidades:** A navegação básica, o controle dos motores e outras partes que já funcionam não devem ser afetadas.


