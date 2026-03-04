# Revisão: BNO e desvio para esquerda na linha reta

## Resumo

Após as alterações para ativar o BNO (`do_reset_cycle=False` em todos os scripts), o robô passou a desviar para a **esquerda** no teste de linha reta, embora antes navegasse em linha reta. A alteração foi **apenas** para o BNO funcionar; a lógica de correção e o restante não foram mudados de propósito.

---

## Por que não funcionou inicialmente? (explicação detalhada)

### 1. O que o BNO08x envia e em que ordem

O BNO085/080 fala com o host por um protocolo chamado **SHTP** (Sensor Hub Transport Protocol). O sensor **não** envia um único “ângulo atual”; ele envia **vários tipos de relatório** em pacotes separados, por I2C:

- **ACCELEROMETER** (0x01) – aceleração
- **GYROSCOPE** (0x02) – velocidade angular
- **ROTATION_VECTOR** (0x05) – orientação (quaternion → yaw que usamos)
- Outros (BASE_TIMESTAMP, PRODUCT_ID_REQUEST, etc.)

Quando o código faz `enable_feature(ROTATION_VECTOR)`, o sensor **começa** a configurar e a enviar esses relatórios. A ordem e o tempo até o **primeiro** ROTATION_VECTOR chegar **não são garantidos**: o firmware pode enviar antes outros pacotes (timestamp, gyro, accel, metadados). Ou seja: logo após o init, a **primeira** leitura que o nosso código pede pode ser feita **antes** de qualquer pacote ROTATION_VECTOR ter sido recebido e processado.

### 2. O que o nosso código faz com essa leitura

No teste de linha reta o fluxo era (antes do ajuste):

1. Inicializar BNO (`bno08x_init`) → sensor conectado, features habilitadas, retorna `(bno, get_bno_yaw)`.
2. **Uma única chamada** `yaw_ref = get_bno_yaw()` **antes** do laço de movimento.
3. Se `yaw_ref is None` → imprimir “BNO sem leitura” e seguir mesmo assim.
4. No laço a cada 30 ms: `left_tps, right_tps = compute_straight_correction(yaw_ref ou 0.0, get_bno_yaw, ...)`.

A função `get_bno_yaw()` lê `bno.quaternion` e converte para yaw em graus. **Se ainda não existir um quaternion válido** (nenhum ROTATION_VECTOR processado), a biblioteca pode lançar exceção ou retornar algo inválido; no nosso código isso vira `None` no `except`.

Conclusão: a **primeira** chamada a `get_bno_yaw()` acontecia **muito cedo** – antes do primeiro ROTATION_VECTOR – e por isso `yaw_ref` ficava `None`.

### 3. O que acontece quando yaw_ref é None no laço

Quando `yaw_ref is None`, o teste usa `yaw_ref = 0.0` dentro do laço (só para não quebrar o cálculo):

- `compute_straight_correction(0.0, get_bno_yaw, base_tps, ...)`.
- Cada vez que `get_bno_yaw()` retorna `None`, a função retorna **(base_tps, base_tps)** – ou seja, **nenhuma correção**, as duas rodas iguais.

Então, na prática:

- **Referência**: estamos “tentando” manter o rumo em **0°** (arbitrário), mas o robô pode ter começado com rumo real diferente (ex.: -2°).
- **Durante o teste**: na maior parte do tempo `get_bno_yaw()` ainda retornava `None` (ROTATION_VECTOR atrasado ou taxa menor que o nosso laço de 30 ms), então **quase sempre** o comando era (base_tps, base_tps).
- **Efeito**: o robô andava **sem correção de rumo**. Qualquer assimetria (motor esquerdo vs direito, piso, peso) virava deriva. Nos seus logs a deriva foi para a **esquerda** (~-12° em 10 s).

Ou seja: **não foi bug de sinal (inverter correção)**. O problema foi **nunca ter uma referência válida** e **quase nunca ter leitura no laço**, então a correção simplesmente não atuou.

### 4. Por que “ontem” parecia ir reto e “hoje” desviava

- **Com `do_reset_cycle=True`**: o ciclo LOW→HIGH no RST podia gerar o pacote 0x7B e deixar o BNO “indisponível” ou instável. Em muitos casos o init **falhava** e o teste rodava **sem BNO** (get_bno_yaw = None sempre). Aí o comportamento era o mesmo: (base_tps, base_tps), sem correção. Em alguns casos (piso, bateria, duração) a assimetria era pequena e o robô parecia ir reto.
- **Com `do_reset_cycle=False`**: o BNO **sempre** conecta. O teste **tem** BNO, mas a primeira leitura ainda era feita cedo demais e no laço havia muitas leituras `None`. Resultado: de novo (base_tps, base_tps) na prática, mas com I2C ativo e possivelmente mais tráfego/atraso (e dump DBG), o que pode ter deixado a deriva mais visível.

Resumindo: a diferença não foi “lógica invertida”, e sim **timing**: quando o BNO passou a estar sempre presente, ficou claro que **não tínhamos referência nem leituras a tempo**; o comportamento “reto” de antes era **sem correção**, com pouca deriva em algumas condições.

### 5. O que corrigimos (e por que funciona agora)

1. **Esperar a primeira leitura válida**  
   Antes de iniciar o movimento, o teste agora faz um loop de até 1,5 s, chamando `get_bno_yaw()` a cada 50 ms. Quando a **primeira** leitura não for `None`, usamos esse valor como `yaw_ref`. Assim o rumo de referência é o **rumo real no momento da partida**, e não 0° por falta de dado.

2. **Warm-up no init**  
   Logo após habilitar as features, o `bno08x_init` faz várias leituras de `bno.quaternion` (com pequeno delay entre elas). Isso “acorda” o pipeline do sensor e faz o primeiro ROTATION_VECTOR chegar mais cedo. Quando o teste pede a primeira leitura (ou entra no loop de espera), a chance de já haver quaternion válido é muito maior.

Com isso, o teste passa a ter **sempre** uma referência correta e **muito mais** leituras válidas no laço, e a correção de rumo passa a atuar de fato – por isso a linha reta volta a funcionar.

## O que os logs mostram

1. **BNO conecta**: "BNO08x OK", endereço 0x4b.
2. **No início do teste**: `AVISO: BNO sem leitura; frente sem correção de rumo.`  
   Ou seja, a **primeira** leitura de yaw (`get_bno_yaw()`) retornou `None` — o ROTATION_VECTOR ainda não tinha chegado.
3. **Durante o teste**: Muitos pacotes "DBG::" (GYRO, ACCEL, PRODUCT_ID, etc.); o ROTATION_VECTOR demora a aparecer ou é pouco lido no laço.
4. **Resultado**:
   - Odometria: **-12,38°** (robô girou ~12° para a esquerda).
   - BNO: início = -0,11°, fim = 0,49° → deriva **0,60°** (BNO acha que quase não girou).

Conclusão: o BNO **não** forneceu rumo de referência no início e, no laço, muitas vezes `get_bno_yaw()` retorna `None`, então a correção de rumo **quase não é aplicada**. O robô anda com (base_tps, base_tps) e o desvio é por assimetria (motores/piso) ou por poucas correções com referência errada (yaw_ref=0).

## Por que “ontem” ia reto e “hoje” vai para a esquerda?

- **Ontem**: Com `do_reset_cycle=True`, o BNO às vezes ficava “indisponível” ou dava problema (ex.: pacote 0x7B). O teste podia rodar **sem** BNO; nesse caso o código já fazia `(base_tps, base_tps)` quando não havia leitura — e o robô podia ir reto se a assimetria fosse pequena ou o teste curto.
- **Hoje**: Com `do_reset_cycle=False`, o BNO **conecta** e “está lá”, mas:
  - No **início** não há leitura → `yaw_ref = None` → usamos `yaw_ref = 0.0` no laço.
  - No laço, muitas vezes `get_bno_yaw()` ainda retorna `None` (ROTATION_VECTOR atrasado ou pouco amostrado) → de novo `(base_tps, base_tps)`.
  - Ou seja: continuamos **sem correção efetiva**, mas agora com o BNO ativo (e possivelmente mais tráfego I2C e dump DBG), o que pode mudar timing e realçar a deriva para a esquerda.

Nada foi invertido de propósito na correção; o problema é **falta de leitura válida no início e durante** o teste, não a lógica de invert (que está correta em `config`: `BNO_STRAIGHT_INVERT_CORRECTION = True`).

## Causas técnicas

1. **Referência no início**  
   O teste chama `get_bno_yaw()` uma vez antes do laço. O BNO envia primeiro outros relatórios (GYRO, ACCEL, etc.); o ROTATION_VECTOR pode demorar um pouco. Se a primeira leitura for `None`, o teste começa **sem** rumo de referência (`yaw_ref = None` → tratado como 0.0).

2. **Poucas leituras no laço**  
   Se o I2C estiver ocupado (ex.: dump “DBG::” da biblioteca) ou o ROTATION_VECTOR for enviado com menor taxa, o laço de 30 ms pode ver muitas vezes `get_bno_yaw() = None` e aplicar quase sempre `(base_tps, base_tps)`.

3. **DBG nos logs**  
   O “********** Packet *************” e “DBG::” vêm da biblioteca Adafruit (pacotes SHTP). O nosso código usa `debug=False` no `BNO08X_I2C`. Se ainda aparecer DBG, pode ser versão antiga da lib ou outro caminho. Esse dump atrasa o laço e piora a situação.

## Ajustes recomendados (sem voltar atrás no BNO)

- **Não reverter** para `do_reset_cycle=True`: o BNO volta a falhar (0x7B / “não disponível”). O objetivo é manter o BNO ativo e corrigir o uso dele.

1. **Aguardar primeira leitura válida antes de iniciar a linha reta**  
   Antes de começar o movimento, fazer um loop (ex.: até 1,5 s) chamando `get_bno_yaw()` a cada ~50 ms até obter um valor não `None`. Só então definir `yaw_ref = get_bno_yaw()` e iniciar o teste. Assim o rumo de referência é o rumo real no início.

2. **Warm-up opcional no init do BNO**  
   Após `enable_feature(ROTATION_VECTOR)`, fazer algumas leituras de quaternion (ex.: 5–10 vezes com 50 ms entre elas) antes de retornar. Isso “acorda” o envio de ROTATION_VECTOR e aumenta a chance de a primeira leitura no teste já ser válida.

3. **Confirmar que não há debug na lib**  
   Garantir que o BNO é criado com `debug=False` (já está em `bno08x_init`) e, se o DBG continuar aparecendo, atualizar `adafruit-circuitpython-bno08x` / `adafruit-blinka` na Raspberry para evitar dump que atrasa o laço.

Com isso, mantemos a alteração que ativa o BNO e corrigimos o desvio para a esquerda garantindo **referência e leituras válidas** no teste de linha reta.

---

## Checklist para integrar navegação BNO no sistema (quando for seguro)

Enquanto a navegação em linha reta com BNO está isolada nos testes, use este checklist ao integrar no sistema principal (teleop, menu, navegador, etc.) para evitar os mesmos bugs:

| Item | O que verificar |
|------|------------------|
| **1. Init BNO** | Todo código que usa BNO deve usar `tools.bno08x_init.init_bno(do_reset_cycle=False)`. O warm-up já está dentro do init. |
| **2. Primeira leitura antes de mover** | Antes de qualquer trecho “em linha reta com correção BNO”, **não** confiar numa única chamada a `get_bno_yaw()`. Ou esperar até obter uma leitura válida (loop com timeout, ex. 1–1,5 s) e só então usar como `yaw_ref`, ou não iniciar correção até ter pelo menos uma leitura. |
| **3. Quando não há leitura no laço** | Manter o comportamento atual: se `get_bno_yaw()` retorna `None`, usar (base_tps, base_tps) – **não** inventar correção com 0° nem aplicar correção com valor antigo sem marcar como “não confiável”. |
| **4. Referência (yaw_ref)** | `yaw_ref` deve ser **sempre** uma leitura real do BNO no momento em que se define “rumo a manter”, nunca 0° por padrão quando na verdade não houve leitura. |
| **5. Ganhos e invert** | Usar os mesmos parâmetros de `config.py`: `BNO_STRAIGHT_KP`, `BNO_STRAIGHT_MAX_CORRECTION_TPS`, `BNO_STRAIGHT_INVERT_CORRECTION`. Não trocar invert sem testar em linha reta. |
| **6. Patch 0x7B** | O patch em `bno08x_init` (ao importar o módulo) já evita KeyError no report 0x7B. Qualquer outro script que crie BNO deve usar o mesmo init (não instanciar BNO08X_I2C direto sem passar pelo init). |
| **7. Debug** | Nunca criar `BNO08X_I2C(..., debug=True)` em produção; deixa o laço lento e atrapalha leituras a tempo. |
| **8. Testes isolados** | Manter `teste_bno_suite.py` e `bno08x_test.py` como referência: se a linha reta falhar no sistema integrado, comparar com o comportamento desses scripts (que já estão corretos). |

Resumo para integração: **sempre obter uma leitura válida antes de definir o rumo de referência** e **nunca assumir 0° quando não houve leitura**; usar só o init centralizado e os ganhos do config.
