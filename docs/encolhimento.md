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
