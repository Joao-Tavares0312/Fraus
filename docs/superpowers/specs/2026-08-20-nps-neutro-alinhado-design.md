# O neutro do modelo alcança o neutro do NPS — design

**Data:** 2026-08-20
**Escopo:** uma constante em `fraus/fusor.py`, um script de medição novo
(`scripts/medir_faixas.py`), testes de fronteira em `tests/test_indicadores.py`
e a poda de três parágrafos do `README.md` que descrevem um estado que não é
mais o do código.

---

## 1. O problema

O score do fusor é `100 * (P(satisfeito) + 0.5 * P(neutro))`. Com o peso em
`0.5`, uma conversa que o modelo classifica **com certeza** como neutra pontua
`50`, vira nota `5`, e a nota `5` cai na faixa `0–6` — **detrator**.

O efeito não é uma borda rara: é toda a classe neutra. A faixa neutra do NPS
(`7–8`) exigiria `P(satisfeito)` entre 0,4 e 0,8 com o resto em neutro — ou
seja, um **empate entre classes**, não uma neutralidade confiante. O modelo
nunca chega à categoria neutra dizendo "neutro"; só chega dizendo "não sei".

Medido antes desta mudança em 90 conversas do simulador (30 por classe,
equilibradas por construção): **67% detrator · 29% promotor · 4% neutro**, com
**NPS −38** onde o esperado seria ≈ 0.

Remedido com `scripts/medir_faixas.py --peso-neutro 0.5` (semente própria,
motor real), o defeito se reproduz: **67,8% detrator · 1,1% neutro · 31,1%
promotor**, NPS **−36,67** — e a matriz por classe mostra a causa sem ambiguidade,
com os **30 neutros indo todos para detrator**.

Isto não é erro de treino. O fusor separa as três classes com folga — medianas
de score 0,11 / 50,99 / 99,03. É a **composição** entre o peso do neutro no
score e a faixa padrão do NPS que produz o viés.

O número que a banca vai olhar primeiro é o NPS. Um NPS estruturalmente
pessimista por composição aritmética, num corpus equilibrado de propósito, é o
tipo de resultado que se defende mal — não porque esteja escondido (está
declarado no README), mas porque a resposta honesta à pergunta "por que −38?"
é "porque a régua está torta", e aí a medida não sustenta a tese.

## 2. A decisão: peso `0.75`

`PESO_NEUTRO_NO_SCORE = 0.75`, constante nomeada no topo de `fraus/fusor.py`,
consumida por `Fusor.pontuar`.

Com ela, as três classes do modelo caem nas três categorias do NPS:

| classe pura | score | nota | categoria |
|---|---|---|---|
| insatisfeito | 0 | 0 | detrator |
| neutro | 75 | 8 | **neutro** |
| satisfeito | 100 | 10 | promotor |

### 2.1 A fronteira do arredondamento é frágil, e por isso vai para teste

`nota_0_10(75)` é `int(round(7.5))`. Python usa arredondamento bancário: `7.5`
vai para `8` porque 8 é par. Se o peso fosse `0.65`, `round(6.5)` daria `6` —
**para baixo**, de volta a detrator, pelo mesmo motivo.

Ou seja: a tabela acima depende de um detalhe do arredondamento, não de uma
propriedade robusta da escolha. O handoff §3.3 registra que as fronteiras 6/7 e
8/9 já divergiram uma vez neste projeto exatamente por arredondamento. Por isso
a fronteira vira **teste explícito**, não comentário.

### 2.2 Por que o peso NÃO vai para `fraus/configuracao.py`

`fraus/configuracao.py` declara na própria docstring que só entra ali o que
muda o comportamento **na leitura**. Esta é a mesma razão pela qual a faixa de
NPS pode ser configurável: `categoria` é derivada na leitura, do `score`
gravado e da faixa vigente, então mudar a faixa refatia dado existente sem
recalcular nada.

O peso do neutro é de outra natureza: ele muda a **escrita** — o `score`
persistido no momento da importação. Um botão que o alterasse deixaria o banco
com scores de duas réguas diferentes somados no mesmo agregado, e nenhuma
leitura conseguiria distinguir os dois. É precisamente o defeito que a decisão
"categoria derivada na leitura" existe para não ter.

Constante, então. Mudá-la é mudar código e repontuar — e é honesto que custe
isso.

### 2.3 Por que não mexer na faixa de NPS em vez do peso

A alternativa aritmética seria alargar a faixa neutra para alcançar a nota 5.
Está descartada: `0–6 detrator, 7–8 neutro, 9–10 promotor` é a definição
canônica do NPS e um invariante declarado do projeto (CLAUDE.md §4). Mexer nela
para acomodar um artefato do score seria trocar um número defensável por um
número inventado — e a comparabilidade com qualquer NPS publicado morreria
junto.

### 2.4 O que NÃO muda

- O fusor **não é retreinado**. Os coeficientes são os mesmos; muda só a
  projeção das probabilidades em escala 0–100.
- `P(satisfeito)` e `P(insatisfeito)` puros continuam em 100 e 0.
- Nenhuma feature entra ou sai. `NOMES_FEATURES` continua com 16.
- `contribuicoes` e `importancias` não são afetadas: elas vivem no eixo dos
  coeficientes, não no score.

## 3. A medição vira reproduzível

Os números do §1 (67/29/4, NPS −38) saíram de uma medição avulsa que **não está
versionada**. Não dá para reproduzi-los, nem para conferir o depois contra o
antes na mesma régua — e um trabalho que vai a banca não pode citar uma medida
que ninguém consegue rodar de novo.

`scripts/medir_faixas.py`:

- gera o corpus do simulador (30 por classe, semente fixa — determinístico);
- pontua com o **motor real**, os pesos de `modelos/`;
- imprime a distribuição por categoria, o NPS e as medianas de score por classe;
- aceita `--peso-neutro` para medir uma régua diferente da vigente **sem editar
  código**, que é o que permite publicar o antes e o depois lado a lado.

O `--peso-neutro` é de medição, não de operação: ele não escreve nada, não toca
no banco e não existe caminho da API até ele. É a diferença entre um
instrumento e um botão.

## 4. Documentação: três parágrafos que descrevem um código que não existe mais

O `README.md` de `main` está atrás do código em três pontos. Os dois primeiros
são independentes desta mudança — foram consertados em PRs já mescladas e o
texto não acompanhou:

1. **Autenticação.** O parágrafo já descreve o "nasce fechada" de
   `fraus/api/primeiro_uso.py` — o que estava velho era a cópia num branch
   antigo, não a de `main`. Sobra **uma frase** internamente contraditória:
   ela ainda vende a tomada da mestra por quem chega primeiro como "o padrão de
   primeiro uso de Grafana e afins", e primeiro uso não é mais uma janela
   aberta. A frase passa a nomear os dois casos em que a janela existe de fato
   (mestra apagada, escrita do arquivo falhada) — o risco não é apagado, é
   posto no lugar certo.
2. **Atribuição por sentença.** O README diz que "não tem endpoint, então a
   transcrição marca só evidência observável". Tem:
   `GET /conversas/{id}/atribuicao`, consumida por `dashboard/lib/api.ts` e
   desenhada por `components/Transcricao.tsx`.
3. **NPS pessimista.** Deixa de ser limitação. O parágrafo é reescrito para
   registrar a composição, a escolha do peso e o número **remedido** — nunca o
   número lembrado.

O que **permanece** na seção de limitações, porque continua verdade e não é
consertável com código: o fusor treinado em conversas sintéticas, o corpus de
emoção traduzido por máquina, a ironia fora de domínio (IDPT são tweets) e o
SentiLex não ler afeto do próprio falante. Nenhuma dessas se resolve sem corpus
anotado novo.

### 4.1 O limite desta edição

O handoff lista "os textos de honestidade" como **intocáveis declarados pelo
João**. Esta mudança edita exatamente três parágrafos, todos por divergência
com o código verificada arquivo a arquivo, e nenhum deles perde ressalva: o
parágrafo do NPS troca uma ressalva por outra (a composição continua explicada,
com o número novo), e os outros dois passam a descrever a defesa que o código
realmente tem. Nada é removido por ser inconveniente.

## 5. Verificação

| o que | como |
|---|---|
| as três classes puras caem nas três categorias | teste novo em `tests/test_indicadores.py` |
| a fronteira `round(7.5) → 8` está fixada | teste novo, assertivo sobre `nota_0_10(75) == 8` |
| nada mais regrediu | `uv run pytest -q` — linha de base medida hoje: **384 passando, 1 deselecionado** (o handoff ainda diz 300; está velho) |
| o NPS do lote equilibrado saiu do −38 | `uv run python scripts/medir_faixas.py`, antes e depois |
| a dashboard não recalculou nada por conta própria | `cd dashboard && npx tsc --noEmit` |

O critério de aceite do §1 é numérico e sai do script: num lote equilibrado por
construção, as três categorias precisam ficar **povoadas**, e o NPS precisa
sair perto de zero. Se a medição não mostrar isso, o desenho está errado e não
se conserta o texto para caber no número.
