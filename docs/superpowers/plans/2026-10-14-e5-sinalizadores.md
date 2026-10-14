# E5 — Sinalizadores por regras: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Marcar conversas de risco com cinco regras explicáveis, derivadas na leitura, sem modelo, sem LLM e sem julgar o atendente humano.

**Architecture:** `fraus/sinalizadores.py` é puro (`Conversa` → lista de achados ou `None`). A API acrescenta o campo `sinalizadores` em `_com_derivacoes` (lista e detalhe pelo mesmo caminho) e o filtro `?sinalizador=` em `GET /conversas`. A dashboard lista os achados acima da transcrição e marca as mensagens de evidência. `scripts/medir_sinalizadores.py` mede com casos construídos e, quando houver, com amostra anotada.

**Tech Stack:** Python 3.11 / FastAPI / pytest; Next.js + TypeScript / vitest (`renderToStaticMarkup`).

**Spec:** `docs/superpowers/specs/2026-10-14-e5-sinalizadores-design.md`

## Global Constraints

- Nada é gravado. Nenhuma coluna, tabela ou chave de payload nova. Score, nota e categoria gravados ficam intactos.
- Nenhuma regra lê texto nem timestamp de fala `humano` para julgá-la. Só a **presença e a posição** da primeira fala `humano` são permitidas. "Score de performance por atendente" é violação de política, não feature.
- Conversa sem fala do cliente: `sinalizadores` é `None`, nunca `[]`. "Não avaliado" ≠ "nada disparou" (invariante 2).
- Os limiares são `0,85` (loop do bot, Jaccard), `0,7` com mínimo de 4 tokens (cliente repete), "mais de 2" respostas do bot (pedido ignorado) e `N = 3` (escalada tardia). Todos são **sem procedência**, e o texto de `detalhe` diz isso.
- O limiar mora só em Python. A tela não redigita limiar: ele chega dentro de `detalhe`.
- O escopo por canal vem de `BancoComEscopo`, e o filtro não pode vazar canal sem permissão.
- Sem LLM e sem dependência nova. Identificadores sem acento; texto de tela com acento.
- Commits em português sem acento, `tipo(escopo): resumo`, com o trailer `Co-Authored-By: Neuro <neuro.chan.dev@gmail.com>`. TDD: teste vermelho primeiro.
- Não tocar `modelos/`, `modelos-onnx/`, `fraus/fusor.py`, `fraus/sinais/tempo.py` nem `NOMES_FEATURES`.

## Decisões do plano (desvios e detalhamentos do spec)

1. **Um achado por regra por conversa.** A `evidencia` reúne todos os índices envolvidos, ordenados. A lista sai na ordem fixa de `REGRAS`.
2. **`loop_do_bot` exige ≥ 3 tokens** na resposta do bot, para "Ok." repetido não disparar. É limiar novo e sem procedência. "Não consecutivas no texto do cliente" foi lido como **há ao menos uma fala do cliente entre as duas respostas**.
3. **Léxico de pedido de humano, fechado:** `atendente`, `humano`, `humana`, `pessoa`, `operador`, `falar com alguem`. Casa por palavra inteira sobre `normalizar_fala` (sem acento, minúscula, sem pontuação).
4. **`pedido_de_humano_ignorado` e `escalada_tardia` são disjuntos.**
   - Ignorado: não há **nenhuma** fala `humano` depois do primeiro pedido, e o bot responde ≥ 3 vezes depois dele.
   - Tardia: há fala `humano` depois do pedido, e entre o pedido e ela há ≥ 4 respostas do bot.
   - A fala `humano` **não** entra na `evidencia`, para a tela nunca destacar a fala do atendente.
5. **`abandono` reaproveita `features_tempo(conversa)["abandonou"]`.** A evidência é a **última fala do cliente** ("o cliente não voltou depois daqui"), e não a última mensagem, que pode ser do humano. Falso positivo comum: despedida do bot. Isso é declarado.
6. **"Sem fala do cliente"** é `not conversa.tem_fala_cliente`. Conversa só de cortesia **é** avaliada, porque o cliente falou.
7. **O filtro pagina depois de filtrar.** Com `sinalizador`, a rota lê o recorte inteiro, deriva, filtra e então aplica `deslocamento`/`limite`. Sem `sinalizador`, nada muda. Regra desconhecida responde 400.
8. **Filtro na tela fica fora.** O spec pede o filtro na API e o destaque na transcrição; um controle de filtro na lista de atendimentos fica para depois.
9. **Os casos construídos moram em `fraus/dados/casos_sinalizadores.py`.** Testes e script usam a mesma fonte. Precisão em caso construído **verifica a implementação, não mede qualidade**, e o script diz isso.
10. **A amostra anotada fica pendente de fonte.** O script aceita `--anotada arquivo.jsonl` e, sem ela, imprime "não verificado — fonte pendente". Wilson vem de `fraus.api.rotas.confianca.wilson`.

## Review Focus

1. **Paginação com filtro:** página 2 de `?sinalizador=abandono&limite=1&deslocamento=1` traz a segunda conversa **sinalizada**, não a segunda do banco. Teste na Tarefa 2.
2. **Fala humana alterada não muda nada:** trocar texto e timestamp de toda fala `humano` deixa `sinalizadores` idêntico. Teste na Tarefa 1.
3. **Texto vazio ou só pontuação** (`"???"`) não dispara loop nem repetição: tokens vazios dão Jaccard 0. Teste na Tarefa 1.
4. **Pedido de humano dentro de outra palavra** (`"humanoide"`, `"pessoal"`) não conta como pedido. Teste na Tarefa 1.
5. **Conversa sem fala do cliente na lista filtrada** não aparece em nenhum filtro e não quebra a tela (`null` tratado). Testes nas Tarefas 2 e 3.

---

### Tarefa 1: módulo puro `fraus/sinalizadores.py`

**Files:**
- Create: `fraus/sinalizadores.py`
- Test: `tests/test_sinalizadores.py`

**Interfaces:**
- Consumes: `fraus.cortesia.normalizar_fala(texto) -> str`; `fraus.sinais.tempo.features_tempo(conversa) -> dict[str, float]`; `Conversa.tem_fala_cliente` (property).
- Produces:
  - `REGRAS: tuple[str, ...] = ("loop_do_bot", "cliente_repete", "pedido_de_humano_ignorado", "escalada_tardia", "abandono")`
  - `sinalizadores(conversa: Conversa) -> list[dict] | None`; cada dict é `{"regra": str, "evidencia": list[int], "detalhe": str}`.
  - `jaccard(a: frozenset[str], b: frozenset[str]) -> float`
  - Constantes: `LIMIAR_LOOP_BOT = 0.85`, `MIN_TOKENS_BOT = 3`, `LIMIAR_CLIENTE_REPETE = 0.7`, `MIN_TOKENS_CLIENTE = 4`, `MAX_RESPOSTAS_SEM_HUMANO = 2`, `N_ESCALADA_TARDIA = 3`, `PEDIDOS_DE_HUMANO`.

- [ ] **Step 1: Escrever os testes que falham**

```python
"""Sinalizadores: positivo, negativo e borda por regra, e as duas guardas do spec.

As guardas que mais importam nao sao as das regras: sao `None` != `[]` (conversa
sem fala do cliente nao foi avaliada) e a de Conformidade (nenhuma regra le o
texto ou o relogio da fala humana).
"""

from datetime import datetime, timedelta, timezone

from fraus.modelos import Conversa, Mensagem
from fraus.sinalizadores import REGRAS, jaccard, sinalizadores

T0 = datetime(2026, 10, 14, 9, 0, tzinfo=timezone.utc)


def conv(*falas, cid="c"):
    """`falas` = pares (autor, texto); um minuto entre cada mensagem."""
    return Conversa(
        id=cid,
        canal="chat",
        iniciada_em=T0,
        mensagens=[
            Mensagem(autor=a, texto=t, enviada_em=T0 + timedelta(minutes=k))
            for k, (a, t) in enumerate(falas)
        ],
    )


def regras(c):
    return [s["regra"] for s in sinalizadores(c)]


def achado(c, regra):
    return next(s for s in sinalizadores(c) if s["regra"] == regra)


def palavras(n, prefixo="p"):
    return " ".join(f"{prefixo}{k}" for k in range(n))


# ---- contrato -------------------------------------------------------------

def test_sem_fala_do_cliente_e_none_e_nao_lista_vazia():
    assert sinalizadores(conv(("bot", "ola, posso ajudar?"))) is None


def test_conversa_comum_avaliada_devolve_lista_vazia():
    c = conv(("cliente", "quero a segunda via do boleto"),
             ("bot", "claro, enviei a segunda via no seu email"),
             ("cliente", "recebi, obrigado"))
    assert sinalizadores(c) == []


def test_regras_tem_ordem_fixa():
    assert REGRAS == ("loop_do_bot", "cliente_repete", "pedido_de_humano_ignorado",
                      "escalada_tardia", "abandono")


def test_jaccard_de_vazios_e_zero():
    assert jaccard(frozenset(), frozenset()) == 0.0


# ---- loop_do_bot ----------------------------------------------------------

RESPOSTA = "nao entendi sua pergunta, pode reformular por favor"


def test_loop_do_bot_positivo():
    c = conv(("cliente", "meu pedido nao chegou"), ("bot", RESPOSTA),
             ("cliente", "o pedido 123 nao chegou"), ("bot", RESPOSTA + "!"),
             ("cliente", "ok"))
    s = achado(c, "loop_do_bot")
    assert s["evidencia"] == [1, 3]
    assert "0,85" in s["detalhe"] and "sem procedência" in s["detalhe"]


def test_loop_do_bot_negativo_sem_cliente_entre_as_respostas():
    c = conv(("cliente", "meu pedido nao chegou"), ("bot", RESPOSTA), ("bot", RESPOSTA),
             ("cliente", "ok"))
    assert "loop_do_bot" not in regras(c)


def test_loop_do_bot_borda_exatamente_no_limiar_dispara():
    # 17 tokens em comum, uniao de 20: Jaccard = 0,85 exato.
    a = palavras(17) + " xa xb"
    b = palavras(17) + " xc"
    c = conv(("cliente", "oi"), ("bot", a), ("cliente", "de novo"), ("bot", b), ("cliente", "ok"))
    assert "loop_do_bot" in regras(c)


def test_loop_do_bot_borda_um_fio_abaixo_nao_dispara():
    # 17 em comum, uniao de 21: 0,8095.
    a = palavras(17) + " xa xb"
    b = palavras(17) + " xc xd"
    c = conv(("cliente", "oi"), ("bot", a), ("cliente", "de novo"), ("bot", b), ("cliente", "ok"))
    assert "loop_do_bot" not in regras(c)


def test_loop_do_bot_resposta_curta_nao_dispara():
    c = conv(("cliente", "oi"), ("bot", "Ok."), ("cliente", "e ai"), ("bot", "Ok."), ("cliente", "?"))
    assert "loop_do_bot" not in regras(c)


def test_so_pontuacao_nao_dispara_nada_por_similaridade():
    c = conv(("cliente", "???"), ("bot", "..."), ("cliente", "???"), ("bot", "..."),
             ("cliente", "???"))
    assert {"loop_do_bot", "cliente_repete"}.isdisjoint(regras(c))


# ---- cliente_repete -------------------------------------------------------

def test_cliente_repete_positivo():
    c = conv(("cliente", "quero cancelar minha assinatura agora"), ("bot", "posso ajudar com outra coisa?"),
             ("cliente", "quero cancelar minha assinatura agora!!"))
    assert achado(c, "cliente_repete")["evidencia"] == [0, 2]


def test_cliente_repete_negativo_falas_diferentes():
    c = conv(("cliente", "quero cancelar minha assinatura agora"), ("bot", "certo"),
             ("cliente", "qual o prazo do reembolso no cartao"))
    assert "cliente_repete" not in regras(c)


def test_cliente_repete_borda_tres_tokens_nao_conta():
    c = conv(("cliente", "nao funcionou ainda"), ("bot", "tente de novo"),
             ("cliente", "nao funcionou ainda"))
    assert "cliente_repete" not in regras(c)


def test_cliente_repete_borda_exatamente_07_dispara():
    # 7 em comum, uniao de 10.
    a = palavras(7) + " xa xb"
    b = palavras(7) + " xc"
    c = conv(("cliente", a), ("bot", "certo"), ("cliente", b))
    assert "cliente_repete" in regras(c)


# ---- pedido_de_humano_ignorado / escalada_tardia ----------------------------

def _bots(n):
    return [("bot", f"resposta automatica numero {k}") for k in range(n)]


def test_pedido_ignorado_positivo():
    c = conv(("cliente", "quero falar com um atendente"), *_bots(3))
    s = achado(c, "pedido_de_humano_ignorado")
    assert s["evidencia"] == [0, 1, 2, 3]
    assert "sem procedência" in s["detalhe"]


def test_pedido_ignorado_borda_duas_respostas_nao_dispara():
    c = conv(("cliente", "quero falar com um atendente"), *_bots(2))
    assert "pedido_de_humano_ignorado" not in regras(c)


def test_pedido_ignorado_negativo_humano_entrou():
    c = conv(("cliente", "quero falar com um atendente"), *_bots(3), ("humano", "oi, sou a Ana"))
    assert "pedido_de_humano_ignorado" not in regras(c)


def test_palavra_que_contem_o_termo_nao_e_pedido():
    c = conv(("cliente", "o robo humanoide do anuncio e pessoal?"), *_bots(3))
    assert "pedido_de_humano_ignorado" not in regras(c)


def test_pedido_com_acento_e_maiuscula_conta():
    c = conv(("cliente", "Quero FALAR COM ALGUÉM, por favor"), *_bots(3))
    assert "pedido_de_humano_ignorado" in regras(c)


def test_escalada_tardia_positivo_e_humano_fora_da_evidencia():
    c = conv(("cliente", "me passa para um humano"), *_bots(4), ("humano", "ola"))
    s = achado(c, "escalada_tardia")
    assert s["evidencia"] == [0, 1, 2, 3, 4]
    assert 5 not in s["evidencia"]
    assert "pedido_de_humano_ignorado" not in regras(c)


def test_escalada_tardia_borda_tres_respostas_nao_dispara():
    c = conv(("cliente", "me passa para um humano"), *_bots(3), ("humano", "ola"))
    assert "escalada_tardia" not in regras(c)


def test_escalada_sem_pedido_nao_dispara():
    c = conv(("cliente", "meu boleto venceu"), *_bots(5), ("humano", "ola"))
    assert "escalada_tardia" not in regras(c)


# ---- abandono ---------------------------------------------------------------

def test_abandono_positivo_ultima_fala_do_bot():
    c = conv(("cliente", "meu boleto venceu"), ("bot", "gerei um novo boleto"))
    assert achado(c, "abandono")["evidencia"] == [0]  # a ultima fala do CLIENTE


def test_abandono_com_humano_por_ultimo_nao_aponta_o_humano():
    c = conv(("cliente", "meu boleto venceu"), ("humano", "resolvido, ate logo"))
    assert achado(c, "abandono")["evidencia"] == [0]


def test_abandono_negativo_cliente_fecha():
    c = conv(("cliente", "meu boleto venceu"), ("bot", "gerei um novo boleto"), ("cliente", "valeu"))
    assert "abandono" not in regras(c)


# ---- Conformidade -------------------------------------------------------------

def test_texto_e_relogio_da_fala_humana_nao_mudam_nada():
    """O Fraus nao pontua atendente. So presenca e posicao da fala humana contam."""
    base = [("cliente", "me passa para um humano"), *_bots(4), ("humano", "ola, sou a Ana"),
            ("cliente", "me passa para um humano"), ("humano", "resolvido")]
    original = conv(*base)
    alterada = original.model_copy(deep=True)
    for k, m in enumerate(alterada.mensagens):
        if m.autor == "humano":
            alterada.mensagens[k] = Mensagem(
                autor="humano", texto="!!! qualquer coisa ofensiva e longa !!!",
                enviada_em=T0 + timedelta(days=3, seconds=k),
            )
    assert sinalizadores(alterada) == sinalizadores(original)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_sinalizadores.py -q`
Expected: FAIL, com `ModuleNotFoundError: No module named 'fraus.sinalizadores'`.

- [ ] **Step 3: Implementação mínima**

```python
"""Sinalizadores por regra: conversas de risco destacadas sem modelo e sem LLM.

Cinco regras de superficie sobre falas do cliente, falas do bot, contagens e
posicao. DERIVADAS NA LEITURA, como a contestacao: nada e gravado, e a marca
vale retroativamente para o que ja esta no banco. Marca e informa, nao
corrige -- score, nota e categoria ficam intactos.

O LIMITE DE CONFORMIDADE E DURO: nenhuma regra le o texto ou o relogio de uma
fala `humano`. Da fala humana so contam a PRESENCA e a POSICAO, e ela nunca
entra na `evidencia` -- a tela nao destaca a fala do atendente. Medir o
humano seria pontua-lo (docs/conformidade.md).

Conversa sem fala do cliente devolve `None`, nao `[]`: "nao avaliado" e
diferente de "nada disparou" (invariante 2).

Os limiares sao SEM PROCEDENCIA (como o 95 da contestacao) e o `detalhe` de
cada achado diz isso. Spec: docs/superpowers/specs/2026-10-14-e5-sinalizadores-design.md
"""

from itertools import combinations

from fraus.cortesia import normalizar_fala
from fraus.modelos import Conversa
from fraus.sinais.tempo import features_tempo

REGRAS = (
    "loop_do_bot",
    "cliente_repete",
    "pedido_de_humano_ignorado",
    "escalada_tardia",
    "abandono",
)

LIMIAR_LOOP_BOT = 0.85
MIN_TOKENS_BOT = 3
LIMIAR_CLIENTE_REPETE = 0.7
MIN_TOKENS_CLIENTE = 4
MAX_RESPOSTAS_SEM_HUMANO = 2
N_ESCALADA_TARDIA = 3

# Fechado de proposito: e uma limitacao declarada, nao um esquecimento.
PEDIDOS_DE_HUMANO = ("atendente", "humano", "humana", "pessoa", "operador", "falar com alguem")


def _tokens(texto: str) -> frozenset[str]:
    return frozenset(normalizar_fala(texto).split())


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    uniao = a | b
    return len(a & b) / len(uniao) if uniao else 0.0


def _pede_humano(texto: str) -> bool:
    fala = f" {normalizar_fala(texto)} "
    return any(f" {termo} " in fala for termo in PEDIDOS_DE_HUMANO)


def _achado(regra: str, evidencia, detalhe: str) -> dict:
    return {"regra": regra, "evidencia": sorted(set(evidencia)), "detalhe": detalhe}


def _loop_do_bot(conversa: Conversa) -> dict | None:
    msgs = conversa.mensagens
    bots = [(i, _tokens(m.texto)) for i, m in enumerate(msgs) if m.autor == "bot"]
    bots = [(i, t) for i, t in bots if len(t) >= MIN_TOKENS_BOT]
    evidencia: set[int] = set()
    for (i, a), (j, b) in combinations(bots, 2):
        cliente_entre = any(m.autor == "cliente" for m in msgs[i + 1:j])
        if cliente_entre and jaccard(a, b) >= LIMIAR_LOOP_BOT:
            evidencia |= {i, j}
    if not evidencia:
        return None
    return _achado(
        "loop_do_bot", evidencia,
        f"{len(evidencia)} respostas do bot quase idênticas, com fala do cliente "
        "entre elas (Jaccard ≥ 0,85; limiar sem procedência)",
    )


def _cliente_repete(conversa: Conversa) -> dict | None:
    falas = [(i, _tokens(m.texto)) for i, m in enumerate(conversa.mensagens)
             if m.autor == "cliente"]
    falas = [(i, t) for i, t in falas if len(t) >= MIN_TOKENS_CLIENTE]
    evidencia: set[int] = set()
    for (i, a), (j, b) in combinations(falas, 2):
        if jaccard(a, b) >= LIMIAR_CLIENTE_REPETE:
            evidencia |= {i, j}
    if not evidencia:
        return None
    return _achado(
        "cliente_repete", evidencia,
        f"o cliente repetiu {len(evidencia)} falas quase iguais (Jaccard ≥ 0,7, "
        "mínimo de 4 palavras; limiar sem procedência)",
    )


def _primeiro_pedido(conversa: Conversa) -> int | None:
    return next((i for i, m in enumerate(conversa.mensagens)
                 if m.autor == "cliente" and _pede_humano(m.texto)), None)


def _primeiro_humano_depois(conversa: Conversa, inicio: int) -> int | None:
    # So a POSICAO da fala humana. Texto e relogio dela nunca sao lidos.
    return next((i for i in range(inicio + 1, len(conversa.mensagens))
                 if conversa.mensagens[i].autor == "humano"), None)


def _bots_entre(conversa: Conversa, inicio: int, fim: int) -> list[int]:
    return [i for i in range(inicio + 1, fim) if conversa.mensagens[i].autor == "bot"]


def _pedido_ignorado(conversa: Conversa) -> dict | None:
    pedido = _primeiro_pedido(conversa)
    if pedido is None or _primeiro_humano_depois(conversa, pedido) is not None:
        return None
    bots = _bots_entre(conversa, pedido, len(conversa.mensagens))
    if len(bots) <= MAX_RESPOSTAS_SEM_HUMANO:
        return None
    return _achado(
        "pedido_de_humano_ignorado", [pedido, *bots],
        f"o cliente pediu atendimento humano e o bot respondeu {len(bots)} vezes "
        "sem um humano entrar (mais de 2; limiar sem procedência)",
    )


def _escalada_tardia(conversa: Conversa) -> dict | None:
    pedido = _primeiro_pedido(conversa)
    if pedido is None:
        return None
    humano = _primeiro_humano_depois(conversa, pedido)
    if humano is None:
        return None
    bots = _bots_entre(conversa, pedido, humano)
    if len(bots) <= N_ESCALADA_TARDIA:
        return None
    return _achado(
        "escalada_tardia", [pedido, *bots],
        f"o humano entrou depois de {len(bots)} respostas do bot ao pedido "
        "(mais de 3; limiar sem procedência). Conta falas do bot, nunca o tempo do humano",
    )


def _abandono(conversa: Conversa) -> dict | None:
    if features_tempo(conversa)["abandonou"] != 1.0:
        return None
    # A evidencia e a ultima fala do CLIENTE, nunca a ultima mensagem: ela
    # pode ser do humano, e a fala humana nao entra em evidencia.
    ultima_do_cliente = max(i for i, m in enumerate(conversa.mensagens) if m.autor == "cliente")
    return _achado(
        "abandono", [ultima_do_cliente],
        "a última fala é de quem responde e o cliente não voltou depois desta mensagem",
    )


_DETECTORES = (_loop_do_bot, _cliente_repete, _pedido_ignorado, _escalada_tardia, _abandono)


def sinalizadores(conversa: Conversa) -> list[dict] | None:
    """Achados na ordem de `REGRAS`; `None` quando nao ha fala do cliente."""
    if not conversa.tem_fala_cliente:
        return None
    return [a for a in (detector(conversa) for detector in _DETECTORES) if a is not None]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_sinalizadores.py -q`
Expected: PASS, todos.

- [ ] **Step 5: Commit**

```bash
git add fraus/sinalizadores.py tests/test_sinalizadores.py
git commit -m "feat(sinalizadores): cinco regras derivadas na leitura, sem julgar o humano"
```

---

### Tarefa 2: exposição na API (`sinalizadores` e `?sinalizador=`)

**Files:**
- Modify: `fraus/api/rotas/conversas.py`, a função `listar` (por volta da linha 250) e `_com_derivacoes` (por volta da linha 287).
- Test: `tests/test_api_sinalizadores.py`

**Interfaces:**
- Consumes: `fraus.sinalizadores.REGRAS`, `fraus.sinalizadores.sinalizadores`.
- Produces:
  - `GET /conversas` e `GET /conversas/{id}` trazem a chave `sinalizadores: list[{regra, evidencia, detalhe}] | None`.
  - `GET /conversas?sinalizador=<regra>` responde 400 para regra fora de `REGRAS`.

- [ ] **Step 1: Testes que falham**

```python
"""Sinalizadores na leitura: lista e detalhe pelo mesmo caminho, filtro que
pagina DEPOIS de filtrar, escopo por canal e nenhum efeito no score."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem
from tests.test_api import MotorFalso

T0 = datetime(2026, 10, 14, 9, 0, tzinfo=timezone.utc)


def _conv(cid, *falas, canal="chat"):
    return Conversa(id=cid, canal=canal, iniciada_em=T0, mensagens=[
        Mensagem(autor=a, texto=t, enviada_em=T0 + timedelta(minutes=k))
        for k, (a, t) in enumerate(falas)])


def abandonada(cid, canal="chat"):
    return _conv(cid, ("cliente", "meu boleto venceu"), ("bot", "gerei um novo boleto"), canal=canal)


def fechada(cid):
    return _conv(cid, ("cliente", "meu boleto venceu"), ("bot", "gerei um novo boleto"),
                 ("cliente", "valeu"))


def sem_cliente(cid):
    return _conv(cid, ("bot", "ola, posso ajudar?"))


@pytest.fixture
def banco(tmp_path):
    b = Banco(tmp_path / "fraus.db")
    b.migrar()
    return b


@pytest.fixture
def cliente(banco, tmp_path):
    return TestClient(criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path))


def test_lista_e_detalhe_trazem_os_mesmos_sinalizadores(cliente, banco):
    banco.salvar(abandonada("a"), 40.0, "detrator")
    linha = cliente.get("/conversas").json()[0]
    detalhe = cliente.get("/conversas/a").json()
    assert [s["regra"] for s in linha["sinalizadores"]] == ["abandono"]
    assert detalhe["sinalizadores"] == linha["sinalizadores"]


def test_sem_fala_do_cliente_e_null_e_nao_lista(cliente, banco):
    banco.salvar(sem_cliente("s"), None, None)
    assert cliente.get("/conversas").json()[0]["sinalizadores"] is None


def test_filtro_por_regra(cliente, banco):
    banco.salvar(abandonada("a"), 40.0, "detrator")
    banco.salvar(fechada("f"), 80.0, "neutro")
    banco.salvar(sem_cliente("s"), None, None)
    ids = [l["id"] for l in cliente.get("/conversas?sinalizador=abandono").json()]
    assert ids == ["a"]


def test_filtro_pagina_depois_de_filtrar(cliente, banco):
    for cid in ("f1", "a1", "f2", "a2", "f3"):
        banco.salvar(abandonada(cid) if cid.startswith("a") else fechada(cid), 50.0, "detrator")
    todas = [l["id"] for l in cliente.get("/conversas?sinalizador=abandono").json()]
    assert sorted(todas) == ["a1", "a2"]
    pagina2 = cliente.get("/conversas?sinalizador=abandono&limite=1&deslocamento=1").json()
    assert [l["id"] for l in pagina2] == todas[1:2]


def test_regra_desconhecida_e_400(cliente):
    r = cliente.get("/conversas?sinalizador=nota_do_atendente")
    assert r.status_code == 400
    assert "abandono" in r.json()["detail"]


def test_score_e_categoria_intactos(cliente, banco):
    banco.salvar(abandonada("a"), 40.0, "detrator")
    antes = cliente.get("/conversas").json()[0]
    cliente.get("/conversas?sinalizador=abandono")
    depois = cliente.get("/conversas").json()[0]
    assert (antes["score"], antes["nota"], antes["categoria"]) == (
        depois["score"], depois["nota"], depois["categoria"])
    assert depois["score"] == 40.0


def test_filtro_nao_vaza_canal_fora_do_escopo(tmp_path):
    banco = Banco(tmp_path / "e.db")
    banco.migrar()
    banco.salvar(abandonada("a", canal="chat"), 40.0, "detrator")
    banco.salvar(abandonada("b", canal="email"), 40.0, "detrator")
    app = criar_app(banco, MotorFalso(), raiz_importacao=tmp_path,
                    chave_mestra="chave-teste-operacao",
                    jwt_segredo="segredo-jwt-de-teste-operacao-123456",
                    codigo_dev="convite-dev-teste")
    cli = TestClient(app)
    headers, ids = {}, {}
    for papel in ("dev", "usuario"):
        cad = {"nome": papel, "email": f"{papel}@empresa.com", "senha": "senha-teste-longa-123"}
        if papel == "dev":
            cad["codigo_dev"] = "convite-dev-teste"
        ids[papel] = cli.post("/auth/registrar", json=cad).json()["id"]
        token = cli.post("/auth/entrar", json={"email": cad["email"], "senha": cad["senha"]}).json()["token"]
        headers[papel] = {"Authorization": "Bearer " + token}
    assert cli.put(f"/operacao/acesso/{ids['usuario']}", headers=headers["dev"],
                   json={"canais": ["chat"]}).status_code == 200
    vistos = [l["id"] for l in cli.get("/conversas?sinalizador=abandono", headers=headers["usuario"]).json()]
    assert vistos == ["a"]
```

> Se `banco.salvar` recusar `categoria=None` para a conversa sem cliente, use a mesma assinatura que `tests/test_api.py` usa para gravar conversa sem sinal. O teste é sobre `sinalizadores is None`, não sobre a gravação.

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_api_sinalizadores.py -q`
Expected: FAIL, com `KeyError: 'sinalizadores'` e o 400 recebendo 200.

- [ ] **Step 3: Implementação**

Em `fraus/api/rotas/conversas.py`, importe `from fraus.sinalizadores import REGRAS, sinalizadores` junto do import de `contestacao`.

Em `_com_derivacoes`, acrescente a chave logo depois de `"contestacao"` e uma frase na docstring: "Os `sinalizadores` (E5) seguem a mesma regra: derivados da conversa, nada gravado".

```python
        "contestacao": contestacao(score, ficha["latencia_mediana_s"]),
        "sinalizadores": sinalizadores(conversa),
        "motivo_sem_sinal": conversa.motivo_sem_sinal,
```

Em `listar`, acrescente o parâmetro `sinalizador: str | None = None` (antes de `ctx`), documente-o na docstring e troque o `return` por:

```python
    if sinalizador is not None and sinalizador not in REGRAS:
        raise HTTPException(
            status_code=400,
            detail="sinalizador desconhecido; use um de: " + ", ".join(REGRAS),
        )
    faixas = ctx.faixas_vigentes()
    de_iso = inicio.isoformat() if inicio else None
    ate_iso = fim.isoformat() if fim else None
    if sinalizador is None:
        return [
            _com_derivacoes(linha["score"], ctx.categoria_de(linha["score"], faixas), linha, conversa)
            for linha, conversa in ctx.banco.listar_com_conversa(
                de=de_iso, ate=ate_iso, limite=limite, deslocamento=deslocamento,
            )
        ]
    # O sinalizador e DERIVADO NA LEITURA: nao ha coluna para o banco filtrar.
    # Pagina DEPOIS de filtrar -- paginar antes faria a pagina 2 pular
    # conversas sinalizadas que cairam na pagina 1 do banco inteiro.
    fichas = [
        _com_derivacoes(linha["score"], ctx.categoria_de(linha["score"], faixas), linha, conversa)
        for linha, conversa in ctx.banco.listar_com_conversa(de=de_iso, ate=ate_iso)
    ]
    marcadas = [
        f for f in fichas
        if f["sinalizadores"] and any(s["regra"] == sinalizador for s in f["sinalizadores"])
    ]
    return marcadas[deslocamento:deslocamento + limite if limite is not None else None]
```

Mantenha a validação de `limite` e `deslocamento` que já existe antes deste bloco.

- [ ] **Step 4: Rodar e ver passar, com a suíte das rotas vizinhas**

Run: `uv run pytest tests/test_api_sinalizadores.py tests/test_api_contestacao.py tests/test_paginacao_conversas.py tests/test_api.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fraus/api/rotas/conversas.py tests/test_api_sinalizadores.py
git commit -m "feat(sinalizadores): campo na leitura e filtro que pagina depois de filtrar"
```

---

### Tarefa 3: tela — lista de achados e marca na transcrição

**Files:**
- Modify: `dashboard/lib/api.ts`, que ganha o tipo `Sinalizador` e o campo `sinalizadores` em `ResumoConversa`, ao lado de `contestacao`.
- Create: `dashboard/components/Sinalizadores.tsx`
- Create: `dashboard/components/Sinalizadores.test.tsx`
- Modify: `dashboard/components/Transcricao.tsx` (prop opcional `sinalizadores`)
- Modify: `dashboard/app/dashboard/atendimentos/[id]/page.tsx` (renderiza `<Sinalizadores>` dentro do painel Transcrição, antes de `<Transcricao>`, e passa a prop)
- Test (Python, fronteira): `tests/test_sinalizadores_atravessa_a_fronteira.py`

**Interfaces:**
- Consumes: chave `sinalizadores` da API (Tarefa 2); `REGRAS` (Tarefa 1).
- Produces: `ROTULO_SINALIZADOR: Record<RegraSinalizador, string>` e o componente `Sinalizadores({ sinalizadores })`.

- [ ] **Step 1: Testes que falham**

`dashboard/components/Sinalizadores.test.tsx`:

```tsx
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Sinalizadores } from "./Sinalizadores";
import type { Sinalizador } from "@/lib/api";

const loop: Sinalizador = {
  regra: "loop_do_bot",
  evidencia: [1, 3],
  detalhe: "2 respostas do bot quase idênticas, com fala do cliente entre elas (Jaccard ≥ 0,85; limiar sem procedência)",
};

const html = (s: Sinalizador[] | null) =>
  renderToStaticMarkup(<Sinalizadores sinalizadores={s} />);

describe("Sinalizadores", () => {
  it("null é não avaliado, não 'nada disparou'", () => {
    const m = html(null);
    expect(m).toContain("não avaliados");
    expect(m).toContain("sem fala do cliente");
    expect(m).not.toContain("Nenhum sinalizador");
  });

  it("lista vazia diz que nada disparou", () => {
    expect(html([])).toContain("Nenhum sinalizador disparou");
  });

  it("achado mostra o rótulo, o detalhe do servidor e as mensagens", () => {
    const m = html([loop]);
    expect(m).toContain("Loop do bot");
    expect(m).toContain(loop.detalhe);
    expect(m).toContain("mensagens 2 e 4");
    expect(m).toContain("não avalia o atendente");
  });
});
```

`tests/test_sinalizadores_atravessa_a_fronteira.py`:

```python
"""O contrato dos sinalizadores tem duas metades; esta e a guarda barata.

Mesmo padrao de tests/test_contestacao_atravessa_a_fronteira.py: le .ts/.tsx
como TEXTO. Nao e typecheck -- impede o silencio.
"""

import pathlib
import re

from fraus.sinalizadores import REGRAS

RAIZ = pathlib.Path(__file__).parent.parent
API_TS = (RAIZ / "dashboard" / "lib" / "api.ts").read_text(encoding="utf-8")
TSX = (RAIZ / "dashboard" / "components" / "Sinalizadores.tsx").read_text(encoding="utf-8")


def test_o_tipo_declara_as_chaves_do_servidor():
    bloco = re.search(r"export type Sinalizador = \{(.*?)\n\};", API_TS, re.S)
    assert bloco is not None
    assert set(re.findall(r"^\s*(\w+):", bloco.group(1), re.M)) == {"regra", "evidencia", "detalhe"}


def test_as_regras_do_tipo_sao_as_do_servidor():
    bloco = re.search(r"export type RegraSinalizador =(.*?);", API_TS, re.S)
    assert bloco is not None
    assert tuple(re.findall(r'"(\w+)"', bloco.group(1))) == REGRAS


def test_o_rotulo_cobre_toda_regra():
    for regra in REGRAS:
        assert re.search(rf"\b{regra}:", TSX), regra


def test_a_tela_nao_redigita_limiar():
    for limiar in ("0,85", "0.85", "0,7", "0.7"):
        assert limiar not in TSX
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd dashboard && npx vitest run components/Sinalizadores.test.tsx` e `uv run pytest tests/test_sinalizadores_atravessa_a_fronteira.py -q`
Expected: FAIL, porque o módulo e o tipo não existem.

- [ ] **Step 3: Implementação**

Em `dashboard/lib/api.ts`, logo depois do tipo `Contestacao`:

```ts
/**
 * Regras do E5, na ordem de `fraus.sinalizadores.REGRAS`. Derivadas na leitura;
 * o limiar vem escrito em `detalhe` pelo servidor e a tela nunca o redigita.
 */
export type RegraSinalizador =
  | "loop_do_bot"
  | "cliente_repete"
  | "pedido_de_humano_ignorado"
  | "escalada_tardia"
  | "abandono";

export type Sinalizador = {
  regra: RegraSinalizador;
  /** Índices (base 0) das mensagens que dispararam a regra. Nunca fala humana. */
  evidencia: number[];
  detalhe: string;
};
```

Em `ResumoConversa`, depois de `contestacao`:

```ts
  /**
   * Sinalizadores por regra (E5). `null` = não avaliado (sem fala do cliente),
   * diferente de `[]` = nada disparou.
   */
  sinalizadores: Sinalizador[] | null;
```

Procure com `grep -rn "contestacao: null" dashboard` os fixtures de teste que montam `ResumoConversa`/`DetalheConversa` e acrescente `sinalizadores: null` em cada um, para o `tsc` seguir limpo.

`dashboard/components/Sinalizadores.tsx`:

```tsx
import type { RegraSinalizador, Sinalizador } from "@/lib/api";

/**
 * Sinalizadores por regra (E5): o que disparou nesta conversa, com o detalhe
 * escrito pelo servidor (que traz o limiar). Marca e informa, não corrige: a
 * nota continua a mesma e o atendimento continua no NPS.
 *
 * `null` é NÃO AVALIADO (sem fala do cliente) e tem frase própria; `[]` é
 * "nada disparou". Confundir os dois faria ausência de dado parecer conversa
 * limpa (invariante 2).
 *
 * Sem estado e sem efeito: sai inteiro do markup do servidor, como a
 * `MarcaContestacao`.
 */
export const ROTULO_SINALIZADOR: Record<RegraSinalizador, string> = {
  loop_do_bot: "Loop do bot",
  cliente_repete: "Cliente repete",
  pedido_de_humano_ignorado: "Pedido de humano ignorado",
  escalada_tardia: "Escalada tardia",
  abandono: "Abandono",
};

function listaDeMensagens(evidencia: number[]): string {
  const n = evidencia.map((i) => String(i + 1));
  if (n.length === 1) return `mensagem ${n[0]}`;
  return `mensagens ${n.slice(0, -1).join(", ")} e ${n[n.length - 1]}`;
}

export function Sinalizadores({ sinalizadores }: { sinalizadores: Sinalizador[] | null }) {
  if (sinalizadores === null) {
    return (
      <p className="border-b border-border px-3 py-2.5 text-xs text-muted-foreground sm:px-5">
        Sinalizadores não avaliados: sem fala do cliente.
      </p>
    );
  }
  if (sinalizadores.length === 0) {
    return (
      <p className="border-b border-border px-3 py-2.5 text-xs text-muted-foreground sm:px-5">
        Nenhum sinalizador disparou.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-1.5 border-b border-border px-3 py-2.5 sm:px-5">
      <ul className="flex flex-col gap-1">
        {sinalizadores.map((s) => (
          <li key={s.regra} className="text-xs">
            <span className="inline-flex items-baseline gap-1.5 font-medium text-warning-rich-text">
              <span aria-hidden>⚑</span>
              {ROTULO_SINALIZADOR[s.regra]}
            </span>{" "}
            <span className="text-muted-foreground">
              — {s.detalhe} · {listaDeMensagens(s.evidencia)}
            </span>
          </li>
        ))}
      </ul>
      <p className="text-[0.6875rem] text-muted-foreground">
        Regras de superfície sobre falas do cliente, do bot e contagens. Não avalia
        o atendente e não muda a nota.
      </p>
    </div>
  );
}
```

Em `Transcricao.tsx`, acrescente a prop opcional
`sinalizadores?: Sinalizador[] | null` e, dentro do `map`, calcule
`const regrasAqui = (sinalizadores ?? []).filter((s) => s.evidencia.includes(indice));`.
Quando `regrasAqui.length > 0`, renderize logo após o `<span>` do horário, no
mesmo `div` do cabeçalho da mensagem:

```tsx
                {regrasAqui.length > 0 ? (
                  <span className="text-[0.6875rem] text-warning-rich-text">
                    <span aria-hidden>⚑ </span>
                    {regrasAqui.map((s) => ROTULO_SINALIZADOR[s.regra]).join(" · ")}
                  </span>
                ) : null}
```

Importe `ROTULO_SINALIZADOR` de `./Sinalizadores` e o tipo `Sinalizador` de `@/lib/api`.

Na página `app/dashboard/atendimentos/[id]/page.tsx`, dentro do `<Painel titulo="Transcrição">` e antes de `<Transcricao>`, renderize
`<Sinalizadores sinalizadores={conversa.sinalizadores ?? null} />` e passe
`sinalizadores={conversa.sinalizadores ?? null}` para `<Transcricao>`. O `?? null` protege contra uma API antiga, sem o campo: ela cai em "não avaliados", nunca em "nada disparou". Acrescente à `legenda` do painel uma frase: "O sinal ⚑ marca a mensagem que disparou um sinalizador por regra."

- [ ] **Step 4: Rodar e ver passar**

Run: `cd dashboard && npx vitest run && npx tsc --noEmit` e `uv run pytest tests/test_sinalizadores_atravessa_a_fronteira.py -q`
Expected: tudo PASS, e `tsc` sem saída. Se `npm`/`vitest` regenerar `dashboard/AGENTS.md`, restaure com `git checkout dashboard/AGENTS.md`.

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/api.ts dashboard/components/Sinalizadores.tsx dashboard/components/Sinalizadores.test.tsx dashboard/components/Transcricao.tsx "dashboard/app/dashboard/atendimentos/[id]/page.tsx" tests/test_sinalizadores_atravessa_a_fronteira.py
# mais os fixtures de teste que ganharam `sinalizadores: null`
git commit -m "feat(dashboard): sinalizadores por regra na transcricao"
```

---

### Tarefa 4: medição, casos construídos e documentação

**Files:**
- Create: `fraus/dados/casos_sinalizadores.py`
- Create: `scripts/medir_sinalizadores.py`
- Test: `tests/test_medir_sinalizadores.py`
- Modify: `docs/limitacoes.md`, `docs/arquitetura.md`, `CLAUDE.md` (linha no mapa de arquivos), `docs/superpowers/specs/2026-10-14-e5-sinalizadores-design.md` (seção "Desvios aceitos", a partir das "Decisões do plano" deste arquivo).

**Interfaces:**
- Consumes: `sinalizadores`, `REGRAS`; `fraus.api.rotas.confianca.wilson(sucessos, n) -> (inf, sup)`; `fraus.ingest.simulador.gerar_lote(frases_por_rotulo, quantidade, semente)`.
- Produces:
  - `CASOS: list[tuple[str, str, Conversa, bool]]`, com `(regra, tipo, conversa, deve_disparar)` e `tipo ∈ {"positivo", "negativo", "borda"}`. São 3 por regra, 15 no total.
  - `medir(casos) -> dict[str, dict]`: por regra, `vp`, `fp`, `fn`, `precisao`, `recall` e `ic_precisao`/`ic_recall` (Wilson; `None` quando o denominador é 0, nunca 0).
  - CLI: `python scripts/medir_sinalizadores.py [--anotada ARQ.jsonl] [--simulador N]`.

- [ ] **Step 1: Testes que falham**

```python
from fraus.dados.casos_sinalizadores import CASOS
from fraus.sinalizadores import REGRAS, sinalizadores
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "medir_sinalizadores", Path(__file__).parent.parent / "scripts" / "medir_sinalizadores.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
carregar_anotada, medir, principal = _mod.carregar_anotada, _mod.medir, _mod.principal


def test_tres_casos_por_regra_um_de_cada_tipo():
    for regra in REGRAS:
        tipos = sorted(t for r, t, _, _ in CASOS if r == regra)
        assert tipos == ["borda", "negativo", "positivo"], regra


def test_cada_caso_construido_se_comporta_como_declarado():
    for regra, tipo, conversa, deve in CASOS:
        disparou = regra in [s["regra"] for s in sinalizadores(conversa) or []]
        assert disparou == deve, (regra, tipo)


def test_medir_denominador_zero_e_none_e_nao_zero():
    res = medir([(r, t, c, d) for r, t, c, d in CASOS if not d])
    assert res["loop_do_bot"]["precisao"] is None
    assert res["loop_do_bot"]["ic_precisao"] is None


def test_medir_nos_casos_construidos():
    res = medir(CASOS)
    for regra in REGRAS:
        assert res[regra]["fn"] == 0 and res[regra]["fp"] == 0


def test_saida_declara_o_que_mede_e_o_que_falta(capsys):
    principal([])
    saida = capsys.readouterr().out
    assert "verifica a implementação, não mede qualidade" in saida
    assert "não verificado" in saida and "fonte pendente" in saida


def test_anotada_le_jsonl(tmp_path):
    import json
    from fraus.dados.casos_sinalizadores import CASOS as C
    conversa = C[0][2]
    arq = tmp_path / "a.jsonl"
    arq.write_text(json.dumps({"conversa": conversa.model_dump(mode="json"),
                               "esperadas": ["loop_do_bot"], "anotador": "teste"}) + "\n")
    casos, anotadores = carregar_anotada(arq)
    assert anotadores == {"teste"}
    assert {(r, d) for r, _, _, d in casos if r == "loop_do_bot"} == {("loop_do_bot", True)}
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_medir_sinalizadores.py -q`
Expected: FAIL, com `ModuleNotFoundError`.

- [ ] **Step 3: Implementação**

`fraus/dados/casos_sinalizadores.py`: escreva os 15 casos reaproveitando **as mesmas conversas** dos testes da Tarefa 1 (positivo, negativo e borda de cada regra). Use um helper `_conv(*falas)` idêntico ao `conv` dos testes, com `T0 = datetime(2026, 10, 14, 9, 0, tzinfo=timezone.utc)`. A docstring diz que os casos são **escritos à mão, rotulados como construídos**, e que o simulador não gera loop de bot. Para `abandono`, a borda é uma conversa cuja última fala é `humano` (dispara, porque `humano` é respondente, e a evidência aponta a última fala do cliente). A lista segue a ordem de `REGRAS`, com o positivo primeiro em cada regra: `CASOS[0]` é o positivo de `loop_do_bot`.

`scripts/medir_sinalizadores.py`:

```python
"""Instrumento do E5: precisao e recall por regra, com IC de Wilson.

Tres fontes, sempre reportadas separadas:
- casos construidos (fraus/dados/casos_sinalizadores.py): verificam a
  implementacao, NAO medem qualidade -- foram escritos para disparar;
- amostra anotada (--anotada): a unica que mede. Sem ela, "nao verificado";
- simulador (--simulador N): so a taxa de disparo, porque nao ha rotulo de regra.

Nao grava nada. Uso: uv run python scripts/medir_sinalizadores.py [--anotada a.jsonl] [--simulador 600]
"""

import argparse
import json
import sys
from pathlib import Path

from fraus.api.rotas.confianca import wilson
from fraus.dados.casos_sinalizadores import CASOS
from fraus.modelos import Conversa
from fraus.sinalizadores import REGRAS, sinalizadores


def _disparou(regra, conversa):
    return regra in [s["regra"] for s in sinalizadores(conversa) or []]


def medir(casos):
    res = {}
    for regra in REGRAS:
        vp = fp = fn = 0
        for r, _tipo, conversa, deve in casos:
            if r != regra:
                continue
            d = _disparou(regra, conversa)
            vp += d and deve
            fp += d and not deve
            fn += (not d) and deve
        res[regra] = {
            "vp": vp, "fp": fp, "fn": fn,
            "precisao": vp / (vp + fp) if vp + fp else None,
            "recall": vp / (vp + fn) if vp + fn else None,
            "ic_precisao": wilson(vp, vp + fp) if vp + fp else None,
            "ic_recall": wilson(vp, vp + fn) if vp + fn else None,
        }
    return res


def carregar_anotada(caminho: Path):
    """JSONL: {"conversa": {...}, "esperadas": [regras], "anotador": "..."}.
    Cada linha vira um caso por regra: dispara se a regra esta em `esperadas`."""
    casos, anotadores = [], set()
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        item = json.loads(linha)
        conversa = Conversa.model_validate(item["conversa"])
        anotadores.add(item["anotador"])
        for regra in REGRAS:
            casos.append((regra, "anotada", conversa, regra in item["esperadas"]))
    return casos, anotadores


def _fmt(v):
    return "n/d" if v is None else f"{v:.2f}"


def _fmt_ic(ic):
    return "n/d" if ic is None else f"[{ic[0]:.2f}, {ic[1]:.2f}]"


def _tabela(res):
    print(f"{'regra':28} {'vp':>3} {'fp':>3} {'fn':>3}  precisão (IC 95%)        recall (IC 95%)")
    for regra, r in res.items():
        print(f"{regra:28} {r['vp']:>3} {r['fp']:>3} {r['fn']:>3}  "
              f"{_fmt(r['precisao'])} {_fmt_ic(r['ic_precisao']):16}  "
              f"{_fmt(r['recall'])} {_fmt_ic(r['ic_recall'])}")


def principal(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--anotada", type=Path)
    p.add_argument("--simulador", type=int, default=0)
    args = p.parse_args(argv)

    print(f"Casos construídos (n = {len(CASOS)}): verifica a implementação, não mede qualidade.")
    _tabela(medir(CASOS))
    print()
    if args.anotada is None:
        print("Amostra anotada: não verificado — fonte pendente (João). Rode com --anotada arquivo.jsonl.")
    else:
        casos, anotadores = carregar_anotada(args.anotada)
        n = len(casos) // len(REGRAS)
        print(f"Amostra anotada (n = {n} conversas; anotador(es): {', '.join(sorted(anotadores))}):")
        _tabela(medir(casos))
    if args.simulador:
        from fraus.ingest.simulador import gerar_lote
        frases = {0: ["pessimo atendimento"], 1: ["ok"], 2: ["otimo, resolveu"]}
        lote = [c for c, _ in gerar_lote(frases, args.simulador, semente=20261014)]
        print(f"\nSimulador (n = {len(lote)}, sem rótulo de regra — só taxa de disparo):")
        for regra in REGRAS:
            k = sum(_disparou(regra, c) for c in lote)
            print(f"  {regra:28} {k}/{len(lote)}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
```

O teste carrega o script por `importlib`, o mesmo padrão de `tests/test_scripts_confianca.py`.

Documentação:
- `docs/limitacoes.md`: seção "Sinalizadores por regra (E5)", com as três limitações do spec, o falso positivo de despedida no `abandono` e a frase "precisão e recall em dado real: não verificado — fonte da amostra anotada pendente".
- `docs/arquitetura.md`: uma linha no lugar onde a contestação aparece, dizendo que `sinalizadores` é derivado na leitura em `_com_derivacoes`.
- `CLAUDE.md`, no mapa de arquivos, depois da linha de `fraus/calibracao.py`: `| \`fraus/sinalizadores.py\` | cinco regras de risco derivadas na leitura; nunca lê texto nem relógio da fala humana |`.
- Spec do E5: o estado vira "aprovado em 14/10/2026" e entra a seção "Desvios aceitos", com as decisões 1 a 10 deste plano, uma linha cada.

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_medir_sinalizadores.py tests/test_sinalizadores.py tests/test_documentacao.py -q && uv run python scripts/medir_sinalizadores.py --simulador 60`
Expected: PASS, e a tabela impressa com "não verificado — fonte pendente".

- [ ] **Step 5: Commit**

```bash
git add fraus/dados/casos_sinalizadores.py scripts/medir_sinalizadores.py tests/test_medir_sinalizadores.py docs/limitacoes.md docs/arquitetura.md CLAUDE.md docs/superpowers/specs/2026-10-14-e5-sinalizadores-design.md
git commit -m "feat(sinalizadores): instrumento de medicao, casos construidos e docs do E5"
```
