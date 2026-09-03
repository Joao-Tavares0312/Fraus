# Bibliografia — detecção de ironia/sarcasmo (pesquisa para incongruência)

Anexo de `docs/superpowers/specs/2026-09-03-incongruencia-ironia-design.md`.
69 fontes levantadas por pesquisa dirigida, priorizando (a) português/domínio
de atendimento, (b) features linguísticas exploráveis sem LLM, (c) ensemble
e abordagens híbridas, (d) datasets e surveys de referência.

## Sumário executivo

Modelos neurais puros (BERT/BERTimbau) capturam fluência e léxico, mas erram
sistematicamente quando a ironia depende de *incongruência* — polaridade que
se contradiz, exagero implausível, contraste com o contexto. Os ganhos mais
citados e mais baratos sem LLM:

1. **Incongruência lexical de polaridade** (Riloff 2013; Joshi 2015) — ganho
   mais replicado (+8 a +20 F1), o mais barato de calcular (SentiLex-PT02 já
   em uso no projeto).
2. **Marcadores tipográficos/morfossintáticos** (Burgers 2012; Ptáček 2014;
   Bouazizi & Ohtsuki): pontuação exagerada, CAPS LOCK, alongamento, aspas
   irônicas — o Fraus já calcula boa parte em `estilo.py`; o ganho é cruzar
   isso com a saída do BERTimbau de ironia, não recalcular do zero.
3. **Marcadores discursivos de contraste** ("mas", "só que") como guinada de
   polaridade intra-mensagem.
4. **Ensemble**: a arquitetura do Fraus (`Fusor` = LogisticRegression sobre
   features heterogêneas) já é o padrão dominante da literatura de ensemble
   para sarcasmo (stacking com meta-classificador logístico). Não é preciso
   trocar de arquitetura — só alimentar o vetor com as features novas.
5. Em domínio de review/atendimento (não Twitter), contraste positivo/negativo
   e hipérbole pesam mais que hashtag/marcador de plataforma — bom para o
   Fraus, que não tem hashtag `#sarcasmo` em chat.

## (i) Irony/sarcasm em português / domínio de atendimento

1. Overview of the IDPT Task on Irony Detection in Portuguese, IberLEF 2021 — https://rua.ua.es/server/api/core/bitstreams/1eb53c67-34ca-471c-955c-e04ad4f3d799/content — corpus/task de origem do modelo atual do Fraus; Bacc 0,52 em tweets vs 0,92 em notícias, evidência de que domínio de tweet é muito mais difícil.
2. PiLN IDPT 2021: Irony Detection in Portuguese Texts with Superficial Features and Embeddings — https://ceur-ws.org/Vol-2943/idpt_paper4.pdf — vencedor no subset de tweets combinou features superficiais (pontuação, POS) com embeddings.
3. Marten & Freitas — The Construction of a Corpus for Detecting Irony and Sarcasm in Portuguese — https://www.semanticscholar.org/paper/0091cd24402ca04b25cbf0931c8d3bbccd406b5b
4. Detecção de Ironia e Sarcasmo em Língua Portuguesa: uma abordagem utilizando Deep Learning — https://www.researchgate.net/publication/323369673
5. BERTimbau: Pretrained BERT Models for Brazilian Portuguese (Souza, Nogueira, Lotufo) — https://www.researchgate.net/publication/345395208
6. BERTimbau in Action: Sentiment, Aspect Extraction, Hate Speech, Irony Detection (FLAIRS) — https://journals.flvc.org/FLAIRS/article/view/133186
7. BERT for Sentiment Analysis: Pre-trained and Fine-Tuned Alternatives (arXiv 2201.03382) — https://arxiv.org/pdf/2201.03382
8. Brazilian Portuguese Hate Speech Classification using BERTimbau — https://www.researchgate.net/publication/360378064
9. SentiLex-PT: Principais características e potencialidades — https://www.researchgate.net/publication/344644990 — léxico já usado em `fraus/sinais/lexico.py`.
10. SentiLex-PT02 — lexiconPT (CRAN) — https://rdrr.io/cran/lexiconPT/man/sentiLex_lem_PT02.html
11. Léxico da afetividade para o processamento computacional do português (SciELO) — http://www.scielo.br/j/rbla/a/jxSZLGKJQVZgxRDVkpR9Dxn
12. UFPel — Detecção Automática de Sarcasmo e Ironia em Múltiplos Idiomas — https://institucional.ufpel.edu.br/projetos/id/u3345
13. Padrões linguísticos para detecção de ironia em múltiplos idiomas — https://www.researchgate.net/publication/348305346
14. A detecção de implicaturas conversacionais da ironia (tese USP, Martins) — https://teses.usp.br/teses/disponiveis/45/45134/tde-20230727-113522/publico/MartinsRayssaKullian.pdf
15. Portuguese Lexicon of Discourse Markers (CLUL) — https://www.clul.ulisboa.pt/en/recurso/portuguese-lexicon-discourse-markers — base para marcadores de contraste (F3).
16. Reyes & Rosso — Detecting irony in customer reviews — https://sites.socsci.uci.edu/~lpearl/courses/readings/ReyesRosso2012_IronyDetection.pdf
17. Mining subjective knowledge from customer reviews: A specific case of irony detection — https://www.researchgate.net/publication/262215513
18. Making objective decisions from subjective data: Detecting irony in customer reviews (Decision Support Systems) — https://www.sciencedirect.com/science/article/abs/pii/S0167923612001388
19. kbuschme/irony-detection (Buschmeier, Cimiano, Klinger) — https://github.com/kbuschme/irony-detection
20. Filatova — Irony and Sarcasm: Corpus Generation and Analysis Using Crowdsourcing (LREC 2012) — https://aclanthology.org/L12-1386/
21. Davidov, Tsur & Rappoport — SASI (ICWSM/CoNLL 2010) — https://aclanthology.org/W10-2914/

## (ii) Features linguísticas exploráveis

22. Riloff et al. — Sarcasm as Contrast between a Positive Sentiment and Negative Situation (EMNLP 2013) — https://aclanthology.org/D13-1066/ — base de F1.
23. González-Ibáñez, Muresan & Wacholder — Identifying Sarcasm in Twitter: A Closer Look (ACL 2011) — https://aclanthology.org/P11-2102/
24. Joshi, Sharma & Bhattacharyya — Harnessing Context Incongruity for Sarcasm Detection (ACL 2015) — https://aclanthology.org/P15-2124/ — referência principal de F1 (+8% F1).
25. Joshi et al. — Harnessing Cognitive Features for Sarcasm Detection (ACL 2016) — https://www.researchgate.net/publication/312594529
26. Burgers, van Mulken & Schellens — Verbal Irony (2012) — https://journals.sagepub.com/doi/10.1177/0261927X12446596 — taxonomia de marcadores usada em F4/F5.
27. Interpreting Verbal Irony: Linguistic Strategies and Semantic Incongruity — https://arxiv.org/pdf/1911.00891
28. Ptáček, Habernal & Hong — Sarcasm Detection on Czech and English Twitter (COLING 2014) — https://aclanthology.org/C14-1022.pdf
29. Bouazizi & Ohtsuki — pattern-based sarcasm detection — https://www.researchgate.net/publication/306524590
30. Bharti et al. — regras de sarcasmo baseadas em interjeição+intensificador — (survey acima)
31. Troiano, Strapparava et al. — A Computational Exploration of Exaggeration / HYPO dataset (EMNLP 2018) — https://aclanthology.org/D18-1367.pdf — base de F4.
32. Kralj Novak, Smailović et al. — Sentiment of Emojis (PLOS ONE 2015) — https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0144296 — léxico já em `fraus/sinais/emoji.py`, base de F2.
33. "With 1 follower I must be AWESOME :P" — role of irony markers (Van Hee et al.) — https://arxiv.org/pdf/1804.05253
34. Irony Detection in Hebrew Documents — aspas como marcador de ironia — https://aclanthology.org/2025.nlp4dh-1.9.pdf — base de F5.
35. Scare quotes (Wikipedia) — https://en.wikipedia.org/wiki/Scare_quotes
36. Rajadesingan, Zafarani & Liu — SCUBA (WSDM 2015) — https://sites.socsci.uci.edu/~lpearl/courses/readings/RajadesinganEtAl2015_SarcasmDetection.pdf
37. Sperber & Wilson — echoic mention theory — https://www.researchgate.net/publication/223333203
38. Utsumi — Implicit Display Theory of Verbal Irony — http://www.utm.inf.uec.ac.jp/~utsumi/paper/IWCH-1996-Utsumi.pdf

## (iii) Ensemble / hybrid approaches

39. An Efficient Sarcasm Detection using Linguistic Features and Ensemble ML (Procedia CS 2024) — https://www.sciencedirect.com/science/article/pii/S1877050924007762
40. Sarcasm Detection over Social Media Platforms Using Hybrid Ensemble Model with Fuzzy Logic (MDPI Electronics 2023) — https://www.mdpi.com/2079-9292/12/4/937
41. Identifying sarcasm using heterogeneous word embeddings (Soft Computing 2023) — https://link.springer.com/article/10.1007/s00500-023-08368-6
42. Multi-Rule Based Ensemble Feature Selection Model for Sarcasm Type Detection (PMC) — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7199606/
43. Ensemble Classification Approach for Sarcasm Detection (2021) — https://pubmed.ncbi.nlm.nih.gov/34853618/ — mesmo princípio do `Fusor` (meta-classificador logístico).
44. Handling Class Imbalanced Data in Sarcasm Detection with Ensemble Oversampling (2025) — https://doi.org/10.1080/08839514.2025.2468534
45. The Sarcasm Detection with the Method of Logistic Regression — https://www.academia.edu/41679417
46. Sarcasm detection using deep learning and ensemble learning (Multimedia Tools and Applications 2022) — https://link.springer.com/article/10.1007/s11042-022-12930-z
47. CascadeNS: Confidence-Cascaded Neurosymbolic Model for Sarcasm Detection — https://arxiv.org/html/2304.01424 — alternativa (regra como filtro pós-modelo) descartada, ver design.
48. MIAN: Multi-head Incongruity Aware Attention Network — https://www.sciencedirect.com/science/article/abs/pii/S0957417424025697
49. Tay et al. — SIARN/MIARN — https://arxiv.org/pdf/2101.05875
50. Sarcasm Detection Using Deep Convolutional Neural Networks: A Modular Deep Learning Framework — https://arxiv.org/pdf/2510.10729

## (iv) Datasets / recursos / shared tasks

51. SemEval-2018 Task 3: Irony Detection in English Tweets — https://aclanthology.org/S18-1005/
52. Overview of the EVALITA 2018 Task on Irony Detection in Italian Tweets (IronITA) — https://books.openedition.org/aaccademia/4470
53. TWITTIRÒ: an Italian Twitter Corpus with a Multi-layered Annotation for Irony — https://journals.openedition.org/ijcol/502
54. Overview of the Task on Irony Detection in Spanish Variants (IroSvA 2019) — https://ceur-ws.org/Vol-2421/IroSvA_paper_6.pdf
55. iSarcasm: A Dataset of Intended Sarcasm (Oprea & Magdy, ACL 2020) — https://aclanthology.org/2020.acl-main.118/ — alerta sobre corpus rotulado por marcador de plataforma (aplica-se ao IDPT).
56. Chinese Irony Corpus Construction and Ironic Structure (COLING 2014) — https://aclanthology.org/C14-1120.pdf
57. A Report on the 2020 Sarcasm Detection Shared Task (FigLang) — https://arxiv.org/pdf/2005.05814
58. Self-Deprecating Sarcasm Detection: Amalgamation of Rule-Based and ML — https://www.researchgate.net/publication/330394215
59. SARC — Self-Annotated Reddit Corpus (referenciado nos surveys acima)

## Surveys gerais

60. Joshi, Bhattacharyya & Carman — Automatic Sarcasm Detection: A Survey (ACM Computing Surveys 2017) — https://dl.acm.org/doi/10.1145/3124420
61. Was that Sarcasm? A Literature Survey on Sarcasm Detection — https://arxiv.org/pdf/2412.00425
62. A Survey on Automated Sarcasm Detection on Twitter — https://arxiv.org/pdf/2202.02516
63. Sarcasm Detection: A Comparative Study — https://arxiv.org/pdf/2107.02276
64. Computational Sarcasm Analysis on Social Media: A Systematic Review — https://arxiv.org/pdf/2209.06170
65. Sarcasm identification in textual data: systematic review, research challenges (AI Review 2020) — https://link.springer.com/article/10.1007/s10462-019-09791-8
66. A Survey in Automatic Irony Processing: Linguistic, Cognitive, and Multi-X Perspectives — https://arxiv.org/pdf/2209.04712
67. Sarcasm Detection Using Contextual Incongruity (Springer, cap. de livro) — https://link.springer.com/chapter/10.1007/978-981-10-8396-9_4
68. Sarcasm Analysis using Conversation Context — https://arxiv.org/pdf/1808.07531 — ganho ao usar o turno anterior (mensagem do bot); estrutura `Conversa`/`Mensagem` do Fraus já tem esse contexto.
69. The Role of Conversation Context for Sarcasm Detection in Online Interactions — https://arxiv.org/pdf/1707.06226
