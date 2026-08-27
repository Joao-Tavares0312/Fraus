# Webhook de integração — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer o tipo de fonte "Webhook" deixar de ser um rótulo: uma rota assinada por fonte que recebe atendimento de qualquer plataforma, com registro de toda entrega e uma tela mestre-detalhe que caiba nisso.

**Architecture:** Um módulo de assinatura puro (`fraus/assinatura.py`) no molde do `credencial.py` já existente; uma rota `POST /integracoes/webhook/{fonte_id}` que lê o corpo **cru** e confere HMAC antes de qualquer parse; o miolo de derivação extraído de `ingestao.py` para uma função compartilhada, para que as duas rotas de entrada não divirjam; uma tabela `entregas_webhook` com poda. No front, a tela `/integracoes` vira mestre-detalhe.

**Tech Stack:** Python 3.11 + FastAPI + SQLite (sem ORM), gerenciado por `uv`. Next.js 16 + shadcn/ui + Tailwind v4 no front. Nenhuma dependência nova — `hmac`, `hashlib`, `base64` e `secrets` são da biblioteca padrão.

**Spec:** `docs/superpowers/specs/2026-08-27-webhook-integracao-design.md`

## Global Constraints

- **Nenhuma dependência nova.** Toda a criptografia usada aqui é biblioteca padrão do Python.
- **Identificadores e docstrings em português SEM acento** (`entregas_webhook`, `confere_assinatura`). Texto de interface leva acento normal.
- **Commits em português, sem acento no assunto**, no formato `tipo(escopo): resumo`. Corpo em pt-BR explicando **por quê**. **Não assinar commits com Claude como co-autor.**
- **TDD sem exceção:** teste que falha primeiro, implementação mínima, teste verde, commit.
- **Invariante 3:** `score`, `nota` e `categoria` são derivados no servidor e nunca aceitos do corpo. O canal vem da **fonte cadastrada**.
- **Invariante 2:** ausência de dado nunca vira zero. Procure `?? 0` e `|| 0` antes de commitar no front.
- **Timestamps timezone-aware.** `datetime` naive é erro de validação.
- **O corpo da requisição nunca é persistido** — é PII de cliente real.
- Rodar `uv run pytest -q` ao fim de cada task; `cd dashboard && npx tsc --noEmit` nas tasks de front.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade | Task |
|---|---|---|
| `fraus/assinatura.py` | **criar** — gerar segredo, assinar e conferir no padrão Standard Webhooks. Puro, sem HTTP e sem banco. | 1 |
| `tests/test_assinatura.py` | **criar** — testes do módulo puro | 1 |
| `fraus/db.py` | **modificar** — tabela `entregas_webhook`, métodos de registro/leitura/poda | 2 |
| `tests/test_entregas.py` | **criar** — testes de persistência de entrega | 2 |
| `fraus/api/registro.py` | **criar** — `registrar_conversa`, o miolo compartilhado pelas duas rotas de entrada | 3 |
| `fraus/api/rotas/ingestao.py` | **modificar** — passa a chamar `registrar_conversa` | 3 |
| `fraus/api/rotas/webhook.py` | **criar** — a rota assinada e o porteiro de 8 passos | 4 |
| `fraus/api/seguranca.py:37` | **modificar** — `ISENTAS` ganha o prefixo da rota nova | 4 |
| `fraus/api/main.py` | **modificar** — registra o router novo | 4 |
| `tests/test_webhook.py` | **criar** — os testes do porteiro | 4, 5 |
| `fraus/api/rotas/integracoes.py` | **modificar** — rota do segredo, rota de entregas, ajuda do tipo | 6 |
| `dashboard/lib/api.ts` | **modificar** — tipos e funções da API nova | 7 |
| `dashboard/components/integracoes/PainelDaFonte.tsx` | **criar** — o detalhe de uma fonte | 8 |
| `dashboard/components/integracoes/ListaDeFontes.tsx` | **criar** — a coluna mestre | 8 |
| `dashboard/components/integracoes/Entregas.tsx` | **criar** — a lista de entregas | 8 |
| `dashboard/components/integracoes/ContratoDoWebhook.tsx` | **criar** — contrato copiável | 8 |
| `dashboard/app/integracoes/page.tsx` | **modificar** — layout mestre-detalhe | 8 |
| `dashboard/components/integracoes/Fontes.tsx` | **modificar** — perde a tabela, vira o formulário de cadastro | 8 |
| `README.md`, `docs/handoff.md` | **modificar** — documentar a integração | 9 |

---

### Task 1: O módulo de assinatura

**Files:**
- Create: `fraus/assinatura.py`
- Test: `tests/test_assinatura.py`

**Interfaces:**
- Consumes: nada. Módulo puro, sem HTTP e sem banco.
- Produces:
  - `PREFIXO = "whsec"`
  - `JANELA_SEGUNDOS = 300`
  - `gerar_segredo() -> str` — devolve `"whsec_<base64>"`
  - `chave_do_segredo(segredo: str) -> bytes` — levanta `ValueError` se malformado
  - `assinar(webhook_id: str, timestamp: str, corpo: bytes, segredo: str) -> str` — devolve `"v1,<base64>"`
  - `confere(webhook_id: str, timestamp: str, corpo: bytes, segredo: str, recebida: str) -> bool`
  - `dentro_da_janela(timestamp: str, agora: int) -> bool`

**Por que o segredo é `whsec_<base64>` e a chave HMAC é o base64 DECODIFICADO:** é o que a
especificação Standard Webhooks define. Usar a string inteira como chave seria
mais simples e mataria o único motivo de adotar o padrão — uma biblioteca de
prateleira do outro lado faria o decode, geraria outra assinatura, e nada
bateria.

- [ ] **Step 1: Escrever os testes que falham**

```python
# tests/test_assinatura.py
"""Assinatura de webhook no padrao Standard Webhooks.

Testes do modulo PURO: sem HTTP e sem banco. O porteiro da rota que usa isto
esta em tests/test_webhook.py.
"""

import base64

import pytest

from fraus import assinatura

CORPO = b'{"id":"atendimento-1","mensagens":[]}'


def test_segredo_gerado_tem_o_prefixo_e_e_base64_valido():
    segredo = assinatura.gerar_segredo()
    assert segredo.startswith("whsec_")
    # A chave HMAC e o base64 DECODIFICADO -- e o que a especificacao define,
    # e o que faz uma biblioteca de prateleira do outro lado bater com a gente.
    assert len(assinatura.chave_do_segredo(segredo)) == 32


def test_dois_segredos_nunca_sao_iguais():
    assert assinatura.gerar_segredo() != assinatura.gerar_segredo()


def test_assinatura_confere_contra_ela_mesma():
    segredo = assinatura.gerar_segredo()
    assinada = assinatura.assinar("msg_1", "1756300000", CORPO, segredo)
    assert assinada.startswith("v1,")
    assert assinatura.confere("msg_1", "1756300000", CORPO, segredo, assinada)


def test_corpo_alterado_em_um_byte_nao_confere():
    """O teste que prova que a conferencia e sobre os BYTES CRUS.

    E o unico que pega a regressao de deixar o FastAPI desserializar e a gente
    re-serializar para conferir: reordenar uma chave ou mudar um espaco muda a
    assinatura, e o defeito passaria despercebido em todo teste de corpo igual.
    """
    segredo = assinatura.gerar_segredo()
    assinada = assinatura.assinar("msg_1", "1756300000", CORPO, segredo)
    assert not assinatura.confere(
        "msg_1", "1756300000", CORPO + b" ", segredo, assinada
    )


@pytest.mark.parametrize("campo", ["id", "timestamp"])
def test_id_ou_timestamp_trocado_nao_confere(campo):
    """Os tres entram no payload assinado -- trocar qualquer um invalida."""
    segredo = assinatura.gerar_segredo()
    assinada = assinatura.assinar("msg_1", "1756300000", CORPO, segredo)
    outro_id = "msg_2" if campo == "id" else "msg_1"
    outro_ts = "1756399999" if campo == "timestamp" else "1756300000"
    assert not assinatura.confere(outro_id, outro_ts, CORPO, segredo, assinada)


def test_segredo_diferente_nao_confere():
    assinada = assinatura.assinar("msg_1", "1756300000", CORPO, assinatura.gerar_segredo())
    assert not assinatura.confere(
        "msg_1", "1756300000", CORPO, assinatura.gerar_segredo(), assinada
    )


@pytest.mark.parametrize("recebida", ["", "v1,", "lixo", "v2,QUJD", "QUJD"])
def test_assinatura_malformada_e_recusada_sem_levantar(recebida):
    """Recusa, nao excecao: entrada malformada vem da rede o tempo todo."""
    segredo = assinatura.gerar_segredo()
    assert not assinatura.confere("msg_1", "1756300000", CORPO, segredo, recebida)


def test_confere_aceita_uma_entre_varias_assinaturas_no_cabecalho():
    """Rotacao de segredo manda as duas assinaturas separadas por espaco.

    Recusar o cabecalho com mais de uma quebraria justamente a rotacao sem
    janela de indisponibilidade, que e o motivo de a especificacao permitir.
    """
    segredo = assinatura.gerar_segredo()
    valida = assinatura.assinar("msg_1", "1756300000", CORPO, segredo)
    assert assinatura.confere(
        "msg_1", "1756300000", CORPO, segredo, f"v1,QUJD {valida}"
    )


@pytest.mark.parametrize("segredo", ["", "whsec_", "sem-prefixo", "whsec_!!!nao-base64"])
def test_segredo_malformado_levanta_value_error(segredo):
    """Aqui LEVANTA, e a diferenca importa: segredo malformado e defeito da
    MAQUINA que hospeda (variavel mal preenchida), nao da requisicao. A rota
    traduz isso em 503, nunca em 401."""
    with pytest.raises(ValueError):
        assinatura.chave_do_segredo(segredo)


@pytest.mark.parametrize("timestamp,esperado", [
    ("1756300000", True),      # exatamente agora
    ("1756299800", True),      # 200s atras, dentro dos 300
    ("1756299699", False),     # 301s atras, fora
    ("1756300301", False),     # 301s no FUTURO, fora
    ("ontem", False),          # nao numerico
    ("", False),
])
def test_janela_de_replay_de_cinco_minutos(timestamp, esperado):
    """A janela vale para os DOIS lados. Relogio adiantado no remetente e um
    caso real; assinatura com timestamp futuro sem limite deixaria uma captura
    valida para sempre."""
    assert assinatura.dentro_da_janela(timestamp, agora=1756300000) is esperado
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `uv run pytest tests/test_assinatura.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'fraus.assinatura'`

- [ ] **Step 3: Implementar**

```python
# fraus/assinatura.py
"""Assinatura de webhook de ENTRADA, no padrao Standard Webhooks.

Irmao do `credencial.py`, e a diferenca entre os dois e a razao de este modulo
existir separado:

- a chave `frs_` so precisa ser CONFERIDA, entao o banco guarda o hash dela e o
  segredo em claro pode morrer no instante em que e mostrado;
- a assinatura de webhook precisa ser RECOMPUTADA, e para isso o servidor
  precisa do segredo em claro toda vez.

Por isso o segredo daqui nunca entra no banco: a fonte guarda o NOME de uma
variavel de ambiente, e o valor mora no ambiente da maquina onde a API roda.
O `fraus.db` continua sem levar credencial junto num backup vazado.

TRES DECISOES, e o motivo de cada uma:

1. **O padrao e o Standard Webhooks, nao um formato nosso.** Os cabecalhos sao
   `webhook-id`, `webhook-timestamp` e `webhook-signature`, e o que se assina e
   `{id}.{timestamp}.{corpo}`. Inventar um formato proprio custaria o mesmo
   trabalho e entregaria menos: com o padrao, quem integra usa biblioteca de
   prateleira em vez de ler a nossa documentacao.

2. **O segredo e `whsec_<base64>` e a chave HMAC e o base64 DECODIFICADO.**
   Usar a string inteira seria mais simples e mataria o unico motivo de adotar
   o padrao -- a biblioteca do outro lado faz o decode, geraria outra
   assinatura, e nada bateria.

3. **O corpo entra aqui como BYTES, nunca como str ou dict.** HMAC e
   byte-exato: desserializar e re-serializar para conferir muda a assinatura
   por reordenacao de chave ou por um espaco de diferenca. A assinatura do tipo
   e o que impede alguem de passar um dict sem perceber.
"""

import base64
import binascii
import hashlib
import hmac
import secrets

PREFIXO = "whsec"

# 32 bytes = 256 bits, o mesmo piso do `credencial.py`. Nao ha dicionario que
# chegue perto de um segredo sorteado desse tamanho.
BYTES_DO_SEGREDO = 32

# Cinco minutos, o valor que a especificacao sugere e que os provedores usam.
# Apertar mais transformaria relogio levemente dessincronizado em recusa; afrouxar
# alarga a janela em que uma captura da rede continua valendo.
JANELA_SEGUNDOS = 300

VERSAO = "v1"


def gerar_segredo() -> str:
    """Segredo novo, no formato que a especificacao define.

    NUNCA e persistido pelo Fraus: sai uma vez na resposta da rota, o operador
    poe na variavel de ambiente e a plataforma recebe a copia.
    """
    return f"{PREFIXO}_{base64.b64encode(secrets.token_bytes(BYTES_DO_SEGREDO)).decode()}"


def chave_do_segredo(segredo: str) -> bytes:
    """Os bytes da chave HMAC, decodificados do segredo.

    LEVANTA `ValueError` em vez de devolver `None`, e a diferenca importa:
    segredo malformado e defeito da maquina que hospeda -- alguem preencheu a
    variavel de ambiente errado. A rota traduz isso em 503 nomeando a variavel,
    nunca em 401: mandar quem integra depurar a propria requisicao por um
    problema que nao e dele custa horas de quem nao pode conserta-lo.
    """
    if not segredo or not segredo.startswith(f"{PREFIXO}_"):
        raise ValueError(f"segredo de webhook deve comecar com '{PREFIXO}_'")
    corpo = segredo[len(PREFIXO) + 1:]
    if not corpo:
        raise ValueError("segredo de webhook sem a parte codificada")
    try:
        # `validate=True` para que caractere fora do alfabeto base64 seja erro,
        # e nao um descarte silencioso que produziria uma chave curta e uma
        # recusa de assinatura sem explicacao.
        return base64.b64decode(corpo, validate=True)
    except (binascii.Error, ValueError) as erro:
        raise ValueError("segredo de webhook nao e base64 valido") from erro


def _conteudo_assinado(webhook_id: str, timestamp: str, corpo: bytes) -> bytes:
    """`{id}.{timestamp}.{corpo}` -- os tres, sempre, e nessa ordem.

    O id entra para que a assinatura pertenca AQUELE evento, e o timestamp para
    que ela expire. Assinar so o corpo deixaria uma captura da rede valida para
    sempre e reaproveitavel em qualquer evento.
    """
    return f"{webhook_id}.{timestamp}.".encode("utf-8") + corpo


def assinar(webhook_id: str, timestamp: str, corpo: bytes, segredo: str) -> str:
    """A assinatura no formato do cabecalho: `v1,<base64>`."""
    digesto = hmac.new(
        chave_do_segredo(segredo),
        _conteudo_assinado(webhook_id, timestamp, corpo),
        hashlib.sha256,
    ).digest()
    return f"{VERSAO},{base64.b64encode(digesto).decode()}"


def confere(
    webhook_id: str, timestamp: str, corpo: bytes, segredo: str, recebida: str
) -> bool:
    """Confere em TEMPO CONSTANTE, e aceita mais de uma assinatura no cabecalho.

    `==` vaza, pelo tempo, quantos bytes bateram -- suficiente para descobrir a
    assinatura byte a byte. `hmac.compare_digest` nao vaza.

    O cabecalho pode trazer VARIAS assinaturas separadas por espaco, e recusar
    isso quebraria justamente a rotacao de segredo sem janela de
    indisponibilidade, que e o motivo de a especificacao permitir. Basta uma
    bater. Todas sao comparadas mesmo depois de uma bater, para que o tempo de
    resposta nao conte QUAL delas era a boa.
    """
    if not recebida:
        return False
    esperada = assinar(webhook_id, timestamp, corpo, segredo)
    achou = False
    for candidata in recebida.split(" "):
        if hmac.compare_digest(candidata.strip(), esperada):
            achou = True
    return achou


def dentro_da_janela(timestamp: str, agora: int) -> bool:
    """Janela de +/- 5 min. Vale para os DOIS lados.

    Relogio adiantado no remetente e caso real, e aceitar timestamp futuro sem
    limite deixaria uma captura da rede valida para sempre -- que e exatamente
    o ataque que o timestamp existe para fechar.

    Timestamp nao numerico e recusa, nao excecao: ele vem da rede.
    """
    try:
        enviado = int(timestamp)
    except (TypeError, ValueError):
        return False
    return abs(agora - enviado) <= JANELA_SEGUNDOS
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `uv run pytest tests/test_assinatura.py -q`
Expected: PASS — 20 testes (os parametrizados contam separado)

- [ ] **Step 5: Commit**

```bash
git add fraus/assinatura.py tests/test_assinatura.py
git commit -m "feat(assinatura): o modulo que confere webhook sem guardar segredo no banco

Irmao do credencial.py, separado porque a propriedade e outra: a chave
frs_ so precisa ser CONFERIDA, entao o banco guarda o hash dela; a
assinatura de webhook precisa ser RECOMPUTADA, e para isso o servidor
precisa do segredo em claro toda vez. Por isso o segredo daqui nunca
entra no banco -- a fonte guarda o NOME de uma variavel de ambiente.

Segue o Standard Webhooks de verdade, inclusive o base64 decodificado
como chave HMAC. Usar a string inteira seria mais simples e mataria o
unico motivo de adotar o padrao: a biblioteca do outro lado faz o
decode e nada bateria.

O corpo entra tipado como bytes de proposito. HMAC e byte-exato, e
desserializar para conferir muda a assinatura por reordenacao de chave
-- defeito que nenhum teste de corpo igual pegaria."
```

---

### Task 2: A tabela de entregas

**Files:**
- Modify: `fraus/db.py` (bloco `ESQUEMA`, e métodos novos após `apagar_fonte`)
- Test: `tests/test_entregas.py`

**Interfaces:**
- Consumes: `Banco` de `fraus/db.py`
- Produces:
  - `VEREDITOS: tuple[str, ...]` em `fraus/db.py`
  - `Banco.registrar_entrega(fonte_id: int, webhook_id: str | None, veredito: str, recebida_em: str, motivo: str | None = None, conversa_id: str | None = None) -> None`
  - `Banco.listar_entregas(fonte_id: int) -> list[dict]` — mais recente primeiro
  - `Banco.entrega_ja_vista(fonte_id: int, webhook_id: str) -> bool`
  - `Banco.ENTREGAS_POR_FONTE = 200`

- [ ] **Step 1: Escrever os testes que falham**

```python
# tests/test_entregas.py
"""Registro de entrega de webhook: o antidoto para a falha silenciosa.

Sem esta tabela, um webhook recusado nao deixa rastro em lugar nenhum -- e
falha silenciosa e o modo de falha numero um dessa integracao.
"""

from fraus.db import VEREDITOS, Banco


def _banco(tmp_path) -> Banco:
    banco = Banco(tmp_path / "fraus.db")
    banco.criar_esquema()
    return banco


def _fonte(banco: Banco) -> int:
    return banco.criar_fonte(
        nome="Zendesk", canal="webchat", tipo="webhook",
        variavel_segredo="FRAUS_WEBHOOK_ZEN", criada_em="2026-08-27T10:00:00+00:00",
    )["id"]


def test_entrega_aceita_e_registrada_com_a_conversa_que_gerou(tmp_path):
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    banco.registrar_entrega(
        fonte_id=fonte_id, webhook_id="msg_1", veredito="aceita",
        recebida_em="2026-08-27T10:01:00+00:00", conversa_id="atendimento-1",
    )
    (entrega,) = banco.listar_entregas(fonte_id)
    assert entrega["veredito"] == "aceita"
    assert entrega["conversa_id"] == "atendimento-1"
    assert entrega["motivo"] is None


def test_entrega_recusada_carrega_o_motivo_e_nao_tem_conversa(tmp_path):
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    banco.registrar_entrega(
        fonte_id=fonte_id, webhook_id="msg_1", veredito="assinatura",
        recebida_em="2026-08-27T10:01:00+00:00", motivo="assinatura nao confere",
    )
    (entrega,) = banco.listar_entregas(fonte_id)
    assert entrega["motivo"] == "assinatura nao confere"
    # None, nunca "" nem 0: nao houve conversa, e isso e diferente de uma
    # conversa de id vazio (invariante 2).
    assert entrega["conversa_id"] is None


def test_entregas_saem_mais_recente_primeiro(tmp_path):
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    for minuto in ("01", "03", "02"):
        banco.registrar_entrega(
            fonte_id=fonte_id, webhook_id=f"msg_{minuto}", veredito="aceita",
            recebida_em=f"2026-08-27T10:{minuto}:00+00:00",
        )
    assert [e["webhook_id"] for e in banco.listar_entregas(fonte_id)] == [
        "msg_03", "msg_02", "msg_01",
    ]


def test_entregas_de_uma_fonte_nao_vazam_para_outra(tmp_path):
    banco = _banco(tmp_path)
    uma, outra = _fonte(banco), _fonte(banco)
    banco.registrar_entrega(
        fonte_id=uma, webhook_id="msg_1", veredito="aceita",
        recebida_em="2026-08-27T10:01:00+00:00",
    )
    assert banco.listar_entregas(outra) == []


def test_webhook_id_ja_visto_e_reconhecido_por_fonte(tmp_path):
    """O dedupe e POR FONTE: duas plataformas podem numerar eventos igual, e
    tratar o `msg_1` de uma como reentrega da outra descartaria atendimento."""
    banco = _banco(tmp_path)
    uma, outra = _fonte(banco), _fonte(banco)
    banco.registrar_entrega(
        fonte_id=uma, webhook_id="msg_1", veredito="aceita",
        recebida_em="2026-08-27T10:01:00+00:00",
    )
    assert banco.entrega_ja_vista(uma, "msg_1") is True
    assert banco.entrega_ja_vista(outra, "msg_1") is False
    assert banco.entrega_ja_vista(uma, "msg_2") is False


def test_poda_mantem_as_ultimas_e_descarta_as_mais_antigas(tmp_path):
    """Registrar recusa de assinatura e o que o operador precisa ver -- e e
    tambem como um atacante enche o SQLite. A poda e o que permite manter a
    primeira propriedade sem pagar a segunda."""
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    for numero in range(banco.ENTREGAS_POR_FONTE + 20):
        banco.registrar_entrega(
            fonte_id=fonte_id, webhook_id=f"msg_{numero:04d}", veredito="assinatura",
            recebida_em=f"2026-08-27T10:00:00+00:00",
        )
    entregas = banco.listar_entregas(fonte_id)
    assert len(entregas) == banco.ENTREGAS_POR_FONTE
    # As 20 primeiras cairam; a mais nova continua.
    assert entregas[0]["webhook_id"] == "msg_0219"
    assert banco.entrega_ja_vista(fonte_id, "msg_0000") is False


def test_a_poda_nao_toca_nas_entregas_de_outra_fonte(tmp_path):
    banco = _banco(tmp_path)
    barulhenta, quieta = _fonte(banco), _fonte(banco)
    banco.registrar_entrega(
        fonte_id=quieta, webhook_id="importante", veredito="aceita",
        recebida_em="2026-08-27T09:00:00+00:00",
    )
    for numero in range(banco.ENTREGAS_POR_FONTE + 20):
        banco.registrar_entrega(
            fonte_id=barulhenta, webhook_id=f"msg_{numero}", veredito="assinatura",
            recebida_em="2026-08-27T10:00:00+00:00",
        )
    assert len(banco.listar_entregas(quieta)) == 1


def test_apagar_a_fonte_leva_as_entregas_dela(tmp_path):
    """Ao contrario das CONVERSAS, que sobrevivem: entrega e registro
    operacional DA fonte, nao dado de atendimento medido. Sem isto, as linhas
    ficariam orfas apontando para um id que ninguem mais consegue consultar."""
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    banco.registrar_entrega(
        fonte_id=fonte_id, webhook_id="msg_1", veredito="aceita",
        recebida_em="2026-08-27T10:01:00+00:00",
    )
    banco.apagar_fonte(fonte_id)
    assert banco.listar_entregas(fonte_id) == []


def test_os_vereditos_possiveis_estao_declarados_num_lugar_so(tmp_path):
    """A tela pinta cada veredito de um jeito e a rota escolhe um deles. Uma
    segunda lista digitada em outro arquivo so ficaria errada no dia em que um
    veredito novo entrasse -- sem erro nenhum, so sumindo da vista."""
    assert VEREDITOS == (
        "aceita", "assinatura", "fora_da_janela", "duplicada",
        "corpo_invalido", "fonte_inativa", "sem_segredo",
    )
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `uv run pytest tests/test_entregas.py -q`
Expected: FAIL — `ImportError: cannot import name 'VEREDITOS' from 'fraus.db'`

- [ ] **Step 3: Implementar**

Em `fraus/db.py`, acrescentar ao final da string `ESQUEMA` (antes do `"""` de fechamento, depois do índice de `lexico_curado`):

```sql
-- Cada chamada de webhook, aceita ou recusada. Sem ela, um webhook recusado nao
-- deixa rastro em lugar nenhum -- e falha silenciosa e o modo de falha numero
-- um dessa integracao.
--
-- Guardar SO as recusas parece economico e quebra o diagnostico central: sem as
-- aceitas, "nao chegou nada" e "chegou e foi tudo recusado" viram a mesma tela
-- vazia.
--
-- O CORPO NUNCA ENTRA AQUI. Seria PII de cliente real parada em disco sem
-- proposito -- e o proposito de depurar e servido pelo veredito e pelo motivo.
--
-- `ON DELETE CASCADE` ao contrario das CONVERSAS, que sobrevivem a fonte:
-- entrega e registro operacional DA fonte, nao dado de atendimento medido.
CREATE TABLE IF NOT EXISTS entregas_webhook (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fonte_id INTEGER NOT NULL REFERENCES fontes_integracao(id) ON DELETE CASCADE,
    webhook_id TEXT,
    recebida_em TEXT NOT NULL,
    veredito TEXT NOT NULL,
    motivo TEXT,
    conversa_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_entregas_fonte ON entregas_webhook(fonte_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_entregas_dedupe ON entregas_webhook(fonte_id, webhook_id);
```

Acrescentar após a constante `ESQUEMA`, no nível do módulo:

```python
# Os vereditos possiveis de uma entrega, num lugar so. A tela pinta cada um de
# um jeito e a rota escolhe um deles; uma segunda lista digitada em outro
# arquivo so ficaria errada no dia em que um veredito novo entrasse -- sem erro
# nenhum, so sumindo da vista.
#
# `sem_segredo` e o unico que NAO e culpa de quem chamou: a variavel de ambiente
# da fonte sumiu do ambiente da API. Ele vira 503, nao 401.
VEREDITOS = (
    "aceita",
    "assinatura",
    "fora_da_janela",
    "duplicada",
    "corpo_invalido",
    "fonte_inativa",
    "sem_segredo",
)
```

Acrescentar os métodos à classe `Banco`, logo após `apagar_fonte`:

```python
    # Quantas entregas cada fonte guarda. Registrar recusa de assinatura e
    # exatamente o que o operador precisa ver -- alguem esta batendo com o
    # segredo errado -- e e tambem como um atacante enche o SQLite. A poda e o
    # que permite manter a primeira propriedade sem pagar a segunda.
    #
    # Ela e TAMBEM a memoria do dedupe (`entrega_ja_vista` consulta esta
    # tabela), entao uma fonte que receba 200 recusas seguidas esquece as
    # aceitas anteriores. O efeito pratico e limitado: `salvar` grava com
    # INSERT OR REPLACE pelo id da conversa, entao reprocessar nao duplica
    # atendimento, so o repontua. E por isso que a poda pode ser simples.
    ENTREGAS_POR_FONTE = 200

    def registrar_entrega(
        self,
        fonte_id: int,
        webhook_id: str | None,
        veredito: str,
        recebida_em: str,
        motivo: str | None = None,
        conversa_id: str | None = None,
    ) -> None:
        """Registra a tentativa e poda as antigas DAQUELA fonte, numa transacao.

        A poda anda junto com o insert de proposito: separada, ela dependeria de
        alguem lembrar de chama-la, e o dia em que ninguem lembrasse seria o dia
        em que a tabela cresce sem teto.
        """
        with self._conectar() as conexao:
            conexao.execute(
                "INSERT INTO entregas_webhook "
                "(fonte_id, webhook_id, recebida_em, veredito, motivo, conversa_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (fonte_id, webhook_id, recebida_em, veredito, motivo, conversa_id),
            )
            # O corte e por `id`, nao por `recebida_em`: o id e monotonico e
            # decidido aqui, e o horario vem de fora -- duas entregas do mesmo
            # segundo deixariam a ordem indefinida e a poda escolheria por sorte
            # qual das duas cai.
            conexao.execute(
                "DELETE FROM entregas_webhook WHERE fonte_id = ? AND id NOT IN ("
                "  SELECT id FROM entregas_webhook WHERE fonte_id = ? "
                "  ORDER BY id DESC LIMIT ?"
                ")",
                (fonte_id, fonte_id, self.ENTREGAS_POR_FONTE),
            )

    def listar_entregas(self, fonte_id: int) -> list[dict]:
        """Entregas da fonte, mais recente primeiro."""
        with self._conectar() as conexao:
            linhas = conexao.execute(
                "SELECT id, fonte_id, webhook_id, recebida_em, veredito, motivo, "
                "conversa_id FROM entregas_webhook WHERE fonte_id = ? ORDER BY id DESC",
                (fonte_id,),
            ).fetchall()
        return [dict(linha) for linha in linhas]

    def entrega_ja_vista(self, fonte_id: int, webhook_id: str) -> bool:
        """Se aquele evento ja passou por aqui. O dedupe e POR FONTE.

        Duas plataformas podem numerar eventos igual, e tratar o `msg_1` de uma
        como reentrega da outra descartaria atendimento em silencio.
        """
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT 1 FROM entregas_webhook WHERE fonte_id = ? AND webhook_id = ? "
                "LIMIT 1",
                (fonte_id, webhook_id),
            ).fetchone()
        return linha is not None
```

**Atenção — `ON DELETE CASCADE` não funciona sozinho no SQLite.** A chave
estrangeira é ignorada a menos que `PRAGMA foreign_keys = ON` seja ligado **por
conexão**. Acrescentar em `_conectar`, logo após o `row_factory`:

```python
        # SQLite ignora chave estrangeira por padrao, e o pragma vale por
        # CONEXAO -- ligar uma vez na criacao do esquema nao teria efeito
        # nenhum nas seguintes. Sem isto, o ON DELETE CASCADE de
        # `entregas_webhook` seria documentacao, nao comportamento: apagar a
        # fonte deixaria as entregas orfas apontando para um id que ninguem
        # mais consegue consultar.
        conexao.execute("PRAGMA foreign_keys = ON")
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `uv run pytest tests/test_entregas.py -q && uv run pytest -q`
Expected: `test_entregas.py` PASS; a suíte inteira continua verde (o pragma novo é a mudança de maior alcance desta task — se alguma coisa quebrar, é aqui).

- [ ] **Step 5: Commit**

```bash
git add fraus/db.py tests/test_entregas.py
git commit -m "feat(db): a tabela que faz webhook recusado deixar rastro

Sem ela, uma chamada de webhook que falha nao aparece em lugar nenhum, e
falha silenciosa e o modo de falha numero um dessa integracao. Guarda
toda tentativa, aceita e recusada: so as recusas fariam \"nao chegou
nada\" e \"chegou e foi tudo recusado\" virarem a mesma tela vazia.

O corpo da requisicao nunca entra -- seria PII de cliente real parada em
disco, e depurar se resolve com veredito e motivo.

Poda de 200 por fonte no mesmo insert: registrar recusa de assinatura e
o que o operador precisa ver, e e tambem como se enche um SQLite.

Liga PRAGMA foreign_keys por conexao, sem o qual o ON DELETE CASCADE
seria documentacao em vez de comportamento."
```

---

### Task 3: O miolo compartilhado pelas duas rotas de entrada

**Files:**
- Create: `fraus/api/registro.py`
- Modify: `fraus/api/rotas/ingestao.py`
- Test: a suíte de `tests/test_api.py` que já cobre `/ingestao` é a rede desta task — ela precisa continuar verde sem uma linha alterada.

**Interfaces:**
- Consumes: `Contexto` de `fraus/api/contexto.py`, `PedidoIngestao` de `fraus/api/esquemas.py`
- Produces: `registrar_conversa(ctx: Contexto, pedido: PedidoIngestao, fonte: dict) -> dict` — devolve `{"id", "canal", "score", "nota", "categoria", "fonte"}`. Levanta `HTTPException(400)` se o corpo não montar uma `Conversa` válida.

**Por que extrair:** duas cópias da regra de derivação divergem, e a invariante 3
do CLAUDE.md nasceu exatamente dessa divergência. Uma das duas envelheceria, e
seria a que ninguém olha.

**Esta task é refatoração pura: nenhum teste novo, nenhum comportamento novo.**
A prova de que deu certo é a suíte existente passar intocada.

- [ ] **Step 1: Rodar a suíte e anotar o verde de partida**

Run: `uv run pytest -q`
Expected: PASS. Anote o número de testes — ele não pode mudar nesta task.

- [ ] **Step 2: Criar o módulo compartilhado**

```python
# fraus/api/registro.py
"""O miolo das duas rotas de ENTRADA: montar, pontuar, derivar e gravar.

Existe para que `POST /ingestao` (chave de fonte) e
`POST /integracoes/webhook/{fonte_id}` (assinatura) nao mantenham duas copias
da mesma regra. Duas copias divergem, e a invariante 3 do projeto -- veredito
derivado no servidor, nunca aceito do cliente -- nasceu exatamente de uma
divergencia dessas. A que envelhece e sempre a que ninguem olha.
"""

from fastapi import HTTPException
from pydantic import ValidationError

from fraus.api.contexto import Contexto
from fraus.api.esquemas import PedidoIngestao
from fraus.indicadores import nota_0_10
from fraus.modelos import Conversa


def registrar_conversa(ctx: Contexto, pedido: PedidoIngestao, fonte: dict) -> dict:
    """Grava o atendimento e devolve o veredito DERIVADO.

    O CANAL e o da fonte cadastrada, nao o que veio no corpo: quem manda o dado
    nao escolhe em que canal ele e contabilizado, do mesmo jeito que nao escolhe
    a propria nota.
    """
    try:
        conversa = Conversa(
            id=pedido.id,
            canal=fonte["canal"],
            iniciada_em=pedido.mensagens[0].enviada_em,
            encerrada_em=pedido.encerrada_em,
            escalou_para_humano=pedido.escalou_para_humano,
            mensagens=sorted(pedido.mensagens, key=lambda m: m.enviada_em),
        )
    except ValidationError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro

    # UMA leitura de curadoria, e e a MESMA que grava a versao: reler abriria
    # janela para pontuar com um lexico e marcar com a versao de outro.
    curadoria = ctx.curadoria_vigente()
    score = ctx.motor.pontuar_conversa(conversa, curadoria)
    # UMA leitura de faixa por requisicao: derivar a categoria duas vezes abria
    # janela para a gravacao e a resposta lerem configuracoes diferentes, e as
    # duas precisam contar a mesma historia.
    categoria = ctx.categoria_de(score, ctx.faixas_vigentes())
    ctx.banco.salvar(conversa, score, categoria, lexico_versao=curadoria.versao)
    return {
        "id": conversa.id,
        "canal": conversa.canal,
        "score": score,
        "nota": nota_0_10(score) if score is not None else None,
        "categoria": categoria,
        "fonte": fonte["nome"],
    }
```

- [ ] **Step 3: Fazer `ingestao.py` chamar o módulo novo**

Substituir o corpo de `fraus/api/rotas/ingestao.py` inteiro por:

```python
"""POST /ingestao -- atendimento vindo de um sistema EXTERNO, pela rede.

E um dos dois caminhos de escrita que nao exigem acesso ao disco da maquina --
o outro e `POST /integracoes/webhook/{fonte_id}`, que autentica por ASSINATURA
em vez de chave. A importacao le arquivo de uma pasta local; estes dois aceitam
a conversa pela rede.

O que os dois fazem com a conversa depois de autenticada e o MESMO codigo
(`fraus/api/registro.py`), de proposito: o canal vem da fonte cadastrada e o
score e derivado no servidor, e duas copias dessa regra divergiriam.
"""

from fastapi import APIRouter, Depends, Header

from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoIngestao
from fraus.api.registro import registrar_conversa
from fraus.api.seguranca import chave_do_cabecalho, fonte_autorizada

router = APIRouter()


@router.post("/ingestao", status_code=201)
def ingerir(
    pedido: PedidoIngestao,
    authorization: str | None = Header(default=None),
    ctx: Contexto = Depends(obter_contexto),
) -> dict:
    """Recebe atendimento de um sistema EXTERNO, autenticado por chave de fonte.

    Fonte desativada recusa com 403 (dentro de `fonte_autorizada`) -- o
    interruptor da tela de Integracoes precisa de fato desligar alguma coisa.

    Score, nota e categoria sao derivados em `registrar_conversa`, como em toda
    entrada, e ignorados se vierem no corpo.
    """
    chave = chave_do_cabecalho(authorization)
    fonte = fonte_autorizada(ctx.banco, chave)
    return registrar_conversa(ctx, pedido, fonte)
```

- [ ] **Step 4: Rodar a suíte inteira — tem de passar sem nenhuma alteração de teste**

Run: `uv run pytest -q`
Expected: PASS, com **exatamente o mesmo número de testes** do Step 1. Se algum teste de `/ingestao` falhar, a extração mudou comportamento e precisa ser corrigida — não o teste.

- [ ] **Step 5: Commit**

```bash
git add fraus/api/registro.py fraus/api/rotas/ingestao.py
git commit -m "refactor(api): o miolo de derivacao sai da rota antes de ganhar um segundo dono

A rota de webhook vai precisar do mesmo trecho: montar a Conversa, ler a
curadoria uma vez, pontuar, derivar a categoria e gravar. Copiar seria o
caminho curto e as duas copias divergiriam -- a invariante 3 (veredito
derivado no servidor) nasceu exatamente de uma divergencia dessas, e a
copia que envelhece e sempre a que ninguem olha.

Refatoracao pura: a suite passa intocada, que e a prova pedida."
```

---

### Task 4: A rota do webhook

**Files:**
- Create: `fraus/api/rotas/webhook.py`
- Modify: `fraus/api/seguranca.py:37` (`ISENTAS`)
- Modify: `fraus/api/main.py` (registro do router)
- Test: `tests/test_webhook.py`

**Interfaces:**
- Consumes: `assinatura` (Task 1), `Banco.registrar_entrega` / `entrega_ja_vista` (Task 2), `registrar_conversa` (Task 3)
- Produces: `router` com `POST /integracoes/webhook/{fonte_id}`; `PREFIXO_WEBHOOK = "/integracoes/webhook"` exportado de `fraus/api/rotas/webhook.py` e consumido por `seguranca.py`

- [ ] **Step 1: Escrever os testes que falham**

```python
# tests/test_webhook.py
"""POST /integracoes/webhook/{fonte_id} -- o porteiro de oito passos.

A ordem e identidade, depois autoridade, depois parse: nada de desserializar
JSON, tocar no banco ou pontuar antes de a assinatura passar.
"""

import json

import pytest

from fraus import assinatura
from fraus.api.rotas.webhook import PREFIXO_WEBHOOK

# Reusa as fixtures de tests/test_api.py -- `cliente` monta o app com o motor
# duble. Um conftest proprio criaria um segundo app para manter em dia.
from tests.test_api import cliente  # noqa: F401

SEGREDO = "whsec_" + "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVphYmNkZWY="
VARIAVEL = "FRAUS_WEBHOOK_TESTE"

CORPO = {
    "id": "atendimento-1",
    "mensagens": [
        {"autor": "cliente", "texto": "meu pedido nao chegou",
         "enviada_em": "2026-08-27T10:00:00-03:00"},
        {"autor": "bot", "texto": "vou verificar",
         "enviada_em": "2026-08-27T10:00:12-03:00"},
    ],
}


@pytest.fixture
def fonte(cliente, monkeypatch):  # noqa: F811
    """Fonte de webhook com o segredo presente no ambiente da API."""
    monkeypatch.setenv(VARIAVEL, SEGREDO)
    return cliente.post("/integracoes/fontes", json={
        "nome": "Zendesk", "canal": "webchat", "tipo": "webhook",
        "variavel_segredo": VARIAVEL,
    }).json()


def _enviar(cliente, fonte_id, corpo=None, *, segredo=SEGREDO, webhook_id="msg_1",
            timestamp=None, agora=None, assinada=None):
    """Monta e envia uma chamada assinada. Serializa UMA vez e assina esses
    bytes exatos -- reserializar para assinar e o defeito que os testes caçam."""
    import time
    bruto = json.dumps(CORPO if corpo is None else corpo).encode("utf-8")
    ts = timestamp if timestamp is not None else str(int(agora or time.time()))
    return cliente.post(
        f"{PREFIXO_WEBHOOK}/{fonte_id}",
        content=bruto,
        headers={
            "content-type": "application/json",
            "webhook-id": webhook_id,
            "webhook-timestamp": ts,
            "webhook-signature": assinada if assinada is not None
                                 else assinatura.assinar(webhook_id, ts, bruto, segredo),
        },
    )


def _entregas(cliente, fonte_id):
    return cliente.get(f"/integracoes/fontes/{fonte_id}/entregas").json()


# --- o caminho feliz --------------------------------------------------------

def test_assinatura_valida_e_aceita_e_grava_a_conversa(cliente, fonte):  # noqa: F811
    resposta = _enviar(cliente, fonte["id"])
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["id"] == "atendimento-1"
    assert corpo["fonte"] == "Zendesk"
    assert [c["id"] for c in cliente.get("/conversas").json()] == ["atendimento-1"]


def test_o_canal_e_o_da_fonte_nunca_o_do_corpo(cliente, fonte):  # noqa: F811
    """Quem manda o dado nao escolhe em que canal ele e contabilizado."""
    _enviar(cliente, fonte["id"], corpo={**CORPO, "canal": "inventado"})
    assert cliente.get("/conversas").json()[0]["canal"] == "webchat"


@pytest.mark.parametrize("campo,valor", [
    ("score", 99.0), ("nota", 10), ("categoria", "promotor"),
])
def test_veredito_no_corpo_e_ignorado(cliente, fonte, campo, valor):  # noqa: F811
    """Invariante 3: score, nota e categoria sao derivados no SERVIDOR."""
    resposta = _enviar(cliente, fonte["id"], corpo={**CORPO, campo: valor})
    assert resposta.status_code == 201
    assert resposta.json()[campo] != valor


# --- o porteiro, um teste por passo -----------------------------------------

def test_fonte_inexistente_e_404(cliente, fonte):  # noqa: F811
    assert _enviar(cliente, 99999).status_code == 404


def test_variavel_ausente_no_ambiente_e_503_nomeando_a_variavel(
    cliente, fonte, monkeypatch,  # noqa: F811
):
    """503, nao 401: variavel ausente e defeito da MAQUINA que hospeda.

    Responder 401 mandaria quem integra caçar um problema que nao e dele --
    horas gastas por quem nem consegue conserta-lo."""
    monkeypatch.delenv(VARIAVEL, raising=False)
    resposta = _enviar(cliente, fonte["id"])
    assert resposta.status_code == 503
    assert VARIAVEL in resposta.json()["detail"]
    assert _entregas(cliente, fonte["id"])[0]["veredito"] == "sem_segredo"


def test_fonte_sem_variavel_nomeada_e_503(cliente):  # noqa: F811
    """Fonte de webhook sem variavel nomeada nao tem como conferir nada."""
    sem = cliente.post("/integracoes/fontes", json={
        "nome": "Solta", "canal": "webchat", "tipo": "webhook",
    }).json()
    assert _enviar(cliente, sem["id"]).status_code == 503


@pytest.mark.parametrize("faltando", ["webhook-id", "webhook-timestamp", "webhook-signature"])
def test_cabecalho_ausente_e_400(cliente, fonte, faltando):  # noqa: F811
    import time
    bruto = json.dumps(CORPO).encode("utf-8")
    ts = str(int(time.time()))
    cabecalhos = {
        "content-type": "application/json",
        "webhook-id": "msg_1",
        "webhook-timestamp": ts,
        "webhook-signature": assinatura.assinar("msg_1", ts, bruto, SEGREDO),
    }
    del cabecalhos[faltando]
    resposta = cliente.post(
        f"{PREFIXO_WEBHOOK}/{fonte['id']}", content=bruto, headers=cabecalhos
    )
    assert resposta.status_code == 400
    assert faltando in resposta.json()["detail"]


def test_timestamp_velho_e_400_e_nao_grava_conversa(cliente, fonte):  # noqa: F811
    import time
    resposta = _enviar(cliente, fonte["id"], agora=time.time() - 3600)
    assert resposta.status_code == 400
    assert cliente.get("/conversas").json() == []
    assert _entregas(cliente, fonte["id"])[0]["veredito"] == "fora_da_janela"


def test_timestamp_muito_no_futuro_e_400(cliente, fonte):  # noqa: F811
    """A janela vale para os dois lados: aceitar futuro sem limite deixaria
    uma captura da rede valida para sempre."""
    import time
    assert _enviar(cliente, fonte["id"], agora=time.time() + 3600).status_code == 400


def test_assinatura_errada_e_401_e_nao_grava_conversa(cliente, fonte):  # noqa: F811
    resposta = _enviar(cliente, fonte["id"], assinada="v1,QUJDREVG")
    assert resposta.status_code == 401
    assert cliente.get("/conversas").json() == []
    assert _entregas(cliente, fonte["id"])[0]["veredito"] == "assinatura"


def test_corpo_alterado_depois_de_assinado_e_401(cliente, fonte):  # noqa: F811
    """O teste central do modulo: prova que a conferencia e sobre os BYTES
    CRUS que chegaram, nao sobre o dict reserializado."""
    import time
    bruto = json.dumps(CORPO).encode("utf-8")
    ts = str(int(time.time()))
    assinada = assinatura.assinar("msg_1", ts, bruto, SEGREDO)
    resposta = cliente.post(
        f"{PREFIXO_WEBHOOK}/{fonte['id']}",
        content=bruto + b" ",  # um unico byte a mais
        headers={
            "content-type": "application/json", "webhook-id": "msg_1",
            "webhook-timestamp": ts, "webhook-signature": assinada,
        },
    )
    assert resposta.status_code == 401


def test_fonte_desativada_e_403_e_so_DEPOIS_da_assinatura(cliente, fonte):  # noqa: F811
    """403 depois da assinatura de proposito: informar que a fonte esta
    desativada a quem nao provou identidade conta a um desconhecido o estado
    interno do sistema."""
    cliente.patch(f"/integracoes/fontes/{fonte['id']}", json={"ativa": False})
    assert _enviar(cliente, fonte["id"]).status_code == 403
    # assinatura errada em fonte desativada responde 401, nao 403 -- a ordem
    # do porteiro e observavel daqui.
    assert _enviar(cliente, fonte["id"], assinada="v1,QUJD").status_code == 401


def test_reentrega_do_mesmo_webhook_id_e_200_e_nao_duplica(cliente, fonte):  # noqa: F811
    """200, NAO erro. O Standard Webhooks manda a plataforma retentar diante de
    qualquer resposta fora de 2xx -- responder erro a uma reentrega legitima
    poria a integracao em laco infinito por conta propria."""
    assert _enviar(cliente, fonte["id"], webhook_id="msg_1").status_code == 201
    repetida = _enviar(cliente, fonte["id"], webhook_id="msg_1")
    assert repetida.status_code == 200
    assert repetida.json()["duplicada"] is True
    assert len(cliente.get("/conversas").json()) == 1
    assert _entregas(cliente, fonte["id"])[0]["veredito"] == "duplicada"


def test_corpo_que_nao_bate_o_contrato_e_400(cliente, fonte):  # noqa: F811
    resposta = _enviar(cliente, fonte["id"], corpo={"id": "x", "mensagens": []})
    assert resposta.status_code == 400
    assert _entregas(cliente, fonte["id"])[0]["veredito"] == "corpo_invalido"


def test_corpo_que_nao_e_json_e_400_sem_explodir(cliente, fonte):  # noqa: F811
    import time
    ts = str(int(time.time()))
    bruto = b"isto nao e json"
    resposta = cliente.post(
        f"{PREFIXO_WEBHOOK}/{fonte['id']}", content=bruto,
        headers={
            "content-type": "application/json", "webhook-id": "msg_1",
            "webhook-timestamp": ts,
            "webhook-signature": assinatura.assinar("msg_1", ts, bruto, SEGREDO),
        },
    )
    assert resposta.status_code == 400


# --- o registro -------------------------------------------------------------

def test_entrega_aceita_aponta_a_conversa_que_gerou(cliente, fonte):  # noqa: F811
    _enviar(cliente, fonte["id"])
    (entrega,) = _entregas(cliente, fonte["id"])
    assert entrega["veredito"] == "aceita"
    assert entrega["conversa_id"] == "atendimento-1"


def test_o_corpo_da_requisicao_nao_aparece_em_entrega_nenhuma(cliente, fonte):  # noqa: F811
    """O corpo e PII de cliente real. Depurar se resolve com veredito e motivo."""
    _enviar(cliente, fonte["id"])
    assert "meu pedido nao chegou" not in cliente.get(
        f"/integracoes/fontes/{fonte['id']}/entregas"
    ).text


# --- a regressao que so apareceria em producao ------------------------------

def test_a_rota_responde_com_a_mestra_ligada_sem_exigir_chave_de_acesso(
    tmp_path, monkeypatch,
):
    """A regressao de ISENTAS, e ela e silenciosa.

    Com FRAUS_CHAVE_MESTRA definida, o middleware exige `Bearer fra_` em toda
    rota fora da lista. A plataforma externa nao tem -- nem pode ter -- uma
    chave de acesso: a credencial dela e a ASSINATURA. Sem a rota na lista,
    toda chamada levaria 401 antes de a assinatura ser olhada, e o log de
    entregas ficaria vazio dizendo "nao chegou nada" enquanto a plataforma
    recebe 401 em cada tentativa.
    """
    from fastapi.testclient import TestClient
    from tests.test_api import MotorDuble  # o duble ja usado pela suite
    from fraus.api.main import criar_app
    from fraus.db import Banco

    monkeypatch.setenv(VARIAVEL, SEGREDO)
    banco = Banco(tmp_path / "fraus.db")
    banco.criar_esquema()
    app = criar_app(banco=banco, motor=MotorDuble(), raiz=tmp_path,
                    chave_mestra="mestra-secreta")
    protegido = TestClient(app)

    fonte_criada = protegido.post(
        "/integracoes/fontes",
        json={"nome": "Zendesk", "canal": "webchat", "tipo": "webhook",
              "variavel_segredo": VARIAVEL},
        headers={"Authorization": "Bearer mestra-secreta"},
    ).json()

    # Sem Authorization nenhum -- so a assinatura.
    assert _enviar(protegido, fonte_criada["id"]).status_code == 201


def test_a_url_com_barra_final_tambem_passa_pelo_middleware(cliente, fonte):  # noqa: F811
    """Quem cadastra a URL do outro lado poe barra final o tempo todo, e o
    Starlette redireciona -- mas a lista ISENTAS compara o path."""
    import time
    bruto = json.dumps(CORPO).encode("utf-8")
    ts = str(int(time.time()))
    resposta = cliente.post(
        f"{PREFIXO_WEBHOOK}/{fonte['id']}/", content=bruto,
        headers={
            "content-type": "application/json", "webhook-id": "msg_1",
            "webhook-timestamp": ts,
            "webhook-signature": assinatura.assinar("msg_1", ts, bruto, SEGREDO),
        },
        follow_redirects=True,
    )
    assert resposta.status_code == 201
```

**Nota para quem implementa:** os testes acima importam `cliente` e `MotorDuble`
de `tests/test_api.py`. Confirme os nomes reais dessas fixtures antes de rodar
(`grep -n "def cliente\|class Motor" tests/test_api.py`) e ajuste o import — o
resto do teste não muda. Se `criar_app` não aceitar `chave_mestra` como
argumento nomeado, veja como `tests/test_autenticacao.py` monta o app protegido
e copie aquele caminho.

- [ ] **Step 2: Rodar e verificar que falha**

Run: `uv run pytest tests/test_webhook.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'fraus.api.rotas.webhook'`

- [ ] **Step 3: Implementar a rota**

```python
# fraus/api/rotas/webhook.py
"""POST /integracoes/webhook/{fonte_id} -- atendimento por webhook assinado.

O SEGUNDO caminho de escrita pela rede, ao lado de `POST /ingestao`. A
diferenca e a credencial: `/ingestao` pede uma chave `frs_` no cabecalho
Authorization, e isto aqui confere uma ASSINATURA sobre o corpo. As duas
existem porque plataforma nenhuma dispensa a segunda forma -- o padrao de
mercado e URL unica por endpoint com assinatura, nao header customizado.

O que as duas fazem depois de autenticar e o MESMO codigo
(`fraus/api/registro.py`): o canal vem da fonte e o veredito e derivado no
servidor.

A ORDEM DO PORTEIRO E IDENTIDADE, DEPOIS AUTORIDADE, DEPOIS PARSE. Nada de
desserializar JSON, tocar no banco ou pontuar antes de a assinatura passar --
e a regra que separa um receptor de webhook de uma porta aberta.
"""

import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import ValidationError

from fraus import assinatura
from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoIngestao
from fraus.api.registro import registrar_conversa

router = APIRouter()

# Exportado para `fraus/api/seguranca.py` montar a lista ISENTAS a partir daqui.
# Uma segunda copia da string la so ficaria errada no dia em que esta mudasse --
# e o efeito seria 401 em toda chamada de webhook, com o log de entregas vazio
# dizendo "nao chegou nada".
PREFIXO_WEBHOOK = "/integracoes/webhook"


class Recusa(Exception):
    """Recusa do porteiro: o status HTTP, o veredito registrado e o motivo.

    Excecao propria em vez de HTTPException direta porque TODA recusa precisa
    virar linha em `entregas_webhook` antes de virar resposta. Levantar
    HTTPException de dentro dos passos deixaria o registro na mao de quem
    lembrasse -- e a recusa que ninguem registra e exatamente a que o operador
    precisava ver.
    """

    def __init__(self, status: int, veredito: str, motivo: str) -> None:
        super().__init__(motivo)
        self.status = status
        self.veredito = veredito
        self.motivo = motivo


@router.post(PREFIXO_WEBHOOK + "/{fonte_id}")
async def receber(
    fonte_id: int,
    request: Request,
    webhook_id: str | None = Header(default=None, alias="webhook-id"),
    webhook_timestamp: str | None = Header(default=None, alias="webhook-timestamp"),
    webhook_signature: str | None = Header(default=None, alias="webhook-signature"),
    ctx: Contexto = Depends(obter_contexto),
):
    """Recebe atendimento assinado no padrao Standard Webhooks.

    O corpo e lido CRU, em bytes, e nao por um modelo Pydantic no parametro:
    HMAC e byte-exato, e deixar o FastAPI desserializar e a gente re-serializar
    para conferir muda a assinatura por reordenacao de chave ou por um espaco
    de diferenca. A validacao Pydantic acontece depois, sobre os MESMOS bytes,
    e so depois de a assinatura passar.
    """
    fonte = ctx.banco.buscar_fonte(fonte_id)
    if fonte is None:
        # Sem fonte nao ha de quem registrar a entrega -- e uma linha com
        # fonte_id invalido nao teria onde ser lida.
        raise HTTPException(status_code=404, detail="fonte nao encontrada")

    corpo = await request.body()
    recebida_em = datetime.now(timezone.utc).isoformat()

    def registrar(veredito: str, motivo: str | None = None,
                  conversa_id: str | None = None) -> None:
        ctx.banco.registrar_entrega(
            fonte_id=fonte_id, webhook_id=webhook_id, veredito=veredito,
            recebida_em=recebida_em, motivo=motivo, conversa_id=conversa_id,
        )

    try:
        resultado = _passar_pelo_porteiro(
            ctx, fonte, fonte_id, corpo,
            webhook_id, webhook_timestamp, webhook_signature,
        )
    except Recusa as recusa:
        registrar(recusa.veredito, recusa.motivo)
        raise HTTPException(status_code=recusa.status, detail=recusa.motivo) from recusa

    if resultado is None:
        # Passo 7: reentrega. 200, NAO erro -- o Standard Webhooks manda a
        # plataforma retentar diante de qualquer resposta fora de 2xx, e
        # responder erro a uma reentrega legitima poria a integracao em laco
        # infinito por conta propria.
        registrar("duplicada", "webhook-id ja processado")
        return {"duplicada": True, "webhook_id": webhook_id}

    registrar("aceita", conversa_id=resultado["id"])
    return JSONResponse(status_code=201, content=jsonable_encoder(resultado))


def _passar_pelo_porteiro(
    ctx: Contexto,
    fonte: dict,
    fonte_id: int,
    corpo: bytes,
    webhook_id: str | None,
    webhook_timestamp: str | None,
    webhook_signature: str | None,
) -> dict | None:
    """Os passos 2 a 8. Devolve o veredito, ou None se for reentrega.

    Levanta `Recusa` -- nunca HTTPException -- para que quem chamou registre a
    entrega antes de responder.
    """
    # Passo 2: o segredo. 503, nao 401: variavel ausente e defeito da MAQUINA
    # que hospeda, e o corpo nomeia a variavel porque quem opera precisa saber
    # qual. Responder 401 mandaria quem integra depurar a propria requisicao
    # por um problema que nao e dele.
    nome_da_variavel = fonte["variavel_segredo"]
    if not nome_da_variavel:
        raise Recusa(503, "sem_segredo", (
            f"a fonte '{fonte['nome']}' nao nomeia variavel de ambiente para o "
            "segredo do webhook -- cadastre o nome dela na tela de Integracoes"
        ))
    segredo = os.environ.get(nome_da_variavel)
    if not segredo:
        raise Recusa(503, "sem_segredo", (
            f"a variavel {nome_da_variavel} nao esta definida no ambiente da API"
        ))
    try:
        assinatura.chave_do_segredo(segredo)
    except ValueError as erro:
        raise Recusa(503, "sem_segredo", (
            f"a variavel {nome_da_variavel} nao carrega um segredo valido: {erro}"
        )) from erro

    # Passo 3: os tres cabecalhos. Nomeia QUAL falta -- "cabecalho ausente" sem
    # o nome manda o integrador conferir os tres.
    for nome, valor in (
        ("webhook-id", webhook_id),
        ("webhook-timestamp", webhook_timestamp),
        ("webhook-signature", webhook_signature),
    ):
        if not valor:
            raise Recusa(400, "corpo_invalido", f"cabecalho {nome} ausente")

    # Passo 4: a janela. Antes do HMAC de proposito -- e a checagem barata, e
    # rejeitar cedo e o que impede um corpo grande de custar computo.
    if not assinatura.dentro_da_janela(webhook_timestamp, agora=int(time.time())):
        raise Recusa(400, "fora_da_janela", (
            f"webhook-timestamp fora da janela de "
            f"{assinatura.JANELA_SEGUNDOS}s do relogio do servidor"
        ))

    # Passo 5: a assinatura.
    if not assinatura.confere(
        webhook_id, webhook_timestamp, corpo, segredo, webhook_signature
    ):
        raise Recusa(401, "assinatura", "assinatura nao confere")

    # Passo 6: a fonte ativa. DEPOIS da assinatura: informar que a fonte esta
    # desativada a quem nao provou identidade conta a um desconhecido o estado
    # interno do sistema.
    if not fonte["ativa"]:
        raise Recusa(403, "fonte_inativa", f"a fonte '{fonte['nome']}' esta desativada")

    # Passo 7: reentrega. Nao e recusa -- ver o comentario em `receber`.
    if ctx.banco.entrega_ja_vista(fonte_id, webhook_id):
        return None

    # Passo 8: so agora o corpo vira objeto.
    try:
        pedido = PedidoIngestao.model_validate_json(corpo)
    except ValidationError as erro:
        raise Recusa(400, "corpo_invalido", str(erro)) from erro

    try:
        return registrar_conversa(ctx, pedido, fonte)
    except HTTPException as erro:
        # `registrar_conversa` levanta 400 quando os campos nao montam uma
        # Conversa valida (timestamp naive, por exemplo). Vira Recusa para que
        # a entrega seja registrada como as outras.
        raise Recusa(erro.status_code, "corpo_invalido", str(erro.detail)) from erro
```

Acrescentar os dois imports que faltam no topo do arquivo:

```python
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
```

- [ ] **Step 4: Pôr a rota em `ISENTAS` e registrar o router**

Em `fraus/api/seguranca.py`, acrescentar o import e a entrada. A lista `ISENTAS`
passa a ter um comentário a mais e um item:

```python
from fraus.api.rotas.webhook import PREFIXO_WEBHOOK
```

```python
# - `/integracoes/webhook/{id}` tem credencial propria (a ASSINATURA do corpo),
#   e a plataforma externa nao tem -- nem pode ter -- uma chave de acesso
#   `fra_`. Sem esta linha o defeito e silencioso e so aparece em producao: com
#   a mestra definida, toda chamada de webhook levaria 401 aqui antes de a
#   assinatura ser olhada, e o log de entregas ficaria vazio dizendo "nao
#   chegou nada" enquanto a plataforma recebe 401 em cada tentativa.
ISENTAS = ("/ingestao", "/acesso/estado", "/saude")
```

O caminho tem `{fonte_id}` variável, então a comparação por igualdade não serve.
Ajustar o middleware em `registrar_middleware_de_acesso`, na linha da checagem:

```python
        caminho = request.url.path.rstrip("/")
        if (
            caminho in ISENTAS
            or caminho.startswith(f"{PREFIXO_WEBHOOK}/")
            or request.method == "OPTIONS"
        ):
            return await call_next(request)
```

Em `fraus/api/main.py`, registrar o router novo junto dos outros:

```python
from fraus.api.rotas import webhook
...
app.include_router(webhook.router)
```

Confira o padrão exato de import e de `include_router` que o arquivo já usa e
siga-o — não invente um segundo estilo.

- [ ] **Step 5: Rodar e verificar que passa**

Run: `uv run pytest tests/test_webhook.py -q`
Expected: PASS. Depois `uv run pytest -q` — a suíte inteira precisa continuar verde.

Se `test_a_rota_responde_com_a_mestra_ligada...` falhar com 401, a mudança do
middleware não pegou. É a falha mais importante do arquivo: ela é o defeito que
só apareceria em produção.

- [ ] **Step 6: Commit**

```bash
git add fraus/api/rotas/webhook.py fraus/api/seguranca.py fraus/api/main.py tests/test_webhook.py
git commit -m "feat(api): a rota de webhook assinada, e o porteiro na ordem certa

Fecha o buraco central: o tipo \"webhook\" existia no cadastro de fonte e
nao ramificava em lugar nenhum -- fonte webhook e fonte csv eram a mesma
coisa. Agora ha URL por fonte, que e o que plataforma nenhuma dispensa.

O corpo e lido CRU. HMAC e byte-exato, e deixar o FastAPI desserializar
para depois reserializar na conferencia muda a assinatura por reordenacao
de chave -- ha um teste que altera um unico byte so para travar isso.

Ordem do porteiro: identidade, autoridade, parse. Duas escolhas parecem
erro e nao sao. Variavel de ambiente ausente e 503, nao 401, porque o
defeito e da maquina que hospeda e 401 mandaria quem integra caçar
problema alheio. Reentrega do mesmo webhook-id e 200, nao erro, porque o
padrao manda a plataforma retentar fora de 2xx -- responder erro poria a
integracao em laco infinito por conta propria.

ISENTAS ganha o prefixo da rota. Sem isso o defeito seria silencioso e so
apareceria em producao: com a mestra ligada, toda chamada levaria 401
antes da assinatura, e o log de entregas diria \"nao chegou nada\"
enquanto a plataforma recebe 401 em cada tentativa."
```

---

### Task 5: A rota do segredo e a de entregas

**Files:**
- Modify: `fraus/api/rotas/integracoes.py`
- Test: `tests/test_webhook.py` (acrescentar ao final)

**Interfaces:**
- Consumes: `assinatura.gerar_segredo` (Task 1), `Banco.listar_entregas` (Task 2)
- Produces:
  - `POST /integracoes/fontes/{fonte_id}/segredo` → `{"segredo", "variavel", "aviso"}`
  - `GET /integracoes/fontes/{fonte_id}/entregas` → `list[dict]`

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar ao final de `tests/test_webhook.py`:

```python
# --- a rota que gera o segredo ----------------------------------------------

def test_gerar_segredo_devolve_em_claro_e_nao_grava_nada(cliente, fonte):  # noqa: F811
    """O segredo NAO entra no banco: a fonte guarda so o NOME da variavel.

    E o que mantem a propriedade do projeto inteiro -- um fraus.db vazado num
    backup nao leva credencial junto."""
    resposta = cliente.post(f"/integracoes/fontes/{fonte['id']}/segredo")
    assert resposta.status_code == 201
    segredo = resposta.json()["segredo"]
    assert segredo.startswith("whsec_")
    assert resposta.json()["variavel"] == VARIAVEL
    # Em lugar nenhum da leitura da fonte o valor aparece.
    assert segredo not in cliente.get("/integracoes/fontes").text


def test_segredo_gerado_e_de_fato_o_que_a_rota_confere(cliente, fonte, monkeypatch):  # noqa: F811
    """O teste que fecha o circuito: gerar -> por no ambiente -> assinar com ele
    -> a rota aceita. Sem ele, os dois lados poderiam divergir de formato e cada
    um passaria nos proprios testes."""
    novo = cliente.post(f"/integracoes/fontes/{fonte['id']}/segredo").json()["segredo"]
    monkeypatch.setenv(VARIAVEL, novo)
    assert _enviar(cliente, fonte["id"], segredo=novo).status_code == 201


def test_gerar_segredo_de_fonte_inexistente_e_404(cliente):  # noqa: F811
    assert cliente.post("/integracoes/fontes/99999/segredo").status_code == 404


def test_dois_segredos_gerados_nunca_sao_iguais(cliente, fonte):  # noqa: F811
    um = cliente.post(f"/integracoes/fontes/{fonte['id']}/segredo").json()["segredo"]
    outro = cliente.post(f"/integracoes/fontes/{fonte['id']}/segredo").json()["segredo"]
    assert um != outro


# --- a rota que le as entregas ----------------------------------------------

def test_entregas_de_fonte_inexistente_e_404(cliente):  # noqa: F811
    assert cliente.get("/integracoes/fontes/99999/entregas").status_code == 404


def test_fonte_sem_entrega_nenhuma_devolve_lista_vazia(cliente, fonte):  # noqa: F811
    """Lista vazia, nao 404: a fonte existe e nao recebeu nada, e isso e
    diferente de a fonte nao existir (invariante 2)."""
    assert cliente.get(f"/integracoes/fontes/{fonte['id']}/entregas").json() == []


def test_o_tipo_webhook_publica_a_ajuda_certa(cliente):  # noqa: F811
    """A ajuda do tipo dizia so \"recebe eventos da plataforma\" quando a rota
    nem existia. Agora ela nomeia o endereco."""
    tipos = {t["valor"]: t for t in cliente.get("/integracoes/tipos").json()}
    assert "webhook" in tipos["webhook"]["ajuda"]
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `uv run pytest tests/test_webhook.py -q -k "segredo or entregas or ajuda"`
Expected: FAIL — 404/405 nas rotas que ainda não existem

- [ ] **Step 3: Implementar**

Em `fraus/api/rotas/integracoes.py`, acrescentar o import:

```python
from fraus import assinatura, credencial
```

Acrescentar as duas rotas após `revogar_chave`:

```python
@router.post("/integracoes/fontes/{fonte_id}/segredo", status_code=201)
def gerar_segredo(
    fonte_id: int,
    authorization: str | None = Header(default=None),
    ctx: Contexto = Depends(obter_contexto),
) -> dict:
    """Gera o segredo de assinatura do webhook e o devolve EM CLARO uma vez.

    E A UNICA ROTA DESTE PROJETO QUE NAO GRAVA A CREDENCIAL QUE EMITE -- nem o
    hash. E de proposito: HMAC exige o segredo em claro no servidor toda vez
    que uma assinatura e conferida, e guardar valor recuperavel no SQLite
    desfaria a propriedade que faz um backup vazado nao levar credencial junto.

    O valor mora na variavel de ambiente que a fonte nomeia. O fluxo do
    operador tem tres passos e a tela mostra os tres: gerar, por na variavel de
    ambiente da maquina da API, entregar a copia a plataforma.

    Privilegio da mestra, como as demais rotas de credencial: uma chave que
    emite outra chave nao seria um posto menor.
    """
    exigir_mestra(ctx, authorization)
    fonte = ctx.banco.buscar_fonte(fonte_id)
    if fonte is None:
        raise HTTPException(status_code=404, detail="fonte nao encontrada")

    variavel = fonte["variavel_segredo"]
    return {
        "segredo": assinatura.gerar_segredo(),
        # O NOME da variavel onde ele deve ser posto. `None` quando a fonte nao
        # nomeia nenhuma -- a tela precisa saber a diferenca para pedir o
        # cadastro em vez de mandar o operador adivinhar onde por o valor.
        "variavel": variavel,
        "aviso": (
            "Guarde agora: este segredo nao e gravado em lugar nenhum pelo Fraus. "
            + (
                f"Defina {variavel} com este valor no ambiente da API e entregue "
                "a mesma copia a plataforma."
                if variavel
                else "Cadastre antes o nome da variavel de ambiente desta fonte."
            )
        ),
    }


@router.get("/integracoes/fontes/{fonte_id}/entregas")
def listar_entregas(
    fonte_id: int, ctx: Contexto = Depends(obter_contexto)
) -> list[dict]:
    """Entregas de webhook daquela fonte, mais recente primeiro.

    Lista VAZIA e resposta legitima: a fonte existe e nao recebeu nada, e isso
    e diferente de a fonte nao existir -- que e 404. O corpo das requisicoes
    nunca esteve aqui (ver o esquema de `entregas_webhook`).
    """
    if ctx.banco.buscar_fonte(fonte_id) is None:
        raise HTTPException(status_code=404, detail="fonte nao encontrada")
    return ctx.banco.listar_entregas(fonte_id)
```

Corrigir a ajuda do tipo webhook em `tipos_de_fonte`, que descrevia uma rota
inexistente:

```python
        {
            "valor": "webhook",
            "rotulo": "Webhook",
            "ajuda": (
                "a plataforma chama POST /integracoes/webhook/{id} com o evento "
                "assinado"
            ),
        },
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `uv run pytest tests/test_webhook.py -q && uv run pytest -q`
Expected: PASS nas duas.

- [ ] **Step 5: Commit**

```bash
git add fraus/api/rotas/integracoes.py tests/test_webhook.py
git commit -m "feat(api): gerar o segredo do webhook e ler o que cada fonte recebeu

A rota do segredo e a unica do projeto que NAO grava a credencial que
emite, nem o hash dela -- e de proposito. HMAC exige o valor em claro no
servidor toda vez que confere, e guardar valor recuperavel no SQLite
desfaria a propriedade que faz um backup vazado nao levar credencial
junto. O valor mora na variavel de ambiente que a fonte ja nomeia, e o
campo que era enfeite passa a ter funcao.

Ha um teste que fecha o circuito -- gerar, por no ambiente, assinar com
ele, a rota aceita. Sem ele os dois lados poderiam divergir de formato e
cada um passaria nos proprios testes.

A ajuda do tipo \"webhook\" dizia so \"recebe eventos da plataforma\"
quando a rota nem existia. Agora nomeia o endereco."
```

---

### Task 6: A porta do front para a API nova

**Files:**
- Modify: `dashboard/lib/api.ts`

**Interfaces:**
- Produces:
  - `type Entrega = { id: number; fonte_id: number; webhook_id: string | null; recebida_em: string; veredito: Veredito; motivo: string | null; conversa_id: string | null }`
  - `type Veredito = "aceita" | "assinatura" | "fora_da_janela" | "duplicada" | "corpo_invalido" | "fonte_inativa" | "sem_segredo"`
  - `type SegredoGerado = { segredo: string; variavel: string | null; aviso: string }`
  - `listarEntregas(fonteId: number): Promise<Resultado<Entrega[]>>`
  - `gerarSegredo(fonteId: number): Promise<Resultado<SegredoGerado>>`

- [ ] **Step 1: Ler o arquivo e copiar o padrão que ele já usa**

Run: `grep -n "export async function gerarChave" -A 12 dashboard/lib/api.ts`

`gerarChave` e `listarFontes` são os modelos exatos a seguir: mesmo tipo de
retorno (`Resultado<T>`), mesmo tratamento de erro, mesma forma de montar a URL
pelo proxy. **Não invente um segundo estilo de chamada** — `lib/api.ts` é a
única porta para a API, e um caminho que não passe pelo proxy vazaria a chave de
acesso para o navegador.

- [ ] **Step 2: Acrescentar os tipos**

```typescript
/**
 * O veredito de uma entrega de webhook. A lista vem de `VEREDITOS` em
 * `fraus/db.py` e é digitada aqui uma única vez — se um veredito novo entrar lá
 * sem entrar aqui, o TypeScript reclama no `switch` de `Entregas.tsx`, que é
 * exatamente onde a divergência precisa aparecer.
 */
export type Veredito =
  | "aceita"
  | "assinatura"
  | "fora_da_janela"
  | "duplicada"
  | "corpo_invalido"
  | "fonte_inativa"
  | "sem_segredo";

export type Entrega = {
  id: number;
  fonte_id: number;
  webhook_id: string | null;
  recebida_em: string;
  veredito: Veredito;
  motivo: string | null;
  /** `null` quando a entrega não gerou conversa — nunca "" nem 0. */
  conversa_id: string | null;
};

export type SegredoGerado = {
  segredo: string;
  /** `null` quando a fonte não nomeia variável de ambiente nenhuma. */
  variavel: string | null;
  aviso: string;
};
```

- [ ] **Step 3: Acrescentar as duas funções, no molde de `gerarChave`**

```typescript
export async function listarEntregas(fonteId: number) {
  return pedir<Entrega[]>(`/integracoes/fontes/${fonteId}/entregas`);
}

export async function gerarSegredo(fonteId: number) {
  return pedir<SegredoGerado>(`/integracoes/fontes/${fonteId}/segredo`, {
    method: "POST",
  });
}
```

**Ajuste os nomes ao que o arquivo de fato usa.** Se o helper não se chamar
`pedir`, ou se as funções existentes recebem opções de outro jeito, siga o que
está lá. As assinaturas públicas (`listarEntregas`, `gerarSegredo`) e os tipos
acima é que não mudam — as tasks seguintes dependem deles.

- [ ] **Step 4: Verificar os tipos**

Run: `cd dashboard && npx tsc --noEmit`
Expected: sem erro.

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/api.ts
git commit -m "feat(dashboard): tipos e porta para as entregas e o segredo do webhook

lib/api.ts continua sendo a unica porta para a API -- um caminho que nao
passe pelo proxy vazaria a chave de acesso para o navegador.

O tipo Veredito e digitado uma vez: veredito novo no Python sem entrar
aqui faz o TypeScript reclamar no switch de Entregas, que e onde a
divergencia precisa aparecer."
```

---

### Task 7: Os componentes do detalhe de uma fonte

**Files:**
- Create: `dashboard/components/integracoes/Entregas.tsx`
- Create: `dashboard/components/integracoes/ContratoDoWebhook.tsx`
- Create: `dashboard/components/integracoes/SegredoDoWebhook.tsx`

**Interfaces:**
- Consumes: `Entrega`, `Veredito`, `listarEntregas`, `gerarSegredo` (Task 6); `FonteIntegracao` (já existe); `ChaveEmClaro`, `EstadoVazio`, `Painel` (já existem)
- Produces:
  - `<Entregas fonteId={number} />`
  - `<ContratoDoWebhook fonte={FonteIntegracao} base={string} />`
  - `<SegredoDoWebhook fonte={FonteIntegracao} />`

**Antes de escrever qualquer pixel:** ler `dashboard/DESIGN.md` e
`dashboard/PRODUCT.md`. São obrigatórios. A regra mestra é *acima da linha é o
que foi DITO, abaixo é o que foi MEDIDO*, e o encoding é âmbar = dito, azul =
medido, dourado = ação e foco **nunca dado**. As decisões de cor estão fechadas —
não abra paleta nova.

- [ ] **Step 1: `Entregas.tsx`**

O componente busca no cliente (`useEffect` + `listarEntregas`), porque a lista
muda enquanto a tela está aberta e é ela que o operador olha ao depurar.

Requisitos, todos verificáveis:

- Cabeçalho com a contagem por veredito (`18 aceitas · 2 assinatura`), derivada
  da lista — nunca de um contador separado.
- Um `switch` sobre `Veredito` que devolve o rótulo em português e a cor. Ele
  precisa ser **exaustivo**, sem `default` que engula caso novo: é o que faz o
  TypeScript reclamar quando um veredito entra no Python e não aqui.
- Rótulos: `aceita` → "aceita"; `assinatura` → "assinatura inválida";
  `fora_da_janela` → "fora da janela de tempo"; `duplicada` → "reentrega";
  `corpo_invalido` → "corpo fora do contrato"; `fonte_inativa` → "fonte
  desativada"; `sem_segredo` → "segredo ausente no ambiente da API".
- `aceita` usa `text-promotor-texto`; `sem_segredo` usa `text-detrator-texto`
  (é defeito da máquina, o mais urgente); os demais, `text-muted-foreground`.
  **Não use o dourado `--primary`** — ele é ação e foco, nunca dado.
- `conversa_id` ausente vira travessão `—`, nunca `0` nem string vazia
  (invariante 2). Use `formatarDataHora` de `lib/formato.ts` para o horário.
- Lista vazia usa `<EstadoVazio>` com `endpoint="POST /integracoes/webhook/{id}"`
  e um texto que nomeia o próximo passo, no molde dos que já existem: enquanto a
  plataforma não chamar a rota, a lista fica vazia — e é assim que ela deve
  ficar, em vez de mostrar um exemplo.
- Um aviso, uma vez só no rodapé do bloco (nunca por linha — regra 3.7 do
  handoff): o Fraus guarda as últimas 200 entregas de cada fonte e nunca o corpo
  da requisição, porque ele traz mensagem de cliente real.

- [ ] **Step 2: `ContratoDoWebhook.tsx`**

Substitui o `<details>` de `ChaveDaFonte.tsx`, que ensinava só o caminho de
`/ingestao`. Mostra:

- a URL da fonte, `{base}/integracoes/webhook/{fonte.id}`, com botão de copiar;
- os três cabeçalhos e o que se assina (`{id}.{timestamp}.{corpo}`) numa
  tabelinha;
- um `curl` copiável com a assinatura marcada como `<CALCULE_O_HMAC>`, e **não**
  um valor de exemplo que pareceria funcionar e não funcionaria;
- o formato do corpo, igual ao exemplo que `ChaveDaFonte` já usa hoje;
- uma frase nomeando o padrão e o porquê, com link para a especificação: os
  cabeçalhos seguem o Standard Webhooks, então dá para usar biblioteca de
  prateleira em vez de implementar à mão;
- a ressalva honesta, uma vez: o Fraus recebe eventos **num contrato
  documentado**; não há adaptador para nenhuma plataforma nomeada, e a tradução
  do formato da plataforma é de quem integra.

- [ ] **Step 3: `SegredoDoWebhook.tsx`**

- Botão "Gerar segredo de assinatura" → `gerarSegredo(fonte.id)`.
- Exibe o resultado no `<ChaveEmClaro>` que já existe — o mesmo componente da
  chave `frs_` e da mestra. **Não faça uma segunda cópia do aviso de "copie
  agora"**: ele é parte da credencial, e duas cópias divergem.
- Mostra os três passos numerados: gerar, definir `{fonte.variavel_segredo}` no
  ambiente da API, entregar a mesma cópia à plataforma.
- Se `fonte.variavel_segredo` for `null`, o botão fica desabilitado e o texto
  diz o que fazer antes: cadastrar o nome da variável, porque sem ela não há
  onde o valor morar.
- Se `fonte.configurada` for `false`, um aviso: a variável não está definida no
  ambiente da API, e **enquanto isso a rota responde 503** — não 401. Nomeie o
  status: é o que faz o operador procurar no lugar certo.
- Nunca guarde o segredo em `localStorage`, `sessionStorage` ou URL. Ele vive no
  estado do componente e morre com a tela, pelo mesmo motivo documentado em
  `ChaveDaFonte.tsx`.

- [ ] **Step 4: Verificar**

```bash
cd dashboard && npx tsc --noEmit && npm run contraste
```
Expected: tipos limpos e contraste AA. Se um veredito novo tiver entrado no
Python sem entrar no `switch`, é aqui que aparece.

- [ ] **Step 5: Commit**

```bash
git add dashboard/components/integracoes/
git commit -m "feat(dashboard): os tres blocos que uma fonte de webhook precisa mostrar

Entregas, contrato e segredo. O switch de veredito e exaustivo de
proposito, sem default: veredito novo no Python que nao chegue aqui vira
erro de tipo, e nao um rotulo em branco na tela.

O contrato marca a assinatura do curl como <CALCULE_O_HMAC> em vez de um
valor de exemplo -- exemplo que parece funcionar e nao funciona custa
mais que ausencia de exemplo.

O segredo reusa o ChaveEmClaro da chave frs_ e da mestra: o aviso de
\"copie agora\" e parte da credencial, e duas copias dele divergiriam.
Diz tambem que variavel ausente responde 503, nomeando o status, para o
operador procurar na maquina em vez de na requisicao."
```

---

### Task 8: O layout mestre-detalhe

**Files:**
- Create: `dashboard/components/integracoes/ListaDeFontes.tsx`
- Create: `dashboard/components/integracoes/PainelDaFonte.tsx`
- Modify: `dashboard/components/integracoes/Fontes.tsx`
- Modify: `dashboard/app/integracoes/page.tsx`

**Interfaces:**
- Consumes: tudo das Tasks 6 e 7; `Importar`, `HistoricoImportacoes`, `ChaveDaFonte` (já existem)
- Produces: `<ListaDeFontes>`, `<PainelDaFonte>`

O alvo:

```
+----------------+---------------------------------+
| FONTES      [+]| Suporte — Zendesk      [ativa]  |
|                |---------------------------------|
| >Suporte-Zend. | Chave frs_ ...abcd     [gerar]  |
|  WhatsApp      | URL   /webhook/3      [copiar]  |
|  Loja CSV      | Segredo FRAUS_WH_ZEN   ok       |
|                | Contrato       [curl] [copiar]  |
|                | Entregas  18 ok / 2 assinatura  |
+----------------+---------------------------------+
| Importar CSV: [arquivo v] [importar]  histórico   |
+---------------------------------------------------+
```

- [ ] **Step 1: `ListaDeFontes.tsx` — a coluna mestre**

Recebe `fontes`, `selecionada` e `aoSelecionar`. Cada item mostra nome, canal e
um ponto de estado (ativa/inativa). O item selecionado é marcado com o dourado
`--primary` — aqui ele é legítimo, é **foco**, não dado.

Acessibilidade, não opcional: os itens são `<button>` dentro de uma lista, com
`aria-current="true"` no selecionado. Navegação por teclado precisa funcionar.

O botão `[+]` no cabeçalho da coluna abre o formulário de cadastro.

- [ ] **Step 2: `PainelDaFonte.tsx` — o detalhe**

Recebe a fonte selecionada e `baseDaApi`. Monta, nesta ordem:

1. cabeçalho com nome, canal, tipo, estado e as ações que hoje moram na tabela
   (renomear, ativar/desativar, remover — inclusive a confirmação de remoção com
   o texto que já existe sobre nenhum atendimento ser apagado);
2. `<ChaveDaFonte>` (já existe, sem alteração de comportamento);
3. **só se `fonte.tipo === "webhook"`**: `<SegredoDoWebhook>`,
   `<ContratoDoWebhook>` e `<Entregas>`.

O condicional é o ponto da task inteira: é o primeiro lugar do código onde o
campo `tipo` de fato **ramifica**. Fonte CSV não ganha bloco de webhook, e é o
que faz o tipo deixar de ser um rótulo.

Sem fonte selecionada, mostra um `<EstadoVazio>` convidando a escolher uma na
coluna — ou a cadastrar a primeira, se não houver nenhuma.

- [ ] **Step 3: `Fontes.tsx` perde a tabela**

Ele guarda o estado da lista e o formulário de cadastro; a tabela sai e dá lugar
a `<ListaDeFontes>` + `<PainelDaFonte>`, com o `useState` da fonte selecionada
morando nele.

**Preserve integralmente:** `recarregar`, `adicionar`, `alternarAtiva`,
`confirmarRenome`, `remover`, o `Alert` de erro, e o parágrafo que explica que o
campo guarda o nome de uma variável de ambiente e não o token. Esse parágrafo é
texto de honestidade — ele **muda de lugar, não de conteúdo**, indo para junto do
campo que explica.

Quando a lista muda, a fonte selecionada precisa acompanhar: cadastrar uma nova
seleciona ela; remover a selecionada limpa a seleção. Selecionar por id que não
existe mais deixaria o painel direito preso num fantasma.

- [ ] **Step 4: `page.tsx` — a página**

Mantém as quatro leituras em `Promise.all` e os estados de erro por bloco, que já
estão certos: se o histórico cair, o cadastro continua de pé.

Muda o arranjo: o mestre-detalhe ocupa o corpo da tela, e **a importação de CSV
desce para uma faixa no rodapé**, junto do histórico. Ela é ação de arquivo
local, não integração de rede — e a legenda atual, que a chama de "a ação da
tela", deixa de ser verdade agora que o webhook existe. Reescreva essa legenda;
não a mantenha por inércia.

A prosa dos rodapés dos três painéis vai para junto do controle que ela explica
(regra 3.7: ressalva empilhada em rodapé é ressalva não lida). Nenhum texto é
apagado — se algum for do lote que o João declarou intocável, deixe-o onde está
e aponte no relato da task.

Responsividade: abaixo de `lg`, mestre e detalhe empilham (a lista vira uma faixa
de seleção acima do painel). A tela não pode rolar na horizontal.

- [ ] **Step 5: Verificar**

```bash
cd dashboard && npx tsc --noEmit && npm run contraste && npm run build
```

**Não rode `npm run build` com o `next dev` do João no ar** — invalida os hashes
dos chunks e a tela vira 403 em tudo. Já foi diagnosticado como "tela feia" uma
vez (armadilha 3 do handoff).

Depois, com a API de pé (`uv run python scripts/api_demo.py`), abra
`/integracoes` e confirme à mão: cadastrar fonte webhook, gerar segredo, ver o
contrato, e a lista de entregas vazia com o texto certo.

- [ ] **Step 6: Commit**

```bash
git add dashboard/
git commit -m "feat(dashboard): integracoes vira mestre-detalhe, e o tipo da fonte enfim ramifica

Tres paineis empilhados, cada um com legenda e rodape longos, nao
cabiam mais: o webhook soma quatro blocos por fonte e a tabela ja era
gorda. A lista vira coluna estreita e a fonte escolhida abre a direita
com tudo que e dela -- a fonte numero doze nao piora a tela.

PainelDaFonte e o primeiro lugar do codigo onde `tipo` de fato ramifica:
fonte csv nao ganha bloco de webhook. E o que faz o campo deixar de ser
um rotulo.

A importacao de CSV desce para o rodape. Ela e acao de arquivo local, nao
integracao de rede, e ocupava o topo por ordem historica -- a legenda que
a chamava de \"a acao da tela\" deixou de ser verdade.

A prosa de honestidade nao foi cortada, foi realocada para junto do
controle que ela explica: ressalva empilhada em rodape e ressalva nao
lida."
```

---

### Task 9: A documentação

**Files:**
- Modify: `README.md`
- Modify: `docs/handoff.md`
- Modify: `CLAUDE.md` (mapa de arquivos)

- [ ] **Step 1: `README.md` — a seção de integração**

Documentar, com um exemplo executável de ponta a ponta:

- cadastrar a fonte com `tipo: webhook` e o nome da variável de ambiente;
- `POST /integracoes/fontes/{id}/segredo` para gerar o segredo;
- definir a variável no ambiente da API e reiniciar;
- o contrato: a URL, os três cabeçalhos, o que se assina, o formato do corpo;
- um exemplo de **assinar em Python** com 8 linhas de `hmac`, para quem integra
  não precisar deduzir o formato da prosa;
- a tabela de status: 201 aceito, 200 reentrega, 400 contrato/janela, 401
  assinatura, 403 fonte desativada, 404 fonte inexistente, **503 variável
  ausente no ambiente da API** — com a frase que explica por que o último é 503;
- a ressalva: HMAC prova origem e integridade, **não confidencialidade**. O corpo
  trafega legível para quem estiver no caminho, e quem publica a API precisa de
  TLS — ver `docs/hospedagem.md`, que já descreve o túnel Cloudflare.

- [ ] **Step 2: `docs/handoff.md`**

- Estado atual: a integração por webhook está de pé, com o número de testes novo.
- Seção 4, mapa do código: `fraus/assinatura.py`, `fraus/api/registro.py` e
  `fraus/api/rotas/webhook.py`.
- Seção 8, armadilhas: acrescentar a de `ISENTAS` — rota de escrita com
  credencial própria precisa entrar na lista, ou o middleware a recusa com 401
  antes de a credencial dela ser olhada, e só com a mestra ligada (isto é, só em
  produção).
- Acrescentar também: `PRAGMA foreign_keys` vale **por conexão** no SQLite —
  ligar na criação do esquema não teria efeito nenhum nas conexões seguintes, e
  o `ON DELETE CASCADE` seria documentação em vez de comportamento.

- [ ] **Step 3: `CLAUDE.md`**

Acrescentar ao mapa de arquivos:

| `fraus/assinatura.py` | HMAC do webhook — o segredo mora no ambiente, nunca no banco |
| `fraus/api/registro.py` | o miolo de derivação, compartilhado pelas duas rotas de entrada |
| `fraus/api/rotas/webhook.py` | webhook assinado por fonte, com registro de entrega |

- [ ] **Step 4: Verificar**

Run: `uv run pytest -q`
Expected: PASS. Confirme que o número de testes citado no handoff é o número real
— handoff com contagem errada é a primeira coisa que a próxima sessão descobre
estar mentindo.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/handoff.md CLAUDE.md
git commit -m "docs(webhook): o contrato, o fluxo do segredo e as duas armadilhas pagas

O README ganha o caminho completo de quem integra, com exemplo de
assinatura em Python -- deduzir o formato da prosa custa uma tarde. A
tabela de status explica por que variavel ausente e 503 e nao 401.

Declara que HMAC prova origem e integridade, nao confidencialidade: o
corpo trafega legivel e quem publica a API precisa de TLS.

Duas armadilhas para o handoff. Rota de escrita com credencial propria
precisa entrar em ISENTAS, ou o middleware recusa com 401 antes de olhar
a credencial dela -- e so com a mestra ligada, isto e, so em producao. E
PRAGMA foreign_keys vale por CONEXAO no SQLite: ligar na criacao do
esquema deixaria o ON DELETE CASCADE como documentacao."
```

---

## Verificação final

```bash
uv run pytest -q
cd dashboard && npx tsc --noEmit && npm run contraste && npm run build
```

E o teste de ponta a ponta que nenhum unitário cobre, com a API de pé:

1. cadastrar uma fonte `webhook` com `variavel_segredo`;
2. gerar o segredo pela tela e pô-lo na variável de ambiente;
3. reiniciar a API para ela ler a variável;
4. assinar um corpo com o exemplo em Python do README e mandar;
5. confirmar 201, a conversa em `/atendimentos`, e a entrega `aceita` na tela;
6. mandar de novo com o mesmo `webhook-id` e confirmar 200 sem conversa nova;
7. mandar com o corpo alterado em um byte e confirmar 401 com `assinatura` na tela.

O passo 3 é o que separa este roteiro de um teste automatizado: `os.environ` é
lido no processo da API, e sem reiniciar o operador vê 503 com o segredo
"definido" — que é justamente a confusão que o veredito `sem_segredo` existe para
nomear.
