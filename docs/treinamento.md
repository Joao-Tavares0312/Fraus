# Treinamento dos modelos do Fraus

| # | Notebook | O que produz | GPU? | Estado |
|---|---|---|---|---|
| 1 | `notebooks/01_treino_bertimbau.ipynb` | `modelos/bertimbau-satisfacao/` — classificador de texto (3 classes), fine-tune do `neuralmind/bert-base-portuguese-cased` sobre o B2W-Reviews01 | **sim** | pronto |
| 2 | `notebooks/02_treino_fusor.ipynb` | `modelos/fusor.joblib` e `modelos/importancias.json` — a regressao logistica que funde os sinais | nao | pronto |
| 3 | `notebooks/03_treino_emocao.ipynb` | `modelos/bertimbau-emocao/` e `modelos/metricas_emocao.json` — classificador das sete classes de emocao | **sim** | pronto |
| 4 | `notebooks/04_treino_ironia.ipynb` | `modelos/bertimbau-ironia/` e `modelos/metricas_ironia.json` — classificador binario de ironia | **sim** | pronto, **mas o corpus precisa ser solicitado** |

O notebook 02 **depende do artefato do 01**: ele carrega o BERTimbau treinado para extrair o sinal de texto de cada conversa. A primeira celula do 02 falha com erro explicito se `modelos/bertimbau-satisfacao` nao estiver no Drive.

Os notebooks 03 e 04 sao **independentes entre si e do 01** — treinam cabecas separadas, em corpora proprios. O 02 e que passa a depender dos tres, porque e ele que monta o vetor de features completo. Ordem de execucao: 01, 03 e 04 em qualquer ordem, e o 02 por ultimo.

O sinal lexico (`fraus/sinais/lexico.py`) **nao tem notebook**: o SentiLex-PT nao e treinado, e recurso pronto, versionado em `fraus/dados/sentilex_pt02.csv`. Ver [Sinal lexico](#sinal-lexico--sentilex-pt02) no fim.

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
4. costura as frases em conversas sinteticas com `fraus.ingest.simulador.gerar_lote`, deterministico por semente, com latencia log-normal e emoji calibrados por rotulo;
5. extrai as features de cada conversa com o BERTimbau do notebook 01 carregado — hoje sao **39** (ver [Contrato de features](#contrato-de-features));
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

As metricas do notebook 02 continuam OTIMISTAS mesmo depois da correcao descrita abaixo: elas medem que o fusor aprendeu a combinar os sinais no dominio sintetico, nao que ele acertaria essa taxa em atendimento real.

### O vazamento do primeiro fusor — 13/08/2026

O primeiro fusor treinado marcou **99,3% de acuracia e F1-macro 0,993**, e era inutil. Vale registrar porque o modo de falha e silencioso e pode voltar.

**O sintoma.** Carregado no repositorio local e alimentado com conversas escritas a mao, o fusor devolvia praticamente a mesma nota para tudo:

| | latencia 5s | 30s | 200s |
|---|---|---|---|
| texto otimo (BERTimbau: 0,96 satisfeito) | 52,48 | 51,32 | 50,02 |
| texto pessimo (BERTimbau: 0,98 insatisfeito) | 49,94 | 49,92 | 49,84 |

Dois textos que o classificador de texto separa com mais de 95% de confianca saiam com **2,5 pontos** de diferenca, ambos colados em 50 e ambos classificados como neutro.

**A causa.** O `PERFIL_POR_ROTULO` do simulador amostrava latencia de faixas **disjuntas** — insatisfeito 60-400s, neutro 15-60s, satisfeito 3-15s. Sem sobreposicao nenhuma, a latencia *era* o rotulo: dava para acertar a classe olhando so o relogio, sem ler uma letra do texto. A regressao logistica fez exatamente isso. Os quatro maiores pesos aprendidos eram todos de tempo (`latencia_p90_s` 2,06 · `latencia_mediana_s` 2,03 · `latencia_primeira_resposta_s` 1,91 · `duracao_total_s` 1,52), contra 1,39 e 1,12 das features de texto. Fora da variedade que ele decorou, o modelo respondia "neutro" para tudo.

Os 99,3% nao mediam fusao. Mediam que o simulador vazava o gabarito.

**Um segundo achado, do mesmo diagnostico.** As features `emoji_score_medio`, `emoji_frac_positivos` e `emoji_frac_negativos` tinham coeficiente **0,0000**: o simulador nunca emitia emoji, entao elas eram constantes no treino e um dos tres sinais da arquitetura nao contribuia nada.

**A correcao** (`fraus/ingest/simulador.py`, coberta por `tests/test_simulador.py`):

- a latencia passou a ser **log-normal** com caudas que se cruzam. As medianas continuam ordenadas, como manda a literatura de live chat, mas ~11% das conversas satisfeitas sao mais lentas que a mediana das insatisfeitas, e vice-versa. Existe atendimento rapido que termina mal;
- as falas do cliente passaram a levar **emoji do lexicon**, com cruzamento deliberado — cliente irritado manda 🙏 (+0,418), cliente satisfeito manda 😩 (-0,368) — para o emoji nao virar o proximo gabarito.

**Como saber se voltou.** Acuracia alta e sintoma que pede investigacao, nao veredito. Depois da correcao o notebook 02 marcou **0,96**, e desta vez o numero se sustentou: os pesos aprendidos mudaram de lugar.

| feature | fusor vazado | fusor corrigido |
|---|---|---|
| `emoji_score_medio` | **0,0000** (morto) | **1,6662** (1º) |
| `texto_prob_satisfeito_media` | 1,3858 | 1,6026 (2º) |
| `texto_prob_insatisfeito_media` | 1,1212 | 1,4722 (3º) |
| `latencia_p90_s` | **2,0575** (1º) | 0,0674 |
| `latencia_mediana_s` | 2,0329 | 0,1621 |
| `latencia_primeira_resposta_s` | 1,9068 | 0,0138 |

O mesmo teste de sanidade que expos o vazamento — mesmo texto, so mudando o relogio — passou de 2,5 pontos de separacao para **99,6**: texto otimo pontua 99,98 e texto pessimo 0,35, com a latencia mexendo fracoes de ponto. O sinal de tempo virou o modificador fraco que ele deve ser.

**O criterio, entao, nao e o numero sozinho.** Diante de acuracia alta, olhe os PESOS: se as features que lideram forem as que carregam o conteudo (texto, emoji), o modelo aprendeu; se forem as circunstanciais (tempo, contagem de turnos), procure o vazamento.

### O fusor de 35 features — 24/08/2026

O contrato subiu de 16 para 35 features em 21/08 (emocao, lexico, ironia e estilo entraram no vetor) e o **artefato ficou tres dias para tras**. Nesse intervalo a API real nao subia: o `StandardScaler` de 16 rejeitava o vetor de 35 na carga. Falha alta e explicita, que e o comportamento que as invariantes 7 e 9 pedem — mas ainda assim tres dias de API parada por artefato desatualizado.

O notebook 02 rodou de novo e o artefato daquele momento passou a ter `n_features_in_ = 35`, na ordem exata de `NOMES_FEATURES`. (Historico: o artefato vigente hoje tem 38 — ver as secoes de 03/09 e 04/09 abaixo.)

**A acuracia caiu de 0,96 para 0,93, e a queda e o resultado saudavel.** O fusor de 16 features media um problema mais facil. Dezenove features novas entraram, tres delas vindas de uma cabeca de ironia com vazamento de corpus conhecido e nao consertado — um numero MENOR e o esperado. Pela regra desta secao, o que decide nao e o numero e sim onde os pesos foram parar:

| feature | fusor de 16 | fusor de 35 |
|---|---|---|
| `texto_prob_satisfeito_media` | 1,6026 (2º) | **1,6572 (1º)** |
| `texto_prob_insatisfeito_media` | 1,4722 (3º) | 1,3867 (2º) |
| `emoji_score_medio` | **1,6662 (1º)** | 1,3354 (3º) |
| `emoji_frac_positivos` | 0,8430 | 0,8098 |
| `emocao_surpresa_media` | — | 0,6655 |
| `emocao_desprezo_derivado` | — | 0,4757 |
| `latencia_mediana_s` | 0,1621 | 0,1200 |
| `latencia_p90_s` | 0,0674 | 0,1419 |
| `duracao_total_s` | 0,4964 | 0,3397 |

O topo continua sendo **texto e emoji**, e as features de tempo continuam no rodape, onde devem estar. As de emocao entram no meio da tabela com peso real sem deslocar o conteudo — `desprezo_derivado`, que e a diade calculada e nao uma classe do modelo, puxa 0,48. Nao ha sinal de vazamento novo.

**A divida que este fusor assume.** Ele foi treinado com a cabeca de ironia vazando (ver a pendencia 1 do README: 6 em 10 frases sinceras saem marcadas como ironicas). `ironia_prob_media` e `ironia_prob_max` pesam 0,30 e 0,31 — nao e desprezivel. **Retreinar a ironia obriga a retreinar o fusor de novo**, e essa ordem esta registrada aqui para nao se perder.

**Teste de sanidade ponta a ponta**, com os tres BERTimbau carregados, sobre conversas do simulador: rotulo insatisfeito pontua ~0, neutro ~73–75, satisfeito ~99, e as tres categorias de NPS saem certas em 9 de 9. **Isso nao e evidencia de qualidade** — sao conversas do proprio gerador sintetico, o dominio em que o fusor foi treinado. O numero honesto continua sendo 0,93 no conjunto de teste separado, e a ressalva do topo desta secao continua valendo: as metricas do notebook 02 medem fusao no dominio sintetico, nao acerto em atendimento real.

### Consequencia no NPS: a classe neutra cai em detrator — HISTORICO (fusor de 16 features, ate 24/08/2026)

**Esta secao mede o fusor de 16 features, NAO o vigente.** Ela ficou aqui sem
data enquanto o artefato foi trocado, e passou a ler como se descrevesse o
fusor atual — que e o defeito mais caro deste projeto. Fica registrada porque o
raciocinio sobre o score continua valendo, e porque a medicao dela e o
contraponto do que o fusor de 35 features entrega.

**A consequencia DEIXOU de valer com o fusor de 35 features.** Base: o teste de
sanidade ponta a ponta da secao anterior, com os tres BERTimbau carregados —
rotulo neutro pontua **~73–75**, cai na faixa 7–8 e as tres categorias de NPS
saem certas em 9 de 9. Ou seja, o neutro nao cai mais em detrator. Ressalva do
mesmo tamanho: aquele teste corre sobre conversas do proprio simulador, o
dominio em que o fusor foi treinado, entao ele desmente a medicao abaixo no
dominio sintetico e nao promete nada sobre atendimento real.

Medido em 90 conversas do simulador, 30 por classe, o fusor corrigido separa bem — medianas **0,11 / 50,99 / 99,03** por rotulo verdadeiro. Mas a categoria de NPS derivada sai **67% detrator · 29% promotor · 4% neutro**, com **NPS -38** num lote equilibrado por construcao.

Nao e falha do treino. O score e `100 * (P(satisfeito) + 0.5 * P(neutro))`, entao conversa classificada com certeza como neutra pontua 50, vira nota 5 e cai na faixa 0-6. A faixa neutra do NPS (7-8) so seria alcancada com `P(satisfeito)` entre 0,4 e 0,8 — um empate entre classes, nao uma neutralidade confiante. As tres classes do modelo e as tres categorias do NPS foram decididas em lugares separados e nunca se encontraram.

**Decisao de projeto: manter e declarar.** A alternativa avaliada era subir o peso do neutro de 0,5 para 0,75 (o centro da faixa passiva do NPS), o que faria neutro puro pontuar 75, virar nota 8 e cair em neutro — alinhando as tres classes as tres categorias. Ficou registrada aqui e na docstring de `Fusor.pontuar` para nao ser "corrigida" por engano.

### Retreino do fusor apos as features de incongruencia (03/09/2026)

O contrato subiu de 35 para 40 features: a familia `incongruencia_*` (`incongruencia_polaridade`,
`incongruencia_emoji_texto`, `incongruencia_marcador_contraste`, `incongruencia_hiperbole`,
`incongruencia_aspas_ironicas`) entrou em `NOMES_FEATURES`, anexada ao FIM da
lista para preservar a ordem das 35 antigas. O fusor salvo em `modelos/`
foi treinado com 35 e `vetorizar` agora produz 40 — ele NAO serve mais.
`Fusor.carregar` (`joblib.load` puro, sem validacao de forma) carrega esse
artefato sem erro nenhum -- a API real SOBE com ele. O erro de dimensao no
`StandardScaler` so aparece na primeira pontuacao de verdade (`/ingestao` ou
`/conversas/importar`), como HTTP 500, nao na carga do servidor. Isso e risco
de demonstracao ao vivo, nao uma trava de subida -- ver a tabela do Fusor no
README para o detalhe medido. A intencao da invariante 7 (falha alta e
explicita) so se cumpre na metade "explicita"; a metade "na carga" fica para
o retreino resolver o descompasso, nao para uma validacao que este codigo
ainda nao tem.

**O corpus sintetico tambem mudou, e isso importa mais do que a contagem de
features.** `FRASES_POR_ROTULO`, em `fraus/ingest/simulador.py`, ganhou frases
novas em duas levas para curar dois vazamentos de rotulo — o mesmo tipo de
falha silenciosa que ja custou o primeiro fusor (ver acima), so que desta vez
em features que ainda nao estavam no vetor:

- **Intensificadores.** Antes, `incongruencia_hiperbole` era nao-zero na
  maior parte das conversas do rotulo satisfeito e ZERO nos rotulos
  insatisfeito e neutro — um previsor unilateral quase perfeito de
  "satisfeito". A literatura inclui hiperbole na deteccao de ironia
  justamente porque elogio hiperbolico e a forma classica da ironia, entao o
  fusor teria aprendido a feature ao contrario do que ela significa. Depois
  da correcao, medido com `gerar_lote(FRASES_POR_ROTULO, 180, semente=7)` —
  o mesmo lote e semente da guarda `test_nenhuma_feature_e_previsor_unilateral`
  em `tests/test_simulador.py`: `insatisfeito 34/60 | neutro 0/60 | satisfeito
  39/60`.
- **Negacao.** `lexico_frac_negados` era nao-zero so no rotulo insatisfeito e
  ZERO nos outros dois — previsor unilateral de "insatisfeito", pre-existente
  desde antes da familia `incongruencia_*` e nunca notado por falta de guarda
  na familia `lexico_*`. Depois, medido com o mesmo lote e semente acima:
  `insatisfeito 15/60 | neutro 17/60 | satisfeito 21/60`.

**Consequencia pratica: o notebook 02 precisa REGERAR o corpus sintetico, nao
reusar um lote cacheado de uma execucao anterior.** O notebook 02 ja gera o
lote do zero a cada execucao — `gerar_lote` roda na propria celula, com
semente fixa, e nao le nenhum artefato salvo de rodada passada — entao rodar
o notebook de novo, sem alterar nada, ja traz o corpus corrigido. O risco e
so para quem tiver guardado um `.csv`/`.pkl` de conversas de uma sessao
antiga do Colab e tentar reaproveitar: um lote assim traz os dois vazamentos
de volta.

**O notebook ja importa o contrato do pacote, nao repete a lista.** A celula
marcada com o comentario `# 5. Os SETE sinais de cada conversa, pelo MESMO
codigo que a API usa` (indice 8 do `.ipynb`, contando a partir de 0) faz
`from fraus.fusor import NOMES_FEATURES, montar_features` e chama
`montar_features` com os tres classificadores — as cinco features novas
entram sozinhas, sem editar o notebook. Isso ja era assim antes desta rodada
(o vazamento do ramo obsoleto registrado na celula 2 foi outra causa, a de
importar de um ramo desatualizado do repositorio, nao de reimplementar a
lista) — nao ha lista duplicada para divergir aqui.

Passos, no Colab:

1. Conferir que a celula do clone do repositorio (`RAMO`) aponta para `main`
   com a Task 5 mergeada, e rodar o notebook do inicio — sem tentar
   reaproveitar nenhum lote de conversas salvo de uma execucao anterior.
2. Antes de subir ao Colab (ou depois, localmente), rodar as guardas de
   vazamento: `uv run pytest tests/test_simulador.py -k unilateral`. Elas
   cobrem as familias `lexico_*`, `emoji_*`, `estilo_*` e `incongruencia_*`
   contra previsor unilateral e precisam estar verdes antes do treino valer
   a pena.
3. Conferir a acuracia contra a do fusor de 35 features (0,93). **Acuracia
   alta demais e sintoma, nao vitoria** — se saltar muito acima do valor
   anterior, suspeite de vazamento antes de comemorar, releia a secao "O
   vazamento do primeiro fusor" acima e confira os PESOS, nao so o numero:
   se as features que lideram forem as de conteudo (texto, emoji), o modelo
   aprendeu; se forem as circunstanciais, procure o vazamento.
4. Conferir os coeficientes das cinco features novas em `Fusor.importancias()`
   / `Fusor.eixo_global()`.

   **CORRECAO DE 04/09/2026, e a licao vale mais que o numero:** este passo
   dizia para esperar peso proximo de zero em
   `incongruencia_marcador_contraste` e `incongruencia_aspas_ironicas`,
   porque as duas sao constantes em zero no corpus do SIMULADOR. A previsao
   estava errada, e o erro foi confundir dois corpora diferentes. O simulador
   fornece a ESTRUTURA temporal (latencia, turnos, escalacao) a partir de seis
   frases por rotulo; o TEXTO do treino e o B2W-Reviews01, resenha real de
   e-commerce, onde marcador de contraste e aspas ironicas ocorrem
   normalmente. Medir uma feature de texto no gerador de estrutura e olhar
   para o corpus errado.

   Os pesos reais do primeiro retreino de 40 features, no eixo
   satisfeito-menos-insatisfeito:

   | feature | peso |
   |---|---|
   | `incongruencia_emoji_texto` | −0,95 |
   | `incongruencia_hiperbole` | −0,65 |
   | `incongruencia_marcador_contraste` | −0,38 |
   | `incongruencia_polaridade` | −0,37 |
   | `incongruencia_aspas_ironicas` | −0,15 |

   As cinco sairam NEGATIVAS, que e a direcao que a literatura preve: mais
   incongruencia empurra a nota para insatisfeito. A hiperbole em −0,65 e a
   evidencia de que o cruzamento do corpus (secao acima) funcionou — sem ele
   ela teria aprendido o sinal contrario.

   O que continua valendo da versao anterior deste passo: as guardas de
   vazamento medem o SIMULADOR e sao sobre a estrutura, nao sobre o texto do
   B2W. `incongruencia_hiperbole` melhorou
   mas nao chegou aos tres: depois da correcao ela dispara em DOIS dos tres
   rotulos — `insatisfeito 34/60` e `satisfeito 39/60` (numeros medidos
   acima, na secao do retreino) —, e `neutro` continua em `0/60`. Isso e
   limitacao declarada, nao vazamento remanescente: fala neutra raramente
   intensifica termo polar com hiperbole, e a decisao foi nao forcar uma
   frase artificial no gerador so para a classe deixar de ficar muda. A
   guarda `test_nenhuma_feature_e_previsor_unilateral`
   (`tests/test_simulador.py`) tolera isso por construcao — ela so falha
   quando a feature dispara em EXATAMENTE UM rotulo, entao 2-de-3 passa
   verde. Isso e posicao aceita sobre o corpus sintetico atual, nao
   descuido: fica registrado aqui para o proximo leitor nao achar que a
   guarda promete "sinal nos tres rotulos" quando ela so promete "nao
   previsor unilateral de UM rotulo so". A guarda nao foi alterada.
5. Copiar `fusor.joblib` e `importancias.json` para `modelos/` na raiz do
   repositorio local (guardando o artefato anterior como `.bak-<N>`, onde N e
   o numero de features dele) e entao, nesta ordem:
   `uv run python scripts/conferir_fusor.py` e `uv run pytest -q` inteiro. O
   laudo faz automaticamente os passos 3 e 4 desta lista — ver "Conferencia do
   artefato" abaixo.

### A ironia sai do vetor (04/09/2026)

Medicao sobre o proprio corpus de treino do fusor (B2W-Reviews01, amostra
equilibrada de 500 resenhas por rotulo, semente 20260904), rodando so a cabeca
de ironia:

```
resenha NEGATIVA (nao): media P(ironia) = 0,1012  mediana 0,0013  frac(P>0,5) = 0,092
resenha POSITIVA (sim): media P(ironia) = 0,7146  mediana 0,9687  frac(P>0,5) = 0,740
                                                        diferenca (sim-nao) = +0,6134
```

A cabeca, treinada no IDPT 2021 (tweet e noticia), aplicada a resenha de
e-commerce funciona na pratica como **detector de sentimento positivo**: marca
74% das resenhas satisfeitas como ironicas contra 9% das insatisfeitas. O
fusor de 40 features aprendeu **+0,77** de peso para `ironia_prob_media` no
eixo satisfeito-menos-insatisfeito — mais ironia empurrando para SATISFEITO,
o inverso do que o nome da feature promete. O fusor de 35 ja tinha o mesmo
sinal (+0,48), entao nao e regressao desta rodada: e o mesmo vazamento medido
de novo, agora com numero.

Consequencia observavel: a frase canonica de ironia deste projeto — "que
atendimento maravilhoso, so esperei 3 horas" — pontuava **99,98 / nota 10 /
promotor** no fusor de 40, porque as duas features de ironia empurravam para
cima em vez de para baixo. (A cabeca isolada acerta essa frase: 0,998 nela,
0,002 num elogio sincero. Quem lia ao contrario era o fusor, e so por causa
do corpus.)

**Decisao: `ironia_prob_media` e `ironia_prob_max` saem de `NOMES_FEATURES`.**
Feature que mede outra coisa que nao o nome dela e pior que feature ausente —
ela nao adiciona sinal, duplica `texto_prob_satisfeito_*` com ruido, e inverte
o caso que o projeto usa como exemplo de manual. A cabeca de ironia CONTINUA
carregada e obrigatoria (invariante 7) e continua sendo lida por mensagem e
exibida na dashboard, onde e honesta e ja vem com a ressalva de confiabilidade
que a tela mostra — o que muda e que ela para de pontuar. O retreino com 38
features foi executado no mesmo dia; ver a secao seguinte.

**Nota sobre a janela entre a mudanca do contrato e o artefato novo.** Enquanto
`modelos/fusor.joblib` era o artefato de 40 e o contrato ja estava em 38, a API
**nao subia** — `Fusor.carregar` passou a comparar `n_features_in_` com
`len(NOMES_FEATURES)` e levantar `FusorIncompativelError` (PR #29, 04/09/2026).
Antes dessa validacao, o mesmo desencontro deixava a API subir normalmente e
estourar HTTP 500 so na primeira pontuacao real — falha tardia, no pior momento
possivel. A validacao troca isso por falha alta e explicita na subida, que e o
que a invariante 7 pede.

### O fusor de 38 features — 04/09/2026

Notebook 02 rodado de novo com a ironia fora do vetor. **Acuracia 0,9433**
(f1_macro 0,9436), contra 0,9467 do fusor de 40. A queda de ~0,003 e o
resultado saudavel e esperado: as duas features removidas *estavam* ajudando
o classificador — so que como detectores de sentimento positivo duplicando
`texto_prob_satisfeito_*`, nao como medida de ironia. Perder um pouco de
acuracia trocando uma feature que mente por nenhuma feature e o negocio certo.

Conferido com `uv run python scripts/conferir_fusor.py` (ver secao
"Conferencia do artefato" abaixo): contrato 38/38, `classes_ = [0, 1, 2]`
(invariante 8), nenhuma feature com peso perto de zero, e as cinco de
incongruencia mantiveram a direcao negativa que a literatura preve:

| feature | fusor de 40 | fusor de 38 |
|---|---|---|
| `incongruencia_emoji_texto` | −0,95 | −1,03 |
| `incongruencia_hiperbole` | −0,65 | −0,64 |
| `incongruencia_polaridade` | −0,37 | −0,37 |
| `incongruencia_marcador_contraste` | −0,38 | −0,27 |
| `incongruencia_aspas_ironicas` | −0,15 | −0,19 |

**Tres pesos com sinal aparentemente invertido, e por que NAO sao vazamento.**
O laudo sinaliza `texto_prob_satisfeito_ultima` (−0,50),
`emoji_frac_positivos` (−0,18) e `emoji_frac_negativos` (+0,60) como suspeitos,
porque o nome promete o sinal contrario. Conferidos contra os artefatos de 40 e
de 35, os tres ja estavam assim nos dois — nao e efeito da remocao da ironia.
A explicacao e **colinearidade**: `texto_prob_satisfeito_media` pesa +2,81 e
`emoji_score_medio` +1,56, e features fortemente correlacionadas com elas
recebem coeficiente negativo de correcao na regressao logistica. E o
comportamento normal do modelo com features redundantes, nao inversao de
semantica como a de `ironia_prob_media`. A diferenca entre os dois casos e
verificavel: a ironia foi medida diretamente no corpus e provou medir outra
coisa; estas tres continuam medindo o que o nome diz, so nao carregam
informacao independente das dominantes. Fica registrado aqui porque o laudo
vai sinalizar as tres em todo retreino futuro, e o proximo leitor precisa
saber que ja foram investigadas.

**O que este retreino NAO resolveu.** A frase canonica do projeto continua
pontuando alto:

```
"que atendimento maravilhoso, so esperei 3 horas"   score 99,95  nota 10
"otimo, mais uma vez ninguem resolveu nada"          score 99,74  nota 10
"resolveu rapido, muito obrigado! adorei"            score 97,82  nota 10
```

As cinco features de incongruencia dao **0,0 nas duas frases ironicas** e
disparam na satisfeita de verdade (`polaridade` 0,5, `hiperbole` 0,5) — ou
seja, hoje elas pegam entusiasmo genuino e nao pegam ironia. Nao e regressao:
e o limite estrutural das cinco, todas funcao de `anotar_texto`/emoji, e
"so esperei 3 horas" nao tem nenhuma palavra polar no SentiLex — e negativo
por pragmatica. O diagnostico completo e a rota proposta
(`incongruencia_situacao_negativa`, que levaria o vetor a 39 e exige mais um
retreino) estao em
`docs/superpowers/specs/2026-09-04-incongruencia-implicita-design.md`.

Corrigindo a previsao registrada na secao anterior: esperava-se que a frase
deixasse de ser empurrada para cima com a saida da ironia. Nao foi o que
aconteceu — o `texto_prob_satisfeito_media` da propria cabeca de texto e 0,858
nela, e domina o eixo sozinho. A remocao consertou o vetor; nao tocou nesta
frase.

### O contrato sobe para 39: incongruencia implicita (04/09/2026)

`incongruencia_situacao_negativa` entrou em `NOMES_FEATURES` -- elogio
convivendo com situacao negativa de atendimento na mesma fala. E a unica das
seis que alcanca a frase canonica do projeto, porque nao depende de um segundo
termo polar no lexicon.

**O retreino do notebook 02 e OBRIGATORIO antes de a API voltar a subir.** O
artefato de 38 nao carrega mais: `Fusor.carregar` valida a dimensao e levanta
`FusorIncompativelError`. Isso e o comportamento desejado, nao um bug.

Medido ANTES de aceitar, no B2W-Reviews01 (2000 resenhas por rotulo, semente
20260904) -- que e o corpus que da o TEXTO do treino:

```
insatisfeito  82/2000 = 4,10%
neutro        53/2000 = 2,65%
satisfeito    35/2000 = 1,75%
```

Dispara nos tres rotulos, gradiente suave, razao 2,3:1 entre os extremos.
Compare com a cabeca de ironia que saiu do vetor no mesmo dia (74% contra 9%,
razao 8:1): aquilo era disjuncao pratica, isto e sinal.

**Uma armadilha de metodo que quase repeti.** Medir esta feature no corpus do
SIMULADOR dava zero nos tres rotulos, e eu quase concluí que ela nasceria com
peso zero. Errado, e pelo mesmo motivo registrado na correcao de 04/09 mais
acima: `FRASES_POR_ROTULO` **nao treina o fusor**. O notebook 02 usa 400 frases
do B2W por classe e pega do simulador so a ESTRUTURA da conversa. O simulador
importa para a guarda `test_nenhuma_feature_e_previsor_unilateral`, nao para o
peso aprendido. As frases dos tres rotulos foram cruzadas mesmo assim -- sem
isso a feature ficava constante em zero la e a guarda passaria por vacuidade,
que e o modo de falha silencioso dela.

### Conferencia do artefato

```bash
uv run python scripts/conferir_fusor.py              # laudo completo
uv run python scripts/conferir_fusor.py --sem-sonda  # pula as frases-sonda
```

Laudo do artefato vigente em `modelos/`, em seis itens: contrato, ordem das
classes, sinal dos pesos por familia, pesos perto de zero, tres frases-sonda e
as metricas do treino. Instrumento, nao botao — nao escreve nada, no modelo de
`scripts/medir_faixas.py`.

Ele existe porque **acuracia nao denuncia** os dois defeitos que esta semana
custaram dois retreinos: o peso invertido de `ironia_prob_media` e o vazamento
de `incongruencia_hiperbole`. Os dois so apareceram porque alguem olhou o sinal
dos coeficientes e a distribuicao por rotulo — exatamente o que uma pessoa
cansada depois de um treino longo pula. Por isso a acuracia nunca e impressa
sozinha no laudo: vem sempre com o lembrete da invariante 10, e com alerta
explicito acima de 0,97.

## Contrato de features

`NOMES_FEATURES`, em `fraus/fusor.py`, e a lista canonica. `vetorizar` levanta `KeyError` se faltar chave — nunca zero silencioso (invariante 9).

Hoje sao **39 features**, de SETE familias no vetor (OITO sinais existem no
sistema — a ironia continua existindo e sendo lida por mensagem, so nao entra
mais aqui, ver a secao acima). O contrato subiu de 16 para 35 em 21/08/2026,
quando os notebooks 03 e 04 passaram a existir e a condicao que justificava a
espera acabou; de 35 para 40 em 03/09/2026, quando a familia `incongruencia_*`
entrou (ver [Retreino do fusor apos as features de
incongruencia](#retreino-do-fusor-apos-as-features-de-incongruencia-03092026)
acima); e caiu de 40 para 38 em 04/09/2026, quando `ironia_prob_media` e
`ironia_prob_max` sairam (ver [A ironia sai do
vetor](#a-ironia-sai-do-vetor-04092026) acima).

| sinal | modulo | features | no vetor? |
|---|---|---|---|
| texto | `fraus/sinais/texto.py` | 4 | sim |
| emoji | `fraus/sinais/emoji.py` | 5 | sim |
| tempo | `fraus/sinais/tempo.py` | 7 | sim |
| emocao | `fraus/sinais/emocao.py` | 8 | sim |
| lexico | `fraus/sinais/lexico.py` | 3 | sim |
| ironia | `fraus/sinais/ironia.py` | 2 | **nao** (lida por mensagem, nao pontua) |
| estilo | `fraus/sinais/estilo.py` | 6 | sim |
| incongruencia | `fraus/sinais/incongruencia.py` | 5 | sim |

**Consequencia:** `montar_features` exige DOIS classificadores (texto e
emocao); `Motor` continua exigindo os TRES (a ironia entra na atribuicao por
mensagem, nao no vetor), e a API nao sobe sem os tres artefatos em `modelos/`.
E o comportamento correto da invariante 7.

## Notebook 03 — classificador de emocao

Requisito de banca: distinguir as **sete emocoes humanas**. A cabeca treinada tem sete classes, e a setima emocao e derivada — ver abaixo.

A ordem das classes **nao e redigitada no notebook**: ele importa `NOMES_EMOCOES` de `fraus.sinais.emocao`, a mesma lista que o sinal usa para ler as probabilidades. Redigitar seria o jeito mais facil de treinar `raiva` no indice 2 e le-la no indice 3.

### Ordem canonica das classes

`fraus/sinais/emocao.py` fixa a ordem, e ela vale no notebook, no sinal e no fusor. Inverter nao gera erro: atribui a emocao errada em silencio, a mesma armadilha da invariante 8.

| indice | classe |
|---|---|
| 0 | alegria |
| 1 | tristeza |
| 2 | raiva |
| 3 | medo |
| 4 | nojo |
| 5 | surpresa |
| 6 | neutro |

### Corpus: `go_emotions_ptbr`

Traducao PT-BR do GoEmotions (Demszky et al., 2020 — 58k comentarios do Reddit, 27 emocoes + neutro), com 43.410 exemplos de treino, 5.426 de validacao e 5.427 de teste. Licenca Apache 2.0. As 27 categorias sao reduzidas as seis de Ekman pelo **mapeamento oficial que o proprio GoEmotions publica** — nao por agrupamento inventado aqui.

O arquivo vem no formato CRU do GoEmotions — **uma linha por anotador**, nao por exemplo. Um rotulo conta quando **pelo menos 2 anotadores** o marcaram (a maioria dos exemplos tem 3 anotadores, entao 2 e maioria simples), e exemplos que caem em mais de uma classe de Ekman sao descartados: a tarefa e multiclasse de rotulo unico, e forcar vencedor entre duas emocoes empatadas inventaria rotulo.

O limiar mais alto rende MAIS exemplos, o que so parece contra-intuitivo ate ver o motivo — com 1 anotador quase todo exemplo recebe varios rotulos Ekman e cai fora do filtro de rotulo unico:

| limiar | exemplos com rotulo unico |
|---|---|
| 1 anotador | 17.367 |
| **2 anotadores** | **46.014** |

### O desequilibrio, e por que NAO subamostrar

Distribuicao medida com limiar 2:

| classe | exemplos |
|---|---|
| alegria | 19.284 |
| neutro | 13.603 |
| raiva | 5.155 |
| surpresa | 4.339 |
| tristeza | 2.601 |
| medo | 588 |
| **nojo** | **444** |

Sao **43:1** entre a maior e a menor. Os notebooks 01 e 02 balanceiam por subamostragem, mas aqui isso seria destrutivo: cortar tudo ao tamanho de `nojo` deixaria **3.108 exemplos** para sete classes, jogando fora 93% do corpus.

**Escolha: pesos de classe na perda**, pela formula `n / (k * n_c)` — a mesma do `class_weight='balanced'` do scikit-learn. Os 46 mil exemplos ficam. Por isso a metrica de selecao do melhor checkpoint e o **F1-macro, nunca a acuracia**: com 43:1, um modelo que chutasse `alegria` sempre marcaria 42% sem ter aprendido nada.

### O teto do desprezo — a declarar no relatorio

`nojo` e a classe mais rara do corpus, e o **desprezo e derivado de raiva x nojo**. A qualidade do desprezo fica limitada de cima pela qualidade da pior classe do modelo: se o F1 de `nojo` sair baixo, o desprezo herda isso. O notebook imprime esse teto explicitamente e grava o F1 por classe em `metricas_emocao.json`, para o numero aparecer no relatorio em vez de ser descoberto pela banca.

**Limitacao a declarar:** a traducao foi feita por maquina (Google Tradutor), sem revisao humana. Por isso a avaliacao reporta tambem o **XED-pt** (7.220 linhas, CC-BY, Plutchik 8 + neutro) como conjunto de teste independente, que nao passou por traducao automatica. O mapeamento Plutchik -> Ekman descarta *anticipation* e *trust*; o resto casa 1:1.

Duas ressalvas sobre o XED-pt: ele e **portugues europeu** ("pa", "artola"), enquanto o treino e PT-BR — diferenca de variedade, nao so de dominio; e o numero dele vai sair **mais baixo** que o interno, o que e esperado e e justamente o ponto, porque e ele que responde "mas nao e so traducao automatica?".

### Por que o desprezo NAO e treinado

A setima emocao e o **desprezo**, e nenhum corpus rotulado em portugues o anota. Havia um corpus multilingue sintetico com `contempt` entre os rotulos, e ele foi **recusado de proposito**: treinar seis classes com dado humano e so o desprezo com dado de outra procedencia ensinaria o modelo a reconhecer o *estilo do texto sintetico* em vez do desprezo. E o mesmo vazamento da latencia disjunta, com outra roupa.

O desprezo e derivado da **diade primaria raiva + nojo**, que e como Plutchik (1980) o define — referencia citavel, nao rotulo inventado. A composicao usa media **geometrica**, nao aritmetica: desprezo exige as duas emocoes juntas, e a aritmetica devolveria 0,5 para raiva pura sem nojo nenhum, o que e raiva e nao desprezo.

## Notebook 04 — classificador de ironia

Classificacao binaria: 0 nao-ironico, 1 ironico.

**Corpus:** IDPT 2021, a tarefa de *Irony Detection in Portuguese* do IberLEF — 15,2k tweets e 18,4k noticias anotados.

### O corpus NAO tem download aberto

Diferente dos outros notebooks, o 04 **nao baixa o corpus sozinho**: o IDPT 2021 nao esta publicado para download livre — nao ha copia no GitHub nem no Hugging Face, e a pagina da tarefa nao expoe link direto. E preciso **solicitar aos organizadores** em <https://sites.google.com/inf.ufpel.edu.br/idpt2021/>.

O notebook aceita **tres origens** para o corpus, escolhidas na variavel `ORIGEM` da celula 3. Todas alimentam a mesma pasta e a mesma deteccao de esquema, entao trocar de fonte nao muda o resto do notebook:

| `ORIGEM` | Quando usar |
|---|---|
| `sintetico` (**padrao**) | gera o corpus com `fraus.ingest.gerador_ironia` — nao depende de liberacao de ninguem |
| `drive` | os arquivos ja estao em `DIR_CORPUS` — foi assim que o IDPT entrou, se liberado |
| `kaggle` | baixa da conta Kaggle; exige `KAGGLE_USERNAME`/`KAGGLE_KEY` nos Secrets do Colab |
| `upload` | seletor de arquivos do navegador, para corpus que chegou por e-mail |

### Alternativas ao IDPT — levantamento de 14/08/2026

Registrado para ninguem repetir a busca. O que **nao serve**, e por que:

| Fonte | Veredito |
|---|---|
| `arbml/multilingual_irony` (HF) | so `tweet_id` + `label`, **sem texto**; reidratar exige API paga do Twitter |
| `ramondomiingos/ptbr-irony-idioms-regionalism` (HF) | < 1.000 linhas, e e *benchmark de LLM* com gabarito em prosa — nao e corpus de classificacao |
| `rafaelanchieta/PiLN` (GitHub) | sao os **modelos** treinados do IDPT, nao o corpus; embeddings dependem de servidor antigo do NILC |
| IroSvA / SemEval-2018 traduzidos | **desaconselhado**: traducao automatica reintroduz o vazamento de procedencia que ja custou o primeiro fusor |

O candidato mais citado e o corpus de **Goncalves et al., BraSNAM 2015** ("Bazinga! Caracterizando e Detectando Sarcasmo e Ironia no Twitter", UFMG), que circula no Kaggle. Lendo o artigo: sao ~2.628 tweets por classe coletados pelas hashtags **`#sarcasm` e `#irony`** e caracterizados com LIWC — ou seja, e um trabalho brasileiro sobre o Twitter **anglofono**. Corpus em ingles. Usa-lo aqui seria o vazamento de procedencia com selo academico.

Verificado tambem e descartado: `OpenNeuro ds004533` ("Ironia VEV") e **neuroimagem** — ressonancia de 40 sujeitos ouvindo frases ironicas, sem nenhuma frase rotulada para treino.

### Onde existe corpus PT-BR de ironia (e como pedir)

Dois, os dois **sem download publico**:

1. **Vieira e Silva, A. (2025)** — *Deteccao automatica de ironia por meio de representacoes contextuais*, tese de doutorado em Linguistica, USP, orientacao de Marcos Lopes. Produziu um corpus de ironia em portugues com conversas da rede X: **1.186 exemplos** finais (de 1.200), anotados por **tres voluntarios humanos**, com o contexto da conversa. Achado relevante para o relatorio: os anotadores precisaram do **contexto de producao em ~30% dos casos** — evidencia direta de que ironia em mensagem isolada tem teto baixo, e ela vale citada mesmo sem o corpus em maos.
2. **Projeto IDPT / UFPel** — <https://institucional.ufpel.edu.br/projetos/id/u3345>, coordenacao de **Larissa Astrogildo de Freitas**. E o grupo por tras do IDPT 2021. Enderece o pedido a coordenacao.

**Tamanho importa aqui:** 1.186 exemplos anotados a mao nao treinam um BERT do zero, mas sao excelentes como **conjunto de teste independente** — exatamente o papel que o XED-pt cumpre no notebook 03. E a arquitetura de honestidade que o projeto ja usa: treinar no que ha em volume, medir no que ha em qualidade.

### O padrao: corpus sintetico

Enquanto nenhum dos dois chega, o notebook gera o proprio corpus com `fraus.ingest.gerador_ironia`. E o mesmo impasse do sinal de tempo e a mesma saida ja aceita: o fusor treina em conversas sinteticas porque nenhum corpus de review tem timestamps.

O gerador foi escrito **contra** o vazamento que matou o primeiro fusor. A armadilha obvia seria "ironico = elogio + fato ruim", que ensinaria o modelo a procurar fato ruim em vez da incongruencia. Tres cruzamentos impedem isso, cada um travado por teste em `tests/test_gerador_ironia.py`:

- os mesmos **fatos ruins** aparecem nas reclamacoes diretas (nao-ironicas);
- as mesmas **palavras elogiosas** aparecem em elogios sinceros e em reclamacoes que comecam agradecendo;
- **numeros e unidades de tempo** aparecem nas duas classes;
- ha uma familia de ironia **por atenuacao**, sem palavra elogiosa nenhuma, para que "tem elogio" nao seja condicao necessaria.

**A metrica interna sera otimista por construcao** — ela mede o quanto o modelo aprendeu estes padroes, nao o quanto le ironia humana. Isso precisa estar no relatorio.

Por isso o `metricas_ironia.json` grava a **procedencia derivada de `ORIGEM`**, nunca `IDPT 2021` fixo: artefato que mente sobre a propria fonte e pior que artefato ausente.

Como o notebook **nunca viu os arquivos**, a celula de carga tem esquema **configuravel**: ela le todo `.csv`/`.tsv` da pasta, imprime as colunas encontradas, tenta achar a de texto e a de rotulo pelos nomes mais provaveis e **para nomeando as colunas disponiveis** se nao achar. Rotulo fora do mapeamento tambem para com erro, em vez de virar 0 silenciosamente.

**Se o corpus nao for liberado a tempo**, a saida honesta e declarar a ironia como trabalho futuro no relatorio. Trocar por um corpus de sarcasmo em ingles traduzido repetiria, com outro nome, o vazamento de procedencia que ja custou o primeiro fusor.

A metrica de selecao do melhor checkpoint e o **F1 da classe ironica isolada**, nao a macro nem a acuracia: e essa classe que o sinal consome, e corpus de ironia costuma ser desequilibrado o bastante para um modelo que responde "nao e ironia" sempre marcar boa acuracia. O treino tambem usa pesos de classe, pelo mesmo motivo.

**Por que uma cabeca separada** e nao mais uma classe do sinal de texto: ironia nao e um sentimento, e uma relacao entre o que o texto DIZ e o que ele SIGNIFICA. "Que atendimento maravilhoso, so esperei 3 horas" e lexicamente positivo e pragmaticamente negativo ao mesmo tempo. Como quarta classe de satisfacao, o modelo seria obrigado a escolher uma das duas leituras — e a informacao de que ha conflito, que e justamente o sinal de ironia, se perderia.

**Limitacao a declarar:** o IDPT e anotado em tweets e comentarios de noticia, nao em atendimento de chatbot. A transferencia de dominio nao esta verificada — ironia em reclamacao de suporte pode ter forma diferente de ironia em comentario de politica.

## Sinal lexico — SentiLex-PT02

Nao tem notebook: e recurso pronto, nao treinado.

**Fonte:** SentiLex-PT02 — Silva, Carvalho e Sarmento, *"Building a Sentiment Lexicon for Social Judgement Mining"* (PROPOR 2012), CC-BY. 82.347 formas flexionadas na origem, **79.189** depois da conversao.

**Preparo:** `scripts/preparar_sentilex.py` converte o arquivo original em `fraus/dados/sentilex_pt02.csv` e imprime o relatorio do que mexeu — 315 entradas cuja polaridade veio do complemento (`POL:N1`), 9 com sinal normalizado (marcadas `REV:POL` na fonte, com o contador vazado no campo de polaridade) e 2.032 formas homografas com polaridades conflitantes, que foram **zeradas** em vez de decididas pela ordem do arquivo.

**Por que um lexicon se o BERTimbau ja le o texto:** porque ele nao foi treinado nos mesmos dados nem carrega os mesmos vieses. Dois sinais de procedencia independente que concordam sustentam a nota melhor que um sozinho — e a **discordancia** entre eles e o formato tipico da ironia.

**Negacao por escopo:** "nao foi otimo" inverte a polaridade de "otimo", com alcance de tres tokens, e o escopo **morre na pontuacao forte** — em "nao chegou. otimo atendimento" o *otimo* continua positivo.

**Acento:** o SentiLex e acentuado e cliente de chat nem sempre. Ha indice de reserva sem acento; das 74.443 chaves resultantes, apenas **24** colidem (`incomodo`/`incomodo`, `ingenua`/`ingenua`) e essas ficam zeradas — chute de polaridade errado e pior que termo ausente.

**Limitacao do recurso, a declarar:** o SentiLex e lexicon de **julgamento social** — anota polaridade dirigida a entidades humanas. E forte no adjetivo que julga (`pessimo`, `otimo`, `incompetente`) e **neutro em verbo de afeto do proprio falante**: `gostar`, `adorar` e `odiar` valem 0 nele. Por isso o sinal lexico complementa o BERTimbau e nao o substitui — quem le "adorei o produto" e o transformer.

## Sinal de estilo

Nao tem notebook: e **deterministico**, nao treinado — `fraus/sinais/estilo.py` mede a FORMA da escrita (caixa alta, pontuacao enfatica, alongamento, palavrao com gradacao, censura), nao o conteudo.

**Por que deterministico e nao um classificador.** O BERTimbau nao aprende enfase porque o B2W-Reviews01 — resenha moderada de e-commerce — praticamente nao contem gritaria nem xingamento. Modelo nao aprende fenomeno que o corpus de treino nao tem, e mais epocas sobre o mesmo texto so reproduziriam o mesmo artefato. Regra escrita a mao cobre exatamente o que falta: forma, nao semantica.

**Fonte do lexicon de palavrao:** `fraus/dados/palavroes_ptbr.csv`, curadoria propria, ~172 termos, colunas `termo,intensidade,alvo`. A intensidade e graduada (`leve`/`medio`/`pesado`, mapeada para 0,33/0,66/1,0) porque "que droga" e "vai tomar no cu" nao sao o mesmo evento, e o alvo (`pessoa`/`desabafo`) existe porque xingar o PRODUTO e reclamacao enquanto xingar o ATENDENTE e ruptura da conversa. Nenhuma dependencia externa entrou para isso, e o SentiLex-PT02 tambem nao serve — ele anota polaridade de julgamento, nao gradacao de baixo calao nem alvo do xingamento.

**Ordem censura-antes-de-normalizacao.** `tem_censura` roda sobre a palavra CRUA, com a mascara (`*@#$%&`) ainda intacta, e so depois `normalizar` reverte homoglifo e apaga acento. Inverter a ordem apagaria a marca de censura antes de ela ser vista — "p*rra" perderia o asterisco e viraria uma palavra qualquer, nunca reconhecida como autocensura.

**Casamento por curinga.** `casar_censurado` trata cada simbolo de mascara como uma letra qualquer (regex com `.` no lugar do simbolo), nao como uma letra fixa: `p*rra` casa `porra`, `c*ralho` casa `caralho`. Mapear o simbolo para uma vogal fixa acertaria um caso e erraria o outro em silencio. Quando mais de um termo do lexicon casa o mesmo padrao com curinga, o desempate e pela MAIOR intensidade — deterministico, e nao pela ordem em que a linha aparece no CSV, o que deixaria o resultado dependente de onde alguem inseriu a linha.

**A excecao do `kkkk`.** Alongamento de caractere (`MINIMO_ALONGAMENTO = 3` repeticoes seguidas) e tratado como enfase, exceto para as letras de riso (`k`, `h`): "kkkk" e o marcador POSITIVO mais comum do chat brasileiro, e contar risada junto de "naooooo" inverteria o sentido da feature em boa parte das conversas reais.

**Limitacao a declarar:** o lexicon de palavrao e curadoria propria, nao recurso academico publicado. Diferente do SentiLex-PT02 (Silva, Carvalho e Sarmento, PROPOR 2012) e do Emoji Sentiment Ranking usados pelos outros sinais, `palavroes_ptbr.csv` nao tem paper citavel nem revisao por pares — a cobertura e a gradacao vieram de julgamento proprio, e isso precisa aparecer no relatorio como o que e.
