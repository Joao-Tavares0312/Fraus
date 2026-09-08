# Abstenção por contestação — o tempo contesta o elogio

**Data:** 08/09/2026
**Estado:** implementado em 08/09/2026, com a medição da tabela abaixo feita
contra a API real depois da implementação

## O problema

A frase canônica do projeto — *"que atendimento maravilhoso, só esperei 3
horas"* — é o caso de manual da ironia de atendimento, e o sistema a lê como
elogio sincero: a cabeça de texto dá **0,858 de satisfeito** para ela.

> **Medição de 08/09/2026 — o "99,93" que circula na documentação deste projeto
> é o caso RÁPIDO, e faltava esse qualificador em todo lugar, inclusive na
> primeira versão desta spec.** A mesma fala, contra a API real, só variando o
> relógio:
>
> | latência | score | nota | categoria | contestada |
> |---:|---:|---:|---|---|
> | 10 s | 99,92 | 10 | promotor | — |
> | 179 s | 99,70 | 10 | promotor | — |
> | **181 s** | **99,69** | **10** | **promotor** | **SIM** |
> | **300 s** | **99,21** | **10** | **promotor** | **SIM** |
> | 600 s | 93,25 | 9 | promotor | — |
> | 1800 s | 17,19 | 2 | detrator | — |
> | 10800 s | 0,00 | 0 | detrator | — |
>
> Com as três horas **dentro do próprio log**, o relógio já derruba o score
> sozinho. Os 99,9 aparecem quando a conversa registrada é rápida — o que é
> real e comum: o cliente abre um atendimento novo e ironiza sobre uma espera
> que aconteceu **fora** daquele log.
>
> **A janela da marca é estreita de propósito, e a estreiteza é a feature:**
> abaixo de 180 s não há contradição a marcar; acima de ~10 min o modelo já
> acerta sem ajuda. A contestação cobre a faixa de ~3 a ~9 minutos, onde o
> texto satura e o tempo ainda não venceu. Se um dia ela parecer inútil por
> marcar pouco, é este bloco que precisa ser lido antes de alargá-la.

`incongruencia_situacao_negativa` entrou no vetor em 04/09/2026 exatamente para
alcançá-la. **Não alcançou.** Ela dispara e ganhou peso −0,193, mas não vence
`texto_prob_satisfeito_media`, que pesa **+2,78**, quando o BERTimbau lê a
frase como elogio sincero. Nenhuma feature agregada de conversa reverte uma
probabilidade saturada por mensagem.

## Por que NÃO uma feature nova no fusor

O handoff de 08/09 propunha (§5.2) cruzar tempo × texto como feature número 40:
disparar quando a probabilidade de satisfeito está saturada **e** a latência
está na faixa crítica. É a rota que a literatura indica — Riloff et al. (EMNLP
2013) definem sarcasmo como contraste entre sentimento positivo e situação
negativa, e o lado negativo já existe medido no sistema, no sinal de tempo.

**O corpus de treino não pode ensinar essa feature.** O fusor treina com texto
real do B2W-Reviews01 costurado na *estrutura* de conversa do simulador
(`docs/treinamento.md:461`): o rótulo vem da resenha, e a latência vem de uma
distribuição log-normal **por rótulo**. A feature de interação só seria
diferente de zero nas caudas que se cruzam — os ~11% de conversas satisfeitas
que saíram lentas (`docs/treinamento.md:131`) — e **todas elas estão rotuladas
satisfeito, por construção**.

O corpus não contém um único exemplo de "elogio + espera longa = insatisfação".
Ele contém o contrário. O fusor aprenderia peso **positivo** para a feature que
existe para derrubar a nota: exatamente o modo de falha que tirou
`ironia_prob_media`/`ironia_prob_max` do vetor em 04/09/2026, com roupa nova. E
`test_nenhuma_feature_e_previsor_unilateral` não pegaria — a feature não é
unilateral, ela só está com o sinal trocado.

> Isto é leitura do corpus e da documentação, **não experimento**. Medir custaria
> um retreino no Colab e a API fora do ar no intervalo — o que já aconteceu
> quatro vezes, a última custando quatro dias. A decisão foi não pagar esse
> custo para confirmar um modo de falha já documentado duas vezes.

A rota da feature fica registrada como **trabalho futuro condicionado a
corpus**: ela é implementável no dia em que existir atendimento real anotado,
que é a mesma condição que trava o retreino da cabeça de ironia.

## O que este desenho faz

The Art of Abstention (ACL 2021) formaliza a regra de Chow: o classificador
decide acima de um limiar de confiança e se abstém abaixo dele. Aplicado aqui,
com uma diferença deliberada — **a abstenção não apaga o número**.

Quando o veredito está saturado e o tempo o contradiz, o atendimento ganha uma
**contestação**: uma marca derivada, ao lado do score, que a tela mostra e o
export leva. O score continua o que o modelo deu, a nota continua 10, a
categoria continua promotor, e o atendimento **continua contando no NPS**.

```
Atendimento sweep-00300s              99,21
  nota 10 · promotor
  ⚠ leitura contestada — elogio saturado
    contra espera de 5 min. Ver transcrição.

NPS: -40  (inclui este)
```

**Por que marcar em vez de tirar do agregado.** Tirar seria mais honesto no
caso isolado e mais perigoso no conjunto: um limiar mal calibrado esvazia o
indicador em silêncio, e "quantos atendimentos sumiram?" é a primeira pergunta
que a banca faz. Marcar não muda nenhum agregado, não transforma nada em
`None`, e mantém a invariante 3 intacta — a contestação também é derivada no
servidor. **Rebaixar para neutro foi recusado**: inventaria um veredito que o
modelo não produziu, que é o número simulado que o `CLAUDE.md` proíbe.

## A regra

```
contestado  =  score > 95  E  latencia_mediana_s > 180
```

**O lado do tempo** vem da literatura que `fraus/sinais/tempo.py` já cita: 57%
de abandono acima de 3 minutos (*From Seconds to Sentiments*, IJHCI 2025). O
número tem procedência publicada, não é gosto nosso.

**O lado do texto é o `score` gravado, e não `texto_prob_satisfeito_media`** —
esta é a adaptação que a leitura obriga. O banco guarda `score`, `categoria` e
o payload da conversa (`fraus/db.py:53`); as 39 features **não são
persistidas**, e recalculá-las por linha significaria rodar o BERTimbau em toda
listagem (este projeto já teve incidente de CPU bloqueando o event loop do
uvicorn).

Três ganhos da troca, além de ser a única viável:

- nenhuma chamada de modelo na leitura, nenhuma coluna nova;
- vale **retroativamente** para o que já está no banco, inclusive as conversas
  da demonstração;
- contesta o **veredito exibido** em vez de um intermediário que a tela nunca
  mostra — o que é mais fácil de defender, não menos.

Na frase canônica com espera de 5 minutos — o falso promotor real, medido:
score 99,21 > 95, latência 300 s > 180.

## Componentes

### `fraus/contestacao.py` — módulo novo

Uma função pura, sem dependência de API, banco ou modelo:

```python
def contestacao(
    score: float | None, latencia_mediana_s: float | None
) -> dict | None
```

Devolve `None` quando não há contestação, ou o dicionário que a tela usa para
escrever a frase sem duplicar a regra em TypeScript (invariante 3):

```python
{
    "motivo": "elogio_contra_espera",
    "latencia_mediana_s": 300.0,
    "limiar_s": 180,
    "score": 99.21,
    "limiar_score": 95,
}
```

Módulo próprio, e não `indicadores.py` (que é a régua do NPS e já é grande) nem
`resumo.py` (cuja `resumir` não recebe o score). Um propósito, testável sozinho.

**Casos de ausência, e por que nenhum deles contesta:**

- `score is None` — conversa sem fala do cliente. Ausência de dado não é
  insatisfação nem contestação (invariante 2).
- `latencia_mediana_s is None` — conversa sem nenhuma resposta. Não há
  contradição *medida*, e inventar uma seria o mesmo pecado com outro nome.
- score alto e latência normal — é elogio, e elogio rápido é o caso saudável.
- score baixo e latência alta — é reclamação com espera longa. O sistema já
  acertou; contestar aqui seria contestar o acerto.

### API

`GET /conversas` e `GET /conversas/{id}`, na mesma expressão onde `categoria` e
`nota` já são derivadas (`fraus/api/rotas/conversas.py:149` e `:169`). Chave
nova `contestacao`, `null` na esmagadora maioria das linhas.

A latência já chega ali por `resumir(conversa)`, que devolve
`latencia_mediana_s` derivada dos timestamps (invariante 5 — latência nunca é
persistida). Nada de novo precisa ser calculado.

**Nenhum agregado muda.** `/indicadores`, NPS, CSAT, contenção e série temporal
seguem idênticos, contando o atendimento contestado como sempre contaram.

### Dashboard

- **Atendimentos** — marca na linha, discreta, ao lado da nota.
- **Transcrição** — bloco com a frase por extenso ("elogio saturado contra
  espera de 5 min"), montada a partir dos campos que a API já mandou.

Segue `dashboard/DESIGN.md`. A marca **não pode depender de JavaScript** para
aparecer, pela mesma regra que tirou a etiqueta de honestidade do `Revelar` na
vitrine: numa ferramenta cujo nome é o dáimon do engano, a ressalva não pode
ser a parte que some quando algo falha.

## Testes

`tests/test_contestacao.py`, sobre a função pura — a regra, cada caso de
ausência, as duas fronteiras (score exatamente 95, latência exatamente 180) e a
frase canônica de ponta a ponta.

Na API, um teste por rota provando que a chave aparece derivada e que
`/indicadores` **não** mudou.

No front, o teste é de que a marca sai do **markup**, não de um efeito: ela
vem dos campos que a API mandou, renderizada no servidor, sem estado de cliente
nem animação de entrada. É o que torna verificável a regra de que a ressalva
não pode depender de JavaScript.

## Honestidade metodológica — o que declarar

**A composição é desenho nosso.** O limiar de tempo tem procedência publicada e
a regra de Chow tem formalização (ACL 2021), mas **não há receita publicada
ligando confiança de sentença a sinal de conversa** — o handoff de 08/09
registra isso como lacuna declarada (§8), e ela continua de pé. O que este
desenho faz é escolher um ponto nesse vazio e dizer que escolheu.

Vale a mesma postura que o projeto já assume com o sinal de tempo treinado em
dados sintéticos: limitação declarada, não segredo.

**Calibração não resolveria isto.** *Temperature scaling* e *Platt scaling*
amaciam a confiança da sentença isolada, mas não usam sinal de conversa — são
ortogonais ao problema, e com conjunto de calibração pequeno podem piorar a
superconfiança.

## O que a verificação achou de quebra, e não é desta spec

Atribuição da mesma conversa com **3 horas** de espera (uma única fala do
cliente, que a cabeça de texto lê como 86% satisfeito):

```
latencia_primeira_resposta_s   -85,405
duracao_total_s                -35,759
latencia_mediana_s             -20,569
latencia_p90_s                 -12,326
texto_prob_satisfeito_media     +4,574   ← o texto inteiro
```

**O tempo pesa 20× o texto.** As features de latência não têm teto, e o corpus
de treino nunca passou de minutos (medianas 5/30/200 s): em 3 horas o z-score
do `StandardScaler` explode e o relógio assume o controle da nota. A conversa
sai com score `4,4e-24`.

O critério do próprio `docs/treinamento.md` diz o que isso é: *"se as features
que lideram forem as circunstanciais (tempo, contagem de turnos), procure o
vazamento."* É a invariante 10 se manifestando **em runtime**, não no treino —
a guarda de vazamento olha a distribuição no corpus, e o corpus não tem
latência de três horas.

Não está resolvido aqui e **não deve ser**: clipar a latência, passar a log ou
aceitar e declarar são três decisões diferentes, e a terceira não é obviamente
errada. Fica como pendência própria em `docs/handoff.md`.

## Fora de escopo

- A feature 40 no fusor (acima — condicionada a corpus).
- A tela `/analisar`: recebe texto colado sem timestamps de diálogo real, então
  o lado do tempo quase nunca dispararia lá. Mostrar a promessa numa tela que
  não a cumpre é pior que não mostrar.
- Retreinar a cabeça de texto para não saturar. É a raiz, é o trabalho mais
  pesado, e continua na fila.

## Referências

- [The Art of Abstention (ACL 2021)](https://aclanthology.org/2021.acl-long.84/)
- [Riloff et al. 2013 — Sarcasm as Contrast between a Positive Sentiment and Negative Situation](https://aclanthology.org/D13-1066/)
- [Joshi et al. — Harnessing Context Incongruity for Sarcasm Detection](https://www.researchgate.net/publication/280997312_Harnessing_Context_Incongruity_for_Sarcasm_Detection)
- *From Seconds to Sentiments* (IJHCI 2025) — a faixa crítica de latência, já citada em `fraus/sinais/tempo.py`
- `docs/treinamento.md` — a costura B2W × simulador e os dois vazamentos já pagos
