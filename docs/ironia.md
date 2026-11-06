# Ironia: corpus e régua

> **Estado em 08/10/2026.** O BERTimbau de ironia foi retreinado no notebook 04
> com a divisão por autor corrigida (treino 28.365 linhas, 58,8% irônicas; teste
> 4.778, 59,2%). Deu F1-macro de **0,994** no teste interno (0,991 só nos tweets)
> e P(irônico) = **1,000** em frases neutras de atendimento, como "qual o prazo
> de entrega do meu pedido" e "ok, obrigado". O modelo **não foi exportado**.
> Esta página explica por quê e o que fazer antes do próximo treino. Medições e
> passos da sessão: nota interna `docs/notas/2026-10-08-ironia-corpus.md`.
>
> **Produção não muda:** a ironia em produção é lida pelo BERTimbau e não entra
> no vetor do Fusor.

## Resumo: consertar o corpus antes de treinar de novo

O vício do IDPT 2021 está nos dados, não no modelo: a classe não irônica dos tweets é **100% de tweets com #economia**, publicados por ~658 contas, quase todas portais de notícia, só em maio e junho de 2017 ([arquivo bruto](https://raw.githubusercontent.com/fabio-ricardo/deteccao-ironia/b735dd95e92adacb73ed27b2a243d5461d7fda93/nao-ironico.csv)). As notícias foram rotuladas **pelo site de origem**, "sem nenhuma rotulação manual" ([Marten & de Freitas, ENIAC 2020](https://sol.sbc.org.br/index.php/eniac/article/download/12172/12037)). Chegar a "100% de exatidão" nesse teste não seria a prova esperada. Pela invariante 10 do projeto, seria o sintoma: ironia é uma tarefa em que anotadores humanos concordam pouco, e um acerto perfeito mostra que o teste mede a fonte. Qualquer encoder afinado nesse rótulo aprende registro e procedência. O ganho real virá de três coisas: trocar o negativo por fala coloquial sincera, medir numa régua de domínio com 200 a 400 itens em pares mínimos e comparar cada candidato com um baseline de estilo.

## O IDPT entrega o rótulo, e nenhum encoder escapa disso

O achado de 08/10 confirma o que os próprios arquivos mostram. No `nao-ironico.csv`, o commit `b735dd9` que o Fraus fixa, as hashtags dominantes são **2.519 `#economia` e 185 `#econom`**, e as datas vão só de 2017-05 a 2017-06. As contas mais frequentes são `noticiaminutobr`, `TSFRadio` (rádio portuguesa) e `portalR7`, e há tweets em espanhol e em português europeu no meio. Do outro lado, o `ironia.csv` tem ~12.700 tweets auto-marcados com `#ironia`, de ~9.300 autores, publicados entre 2014 e 2017. Só 78 tweets irônicos falam de economia, contra ~2.564 não irônicos ([dados verificados](https://raw.githubusercontent.com/fabio-ricardo/deteccao-ironia/b735dd95e92adacb73ed27b2a243d5461d7fda93/nao-ironico.csv)). O `scripts/preparar_corpus_ironia.py` remove a hashtag `#ironia`, mas o vazamento continua no tópico, na fonte e na época. Nas notícias, `estadao.json` é sempre 0, e `sensacionalista.json` e `the_piaui_herald.json` são sempre 1. Ou seja, a tabela fonte × rótulo tem **células vazias**: nenhum tweet coloquial sincero e nenhuma notícia séria irônica.

O histórico público do IDPT já mostrava isso antes do Fraus. O treino oficial tem 15.212 tweets e 18.494 notícias, enquanto os testes são "300 tweets and 300 news gathered and annotated by the organizers" ([García Subies, CEUR Vol-2943](https://ceur-ws.org/Vol-2943/idpt_paper3.pdf)). No teste de tweets, anotado por humanos, **o melhor time chegou a 0,52 de acurácia balanceada** ([Luz et al., BraSNAM 2023](https://sol.sbc.org.br/index.php/brasnam/article/download/24802/24623)), e o BERTimbau afinado ficou em 0,49–0,50, abaixo do acaso ([García Subies](https://ceur-ws.org/Vol-2943/idpt_paper3.pdf)). Enquanto isso, o SiDi-NLP relatou **F1 1,000 na validação de tweets**, tanto com BERTimbau quanto com mBERT ([CEUR Vol-2943](https://ceur-ws.org/Vol-2943/idpt_paper6.pdf)). O F1 de 0,99 que o BERTimbau retreinado deu no teste interno do Fraus, junto com P(irônico)=1,0 em frases neutras de atendimento, repete esse padrão: um número alto dentro da distribuição que desaba quando o rótulo vem de um humano. O padrão é conhecido na literatura. Quando o rótulo de sarcasmo passa a ser dado pelo próprio autor, o melhor modelo cai de F1 0,874 para 0,364 ([Oprea & Magdy, ACL 2020](https://aclanthology.org/2020.acl-main.118)). Filtrar os vieses do SNLI derruba um modelo de 92% para 62% ([Le Bras et al., 2020](https://arxiv.org/abs/2002.04108)).

O fine-tuning completo, com encoder e cabeça juntos, não escapa do atalho: o que separa a classe positiva da negativa é só o texto. Se registro, língua ou gênero textual predizem o rótulo, qualquer encoder aprende isso, o BERTimbau inclusive.

O "100% de exatidão" é inalcançável por um motivo independente do corpus: ironia é ambígua até para humanos. No Tweets8JanSPI, anotado à mão, o Fleiss κ da ironia foi **0,38**, contra 0,59 do sentimento ([BraSNAM 2026](https://sol.sbc.org.br/index.php/brasnam/article/download/43258/43024/)). O MultiPICo usa em média cinco anotadores por item justamente porque o julgamento varia ([ACL 2024](https://aclanthology.org/2024.acl-long.849.pdf)). Um modelo não pode concordar com um rótulo mais do que os humanos concordam entre si, a menos que esteja lendo outra coisa. A invariante 10 diz isso com outras palavras: "acurácia alta demais é sintoma, não vitória".

## Consertar o negativo vale mais que trocar o encoder

Os métodos de debiasing que mexem no modelo, como product-of-experts, autoviés, group DRO e DANN, só redistribuem peso entre exemplos que **contradizem** o atalho ([Clark et al. 2019](https://arxiv.org/abs/1909.03683); [Sagawa et al. 2020](https://arxiv.org/abs/1911.08731)). Com as células "coloquial × não irônico" e "notícia séria × irônico" vazias, não existe exemplo conflitante para repesar. Se a fonte é quase igual ao rótulo, apagar a fonte por treino adversarial apaga o rótulo junto. A correção tem de ser nos dados. O primeiro passo custa minutos: imprimir a tabela de contingência fonte × rótulo e, além dela, treinar um classificador "adivinhe a fonte". Se o rótulo sai da fonte, o corpus reprova antes de qualquer GPU, do mesmo jeito que a invariante 10 manda checar a sobreposição de distribuições por rótulo.

Não existe hoje um corpus PT-BR de ironia que seja grande, anotado por humanos e com negativos coloquiais naturais. O melhor candidato é o **MultiPICo-PT**: 1.994 pares post-resposta de Reddit e Twitter, metade brasileira e metade europeia, 49 anotadores nativos, ~38% irônicos, licença CC BY 4.0 e acesso livre no Hugging Face ([MultiPICo, ACL 2024](https://aclanthology.org/2024.acl-long.849.pdf); [HF](https://huggingface.co/datasets/Multilingual-Perspectivist-NLU/MultiPICo)). As duas classes saem da mesma amostragem e o rótulo vem do julgamento humano, não da fonte. O formato post-resposta combina com o Fraus, em que a fala do bot vem antes da do cliente. O Tweets8JanSPI (2.935 tweets, 224 irônicos, κ 0,38) tem o mesmo desenho, mas é distribuído desidratado, só com IDs, e trata de um único tópico ([BraSNAM 2026](https://sol.sbc.org.br/index.php/brasnam/article/download/43258/43024/)). O Kaggle "viniciuscleves" é um clone do mesmo corpus do IDPT ([Kaggle](https://www.kaggle.com/datasets/viniciuscleves/irony-and-sarcasm-in-brazilian-portuguese)). O de manchetes The Onion × HuffPost reproduz o rótulo por procedência ([Misra & Arora](https://arxiv.org/abs/2212.06035)).

A receita recomendada tem quatro camadas, da mais à menos importante. A primeira é **descartar as notícias**, porque nenhum dos dois lados é fala de cliente, e **substituir o `nao-ironico.csv`** por negativos coloquiais estratificados por polaridade: muito elogio sincero e muita reclamação literal, por exemplo B2W com 5 e com 1 estrela (licença CC BY-NC-SA 4.0, compatível com uso acadêmico ([README B2W](https://raw.githubusercontent.com/americanas-tech/b2w-reviews01/main/README.md))) e frases do GoEmotions-PT, que é Apache 2.0. Isso ataca o modo de falha já medido: a cabeça atual marca 74% das resenhas positivas da B2W como irônicas, contra 9% das negativas (`docs/treinamento.md`, 04/09/2026). A segunda é **somar o MultiPICo-PT**, como fatia de treino e de validação. A terceira são os **pares mínimos escritos à mão** no domínio de atendimento, no molde da subtarefa pareada do iSarcasmEval ([Abu Farha et al. 2022](https://aclanthology.org/2022.semeval-1.111)) e dos negativos por micro-edição do Puntuguese ([HF](https://huggingface.co/datasets/Superar/Puntuguese/blob/main/README.md)). Um exemplo de par: "ótimo serviço, resolveram rápido" × "ótimo serviço, só esperei 3 horas". Esses pares rendem mais como teste do que como treino, porque dados contrafactuais protegem as features perturbadas, mas podem piorar as que não foram perturbadas ([Joshi & He 2022](https://aclanthology.org/2022.acl-long.256)). A quarta é **minerar positivos de domínio** com heurística (elogio + situação negativa, "só que não", "parabéns" numa nota 1) e **confirmar cada um à mão**. Se a heurística virar o rótulo, o projeto volta ao rótulo por marcador. Os tweets irônicos do IDPT podem continuar como positivos, desde que tenham negativos do mesmo meio. Normalizar o estilo (minúsculas, sem URL, @, hashtag nem ponto final) é barato e remove pistas tipográficas, mas não remove o léxico de registro ("PIB", "Meirelles"). Por isso o efeito tem de ser medido com o baseline de estilo, antes e depois.

## Uma régua de pares mínimos separa as causas

O colapso de 02/10 tem uma explicação demonstrada: a divisão saiu com treino 86% irônico e teste 43% irônico, porque as 18.373 notícias sem autor caíam todas no teste. A mesma divisão fez o BERTimbau ficar em 0,511 de F1-macro. Mesmo corrigida, a divisão não decide nada sozinha, porque o rótulo continua sendo a fonte.

Todo treino usa a mesma divisão, conferida pela impressão de `metricas_ironia.json`, e a mesma semente. Cada um deve rodar duas vezes: uma no IDPT corrigido e outra no corpus consertado da seção anterior. A troca de corpus é o fator que a literatura indica como dominante, e é o que a banca vai querer ver. A divisão por autor não basta para medir o atalho. Hoje cada notícia sem autor vira um grupo próprio e se espalha pelos dois lados. Por isso é preciso uma função irmã de `dividir_por_autor` que agrupe por **fonte** (leave-one-source-out) e reaproveite `conferir_divisao`. Essa função vai falhar alto se a fonte for quase igual ao rótulo, e essa falha já é o diagnóstico.

O teste interno não decide nada, já que o BERTimbau marca 0,99 nele. Quem decide é uma **régua de domínio independente**, escrita por quem não viu as predições, congelada com `impressao_dos_textos` antes da primeira avaliação e marcada `independente=True` no laudo. A régua tem **200 a 400 itens em pares mínimos** e quatro estratos: elogio sincero, elogio irônico, reclamação literal (que separa ironia de sentimento negativo) e ironia sem marcador. Inclui ainda testes de invariância no estilo do CheckList ([Ribeiro et al. 2020](https://arxiv.org/abs/2005.04118)): o mesmo texto com e sem ponto final, em caixa alta ou baixa e com um emoji neutro tem de receber a mesma predição. A métrica principal é a **acurácia por par**, em que o modelo acerta os dois membros. O acaso aqui é 25%, e um modelo de estilo não consegue acertar os dois lados de um par com o mesmo registro. O tamanho sai de uma conta binomial própria: com acurácia em torno de 0,8, n=100 dá IC de ±7,8 pontos, n=200 dá ±5,5 e n=400 dá ±3,9. A régua atual tem 20 itens e IC de −0,28 a +0,17, larga demais para decidir qualquer coisa. Pares mínimos com troca de rótulo derrubam modelos em até 25% em relação ao teste original ([Gardner et al. 2020](https://arxiv.org/abs/2004.02709)), e é essa queda que o Fraus precisa conseguir medir.

Três baselines entram como modelos extras em `preditos_por_modelo`, no espírito do baseline "só a hipótese", que acerta ~67% no SNLI ([Gururangan et al. 2018](https://arxiv.org/abs/1803.02324)). O primeiro é **só estilo**: regressão logística sobre ~15 features sem léxico (comprimento, proporção de maiúsculas, ponto final, `!?…`, dígitos e R$, URL, @, hashtag, emoji, alongamento, "kkk"). O segundo é **só fonte**. O terceiro é **TF-IDF + LR**, que mostra a parte lexical do registro. Se o baseline de estilo também chega perto de 0,99 no teste interno, o teste mede procedência. O modelo só conta como detector de ironia se vencer o baseline de estilo **na régua**, com diferença demonstrada. `fraus/comparacao_modelos.py` já tem `mcnemar_exato`, `bootstrap_da_diferenca` (2.000 reamostras, F1-macro) e `avaliar_conjunto`, que já distinguem procedência igual de independente. As quatro peças que faltavam já existem no mesmo módulo: IC de um único modelo, **bootstrap por par** (reamostrar pares, e não itens, para preservar a dependência dentro do par), acurácia por par e **ECE** com diagrama de confiabilidade ([Guo et al. 2017](https://arxiv.org/abs/1706.04599)). O ECE importa porque o modelo sai superconfiante e a temperatura dele é ajustada numa fatia do próprio corpus viciado. Para o McNemar, o que conta são os pares discordantes: com ~20 discordantes, só uma divisão de 15:5 ou mais dá p<0,05. Como guarda de regressão, entra a medição que já existe em `docs/treinamento.md`: P(irônico) médio por estrela da B2W. Se a diferença entre resenhas positivas e negativas continuar grande, o atalho continua lá.

## Régua de pares mínimos

Estado: **rascunho pronto, anotação em andamento.** Spec em
`docs/superpowers/specs/2026-10-08-regua-pares-ironia-design.md` (interno).

- 150 pares (elogio, reclamação, neutra), registro equilibrado conferido por
  `conferir_registro_equilibrado` e, par a par, mesma vírgula e mesmo número
  de "?" nos dois lados. O baseline só de estilo acerta 0,18 dos pares fora
  da amostra no rascunho, abaixo do acaso (0,25). O rascunho é autoral; o
  rótulo que vale é o da anotação às cegas.
- A anotação mora no Fraus, por link e sem conta: `scripts/criar_link_anotacao.py
  --quantos N` chama `POST /anotacao/anotadores` (só dev) e imprime
  `<id>  https://fraus-one.vercel.app/anotar/<token>`. O banco guarda só o hash do
  token e um id opaco (`a_` + 8 hex), nunca nome. A página recebe de
  `GET /anotacao/<token>` só `id` e `texto`, na ordem daquele anotador, e grava
  por `POST /anotacao/<token>/respostas`; o instante é do servidor. A primeira
  rodada (João, na página antiga do claude.ai) está versionada em
  `fraus/dados/anotacao_regua/anotador-claude-ai.json`, anotador `claude-ai-1`.
- Para um grupo de mensagens, `scripts/criar_link_anotacao.py --grupo 5` cria
  **um** link (`https://fraus-one.vercel.app/anotar/grupo/<token>`) com 5
  vagas. Cada pessoa que o abre ganha o próprio anotador (a vaga é ocupada de
  forma serializada no banco, então 5 não viram 6) e a página guarda o link
  pessoal só naquele navegador. Em outro aparelho, abrir o link do grupo de
  novo gasta outra vaga e começa do zero; quem quiser trocar de aparelho guarda
  o endereço da página pessoal. Repassar o link do grupo também gasta vaga.
  Grupo cheio responde "Este link já foi usado por todas as pessoas previstas".
  Revogar o grupo (`POST /anotacao/grupos/<g_id>/revogar`) fecha a entrada;
  com `?anotadores=1` revoga também quem entrou, e as respostas saem do export.
- O token viaja na URL e fica nos logs de requisição da Vercel e no histórico
  do navegador, como o link de convite. Link vazado se revoga com
  `scripts/criar_link_anotacao.py --revogar <id>`; as respostas desse anotador
  saem do export.
- **Critério de promoção de qualquer cabeça de ironia:** vencer o baseline só
  de estilo (`fraus/baseline_estilo.py`) em acurácia por par na régua, com IC
  95% da diferença excluindo zero. O teste interno do IDPT não entra. No
  laudo isso é o campo `candidato_vence_por_par` (limite inferior do IC da
  diferença acima de zero). `por_par_demonstrada` só diz que o IC exclui zero
  e também acende quando o candidato é significativamente pior; para promover,
  vale `candidato_vence_por_par`.
- Depois da anotação: `uv run python scripts/exportar_anotacao.py respostas-fraus.json`
  baixa `GET /anotacao/respostas` (só dev) e
  `uv run python scripts/consolidar_regua_ironia.py fraus/dados/anotacao_regua/anotador-claude-ai.json respostas-fraus.json`
  concatena os arquivos e consolida. Menos de 100 pares confirmados para o
  script com erro dizendo quantos faltam.
- Cada registro é
  `{"anotador": "...", "frase_id": "...", "resposta": "ironico|nao_ironico|contexto", "instante": "2026-10-08T12:00:00.000000+00:00"}`;
  o script usa a última resposta de cada anotador por frase.
- A página embaralha a ordem por anotador (semente derivada do id) e nunca põe
  os dois lados de um par em sequência. A régua congelada guarda duas
  impressões no meta: uma dos textos e outra de `par_id|rótulo|texto`, de modo
  que trocar um rótulo ou mover um par também falha alto na carga.

## Conclusão

A pergunta "qual encoder lê ironia" foi formulada sobre um corpus que não sustenta nenhuma resposta, porque nele o rótulo é a fonte. A decisão que de fato move o resultado vem antes do encoder. São três passos: trocar o `nao-ironico.csv` de #economia e as notícias por fala coloquial sincera, construir a régua de pares mínimos e comparar cada modelo com um baseline de estilo que não sabe nada de ironia.

Para a banca, a meta de 100% se transforma num argumento a favor do projeto. Mostrar que o BERTimbau marca 0,99 no teste interno, que um classificador de pontuação e caixa alta chega perto disso, e que ambos caem para perto do acaso numa régua de pares mínimos é uma demonstração empírica da invariante 10 em ironia. Essa demonstração convence mais do que qualquer número alto. Promover o modelo depende de ele vencer o baseline de estilo na régua independente, com IC que exclua zero. O teste interno não serve para essa decisão.
