# Handoff — Fraus, atualizado em 08/09/2026 (contestação, teto de vazão e a porta destrancada)

Escrito para uma sessão que não viveu nada do que está aqui. O objetivo é que
você consiga **decidir**, não só executar: cada regra abaixo vem com o motivo,
porque várias delas parecem erro até você saber por que existem.

O trabalho é o **TCC do João** (pt-BR). Fale em português com ele.

---

## 1. O que o Fraus é, em três frases

Ferramenta que lê atendimento por chatbot e **estima satisfação sem perguntar
nada ao cliente** — a tese é que "ok, obrigado 🙂" e sair insatisfeito é o caso
que uma pesquisa de NPS declarada não captura.

**Requisito de banca: nenhum LLM em runtime.** Três BERTimbau fine-tunados
(satisfação, emoção, ironia) e um fusor `LogisticRegression`. Se você se pegar
propondo chamar uma API de LLM para resolver alguma coisa, parou — isso invalida
o trabalho.

Stack: FastAPI + SQLite + Pydantic no back; Next.js 16 + shadcn/ui + Tailwind v4
+ Recharts no front (`dashboard/`).

---

## 2. Estado atual — 08/09/2026

| | |
|---|---|
| Testes | **767 passed, 1 deselected** (Python) · **69** (front) — 08/09/2026 |
| Modelos | os três em `modelos/`, 1,3 GB, **fora do git**; fusor em dia (39 features, acurácia 0,950) |
| API real | `uv run uvicorn fraus.api.main:app --port 8001` → confira `/saude`, tem de dizer `"motor":"real"` |
| API dublê | `uv run python scripts/api_demo.py` → :8000. **Só para trabalho de interface sem modelo.** Números sintéticos com cara de predição — invariante 7 |
| Dashboard | `cd dashboard && npm run dev` (ou `npm run build && npx next start`) |

**A API nasce FECHADA**, e este parágrafo dizia o contrário até 08/09/2026. Na
primeira subida ela gera a mestra e uma chave de acesso e grava as duas em
`.fraus-chaves.txt` (caminho configurável por `FRAUS_CAMINHO_CHAVES`),
anunciando no boot. A dashboard lê a chave desse arquivo sozinha. `curl` na mão
precisa de `Authorization: Bearer <mestra>`; sem isso você toma 401 e vai achar
que quebrou alguma coisa.

**Armadilha de sessão: se você definir `FRAUS_CHAVE_MESTRA` e
`FRAUS_JWT_SEGREDO` sem `FRAUS_CODIGO_CONVITE`, a API responde 401 para anônimo
e mesmo assim está aberta** — `registrar` → `entrar` → o JWT lê tudo. Desde
08/09/2026 o boot grita quando essa combinação sobe. Ver `README.md`, seção "A
porta destrancada".

Com a mestra ligada, toda rota exige `Authorization: Bearer`, exceto duas,
que têm credencial própria: `POST /ingestao` (chave de fonte `frs_`) e
`POST /integracoes/webhook/{fonte_id}` (assinatura HMAC no corpo). A segunda é
**anônima por desenho** — a plataforma externa não tem, nem pode ter, uma chave
`fra_`; ver a armadilha 8. Ela é uma porta pública de **escrita**: quem publica
a API na internet precisa saber que ela existe. Ver `README.md` e
`docs/hospedagem.md`.

### A LP e a autenticação de usuário, em um parágrafo cada

**A raiz virou vitrine.** `/` descreve o produto (tese, sete sinais,
honestidade metodológica) e as telas moram em `/dashboard/*`, com redirect das
rotas antigas. Nenhum número da LP é inventado — 39 features e sete sinais são
fatos do código, e não há acurácia fabricada nem depoimento. **Isso impõe uma
obrigação:** quando `NOMES_FEATURES` mudar, os números da LP mudam junto
(`dashboard/app/page.tsx`, `lp/Contador.tsx`, `lp/Constelacao.tsx`). Em
04/09/2026 o contrato foi a 38 (e no mesmo dia a 39) e a LP ficou anunciando 35 — número falso numa
tela pública, exatamente o que esta seção promete que não acontece. Agora há
guarda: `tests/test_derivacoes_dashboard.py::test_a_vitrine_anuncia_o_numero_real_de_features`
lê o `page.tsx` como texto e compara com `NOMES_FEATURES`. Ela cobre só o
contador principal — as menções em prosa (`lp/Contador.tsx`,
`lp/Constelacao.tsx`, o texto corrido da própria página) continuam sendo
conferência manual.

**Usuário é identidade, não credencial técnica.** Tabela `usuarios` (senha
scrypt em `fraus/usuarios.py`), JWT HS256 (`fraus/token_acesso.py`, PyJWT —
única dependência nova), rotas em `fraus/api/rotas/auth.py`. Papéis: `dev`
administra, `usuario` analisa — o portão de papel mora no middleware
(`seguranca.py`, `rota_administrativa`) e vale **nos dois modos**: JWT de
usuario apresentado toma 403 em rota administrativa mesmo com a API aberta.
Segredos no ambiente, nunca no banco: `FRAUS_JWT_SEGREDO` (assina o token; sem
ela o login responde 503 e a dashboard abre sem exigir login — modo aberto) e
`FRAUS_CODIGO_DEV` (código de convite; sem ela ninguém nasce dev; código
errado é 403 explícito, nunca rebaixamento silencioso). No Next, o token vive
em cookie httpOnly (`fraus_sessao`) e é o degrau ZERO da credencial do proxy —
vence a chave `fra_` do deploy de propósito, ou o portão de papel nunca veria
o papel. A recusa de login é uniforme em status, texto e tempo (o scrypt
deriva mesmo para e-mail inexistente).

### Como subir

```bash
uv run uvicorn fraus.api.main:app --port 8001   # a API REAL, carrega os 3 modelos
cd dashboard && npm run dev
```

**Não suba `scripts/api_demo.py` achando que é a API.** Ele é o motor dublê:
devolve números sintéticos com cara de predição, e a dashboard não distingue.
Uma sessão já perdeu um dia inteiro com isso — inclusive os pesos por feature,
que saíam numa progressão `0,2 / 0,25 / 0,3` e passavam por peso de regressão.

**Como saber em qual você está, em uma linha:** `curl -s :8001/saude` responde
`{"status":"ok","motor":"real"}` ou `"motor":"duble"`. Desde a PR #32 os
caminhos dos artefatos ancoram na raiz do projeto, então o diretório de onde
você lança o uvicorn não decide mais o motor — mas confira mesmo assim.

### Comandos de verificação

```bash
uv run pytest -q                 # 767 passed, 1 deselected
uv run pytest -m lento           # o de minutos, obrigatório ao mexer no gerador
cd dashboard && npx tsc --noEmit # tipos
cd dashboard && npm run contraste # WCAG AA, por cálculo
```

---

## 3. As regras que governam este código

Não são preferências de estilo. Cada uma nasceu de um defeito real, e violá-las
é reintroduzir o defeito.

### 3.1 Ausência nunca vira zero

A regra mais importante do projeto. `None`/`null` e `0` significam coisas
diferentes e **não podem se confundir em lugar nenhum**:

- conversa sem fala do cliente tem `score: null`, não `0` — "o cliente não
  falou" não é "o cliente estava insatisfeito";
- conversa sem atendente humano tem `latencia_mediana_humano_s: null`, exibido
  como travessão e exportado como célula **vazia** no CSV — `0.0` numa coluna de
  tempo de resposta se lê como "respondeu na hora", e a conversa que nunca teve
  atendente apareceria como a mais ágil da operação;
- palavra acima do teto de medição tem `peso: null`, e palavra medida em zero
  tem `peso: 0` — "não medimos" e "medimos e não importou" são respostas
  diferentes;
- métrica não exportada é `null`, nunca `0%`.

Ordenação segue junto: nota e espera mandam a ausência **para o fim nos dois
sentidos** (`TabelaConversas.ausenciaPorUltimo`).

### 3.2 Sem horário, sem nota

Latência é uma das 39 features do fusor, com peso aprendido. Uma transcrição de
`.docx`/`.pdf` sem relógio não recebe nota, e a tela diz por quê.

Zerar os campos de tempo seria o caminho fácil e **zero não é neutro**: o modelo
aprendeu que resposta rápida acompanha cliente satisfeito, então a conversa
entraria como se toda resposta tivesse sido instantânea e a nota sairia melhor
que a verdade — sem nenhum erro aparecer. Ver `fraus/ingest/transcricao.py`.

### 3.3 O veredito é sempre derivado no servidor

`score`, `nota` e `categoria` nunca vêm do cliente. Campos com esses nomes no
corpo de uma requisição são **ignorados por construção** — há teste para
`/conversas/importar` e para `/ingestao`. O canal também: na ingestão ele vem
da **fonte cadastrada**, não do corpo.

A `nota` é derivada no Python e o front só exibe. Recalcular no JavaScript já
divergiu nas fronteiras 6/7 e 8/9 (arredondamento bancário contra meio-para-cima)
e fazia a tabela mostrar nota 7 ao lado de "Detrator".

### 3.4 Emoção pontua; ironia NÃO pontua mais, desde 04/09/2026

O fusor tem **39 features** (confira `fraus.fusor.NOMES_FEATURES`), de SETE
famílias. Emoção entrou no vetor em 21/08/2026 e continua lá. A **ironia
entrou junto e saiu em 04/09/2026**: medida no próprio corpus de treino
(B2W-Reviews01), a cabeça marca 74% das resenhas satisfeitas como irônicas
contra 9% das insatisfeitas — no corpus do fusor ela é um detector de
sentimento positivo, não de ironia, e o fusor aprendeu peso **+0,77** para
`ironia_prob_media`, empurrando ironia para SATISFEITO. Feature que mede outra
coisa que não o nome dela é pior que feature ausente. Ver
`docs/treinamento.md`, seção "A ironia sai do vetor".

A cabeça de ironia **continua carregada e obrigatória** (invariante 7) e
continua sendo lida por mensagem e exibida na dashboard — o que mudou é que
ela não pontua. A interface sempre manteve as leituras **visualmente separadas**
da nota, e isso vale independente de a feature pontuar ou não: encostar
"ironia 99%" na barra de satisfação convida a ler uma como causa da outra.

### 3.5 O que ficou de fora é relatado

Importação diz quantas linhas rejeitou e por quê. Análise diz quantas conversas
cortou. O adaptador da Totalk diz **o que inferiu**. "Importado com sucesso" sem
a contagem de rejeitadas esconde exatamente a linha que precisa de conserto.

### 3.6 Estado vazio nomeia o próximo passo

Nada de "sem dados". O estado vazio diz o endpoint ou o notebook que preenche
aquilo. Ver `components/EstadoVazio.tsx`.

### 3.7 Ressalva repetida vira ruído

Já corrigido duas vezes: o aviso de métrica suspeita era por cartão (3×) e virou
por cabeça; a prosa do desprezo/ironia era por mensagem (até 19×) e virou uma
vez na legenda do painel. Se você repetir uma explicação em cada item de uma
lista, ela para de ser lida.

---

## 4. Mapa do código

### Back — `fraus/`

| arquivo | o que é |
|---|---|
| `modelos.py` | modelo canônico: `Conversa`, `Mensagem`. Timestamp **timezone-aware** obrigatório |
| `fusor.py` | `LogisticRegression` + `StandardScaler`. `NOMES_FEATURES` é o contrato de 35 |
| `resumo.py` | ficha operacional: contagem por autor, latências **separadas** bot/humano, `desfecho` |
| `indicadores.py` | NPS, CSAT, contenção, série diária |
| `credencial.py` | chave de fonte (`frs_`): gerar, hash, conferir em tempo constante |
| `acesso.py` | chave de acesso (`fra_`) e a mestra — mesmo desenho do `credencial.py` |
| `db.py` | SQLite. `_fonte()` remove `chave_hash` **na origem** |
| `sinais/texto.py` | BERTimbau de satisfação — **o único que pontua** |
| `sinais/emocao.py` | 7 de Ekman + desprezo derivado (Plutchik, média geométrica) |
| `sinais/ironia.py` | binária. **Ver pendência 1** |
| `sinais/palavras.py` | peso por palavra via **oclusão** + vocabulário comparado |
| `sinais/tempo.py` | latências. `latencias_da_conversa` é pública de propósito |
| `ingest/csv_driver.py` | o driver **canônico** |
| `ingest/totalk.py` | adaptador do export da Totalk |
| `ingest/transcricao.py` | prosa (`Autor: mensagem`) de docx/pdf |
| `ingest/arquivos.py` | decide o formato e traduz erro em mensagem útil |
| `ingest/gerador_ironia.py` | corpus sintético blindado contra vazamento |
| `api/main.py` | ~1200 linhas. `criar_app(banco, motor, raiz)` recebe tudo por parâmetro |
| `assinatura.py` | HMAC de webhook (Standard Webhooks): `whsec_<base64>`, chave = base64 **decodificado**, assina `{id}.{timestamp}.{corpo}`, janela de 5 min |
| `api/registro.py` | o miolo de `montar → pontuar → derivar → gravar`, compartilhado por `/ingestao` e `/integracoes/webhook/{id}`; é onde mora `resumo_validacao` |
| `api/rotas/webhook.py` | `POST /integracoes/webhook/{fonte_id}` — o porteiro na ordem identidade→autoridade→parse, com registro de entrega em `entregas_webhook` |

### Front — `dashboard/`

Telas: `/` (visão geral), `/atendimentos`, `/analisar`, `/modelo`,
`/configuracoes`, `/integracoes`.

`lib/api.ts` é a **única** porta para a API — tipos e funções. `lib/formato.ts`
concentra formatação (`formatarEsperaOuTraco` é quem transforma `null` em `—`).

`components/CabecasDeLeitura.tsx` é **compartilhado** entre o simulador e a
análise. Não faça uma segunda cópia: duas cópias de um painel que explica um
modelo envelhecem separadas, e a que envelhece é sempre a que ninguém olha.

---

## 5. Design — leia antes de mexer em pixel

**`dashboard/DESIGN.md` e `dashboard/PRODUCT.md` são obrigatórios.** O mundo
visual se chama **"Pauta"** e a regra mestra é:

> Acima da linha é o que foi **DITO**. Abaixo da linha é o que foi **MEDIDO**.

Encoding que atravessa tudo:

- **âmbar** (`--dito`) = fala, texto, emoji;
- **azul** (`--medido`) = score, probabilidade, tendência;
- **dourado** (`--primary`) = ação e foco, **nunca dado**.

O `--primary` é o dourado do R da logo, medido do arquivo:
`oklch(0.78 0.085 80)`. Ele convive com o âmbar porque o que os separa é o
**croma** (0,085 fosco contra 0,15 saturado), e porque nunca dividem superfície.
Detalhes e o par de risco em `DESIGN.md` §3.3.

**Intocáveis declarados pelo João:** os textos de honestidade, o gráfico
sobreposto NPS × latência, e âmbar=dito / azul=medido.

`npm run contraste` verifica AA **por cálculo**, incluindo o rótulo dentro do
botão. Rode depois de mexer em cor.

---

## 6. Skills a usar

Instaladas em `~/.claude/skills/`. As que servem a este projeto:

| skill | quando |
|---|---|
| **impeccable** | qualquer trabalho de UI. Modo **Operate** (é ferramenta de dados, não landing page). `PRODUCT.md` e `DESIGN.md` já existem — ela os lê |
| **taste-skill** | auditoria de frontend, antes de propor redesenho |
| **redesign-skill** | auditoria de execução: ritmo tipográfico, densidade, estados |
| **security-audit** | **relevante de verdade aqui** — API sem autenticação nas rotas de leitura + PII de cliente real |
| **superpowers:brainstorming** | antes de planejar feature nova |
| **superpowers:systematic-debugging** | antes de caçar bug |

As demais (`access`, `configure`, `silence`, `who`, `decisions`,
`flow-patterns`) são do assistente Discord do João, **não deste projeto**.

Ao invocar a `impeccable`, não deixe ela redirecionar a paleta: as decisões de
cor estão fechadas e documentadas.

---

## 7. Pendências, em ordem

O `README.md` tem a lista canônica e foi atualizado hoje. Resumo:

### P0 — Retreinar a ironia — DÍVIDA ASSUMIDA, não mais pré-requisito

A cabeça reporta acurácia `1.0` e erra **6 em 10** falas sinceras de
atendimento, com 0,999 de confiança. Causa medida: vazamento de marcador de
discurso no gerador. **O gerador já foi corrigido**; falta rodar
`notebooks/04_treino_ironia.ipynb` no Colab e substituir
`modelos/bertimbau-ironia/`.

**O risco voltou a ser evitado em 04/09/2026, e não por causa deste retreino.**
Entre 21/08 e 04/09 a ironia pontuava, e o score carregava esse vazamento. Ela
saiu do vetor em 04/09 por um motivo diferente e mais grave (ver §3.4): no
corpus de treino do fusor ela funciona como detector de sentimento positivo.
Com ela fora, **o vazamento da cabeça não se propaga mais para a nota** — mas
ela continua obrigatória para a API subir e continua sendo exibida por
mensagem na dashboard, com a ressalva de confiabilidade que a tela já mostra.
Rodar o notebook 04 continua valendo; só deixou de ser urgente.

Verificação: `uv run pytest tests/test_ironia_dominio.py`. Se o modelo melhorar,
**aperte os limiares desse arquivo junto** — limiar frouxo que nunca falha não
mede nada. E se `test_acuracia_perfeita_do_relatorio_vale_so_no_corpus_gerado`
passar a falhar, a limitação foi superada e os textos de ressalva na interface
precisam ser reescritos, não mantidos por inércia.

### P0 — A ironia continua escapando do score

**RESOLVIDO em 08/09/2026 o que travava esta seção:** o artefato foi
retreinado no contrato de 39 (`n_features_in_ = 39`, acurácia e F1-macro
**0,950**, contra 0,943 do de 38) e a API real sobe — verificado nesta data,
`{"status":"ok","motor":"real"}`. A recusa anterior era o comportamento correto
da invariante 7, não um bug: `Fusor.carregar` valida a dimensão. Confira
qualquer artefato com `uv run python scripts/conferir_fusor.py`.

**O que continua P0 é o caso em si:** a frase canônica segue saindo promotor
sempre que o relógio não a contradiz.

A feature que ataca o caso foi IMPLEMENTADA em 04/09/2026 e e a razao de o
contrato ter subido para 39: `incongruencia_situacao_negativa` marca elogio
convivendo com situacao negativa de atendimento na mesma fala. E a unica das
seis que alcanca a frase canonica, porque nao precisa de um segundo termo
polar no lexicon:

```
"que atendimento maravilhoso, so esperei 3 horas"            -> dispara
"Nossa, eu realmente gostei de ficar 5h esperando"           -> dispara
"esperei 3 horas e ninguem resolveu"        (reclamacao)     -> nao dispara
"nao gostei de ficar esperando"             (negado)         -> nao dispara
```

**O peso, agora medido:** −0,193 no eixo satisfeito−insatisfeito. A feature não
nasceu morta (nenhuma das 39 ficou com |peso| < 0,02, então o risco da
invariante 10 não se concretizou), e ainda assim **não vence** os +2,78 de
`texto_prob_satisfeito_media`. Nenhuma feature agregada de conversa reverte uma
probabilidade saturada por mensagem — é essa a conclusão que levou à
**contestação** de 08/09/2026, que marca em vez de corrigir (seção Feita,
abaixo), e à recusa de tentar a feature 40 cruzando tempo × texto (o corpus não
pode ensiná-la).
Ao conferir o artefato novo, o peso dela precisa sair NEGATIVO no eixo
satisfeito-menos-insatisfeito, como as outras cinco de incongruencia. Peso
positivo significaria que ela virou detector de satisfacao -- o mesmo modo de
falha que tirou a ironia do vetor -- e ai ela sai tambem.

Medicao feita ANTES de aceitar (invariante 10), no B2W, que e o corpus que da o
TEXTO do treino: dispara em 4,10% / 2,65% / 1,75% dos rotulos insatisfeito,
neutro e satisfeito. Tres rotulos, gradiente suave, razao 2,3:1 -- sinal, nao
previsor unilateral.

**Armadilha que quase me pegou aqui, e que vale para qualquer feature nova:**
medir no corpus do SIMULADOR dava zero nos tres rotulos, o que sugeriria peso
zero. Errado -- `FRASES_POR_ROTULO` NAO treina o fusor. O notebook 02 usa 400
frases do B2W por classe e pega do simulador so a ESTRUTURA da conversa. O
simulador importa para a guarda de previsor unilateral, nao para o peso. As
frases foram cruzadas nos tres rotulos mesmo assim, senao a guarda passaria por
vacuidade sobre a feature nova.

**A regra que vale sempre que o contrato mudar:** `Fusor.carregar` valida
`n_features_in_` contra `len(NOMES_FEATURES)` e levanta `FusorIncompativelError`
— a API não sobe com artefato desatualizado, e isso é o comportamento correto
da invariante 7, não um bug a consertar. Rodar o notebook 02 e substituir
`modelos/fusor.joblib` é o que destrava. Ver `docs/treinamento.md`.

### Feita — Autenticação, antes de hospedar

Resolvida em `feat/autenticacao` (300 testes, `tests/test_autenticacao.py`).
`FRAUS_CHAVE_MESTRA` ausente mantém a API aberta, como antes; presente, exige
`Authorization: Bearer` (mestra ou chave de acesso `fra_`) em toda rota, exceto
`POST /ingestao`, que segue só com chave de fonte `frs_`. Gerenciar chaves
(`POST`/`GET`/`DELETE /acesso/chaves`, e a chave de fonte) é privilégio
exclusivo da mestra — chave de acesso tentando recebe 403. A dashboard não fala
mais com a API direto: passa pelo proxy `app/api/fraus/[...caminho]/route.ts`,
que anexa a chave de acesso no servidor Next e nunca a deixa chegar ao
navegador. Ver `README.md` e `docs/hospedagem.md`. Falta só mesclar a branch em
`main`.

### Feita — A porta destrancada e o teto de `/ingestao` — 08/09/2026

Duas coisas que o levantamento de 08/09 achou, e uma que ele achou mentindo.

**A porta destrancada.** Com `FRAUS_CHAVE_MESTRA` + `FRAUS_JWT_SEGREDO` e sem
`FRAUS_CODIGO_CONVITE`, três chamadas (`registrar` → `entrar` → `GET
/conversas`) leem tudo que a mestra protege. **A tranca já existia** desde
02/09 — o que não existia era alguém dizer que ela estava aberta: os avisos de
boot só falavam de *ausência* de autenticação, e essa combinação não é
ausência, é as duas portas ligadas com uma delas destrancada. Agora
`aviso_de_porta_destrancada` (`fraus/api/main.py`) grita na subida. Continua
sendo aviso e não recusa de subir: cadastro aberto é o certo em `localhost`,
que é o uso declarado. `tests/test_aviso_de_porta_destrancada.py`.

**O teto de `/ingestao`.** 120 escritas por minuto, por fonte, com
`Retry-After` — OWASP API4:2023. Ele vive **na rota**, depois de
`fonte_autorizada`, e não no middleware onde mora o teto de `/auth/*`: o
middleware roda antes da autenticação e só poderia contar pela chave crua, mas
`credencial.fonte_da_chave` lê o id **sem conferir hash**, então um anônimo
mandando `frs_3_lixo` gastaria a janela da fonte 3. Defesa que o atacante usa
como arma é pior que nenhuma. `tests/test_vazao_de_ingestao.py`.

**A documentação que mentia.** O docstring de `fraus/credencial.py` afirmava
que "o resto da API continua sem autenticação" — verdade quando escrito, falso
desde 25/08. E o `CLAUDE.md` dizia "38 chaves de feature" na invariante 9 e
"(35)" no mapa: dois números de duas revisões, nenhum o vigente (**39**).
Corrigidos, e agora `test_o_CLAUDE_md_declara_o_mesmo_numero_de_features`
amarra o número do `CLAUDE.md` a `len(NOMES_FEATURES)` — a documentação que
governa toda sessão de agente passa a envelhecer com barulho.

### Feita — A contestação: o tempo contesta o elogio — 08/09/2026

A frase canônica sai promotor sempre que o relógio não a contradiz, e agora ela
**avisa**. Quando `score > 95` e `latencia_mediana_s > 180`, `/conversas` e `/conversas/{id}`
devolvem `contestacao` — derivada na leitura, sem coluna nova e sem chamada de
modelo, valendo retroativamente para o que já está no banco. A tabela de
Atendimentos e a tela do atendimento mostram a marca; o CSV leva a coluna.

**Ela marca, não corrige** — nenhum agregado muda, e há teste provando isso
(`test_o_atendimento_contestado_continua_contando_no_NPS`). Tirar do agregado
esvaziaria o indicador em silêncio se o limiar estivesse mal calibrado.

**Por que não virou feature 40**, e esta é a parte que economiza a próxima
sessão: o corpus não pode ensinar a interação tempo × texto. O texto vem do
B2W, a latência sai de distribuição **por rótulo**, e satisfeito-e-lento está
rotulado *satisfeito* por construção — a feature nasceria com peso **positivo**,
repetindo o modo de falha que tirou `ironia_prob_*` do vetor em 04/09. Isso é
leitura do corpus, **não experimento**; medir custaria um retreino e a API fora
do ar. Fica condicionado a corpus de atendimento real, a mesma condição da
cabeça de ironia.

Desenho, alternativas recusadas e as referências em
`docs/superpowers/specs/2026-09-08-abstencao-por-contestacao-design.md`.

O único número sem procedência é o **limiar de score em 95** — o de tempo vem
de IJHCI 2025. Está declarado assim no código e na spec.

**Verificado contra a API real** (`motor: real`), varrendo a latência com a
mesma fala: 99,92 em 10 s · 99,70 em 179 s · **99,69 em 181 s (contestada)** ·
**99,21 em 300 s (contestada)** · 93,25 em 600 s · 17,19 em 1800 s · 0,00 em
10800 s. A janela útil é de ~3 a ~9 minutos, e a estreiteza é a feature: abaixo
não há contradição a marcar, acima o modelo já acerta sozinho. **O "99,93" que
circulava aqui era o caso rápido** — com três horas dentro do log a conversa
pontua 0,00, e faltava esse qualificador em todo lugar.

### P0 — O tempo domina o score fora da distribuição de treino

**Achado de 08/09/2026, e é maior que o trabalho que o encontrou.** Atribuição
de uma conversa com 3 h de espera e uma única fala do cliente que a cabeça de
texto lê como 86% satisfeito:

```
latencia_primeira_resposta_s   -85,405
duracao_total_s                -35,759
latencia_mediana_s             -20,569
latencia_p90_s                 -12,326
texto_prob_satisfeito_media     +4,574   ← o texto inteiro
```

O tempo pesa **20× o texto**. As features de latência não têm teto e o corpus
de treino nunca passou de minutos (medianas 5/30/200 s): em 3 h o z-score do
`StandardScaler` explode e o relógio assume a nota. A conversa sai em `4,4e-24`.

O critério do próprio `docs/treinamento.md` diz o que isso é: *"se as features
que lideram forem as circunstanciais (tempo, contagem de turnos), procure o
vazamento."* É a **invariante 10 em runtime** — a guarda de vazamento olha a
distribuição no corpus, e o corpus não tem latência de três horas.

**MEDIDO em 08/09/2026** com `uv run python scripts/medir_dominio_do_tempo.py`
(instrumento novo, roda em segundos e não carrega BERTimbau nenhum):

| latência | contrib. tempo | contrib. texto | razão |
|---:|---:|---:|---:|
| 60 s | +0,48 | +4,57 | 0,1× |
| 300 s | −2,97 | +4,57 | 0,7× |
| **411 s** | **−4,57** | **+4,57** | **1,0× — o empate** |
| 600 s | −7,29 | +4,57 | 1,6× |
| 1800 s | −24,54 | +4,57 | 5,4× |
| 10800 s | −153,96 | +4,57 | 33,7× |

**O relógio empata com o texto em 411 s (6,9 min) e manda a partir dali.** Isso
é **4,0 desvios** acima da média de `latencia_mediana_s` no treino (67,0 s,
sigma 85,9 s) — ou seja, o ponto em que o relógio toma a nota está **fora** do
que o corpus mostrou ao modelo. Cada segundo de espera vale 0,0144 de
contribuição, **sem teto**.

O laudo bate com a varredura contra a API real: em 600 s o score já tinha caído
para 93,25, e em 300 s ainda estava em 99,21.

**Três saídas, e a terceira não é obviamente errada:**

1. **Escala log** (`log1p`) nas quatro features de tempo. É a mais defensável
   tecnicamente: o simulador gera latência **log-normal** de propósito
   (`docs/treinamento.md`), então a feature é de cauda pesada por construção e
   o `StandardScaler` — que pressupõe algo próximo de normal — é a ferramenta
   errada para ela. Custo: retreino, e os nomes `latencia_*_s` passariam a
   mentir sobre a unidade, então o contrato de 39 chaves mudaria de nome junto.
2. **Clipar num teto** (algo perto de 600 s). Mais barato de explicar e mantém
   os nomes. Custo: perde a distinção entre 10 min e 3 h — o que talvez não
   seja perda, porque acima de certo ponto "muito lento" é só "muito lento".
   Também exige retreino.
3. **Aceitar e declarar** como limitação. Custo zero em código, e o preço é
   defender numa banca um modelo em que o relógio vence o texto a partir de
   sete minutos — num produto cuja tese é justamente que o texto revela o que o
   relógio não mostra.

Decisão do dono do projeto — **não tomada**.

### Feita — Os três sinais invertidos do fusor — 08/09/2026

`conferir_fusor.py` marca três features como suspeitas desde o fusor de 35, e o
aviso sobreviveu a todos os retreinos: `texto_prob_satisfeito_ultima` (−0,49),
`emoji_frac_positivos` (−0,19) e `emoji_frac_negativos` (+0,59), todas com
sinal oposto ao esperado. Lido isolado, o terceiro diz "mais emoji negativo
empurra para satisfeito".

**A leitura isolada é que está errada.** Cada uma tem uma irmã forte com o sinal
certo — `emoji_score_medio` (+1,55), `texto_prob_satisfeito_media` (+2,78) — e
no corpus do simulador elas se movem quase juntas:

```
corr(score_medio, frac_positivos) = +0,941
corr(score_medio, frac_negativos) = -0,903
corr(frac_positivos, frac_negativos) = -0,885     (254 de 300 conversas)
```

Features colineares dividem um efeito único: a forte fica com ele, a redundante
vira termo de correção com sinal frequentemente oposto. **O efeito líquido da
família é o que se interpreta**, e ele aponta certo: de 4 emojis negativos a 4
positivos a contribuição somada da família emoji vai de **−0,06 para +1,93**;
no texto, de P(satisfeito) 0,05 a 0,95, de **−2,23 para +4,56**.

`uv run python scripts/investigar_sinais_invertidos.py` reproduz tudo em
segundos, sem BERTimbau.

**O aviso do `conferir_fusor.py` continua saindo, de propósito** — o dia em que
ele parar de sair para a quarta feature é o dia em que ele deixa de servir. Ele
agora aponta para este laudo, para ninguém reinvestigar o mesmo caso a cada
retreino.

**Uma armadilha de sonda que quase entrou no laudo:** varrendo só emoji polar,
`corr(frac_pos, frac_neg)` dá **−1,000** — mas isso é artefato, porque com
todos polares as duas somam 1 por construção. Emoji neutro quebra a soma. O
número honesto é o do corpus, acima.

### Feita — O teto de vazão do webhook — 08/09/2026

Fechou a metade que sobrou de manhã: `/ingestao` ganhou teto e o webhook não,
sendo que ele é o **outro** caminho de escrita pela rede, com a mesma exposição
(OWASP API4:2023) e **pior** em um aspecto — a rota é anônima por desenho, e
cada entrega aceita roda o Motor inteiro.

120 entregas por minuto por fonte, mesmo número de `/ingestao` de propósito: as
duas rotas fazem o mesmo trabalho depois de autenticar e custam o mesmo. Mas
**contadores separados** — uma fonte pode receber pelos dois caminhos, e janela
compartilhada faria o volume de uma rota cortar a outra.

**Três decisões que valem ser lidas antes de mexer:**

1. **O teto vive logo depois do HMAC**, e aqui isso pesa mais que em
   `/ingestao`: o `fonte_id` vem **na URL**, então qualquer anônimo escolhe
   contra qual fonte bater. Contar a tentativa recusada transformaria o teto no
   caminho mais curto para derrubar a integração alheia.
2. **O 429 é `Recusa`, não `HTTPException` direta** — toda recusa desta rota
   vira linha em `entregas_webhook`, e um 429 invisível ali seria justamente a
   recusa que o operador precisava ver: é ela que explica por que a plataforma
   começou a retentar. `Recusa` ganhou `cabecalhos` para o `Retry-After`.
3. **Isso só é seguro porque `entrega_ja_vista` conta apenas veredito
   "aceita".** Se um dia ela passar a contar qualquer veredito, este 429 vira
   uma forma de queimar um `webhook-id` legítimo — a plataforma retenta o mesmo
   id e leva "duplicada", e o atendimento some em silêncio. Há teste para isso
   (`test_o_429_nao_queima_o_webhook_id_para_a_retentativa`).

### P0 — Hospedagem — BLOQUEADA POR CAPACIDADE DA ORACLE, 11/09/2026

> Estado completo, com o que foi medido e o que foi descartado:
> **[notas/2026-09-11-deploy-na-oracle.md](notas/2026-09-11-deploy-na-oracle.md)**

A API **não cabe em serverless** (torch instalado mede 769 MB contra o teto de
500 MB da Vercel, mais 1,3 GB de pesos). Precisa de container com volume e
~2 GB de RAM.

**Tudo está pronto menos a máquina.** A `oci` CLI está autenticada, a VCN e a
Security List existem (22, 80 e 443 abertas), e
`scripts/provisionar_oracle.sh <IP>` executa o deploy inteiro num comando. O
`Dockerfile` foi **ensaiado em container real** e devolve `motor: real` com
predição correta — inclusive `None` para conversa sem fala do cliente.

O que falta é hardware: `Out of capacity for shape VM.Standard.A1.Flex`, em
~35 tentativas. Já descartado por medição — não é a imagem, não é o tamanho do
shape (1/6 e 2/12 falham igual), não é cota (`used 0, available 2`), e **não é
resolvível trocando de região**: recurso Always Free só existe na região de
origem, que é `sa-saopaulo-1`. Um laço destacado segue pedindo a máquina.

A alavanca que sobra é upgrade para **Pay As You Go** — mantém a franquia
gratuita e costuma destravar a fila de A1, mas exige cartão e passa a cobrar
qualquer coisa além dela. Decisão do João.

### P1 — O site público da documentação

O workflow, o recorte e as três camadas de guarda contra vazamento estão
prontos e testados. Faltam três valores que só o João pode criar no
repositório privado: o secret `DEPLOY_KEY_DOCS` e as variáveis `REPO_DOCS` e
`FRAUS_URL_DASHBOARD`. Passo a passo na nota citada acima.

### P2 — Dívida de escala

`GET /conversas?de=&ate=` e `GET /indicadores?de=&ate=`; agregado de léxico por
classe e de tempo mediano de resposta.

### P2 — Decisões do João

Empresa fictícia (não definida), tema claro (dark-only hoje), pin do
`scikit-learn==1.6.1` no `pyproject.toml`, e remover `content/fraus` da raiz.

---

## 8. Armadilhas já pagas — não repita

0. **A vitrine NÃO rola na horizontal — e o `scrollWidth` maior que a viewport
   não prova que role.** Medido em 08/09/2026 na `main` e na
   `feat/tipografia-e-heroi`, com resultado idêntico nas duas: em 360/390/440px
   o `document.scrollWidth` dá viewport + 96px, e mesmo assim
   `window.scrollTo(9999, 0)` deixa o `scrollX` em **0**. Motivo:
   `body { overflow-x: hidden }` (globals.css) **propaga para o viewport**,
   porque o `html` não declara overflow — então o excesso é recortado e não
   vira barra de rolagem. Os 96px são o `fixed inset-0` do ateliê (que se
   dimensiona pelo viewport de LAYOUT, e portanto acompanha o excesso em vez de
   causá-lo) mais a esteira `w-max`, que é faixa rolante por desenho.
   Nenhum conteúdo fica inalcançável: o container de conteúdo mede exatamente a
   viewport.

   **Antes de "consertar transbordo" nesta vitrine, meça `window.scrollX` depois
   de um `scrollTo`, não o `scrollWidth`.** Uma sessão já gastou uma hora
   perseguindo isso.

   Duas armadilhas de método que apareceram no mesmo dia: **a primeira carga
   depois de `npm run dev` não é representativa** (ela mediu "sem transbordo" e
   a segunda mediu 96px — o servidor ainda estava compilando), e uma sonda que
   procura o culpado do transbordo precisa ignorar quem tem ancestral
   recortante, senão lista só vítimas.

1. **`fullPage` do Playwright/headless NÃO dispara `whileInView`.** Confirmado
   de novo em 08/09/2026: a tela de Atendimentos sai com a tabela em branco na
   captura, e o DOM desmente — o HTML servido tem o conteúdo. Capture por
   viewport com rolagem, ou confira o HTML com `curl` em vez da imagem. Pelo
   mesmo motivo, `curl` no HTML é a prova mais barata de que algo **não**
   depende de JavaScript.


1. **Data da Totalk é `MM/DD/YYYY`**, não `DD/MM`. Lida como brasileira, espalha
   as mensagens por cinco meses e a latência sai absurda **em silêncio**.
2. **Não mate servidor com `pkill`** — não casa `npx next start`. Use a porta:
   `Get-NetTCPConnection -LocalPort 3000 -State Listen | Stop-Process -Force`.
3. **Não rode `npm run build` com o `next dev` do João no ar** — invalida os
   hashes dos chunks e a tela vira 403 em tudo. Já foi diagnosticado como "tela
   feia" uma vez.
4. **CORS é lista explícita**: `FRAUS_ORIGENS` libera 3000/3001. Teste na 3002 e
   a chamada do navegador falha — foi assim que descobrimos que a proteção
   funciona.
5. **Coluna ausente é defeito do ARQUIVO**, não da linha: o driver deixa o
   `KeyError` propagar e a borda HTTP traduz em 400 nomeando a coluna. Não
   capture no driver.
6. **`<input type=file>` só dispara `change` quando o valor muda.** Zere
   `evento.target.value` ou reenviar o mesmo arquivo não faz nada.
7. **Oclusão quebra expressão fixa**: "Bom dia" sem "dia" vira "Bom" solto, e
   "dia" recebe peso alto e enganoso. Está declarado na interface — não trate
   como bug.
8. **Rota de escrita com credencial própria precisa ser isenta no middleware
   de chave de acesso**, ou ele a recusa com 401 **antes** de olhar a
   credencial dela. `/integracoes/webhook/{id}` tem assinatura própria — a
   plataforma externa não tem, nem pode ter, uma chave `fra_`. Em
   `fraus/api/seguranca.py`, a tupla `ISENTAS` (`/ingestao`, `/acesso/estado`,
   `/saude`) compara caminho por **igualdade**, e não serviria aqui: o caminho
   do webhook carrega `{fonte_id}` variável. Por isso a isenção do webhook é
   uma condição **separada**, ao lado de `ISENTAS` no mesmo `or` —
   `caminho.startswith(PREFIXO_WEBHOOK + "/")`. O defeito só aparece com a
   mestra **ligada**, isto é, só em produção: o log de entregas fica vazio
   dizendo "não chegou nada" enquanto a plataforma recebe 401 em cada
   tentativa, e nada no ambiente de desenvolvimento (API aberta) revela o
   problema.
9. **`PRAGMA foreign_keys` vale por CONEXÃO no SQLite**, não por banco. Ligá-lo
   uma vez na criação do esquema não teria efeito nenhum nas conexões
   seguintes — cada `_conectar()` precisa executá-lo de novo — e sem isso o
   `ON DELETE CASCADE` de `entregas_webhook` seria documentação em vez de
   comportamento: apagar uma fonte deixaria as entregas órfãs, apontando para
   um `fonte_id` que ninguém mais consegue consultar.
10. **`str(ValidationError)` do Pydantic v2 embute o `input_value` recebido** —
    para JSON malformado, até o corpo cru inteiro; para campo de tipo errado,
    o valor daquele campo. Gravar essa mensagem num log ou devolvê-la no
    `detail` de uma resposta persiste ou vaza PII de cliente real. Por isso
    `fraus/api/registro.py` tem `resumo_validacao`, que usa só `loc` (onde) e
    `type` (o que) de `erro.errors()`, e descarta `input`/`msg`/`ctx` de
    propósito — qualquer um deles pode carregar o valor recebido.
11. **Dedupe de webhook só pode contar entregas com veredito `aceita`.**
    `entrega_ja_vista` filtra por `veredito = 'aceita'` de propósito: se
    contasse qualquer veredito, uma recusa registrada — inclusive de um
    anônimo com assinatura inválida, já que a rota é anônima por desenho —
    faria a entrega legítima seguinte com o mesmo `webhook-id` virar
    "duplicada", e o atendimento se perderia em silêncio. Tem variante
    auto-infligida: um 503 (variável de segredo ausente) grava a linha, o
    operador corrige a variável no ambiente e reinicia, e a retentativa da
    plataforma some como se já tivesse entrado.

---

## 9. Convenções

Commits em **conventional commits**, assunto **sem acento**, corpo em pt-BR
explicando **por quê** (veja o histórico — a régua é alta e é intencional; esses
commits são material de defesa do TCC).

**Não assine commits com Claude como co-autor.**

Comentários e docstrings em pt-BR sem acento no código Python; texto de
interface em pt-BR **com** acento.
