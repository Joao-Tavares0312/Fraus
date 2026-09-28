# Pendências provocadas pelo deploy serverless — 17/09/2026

## Resumo

Separar dashboard, API, artefatos e estado removeu a dependência da máquina
local, mas mudou o perfil operacional. O problema deixou de ser “não cabe” e
passou a ser **cold start, quantidade de saltos e custo de hidratação**.

Esta nota registra o que foi medido. Não atribui toda lentidão ao modelo e não
propõe manter a função aquecida antes de separar as causas.

## Linha de base medida

Medições contra produção, em 17/09/2026:

| Trecho | Resultado |
|---|---:|
| landing, resposta quente | 0,26–0,59 s |
| `GET /saude` direto, quente | 0,17–0,31 s |
| `GET /api/fraus/saude` pelo proxy, quente | 0,24–0,26 s |
| cold start observado da API | 10,8 s |
| seis endpoints de leitura, quentes e sequenciais | 0,25–0,66 s cada |
| inferência após aquecimento | 0,8 s |
| HTML inicial da landing | ~71 KB |
| JavaScript referenciado pela landing | ~799 KB / 12 chunks |

Os endpoints da visão geral rodam em paralelo, portanto seus tempos não devem
ser simplesmente somados. Autenticação no layout ocorre antes da página e cria
uma etapa sequencial.

## P0 — retirar o modelo do caminho das rotas leves — concluído em 28/09/2026

### Evidência

`api/index.py` chama `criar_app_padrao()` na primeira requisição.
`criar_app_padrao()` monta os três classificadores e só depois cria banco,
autenticação e routers. Assim, `/saude`, `/auth/estado`, `/auth/eu` e leituras
do Postgres pagam a mesma carga de uma inferência.

O carregamento preguiçoso atual resolveu o timeout de **importação**, mas não o
cold start percebido pelo primeiro usuário.

### Mudança implementada

1. montar FastAPI, banco, autenticação e rotas leves sem o `Motor`;
2. encapsular o motor num provedor thread-safe com estados `frio`, `carregando`,
   `pronto` e `erro`;
3. carregar o provedor apenas em análise, simulação, ingestão que pontua e
   repontuação;
4. separar liveness de readiness sem anunciar `motor=real` antes de ele estar
   operacional;
5. medir carga e inferência com `Server-Timing` ou log estruturado.

Os cinco itens foram implementados. O provedor em
`fraus/api/motor_preguicoso.py` serializa a primeira carga, memoriza sucesso ou
erro e nunca troca falha por dublê. `GET /saude` permanece liveness e informa
`estado_motor`; `GET /saude/prontidao` devolve 503 enquanto o estado não for
`pronto`, sem iniciar a carga como efeito colateral. A instrumentação detalhada
do item 5 expõe `carga_modelo`, `inferencia`, `consulta_db`, `espera_pool` e o
tempo total por `Server-Timing`, além de emitir logs JSON sem payload, token ou
SQL.

### Critério de aceite

- `/auth/estado` e uma leitura de banco frios respondem sem carregar ONNX;
- a primeira inferência pode continuar lenta, mas a interface entra e explica
  “motor aquecendo” em vez de parecer travada;
- concorrência na primeira inferência monta uma única instância do motor;
- falha de artefato continua alta e visível, sem cair para dublê.

## P0 — tirar a API do caminho crítico da landing — concluído

### Evidência

`dashboard/app/page.tsx` chama `usuarioDaSessao()` e depois
`loginDisponivel()`. Isso torna a página pública dinâmica e faz o primeiro
visitante acordar a API apenas para decidir se o CTA diz “Entrar”, “Dashboard”
ou “Abrir”. Com cookie, há ainda `/auth/eu` antes de `/auth/estado`.

### Mudança proposta

- servir a landing como conteúdo estático/cacheável;
- usar CTA estável para `/entrar` ou decidir somente pela presença do cookie,
  sem validar a conta na renderização pública;
- deixar a validação real para a rota de entrada/dashboard;
- evitar duas consultas sequenciais quando ambas forem inevitáveis.

### Critério de aceite

- resposta da landing com cache de CDN;
- indisponibilidade da API não altera TTFB nem conteúdo principal da LP;
- nenhum segredo ou estado autenticado entra no HTML público.

A landing agora é estática e o CTA público não consulta a API. A autenticação
real continua nas rotas protegidas.

## P0 — orçamento de JavaScript e animação da landing — concluído em 28/09/2026

### Evidência

A landing referencia aproximadamente 799 KB de JavaScript em 12 chunks. Ela
hidrata Motion e um campo de partículas; resposta HTTP rápida não impede
travamento de main thread ou GPU em celular básico.

### Mudança proposta

- medir LCP, INP, CLS, TBT e memória em perfil móvel;
- carregar partículas após primeira pintura ou quando a hero estiver visível;
- desabilitar WebGL em `save-data`, hardware fraco e telas pequenas;
- substituir revelações triviais por CSS/IntersectionObserver pequeno;
- carregar bibliotecas de movimento por seção, não na primeira dobra inteira;
- estabelecer orçamento inicial: medir antes e definir teto baseado no corte
  alcançável, em vez de escolher número decorativo.

A cena 3D ficou restrita a perfis capazes; telas menores que 768 px,
`prefers-reduced-motion`, `save-data` e hardware limitado recebem a mesma
narrativa em uma cena leve. Partículas e 3D são carregados sob demanda. A
validação Playwright cobre quatro perfis e aplica orçamento de bytes e CLS. No
perfil móvel medido, a transferência caiu de 2.660.841 B para 702.921 B
(-73,6%).

## P1 — reduzir viagens da visão geral — decisão encerrada em 28/09/2026

A visão geral pede conversas, indicadores, configurações, série e léxico em
paralelo. Quente, o maior tempo observado foi 0,66 s; ainda assim são cinco
invocações e cinco aquisições de conexão.

Avaliar uma rota BFF `/dashboard/resumo` ou cache curto para configurações e
agregados. A consolidação só entra se a instrumentação mostrar ganho; preservar
falha parcial pode valer mais que economizar chamadas.

Não foi criada uma rota agregadora especulativa: ela repetiria as mesmas
consultas no servidor, eliminaria a recuperação parcial da tela e criaria um
novo contrato sem evidência de ganho. A instrumentação entregue permite voltar
a essa decisão se medições reais apontarem contenção no pool ou overhead de
rede dominante.

## P1 — conexões Postgres em escala serverless — concluído em 28/09/2026

Cada instância cria `ConnectionPool(min_size=1, max_size=5)`. Em serverless, o
teto efetivo é `instâncias × 5`, não cinco. Uma rajada pode multiplicar
conexões até atingir a cota do Supabase.

O padrão agora é `min_size=0`, `max_size=2`, configurável e validado por
ambiente. A criação é serializada por processo e aquisições registram contagem,
falha, espera total/última/máxima; `espera_pool` também entra no
`Server-Timing`. O transaction pooler continua obrigatório.

## P1 — região como experimento, não palpite — instrumento entregue em 28/09/2026

A função foi empacotada em `iad1`; o banco restaurado está em Ohio. Usuários no
Brasil pagam o salto até os EUA, mas mover apenas a API para São Paulo pode
piorar API → banco e Next → API.

O instrumento para medir as três pernas (navegador → Next, Next → API, API →
Supabase) foi entregue. A escolha de região não é dívida de código: depende de
uma execução controlada contra os ambientes e da localização real dos usuários.
A decisão correta pode ser manter todo o plano de dados no mesmo lado, não
aproximar uma peça isolada.

`scripts/medir_latencia_deploy.py` decompõe DNS, conexão+TLS, TTFB e
transferência e preserva região e `Server-Timing`, sem publicar o hostname.

## P1 — CI/CD da API — concluído em 28/09/2026

O projeto `fraus-api` foi publicado manualmente. Confirmar e documentar a
integração Git; se ela não existir, mudanças em `main` podem atualizar a
dashboard sem atualizar a API.

Critério de aceite: preview e produção reproduzíveis a partir de commit, com
checksum do modelo registrado e smoke test de `/saude` após o deploy.

O workflow manual e protegido `api-deploy.yml` valida, constrói com CLI fixo,
publica o prebuilt e roda smoke finito. Secrets precisam ser configurados no
ambiente `production-api`; criar o workflow não executa deploy.

## P1 — observabilidade e regressão — concluído em 28/09/2026

Adicionar:

- logs estruturados com `cold_start`, `carga_modelo_ms`, `consulta_db_ms` e
  `inferencia_ms`;
- `Server-Timing` nas respostas relevantes;
- Web Vitals da landing e dashboard;
- smoke test periódico que não seja usado para mascarar cold start;
- alarme de falha de API, Supabase pausado e expiração/revogação da URL do
  artefato.

Logs estruturados e `Server-Timing` cobrem aplicação, banco, pool e modelo. A
landing mede FCP, LCP e CLS em perfis desktop, móvel, movimento reduzido e
economia de dados. O smoke test é finito e roda após publicação; não mantém a
função aquecida. Alarmes e notificações dependem do provedor/conta de produção
e devem ser configurados no ambiente `production-api`, pois o repositório não
possui autoridade nem destinatários para criá-los sozinho.

## P2 — ciclo de vida do artefato — concluído em 28/09/2026

Uma atualização de modelo exige ZIP, upload, SHA-256 e duas variáveis. Criar
script único que publique objeto imutável, valide conteúdo, atualize ambiente e
retenha a versão anterior para rollback. Nunca imprimir a URL pré-autenticada.

`scripts/gerenciar_artefatos.py` empacota deterministicamente, emite manifesto
e checksum, valida antes do PUT e confere uma versão retida para rollback sem
imprimir URL/token. A atualização dos secrets de URL/checksum permanece uma decisão
explícita do operador, evitando que uma ferramenta local ganhe autoridade sobre
o ambiente de produção inteiro.

## O que não fazer ainda

- pingar a API continuamente para esconder cold start;
- quantizar satisfação ou emoção sem repetir a validação de equivalência;
- mover regiões sem decompor a latência;
- remover autenticação, verificações de artefato ou falha alta para ganhar
  milissegundos;
- atribuir lentidão da landing ao BERTimbau: a landing tem dívida própria de
  bundle e animação.
