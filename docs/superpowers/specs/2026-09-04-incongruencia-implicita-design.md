# Incongruência implícita — desenho para a frase que as 5 features atuais não pegam

Data: 2026-09-04
Status: proposta, sem implementação

## O problema

`fraus/sinais/incongruencia.py` tem cinco features (`incongruencia_polaridade`,
`incongruencia_emoji_texto`, `incongruencia_marcador_contraste`,
`incongruencia_hiperbole`, `incongruencia_aspas_ironicas`) documentadas em
`docs/superpowers/specs/2026-09-03-incongruencia-ironia-design.md`. No fusor
treinado com 40 features, as cinco aprenderam peso negativo no eixo
satisfeito-menos-insatisfeito (ver `docs/treinamento.md`, seção "Retreino do
fusor após as features de incongruência"):

| feature | peso |
|---|---|
| `incongruencia_emoji_texto` | −0,95 |
| `incongruencia_hiperbole` | −0,65 |
| `incongruencia_marcador_contraste` | −0,38 |
| `incongruencia_polaridade` | −0,37 |
| `incongruencia_aspas_ironicas` | −0,15 |

Direção certa: mais incongruência empurra para insatisfeito, como a literatura
prevê. Mas nenhuma delas dispara na frase que o próprio módulo usa como
exemplo de manual:

```
"que atendimento maravilhoso, so esperei 3 horas"

anotar_texto() acha:              [('maravilhoso', +1, False)]
incongruencia_polaridade          0.0   -- só há UM termo com polaridade; F1 precisa de dois lados
incongruencia_emoji_texto         0.0   -- não há emoji na frase
incongruencia_marcador_contraste  0.0   -- não há "mas"/"só que"/etc.
incongruencia_hiperbole           0.0   -- "maravilhoso" não está intensificado
incongruencia_aspas_ironicas      0.0   -- não há aspas
```

A causa é estrutural, não um bug de uma feature isolada: o SentiLex-PT02 só
acha `maravilhoso` (+1). "só esperei 3 horas" é negativo por **pragmática**
— conhecimento de mundo sobre atendimento —, não por léxico. Nenhuma palavra
do trecho tem polaridade no SentiLex, e as cinco features atuais são todas
funções de `anotar_texto`/`emojis_com_posicao`: sem um segundo termo polar (ou
emoji, ou marcador, ou aspas) para contrastar, todas ficam mudas.

Isso é exatamente a distinção que Joshi, Sharma & Bhattacharyya fazem entre
incongruência **explícita** (o que o módulo já cobre) e **implícita** (o que
falta) — ver a seção de pesquisa abaixo.

## Pesquisa

### Riloff et al., EMNLP 2013 — "Sarcasm as Contrast between a Positive Sentiment and Negative Situation"
<https://aclanthology.org/D13-1066/>

É a referência que já fundamenta `incongruencia_polaridade` (F1) na bibliografia
de 03/09, mas o que ela contribui aqui é o **algoritmo de extração de frases de
situação negativa**, não o contraste léxico simples.

**A ideia central.** Sarcasmo em tweet costuma ter a forma "sentimento positivo
+ situação negativa" — "adoro ficar em espera 40 minutos", "amo quando cancelam
meu voo". A situação negativa raramente carrega palavra de polaridade
(`espera`, `cancelam meu voo` não estão em nenhum lexicon de sentimento); o que
a marca como negativa é conhecimento de mundo sobre o que é desagradável
viver.

**O algoritmo de bootstrapping**, tal como descrito nos resumos consultados
(a versão completa do PDF não pôde ser extraída por esta pesquisa — ver nota
de proveniência abaixo):
1. Parte de tweets marcados `#sarcasm` e de **uma única semente**: o verbo de
   sentimento positivo "love".
2. Assume que, num tweet sarcástico, a frase verbal de sentimento positivo
   aparece à ESQUERDA e a frase de situação negativa aparece à DIREITA dela
   (ordem, não coocorrência livre).
3. Itera nas duas direções: de tweets com "love" já conhecido, extrai os
   n-gramas/frases verbais à direita como candidatas a "situação negativa"; de
   tweets com uma situação negativa já aprendida, extrai a frase verbal à
   esquerda como candidata a "sentimento positivo" — o mesmo mecanismo de
   bootstrapping mútuo de Riloff & Jones (1999), que a própria autora revisita
   em retrospectiva (Riloff, "A Retrospective on Mutual Bootstrapping", AI
   Magazine 2018, <https://onlinelibrary.wiley.com/doi/abs/10.1609/aimag.v39i1.2778>).
4. O que é extraído: sintagmas verbais (frase verbal de sentimento positivo) e
   complementos verbais/predicativos (a situação negativa) — não n-gramas
   soltos, unidades com papel sintático.
5. Resultado: um léxico de frases de "situação negativa" aprendido do corpus,
   sem anotação manual de cada frase — só a semente e a suposição estrutural
   de ordem.

**Ganho medido**: a configuração "Contrast (+VPs, −Situations), Ordered"
(contraste entre frase verbal positiva e situação negativa, respeitando a
ordem) obteve a maior precisão entre as variantes testadas (0,70), com F1 de
0,51 no melhor ajuste — números levantados via busca dirigida (resumo de
terceiros), não confirmados linha a linha no PDF original; citar com essa
ressalva se usados no relatório.

**O que isso significa para o Fraus**: o método é feito para corpus grande de
mídia social livre (Twitter), sem anotação prévia — exatamente o recurso que
o projeto NÃO tem para atendimento em português. Rodar bootstrapping aqui
exigiria (a) um corpus de conversas de atendimento marcadas como
irônicas/sarcásticas em volume suficiente para convergir, e (b) validação de
que a suposição de ordem ("positivo à esquerda, negativo à direita") vale em
português e em fala de cliente, não só em tweet em inglês. Nenhuma das duas
condições está disponível — mesmo problema que já bloqueou o notebook 04
(corpus IDPT sem download aberto, resolvido com corpus sintético declarado
como limitação).

### Joshi, Sharma & Bhattacharyya, ACL 2015 — "Harnessing Context Incongruity for Sarcasm Detection"
<https://aclanthology.org/P15-2124/>

Já citada na bibliografia de 03/09 como base de F1. O que ela contribui além
disso: a **operacionalização de incongruência implícita**. Segundo os
resumos consultados, os autores extraem features de "phrases corresponding to
implicit incongruity" — passagens onde sentimento é expresso SEM palavra de
sentimento, e reportam ganho de F1 combinando explícito + implícito acima do
uso isolado da incongruência explícita (a fonte primária que já embasa F1 no
projeto). O mecanismo de extração dessas frases implícitas, segundo a
literatura secundária consultada, é o mesmo bootstrapping de Riloff — Joshi
2015 consome o léxico de "situação negativa" de Riloff 2013 como uma das
fontes de feature, e soma marcadores implícitos a marcadores explícitos
(interjeição, pontuação) num único classificador.

Ou seja: as duas referências não são independentes. Riloff 2013 resolve "como
aprender o que é situação negativa"; Joshi 2015 mostra que ligar esse
conhecimento (explícito + implícito) supera qualquer um sozinho. Para o Fraus,
a peça que falta é a mesma nas duas: **uma lista (aprendida ou curada) de
frases/padrões de situação negativa**.

### Busca por alternativas em português / sem corpus anotado grande

Pesquisa dirigida (WebSearch) por léxico de situação negativa em português ou
recurso equivalente para atendimento não encontrou nenhum recurso acadêmico
citável — os resultados foram só páginas de blog de CRM/atendimento com
"frases prontas" (ver lista abaixo), não léxicos anotados nem corpora. Isso
confirma o diagnóstico do projeto sobre outros sinais (SentiLex é o único
léxico de julgamento social em PT com procedência acadêmica; não existe
equivalente para "situação negativa de atendimento"):

- <https://www.atendesimples.com/blog/7-frases-que-nao-devem-ser-ditas-em-um-atendimento>
- <https://digisac.com.br/blog/30-frases-prontas-atendimentos-dificeis>
- <https://blog.zapsign.com.br/frases-prontas-para-atendimento-ao-cliente/>
- <https://www.zendesk.com.br/blog/frases-prontas-atendimento-cliente/>

Nenhuma dessas é lexicon nem dataset — são conteúdo de marketing sobre como o
ATENDENTE deve falar, não sobre o que o CLIENTE reclama. Não servem como fonte
citável de "situação negativa"; confirmam que não há recurso pronto para
adaptar, só a opção de curar à mão ou extrair por bootstrapping de um corpus
que o projeto teria de montar primeiro.

## Avaliação honesta: bootstrapping automático vs. lista curada

**Bootstrapping (replicar Riloff 2013 em PT-BR/atendimento).**
Prós: procedência "acadêmica" — o método tem paper, a técnica é replicável, a
lista cresceria além do que uma pessoa lembra de escrever.
Contras, decisivos aqui:
- Precisa de um corpus de atendimento em português marcado como
  irônico/sarcástico em volume — não existe (mesmo buraco do notebook 04,
  que já foi resolvido com corpus sintético declarado, não com bootstrapping).
- Bootstrapping sem corpus nativo forçaria (a) traduzir um corpus de sarcasmo
  em inglês, repetindo o vazamento de procedência que `docs/treinamento.md`
  já registra como descartado para o classificador de ironia
  ("IroSvA / SemEval-2018 traduzidos — desaconselhado: tradução automática
  reintroduz o vazamento de procedência que já custou o primeiro fusor"), ou
  (b) rodar sobre o próprio B2W-Reviews01 sem marcação de ironia, o que não é
  o regime que o algoritmo pressupõe (ele precisa de exemplos POSITIVOS
  confirmados de sarcasmo para arrancar do zero com a semente).
- Resultado de um bootstrapping malfeito é **ruído silencioso**: frases
  aprendidas erradas entram no vetor como se tivessem procedência, e ninguém
  audita cada uma. A banca perguntaria "de onde saiu esta frase" e a resposta
  seria "de um algoritmo, não verificamos cada item" — pior postura que uma
  lista pequena e declaradamente manual.

**Lista curada de frases/padrões de situação negativa de atendimento.**
Prós:
- O domínio de atendimento tem um catálogo finito e conhecido de situações
  negativas — a literatura de CX (Customer Experience) e os próprios blogs
  encontrados na pesquisa (ainda que não citáveis como léxico) apontam
  sempre os mesmos temas: espera longa, repetição de informação,
  transferência, cobrança indevida, não entrega, promessa não cumprida,
  reabertura de chamado. Não é uma lista arbitrária — é o mesmo catálogo que
  qualquer manual de atendimento cobre, e o projeto já tem uma lista curada
  do mesmo tipo (`fraus/dados/palavroes_ptbr.csv`, "curadoria própria... a
  cobertura e a gradação vieram de julgamento próprio", como
  `docs/treinamento.md` já declara sobre palavrão).
- Procedência é honesta e barata de defender na banca: "list curada por nós,
  com critério X, tamanho Y, limitação declarada" — o mesmo formato que já
  existe para `MARCADORES_CONTRASTE` e `INTENSIFICADORES_*` em
  `incongruencia.py`, ambas listas curadas pequenas "de propósito" (o próprio
  docstring do módulo já justifica: "marcador duvidoso marca contraste que
  não existe, e ruído correlacionado com fala normal é pior que feature
  ausente").
- Falso positivo é mais fácil de auditar: uma lista de 20-40 padrões cabe
  numa revisão manual completa; um léxico de bootstrapping com centenas de
  frases não cabe.
Contras:
- Não escala sozinha — cobertura limitada ao que foi pensado, mesma
  limitação que `palavroes_ptbr.csv` já assume.
- Não tem "paper" próprio — mas o precedente do projeto (`palavroes_ptbr.csv`)
  já mostra que isso é aceitável quando declarado, e é preferível a inventar
  procedência acadêmica que a lista não tem.

**Recomendação: lista curada.** O domínio de atendimento é pequeno e
conhecido o bastante para justificar isso — ao contrário de sarcasmo em
Twitter (domínio aberto, qualquer assunto), atendimento tem um número finito
de reclamações-tipo. Bootstrapping é a ferramenta certa quando não se sabe a
priori o vocabulário do domínio; aqui se sabe. E a lista curada tem a
propriedade que a banca mais valoriza neste projeto: procedência declarada
sem fingir automação que não existe.

## Abordagens concretas

### Abordagem A — lista curada de n-gramas de situação negativa, casada por regex (RECOMENDADA)

Feature nova: `incongruencia_situacao_negativa`.

**Lógica, em pseudocódigo:**
```
SITUACOES_NEGATIVAS = (
    # espera / demora
    "esperei", "esperando", "fiquei esperando", "horas esperando",
    "demorou", "demora", "ate agora nao",
    # repeticao / transferencia
    "tive que repetir", "repeti tudo", "me transferiram", "fui transferido",
    "de novo", "outra vez",
    # promessa / entrega
    "nao chegou", "nunca chegou", "prometeram e nao", "cancelaram",
    "nao resolveu", "sem solucao", "sem resposta",
    # cobranca
    "cobraram errado", "cobranca indevida", "descontaram sem",
)
# cada item vira uma regex de fronteira de palavra, como MARCADORES_CONTRASTE

def _situacao_negativa(texto, achados):
    tem_situacao = any(regex.search(texto.lower()) for regex in _REGEX_SITUACOES)
    if not tem_situacao:
        return 0.0
    polaridades = _filtra_polaridades(achados)
    positivos = sum(1 for p in polaridades if p > 0)
    if positivos == 0:
        return 0.0   # situação negativa sem elogio léxico não é incongruência, é reclamação comum
    return 1.0   # elogio léxico presente + situação negativa presente na mesma fala
```

**Cálculo passo a passo na frase canônica:**
```
texto = "que atendimento maravilhoso, so esperei 3 horas"
achados = anotar_texto(texto)              -> [('maravilhoso', +1, False)]
_situacao_negativa:
  regex "esperei" casa em "so esperei 3 horas"   -> tem_situacao = True
  polaridades = [+1]                              -> positivos = 1
  resultado = 1.0
```
Dispara. É exatamente o caso que as cinco features atuais perdem, porque
"esperei" não é palavra polar em nenhum lexicon de sentimento — é polar por
conhecimento de mundo, que é o que a lista curada declara explicitamente
em vez de fingir que vem do SentiLex.

**De onde vêm os dados:** lista curada por nós, ~20-40 padrões, agrupados por
tema (espera, repetição/transferência, entrega/promessa, cobrança) —
inspirados no catálogo recorrente que aparece nos próprios materiais de CX
levantados na pesquisa (não citáveis como léxico, mas confirmam que o
catálogo de queixas de atendimento é conhecido e pequeno) e no bom senso do
domínio, do mesmo jeito que `MARCADORES_CONTRASTE` e `palavroes_ptbr.csv` já
são.

**Falsos positivos previsíveis:**
- "esperei" numa frase sem elogio nenhum: reclamação direta, não ironia —
  coberto pelo `if positivos == 0: return 0.0`.
- "esperei pouco" ou "não esperei nada" (negação/atenuação): a lista de
  n-gramas simples não distingue "esperei 3 horas" de "não esperei nem um
  minuto" — os dois casam "esperei". Mitigação: aplicar o mesmo escopo de
  negação de `lexico.py` (`anotar_texto` já resolve negação para termos do
  SentiLex; o padrão de situação negativa precisaria de checagem similar —
  não negar dentro de 3 tokens antes do match) antes de aceitar o padrão como
  disparado.
- Elogio genuíno sobre a RESOLUÇÃO de uma situação inicialmente ruim ("o
  atendimento foi ótimo, resolveram rápido mesmo eu tendo esperado antes")
  não é ironia — é elogio real após frustração real. A lista de n-gramas não
  distingue isso de ironia pura. É limitação aceita, não resolvida por regra:
  o peso aprendido pelo fusor (não uma regra de decisão binária) é quem
  pondera esse ruído contra as outras 39 features, do mesmo jeito que
  `incongruencia_hiperbole` já convive com "otimo demais" ser tanto ironia
  quanto satisfação genuína (ver docstring de `_hiperbole`).

### Abordagem B — extensão do bootstrapping de Riloff sobre o B2W-Reviews01

Rodar uma versão adaptada do algoritmo (semente "adorei"/"amei", extrair
complementos à direita) sobre o corpus de treino já disponível
(B2W-Reviews01), usando resenhas 1-2 estrelas como proxy de "situação
negativa confirmada" para aprender o vocabulário, e depois aplicar a lista
aprendida como lookup, igual à Abordagem A.

**Trade-off:** ganha escala (aprende mais frases do que uma pessoa lembraria),
mas herda o risco central do invariante 10: como a semente de extração usa o
PRÓPRIO corpus que também rotula o fusor (`overall_rating`/`recommend_to_a_friend`
do B2W), qualquer termo aprendido carrega correlação com o rótulo por
construção — a feature resultante corre risco real de ser um detector de
sentimento negativo requentado, não de incongruência. Esse é precisamente o
padrão de falha que já derrubou `ironia_prob_media`/`ironia_prob_max`
(seção "A ironia sai do vetor" em `docs/treinamento.md`): uma feature que
"funciona" no corpus de treino por reproduzir o próprio sinal de sentimento,
sem medir a relação de contraste que o nome promete. Não recomendada sem uma
fonte de "situação negativa" INDEPENDENTE do corpus de rótulo — e essa fonte
independente não existe em português hoje.

### Abordagem C — não adicionar feature; delegar ao classificador de ironia (BERTimbau)

Argumento: a cabeça de ironia (`fraus/sinais/ironia.py`) já é um classificador
neural que poderia, em princípio, captar incongruência implícita sem
depender de léxico algum — é justamente o tipo de padrão que features
determinísticas não alcançam.

**Por que não resolve o problema deste documento:** a cabeça de ironia já
existe, é obrigatória (invariante 7) e é lida por mensagem — mas está FORA
do vetor do fusor desde 04/09/2026 exatamente porque, medida no corpus de
treino (B2W-Reviews01), ela funciona como detector de sentimento POSITIVO, não
de ironia (74% das resenhas satisfeitas marcadas como irônicas contra 9% das
insatisfeitas). Delegar a incongruência implícita a ela sem verificação
repetiria o mesmo erro que acabou de ser corrigido. Não é solução nova, é
reverter a correção de 04/09.

## Riscos de vazamento (invariante 10) — avaliação direta

A pergunta que a invariante exige: **a feature proposta (Abordagem A) separa
sozinha as classes no corpus de treino?**

Risco real, e precisa ser medido antes do retreino valer, pelo mesmo processo
que `tests/test_simulador.py -k unilateral` já roda para as 5 features
existentes:

1. **No SIMULADOR** (a estrutura temporal do treino): `FRASES_POR_ROTULO`
   em `fraus/ingest/simulador.py` precisa conter situação negativa (espera,
   transferência etc.) tanto em falas do rótulo INSATISFEITO (reclamação
   direta, sem elogio — a feature fica 0.0 porque falta o lado positivo)
   quanto em falas do rótulo SATISFEITO com elogio explícito sobre a
   resolução (para a feature não disparar SÓ no insatisfeito ou SÓ como
   função do rótulo). Sem essa cobertura cruzada, a feature repete
   exatamente o vazamento de `incongruencia_hiperbole` pré-correção
   (unilateral no satisfeito) documentado em `docs/treinamento.md`.
2. **No B2W-Reviews01** (o texto real do treino): medir, como já foi feito
   para a cabeça de ironia (amostra equilibrada por rótulo, mesma semente
   `20260904`), a taxa de disparo de `incongruencia_situacao_negativa` por
   classe (`overall_rating`/`recommend_to_a_friend`). Se disparar quase só
   numa classe, é previsor unilateral disfarçado de feature de incongruência
   — mesmo risco que já derrubou as duas features de ironia do vetor.
3. Adicionar guarda de teste equivalente a
   `test_nenhuma_feature_e_previsor_unilateral` cobrindo a nova chave, antes
   de aceitar qualquer retreino.

Comparado às 5 features atuais, o risco aqui é MAIOR, não menor: a Abordagem A
depende de uma lista curada com viés de quem escreveu — é mais fácil, sem
querer, escrever exemplos de situação negativa que soam como reclamação pura
(logo, correlacionados com insatisfeito) do que exemplos que soam como ironia
de fato (elogio + situação negativa). A mitigação é a mesma que já funcionou
para `incongruencia_hiperbole`: garantir, no corpus sintético, situação
negativa presente nos TRÊS rótulos, variando se vem acompanhada de elogio
léxico ou não.

## Feature teria sinal no corpus de treino (B2W)?

Sim, com razão de sobra — resenha de e-commerce fala constantemente de prazo
de entrega, atendimento e cobrança, então "não chegou", "demorou",
"cobraram errado" etc. aparecem em volume nas resenhas negativas. O risco não
é ausência de sinal (o problema que derrubou `emoji_score_medio` no primeiro
fusor, quando o simulador nunca emitia emoji) — é sinal **correlacionado
demais com o rótulo por vir sempre desacompanhado de elogio** nas resenhas
ruins. Constante-no-treino não é o risco aqui; unilateral-por-classe é.

## Custo de implementação: retreino obrigatório

Adicionar `incongruencia_situacao_negativa` (ou qualquer nome escolhido) muda
`NOMES_FEATURES` em `fraus/fusor.py` — sobe de 38 para 39 (ou mais, se
Abordagem A vier com sub-features por tema). Isso **exige rodar o notebook 02
de novo**: o artefato salvo (`modelos/fusor.joblib`) tem `n_features_in_`
travado no tamanho antigo, e a API sobe normalmente (`joblib.load` não valida
forma) mas falha em HTTP 500 na primeira pontuação real — o mesmo risco de
demonstração ao vivo já registrado em `docs/treinamento.md` para o retreino de
03/09. O corpus sintético do simulador também precisa ganhar frases que
cubram a nova feature nos três rótulos (mesmo processo do retreino anterior),
não só o vetor de features.

## Limitação metodológica a declarar

A lista de padrões de situação negativa é curadoria própria, sem paper nem
revisão por pares — mesma natureza de limitação já declarada para
`fraus/dados/palavroes_ptbr.csv` e para `MARCADORES_CONTRASTE`/
`INTENSIFICADORES_*` em `incongruencia.py`. Diferente do SentiLex-PT02, que
tem procedência acadêmica (Silva, Carvalho e Sarmento, PROPOR 2012), a lista
de situação negativa não pretende ser um recurso lexical formal — é um
catálogo pequeno, ajustável, que cobre os temas mais recorrentes de queixa em
atendimento (espera, repetição, transferência, entrega, cobrança) e nada
além disso. Cobertura fora desses temas (por exemplo, situação negativa
específica de um setor não representado na lista) fica sem sinal, na mesma
lógica de "feature ausente é melhor que feature ruidosa" que já rege as
demais listas do módulo. O relatório deve declarar isso explicitamente,
junto da citação de Riloff 2013/Joshi 2015 como a motivação teórica, sem
sugerir que a lista foi extraída pelo método deles — ela não foi.

## Referências consultadas nesta pesquisa

- Riloff, Qadir et al. — Sarcasm as Contrast between a Positive Sentiment and
  Negative Situation (EMNLP 2013) — <https://aclanthology.org/D13-1066/>
- Riloff — A Retrospective on Mutual Bootstrapping (AI Magazine 2018) —
  <https://onlinelibrary.wiley.com/doi/abs/10.1609/aimag.v39i1.2778>
- Joshi, Sharma & Bhattacharyya — Harnessing Context Incongruity for Sarcasm
  Detection (ACL 2015) — <https://aclanthology.org/P15-2124/>
- Blogs de CX/atendimento levantados por busca dirigida (não citáveis como
  léxico, usados só para confirmar que o catálogo de queixas é pequeno e
  recorrente): atendesimples.com, digisac.com.br, blog.zapsign.com.br,
  zendesk.com.br — ver seção de pesquisa acima.
- Demais 69 fontes já catalogadas em
  `docs/superpowers/specs/2026-09-03-incongruencia-bibliografia.md`, em
  particular a nota sobre iSarcasm (Oprea & Magdy, ACL 2020) sobre corpus
  rotulado por marcador de plataforma, que se aplica igualmente a um eventual
  bootstrapping sobre B2W rotulado por `overall_rating`.

**Nota de proveniência.** O PDF de Riloff et al. 2013 não pôde ser extraído
por texto nesta sessão (WebFetch devolveu conteúdo binário não decodificado);
os detalhes do algoritmo e as métricas de precisão/F1 citadas acima vêm de
resumos de terceiros levantados por busca (ResearchGate, revisões de curso) e
não foram conferidos linha a linha contra o artigo original. Antes de citar
os números 0,70/0,51 no relatório final da banca, ler o PDF diretamente
(<https://aclanthology.org/D13-1066.pdf> ou
<https://nlp.cs.utah.edu/assets/pdfs/riloff2013sarcasm.pdf>) para confirmar.
