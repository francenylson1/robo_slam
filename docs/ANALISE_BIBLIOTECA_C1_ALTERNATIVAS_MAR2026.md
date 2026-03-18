# Análise: Outra biblioteca poderia solucionar o problema? (Mar 2026)

## Resumo

Sim, **usar uma biblioteca diferente** pode ajudar, mas a solução não é garantida. O problema pode estar em **várias camadas** (biblioteca, lógica da aplicação, hardware, ambiente). Este documento analisa onde está cada parte e quais alternativas existem.

---

## 1. Onde pode estar o problema?

### Camada A — Biblioteca `rplidarc1` (dsaadatmandi)

| Aspecto | Situação | Risco |
|--------|----------|-------|
| **Origem** | Projeto comunitário (12 estrelas, 1 fork no GitHub) | Protocolo implementado por engenharia reversa, não oficial |
| **Protocolo** | C1 usa protocolo diferente de A1/A2; rplidarc1 implementa do zero | Possíveis erros de parsing (ângulo, distância, quality) |
| **Byte alignment** | A lib tenta corrigir desalinhamento de bytes | Se falhar, pontos podem ser perdidos ou incorretos |
| **Shutdown** | Documentado: "Falha de segmentação" ao encerrar | Condição de corrida ou uso indevido da serial ao fechar |
| **Manutenção** | Poucos commits recentes, 1 fork | Possível estagnação do projeto |

**Conclusão:** A rplidarc1 pode ter bugs no protocolo, no parsing ou no shutdown, gerando leituras intermitentes ou incorretas.

---

### Camada B — Lógica da aplicação (nosso código)

| Aspecto | Situação | Observação |
|--------|----------|-----------|
| **Cone frontal** | FRONT_CENTER, FRONT_WIDTH, zona parachoques | Ajustado conforme calibração; pode estar desalinhado |
| **Algoritmo de calibração** | `encontrar_angulo_obstaculo` | Corrigido: usa obstáculo mais próximo, não mais pontos |
| **Desbloqueio** | 5 scans livres + último obstáculo > 0,8 m | Conservador; não explica “às vezes não para” |
| **min_ignore** | 50 mm zona estrita, 150 mm lateral, 220 mm parachoques | Pode descartar pontos válidos ou manter ruído |
| **Frequência de decisão** | Um scan completo por decisão | Atraso ~100–200 ms entre varreduras |

**Conclusão:** A lógica da aplicação pode falhar se a biblioteca entregar dados ruins, mas o foco principal da inconsistência tende a ser na detecção (biblioteca ou sensor).

---

### Camada C — Sensor C1 (hardware)

| Aspecto | Situação | Risco |
|--------|----------|-------|
| **Superfícies** | Lixeira cilíndrica/escura, tecido, pele | Reflexão fraca em certos ângulos |
| **Taxa de varredura** | ~5–10 Hz | Objeto que entra/sai do cone entre varreduras pode não ser detectado |
| **Resolução angular** | Depende do firmware | Poucos pontos em objetos pequenos |
| **USB** | Raspberry Pi, /dev/ttyUSB0 | Possível instabilidade com outros periféricos |

**Conclusão:** Limitações físicas do sensor existem, mas não explicam sozinhos distâncias erradas (ex.: 1430 mm em vez de 500 mm) — isso aponta mais para parsing ou lógica.

---

### Camada D — Ambiente ( Raspberry Pi, USB, carregamento)

| Aspecto | Situação | Risco |
|--------|----------|-------|
| **CPU** | PyQt5, navegação, lidar em thread | Picos de carga podem atrasar leitura serial |
| **Serial** | 460800 baud | Buffer pode encher ou bytes serem perdidos sob carga |
| **Fechamento** | PyQt5 + threading + rplidarc1 | Falha de segmentação sugere conflito ao shutdown |

**Conclusão:** Ambiente pode piorar intermitência, mas é menos provável ser a causa principal dos erros de distância/ângulo.

---

## 2. Alternativas de biblioteca

### Opção 1 — `rplidar_sdk_python` (bindings do SDK oficial)

| Item | Descrição |
|------|-----------|
| **O que é** | Bindings Python do SDK oficial SLAMTEC (C++) |
| **Repositório** | [theunkn0wn1/rplidar_sdk_python](https://github.com/theunkn0wn1/rplidar_sdk_python) |
| **Vantagem** | Usa o mesmo código de protocolo testado pelo fabricante |
| **Desvantagem** | Exige compilação C++ e dependências; pode haver menos suporte explícito ao C1 |
| **Compatibility C1** | SDK oficial suporta C1; bindings Python podem precisar de configuração específica (baudrate 460800 etc.) |

**Pode resolver?** Sim, se o problema estiver no parsing/protocolo da rplidarc1.

---

### Opção 2 — SDK oficial C++ + subprocesso/HTTP

| Item | Descrição |
|------|-----------|
| **O que é** | Compilar `rplidar_sdk` (C++) e expor dados via socket, pipe ou HTTP |
| **Repositório** | [Slamtec/rplidar_sdk](https://github.com/Slamtec/rplidar_sdk) |
| **Vantagem** | Protocolo oficial, com suporte explícito ao C1 |
| **Desvantagem** | Mais integração (subprocesso, parsing, IPC); compilação para ARM na Raspberry |
| **C1** | Suportado nas plataformas oficiais (incl. Linux) |

**Pode resolver?** Sim, com mais esforço de integração.

---

### Opção 3 — Contribuir/fixar `rplidarc1`

| Item | Descrição |
|------|-----------|
| **O que é** | Investigar e corrigir bugs na rplidarc1 |
| **Repositório** | [dsaadatmandi/rplidarc1](https://github.com/dsaadatmandi/rplidarc1) |
| **Vantagem** | Mantém stack 100% Python, sem C++ |
| **Desvantagem** | Exige debug do protocolo e possível engenharia reversa |

**Pode resolver?** Sim, se o bug for identificável na rplidarc1.

---

### Opção 4 — ROS + rplidar_ros

| Item | Descrição |
|------|-----------|
| **O que é** | Usar ROS e o pacote oficial rplidar_ros |
| **Repositório** | [slamtec/rplidar_ros](https://github.com/slamtec/rplidar_ros) |
| **Vantagem** | Integração madura com outros sensores e navegação |
| **Desvantagem** | Projeto atual não usa ROS; migração grande |

**Pode resolver?** Tecnicamente sim, mas com impacto arquitetural alto.

---

## 3. Por que outra biblioteca poderia resolver?

1. **Protocolo correto** — O SDK oficial foi validado pelo fabricante; erros de parsing (ângulo/distância/quality) podem ser corrigidos.
2. **Byte alignment** — Implementação oficial lida com alinhamento do pacote; a rplidarc1 pode ter edge cases.
3. **Qualidade e sincronização** — SDK pode oferecer filtros e sincronização melhores, reduzindo ruído.
4. **Shutdown** — Encerramento controlado pode evitar falha de segmentação.

---

## 4. Onde o problema provavelmente está?

| Sintoma | Camada mais provável | Observação |
|---------|----------------------|-----------|
| Distância errada (1430 mm vs 500 mm) | **A ou B** | Parsing ou lógica de agregação (já ajustada em B) |
| “Às vezes para, às vezes não” | **A ou C** | Detecção intermitente: protocolo ou física do sensor |
| Todas as direções ≈ 270° na calibração | **B** | Bug no algoritmo (corrigido com “obstáculo mais próximo”) |
| Falha de segmentação ao sair | **A ou D** | Shutdown da rplidarc1 + threading/PyQt5 |

---

## 5. Recomendações práticas

### Curto prazo (manter rplidarc1)

1. Validar calibração novamente com o algoritmo corrigido.
2. Adicionar log das leituras brutas (`a_deg`, `d_mm`) durante a navegação.
3. Comparar com `tools/teste_c1_isolado.py` — se o teste isolado for estável e o main.py não, o problema é integração; se ambos forem instáveis, o problema é biblioteca ou sensor.

### Médio prazo (testar alternativa)

1. Avaliar `rplidar_sdk_python` no ambiente da Raspberry.
2. Criar um wrapper que ofereça a mesma interface (`a_deg`, `d_mm`) para `lidar_c1_reader`.
3. Rodar os mesmos cenários (calibração, navegação, parada) e comparar consistência.

### Longo prazo

1. Se a troca de biblioteca resolver: manter a alternativa e reportar/contribuir para a rplidarc1.
2. Se não resolver: reforçar redundância (ex.: ultrassom ou bumper) e aceitar alguma variação do C1 em certas condições.

---

## 6. Referências

- [rplidarc1](https://github.com/dsaadatmandi/rplidarc1) — Biblioteca Python atual
- [Slamtec rplidar_sdk](https://github.com/Slamtec/rplidar_sdk) — SDK oficial C++
- [rplidar_sdk_python](https://github.com/theunkn0wn1/rplidar_sdk_python) — Bindings Python do SDK
- [Issue #127 — C1 ultra_simple](https://github.com/Slamtec/rplidar_sdk/issues/127) — Notas de compatibilidade C1 (baud 460800)
