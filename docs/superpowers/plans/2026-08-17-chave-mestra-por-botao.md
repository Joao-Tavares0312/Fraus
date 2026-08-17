# Chave mestra por botão — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ligar a autenticação da API por um botão na tela de Configurações, sem terminal e sem reiniciar processo, mantendo a dashboard navegando depois do clique.

**Architecture:** A mestra passa a ter duas procedências — `FRAUS_CHAVE_MESTRA` (que vence) e um hash na tabela `chave_mestra` de uma linha. O middleware de acesso passa a ser sempre registrado e a decidir por requisição, consultando o estado vigente. `POST /acesso/mestra` gera a mestra e, no primeiro uso, emite junto a chave de acesso da dashboard; uma rota do Next guarda essa chave num cookie `httpOnly` que o proxy usa quando não há variável de ambiente.

**Tech Stack:** Python 3.11 · FastAPI · SQLite · pytest · Next.js (App Router) · TypeScript

## Global Constraints

- **A mestra em claro nunca é persistida.** O banco guarda `sha256` + dica de 4 caracteres.
- **`FRAUS_CHAVE_MESTRA` vence o banco.** Quem já usa a variável não muda nada.
- **Nenhuma rota desliga a autenticação.** Desligar é trabalho de ambiente.
- **Nenhuma rota inicia processo.**
- **Cookie de chave de acesso é `httpOnly`**, `SameSite=Lax`, `Secure` quando `NODE_ENV === "production"`.
- Comando de teste da API: `uv run pytest -q` (linha de base atual: **317 passed, 1 deselected**).
- Comando de build do front: `cd dashboard && npm run build`.
- Cada task termina com a suíte verde e um commit.

---

### Task 1: A mestra no banco

**Files:**
- Modify: `fraus/db.py` (schema + três métodos)
- Test: `tests/test_db_chave_mestra.py`

**Interfaces:**
- Produces:
  - `Banco.gravar_chave_mestra(chave_hash: str, dica: str, criada_em: str) -> None` — insere ou substitui a linha única
  - `Banco.hash_da_chave_mestra() -> str | None`
  - `Banco.chave_mestra_registrada() -> dict | None` — `{"dica": str, "criada_em": str}`, nunca o hash

- [ ] **Step 1: Escrever o teste**

```python
"""A mestra no banco: uma linha, hash nunca exposto, substituicao no lugar."""

import pytest

from fraus.db import Banco


@pytest.fixture
def banco(tmp_path):
    b = Banco(tmp_path / "t.db")
    b.migrar()
    return b


def test_banco_novo_nao_tem_mestra(banco):
    assert banco.hash_da_chave_mestra() is None
    assert banco.chave_mestra_registrada() is None


def test_gravar_e_ler_o_hash(banco):
    banco.gravar_chave_mestra("hash-1", "9a3f", "2026-08-17T10:00:00+00:00")
    assert banco.hash_da_chave_mestra() == "hash-1"


def test_registro_publico_nao_carrega_o_hash(banco):
    banco.gravar_chave_mestra("hash-1", "9a3f", "2026-08-17T10:00:00+00:00")
    registro = banco.chave_mestra_registrada()
    assert registro == {"dica": "9a3f", "criada_em": "2026-08-17T10:00:00+00:00"}
    assert "chave_hash" not in registro


def test_gravar_de_novo_substitui_no_lugar(banco):
    """Rotacao troca a mestra, nao acumula uma segunda valida."""
    banco.gravar_chave_mestra("hash-1", "9a3f", "2026-08-17T10:00:00+00:00")
    banco.gravar_chave_mestra("hash-2", "b7c1", "2026-08-17T11:00:00+00:00")
    assert banco.hash_da_chave_mestra() == "hash-2"
    assert banco.chave_mestra_registrada()["dica"] == "b7c1"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_db_chave_mestra.py -q`
Expected: FAIL — `AttributeError: 'Banco' object has no attribute 'gravar_chave_mestra'`

- [ ] **Step 3: Implementar**

No bloco de `CREATE TABLE` de `migrar`:

```sql
CREATE TABLE IF NOT EXISTS chave_mestra (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    chave_hash TEXT NOT NULL,
    dica TEXT NOT NULL,
    criada_em TEXT NOT NULL
)
```

E os três métodos, seguindo o estilo dos vizinhos (`hash_da_chave_acesso` como
modelo):

```python
    def gravar_chave_mestra(self, chave_hash: str, dica: str, criada_em: str) -> None:
        """Grava a mestra NO LUGAR da anterior, se houver.

        `INSERT OR REPLACE` com `id = 1` fixo: a rotacao troca a credencial em
        vez de acumular uma segunda valida, e o `CHECK (id = 1)` do schema faz
        do "existe no maximo uma mestra" uma garantia do banco, nao uma regra
        que a aplicacao precisa lembrar de conferir.
        """
        with self._conectar() as conexao:
            conexao.execute(
                "INSERT OR REPLACE INTO chave_mestra (id, chave_hash, dica, criada_em)"
                " VALUES (1, ?, ?, ?)",
                (chave_hash, dica, criada_em),
            )

    def hash_da_chave_mestra(self) -> str | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT chave_hash FROM chave_mestra WHERE id = 1"
            ).fetchone()
        return linha["chave_hash"] if linha else None

    def chave_mestra_registrada(self) -> dict | None:
        """Dica e data da mestra gravada. O hash NAO sai daqui."""
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT dica, criada_em FROM chave_mestra WHERE id = 1"
            ).fetchone()
        if linha is None:
            return None
        return {"dica": linha["dica"], "criada_em": linha["criada_em"]}
```

- [ ] **Step 4: Rodar os testes**

Run: `uv run pytest tests/test_db_chave_mestra.py -q && uv run pytest -q`
Expected: os 4 novos passam; suíte inteira verde (321 total).

- [ ] **Step 5: Commit**

```bash
git add fraus/db.py tests/test_db_chave_mestra.py
git commit -m "feat(acesso): a chave mestra passa a ter lugar no banco"
```

---

### Task 2: A mestra vigente e o middleware por requisição

O passo que faz o botão poder existir. Enquanto o middleware for registrado
condicionalmente no boot, ligar em runtime não protege nada.

**Files:**
- Modify: `fraus/api/contexto.py` (dois métodos)
- Modify: `fraus/api/seguranca.py` (`e_mestra`, `exigir_mestra`, `registrar_middleware_de_acesso`)
- Test: `tests/test_autenticacao_runtime.py`

**Interfaces:**
- Consumes: `Banco.hash_da_chave_mestra` (Task 1)
- Produces:
  - `Contexto.autenticacao_ligada() -> bool`
  - `Contexto.origem_da_mestra() -> str | None` — `"ambiente"`, `"banco"` ou `None`
  - `seguranca.e_mestra(ctx, chave)` passa a conferir ambiente **e** banco

- [ ] **Step 1: Escrever o teste**

```python
"""A autenticacao decide por REQUISICAO, nao por boot.

Sem isto, ligar a mestra em runtime nao protegeria nada: o middleware nem
existiria no app que subiu aberto.
"""

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus import credencial
from fraus.db import Banco


class MotorFalso:
    def pontuar_conversa(self, conversa):
        return 50.0


def _cliente(tmp_path, chave_mestra=None):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    app = criar_app(
        banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path,
        chave_mestra=chave_mestra,
    )
    return TestClient(app), banco


def test_mestra_gravada_no_banco_passa_a_valer_no_mesmo_processo(tmp_path):
    cliente, banco = _cliente(tmp_path)
    assert cliente.get("/conversas").status_code == 200  # aberta

    chave = "frm_" + "a" * 64
    banco.gravar_chave_mestra(
        credencial.hash_da_chave(chave), credencial.dica(chave),
        "2026-08-17T10:00:00+00:00",
    )

    # MESMO cliente, MESMO app: sem reiniciar nada.
    assert cliente.get("/conversas").status_code == 401
    autorizada = cliente.get("/conversas", headers={"Authorization": f"Bearer {chave}"})
    assert autorizada.status_code == 200


def test_ambiente_vence_o_banco(tmp_path):
    do_ambiente = "segredo-do-ambiente"
    cliente, banco = _cliente(tmp_path, chave_mestra=do_ambiente)
    do_banco = "frm_" + "b" * 64
    banco.gravar_chave_mestra(
        credencial.hash_da_chave(do_banco), credencial.dica(do_banco),
        "2026-08-17T10:00:00+00:00",
    )

    assert cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {do_ambiente}"}
    ).status_code == 200
    # A do banco tambem vale: as duas procedencias autorizam, o ambiente so tem
    # precedencia como ORIGEM declarada -- nao invalida a gravada.
    assert cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {do_banco}"}
    ).status_code == 200


def test_estado_sem_mestra_nenhuma(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.get("/acesso/estado").json() == {"ligada": False, "origem": None}


def test_estado_com_ambiente(tmp_path):
    cliente, _ = _cliente(tmp_path, chave_mestra="segredo")
    corpo = cliente.get(
        "/acesso/estado", headers={"Authorization": "Bearer segredo"}
    ).json()
    assert corpo == {"ligada": True, "origem": "ambiente"}
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_autenticacao_runtime.py -q`
Expected: FAIL — `/acesso/estado` dá 404 e a mestra do banco não autoriza.

- [ ] **Step 3: Implementar no `Contexto`**

```python
    def autenticacao_ligada(self) -> bool:
        """Se alguma mestra existe -- do ambiente ou gravada."""
        return self.origem_da_mestra() is not None

    def origem_da_mestra(self) -> str | None:
        """De onde vem a mestra vigente. O AMBIENTE vence.

        Duas procedencias porque as duas resolvem problemas diferentes: a
        variavel e o caminho de quem opera por ambiente (e a saida de quem
        perdeu a chave gerada pela tela), e o banco e o que faz o botao
        sobreviver a reiniciar o processo. Ler as duas por requisicao e o que
        permite ligar a autenticacao sem derrubar o servidor.
        """
        if self.chave_mestra is not None:
            return "ambiente"
        if self.banco.hash_da_chave_mestra() is not None:
            return "banco"
        return None
```

- [ ] **Step 4: Implementar em `seguranca.py`**

`e_mestra` passa a conferir as duas procedências:

```python
def e_mestra(ctx: Contexto, chave: str) -> bool:
    """Confere a chave contra as duas procedencias da mestra.

    A do ambiente e comparada em tempo constante contra o valor cru; a do
    banco, contra o hash -- `credencial.confere` tambem nao vaza pelo tempo.
    Uma chave errada percorre as duas antes de ser negada, entao o tempo de
    resposta nao conta qual das duas existe.
    """
    do_ambiente = False
    if ctx.chave_mestra is not None:
        do_ambiente = hmac.compare_digest(
            chave.encode("utf-8"), ctx.chave_mestra.encode("utf-8")
        )
    do_banco = credencial.confere(chave, ctx.banco.hash_da_chave_mestra())
    return do_ambiente or do_banco
```

`exigir_mestra` troca `if ctx.chave_mestra is None` por
`if not ctx.autenticacao_ligada()`.

O middleware passa a ser sempre registrado, decidindo por requisição:

```python
def registrar_middleware_de_acesso(app: FastAPI, ctx: Contexto) -> None:
    """Exige chave em toda rota QUANDO ha mestra -- decidido por requisicao.

    Antes o middleware so era registrado se houvesse mestra no boot, e isso
    tornava impossivel ligar a autenticacao sem reiniciar: o app que subiu
    aberto nao tinha onde exigir a chave. Agora ele existe sempre e pergunta o
    estado a cada requisicao -- sem mestra, libera igual a antes.
    """

    @app.middleware("http")
    async def exigir_chave_de_acesso(request, call_next):
        if not ctx.autenticacao_ligada():
            return await call_next(request)
        # /ingestao tem credencial propria (chave de FONTE): uma credencial por
        # rota. /acesso/estado e publica por necessidade -- a tela precisa dela
        # justamente quando ainda nao ha credencial. OPTIONS e o preflight do
        # navegador, que nao carrega header de autorizacao por definicao.
        caminho = request.url.path.rstrip("/")
        if caminho in ISENTAS or request.method == "OPTIONS":
            return await call_next(request)
        ...  # resto igual ao de hoje
```

com `ISENTAS = ("/ingestao", "/acesso/estado")` no topo do módulo.

- [ ] **Step 5: Implementar `GET /acesso/estado`**

Em `fraus/api/rotas/acesso.py`:

```python
@router.get("/acesso/estado")
def estado(ctx: Contexto = Depends(obter_contexto)) -> dict:
    """A autenticacao esta ligada, e de onde vem a mestra.

    PUBLICA por necessidade: a tela precisa desta resposta exatamente quando
    ainda nao existe credencial nenhuma para apresentar. Por isso ela nao
    carrega dica, hash nem data -- so o suficiente para a interface saber o
    que desenhar.
    """
    return {"ligada": ctx.autenticacao_ligada(), "origem": ctx.origem_da_mestra()}
```

- [ ] **Step 6: Rodar tudo**

Run: `uv run pytest -q`
Expected: verde. Os testes de `tests/test_autenticacao.py` são a prova de que o
middleware sempre-registrado não mudou o comportamento de quem usa ambiente.

- [ ] **Step 7: Commit**

```bash
git add fraus/api tests/test_autenticacao_runtime.py
git commit -m "feat(acesso): a autenticacao passa a ser decidida por requisicao"
```

---

### Task 3: `POST /acesso/mestra`

**Files:**
- Modify: `fraus/api/rotas/acesso.py`
- Modify: `fraus/acesso.py` (o gerador da mestra)
- Test: `tests/test_acesso_mestra.py`

**Interfaces:**
- Consumes: Tasks 1 e 2
- Produces:
  - `acesso.gerar_mestra() -> tuple[str, str]` — `(chave_em_claro, hash)`, prefixo `frm_`
  - `POST /acesso/mestra` → 201 `{"chave_mestra", "chave_acesso"|null, "aviso"}` · 409 quando já ligada sem a mestra atual

- [ ] **Step 1: Escrever o teste**

```python
"""POST /acesso/mestra: primeiro uso, recusa de sobrescrita e rotacao."""

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco


class MotorFalso:
    def pontuar_conversa(self, conversa):
        return 50.0


def _cliente(tmp_path, chave_mestra=None):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    return TestClient(criar_app(
        banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path,
        chave_mestra=chave_mestra,
    ))


def test_primeiro_uso_liga_e_devolve_as_duas_chaves(tmp_path):
    cliente = _cliente(tmp_path)
    resposta = cliente.post("/acesso/mestra")
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["chave_mestra"].startswith("frm_")
    assert corpo["chave_acesso"].startswith("fra_")
    assert "aviso" in corpo

    # Ligou de verdade, no mesmo processo.
    assert cliente.get("/conversas").status_code == 401
    # E a chave de acesso emitida junto FUNCIONA -- sem isso o clique deixaria
    # a propria dashboard em 401.
    assert cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {corpo['chave_acesso']}"}
    ).status_code == 200
    # A mestra tambem.
    assert cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {corpo['chave_mestra']}"}
    ).status_code == 200


def test_segunda_chamada_sem_a_mestra_atual_e_409(tmp_path):
    cliente = _cliente(tmp_path)
    primeira = cliente.post("/acesso/mestra").json()

    conflito = cliente.post(
        "/acesso/mestra",
        headers={"Authorization": f"Bearer {primeira['chave_acesso']}"},
    )
    assert conflito.status_code == 409
    # A mestra de quem esta dentro continua valendo: nada foi sobrescrito.
    assert cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {primeira['chave_mestra']}"}
    ).status_code == 200


def test_rotacao_com_a_mestra_atual_invalida_a_antiga(tmp_path):
    cliente = _cliente(tmp_path)
    antiga = cliente.post("/acesso/mestra").json()["chave_mestra"]

    resposta = cliente.post(
        "/acesso/mestra", headers={"Authorization": f"Bearer {antiga}"}
    )
    assert resposta.status_code == 201
    nova = resposta.json()["chave_mestra"]
    assert nova != antiga
    # Rotacao NAO emite chave de acesso: a da dashboard continua valendo.
    assert resposta.json()["chave_acesso"] is None

    assert cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {antiga}"}
    ).status_code == 401
    assert cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {nova}"}
    ).status_code == 200


def test_com_mestra_de_ambiente_a_rota_recusa(tmp_path):
    """Quem opera por ambiente nao troca a credencial por HTTP.

    A variavel e a fonte, e sobrescreve-la pelo banco criaria duas verdades
    com a do ambiente vencendo -- o botao pareceria funcionar e nao mudaria
    nada.
    """
    cliente = _cliente(tmp_path, chave_mestra="segredo-do-ambiente")
    resposta = cliente.post(
        "/acesso/mestra", headers={"Authorization": "Bearer segredo-do-ambiente"}
    )
    assert resposta.status_code == 409
    assert "ambiente" in resposta.json()["detail"]


def test_resposta_nunca_carrega_hash(tmp_path):
    cliente = _cliente(tmp_path)
    corpo = cliente.post("/acesso/mestra").json()
    assert "chave_hash" not in corpo
    assert "hash" not in str(corpo).replace("chave_mestra", "")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_acesso_mestra.py -q`
Expected: FAIL — 404/405 em `/acesso/mestra`.

- [ ] **Step 3: Implementar o gerador**

Em `fraus/acesso.py`:

```python
PREFIXO_MESTRA = "frm"


def gerar_mestra() -> tuple[str, str]:
    """Cria uma chave mestra nova. Devolve `(chave_em_claro, hash)`.

    Sem id embutido, ao contrario de `gerar`: existe no maximo UMA mestra, e
    nao ha linha a localizar. O prefixo proprio serve ao mesmo proposito dos
    outros dois -- varredura de segredo em repositorio reconhece o que e, e
    uma chave apresentada no papel errado falha na leitura do prefixo.
    """
    segredo = secrets.token_hex(credencial.BYTES_DO_SEGREDO)
    chave = f"{PREFIXO_MESTRA}_{segredo}"
    return chave, credencial.hash_da_chave(chave)
```

- [ ] **Step 4: Implementar a rota**

Em `fraus/api/rotas/acesso.py`, com a docstring explicando os dois caminhos e
o porquê do 409. A rota:

1. Se `ctx.chave_mestra is not None` → 409 nomeando o ambiente como fonte.
2. Se há hash no banco → exige a mestra atual (`exigir_mestra`) e, faltando,
   409 explicando que a rotação precisa da chave atual.
3. Gera a mestra, grava o hash com `credencial.dica`, e **só no primeiro uso**
   emite a chave de acesso `dashboard` (reaproveitando o caminho de
   `criar_chave_acesso`).

- [ ] **Step 5: Rodar tudo**

Run: `uv run pytest -q`
Expected: verde.

- [ ] **Step 6: Commit**

```bash
git add fraus/acesso.py fraus/api/rotas/acesso.py tests/test_acesso_mestra.py
git commit -m "feat(acesso): rota que liga a autenticacao e rotaciona a mestra"
```

---

### Task 4: O proxy do Next sobrevive ao clique

**Files:**
- Create: `dashboard/app/api/fraus/ligar-autenticacao/route.ts`
- Modify: `dashboard/app/api/fraus/[...caminho]/route.ts`

**Interfaces:**
- Produces:
  - `POST /api/fraus/ligar-autenticacao` → repassa o corpo da API e, em 201, grava o cookie `fraus_acesso`
  - o proxy geral passa a usar `FRAUS_CHAVE_ACESSO ?? cookie fraus_acesso`

- [ ] **Step 1: Criar a rota de ligar**

```ts
/**
 * Liga a autenticacao da API e guarda a chave de acesso emitida.
 *
 * Existe separada do proxy porque o proxy e BOBO de proposito: ele repassa
 * bytes e nao interpreta corpo de resposta. Quem sabe que o 201 desta rota
 * especifica carrega uma credencial a guardar e esta rota.
 *
 * A chave vai para um cookie `httpOnly`: o JS do navegador continua sem
 * alcancar credencial nenhuma, que e a mesma promessa da variavel de ambiente
 * server-side.
 */

const API = process.env.FRAUS_API_URL ?? "http://localhost:8000";
const COOKIE = "fraus_acesso";

export async function POST(requisicao: Request): Promise<Response> {
  const autorizacao = requisicao.headers.get("authorization");
  const cabecalhos: HeadersInit = autorizacao ? { authorization: autorizacao } : {};

  let resposta: Response;
  try {
    resposta = await fetch(`${API}/acesso/mestra`, {
      method: "POST",
      headers: cabecalhos,
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
  } catch {
    return Response.json({ detail: "API não respondeu" }, { status: 502 });
  }

  const corpo = await resposta.json().catch(() => null);
  if (resposta.status !== 201 || !corpo) {
    return Response.json(corpo ?? { detail: "resposta inesperada da API" }, {
      status: resposta.status,
    });
  }

  const devolvida = Response.json(corpo, { status: 201 });
  if (corpo.chave_acesso) {
    devolvida.headers.append(
      "set-cookie",
      [
        `${COOKIE}=${corpo.chave_acesso}`,
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
        process.env.NODE_ENV === "production" ? "Secure" : "",
        // Sem Max-Age: cookie de sessao. Fechar o navegador exige a chave de
        // novo, e a chave continua no banco -- nada e perdido, so o atalho.
      ].filter(Boolean).join("; "),
    );
  }
  return devolvida;
}
```

- [ ] **Step 2: Fazer o proxy ler o cookie**

Em `[...caminho]/route.ts`, trocar a constante de módulo por leitura por
requisição:

```ts
const CHAVE_DO_AMBIENTE = process.env.FRAUS_CHAVE_ACESSO;
const COOKIE = "fraus_acesso";

function chaveDaRequisicao(requisicao: Request): string | undefined {
  // O ambiente vence: e a credencial declarada do deploy. O cookie e o atalho
  // de quem ligou a autenticacao pela tela, e existe justamente porque
  // variavel de ambiente nao muda em processo vivo.
  if (CHAVE_DO_AMBIENTE) return CHAVE_DO_AMBIENTE;
  const bruto = requisicao.headers.get("cookie");
  if (!bruto) return undefined;
  for (const pedaco of bruto.split(";")) {
    const [nome, ...resto] = pedaco.trim().split("=");
    if (nome === COOKIE) return resto.join("=");
  }
  return undefined;
}
```

e no corpo de `repassar`:

```ts
  const chave = chaveDaRequisicao(requisicao);
  if (chave) cabecalhos.set("authorization", `Bearer ${chave}`);
```

O `cabecalhos.delete("cookie")` **também** entra: o cookie da dashboard não
tem nada a fazer numa requisição para a API.

- [ ] **Step 3: Build**

Run: `cd dashboard && npm run build`
Expected: build verde, sem erro de tipo.

- [ ] **Step 4: Commit**

```bash
git add dashboard/app/api
git commit -m "feat(dashboard): a chave de acesso pode vir de cookie httpOnly"
```

---

### Task 5: O painel na tela de Configurações

**Files:**
- Create: `dashboard/components/configuracoes/Autenticacao.tsx`
- Modify: `dashboard/app/configuracoes/page.tsx`
- Modify: `dashboard/lib/api.ts` (leitura de `GET /acesso/estado`)

**Interfaces:**
- Consumes: `GET /acesso/estado`, `POST /api/fraus/ligar-autenticacao`
- Produces: `<Autenticacao estado={...} />` — client component com os três estados

- [ ] **Step 1: Ler o estado no server component**

Em `lib/api.ts`, na forma dos outros leitores do arquivo, um
`obterEstadoDeAcesso()` para `/acesso/estado`, tipado
`{ligada: boolean; origem: "ambiente" | "banco" | null}`.

- [ ] **Step 2: Criar o componente**

Três estados, e o que cada um mostra:

- `ligada: false` — uma frase do que o botão faz e o botão "Ligar
  autenticação". Ao clicar, `POST /api/fraus/ligar-autenticacao`.
- acabou de ligar — as duas chaves em `<code>`, botão de copiar cada uma, e o
  aviso de que não voltam a aparecer. `router.refresh()` só depois de o João
  dispensar o painel, para a chave não sumir da tela por um re-render.
- `ligada: true` — o estado e a origem. Origem `"ambiente"`: diz que a
  variável manda e que a tela não troca credencial de ambiente. Origem
  `"banco"`: explica como rotacionar. **Sem botão de desligar** — e a ausência
  é declarada, como o painel "O que esta tela não configura" já faz.

- [ ] **Step 3: Encaixar na página**

Um `<Painel titulo="Autenticação">` acima de "Faixas de NPS", e um item novo
no painel "O que esta tela não configura": desligar a autenticação.

- [ ] **Step 4: Build + verificação manual**

Run: `cd dashboard && npm run build`
Expected: verde.

Depois, com `uv run python scripts/api_demo.py` e `npm run dev`: abrir
`/configuracoes`, ver "desligada", clicar, ver as duas chaves, navegar para
`/atendimentos` e confirmar que a lista **continua carregando** (é o cookie
funcionando), reiniciar a API e confirmar que segue exigindo chave.

- [ ] **Step 5: Commit**

```bash
git add dashboard
git commit -m "feat(dashboard): painel que liga a autenticacao na tela"
```

---

### Task 6: README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Reescrever "Ligando a autenticação"**

O botão passa a ser o caminho principal (abrir `/configuracoes`, clicar,
guardar as duas chaves); a variável de ambiente vira a alternativa de quem
opera por ambiente, com a nota de que ela **vence** o banco.

- [ ] **Step 2: Corrigir as limitações conhecidas**

Dois pontos ficaram desatualizados por esta feature: "a API é aberta por
padrão, e passa a exigir chave quando `FRAUS_CHAVE_MESTRA` é definida" (agora
há a segunda procedência) e "a dashboard publicada continua sem login" (agora
há o cookie, e sem ele a dashboard cai em 401). Nenhum dos dois pode continuar
como está — limitação desatualizada é pior que limitação ausente.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(acesso): o botao como caminho principal da autenticacao"
```
