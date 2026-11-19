# Encolher os modelos — o que foi medido, e por que a int8 foi recusada

> Medido em 10/09/2026, na máquina de desenvolvimento, contra os checkpoints
> reais. Nada aqui exigiu retreino: quantização dinâmica é transformação
> **pós-treino** sobre os pesos já aprendidos.

!!! warning "Revisão de 16/11/2026: modelos congelados"
    Retreino, destilação, troca de arquitetura, calibração e promoção estão
    fora da fila por decisão do João. Esta página preserva medições de setembro
    e propostas experimentais, não uma campanha atual. Nenhum benchmark ou
    deploy foi executado nesta revisão; a presença do backend no código não
    identifica os pesos publicados.

O código atual mantém `torch` como padrão declarado e permite `onnx` e
`onnx-multitarefa` (`fraus/api/caminhos.py`). O executor ONNX
(`fraus/sinais/onnx.py`) usa CPU, otimização `ORT_ENABLE_ALL`, arena desativada
e aplica a temperatura do `fraus_receita.json`. `torch` é extra opcional no
`pyproject.toml`, não dependência principal. A API carrega o motor
preguiçosamente: pode subir sem os grafos e falhar explicitamente na primeira
rota que exige inferência; não há fallback para outro executor.

A variante com ironia int8 aceita em setembro só foi medida com aqueles
checkpoints. O código de caminhos registra, desde 19/10/2026, a opção por
**fp32 na ironia MultiPICo**, por mudança de classe em duas sondas int8.
Isso não altera os resultados históricos abaixo nem comprova o artefato de produção.

## O problema

| | |
|---|---|
| 3 BERTimbau (fp32) | 3 × 416 MB = **1.249 MB** |
| `torch` que os executa | **497 MB** |
| **imagem de inferência** | **~1,75 GB** |

Na avaliação de setembro, esse porte limitava hospedagem e motivava estudar
o teto de função Python da Vercel então considerado (500 MB desde
24/02/2026). O limite do provedor não foi revalidado nesta revisão.

## O que foi testado

Quantização dinâmica int8, sobre `bertimbau-satisfacao`, com as mesmas dez
sondas em todas as variantes:

| estratégia | tamanho | max Δp | classe mudou |
|---|---|---|---|
| qint8 em tudo | 105,5 MB | 0,4535 | 1 sonda |
| qint8 só em MatMul | 172,0 MB | 0,4953 | 1 sonda |
| qint8 MatMul + `per_channel` | 172,4 MB | 0,1385 | nenhuma |
| quint8 só em MatMul | 172,0 MB | 0,2620 | 1 sonda |
| **qint8 em tudo + `per_channel`** | **105,9 MB** | **0,1015** | **nenhuma** |
| qint8 tudo + `per_channel` + `reduce_range` | 105,9 MB | 0,1798 | nenhuma |

Duas coisas valem ser registradas porque contrariam a intuição comum:

1. **`per_channel` é o que decide**, não a escolha de quais operadores
   quantizar. Ele dá a cada coluna de peso a própria faixa, em vez de espremer
   a matriz inteira numa só — e numa camada de atenção as colunas têm
   magnitudes muito diferentes.
2. **"não quantize o embedding, só MatMul" saiu pior nas duas pontas**: 63%
   maior *e* menos fiel. Foi medido, não herdado de tutorial.

## O resultado da melhor variante

Aplicada aos três modelos:

```
modelo            antes     depois   redução   max Δp   classe mudou
satisfacao       416.2M     105.9M     3.93x   0.1015   nenhuma
emocao           416.2M     105.9M     3.93x   0.1129   nenhuma
ironia           416.2M     105.8M     3.93x   0.1486   nenhuma
TOTAL           1248.6M     317.6M     3.93x
```

Velocidade: **2,10× mais rápido** em CPU (309 ms → 147 ms por lote de 10
frases, `bertimbau-satisfacao`).

Pela medida de classificador — nenhuma sonda mudou de classe vencedora — isso
passaria.

## E é aqui que ela é recusada

**Diferença de probabilidade é a medida errada para este sistema.** O score do
Fraus é uma *projeção* das três probabilidades num eixo 0–100; a nota é o score
arredondado; a categoria é a nota caindo numa faixa. Cada degrau absorve ou
**amplifica** o erro do anterior.

Medido ponta a ponta, com o motor inteiro montado dos dois jeitos, sobre 180
conversas determinísticas do simulador:

| | |
|---|---|
| desvio médio de score | 0,83 pontos |
| **desvio máximo** | **25,65 pontos** |
| notas diferentes | **16 de 180** (8,9%) |
| **categorias diferentes** | **3 de 180** (1,7%) |

E o caso que encerra a discussão:

```
sim-0-635276501    59,95  ->  85,61    detrator  ->  promotor
```

Uma conversa atravessa **duas faixas** e troca de veredito. Categoria é o que a
tela mostra e o que o NPS agrega: trocar o backend não pode trocar o veredito.

> **Decisão registrada em setembro: os artefatos int8 não foram promovidos.**
> A sessão os mantinha em `modelos-onnx/` (fora do git) para reprodução;
> `scripts/comparar_backends.py` reprovou aquela variante. Não se afirma
> que os mesmos arquivos ou o mesmo resultado estejam no ambiente atual.

## A variante mista, medida em 11/09/2026

A tabela de caminhos abaixo listava "fp32 na satisfação, int8 no resto" como
**estimativa**, nunca medida. A hipótese era que o flip vinha de quantizar o
modelo que *governa* o score, e que poupá-lo resolveria. Foi medida, com o mesmo
portão e as mesmas 180 conversas:

| | int8 nos três | **mista** |
|---|---|---|
| desvio médio de score | 0,83 | **0,356** |
| desvio máximo | 25,65 | **18,99** |
| notas diferentes | 16 de 180 | **6 de 180** |
| categorias diferentes | 3 de 180 | **2 de 180** |

**A hipótese estava metade certa, e metade não basta.** Poupar a satisfação corta
o dano quase pela metade — e ainda troca o veredito de duas conversas. A mesma
`sim-0-635276501` do caso original segue atravessando faixa (59,95 → 78,94).

### De quem é a culpa, então

A ironia **saiu do vetor do Fusor** em 04/09/2026 (ver `NOMES_FEATURES`), então
quantizá-la não pode mover score nenhum. Isso deixa apenas a emoção como
suspeita, e a medição confirma — satisfação fp32 + emoção fp32 + **ironia int8**:

```
desvio medio de score :  0.000 pontos
desvio MAXIMO         :  0.000 pontos
notas diferentes      : 0 de 180
CATEGORIAS diferentes : 0 de 180
ACEITO
```

Zero exato, nas 180. Duas coisas ficam provadas de uma vez:

1. **ONNX fp32 é troca de executor, não de modelo.** Δp máximo `0,0000` por
   modelo, desvio `0,000` ponta a ponta. O que a conversão custa é nada.
2. **A única cabeça quantizável de graça é a ironia**, e exatamente porque ela
   não pontua. As duas que pontuam não toleram int8.

### E o que isso faz com a máquina de 1 GB

Nada de bom. O `VM.Standard.E2.1.Micro` (o único shape com capacidade em
sa-saopaulo-1 em 11/09/2026) tem 1 GB de RAM, e o sistema operacional come ~200:

| variante | pesos | veredito | cabe em ~800 MB |
|---|---|---|---|
| ONNX fp32 nos três | 1.250 MB | ✅ idêntico | ❌ |
| **fp32 + fp32 + ironia int8** | **939 MB** | ✅ **desvio 0,000** | ❌ |
| fp32 satisfação + int8 nas outras | 628 MB | ❌ 2/180 trocam | ⚠️ no limiar |
| int8 nos três | 318 MB | ❌ 3/180 trocam | ✅ |

A ordem é cruelmente monótona: **tudo que cabe troca veredito, e tudo que
preserva o veredito não cabe.** Não há ajuste no meio — a emoção precisa ficar em
fp32, e aí são dois codificadores de 416 MB, que já estouram o orçamento sozinhos.

!!! warning "Medição preliminar de 11/09 — substituída pela medição de 15/09 abaixo"
    Medindo o processo com o motor montado, o ONNX consumiu **mais** residente
    que o torch (pico 1.366 MB contra 1.075 MB): o `onnxruntime` carrega o grafo
    inteiro de imediato, enquanto o torch mapeia os `safetensors` e só paga as
    páginas que toca.

    Esse número **não está limpo**: a sonda importava `fraus.motor` e
    `fraus.fusor` antes de escolher o backend, e são eles que arrastam torch e
    sklearn — 354 MB de base nos dois casos. Naquela data, faltava medir em
    uma venv sem torch e mover a dependência principal para um extra.
    Essa mudança já existe no `pyproject.toml`; o bloqueio era histórico.

    A conclusão acima não depende disso — 939 MB de peso já passam de 800 —, mas
    a promessa de redução de RAM ainda não estava verificada naquela medição.
    A seção de 15/09 registra o ensaio posterior sem torch.

### O que sobra de ganho real

Independentemente da máquina pequena, a variante aceita oferecia ganho em
disco para o deploy na A1: desvio `0,000` no ensaio e retirada dos 497 MB do
`torch`. Na sessão de 11/09/2026, o envio de código e pesos para a VM era
de 1,3 GB. Esses números não são medição de um deploy atual.

Se 1 GB virasse requisito, a hipótese de pesquisa era **um codificador com
três cabeças**, evitando três cópias de cerca de 110M de parâmetros.
O peso fp32 estimado seria próximo de 416 MB, mas isso não prova RAM total,
fidelidade ou qualidade. Exige retreino; ficou fora da fila em 16/11/2026.

## O backend ONNX em produção, medido em 15/09/2026

A variante aceita acima (satisfação e emoção fp32, ironia int8) ganhou um
executor explícito: `FRAUS_BACKEND=onnx`. O padrão continua `torch`, sem
detecção ou fallback. Backend desconhecido falha na configuração; grafo
ausente falha quando o motor é carregado. `torch` saiu das dependências
principais para o extra `torch`, com import preguiçoso no caminho do motor.

Isso destravou a **medição de RAM que estava pendente**, agora numa venv sem
torch instalado (`uv sync --extra dev --extra onnx`), com o app montado por
`criar_app_padrao` e 30 conversas atribuídas:

| executor | pico de RSS | 180 conversas (`atribuir`) | categorias trocadas |
|---|---|---|---|
| torch | 1.848 MB | 53,7 s | referência |
| ONNX, 1 thread (config antiga) | — | 45,2 s | 0 |
| ONNX, todos os núcleos | 1.445 MB | 35,0 s | 0 |
| **ONNX, todos os núcleos, sem arena** | **1.347 MB** | **33,2 s** | **0** |

Desvio máximo de score contra o torch: `6,5e-5`. A venv sem torch ocupa 430 MB
contra 5,0 GB, e a imagem Docker `--build-arg BACKEND=onnx` mede **995 MB**,
já com o motor real respondendo `/analisar`.

Duas coisas contrariam a intuição e foram medidas, não supostas:

1. **A fusão offline `-O2` do otimizador de transformers saiu mais lenta**
   (41,2 s contra 35,0 s), embora tenha fundido tudo (12 `Attention`, 24
   `SkipLayerNormalization`, 12 `BiasGelu`, GELU exata). A sessão já roda com
   `ORT_ENABLE_ALL`, que funde na carga; o grafo pré-fundido só perde otimizações
   que o runtime faria por conta própria. **Recusada.**
2. **`intra_op_num_threads = 1` era o gargalo.** Fazia sentido quando várias
   requisições podiam entrar no modelo juntas. Agora o `Motor` deixa uma passada
   por vez (`FRAUS_INFERENCIAS_SIMULTANEAS`), e a passada usa os núcleos
   (`FRAUS_ONNX_THREADS`, padrão 0 = o runtime escolhe).

### Emoção com int8 só nos pesos — aceita pelo portão, não promovida por padrão

A int8 recusada acima é **dinâmica**: quantiza pesos *e* computa as ativações
em int8. A variante `--precisao int8-pesos` (`MatMulNBits`, 8 bits, blocos de
32, simétrica) guarda os pesos em int8 e mantém a ativação em fp32. Aplicada só
à emoção, com satisfação fp32 e ironia int8, nas mesmas 180 conversas:

| | ONNX aceito (emoção fp32) | **emoção int8-pesos** |
|---|---|---|
| peso da emoção | 417 MB | **184 MB** |
| pico de RSS da API | 1.347 MB | **1.056 MB** |
| 180 conversas (`atribuir`) | 33,2 s | 49,6 s |
| desvio máximo de score | 0,0001 | **0,51 ponto** |
| notas / categorias trocadas | 0 / 0 | **0 / 0** |

Ela passa no portão (zero categorias) e no do script (Δp 0,0148 < 0,02). Mas,
ao contrário do fp32, **não é o mesmo número**: meio ponto de score é margem
que uma conversa encostada na fronteira 6/7 ou 8/9 pode atravessar num corpus
maior que as 180. Por isso ela fica disponível e documentada, **não** como o
padrão de `modelos-onnx/`. E 1.056 MB **ainda não cabe** numa máquina de 1 GB,
então ela não resolve o caso que justificaria o risco.

A hipótese de encoder compartilhado continua sem comprovação de RAM ou qualidade.

## O que sobra como caminho

As estimativas abaixo pertencem ao levantamento de setembro. Não são medições
de fp16 nem alternativas aprovadas para substituir os pesos congelados.

| caminho | tamanho estimado | fidelidade | cabe em 500 MB? |
|---|---|---|---|
| **ONNX fp16** | 3 × 208 = 624 MB + ~50 MB de runtime | quase idêntica | ❌ — mas corta a imagem de 1,75 GB para ~0,67 GB |
| **fp32 na satisfação, int8 no resto** | 416 + 106 + 106 = 628 MB | reprovada: 2 de 180 categorias diferentes | ❌ |
| **int8 nos três** | 318 MB + ~50 MB | **1,7% troca de veredito** | ✅ |

Ou seja: **o orçamento de 500 MB só é alcançável pagando o preço que foi
recusado acima.** Isso não é um impasse técnico a resolver com mais tuning — é
a Vercel serverless não sendo o alvo certo para este sistema, e vale mais dizer
isso do que espremer o número até ele caber.

ONNX fp16 era um experimento proposto, com redução de disco estimada e
fidelidade ainda a medir. Não há nesta página benchmark que sustente ganho
de 2,6× com paridade fp16, nem próximo experimento ativo em 16/11/2026.

## Reproduzir

Comandos históricos de conversão e comparação; o conversor usa int8 por
padrão, **não** a combinação aceita de setembro. Eles não publicam artefatos
nem constituem instrução para trocar os modelos atuais.

```bash
uv sync --extra conversao
uv run python scripts/encolher_modelos.py            # converte e afere
uv run python scripts/comparar_backends.py --n 180   # o portão que recusou
```

## Variante experimental: um encoder, três cabeças

O código aceita `FRAUS_BACKEND=onnx-multitarefa`, mas ele **não é o padrão**.
Esta página não apresenta artefato promovido desse experimento. Diferente
da quantização, compartilhar o encoder exige treino: os três checkpoints
aprenderam representações diferentes durante o fine-tuning.
**O roteiro abaixo é histórico e está fora da fila desde 16/11/2026.**

O caminho implementado usa destilação. Os modelos atuais são os professores e
um BERTimbau único aprende simultaneamente as distribuições de satisfação,
emoção e ironia. A saída ONNX possui três tensores nomeados e o `Motor` executa
o encoder uma vez por lote — não três vezes com pesos apenas compartilhados.

```bash
uv sync --extra treino --extra onnx
uv run python scripts/treinar_multitarefa.py corpus.csv --epocas 3
uv run python scripts/comparar_backends.py --multitarefa --n 180
```

O corpus aceita CSV/JSONL com campo `texto` ou TXT com uma frase por linha.
O protocolo de pesquisa previa corpus público representativo, nunca exportar
conversas de clientes sem base legal e anonimização. O candidato é gravado
separadamente; os critérios históricos de eventual promoção eram:

- zero troca de categoria nas 180 conversas de regressão;
- métricas por cabeça não inferiores às publicadas nos cartões dos modelos;
- pico de RSS abaixo de 800 MB no container completo;
- inspeção das fatias críticas antes da troca da régua.

O tamanho esperado do grafo fp32 é aproximadamente o de um BERTimbau (cerca de
416 MB) mais três camadas lineares pequenas. O número de RAM continua sendo uma
hipótese até o artefato treinado ser medido; o código não o apresenta como ganho
concluído.
