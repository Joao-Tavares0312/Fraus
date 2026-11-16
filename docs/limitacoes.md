# Limitações conhecidas

Esta página existe porque um sistema que estima satisfação **precisa** declarar
onde erra. As ressalvas da interface não substituem este inventário: nem toda
limitação tem um indicador próprio em tela.

Desde **16/11/2026 os modelos estão congelados** por decisão do projeto:
retreino, calibração, promoção e troca de pesos/arquitetura ficam fora da fila
ativa. Isso não elimina as limitações nem valida os artefatos existentes.

A régua de `fraus/motor.py` combina a assinatura do fusor e
`FORMULAS_DE_CORTESIA`; não inclui identidade dos checkpoints das cabeças nem
backend. Comparar réguas ajuda a detectar mudanças cobertas por essa
assinatura, mas não comprova que todo o pipeline permaneceu igual. A
compatibilidade do artefato conformal com a régua herda esse limite.

## Generalização e proveniência — atualização de 27/10/2026

O [relatório público de generalização](generalizacao.md) centraliza protocolo,
baselines locais, resultados dos nove treinos e ablações do fusor. As medições
datadas nas demais seções abaixo são **históricas**: não identificam
automaticamente os pesos publicados hoje. Uma resposta de saúde da API não
demonstra inferência real nem proveniência do checkpoint.

Há dependência por produto na antiga divisão posicional do fusor reconstruída
em 26/10. Faltam curvas e manifestos históricos suficientes para diagnosticar
sobreajuste dos pesos antigos/publicados: esse diagnóstico permanece
**inconclusivo**, não “sem sobreajuste”.

A reprodução de 26–27/10 concluiu as três sementes por cabeça em T4 e o novo
experimento sintético do fusor. Suas curvas comparáveis mostram treino
melhorando enquanto a perda de validação piora persistentemente em fases
explicitadas no relatório: **evidência de sobreajuste desses candidatos novos**,
sem identificar uma causa única ou invalidar a seleção isolada por validação.
Nenhum candidato foi promovido; esta medição não identifica o checkpoint em produção.

ConsumerBR e XED já foram consultados e não são testes virgens. A amostra
ConsumerBR não tem colisões textuais normalizadas com o treino B2W novo;
XED tem seis com o treino GoEmotions novo, duas com conflito de rótulo.
No XED, F1-macro nas sete classes não é o mesmo indicador que F1-macro nas
seis presentes. Queda fora de domínio, isoladamente, não diagnostica
sobreajuste. A régua pequena de ironia tampouco valida atendimento real.

O manifesto do fusor novo isola produtos B2W. A prova complementar confirma
zero colisões textuais normalizadas da validação/teste B2W com os treinos
reais das três cabeças novas, sem sobrescrever o relatório conservador original.
Essa independência observável não cobre paráfrases, traduções ou proveniência
ausente; grupos entre fontes não são comparáveis. Nada disso comprova
retroativamente a independência das cabeças antigas, nem valida acurácia em
suporte real: as conversas e os tempos do experimento do fusor são sintéticos.


## Limitações operacionais do deploy gratuito

Os registros de publicação de setembro de 2026 descrevem uma API ONNX na
Vercel com Large Functions. O pacote registrado em 30/09 tinha cerca de
1,95 GB (1,46 GB em 17/09); um primeiro `/saude` após esfriar foi registrado
em 10,8 s. São medições históricas, não um orçamento atual de latência nem
uma conferência do provedor em 16/11/2026.

O contrato atual (`vercel.json`) separa uma função leve, sem ONNX, da função
do motor: limites de execução de 60 e 300 segundos, respectivamente. Rotas de
leitura do banco não precisam carregar as três cabeças; análise, atribuição e
outras rotas que exigem inferência seguem para a função do motor. A separação
no código não é uma medição nova do ambiente publicado.

Cada instância da função do motor tem seu próprio motor. O código dispara
aquecimento em segundo plano no boot dessa função e nas sondas de saúde; há
workflow com agenda de
cinco minutos (`.github/workflows/api-aquecer.yml`). Isso não comprova que a
agenda esteja ativa no provedor, nem elimina o cold start: a sonda e o usuário
podem cair em instâncias diferentes. Os registros antigos de memória e tempo
não dimensionam automaticamente um novo ambiente.

Vercel Hobby, Supabase Free e Oracle Object Storage gratuito oferecem cotas,
não SLA. Ao ultrapassá-las, a aplicação pode ser limitada ou pausada. O estado
fica no banco; o armazenamento de modelos participa do build, não da
inferência. A configuração externa, os backups e a recuperação do banco não
foram revalidados nesta revisão.

O backend já expõe `Server-Timing` e logs estruturados de latência
(`fraus/api/observabilidade.py`), mas não há coleta de Web Vitals de campo no
front nem orçamento atual de bytes/CLS da landing. Instrumentação de servidor
não prova experiência rápida no navegador.

Essas limitações são operacionais. Elas não alteram as limitações científicas
abaixo e não autorizam apresentar a estimativa como NPS declarado.

---

## O NPS é inferido, não perguntado

Toda exibição carrega a etiqueta de estimativa e o sublinhado pontilhado de
proveniência. Apresentar como NPS declarado seria falso.

**O intervalo de confiança cobre a incerteza AMOSTRAL, não a do modelo.** Ele
responde "quantas conversas sustentam este número"; ele **não** responde "o
quanto o modelo pode estar errado". Os executores leem a temperatura de
`fraus_receita.json` **quando o checkpoint a fornece**; sem esse arquivo, usam
temperatura 1. Isso não comprova que os pesos em uso estejam calibrados, e não
entra neste intervalo. Um IC apresentado como se cobrisse o erro do modelo é
pior que não ter IC nenhum.

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
A abstenção só marca: a conversa **continua no NPS e no CSAT**. Na árvore
consultada em 16/11/2026, `fraus/dados/conformal_fusor.json` **não existe**.
Sem artefato compatível com a régua vigente, as rotas respondem 503; um detalhe
pontuado com régua antiga pode responder 409. Não há conjunto vazio fingindo
confiança. Cobertura e acurácia por abstenção continuam **não verificadas**;
a ausência de fusor `log1p` foi o bloqueio registrado em 14/10/2026, não uma
inspeção do ambiente atual. No detalhe, a deriva pode adicionar um critério de
abstenção, mas acima de 40 mensagens do cliente ela não é avaliada: a resposta
declara esse limite. O agregado considera só conjunto vazio ou múltiplo, sem
passagem pelo modelo. O limiar `|z| > 4` pode disparar por uma única feature
rara; sua frequência em tráfego real não foi medida.

Há medições sintéticas de ECE top-1 dos candidatos de outubro e de 13/11,
descritas em [Generalização](generalizacao.md). Elas não são a validação
de cobertura ou da abstenção conformal em atendimento real.

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
humana nunca são lidos para julgar, porque o Fraus não pontua atendentes.
Os casos construídos **verificam a implementação, não medem qualidade**;
precisão e recall em dado real: **não verificado — fonte da amostra anotada
pendente**.

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

Desde a correção de 13/11/2026, as três latências de uma conversa sem
resposta são ausentes (`None`), não zero. O fusor usa a média do treino
(z = 0) para essas ausências, sem retreino; não é uma penalização aprendida
por falta de resposta. Scores já gravados não são recalculados por essa
mudança (`fraus/sinais/tempo.py`, `fraus/fusor.py`).

---

## A cabeça de ironia é pouco confiável

As medições antigas desta página se referem a um checkpoint treinado em corpus
gerado, que reportava acurácia `1.0` e falhava em frases de atendimento com
alta confiança. O atalho de marcador de discurso foi observado nesse contexto;
ele **não diagnostica por si só a cabeça local ou publicada hoje**.

A campanha MultiPICo deixou de ser apenas proposta: desde 13/11/2026, o
registro de publicação identifica essa cabeça no servidor (F1-macro 0,660 no
teste do corpus, contra 0,490 da anterior). O teste é interno ao MultiPICo,
não validação em atendimento real; ver
[Novidades de 13/11/2026](novidades-2026-11-13.md).
A ironia continua fora do vetor desde 04/09/2026 por outro motivo
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

O registro histórico da frase canônica — *"que atendimento maravilhoso, só
esperei 3 horas"* — mostrou uma saída promotora quando o relógio não a
contradizia. Não é uma previsão universal para qualquer checkpoint.

Na medição histórica, `incongruencia_situacao_negativa` tinha peso **−0,193**
e não vencia os **+2,78** de `texto_prob_satisfeito_media`. Os coeficientes
dependem do artefato; não foram reavaliados nesta revisão.

Por isso a **contestação** (08/09/2026) **marca em vez de corrigir**: quando
`score > 95` e `latencia_mediana_s > 180`, a tela avisa — e o atendimento
**continua contando no NPS**, com teste provando isso. Tirá-lo do agregado
esvaziaria o indicador em silêncio se o limiar estivesse mal calibrado.

O limiar de score em 95 não tem procedência empírica declarada; não é o único
limiar heurístico do projeto (ver E5 e `fraus/explicacao.py`). O de tempo é
atribuído à literatura IJHCI 2025.

---

## A explicação é do modelo, não do cliente

O "por que esta nota" desmonta o que o **fusor** fez, e isso tem limites que a
tela não deve esconder:

- **O efeito por família não soma a nota.** A soma exata mora no eixo do logit
  (intercepto + contribuições = log da razão entre classes); o score é uma
  projeção não linear desses logits. Os pontos por família são um recálculo
  exato com a família na média do treino, mas **não aditivo**; não são parcelas
  que, somadas, reproduzem a nota.
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

1. **avaliar ironia no domínio certo**; retreino seria pesquisa futura, fora da
   fila ativa por decisão de 16/11/2026;
2. **a interação tempo × texto** como feature. Ela nasceria com o peso
   invertido: o texto vem do B2W, a latência sai de distribuição por rótulo, e
   satisfeito-e-lento está rotulado *satisfeito* por construção. Isso é leitura
   do corpus, não experimento.

## Feedback observado não é validação completa

O backend aceita `feedback_declarado` binário (`-1`/`1`) e comentário,
sem mover o score. `GET /indicadores` informa o total com voto **e score** e a
concordância com as categorias inferidas (positivo com promotor, negativo com
detrator; neutro não conta como concordante). Esse cruzamento não mede
causalidade nem transforma resolução declarada em NPS perguntado.

O TARS ainda não envia esse voto, e a dashboard não apresenta o agregado de
concordância. A comparação de nota declarada 0–10 com nota inferida (E3) não
foi iniciada; não deve ser confundida com o contrato binário existente.
