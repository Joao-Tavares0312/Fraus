# Ironia: corpus e Laya

> **Estado em 08/10/2026.** O BERTimbau de ironia foi retreinado no notebook 04
> com a divisão por autor corrigida (treino 28.365 linhas, 58,8% irônicas; teste
> 4.778, 59,2%). Deu F1-macro de **0,994** no teste interno (0,991 só nos tweets)
> e P(irônico) = **1,000** em frases neutras de atendimento, como "qual o prazo
> de entrega do meu pedido" e "ok, obrigado". O modelo **não foi exportado** e o
> Laya não foi treinado. Esta página explica por quê e o que fazer antes do
> próximo treino. Medições e passos da sessão: nota interna
> `docs/notas/2026-10-08-ironia-corpus.md`.
>
> **Produção não muda:** a ironia em produção é lida pelo Laya sem treino
> (`laya-onnx`) e não entra no vetor do Fusor.

## Resumo: consertar o corpus antes de treinar o Laya

Treinar o Laya (mmBERT-base, `laya==0.3.21`) só em ironia é fácil de fazer e não resolve o problema que motivou a ideia. O vício do IDPT 2021 está nos dados, não no modelo nem na mistura de tarefas: a classe não irônica dos tweets é **100% de tweets com #economia**, publicados por ~658 contas, quase todas portais de notícia, só em maio e junho de 2017 ([arquivo bruto](https://raw.githubusercontent.com/fabio-ricardo/deteccao-ironia/b735dd95e92adacb73ed27b2a243d5461d7fda93/nao-ironico.csv)). As notícias foram rotuladas **pelo site de origem**, "sem nenhuma rotulação manual" ([Marten & de Freitas, ENIAC 2020](https://sol.sbc.org.br/index.php/eniac/article/download/12172/12037)). Qualquer encoder afinado nesse rótulo aprende registro e procedência, seja o Laya sozinho, o Laya multitarefa ou o BERTimbau. O formato de pergunta do Laya não protege contra isso, porque a instrução e os critérios são tokens idênticos em todos os exemplos e o gradiente vem só do texto. Chegar a "100% de exatidão" nesse teste não seria a prova esperada. Pela invariante 10 do projeto, seria o sintoma: ironia é uma tarefa em que anotadores humanos concordam pouco, e um acerto perfeito mostra que o teste mede a fonte. O ganho real virá de três coisas: trocar o negativo por fala coloquial sincera, medir numa régua de domínio com 200 a 400 itens em pares mínimos e rodar três treinos que separem as causas. Pela literatura, a diferença de encoder entre o Laya e o BERTimbau deve ficar em poucos pontos. Contra o multitarefa de 02/10, o Laya só-ironia quase certamente vai "ganhar" no teste interno, mas esse ganho virá da divisão corrigida, e não do fato de treinar só ironia.

## O IDPT entrega o rótulo, e nenhum encoder escapa disso

O achado de 08/10 confirma o que os próprios arquivos mostram. No `nao-ironico.csv`, o commit `b735dd9` que o Fraus fixa, as hashtags dominantes são **2.519 `#economia` e 185 `#econom`**, e as datas vão só de 2017-05 a 2017-06. As contas mais frequentes são `noticiaminutobr`, `TSFRadio` (rádio portuguesa) e `portalR7`, e há tweets em espanhol e em português europeu no meio. Do outro lado, o `ironia.csv` tem ~12.700 tweets auto-marcados com `#ironia`, de ~9.300 autores, publicados entre 2014 e 2017. Só 78 tweets irônicos falam de economia, contra ~2.564 não irônicos ([dados verificados](https://raw.githubusercontent.com/fabio-ricardo/deteccao-ironia/b735dd95e92adacb73ed27b2a243d5461d7fda93/nao-ironico.csv)). O `scripts/preparar_corpus_ironia.py` remove a hashtag `#ironia`, mas o vazamento continua no tópico, na fonte e na época. Nas notícias, `estadao.json` é sempre 0, e `sensacionalista.json` e `the_piaui_herald.json` são sempre 1. Ou seja, a tabela fonte × rótulo tem **células vazias**: nenhum tweet coloquial sincero e nenhuma notícia séria irônica.

O histórico público do IDPT já mostrava isso antes do Fraus. O treino oficial tem 15.212 tweets e 18.494 notícias, enquanto os testes são "300 tweets and 300 news gathered and annotated by the organizers" ([García Subies, CEUR Vol-2943](https://ceur-ws.org/Vol-2943/idpt_paper3.pdf)). No teste de tweets, anotado por humanos, **o melhor time chegou a 0,52 de acurácia balanceada** ([Luz et al., BraSNAM 2023](https://sol.sbc.org.br/index.php/brasnam/article/download/24802/24623)), e o BERTimbau afinado ficou em 0,49–0,50, abaixo do acaso ([García Subies](https://ceur-ws.org/Vol-2943/idpt_paper3.pdf)). Enquanto isso, o SiDi-NLP relatou **F1 1,000 na validação de tweets**, tanto com BERTimbau quanto com mBERT ([CEUR Vol-2943](https://ceur-ws.org/Vol-2943/idpt_paper6.pdf)). O F1 de 0,99 que o BERTimbau retreinado deu no teste interno do Fraus, junto com P(irônico)=1,0 em frases neutras de atendimento, repete esse padrão: um número alto dentro da distribuição que desaba quando o rótulo vem de um humano. O padrão é conhecido na literatura. Quando o rótulo de sarcasmo passa a ser dado pelo próprio autor, o melhor modelo cai de F1 0,874 para 0,364 ([Oprea & Magdy, ACL 2020](https://aclanthology.org/2020.acl-main.118)). Filtrar os vieses do SNLI derruba um modelo de 92% para 62% ([Le Bras et al., 2020](https://arxiv.org/abs/2002.04108)).

A esperança de que o Laya "evitaria dados viciados" esbarra em como ele aprende. O fine-tuning do script oficial é completo, com encoder e cabeça juntos, sem LoRA. A sequência sempre começa com a mesma instrução e os mesmos critérios A/B de `PERGUNTA_IRONIA` ([`laya/common.py`](https://pypi.org/project/laya/0.3.21/), `build_sequence`). O que separa A de B é só o `state`, isto é, o texto. Se registro, língua ou gênero textual predizem o rótulo, o mmBERT aprende isso igualzinho ao BERTimbau. O próprio guia do Laya avisa: "The loop is only as good as the targets… treat their quality as the ceiling" ([finetune.md](https://github.com/NandhaKishorM/laya/blob/d8a2e59781ca135169a36095056132e273cd9938/docs/finetune.md)). O único ponto a favor do Laya tinha sido o prior zero-shot. Sem treino, ele fez F1 0,554 no teste interno e 0,524 na régua, com 0% de falso positivo, melhor que o BERTimbau. O run de 02/10 mostrou que o fine-tuning completo apaga esse prior (nota interna de 02/10, `docs/notas/2026-10-02-treino-laya.md`).

O "100% de exatidão" é inalcançável por um motivo independente do corpus: ironia é ambígua até para humanos. No Tweets8JanSPI, anotado à mão, o Fleiss κ da ironia foi **0,38**, contra 0,59 do sentimento ([BraSNAM 2026](https://sol.sbc.org.br/index.php/brasnam/article/download/43258/43024/)). O MultiPICo usa em média cinco anotadores por item justamente porque o julgamento varia ([ACL 2024](https://aclanthology.org/2024.acl-long.849.pdf)). Um modelo não pode concordar com um rótulo mais do que os humanos concordam entre si, a menos que esteja lendo outra coisa. A invariante 10 diz isso com outras palavras: "acurácia alta demais é sintoma, não vitória".

## Treinar só ironia exige mexer em sete células e num rótulo de produção

O pacote `laya==0.3.21` só faz inferência e não tem API de treino. O fine-tuning roda pelo script de pesquisa `finetune_single_device.py`, no commit `d8a2e597` ([script](https://raw.githubusercontent.com/NandhaKishorM/laya/d8a2e59781ca135169a36095056132e273cd9938/research/scripts/finetune_single_device.py)). O notebook 07 já o executa em subprocesso e confere o SHA-256. O script aceita tarefa única direto: basta o JSONL ter apenas linhas de `caso_ironia(texto, p)`, com `gold.ironia.probabilities = {"A": p, "B": 1-p}`, em que A = irônico. A ordem das chaves de `criteria` define a ordem do alvo. Por isso `PERGUNTA_IRONIA` tem de ser importada de `fraus/sinais/ironia_laya.py` e nunca redigitada, que é o mesmo cuidado que a invariante 8 pede para a ordem das classes.

As mudanças no notebook 07 (`notebooks/07_treino_laya.ipynb`) são estas, pela numeração "#" dos comentários das células:

| Célula | Hoje | Para só ironia |
|---|---|---|
| #2 (imports) | importa emoção e ironia | pode ficar; os nomes de emoção deixam de ser usados |
| #4 (corpus de emoção) | GoEmotions-pt + XED-pt | **pular inteira**; define `dados_emocao`, `emocao_teste`, `frases_xed`, usados adiante |
| #5 (divisão de ironia) | `dividir_por_autor`, `conferir_divisao`, guarda de impressão contra `metricas_ironia.json` | **não mexer**: é o que garante que o BERTimbau do notebook 04 foi treinado na mesma divisão |
| #6 (JSONL) | laço de emoção com `repeticoes_por_classe` + ironia suavizada 0,05 | só ironia; `proibidos` = teste de ironia ∪ régua; manter o `assert` de vazamento |
| #7 (treino) | `MODO_FUMACA`, `EPOCAS=4` | fumaça primeiro (600 casos), depois completo |
| #8 (comparação) | confere `DIR_BERT_EMOCAO`, prevê emoção e XED | tirar a emoção; manter `prever_*`, `comparar`, `laya.load` |
| #9 (ironia) | teste interno, recortes `tweets`/`noticias`, régua | sem mudança |
| #10 (poda + ONNX) | vocabulário com emoção, `cobertura_xed` | `perguntas = {**PERGUNTA_IRONIA}`; a cobertura precisa de outro texto independente |
| #11 (manifesto) | `perguntas: ["emocao","ironia"]` | `["ironia"]`; **ver a armadilha abaixo** |
| #12 (laudo) | conjuntos de emoção e ironia | só `ironia_interno`, `ironia_tweets`, `ironia_noticias`, `ironia_regua` |

A **armadilha do manifesto** é a parte que não aparece no notebook. Em `fraus/sinais/emocao_laya.py`, `laya_treinado_pelo_fraus(diretorio)` devolve `"emocao" in perguntas_do_artefato(diretorio)`, e um manifesto ausente equivale a `("ironia",)`. Assim, um artefato treinado só em ironia é **indistinguível do checkpoint base**, e a dashboard o rotularia como "Laya sem treino", o que é falso. Há um segundo efeito, mais silencioso: `obter_classificador_emocao_laya_onnx` reaproveita o mesmo agente e responderia emoção com uma cabeça afinada só em ironia. A correção precisa vir antes do treino e com TDD. O manifesto ganha um marcador explícito de procedência, por exemplo `"treinado_pelo_fraus": true` junto com a revisão e `rodada_de_fumaca: false`. `laya_treinado_pelo_fraus` passa a ler esse campo, e a leitura de emoção pelo Laya passa a recusar, com falha alta, um artefato que não declara `emocao`. Os dois testes falham primeiro com o manifesto só-ironia e passam depois.

Os hiperparâmetros estão quase todos fixos no código do script. A linha de comando aceita só `--data`, `--model-dir`, `--output-dir`, `--device`, `--epochs` e `--seed`. Mudar qualquer outra coisa obriga a editar o arquivo, o que quebra o SHA-256 conferido e precisa ser declarado como desvio do caminho oficial.

| Parâmetro | Valor no script | Recomendação para só ironia |
|---|---|---|
| Micro-lote / acumulação | 8 / nenhuma (lote efetivo 8) | manter; a receita 2×T4 do autor usa lote efetivo 64, mas isso exige editar o script |
| LR encoder / cabeça | 2,5e-5 / 1e-4, AdamW wd 0,01 | manter |
| Agenda | cosseno até 1e-6, sem warmup; σ do ruído de 0,4 a 0,1 | manter |
| Precisão | fp16 autocast + gradient checkpointing, clip 1,0 | manter |
| `max_len` | 1024 (forçado) | controlar pelo `MAX_CARACTERES` do notebook: **280–400** em vez de 1200, para aproximar o tamanho de uma mensagem de chat e baratear o treino |
| Épocas | padrão 4 | **2 a 3**: o corpus tem um atalho forte, e mais épocas tendem a decorá-lo |
| Semente | padrão 0 | 42 e mais duas sementes se o tempo couber, porque o fine-tuning é instável entre sementes ([Dodge et al. 2020](https://arxiv.org/abs/2002.06305); [Mosbach et al. 2021](https://arxiv.org/abs/2006.04884)) |
| Peso de classe | inexistente | dispensável: a divisão corrigida tem 59% de irônicas dos dois lados (≈1,4:1) |
| Suavização do alvo | 0,05 | considerar 0,1: rótulo por procedência não sustenta certeza de 0,975 |
| Calibração | temperatura por LBFGS em `min(400, n//10)` itens separados antes do treino | manter; ela não muda o argmax, mas muda qualquer limiar de 0,5 |

Sobre o tempo na T4: o run de 02/10 processou 142.204 itens (71.102 × 2 épocas) em 89 minutos, cerca de 26,6 itens/s com a carga incluída (nota interna de 02/10, `docs/notas/2026-10-02-treino-laya.md`). Com os 28.365 itens de treino da divisão corrigida, a conta direta dá **~18 minutos por época, ~35 minutos para 2 épocas e ~70–75 minutos para 4**. Essa é uma extrapolação de um único run. As notícias são bem mais longas que as frases do GoEmotions que dominavam aquele treino, então o tempo real pode ser 1,5 a 2× maior. A estimativa que vale é a que a rodada de fumaça imprime. O script não salva checkpoint por época. Chamá-lo várias vezes com `--epochs 1` também não equivale a um treino de N épocas, porque reinicia o cosseno, a σ do ruído e o otimizador e separa de novo a fatia de calibração. Como 2 a 3 épocas cabem numa sessão T4, o caminho mais simples é o atual: copiar para o Drive no fim.

## Consertar o negativo vale mais que trocar o encoder

Os métodos de debiasing que mexem no modelo, como product-of-experts, autoviés, group DRO e DANN, só redistribuem peso entre exemplos que **contradizem** o atalho ([Clark et al. 2019](https://arxiv.org/abs/1909.03683); [Sagawa et al. 2020](https://arxiv.org/abs/1911.08731)). Com as células "coloquial × não irônico" e "notícia séria × irônico" vazias, não existe exemplo conflitante para repesar. Se a fonte é quase igual ao rótulo, apagar a fonte por treino adversarial apaga o rótulo junto. A correção tem de ser nos dados. O primeiro passo custa minutos: imprimir a tabela de contingência fonte × rótulo e, além dela, treinar um classificador "adivinhe a fonte". Se o rótulo sai da fonte, o corpus reprova antes de qualquer GPU, do mesmo jeito que a invariante 10 manda checar a sobreposição de distribuições por rótulo.

Não existe hoje um corpus PT-BR de ironia que seja grande, anotado por humanos e com negativos coloquiais naturais. O melhor candidato é o **MultiPICo-PT**: 1.994 pares post-resposta de Reddit e Twitter, metade brasileira e metade europeia, 49 anotadores nativos, ~38% irônicos, licença CC BY 4.0 e acesso livre no Hugging Face ([MultiPICo, ACL 2024](https://aclanthology.org/2024.acl-long.849.pdf); [HF](https://huggingface.co/datasets/Multilingual-Perspectivist-NLU/MultiPICo)). As duas classes saem da mesma amostragem e o rótulo vem do julgamento humano, não da fonte. O formato post-resposta combina com o Fraus, em que a fala do bot vem antes da do cliente. O Tweets8JanSPI (2.935 tweets, 224 irônicos, κ 0,38) tem o mesmo desenho, mas é distribuído desidratado, só com IDs, e trata de um único tópico ([BraSNAM 2026](https://sol.sbc.org.br/index.php/brasnam/article/download/43258/43024/)). O Kaggle "viniciuscleves" é um clone do mesmo corpus do IDPT ([Kaggle](https://www.kaggle.com/datasets/viniciuscleves/irony-and-sarcasm-in-brazilian-portuguese)). O de manchetes The Onion × HuffPost reproduz o rótulo por procedência ([Misra & Arora](https://arxiv.org/abs/2212.06035)).

A receita recomendada tem quatro camadas, da mais à menos importante. A primeira é **descartar as notícias**, porque nenhum dos dois lados é fala de cliente, e **substituir o `nao-ironico.csv`** por negativos coloquiais estratificados por polaridade: muito elogio sincero e muita reclamação literal, por exemplo B2W com 5 e com 1 estrela (licença CC BY-NC-SA 4.0, compatível com uso acadêmico ([README B2W](https://raw.githubusercontent.com/americanas-tech/b2w-reviews01/main/README.md))) e frases do GoEmotions-PT, que é Apache 2.0. Isso ataca o modo de falha já medido: a cabeça atual marca 74% das resenhas positivas da B2W como irônicas, contra 9% das negativas (`docs/treinamento.md`, 04/09/2026). A segunda é **somar o MultiPICo-PT**, como fatia de treino e de validação. A terceira são os **pares mínimos escritos à mão** no domínio de atendimento, no molde da subtarefa pareada do iSarcasmEval ([Abu Farha et al. 2022](https://aclanthology.org/2022.semeval-1.111)) e dos negativos por micro-edição do Puntuguese ([HF](https://huggingface.co/datasets/Superar/Puntuguese/blob/main/README.md)). Um exemplo de par: "ótimo serviço, resolveram rápido" × "ótimo serviço, só esperei 3 horas". Esses pares rendem mais como teste do que como treino, porque dados contrafactuais protegem as features perturbadas, mas podem piorar as que não foram perturbadas ([Joshi & He 2022](https://aclanthology.org/2022.acl-long.256)). A quarta é **minerar positivos de domínio** com heurística (elogio + situação negativa, "só que não", "parabéns" numa nota 1) e **confirmar cada um à mão**. Se a heurística virar o rótulo, o projeto volta ao rótulo por marcador. Os tweets irônicos do IDPT podem continuar como positivos, desde que tenham negativos do mesmo meio. Normalizar o estilo (minúsculas, sem URL, @, hashtag nem ponto final) é barato e remove pistas tipográficas, mas não remove o léxico de registro ("PIB", "Meirelles"). Por isso o efeito tem de ser medido com o baseline de estilo, antes e depois.

## Três treinos e uma régua de 300 pares separam as causas

O colapso de 02/10 tem uma explicação demonstrada que não depende da multitarefa. A divisão saiu com treino 86% irônico e teste 43% irônico, porque as 18.373 notícias sem autor caíam todas no teste. O Laya treinado chegou a recall de **0,988 no irônico e 0,087 no não irônico**, com F1-macro de 0,388. A mesma divisão fez o BERTimbau ficar em 0,511, e a rodada de fumaça já mostrava 100% de falso positivo (nota interna de 02/10, `docs/notas/2026-10-02-treino-laya.md`). Ainda assim, a hipótese de interferência entre tarefas tem base. No pre-finetuning multitarefa, o desempenho cai quando há poucas tarefas ([Muppet](https://arxiv.org/abs/2101.11038)), e a mistura de 02/10 era 83% emoção para 17% ironia. Mas emoção e sentimento como tarefas auxiliares **ajudam** o sarcasmo em outros trabalhos ([Chauhan et al. 2020](https://aclanthology.org/2020.acl-main.401/)). Só um desenho controlado decide.

| Treino | O que varia | Comparação que responde |
|---|---|---|
| (i) Laya só ironia | tarefa única, divisão corrigida | (i) × (ii): a multitarefa atrapalha? |
| (ii) Laya emoção + ironia **balanceado** | amostragem por temperatura ou uma época de ironia por época de emoção | (i) × (ii): se Δ ≈ 0, a hipótese da multitarefa cai |
| (iii) BERTimbau só ironia (notebook 04) | encoder | (i) × (iii): o encoder importa, com dado e tarefa iguais? |

Os três treinos usam a mesma divisão, conferida pela impressão de `metricas_ironia.json`, e a mesma semente. Cada um deve rodar duas vezes: uma no IDPT corrigido e outra no corpus consertado da seção anterior. A troca de corpus é o fator que a literatura indica como dominante, e esse fator 2 × 3 é o que a banca vai querer ver. A divisão por autor não basta para medir o atalho. Hoje cada notícia sem autor vira um grupo próprio e se espalha pelos dois lados. Por isso é preciso uma função irmã de `dividir_por_autor` que agrupe por **fonte** (leave-one-source-out) e reaproveite `conferir_divisao`. Essa função vai falhar alto se a fonte for quase igual ao rótulo, e essa falha já é o diagnóstico.

O teste interno não decide nada, já que o BERTimbau marca 0,99 nele. Quem decide é uma **régua de domínio independente**, escrita por quem não viu as predições, congelada com `impressao_dos_textos` antes da primeira avaliação e marcada `independente=True` no laudo. A régua tem **200 a 400 itens em pares mínimos** e quatro estratos: elogio sincero, elogio irônico, reclamação literal (que separa ironia de sentimento negativo) e ironia sem marcador. Inclui ainda testes de invariância no estilo do CheckList ([Ribeiro et al. 2020](https://arxiv.org/abs/2005.04118)): o mesmo texto com e sem ponto final, em caixa alta ou baixa e com um emoji neutro tem de receber a mesma predição. A métrica principal é a **acurácia por par**, em que o modelo acerta os dois membros. O acaso aqui é 25%, e um modelo de estilo não consegue acertar os dois lados de um par com o mesmo registro. O tamanho sai de uma conta binomial própria: com acurácia em torno de 0,8, n=100 dá IC de ±7,8 pontos, n=200 dá ±5,5 e n=400 dá ±3,9. A régua atual tem 20 itens e IC de −0,28 a +0,17, larga demais para decidir qualquer coisa. Pares mínimos com troca de rótulo derrubam modelos em até 25% em relação ao teste original ([Gardner et al. 2020](https://arxiv.org/abs/2004.02709)), e é essa queda que o Fraus precisa conseguir medir.

Três baselines entram como modelos extras em `preditos_por_modelo`, no espírito do baseline "só a hipótese", que acerta ~67% no SNLI ([Gururangan et al. 2018](https://arxiv.org/abs/1803.02324)). O primeiro é **só estilo**: regressão logística sobre ~15 features sem léxico (comprimento, proporção de maiúsculas, ponto final, `!?…`, dígitos e R$, URL, @, hashtag, emoji, alongamento, "kkk"). O segundo é **só fonte**. O terceiro é **TF-IDF + LR**, que mostra a parte lexical do registro. Se o baseline de estilo também chega perto de 0,99 no teste interno, o teste mede procedência. O modelo só conta como detector de ironia se vencer o baseline de estilo **na régua**, com diferença demonstrada. `fraus/comparacao_modelos.py` já tem `mcnemar_exato`, `bootstrap_da_diferenca` (2.000 reamostras, F1-macro), `avaliar_conjunto` e `montar_laudo`, que já distinguem procedência igual de independente. As quatro peças que faltavam já existem no mesmo módulo: IC de um único modelo, **bootstrap por par** (reamostrar pares, e não itens, para preservar a dependência dentro do par), acurácia por par e **ECE** com diagrama de confiabilidade ([Guo et al. 2017](https://arxiv.org/abs/1706.04599)). O ECE importa porque o Laya sai superconfiante e a temperatura dele é ajustada numa fatia do próprio corpus viciado. Para o McNemar, o que conta são os pares discordantes: com ~20 discordantes, só uma divisão de 15:5 ou mais dá p<0,05. Como guarda de regressão, entra a medição que já existe em `docs/treinamento.md`: P(irônico) médio por estrela da B2W. Se a diferença entre resenhas positivas e negativas continuar grande, o atalho continua lá.

## O ganho esperado é de poucos pontos, e vem do dado

Contra o multitarefa de 02/10, o Laya só-ironia vai melhorar muito no teste interno: de 0,388 para algo bem acima, talvez perto do 0,99 do BERTimbau. Esse salto vem da divisão corrigida e da proporção de 59/59, que eliminam o colapso "tudo é irônico". Ele não deve ser atribuído ao treino em tarefa única nem apresentado como detecção de ironia. Na comparação justa, o treino (i) contra o (ii) balanceado, o tamanho de efeito publicado para multitarefa é de **poucos pontos, em qualquer direção** ([Standley et al. 2020](https://arxiv.org/abs/1905.07553); [Chauhan et al. 2020](https://aclanthology.org/2020.acl-main.401/)). O que se espera é empate dentro do IC.

Contra o BERTimbau, com tarefa e dado iguais, a literatura não dá motivo para esperar diferença grande. Em PT-BR, o BERTimbau vence o mBERT por margens de 2 a 4 pontos, por exemplo 89,2 contra 86,8 de F1 no ASSIN2 RTE ([neuralmind-ai](https://github.com/neuralmind-ai/portuguese-bert)). O mmBERT-base supera o XLM-R base no XTREME (72,8 contra 70,4), mas português é só ~2,4% da mistura de pré-treino, e o artigo não traz nenhum benchmark de classificação em português ([Marone et al. 2025](https://arxiv.org/html/2509.06888)). Há um precedente em que o mmBERT-base venceu o BERTimbau em NER clínico em português, com micro-F1 de 0,76, num preprint ainda sem revisão ([arXiv 2603.26510](https://arxiv.org/abs/2603.26510)). Não existe resultado de mmBERT, XLM-R ou Laya no IDPT, nem de afinação do Laya em ironia em qualquer língua. Na CPU, o Laya é mais lento: 459 ms contra 273 ms por mensagem na ironia, com ressalva, porque o Laya rodou em ONNX FP32 e o BERTimbau em PyTorch (nota interna de 02/10, `docs/notas/2026-10-02-treino-laya.md`). A velocidade do ModernBERT só aparece em GPU e em sequências longas.

A única vantagem estrutural do Laya para ironia é o vocabulário multilíngue, que permite misturar o MultiPICo das outras oito línguas. A literatura, porém, é desfavorável à transferência de ironia entre línguas: o viés de tópico dos corpora atrapalha ([Ortega-Bueno et al. 2023](https://boa.unimib.it/handle/10281/451401)), e detectores de sarcasmo não generalizam entre datasets ([Jang & Frassinelli 2024](https://aclanthology.org/2024.naacl-long.238)). O ganho que de fato muda o produto aparece na régua de domínio, quando se troca o corpus. Um modelo treinado no IDPT deve ficar perto do acaso por par, como o 0,52 oficial nos tweets. Um modelo treinado com negativos coloquiais e pares mínimos tem espaço para ganhar dezenas de pontos ali, na escala das quedas de 25 a 30 pontos que a literatura de contrast sets e filtragem adversarial atribui ao viés. Essa magnitude é inferência por analogia e não foi medida em português. A régua de 300 pares existe justamente para medi-la.

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
  `<id>  https://fraus.vercel.app/anotar/<token>`. O banco guarda só o hash do
  token e um id opaco (`a_` + 8 hex), nunca nome. A página recebe de
  `GET /anotacao/<token>` só `id` e `texto`, na ordem daquele anotador, e grava
  por `POST /anotacao/<token>/respostas`; o instante é do servidor. A primeira
  rodada (João, na página antiga do claude.ai) está versionada em
  `fraus/dados/anotacao_regua/anotador-claude-ai.json`, anotador `claude-ai-1`.
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

A pergunta "Laya ou BERTimbau, só ironia ou multitarefa" foi formulada sobre um corpus que não sustenta nenhuma das quatro respostas, porque nele o rótulo é a fonte. A decisão que de fato move o resultado vem antes do encoder. São três passos: trocar o `nao-ironico.csv` de #economia e as notícias por fala coloquial sincera, construir a régua de pares mínimos e comparar cada modelo com um baseline de estilo que não sabe nada de ironia. O Laya só-ironia continua valendo como experimento, como a célula (i) de um desenho controlado e não como conserto, e só depois de corrigir `laya_treinado_pelo_fraus` para que o produto não rotule um modelo treinado como "sem treino".

Para a banca, a meta de 100% se transforma num argumento a favor do projeto. Mostrar que o BERTimbau marca 0,99 no teste interno, que um classificador de pontuação e caixa alta chega perto disso, e que ambos caem para perto do acaso numa régua de pares mínimos é uma demonstração empírica da invariante 10 em ironia. Essa demonstração convence mais do que qualquer número alto. Promover o modelo depende de ele vencer o baseline de estilo na régua independente, com IC que exclua zero. O teste interno não serve para essa decisão.
