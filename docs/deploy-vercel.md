# Deploy gratuito: Vercel, Oracle Object Storage e Supabase

## Estado atual

Desde 17/09/2026, a aplicação real está publicada em duas unidades:

| Peça | Projeto | Responsabilidade |
|---|---|---|
| dashboard | Vercel `fraus` | Next.js, sessão e proxy server-side |
| API | Vercel `fraus-api` | FastAPI, ONNX Runtime e fusor |
| artefatos | Oracle Object Storage | ZIP privado dos modelos e do fusor |
| estado | Supabase | Postgres persistente pelo transaction pooler |

URLs de produção:

- <https://fraus-one.vercel.app>
- <https://fraus-api.vercel.app>

**Atualização de 30/09/2026:** a entrega de Operação, análise persistida e
convites (PR #75, `main` em `ab1b5da`) também foi publicada na API. Deploy
`dpl_2ghd1GGyN6ftxYvZ7pgPwnA3KyvF` em estado `Ready`, com alias de produção
aplicado e pacote Python de **1,95 GB** em `iad1`. O tamanho é do pacote, não
da memória em execução. Contratos e evidências estão em
[Operação e produção](notas/2026-09-30-operacao-producao.md).

**Atualização de 02/10/2026:** a `main` com os PRs #78 a #81 foi publicada na
API pela CLI (deploy `fraus-ajbdtr0gh`, `Ready`, alias de produção aplicado).
Entraram as rotas `/modelo/comparacao*` e a trava de migração do Postgres. O
build levou 10 minutos.

**Os deploys são independentes.** O merge atualizou a dashboard, mas a API
antiga ainda devolvia 404 nas novas rotas. Publicar `fraus-api` resolveu o
descompasso. O workflow de API é manual e ainda depende da configuração de
secrets descrita abaixo; não há publicação automática da API no merge.

Não há modelo executando no navegador e não há chamada a serviço de IA externo
durante a inferência. A função contém os grafos ONNX; o bucket é acessado apenas
no build.

## O problema que existia

O deploy monolítico não cabia no plano gratuito comum:

1. PyTorch adicionava centenas de megabytes ao runtime;
2. os três BERTimbau ocupavam mais de 1 GB;
3. guardar pesos no Git tornava cada deploy pesado;
4. SQLite seria descartado junto com uma função efêmera;
5. não havia capacidade Ampere A1 disponível na Oracle para criar a VM grátis.

Separar apenas “front” e “back” não bastava. A API continuaria grande e sem
estado persistente. A solução separou também **código, artefato e estado**.

## Solução implementada

### 1. Runtime menor sem trocar o modelo

`FRAUS_BACKEND=onnx` executa os mesmos checkpoints exportados:

- satisfação: ONNX fp32;
- emoção: ONNX fp32;
- ironia: ONNX int8 no pacote; **em produção quem lê ironia é o Laya sem
  treino em ONNX** (`FRAUS_IRONIA_BACKEND=laya-onnx`), e o BERTimbau de ironia
  não é carregado;
- fusor: `joblib`.

A quantização ficou restrita à cabeça de ironia porque ela não pontua o score e
foi a variante que preservou o comportamento aceito. Satisfação e emoção
continuam em fp32; portanto, o deploy não “coube” às custas de uma redução não
medida de eficiência.

### 2. Artefatos fora do Git, mas dentro da função

O ZIP versionado pelo SHA-256 fica num bucket privado do Oracle Object Storage.
Uma URL pré-autenticada concede apenas leitura daquele objeto. No build,
`scripts/preparar_modelos_vercel.py`:

1. exige `FRAUS_MODELOS_URL` e `FRAUS_MODELOS_SHA256`;
2. baixa o arquivo;
3. verifica o checksum;
4. recusa entradas ZIP que escapem do destino;
5. valida `model.onnx`, configuração, tokenizador e fusor;
6. falha o deploy se qualquer artefato estiver incompleto.

Depois do build, a inferência não depende da Oracle: os arquivos já fazem parte
da função Vercel.

### 3. Inicialização compatível com serverless

`api/index.py` expõe uma aplicação ASGI preguiçosa. Importar o módulo é barato;
a aplicação é montada na primeira chamada, protegida por trava. O motor é um
`ProvedorDeMotor`: sua carga começa em segundo plano no boot e em `/saude`,
sem criar as três sessões ONNX durante o import. `/saude/prontidao` afirma se
a carga terminou; veja a seção de aquecimento abaixo.

### 4. Estado persistente no Supabase

`FRAUS_DATABASE_URL` usa o shared transaction pooler IPv4 do Supabase na porta
`6543`. `psycopg` roda com `prepare_threshold=None`, necessário no modo
transaction, e o pool da aplicação é pequeno para respeitar a cota gratuita.

O erro `tenant/user not found` encontrado durante o deploy tinha duas causas:
o projeto estava inativo durante a restauração e a URI antiga usava a porta
`5432`. A conexão passou assim que o projeto ficou ativo e a URI oficial do
transaction pooler, porta `6543`, substituiu a antiga.

### 5. Monorepo sem cruzar builds

Há duas configurações deliberadamente separadas:

- `/vercel.json`: função Python, preparação dos modelos, duração e inclusão dos
  arquivos da API;
- `/dashboard/vercel.json`: Next.js e `npm run build`.

Sem a segunda, o deploy automático da dashboard herdava o comando da raiz e
tentava executar `dashboard/scripts/preparar_modelos_vercel.py`, que não existe.

## Variáveis

### Projeto `fraus-api`

| Variável | Função |
|---|---|
| `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` | habilita o pacote acima do limite padrão |
| `FRAUS_MODELOS_URL` | URL privada de leitura do ZIP |
| `FRAUS_MODELOS_SHA256` | identidade imutável do artefato |
| `FRAUS_LAYA_MODELO_URL` | URL privada do ZIP Laya validado |
| `FRAUS_LAYA_MODELO_SHA256` | identidade imutável do ZIP Laya separado |
| `FRAUS_BACKEND=onnx` | escolhe ONNX Runtime sem fallback silencioso |
| `FRAUS_AMBIENTE=producao` | ativa a validação de segredos e banco persistente no boot |
| `FRAUS_IRONIA_BACKEND=laya-onnx` | ativa a Laya exportada para ONNX, quando o ZIP separado estiver configurado |
| `FRAUS_DATABASE_URL` | transaction pooler do Supabase (`:6543`) |
| `FRAUS_POSTGRES_MIN_CONEXOES=0` | não reserva conexão por instância fria |
| `FRAUS_POSTGRES_MAX_CONEXOES=2` | teto por instância serverless (1–20) |
| `FRAUS_POSTGRES_TIMEOUT_S=10` | espera máxima por uma conexão do pool |
| `FRAUS_CHAVE_MESTRA` | administração da API |
| `FRAUS_CHAVE_ACESSO` | acesso usado pela dashboard |
| `FRAUS_JWT_SEGREDO` | assinatura das sessões |
| `FRAUS_CODIGO_CONVITE` | controla cadastro |
| `FRAUS_CODIGO_DEV` | código que o cadastro exige para criar conta com papel `dev` |
| `FRAUS_MODELOS_TOKEN`, `FRAUS_LAYA_MODELO_TOKEN` | opcionais: `Bearer` para baixar os ZIPs quando o objeto é privado por token e não por URL assinada |
| `FRAUS_ORIGENS` | origens públicas permitidas |
| `FRAUS_FUSOR_CANDIDATO` | opcional: caminho de `.joblib` compatível para comparar fusores; não promove o candidato |

### Projeto `fraus`

| Variável | Função |
|---|---|
| `FRAUS_API_URL=https://fraus-api.vercel.app` | destino do proxy Next |
| `FRAUS_CHAVE_ACESSO` | credencial server-side; nunca vai ao navegador |

Nenhum valor secreto deve entrar no repositório. Alterar variável na Vercel
exige novo deploy para entrar no processo.

Com `FRAUS_AMBIENTE=producao`, a API falha no boot se
`FRAUS_DATABASE_URL` estiver ausente ou não usar `postgres://` ou
`postgresql://`. Isso impede que um deploy serverless
pareça saudável usando SQLite efêmero e perca conversas, chaves e configurações
num cold start. A chave mestra também continua obrigatória no ambiente, portanto
o deploy não depende da escrita de `.fraus-chaves.txt`.

## Cold start e motor aquecendo

Em serverless cada instância tem o próprio motor. Até 30/09/2026 o motor só
carregava na primeira **predição**, então `/saude` respondia `frio` por tempo
indeterminado e o usuário pagava a abertura dos três grafos ONNX dentro da
requisição. Com várias instâncias, a sonda caía numa quente e depois numa fria,
e o rodapé do dashboard oscilava entre "no ar" e "motor aquecendo".

O que foi feito, em três camadas:

1. **Aquecer sem bloquear.** `ProvedorDeMotor.aquecer()` inicia a carga numa
   thread e volta na hora (idempotente; falha fica memorizada como `erro`, sem
   fallback). Ele é chamado no boot de `criar_app_padrao` (desligue com
   `FRAUS_AQUECER=0`) e em cada `GET /saude`, então qualquer sonda basta para
   uma instância fria começar a carregar. `/saude/prontidao` continua sendo a
   afirmação forte: 503 até o motor estar pronto.
2. **Manter quente.** `.github/workflows/api-aquecer.yml` sonda `/saude` e
   espera `/saude/prontidao` a cada 5 minutos **no pedido**: o agendador do
   GitHub não garante o intervalo e, medido em 02/10/2026, entregou 10
   execuções em 45 horas. Antes de uma demonstração, aqueça à mão (`/saude` e
   depois `/saude/prontidao` até 200). Roda só a partir da branch padrão
   e usa o secret `FRAUS_API_PUBLIC_URL` (ou `https://fraus-api.vercel.app`).
3. **Não oscilar no dashboard.** `suavizarSaude` não deixa "no ar" ser
   rebaixado por uma instância fria; enquanto a API não está pronta o polling é
   de 4 s, depois 20 s.

Limite declarado: a Vercel não garante que a sonda e o usuário caiam na mesma
instância. Isto reduz o cold start, não o elimina. Para eliminá-lo de vez, a API
precisa de um processo sempre ligado (ver `Dockerfile` e `docs/hospedagem.md`).

## Deploy reproduzível e smoke

O workflow manual `.github/workflows/api-deploy.yml` usa o ambiente
`production-api`, trava concorrência de promoções e fixa a versão do CLI da
Vercel. Em 30/09/2026, esse ambiente ainda não tinha secrets nem regras de
proteção configuradas. O código do workflow está entregue; sua operação
depende dessa configuração. Configure os secrets `VERCEL_TOKEN`, `VERCEL_ORG_ID`,
`VERCEL_PROJECT_ID`, `FRAUS_API_PUBLIC_URL` e `FRAUS_CHAVE_ACESSO`. O job:

1. instala pelo `uv.lock` com `--frozen` e testa os contratos operacionais;
2. produz o build de produção antes de publicar;
3. publica o mesmo diretório prebuilt;
4. executa uma vez `scripts/smoke_deploy.py` contra `/saude`.

O smoke tem repetição limitada para propagação do deploy e termina. Ele não é
agendado e não deve virar ping contínuo para esconder cold start. URL e token
entram apenas por secrets e nunca são incluídos na saída do script.

### Publicação manual pelo CLI

Na entrega de 30/09/2026, foi usado o CLI da Vercel já autenticado, em checkout
isolado da `main`. A raiz do repositório é o projeto **`fraus-api`**; o
diretório `dashboard/` pertence ao projeto **`fraus`**. Confira o projeto
vinculado antes de publicar:

```bash
vercel link --yes --project fraus-api --scope wakefull
vercel --prod --yes
vercel inspect <url-do-deploy>
```

O CLI perdeu a conexão durante o acompanhamento desta publicação (`fetch
failed`), mas o deploy terminou. Antes de repetir, consulte `inspect` e confira
`Ready` e os aliases: erro de acompanhamento não prova falha de build.

Depois, confira `/saude`, `/saude/prontidao`, `/openapi.json` e as rotas
modificadas pelo proxy `/api/fraus`. Para esta entrega, radar, equipes,
jornadas, problemas e acessos devem existir em `/operacao`; `PUT` de equipe,
convites e `/analisar/registrar` devem aparecer no OpenAPI. Não use gravação de
conversa ou aceite de convite como smoke em produção sem dados destinados a isso.

## Artefatos e rollback

`scripts/gerenciar_artefatos.py` concentra o ciclo sem registrar URL privada:

```bash
uv run python scripts/gerenciar_artefatos.py empacotar --versao 2026-09-28 --saida dist/modelos-2026-09-28.zip
uv run python scripts/gerenciar_artefatos.py validar dist/modelos-2026-09-28.zip --sha256 SHA_ESPERADO
# FRAUS_ARTEFATO_PUBLICAR_URL e FRAUS_ARTEFATO_TOKEN vêm do ambiente
uv run python scripts/gerenciar_artefatos.py publicar dist/modelos-2026-09-28.zip --sha256 SHA_ESPERADO
```

O empacotamento é determinístico, cria manifesto e arquivo `.sha256`, recusa
sobrescrever pacote existente e valida a topologia antes da publicação. Para
rollback, mantenha pelo menos o ZIP, a URL de leitura e o checksum anteriores;
rode `rollback` para validar a cópia retida, restaure `FRAUS_MODELOS_URL` e
`FRAUS_MODELOS_SHA256` aos valores daquela versão e faça novo deploy. O comando
não sobrescreve o objeto imutável. O instalador do build também restaura o
bundle local anterior se uma promoção for interrompida pela metade.

## Medir latência e região

Use `scripts/medir_latencia_deploy.py` separadamente para cada perna acessível
(dashboard/proxy e API direta). Ele mede DNS, conexão+TLS, TTFB e transferência,
preserva `Server-Timing` e os cabeçalhos de região conhecidos. O relatório usa
um hash do alvo em vez do hostname:

```bash
FRAUS_MEDIR_URL=https://... uv run python scripts/medir_latencia_deploy.py --amostras 5
```

Compare medianas com a mesma origem de rede antes de alterar região. A parcela
API→Postgres aparece em `Server-Timing` como `espera_pool` e `consulta_db`.

## Verificação realizada

Em **30/09/2026**, depois da publicação da API:

- deploy `Ready`, alias `fraus-api.vercel.app` e pacote de **1,95 GB**;
- pelo proxy da dashboard, radar, equipes, jornadas, problemas e acessos: **200**;
- simulação de escala, somente leitura: **200**, com cálculo realizado;
- `/saude`: motor real; `/auth/estado`: login disponível;
- OpenAPI com edição de equipe, convites, aceite e análise persistida;
- CI da `main`: **1.091 passed, 4 skipped, 1 deselected** por dialeto,
  SQLite e PostgreSQL; dashboard com **163 testes em 20 arquivos** e build aprovado.

Este smoke não criou contas, aceitou convites ou gravou conversas em produção.
Replay e cenários foram validados com motor real em bancos isolados, não neste
smoke. A configuração do fusor candidato em produção não foi confirmada.

Histórico de **17/09/2026**:

- função Python construída com **1,46 GB**;
- `GET /saude` direto: `status=ok`, `motor=real`;
- cold start observado: **10,8 s**;
- `POST /modelo/simular` autenticado: resposta em **0,8 s**;
- frase de teste classificada com emoção dominante `tristeza`;
- `/api/fraus/saude` pela dashboard: `status=ok`, `motor=real`;
- build de produção do Next.js aprovado;
- testes de empacotamento, checksum, ZIP e monorepo aprovados.

## O que saiu do roadmap

Estão concluídas e não devem voltar como pendência aberta:

- criar VM Ampere A1 na Oracle;
- contratar VPS para hospedar a API;
- manter computador e túnel Cloudflare ligados;
- colocar modelos no Git ou no front;
- usar SQLite efêmero em produção;
- quantizar satisfação ou emoção sem evidência de equivalência;
- hospedar dashboard e inferência no mesmo projeto Vercel.

## Limites que continuam

- Configurar os secrets do workflow manual de API; o merge sozinho não o executa.
- O primeiro acesso após a função esfriar é mais lento.
- As cotas gratuitas podem pausar ou limitar o serviço; gratuidade não é SLA.
- Uma nova versão dos modelos exige gerar ZIP, checksum e atualizar as duas
  variáveis correspondentes antes do deploy.
- A URL pré-autenticada do bucket é segredo operacional e precisa ser revogada
  e recriada se vazar.
- Restaurar ou recriar o Supabase pode mudar a URI do pooler.
- A arquitetura resolve hospedagem; não resolve as limitações científicas da
  ironia, da latência sintética ou da calibração do modelo.
