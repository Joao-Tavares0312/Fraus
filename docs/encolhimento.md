# Encolher os modelos — o que foi medido, e por que a int8 foi recusada

> Medido em 10/09/2026, na máquina de desenvolvimento, contra os checkpoints
> reais. Nada aqui exigiu retreino: quantização dinâmica é transformação
> **pós-treino** sobre os pesos já aprendidos.

## O problema

| | |
|---|---|
| 3 BERTimbau (fp32) | 3 × 416 MB = **1.249 MB** |
| `torch` que os executa | **497 MB** |
| **imagem de inferência** | **~1,75 GB** |

Isso limita hospedagem, encarece o container e — desde que o teto de função
Python da Vercel subiu para 500 MB (24/02/2026) — é a única coisa entre o Fraus
e um deploy serverless.

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

> **Decisão: os artefatos int8 NÃO são promovidos.** Eles ficam em
> `modelos-onnx/` (fora do git) para quem quiser reproduzir a medição, e o
> portão de `scripts/comparar_backends.py` continua vermelho de propósito.

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

!!! warning "Medição de RAM pendente, e por que o número preliminar não serve"
    Medindo o processo com o motor montado, o ONNX consumiu **mais** residente
    que o torch (pico 1.366 MB contra 1.075 MB): o `onnxruntime` carrega o grafo
    inteiro de imediato, enquanto o torch mapeia os `safetensors` e só paga as
    páginas que toca.

    Esse número **não está limpo**: a sonda importava `fraus.motor` e
    `fraus.fusor` antes de escolher o backend, e são eles que arrastam torch e
    sklearn — 354 MB de base nos dois casos. Medir o caminho ONNX de verdade
    exige uma venv **sem** torch, e hoje `torch>=2.3` é dependência
    **principal** no `pyproject.toml`: a imagem sem torch que o extra `onnx`
    promete não existe sem mover essa dependência para um extra.

    A conclusão acima não depende disso — 939 MB de peso já passam de 800 —, mas
    a promessa de "ONNX corta a imagem em 2,6×" continua **não verificada em
    RAM**, só em disco.

### O que sobra de ganho real

Independente da máquina pequena, a variante aceita **é um ganho para o deploy na
A1**: desvio `0,000`, e a imagem perde os 497 MB do `torch` em disco (depois de
mover a dependência). Na sessão de 11/09/2026 o envio do código e dos pesos para
a VM era de 1,3 GB — cortar isso quase pela metade é menos tempo de deploy e
menos coisa para dar errado no meio.

E se 1 GB algum dia virar requisito de verdade, o caminho não é quantização: é
**um codificador com três cabeças**. Os três checkpoints são ajustes finos do
mesmo BERTimbau, então os 110M de parâmetros estão duplicados três vezes. Um
encoder compartilhado com três cabeças de classificação daria ~416 MB em precisão
cheia — cabe em 1 GB sem quantizar nada e sem risco de veredito. O preço é
retreino, e portanto a invariante 10 de novo; não é ajuste de deploy.

## O backend ONNX em produção, medido em 15/09/2026

A variante aceita acima (satisfação e emoção fp32, ironia int8) virou um
executor de verdade: `FRAUS_BACKEND=onnx`. O padrão continua `torch`, e não há
detecção nem fallback — backend desconhecido ou grafo ausente derruba o boot
(invariante 7). O `torch` saiu das dependências principais para o extra
`torch`, e o import dele ficou preguiçoso: `fraus.motor` não o arrasta mais
(há teste para isso).

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

A conclusão sobre o encoder compartilhado abaixo não mudou.

## O que sobra como caminho

| caminho | tamanho estimado | fidelidade | cabe em 500 MB? |
|---|---|---|---|
| **ONNX fp16** | 3 × 208 = 624 MB + ~50 MB de runtime | quase idêntica | ❌ — mas corta a imagem de 1,75 GB para ~0,67 GB |
| **fp32 na satisfação, int8 no resto** | 416 + 106 + 106 = 628 MB | boa no que pontua | ❌ |
| **int8 nos três** | 318 MB + ~50 MB | **1,7% troca de veredito** | ✅ |

Ou seja: **o orçamento de 500 MB só é alcançável pagando o preço que foi
recusado acima.** Isso não é um impasse técnico a resolver com mais tuning — é
a Vercel serverless não sendo o alvo certo para este sistema, e vale mais dizer
isso do que espremer o número até ele caber.

**O ganho continua real fora da Vercel:** ONNX fp16 num container corta a
imagem em ~2,6× e remove o `torch`, sem custo de fidelidade digno de nota. Esse
é o próximo experimento, e ele não precisa de retreino nenhum também.

## Reproduzir

```bash
uv sync --extra conversao
uv run python scripts/encolher_modelos.py            # converte e afere
uv run python scripts/comparar_backends.py --n 180   # o portão que recusou
```
