# Autenticacao da API — plano de implementacao

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** proteger a API inteira com chaves de acesso revogaveis + chave mestra por env, e fazer a dashboard falar com a API por um proxy no servidor Next para a chave nunca tocar o navegador.

**Architecture:** um modulo `fraus/acesso.py` reusa as primitivas de `fraus/credencial.py` com prefixo `fra_`; uma tabela nova `chaves_acesso` no SQLite; `criar_app` ganha o parametro `chave_mestra` e, quando ele existe, um middleware HTTP exige `Authorization: Bearer` em tudo menos `POST /ingestao` (que segue regida pela chave de fonte). No front, `lib/api.ts` passa a chamar `/api/fraus/...` e um route handler catch-all repassa para `FRAUS_API_URL` anexando `FRAUS_CHAVE_ACESSO`.

**Tech Stack:** FastAPI + SQLite (sem ORM) no back; Next.js 16 route handlers no front.

**Spec:** `docs/superpowers/specs/2026-08-14-autenticacao-design.md`.

## Global Constraints

- Python: identificadores e docstrings em pt-BR **sem acento**; texto de interface **com** acento.
- Commits: conventional commits, assunto sem acento, corpo em pt-BR explicando por que. **Sem co-autor Claude.**
- TDD: teste que falha primeiro. Suite: `uv run pytest -q` (hoje 282 verdes).
- Hash nunca circula em resposta (padrao `_fonte` do `db.py`): remover na origem.
- Mensagem de recusa **uniforme** `"chave invalida"` para malformada, inexistente e revogada; 401 sempre com `WWW-Authenticate: Bearer`.
- `FRAUS_CHAVE_MESTRA` vazia = ausente (nunca "Bearer vazio autoriza").
- Front: antes de escrever o route handler, **ler** `dashboard/node_modules/next/dist/docs/` (route handlers) — o AGENTS.md avisa que esta versao do Next difere do conhecimento de treino.

---

### Task 1: `fraus/acesso.py` — chave de acesso `fra_`

**Files:**
- Create: `fraus/acesso.py`
- Test: `tests/test_acesso.py`

**Interfaces:**
- Consumes: `fraus.credencial.hash_da_chave`, `credencial.dica`, `credencial.confere`, `credencial.BYTES_DO_SEGREDO` (existentes).
- Produces: `acesso.gerar(chave_id: int) -> tuple[str, str]` (chave em claro, hash); `acesso.id_da_chave(chave: str) -> int | None`; `acesso.PREFIXO = "fra"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_acesso.py
"""Chave de ACESSO (le a API inteira) -- irma da chave de fonte de credencial.py."""

from fraus import acesso, credencial


def test_gerar_produz_chave_no_formato_fra_id_segredo():
    chave, chave_hash = acesso.gerar(7)
    partes = chave.split("_")
    assert partes[0] == "fra"
    assert partes[1] == "7"
    assert len(partes[2]) == credencial.BYTES_DO_SEGREDO * 2  # hex
    assert chave_hash == credencial.hash_da_chave(chave)


def test_id_da_chave_le_o_id_sem_confiar_nele():
    chave, _ = acesso.gerar(42)
    assert acesso.id_da_chave(chave) == 42


def test_id_da_chave_recusa_formatos_estranhos():
    assert acesso.id_da_chave("qualquer coisa") is None
    assert acesso.id_da_chave("fra_abc_123") is None
    # chave de FONTE nao e chave de acesso: prefixo distingue os papeis
    chave_de_fonte, _ = credencial.gerar(1)
    assert acesso.id_da_chave(chave_de_fonte) is None


def test_chaves_geradas_sao_diferentes():
    assert acesso.gerar(1)[0] != acesso.gerar(1)[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_acesso.py -q`
Expected: FAIL — `ModuleNotFoundError: fraus.acesso` (ou ImportError).

- [ ] **Step 3: Write minimal implementation**

```python
# fraus/acesso.py
"""Chave de ACESSO: autoriza a leitura da API inteira, nao uma fonte.

Mesmo desenho de fraus/credencial.py (segredo sorteado, hash no banco,
mostrada uma vez) com prefixo proprio -- `fra_` contra `frs_` -- porque os
papeis nao se misturam: chave de fonte so empurra atendimento para dentro
(`POST /ingestao`), chave de acesso le todo o resto. Uma chave de um papel
apresentada no lugar do outro falha na leitura do prefixo, antes de qualquer
consulta ao banco.
"""

import secrets

from fraus import credencial

PREFIXO = "fra"


def gerar(chave_id: int) -> tuple[str, str]:
    """Cria uma chave nova. Devolve `(chave_em_claro, hash)`.

    O id vem do banco (a linha nasce antes da chave) e vai embutido em texto
    claro para a conferencia achar o hash sem varrer a tabela -- quem autoriza
    e o hash, nunca o id. Ver credencial.py, decisao 3.
    """
    segredo = secrets.token_hex(credencial.BYTES_DO_SEGREDO)
    chave = f"{PREFIXO}_{chave_id}_{segredo}"
    return chave, credencial.hash_da_chave(chave)


def id_da_chave(chave: str) -> int | None:
    """Le o id embutido, sem confiar nele. `None` para tudo fora do formato."""
    partes = chave.split("_")
    if len(partes) != 3 or partes[0] != PREFIXO:
        return None
    try:
        return int(partes[1])
    except ValueError:
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_acesso.py -q` → PASS. Depois `uv run pytest -q` inteiro → 282 + 4.

- [ ] **Step 5: Commit**

```bash
git add fraus/acesso.py tests/test_acesso.py
git commit -m "feat(acesso): chave de acesso fra_, irma da chave de fonte"
```

---

### Task 2: tabela `chaves_acesso` e metodos do `Banco`

**Files:**
- Modify: `fraus/db.py` (ESQUEMA + metodos novos ao fim da classe)
- Test: `tests/test_db_chaves_acesso.py`

**Interfaces:**
- Consumes: `Banco.migrar()`, `Banco._conectar()` (existentes).
- Produces: `Banco.criar_chave_acesso(nome: str, criada_em: str) -> dict` (id, nome, dica=None, criada_em — sem hash); `Banco.gravar_chave_acesso(identificador: int, chave_hash: str, dica: str) -> None`; `Banco.listar_chaves_acesso() -> list[dict]`; `Banco.hash_da_chave_acesso(identificador: int) -> str | None`; `Banco.apagar_chave_acesso(identificador: int) -> bool`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_db_chaves_acesso.py
"""Persistencia das chaves de acesso. O hash nunca sai nas listagens."""

from fraus.db import Banco


def _banco(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    return banco


def test_criar_e_listar_sem_expor_hash(tmp_path):
    banco = _banco(tmp_path)
    registro = banco.criar_chave_acesso("dashboard", "2026-08-14T00:00:00+00:00")
    banco.gravar_chave_acesso(registro["id"], chave_hash="abc123", dica="3f9a")
    listadas = banco.listar_chaves_acesso()
    assert len(listadas) == 1
    assert listadas[0]["nome"] == "dashboard"
    assert listadas[0]["dica"] == "3f9a"
    assert "chave_hash" not in listadas[0]
    assert "chave_hash" not in registro


def test_hash_so_sai_pelo_caminho_explicito(tmp_path):
    banco = _banco(tmp_path)
    registro = banco.criar_chave_acesso("ci", "2026-08-14T00:00:00+00:00")
    banco.gravar_chave_acesso(registro["id"], chave_hash="abc123", dica="9z9z")
    assert banco.hash_da_chave_acesso(registro["id"]) == "abc123"
    assert banco.hash_da_chave_acesso(999) is None


def test_apagar_revoga(tmp_path):
    banco = _banco(tmp_path)
    registro = banco.criar_chave_acesso("temporaria", "2026-08-14T00:00:00+00:00")
    assert banco.apagar_chave_acesso(registro["id"]) is True
    assert banco.apagar_chave_acesso(registro["id"]) is False
    assert banco.listar_chaves_acesso() == []
    assert banco.hash_da_chave_acesso(registro["id"]) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_db_chaves_acesso.py -q`
Expected: FAIL — `AttributeError: 'Banco' object has no attribute 'criar_chave_acesso'`.

- [ ] **Step 3: Write minimal implementation**

No `ESQUEMA` (depois do bloco de `importacoes`):

```sql
-- Chave de ACESSO: autoriza a leitura da API inteira quando FRAUS_CHAVE_MESTRA
-- esta definida. `chave_hash`/`dica` seguem o desenho de fontes_integracao:
-- hash no banco, nunca a chave; dica de 4 chars para o operador reconhecer.
-- Revogar e DELETE: chave sem linha e chave que nao autoriza.
CREATE TABLE IF NOT EXISTS chaves_acesso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    chave_hash TEXT,
    dica TEXT,
    criada_em TEXT NOT NULL
);
```

Metodos ao fim da classe `Banco` (antes de `_fonte` ou depois de `todas`, seguindo o estilo):

```python
def criar_chave_acesso(self, nome: str, criada_em: str) -> dict:
    """Cria a LINHA da chave. O hash chega depois, por gravar_chave_acesso:
    a chave embute o id, entao o id precisa existir antes do segredo."""
    with self._conectar() as conexao:
        cursor = conexao.execute(
            "INSERT INTO chaves_acesso (nome, criada_em) VALUES (?, ?)",
            (nome, criada_em),
        )
        identificador = cursor.lastrowid
    return {"id": identificador, "nome": nome, "dica": None, "criada_em": criada_em}

def gravar_chave_acesso(self, identificador: int, chave_hash: str, dica: str) -> None:
    with self._conectar() as conexao:
        conexao.execute(
            "UPDATE chaves_acesso SET chave_hash = ?, dica = ? WHERE id = ?",
            (chave_hash, dica, identificador),
        )

def listar_chaves_acesso(self) -> list[dict]:
    """O HASH NAO SAI POR AQUI -- mesma regra de _fonte: removido na origem."""
    with self._conectar() as conexao:
        linhas = conexao.execute(
            "SELECT id, nome, dica, criada_em FROM chaves_acesso ORDER BY criada_em, id"
        ).fetchall()
    return [dict(linha) for linha in linhas]

def hash_da_chave_acesso(self, identificador: int) -> str | None:
    """O unico caminho para ler o hash -- explicito no nome, uso unico."""
    with self._conectar() as conexao:
        linha = conexao.execute(
            "SELECT chave_hash FROM chaves_acesso WHERE id = ?", (identificador,)
        ).fetchone()
    return linha["chave_hash"] if linha is not None else None

def apagar_chave_acesso(self, identificador: int) -> bool:
    with self._conectar() as conexao:
        cursor = conexao.execute(
            "DELETE FROM chaves_acesso WHERE id = ?", (identificador,)
        )
        return cursor.rowcount > 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_db_chaves_acesso.py -q` → PASS; `uv run pytest -q` inteiro verde.

- [ ] **Step 5: Commit**

```bash
git add fraus/db.py tests/test_db_chaves_acesso.py
git commit -m "feat(db): tabela chaves_acesso, hash fora das listagens"
```

---

### Task 3: `criar_app(chave_mestra=...)` + middleware global

**Files:**
- Modify: `fraus/api/main.py` (assinatura de `criar_app` na linha ~452; middleware logo apos a criacao do `app`; `criar_app_padrao` ~1140)
- Test: `tests/test_autenticacao.py`

**Interfaces:**
- Consumes: `acesso.id_da_chave` (Task 1), `Banco.hash_da_chave_acesso` (Task 2), `credencial.confere`.
- Produces: `criar_app(banco, motor, raiz_importacao=None, chave_mestra: str | None = None)`. String vazia normalizada para `None`. Helper interno `_acesso_autorizado(chave: str) -> bool` (closure) usado pela Task 4. `criar_app_padrao` le `FRAUS_CHAVE_MESTRA` do ambiente e imprime aviso quando ausente.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_autenticacao.py
"""Autenticacao da API: liga quando ha chave mestra, e nada muda sem ela.

O motor falso respeita o contrato minimo que as rotas usadas aqui exigem.
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco

MESTRA = "segredo-de-teste-com-entropia-suficiente"


class MotorFalso:
    def pontuar_conversa(self, conversa):
        return 50.0

    def importancias(self):
        return None


def _cliente(tmp_path, chave_mestra=None):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    app = criar_app(
        banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path,
        chave_mestra=chave_mestra,
    )
    return TestClient(app)


def test_sem_chave_mestra_a_api_continua_aberta(tmp_path):
    cliente = _cliente(tmp_path)
    assert cliente.get("/conversas").status_code == 200


def test_com_chave_mestra_leitura_sem_header_e_401(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    resposta = cliente.get("/conversas")
    assert resposta.status_code == 401
    assert resposta.headers["WWW-Authenticate"] == "Bearer"


def test_chave_mestra_autentica_qualquer_rota(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    resposta = cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {MESTRA}"}
    )
    assert resposta.status_code == 200


def test_chave_errada_e_401_com_mensagem_uniforme(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    resposta = cliente.get(
        "/conversas", headers={"Authorization": "Bearer fra_1_deadbeef"}
    )
    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "chave invalida"


def test_chave_mestra_vazia_e_o_mesmo_que_ausente(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra="")
    assert cliente.get("/conversas").status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_autenticacao.py -q`
Expected: FAIL — `TypeError: criar_app() got an unexpected keyword argument 'chave_mestra'`.

- [ ] **Step 3: Write minimal implementation**

Em `fraus/api/main.py`:

1. Acrescentar aos imports: `import hmac` (topo) e `from fastapi.responses import JSONResponse`.
2. Assinatura:

```python
def criar_app(
    banco: Banco,
    motor,
    raiz_importacao: Path | None = None,
    chave_mestra: str | None = None,
) -> FastAPI:
```

3. Logo no comeco do corpo, normalizar e definir os helpers (closure sobre `banco` e `chave_mestra`):

```python
    # Vazia e ausente sao a mesma coisa: "Bearer " autorizando seria a pior
    # combinacao possivel de configuracao errada com acesso liberado.
    chave_mestra = chave_mestra or None

    def _e_mestra(chave: str) -> bool:
        if chave_mestra is None:
            return False
        return hmac.compare_digest(chave.encode("utf-8"), chave_mestra.encode("utf-8"))

    def _acesso_autorizado(chave: str) -> bool:
        """Mestra ou chave de acesso valida. Mensagem de recusa e uniforme
        la fora: daqui so sai sim ou nao."""
        if _e_mestra(chave):
            return True
        chave_id = acesso.id_da_chave(chave)
        guardado = banco.hash_da_chave_acesso(chave_id) if chave_id is not None else None
        return credencial.confere(chave, guardado)
```

(e `from fraus import acesso` junto do `from fraus import credencial` no topo.)

4. Depois da criacao do `app` (e ANTES do `add_middleware(CORSMiddleware...)` existente, para o CORS ficar por fora e o preflight nunca cair no 401 — em Starlette, o middleware adicionado por ULTIMO e o mais externo):

```python
    if chave_mestra is not None:
        @app.middleware("http")
        async def exigir_chave_de_acesso(request, call_next):
            # /ingestao tem credencial propria (chave de FONTE): uma credencial
            # por rota. OPTIONS e o preflight do navegador -- nao carrega
            # header de autorizacao por definicao.
            if request.url.path == "/ingestao" or request.method == "OPTIONS":
                return await call_next(request)
            cabecalho = request.headers.get("authorization")
            if not cabecalho or not cabecalho.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"detail": (
                        "informe a chave de acesso em Authorization: Bearer <chave>"
                    )},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if not _acesso_autorizado(cabecalho[len("Bearer "):]):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "chave invalida"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return await call_next(request)
```

**Atencao a ordem:** se o `add_middleware(CORSMiddleware, ...)` atual estiver antes do ponto onde o middleware de chave e registrado, mover o bloco do CORS para DEPOIS, com comentario dizendo por que a ordem importa.

5. Em `criar_app_padrao`:

```python
    chave_mestra = os.environ.get("FRAUS_CHAVE_MESTRA") or None
    if chave_mestra is None:
        print(
            "AVISO: API sem autenticacao (uso local). "
            "Defina FRAUS_CHAVE_MESTRA para exigir chave em todas as rotas."
        )
    return criar_app(banco=banco, motor=motor, chave_mestra=chave_mestra)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_autenticacao.py -q` → PASS. Suite inteira: `uv run pytest -q` — **todos os testes existentes devem continuar verdes** (eles chamam `criar_app` sem `chave_mestra`, modo aberto = regressao zero).

- [ ] **Step 5: Commit**

```bash
git add fraus/api/main.py tests/test_autenticacao.py
git commit -m "feat(api): exigencia de chave de acesso quando ha chave mestra"
```

---

### Task 4: rotas de gerenciamento `/acesso/chaves`

**Files:**
- Modify: `fraus/api/main.py` (rotas novas perto das rotas de `/integracoes`; modelo `PedidoChaveAcesso` junto dos outros `BaseModel`)
- Test: `tests/test_autenticacao.py` (acrescentar)

**Interfaces:**
- Consumes: `_acesso_autorizado`/`_e_mestra` (Task 3), `acesso.gerar` (Task 1), metodos do `Banco` (Task 2), `credencial.dica`, `credencial.hash_da_chave`, `_chave_do_cabecalho` (existente, linha ~392).
- Produces: `POST /acesso/chaves {nome}` → 201 `{id, nome, dica, criada_em, chave, aviso}`; `GET /acesso/chaves` → 200 lista sem hash; `DELETE /acesso/chaves/{id}` → 204 (404 se nao existe). Todas exigem a **mestra** (403 para chave de acesso valida).

- [ ] **Step 1: Write the failing test** (acrescentar a `tests/test_autenticacao.py`)

```python
def _criar_chave_de_acesso(cliente, nome="dashboard"):
    resposta = cliente.post(
        "/acesso/chaves",
        json={"nome": nome},
        headers={"Authorization": f"Bearer {MESTRA}"},
    )
    assert resposta.status_code == 201
    return resposta.json()


def test_chave_de_acesso_criada_pela_mestra_autentica_leitura(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    corpo = _criar_chave_de_acesso(cliente)
    assert corpo["chave"].startswith("fra_")
    resposta = cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {corpo['chave']}"}
    )
    assert resposta.status_code == 200


def test_chave_de_acesso_nao_gerencia_chaves(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    corpo = _criar_chave_de_acesso(cliente)
    autorizacao = {"Authorization": f"Bearer {corpo['chave']}"}
    assert cliente.post("/acesso/chaves", json={"nome": "x"}, headers=autorizacao).status_code == 403
    assert cliente.get("/acesso/chaves", headers=autorizacao).status_code == 403
    assert cliente.delete(f"/acesso/chaves/{corpo['id']}", headers=autorizacao).status_code == 403


def test_revogacao_vale_na_chamada_seguinte(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    corpo = _criar_chave_de_acesso(cliente)
    mestra = {"Authorization": f"Bearer {MESTRA}"}
    assert cliente.delete(f"/acesso/chaves/{corpo['id']}", headers=mestra).status_code == 204
    resposta = cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {corpo['chave']}"}
    )
    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "chave invalida"


def test_listagem_nunca_expoe_hash(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    _criar_chave_de_acesso(cliente)
    resposta = cliente.get(
        "/acesso/chaves", headers={"Authorization": f"Bearer {MESTRA}"}
    )
    assert resposta.status_code == 200
    for item in resposta.json():
        assert "chave_hash" not in item
        assert "chave" not in item
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_autenticacao.py -q`
Expected: FAIL — 404 em `/acesso/chaves` (rota inexistente).

- [ ] **Step 3: Write minimal implementation**

Modelo (junto dos outros `BaseModel` no topo do arquivo):

```python
class PedidoChaveAcesso(BaseModel):
    nome: str = Field(min_length=1)
```

Helper dentro de `criar_app` (depois de `_acesso_autorizado`):

```python
    def _exigir_mestra(authorization: str | None) -> None:
        """Gerenciar chaves e privilegio da mestra, nunca de chave de acesso.

        No modo aberto (sem mestra) nao ha o que exigir -- as rotas de
        gerenciamento seguem abertas como o resto, coerente com a decisao de
        ativacao condicionada.

        403, nao 401: quem chega aqui com chave de acesso valida ja passou
        pelo middleware -- a credencial esta certa, o privilegio e que falta.
        """
        if chave_mestra is None:
            return
        chave = _chave_do_cabecalho(authorization)
        if not _e_mestra(chave):
            raise HTTPException(
                status_code=403, detail="esta rota exige a chave mestra"
            )
```

Rotas (perto das rotas de `/integracoes/fontes/{id}/chave`, ~linha 742):

```python
    @app.post("/acesso/chaves", status_code=201)
    def criar_chave_acesso(
        pedido: PedidoChaveAcesso, authorization: str | None = Header(default=None)
    ) -> dict:
        """Gera uma chave de acesso e a devolve EM CLARO uma unica vez."""
        _exigir_mestra(authorization)
        registro = banco.criar_chave_acesso(
            nome=pedido.nome,
            criada_em=datetime.now(timezone.utc).isoformat(),
        )
        chave, chave_hash = acesso.gerar(registro["id"])
        banco.gravar_chave_acesso(
            registro["id"], chave_hash=chave_hash, dica=credencial.dica(chave)
        )
        return {
            **registro,
            "dica": credencial.dica(chave),
            "chave": chave,
            "aviso": (
                "Guarde agora: esta chave não pode ser lida de novo. "
                "Revogue e gere outra se perdê-la."
            ),
        }

    @app.get("/acesso/chaves")
    def listar_chaves_acesso(authorization: str | None = Header(default=None)) -> list[dict]:
        _exigir_mestra(authorization)
        return banco.listar_chaves_acesso()

    @app.delete("/acesso/chaves/{chave_id}", status_code=204)
    def revogar_chave_acesso(
        chave_id: int, authorization: str | None = Header(default=None)
    ) -> None:
        _exigir_mestra(authorization)
        if not banco.apagar_chave_acesso(chave_id):
            raise HTTPException(status_code=404, detail="chave nao encontrada")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_autenticacao.py -q` → PASS; suite inteira verde.

- [ ] **Step 5: Commit**

```bash
git add fraus/api/main.py tests/test_autenticacao.py
git commit -m "feat(api): rotas de chave de acesso, gerenciadas so pela mestra"
```

---

### Task 5: mestra nas rotas de chave de fonte; `/ingestao` intocada

**Files:**
- Modify: `fraus/api/main.py` (rotas `POST`/`DELETE /integracoes/fontes/{fonte_id}/chave`, ~linhas 742-779)
- Test: `tests/test_autenticacao.py` (acrescentar)

**Interfaces:**
- Consumes: `_exigir_mestra` (Task 4), rotas existentes `gerar_chave`/`revogar_chave`, fluxo de ingestao de `tests/test_credencial.py` como referencia de payload.
- Produces: as duas rotas de chave de fonte passam a receber `authorization` e chamar `_exigir_mestra`. `/ingestao` permanece regida exclusivamente pela chave de fonte.

- [ ] **Step 1: Write the failing test** (acrescentar a `tests/test_autenticacao.py`)

```python
def _criar_fonte(cliente, cabecalhos):
    resposta = cliente.post(
        "/integracoes/fontes",
        json={"nome": "totalk", "canal": "whatsapp", "tipo": "webhook"},
        headers=cabecalhos,
    )
    assert resposta.status_code == 201
    return resposta.json()


def test_gerar_chave_de_fonte_exige_a_mestra(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    mestra = {"Authorization": f"Bearer {MESTRA}"}
    fonte = _criar_fonte(cliente, mestra)
    corpo_acesso = _criar_chave_de_acesso(cliente)
    leitura = {"Authorization": f"Bearer {corpo_acesso['chave']}"}
    assert cliente.post(f"/integracoes/fontes/{fonte['id']}/chave", headers=leitura).status_code == 403
    assert cliente.post(f"/integracoes/fontes/{fonte['id']}/chave", headers=mestra).status_code == 201
    assert cliente.delete(f"/integracoes/fontes/{fonte['id']}/chave", headers=leitura).status_code == 403


def test_ingestao_segue_regida_pela_chave_de_fonte(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    mestra = {"Authorization": f"Bearer {MESTRA}"}
    fonte = _criar_fonte(cliente, mestra)
    chave_da_fonte = cliente.post(
        f"/integracoes/fontes/{fonte['id']}/chave", headers=mestra
    ).json()["chave"]

    pedido = {
        "conversa_externa_id": "abc-1",
        "mensagens": [
            {
                "autor": "cliente",
                "texto": "obrigado",
                "enviada_em": "2026-08-14T12:00:00+00:00",
            }
        ],
    }
    # A MESTRA nao autoriza a ingestao: uma credencial por rota.
    recusada = cliente.post(
        "/ingestao", json=pedido, headers=mestra
    )
    assert recusada.status_code == 401
    aceita = cliente.post(
        "/ingestao", json=pedido,
        headers={"Authorization": f"Bearer {chave_da_fonte}"},
    )
    assert aceita.status_code == 201
```

**Nota:** conferir em `tests/test_credencial.py` o payload EXATO que `POST /ingestao` aceita (nomes de campos do `PedidoIngestao`) e ajustar `pedido` acima para casar — o formato aqui e ilustrativo; o contrato ja existente e a fonte da verdade.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_autenticacao.py -q`
Expected: FAIL — `gerar_chave` com chave de leitura devolve 201 (nao ha exigencia de mestra ainda).

- [ ] **Step 3: Write minimal implementation**

Nas duas rotas existentes, acrescentar o parametro e a primeira linha:

```python
    @app.post("/integracoes/fontes/{fonte_id}/chave", status_code=201)
    def gerar_chave(
        fonte_id: int, authorization: str | None = Header(default=None)
    ) -> dict:
        _exigir_mestra(authorization)
        ...  # corpo existente intocado

    @app.delete("/integracoes/fontes/{fonte_id}/chave", status_code=204)
    def revogar_chave(
        fonte_id: int, authorization: str | None = Header(default=None)
    ) -> None:
        _exigir_mestra(authorization)
        ...  # corpo existente intocado
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -q` — a suite INTEIRA. `tests/test_credencial.py` roda em modo aberto (sem mestra) e deve continuar verde sem mudanca.

- [ ] **Step 5: Commit**

```bash
git add fraus/api/main.py tests/test_autenticacao.py
git commit -m "feat(api): gerar e revogar chave de fonte exigem a mestra

Era o buraco central: quem alcancava a URL gerava credencial de ingestao
para si. /ingestao continua regida so pela chave de fonte -- uma
credencial por rota."
```

---

### Task 6: proxy no servidor Next + `lib/api.ts` aponta para ele

**Files:**
- Create: `dashboard/app/api/fraus/[...caminho]/route.ts`
- Modify: `dashboard/lib/api.ts` (constante `BASE`, ~linha 13)

**Interfaces:**
- Consumes: env server-side `FRAUS_API_URL` (padrao `http://localhost:8000`) e `FRAUS_CHAVE_ACESSO` (opcional).
- Produces: qualquer chamada `/api/fraus/<resto>` repassada com metodo, corpo, query e status preservados. `lib/api.ts` exporta `BASE = "/api/fraus"`; `BASE_DA_API` continua existindo SO para o exemplo de curl da tela de integracoes (le `NEXT_PUBLIC_API_URL ?? "http://localhost:8000"`), com comentario dizendo que ela e texto de exibicao, nunca destino de fetch.

- [ ] **Step 0: Ler a doc do Next da versao instalada**

Ler `dashboard/node_modules/next/dist/docs/` sobre route handlers e params assincronos ANTES de escrever — o AGENTS.md do dashboard avisa que esta versao difere do conhecimento de treino. Ajustar o codigo abaixo ao que a doc disser (ex.: `params` como Promise).

- [ ] **Step 1: Escrever o handler**

```ts
// dashboard/app/api/fraus/[...caminho]/route.ts
/**
 * Proxy da API do Fraus. Existe para a chave de acesso viver SO no servidor
 * Next (env sem NEXT_PUBLIC_) e nunca tocar o navegador -- variavel publica
 * vai para o bundle JS, e segredo no bundle e segredo publicado.
 *
 * Repassa metodo, corpo (inclusive multipart de /analisar), query e status.
 * O Authorization vindo do navegador e DESCARTADO: a credencial do deploy e a
 * do servidor, nao a que o cliente mandar.
 */

const API = process.env.FRAUS_API_URL ?? "http://localhost:8000";
const CHAVE = process.env.FRAUS_CHAVE_ACESSO;

async function repassar(
  requisicao: Request,
  contexto: { params: Promise<{ caminho: string[] }> },
): Promise<Response> {
  const { caminho } = await contexto.params;
  const busca = new URL(requisicao.url).search;
  const destino = `${API}/${caminho.join("/")}${busca}`;

  const cabecalhos = new Headers(requisicao.headers);
  cabecalhos.delete("host");
  cabecalhos.delete("authorization");
  if (CHAVE) cabecalhos.set("authorization", `Bearer ${CHAVE}`);

  const resposta = await fetch(destino, {
    method: requisicao.method,
    headers: cabecalhos,
    body: requisicao.body,
    // meio-duplex e exigido pelo fetch do Node ao repassar um corpo em stream
    // @ts-expect-error duplex ainda nao esta no tipo RequestInit
    duplex: "half",
    cache: "no-store",
  });

  return new Response(resposta.body, {
    status: resposta.status,
    headers: resposta.headers,
  });
}

export {
  repassar as GET,
  repassar as POST,
  repassar as PUT,
  repassar as DELETE,
};
```

- [ ] **Step 2: Apontar `lib/api.ts` para o proxy**

Trocar a linha 13:

```ts
/**
 * Toda chamada sai por /api/fraus: o proxy no servidor Next anexa a chave de
 * acesso (FRAUS_CHAVE_ACESSO, env server-side) e repassa para FRAUS_API_URL.
 * A chave nunca chega ao navegador.
 */
const BASE = "/api/fraus";
```

E revisar `BASE_DA_API`: manter lendo `process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"` com o comentario dizendo que e SO o endereco exibido no exemplo de curl da ingestao (o integrador externo fala com a API direto, nao com o proxy).

- [ ] **Step 3: Verificar tipos e build**

Run: `cd dashboard && npx tsc --noEmit && npm run build`
Expected: sem erro. (Nao rodar com o `next dev` do Joao no ar — armadilha 3 do handoff.)

- [ ] **Step 4: Fumaca manual**

Com a API demo no ar (`uv run python scripts/api_demo.py`) e `npx next start -p 3000`:
- `curl http://localhost:3000/api/fraus/saude` → 200 igual ao da API;
- abrir a dashboard: visao geral carrega, upload em `/analisar` funciona (multipart atravessa o proxy).

Depois, o cenario com chave (prova de fogo):
- subir a API real ou demo com `FRAUS_CHAVE_MESTRA=teste`;
- gerar uma chave de acesso via curl com a mestra;
- reiniciar o Next com `FRAUS_API_URL=http://localhost:8000 FRAUS_CHAVE_ACESSO=<chave>`;
- dashboard funciona; `curl http://localhost:8000/conversas` sem header → 401.

- [ ] **Step 5: Commit**

```bash
git add dashboard/app/api/fraus dashboard/lib/api.ts
git commit -m "feat(dashboard): toda chamada sai por um proxy no servidor Next

A chave de acesso vive em FRAUS_CHAVE_ACESSO, env sem NEXT_PUBLIC_, e o
proxy a anexa no servidor -- variavel publica iria para o bundle JS, e
segredo no bundle e segredo publicado."
```

---

### Task 7: documentacao

**Files:**
- Modify: `README.md` (secao "Limitações conhecidas" — o item de autenticacao; secao "Pendências" — item 4 sai; tabela de variaveis ganha `FRAUS_CHAVE_MESTRA`; secao da dashboard troca `NEXT_PUBLIC_API_URL` por `FRAUS_API_URL`/`FRAUS_CHAVE_ACESSO`)
- Modify: `docs/hospedagem.md` (secao "Antes de expor" vira o passo a passo com as chaves; o laco de CORS ganha a nota de que o caminho normal virou servidor→servidor)
- Modify: `docs/handoff.md` (estado + pendencias)
- Modify: `Dockerfile` (comentario/exemplo com `FRAUS_CHAVE_MESTRA`)

- [ ] **Step 1:** README — a limitacao "API sem autenticacao" vira a descricao do modelo: sem `FRAUS_CHAVE_MESTRA` a API roda aberta (uso local); com ela, toda rota exige `Authorization: Bearer` (mestra ou chave de acesso); `/ingestao` segue com chave de fonte; gerenciamento de chaves e privilegio da mestra. Pendencia 4 removida da lista.
- [ ] **Step 2:** hospedagem.md — ordem de publicacao atualizada: definir `FRAUS_CHAVE_MESTRA` no host da API; gerar chave de acesso via curl; configurar `FRAUS_API_URL` + `FRAUS_CHAVE_ACESSO` na Vercel. Aviso do tunel cloudflared atualizado (com mestra definida o tunel deixa de ser porta aberta).
- [ ] **Step 3:** handoff.md — estado e a pendencia P0 de autenticacao marcada como feita.
- [ ] **Step 4:** Dockerfile — exemplo de `docker run` com `-e FRAUS_CHAVE_MESTRA=...`.
- [ ] **Step 5: Commit**

```bash
git add README.md docs/hospedagem.md docs/handoff.md Dockerfile
git commit -m "docs: autenticacao documentada, pendencia P0 encerrada"
```

---

## Self-review (feito na escrita)

- **Cobertura da spec:** A) Tasks 1-2-4; B) Task 3; C) Task 6; D) casos de borda nos testes das Tasks 3-5 e no handler; E) Tasks 1-5 (testes) + Task 6 Step 4 (fumaca); F) Task 7. Escopo declarado fora (login, escopos por chave, rate limit) nao tem task — correto.
- **Placeholders:** nenhum "TBD"; o unico ajuste em execucao e o payload de `/ingestao` na Task 5, apontado explicitamente para `tests/test_credencial.py` como fonte da verdade, e o Step 0 da Task 6 (doc do Next da versao instalada), ambos verificacoes deliberadas, nao lacunas.
- **Consistencia de tipos:** `acesso.gerar(chave_id)` (Task 1) casa com o uso na Task 4; `Banco.criar_chave_acesso(nome, criada_em)` e `gravar_chave_acesso(id, chave_hash, dica)` (Task 2) casam com a Task 4; `criar_app(..., chave_mestra=None)` (Task 3) casa com `_cliente` dos testes.
