# Diferenciais — roteiro da demonstração

Roteiro para apresentar os diferenciais na banca, em cerca de 10 minutos. Cada passo diz:

- o que mostrar;
- o que falar;
- o que **não** afirmar.

A comparação com produtos do mercado está em [concorrentes](concorrentes.md), e cada afirmação ali tem fonte e data.

## Antes de começar

- **Com os modelos reais** (o fusor `log1p` em `modelos/`): suba a API real e a dashboard. É o único jeito de mostrar a explicação, o contrafactual, os drivers e o replay com números do modelo.
- **Sem os modelos:** `uv run python scripts/api_demo.py` sobe um snapshot sintético. Nesse caso, diga em voz alta que os números são sintéticos.
- **O selo de confiança (E2)** só aparece depois de `scripts/calibrar_conformal.py --gravar`. Sem o artefato, a tela mostra o motivo (503). **Mostrar isso também é honesto**: o sistema se recusa a fingir confiança.
- Escolha antes três atendimentos:
  1. um detrator com espera longa (para o contrafactual);
  2. um com abstenção ou sinalizador;
  3. um com início de deterioração no Replay.

## 1. A tese (1 min)

**Falar:**

> O Fraus estima a satisfação a partir da conversa, sem perguntar ao cliente e sem LLM em produção. São modelos pequenos, locais e determinísticos. Hoje vou mostrar quatro coisas que ele faz de forma diferente:
>
> - explica a nota a partir dos próprios coeficientes;
> - diz quando não tem confiança;
> - marca riscos sem julgar o atendente;
> - mostra o que puxa o NPS, sem confundir isso com causa.

**Não afirmar:** que o NPS foi perguntado ao cliente. Ele é **inferido**, e toda tela tem a etiqueta "estimativa".

## 2. Um atendimento, de ponta a ponta (4 min)

Abra o atendimento 1 em Atendimentos.

1. **A nota, a categoria e a etiqueta "estimativa".** A nota sai do servidor; a tela só exibe.
2. **"Por que esta nota" (E1).** A frase é montada por template sobre a decomposição exata do fusor.
   - **Falar:** "A soma das contribuições reproduz exatamente o logit do modelo. Não é uma aproximação, e não é um texto gerado sobre o modelo: é o modelo."
   - **Não afirmar:** que o efeito por família soma a nota. Ele é um recálculo exato, mas não é aditivo, e a tela diz isso.
3. **Contrafactual de espera (E1).** Simule "primeira resposta em 60 s".
   - **Falar:** "Se a primeira resposta tivesse vindo em um minuto, a estimativa seria esta. Nada é gravado."
   - Mostre a recusa (422) com uma hipótese fora da faixa de treino: o sistema não extrapola.
4. **Selo de confiança (E2).** Mostre a classe de satisfação compatível com a nota, com calibração de 90%. Depois mostre um caso de abstenção.
   - **Falar:** "Quando a nota é compatível com mais de uma classe, ele diz 'leitura sem confiança suficiente'. A conversa continua no NPS: a abstenção marca e informa, não corrige."
   - **Não afirmar:** que a garantia vale em produção. Ela vale sob permutabilidade com o holdout, e o tempo desse holdout é sintético.
5. **Sinalizadores (E5).** Mostre a lista acima da transcrição e a marca ⚑ nas mensagens.
   - **Falar:** "São regras explicáveis sobre a fala do cliente, a do bot, contagens e posição. Nenhuma lê o que o atendente humano escreveu: há um teste que prova isso."

## 3. O agregado (2 min)

1. **Drivers (E1), na Visão geral, sob demanda.** Mostre o que mais pesa em detratores e em promotores, com IC.
   - **Falar:** "É uma amostra sorteada por semente, e o tamanho dela é declarado. É associação no modelo, não causa."
2. **Impacto por tema (E6), na aba Radar da Operação.** Mostre o NPS inferido do tema contra o resto do recorte, com IC.
   - **Falar:** "É associação, não causa, e o IC só cobre a incerteza amostral. Com menos de 30 conversas com sinal em qualquer lado, ele não dá número nenhum e diz quanto falta."

## 4. Retrospectiva de uma conversa (1 min)

Abra o atendimento 3 na aba Replay da Operação.

- **Falar:** "Cada ponto do gráfico só vê as mensagens que já tinham acontecido; há um teste de não vazamento para isso. A linha tracejada marca o início da deterioração, ou seja, de onde a estimativa ficou detratora e não voltou. É retrospectivo: o Fraus não alerta durante o atendimento."
- **Não afirmar:**
  - que o lead time medido prevê o de produção, porque o simulador não gera trajetória;
  - que essa marca detecta mais detratores que o score final, porque, por construção, não detecta.

## 5. O que o Fraus não faz (slide, 1 min)

| não faz | por quê |
|---|---|
| Não pontua atendente humano | É política de conformidade, não feature. Nenhuma regra lê a fala do atendente. |
| Não roda durante o atendimento | É lote, sobre conversa encerrada. Não há alerta ao vivo. |
| Não decide nada sozinho | Abstenção, sinalizadores e deterioração marcam e informam. A nota não muda. |
| Não usa LLM em produção | São modelos locais e determinísticos. A explicação vem dos coeficientes. |
| Não afirma causa | Drivers e impacto por tema são associação. |
| Não troca ausência por zero | Sem sinal, ou com amostra pequena, a tela nomeia o que falta. |
| Não chama de NPS declarado | É NPS **inferido**, sempre com a etiqueta de estimativa. |

## 6. Perguntas prováveis da banca

**"Por que não usar um LLM?"** Custo, latência, determinismo e execução local. A explicação do Fraus é exata porque o modelo final é linear. A comparação numérica com LLM foi **descartada** do escopo (E4); não há número para citar.

**"Esses números foram medidos no modelo real?"** Responda pelo [relatório](relatorio.md). As medições no fusor real estão marcadas como "não verificado", e os scripts estão prontos. Não arredonde isso para "sim".

**"O sinal de tempo é real?"** Não. O fusor treinou o tempo em dados **sintéticos**, calibrados pela literatura, porque nenhum corpus público em português tem timestamps de diálogo. Isso está declarado em todas as métricas.

**"Como vocês sabem que os sinalizadores acertam?"** Os casos construídos verificam a implementação. Precisão e recall em dado real dependem de uma amostra anotada que ainda não existe.

**"Qual a diferença para os produtos do mercado?"** Comece pelo mais próximo: o Intercom CX Score também infere sem pesquisa, explica por motivos, deixa sem nota a conversa sem informação e não avalia atendente individual. Diga isso antes que a banca diga. O que é diferente, com fonte em [concorrentes](concorrentes.md):

- o Fraus não usa LLM (o Intercom declara usar LLM de terceiros);
- a explicação do Fraus é a decomposição exata do modelo;
- a incerteza do Fraus tem garantia estatística declarada, por classe. Nos concorrentes lidos, não encontramos incerteza por previsão;
- Zendesk QA, Observe.AI e Medallia pontuam agentes, e o Fraus não.
