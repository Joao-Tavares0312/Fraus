# E1 — "Por que esta nota" e drivers

> Estado: **aguardando aprovação**. Faz parte de
> [Diferenciais](2026-10-14-diferenciais-visao-geral.md).

## Objetivo

Explicar cada nota de forma **exata**: a explicação reconstrói a predição, não
a aproxima. Mostrar também o que mais puxa detratores e promotores no
agregado. É a resposta ao "CX Score Reasons", com a diferença de que aqui a
explicação **é** o modelo, e não um texto gerado sobre ele.

## Desenho

**1. Decomposição exata.** A regressão é multinomial com classes 0, 1 e 2.
Contra a classe 0, ela tem dois eixos aditivos:

- `l₂ = log(P₂/P₀) = (b₂ − b₀) + Σᵢ (w₂ − w₀)ᵢ · zᵢ`
- `l₁ = log(P₁/P₀) = (b₁ − b₀) + Σᵢ (w₁ − w₀)ᵢ · zᵢ`

O score sai **exatamente** desses dois números:
`P = softmax(0, l₁, l₂)`, `score = 100 · (P₂ + 0,75 · P₁)`.

`Fusor.decompor(features)` devolve, para cada eixo, o intercepto e a
contribuição de cada feature, agrupada também por família. O `z` é calculado
depois do `log1p` e do `StandardScaler`, que é o espaço em que o fusor opera.

O eixo 2×0 é o que `contribuicoes` já calcula hoje, então o número que a tela
mostra hoje não muda. O caso binário segue a mesma regra de `_diferenca`.

**2. Efeito por família, em pontos de score.** Para cada família, recalcula o
score com as features dessa família em `z = 0` (a média do treino) e mostra a
diferença: "sem o sinal de tempo, na média do treino, o score seria 64 em vez
de 41".

É exato, porque é um recálculo, mas **não é aditivo**: as famílias não somam
o score. A tela diz isso, e a soma exata fica no eixo de logit (item 1).

**3. Texto por template**, nunca por LLM. Usa as duas famílias de maior efeito
para cada lado ("a espera de 12 min pesou contra; o texto do cliente pesou a
favor") e a medida bruta da feature dominante quando ela existe (minutos de
espera). Os templates moram em `fraus/explicacao.py`, com teste para cada um.

**4. Contrafactual de espera** (`POST /conversas/{id}/contrafactual`, com
`{"primeira_resposta_s": 60}` ou `{"teto_espera_s": 120}`). Reaproveita a
reescrita de timestamps do laboratório (`/operacao/laboratorio/cenario`),
recalcula as features e pontua.

- **Recusa com 422 e mensagem** quando alguma feature do vetor contrafactual
  ou do original tem `|z| > LIMIAR_Z` (4,0, o mesmo critério de
  `/saude/deriva`). "Faixa de treino" quer dizer exatamente isso, porque o
  artefato não guarda mínimo nem máximo.
- **Nada é gravado.**

**5. Drivers agregados** (`GET /explicacao/drivers?inicio&fim&canal&tema`):

- **Por conversa,** dentro do escopo, com sinal, com a régua e o léxico
  vigentes, e **com teto de 200 conversas**, sorteadas por semente fixa e
  declaradas na resposta: decompõe e calcula a média da contribuição por
  família, separando detratores de promotores. O intervalo vem de bootstrap
  com 1.000 reamostras e semente fixa.
- **O que não entra:** conversas sem sinal ficam fora, e são contadas
  (invariante 2, `None` nunca vira 0). Conversas de outra régua também ficam
  fora, contadas como "repontuar para incluir".
- **Rótulo fixo:** "associação no modelo, não causa".
- **Alternativa** (exige aprovação de schema, regra 5): gravar o vetor de
  features no `payload` e acabar com o teto. **Recomendo não fazer agora.**

**6. Tela.**

- Bloco "Por que esta nota" na transcrição: o texto, as barras por família e
  o contrafactual de espera. Reaproveita `PainelContribuicoes` e
  `BarrasDeFeature`.
- Painel "Drivers" em Indicadores.
- A família de cada feature vem do **servidor**. Hoje o TS deriva por
  prefixo em `dashboard/lib/derivacoes.ts`, e duas cópias divergiriam.

## Métrica de aceitação

- **Aditividade:** intercepto + Σ contribuições reproduz `log(P₂/P₀)` e
  `log(P₁/P₀)` com erro menor que 1e-9. O score refeito a partir de
  `(l₁, l₂)` bate com `Fusor.pontuar` com erro menor que 1e-9. O teste usa um
  fusor sintético e, quando os pesos existirem, roda também contra o
  artefato real.
- **Recusa:** contrafactual com `|z| > 4` responde 422 com a feature citada.
  Dentro da faixa responde 200 com o score de antes e de depois.
- **Escopo:** conversa de canal sem permissão responde 404 em todas as rotas
  novas (como `/atribuicao`). Os drivers não incluem canal fora do escopo.
- **Score intacto:** os scores gravados são iguais antes e depois de chamar
  todas as rotas novas.
- **`None` ≠ 0:** uma conversa sem sinal não entra nas médias, e os
  contadores dizem quantas ficaram fora.

## Dados

Testes com fusor sintético e conversas do simulador. As medições de exemplo
para a banca usam o fusor real, que exige os pesos.

## Limitações declaradas

- Contribuição é medida **no modelo**, não causa.
- O sinal de tempo foi treinado em dado sintético.
- "Faixa de treino" é `|z| ≤ 4` sobre a média e o desvio do scaler.
- O teto de 200 conversas faz dos drivers uma estimativa por amostra.

## Desvios aceitos

Decididos no plano e registrados aqui; onde divergem do desenho acima, vale esta seção.

1. **A explicação viaja dentro de `GET /conversas/{id}/atribuicao`** (campo novo `explicacao`), e não numa rota própria.
   - A atribuição já recalcula as features, e uma rota a mais pagaria o BERTimbau duas vezes.
   - Campo novo numa resposta sem `response_model` não muda o OpenAPI.
2. **Drivers ficam em `GET /indicadores/drivers`**, com amostra padrão de 50 e teto de 200 (o mesmo desenho de `/saude/deriva`).
   - O filtro por **tema** sai do E1: tema é calculado na hora pelo Radar, e o impacto por tema é o E6.
3. **O painel de drivers fica na Visão geral, atrás de um botão.** `/modelo/*` é só de `dev` (`fraus/api/seguranca.py:248`), e cada conversa da amostra custa uma passagem de modelo, então o painel não carrega sozinho.
4. **O contrafactual de primeira resposta recusa (422)** quando o alvo poria a resposta antes de uma fala anterior do cliente, porque reordenar a conversa inventaria outra conversa.
5. **Os testes de front usam `renderToStaticMarkup`**, sem biblioteca nova de teste de componente.
6. **O campo do contrafactual é `espera_maxima_s`** (como no laboratório), não `teto_espera_s`; o pedido é estrito e recusa campo desconhecido com 422.
7. **`familia_da_feature` vai na resposta, mas o front ainda deriva a família por prefixo** em `dashboard/lib/derivacoes.ts`; a troca fica para depois (as duas regras concordam hoje).

## Fora de escopo

- Explicação por LLM.
- SHAP ou LIME, desnecessários para um modelo linear.
- Contrafactual de texto ("se o cliente tivesse escrito...").
- Gravar contribuições.
