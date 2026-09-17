# Limitações conhecidas

Esta página existe porque um sistema que estima satisfação **precisa** declarar
onde erra. Nada aqui é segredo, e nada aqui está escondido na tela: cada item
tem contrapartida visível na interface.

## Limitações operacionais do deploy gratuito

A hospedagem da API deixou de ser pendência em 17/09/2026, mas “publicada” não
significa “sem limites”. A função ONNX tem cerca de 1,46 GB e usa Large
Functions na Vercel. Depois de esfriar, o primeiro `/saude` observado levou
10,8 s; requisições seguintes foram rápidas, mas não há garantia de latência.

Vercel Hobby, Supabase Free e Oracle Object Storage gratuito oferecem cotas,
não SLA. Ao ultrapassá-las, a aplicação pode ser limitada ou pausada. O estado
fica no Supabase; o Oracle participa do build, não da inferência. Uma restauração
do projeto pode alterar a URI do pooler, e o transaction pooler precisa usar a
porta indicada no painel (6543 no deploy atual).

Essas limitações são operacionais. Elas não alteram as limitações científicas
abaixo e não autorizam apresentar a estimativa como NPS declarado. Detalhes em
[Deploy gratuito na Vercel](deploy-vercel.md).

---

## O NPS é inferido, não perguntado

Toda exibição carrega a etiqueta de estimativa e o sublinhado pontilhado de
proveniência. Apresentar como NPS declarado seria falso.

**O intervalo de confiança cobre a incerteza AMOSTRAL, não a do modelo.** Ele
responde "quantas conversas sustentam este número"; ele **não** responde "o
quanto o modelo pode estar errado" — isso exigiria calibração, que ainda não
existe. Um IC apresentado como se cobrisse o erro do modelo é pior que não ter
IC nenhum, e por isso a ressalva está impressa junto do número, não só aqui.

Abaixo de **30 atendimentos com sinal** a tela não mostra ponto estimado: mostra
pausa e o `n`.

---

## O sinal de tempo é treinado em dados sintéticos

Nenhum corpus público de review em português tem timestamps de diálogo. O
simulador (`fraus/ingest/simulador.py`) gera conversas determinísticas com
latências calibradas por literatura de live chat.

**E isso tem uma consequência medida, não hipotética.** As features de latência
não têm teto, e o corpus nunca passou de minutos (medianas de 5/30/200 s). Numa
conversa com **3 horas** de espera, medida em 08/09/2026 contra a API real:

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

O conserto de verdade — `log1p` ou winsorização antes do scaler — exige
retreino. Enquanto ele não vem, [`GET /saude/deriva`](referencia/diagnostico.md)
torna o caso **visível**: contra o fusor real, essa conversa dá `|z| = 124,9`
em `latencia_mediana_s`, contra um limiar de 4.

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

## O que não dá para consertar sem corpus de atendimento real

Duas coisas ficam condicionadas ao mesmo recurso que não existe publicamente em
português — um corpus de **diálogo de atendimento** rotulado:

1. **retreinar a cabeça de ironia** em domínio certo;
2. **a interação tempo × texto** como feature. Ela nasceria com o peso
   invertido: o texto vem do B2W, a latência sai de distribuição por rótulo, e
   satisfeito-e-lento está rotulado *satisfeito* por construção. Isso é leitura
   do corpus, não experimento.
