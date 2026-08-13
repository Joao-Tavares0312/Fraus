# Treinamento dos modelos do Fraus

O Fraus tem DOIS artefatos treinados, produzidos por dois notebooks que rodam **nesta ordem**:

| # | Notebook | O que produz | Precisa de GPU? |
|---|---|---|---|
| 1 | `notebooks/01_treino_bertimbau.ipynb` | `modelos/bertimbau-satisfacao/` — o classificador de texto (3 classes), fine-tune do `neuralmind/bert-base-portuguese-cased` sobre o B2W-Reviews01 | **sim** |
| 2 | `notebooks/02_treino_fusor.ipynb` | `modelos/fusor.joblib` — a regressao logistica que funde os tres sinais; e `modelos/importancias.json`, o peso de cada feature | nao |

O notebook 02 **depende do artefato do 01**: ele carrega o BERTimbau treinado para extrair o sinal de texto de cada conversa. A primeira celula do 02 falha com erro explicito se `modelos/bertimbau-satisfacao` nao estiver no Drive.

**Os dois artefatos sao obrigatorios para o app real subir.** `fraus/api/main.py` carrega o classificador e o fusor no boot e propaga o erro sem fallback — servir predicao sem modelo carregado e pior do que estar fora do ar. Com so um dos dois, o unico servidor que sobe e `scripts/api_demo.py`, que usa motor duble e nao serve para producao.

O treino roda inteiramente no Google Colab, fora deste repositorio — nao ha teste automatizado local para essas etapas.

## Como abrir no Colab

1. Va em [colab.research.google.com](https://colab.research.google.com).
2. `Arquivo > Fazer upload de notebook` e selecione o notebook (ou abra direto do GitHub se o repositorio estiver acessivel a partir da sua conta).

## Notebook 01 — classificador de texto

### Exigencia de GPU

O notebook so funciona com acelerador de GPU habilitado. Antes de rodar qualquer celula:

`Ambiente de execucao > Alterar tipo de ambiente de execucao > GPU`

A primeira celula do notebook faz `assert torch.cuda.is_available()` e falha com uma mensagem explicita se o ambiente de execucao estiver sem GPU.

### Onde o checkpoint fica no Drive

O notebook monta o Google Drive (`drive.mount('/content/drive')`) e usa dois diretorios dentro dele, para sobreviver a uma queda de sessao do Colab — o mesmo padrao ja usado no notebook de RVC do projeto Neuro-ai:

- `/content/drive/MyDrive/fraus/checkpoints` — checkpoints intermediarios salvos pelo `Trainer` a cada epoca (`save_strategy="epoch"`, `save_total_limit=2`). Se a sessao cair, o proximo `Trainer.train()` pode retomar a partir do ultimo checkpoint salvo aqui.
- `/content/drive/MyDrive/fraus/modelos/bertimbau-satisfacao` — destino final do modelo treinado, do tokenizador e do `metricas.json`, escritos na ultima celula do notebook.

### Para onde copiar o artefato no repo local

Depois que o notebook terminar (celula de avaliacao e export), baixe a pasta `fraus/modelos/bertimbau-satisfacao` do Google Drive e copie o conteudo para:

```
modelos/bertimbau-satisfacao/
```

na raiz deste repositorio. Os arquivos esperados sao:

- `config.json`
- `model.safetensors`
- `tokenizer.json`
- `tokenizer_config.json`
- `special_tokens_map.json`
- `metricas.json` — `{"acuracia": float, "f1_macro": float, "classes": ["insatisfeito", "neutro", "satisfeito"]}`

`fraus/sinais/texto.py` carrega esse diretorio para servir o classificador — e o notebook 02 tambem, para extrair o sinal de texto das conversas de treino do fusor.

**Importante:** `modelos/` esta no `.gitignore` deste repositorio. O artefato do modelo treinado (pesos, tokenizer, metricas) **nao vai para o git** — ele fica local, versionado apenas via o checkpoint no Drive.

### Mapeamento de rotulo

O rotulo de satisfacao vem do campo `overall_rating` (nota de 1 a 5) do B2W-Reviews01:

| `overall_rating` | rotulo       | indice |
|-------------------|--------------|--------|
| 1–2                | insatisfeito | 0      |
| 3                  | neutro       | 1      |
| 4–5                | satisfeito   | 2      |

O corpus e balanceado por subamostragem da classe majoritaria antes do split de treino/teste, porque as notas 4-5 dominam o corpus e enviesariam o classificador.

## Notebook 02 — fusor dos tres sinais

Roda DEPOIS do 01, sem GPU. O que ele faz, em sequencia:

1. monta o Drive e confere `modelos/bertimbau-satisfacao` (falha alto apontando o notebook 01 se faltar);
2. clona este repositorio e instala o pacote `fraus` — a extracao de features usa o MESMO codigo da API (`fraus.fusor.montar_features`), nunca uma reimplementacao;
3. carrega o B2W-Reviews01 e rotula por `recommend_to_a_friend` (ver abaixo);
4. costura as frases em conversas sinteticas com `fraus.ingest.simulador.gerar_lote`, deterministico por semente, com latencia calibrada por rotulo;
5. extrai as 16 features de cada conversa com o BERTimbau do notebook 01 carregado;
6. treina o `Fusor` (`treinar(exemplos, rotulos)`);
7. avalia num conjunto de teste separado — conversas geradas com outra semente e a partir de frases disjuntas — imprimindo acuracia e F1-macro;
8. exporta `fusor.joblib` (via `Fusor.salvar`) e `importancias.json` (o retorno de `Fusor.importancias()`, que vira o grafico "qual sinal pesou mais" da apresentacao).

Os dois arquivos saem em `/content/drive/MyDrive/fraus/modelos/`. Baixe para `modelos/` na raiz do repositorio local, ao lado de `bertimbau-satisfacao/`.

### Rotulo do fusor: `recommend_to_a_friend`

Esta e a etapa em que o campo `recommend_to_a_friend` do B2W-Reviews01 entra. A spec (secao 5.1) o declara como a **ancora do NPS inferido** — "sem ele, o NPS da dashboard seria metrica inventada" — e o alvo do fusor e justamente a categoria de NPS que a dashboard exibe. O notebook 01 usou `overall_rating` porque treinava sentimento de texto; o 02 usa a recomendacao porque treina NPS.

| campo | valor | classe | indice |
|---|---|---|---|
| `recommend_to_a_friend` | `Yes` | satisfeito | 2 |
| `recommend_to_a_friend` | `No` | insatisfeito | 0 |
| `overall_rating` | `3` | neutro | 1 |

**Por que a linha do neutro existe.** `recommend_to_a_friend` e binario, e as classes do projeto sao tres. Um fusor de duas classes zeraria o termo do neutro no score (`100 * (P(satisfeito) + 0.5 * P(neutro))`) e empurraria todo atendimento morno para uma das pontas, inflando o NPS nos dois sentidos. A alternativa seria treinar em duas classes e recortar o neutro por uma faixa de score — mas isso trocaria um rotulo observado por um limiar arbitrado a mao depois do treino. Aqui o neutro e `overall_rating == 3`, um rotulo do corpus, e a nota 3 tem precedencia sobre a recomendacao para que a mesma resenha nao caia em duas classes. As duas pontas — as unicas que contam no NPS, ja que neutros nao entram na formula — seguem ancoradas em `recommend_to_a_friend`.

As tres classes sao subamostradas ao tamanho da menor (a nota 3 e minoria no corpus), o mesmo balanceamento do notebook 01.

### Limitacao metodologica a declarar no relatorio

O fusor e treinado sobre conversas SINTETICAS: nenhum corpus publico de resenha PT-BR tem timestamps de dialogo, entao a latencia, a escalacao e o abandono saem de distribuicoes calibradas pela literatura de live chat, nao de atendimento observado. O texto e real (B2W), o tempo nao e.

A consequencia pratica aparece na avaliacao: como o simulador amostra latencia de faixas distintas por rotulo, o sinal de tempo separa as classes com facilidade artificial e as metricas do notebook 02 saem otimistas. Elas medem que o fusor aprendeu a combinar os sinais, nao que ele acertaria essa taxa em atendimento real.
