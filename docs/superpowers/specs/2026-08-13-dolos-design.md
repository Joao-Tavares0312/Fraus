# Dolos — Análise de Satisfação em Atendimentos por Chatbot

**Data:** 2026-08-13
**Status:** spec aprovada, aguardando plano de implementação
**Autor:** João Pedro Tavares Vicente

---

## 1. Contexto e objetivo

Trabalho acadêmico. Desenvolver e implementar uma ferramenta baseada em Inteligência
Artificial capaz de analisar atendimentos realizados por chatbot, identificando o nível
de satisfação dos clientes por meio de mensagens, palavras-chave, emojis e tempo de
resposta. A ferramenta gera indicadores e relatórios que permitem avaliar a qualidade e
a eficiência do atendimento e identificar oportunidades de melhoria.

**Restrição de projeto:** o motor de análise não pode depender de uma LLM em runtime.
A classificação roda em CPU, com modelo próprio treinado. Isso é requisito, não
otimização — é o que torna o trabalho um projeto de IA e não uma integração de API.

### 1.1 Por que "Dolos"

Dolos é o daemon grego do ardil e do engano, contraparte masculina de Ápate. O nome
descreve o problema real: **o cliente mente**. Ele digita "ok, obrigado 🙂" e sai
insatisfeito.

Isso não é retórica — é o achado central da literatura:

- Modelos baseados apenas em características genéricas da conversa (número de mensagens
  do usuário, intents previstos) explicam **cerca de 10% da variância** da satisfação
  declarada. A conversa em si carrega o resto do sinal.
  ([Springer, *Conversation logs as a source of insight*, 2025](https://link.springer.com/article/10.1007/s41233-025-00071-8))
- Existe inconsistência sistemática entre a nota que o usuário atribui e o texto que ele
  escreve, a ponto de haver linha de pesquisa dedicada a filtrar essas contradições
  antes de treinar.
  ([PMC11793979](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11793979/))

Dolos lê o que foi dito de verdade, não a nota que o cliente teve preguiça de dar.

---

## 2. Escopo do épico

Ferramenta que ingere transcrições de atendimento por chatbot e produz, sem LLM em
runtime, um score de satisfação por atendimento e indicadores agregados, expostos numa
dashboard com relatórios exportáveis.

Cinco entregáveis, nesta ordem de dependência:

1. **Ingestão** — adapter plugável de fonte de conversa.
2. **Engine de análise** — três sinais (texto, emoji, tempo) fundidos num score.
3. **Treinamento** — notebook Colab, fine-tune de BERTimbau, artefato versionado.
4. **API** — FastAPI servindo o modelo e as agregações.
5. **Dashboard** — resumo do atendimento, nota e NPS.

### 2.1 Fora de escopo (explícito)

- RAG / base vetorial no núcleo do produto (justificativa na seção 4.4).
- Integração implementada com WhatsApp ou Discord — apenas especificada (seção 3.2).
- UI de administração de campanhas.
- Coleta de nota declarada pelo cliente. O NPS aqui é **inferido** (seção 7.2).

---

## 3. Ingestão

### 3.1 Modelo de dados canônico

Toda fonte é normalizada para uma estrutura única, e o resto do sistema só conhece essa
estrutura:

```
Conversa
  id: str
  canal: str                  # "csv" | "discord" | "whatsapp" | "simulado"
  iniciada_em: datetime
  encerrada_em: datetime | None
  escalou_para_humano: bool
  mensagens: list[Mensagem]

Mensagem
  autor: "cliente" | "bot" | "humano"
  texto: str
  enviada_em: datetime
```

Latência não é armazenada: é **derivada** dos timestamps na engine. Guardar valor
derivado é convite a inconsistência.

### 3.2 Drivers

| Driver | Estado | Nota |
|---|---|---|
| `csv` / `json` | **implementado** | fonte primária da entrega |
| `simulado` | **implementado** | gerador de conversas sintéticas (seção 5.2) |
| `discord` | especificado | bot com `MESSAGE_CONTENT` intent; leitura de histórico de canal é direta |
| `whatsapp` | especificado | Cloud API exige verificação de negócio (2–7 dias úteis) e webhooks obrigatórios; ligar direto na Meta é projeto de meses. Só faz sentido via provedor (BSP). ([Chatarmin, 2026](https://chatarmin.com/en/blog/whats-app-business-api-integration)) |
| plataforma da empresa | especificado | se houver acesso ao repo/API, vira mais um driver |

Consequência prática registrada: **se surgir uma empresa parceira, Discord ou uma
plataforma própria custam ordens de magnitude menos esforço que WhatsApp.** O escopo do
trabalho não deve depender de WhatsApp.

---

## 4. Engine de análise

### 4.1 Arquitetura

```
Conversa
   ├── sinal TEXTO  → BERTimbau fine-tuned → P(negativo, neutro, positivo) por mensagem do cliente
   ├── sinal EMOJI  → Emoji Sentiment Ranking → (score, %pos, %neg, posição relativa)
   └── sinal TEMPO  → features de latência + escalação + abandono
                                    │
                                    ▼
                        FUSOR (LogReg / Gradient Boosting)
                                    │
                                    ▼
                  score de satisfação 0–100 + categoria + atribuição por sentença
```

Cada sinal é um módulo independente com entrada e saída declaradas, testável sozinho.
O fusor é o único ponto que conhece os três.

### 4.2 Sinal de texto — BERTimbau

BERTimbau é o encoder correto para PT-BR: fine-tuning permitiu que modelos BERT
superassem as alternativas, e o BERTimbau supera as variantes multilíngues em
classificação de sentimento em português.
([Souza et al., arXiv:2201.03382](https://arxiv.org/pdf/2201.03382);
[PROPOR 2026, análise estruturada de sentimento com BERTimbau](https://aclanthology.org/2026.propor-1.92/);
[BERTaú — BERT do Itaú para atendimento digital](https://research.latinxinai.org/papers/neurips/2023/pdf/Vinicius_Carida.pdf))

Saída por mensagem do cliente, não por conversa. A agregação para o nível de conversa é
responsabilidade do fusor — é isso que permite a atribuição por sentença na dashboard.

### 4.3 Sinal de emoji

Emojis **não** são removidos no pré-processamento. O Emoji Sentiment Ranking fornece
polaridade para 751 emojis, derivada de ~70.000 tweets anotados por 83 anotadores em 13
idiomas europeus.
([Kralj Novak et al., *Sentiment of Emojis*, PLOS ONE 2015](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0144296);
[dataset](https://research.ceu.edu/en/datasets/emoji-sentiment-ranking-10/))

Incorporar features de emoji melhora acurácia e F1 em classificação de sentimento
([Emo-SL, IEEE Access](https://ieeexplore.ieee.org/document/10483059/);
[Nature Scientific Reports 2025](https://www.nature.com/articles/s41598-025-92286-0);
[Towards Data Science — *stop cleaning them out*](https://towardsdatascience.com/emojis-aid-social-media-sentiment-analysis-stop-cleaning-them-out-bb32a1e5fc8e/)).

Achado que vira feature: **a polaridade do emoji aumenta com a distância — emojis
tendem a aparecer no fim da mensagem, e quanto mais ao fim, mais forte a polaridade.**
Portanto a posição relativa do emoji na mensagem entra como feature, não só a contagem.

Viés conhecido a documentar no relatório: a maioria dos emojis do lexicon é positiva,
especialmente os mais populares. O fusor precisa ser calibrado contra isso.

### 4.4 Sinal de tempo

Latência tem efeito medido e **não-linear** sobre satisfação:

- CSAT máximo (~84,7%) quando a resposta chega entre 5 e 10 segundos.
- Cada minuto adicional de espera derruba o CSAT em 2–3 pontos.
- 57% dos clientes abandonam a sessão quando a espera passa de 3 minutos.
  ([benchmarks de live chat 2026](https://www.gethelpable.com/blog/live-chat-response-time-benchmarks);
  [estatísticas de tempo de resposta](https://livechatai.com/blog/customer-support-response-time-statistics))

E o efeito é **moderado por contexto**: latência maior acompanhada de indicador de
digitação dói menos, porque aumenta a percepção de presença social; latência moderada
combinada com suporte emocional chega a *melhorar* a avaliação do chatbot.
([*From Seconds to Sentiments*, International Journal of Human–Computer Interaction, 2025](https://www.tandfonline.com/doi/full/10.1080/10447318.2025.2508915))

Por isso latência entra como **feature do fusor**, aprendida junto com o texto — não
como penalidade linear arbitrada por nós. Features: mediana e p90 da latência do bot,
latência da primeira resposta, duração total, número de turnos, houve escalação, houve
abandono.

### 4.5 Decisão: fine-tuning, não RAG (nem OKF)

A task do trabalho pergunta "OKF ou RAG". A resposta com fonte é: **nenhum dos dois no
núcleo.**

A regra de decisão de 2026 é explícita: *"if your task is classification, fine-tuning
almost always wins on accuracy and latency"*, e para tarefas estreitas de alto volume
(classificação, extração estruturada) o fine-tune de um modelo pequeno tem ROI melhor
que chamar um modelo frontier.
([Winder.ai](https://winder.ai/rag-vs-fine-tuning-2026-decision-framework/);
[Zartis](https://www.zartis.com/rag-vs-fine-tuning-a-2026-decision-framework/);
[BEON.tech](https://beon.tech/blog/rag-vs-fine-tuning-vs-agents/))

RAG resolve **conhecimento factual atualizado**, não classificação. Não há pergunta
factual a responder aqui — há um rótulo a inferir. Adicionar ChromaDB ou pgvector ao
núcleo seria infraestrutura sem função.

As contraindicações do fine-tune também foram checadas e não se aplicam: as categorias
não mudam mês a mês (satisfação é estável), e há muito mais que 50 exemplos por classe.

**Extensão futura documentada (não implementada):** um índice vetorial sobre a base de
conhecimento da empresa permitiria medir *aderência/resolução* — "o bot respondeu o que
foi perguntado?" — que é uma dimensão diferente de *satisfação*. Isso é o híbrido que a
literatura recomenda como arquitetura de produção madura. Fica no roadmap.

---

## 5. Dados e treinamento

### 5.1 Datasets públicos

| Dataset | Volume | Por que |
|---|---|---|
| [B2W-Reviews01](https://github.com/americanas-tech/b2w-reviews01) | 130k+ reviews PT-BR | nota 1–5 **e label "recomenda a um amigo"** — proxy direto de NPS; inclui perfil do avaliador |
| [TweetSentBR](https://paperswithcode.com/dataset/tweetsentbr) | 15k sentenças | 3 classes, anotação manual por 7 anotadores; registro **conversacional**, com emoji e gíria |
| [Olist](https://www.kaggle.com/datasets/fredericods/ptbr-sentiment-analysis-datasets) | ~100k pedidos | reviews de e-commerce com metadados de pedido |

Compilação consolidada em [Brazilian Portuguese Sentiment Analysis Datasets (Kaggle)](https://www.kaggle.com/datasets/fredericods/ptbr-sentiment-analysis-datasets)
e [Portuguese-NLP (github)](https://github.com/ajdavidl/Portuguese-NLP).

O `label recomenda a um amigo` do B2W é a **âncora de treino do NPS inferido**. Sem ele,
o NPS da dashboard seria métrica inventada.

### 5.2 Simulador de conversas

Nenhum dataset público de review tem **timestamps de diálogo** — logo, nenhum deles
treina o sinal de tempo. O simulador costura sentenças rotuladas desses corpora em
diálogos cliente↔bot sintéticos, com latências amostradas de distribuições realistas
calibradas pelos benchmarks da seção 4.4, e injeta eventos de escalação e abandono.

Isso é declarado abertamente como limitação metodológica no relatório: o sinal de tempo
é treinado em dados sintéticos calibrados por literatura, não observados.

### 5.3 Treinamento

Google Colab, GPU gratuita, checkpoint no Google Drive — mesmo padrão já usado no
projeto Neuro-ai. Notebook versionado no repo.

Referências práticas:
[fine-tune de BERT PT-BR com Hugging Face](https://carloszan.medium.com/fine-tuning-em-um-modelo-bert-para-classifica%C3%A7%C3%A3o-de-dados-financeiros-com-hugging-face-13a80b421375) ·
[Chris McCormick — BERT Fine-Tuning Tutorial](https://mccormickml.com/2019/07/22/BERT-fine-tuning/) ·
[Pierre Guillou — treinando modelos PT-BR no Colab](https://medium.com/@pierre_guillou/estado-da-arte-do-nlp-com-as-bibliotecas-transformers-de-hugging-face-e-fastai-v2-992dd1fd3a8) ·
[vídeo: Fine-Tuning BERT using Hugging Face Transformers](https://www.youtube.com/watch?v=bHR88Ug7K8Q) ·
[vídeo: Text Classification using BERT no Google Colab](https://www.youtube.com/watch?v=E9nGPt4iMM8)

### 5.4 Decisão: treinar vs. usar base de conhecimento pronta

Task do trabalho. **Treinar**, por três razões defensáveis:

1. **Domínio.** Modelo genérico não conhece o vocabulário do atendimento (nomes de
   produto, jargão de suporte, formas locais de reclamar).
2. **Custo e latência.** Chamar um modelo frontier por conversa não escala em volume de
   atendimento; substituí-lo por um modelo pequeno fine-tuned é exatamente o caso de ROI
   descrito na literatura de 2026.
3. **Viabilidade.** Para classificação e extração, **200–500 exemplos curados costumam
   bastar** — qualidade vence quantidade. O custo de treinar é baixo.
   ([Sivaro, *LLM Fine Tuning for Text Classification: The 2026 Playbook*](https://sivaro.in/articles/llm-fine-tuning-for-text-classification-the-2026-playbook/))

E o requisito do projeto proíbe LLM em runtime, o que já elimina a alternativa.

---

## 6. Stack e dependências

| Camada | Escolha | Justificativa |
|---|---|---|
| Linguagem | Python 3.11 | ecossistema de NLP |
| Modelo | `transformers` + `torch` | CPU em runtime, GPU só no Colab |
| Fusor | `scikit-learn` | LogReg/GBM — interpretável, exigência do relatório |
| Emoji | `emoji` + Emoji Sentiment Ranking (CSV local) | lexicon estático, sem dependência de rede |
| API | **FastAPI** | padrão para servir modelo; async nativo |
| Persistência | **SQLite** → Postgres/Supabase se multiusuário | sem vetorial; ver 4.5 |
| Dashboard | **Next.js + Recharts** | ver abaixo |

**Streamlit vs. Next.js:** Streamlit é excelente para prototipagem rápida, mas para uma
aplicação multiusuário, publicamente acessível e apresentável, Next.js + FastAPI é a
arquitetura correta de longo prazo — o backend Python não muda, é exposto por REST.
([série FastAPI + Streamlit + Next.js](https://jaehyeon.me/series/realtime-dashboard-with-fastapi-streamlit-and-next.js/);
[Streamlit alternatives 2026](https://www.innonexa.com/2026/07/02/streamlit-alternatives-python-ai-agent-apps-2026/))

Como este é um trabalho a ser **apresentado**, a dashboard é entregável de primeira
classe, não protótipo. Next.js.

---

## 7. Dashboard e indicadores

### 7.1 Princípio de design vindo da pesquisa

Duas orientações consistentes na literatura de analytics de chatbot:

1. **Começar com 3–4 KPIs** e acertá-los antes de expandir; containment rate é a métrica
   isolada mais importante.
2. **Otimizar um KPI isolado quebra outro** — empurrar taxa de deflexão tornando difícil
   falar com um humano derruba o CSAT. A suíte de analytics precisa mostrar como as
   métricas se influenciam.
   ([Agentkit](https://agentkit.ai/blog/chatbot-kpis-metrics);
   [Netguru](https://www.netguru.com/blog/chatbot-kpis);
   [Quickchat](https://quickchat.ai/post/chatbot-analytics))

Consequência de design: os eixos em tensão aparecem **sobrepostos no mesmo gráfico**, não
como cards isolados.

### 7.2 Estrutura

**Topo — 4 indicadores:**

- **NPS inferido** — `%promotores − %detratores`, faixas **0–6 detrator / 7–8 neutro /
  9–10 promotor**, escala −100 a +100. Categoria sempre derivada no servidor, nunca
  recebida do cliente (padrão já estabelecido no projeto NPS da Wascer).
- **CSAT %** — baseline saudável de referência: 75–85% para um chatbot bem ajustado.
- **Containment rate** — conversas resolvidas sem intervenção humana.
- **Tempo mediano de resposta** — com as faixas de referência da seção 4.4 marcadas.

**Meio — gráficos:**

- Série temporal de NPS × latência mediana **sobrepostas** (o trade-off visível).
- Distribuição dos scores de satisfação.
- Top palavras-chave e top emojis, separados por classe (promotor / neutro / detrator).

**Base — tabela de atendimentos.** Clique abre o **resumo do atendimento**: transcrição
completa, score, categoria, e **quais trechos puxaram a nota** (atribuição por sentença,
possível porque o sinal de texto é calculado por mensagem — seção 4.2).

Essa atribuição é o que transforma "nota ruim" em "oportunidade de melhoria", que é o
objetivo declarado do trabalho.

**Relatório:** export do período em PDF e CSV.

### 7.3 Honestidade metodológica

NPS canônico é uma pergunta feita ao cliente. Aqui ele é **inferido a partir do texto**.
A dashboard rotula explicitamente como estimativa, e o label "recomenda a um amigo" do
B2W-Reviews01 é a âncora que dá lastro ao número. Apresentar NPS inferido como NPS
declarado seria falso.

---

## 8. Repositórios

- **`Dolos`** (novo, privado) — projeto inteiro: engine, API, dashboard, notebooks Colab.
- **`Neuro-ai`**, branch nova — extrai o detector de humor existente num pacote
  reutilizável que o Dolos consome. Escopo limitado a isso; nada de feature nova na Neuro.

---

## 9. Tratamento de erro

- **Modelo ausente ou corrompido no boot da API** → falha alta e explícita. Servir
  predição sem modelo carregado é pior que estar fora do ar.
- **Conversa malformada na ingestão** → rejeitada individualmente com motivo registrado;
  o lote continua. Um CSV ruim não pode derrubar a importação inteira.
- **Conversa sem mensagem do cliente** → ingerida, mas sem score; aparece na dashboard
  como "sem sinal", não como nota 0. Ausência de dado não é insatisfação.
- **Erro de agregação na dashboard** → o indicador afetado mostra estado de falha; os
  demais continuam renderizando.

---

## 10. Testes

- **Sinal de emoji** — unitário contra o lexicon: polaridade conhecida, posição, texto
  sem emoji.
- **Sinal de tempo** — derivação de latência a partir de timestamps, incluindo bordas
  (turno único, conversa aberta, timestamps fora de ordem).
- **Fusor** — treina em fixture pequena e determinística; verifica que score sobe com
  texto positivo e cai com latência alta.
- **Ingestão** — round-trip CSV → modelo canônico; linhas malformadas isoladas.
- **Agregação** — NPS calculado à mão numa fixture de votos conhecidos confere com a
  função (as fronteiras 6/7 e 8/9 são o alvo).
- **API** — contrato dos endpoints; comportamento com modelo ausente.

---

## 11. Mapa das tasks da disciplina

| Task | Onde está resolvida |
|---|---|
| Definir escopo do projeto (épico) | Seção 2 |
| Definir nome do projeto | Seção 0/1.1 — **Dolos** |
| Pesquisar dependências e linguagem | Seção 6 |
| OKF ou RAG — o que é viável | Seção 4.5 — nenhum dos dois no núcleo; fine-tune |
| Dashboard para verificar resultados, API | Seções 6 e 7 |
| Como implementar num chat | Seção 3.2 |
| Definir empresa | Seção 3.2 — fonte plugável; entrega não depende de empresa |
| Treinar IA vs. base de conhecimento | Seção 5.4 — treinar, com três razões |

---

## 12. Referências

**Modelos e NLP em português**
- Souza, Nogueira, Lotufo. *BERT for Sentiment Analysis: Pre-trained and Fine-Tuned Alternatives.* [arXiv:2201.03382](https://arxiv.org/pdf/2201.03382) · [ACM](https://dl.acm.org/doi/10.1007/978-3-030-98305-5_20)
- *Structured Sentiment Analysis in Brazilian Portuguese: An Exploratory Study Using BERTimbau.* [PROPOR 2026](https://aclanthology.org/2026.propor-1.92/)
- *BERTaú: Itaú BERT for digital customer service.* [LatinX in AI / NeurIPS](https://research.latinxinai.org/papers/neurips/2023/pdf/Vinicius_Carida.pdf)
- *Utilizando BERTimbau para a Classificação de Emoções em Português.* [ResearchGate](https://www.researchgate.net/publication/356825341_Utilizando_BERTimbau_para_a_Classificacao_de_Emocoes_em_Portugues)
- *Exploring BERT for Aspect-based Sentiment Analysis in Portuguese Language.* [FLAIRS](https://journals.flvc.org/FLAIRS/article/download/130601/133875/232982)

**Datasets**
- [B2W-Reviews01](https://github.com/americanas-tech/b2w-reviews01) · [ficha do corpus](https://opencor.gitlab.io/corpora/real19b2wreviews01/)
- [TweetSentBR](https://paperswithcode.com/dataset/tweetsentbr)
- [Brazilian Portuguese Sentiment Analysis Datasets (Kaggle)](https://www.kaggle.com/datasets/fredericods/ptbr-sentiment-analysis-datasets)
- [RePro: A Benchmark Dataset for Opinion Mining in Brazilian Portuguese (PROPOR 2024)](https://aclanthology.org/2024.propor-1.44.pdf)
- [Portuguese-NLP — lista de recursos](https://github.com/ajdavidl/Portuguese-NLP)

**Satisfação em chatbot**
- *Conversation logs as a source of insight: predicting user satisfaction for customer service chatbots.* [Quality and User Experience, Springer, 2025](https://link.springer.com/article/10.1007/s41233-025-00071-8)
- *Speech Sentiment and Customer Satisfaction Estimation in Socialbot Conversations.* [arXiv:2008.12376](https://arxiv.org/pdf/2008.12376)
- *A Role-Selected Sharing Network for Joint Machine-Human Chatting Handoff and Service Satisfaction Analysis.* [arXiv:2109.08412](https://arxiv.org/pdf/2109.08412)
- *Refining the prediction of user satisfaction on chat-based AI applications.* [PMC11793979](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11793979/)
- *I, Chatbot: Modeling the Determinants of Users' Satisfaction and Continuance Intention.* [ResearchGate](https://www.researchgate.net/publication/343148558_I_Chatbot_Modeling_the_Determinants_of_Users'_Satisfaction_and_Continuance_Intention_of_AI-Powered_Service_Agents)

**Emoji**
- Kralj Novak et al. *Sentiment of Emojis.* [PLOS ONE 2015](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0144296) · [PDF](https://research.ceu.edu/ws/portalfiles/portal/5330193/Kralj-Novak-Petra1_2015.pdf) · [dataset](https://research.ceu.edu/en/datasets/emoji-sentiment-ranking-10/)
- *Emo-SL Framework: Emoji Sentiment Lexicon.* [IEEE Access](https://ieeexplore.ieee.org/document/10483059/)
- *Sentiment analysis of emoji fused reviews using machine learning and BERT.* [Nature Scientific Reports 2025](https://www.nature.com/articles/s41598-025-92286-0)
- *An emoji feature-incorporated multi-view deep learning for explainable sentiment classification.* [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0040162524001227)

**Tempo de resposta**
- *From Seconds to Sentiments: Differential Effects of Chatbot Response Latency on Customer Evaluations.* [IJHCI 2025](https://www.tandfonline.com/doi/full/10.1080/10447318.2025.2508915) · [PDF](https://scholarworks.bwise.kr/erica/bitstream/2021.sw.erica/125647/1/FromSecondstoSentimentsDifferentialEffectsofChatbotResponseLatencyonCustomerEvaluations.pdf)
- [Live Chat Response Time Benchmarks 2026](https://www.gethelpable.com/blog/live-chat-response-time-benchmarks)
- [Customer Support Response Time Statistics](https://livechatai.com/blog/customer-support-response-time-statistics)

**KPIs e dashboard**
- [Chatbot KPIs: The Complete Metrics Reference for 2026 — Agentkit](https://agentkit.ai/blog/chatbot-kpis-metrics)
- [Chatbot KPIs that prove ROI to leadership — Netguru](https://www.netguru.com/blog/chatbot-kpis)
- [Chatbot Analytics: KPIs, Dashboards & Metrics Guide — Quickchat](https://quickchat.ai/post/chatbot-analytics)
- [AI Chatbot KPIs: 15 Metrics That Actually Matter in 2026 — Heeya](https://heeya.fr/en/blog/ai-chatbot-kpis-metrics-guide-2026)

**RAG vs. fine-tuning**
- [RAG vs Fine-Tuning 2026: A Decision Framework — Winder.ai](https://winder.ai/rag-vs-fine-tuning-2026-decision-framework/)
- [RAG vs Fine-Tuning: A 2026 Decision Framework — Zartis](https://www.zartis.com/rag-vs-fine-tuning-a-2026-decision-framework/)
- [RAG vs Fine-Tuning vs Agents — BEON.tech](https://beon.tech/blog/rag-vs-fine-tuning-vs-agents/)
- [LLM Fine Tuning for Text Classification: The 2026 Playbook — Sivaro](https://sivaro.in/articles/llm-fine-tuning-for-text-classification-the-2026-playbook/)

**Integração de canal**
- [WhatsApp Business API Integration 2026 — Chatarmin](https://chatarmin.com/en/blog/whats-app-business-api-integration)
- [WhatsApp Cloud API Integration in 2026 — Medium](https://medium.com/@aktyagihp/whatsapp-cloud-api-integration-in-2026-0493dd05d644)

**Stack**
- [Realtime Dashboard with FastAPI, Streamlit and Next.js — Jaehyeon Kim](https://jaehyeon.me/series/realtime-dashboard-with-fastapi-streamlit-and-next.js/)
- [Streamlit Alternatives in 2026 — Innonexa](https://www.innonexa.com/2026/07/02/streamlit-alternatives-python-ai-agent-apps-2026/)

**Mitologia**
- [Dolo (mitologia) — Wikipédia](https://pt.wikipedia.org/wiki/Dolo_(mitologia))
- [Dolo e Ápate: O dom da mentira — HistóriaBlog](https://historiablog.org/2023/07/09/dolo-e-apate/)
- [Apate — Wikipedia](https://en.wikipedia.org/wiki/Apate)
