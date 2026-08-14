# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Analista de operação de atendimento, em português do Brasil, sentado no próprio
monitor em sala com luz normal — **uso diário, não apresentação**. Ele chega
com uma pergunta operacional ("como estamos esta semana?", "quais atendimentos
deram errado?") e precisa varrer números e descer para casos individuais.

Audiência secundária confirmada: a **banca avaliadora** do trabalho de
conclusão, que julga o rigor metodológico tanto quanto o resultado. Ela não é a
cena de uso que governa o desenho.

## Product Purpose

Medir satisfação em atendimentos por chatbot **sem perguntar nada ao cliente**.
O produto existe porque a nota declarada mente: o cliente escreve "ok, obrigado
🙂" e sai insatisfeito. Modelos que olham só características genéricas da
conversa explicam ~10% da variância da satisfação declarada.

Sucesso é o analista confiar no número o bastante para agir, sabendo com
precisão o que nele é medido e o que é estimado.

## Positioning

Fusão de **três sinais independentes** calculados por mensagem — texto
(BERTimbau fine-tunado), emoji (Emoji Sentiment Ranking, com a posição relativa
na mensagem como feature) e tempo (latência como feature aprendida, não
penalidade linear) — sem LLM em runtime.

O que um produto vizinho não copia honestamente: a **atribuição**. Como o score
de texto é por mensagem, o produto aponta *quais falas* puxaram a nota, em vez
de devolver um número opaco.

## Operating Context

- Atendimentos entram por importação de CSV numa raiz configurável, ou por
  fontes cadastradas na tela de Integrações.
- O analista filtra por período e desce da visão agregada para a transcrição de
  um atendimento.
- A API é local, **sem autenticação**, destinada a uso na máquina do analista.
- Cinco telas: Visão geral, Atendimentos (lista e transcrição), Modelo,
  Configurações, Integrações.

## Capabilities and Constraints

- Indicadores: NPS inferido, CSAT, taxa de contenção, latência mediana.
- Faixas de NPS **configuráveis** (padrão 0–6 detrator, 7–8 neutro, 9–10
  promotor) e limiares de latência de exibição (padrão 10 s / 60 s / 3 min).
- Score e categoria são **sempre derivados no servidor**; a interface nunca
  recalcula nota.
- **Sem LLM em runtime** — requisito do trabalho, não escolha de custo.
- O modelo ainda não foi treinado: hoje roda um motor dublê determinístico, e a
  tela Modelo mostra métricas em estado vazio em vez de inventar número.
- O sinal de tempo é treinado em conversas sintéticas, porque nenhum corpus
  público de review PT-BR tem timestamps de diálogo.
- **A classe neutra conta como detratora**, e o NPS sai pessimista por
  construção — decisão de projeto, declarada.
- `GET /serie-temporal` agrega a série no servidor; léxico por classe e tempo
  mediano ainda são derivados das transcrições no cliente.

## Brand Commitments

- Nome **Fraus**, a divindade romana da fraude — contraparte latina de
  Ápate/Dolos, posta por Virgílio à entrada do Inferno. O nome carrega a tese:
  o cliente mente, o texto não.
- Logo: monograma **FR**, F branco e R dourado sobre preto (`#070707`).
- Vinculante por decisão do usuário nesta sessão:
  - os **textos de honestidade** ("estimativa", "sem sinal", nota metodológica,
    estados vazios que nomeiam o que falta) permanecem;
  - o encoding **âmbar = o que foi dito / azul = o que foi medido**;
  - o **gráfico sobreposto de NPS × latência** — pode mudar de forma, mas a
    sobreposição continua, porque é o trade-off que cartão isolado esconde.

## Evidence on Hand

- 62 atendimentos sintéticos do simulador no banco de demonstração, incluindo
  atendimentos **sem fala do cliente** para exercitar o estado "sem sinal".
- Léxico de emoji real: 969 entradas do Emoji Sentiment Ranking, com as
  contagens de anotação humanas originais.
- Referências citáveis no repositório (Springer 2025, IJHCI 2025, Ekman 1992,
  Plutchik 1980, Virgílio).
- **Ausências que não podem ser fabricadas:** não há cliente real, nenhuma
  métrica de modelo treinado, nenhum atendimento de operação real. Todo dado
  visível hoje é sintético e precisa continuar rotulado como tal.

## Product Principles

1. **Nunca inventar número.** Onde falta dado, a tela nomeia o que falta e qual
   etapa ou endpoint resolveria. Numa ferramenta batizada com o nome do daemon
   do engano, dado plausível inventado seria a pior falha possível.
2. **Separar o dito do medido, sempre visivelmente.** A distância entre os dois
   é a informação que o produto vende.
3. **Ausência de dado não é insatisfação.** "Sem sinal" nunca vira zero, nunca
   entra em média, e não pertence à escala.
4. **Mostrar o trade-off, não o indicador isolado.** Otimizar um KPI sozinho
   quebra outro.
5. **O servidor é a fonte da verdade.** Score e categoria vêm dele; a interface
   apresenta e não recalcula.

## Accessibility & Inclusion

- Todo par de cor que carrega **texto** cruza WCAG AA (4.5:1), verificado por
  cálculo em `npm run contraste` — cor de marcação e cor de tipo são coisas
  diferentes.
- Categoria **nunca é comunicada só por cor**: acompanha rótulo textual.
- `prefers-reduced-motion` respeitado.
- Interface inteiramente em português do Brasil.

## Open Decisions

- A **empresa fictícia** do trabalho não está definida (ramo, porte, canais,
  volume plausível de atendimentos). Ela atravessa a apresentação inteira e
  ainda não pode ser assumida.
