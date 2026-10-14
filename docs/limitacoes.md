# Limitações conhecidas

Esta página existe porque um sistema que estima satisfação **precisa** declarar
onde erra. Nada aqui é segredo, e nada aqui está escondido na tela: cada item
tem contrapartida visível na interface.

## Limitações operacionais do deploy gratuito

A hospedagem da API deixou de ser pendência em 17/09/2026, mas “publicada” não
significa “sem limites”. A função ONNX tem cerca de 1,95 GB (pacote
publicado em 30/09/2026; eram 1,46 GB em 17/09) e usa Large Functions na
Vercel. Depois de esfriar, o primeiro `/saude` observado levou
10,8 s; requisições seguintes foram rápidas, mas não há garantia de latência.

**Cold start e "motor aquecendo".** A API é serverless: cada instância tem o
próprio motor, e ele só ficava pronto depois da primeira predição. Desde
30/09/2026 o motor aquece em segundo plano no boot da instância e a cada sonda
de saúde, e um workflow sonda a API a cada 5 minutos. Isso **reduz** o cold
start, mas não o elimina — a Vercel não garante que a sonda e o usuário caiam na
mesma instância. Eliminá-lo exige um processo sempre ligado com pelo menos
1,5–2 GB de RAM; o plano gratuito do Render (512 MB, dorme em 15 min) não
serve, porque a API mede cerca de 1,06 GB de RSS com os três modelos.

Vercel Hobby, Supabase Free e Oracle Object Storage gratuito oferecem cotas,
não SLA. Ao ultrapassá-las, a aplicação pode ser limitada ou pausada. O estado
fica no Supabase; o Oracle participa do build, não da inferência. Uma restauração
do projeto pode alterar a URI do pooler, e o transaction pooler precisa usar a
porta indicada no painel (6543 no deploy atual).

Essas limitações são operacionais. Elas não alteram as limitações científicas
abaixo e não autorizam apresentar a estimativa como NPS declarado.

---

## O NPS é inferido, não perguntado

Toda exibição carrega a etiqueta de estimativa e o sublinhado pontilhado de
proveniência. Apresentar como NPS declarado seria falso.

**O intervalo de confiança cobre a incerteza AMOSTRAL, não a do modelo.** Ele
responde "quantas conversas sustentam este número"; ele **não** responde "o
quanto o modelo pode estar errado" — isso exigiria calibração aplicada no
runtime, que ainda não existe: `notebooks/05_calibracao.ipynb` mede temperatura
e ECE por cabeça (`modelos/calibracao.json`), mas nada em `fraus/` consome esse
arquivo. Um IC apresentado como se cobrisse o erro do modelo é pior que não ter
IC nenhum, e por isso a ressalva está impressa junto do número, não só aqui.

O intervalo usa **Wald ajustado triangular AW(3,T)**: pseudocontagens de 0,75
para cada extremo e 1,5 para neutros, com variância dividida por `n + 2`,
conforme [Turk, Cinderich e McNeill (2026)](https://doi.org/10.3390/stats9020045).
Isso evita intervalo de largura zero quando todas as conversas pertencem à
mesma categoria. O NPS pontual e a contagem continuam sendo os observados;
o ajuste só participa dos limites do intervalo.

Abaixo de **30 atendimentos com sinal** o cartão principal e a leitura do
intervalo ocultam o ponto estimado e mostram o `n`. Esse corte é uma regra de
exibição, não uma garantia de precisão a partir de 30. A série diária e o
campo `nps` da API preservam o agregado observado; `nps_intervalo.nps` é o
campo que autoriza a exibição do ponto no cartão. Sem intervalo (API antiga
ou falha do endpoint), a dashboard preserva o agregado disponível.

---

## O sinal de tempo é treinado em dados sintéticos

Nenhum corpus público de review em português tem timestamps de diálogo. O
simulador (`fraus/ingest/simulador.py`) gera conversas determinísticas com
latências calibradas por literatura de live chat.

**E isso teve uma consequência medida, não hipotética.** As features de latência
não têm teto, e o corpus nunca passou de minutos (medianas de 5/30/200 s). Numa
conversa com **3 horas** de espera, medida em 08/09/2026 contra a API real, com
o fusor da época (em segundos crus):

```
latencia_primeira_resposta_s   -85,405
duracao_total_s                -35,759
latencia_mediana_s             -20,569
latencia_p90_s                 -12,326
texto_prob_satisfeito_media     +4,574   ← o texto inteiro
```

O tempo pesa **20× o texto**, e a conversa sai em `4,4e-24`. O peso *por
unidade* continua pequeno (0,12–0,16); o que explode é o **z-score** que entra
no `StandardScaler`.

**Conserto em 15/09/2026:** as quatro features de espera entram no vetor em
`log1p` (`FEATURES_EM_LOG`, em `fraus/fusor.py`), o fusor foi retreinado nessa
escala e `Fusor.carregar` recusa artefato treinado em segundos crus. A
winsorização no p99 foi medida e recusada: fazia 3 h pesarem o mesmo que
10 min. Com `log1p` o relógio ainda pesa mais quanto maior a espera, mas cada
vez mais devagar — 3 h pesam 2,1× o texto, não mais 20× (medições em
[Treinamento](treinamento.md)). O que continua valendo é a origem sintética do
sinal: espera muito acima do treino segue fora da distribuição, e
[`GET /saude/deriva`](referencia/diagnostico.md) torna o caso **visível** (com o
fusor em segundos crus, essa conversa dava `|z| = 124,9` em
`latencia_mediana_s`, contra um limiar de 4).

---

## A cabeça de ironia é pouco confiável

Ela reporta acurácia `1.0` no corpus gerado e erra **6 em 10** falas sinceras de
atendimento, com 0,999 de confiança — vazamento de marcador de discurso no
gerador, já corrigido no gerador e pendente de retreino.

**O vazamento não chega mais à nota**, porque a ironia saiu do vetor em
04/09/2026 por um motivo diferente e mais grave (ver
[Arquitetura](arquitetura.md)). Ela continua sendo exibida por mensagem, com a
ressalva colada ao número.

---

## Desprezo não é uma classe treinada

Nenhum corpus em português a anota. Ela é derivada da díade raiva + nojo
(Plutchik, 1980) pela **média geométrica** — que exige as *duas* emoções juntas,
enquanto a média aritmética daria meio ponto para raiva pura sem nojo nenhum, o
que é raiva, não desprezo.

---

## Nenhuma feature agregada reverte uma probabilidade saturada

A frase canônica — *"que atendimento maravilhoso, só esperei 3 horas"* — sai
promotora sempre que o relógio não a contradiz.

`incongruencia_situacao_negativa` foi criada para alcançá-la e tem peso
**−0,193**; ela não vence os **+2,78** de `texto_prob_satisfeito_media` quando o
BERTimbau lê a frase como elogio sincero.

Por isso a **contestação** (08/09/2026) **marca em vez de corrigir**: quando
`score > 95` e `latencia_mediana_s > 180`, a tela avisa — e o atendimento
**continua contando no NPS**, com teste provando isso. Tirá-lo do agregado
esvaziaria o indicador em silêncio se o limiar estivesse mal calibrado.

O limiar de score em 95 é o único número do projeto **sem procedência**, e está
declarado assim no código e na spec. O de tempo vem de IJHCI 2025.

---

## A explicação é do modelo, não do cliente

O "por que esta nota" desmonta o que o **fusor** fez, e isso tem limites que a
tela não deve esconder:

- **O efeito por família não soma a nota.** A soma exata mora no eixo do logit
  (intercepto + contribuições = log da razão entre classes); o score é uma
  projeção não linear desses logits. Os pontos por família são uma leitura
  aproximada, e a tela os trata como tal.
- **Contribuição é associação, não causa.** Um peso alto diz o que o modelo
  aprendeu a associar ao rótulo, não o que faria o cliente mudar de opinião.
- **"Faixa de treino" quer dizer `|z| ≤ 4`** sobre média e desvio do scaler
  (o mesmo limiar de `fraus/deriva.py`). O artefato não guarda mínimo nem
  máximo, então o contrafactual de espera recusa o que sai dessa faixa.
- **O sinal de tempo é sintético**, e por isso o contrafactual de espera herda a
  limitação da seção acima: é uma hipótese sobre o modelo, não uma previsão.
- **Os drivers são uma amostra com semente** (padrão 50 conversas, teto 200),
  cada uma custando uma passagem de modelo. O intervalo vem de bootstrap sobre
  a amostra e mede incerteza amostral, não erro do modelo. O teto limita só o
  número de conversas, não de mensagens: uma amostra de conversas longas numa
  instância fria pode se aproximar do tempo limite do proxy.

---

## O que não dá para consertar sem corpus de atendimento real

Duas coisas ficam condicionadas ao mesmo recurso que não existe publicamente em
português — um corpus de **diálogo de atendimento** rotulado:

1. **retreinar a cabeça de ironia** em domínio certo;
2. **a interação tempo × texto** como feature. Ela nasceria com o peso
   invertido: o texto vem do B2W, a latência sai de distribuição por rótulo, e
   satisfeito-e-lento está rotulado *satisfeito* por construção. Isso é leitura
   do corpus, não experimento.
