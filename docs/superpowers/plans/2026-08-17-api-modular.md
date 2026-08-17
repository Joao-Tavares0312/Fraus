# API modular — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Quebrar `fraus/api/main.py` (1367 linhas, ~30 rotas em closures) em módulos por domínio, sem mudar uma vírgula do contrato HTTP.

**Architecture:** As rotas deixam de ser closures sobre `criar_app` e viram funções de nível de módulo em `APIRouter`s, recebendo um `Contexto` (dataclass com `banco`, `motor`, `raiz`, `chave_mestra` e os derivados compartilhados) por `Depends`. Contratos de entrada em `esquemas.py`, autenticação em `seguranca.py`, helpers puros em `periodo.py`/`caminhos.py`, e a classe `Motor` desce para `fraus/motor.py` por ser domínio, não borda HTTP.

**Tech Stack:** Python 3.11 · FastAPI · Pydantic v2 · pytest · uv

## Global Constraints

- **O contrato HTTP não muda.** Mesmos paths, mesmos corpos, mesmos status, mesmos cabeçalhos.
- **Nenhum teste existente é editado.** Se um precisar mudar, o refactor quebrou o contrato — pare e reveja. Testes NOVOS só na Task 1.
- **Todo código movido é movido, não reescrito.** Docstrings e comentários acompanham a linha que documentam. Renomear `_privado` para público na hora de mover é a única alteração permitida.
- **`criar_app(banco, motor, raiz_importacao=None, chave_mestra=None) -> FastAPI` mantém assinatura e semântica.**
- `from fraus.api.main import Motor` e `uvicorn fraus.api.main:app` continuam funcionando.
- Ordem de middleware é comportamento: o CORS é registrado DEPOIS do middleware de chave (em Starlette o último registrado é o mais externo), senão o preflight morre em 401.
- Comando de teste: `uv run pytest -q` na raiz do repositório.
- Cada task termina com a suíte inteira verde e um commit.

---

### Task 1: Fechar as lacunas de cobertura

Rede de segurança antes de mover qualquer linha. Auditoria das ~30 rotas contra a suíte atual apontou duas descobertas: `POST /analisar/arquivo` (zero testes) e `POST /ingestao` (só o par 401/201 — o canal derivado da fonte e a recusa de fonte desativada não são exercidos, apesar de documentados na docstring da rota).

**Files:**
- Modify: `tests/test_api.py` (acrescentar ao fim)
- Modify: `tests/test_autenticacao.py` (acrescentar ao fim)

**Interfaces:**
- Consumes: fixture `cliente` de `tests/test_api.py` (`criar_app` com `MotorFalso` e `raiz_importacao=tmp_path`); helpers `_cliente`, `_criar_fonte`, `MESTRA` de `tests/test_autenticacao.py`
- Produces: nada de código de produção — só a rede que as tasks 2-14 usam

- [ ] **Step 1: Escrever os testes de `/analisar/arquivo`**

Acrescentar ao fim de `tests/test_api.py`:

```python
def test_analisar_arquivo_aceita_csv_e_nao_grava_nada(cliente):
    """Upload multipart analisa e descarta: nada entra no banco."""
    resposta = cliente.post(
        "/analisar/arquivo",
        files={"arquivo": ("conversa.csv", CSV.encode("utf-8"), "text/csv")},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["conversas_no_arquivo"] == 1
    assert corpo["conversas_analisadas"] == 1
    assert len(corpo["analises"]) == 1
    # A rota nao persiste: a listagem segue vazia depois da analise.
    assert cliente.get("/conversas").json() == []


def test_analisar_arquivo_vazio_e_400(cliente):
    resposta = cliente.post(
        "/analisar/arquivo",
        files={"arquivo": ("vazio.csv", b"", "text/csv")},
    )
    assert resposta.status_code == 400
    assert "vazio" in resposta.json()["detail"]


def test_analisar_arquivo_ilegivel_e_400_que_explica(cliente):
    """Formato que a extracao nao le vira 400 nomeando o esperado, nunca 500."""
    resposta = cliente.post(
        "/analisar/arquivo",
        files={"arquivo": ("foto.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, "image/png")},
    )
    assert resposta.status_code == 400
    assert resposta.json()["detail"]
```

- [ ] **Step 2: Rodar e ver passar (são testes de caracterização do código atual)**

Run: `uv run pytest tests/test_api.py -q -k analisar_arquivo`
Expected: 3 passed. Se algum falhar, o comportamento atual difere do descrito — **corrija o teste para descrever o que a API faz hoje**, não a API. O objetivo é fotografar o comportamento, não julgá-lo.

- [ ] **Step 3: Escrever os testes de `/ingestao`**

Acrescentar ao fim de `tests/test_autenticacao.py`:

```python
def test_ingestao_usa_o_canal_da_fonte_e_ignora_o_corpo(tmp_path):
    """Quem manda o dado nao escolhe em que canal ele e contabilizado."""
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    mestra = {"Authorization": f"Bearer {MESTRA}"}
    fonte = _criar_fonte(cliente, mestra)
    chave = cliente.post(
        f"/integracoes/fontes/{fonte['id']}/chave", headers=mestra
    ).json()["chave"]

    resposta = cliente.post(
        "/ingestao",
        json={
            "id": "canal-1",
            "canal": "canal-inventado-pelo-cliente",
            "mensagens": [
                {
                    "autor": "cliente",
                    "texto": "obrigado",
                    "enviada_em": "2026-08-14T12:00:00+00:00",
                }
            ],
        },
        headers={"Authorization": f"Bearer {chave}"},
    )
    assert resposta.status_code == 201
    assert resposta.json()["canal"] == fonte["canal"]
    assert resposta.json()["fonte"] == fonte["nome"]


def test_ingestao_de_fonte_desativada_e_403(tmp_path):
    """O interruptor da tela de Integracoes precisa desligar de fato."""
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    mestra = {"Authorization": f"Bearer {MESTRA}"}
    fonte = _criar_fonte(cliente, mestra)
    chave = cliente.post(
        f"/integracoes/fontes/{fonte['id']}/chave", headers=mestra
    ).json()["chave"]
    cliente.patch(
        f"/integracoes/fontes/{fonte['id']}", json={"ativa": False}, headers=mestra
    )

    resposta = cliente.post(
        "/ingestao",
        json={
            "id": "desligada-1",
            "mensagens": [
                {
                    "autor": "cliente",
                    "texto": "oi",
                    "enviada_em": "2026-08-14T12:00:00+00:00",
                }
            ],
        },
        headers={"Authorization": f"Bearer {chave}"},
    )
    # 403, nao 401: a chave esta certa, o que esta desligado e a fonte.
    assert resposta.status_code == 403
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_autenticacao.py -q -k ingestao`
Expected: todos passam. Mesma regra do Step 2 — divergência corrige o teste, não a API.

- [ ] **Step 5: Rodar a suíte inteira e registrar a linha de base**

Run: `uv run pytest -q`
Expected: verde. **Anote o número total de testes** — ele não pode cair em nenhuma task seguinte.

- [ ] **Step 6: Commit**

```bash
git add tests/test_api.py tests/test_autenticacao.py
git commit -m "test(api): cobrir /analisar/arquivo e o contrato de fonte da ingestao"
```

---

### Task 2: `esquemas.py` — os contratos de entrada

Os sete `BaseModel` não dependem de nada do app. É o movimento de menor risco e serve de ensaio do padrão.

**Files:**
- Create: `fraus/api/esquemas.py`
- Modify: `fraus/api/main.py:130-174` (remover as classes, importar de `esquemas`)

**Interfaces:**
- Produces: `fraus.api.esquemas.{PedidoFonte, PedidoAjusteFonte, PedidoImportacao, PedidoSimulacao, PedidoAnalise, PedidoChaveAcesso, PedidoIngestao}` e a constante `TIPOS_DE_FONTE: tuple[str, ...]`

- [ ] **Step 1: Criar `fraus/api/esquemas.py`**

Mover, com docstrings e comentários intactos, as classes das linhas 133-174 de `main.py` e a constante `TIPOS_DE_FONTE` (linha 130). O cabeçalho do módulo novo:

```python
"""Contratos de ENTRADA da API -- o que o cliente pode mandar.

Nenhum deles aceita veredito: score, nota e categoria sao derivados no
servidor em toda entrada, e um campo de entrada que os aceitasse seria a
porta para o cliente escolher a propria nota.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from fraus.modelos import Mensagem
```

- [ ] **Step 2: Trocar as definições por import em `main.py`**

Remover as linhas 130-174 e acrescentar ao bloco de imports:

```python
from fraus.api.esquemas import (PedidoAjusteFonte, PedidoAnalise,
                                PedidoChaveAcesso, PedidoFonte,
                                PedidoImportacao, PedidoIngestao,
                                PedidoSimulacao, TIPOS_DE_FONTE)
```

- [ ] **Step 3: Rodar a suíte**

Run: `uv run pytest -q`
Expected: verde, mesmo total da Task 1.

- [ ] **Step 4: Commit**

```bash
git add fraus/api/esquemas.py fraus/api/main.py
git commit -m "refactor(api): contratos de entrada saem para esquemas.py"
```

---

### Task 3: `fraus/motor.py` — o domínio sai da borda HTTP

`Motor` (linhas 176-368) amarra classificador e fusor. É o equivalente ao `libs/tracking-core` do wascer-watcher e não tem nada de HTTP. Os testes usam dublês duck-typed, então nada na suíte importa a classe — mas `scripts/api_demo.py` pode, e o reexport protege isso.

**Files:**
- Create: `fraus/motor.py`
- Modify: `fraus/api/main.py:176-368` (remover a classe, importar e reexportar)

**Interfaces:**
- Produces: `fraus.motor.Motor` com os métodos públicos `pontuar_conversa(conversa) -> float | None`, `atribuir_conversa(conversa) -> dict`, `importancias() -> dict`, `analisar_conversa(conversa, referencia=None) -> dict`, `simular_texto(texto: str) -> dict`
- Consumes: nada das tasks anteriores

- [ ] **Step 1: Criar `fraus/motor.py`**

Mover a classe inteira (linhas 176-368), com toda a documentação. Os imports que ela precisa, hoje no topo de `main.py`:

```python
from fraus.fusor import Fusor, montar_features
from fraus.sinais.emocao import (NOMES_EMOCOES, ClassificadorEmocao,
                                 desprezo_derivado)
from fraus.sinais.emoji import emojis_com_posicao, score_do_emoji
from fraus.sinais.ironia import IRONICO, ClassificadorIronia
from fraus.sinais.palavras import pesos_das_palavras, vocabulario
from fraus.sinais.texto import (INSATISFEITO, NEUTRO, SATISFEITO,
                                ClassificadorTexto)
```

- [ ] **Step 2: Importar e reexportar em `main.py`**

```python
from fraus.motor import Motor  # reexportado: `from fraus.api.main import Motor` segue valendo
```

Depois de remover a classe, apagar de `main.py` os imports que só ela usava (`montar_features`, `NOMES_EMOCOES`, `desprezo_derivado`, `IRONICO`, `pesos_das_palavras`, `vocabulario`, `INSATISFEITO`, `NEUTRO`, `SATISFEITO`, `emojis_com_posicao`, `score_do_emoji`). **Confira um a um** com `grep -n "<nome>" fraus/api/main.py` antes de remover: `criar_app_padrao` ainda usa `ClassificadorTexto`, `ClassificadorEmocao`, `ClassificadorIronia` e `Fusor`, e `_montar_analise` ainda usa `contar_palavras`.

- [ ] **Step 3: Verificar que o reexport funciona**

Run: `uv run python -c "from fraus.api.main import Motor; print(Motor)"`
Expected: imprime `<class 'fraus.motor.Motor'>`

- [ ] **Step 4: Rodar a suíte**

Run: `uv run pytest -q`
Expected: verde, mesmo total.

- [ ] **Step 5: Commit**

```bash
git add fraus/motor.py fraus/api/main.py
git commit -m "refactor(motor): a classe Motor sai da borda HTTP para o dominio"
```

---

### Task 4: `periodo.py` e `caminhos.py` — helpers puros

Duas famílias de helper que não dependem de `banco` nem de `motor`: validação de recorte de período e resolução de caminho. Vão juntas porque nenhuma das duas tem teste próprio e ambas são exercidas pelas mesmas rotas.

**Files:**
- Create: `fraus/api/periodo.py`
- Create: `fraus/api/caminhos.py`
- Modify: `fraus/api/main.py` (remover as funções, importar)

**Interfaces:**
- Produces:
  - `fraus.api.periodo.dia_ou_400(valor: str | None, nome: str) -> date | None`
  - `fraus.api.periodo.recorte_ou_400(de: str | None, ate: str | None) -> tuple[date | None, date | None]`
  - `fraus.api.periodo.no_recorte(iniciada_em: datetime, inicio: date | None, fim: date | None) -> bool`
  - `fraus.api.caminhos.resolver_dentro_da_raiz(raiz: Path, caminho_pedido: str) -> Path`
  - `fraus.api.caminhos.metricas_de(caminho: Path) -> dict | None`
  - as constantes de path: `CAMINHO_MODELO_TEXTO`, `CAMINHO_MODELO_EMOCAO`, `CAMINHO_MODELO_IRONIA`, `CAMINHO_FUSOR`, `CAMINHO_BANCO`, `CAMINHO_METRICAS`, `CAMINHO_METRICAS_EMOCAO`, `CAMINHO_METRICAS_IRONIA`, `RAIZ_IMPORTACAO`

- [ ] **Step 1: Criar `fraus/api/periodo.py`**

Mover `_dia_ou_400` (linhas 765-780), `_recorte_ou_400` (634-642) e `_no_recorte` (644-646), **tirando o sublinhado** — deixam de ser privadas ao virar módulo. As três são funções puras hoje definidas dentro de `criar_app` sem fechar sobre nada dele; conferir isso ao mover. Cabeçalho:

```python
"""Recorte de periodo das rotas de leitura -- `de` e `ate`, pontas INCLUSIVAS.

Data malformada e 400 que NOMEIA o parametro, nunca filtro descartado em
silencio: um recorte ignorado devolveria a serie inteira parecendo o recorte
pedido, e o grafico mentiria sem nenhum sinal de erro.
"""
```

- [ ] **Step 2: Criar `fraus/api/caminhos.py`**

Mover `resolver_dentro_da_raiz` (371-386), `_metricas_de` → `metricas_de` (389-397) e as constantes de path das linhas 57-75 e 120.

- [ ] **Step 3: Importar em `main.py` e apagar as definições**

```python
from fraus.api.caminhos import (CAMINHO_BANCO, CAMINHO_FUSOR,
                                CAMINHO_METRICAS, CAMINHO_METRICAS_EMOCAO,
                                CAMINHO_METRICAS_IRONIA, CAMINHO_MODELO_EMOCAO,
                                CAMINHO_MODELO_IRONIA, CAMINHO_MODELO_TEXTO,
                                RAIZ_IMPORTACAO, metricas_de,
                                resolver_dentro_da_raiz)
from fraus.api.periodo import dia_ou_400, no_recorte, recorte_ou_400
```

Atualizar as chamadas: `_dia_ou_400(` → `dia_ou_400(`, `_recorte_ou_400(` → `recorte_ou_400(`, `_no_recorte(` → `no_recorte(`, `_metricas_de(` → `metricas_de(`.

- [ ] **Step 4: Rodar a suíte**

Run: `uv run pytest -q`
Expected: verde, mesmo total. `tests/test_api_periodo.py` é o que prova esta task.

- [ ] **Step 5: Commit**

```bash
git add fraus/api/periodo.py fraus/api/caminhos.py fraus/api/main.py
git commit -m "refactor(api): helpers de periodo e de caminho saem para modulos proprios"
```

---

### Task 5: `contexto.py` — desatar a closure

O passo que destrava todos os seguintes. Enquanto as rotas continuam onde estão, `criar_app` passa a montar um `Contexto` e a usá-lo internamente.

**Files:**
- Create: `fraus/api/contexto.py`
- Modify: `fraus/api/main.py:477-582` (o começo de `criar_app`)

**Interfaces:**
- Consumes: `fraus.api.periodo.{recorte_ou_400, no_recorte}` (Task 4), `fraus.motor.Motor` (Task 3)
- Produces:
  - `fraus.api.contexto.Contexto` — dataclass com os campos `banco: Banco`, `motor: Motor`, `raiz: Path`, `chave_mestra: str | None` e os métodos `faixas_vigentes() -> dict`, `categoria_de(score: float | None, faixas: dict) -> str | None`, `registros_do_recorte(de: str | None, ate: str | None) -> list[tuple[Conversa, float | None]]`
  - `fraus.api.contexto.obter_contexto(request: Request) -> Contexto` — a dependência que as rotas declaram

- [ ] **Step 1: Criar `fraus/api/contexto.py`**

```python
"""O que as rotas precisam saber, num objeto so.

Ate aqui `banco`, `motor`, `raiz` e `chave_mestra` chegavam nas rotas por
FECHAMENTO LEXICO: toda rota era uma closure dentro de `criar_app`, e era
so isso que impedia elas de morarem em arquivos separados. O `Contexto`
troca o fechamento por injecao -- `Depends(obter_contexto)` -- e cada
dominio vira um modulo de verdade.

O que mora aqui e o que MAIS DE UM dominio usa. O que e de um dominio so
fica no modulo dele: este objeto atravessa a API inteira, e um saco de
tudo seria pior do que a closure que ele veio substituir.
"""

from dataclasses import dataclass
from pathlib import Path

from fastapi import Request

from fraus.configuracao import carregar as carregar_configuracao
from fraus.configuracao import faixas_de
from fraus.api.periodo import no_recorte, recorte_ou_400
from fraus.db import Banco
from fraus.indicadores import categoria_nps
from fraus.motor import Motor


@dataclass(frozen=True)
class Contexto:
    banco: Banco
    motor: Motor
    raiz: Path
    chave_mestra: str | None

    def faixas_vigentes(self) -> dict:
        """Faixa de NPS da configuracao vigente, lida a cada requisicao.

        Ler por requisicao (em vez de guardar num atributo) e o que garante
        que `/indicadores` e `/conversas` NUNCA discordem: nao existe copia
        da faixa envelhecendo em memoria depois de um PUT.
        """
        return faixas_de(carregar_configuracao(self.banco))

    def categoria_de(self, score: float | None, faixas: dict) -> str | None:
        """Categoria DERIVADA NA LEITURA do score gravado e da faixa vigente.

        A coluna `categoria` do banco e o retrato do instante da importacao
        e NAO e lida aqui: mudar a faixa muda a fatia de atendimento ja
        pontuado. O `score`, esse sim resultado do modelo, nunca e
        recalculado.
        """
        return categoria_nps(score, faixas) if score is not None else None

    def registros_do_recorte(self, de: str | None, ate: str | None) -> list:
        """Conversas do periodo, com a validacao de recorte compartilhada."""
        inicio, fim = recorte_ou_400(de, ate)
        return [
            (conversa, score)
            for conversa, score in self.banco.todas()
            if no_recorte(conversa.iniciada_em, inicio, fim)
        ]


def obter_contexto(request: Request) -> Contexto:
    """A dependencia que toda rota declara. Montada uma vez em `criar_app`."""
    return request.app.state.contexto
```

- [ ] **Step 2: Montar o `Contexto` em `criar_app`**

No começo de `criar_app`, depois da linha `app = FastAPI(...)`:

```python
    raiz = Path(raiz_importacao) if raiz_importacao is not None else RAIZ_IMPORTACAO
    ctx = Contexto(
        banco=banco,
        motor=motor,
        raiz=raiz,
        # Vazia e ausente sao a mesma coisa: "Bearer " autorizando seria a pior
        # combinacao possivel de configuracao errada com acesso liberado.
        chave_mestra=chave_mestra or None,
    )
    app.state.contexto = ctx
```

Trocar as closures `faixas_vigentes()` e `categoria_de(...)` (linhas 563-581) por chamadas a `ctx.faixas_vigentes()` e `ctx.categoria_de(...)`, e `_registros_do_recorte` (723-730) por `ctx.registros_do_recorte(...)`. Remover as três definições locais e a atribuição duplicada de `raiz` (linha 561). Onde o corpo das rotas lê `chave_mestra`, passar a ler `ctx.chave_mestra`.

- [ ] **Step 3: Rodar a suíte**

Run: `uv run pytest -q`
Expected: verde, mesmo total. Um `AttributeError: 'State' object has no attribute 'contexto'` aqui significa que `app.state.contexto` foi atribuído depois de algum uso — mova a atribuição para cima.

- [ ] **Step 4: Commit**

```bash
git add fraus/api/contexto.py fraus/api/main.py
git commit -m "refactor(api): dependencias das rotas saem da closure para um Contexto"
```

---

### Task 6: `seguranca.py` — autenticação num lugar só

**Files:**
- Create: `fraus/api/seguranca.py`
- Modify: `fraus/api/main.py:400-462, 489-549` (remover, importar)

**Interfaces:**
- Consumes: `fraus.api.contexto.Contexto` (Task 5)
- Produces:
  - `chave_bearer(authorization: str | None) -> str | None`
  - `chave_do_cabecalho(authorization: str | None) -> str`
  - `fonte_autorizada(banco: Banco, chave: str) -> dict`
  - `e_mestra(ctx: Contexto, chave: str) -> bool`
  - `acesso_autorizado(ctx: Contexto, chave: str) -> bool`
  - `exigir_mestra(ctx: Contexto, authorization: str | None) -> None`
  - `registrar_middleware_de_acesso(app: FastAPI, ctx: Contexto) -> None`

- [ ] **Step 1: Criar `fraus/api/seguranca.py`**

Mover, preservando toda a documentação: `_chave_bearer` (400-413), `_chave_do_cabecalho` (416-430), `_fonte_autorizada` (433-462) — as três perdem o sublinhado — e as closures `_e_mestra` (489-492), `_acesso_autorizado` (494-501), `_exigir_mestra` (503-519), que passam a receber `ctx: Contexto` como primeiro parâmetro em vez de fechar sobre `chave_mestra` e `banco`.

O middleware (521-549) vira uma função que o registra:

```python
def registrar_middleware_de_acesso(app: FastAPI, ctx: Contexto) -> None:
    """Exige chave em toda rota, quando ha chave mestra definida.

    Nao registra nada sem mestra: a API aberta e o modo local documentado no
    README, e um middleware que sempre autoriza seria so custo por
    requisicao com aparencia de defesa.
    """
    if ctx.chave_mestra is None:
        return

    @app.middleware("http")
    async def exigir_chave_de_acesso(request, call_next):
        # /ingestao tem credencial propria (chave de FONTE): uma credencial
        # por rota. OPTIONS e o preflight do navegador -- nao carrega header
        # de autorizacao por definicao.
        # `rstrip("/")`: `/ingestao/` e a MESMA rota (o Starlette redireciona
        # para ela), e comparar o path exato mandava o integrador que
        # configurou a URL com barra final para o 401 daqui em vez da
        # credencial de fonte.
        if request.url.path.rstrip("/") == "/ingestao" or request.method == "OPTIONS":
            return await call_next(request)
        cabecalho = request.headers.get("authorization")
        chave_recebida = chave_bearer(cabecalho)
        if chave_recebida is None:
            return JSONResponse(
                status_code=401,
                content={"detail": (
                    "informe a chave de acesso em Authorization: Bearer <chave>"
                )},
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not acesso_autorizado(ctx, chave_recebida):
            return JSONResponse(
                status_code=401,
                content={"detail": "chave invalida"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await call_next(request)
```

- [ ] **Step 2: Trocar em `main.py`**

```python
from fraus.api.seguranca import (chave_do_cabecalho, exigir_mestra,
                                 fonte_autorizada, registrar_middleware_de_acesso)
```

Substituir o bloco 489-549 por `registrar_middleware_de_acesso(app, ctx)`, mantendo o `app.add_middleware(CORSMiddleware, ...)` **depois** dele, com o comentário das linhas 551-554 intacto. Nas rotas, `_exigir_mestra(authorization)` → `exigir_mestra(ctx, authorization)`, `_chave_do_cabecalho(...)` → `chave_do_cabecalho(...)`, `_fonte_autorizada(banco, chave)` → `fonte_autorizada(ctx.banco, chave)`.

- [ ] **Step 3: Rodar os testes de autenticação primeiro**

Run: `uv run pytest tests/test_autenticacao.py tests/test_acesso.py -q`
Expected: verde. São 17 testes e é o que esta task pode quebrar.

- [ ] **Step 4: Rodar a suíte inteira**

Run: `uv run pytest -q`
Expected: verde, mesmo total.

- [ ] **Step 5: Commit**

```bash
git add fraus/api/seguranca.py fraus/api/main.py
git commit -m "refactor(api): autenticacao e middleware saem para seguranca.py"
```

---

### Task 7: `rotas/saude.py` e `rotas/configuracoes.py` — o padrão dos routers

A primeira task de router estabelece o padrão que as tasks 8-13 repetem. Dois domínios pequenos e sem entrelaçamento.

**Files:**
- Create: `fraus/api/rotas/__init__.py` (vazio)
- Create: `fraus/api/rotas/saude.py`
- Create: `fraus/api/rotas/configuracoes.py`
- Modify: `fraus/api/main.py` (remover as rotas, `include_router`)

**Interfaces:**
- Consumes: `fraus.api.contexto.{Contexto, obter_contexto}` (Task 5)
- Produces: `fraus.api.rotas.saude.router` e `fraus.api.rotas.configuracoes.router`, ambos `APIRouter`

- [ ] **Step 1: Criar `fraus/api/rotas/__init__.py` vazio e `fraus/api/rotas/saude.py`**

```python
"""GET /saude -- a rota que responde antes de qualquer dependencia."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/saude")
def saude() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 2: Criar `fraus/api/rotas/configuracoes.py`**

```python
"""GET e PUT /configuracoes -- as faixas de NPS e os cortes de latencia."""

from fastapi import APIRouter, Depends, HTTPException

from fraus.api.contexto import Contexto, obter_contexto
from fraus.configuracao import PADROES as CONFIGURACAO_DE_FABRICA
from fraus.configuracao import carregar as carregar_configuracao
from fraus.configuracao import salvar as salvar_configuracao

router = APIRouter()


@router.get("/configuracoes")
def configuracoes(ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Configuracao vigente E a de fabrica -- a tela precisa das duas.

    Sem a de fabrica, "voltar ao padrao" seria um botao que a interface
    teria que preencher com numeros digitados de novo, e digitar de novo e
    exatamente como faixa duplicada nasce.
    """
    return {
        "vigente": carregar_configuracao(ctx.banco),
        "fabrica": CONFIGURACAO_DE_FABRICA,
    }


@router.put("/configuracoes")
def configurar(pedido: dict, ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Grava as chaves enviadas. Chave desconhecida ou valor invalido e 400.

    O corpo e um dicionario cru de proposito: chave desconhecida precisa
    chegar a validacao para ser NOMEADA no erro, e nao ser descartada em
    silencio por um modelo de entrada tolerante.
    """
    try:
        vigente = salvar_configuracao(ctx.banco, pedido)
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
    return {"vigente": vigente, "fabrica": CONFIGURACAO_DE_FABRICA}
```

- [ ] **Step 3: Montar em `main.py`**

Remover as quatro rotas de `criar_app` e, depois do registro dos middlewares:

```python
    app.include_router(saude.router)
    app.include_router(configuracoes.router)
```

com `from fraus.api.rotas import configuracoes, saude` no topo.

- [ ] **Step 4: Rodar a suíte**

Run: `uv run pytest -q`
Expected: verde, mesmo total.

- [ ] **Step 5: Commit**

```bash
git add fraus/api/rotas fraus/api/main.py
git commit -m "refactor(api): saude e configuracoes viram routers"
```

---

### Task 8: `rotas/acesso.py`

**Files:**
- Create: `fraus/api/rotas/acesso.py`
- Modify: `fraus/api/main.py:930-965`

**Interfaces:**
- Consumes: `Contexto`/`obter_contexto` (Task 5), `exigir_mestra` (Task 6), `PedidoChaveAcesso` (Task 2)
- Produces: `fraus.api.rotas.acesso.router`

- [ ] **Step 1: Criar `fraus/api/rotas/acesso.py`**

Mover as três rotas (`POST /acesso/chaves`, `GET /acesso/chaves`, `DELETE /acesso/chaves/{chave_id}`) com as docstrings. Cada uma ganha `ctx: Contexto = Depends(obter_contexto)` **depois** dos parâmetros sem padrão e chama `exigir_mestra(ctx, authorization)`. O módulo importa `from fraus import acesso, credencial` — atenção ao nome: o módulo de rotas se chama `acesso` e o de domínio também; importe o de domínio como `from fraus import acesso as acesso_dominio` para não sombrear.

```python
"""/acesso/chaves -- as chaves que a dashboard usa para ler a API.

Gerenciar chave e privilegio da MESTRA, nunca de chave de acesso: uma chave
que pode emitir outra chave nao e um posto menor, e o 403 daqui e o que
separa os dois niveis.
"""
```

- [ ] **Step 2: Montar em `main.py`**

Remover as rotas, acrescentar `app.include_router(acesso.router)` e o import.

- [ ] **Step 3: Rodar os testes de acesso e a suíte**

Run: `uv run pytest tests/test_acesso.py tests/test_autenticacao.py -q && uv run pytest -q`
Expected: verde nas duas, mesmo total.

- [ ] **Step 4: Commit**

```bash
git add fraus/api/rotas/acesso.py fraus/api/main.py
git commit -m "refactor(api): chaves de acesso viram router"
```

---

### Task 9: `rotas/integracoes.py`

Sete rotas: fontes (listar, criar, ajustar, apagar), chave da fonte (gerar, revogar), tipos, arquivos importáveis e histórico de importações.

**Files:**
- Create: `fraus/api/rotas/integracoes.py`
- Modify: `fraus/api/main.py:830-928, 1008-1071`

**Interfaces:**
- Consumes: `Contexto`/`obter_contexto`, `exigir_mestra`, `PedidoFonte`, `PedidoAjusteFonte`, `TIPOS_DE_FONTE`
- Produces: `fraus.api.rotas.integracoes.router`

- [ ] **Step 1: Criar `fraus/api/rotas/integracoes.py`**

Mover as sete rotas e a função `_fonte_publica` (linhas 465-474), que só este domínio usa — por isso ela fica aqui e não no `Contexto`. A rota `arquivos_importaveis` usa `ctx.raiz` no lugar da closure `raiz`.

- [ ] **Step 2: Montar em `main.py` e rodar a suíte**

Run: `uv run pytest -q`
Expected: verde, mesmo total. São 16+ testes de `/integracoes/fontes` e é o maior risco desta task.

- [ ] **Step 3: Commit**

```bash
git add fraus/api/rotas/integracoes.py fraus/api/main.py
git commit -m "refactor(api): integracoes viram router"
```

---

### Task 10: `rotas/ingestao.py`

**Files:**
- Create: `fraus/api/rotas/ingestao.py`
- Modify: `fraus/api/main.py:967-1006`

**Interfaces:**
- Consumes: `Contexto`/`obter_contexto`, `chave_do_cabecalho` e `fonte_autorizada` (Task 6), `PedidoIngestao` (Task 2)
- Produces: `fraus.api.rotas.ingestao.router`

- [ ] **Step 1: Criar `fraus/api/rotas/ingestao.py`**

Mover a rota com a docstring inteira. As chamadas viram `chave = chave_do_cabecalho(authorization)` e `fonte = fonte_autorizada(ctx.banco, chave)`; a pontuação, `score = ctx.motor.pontuar_conversa(conversa)`; a gravação, `ctx.banco.salvar(conversa, score, ctx.categoria_de(score, faixas))`.

Ao mover, **calcule `faixas = ctx.faixas_vigentes()` uma vez** e use nas duas derivações de categoria (hoje as linhas 998 e 1004 chamam `faixas_vigentes()` duas vezes na mesma requisição, e a segunda pode ler uma configuração alterada entre as duas leituras). Isso é correção de uma leitura inconsistente, não mudança de contrato: a resposta continua idêntica.

- [ ] **Step 2: Montar em `main.py` e rodar**

Run: `uv run pytest tests/test_autenticacao.py -q && uv run pytest -q`
Expected: verde. Os dois testes escritos na Task 1 são o que prova esta.

- [ ] **Step 3: Commit**

```bash
git add fraus/api/rotas/ingestao.py fraus/api/main.py
git commit -m "refactor(api): ingestao vira router"
```

---

### Task 11: `rotas/modelo.py`

Cinco rotas: `/modelo`, `/modelo/lexicon`, `/modelo/simular`, `/analisar`, `/analisar/arquivo` — mais os helpers `_extrair_ou_400` e `_montar_analise`, que só elas usam.

**Files:**
- Create: `fraus/api/rotas/modelo.py`
- Modify: `fraus/api/main.py:1073-1321`

**Interfaces:**
- Consumes: `Contexto`/`obter_contexto`, `metricas_de` e as constantes `CAMINHO_METRICAS*` (Task 4), `PedidoSimulacao` e `PedidoAnalise` (Task 2)
- Produces: `fraus.api.rotas.modelo.router`

- [ ] **Step 1: Criar `fraus/api/rotas/modelo.py`**

Mover as cinco rotas, os helpers `extrair_ou_400`/`montar_analise` (sem sublinhado) e as constantes que só este domínio usa: `TETO_TEXTO_SIMULACAO`, `TETO_LEXICON`, `TETO_ARQUIVO_ANALISE`, `TETO_CONVERSAS_ANALISE`, `LIMITE_LEXICON_PADRAO`.

`montar_analise` recebe `ctx` como primeiro parâmetro — ela usa `banco.todas()`, `banco.listar()`, `motor.analisar_conversa` e `faixas_vigentes()`.

- [ ] **Step 2: Montar em `main.py` e rodar**

Run: `uv run pytest -q`
Expected: verde, mesmo total. Os três testes de `/analisar/arquivo` da Task 1 cobrem o caminho que antes não tinha rede.

- [ ] **Step 3: Commit**

```bash
git add fraus/api/rotas/modelo.py fraus/api/main.py
git commit -m "refactor(api): modelo e analise viram router"
```

---

### Task 12: `rotas/indicadores.py`

Três rotas de agregado: `/indicadores`, `/lexico`, `/serie-temporal`.

**Files:**
- Create: `fraus/api/rotas/indicadores.py`
- Modify: `fraus/api/main.py:732-763, 782-801`

**Interfaces:**
- Consumes: `Contexto`/`obter_contexto` (em especial `ctx.registros_do_recorte`), `recorte_ou_400` e `no_recorte` (Task 4)
- Produces: `fraus.api.rotas.indicadores.router`

- [ ] **Step 1: Criar `fraus/api/rotas/indicadores.py`**

Mover as três rotas com as docstrings. As três usam `ctx.registros_do_recorte(de, ate)`; `/serie-temporal` também precisa de `inicio`/`fim` para ecoar no corpo, então ela chama `recorte_ou_400(de, ate)` diretamente e filtra com `no_recorte`, como hoje.

- [ ] **Step 2: Montar em `main.py` e rodar**

Run: `uv run pytest tests/test_api_periodo.py -q && uv run pytest -q`
Expected: verde nas duas, mesmo total.

- [ ] **Step 3: Commit**

```bash
git add fraus/api/rotas/indicadores.py fraus/api/main.py
git commit -m "refactor(api): indicadores, lexico e serie temporal viram router"
```

---

### Task 13: `rotas/conversas.py`

O último e maior: `POST /conversas/importar`, `GET /conversas`, `GET /conversas/{id}`, `GET /conversas/{id}/atribuicao`.

**Files:**
- Create: `fraus/api/rotas/conversas.py`
- Modify: `fraus/api/main.py:587-721`

**Interfaces:**
- Consumes: `Contexto`/`obter_contexto`, `resolver_dentro_da_raiz` (Task 4), `recorte_ou_400`/`no_recorte` (Task 4), `PedidoImportacao` (Task 2)
- Produces: `fraus.api.rotas.conversas.router`

- [ ] **Step 1: Criar `fraus/api/rotas/conversas.py`**

Mover as quatro rotas e a constante `LIMITE_MOTIVOS`, que só a importação usa. A ordem de declaração importa: `GET /conversas/{conversa_id}` precisa continuar depois de `GET /conversas`, e `/conversas/{id}/atribuicao` depois de `/conversas/{id}` — o roteamento do FastAPI é por ordem de registro, e inverter faria `atribuicao` cair como `conversa_id`.

- [ ] **Step 2: Montar em `main.py` e rodar**

Run: `uv run pytest -q`
Expected: verde, mesmo total.

- [ ] **Step 3: Commit**

```bash
git add fraus/api/rotas/conversas.py fraus/api/main.py
git commit -m "refactor(api): conversas viram router"
```

---

### Task 14: `main.py` final e verificação de ponta a ponta

**Files:**
- Modify: `fraus/api/main.py`
- Modify: `README.md` (nota de estrutura)

**Interfaces:**
- Consumes: todos os routers das tasks 7-13
- Produces: `criar_app`, `criar_app_padrao`, `__getattr__` (PEP 562), reexport de `Motor`

- [ ] **Step 1: Deixar `main.py` só com a montagem**

O arquivo final tem: docstring do módulo (atualizada para descrever a montagem, mantendo a explicação do `__getattr__` preguiçoso), imports, `criar_app` (monta `Contexto`, registra middlewares na ordem certa, inclui os 8 routers, devolve o app), `criar_app_padrao`, `__getattr__` e o reexport de `Motor`.

- [ ] **Step 2: Conferir o tamanho de cada arquivo**

Run: `uv run python -c "import pathlib; [print(len(p.read_text(encoding='utf-8').splitlines()), p) for p in sorted(pathlib.Path('fraus/api').rglob('*.py'))]"`
Expected: nenhum arquivo acima de ~250 linhas; `main.py` perto de 120.

- [ ] **Step 3: Conferir que nada do contrato mudou — inventário de rotas**

Run:
```bash
uv run python -c "
from fraus.api.main import criar_app
from fraus.db import Banco
import tempfile, pathlib
d = pathlib.Path(tempfile.mkdtemp()); b = Banco(d/'f.db'); b.migrar()
class M:
    def pontuar_conversa(self, c): return 90.0
app = criar_app(banco=b, motor=M(), raiz_importacao=d)
for r in sorted(app.routes, key=lambda r: getattr(r, 'path', '')):
    if hasattr(r, 'methods'): print(sorted(r.methods), r.path)
"
```
Expected: as 30 rotas, com os mesmos métodos e paths de antes. Compare com a saída do mesmo comando em `git stash`/`git checkout` do commit anterior à Task 2 se houver qualquer dúvida.

- [ ] **Step 4: Rodar a suíte inteira**

Run: `uv run pytest -q`
Expected: verde, **mesmo total anotado na Task 1**, sem um teste existente editado. Confirme com `git diff --stat <commit-antes-da-task-2>..HEAD -- tests/` — só devem aparecer as adições da Task 1.

- [ ] **Step 5: Subir o servidor de demonstração e bater nele**

Run: `uv run python scripts/api_demo.py` (em background) e depois `curl -s localhost:8000/saude && curl -s localhost:8000/indicadores`
Expected: `{"status":"ok"}` e o objeto de indicadores. Derrube o processo depois.

- [ ] **Step 6: Documentar a estrutura no README**

Acrescentar, na seção de desenvolvimento, um parágrafo curto listando `fraus/api/{contexto,esquemas,seguranca,periodo,caminhos}.py` e `fraus/api/rotas/` — quem for mexer na API precisa saber onde cada domínio mora sem abrir oito arquivos para descobrir.

- [ ] **Step 7: Commit**

```bash
git add fraus/api/main.py README.md
git commit -m "refactor(api): main.py fica so com a montagem do app"
```
