# Sinal de incongruência — complemento ao classificador de ironia

Data: 2026-09-03
Status: aprovado para plano de implementação

## Contexto e motivação

`fraus/sinais/ironia.py` calcula ironia com uma única cabeça BERTimbau binária
(NAO_IRONICO/IRONICO), treinada no corpus IDPT 2021 (IberLEF — 15,2k tweets +
18,4k notícias). O próprio módulo já declara a limitação: o corpus é de tweet
e notícia, não de atendimento de chatbot, e a transferência de domínio não é
verificada. Pesquisa de literatura (69 fontes, ver
`docs/superpowers/specs/2026-09-03-incongruencia-bibliografia.md`) mostra que
modelos neurais puros erram sistematicamente quando a ironia depende de
**incongruência** — contraste de polaridade dentro do próprio texto — e que o
ganho mais replicado e mais barato de obter vem de features explícitas dessa
incongruência (Riloff 2013, Joshi 2015: +8 a +20% F1 sobre baseline léxico).

Este documento cobre só essa melhoria: um sinal novo de incongruência que
complementa (não substitui) o classificador de ironia existente. Duas
pendências relacionadas — expandir a detecção de maiúsculas/repetição (já
existe em `fraus/sinais/estilo.py`) e um módulo de censura de dados sensíveis
(CPF etc., inexistente hoje) — ficam fora de escopo, viram specs próprias.

## Arquitetura

Novo módulo `fraus/sinais/incongruencia.py`, irmão de `ironia.py`, `lexico.py`,
`emoji.py` e `estilo.py`: mesma forma dos demais sinais — uma função pública
`features_incongruencia(conversa, curadoria=None) -> dict[str, float]` que lê
só `mensagens_cliente`, sem estado, sem rede, sem novo modelo/checkpoint.
Puro léxico + regex, coerente com o invariante "sem LLM em runtime".

Ele **reusa** infraestrutura existente em vez de duplicar:
- `anotar_texto` e o escopo de negação de `fraus/sinais/lexico.py`
- `emojis_com_posicao` e `score_do_emoji` de `fraus/sinais/emoji.py`
- o padrão de agregação (média por conversa, dict zerado para conversa vazia)
  já usado em todos os outros sinais

## As 5 features

Cada uma é calculada por mensagem do cliente e agregada como média (ou
fração de mensagens, para as booleanas) na conversa.

**F1 — `incongruencia_polaridade`** (Riloff 2013; Joshi 2015)
Conta termos de polaridade positiva e negativa na mesma mensagem via
`anotar_texto` (que já aplica o escopo de negação). Score:
`min(pos, neg) / max(1, pos + neg)`. É o ganho mais citado na literatura.

**F2 — `incongruencia_emoji_texto`** (Kralj Novak et al. 2015 aplicado)
Diferença de sinal entre a polaridade média do texto (`anotar_texto`) e a
polaridade dos emojis da mesma mensagem (`score_do_emoji`). Emoji positivo
com texto negativo (ou vice-versa) é sinal forte de ironia.

**F3 — `incongruencia_marcador_contraste`** (lista fixa de conectivos PT:
"mas", "só que", "porém", "contudo", "todavia", "entretanto", "mesmo assim")
Fração de mensagens em que um desses conectivos separa um trecho de
polaridade positiva de um trecho de polaridade negativa (`anotar_texto` nos
dois lados do conectivo).

**F4 — `incongruencia_hiperbole`** (Troiano & Strapparava 2018; Burgers 2012)
Intensificador (lista fixa nova: "muito", "super", "extremamente",
"totalmente", "completamente") adjacente a termo de polaridade extrema do
lexicon, normalizado por mensagem. Captura "atendimento *maravilhoso*, só
esperei 2 horas".

**F5 — `incongruencia_aspas_ironicas`** (Burgers 2012)
Fração de mensagens com palavra/expressão entre aspas cuja polaridade
(`anotar_texto`) diverge do resto da mensagem — "aspas de deboche"
(`"ótimo" atendimento`).

Conversa sem fala do cliente devolve as 5 chaves zeradas (invariante 2, mesmo
padrão de `features_estilo`/`features_ironia`).

## Integração com o Fusor

`NOMES_FEATURES` (`fraus/fusor.py`) sobe de 35 para 40: as 5 chaves novas
entram como família própria ("incongruência"), na mesma posição lógica das
demais (a ordem exata dentro da lista é decidida no plano). `montar_features`
passa a chamar `features_incongruencia` junto dos outros sete sinais.

Como o vetor mudou, o **Fusor precisa ser retreinado**: o notebook de treino
recalcula o vetor de 40 features sobre o corpus existente e re-treina
`LogisticRegression` + `StandardScaler`; o artefato salvo é substituído. O
treino roda no Colab, fora deste ambiente — a spec e o plano cobrem deixar
tudo pronto (código, dados, procedimento documentado em
`docs/treinamento.md`) para a execução manual do notebook.

**Vazamento de rótulo (invariante 10):** antes de aceitar o retrain, checar
que nenhuma das 5 features novas tem distribuição disjunta por classe no
corpus de treino — mesmo cuidado que já existe para as demais features,
documentado em `scripts/medir_faixas.py`/`docs/treinamento.md`.

Nenhuma mudança é necessária na dashboard: `PesosFeatures.tsx`,
`BarrasDeFeature.tsx` e `PainelContribuicoes.tsx` não hardcodam a lista de
features — consomem `contribuicoes`/`importancias`/`eixo_global` do Fusor via
API, então as 5 novas aparecem automaticamente.

## Testes

TDD, teste antes do código, por função:
- Cada uma das 5 funções privadas de `incongruencia.py`: caso positivo (frase
  desenhada para disparar a feature), caso negativo, caso vazio.
- `features_incongruencia`: conversa sem fala do cliente → todas 0.0;
  conversa com fala → agregação correta.
- `montar_features`/`vetorizar`: as 40 chaves batem com `NOMES_FEATURES`;
  falta de qualquer uma levanta `KeyError` (invariante 9).
- Checagem de não-vazamento de rótulo no corpus de treino para as 5 features
  novas, antes do retrain valer como aceito.

## Limitação metodológica a declarar

As 5 features de incongruência dependem do SentiLex-PT02 e do lexicon de
emoji já em uso — herdam as mesmas limitações deles (SentiLex é léxico de
julgamento social, neutro em verbo de afeto do próprio falante; ver
`fraus/sinais/lexico.py`). Marcadores de contraste e intensificadores são
listas fixas curadas manualmente, não extraídas de um recurso lexical
formal para PT-BR de atendimento — mesma natureza de limitação declarada que
as demais listas fixas do projeto (`SIGLAS`, `LETRAS_DE_RISO` em
`estilo.py`).
