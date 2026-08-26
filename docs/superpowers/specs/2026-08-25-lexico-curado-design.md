# O léxico curado — o analista conserta o dicionário, não a nota

**Data:** 2026-08-25
**Escopo:** `fraus/sinais/curadoria.py` (novo), `fraus/sinais/lexico.py`,
`fraus/sinais/emoji.py`, `fraus/motor.py`, `fraus/db.py`,
`fraus/api/rotas/lexico.py` (novo), `fraus/api/rotas/modelo.py`,
`fraus/api/rotas/conversas.py`, `dashboard/app/modelo/page.tsx`, `README.md`.

**Fora desta spec, por decisão:** a descoberta pela transcrição (token
desconhecido sublinhado, popover no lugar). Ver §9.

---

## 1. O problema

O SentiLex-PT02 tem 79.189 formas e não tem `lentíssimo`. O Emoji Sentiment
Ranking tem 751 emojis anotados em 2015 e não tem os que entraram depois. Nem um
nem outro conhece o jargão da empresa que opera o atendimento.

Quando o léxico não conhece a palavra, ela vale **0** — e essa é a decisão certa
para um termo desconhecido. O que falta é o analista poder dizer *"esta aqui eu
conheço"* sem esperar um retreino que não vai acontecer.

## 2. O que o peso curado FAZ — e o que ele não faz

**Ele alimenta o sinal léxico. Não corrige o score.**

```
você cadastra: "lentíssimo" → negativa
        ↓
  lexico_polaridade_media  muda
  lexico_cobertura         muda
        ↓
  fusor treinado (35 features)
        ↓
      score muda
```

Quem pontua continua sendo o modelo. O analista preenche um buraco do
dicionário, exatamente como se a palavra sempre tivesse estado nas 79 mil do
SentiLex.

**Por que não corrigir o score direto**, que seria mais previsível: um ajuste
fixo por cima do número do modelo cria uma **segunda régua**. O README já
documenta essa dor com `PESO_NEUTRO_NO_SCORE` — duas réguas somadas no mesmo
agregado, sem nenhuma leitura capaz de separá-las. Repetir isso, agora com uma
régua que cada instalação define sozinha, seria pior.

## 3. A escala — cada léxico na sua régua

| léxico | escala | por quê |
|---|---|---|
| **palavra** | inteiro **−1 / 0 / +1** | é a escala das 79.189 formas do SentiLex, e é nela que `lexico_polaridade_media` foi treinada |
| **emoji** | float contínuo **[−1, 1]** | é a escala do Emoji Sentiment Ranking, derivada de contagem de anotadores |

**Não é uma régua só, e a recusa é deliberada.** Deixar o analista digitar
`−0,7` numa palavra injeta na média de polaridade um valor que o fusor **nunca
viu no treino**: a feature passa a operar fora da distribuição em que os pesos
foram aprendidos, e o efeito no score deixa de ser previsível. Cada entrada
curada precisa ser indistinguível de uma que já estava no léxico base.

O `0` para palavra não é inútil: ele **silencia** um termo que o SentiLex anota
com polaridade errada para o domínio de atendimento.

## 4. A arquitetura — por parâmetro, nunca estado global

Módulo novo `fraus/sinais/curadoria.py`, com um objeto `Curadoria` carregado do
banco e duas consultas: `polaridade_de(termo) -> int | None` e
`score_de(emoji) -> float | None`. `None` significa "não curado" — o léxico base
responde.

**A curadoria VENCE o léxico base.** Isso a faz servir aos dois casos: preencher
buraco (`lentíssimo` não existe) e corrigir polaridade errada de domínio.

### 4.1 Por que por parâmetro, e não dentro do `lru_cache`

Os dois léxicos carregam com `@lru_cache(maxsize=1)` — estado global de
processo, e correto para um CSV que não muda. A curadoria **muda em runtime**, e
se entrasse por ali, cadastrar uma palavra exigiria reiniciar a API.

É exatamente o bug que a autenticação já teve: o middleware só era registrado no
boot, e a rota que gravava a mestra apenas *parecia* ligar a defesa. A
invariante 4 já fixou o padrão para as faixas de NPS — **passa por parâmetro,
nunca estado global mutável, e é lido a cada requisição.**

Assinaturas afetadas, todas com `curadoria` opcional ao fim para não quebrar
chamador existente:

- `lexico.polaridade_do_termo(termo, curadoria=None)`
- `lexico.anotar_texto(texto, curadoria=None)`
- `lexico.features_lexico(conversa, curadoria=None)`
- `emoji.score_do_emoji(caractere, curadoria=None)`
- `emoji.features_emoji(conversa, curadoria=None)`
- `motor.Motor.pontuar_conversa(conversa, curadoria=None)`

**Quem carrega, e quando:** `Contexto` ganha `curadoria_vigente()`, que lê a
tabela **a cada requisição** — irmã de `faixas_vigentes()`, pelo mesmo motivo
escrito lá: *"não existe cópia do estado envelhecendo em memória depois de um
PUT"*. O `Motor` é construído uma vez no boot e continua sem saber da curadoria;
quem a passa é a rota, no momento de pontuar. Um `Motor` que a guardasse
recriaria o problema da §4.1 dentro de outro objeto.

O custo é uma leitura de tabela pequena por pontuação, no mesmo SQLite que a
rota já abriu — a mesma conta que o middleware de autenticação já paga.

### 4.2 O n-grama continua funcionando

`anotar_texto` busca n-gramas de 5 até 1 antes de cair no token solto. A
curadoria entra **na mesma busca**, no mesmo ponto (`_polaridade`), então um
termo curado de duas palavras (`fora do ar`) vence o token solto que o compõe,
igual a um idioma do SentiLex. Nenhuma ordem de precedência nova é inventada.

## 5. O banco

```sql
CREATE TABLE IF NOT EXISTS lexico_curado (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,          -- 'palavra' | 'emoji'
    termo TEXT NOT NULL,
    peso REAL NOT NULL,
    motivo TEXT,                 -- por que, nas palavras do analista
    criado_em TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_lexico_curado_termo
    ON lexico_curado(tipo, termo);
```

O índice único é o que faz recadastrar o mesmo termo ser **edição**, não
duplicata silenciosa com uma das duas vencendo por ordem de leitura.

`motivo` é opcional e existe para a decisão sobreviver a quem a tomou: um `peso`
sem porquê, seis meses depois, é indistinguível de erro de digitação.

## 6. A versão, e a régua misturada

O `score` é gravado na importação. Cadastrar uma palavra **não** repontua o que
já existe — e sem tratamento isso é o defeito que o README já nomeia.

- `configuracoes` ganha a chave `lexico_versao` (inteiro, começa em 0),
  **incrementada a cada escrita** em `lexico_curado`.
- `conversas` ganha a coluna `lexico_versao`, gravada no momento da pontuação.
  Entra por `COLUNAS_ACRESCENTADAS` em `db.py`, que é como o projeto já
  acrescenta coluna sem quebrar banco antigo. Linha antiga fica `NULL` e é lida
  como "anterior a este mecanismo".
- `GET /indicadores` passa a devolver `pontuadas_com_lexico_antigo` e `total`.
  **As duas contagens são do BANCO INTEIRO, não do recorte `de`/`ate`**, e é a
  única coisa nessa resposta que ignora o período: a régua misturada é uma
  propriedade do banco, não da semana que se está olhando. Um aviso que sumisse
  ao filtrar o período esconderia o problema exatamente de quem estivesse
  investigando um número estranho. A Visão geral usa os dois para nomear a
  divergência:

  > ⚠️ **41 de 62 atendimentos foram pontuados com um léxico anterior.**
  > `[ Repontuar tudo ]`

**Nada muda sozinho, e nada mistura em silêncio.** Este é o requisito, não o
aviso: uma feature que altera o score em silêncio num projeto cuja tese é
honestidade metodológica seria autocontraditória.

### 6.1 `POST /conversas/repontuar`

Recarrega cada conversa do payload, repontua com a curadoria vigente, grava
`score`, `categoria` e `lexico_versao`. Responde com quantas foram.

**Limitação declarada, não resolvida:** repontuar roda os **três BERTimbau** de
novo por conversa. O vetor é de 35 features e o fusor exige as 35 — não existe
recalcular só as três léxicas e as cinco de emoji sem o resto. Em dezenas de
atendimentos são segundos; em milhares vira trabalho de fila, e a fila fica
fora desta spec. A rota é **síncrona** e a tela mostra "repontuando…".

## 7. A API

| rota | o que faz |
|---|---|
| `GET /lexico/curado` | lista o que existe: tipo, termo, peso, motivo, data |
| `POST /lexico/curado` | cadastra ou edita. Valida a escala da §3 |
| `DELETE /lexico/curado/{id}` | revoga. Incrementa a versão, como qualquer escrita |
| `POST /conversas/repontuar` | §6.1 |

**Validação de entrada**, e ela é a fronteira que sustenta a §2:

- `tipo` ∈ {`palavra`, `emoji`} — qualquer outro é **400**;
- `palavra`: `peso` ∈ {−1, 0, 1}, inteiro. `−0.7` é **400** nomeando a escala;
- `emoji`: `peso` ∈ [−1, 1], e `termo` precisa ser **um único emoji** — validado
  com a mesma `lib_emoji` que o sinal já usa, nunca por regex própria;
- `termo` de palavra é normalizado como o léxico normaliza (minúsculas), para
  `Lentíssimo` e `lentíssimo` não virarem duas linhas.

O modelo de entrada aceita **só** `tipo`, `termo`, `peso` e `motivo`. Nada que
se pareça com score, nota ou categoria — invariante 3.

Como toda rota, entra sob o middleware de chave de acesso. Não é privilégio de
mestra: curar léxico é trabalho do analista, não administração de credencial.

## 8. A honestidade na tela

`/modelo` ganha um painel **Léxico curado**: lista, edita, revoga, e cadastra
por formulário. Ao lado das métricas do modelo, a ficha passa a declarar:

> **N termos curados nesta instalação** — 12 palavras, 3 emojis.

Isso não é enfeite de contagem. Um score influenciado por curadoria humana não
pode se apresentar como inferência pura do modelo, pela mesma regra que faz o
NPS carregar "estimativa" em todo lugar onde aparece. Com zero termos curados a
linha **some** — a tela não anuncia uma intervenção que não houve.

O README ganha uma seção com o mecanismo, a escala de cada léxico e a limitação
do repontuar.

## 9. Fora de escopo — e por quê

**A descoberta pela transcrição** (token que o léxico não conhece sublinhado na
fala, popover para classificar no lugar) é a segunda spec. Ela é UX sobre este
núcleo e não tem onde salvar sem ele; juntar as duas produz uma spec que
ninguém revisa direito e um plano de vinte tarefas.

**A fila de "palavras que o modelo mais perdeu"** — ordenar por frequência os
termos desconhecidos nas falas de cliente — não está em nenhuma das duas. É uma
terceira, e só vale a pena depois de existir volume real de atendimento.

**A fila assíncrona do repontuar** — ver §6.1.

**Curadoria por canal ou por fonte** (a mesma palavra pesando diferente no
WhatsApp e no Discord): não há evidência de que o domínio mude entre canais no
volume deste trabalho, e a tabela ganharia uma dimensão que ninguém pediu.

## 10. Testes

- **Curadoria vence o léxico base:** termo que existe no SentiLex com polaridade
  `1` e curado como `−1` é anotado como `−1`.
- **Termo curado ausente do léxico base** entra na anotação e move
  `lexico_polaridade_media` e `lexico_cobertura`.
- **A negação continua valendo sobre termo curado:** "não ficou lentíssimo"
  inverte o peso curado, pelo mesmo escopo de 3 tokens.
- **N-grama curado vence o token solto** que o compõe.
- **Emoji curado** move `emoji_score_medio`; emoji fora do léxico e não curado
  continua valendo 0.
- **Sem curadoria (`None`), o comportamento é byte a byte o de hoje** — é o
  teste que garante que esta spec não mexeu no que já funcionava.
- **Validação:** peso `−0.7` em palavra dá 400; `tipo` inválido dá 400; dois
  emojis num `termo` de emoji dá 400.
- **Versão:** escrever incrementa; revogar incrementa; conversa pontuada grava a
  versão vigente; `/indicadores` conta as defasadas.
- **Repontuar** atualiza `score` e `lexico_versao` e zera a contagem defasada.
