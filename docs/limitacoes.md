# Limitações conhecidas

Esta página existe porque um sistema que estima satisfação **precisa** declarar
onde erra. Nada aqui é segredo, e nada aqui está escondido na tela: cada item
tem contrapartida visível na interface.

## Generalização e proveniência — atualização de 26/10/2026

O [relatório público de generalização](generalizacao.md) centraliza protocolo,
baselines locais e limites de independência. As medições datadas abaixo são
**históricas**: não identificam automaticamente os pesos publicados hoje.
Uma resposta de saúde da API não demonstra inferência real nem proveniência
do checkpoint.

Há dependência por produto na antiga divisão posicional do fusor reconstruída
agora, mas faltam curvas e manifestos antigos suficientes para diagnosticar
overfitting dos pesos atuais. A campanha de três sementes por cabeça e o novo
experimento do fusor estão **pendentes de autenticação Colab**; o diagnóstico
atual é **inconclusivo**, não “sem overfitting”.

ConsumerBR e XED já foram consultados como benchmarks de transferência e não
são testes virgens. No XED, F1-macro nas sete classes não é o mesmo indicador
que F1-macro apenas nas classes presentes. A cabeça de ironia também tem
baselines locais recentes, sem que isso converta a régua pequena em avaliação
independente de atendimentos. Ver os resultados e respectivas condições em
[Generalização](generalizacao.md), sem misturá-los às tabelas históricas.

O novo manifesto/caches do fusor reduzem uma fonte de dependência, mas não
comprovam retroativamente quais exemplos treinaram cabeças antigas. Sem essa
cadeia, a independência do sistema completo não é verificável. Mesmo um teste
agrupado correto de conversas sintéticas não valida acurácia em suporte real.


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
quanto o modelo pode estar errado". A temperatura gravada no artefato
(`fraus_receita.json`, desde 19/10/2026) calibra a confiança de cada cabeça,
mas não entra neste intervalo. Um IC apresentado como se cobrisse o erro do modelo é pior que não ter
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

### Calibração e conjunto conformal do fusor (E2)

Nada recalibra em runtime e
o score gravado não muda. O que existe agora é um *conjunto conformal*
(Mondrian, por classe, sobre o score já gravado) e um marcador de abstenção
("leitura sem confiança suficiente"), mais os instrumentos que medem a
calibração (`fraus/calibracao.py`, `scripts/medir_calibracao.py`,
`scripts/medir_abstencao.py`). A garantia é só esta: cobertura ≥ alvo **por
classe**, sob permutabilidade com o conjunto de calibração. Ela **não vale**
sob mudança de distribuição — e atendimento real é mudança de distribuição em
relação ao holdout sintético do B2W —, e o sinal de tempo do fusor é sintético.
A abstenção só marca: a conversa **continua no NPS e no CSAT**. Sem artefato
calibrado para a régua vigente as rotas respondem 503, nunca um conjunto vazio
fingindo confiança. Os números de ECE, cobertura e acurácia por abstenção ainda
**não foram medidos**: não verificado — fusor log1p ausente na máquina de
desenvolvimento em 14/10/2026. Por conversa, basta uma feature rara longe da
média de treino (|z| > 4; por exemplo, features binárias com prevalência de
treino abaixo de ~6%, ou contagens de turnos acima da faixa do simulador) para
disparar o critério "deriva"; em tráfego real, portanto, ele deve disparar
com frequência — honesto por construção, não medido.

### Sinalizadores por regra (E5)

Cinco regras de superfície, derivadas na
leitura e sem gravar nada: `loop_do_bot`, `cliente_repete`,
`pedido_de_humano_ignorado`, `escalada_tardia` e `abandono`. Três limitações
valem para todas. (1) São heurísticas: resposta legitimamente repetida
("posso ajudar em algo mais?") dispara `loop_do_bot` sem ser defeito. (2) O
léxico de pedido de humano é fechado (`atendente`, `humano`, `humana`,
`pessoa`, `operador`, `falar com alguém`) e casa por palavra inteira: pedido em
outras palavras passa em branco, e o plural ("atendentes", "pessoas",
"humanos") **não** casa (falso negativo declarado); já "a pessoa que me
atendeu" conta como pedido (falso positivo declarado). (3) Os limiares (0,85,
0,7, "mais de 2" respostas, N = 3) são **sem procedência** e não foram medidos em dado real; o `detalhe` de cada
achado diz isso. No `abandono`, o falso positivo comum é a despedida do bot
depois que o cliente já resolveu e saiu. Nenhuma regra lê o texto nem o relógio
da fala do atendente: só a presença e a posição da primeira fala humana contam, e o
autor da última mensagem (usado pelo `abandono`); o texto e o relógio da fala
humana nunca são lidos para julgar, porque o Fraus não pontua atendentes. Os casos construídos (15) **verificam a
implementação, não medem qualidade**; precisão e recall em dado real: **não
verificado — fonte da amostra anotada pendente**.

### Impacto por tema e deterioração (E6)

O impacto de um tema é a diferença
entre o NPS inferido das conversas do tema e o do resto do recorte, com IC por
bootstrap: é **associação, não causa**. Exige no mínimo 30 conversas com sinal
nos dois lados; abaixo disso o impacto é nulo, nunca 0. O tema vem de TF-IDF com
DBSCAN e é instável com pouco dado. A deterioração acha, numa conversa
**encerrada**, o início da deterioração (`indice_virada`): a mensagem a partir da qual a estimativa por prefixo fica detratora
e não volta. É **retrospectiva e em lote, nunca alerta ao vivo**. O lead time em
dado sintético não prevê o de produção, e o simulador não gera trajetória (cada
conversa sorteia as falas do cliente de um só rótulo), então a medição feita nele
é artefato do gerador. Não há margem em torno do limiar: uma estimativa que oscila perto da fronteira de detrator marca o início com uma variação pequena (na demonstração, de cerca de 67 para 61 pontos). O início da deterioração não aumenta o recall sobre o score final; ela
só acrescenta lead time. Medição com o fusor real: **não verificado — fusor
log1p ausente em 14/10/2026** (`scripts/medir_deterioracao.py` sai com código 2
e diz isso).

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

As medições antigas desta página se referem a um checkpoint treinado em corpus
gerado, que reportava acurácia `1.0` e falhava em frases de atendimento com
alta confiança. O atalho de marcador de discurso foi observado nesse contexto;
ele **não diagnostica por si só a cabeça local ou publicada hoje**.

Os baselines de 26/10/2026 e a campanha diagnóstica proposta com MultiPICo
estão em [Generalização](generalizacao.md); campanha proposta não é retreino
executado. A ironia continua fora do vetor desde 04/09/2026 por outro motivo
medido historicamente (ver [Arquitetura](arquitetura.md)), e é exibida por
mensagem, com ressalva. Não há promessa de que detecte ironia corretamente em
atendimentos reais.

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

O projeto não dispõe de corpus novo de **diálogo de atendimento** rotulado e
com proveniência suficiente para validar estas duas frentes:

1. **retreinar a cabeça de ironia** em domínio certo;
2. **a interação tempo × texto** como feature. Ela nasceria com o peso
   invertido: o texto vem do B2W, a latência sai de distribuição por rótulo, e
   satisfeito-e-lento está rotulado *satisfeito* por construção. Isso é leitura
   do corpus, não experimento.
