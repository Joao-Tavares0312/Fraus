# Inventário de código usado × não usado — auditoria de 13/10/2026

Fase 2B. Critério de "necessário": alcançado de um ponto de entrada de
produção (`fraus/api/main.py`, build da dashboard, deploy), feature
documentada, script que a documentação manda rodar, teste que protege
comportamento necessário, notebook de treino ou única fonte de uma
invariante. Na dúvida, **manter e reportar**.

Ferramentas (estado final da branch, todas rodadas de novo depois das
exclusões): `uvx vulture fraus scripts api --min-confidence 60` (125 itens),
`uv run --with deptry deptry .` (19 itens fora de `notebooks/`),
`npx knip` na dashboard, `ruff --select F401,F841,ERA001`, e `git grep -w`
por símbolo em código, testes, notebooks e docs. **Todo item listado pelas
três ferramentas tem decisão abaixo.**

## Excluído

| item | tipo | evidência de não uso | commit |
|---|---|---|---|
| `fraus/ingest/csv_driver.py::carregar_texto` (+ `import io`) | função | `git grep` só acha a definição (e um plano antigo em `docs/superpowers`) | `chore(ingest)` |
| `fraus/ingest/totalk.py::converter_texto` | função | `git grep` só acha a definição | `chore(ingest)` |
| `dashboard/components/ui/card.tsx`, `pagination.tsx`, `scroll-area.tsx` | arquivo | knip "unused files"; nenhum import de `ui/card`, `ui/pagination`, `ui/scroll-area` | `chore(dashboard)` |
| `emDuasCasas` (`components/lp/fatos.ts`), `PERIODO_TOTAL` (`lib/periodo.ts`), `trocaDeEstado` (`lib/movimento.ts`) | export | knip "unused export" e `grep -w` = 1 (só a definição) | `chore(dashboard)` |
| `analisarArquivo`, `listarPerfisMapeamento`, `apagarPerfilMapeamento` (`lib/api.ts`) | função | knip; nenhum componente, teste ou script chama. As rotas da API ficam | `chore(dashboard)` |
| imports `CAMINHO_BANCO`, `hashlib`, `no_recorte`, `unicodedata` | import | ruff F401 + `git grep` (inclusive por string) | `chore(api)` |

Saldo: 4 arquivos, 8 funções/constantes e 4 imports; −~395 linhas (3 componentes shadcn
≈ 340, Python ≈ 25, TypeScript ≈ 30). Nenhuma dependência saiu; uma passou a
ser declarada (`clsx`, usada e não listada) e uma mudou de seção (`shadcn` →
`devDependencies`). Efeito medido: `npm audit --omit=dev` 16 → 0
vulnerabilidades; o `next build` e o tempo da suíte não mudaram de forma
mensurável (pytest 155 s → ~110 s entre execuções, variação de máquina, não
efeito da limpeza). O contrato HTTP das rotas mantidas não mudou por
exclusão: nenhuma rota foi removida.

## Mantido por dúvida (reportar)

| item | motivo |
|---|---|
| `fraus/baseline_estilo.py::BaselineEstilo.prever_probabilidades` | sem chamador hoje; pertence à régua de ironia em andamento (plano de 08/10/2026) |
| Rotas sem consumidor no código: `GET /saude/deriva`, `GET /saude/prontidao`, `GET /modelo/ironia-laya`, `GET /operacao/exportar`, `POST /anotacao/grupos/{grupo}/revogar` | todas documentadas ou de operação (prontidão é readiness para orquestrador; exportar foi corrigida nesta auditoria). Nenhuma removida |
| `pngjs` e o binário `jiti` (knip "unlisted") | usados só por `scripts/renderizar-posteres.ts` (`npm run posteres`), ferramenta de desenvolvimento; chegam via `vgpu` e `eslint`/`vite`. Declarar em devDependencies é sugestão |
| `entradaDeSistema`/`itemDaPilha` (knip "duplicate exports", `lib/movimento.ts`) | o mesmo objeto exportado com dois nomes; unificar é refactor, fica como sugestão |

## Mantido — falso positivo confirmado

**knip**

| item | decisão | justificativa |
|---|---|---|
| `scripts/validar-operacao-playwright.mjs` | manter | citado no README, em `dashboard/README.md` e na nota de 30/09 como roteiro de QA |
| `@vgpu/wgsl-std` | manter | importado por `lib/lp-nova/shaders/simular.wgsl`, que o knip não lê |
| 25 exports de `components/ui/*` (Sidebar*, Select*, Sheet*, Table*, `badgeVariants`, `AlertAction`, `EmptyContent`, `tabsListVariants`, `useSidebar`) | manter | biblioteca vendorizada pelo `shadcn add`, substituída inteira na próxima geração (`eslint.config.mjs` já a trata assim) |
| `CLASSE_TEXTO_DA_CATEGORIA`, `corDoNo`, `raioDoNo`, `ROTAS_COM_COREOGRAFIA`, `chaveDoCookie`, `ROTEIRO`, `CURVA`, `EMOCOES_VISIVEIS`, `periodoEstaAtivo`, `tokenDaSessao`, `TEMA_PADRAO`, `CHAVE_TEMA`, `classeDoTema`, `temaValido`, `EVENTO_TEMA` | manter | usados dentro do próprio arquivo (`grep -w` ≥ 2); sobra só a palavra `export`, o que é estilo |
| 15 tipos exportados de `lib/api.ts`, `lib/operacao.ts`, `lib/lp-nova/leituras.ts`, `CartaoIndicador`, `EscalaNps` | manter | descrevem o contrato da API e compõem tipos usados; tirar o `export` é estilo |

**deptry** (rodado no ambiente do projeto; via `uvx` isolado ele não mapeia `scikit-learn→sklearn`, `pyjwt→jwt` e dá ~60 falsos positivos)

| item | decisão | justificativa |
|---|---|---|
| DEP003 `numpy` (8×), `starlette` (2×), `psycopg_pool` | manter e reportar | transitivas de scikit-learn/onnxruntime, FastAPI e psycopg[pool]; declarar explicitamente é sugestão |
| DEP002 `python-multipart` | manter | exigida pelo FastAPI para `UploadFile`/`Form` em `/analisar/arquivo` (import dinâmico) |
| DEP002 `pytest`, `httpx` | manter | extra `dev`; `httpx` é exigido pelo `TestClient` |
| DEP002 `mkdocs-material`, `mkdocstrings`, `mkdocs-to-pdf` | manter | extra `docs`; plugins carregados pelo `mkdocs.yml` |
| DEP002 `onnx-ir` | manter | extra `conversao`; usado pelo `optimum` na exportação ONNX |
| DEP001 `pandas` em `scripts/retreinar_fusor_local.py` | manter | o próprio script manda rodar com `uv run --with pandas` (dependência efêmera por desenho) |

**ruff** `F401,F841,ERA001`: em `fraus/` havia 4 imports órfãos —
`CAMINHO_BANCO` (`api/main.py`), `hashlib` (`rotas/analise.py`),
`no_recorte` (`rotas/conversas.py`) e `unicodedata` (`sinais/lexico.py`)
**excluídos** no lote 3 (`chore(api)`). Ficam os 6 `F401` de `api/main.py`
(`TETO_CORPO`, `TIPOS_DE_FONTE`, `TETO_ARQUIVO_ANALISE`,
`TETO_CONVERSAS_ANALISE`, `TETO_LEXICON`, `TETO_TEXTO_SIMULACAO`): o
comentário do arquivo os declara reexportação, e `tests/test_api.py` usa
quatro. Os `ERA001` de `fraus/fusor.py` são os rótulos de família (`# texto (4)`...) dentro de
`NOMES_FEATURES` (área protegida), não código comentado. Os de
`tests/`/`scripts/` ficam como sugestão de estilo.

**vulture** — os 125 itens, um por linha:

| item | tipo | evidência | risco de falso positivo | decisão | justificativa |
|---|---|---|---|---|---|
| `fraus/api/esquemas.py:24` `model_config` | variable | vulture 60% | alto | manter | Pydantic/validador chamado pelo framework |
| `fraus/api/esquemas.py:137` `_encerramento_coerente` | method | vulture 60% | alto | manter | validador Pydantic (`model_validator`) desta auditoria |
| `fraus/api/main.py:438` `__getattr__` | function | vulture 60% | alto | manter | PEP 562 (import preguicoso de `app`) |
| `fraus/api/rotas/acesso.py:45` `criar_ou_rotacionar_mestra` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/acesso.py:159` `revogar_chave_acesso` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/analise.py:62` `analisar_e_registrar` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/analise.py:113` `analisar` | function | vulture 60% | alto | manter | usado fora do arquivo: dashboard/app/api/fraus/[...caminho]/route.ts, dashboard/app/dashboard/analisar/page.tsx, dashboard/lib/api.ts ... |
| `fraus/api/rotas/analise.py:184` `previa` | function | vulture 60% | alto | manter | usado fora do arquivo: dashboard/lib/api.ts, fraus/api/esquemas.py, fraus/api/rotas/conversas.py ... |
| `fraus/api/rotas/analise.py:232` `analisar_arquivo` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/anotacao.py:63` `model_config` | variable | vulture 60% | alto | manter | Pydantic/validador chamado pelo framework |
| `fraus/api/rotas/anotacao.py:68` `_resposta_conhecida` | method | vulture 60% | alto | manter | Pydantic/validador chamado pelo framework |
| `fraus/api/rotas/anotacao.py:79` `model_config` | variable | vulture 60% | alto | manter | Pydantic/validador chamado pelo framework |
| `fraus/api/rotas/anotacao.py:180` `criar_anotador` | function | vulture 60% | alto | manter | usado fora do arquivo: tests/test_anotacao_api.py, tests/test_anotacao_grupo.py |
| `fraus/api/rotas/anotacao.py:221` `entrar_no_grupo` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/anotacao.py:235` `revogar_grupo` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/anotacao.py:253` `revogar_anotador` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/anotacao.py:266` `exportar_respostas` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/anotacao.py:279` `fila_do_anotador` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/anotacao.py:295` `gravar_resposta` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/auth.py:141` `entrar` | function | vulture 60% | alto | manter | usado fora do arquivo: dashboard/app/api/fraus/iniciar/route.ts, dashboard/app/api/sessao/entrar/route.ts, dashboard/app/cadastrar/page.tsx ... |
| `fraus/api/rotas/auth.py:170` `eu` | function | vulture 60% | alto | manter | usado fora do arquivo: dashboard/lib/ordenacao.test.ts, dashboard/lib/sessao.ts, fraus/api/seguranca.py ... |
| `fraus/api/rotas/configuracoes.py:27` `configurar` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/conversas.py:95` `previa_da_importacao` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/conversas.py:109` `importar` | function | vulture 60% | alto | manter | usado fora do arquivo: dashboard/app/dashboard/grafo/page.tsx, dashboard/app/dashboard/integracoes/page.tsx, dashboard/lib/api.ts ... |
| `fraus/api/rotas/conversas.py:214` `repontuar` | function | vulture 60% | alto | manter | usado fora do arquivo: dashboard/lib/repontuacao.ts, fraus/api/repontuacao.py, fraus/api/seguranca.py ... |
| `fraus/api/rotas/conversas.py:236` `progresso_da_repontuacao` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/conversas.py:323` `atribuir` | function | vulture 60% | alto | manter | usado fora do arquivo: dashboard/app/dashboard/atendimentos/[id]/page.tsx, dashboard/lib/derivacoes.ts, fraus/sinais/emocao.py |
| `fraus/api/rotas/conversas.py:368` `detalhar` | function | vulture 60% | alto | manter | usado fora do arquivo: fraus/sinais/estilo.py |
| `fraus/api/rotas/indicadores.py:110` `serie_temporal` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/ingestao.py:24` `ingerir` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/integracoes.py:96` `ajustar_fonte` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/integracoes.py:138` `gerar_chave` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/integracoes.py:234` `listar_entregas_da_fonte` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/integracoes.py:248` `tipos_de_fonte` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/integracoes.py:275` `arquivos_importaveis` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/modelo.py:129` `simular` | function | vulture 60% | alto | manter | usado fora do arquivo: dashboard/app/dashboard/modelo/page.tsx, dashboard/lib/api.ts, dashboard/lib/lp-nova/cena.ts ... |
| `fraus/api/rotas/modelo.py:156` `ficha_ironia_laya` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/modelo.py:172` `simular_ironia_laya` | function | vulture 60% | alto | manter | usado fora do arquivo: tests/test_rota_ironia_laya.py |
| `fraus/api/rotas/modelo.py:247` `relatorio_comparacao` | function | vulture 60% | alto | manter | usado fora do arquivo: tests/test_rota_comparacao.py |
| `fraus/api/rotas/modelo.py:294` `simular_comparacao` | function | vulture 60% | alto | manter | usado fora do arquivo: tests/test_rota_comparacao.py |
| `fraus/api/rotas/operacao.py:31` `pessoas` | variable | vulture 60% | alto | manter | usado fora do arquivo: dashboard/lib/anotacao.test.ts, dashboard/lib/anotacao.ts, dashboard/lib/operacao.ts ... |
| `fraus/api/rotas/operacao.py:64` `prazo` | variable | vulture 60% | alto | manter | usado fora do arquivo: dashboard/app/api/sessao/entrar/route.ts, dashboard/lib/operacao.ts, fraus/dados/regua_ironia_rascunho.csv ... |
| `fraus/api/rotas/operacao.py:134` `radar` | function | vulture 60% | alto | manter | usado fora do arquivo: scripts/validar_operacao_real.py, tests/test_auditoria_02_10.py |
| `fraus/api/rotas/operacao.py:160` `criar_equipe` | function | vulture 60% | alto | manter | usado fora do arquivo: tests/test_convites_equipe.py |
| `fraus/api/rotas/operacao.py:177` `editar_equipe` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/operacao.py:199` `definir_papel` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/operacao.py:222` `gerar_convite` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/operacao.py:238` `listar_convites` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/operacao.py:247` `revogar_convite` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/operacao.py:262` `ver_convite` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/operacao.py:284` `jornadas` | function | vulture 60% | alto | manter | usado fora do arquivo: tests/test_operacao.py |
| `fraus/api/rotas/operacao.py:302` `vincular_jornada` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/operacao.py:339` `criar_problema` | function | vulture 60% | alto | manter | registrado por decorador (rota/middleware FastAPI) |
| `fraus/api/rotas/operacao.py:356` `agir_problema` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/operacao.py:373` `replay` | function | vulture 60% | alto | manter | usado fora do arquivo: scripts/validar_operacao_real.py, tests/test_operacao.py |
| `fraus/api/rotas/operacao.py:397` `cenario` | function | vulture 60% | alto | manter | usado fora do arquivo: dashboard/app/api/fraus/iniciar/route.ts, dashboard/app/globals.css, dashboard/lib/cena.ts ... |
| `fraus/api/rotas/operacao.py:421` `comparar` | function | vulture 60% | alto | manter | usado fora do arquivo: dashboard/app/dashboard/modelo/page.tsx, dashboard/lib/api.ts, fraus/anotacao_regua.py ... |
| `fraus/api/rotas/operacao.py:448` `mapa_acesso` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/operacao.py:466` `configurar_acesso` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/operacao.py:498` `autorizar_exportacao` | function | vulture 60% | alto | manter | rota FastAPI (decorador `@router.*` multilinha, conferido por AST) |
| `fraus/api/rotas/operacao.py:511` `exportar` | function | vulture 60% | alto | manter | usado fora do arquivo: dashboard/app/api/fraus/iniciar/route.ts, dashboard/lib/api.ts, fraus/api/seguranca.py ... |
| `fraus/api/rotas/perfis.py:61` `apagar` | function | vulture 60% | alto | manter | usado fora do arquivo: dashboard/app/dashboard/configuracoes/page.tsx, dashboard/lib/api.ts, dashboard/lib/lp-nova/quadro.ts ... |
| `fraus/api/rotas/saude.py:76` `deriva` | function | vulture 60% | alto | manter | usado fora do arquivo: dashboard/app/globals.css, dashboard/lib/pontuarCliques.ts, fraus/api/rotas/auth.py ... |
| `fraus/api/rotas/webhook.py:88` `receber` | function | vulture 60% | alto | manter | usado fora do arquivo: dashboard/app/dashboard/layout.tsx, dashboard/app/globals.css, dashboard/lib/operacao.ts ... |
| `fraus/api/seguranca.py:315` `exigir_chave_de_acesso` | function | vulture 60% | alto | manter | middleware registrado por `@app.middleware('http')` |
| `fraus/api/vazao.py:170` `limitar_tentativas_de_autenticacao` | function | vulture 60% | alto | manter | middleware registrado por `@app.middleware('http')` |
| `fraus/avaliacao_ironia.py:57` `exemplos_sinceros` | variable | vulture 60% | alto | manter | campo de dataclass serializado no laudo |
| `fraus/avaliacao_ironia.py:58` `exemplos_ironicos` | variable | vulture 60% | alto | manter | campo de dataclass serializado no laudo |
| `fraus/avaliacao_ironia.py:59` `falsos_positivos` | variable | vulture 60% | alto | manter | usado fora do arquivo: tests/test_avaliacao_ironia.py, tests/test_ironia_dominio.py |
| `fraus/avaliacao_ironia.py:60` `falsos_negativos` | variable | vulture 60% | alto | manter | usado fora do arquivo: tests/test_avaliacao_ironia.py |
| `fraus/avaliacao_ironia.py:63` `maior_confianca_errada` | variable | vulture 60% | alto | manter | usado fora do arquivo: notebooks/07_treino_laya.ipynb, tests/test_avaliacao_ironia.py |
| `fraus/avaliacao_ironia.py:134` `dominio` | variable | vulture 60% | alto | manter | usado fora do arquivo: dashboard/lib/api.ts, fraus/api/contexto.py, fraus/api/main.py ... |
| `fraus/avaliacao_ironia.py:155` `conferir_registro_equilibrado` | function | vulture 60% | alto | manter | usado fora do arquivo: tests/test_regua_pares_rascunho.py |
| `fraus/avaliacao_ironia.py:194` `concordancia` | variable | vulture 60% | alto | manter | usado fora do arquivo: fraus/consolidacao_regua.py, scripts/consolidar_regua_ironia.py, tests/test_consolidacao_regua.py ... |
| `fraus/avaliacao_ironia.py:209` `carregar_regua_pares` | function | vulture 60% | alto | manter | usado fora do arquivo: tests/test_regua_pares_congelada.py |
| `fraus/baseline_estilo.py:66` `BaselineEstilo` | class | vulture 60% | alto | manter | usado fora do arquivo: tests/test_baseline_estilo.py |
| `fraus/baseline_estilo.py:81` `prever_probabilidades` | method | vulture 60% | alto | manter e reportar | sem chamador hoje; pertence a regua de ironia em andamento (plano de 08/10/2026) |
| `fraus/comparacao_modelos.py:118` `acuracia_por_par` | function | vulture 60% | alto | manter | usado fora do arquivo: tests/test_baseline_estilo.py, tests/test_comparacao_por_par.py |
| `fraus/comparacao_modelos.py:159` `ece` | function | vulture 60% | alto | manter | usado fora do arquivo: notebooks/05_calibracao.ipynb, tests/test_comparacao_por_par.py |
| `fraus/comparacao_modelos.py:241` `avaliar_conjunto` | function | vulture 60% | alto | manter | usado fora do arquivo: notebooks/07_treino_laya.ipynb, tests/test_comparacao_modelos.py, tests/test_comparacao_por_par.py ... |
| `fraus/comparacao_modelos.py:325` `montar_laudo` | function | vulture 60% | alto | manter | usado fora do arquivo: notebooks/07_treino_laya.ipynb, tests/test_comparacao_modelos.py, tests/test_comparacao_por_par.py ... |
| `fraus/db.py:264` `VEREDITOS` | variable | vulture 60% | alto | manter | usado fora do arquivo: dashboard/lib/api.ts, dashboard/lib/vereditos.ts, tests/test_auditoria_02_10.py ... |
| `fraus/db.py:365` `traco` | variable | vulture 100% | alto | manter | parametro exigido pela assinatura (__exit__/handler) |
| `fraus/db.py:415` `traco` | variable | vulture 100% | alto | manter | parametro exigido pela assinatura (__exit__/handler) |
| `fraus/db.py:597` `row_factory` | attribute | vulture 60% | alto | manter | atribuicao em objeto externo (SessionOptions/zipfile/row_factory/hook) |
| `fraus/db.py:619` `metricas_do_pool` | method | vulture 60% | alto | manter | usado fora do arquivo: tests/test_pool_postgres.py |
| `fraus/divisao.py:39` `dividir_por_autor` | function | vulture 60% | alto | manter | usado fora do arquivo: notebooks/04_treino_ironia.ipynb, notebooks/07_treino_laya.ipynb, tests/test_divisao.py |
| `fraus/divisao.py:51` `conferir_divisao` | function | vulture 60% | alto | manter | usado fora do arquivo: notebooks/04_treino_ironia.ipynb, notebooks/07_treino_laya.ipynb, tests/test_divisao.py |
| `fraus/ingest/arquivos.py:282` `ZLIB_MAX_OUTPUT_LENGTH` | attribute | vulture 60% | alto | manter | atribuicao em objeto externo (SessionOptions/zipfile/row_factory/hook) |
| `fraus/ingest/csv_driver.py:32` `carregar_csv` | function | vulture 60% | alto | manter | usado fora do arquivo: tests/test_csv_driver.py |
| `fraus/ingest/gerador_ironia.py:223` `gerar_exemplos` | function | vulture 60% | alto | manter | usado fora do arquivo: notebooks/04_treino_ironia.ipynb, notebooks/05_treino_multitarefa.ipynb, tests/test_gerador_ironia.py |
| `fraus/modelos.py:25` `_valida_enviada_em` | method | vulture 60% | alto | manter | Pydantic/validador chamado pelo framework |
| `fraus/modelos.py:43` `_valida_iniciada_em` | method | vulture 60% | alto | manter | Pydantic/validador chamado pelo framework |
| `fraus/modelos.py:48` `_valida_encerrada_em` | method | vulture 60% | alto | manter | Pydantic/validador chamado pelo framework |
| `fraus/pesos_fp16.py:24` `guardar_em_fp16` | function | vulture 60% | alto | manter | usado fora do arquivo: notebooks/07_treino_laya.ipynb, tests/test_pesos_fp16.py |
| `fraus/sinais/curadoria.py:93` `total_de_palavras` | method | vulture 60% | alto | manter | usado fora do arquivo: tests/test_curadoria.py |
| `fraus/sinais/curadoria.py:96` `total_de_emojis` | method | vulture 60% | alto | manter | usado fora do arquivo: tests/test_curadoria.py |
| `fraus/sinais/emocao.py:29` `ALEGRIA` | variable | vulture 60% | alto | manter | constante que nomeia a ordem das 7 classes (contrato do modelo) |
| `fraus/sinais/emocao.py:29` `MEDO` | variable | vulture 60% | alto | manter | idem |
| `fraus/sinais/emocao.py:29` `SURPRESA` | variable | vulture 60% | alto | manter | idem |
| `fraus/sinais/emocao.py:29` `TRISTEZA` | variable | vulture 60% | alto | manter | idem |
| `fraus/sinais/laya_compat.py:44` `build_sequence` | function | vulture 60% | alto | manter | instalado em `laya.common` por `laya_compat.instalar` via `globals()[nome]` |
| `fraus/sinais/laya_compat.py:84` `collapsed_options` | function | vulture 60% | alto | manter | instalado em `laya.common` por `laya_compat.instalar` via `globals()[nome]` |
| `fraus/sinais/laya_compat.py:94` `answer_confidence` | function | vulture 60% | alto | manter | instalado em `laya.common` por `laya_compat.instalar` via `globals()[nome]` |
| `fraus/sinais/laya_compat.py:98` `confidence_from_probs` | function | vulture 60% | alto | manter | instalado em `laya.common` por `laya_compat.instalar` via `globals()[nome]` |
| `fraus/sinais/laya_compat.py:104` `temp_bucket` | function | vulture 60% | alto | manter | instalado em `laya.common` por `laya_compat.instalar` via `globals()[nome]` |
| `fraus/sinais/laya_compat.py:109` `clamp_temperature` | function | vulture 60% | alto | manter | instalado em `laya.common` por `laya_compat.instalar` via `globals()[nome]` |
| `fraus/sinais/laya_compat.py:115` `collate_items` | function | vulture 60% | alto | manter | instalado em `laya.common` por `laya_compat.instalar` via `globals()[nome]` |
| `fraus/sinais/laya_compat.py:140` `_fix_tokenizer_config` | attribute | vulture 60% | alto | manter | atribuicao em objeto externo (SessionOptions/zipfile/row_factory/hook) |
| `fraus/sinais/laya_compat.py:142` `_check_question` | method | vulture 60% | alto | manter | Pydantic/validador chamado pelo framework |
| `fraus/sinais/onnx.py:81` `intra_op_num_threads` | attribute | vulture 60% | alto | manter | atribuicao em objeto externo (SessionOptions/zipfile/row_factory/hook) |
| `fraus/sinais/onnx.py:86` `enable_cpu_mem_arena` | attribute | vulture 60% | alto | manter | atribuicao em objeto externo (SessionOptions/zipfile/row_factory/hook) |
| `fraus/sinais/onnx.py:87` `graph_optimization_level` | attribute | vulture 60% | alto | manter | atribuicao em objeto externo (SessionOptions/zipfile/row_factory/hook) |
| `fraus/treino_laya.py:48` `distribuicao_de_votos` | function | vulture 60% | alto | manter | usado fora do arquivo: notebooks/07_treino_laya.ipynb, tests/test_treino_laya.py |
| `fraus/treino_laya.py:62` `distribuicao_de_rotulo` | function | vulture 60% | alto | manter | usado fora do arquivo: notebooks/07_treino_laya.ipynb, tests/test_treino_laya.py |
| `fraus/treino_laya.py:80` `caso_emocao` | function | vulture 60% | alto | manter | usado fora do arquivo: notebooks/07_treino_laya.ipynb, tests/test_treino_laya.py |
| `fraus/treino_laya.py:99` `caso_ironia` | function | vulture 60% | alto | manter | usado fora do arquivo: notebooks/07_treino_laya.ipynb, tests/test_treino_laya.py |
| `fraus/treino_laya.py:117` `repeticoes_por_classe` | function | vulture 60% | alto | manter | usado fora do arquivo: notebooks/07_treino_laya.ipynb, tests/test_treino_laya.py |
| `fraus/treino_laya.py:141` `mapa_de_poda` | function | vulture 60% | alto | manter | usado fora do arquivo: notebooks/07_treino_laya.ipynb, tests/test_treino_laya.py |
| `scripts/gerenciar_artefatos.py:72` `compress_type` | attribute | vulture 60% | alto | manter | atribuicao em objeto externo (SessionOptions/zipfile/row_factory/hook) |
| `scripts/gerenciar_artefatos.py:73` `external_attr` | attribute | vulture 60% | alto | manter | atribuicao em objeto externo (SessionOptions/zipfile/row_factory/hook) |
| `scripts/gravar_leituras_lp.py:82` `redirect_request` | method | vulture 60% | alto | manter | usado fora do arquivo: tests/test_gravar_leituras_lp.py |
| `scripts/gravar_leituras_lp.py:82` `req` | variable | vulture 100% | alto | manter | parametro exigido pela assinatura (__exit__/handler) |
| `scripts/hook_log_weasyprint.py:37` `on_config` | function | vulture 60% | alto | manter | hook do mkdocs, chamado pelo nome |
| `scripts/treinar_multitarefa.py:100` `forward` | method | vulture 60% | alto | manter | usado fora do arquivo: notebooks/07_treino_laya.ipynb |
