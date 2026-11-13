# Satisfação, emoção e fusor: três tentativas, nenhuma promoção — 13/11/2026

Resumo: nenhuma das três peças que pontuam a nota foi promovida. A régua
foi escrita antes de medir e não foi afrouxada. O que muda no código é a
**latência ausente** em conversa sem resposta (B01 da auditoria de 13/10),
que vale para o fusor de produção sem retreino.

Produção continua a de hoje cedo: satisfação de agosto (SHA-256 `9f9448ae…`),
emoção de agosto (`e9735f12…`), fusor de 15/09 em `log1p` (`5c468660…`) e
ironia do MultiPICo. Nada foi publicado.

## A régua (escrita antes)

1. Época, semente, temperatura e limiar escolhidos na validação; teste lido
   uma vez.
2. Satisfação: decide o ConsumerBR. Promove se o IC95 da diferença de F1-macro
   excluir zero **e** o recall de neutro não cair em relação à cabeça atual
   **e** o fusor montado sobre ela não perder no pareado.
3. Emoção: decide o XED-pt, IC95 excluindo zero.
4. Fusor: pareado no mesmo manifesto, com IC, e `scripts/conferir_fusor.py`
   em todo candidato.

## Instrumentos conferidos antes de medir

Nada abaixo foi aceito sem reproduzir um número já registrado:

| Instrumento | Registrado | Reproduzido em 13/11 |
|---|---|---|
| Benchmark de satisfação na GPU (Colab T4), B2W 5.000 | 0,7646 (29/10, CPU) | 0,7646 |
| Idem, ConsumerBR 5.000 | 0,5388 | 0,5388 |
| Braço controle da emoção, F1 de validação por época | 0,5518 / 0,5593 / 0,5783 (26/10) | 0,5521 / 0,5601 / 0,5781 |
| Pareado do fusor (42 − atual), 300 conversas | −0,029 [−0,064; +0,005] | −0,0293 [−0,0640; +0,0051] |
| Identidade do cache de features (manifesto, checkpoints, código) | `features-atual.json` | igual |

Impressões dos conjuntos de teste: B2W `481da017399a`, ConsumerBR
`99a53fd45904`, GoEmotions-PT `8b48cefed8df`, XED-pt `a1d2cd6db52c` — as mesmas
de 26/10 e 29/10. SHA-256 dos arquivos de corpus usados no Colab conferidos
contra a cópia local (ConsumerBR `e9fd6811…`, XED `bf6c1db1…`).

## Satisfação: o ajuste do neutro — não promove

Ajuste curto que estava preparado desde 29/10 e nunca tinha rodado: parte do
candidato 42 (SHA-256 `709951b5…`), 2 épocas a 5e-6, treino balanceado
(7.000 por classe, 21.000 no total, amostra do treino do manifesto), alvo
suave só no neutro (0,2), sem peso de classe. Divisão conferida contra o
manifesto antes de treinar. A validação escolheu a **época 1** (F1 0,7587;
época 2: 0,7551, perda subindo) e temperatura 1,351. Pesos
`e2a9d00c…`, fora do git.

| Conjunto | n | Atual | Ajustado | Diferença [IC95] | Recall de neutro: atual → ajustado |
|---|---:|---:|---:|---|---|
| ConsumerBR (decide) | 5.000 | 0,539 | **0,574** | **+0,035 [+0,020; +0,050]** | **0,368 → 0,201** |
| B2W, teste interno | 5.000 | 0,765 | 0,762 | −0,003 [−0,013; +0,008] | 0,710 → 0,553 |
| Fusor, 300 conversas sintéticas | 300 | 0,940 | 0,914 | −0,026 [−0,060; +0,008] | 0,91 → 0,77 |

Para comparação, o candidato 42 sem ajuste tinha neutro 0,159 no ConsumerBR,
0,515 no B2W e 0,76 no fusor. O ajuste **recuperou parte** do neutro (+0,04
nos dois benchmarks) sem perder o ganho no ConsumerBR, mas ficou longe da
cabeça atual.

Veredito pela régua: condição 1 passa; **condição 2 falha** (neutro 0,20 contra
0,37); condição 3 não passa por margem (o IC cruza zero, mas a estimativa é
negativa e o neutro do fusor cai de 0,91 para 0,77). `conferir_fusor.py` no
fusor montado sobre ela acusa **sinal invertido** em
`incongruencia_marcador_contraste` (+0,54) e `incongruencia_hiperbole`. Não
promove.

Leitura: o ganho no ConsumerBR vem de mover satisfeito que o modelo atual
chamava de neutro (recall de satisfeito 0,40 → 0,57). Esse movimento é o
mesmo que tira o neutro. Com esta família de ajustes, ganhar no F1 e manter
o neutro parecem estar em tensão; inferência, não medido além destas duas
receitas.

JSON: `2026-11-13-benchmark-satisfacao-ajustado.json` e a receita em
`2026-11-13-fusor-e-receitas.json`.

## Emoção: cortesia não é alegria — não promove

Hipótese de dado, uma só: a frase-tese ("ok, obrigado 🙂 já resolvi sozinho
depois de esperar 40 minutos") sai **alegria 0,98** porque o mapa Ekman do
GoEmotions põe `gratitude`, `approval` e `caring` dentro de alegria. Cortesia
e assentimento não são alegria sentida.

Dois braços, **mesma divisão** (os textos ficam nos mesmos lados; quem perde
o rótulo único sai), mesma receita da campanha (5 épocas, 2e-5, semente 13 —
a escolhida pela validação em 26/10):

- controle: mapa original;
- cortesia: as três classes finas contam como neutro. No treino, alegria cai
  de 13.987 para 8.760 exemplos e neutro sobe de 12.040 para 16.187.

Risco declarado antes de medir: o XED-pt não tem neutro, então mandar mais
coisa para neutro tende a errar mais ali por construção.

| Conjunto | n | Atual | Controle | Cortesia | Cortesia − atual [IC95] | Cortesia − controle [IC95] |
|---|---:|---:|---:|---:|---|---|
| XED-pt, seis classes presentes (decide) | 4.286 | 0,280 | 0,272 | 0,266 | **−0,015 [−0,023; −0,006]** | −0,006 [−0,014; +0,002] |
| GoEmotions-PT, teste interno (rótulo original) | 7.328 | 0,691 | 0,596 | 0,550 | −0,141 | −0,046 |

O GoEmotions interno mede o braço cortesia contra um rótulo que ele foi
treinado para contrariar: a queda ali é esperada e não decide nada. O 0,691
da cabeça atual é o mesmo número otimista de 26/10 (pesos anteriores à
divisão).

Sonda (probabilidade da classe mais alta, `2026-11-13-sonda-emocao.json`):

| Frase | Atual | Controle | Cortesia |
|---|---|---|---|
| ok, obrigado 🙂 já resolvi sozinho depois de esperar 40 minutos | alegria 0,98 | alegria 0,92 | **neutro 0,89** |
| ok, obrigado | alegria 0,98 | alegria 0,91 | neutro 0,89 |
| muito obrigado, vocês resolveram rápido, adorei! | alegria 0,99 | alegria 0,94 | **neutro 0,83** |
| que atendimento maravilhoso, só esperei 3 horas | alegria 0,98 | alegria 0,94 | alegria 0,92 |

O braço cortesia acerta a frase-tese e **erra** o elogio sincero, que vira
neutro. A correção passa do ponto: "obrigado" pesa mais que "adorei".

Veredito: perde para a cabeça atual no XED-pt com IC excluindo zero. Não
promove. Contra o próprio controle, a diferença no XED-pt não é distinguível
de zero: o remapeamento não piora a transferência de forma mensurável, mas
também não melhora. O código do remapeamento (`ler_goemotions_ptbr(...,
finas_para_neutro=...)`, `rerrotular_lados`) fica, testado e desligado por
padrão, para repetir o experimento.

## Fusor

### Por que o completo empata com o texto sozinho

Investigado **sem ler o teste**: 1.500 conversas novas do lado de
validação do manifesto (500 frases por classe, semente 20261113), fusores
treinados nas mesmas 900 conversas de treino, cabeças de produção.

| Variante | F1 | Diferença para o completo [IC95] |
|---|---:|---|
| completo (39) | 0,922 | — |
| só texto (4) | 0,917 | −0,005 [−0,020; +0,009] |
| texto + emoji (9) | **0,942** | **+0,020 [+0,008; +0,033]** |
| sem emoção | 0,934 | +0,012 [+0,003; +0,021] |
| sem estilo | 0,935 | +0,013 [+0,006; +0,022] |
| sem léxico | 0,931 | +0,009 [+0,003; +0,016] |
| sem incongruência | 0,932 | +0,010 [+0,003; +0,017] |
| sem texto (35) | 0,865 | −0,057 [−0,074; −0,041] |

E, no teste de 13/11 já lido, com a cabeça mais fraca (candidato 42), o
completo **supera** o texto sozinho: +0,031 [+0,003; +0,061].

Conclusão: é sobretudo **limitação do teste**, com um custo real de variância.

- No simulador, emoji e tempo são sorteados pelo rótulo, independentes do
  texto: trazem informação nova, e por isso texto + emoji ganha.
- Emoção, léxico e incongruência releem a **mesma** frase do B2W que o
  BERTimbau de satisfação, treinado nesse corpus, já lê bem. Aqui não têm o que
  acrescentar e, com 900 conversas de treino, viram ruído (cerca de 0,01 de F1).
- O que essas famílias existem para pegar — ironia, incongruência, cortesia
  em atendimento — não existe no teste sintético. O teste não mede o valor
  delas; não prova que não têm valor.
- As 35 features não somam zero: sozinhas dão 0,865. Elas são **redundantes**
  com o texto quando o texto é bom.

### Candidato: regularização escolhida na validação — não promove

Mesmas 39 features, mesma receita, só o C da `LogisticRegression` escolhido
na validação (120 oficiais + 1.500 do diagnóstico). Curva plana entre 0,03 e
0,3; escolhido **C = 0,3** (0,9294 contra 0,9234 do C = 1). Congelado antes do
teste.

| | Receita atual (C = 1) | C = 0,3 | Diferença [IC95] |
|---|---:|---:|---|
| F1, 300 conversas de teste | 0,940 | 0,943 | +0,003 [−0,011; +0,017] |
| ECE | 0,020 | 0,026 | — |

`conferir_fusor.py`: sinal invertido em três features de incongruência
(`incongruencia_emoji_texto` +0,32, `marcador_contraste`, `hiperbole`). O fusor
de produção tem as seis negativas. Não promove. Retreinar o fusor no
sintético tende a inverter a incongruência: é a invariante 10 aparecendo de
novo, e mais um motivo para não trocar o fusor por acurácia.

### B01: conversa sem resposta — corrigido sem retreino

Antes, a conversa que ninguém respondeu tinha as três latências **0,0**, a
mesma codificação de "respondeu na hora". Agora `features_tempo` devolve
`None`; o vetor leva NaN; o `Fusor` troca NaN pela média do treino (z = 0)
depois do scaler, no caminho único de pontuação, classe, contribuição,
decomposição e deriva. Só as três latências podem faltar; qualquer outra
feature `None` é erro. Suíte inteira passou (1.700 testes).

Sonda com o fusor de produção e as cabeças de produção (cliente pede ajuda e
pergunta "alguém aí?" 10 min depois):

| Conversa | Regra antiga (0,0) | Regra nova |
|---|---|---|
| sem resposta | 75,1 · nota 8 | **71,0 · nota 7** |
| resposta do bot em 120 s | 68,3 · nota 7 | 68,3 · nota 7 |
| resposta do bot em 5 s | 72,9 · nota 7 | 72,9 · nota 7 |

O efeito é bem menor que o da auditoria (82 contra 29), que foi medida com o
fusor antigo em segundos crus. A conversa sem resposta ainda pontua acima da
respondida em 120 s, porque "não medido" agora vale a espera média do treino.
Se "ninguém respondeu" deve **penalizar** é decisão de produto: exige feature
própria e retreino, e não foi feito.

Isto muda a nota de conversas sem resposta pontuadas daqui em diante. O
`score` já gravado não é recalculado (invariante 4); repontuar é decisão do
João.

JSONs: `2026-11-13-fusor-e-receitas.json` (pareados, seleção de C,
diagnóstico, receitas). Laudos do `conferir_fusor.py` ficam fora do git.

## O que foi medido e o que foi inferido

Medido: todos os números das tabelas, com n, impressão e data acima.

Inferido, não medido:

- que o ganho do ConsumerBR e a perda do neutro estão em tensão em geral (só
  duas receitas foram vistas);
- que as famílias de texto ajudariam em atendimento real (não há corpus
  rotulado de atendimento);
- que a cabeça atual de satisfação tem vantagem no teste do fusor por ter
  visto frases dele (proveniência histórica ausente).

## O que não foi verificado

- Nenhum candidato foi para a Vercel; memória, ONNX e `/saude/prontidao` não
  foram medidos para eles, porque nenhum seria promovido.
- Só uma semente por braço da emoção e por ajuste: não há desvio entre
  sementes.
- A amostra de 5.000 do ConsumerBR, não o teste inteiro (143.717).
- O B01 não foi exercitado em produção nem na dashboard; o contrato da API
  (`latencia_*` já é `number | null` no front) não mudou.
- O candidato 42 foi medido no fusor com temperatura 1 (o diretório não tem
  `fraus_receita.json`); o ajustado, com 1,351. No F1 dos benchmarks isso não
  pesa (argmax), no fusor pesa, porque as features são probabilidades.

## Onde está cada coisa (fora do git)

`~/.cache/fraus/motores-2026-11-13/`: pesos do ajustado
(`candidatos/ajustado-42`), caches e fusores candidatos (`fusor/`), logs e
JSONs crus do Colab (`brutos/`), scripts da sessão (`scripts/`). Os braços da
emoção não foram exportados.
