# Sinal de estilo e contrato completo de features — 21/08/2026

## O problema

Duas lacunas separadas, que se resolvem no mesmo retreino.

**A primeira: o Fraus nao le enfase.** Cliente que escreve `NAO ACREDITO NISSO`,
`pfvvvv`, `que p*rra e essa` ou `?????` carrega informacao de intensidade que
nenhum dos tres sinais atuais captura. O sinal de texto le a frase, o de emoji
le os pictogramas, o de tempo le o relogio — a FORMA da escrita nao tem dono.

Retreinar o BERTimbau nao resolve isso, e essa e a conclusao que orienta todo o
resto do documento. O B2W-Reviews01 e resenha moderada de e-commerce: gritaria e
palavrao praticamente nao ocorrem. Um modelo nao aprende fenomeno que o corpus
nao contem, e mais epocas sobre o mesmo texto so reproduzem o mesmo artefato.
Enfase e um sinal DETERMINISTICO — irmao do `emoji.py`, nao epoca extra de
treino.

Verificado em 21/08/2026: os quatro notebooks nao destroem o sinal. Todos os
`.lower()` presentes caem em rotulo (`recommend_to_a_friend`, `rotulo_bruto`) ou
em nome de coluna (`bruto.columns`); nenhum toca o texto, e os `strip()` so
aparam borda. O BERTimbau e `cased` de proposito. A caixa alta sempre chegou
inteira ao tokenizer — nunca houve quem a LESSE.

**A segunda: tres modelos prontos estao fora do vetor.** `emocao.py` (8
features), `lexico.py` (3) e `ironia.py` (2) existem, estao testados e nao
entram em `NOMES_FEATURES`, que tem 16. A espera era deliberada e esta declarada
em `docs/treinamento.md`: subir o contrato faria `montar_features` exigir
classificadores que ninguem tinha treinado. Os notebooks 03 e 04 agora existem,
entao a condicao que justificava a espera acabou.

## O que vai ser feito

Criar o sinal de estilo, subir `NOMES_FEATURES` de 16 para 35, retreinar o
fusor sobre o vetor completo e re-medir o NPS.

## Sinal de estilo

Novo modulo `fraus/sinais/estilo.py`. Deterministico, sem modelo, sobre as falas
do cliente — coerente com os demais sinais: fala do bot nao carrega enfase do
cliente.

| feature | mede | por que nao e redundante |
|---|---|---|
| `estilo_frac_caixa_alta` | fracao de palavras gritadas (>=3 chars, todas maiusculas, ao menos uma letra) | enfase prosodica que o corpus de treino do BERTimbau nao contem |
| `estilo_pontuacao_enfatica` | densidade de `!!`, `??`, `?!` por mensagem | intensidade sem lexicalizar |
| `estilo_frac_alongamento` | repeticao de caractere (`naooooo`, `pfvvvv`) | marcador de afeto tipico de chat |
| `estilo_palavrao_intensidade` | media da gradacao leve/medio/pesado | "que droga" e "vai tomar no cu" nao sao o mesmo evento |
| `estilo_palavrao_dirigido` | fracao dirigida ao atendente vs desabafo | xingar o produto e reclamacao; xingar o atendente e ruptura |
| `estilo_frac_censurado` | `p*rra`, `c@ralho`, `#@$%` | autocensura e raiva COM autocontrole — estado distinto de raiva crua |

### Tres decisoes de implementacao

**Normalizacao de homoglifos vem antes do dicionario.** `c@r@lh0` normaliza para
`caralho` (`@`->`a`, `0`->`o`, `$`->`s`, `*` por casamento aproximado de vogal),
senao o lexicon erra toda ocorrencia censurada. **A censura e detectada ANTES da
normalizacao**, porque o fato de ter censurado e o dado que
`estilo_frac_censurado` mede — normalizar primeiro apagaria a evidencia.

**`kkkk` nao e alongamento negativo.** E a unica excecao com tratamento proprio
no codigo. Riso alongado e o marcador positivo mais comum de chat brasileiro;
juntar com `naooooo` numa feature so inverteria o sentido em boa parte das
conversas.

**Sigla nao e gritaria.** `CPF`, `NF`, `SAC` sao caixa alta e nao sao enfase. O
piso de 3 caracteres sozinho nao basta; sigla conhecida fica numa lista de
excecao, e o teto de comprimento evita que `OK` e `NAO` poluam a medida.

### Lexicon de palavroes

`fraus/dados/palavroes_ptbr.csv`, curado a mao neste repositorio: termo,
intensidade (leve/medio/pesado) e se e tipicamente dirigido a pessoa ou
desabafo. ~150 termos.

Alternativas descartadas: dependencia externa (`better-profanity` e similares)
viola "nada de dependencia nova sem motivo declarado", tem cobertura PT-BR fraca
e nao tem gradacao — e a banca vai perguntar a procedencia. Reaproveitar o
SentiLex nao funciona: ele e lexicon de julgamento social, forte em `pessimo` e
`incompetente`, e nao anota palavrao.

## Contrato de features: 16 -> 35

Nova ordem canonica em `NOMES_FEATURES`: texto (4), emoji (5), tempo (7), emocao
(8), lexico (3), ironia (2), estilo (6).

`montar_features` passa a exigir TRES classificadores — satisfacao, emocao e
ironia. Consequencias diretas e aceitas:

- o notebook 02 so roda depois que 03 e 04 produzirem artefato;
- a API nao sobe sem os tres modelos em `modelos/`. E o comportamento correto
  (invariante 7): servir predicao sem modelo carregado e pior que estar fora do
  ar.

`vetorizar` continua levantando `KeyError` em chave faltante. Nunca zero
silencioso (invariante 9).

## Anti-vazamento no simulador

O simulador precisa emitir estilo, senao as 6 features ficam constantes no treino
e nascem com peso zero — foi exatamente o destino de `emoji_score_medio` no
primeiro fusor. Mas emitir do jeito ingenuo cria um vazamento novo: se palavrao e
gritaria so ocorrerem em conversa insatisfeita, o estilo VIRA o rotulo, e a
regressao logistica vai ler o palavrao em vez do texto — a latencia disjunta de
13/08 com outra roupa.

Regra, entao: **cruzamento deliberado**, o mesmo padrao ja aplicado ao emoji e a
latencia.

- cliente satisfeito tambem grita (`OBRIGADOOO`, `kkkk PERFEITO`);
- cliente insatisfeito tambem reclama educado, em minusculas;
- palavrao ocorre nas TRES classes, com intensidade sobreposta.

Travado por teste: cada feature de estilo tem variancia > 0 dentro de cada
rotulo, e as distribuicoes por rotulo se sobrepoem.

## Notebooks

| # | notebook | roda de novo? | por que |
|---|---|---|---|
| 01 | BERTimbau satisfacao | nao | corpus e pipeline inalterados; reproduziria o mesmo artefato gastando GPU |
| 03 | emocao | nao | ja pronto; passa a ser obrigatorio por entrar no vetor |
| 04 | ironia | sim | passa a ser obrigatorio; sem IDPT liberado, usa o corpus sintetico e grava a procedencia real |
| 02 | fusor | **reescrito e retreinado** | unica mudanca real: carrega tres classificadores, extrai 35 features, treina e diagnostica |

O notebook 02 ganha tres celulas de diagnostico, todas nascidas do vazamento da
v1:

1. **sanidade de variancia** — desvio padrao de cada feature DENTRO de cada
   rotulo, impresso antes do treino. Feature com sigma ~ 0 e sinalizada. Teria
   pego `emoji_score_medio` morto em minutos, em vez de depois do modelo pronto;
2. **pesos por grupo de sinal** — soma dos coeficientes absolutos por familia. O
   criterio de `docs/treinamento.md` continua valendo: se tempo ou estilo
   liderarem sobre texto, e vazamento, nao vitoria;
3. **teste do relogio** — mesmo texto, tres latencias. Ja expos a v1 (2,5 pontos
   de separacao contra 99,6 do fusor corrigido) e fica permanente.

### Limitacao a declarar no relatorio

35 features numa regressao logistica treinada sobre conversa sintetica e muita
dimensao para o sinal disponivel. Se emocao ou estilo sairem com o grupo inteiro
colado em zero, a leitura correta e "o simulador nao gera esse fenomeno de forma
realista", nao "a feature e inutil". Isso vai para o relatorio como limitacao
declarada, no mesmo lugar onde o sinal de tempo ja esta.

## NPS: re-medicao

`PESO_NEUTRO_NO_SCORE = 0.75` foi calibrado contra um fusor de 16 features. Com
35, a distribuicao de score muda e o alinhamento precisa ser reconferido.

Instrumento: `scripts/medir_faixas.py`, que ja faz o necessario — lote
equilibrado por construcao, semente fixa, motor real, e `--peso-neutro` para
medir uma regua diferente da vigente sem editar codigo.

1. `uv run python scripts/medir_faixas.py` — regua vigente (0.75);
2. `uv run python scripts/medir_faixas.py --peso-neutro 0.5` — regua antiga, para
   publicar antes e depois lado a lado.

**Criterio de decisao, fixado aqui de proposito antes de ver o numero:** olhar
PRIMEIRO as medianas por classe.

- medianas continuam separadas (hoje ~0,11 / 50,99 / 99,03) e so a distribuicao
  de categoria escorrega -> defeito de COMPOSICAO, e o peso e o lugar certo;
- medianas colapsam umas nas outras -> defeito de TREINO, e mexer no peso
  maquiaria modelo ruim.

O script imprime as duas coisas juntas justamente para separar esses casos.

Se o 0.75 nao se sustentar, a mudanca de peso e decisao do Joao com o numero na
mesa, nao commit automatico: mexer nele exige repontuar o banco, porque scores
de duas reguas somados no mesmo agregado nao se separam na leitura. E honesto
que custe isso.

As faixas de NPS (0-6 / 7-8 / 9-10) NAO mudam. Sao padrao de fabrica pela
invariante 4, e recalibra-las destruiria a comparacao com NPS de mercado.

## Testes

TDD: teste vermelho primeiro.

- `tests/test_sinal_estilo.py` (novo) — caixa alta vs sigla; `kkkk` separado de
  alongamento negativo; censura detectada antes da normalizacao; homoglifos
  (`c@r@lh0`); palavrao dirigido vs desabafo; **conversa sem fala do cliente com
  todas as features zeradas sem estourar**;
- `tests/test_fusor.py` — `NOMES_FEATURES` com 35 entradas, sem duplicata;
  `vetorizar` levantando `KeyError` para cada familia nova;
- `tests/test_simulador.py` — variancia > 0 por rotulo e sobreposicao entre
  rotulos, para as features de estilo.

Invariante 2 vale integralmente: ausencia de estilo em conversa sem fala do
cliente e "sem sinal", nunca zero fingindo medicao. Nenhum `?? 0` ou `|| 0` entra
no caminho.

## Fora de escopo

**Gerar respostas.** Levantado nesta sessao e recusado por dois motivos
independentes. Tecnico: o BERTimbau e um encoder treinado com masked language
modeling — nao ha "proxima palavra" nele, e gerar exige decoder autorregressivo
ou seq2seq, com outra arquitetura, outro objetivo e outro corpus. De projeto: a
invariante 1 proibe LLM em runtime, e um gerador que caiba em CPU alucina o
bastante para envenenar uma ferramenta de medicao. O Fraus e medidor, nao
atendente — e essa fronteira e parte do que torna o trabalho defensavel.

O caminho compativel, se a necessidade voltar, e resposta por TEMPLATE preenchido
com o que o modelo ja sabe ("detrator, raiva 0,81, gritou, xingou dirigido ao
atendente -> escalar para humano"): zero geracao, zero alucinacao, cada palavra
rastreavel ate uma feature. Nao entra neste escopo.
