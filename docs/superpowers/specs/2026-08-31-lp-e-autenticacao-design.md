# Landing page e autenticação de usuário — design

**Data:** 31/08/2026
**Estado:** aprovado pelo dono do projeto (decisões de 31/08/2026), aguardando plano de implementação

---

## 1. O problema

O Fraus não tem porta de entrada. Quem abre a raiz da dashboard cai direto na
ferramenta — sem saber o que o produto é, o que ele mede e o que ele **não**
mede. Para a banca, o produto aparece sem a própria tese na frente.

E não existe o conceito de **usuário**. As credenciais de hoje são técnicas e
resolvem outro problema: a mestra e as chaves `fra_` autenticam *processos*
(a dashboard, um integrador), as chaves `frs_` autenticam *fontes*. Nenhuma
delas diz **quem** está olhando a tela, e nenhuma distingue quem opera a
ferramenta de quem só analisa os números.

## 2. O que foi decidido, e o que foi recusado

### 2.1 A LP mora na raiz; a dashboard muda para `/dashboard`

A raiz (`/`) vira a página pública do produto: a tese, os sete sinais, a
honestidade metodológica e o botão de entrar. As telas de trabalho migram para
`/dashboard/*` (`/dashboard`, `/dashboard/atendimentos`, `/dashboard/analisar`,
`/dashboard/modelo`, `/dashboard/configuracoes`, `/dashboard/integracoes`,
`/dashboard/grafo`), protegidas por sessão.

Recusado: LP em rota secundária (`/sobre`) com a dashboard na raiz. O visitante
cairia dentro da ferramenta sem contexto — exatamente o defeito que a LP
existe para corrigir. É também o padrão que os produtos de referência seguem
(Stripe, Revolut): raiz vende, `/dashboard` trabalha.

As rotas antigas **redirecionam** para as novas. Link salvo, favorito e
documentação anterior não podem quebrar em silêncio.

### 2.2 Dois papéis: `dev` administra, `usuario` analisa

| Papel | Telas | O que pode |
|---|---|---|
| `dev` | todas | tudo: Integrações, Modelo, Configurações, chaves, importação |
| `usuario` | Visão geral, Atendimentos | ler e analisar; nenhuma tela administrativa |

O corte mapeia os dois perfis que o `PRODUCT.md` já descreve: quem **opera** a
ferramenta (cadastra fonte, gerencia chave, acompanha o modelo) e o **analista**
que chega com uma pergunta operacional e desce ao caso individual.

### 2.3 Cadastro diferenciado: papel `dev` exige código de convite

O formulário de cadastro cria `usuario` por padrão. Para nascer `dev`, o
cadastro exige o **código de convite** — `FRAUS_CODIGO_DEV`, variável de
ambiente, mesmo desenho do segredo de webhook: mora no ambiente, nunca no
banco.

Recusado: escolher o papel livremente no formulário — auto-promoção de qualquer
visitante a administrador não é cadastro diferenciado, é campo decorativo.

Recusado: "o primeiro usuário cadastrado vira dev". É mágico (nada na tela
explica por que o segundo cadastro saiu diferente do primeiro) e falha no caso
real: se o primeiro a se cadastrar for um analista, a instância nasce sem
administrador e sem caminho para ter um.

Sem `FRAUS_CODIGO_DEV` definido, **não há como nascer dev** — coerente com a
regra da casa: privilégio se liga por decisão explícita do operador, nunca por
padrão.

### 2.4 O FastAPI emite o JWT; o servidor continua a fonte da verdade

`POST /auth/entrar` confere a senha e devolve um JWT **HS256** assinado com
`FRAUS_JWT_SEGREDO` (ambiente, nunca banco — a mesma regra do
`fraus/assinatura.py`). Payload mínimo: `sub` (id do usuário), `papel`, `iat`,
`exp` (12 horas). O papel viaja **dentro do token assinado**: a interface o lê
para esconder telas, mas quem decide é o servidor, que o confere a cada
requisição — ninguém promove a si mesmo editando o localStorage.

Recusado: sessão no lado Next (Auth.js e vizinhos). Criaria uma segunda fonte
de verdade de identidade fora da API, e a regra do projeto é uma só: **o
servidor Python é a fonte da verdade** — vale para score e vale para quem é
dev.

Dependência nova, com motivo declarado: **PyJWT**. Assinar e conferir JWT à mão
com `hmac` + `base64` custa o mesmo que o módulo de prateleira e reintroduz a
classe de bug que a biblioteca já matou (confusão de algoritmo, `exp` não
conferido). É a única dependência nova desta feature.

### 2.5 Senha com `hashlib.scrypt`, sem dependência nova

Hash de senha usa `hashlib.scrypt` do stdlib (salt de 16 bytes por usuário,
`n=2**14, r=8, p=1`), comparação em tempo constante — o mesmo desenho de
`credencial.py`, endurecido para segredo de baixa entropia. Argon2 exigiria
`argon2-cffi`; o scrypt entrega a propriedade que importa (custo de memória
contra força bruta) sem dependência.

### 2.6 O cookie é httpOnly e quem o guarda é o Next

O navegador **nunca vê o token**: a rota de login do Next chama a API, recebe o
JWT e o grava em cookie `httpOnly` + `SameSite=Lax`. O middleware do Next
protege `/dashboard/*` (sem cookie válido → redireciona à LP) e o proxy
existente (`app/api/fraus/[...caminho]/route.ts`) repassa o token à API — o
mesmo desenho que já mantém a chave `fra_` fora do navegador. Sair é apagar o
cookie.

### 2.7 Como o JWT convive com as credenciais técnicas

O middleware de acesso da API passa a aceitar **três** credenciais quando a
mestra está ligada: mestra, chave `fra_` e JWT válido. `/auth/entrar` e
`/auth/registrar` entram nas isentas — são as rotas de quem ainda não tem
credencial (o mesmo argumento de `/acesso/estado`).

A restrição de papel é uma dependência própria (`exigir_dev`) nas rotas
administrativas: quem chega com JWT de `usuario` recebe **403** (a credencial
está certa; o privilégio é que falta — o mesmo contrato de `exigir_mestra`).
Credencial técnica (mestra, `fra_`) segue passando: ela autentica um processo
operado por quem já tem privilégio de infraestrutura.

**No modo aberto (sem mestra), a API continua aberta** — comportamento
documentado desde a autenticação, inalterado. O que muda é a *dashboard*:
`/dashboard/*` exige login sempre, porque identidade e papel são conceito da
interface de trabalho, não um interruptor da API.

### 2.8 O que a LP diz — e o que ela não pode dizer

Seções, nesta ordem: a tese ("o cliente escreve 'ok, obrigado 🙂' e sai
insatisfeito — a nota declarada mente"), como funciona (sete famílias de sinal
→ fusor → score 0–100, **sem LLM em runtime**), a honestidade metodológica
(NPS **inferido**, sinal de tempo treinado em dados sintéticos — limitação
declarada, não segredo), e a entrada (entrar / criar conta).

A LP obedece à honestidade do produto: **nenhum número inventado** — sem
"98% de acurácia", sem contador de clientes fictício, sem depoimento
fabricado. Se um número aparece na LP, ele é real (35 features, 7 sinais) ou é
o dado sintético do simulador **rotulado como tal**.

## 3. O que fica de fora, por decisão

- **Recuperação de senha por e-mail** — não há servidor de e-mail no projeto.
  Redefinição é ato do dev (pendência futura, se doer).
- **OAuth / login social** — dependência externa de runtime numa aplicação
  cujo argumento é rodar local.
- **Multi-tenancy** — um banco, uma operação. É o escopo do trabalho.
- **Refresh token** — `exp` de 12h e o analista entra de novo amanhã. Um
  segundo token dobraria a superfície por conveniência marginal.

## 4. Consequências honestas, para dizer na tela

- A rota de webhook continua **anônima por desenho** e a de ingestão continua
  com chave de fonte — nada disso passa a exigir usuário.
- No modo aberto, a API responde sem credencial a quem falar HTTP direto; o
  login protege a **dashboard**. Quem publica a API na internet liga a mestra
  — o mesmo aviso que o README já faz.
