# Auditoria de 13/10/2026 — features, bugs e segurança

Branch `auditoria/2026-10-13`, a partir da `main` em `c4f0871` (merge da PR
#90). Documento interno: fica fora do site público (`mkdocs-publico.yml`).

## 1. Resumo executivo

Auditados a API (FastAPI, ~17,5 mil linhas em `fraus/`), a dashboard
(Next.js, ~31 mil linhas), os scripts operacionais, o deploy (Vercel, Docker,
workflows) e o histórico do git. Seis frentes rodaram em paralelo, só
leitura, com sonda executada para cada suspeita; as correções foram feitas
depois, uma por commit, com teste que falhava antes.

**41 achados: 0 crítico, 1 alto, 14 médios, 22 baixos, 4 informativos**
(mais observações informativas sem ação, listadas no fim da seção 3).
**29 corrigidos** na branch: 24 com teste de regressão que falhava antes, 3
com evidência de ferramenta (`npm audit`, `pip-audit`, build) e 2 de texto. Os
12 abertos são
de área protegida (modelo/contrato de features), decisão de produto ou
infraestrutura fora do repositório. Nenhum BOLA/BFLA explorável: o escopo
por canal, a hierarquia de equipe, os convites e o JWT se sustentaram em
toda a matriz rota × credencial. O histórico do git está limpo de segredos.
O achado mais grave que **foi corrigido** é o ReDoS da censura de e-mail,
alcançável pelo cliente final do chatbot sem credencial nenhuma. O mais
grave que **ficou aberto** é o alto: conversa que ninguém respondeu entra no
fusor como resposta instantânea — corrigir exige mudar o vetor e retreinar.

## 2. Baseline × final

| Verificação | Baseline (antes de mudar algo) | Final |
|---|---|---|
| `uv run pytest -q` (SQLite) | 1357 passed, 7 skipped, 0 falhas (155 s) | ver seção 10 |
| `pytest` com PostgreSQL 16 descartável | 1358 passed, 6 skipped, 0 falhas (672 s) | ver seção 10 |
| `scripts/conferir_fusor.py` | falha: `modelos/importancias.json` ausente | idem — **não verificado** (sem pesos) |
| `scripts/medir_faixas.py` | falha: `ModeloAusenteError` | idem — **não verificado** (sem pesos) |
| `scripts/smoke_integracoes.py` | **travava** (TimeoutError) aceitando motor em erro como real | sai com 1 em ~4 s dizendo que faltam modelos |
| `npm test` | 347 passed | ver seção 10 |
| `npx tsc --noEmit` | limpo | limpo |
| `npm run build` | verde | verde |
| `npm audit` | 16 (1 crítica, 13 altas, 2 moderadas) | 9 altas, todas em devDependencies |
| `npm audit --omit=dev` | 16 | **0** |
| `pip-audit` sobre o `uv.lock` | pypdf, pyjwt, urllib3, transformers | só transformers (correção exige a major 5) |

O venv local é Python 3.14 (o projeto declara 3.11); a suíte passa nele.

## 3. Achados

Severidade: Crítico / Alto / Médio / Baixo / Informativo. "Teste" é o teste
de regressão que falhava antes da correção.

### 3.1 Corrigidos

| ID | Sev. | Categoria | Local | Descrição | Causa raiz | Commit | Teste |
|---|---|---|---|---|---|---|---|
| A01 | Médio | ReDoS (CWE-1333, API4) | `fraus/seguranca/pii.py` `_EMAIL` | fala de 50 mil caracteres custava ~26 s; o cliente final alcança pelo webhook | `[\w.+-]+` sem teto recuava o resto do texto a cada início | `7dd0ba1` | `test_pii.py::test_censura_de_email_e_linear_no_tamanho_da_fala` |
| A02 | Médio | ReDoS | `fraus/ingest/transcricao.py` `LINHA` | 8 mil espaços + `x` ~7,7 s; 50 mil ~393 s | `^\s*` disputava espaços com o autor | `f2d2c1e` | `test_transcricao_custo.py::test_linha_com_muito_espaco...` |
| A03 | Médio | Complexidade (CWE-407) | `transcricao.ler` | recensurava o acumulado a cada linha: 12 kB ~8,7 s | censura sobre o texto inteiro por linha | `e4209df` | `test_transcricao_custo.py::test_muitas_linhas...` |
| A04 | Médio | Exposição na rede (CWE-1327) | `dashboard/package.json` | `next dev` em todas as interfaces; sem login o proxy empresta a chave técnica a quem estiver na rede | bind padrão do Next | `86dd63c` | `lib/rotas-locais.test.ts` (npm run dev) |
| A05 | Médio | Correção | `fraus/indicadores.py` | faixas de NPS invertidas aceitas (NPS −100 com score 100) | só cobertura e contiguidade eram conferidas | `aedabf6` | `test_indicadores.py::test_faixas_fora_da_ordem...` |
| A06 | Médio | Paridade de dialeto | `fraus/db.py` `listar_com_conversa` | Postgres perdia/repetia conversas empatadas na paginação (200 → 187 distintas) | `ORDER BY` sem desempate | `fe5d669` | `test_paginacao_conversas.py` (rodado nos dois dialetos) |
| A07 | Médio | Correção (timezone) | `rotas/operacao.py` jornadas | contatos ordenados pelo texto ISO com offsets diferentes; resolução declarada do contato errado | comparação lexicográfica | `62b20bb` | `test_operacao.py::test_jornada_ordena...` |
| A08 | Médio | Invariante 8 | `fraus/fusor.py` `Fusor.carregar` | artefato 1-based carregava e pontuava ao contrário | carga não conferia `classes_` | `cef0117` | `test_fusor.py::test_carregar_recusa_fusor_com_classes...` |
| A09 | Médio | Invariante 2 | `fraus/modelos.py` | fala vazia do cliente saía promotor 90 | `e_so_cortesia("")` é falso | `83382fb` | `test_cortesia_sem_sinal.py::test_fala_vazia...` |
| A10 | Médio | Validação (inv. 6) | `fraus/api/esquemas.py` | `encerrada_em` antes da última fala (ou naive) aceito; duração negativa vira zero no vetor | sem validador de coerência | `54892ca` | `test_ingestao_encerramento.py` |
| A11 | Médio | Supply chain | `dashboard/package-lock.json` | `next` 16.3.6 (alta) e cadeia com proxy-addr crítica | lock defasado | `1135dc4`, `6da2631` | `npm audit --omit=dev` = 0 |
| A12 | Baixo | Supply chain | `uv.lock` | pypdf 6.16.1 (4 DoS alcançáveis por `/analisar/*`), pyjwt, urllib3 | lock defasado | `d693879` | `pip-audit` |
| A13 | Baixo | DoS (CWE-409) | `fraus/ingest/arquivos.py` | PDF de 72 KB custava 14–18 s de CPU | teto de 75 MB do pypdf | `e3f9f5f` | `test_arquivos.py::test_pdf_com_fluxo_inflado...` |
| A14 | Baixo | Enumeração (CWE-204) | `fraus/api/observabilidade.py` | `Server-Timing` de `/auth/entrar` revelava se o e-mail tem conta | detalhamento publicado em toda rota | `ab3ea72` | `test_observabilidade.py::test_rotas_de_autenticacao...` |
| A15 | Baixo | Sessão (CWE-613) | `app/api/sessao/sair` | "Sair" deixava o cookie `fraus_acesso` | logout só conhecia a sessão | `0b4c217` | `lib/rotas-locais.test.ts` |
| A16 | Baixo | Exposição (CWE-200) | `app/api/fraus/iniciar` | `GET` respondia 200 em produção com argv e caminho do log | GET não consultava o modo local | `278d021` | `lib/rotas-locais.test.ts` |
| A17 | Baixo | LGPD (CWE-532) | `csv_driver.py`, `totalk.py` | motivo de rejeição gravava CPF/e-mail/telefone crus | `str(erro)` de biblioteca persistido | `fa18a0c` | `test_motivo_sem_pii.py` |
| A18 | Baixo | Integridade (CWE-639) | `rotas/conversas.py` importar | arquivo com id `fonte:N:` sobrescrevia conversa da integração e o canal | upsert por id sem namespace | `b989248` | `test_api.py::test_importacao_recusa_id_com_prefixo...` |
| A19 | Baixo | Correção | `fraus/api/repontuacao.py` | queda do banco na gravação final prendia o trabalho em "rodando" (409 por 15 min) | escrita final fora do `try` | `b16bff1` | `test_api_repontuar.py::test_queda_momentanea...` |
| A20 | Baixo | Correção | `fraus/db.py` | `deslocamento` sem `limite` divergia entre dev e usuário com escopo | OFFSET só com LIMIT | `fe5d669` | `test_paginacao_conversas.py` |
| A21 | Baixo | Consistência / CSV (CWE-1236) | `rotas/operacao.py` exportar | CSV do servidor sem `contestada`, sem ordem, sem `\t`/`\r` | exportação fora da derivação | `de54121` | `test_operacao.py::test_exportacao_do_servidor...` |
| A22 | Baixo | CSV (CWE-1236) | `components/TabelaConversas.tsx` | gatilhos de fórmula sem `\t`/`\r` | lista incompleta | `870195e` | `components/TabelaConversas.test.tsx` |
| A23 | Baixo | Correção | `rotas/operacao.py` laboratório | fusor candidato incompatível dava 500, não o 503 explicativo | `except` sem `FusorIncompativelError` | `07f0ea0` | `test_operacao.py::test_laboratorio_recusa...` |
| A24 | Baixo | Diagnóstico | `fraus/api/main.py` | arquivo de chaves antigo: API sobe aberta e o aviso culpava "permissão" | aviso só conhecia falha de escrita | `0f03d42` | `test_primeiro_uso.py::test_aviso_de_subida_aberta...` |
| A25 | Baixo | Ferramenta | `scripts/smoke_integracoes.py` | sem modelos, aceitava motor em erro e travava | olhava `/saude`; stdout em pipe não drenado | `69430e9` | `test_smoke_integracoes_sem_modelos.py` |
| A26 | Baixo | Documentação | trilha de auditoria (tela e `metodo`) | prometia detectar "alterações parciais"; a remoção do fim passa | limite não declarado | `8d84bff` | `test_operacao.py::test_auditoria_declara...` |
| A27 | Baixo | Documentação | `primeiro_uso.py`, `acesso.py`, README | `fra_` descrita como "apenas lê"; escreve quase tudo | texto antigo | `5560283` | — (texto) |
| A28 | Informativo | Dependência | `dashboard/package.json` | `clsx` usado e não declarado | chegava por tabela | `ac763ab` | build |
| A29 | Informativo | Documentação | README e `docs/` | ~15 divergências (ver matriz) | texto desatualizado | passada de docs | — |

### 3.2 Abertos

| ID | Sev. | Categoria | Local | Descrição | Por que não foi corrigido | Recomendação |
|---|---|---|---|---|---|---|
| B01 | **Alto** | Correção do modelo (inv. 2/§3.2) | `fraus/sinais/tempo.py:53-59` | conversa que ninguém respondeu: latências 0,0 e abandono 0,0 — a mesma codificação de "respondeu na hora". Sonda: score 82 contra 29 de uma resposta em 120 s | muda o vetor do fusor e exige retreino (área protegida, regra 4) | representar "sem resposta" explicitamente (feature própria ou ausência → `score: None`) e retreinar; até lá, considerar tratar como sem sinal |
| B02 | Médio | Supply chain | `vercel.json`, `requirements.txt`, `Dockerfile` | o deploy instala por faixas `>=` e ignora o `uv.lock`; hoje resolveria `transformers` 5.x (testado: 4.57) — muda tokenização em silêncio | listado no handoff como decisão do dono | gerar `requirements.txt` com `uv export --frozen` (com hashes) e instalar `--require-hashes`; fixar torch no Dockerfile |
| B03 | Médio | LGPD (CWE-916) | `rotas/operacao.py` `vincular_jornada` | referência de jornada é `sha256(ref)[:24]` sem sal: CPF/telefone é reversível por força bruta | trocar por HMAC muda os pseudônimos já gravados (jornadas se partiriam) | HMAC com segredo próprio + migração dos vínculos |
| B04 | Médio | Supply chain | `transformers` 4.57.6 | 9 advisories no pip-audit (RCE exige controlar o modelo; artefato tem SHA-256 no build) | correção só na major 5 (modelo) | avaliar a major 5 junto com o retreino |
| B05 | Baixo | Consumo de recurso | `rotas/webhook.py` + `db.py` poda | anônimo expulsa do histórico as recusas legítimas da fonte (201 POSTs com assinatura lixo) | limitar por IP não funciona atrás do proxy; agregar recusas exige mudar o esquema | agregar recusas anônimas iguais com contador |
| B06 | Baixo | Vazão | `fraus/api/vazao.py` + `/api/sessao/entrar` | terceiro esgota o teto de 20/min de login de todos atrás do proxy | o proxy não repassa IP; corrigir exige header assinado | header de IP com segredo compartilhado, ou teto também por e-mail |
| B07 | Baixo | Supply chain | `.github/workflows/*.yml` | actions por tag mutável em jobs com `VERCEL_TOKEN`/`DEPLOY_KEY_DOCS` | exige resolver SHAs e mexer em CI | fixar por SHA e passar segredo por `env:` |
| B08 | Baixo | Hardening | `Dockerfile` | container roda como root; base sem digest | sem como testar o build do Cloud Run aqui | `USER` não-root e `@sha256` |
| B09 | Baixo | Paridade | `fraus/db.py:1585` | e-mail com acento: SQLite `NOCASE` não dobra, Postgres dobra (conta duplicada só no SQLite) | normalizar e-mail mexe em contas existentes | `casefold` na borda + migração |
| B10 | Baixo | Arredondamento | `fraus/indicadores.py:47` | `round()` bancário: 65→6 (detrator) e 85→8 (neutro), enquanto 75→8 | fronteira fixada por teste e de produto | decidir meio-para-cima; ver PESO_NEUTRO |
| B11 | Informativo | Invariante 1 | `fraus/sinais/ironia_laya.py` | `FRAUS_IRONIA_BACKEND=laya` baixa o modelo do Hugging Face na primeira predição | opt-in experimental | exigir artefato local ou `HF_HUB_OFFLINE=1` |
| B12 | Informativo | Robustez | webhook, `/conversas/importar`, xlsx | id de fonte com 30 dígitos, NUL no caminho e xlsx com DTD viram 500; corrida de dedupe do webhook repete inferência | impacto baixo | `Path(ge=1, le=2**62)`, validar NUL, trazer `iter_rows` para o `try` |

Achados da passada de documentação, abertos (baixos e informativos, não
corrigidos por falta de tempo nesta sessão):

- `scripts/resetar_mestra.py` só usa SQLite e **ignora `FRAUS_DATABASE_URL`**;
  e, depois de rodá-lo, o `.fraus-chaves.txt` antigo impede a autenticação
  de religar (a API sobe aberta, com o aviso corrigido em A24). Baixo.
- `FRAUS_MODO_LOCAL=1` também faz o proxy voltar a ler `.fraus-chaves.txt`
  num build de produção; o README só fala do botão Iniciar.
- O README da seção de saúde ainda não trata `motor: real` com
  `estado_motor: erro`.
- O webhook responde 400 (não 422) para `encerrada_em` inválido, porque
  valida o corpo por conta própria; a importação responde 400 e o
  `/analisar/registrar` 422 para o mesmo arquivo sem horário.
- A docstring de `fraus/api/rotas/lexico.py` diz que vale "a chave de acesso
  como o resto", mas JWT de `usuario` leva 403 ali.
- Rotas sem documentação no README: `/operacao/*`, `/auth/eu`,
  `/integracoes/arquivos` e `/importacoes`, `/modelo/ironia-laya*`,
  comparação de modelos e grupos de anotação.

Também informativos e sem ação: `/saude` diz `motor: real` com o provedor em
erro (é liveness por desenho; readiness é `/saude/prontidao`); usuário sem
documento de permissão vê todos os canais (declarado na tela de Acessos);
scrypt `N=2**14` abaixo do mínimo OWASP atual; sem entropia mínima exigida
para mestra/códigos no boot; plano B do NPS da dashboard mostra o ponto
abaixo de 30 conversas quando `/indicadores` falha (escolha comentada no
código); `/ingestao` desserializa o corpo antes de autenticar (422 ecoa o
próprio corpo para o próprio anônimo).

## 4. Matriz de conformidade das features

Em [2026-10-13-features.md](2026-10-13-features.md): 98 linhas, 11 seções,
anexos de variáveis de ambiente e rotas × consumidores.

## 5. Matriz rota × credencial

Medida **executando** `criar_app` com mestra no ambiente e JWT ligado,
chamando cada rota do OpenAPI com cada credencial (ids inexistentes, corpo
`{}`). 401 = barrada no middleware; 403 = barrada por papel ou mestra;
2xx/404/409/410/422/503 = passou da autorização.

| Rota | anônimo | `frs_` | `fra_` | mestra | JWT usuario | JWT dev |
|---|---|---|---|---|---|---|
| `GET /saude`, `/saude/prontidao`, `/acesso/estado`, `/auth/estado` | ok | ok | ok | ok | ok | ok |
| `POST /auth/registrar`, `/auth/entrar` (20/min por IP) | ok | ok | ok | ok | ok | ok |
| `GET /auth/eu` | 401 | 401 | 401 | 401 | ok | ok |
| `POST /ingestao` (só `frs_`, conferida na rota) | 401 | ok | 401 | 401 | 401 | 401 |
| `POST /integracoes/webhook/{id}` (assinatura própria) | assinatura | assinatura | assinatura | assinatura | assinatura | assinatura |
| `GET /operacao/convites/{token}`, rotas públicas de anotação por token | ok | ok | ok | ok | ok | ok |
| `POST /operacao/convites/{t}/aceitar` | 401 | 401 | 401 | 401 | ok | ok |
| leituras: `/conversas*`, `/indicadores`, `/lexico`, `/serie-temporal`, `/grafo`, `/saude/deriva`, `GET /configuracoes`, `/lexico/curado`, `/perfis-mapeamento` | 401 | 401 | ok | ok | ok (escopo) | ok |
| `/analisar*` (gravação com escopo no `salvar_lote`) | 401 | 401 | ok | ok | ok | ok |
| `/operacao`: radar, escala, equipes (GET), jornadas, problemas, replay, laboratório | 401 | 401 | ok | ok | ok (escopo) | ok |
| gestão de equipe (`PUT`/`PATCH` membros, convites) | 401 | 401 | ok | ok | `exigir_gestao` | ok |
| `GET /operacao/exportar`, `POST /operacao/exportacao/autorizar` | 401 | 401 | ok | ok | 403 sem `exporta_ate` | ok |
| administração: `PUT /configuracoes`, léxico curado, perfis, importação, repontuação, `/modelo*`, fontes, acessos, `POST /operacao/equipes`, anotadores | 401 | 401 | **ok** | ok | 403 | ok |
| `/acesso/chaves`, chave e segredo de fonte | 401 | 401 | 403 | ok | 403 | 403 |
| `POST /acesso/mestra` | 401 | 401 | 409 | só com a atual | 409 | 409 |

Negados conferidos: membro não lê conversa de canal fora do escopo por id,
exportação, atribuição, jornada, replay, laboratório nem grafo; gestor não
vira `dev` nem mexe em canais; convite da equipe A não age na B; última
proprietária protegida; revogação de sessão vale na hora. A `fra_` ser
credencial de operador (linha "administração") é o contrato real — o texto
que a chamava de "somente leitura" foi corrigido (A27); restringi-la é
decisão do dono. Sem mestra (modo local), quem chega sem credencial é
administrador — documentado.

## 6. Não verificado / limites da auditoria

- **Pesos dos modelos ausentes.** `conferir_fusor.py`, `medir_faixas.py`, o
  smoke de integrações com motor real e qualquer inferência de ponta a ponta
  não rodaram. Baixar o pacote do bucket do deploy seria tocar a
  infraestrutura de produção. Em especial: **o fusor de produção não foi
  conferido contra a nova checagem de classes (A08)** — rodar
  `scripts/conferir_fusor.py` antes de publicar a API.
- **Produção não foi tocada**: o que a Vercel entrega em `request.client.host`
  (B06), as variáveis de Production/Preview (`FRAUS_AMBIENTE`,
  `FRAUS_IRONIA_BACKEND`), a versão realmente instalada no último deploy (B02),
  HSTS do `*.vercel.app` e proteções do GitHub ficaram fora.
- **Não reproduzi** os payloads específicos de cada GHSA do pypdf; a
  alcançabilidade é por leitura do código.
- Tempos de ReDoS foram medidos nesta máquina; na Vercel o teto de duração da
  função corta a invocação (não confirmado), no Docker/Cloud Run não.
- Postgres: só a versão 16 local, collation en_US.utf8; o Supabase de
  produção não foi usado.
- Cabeçalhos de segurança das páginas (CSP, `frame-ancestors`, nosniff,
  Referrer-Policy) não existem no `next.config.ts`; anotado como reforço, não
  como achado, porque o cookie `Lax` neutraliza o clickjacking com login.

## 7. Riscos residuais e decisões do dono

1. **B01** é o risco de produto mais sério: conversas abandonadas sem resposta
   pontuam alto. Decidir o formato (feature "sem resposta" ou sem sinal) e
   retreinar.
2. **B02** antes do próximo deploy da API: travar o que a Vercel instala.
3. **B03** e o contrato da `fra_` (se deve virar só leitura).
4. Âncora externa para a trilha de auditoria (A26 só declarou o limite).
5. Repositório público ainda descrito como privado (pendência antiga do
   handoff; não mexida).
6. Namespace para todo id importado (A18 só recusa os prefixos reservados).

Sugestões fora de escopo (não feitas): unificar `entradaDeSistema`/
`itemDaPilha`; declarar `numpy`, `starlette`, `psycopg_pool` e as ferramentas
de `scripts/renderizar-posteres.ts`; limpar `F401`/`ERA001` de `tests/` e
`scripts/`; `local_files_only=True` nos `from_pretrained` (os construtores já
conferem o diretório antes, então é defesa em profundidade); teste unitário
de `lib/mesma-origem.ts` e do 409 de `/analisar/registrar`; validar o fusor
dentro de `preparar_modelos_vercel.py`.

## 8. Ação manual fora do repositório

- **Antes de publicar a `fraus-api`**: rodar `scripts/conferir_fusor.py` com
  os pesos reais (checagem nova de classes, A08) e o smoke com modelos.
- Publicar a API e a dashboard **separadamente** e conferir pelo proxy
  (`curl` sem cookie em `/api/fraus/conversas` → 401; `GET
  /api/fraus/iniciar` → 404).
- Rotacionar `FRAUS_CHAVE_ACESSO` (pendência de 02/10 que segue aberta).
- Ligar no GitHub: secret scanning, push protection, proteção da `main` e
  regras do environment `production-api`.
- Fixar as actions por SHA (B07) e o `requirements.txt` (B02).
- Conferir na Vercel que Production e Preview têm `FRAUS_AMBIENTE=producao`.

## 9. Inventário de código usado × não usado

Em [2026-10-13-codigo-morto.md](2026-10-13-codigo-morto.md). Saíram 4
arquivos, 8 funções/constantes e 4 imports (~395 linhas); nenhuma rota e
nenhuma dependência de runtime. Todo item de `vulture` (125), `deptry` (19)
e `knip` tem decisão registrada; o que ficou é falso positivo confirmado,
área protegida ou trabalho em andamento.

## 10. Verificação final e commits

Rodado na ponta da branch, depois de todas as correções:

| Verificação | Resultado |
|---|---|
| `uv run pytest -q` (SQLite) | **1393 passed, 7 skipped, 0 falhas** (156 s) |
| `pytest` com PostgreSQL 16 descartável | **1394 passed, 6 skipped, 0 falhas** (477 s) |
| `scripts/smoke_integracoes.py` | exit 1 em segundos: "o motor nao ficou pronto (erro) -- confira se os tres modelos estao em modelos/" (correto sem pesos) |
| `scripts/conferir_fusor.py`, `scripts/medir_faixas.py` | exit 1 por modelo ausente — **não verificados** (sem pesos) |
| `npm test` | 351 passed (42 arquivos) |
| `npx tsc --noEmit` | limpo |
| `npm run build` | verde |
| `npm run contraste` | AA nos 2 temas |
| `npm audit` / `--omit=dev` | 9 altas só em devDependencies / **0** |
| `mkdocs build --strict` (interno e público) | verde (rodado na passada de docs) |

Testes pré-existentes: o `git diff` em `tests/` só acrescenta; a única linha
removida troca o conjunto `fora` de `test_documentacao.py` por um
superconjunto (mais restritivo). Nenhum teste foi afrouxado. O diff não leva
banco, artefato de modelo nem segredo.

Commits da branch:

- `1135dc4` fix(deps): next 16.4.0 e proxy-addr/undici sem as falhas do npm audit
- `6da2631` fix(deps): shadcn sai de dependencies, porque e CLI e CSS de build
- `0b4c217` fix(dashboard): sair esquece tambem o cookie da chave tecnica
- `278d021` fix(dashboard): GET /api/fraus/iniciar responde 404 com o modo local desligado
- `07f0ea0` fix(operacao): laboratorio recusa fusor candidato incompativel com 503, nao 500
- `ab3ea72` fix(seguranca): Server-Timing de /auth/* nao delata se o e-mail tem conta
- `0f03d42` fix(api): aviso de subida aberta nomeia o arquivo de chaves antigo
- `e3f9f5f` fix(ingest): teto de 5 MB por fluxo do PDF recusa a bomba de descompressao
- `aedabf6` fix(indicadores): faixas de NPS so valem na ordem detrator, neutro, promotor
- `fe5d669` fix(db): paginacao de conversas desempata por id e respeita deslocamento sem limite
- `62b20bb` fix(operacao): jornadas ordenam contatos pelo instante, nao pelo texto ISO
- `cef0117` fix(fusor): carga recusa artefato com classes fora de 0/1/2 ou sem um dos polos
- `83382fb` fix(modelos): fala vazia do cliente e sem sinal, nao nota
- `b16bff1` fix(repontuacao): queda momentanea do banco no fim nao prende o trabalho em rodando
- `de54121` fix(operacao): CSV de /operacao/exportar leva contestada, sai em ordem e neutraliza tab
- `870195e` fix(dashboard): CSV da tela neutraliza tab e retorno no inicio da celula
- `54892ca` fix(ingestao): encerrada_em sem fuso ou antes da ultima fala e recusado na borda
- `7dd0ba1` fix(seguranca): regex de e-mail da censura de PII deixa de ser quadratica
- `f2d2c1e` fix(ingest): linha de transcricao com muito espaco inicial deixa de ser quadratica
- `e4209df` fix(ingest): transcricao censura cada fala uma vez, nao o acumulado a cada linha
- `fa18a0c` fix(ingest): motivo de rejeicao da importacao nao grava o valor recebido
- `b989248` fix(importacao): arquivo nao pode trazer id com prefixo reservado ao servidor
- `69430e9` fix(scripts): smoke de integracoes sem modelos diz que faltam modelos, e nao trava
- `86dd63c` fix(dashboard): npm run dev escuta so em 127.0.0.1
- `8d84bff` fix(auditoria): a cadeia declara que nao detecta a remocao dos eventos mais recentes
- `d693879` fix(deps): pypdf 6.20.1, pyjwt 2.15.1 e urllib3 2.8.0 no uv.lock
- `6a2a9be` chore(ingest): remove carregar_texto e converter_texto, sem chamador
- `cad6a27` chore(dashboard): remove componentes e exports sem nenhum uso
- `ac763ab` fix(deps): clsx passa a ser dependencia declarada da dashboard
- `5560283` docs(acesso): a chave fra_ e credencial de operador, nao somente leitura
- `776013e` chore(api): remove imports sem uso em main, analise, conversas e lexico
- `d64ffd8` fix(docs): relatorios de auditoria ficam fora do site publico
- `a0421d7` docs(readme): completa a tabela de variaveis com o que o codigo le
- `8d46ae3` docs(limitacoes): o log1p do tempo esta no codigo desde 15/09
- `83fd923` docs(readme): rotas publicas, credenciais e login como o codigo os faz
- `8d9b8b1` docs(api): contratos de repontuacao, webhook, ingestao, boot e deploy
