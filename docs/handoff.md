# Handoff — Fraus, 31/08/2026 (atualizado — LP na raiz e autenticação de usuário)

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

## 2. Estado atual — 31/08/2026

| | |
|---|---|
| Branch | `feat/lp-e-autenticacao` (webhook foi mesclado na main via PR #20; agora: LP pública na raiz, telas em `/dashboard/*`, login/cadastro com JWT e papéis dev/usuario — ver spec `docs/superpowers/specs/2026-08-31-lp-e-autenticacao-design.md`) |
| Testes | **595 passed, 1 deselected** |
| Modelos | os três em `modelos/`, 1,3 GB, **fora do git** |
| API | `uv run python scripts/api_demo.py` → :8000 |
| Dashboard | `cd dashboard && npm run build && npx next start -p 3000` |

Sem `FRAUS_CHAVE_MESTRA` no ambiente, a API sobe **aberta**, como sempre — é o
modo de desenvolvimento local e o que os comandos acima assumem. Definir a
variável liga a exigência de `Authorization: Bearer` em toda rota, exceto duas,
que têm credencial própria: `POST /ingestao` (chave de fonte `frs_`) e
`POST /integracoes/webhook/{fonte_id}` (assinatura HMAC no corpo). A segunda é
**anônima por desenho** — a plataforma externa não tem, nem pode ter, uma chave
`fra_`; ver a armadilha 8. Ela é uma porta pública de **escrita**: quem publica
a API na internet precisa saber que ela existe. Ver `README.md` e
`docs/hospedagem.md`.

### A LP e a autenticação de usuário, em um parágrafo cada

**A raiz virou vitrine.** `/` descreve o produto (tese, sete sinais,
honestidade metodológica) e as telas moram em `/dashboard/*`, com redirect das
rotas antigas. Nenhum número da LP é inventado — 38 features e sete sinais são
fatos do código, e não há acurácia fabricada nem depoimento. **Isso impõe uma
obrigação:** quando `NOMES_FEATURES` mudar, os números da LP mudam junto
(`dashboard/app/page.tsx`, `lp/Contador.tsx`, `lp/Constelacao.tsx`). Em
04/09/2026 o contrato foi a 38 e a LP ficou anunciando 35 — número falso numa
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
uv run python scripts/api_demo.py            # :8000, carrega os 3 modelos
cd dashboard && npm run build && npx next start -p 3000
```

O boot da API imprime qual motor subiu. Se aparecer "motor dublê", os pesos não
estão em `modelos/` — números sintéticos, **não** predição.

### Comandos de verificação

```bash
uv run pytest -q                 # 551 passed, 1 deselected
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

Latência é uma das 38 features do fusor, com peso aprendido. Uma transcrição de
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

O fusor tem **38 features** (confira `fraus.fusor.NOMES_FEATURES`), de SETE
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

O fusor está em dia: contrato e artefato batem em **38 features** desde
04/09/2026, acurácia 0,943. Confira a qualquer momento com
`uv run python scripts/conferir_fusor.py`.

O que continua aberto é o caso que deu origem a tudo isto. A frase canônica do
projeto pontua **99,95 / nota 10 / promotor**:

```
"que atendimento maravilhoso, so esperei 3 horas"
```

As cinco features de `incongruencia_*` dão **0,0** nela e disparam numa frase
de satisfação genuína — hoje elas pegam entusiasmo, não ironia. A causa é
estrutural, não bug: todas são função de `anotar_texto`/emoji, e "só esperei 3
horas" não tem palavra polar no SentiLex; é negativo por **pragmática**. E a
cabeça de texto classifica a frase como satisfeito com 0,858, dominando o eixo.

Rota proposta, já pesquisada e desenhada:
`docs/superpowers/specs/2026-09-04-incongruencia-implicita-design.md` —
`incongruencia_situacao_negativa`, lista curada de padrões de queixa de
atendimento (espera, transferência, cobrança) que só dispara quando há elogio
léxico na mesma fala. Custo: vetor vai a 39 features, **exige rodar o notebook
02 de novo**, e exige frases novas no simulador nos três rótulos para não
repetir o vazamento unilateral que já pegou `incongruencia_hiperbole`.

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

### P1 — Hospedagem

`Dockerfile` e `docs/hospedagem.md` prontos. A API **não cabe em serverless**
(torch instalado = 497 MB contra teto de 250 MB da Vercel, mais 1,3 GB de
pesos). Precisa de container com volume e ~2 GB de RAM. O front na Vercel é um
comando — e mostra "API não respondeu" até a API ter endereço.

### P2 — Dívida de escala

`GET /conversas?de=&ate=` e `GET /indicadores?de=&ate=`; agregado de léxico por
classe e de tempo mediano de resposta.

### P2 — Decisões do João

Empresa fictícia (não definida), tema claro (dark-only hoje), pin do
`scikit-learn==1.6.1` no `pyproject.toml`, e remover `content/fraus` da raiz.

---

## 8. Armadilhas já pagas — não repita

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
