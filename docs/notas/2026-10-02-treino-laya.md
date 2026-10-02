# Treino do Laya para emoção e ironia — pesquisa e plano, 02/10/2026

Nota interna. Registra o que a pesquisa encontrou sobre treinar o Laya nas duas
tarefas do Fraus, o que foi medido localmente, o que **ainda não foi medido** e
a bibliografia levantada. O treino em si não rodou: o notebook
`notebooks/07_treino_laya.ipynb` está pronto e depende de uma sessão do Colab.

## O que o Laya é

**Não é um JEPA.** "Jev" é a API hospedada da TypeSafe; o Laya é a alternativa
aberta a ela. Nenhum documento do projeto fala em predição em espaço latente.
O que o repositório, os model cards e o código descrevem:

- encoder BERT bidirecional com uma cabeça de decisão treinada do zero (2
  camadas de transformer e um pontuador de opções);
- o checkpoint multilíngue, que é o que o Fraus usa, é **mmBERT-base**: 22
  camadas, hidden 768, vocabulário de 256 mil tokens, 322 M de parâmetros;
- uma pergunta `choice` vira `[CLS] instrução [SEP] [MASK] opção … [SEP] texto`;
  cada opção é pontuada no seu `[MASK]` e o softmax é entre as opções;
- licença Apache-2.0; repositório `NandhaKishorM/laya`, criado em 18/09/2026 e
  em desenvolvimento rápido (0.3.20 a 0.3.23 em poucos dias). O Fraus fixa
  `laya==0.3.21`.

O teste que já existia (`fraus/sinais/ironia_laya.py`) usa o checkpoint **sem
treino**: ele só redige a pergunta.

## Como se treina

O caminho oficial é fine-tuning **completo** — encoder e cabeça — sem LoRA,
adapters ou cabeça congelada.

| | |
|---|---|
| épocas | 4 |
| taxas | encoder 2,5e-5, cabeça 1e-4, AdamW, weight decay 0,01, cosseno |
| lote | 8 por passo |
| memória | fp16, gradient checkpointing, clip de norma 1,0 |
| dado | JSONL com `state`, `questions` e `gold` (probabilidade por opção) |

A perda (RLCD) soma um termo de policy-gradient sobre regras de pontuação
próprias a uma cross-entropy contra a **distribuição**-alvo. O alvo é uma
distribuição, não um rótulo — e o GoEmotions publica o voto de cada anotador,
então a emoção entra com a distribuição dos votos.

O script de GPU única (`research/scripts/finetune_single_device.py`) só existe
a partir da tag 0.3.23, mas importa apenas funções que a 0.3.21 já tem. O
notebook o baixa de um commit fixo, com SHA-256 conferido, e o roda contra o
pacote 0.3.21 instalado.

Limitações que o próprio autor documenta e que tocam as duas tarefas:

- os checkpoints saem **superconfiantes**; a temperatura precisa ser reajustada
  em dado separado antes de comparar probabilidade (acerto não muda);
- negação em escolha forçada pode seguir a pergunta em vez do texto (issue
  #377, reproduzida no multilíngue com resposta errada a 0,9998);
- muitas opções degradam a seleção por confiança (issue #394);
- o script não tem checkpoint por época nem peso de classe na perda.

## Sobre "100% de acerto"

Nada do que foi verificado sustenta essa meta. O melhor resultado que o autor
reporta no próprio benchmark, depois do fine-tuning, é 0,766. Nas tarefas do
Fraus o teto é dado pelos anotadores: emoção e ironia têm discordância humana
documentada (seção de avaliação da bibliografia), o corpus de emoção é
tradução automática e o de ironia foi rotulado por hashtag e procedência.

A invariante 10 já diz o resto: acurácia alta demais é sintoma. O primeiro
fusor marcou 99,3% lendo o relógio. A pergunta que o notebook responde é se o
Laya treinado **ganha do BERTimbau no mesmo teste, com diferença que sobrevive
a um teste estatístico** — McNemar exato e IC por bootstrap da diferença de
F1-macro (`fraus/comparacao_modelos.py`).

Os números do BERTimbau a bater, do cartão do modelo: emoção F1-macro 0,584 no
teste interno e **0,281 no XED-pt**. Em ironia, a régua de domínio de
`fraus/avaliacao_ironia.py` é quem decide, porque o BERTimbau treinado no IDPT
aprendeu sentimento positivo e o Laya treinado no mesmo dado pode repetir.

## O que foi medido nesta máquina

Rodada de fumaça em CPU, com 24 casos inventados e uma época. Prova que o
caminho funciona; **não mede qualidade**.

| Medida | Resultado |
|---|---|
| script oficial com `laya==0.3.21` e o JSONL de `fraus/treino_laya.py` | treina e grava checkpoint (54 s) |
| checkpoint treinado | carrega com `laya.load` e responde as duas perguntas |
| parâmetros | 321,9 M no total; **196,6 M (61%) na tabela de embeddings** |
| poda de vocabulário para 19.217 tokens | 140,1 M de parâmetros; desvio **0,0** contra o original |
| ONNX FP32 podado | 565 MB; desvio 0,0000 e nenhuma decisão trocada em 23 frases |
| ONNX INT8 (MatMul) podado | 200 MB; desvio máximo 0,53; **11 decisões trocadas** em 46 |
| ONNX INT8 (MatMul + Gather) podado | 155 MB; desvio máximo 0,34; 11 decisões trocadas em 46 |
| latência, duas perguntas por frase, 8 threads | 411 ms em FP32, 195 ms em INT8 |

Duas leituras:

1. **A poda de vocabulário é o ganho seguro.** É sem perda para texto coberto
   e tira mais da metade do modelo. O FP32 em produção hoje passa de 1 GB
   (comentário em `scripts/preparar_modelos_vercel.py`). A lista de 19 mil
   tokens veio só dos docs e léxicos do repositório; com os corpora de verdade
   ela cresce, e o notebook mede quanto do XED-pt cai em `<unk>`.
2. **O INT8 não está aprovado.** As trocas foram medidas num checkpoint com
   três passos de gradiente, com probabilidades coladas no limiar — não é
   representativo, mas também não é um sinal verde. O notebook só troca o FP32
   pelo INT8 se no máximo 1% das decisões mudar numa amostra do teste.

O grafo exportado aceita **uma frase e uma pergunta por chamada**: emoção e
ironia pelo Laya são duas passadas por mensagem.

## O que falta

- **Rodar o treino.** Primeiro com `MODO_FUMACA = True`, que valida o notebook
  inteiro em minutos e imprime a estimativa do treino completo na T4.
- **Decidir com os números.** Se o Laya treinado não ganhar do BERTimbau no
  XED-pt e na régua, ele não é promovido.
- **Emoção pelo Laya em produção não existe no código.** O ZIP do notebook
  tem o desenho do notebook 06 e a cabeça de ironia o lê sem mudança; ler
  emoção dele exige um adaptador novo e uma decisão sobre o Fusor, que foi
  treinado com as features `emocao_*` do BERTimbau.
- Não testado por ninguém: se a RLCD treina bem com alvo quase one-hot (o caso
  da ironia) e se o fine-tuning corrige a falha de negação da issue #377.

## Bibliografia

147 artigos distintos, levantados em 02/10/2026. Cada um teve a página aberta para
conferir título, autores e ano; os 101 do arXiv foram conferidos de novo contra a
API do arXiv. A linha de aplicação é leitura do resumo, não do artigo inteiro, e
em alguns itens o veículo de publicação vem de memória e não da página.

Ficaram de fora por não terem página verificada: o overview do IDPT 2021, o
artigo do BERTimbau, Dietterich (1998), Gneiting e Raftery (2007) e os corpora
brasileiros de sentimento (B2W-Reviews01, ReLi, TweetSentBR, OLIST).

### Corpora e modelos de emoção

1. [DailyDialog: A Manually Labelled Multi-turn Dialogue Dataset](https://arxiv.org/abs/1710.03957) — Li et al., 2017, IJCNLP 2017. Diálogos multi-turno rotulados manualmente com intenção e emoção, em inglês, útil como dado de diálogo para pré-ajuste ou comparação de emoção em conversa.
2. [EmoBank: Studying the Impact of Annotation Perspective and Representation Format on Dimensional Emotion Analysis](https://aclanthology.org/E17-2092/) — Buechel e Hahn, 2017, EACL 2017. Corpus de 10 mil sentenças com anotação VAD que mostra maior concordância na perspectiva do leitor, lembrando que a perspectiva de anotação afeta o rótulo de emoção.
3. [An Analysis of Annotated Corpora for Emotion Classification in Text](https://aclanthology.org/C18-1179/) — Bostan e Klinger, 2018, COLING 2018. Unifica corpora de emoção em um esquema comum e mostra em experimentos cross-corpus que juntar todos os dados de treino é subótimo, alertando para escolher corpora compatíveis em domínio.
4. [CARER: Contextualized Affect Representations for Emotion Recognition](https://aclanthology.org/D18-1404/) — Saravia et al., 2018, EMNLP 2018. Origem do corpus Emotion (DAIR) de tweets rotulados por hashtags, amplamente usado como benchmark de seis emoções, mas com rótulos de supervisão distante que exigem cautela como padrão-ouro.
5. [SemEval-2018 Task 1: Affect in Tweets](https://aclanthology.org/S18-1001/) — Mohammad et al., 2018, SemEval 2018. Tarefa com tweets em inglês, árabe e espanhol que cobre classificação de emoção e intensidade, referência clássica de protocolo de avaliação para emoção em texto curto.
6. [MELD: A Multimodal Multi-Party Dataset for Emotion Recognition in Conversations](https://arxiv.org/abs/1810.02508) — Poria et al., 2019, ACL 2019 (arXiv). Cerca de 13 mil falas de 1.433 diálogos de Friends com rótulos de emoção, benchmark de emoção em conversa, útil para avaliar o efeito do contexto de diálogo.
7. [SemEval-2019 Task 3: EmoContext Contextual Emotion Detection in Text](https://aclanthology.org/S19-2005/) — Chatterjee et al., 2019, SemEval 2019. Detecção de emoção em diálogo com 4 classes (feliz, triste, raiva, outros) e 30.160 diálogos de treino, vencedor com F1 micro de 79,59, mostrando que a classe feliz era a mais difícil.
8. [EmoEvent: A Multilingual Emotion Corpus based on different Events](https://aclanthology.org/2020.lrec-1.186) — Plaza del Arco et al., 2020, LREC 2020. Corpus de 8.409 tweets em espanhol e 7.303 em inglês com as seis emoções de Ekman mais neutro, rotulados por três anotadores, o esquema de sete classes mais próximo do usado no Fraus.
9. [GoEmotions: A Dataset of Fine-Grained Emotions](https://arxiv.org/abs/2005.00547) — Demszky et al., 2020, ACL 2020. Corpus de 58 mil comentários do Reddit com 27 emoções mais neutro e F1 médio de 0,46 com BERT, base mais usada para traduzir ao português e mapear para as 7 classes de Ekman.
10. [XED: A Multilingual Dataset for Sentiment Analysis and Emotion Detection](https://arxiv.org/abs/2011.01612) — Öhman et al., 2020, COLING 2020. Dataset de legendas anotado com as emoções de Plutchik mais neutro (25 mil frases em finlandês, 30 mil em inglês e projeção para 30 idiomas), usável para dados multilíngues com a ressalva de que a projeção de anotação introduz ruído.
11. [A Weakly Supervised Dataset of Fine-Grained Emotions in Portuguese](https://arxiv.org/abs/2108.07638) — Cortiz et al., 2021, STIL 2021. Corpus em português rotulado por supervisão fraca léxica, com BERT atingindo F1 de 0,64 em um padrão-ouro manual, evidenciando o custo-benefício e o risco de ruído de rótulo dessa estratégia.
12. [Universal Joy: A Data Set and Results for Classifying Emotions Across Languages](https://aclanthology.org/2021.wassa-1.7) — Lamprinidis et al., 2021, WASSA 2021. Mais de 530 mil posts do Facebook em 18 idiomas com cinco emoções, mostrando que mBERT transfere bem entre idiomas tipologicamente próximos e funciona em zero-shot.
13. [Utilizando BERTimbau para a Classificação de Emoções em Português](https://sol.sbc.org.br/index.php/stil/article/view/17784) — Hammes e Freitas, 2021, STIL 2021. Ajusta BERTimbau base e large em GoEmotions traduzido automaticamente para o português com algoritmo de balanceamento de classes, referência direta para o baseline BERTimbau e para o tratamento de desbalanceamento.
14. [XLM-EMO: Multilingual Emotion Prediction in Social Media Text](https://aclanthology.org/2022.wassa-1.18) — Bianchi et al., 2022, WASSA 2022. Reúne datasets de 19 idiomas e treina um modelo XLM-R multilíngue com bom desempenho zero-shot, modelo de como combinar corpora heterogêneos em um conjunto comum de emoções.
15. [Emotion Analysis in NLP: Trends, Gaps and Roadmap for Future Directions](https://arxiv.org/abs/2403.01222) — Plaza-del-Arco et al., 2024, LREC-COLING 2024. Survey de 154 trabalhos que critica o encaixe das taxonomias de Ekman e Plutchik na tarefa e a falta de consideração da subjetividade, base para justificar e declarar limitações da escolha de 7 classes.
16. [Portuguese Emotion Detection Model Using BERTimbau Applied to COVID-19 News and Replies](https://sol.sbc.org.br/index.php/bracis/article/view/33599) — Oliveira e Sichman, 2024, BRACIS 2024. Ajusta BERTimbau em GoEmotions traduzido para oito categorias de emoção e mostra a aplicação em respostas no Twitter, onde raiva é a classe mais prevalente (21,1%), indicando o desbalanceamento esperado em texto real.
17. [BRIGHTER: BRIdging the Gap in Human-Annotated Textual Emotion Recognition Datasets for 28 Languages](https://arxiv.org/abs/2502.11926) — Muhammad et al., 2025, ACL 2025. Corpus multilíngue anotado por falantes fluentes em 28 idiomas, multirrótulo com intensidade, útil como referência de protocolo de anotação e de avaliação mono e cross-lingual de emoção.
18. [Benchmarking Psychological Lexicons and Large Language Models for Emotion Detection in Brazilian Portuguese](https://pure.ewha.ac.kr/en/publications/benchmarking-psychological-lexicons-and-large-language-models-for/) — Aparecido et al., 2025, AI (MDPI) 6(10), 249. Compara BERTimbau, Mistral 24B e o léxico EmoAtlas em português, com BERTimbau na frente (acurácia 0,876) em 5.000 comentários do GoEmotions traduzidos por LLM, e custo computacional até 40 vezes maior nos transformers.
19. [Perspectives in Play: A Multi-Perspective Approach for More Inclusive NLP Systems](https://arxiv.org/abs/2506.20209) — Muscato et al., 2025, IJCAI 2025. Mostra que rótulos suaves preservam a discordância humana e melhoram o F1 em tarefas subjetivas, com menor confiança em ironia, alertando para a subjetividade dos rótulos de ironia e emoção.
20. [SemEval-2025 Task 11: Bridging the Gap in Text-Based Emotion Detection](https://arxiv.org/abs/2503.07269) — Muhammad et al., 2025, arXiv / SemEval-2025. Tarefa compartilhada com mais de 30 idiomas e seis categorias de emoção multirrótulo, mostrando o estado da arte recente em detecção multilíngue que serve de comparação para o encoder mmBERT.
21. [The Super Emotion Dataset](https://arxiv.org/abs/2505.15348) — Junqué de Fortuny, 2025, arXiv. Harmoniza várias fontes de texto em uma taxonomia única baseada em Shaver, sob licença CC BY-SA 4.0, exemplo de consolidação de taxonomias e de dado com licença permissiva.
22. [Exploratory Review of Emotion Recognition Resources in Brazilian Portuguese](https://journals-sol.sbc.org.br/index.php/jis/article/view/6767) — Joshi et al., 2026, Journal on Interactive Systems 17(1). Levantamento de 59 recursos de emoção em português brasileiro, pequenos e com menos de 60% disponíveis aberta ou sob pedido, justificando a escassez de dados e o uso de traduções.
23. [Quality and Agreement in Multilabel Emotion Annotation: A Case Study and Evaluation Framework](https://arxiv.org/abs/2606.21069) — Öhman e Koufakou, 2026, CAS @ LREC 2026. Propõe tratar a discordância entre anotadores como sinal com rótulos suaves de proporção de votos, em vez de voto majoritário, relevante para concordância e ruído de rótulo em emoção.

### Ironia e sarcasmo

24. [Semi-Supervised Recognition of Sarcasm in Twitter and Amazon](https://aclanthology.org/W10-2914/) — Davidov et al., 2010, CoNLL 2010 (ACL Anthology). Trabalho pioneiro de detecção semi-supervisionada em tweets e resenhas da Amazon, origem do uso de hashtags como rótulo fraco.
25. [Identifying Sarcasm in Twitter: A Closer Look](https://aclanthology.org/P11-2102/) — González-Ibáñez et al., 2011, ACL 2011 (ACL Anthology). Estudo inicial de sarcasmo no Twitter com rótulos por hashtag, referência para o limite entre rótulo do autor e julgamento humano.
26. [Sarcasm as Contrast between a Positive Sentiment and Negative Situation](https://aclanthology.org/D13-1066/) — Riloff et al., 2013, EMNLP 2013 (ACL Anthology). Fundamenta a ideia de que a ironia surge do contraste entre sentimento positivo e situação negativa, base da feature de incongruência do Fraus.
27. [Bazinga! Caracterizando e Detectando Sarcasmo e Ironia no Twitter](http://www.each.usp.br/digiampietri/BraSNAM/2015/p12.pdf) — Gonçalves et al., 2015, BraSNAM 2015 (CSBC). Base coletada automaticamente pelas hashtags #sarcasm e #irony em tweets, exemplo clássico de supervisão distante por hashtag, com caracterização linguística e classificação por Macro-F1.
28. [Contextualized Sarcasm Detection on Twitter](https://homes.cs.washington.edu/~nasmith/papers/bamman+smith.icwsm15.pdf) — Bamman e Smith, 2015, ICWSM 2015. Mostra que features extralinguísticas (autor, audiência, ambiente da conversa) elevam a acurácia sobre features só de texto, sustentando o papel do contexto.
29. [Automatic Sarcasm Detection: A Survey](https://arxiv.org/abs/1602.03426) — Joshi et al., 2016, arXiv:1602.03426 (ACM Computing Surveys). Survey que organiza a área em padrões semi-supervisionados, supervisão por hashtag e uso de contexto, com tabela de datasets, tipos de feature e métodos de anotação.
30. [The Role of Conversation Context for Sarcasm Detection in Online Interactions](https://arxiv.org/abs/1707.06226) — Ghosh et al., 2017, SIGDIAL 2017 (arXiv:1707.06226). LSTM com atenção sobre contexto e resposta supera o modelo que lê só a resposta, argumento para incluir a fala anterior do atendente ao julgar ironia do cliente.
31. [#SarcasmDetection is soooo general! Towards a Domain-Independent Approach for Detecting Sarcasm](https://arxiv.org/abs/1806.03369) — Parde e Nielsen, 2018, FLAIRS-30 (arXiv:1806.03369). Detectores de sarcasmo rendem bem só no domínio de treino, e features generalizáveis com adaptação de domínio chegaram a F1 de 0,780 contra baselines de 0,515 e 0,345.
32. [A Large Self-Annotated Corpus for Sarcasm (SARC)](https://arxiv.org/abs/1704.05579) — Khodak et al., 2018, LREC 2018 (arXiv:1704.05579). Corpus do Reddit com 1,3 milhão de afirmações sarcásticas rotuladas pelos próprios autores, com contexto de conversa e cenários balanceado e desbalanceado, útil como dado de pré-treino em inglês.
33. [SemEval-2018 Task 3: Irony Detection in English Tweets](https://aclanthology.org/S18-1005/) — Van Hee et al., 2018, SemEval-2018 (ACL Anthology). Corpus de 3.834 tweets de treino coletados por hashtags (#irony, #sarcasm, #not) e anotados manualmente, com melhor F1 de 0,71 na tarefa binária e 0,51 na multiclasse, mostrando que ironia binária é bem mais fácil que tipos de ironia.
34. [Overview of the Task on Irony Detection in Spanish Variants (IroSvA 2019)](https://ceur-ws.org/Vol-2421/IroSvA_overview.pdf) — Ortega-Bueno et al., 2019, IberLEF 2019 (CEUR Vol-2421). Tarefa de ironia em tweets e comentários com contexto, F1 macro máximo de 0,7167, 0,6803 e 0,6596 nas três variantes, e concordância de Cohen kappa médio de 0,67 em uma das etapas de anotação.
35. [iSarcasm: A Dataset of Intended Sarcasm](https://arxiv.org/abs/1911.03123) — Oprea e Magdy, 2019, arXiv:1911.03123 (ACL 2020). Distingue sarcasmo pretendido de percebido e mostra que modelos de ponta têm desempenho baixo quando o rótulo vem do autor, indicando que corpora rotulados por hashtag ou terceiros são enviesados ou óbvios demais.
36. [A Transformer-based Approach to Irony and Sarcasm Detection](https://arxiv.org/abs/1911.10401) — Potamias et al., 2020, Neural Computing and Applications (arXiv:1911.10401). Combina transformer pré-treinado com RCNN em quatro benchmarks de linguagem figurada com pouco pré-processamento, referência de arquitetura sobre encoder.
37. [TweetEval: Unified Benchmark and Comparative Evaluation for Tweet Classification](https://aclanthology.org/2020.findings-emnlp.148/) — Barbieri et al., 2020, Findings of EMNLP 2020. Benchmark de sete tarefas de tweets (inclui ironia) que mostra que continuar o pré-treino de modelos genéricos em corpus do Twitter ajuda, referência de baseline para ironia.
38. [CISUC at IDPT2021: Traditional and Deep Learning for Irony Detection in Portuguese](https://ceur-ws.org/Vol-2943/idpt_paper2.pdf) — Gonçalo Oliveira et al., 2021, IberLEF 2021 (CEUR Vol-2943). Compara regressão logística e BERT em tweets e notícias do IDPT, observa que F1 de validação muito alto sugere que ironia em texto formal não é tão difícil, e analisa as features mais importantes.
39. [GuillemGSubies at IDPT2021: Identifying Irony in Portuguese with BERT](https://ceur-ws.org/Vol-2943/idpt_paper3.pdf) — García Subies, 2021, IberLEF 2021 (CEUR Vol-2943). Afina BERTimbau com grid search e aumento de dados por substituição MLM no IDPT, receita direta de comparação com o BERTimbau do Fraus.
40. [Irony Detection in the Portuguese Language using BERT (BERT4EVER)](https://ceur-ws.org/Vol-2943/idpt_paper1.pdf) — Jiang et al., 2021, IberLEF 2021 (CEUR Vol-2943). Ficou à frente nas notícias do IDPT com BERT, perda ponderada e ensemble, mas na tabela de teste de tweets a acurácia balanceada ficou em torno de 0,50, ou seja, acaso, apesar de cerca de 0,91 na validação de notícias.
41. [Perceived and Intended Sarcasm Detection with Graph Attention Networks](https://arxiv.org/abs/2110.04001) — Plepi e Flek, 2021, Findings of EMNLP 2021 (arXiv:2110.04001). Usa histórico do usuário e grafo de conversa em 30 mil tweets rotulados e mostra que o contexto captura melhor a intenção do autor que a percepção do leitor.
42. [PiLN IDPT 2021: Irony Detection in Portuguese Texts with Superficial Features and Embeddings](https://ceur-ws.org/Vol-2943/idpt_paper4.pdf) — Anchiêta et al., 2021, IberLEF 2021 (CEUR Vol-2943). Usa features superficiais, embeddings e retrotradução para equilibrar o corpus de tweets (12.736 irônicos contra 3.156 não irônicos após o aumento) e ficou em primeiro e segundo nos tweets.
43. [Sarcasm Detection: A Comparative Study](https://arxiv.org/abs/2107.02276) — Yaghoobian et al., 2021, arXiv:2107.02276. Revisão comparativa que retoma os padrões semi-supervisionados, a supervisão por hashtag e o uso de contexto como marcos da área.
44. [SiDi-NLP-Team at IDPT2021: Irony Detection in Portuguese 2021](https://ceur-ws.org/Vol-2943/idpt_paper6.pdf) — Almeida Neto et al., 2021, IberLEF 2021 (CEUR Vol-2943). Reporta acurácia e F1 de 1,000 para BERTimbau e mBERT na validação holdout de tweets, sinal de que o corpus de tweets permite atalhos ou vazamento, contra F1 de 0,900 do BERTimbau nas notícias.
45. [TeamUFPR at IDPT 2021: Equalizing a Strategy Using Machine Learning for Two Types of Data in Detecting Irony](https://ceur-ws.org/Vol-2943/idpt_paper5.pdf) — Heinrich et al., 2021, IberLEF 2021 (CEUR Vol-2943). Avalia dez algoritmos clássicos com quatro estratégias de seleção de features e subamostragem nos dois corpora do IDPT, mostrando que lematização não ajuda.
46. [SemEval-2022 Task 6: iSarcasmEval, Intended Sarcasm Detection in English and Arabic](https://aclanthology.org/2022.semeval-1.111/) — Abu Farha et al., 2022, SemEval-2022 (ACL Anthology). Rótulos fornecidos pelos próprios autores dos textos evitam supervisão distante e anotação de terceiros, e a maioria das 60 equipes usou modelos de linguagem pré-treinados, o que sustenta usar encoders afinados como o mmBERT.
47. [Improving Irony Detection by Balancing Methods and Feature Selection](https://sol.sbc.org.br/index.php/brasnam/article/view/24802) — Luz et al., 2023, BraSNAM 2023 (SOL/SBC). Trabalho em português sobre o corpus IDPT que reporta acurácia balanceada de 0,55 e mostra que amostragem e seleção de features melhoram o resultado sob desbalanceamento.
48. [Generalizable Sarcasm Detection Is Just Around The Corner, Of Course!](https://arxiv.org/abs/2404.06357) — Jang e Frassinelli, 2024, arXiv:2404.06357. Em quatro datasets, modelos afinados falham em generalizar entre datasets e rótulos de terceiros rendem mais que os dos autores, alertando contra extrapolar o resultado do IDPT para mensagens de atendimento.
49. [SarcasmBench: Towards Evaluating Large Language Models on Sarcasm Understanding](https://arxiv.org/abs/2408.11319) — Zhang et al., 2024, arXiv:2408.11319. Em seis benchmarks, 11 LLMs ficam abaixo de baselines supervisionados de modelos pré-treinados e o prompting few-shot é o mais eficaz, apoiando o afinamento de encoder em vez de LLM.

### Encoders e fine-tuning completo

50. [Training Deep Nets with Sublinear Memory Cost](https://arxiv.org/abs/1604.06174) — Chen et al., 2016, arXiv (1604.06174). Origem do gradient checkpointing: memória O(sqrt(n)) em troca de um forward extra, útil para caber lotes maiores ou sequências longas na T4.
51. [SGDR: Stochastic Gradient Descent with Warm Restarts](https://arxiv.org/abs/1608.03983) — Loshchilov & Hutter, 2017, ICLR 2017. Origem do agendamento de LR por cosseno com reinícios, referência para o decaimento cosseno usado após o warmup no fine-tuning.
52. [BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding](https://arxiv.org/abs/1810.04805) — Devlin et al., 2018, arXiv (1810.04805). Base do paradigma de pré-treino MLM + fine-tuning completo com uma cabeça mínima por tarefa, que é o ponto de partida do BERTimbau e do mmBERT.
53. [Focal Loss for Dense Object Detection](https://arxiv.org/abs/1708.02002) — Lin et al., 2018, arXiv (1708.02002). A focal loss reduz o peso dos exemplos fáceis e é uma opção para lidar com desbalanceamento de classes, relevante às classes raras de emoção.
54. [Mixed Precision Training](https://arxiv.org/abs/1710.03740) — Micikevicius et al., 2018, ICLR 2018. Base da precisão mista: pesos mestres em FP32 e escalonamento de perda, com redução de cerca de 2x na memória sem perda de acurácia, o que viabiliza o treino na T4.
55. [Universal Language Model Fine-tuning for Text Classification](https://arxiv.org/abs/1801.06146) — Howard & Ruder, 2018, ACL 2018. Origem das técnicas de fine-tuning discriminativo (LR por camada) e descongelamento gradual, que reduziram o erro em 18-24% na maioria dos datasets.
56. [Class-Balanced Loss Based on Effective Number of Samples](https://arxiv.org/abs/1901.05555) — Cui et al., 2019, arXiv (1901.05555). Repondera a perda pelo número efetivo de amostras (1-β^n)/(1-β), alternativa fundamentada a pesos inversamente proporcionais à frequência em classes de emoção desbalanceadas.
57. [Decoupled Weight Decay Regularization](https://arxiv.org/abs/1711.05101) — Loshchilov & Hutter, 2019, ICLR 2019. Define o AdamW, com weight decay desacoplado do gradiente adaptativo, o otimizador padrão recomendado para o fine-tuning completo do encoder.
58. [How multilingual is Multilingual BERT?](https://arxiv.org/abs/1906.01502) — Pires et al., 2019, arXiv (1906.01502). Documenta que o mBERT transfere entre línguas mas com deficiências sistemáticas em certos pares, contexto para preferir um encoder específico ou moderno para o português.
59. [How to Fine-Tune BERT for Text Classification?](https://arxiv.org/abs/1905.05583) — Sun et al., 2019, arXiv (1905.05583). Estudo sistemático de estratégias de fine-tuning do BERT para classificação de texto (incluindo pré-treino adicional e escolhas de taxa de aprendizado), com novo estado da arte em oito datasets.
60. [Multi-Task Deep Neural Networks for Natural Language Understanding](https://arxiv.org/abs/1901.11504) — Liu et al., 2019, ACL 2019. Treino multitarefa sobre BERT atua como regularizador e melhora o GLUE para 82,7%, base para considerar um encoder compartilhado entre emoção e ironia.
61. [RoBERTa: A Robustly Optimized BERT Pretraining Approach](https://arxiv.org/abs/1907.11692) — Liu et al., 2019, arXiv (1907.11692). Mostra que o BERT original estava subtreinado e que escolhas de hiperparâmetros e dados pesam muito, justificando comparar encoders por receita de treino e não só por arquitetura.
62. [DeBERTa: Decoding-enhanced BERT with Disentangled Attention](https://arxiv.org/abs/2006.03654) — He et al., 2020, arXiv (2006.03654). Atenção desentrelaçada de conteúdo e posição supera RoBERTa-large (+0,9% MNLI), base arquitetural do Albertina PT-* e referência de encoder forte.
63. [Don't Stop Pretraining: Adapt Language Models to Domains and Tasks](https://arxiv.org/abs/2004.10964) — Gururangan et al., 2020, ACL 2020. Pré-treino adicional no domínio (DAPT) e na tarefa (TAPT) traz ganhos em classificação, justificando continuar o MLM sobre texto de atendimento antes do fine-tuning.
64. [ELECTRA: Pre-training Text Encoders as Discriminators Rather Than Generators](https://arxiv.org/abs/2003.10555) — Clark et al., 2020, ICLR 2020. Pré-treino por detecção de token substituído é mais eficiente em amostras que o MLM, e o artigo é referência para práticas de fine-tuning como decaimento de LR por camada.
65. [Fine-Tuning Pretrained Language Models: Weight Initializations, Data Orders, and Early Stopping](https://arxiv.org/abs/2002.06305) — Dodge et al., 2020, arXiv (2002.06305). Inicialização e ordem dos dados contribuem de forma comparável para a variância entre sementes, e muitas execuções divergem cedo, o que sustenta rodar várias sementes e usar early stopping.
66. [Mixout: Effective Regularization to Finetune Large-scale Pretrained Language Models](https://arxiv.org/abs/1909.11299) — Lee et al., 2020, ICLR 2020. Regularização que mistura estocasticamente parâmetros do modelo pré-treinado e do ajustado, melhorando a estabilidade e a acurácia média do fine-tuning do BERT em dados pequenos.
67. [SMART: Robust and Efficient Fine-Tuning for Pre-trained Natural Language Models through Principled Regularized Optimization](https://arxiv.org/abs/1911.03437) — Jiang et al., 2020, ACL 2020. Combina regularização de suavidade e otimização proximal de Bregman para conter overfitting e esquecimento catastrófico no fine-tuning com poucos dados.
68. [Unsupervised Cross-lingual Representation Learning at Scale](https://arxiv.org/abs/1911.02116) — Conneau et al., 2020, ACL 2020. XLM-R mostra que um encoder multilíngue (100 línguas) pode ficar competitivo com modelos monolingues, argumento direto para usar um encoder multilíngue como o mmBERT em português.
69. [Exploiting Cloze Questions for Few Shot Text Classification and Natural Language Inference](https://arxiv.org/abs/2001.07676) — Schick & Schütze, 2021, EACL 2021. PET reformula a tarefa como pergunta cloze e usa o MLM pré-treinado como classificador, precursor direto da pontuação de opções em tokens [MASK].
70. [It's Not Just Size That Matters: Small Language Models Are Also Few-Shot Learners](https://arxiv.org/abs/2009.07118) — Schick & Schütze, 2021, NAACL 2021. Mostra que modelos pequenos com perguntas cloze e otimização por gradiente rivalizam com modelos muito maiores, apoiando o uso de um encoder base em vez de LLM.
71. [Making Pre-trained Language Models Better Few-shot Learners](https://arxiv.org/abs/2012.15723) — Gao et al., 2021, ACL 2021. LM-BFF formaliza o fine-tuning baseado em prompt com cloze e [MASK], o mecanismo da cabeça do Laya, com ganho de até 30% (11% em média) sobre fine-tuning padrão em poucos exemplos.
72. [On the Stability of Fine-tuning BERT: Misconceptions, Explanations, and Strong Baselines](https://arxiv.org/abs/2006.04884) — Mosbach et al., 2021, ICLR 2021. Atribui a instabilidade a gradientes que desaparecem na otimização e não a esquecimento catastrófico ou dataset pequeno, e propõe uma receita simples que estabiliza o fine-tuning.
73. [R-Drop: Regularized Dropout for Neural Networks](https://arxiv.org/abs/2106.14448) — Liang et al., 2021, NeurIPS 2021. Minimiza a divergência KL bidirecional entre duas passagens com dropout, regularização aplicável ao fine-tuning de RoBERTa-large e similares.
74. [Revisiting Few-sample BERT Fine-tuning](https://arxiv.org/abs/2006.05987) — Zhang et al., 2021, arXiv (2006.05987). Aponta o otimizador com estimativa de gradiente enviesada, o subuso de camadas e poucas iterações como causas de instabilidade, apoiando o uso de AdamW com correção de viés e mais épocas.
75. [Advancing Neural Encoding of Portuguese with Transformer Albertina PT-*](https://arxiv.org/abs/2305.06721) — Rodrigues et al., 2023, arXiv (2305.06721). Encoder DeBERTa específico para português (PT-PT e PT-BR) em hardware de consumo, comparador natural ao BERTimbau e ao mmBERT na avaliação.
76. [DeBERTaV3: Improving DeBERTa using ELECTRA-Style Pre-Training with Gradient-Disentangled Embedding Sharing](https://arxiv.org/abs/2111.09543) — He et al., 2023, ICLR 2023. Mostra que o pré-treino estilo ELECTRA com compartilhamento de embeddings desentrelaçado melhora o GLUE (91,37% no large) e traz a variante multilíngue mDeBERTa como alternativa de encoder.
77. [Smarter, Better, Faster, Longer: A Modern Bidirectional Encoder for Fast, Memory Efficient, and Long Context Finetuning and Inference](https://arxiv.org/abs/2412.13663) — Warner et al., 2024, arXiv (2412.13663). Apresenta o ModernBERT (2T tokens, contexto de 8192), a arquitetura da família do mmBERT/Laya, projetada para fine-tuning e inferência eficientes em memória em GPUs comuns como a T4.
78. [mmBERT: A Modern Multilingual Encoder with Annealed Language Learning](https://arxiv.org/abs/2509.06888) — Marone et al., 2025, arXiv (2509.06888). Descreve o encoder multilíngue ModernBERT-based (3T tokens, mais de 1.800 línguas) com cronograma de máscara inverso, que é o backbone do Laya usado no projeto.

### PEFT, few-shot, destilação, JEPA e aumento de dados

79. [Distilling the Knowledge in a Neural Network](https://arxiv.org/abs/1503.02531) — Hinton et al., 2015, arXiv (NIPS 2014 Workshop). Introduz a destilação com soft targets de temperatura, base da soft cross-entropy contra distribuições do modelo professor usada no treino do Laya.
80. [mixup: Beyond Empirical Risk Minimization](https://arxiv.org/abs/1710.09412) — Zhang et al., 2018, ICLR 2018. Treinar em combinações convexas de pares de exemplos e rótulos reduz a memorização de rótulos corrompidos, relevante para rótulos de emoção e ironia ruidosos.
81. [Benchmarking Zero-shot Text Classification: Datasets, Evaluation and Entailment Approach](https://arxiv.org/abs/1909.00161) — Yin et al., 2019, EMNLP 2019. Formular a classificação zero-shot como inferência textual (NLI) cobre aspectos como emoção e situação, base conceitual para uma cabeça zero-shot guiada por instrução e critérios.
82. [DistilBERT, a distilled version of BERT: smaller, faster, cheaper and lighter](https://arxiv.org/abs/1910.01108) — Sanh et al., 2019, arXiv (NeurIPS 2019 EMC2 Workshop). Destilar um BERT reduz 40% do tamanho mantendo 97% da compreensão de linguagem e 60% mais rápido, referência para classificadores compactos em produção sem LLM.
83. [EDA: Easy Data Augmentation Techniques for Boosting Performance on Text Classification Tasks](https://arxiv.org/abs/1901.11196) — Wei et al., 2019, EMNLP-IJCNLP 2019. Quatro operações simples (sinônimo, inserção, troca, remoção) igualaram com 50% dos dados o treino com todos, aplicável de forma barata ao corpus pequeno de ironia.
84. [Parameter-Efficient Transfer Learning for NLP](https://arxiv.org/abs/1902.00751) — Houlsby et al., 2019, arXiv (ICML 2019). Adapters inseridos entre camadas ficam a 0,4% do fine-tuning completo adicionando 3,6% de parâmetros por tarefa, uma opção para manter um encoder base compartilhado entre as tarefas de emoção e de ironia.
85. [Supervised Contrastive Learning](https://arxiv.org/abs/2004.11362) — Khosla et al., 2020, NeurIPS 2020 / arXiv. A perda contrastiva supervisionada aproxima embeddings da mesma classe e afasta as demais, alcançando 81,4% top-1 no ImageNet com ResNet-200, candidata a termo auxiliar na representação das 7 emoções.
86. [TinyBERT: Distilling BERT for Natural Language Understanding](https://arxiv.org/abs/1909.10351) — Jiao et al., 2020, Findings of EMNLP 2020. Destilação em camadas (embeddings, atenção, saídas) faz um aluno de 4 camadas alcançar mais de 96,8% do professor, mostrando que o sinal do professor pode ir além dos logits.
87. [Unsupervised Data Augmentation for Consistency Training](https://arxiv.org/abs/1904.12848) — Xie et al., 2020, NeurIPS 2020. Consistência entre exemplo original e aumentado (inclusive retrotradução) permite, no IMDb, 4,20% de erro com 20 rótulos, argumentando o uso de dados não rotulados de atendimento.
88. [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685) — Hu et al., 2021, arXiv (ICLR 2022). Treinar só matrizes de baixo posto congelando o encoder permite adaptar o Laya ou o BERTimbau a emoção/ironia com poucos parâmetros treináveis, reduzindo 10.000 vezes os parâmetros em relação ao fine-tuning completo no GPT-3 175B.
89. [Prefix-Tuning: Optimizing Continuous Prompts for Generation](https://arxiv.org/abs/2101.00190) — Li et al., 2021, arXiv (ACL 2021). Ajustar apenas prefixos contínuos (0,1% dos parâmetros) supera o fine-tuning em regime de poucos dados, argumento relevante para a ironia em português, com pouco rótulo.
90. [SimCSE: Simple Contrastive Learning of Sentence Embeddings](https://arxiv.org/abs/2104.08821) — Gao et al., 2021, EMNLP 2021. Contraste com dropout como augmentation produz embeddings de sentenças fortes (76,3% Spearman no não supervisionado com BERT base), útil para pré-ajustar representações de mensagens curtas.
91. [The Power of Scale for Parameter-Efficient Prompt Tuning](https://arxiv.org/abs/2104.08691) — Lester et al., 2021, EMNLP 2021. Prompt tuning só iguala o fine-tuning completo em modelos grandes, o que alerta que num encoder base como mmBERT ele tende a ser menos competitivo que LoRA ou adapters.
92. [BitFit: Simple Parameter-efficient Fine-tuning for Transformer-based Masked Language-models](https://arxiv.org/abs/2106.10199) — Ben-Zaken et al., 2022, ACL 2022 (Short). Ajustar apenas os termos de bias é competitivo com o fine-tuning completo em conjuntos pequenos e médios, servindo de baseline mínimo de custo para a classificação de ironia.
93. [Efficient Few-Shot Learning Without Prompts](https://arxiv.org/abs/2209.11055) — Tunstall et al., 2022, arXiv. O SetFit ajusta um sentence transformer de forma contrastiva e treina uma cabeça de classificação, com resultados comparáveis a PEFT e PET e treino uma ordem de grandeza mais rápido, adequado ao pouco dado de ironia.
94. [Few-Shot Parameter-Efficient Fine-Tuning is Better and Cheaper than In-Context Learning](https://arxiv.org/abs/2205.05638) — Liu et al., 2022, arXiv (NeurIPS 2022). O T-Few com (IA)^3 supera o aprendizado em contexto com custo muito menor e superou o estado da arte do RAFT em 6 pontos percentuais, apoiando PEFT em poucos exemplos.
95. [ZeroGen: Efficient Zero-shot Learning via Dataset Generation](https://arxiv.org/abs/2202.07922) — Ye et al., 2022, EMNLP 2022. Gerar um conjunto sintético com um modelo grande para treinar um classificador pequeno funciona para classificação de texto, base para o uso de professor/geração como fonte de supervisão.
96. [QLoRA: Efficient Finetuning of Quantized LLMs](https://arxiv.org/abs/2305.14314) — Dettmers et al., 2023, NeurIPS 2023 / arXiv. Combinar LoRA com quantização de 4 bits mantém o desempenho do fine-tuning de 16 bits e permite treinar um modelo de 65B em uma GPU de 48GB, relevante ao orçamento de GPU do Colab.
97. [Self-Supervised Learning from Images with a Joint-Embedding Predictive Architecture](https://arxiv.org/abs/2301.08243) — Assran et al., 2023, CVPR 2023 / arXiv. O I-JEPA prediz representações de blocos alvo em espaço latente sem augmentations manuais, fundamento da família JEPA usada como inspiração para texto.
98. [Synthetic Data Generation with Large Language Models for Text Classification: Potential and Limitations](https://arxiv.org/abs/2310.07849) — Li et al., 2023, EMNLP 2023. A subjetividade da tarefa se associa negativamente ao desempenho de modelos treinados com dados sintéticos de LLM, alertando que gerar exemplos de ironia sintéticos é arriscado.
99. [LLM-JEPA: Large Language Models Meet Joint Embedding Predictive Architectures](https://arxiv.org/abs/2509.14252) — Huang et al., 2025, arXiv. Um objetivo JEPA no espaço de embeddings somado à perda padrão melhora o fine-tuning em vários modelos e conjuntos (inclusive RottenTomatoes) e resiste a overfitting, motivando objetivos auxiliares em embedding.

### Avaliação honesta, ruído de rótulo e calibração

100. [Statistical Comparisons of Classifiers over Multiple Data Sets](https://jmlr.org/papers/v7/demsar06a.html) — Demšar, 2006, Journal of Machine Learning Research 7. Recomenda o teste de Wilcoxon para dois classificadores em vários conjuntos (e Friedman para mais de dois), útil se Laya e BERTimbau forem comparados em vários corpora ou fatias.
101. [An Empirical Investigation of Statistical Significance in NLP](https://aclanthology.org/D12-1091/) — Berg-Kirkpatrick, Burkett, Klein, 2012, EMNLP-CoNLL 2012. Fundamenta o uso de bootstrap pareado e a investigação empírica de quando uma diferença de métrica entre dois sistemas é significativa ou acaso.
102. [On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599) — Guo et al., 2017, ICML 2017. Mostra que redes modernas são mal calibradas e que temperature scaling corrige isso de forma simples, relevante porque a confiança do classificador alimenta o fusor do Fraus.
103. [Reporting Score Distributions Makes a Difference: Performance Study of LSTM-networks for Sequence Tagging](https://arxiv.org/abs/1707.09861) — Reimers, Gurevych, 2017, EMNLP 2017. Mostra que a semente aleatória sozinha gera diferenças estatisticamente significativas, então cada modelo deve ser reportado como distribuição de várias execuções, não como um número único.
104. [Annotation Artifacts in Natural Language Inference Data](https://aclanthology.org/N18-2017/) — Gururangan et al., 2018, NAACL 2018. Um classificador só com a hipótese chegou a cerca de 67% no SNLI e 53% no MultiNLI, prova de que artefatos de anotação inflam métricas, análogo ao atalho de latência do Fraus.
105. [Hypothesis Only Baselines in Natural Language Inference](https://aclanthology.org/S18-2023/) — Poliak et al., 2018, *SEM 2018. Propõe o baseline que ignora parte da entrada para detectar vazamento por atalho, equivalente a treinar o fusor sem o texto e conferir se ainda acerta.
106. [The Hitchhiker's Guide to Testing Statistical Significance in Natural Language Processing](https://aclanthology.org/P18-1128/) — Dror et al., 2018, ACL 2018. Oferece um protocolo prático para escolher o teste de significância em PLN, base para decidir como comparar Laya e BERTimbau no mesmo conjunto de teste.
107. [Can You Trust Your Model's Uncertainty? Evaluating Predictive Uncertainty Under Dataset Shift](https://arxiv.org/abs/1906.02530) — Ovadia et al., 2019, NeurIPS 2019. Mostra que a calibração pós-hoc falha sob mudança de distribuição, então calibrar no corpus de treino não garante confiança confiável em atendimento real.
108. [Errudite: Scalable, Reproducible, and Testable Error Analysis](https://aclanthology.org/P19-1073/) — Wu et al., 2019, ACL 2019. Ensina a definir grupos de erro de forma precisa e reproduzível e testar hipóteses sobre a causa, método para analisar onde o Laya e o BERTimbau diferem.
109. [Inherent Disagreements in Human Textual Inferences](https://aclanthology.org/Q19-1043/) — Pavlick, Kwiatkowski, 2019, TACL 7. Demonstra que a discordância humana persiste mesmo com mais anotadores e contexto, ou seja, é ambiguidade real, e propõe avaliar modelos contra a distribuição de julgamentos humanos.
110. [Measuring Calibration in Deep Learning](https://arxiv.org/abs/1904.01685) — Nixon et al., 2019, arXiv (cs.LG). Aponta falhas do ECE e mostra que o ranking de métodos de recalibração depende da medida escolhida, então convém reportar mais de uma métrica de calibração.
111. [Model Cards for Model Reporting](https://arxiv.org/abs/1810.03993) — Mitchell et al., 2019, FAT* 2019 (arXiv 1810.03993). Propõe documentar o modelo com avaliação por subgrupos e uso pretendido, estrutura para o cartão do modelo que já existe no projeto.
112. [Right for the Wrong Reasons: Diagnosing Syntactic Heuristics in Natural Language Inference](https://aclanthology.org/P19-1334/) — McCoy, Pavlick, Linzen, 2019, ACL 2019. Mostra que modelos incluindo BERT acertam por heurísticas frágeis e falham num conjunto de teste construído para quebrá-las, modelo para criar um conjunto adversarial próprio.
113. [Show Your Work: Improved Reporting of Experimental Results](https://aclanthology.org/D19-1224/) — Dodge et al., 2019, EMNLP-IJCNLP 2019. Ensina que a nota de teste isolada não basta e que o orçamento de ajuste de hiperparâmetros deve ser igual e reportado ao comparar o Laya fine-tunado com o BERTimbau.
114. [Slice-based Learning: A Programming Model for Residual Learning in Critical Data Slices](https://arxiv.org/abs/1909.06349) — Chen et al., 2019, NeurIPS 2019. Formaliza fatias críticas de dados em que o desempenho é pior que a média, justificando reportar a métrica por fatia e não só a global.
115. [We Need to Talk about Standard Splits](https://aclanthology.org/P19-1267/) — Gorman, Bedrick, 2019, ACL 2019. Mostra que rankings de sistemas obtidos num único split fixo podem não se reproduzir em splits aleatórios, então a comparação deve repetir a avaliação em vários splits.
116. [Beyond Accuracy: Behavioral Testing of NLP Models with CheckList](https://aclanthology.org/2020.acl-main.442/) — Ribeiro et al., 2020, ACL 2020. Mostra que a acurácia held-out costuma superestimar o desempenho e propõe testes comportamentais por capacidade (negação, emoji, ironia) para complementar a comparação entre modelos.
117. [Calibration of Pre-trained Transformers](https://aclanthology.org/2020.emnlp-main.21/) — Desai, Durrett, 2020, EMNLP 2020. Avalia a calibração de BERT e RoBERTa dentro e fora do domínio e mostra o efeito de temperature scaling e label smoothing, guia para calibrar o Laya e o BERTimbau.
118. [Dataset Cartography: Mapping and Diagnosing Datasets with Training Dynamics](https://aclanthology.org/2020.emnlp-main.746/) — Swayamdipta et al., 2020, EMNLP 2020. Usa confiança e variabilidade durante o treino para separar exemplos fáceis, ambíguos e difíceis, sendo que os difíceis frequentemente são erros de rótulo, ferramenta para limpar o corpus.
119. [Shortcut Learning in Deep Neural Networks](https://arxiv.org/abs/2004.07780) — Geirhos et al., 2020, Nature Machine Intelligence (arXiv 2004.07780). Define atalhos como regras de decisão que funcionam no benchmark e falham em outras condições, e recomenda benchmarks que testem transferência, base conceitual para tratar acurácia alta demais como sintoma.
120. [With Little Power Comes Great Responsibility](https://arxiv.org/abs/2010.06595) — Card et al., 2020, EMNLP 2020. Mostra que experimentos subdimensionados são comuns em PLN, logo é preciso fazer análise de poder para saber se o conjunto de teste detecta a diferença pequena entre os dois modelos.
121. [Accounting for Variance in Machine Learning Benchmarks](https://arxiv.org/abs/2103.03098) — Bouthillier et al., 2021, MLSys 2021. Mostra que amostragem de dados, inicialização e hiperparâmetros afetam muito os resultados, e orienta como estimar a variância antes de declarar um modelo melhor.
122. [Confident Learning: Estimating Uncertainty in Dataset Labels](https://arxiv.org/abs/1911.00068) — Northcutt, Jiang, Chuang, 2021, Journal of Artificial Intelligence Research (arXiv 1911.00068). Apresenta um método agnóstico a modelo para estimar a distribuição conjunta entre rótulo ruidoso e verdadeiro e achar erros de rótulo, aplicável para auditar os corpora de emoção e ironia.
123. [Memorization vs. Generalization: Quantifying Data Leakage in NLP Performance Evaluation](https://aclanthology.org/2021.eacl-main.113/) — Elangovan, He, Verspoor, 2021, EACL 2021. Mostra que sobreposição entre treino e teste infla os resultados, logo é preciso deduplicar e medir a sobreposição antes de comparar os modelos.
124. [Pervasive Label Errors in Test Sets Destabilize Machine Learning Benchmarks](https://arxiv.org/abs/2103.14749) — Northcutt, Athalye, Mueller, 2021, NeurIPS 2021 Datasets and Benchmarks. Encontrou em média pelo menos 3,3% de erros de rótulo nos conjuntos de teste de 10 datasets, o que impõe um teto abaixo de 100% e pode inverter o ranking entre modelos.
125. [Uncovering the Limits of Text-based Emotion Detection](https://arxiv.org/abs/2109.01900) — Alvarez-Gonzalez, Kaltenbrunner, Gómez, 2021, Findings of EMNLP 2021. Mostra que emoções expressas por quem escreve são bem mais difíceis de detectar do que as percebidas por leitores, evidenciando um limite intrínseco da tarefa de emoção em texto.
126. [We Need To Talk About Random Splits](https://aclanthology.org/2021.eacl-main.156/) — Søgaard et al., 2021, EACL 2021. Mostra que splits aleatórios também dão estimativas otimistas e recomenda múltiplos conjuntos de teste independentes, argumento para testar o modelo fora do corpus de treino.
127. [Dealing with Disagreements: Looking Beyond the Majority Vote in Subjective Annotations](https://aclanthology.org/2022.tacl-1.6/) — Davani, Díaz, Prabhakaran, 2022, TACL 10. Mostra que prever o julgamento de cada anotador rende desempenho igual ou melhor que o voto majoritário e uma incerteza correlacionada com a discordância, útil em tarefas subjetivas como emoção e ironia.
128. [Leakage and the Reproducibility Crisis in ML-based Science](https://arxiv.org/abs/2207.07048) — Kapoor, Narayanan, 2022, arXiv (cs.LG). Oferece uma taxonomia de 8 tipos de vazamento (329 artigos afetados) e as fichas de informação do modelo, checklist para auditar o pipeline de treino do Fraus.
129. [The "Problem" of Human Label Variation: On Ground Truth in Data, Modeling and Evaluation](https://aclanthology.org/2022.emnlp-main.731/) — Plank, 2022, EMNLP 2022. Argumenta que a variação humana de rótulos afeta dados, modelagem e avaliação e não é só ruído, então não existe verdade única contra a qual 100% faria sentido.

### Sentimento em português, diálogo e transferência

130. [Sentiment of Emojis](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0144296) — Novak et al., 2015, PLOS ONE. Constrói o Emoji Sentiment Ranking com 751 emojis a partir de 1,6 milhão de tweets em 13 línguas, fonte do léxico de emoji e do viés positivo (média +0,3) a considerar.
131. [Building a Sentiment Corpus of Tweets in Brazilian Portuguese](https://arxiv.org/abs/1712.08917) — Brum e Nunes, 2017, arXiv (LREC 2018). Apresenta o TweetSentBR com 15 mil sentenças em três classes, com baseline de 64,62% de acurácia em três classes, mostrando a dificuldade do sentimento em tweets em português.
132. [Using millions of emoji occurrences to learn any-domain representations for detecting sentiment, emotion and sarcasm](https://arxiv.org/abs/1708.00524) — Felbo et al., 2017, arXiv (EMNLP 2017). DeepMoji usa 1246 milhões de tweets com 64 emojis como supervisão distante e obtém estado da arte em oito benchmarks, justificando emoji como sinal de sentimento, emoção e sarcasmo.
133. [DialogueRNN: An Attentive RNN for Emotion Detection in Conversations](https://arxiv.org/abs/1811.00405) — Majumder et al., 2018, arXiv (AAAI 2019). Modelar o estado de cada interlocutor ao longo da conversa melhora a emoção por fala, argumento para contexto de diálogo além da mensagem isolada.
134. [EmotionLines: An Emotion Corpus of Multi-Party Conversations](https://arxiv.org/abs/1802.08379) — Chen et al., 2018, arXiv (LREC 2018). Anota 29.245 falas de 2.000 conversas com sete emoções (Ekman mais neutro), incluindo mensagens privadas de Messenger, próximo do formato curto e informal de chat.
135. [XNLI: Evaluating Cross-lingual Sentence Representations](https://arxiv.org/abs/1809.05053) — Conneau et al., 2018, arXiv (EMNLP 2018). Benchmark em 15 línguas em que traduzir os dados de teste foi o melhor baseline, referência clássica de comparação translate versus encoder multilíngue.
136. [Cross-Lingual Ability of Multilingual BERT: An Empirical Study](https://arxiv.org/abs/1912.07840) — K et al., 2019, arXiv (ICLR 2020). Mostra que sobreposição lexical pesa pouco e a profundidade da rede importa para a transferência, orientando o que esperar do zero-shot para o português.
137. [Emotion Recognition in Conversation: Research Challenges, Datasets, and Recent Advances](https://arxiv.org/abs/1905.02947) — Poria et al., 2019, arXiv (IEEE Access). Survey de ERC que organiza desafios, datasets e métodos, e serve de mapa para posicionar a classificação por mensagem frente ao estado da arte contextual.
138. [Are All Languages Created Equal in Multilingual BERT?](https://arxiv.org/abs/2005.09093) — Wu e Dredze, 2020, arXiv (RepL4NLP 2020). O mBERT é bom em línguas de muitos recursos e fraco nas de poucos, e o encoder monolíngue nem sempre ganha, relevante para comparar o encoder multilíngue ao BERTimbau.
139. [COSMIC: COmmonSense knowledge for eMotion Identification in Conversations](https://arxiv.org/abs/2010.02795) — Ghosal et al., 2020, arXiv (Findings of EMNLP 2020). Usa conhecimento de senso comum para distinguir emoções parecidas e detectar mudanças emocionais, apontando limite de modelos que ignoram contexto em quatro datasets de ERC.
140. [MAD-X: An Adapter-Based Framework for Multi-Task Cross-Lingual Transfer](https://arxiv.org/abs/2005.00052) — Pfeiffer et al., 2020, arXiv (EMNLP 2020). Adapters modulares de língua e tarefa melhoram a transferência cross-lingual com menos parâmetros, opção para adaptar o encoder ao português sem retreinar tudo.
141. [Translation Artifacts in Cross-lingual Transfer Learning](https://arxiv.org/abs/2004.04721) — Artetxe et al., 2020, arXiv (EMNLP 2020). Mostra que artefatos de tradução alteram o desempenho (ganhos de 4,3 pontos no translate-test e 2,8 no zero-shot do XNLI), alertando para vieses de corpora traduzidos por máquina.
142. [XTREME: A Massively Multilingual Multi-task Benchmark for Evaluating Cross-lingual Generalization](https://arxiv.org/abs/2003.11080) — Hu et al., 2020, arXiv (ICML 2020). Benchmark de 40 línguas e 9 tarefas que evidencia lacuna sensível entre transferência cross-lingual e desempenho em inglês, base para medir o custo de não treinar em português.
143. [Simulating User Satisfaction for the Evaluation of Task-oriented Dialogue Systems](https://arxiv.org/abs/2105.03748) — Sun et al., 2021, arXiv (SIGIR 2021). Cria o dataset USS com 6.800 diálogos rotulados em 5 níveis e mostra que modelos BERT generalizam melhor entre domínios, apoiando estimar satisfação a partir do texto.
144. [XLM-T: Multilingual Language Models in Twitter for Sentiment Analysis and Beyond](https://arxiv.org/abs/2104.12250) — Barbieri et al., 2021, arXiv (LREC 2022). Modelo XLM-R adaptado a milhões de tweets em mais de trinta línguas, com datasets unificados de sentimento em oito línguas, referência para texto curto e informal multilíngue.
145. [Understanding User Satisfaction with Task-oriented Dialogue Systems](https://arxiv.org/abs/2204.12195) — Siro et al., 2022, arXiv (SIGIR 2022). Mostra que a satisfação varia entre anotadores e dimensões (relevância, compreensão, eficiência), o que limita tratar a nota de satisfação como rótulo único e limpo.
146. [Revisiting Machine Translation for Cross-lingual Classification](https://arxiv.org/abs/2305.14240) — Artetxe et al., 2023, arXiv. Compara translate-test com modelos multilíngues e conclui que a melhor abordagem depende da tarefa, orientando a escolha entre dado traduzido e zero-shot.
147. [Sabiá: Portuguese Large Language Models](https://arxiv.org/abs/2304.07880) — Pires et al., 2023, arXiv. Mostra que pré-treino monolíngue em português melhora modelos já multilíngues em 14 datasets do benchmark Poeta, argumento a favor de modelos específicos do português.
