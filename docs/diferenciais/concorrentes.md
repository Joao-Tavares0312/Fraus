# Diferenciais — o que os concorrentes fazem (fontes de 14/10/2026)

Esta página sustenta toda afirmação sobre concorrentes que entrar em documento ou slide. Cada linha tem URL e data de acesso, e a confiança é uma de três:

- **confirmado:** citação na página oficial;
- **parcial:** veio de trecho de busca ou de resumo da página, sem a frase literal;
- **não confirmado.**

O que não está aqui **não pode ser afirmado** na banca.

**Como foi coletado.** Busca web e depois a leitura da página, em 14/10/2026. A leitura passa por um resumo automático, então uma citação marcada "parcial" precisa ser relida na fonte antes de virar slide. Algumas páginas recusaram o acesso (403); elas estão marcadas.

## Leitura honesta do resultado

**O produto mais próximo do Fraus é o Intercom CX Score.** Ele também:

- infere a satisfação sem pesquisa;
- explica a nota por motivos (*reasons*);
- deixa sem nota a conversa sem informação suficiente;
- pontua só depois de a conversa encerrar;
- declara que não serve para avaliar o desempenho individual de quem atende.

**Isso tira do Fraus o direito de chamar de exclusivos os pontos acima.** O que sobra de diferente, com base no que foi verificado:

1. **Sem LLM.** O Intercom declara que combina tecnologia própria com "*third-party large language models*". O Fraus usa modelos pequenos e locais e roda sem rede no caminho de predição.
2. **Explicação que é o modelo.** No Fraus, as contribuições somam exatamente o logit do fusor (E1), e a frase sai por template sobre essa soma. Nas fontes lidas, os *reasons* do Intercom são categorias atribuídas à conversa; não encontramos descrição de decomposição numérica.
3. **Incerteza com garantia estatística declarada.** O Fraus tem um conjunto conformal por classe, com cobertura-alvo e abstenção quando o conjunto não tem exatamente uma classe (E2). A abstenção do Intercom, nas fontes lidas, é por elegibilidade: falta de informação na conversa. **Não encontramos, em nenhum concorrente, incerteza por previsão.**
4. **Método aberto e reproduzível.** O código, as sementes, as limitações e o que não foi verificado estão publicados.

**Diferença de política.** Zendesk QA, Observe.AI e Medallia **pontuam agentes** (QA por rubrica, coaching). O Fraus não pontua atendente, por desenho. O Intercom também declara não servir para isso.

## Intercom — Fin CX Score

Fonte principal: <https://www.intercom.com/help/en/articles/10495092-understand-customer-experience-at-scale-with-the-cx-score> (acesso em 14/10/2026).

| afirmação | evidência | confiança |
|---|---|---|
| Infere sem pesquisa | "scoring every meaningful interaction—without relying on surveys" | confirmado |
| Usa LLM de terceiros | "combination of Intercom's proprietary technology and third-party large language models" | confirmado |
| Explica por *reasons* (qualidade da resposta, esforço do cliente, emoção forte, feedback de produto e de política) | rótulo "CX Score reasons"; a lista veio do resumo da página | confirmado (*reasons*); parcial (a lista) |
| Escala de 1 a 5 | trecho de busca | parcial |
| Deixa sem nota a conversa sem informação suficiente | "enough conclusive information in the conversation to determine a rating" | confirmado (por elegibilidade) |
| Intervalo de confiança ou probabilidade por previsão | — | não confirmado |
| Não serve para avaliar atendente individual | "not intended to help assess individual teammate performance" | confirmado |
| Só depois do encerramento | o resumo cita "The conversation has been closed" como requisito | parcial |

O blog <https://www.intercom.com/blog/the-new-cx-score-explained/> apareceu na busca e **não foi lido**.

## Zendesk — Zendesk QA (ex-Klaus) / AutoQA

Fontes, todas acessadas em 14/10/2026:

- <https://www.zendesk.com.br/blog/ai/workflow-automation/auto-qa/>
- <https://support.zendesk.com/hc/en-us/articles/9046364914842-Improving-AutoQA-accuracy>

| afirmação | evidência | confiança |
|---|---|---|
| Avalia 100% das conversas contra rubricas, incluindo o agente | "calls, chats and e-mails"; pontuação de agente por rubrica (resumo) | confirmado |
| Detecta sentimento, riscos, bots em laço e sinais de churn | "changes in customer sentiment, compliance gaps, looping bots, unresolved issues, churn signals" | confirmado |
| **Pontua o desempenho do agente** | "as a confidence indicator when evaluating agent performance" | confirmado |
| Mede acurácia contra revisão humana, não a incerteza por previsão | "reflects agreement between AI and human ratings" (resumo) | parcial |
| Usa IA generativa | resumo | parcial |
| Tempo real | resumo | parcial |
| Prevê CSAT de forma nativa | só aparece num app de marketplace que não foi lido (403) | não confirmado |

Nota: o Zendesk também detecta "*looping bots*", assim como o `loop_do_bot` do E5. A diferença está em pontuar o agente, não na regra.

## Observe.AI

Fonte: <https://www.observe.ai/platform/interaction-intelligence> (acesso em 14/10/2026). A página de CX deu 404.

| afirmação | evidência | confiança |
|---|---|---|
| Pontua todas as interações contra rubrica | "Score 100% of interactions - automatically" | confirmado |
| Explica por trecho da transcrição | "exact transcript moments behind every score" | confirmado (por evidência; não por *drivers*) |
| Pontua agentes (QA, coaching) | trechos de busca do blog | parcial |
| Sentimento como nota atribuída por IA | trecho de busca do blog | parcial |
| CSAT previsto | só em guia de terceiros | não confirmado |
| Confiança ou abstenção | — | não confirmado |

## Medallia — Conversational Intelligence

Fonte: <https://www.medallia.com/suite/contact-center-experience/conversational-intelligence/> (acesso em 14/10/2026).

| afirmação | evidência | confiança |
|---|---|---|
| Emoção e sentimento por IA | "AI-powered emotion analysis highlights sentiment, pains, and emerging CX trends" | confirmado |
| Pontuação automática de toda interação, ligada ao agente | "Automated Scoring For Every Interaction" | confirmado |
| Coaching logo após a interação | resumo | parcial |
| NPS ou CSAT previsto sem pesquisa | a página trata a conversa como complemento da pesquisa | não confirmado |
| Explicação, confiança ou abstenção por previsão | — | não confirmado |

## Zenvia (incorporou a Movidesk)

Fontes (acesso em 14/10/2026):

- <https://zenvia.com/en/customer-cloud/serve-better/> (lida);
- o artigo da base de conhecimento sobre análise de sentimento devolveu só o título.

| afirmação | evidência | confiança |
|---|---|---|
| Análise de sentimento com IA em tickets e chats | "identify sentiments, and prioritize tickets" | confirmado |
| "Índice de Satisfação" inferido da conversa, sem pesquisa | "without depending on formal surveys" (trecho de busca) | parcial |
| IA generativa para categorizar e medir sentimento | trecho de busca | parcial |
| Aquisição da Movidesk em 2022 | trecho de busca | parcial |
| Sentimento por agente; tempo real por conversa | o resumo foi especulativo e foi descartado | não confirmado |
| Explicação, confiança ou abstenção | — | não confirmado |

## Blip (Take Blip)

As páginas de ajuda deram 403. O conteúdo vem de trechos de busca, exceto a extensão Feeling Monitor.

| afirmação | evidência | confiança |
|---|---|---|
| "Conversation Quality": nota de 0 a 100 a partir de fluência, integridade, resolução e relevância | <https://help.blip.ai/hc/en-us/articles/36747923309719-Conversation-quality>: "predominant sentiment expressed by the user throughout the conversation" | parcial |
| Monitor de sentimento em tempo real | <https://store.blip.ai/en/extensions/x5epboo>: "Track your customers' sentiment in real time". **É extensão paga de terceiro**, não nativa | confirmado |
| Desk Score ("qualidade com IA"): o que avalia | <https://help.blip.ai/hc/en-us/articles/37508015695127> (403) | não confirmado |
| Se a nota usa LLM; explicação, confiança ou abstenção | — | não confirmado |

## O que NÃO pode ser afirmado

- Que o Fraus é o único a inferir satisfação sem pesquisa. **O Intercom faz isso.**
- Que o Fraus é o único a explicar a nota, ou a não avaliar atendente. **O Intercom também.**
- Que o Zendesk QA, a Observe.AI ou a Medallia preveem CSAT ou NPS de forma nativa: não confirmado em fonte oficial.
- Qualquer coisa sobre a aquisição da Medallia: não pesquisado.
- Qualquer coisa sobre o Desk Score da Blip, ou se a Blip usa LLM: não confirmado.
- Qualquer comparação numérica com LLM: o E4 foi descartado e não há número.
