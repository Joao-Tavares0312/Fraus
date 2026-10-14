# E5 — Sinalizadores por regras ("Spotlight" sem LLM)

> Estado: **aguardando aprovação**. Faz parte de
> [Diferenciais](2026-10-14-diferenciais-visao-geral.md).

## Objetivo

Destacar conversas de risco com regras **explicáveis**, derivadas na leitura,
sobre **falas do cliente, falas do bot, contagens e relógio**. Nenhuma regra
julga o atendente humano. Isso é limite da Conformidade, e quebrá-lo é bug.

## Desenho

O módulo `fraus/sinalizadores.py` é puro: recebe uma `Conversa` e devolve uma
lista de `{regra, evidencia: [indices de mensagem], detalhe}`. Nada é gravado.

| regra | dispara quando | sobre |
|---|---|---|
| `loop_do_bot` | duas ou mais respostas do **bot** quase idênticas (Jaccard de tokens normalizados ≥ 0,85), não consecutivas no texto do cliente | bot |
| `cliente_repete` | duas ou mais falas do **cliente** com Jaccard ≥ 0,7 e no mínimo 4 tokens | cliente |
| `pedido_de_humano_ignorado` | o cliente pede humano (léxico fixo: "atendente", "humano", "pessoa", "falar com alguém"...) e o bot responde mais de 2 vezes sem haver fala `humano` | cliente + bot |
| `escalada_tardia` | a primeira fala `humano` chega depois de mais de N falas do bot após o primeiro pedido de humano (N = 3, sem procedência, declarado) | bot + relógio |
| `abandono` | reaproveita `features_tempo`: a última fala é de um respondente e o cliente não volta | contagem |

- **Limiares:** declarados como **sem procedência** quando for o caso, como o
  95 da contestação.
- **`escalada_tardia`:** conta falas **do bot** antes do humano, nunca o
  tempo de resposta do humano. Medir o humano seria pontuá-lo.
- **Conversa sem fala do cliente:** a lista é `None`, não `[]`. "Não avaliado"
  é diferente de "nada disparou".

**Exposição.**

- Campo `sinalizadores` em `_com_derivacoes`, ao lado da contestação.
- Filtro `?sinalizador=` em `GET /conversas`. O escopo por canal já vem de
  `BancoComEscopo`.
- Destaque na transcrição: as mensagens de `evidencia` ficam marcadas, com o
  nome da regra e o limiar.

**Medição** (`scripts/medir_sinalizadores.py`).

- **Casos construídos por regra:** um positivo, um negativo e um de borda.
  Ficam nos testes e no script.
- **Amostra anotada à mão:** n declarado e quem anotou. Precisão e recall por
  regra, com IC de Wilson.
- **Pendência:** a fonte da amostra depende do João. Sem dado real, a amostra
  vem do simulador mais conversas escritas à mão para o teste, **rotuladas
  assim**, porque o simulador não gera loop de bot.

## Métrica de aceitação

- **Testes por regra:** positivo, negativo e borda.
- **`None` ≠ 0:** conversa sem fala do cliente devolve `None` e não entra em
  contagem.
- **Guarda de Conformidade:** um teste falha se alguma regra ler texto ou
  timestamp de fala `humano` para julgar a fala. Só a presença e a posição da
  primeira fala `humano` são permitidas.
- **Escopo:** o filtro não vaza canal sem permissão.
- **Score intacto:** scores e categorias não mudam.

## Dados

Simulador mais casos construídos. A amostra anotada fica pendente de fonte.

## Limitações declaradas

- As regras são heurísticas de superfície: falso positivo em resposta
  legitimamente repetida (por exemplo, "posso ajudar em algo mais?").
- O léxico de pedido de humano é fechado.
- Os limiares não foram medidos em dado real.

## Fora de escopo

- Alerta em tempo real.
- Ação automática.
- Qualquer métrica por atendente.
- Detecção por LLM.
