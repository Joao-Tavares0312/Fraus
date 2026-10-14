# Limpeza do repositório: inventário de 14/10/2026

Etapa A (somente leitura) da missão de enxugar o repositório. Branch
`limpeza/2026-10-14`, criada de `origin/main` (`e52376b`, merge da PR #91).
Nada foi excluído. A Etapa B espera aprovação item a item.

Ponto de partida: a auditoria de ontem
([2026-10-13-codigo-morto.md](../auditoria/2026-10-13-codigo-morto.md)) já
passou `vulture`, `deptry`, `knip` e `ruff` símbolo a símbolo e removeu o que
estava morto. Este inventário não repete aquelas decisões e trabalha no nível
de **arquivo**, redundância e versionamento.

## Conclusão primeiro

**O repositório não está inchado de código morto.** O grafo de importação
alcança **85 dos 89 módulos** de `fraus/` a partir de `fraus/api/main.py`, e os
4 restantes são usados por notebook de treino ou por script que a documentação
manda rodar. **Todo** `.ts`, `.tsx` e `.css` da dashboard é alcançado a partir de
uma rota Next. A lista de exclusão defensável tem **6 arquivos** (cerca de
1,7 MB), alguns símbolos e 12 imports. Isso é **menos de 1% dos 652
arquivos**.

Se a dor é "difícil achar onde mexer", o que pesa é a **estrutura**, não a
sobra:

- 128 arquivos em `tests/` e 42 `*.test.ts(x)` ao lado do código;
- 43 specs e planos datados em `docs/superpowers/`;
- 7,9 MB de PNG em `dashboard/public/lp-nova/`.

As duas primeiras se resolvem com índice e arquivamento (seção 5); a terceira,
com compressão (seção 4). Nenhuma delas é exclusão.

## 1. Fotografia (A1)

`git ls-files | wc -l` → **652** (o enunciado falava em 649; a PR #91 somou 3).
O total é 18,6 MB rastreados (`du -ch` → 20M com blocos).

### Por pasta

| pasta | arquivos | KB | % arq | % KB |
|---|---|---|---|---|
| dashboard | 280 | 12266 | 42,9 | 65,8 |
| fraus | 95 | 2366 | 14,6 | 12,7 |
| docs | 78 | 2007 | 12,0 | 10,8 |
| tests | 128 | 714 | 19,6 | 3,8 |
| (raiz) | 17 | 652 | 2,6 | 3,5 |
| scripts | 34 | 249 | 5,2 | 1,3 |
| notebooks | 8 | 207 | 1,2 | 1,1 |
| dados_demo | 1 | 148 | 0,2 | 0,8 |
| .github | 4 | 12 | 0,6 | 0,1 |
| dados_lp | 5 | 3 | 0,8 | 0,0 |
| api | 1 | 0 | 0,2 | 0,0 |
| overrides | 1 | 0 | 0,2 | 0,0 |

Subpastas que concentram arquivos:

| subpasta | arquivos | KB |
|---|---|---|
| `dashboard/components` | 118 | 763 |
| `dashboard/lib` | 85 | 358 |
| `dashboard/app` | 34 | 198 |
| `docs/superpowers` | 43 | 976 |
| `fraus/api` | 33 | 267 |
| `scripts/` | 32 | 203 |

Subpastas que concentram peso:

| subpasta | arquivos | KB | % do peso |
|---|---|---|---|
| `dashboard/public` | 11 | 10411 | **55,9** |
| `fraus/dados` | 6 | 1609 | 8,6 |

### Por extensão (as que pesam)

| ext | arquivos | KB | % arq | % KB |
|---|---|---|---|---|
| .png | 9 | 9255 | 1,4 | **49,7** |
| .py | 248 | 1657 | 38,0 | 8,9 |
| .hdr | 1 | 1655 | 0,2 | 8,9 |
| .md | 84 | 1641 | 12,9 | 8,8 |
| .csv | 9 | 1542 | 1,4 | 8,3 |
| .tsx | 139 | 845 | 21,3 | 4,5 |
| .json | 13 | 541 | 2,0 | 2,9 |
| .lock | 1 | 509 | 0,2 | 2,7 |
| .ts | 95 | 395 | 14,6 | 2,1 |
| .ipynb | 8 | 207 | 1,2 | 1,1 |
| .db | 1 | 148 | 0,2 | 0,8 |

### Maiores arquivos

| KB | arquivo | situação |
|---|---|---|
| 3032 | `dashboard/public/lp-nova/hero.png` | vivo (`lp.css:99-105`) |
| 2664 | `dashboard/public/lp-nova/mascara.png` | vivo |
| 2300 | `dashboard/public/lp-nova/fecho.png` | vivo |
| 1656 | `dashboard/public/assets/hdri/studio_small_06_1k.hdr` | **órfão** (C2) |
| 1500 | `fraus/dados/sentilex_pt02.csv` | vivo (sinal de léxico) |
| 744 | `dashboard/public/og-fraus.png` | vivo |
| 512 | `uv.lock` | vivo |
| 420 | `docs/assets/banner-instrumento.png` | vivo (docs) |
| 412 | `dashboard/package-lock.json` | vivo |
| 148 | `dados_demo/fraus-demo.db` | vivo (`scripts/api_demo.py:353`) |

**Duplicatas por hash** (`git ls-files | xargs sha1sum | sort | uniq -w40 -D`):

- `dashboard/public/fraus-logo.svg` ≡ `docs/assets/fraus-logo.svg` (ver C1);
- 6 `__init__.py` vazios, que são necessários.

## 2. Candidatos, por impacto

Risco = chance de ser falso positivo. Decisão proposta; nada foi executado.

| # | item | tipo | evidência | risco | decisão | justificativa |
|---|---|---|---|---|---|---|
| C1 | `docs/assets/fraus-logo.svg` (≡ `dashboard/public/fraus-logo.svg`) | arquivo gerado rastreado | `git check-ignore -v --no-index` → `.gitignore:38:/docs/assets/fraus-logo.svg`; `scripts/reunir_docs.py:27-28` o copia de `dashboard/public/` no build; sha1 idêntico | baixo | **desversionar** (`git rm --cached`) | o próprio `.gitignore` já diz que ele não deveria estar no índice |
| C2 | `dashboard/public/assets/hdri/studio_small_06_1k.hdr` (1,6 MB) e `dashboard/public/assets/ATTRIBUTION.md` | asset órfão | `git grep "studio_small\|hdri\|ATTRIBUTION"` só acha os próprios arquivos e `PROVENIENCIA.md:44-46`, que já prevê que ficariam "órfãos" quando a cena 3D da LP antiga saísse (saiu no `61db71d`, 30/09) | baixo | **excluir** e atualizar `PROVENIENCIA.md:44-46` | é o maior arquivo morto do repo: 8,9% do peso rastreado |
| C3 | `scripts/anotacao_ironia/index.html`, `scripts/anotacao_ironia/frases.json` (36 KB), `scripts/gerar_anotacao_ironia.py` | ferramenta substituída | `git grep "anotacao_ironia/\|gerar_anotacao_ironia\|frases.json"` fora de `docs/superpowers` só acha os três entre si; o fluxo foi substituído pela rota `/anotar` da dashboard (`docs/ironia.md:113-116`, "página antiga do claude.ai"); as respostas da rodada estão em `fraus/dados/anotacao_regua/anotador-claude-ai.json` | médio | **excluir** (`frases_para_anotacao` em `fraus/` fica, porque tem uso e teste) | o plano de 08/10 os cita, mas como histórico. Ver pergunta P2 |
| C4 | `formatarPercentual` (`dashboard/lib/formato.ts:60`), `formatarDiaCurto` (`:151`) | export sem chamador | `npx knip --production`; `git grep -nw` → só a definição | baixo | **excluir** | não está no doc de ontem; nenhum teste os cobre |
| C5 | 12 imports `F401` em `tests/` | import morto | `uvx ruff check tests --select F401` (lista abaixo) | baixo | **excluir** | não muda nenhum assert |
| C6 | `VENDORIZADOS` em `dashboard/eslint.config.mjs` | configuração obsoleta | a lista ignora 5 arquivos react-bits que não existem mais (`Particles`, `GlassSurface`, `StarBorder`, `GlitchText`, `WarpText`); o comentário cita `components/lp/FechoVitrine.tsx`, também inexistente | baixo | **excluir as 5 entradas e a menção** | o doc de ontem diz que o eslint trata `components/ui` como vendorizado, e isso está errado: ele trata essa lista |
| C7 | parâmetro `cliente_nao_usado=None` em `tests/test_arquivos.py:56` | parâmetro morto | vulture 100% | baixo | **excluir** | nenhum chamador o passa |
| C8 | `tests/test_sinal_estilo.py:174` (`..._ainda_conta_censura_e_intensidade`) | teste duplicado | a mesma entrada e as mesmas asserções do teste da linha 141 | baixo | **manter e reportar** | a regra 6 só permite tirar teste junto com o código que ele cobre. Ver P3 |
| C9 | `dominanteDaTela` (`dashboard/lib/hierarquia.ts:75`) | export só usado por teste | `knip --production`; só `lib/hierarquia.test.ts` o chama | médio | **manter e reportar** | pode ser regra de design ainda não ligada; tirar levaria o teste junto |

Os 12 imports de C5:

- `test_api_periodo.py:10` `timezone`
- `test_assinatura.py:7` `base64`
- `test_autenticacao.py:6` `datetime` e `timezone`
- `test_baseline_estilo.py:1` `pytest`
- `test_csv_driver.py:1` `pytest`
- `test_emocao_laya.py:3` `pytest`
- `test_evidencia.py:21` `pytest`
- `test_grafo.py:3` `TODAS_AS_CAMADAS`
- `test_indicadores.py:7` `N_MINIMO_NPS`
- `test_ordem_entre_dialetos.py:27` `timezone`
- `test_regua_pares_congelada.py:6` `CAMINHO_META_REGUA`

**Falso positivo:** o ruff também aponta `ambiente` em
`test_convites_equipe.py:7`, mas ele é fixture do pytest. Fica, e a sugestão é
marcá-lo com `# noqa`.

### Mantido: verificado e vivo

| item | por que fica |
|---|---|
| `fraus/fatias.py` | fora do grafo da API, mas usado por `scripts/avaliar_por_fatias.py`, que `docs/cartao-do-modelo.md:6` manda rodar |
| `fraus/ingest/simulador.py` | fora do grafo da API, mas usado pelo notebook 02, pelo `api_demo` e por 7 scripts |
| `fraus/ingest/gerador_ironia.py` | fora do grafo da API, mas usado pelos notebooks 04 e 05 |
| `fraus/pesos_fp16.py` | fora do grafo da API, mas usado pelo notebook 07 |
| `api/index.py` | é a entrada `functions` do `vercel.json` (deploy `fraus-api`), protegida por `tests/test_deploy_vercel.py` |
| `requirements.txt` | não é lista paralela: contém só `.[onnx]` e é lido pela Vercel |
| `dados_demo/fraus-demo.db` | snapshot do `api_demo.py`. Conferido: 64 conversas sintéticas; as tabelas de mestra, chaves, usuários, fontes e entregas estão **vazias**; sem e-mail, CPF, telefone nem token |
| `fraus/dados/*` | lidos em produção. Exceção: `anotador-claude-ai.json`, lido só por `scripts/consolidar_regua_ironia.py` (documentado) e pelo teste dele. Ele vai no pacote da Vercel por `includeFiles: "**"`; ver R4 |
| `dashboard/public/lp-nova/*.png`, `og-fraus.png`, `fraus-marca.svg`, `fraus-logo.svg`, `PROVENIENCIA.md` | referenciados (`lp.css`, metadados, `reunir_docs.py`) |
| `dashboard/scripts/*`, `dashboard/.impeccable/*` | chamados por `package.json` e `DESIGN.md`; `.impeccable` é estado da ferramenta de design (09/10) |
| `scripts/medir_*`, `investigar_*`, `validar_candidato_ironia` etc. | reproduzem números que README, handoff e cartão do modelo citam |
| notebooks 05 a 07 | `05_calibracao` gera o laudo de calibração; `05_treino_multitarefa` gera candidato não promovido; **`06_exportar_laya_onnx` gera o ZIP do Laya que roda em produção** |
| todas as fixtures do pytest (37) e todos os `tests/*.py` | nenhum teste aponta para módulo inexistente (checado por AST) |
| rotas sem consumidor no front | já decididas ontem; o OpenAPI não muda nesta limpeza |

### Mantido por dúvida (reportar)

| item | motivo |
|---|---|
| `scripts/converter_totalk.py` | sem referência no repo, mas é a interface de linha de comando de um adaptador vivo (`fraus/ingest/totalk.py`) |
| `cloudbuild.yaml`, `.gcloudignore`, `scripts/configurar_cloud_run.ps1`, `docs/cloud-run.md` | não há deploy ativo no Cloud Run (produção = Vercel + Supabase), mas estão documentados como alternativa e cobertos por teste. Saem os quatro juntos, se você desistir do Cloud Run (P1) |
| `scripts/provisionar_oracle.sh`, `scripts/abrir_portas_oracle.py` | a Oracle hoje guarda só o Object Storage dos modelos. Não verifiquei se você ainda quer a VM (P1) |
| `dashboard/public/icon-32.png`, `icon-512.png` (14 KB) | nenhum código os referencia, mas `docs/assets/fonte/gerar-assets-instrumento.mjs:228-229` os recria; não verifiquei URL externa (P4) |
| `docs/social-preview.png` (84 KB) | sem referência; provavelmente é o social preview do GitHub, subido à mão (não verificado) |
| 13 cópias de `MotorFalso` em `tests/` (6 variantes); ~15 arquivos importam dublês de `tests/test_api.py` | consolidar num `conftest` seria refactor, não exclusão |
| ingestão em três caminhos (`csv_driver`, `totalk`, `mapeador`) | a docstring do `mapeador` diz que ele dispensa adaptadores; não medi se ele cobre a Totalk. Risco alto |
| 4 route handlers do proxy (`chaves`, `chaves/[id]`, `ligar-autenticacao`, `sessao/entrar`) com o mesmo esqueleto | juntar num helper é refactor |
| `lib/formato.test.ts` e `lib/formato-led.test.ts` testam o mesmo módulo | junção cosmética |

## 3. Área protegida (regra 5): só reporte

- `modelos/` local contém só `comparacao_modelos.json` e `metricas_laya.json`;
  **não há pesos nesta máquina** (`find / -name fusor.joblib` vazio). Por isso o
  smoke falha (ver Baseline). Não mexi.
- `NOMES_FEATURES`, `PESO_NEUTRO_NO_SCORE` e `fraus/sinais/ironia.py`: nenhum
  candidato. Os `ERA001` de `fraus/fusor.py` são rótulos de família dentro de
  `NOMES_FEATURES`, não código comentado.
- O par vigente × candidato (`emocao`/`emocao_laya`, `ironia`/`ironia_laya`)
  serve a rota de comparação e fica.

## 4. Ganho estimado

| medida | antes | depois (se C1–C7 forem aprovados) |
|---|---|---|
| arquivos rastreados | 652 | **646** (−6: C1, C2 ×2, C3 ×3) |
| peso rastreado | 18,6 MB | ~16,9 MB (−1,7 MB, sendo 1,6 MB do `.hdr`) |
| linhas | — | cerca de −600 (`index.html` + `frases.json` + gerador ≈ 550; o resto é TS e imports). Estimativa: conto ao executar |
| dependências | — | **nenhuma sai**: nenhuma dependência está órfã nem é usada só por candidato |
| bundle do front (`.next/static`) | 3,2 MB | não muda: nenhum candidato está no grafo do bundle. O `.hdr` mora em `public/`, que vai como arquivo estático, não no bundle |
| pacote da API (`fraus/`) | 2,5 MB | não muda |
| `pytest` | 167 s | não muda de forma mensurável |
| `next build` | 13,6 s (com cache) | não muda |

O ganho real em peso **não está na exclusão**: os três pôsteres
`lp-nova/*.png` somam 7,9 MB em PNG RGBA 1600×1000. Comprimir para WebP/AVIF
no gerador (`npm run posteres`) cortaria provavelmente mais de 6 MB, mas isso
é mudança de pipeline, fora do escopo "só exclusão". Ver P5.

## 5. Arquivos que não deveriam estar versionados (A2) e higiene

- **Nada de `.next`, `node_modules`, `__pycache__`, `.pyc`, logs, `.env` real,
  zip, pesos, coverage, Playwright ou screenshot de teste versionado.**
- Segredos: a varredura por `fra_`, `frs_`, `whsec_`, JWT (`eyJ…`), `sk-`,
  `postgres://user:senha@` e `FRAUS_CHAVE_MESTRA=` não achou nada real:
  - as URLs postgres com senha são de teste em localhost (`testes.yml:51`,
    `tests/conftest.py:13`, `tests/test_pool_postgres.py:41`);
  - os `FRAUS_CHAVE_MESTRA=` com valor são exemplo de plano, referência ao
    Secret Manager ou `openssl rand` gerado na hora.
  
  **Não há achado de segurança nem histórico para limpar.**
- `.mcp.json` versionado contém o `project_ref` do Supabase de produção. Não é
  segredo, mas identifica o projeto. Reportar.
- **Lacunas no `.gitignore`** (proposta: acrescentar):
  - `/dist/`: `docs/deploy-vercel.md:239` manda gerar `dist/modelos-*.zip`
    (~1 GB) e nada o ignora, então um `git add -A` o versionaria;
  - `/site-pdf/`: gerado pelo `docs.yml:97`;
  - `.test-temp*/` (o `.gitignore` cobre só `.test-temp-vercel-new/`; o
    `.vercelignore` cobre o padrão inteiro);
  - `.api-vercel`.
- `reports/` e `research_notes/` estão **untracked** na raiz (o rascunho do
  treino do Laya). Não toquei. Ver P6.
- **Plano de arquivamento de docs (só proposta).** `docs/superpowers/` tem 43
  arquivos fora do nav e fora do site público. Pelo critério "os arquivos
  descritos existem na `main`", cerca de 27 estão concluídos e 11 são temas
  visuais substituídos pelo Instrumento: vidro líquido, vaporwave, a fenda,
  pauta, tipografia, hierarquia e vitrine. Proposta: criar
  `docs/superpowers/README.md` com o status de cada um; mover os 11 para
  `docs/superpowers/arquivo/` é opcional. Nada se apaga.

**Docs que divergem do código** (correção, não exclusão):

1. `docs/treinamento.md:684` diz que o notebook 07 está "ainda não executado".
   Ele rodou em 02/10 e não foi promovido.
2. A tabela de `docs/treinamento.md:12-17` lista só os notebooks 01 a 04. Não
   cita o **06**, que gera o ZIP do Laya em produção.
3. O cabeçalho do `Dockerfile` ainda argumenta "por que não serverless",
   embora a produção esteja na Vercel.
4. O `CLAUDE.md` diz que `mkdocs-pdf.yml` herda do principal; ele herda de
   `mkdocs-publico.yml`.
5. A lista de exclusões do site público no `CLAUDE.md` está incompleta: faltam
   `auditoria/`, `colab.md`, `deploy-vercel.md` e `cloud-run.md`.
6. `docs/colab.md` cita `scripts/treinar.py`, que não existe, e o WSL `dell08`.
7. `dashboard/.env.local.example` define `NEXT_PUBLIC_API_URL`, que ninguém
   lê; `NEXT_PUBLIC_SITE_URL` é lida e não está documentada.
8. `dashboard/public/PROVENIENCIA.md:44` diz que o HDRI continua referenciado
   (corrige-se junto com C2).
9. Nenhum link aponta para `docs/auditoria/2026-10-13-relatorio.md`.

**Ambiente (achado lateral):** o `.venv` está em **Python 3.14.7**, não em
3.11. O `pyproject` pede `>=3.11` e não há `.python-version`. A suíte passa,
mas não é a versão que o `CLAUDE.md` declara.

## 6. Plano de lotes (do menor risco para o maior)

Um commit por lote. Depois de cada lote rodam `pytest`, smoke, `tsc`, `npm test`
e `npm run build`; se algo quebrar, `git revert` do lote.

| lote | conteúdo | risco |
|---|---|---|
| **L1** higiene de versionamento | C1 (`git rm --cached docs/assets/fraus-logo.svg`) e as 4 entradas novas no `.gitignore` | baixo |
| **L2** asset órfão | C2 (`.hdr` e `ATTRIBUTION.md`) e a correção de `PROVENIENCIA.md:44-46` | baixo |
| **L3** front morto | C4 (2 funções) e C6 (5 entradas do eslint e o comentário) | baixo |
| **L4** testes | C5 (12 imports) e C7 (o parâmetro); C8 só se você responder sim em P3 | baixo |
| **L5** ferramenta substituída | C3 (página, JSON e gerador da anotação antiga) | médio |
| **L6** *(opcional, se P1 = sim)* | infra abandonada: Cloud Run e/ou Oracle, com os testes, docs e trechos do README que os citam | médio |
| **L7** *(fora de "só exclusão", aprovação separada)* | as 9 correções de documentação e o `superpowers/README.md` | baixo |

## 7. Perguntas

- **P1.** O Cloud Run e a VM da Oracle (`cloudbuild.yaml`, `.gcloudignore`,
  `configurar_cloud_run.ps1`, `docs/cloud-run.md`, `provisionar_oracle.sh`,
  `abrir_portas_oracle.py`) ainda são plano B, ou posso tirá-los (L6)?
- **P2.** A página de anotação antiga (C3) pode sair, sabendo que o fluxo vivo
  é a rota `/anotar` e que as respostas já estão consolidadas?
- **P3.** O teste duplicado em `test_sinal_estilo.py` (C8) é exceção aceitável
  à regra 6 (cópia idêntica, sem perda de cobertura), ou fica?
- **P4.** `icon-32.png` e `icon-512.png`: existe algum lugar fora do repo
  (manifest antigo, link externo) que os use? Se não, saem junto com as duas
  linhas do gerador.
- **P5.** Quer a compressão dos pôsteres `lp-nova` (−6 MB estimados) como
  tarefa separada, fora desta limpeza?
- **P6.** `reports/` e `research_notes/`: entram no git (em `docs/notas/`?), vão
  para o `.gitignore` ou ficam como estão?
- **P7.** O L7 (correção de docs) entra nesta branch ou numa PR própria?
- **P8.** Este arquivo mora em `docs/limpeza/`, que o `mkdocs-publico.yml`
  **não** exclui, então ele iria para o site público. Acrescento `limpeza/` ao
  `exclude_docs` (como `auditoria/`) no L1? Ainda não editei nada.

## Baseline (antes de qualquer exclusão)

Máquina local, `.venv` em Python 3.14.7, branch em `e52376b`.

| comando | resultado |
|---|---|
| `uv sync --extra dev --extra torch` | ok |
| `uv run pytest -q` | **1393 passed, 7 skipped, 1 deselected**, 171 warnings, 166,9 s (2 min 50 s de parede) |
| `uv run python scripts/smoke_integracoes.py` | **falha pré-existente de ambiente:** "o motor nao ficou pronto (erro) -- confira se os tres modelos estao em modelos/". `/saude` responde 200 e `/saude/prontidao` responde 503, porque esta máquina não tem os pesos. Não é regressão; o critério depois de cada lote é "a mesma falha, no mesmo ponto" |
| OpenAPI | `/tmp/openapi-antes.json`, gerado por `criar_app(Banco(tmp), motor=None).openapi()` sem subir servidor: **76 caminhos** |
| `npm ci` | ok |
| `npm test` (vitest) | **42 arquivos, 351 testes passaram**, 11,3 s |
| `npx tsc --noEmit` | exit 0 |
| `npx tsc --noEmit --noUnusedLocals --noUnusedParameters` | 0 erros |
| `npm run build` | ok, 13,6 s com cache; 13 páginas estáticas; `.next/static` = 3,2 MB |
| `npm audit` | 9 *high*, todas em devDependencies (`shadcn`, `eslint-config-next`, `ts-morph`, `micromatch`, `braces`…); `npm audit --omit=dev` → **0** |
| `git ls-files \| wc -l` | 652 |

Ferramentas da Etapa A:

- Python: grafo de importação por AST (imports dentro de função, strings
  `"fraus.x"` e pacotes pais), `uvx ruff --select F401,F841,ERA001`,
  `uvx vulture --min-confidence 80`;
- dashboard: `npx knip`, `npx knip --production`, `tsc` com unused, grep por
  classe CSS e asset;
- busca textual: `git grep` em código, testes, docs, workflows,
  `vercel.json`, `pyproject.toml`, `package.json` e o JSON dos notebooks;
- `deptry` não foi rodado de novo: nenhum candidato muda dependência, e o
  resultado de ontem continua válido.
