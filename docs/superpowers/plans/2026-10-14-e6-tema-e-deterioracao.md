# E6 — Impacto por tema e trajetória de deterioração: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Medir, em retrospectiva e em lote, quanto o NPS inferido de um tema difere do resto do recorte (com IC) e onde, numa conversa encerrada, a estimativa por prefixo virou detratora para não voltar.

**Architecture:** Dois módulos puros. `fraus/impacto.py` faz a diferença de NPS com IC por bootstrap e entra em cada tema de `descobrir_temas`. `fraus/deterioracao.py` encontra o ponto de virada sobre os scores por prefixo que `Motor.scores_do_replay` já produz, e entra como o campo `deterioracao` em `GET /operacao/replay/{id}`. A tela mostra os dois no Radar e no Replay da Operação. `scripts/medir_deterioracao.py` mede recall, falso alarme e lead time, e declara antes que o simulador não gera trajetória.

**Tech Stack:** Python 3.11 / numpy (já instalado) / FastAPI / pytest; Next.js + TypeScript / vitest (`renderToStaticMarkup`).

**Spec:** `docs/superpowers/specs/2026-10-14-e6-tema-e-deterioracao-design.md`

## Global Constraints

- **Retrospectivo e em lote.** Nada roda durante o atendimento, nada alerta e nada decide sozinho. O texto de tela diz "retrospectivo".
- **Nada é gravado.** Score, nota e categoria ficam intactos. Não há coluna nova, e a trajetória não é persistida (invariante 5).
- **Faixas vigentes por parâmetro**, nunca global mutável nem número redigitado. "Detrator" é `categoria_nps(score, faixas) == "detrator"`.
- **Invariante 2.** Abaixo de 30 conversas com sinal (`N_MINIMO_NPS`), no tema ou no resto, `impacto_nps` é `null` com `motivo: "n abaixo do mínimo"`, nunca 0. Conversa sem sinal fica fora da conta e é contada (`sem_sinal_tema`).
- **Rótulos fixos:** "associação, não causa" no impacto; "retrospectivo: lead time hipotético, não alerta" na deterioração.
- **O IC é reprodutível:** bootstrap com 1.000 reamostras e semente fixa `20261014`.
- **O escopo por canal** vem do banco com escopo (`ctx.registros_do_recorte` → `banco.todas()`).
- **Nenhum número inventado.** Medição com modelo real sem o fusor log1p presente é "não verificado — modelos ausentes".
- Sem LLM e sem dependência nova. Não tocar `modelos/`, `fusor.py`, `NOMES_FEATURES`, `PESO_NEUTRO_NO_SCORE` nem `Motor.scores_do_replay`.
- Commits em português sem acento, `tipo(escopo): resumo`, com o trailer `Co-Authored-By: Neuro <neuro.chan.dev@gmail.com>`. TDD: teste vermelho primeiro.

## Decisões do plano (desvios e detalhamentos do spec)

1. **O impacto viaja aninhado** em `tema["impacto"]` (`impacto_nps`, `ic_inferior`, `ic_superior`, `n_tema`, `n_resto`, `sem_sinal_tema`, `minimo`, `motivo`, `rotulo`), como o `intervalo` já faz.
2. **O n mínimo vale para os dois lados.** Com o resto abaixo de 30, o impacto também é `null`, porque a diferença precisa dos dois NPS.
3. **"Resto do recorte"** são as conversas examinadas pelo radar (depois do `TETO_RADAR`) que não estão no tema.
4. **O IC é o percentil 2,5–97,5** da diferença com reamostragem independente de tema e resto.
5. **Virada:** é o primeiro índice `k` com score definido e detrator tal que todo score definido depois de `k` também é detrator. Score `None` (prefixo ainda sem sinal) não quebra a sequência. Se o último score definido não é detrator, não há virada (`motivo: "não terminou detratora"`). Sem nenhum score, `motivo: "sem sinal do cliente"`.
6. **Lead time:** `falas_ate_o_fim = len(mensagens) − 1 − k` e `segundos_ate_o_fim = fim − enviada_em[k]`, com `fim = encerrada_em` ou a última mensagem. Virada na última mensagem dá 0: só ficou visível no fim, e isso é dito.
7. **O campo `virada` que já existe nos pontos** (variação ≥ 10) não muda. O novo é `deterioracao.indice_virada`, outro conceito.
8. **Conferência do simulador.** `gerar_conversa(rotulo, frases_cliente, semente)` sorteia todas as falas do cliente de um único conjunto de frases, o do rótulo. A conferência é estrutural: um teste prende a assinatura (um só `frases_cliente`). O script declara que **o lead time medido no simulador é artefato do gerador**. Se o simulador ganhar trajetória, o teste quebra e a declaração tem de ser revista.
9. **A virada não aumenta o recall** sobre o baseline "só no fim": há virada se e só se o último score é detrator. O script imprime os dois recalls e diz isso. O que a virada acrescenta é o lead time.
10. **Com modelo ausente, o script** imprime a conferência e depois "não verificado — modelos ausentes: <erro>", e sai com código 2. Nada de motor dublê (invariante 7).
11. **Na tela:** o impacto entra no `<details>` do tema, ao lado do NPS do tema. A deterioração entra no Replay com uma linha de referência no gráfico e uma frase. Campo ausente (API antiga) não renderiza nada inventado: o impacto mostra "indisponível nesta versão da API"; a deterioração não mostra nada.

## Review Focus

1. **Vazamento de futuro no replay:** alterar a mensagem `j` não pode mudar o score de nenhum prefixo `k < j`, e o teste não pode passar no vazio. Tarefa 2.
2. **Tema com muitas conversas sem sinal:** elas não entram na conta e aparecem em `sem_sinal_tema`; com menos de 30 com sinal, `null` e nunca 0. Tarefa 1.
3. **Score que volta acima do limiar:** a virada é a última descida definitiva, não a primeira. Tarefa 2.
4. **Faixa configurada diferente da de fábrica:** a virada e o impacto respeitam as faixas passadas. Tarefas 1 e 2.
5. **API antiga sem os campos novos:** a tela não quebra e não inventa. Tarefa 3.

---

### Tarefa 1: impacto por tema (`fraus/impacto.py` + radar)

**Files:**
- Create: `fraus/impacto.py`
- Modify: `fraus/operacao.py` (`descobrir_temas`, por volta das linhas 29–80)
- Test: `tests/test_impacto.py`

**Interfaces:**
- Consumes: `fraus.indicadores.N_MINIMO_NPS`, `calcular_nps(scores, faixas)`, `categoria_nps(score, faixas)`.
- Produces:
  - `impacto_nps(scores_tema, scores_resto, faixas, reamostras=1000, semente=20261014) -> dict`, com as chaves da decisão 1.
  - Constantes `ROTULO_IMPACTO = "associação, não causa"` e `MOTIVO_N_MINIMO = "n abaixo do mínimo"`.
  - Cada tema de `descobrir_temas` ganha a chave `"impacto"`.

- [ ] **Step 1: Testes que falham**

```python
"""Impacto do tema no NPS inferido: diferenca contra o resto, com IC, e nunca 0
no lugar de "nao ha dado"."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.impacto import MOTIVO_N_MINIMO, ROTULO_IMPACTO, impacto_nps
from fraus.indicadores import FAIXAS_NPS
from fraus.modelos import Conversa, Mensagem
from fraus.operacao import descobrir_temas
from tests.test_api import MotorFalso

T0 = datetime(2026, 10, 1, 10, tzinfo=timezone.utc)


def test_diferenca_de_nps_com_ic_reprodutivel():
    tema = [20.0] * 30 + [95.0] * 10          # NPS -50
    resto = [95.0] * 30 + [20.0] * 10         # NPS +50
    r = impacto_nps(tema, resto, FAIXAS_NPS)
    assert r["impacto_nps"] == -100.0
    assert r["ic_inferior"] <= -100.0 <= r["ic_superior"]
    assert r == impacto_nps(tema, resto, FAIXAS_NPS)
    assert r["rotulo"] == ROTULO_IMPACTO and r["motivo"] is None


def test_abaixo_do_minimo_e_null_com_motivo_nunca_zero():
    r = impacto_nps([20.0] * 29, [95.0] * 40, FAIXAS_NPS)
    assert r["impacto_nps"] is None and r["ic_inferior"] is None and r["ic_superior"] is None
    assert r["motivo"] == MOTIVO_N_MINIMO and r["n_tema"] == 29 and r["minimo"] == 30


def test_resto_abaixo_do_minimo_tambem_e_null():
    assert impacto_nps([20.0] * 40, [95.0] * 5, FAIXAS_NPS)["impacto_nps"] is None


def test_sem_sinal_fica_fora_e_e_contado():
    r = impacto_nps([None] * 50 + [20.0] * 10, [95.0] * 40, FAIXAS_NPS)
    assert r["n_tema"] == 10 and r["sem_sinal_tema"] == 50 and r["impacto_nps"] is None


def test_faixa_vigente_por_parametro():
    # score 75 -> nota 8: neutro na fabrica, promotor numa faixa 0-6/7-7/8-10.
    faixas = {"detrator": (0, 6), "neutro": (7, 7), "promotor": (8, 10)}
    fab = impacto_nps([75.0] * 30, [20.0] * 30, FAIXAS_NPS)["impacto_nps"]
    outra = impacto_nps([75.0] * 30, [20.0] * 30, faixas)["impacto_nps"]
    assert fab == 100.0 and outra == 200.0


def _conv(i, texto, canal="chat", dia=0):
    t = T0 + timedelta(days=dia)
    return Conversa(id=i, canal=canal, iniciada_em=t, mensagens=[
        Mensagem(autor="cliente", texto=texto, enviada_em=t),
        Mensagem(autor="bot", texto="vou verificar", enviada_em=t + timedelta(seconds=30))])


def test_radar_traz_impacto_por_tema():
    registros = [(_conv(f"a{i}", "cobranca duplicada preciso estorno"), 20.0) for i in range(30)]
    registros += [(_conv(f"b{i}", "senha bloqueada acesso login"), 95.0) for i in range(30)]
    temas = descobrir_temas(registros, FAIXAS_NPS)["temas"]
    cobranca = next(t for t in temas if "a0" in t["conversa_ids"])
    assert cobranca["impacto"]["impacto_nps"] == -200.0
    assert cobranca["impacto"]["n_resto"] == 30


def test_radar_pequeno_tem_impacto_null_e_nao_quebra():
    registros = [(_conv(f"a{i}", "cobranca duplicada preciso estorno"), 20.0) for i in range(3)]
    tema = descobrir_temas(registros, FAIXAS_NPS)["temas"][0]
    assert tema["impacto"]["impacto_nps"] is None and tema["impacto"]["motivo"] == MOTIVO_N_MINIMO


def test_rota_respeita_escopo_e_nao_grava(tmp_path):
    banco = Banco(tmp_path / "e.db")
    banco.migrar()
    for i in range(3):
        banco.salvar(_conv(f"a{i}", "cobranca duplicada preciso estorno"), 20.0, "detrator")
        banco.salvar(_conv(f"e{i}", "cobranca duplicada preciso estorno", canal="email"), 20.0, "detrator")
    antes = [(c.model_dump(), s) for c, s in banco.todas()]
    app = criar_app(banco, MotorFalso(), raiz_importacao=tmp_path, chave_mestra="chave-teste-operacao",
                    jwt_segredo="segredo-jwt-de-teste-operacao-123456", codigo_dev="convite-dev-teste")
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
    tema_u = cli.get("/operacao/radar", headers=headers["usuario"]).json()["temas"][0]
    tema_d = cli.get("/operacao/radar", headers=headers["dev"]).json()["temas"][0]
    assert tema_u["impacto"]["n_tema"] + tema_u["impacto"]["n_resto"] == 3
    assert tema_d["impacto"]["n_tema"] + tema_d["impacto"]["n_resto"] == 6
    assert [(c.model_dump(), s) for c, s in banco.todas()] == antes
```

> Se `GET /operacao/radar` exigir outra credencial além do JWT (veja `tests/test_operacao.py::ambiente`), ajuste só o cabeçalho, não as asserções.

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_impacto.py -q`
Expected: FAIL, com `ModuleNotFoundError: No module named 'fraus.impacto'`.

- [ ] **Step 3: Implementação**

`fraus/impacto.py`:

```python
"""Impacto de um tema no NPS inferido: NPS(tema) - NPS(resto do recorte), com IC.

Retrospectivo e em lote; marca, nao decide. E ASSOCIACAO, NAO CAUSA: um tema
pode andar junto com outro fator (canal, horario, produto) que e quem de fato
move a nota.

Ausencia nao vira zero (invariante 2): abaixo de `N_MINIMO_NPS` conversas com
sinal no tema OU no resto, a diferenca e `None` com motivo -- a mesma regra do
cartao de NPS. Conversa sem sinal fica fora da conta e e contada.

O IC e percentil 2,5-97,5 de bootstrap com reamostragem independente dos dois
lados, semente fixa. Captura so a incerteza AMOSTRAL, nunca a do modelo.
Spec: docs/superpowers/specs/2026-10-14-e6-tema-e-deterioracao-design.md
"""

import numpy as np

from fraus.indicadores import N_MINIMO_NPS, calcular_nps, categoria_nps

REAMOSTRAS = 1000
SEMENTE_IMPACTO = 20261014
ROTULO_IMPACTO = "associação, não causa"
MOTIVO_N_MINIMO = "n abaixo do mínimo"

_VALOR = {"promotor": 1.0, "detrator": -1.0}


def _contribuicoes(scores, faixas) -> np.ndarray:
    # +1 promotor, -1 detrator, 0 neutro: a media x 100 e o NPS.
    return np.array([_VALOR.get(categoria_nps(s, faixas), 0.0) for s in scores])


def impacto_nps(scores_tema, scores_resto, faixas, reamostras=REAMOSTRAS,
                semente=SEMENTE_IMPACTO) -> dict:
    tema = [s for s in scores_tema if s is not None]
    resto = [s for s in scores_resto if s is not None]
    base = {"n_tema": len(tema), "n_resto": len(resto),
            "sem_sinal_tema": len(scores_tema) - len(tema),
            "minimo": N_MINIMO_NPS, "rotulo": ROTULO_IMPACTO}
    if len(tema) < N_MINIMO_NPS or len(resto) < N_MINIMO_NPS:
        return {**base, "impacto_nps": None, "ic_inferior": None, "ic_superior": None,
                "motivo": MOTIVO_N_MINIMO}
    impacto = round(calcular_nps(tema, faixas) - calcular_nps(resto, faixas), 2)
    a, b = _contribuicoes(tema, faixas), _contribuicoes(resto, faixas)
    sorteio = np.random.default_rng(semente)
    media_a = a[sorteio.integers(0, len(a), size=(reamostras, len(a)))].mean(axis=1)
    media_b = b[sorteio.integers(0, len(b), size=(reamostras, len(b)))].mean(axis=1)
    inferior, superior = np.percentile(100.0 * (media_a - media_b), [2.5, 97.5])
    return {**base, "impacto_nps": impacto, "ic_inferior": round(float(inferior), 2),
            "ic_superior": round(float(superior), 2), "motivo": None}
```

Em `fraus/operacao.py`, importe `from fraus.impacto import impacto_nps`. No laço de `descobrir_temas`, antes do `temas.append`, monte:

```python
        no_tema = set(indices)
        resto = [registros[i][1] for i in range(len(registros)) if i not in no_tema]
```

No dict do tema, acrescente `"impacto": impacto_nps([registros[i][1] for i in indices], resto, faixas),`. Ao `"metodo"`, acrescente a frase: `"; impacto = NPS do tema menos NPS do resto do recorte, IC 95% por bootstrap (1.000 reamostras), associação, não causa"`.

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_impacto.py tests/test_operacao.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fraus/impacto.py fraus/operacao.py tests/test_impacto.py
git commit -m "feat(impacto): impacto do tema no NPS inferido com IC no radar"
```

---

### Tarefa 2: trajetória de deterioração (`fraus/deterioracao.py` + replay)

**Files:**
- Create: `fraus/deterioracao.py`
- Modify: `fraus/api/rotas/operacao.py` (rota `replay`, por volta das linhas 373–395)
- Test: `tests/test_deterioracao.py`

**Interfaces:**
- Consumes: `categoria_nps(score, faixas)`; `Motor.scores_do_replay(conversa, curadoria) -> list[float | None]` (sem mudança); `tests.test_motor._motor()`.
- Produces:
  - `indice_de_virada(scores, abaixo) -> int | None`, onde `abaixo` é `Callable[[float], bool]`.
  - `deterioracao(scores, conversa, faixas) -> dict`, com as chaves `indice_virada`, `falas_ate_o_fim`, `segundos_ate_o_fim`, `motivo`, `criterio` e `rotulo`.
  - Constantes `ROTULO_DETERIORACAO`, `CRITERIO_DETERIORACAO`, `MOTIVO_SEM_SINAL = "sem sinal do cliente"`, `MOTIVO_NAO_TERMINOU = "não terminou detratora"`.
  - `GET /operacao/replay/{id}` ganha a chave `"deterioracao"`.

- [ ] **Step 1: Testes que falham**

```python
"""Deterioracao: onde a estimativa por prefixo virou detratora PARA NAO VOLTAR,
numa conversa encerrada. Retrospectivo; e o teste de nao-vazamento que segura
o "sem ver o futuro"."""

from datetime import datetime, timedelta, timezone

from fraus.deterioracao import (MOTIVO_NAO_TERMINOU, MOTIVO_SEM_SINAL, ROTULO_DETERIORACAO,
                                deterioracao, indice_de_virada)
from fraus.indicadores import FAIXAS_NPS
from fraus.modelos import Conversa, Mensagem
from tests.test_motor import _motor

T0 = datetime(2026, 10, 1, 10, tzinfo=timezone.utc)
abaixo = lambda s: s < 65


def conv(*falas, encerrada=None):
    return Conversa(id="c", canal="chat", iniciada_em=T0, encerrada_em=encerrada, mensagens=[
        Mensagem(autor=a, texto=t, enviada_em=T0 + timedelta(minutes=k)) for k, (a, t) in enumerate(falas)])


def test_virada_e_a_ultima_descida_definitiva():
    assert indice_de_virada([90, 40, 80, 50, 30], abaixo) == 3


def test_none_nao_quebra_a_sequencia():
    assert indice_de_virada([None, 40, None, 30], abaixo) == 1


def test_termina_acima_nao_tem_virada():
    assert indice_de_virada([40, 30, 80], abaixo) is None


def test_lead_time_em_falas_e_segundos():
    c = conv(("cliente", "a"), ("bot", "b"), ("cliente", "c"), ("bot", "d"), ("cliente", "e"))
    d = deterioracao([90.0, 90.0, 40.0, 40.0, 30.0], c, FAIXAS_NPS)
    assert d["indice_virada"] == 2 and d["falas_ate_o_fim"] == 2
    assert d["segundos_ate_o_fim"] == 120.0 and d["motivo"] is None
    assert d["rotulo"] == ROTULO_DETERIORACAO


def test_encerrada_em_conta_como_fim():
    c = conv(("cliente", "a"), ("bot", "b"), encerrada=T0 + timedelta(minutes=10))
    assert deterioracao([30.0, 30.0], c, FAIXAS_NPS)["segundos_ate_o_fim"] == 600.0


def test_sem_score_e_motivo_e_nao_zero():
    d = deterioracao([None, None], conv(("bot", "a"), ("bot", "b")), FAIXAS_NPS)
    assert d["indice_virada"] is None and d["falas_ate_o_fim"] is None
    assert d["motivo"] == MOTIVO_SEM_SINAL


def test_nao_terminou_detratora():
    d = deterioracao([30.0, 90.0], conv(("cliente", "a"), ("cliente", "b")), FAIXAS_NPS)
    assert d["indice_virada"] is None and d["motivo"] == MOTIVO_NAO_TERMINOU


def test_faixa_vigente_por_parametro():
    # score 70 -> nota 7: neutro na fabrica, detrator numa faixa 0-7.
    faixas = {"detrator": (0, 7), "neutro": (8, 8), "promotor": (9, 10)}
    c = conv(("cliente", "a"))
    assert deterioracao([70.0], c, FAIXAS_NPS)["indice_virada"] is None
    assert deterioracao([70.0], c, faixas)["indice_virada"] == 0


def test_score_do_prefixo_nao_ve_mensagem_futura():
    """Alterar a mensagem j nao muda nenhum score de prefixo k < j."""
    motor = _motor()
    c = conv(("cliente", "otimo atendimento"), ("bot", "posso ajudar"),
             ("cliente", "ainda nao resolveu"), ("bot", "vou verificar"),
             ("cliente", "obrigado"))
    base = motor.scores_do_replay(c)
    mudou_algo = False
    for j in range(1, len(c.mensagens)):
        alterada = c.model_copy(deep=True)
        original = alterada.mensagens[j]
        alterada.mensagens[j] = Mensagem(autor=original.autor,
                                         texto="pessimo horrivel nunca mais volto",
                                         enviada_em=original.enviada_em + timedelta(seconds=30))
        novos = motor.scores_do_replay(alterada)
        assert novos[:j] == base[:j], j
        mudou_algo |= novos[j:] != base[j:]
    assert mudou_algo, "o teste passaria no vazio: nenhuma alteracao mexeu em score algum"
```

Em `tests/test_operacao.py::test_replay_cenario_e_comparacao_nao_gravam`, logo depois de `assert r.status_code == 200 and len(r.json()["pontos"]) == 2`, acrescente:

```python
    assert set(r.json()["deterioracao"]) >= {"indice_virada", "falas_ate_o_fim", "segundos_ate_o_fim", "motivo", "criterio", "rotulo"}
```

> Se, com o `_motor()` sintético, nenhuma alteração mexer em score (os dublês de texto podem ignorar o texto), troque o texto alterado por outro que o dublê de `tests/test_motor.py` leia de forma diferente. Leia `_TextoDuble` para escolher. **Não** remova o `assert mudou_algo`.

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_deterioracao.py -q`
Expected: FAIL, com `ModuleNotFoundError: No module named 'fraus.deterioracao'`.

- [ ] **Step 3: Implementação**

`fraus/deterioracao.py`:

```python
"""Trajetoria de deterioracao numa conversa ENCERRADA: retrospectiva, em lote.

Le os scores por prefixo que `Motor.scores_do_replay` ja produz -- cada um so
com as falas que ja tinham ocorrido -- e acha a VIRADA: a primeira mensagem a
partir da qual a estimativa fica detratora (faixa vigente, por parametro) e
nao volta ate o fim. O lead time e quantas mensagens e quanto tempo havia
entre a virada e o fim.

E HIPOTETICO E RETROSPECTIVO. Nao e alerta, nao roda durante o atendimento
(Conformidade, regra 3) e nada e gravado (invariante 5). Prefixo sem sinal do
cliente tem score `None`, que nao quebra a sequencia nem vira zero.

A virada existe se e so se o ultimo score definido e detrator: ela NAO aumenta
o recall sobre o score final. O que ela acrescenta e o lead time.
Spec: docs/superpowers/specs/2026-10-14-e6-tema-e-deterioracao-design.md
"""

from fraus.indicadores import categoria_nps

ROTULO_DETERIORACAO = "retrospectivo: lead time hipotético, não alerta"
CRITERIO_DETERIORACAO = (
    "primeira mensagem a partir da qual a estimativa por prefixo fica detratora "
    "(faixa vigente) e não volta até o fim"
)
MOTIVO_SEM_SINAL = "sem sinal do cliente"
MOTIVO_NAO_TERMINOU = "não terminou detratora"


def indice_de_virada(scores, abaixo) -> int | None:
    virada = None
    for indice, score in enumerate(scores):
        if score is None:
            continue
        if abaixo(score):
            if virada is None:
                virada = indice
        else:
            virada = None
    return virada


def deterioracao(scores, conversa, faixas) -> dict:
    base = {"criterio": CRITERIO_DETERIORACAO, "rotulo": ROTULO_DETERIORACAO}
    vazio = {"indice_virada": None, "falas_ate_o_fim": None, "segundos_ate_o_fim": None}
    if all(s is None for s in scores):
        return {**base, **vazio, "motivo": MOTIVO_SEM_SINAL}
    virada = indice_de_virada(scores, lambda s: categoria_nps(s, faixas) == "detrator")
    if virada is None:
        return {**base, **vazio, "motivo": MOTIVO_NAO_TERMINOU}
    fim = conversa.encerrada_em or conversa.mensagens[-1].enviada_em
    return {**base, "indice_virada": virada,
            "falas_ate_o_fim": len(conversa.mensagens) - 1 - virada,
            "segundos_ate_o_fim": (fim - conversa.mensagens[virada].enviada_em).total_seconds(),
            "motivo": None}
```

Na rota `replay` de `fraus/api/rotas/operacao.py`, importe `from fraus.deterioracao import deterioracao` e acrescente ao dict de retorno:

```python
        "deterioracao": deterioracao(scores, conversa, faixas),
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_deterioracao.py tests/test_operacao.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fraus/deterioracao.py fraus/api/rotas/operacao.py tests/test_deterioracao.py tests/test_operacao.py
git commit -m "feat(deterioracao): virada retrospectiva e lead time no replay"
```

---

### Tarefa 3: tela — impacto no Radar e deterioração no Replay

**Files:**
- Modify: `dashboard/lib/operacao.ts`, com os tipos `ImpactoTema` e `Deterioracao` e os campos opcionais em `Tema` e `Replay`.
- Create: `dashboard/components/operacao/ImpactoTema.tsx`, `dashboard/components/operacao/DeterioracaoReplay.tsx`
- Create: `dashboard/components/operacao/ImpactoTema.test.tsx`, `dashboard/components/operacao/DeterioracaoReplay.test.tsx`
- Modify: `dashboard/components/operacao/Planejamento.tsx` (`RadarOperacao`) e `dashboard/components/operacao/Leituras.tsx` (`ReplayOperacao`)

**Interfaces:**
- Consumes: `tema.impacto` (Tarefa 1) e `replay.deterioracao` (Tarefa 2).
- Produces: `ImpactoTema({ impacto })` e `DeterioracaoReplay({ deterioracao })`.

- [ ] **Step 1: Testes que falham**

`ImpactoTema.test.tsx`:

```tsx
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ImpactoTema } from "./ImpactoTema";
import type { ImpactoTema as Impacto } from "@/lib/operacao";

const medido: Impacto = { impacto_nps: -23.5, ic_inferior: -40.1, ic_superior: -6.2, n_tema: 48, n_resto: 310, sem_sinal_tema: 3, minimo: 30, motivo: null, rotulo: "associação, não causa" };
const html = (i: Impacto | undefined) => renderToStaticMarkup(<ImpactoTema impacto={i} />);

describe("ImpactoTema", () => {
  it("mostra a diferença com sinal, o IC e o rótulo", () => {
    const m = html(medido);
    expect(m).toContain("−23,5");
    expect(m).toContain("−40,1");
    expect(m).toContain("associação, não causa");
    expect(m).toContain("3 sem sinal");
  });
  it("abaixo do mínimo nomeia o que falta e não mostra zero", () => {
    const m = html({ ...medido, impacto_nps: null, ic_inferior: null, ic_superior: null, n_tema: 12, motivo: "n abaixo do mínimo" });
    expect(m).toContain("n abaixo do mínimo");
    expect(m).toContain("12");
    expect(m).not.toMatch(/[+−]0(,0)?\b/);
  });
  it("API antiga: indisponível", () => {
    expect(html(undefined)).toContain("indisponível nesta versão da API");
  });
});
```

`DeterioracaoReplay.test.tsx`:

```tsx
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { DeterioracaoReplay } from "./DeterioracaoReplay";
import type { Deterioracao } from "@/lib/operacao";

const base: Deterioracao = { indice_virada: 2, falas_ate_o_fim: 4, segundos_ate_o_fim: 600, motivo: null, criterio: "primeira mensagem a partir da qual…", rotulo: "retrospectivo: lead time hipotético, não alerta" };
const html = (d: Deterioracao | undefined) => renderToStaticMarkup(<DeterioracaoReplay deterioracao={d} />);

describe("DeterioracaoReplay", () => {
  it("virada: índice, falas e tempo antes do fim, com o rótulo", () => {
    const m = html(base);
    expect(m).toContain("índice 2");
    expect(m).toContain("4 mensagens");
    expect(m).toContain("retrospectivo");
  });
  it("sem virada mostra o motivo", () => {
    expect(html({ ...base, indice_virada: null, falas_ate_o_fim: null, segundos_ate_o_fim: null, motivo: "não terminou detratora" })).toContain("não terminou detratora");
  });
  it("API antiga não renderiza nada", () => {
    expect(html(undefined)).toBe("");
  });
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd dashboard && npx vitest run components/operacao/ImpactoTema.test.tsx components/operacao/DeterioracaoReplay.test.tsx`
Expected: FAIL, porque os módulos não existem.

- [ ] **Step 3: Implementação**

Em `dashboard/lib/operacao.ts`:

```ts
/** Impacto do tema no NPS inferido (E6). `impacto_nps` null = n abaixo do mínimo, nunca 0. */
export type ImpactoTema = { impacto_nps: number | null; ic_inferior: number | null; ic_superior: number | null; n_tema: number; n_resto: number; sem_sinal_tema: number; minimo: number; motivo: string | null; rotulo: string };
/** Virada retrospectiva no replay (E6). Ausente = API anterior ao E6. */
export type Deterioracao = { indice_virada: number | null; falas_ate_o_fim: number | null; segundos_ate_o_fim: number | null; motivo: string | null; criterio: string; rotulo: string };
```

Acrescente `impacto?: ImpactoTema` ao tipo `Tema` e `deterioracao?: Deterioracao` ao tipo `Replay`.

`ImpactoTema.tsx` é um componente sem estado:
- `undefined` → `<p className="text-xs text-muted-foreground">Impacto no NPS indisponível nesta versão da API.</p>`.
- `impacto_nps === null` → "Impacto no NPS: {motivo} — {n_tema} conversas com sinal no tema, mínimo {minimo}.", e o `sem_sinal_tema` quando for maior que 0.
- Caso medido → "Impacto no NPS: {±x,x} pontos contra o resto do recorte (IC 95%: {a} a {b}) · {n_tema} no tema, {n_resto} no resto · {sem_sinal_tema} sem sinal" e, numa segunda linha muted, o `rotulo`.

Formate o número com `Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: "always" })` e troque o hífen pelo sinal de menos tipográfico (`.replace("-", "−")`), para casar com o teste. Use as classes de texto que `FaixaNps` em `comum.tsx` já usa.

`DeterioracaoReplay.tsx` é um componente sem estado:
- `undefined` → `null`.
- `indice_virada === null` → "Sem ponto de virada: {motivo}.".
- Caso com virada → "A estimativa ficou detratora a partir do índice {k} e não voltou: {falas_ate_o_fim} mensagens e {formatarSegundos(segundos_ate_o_fim)} antes do fim.". Quando `falas_ate_o_fim === 0`, a frase é "…só no fim da conversa." no lugar do trecho de mensagens e tempo.
- Abaixo, em muted: `{rotulo}. Critério: {criterio}.`

Em `RadarOperacao` (Planejamento.tsx), dentro do `<details>`, logo depois de `<FaixaNps titulo="NPS do tema" … />`, renderize `<ImpactoTema impacto={t.impacto} />`.

Em `ReplayOperacao` (Leituras.tsx), logo depois do `<div className="h-64 …">` do gráfico, renderize `<DeterioracaoReplay deterioracao={r.dado.deterioracao} />`. Dentro do `LineChart`, quando `r.dado.deterioracao?.indice_virada` não for `null`/`undefined`, acrescente `<ReferenceLine x={r.dado.deterioracao.indice_virada} stroke="var(--detrator)" strokeDasharray="4 3" />`. Atualize o `aria-label` do gráfico para mencionar a linha tracejada da virada.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd dashboard && npx vitest run && npx tsc --noEmit`
Expected: PASS e `tsc` sem saída. Restaure `dashboard/AGENTS.md` com `git checkout` se ele for regenerado.

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/operacao.ts dashboard/components/operacao/ImpactoTema.tsx dashboard/components/operacao/ImpactoTema.test.tsx dashboard/components/operacao/DeterioracaoReplay.tsx dashboard/components/operacao/DeterioracaoReplay.test.tsx dashboard/components/operacao/Planejamento.tsx dashboard/components/operacao/Leituras.tsx
git commit -m "feat(dashboard): impacto do tema no radar e virada no replay"
```

---

### Tarefa 4: medição e documentação

**Files:**
- Create: `scripts/medir_deterioracao.py`
- Test: `tests/test_medir_deterioracao.py`
- Modify: `docs/limitacoes.md`, `docs/arquitetura.md`, `CLAUDE.md` (duas linhas no mapa), e o spec do E6 (estado e "Desvios aceitos").

**Interfaces:**
- Consumes: `indice_de_virada`, `deterioracao`; `fraus.ingest.simulador.gerar_conversa`/`gerar_lote`; para o motor real, o mesmo caminho de `scripts/medir_aditividade.py` (`montar_classificadores(backend_declarado())`, `Fusor.carregar`, `Motor(texto, fusor, emocao, ironia)`).
- Produces:
  - `conferir_trajetoria() -> str`: a declaração de artefato, presa à assinatura de `gerar_conversa`.
  - `medir(casos, limiares) -> dict`: `casos` é uma lista de `(scores, conversa, rotulo)`; o resultado tem, por limiar, `recall_virada`, `recall_fim`, `falso_alarme`, `lead_falas_mediana` e `lead_segundos_mediana` (`None` quando o denominador é 0).
  - CLI: `python scripts/medir_deterioracao.py [--n 300] [--semente 20261014]`.

- [ ] **Step 1: Testes que falham**

```python
import importlib.util
import inspect
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fraus.ingest.simulador import gerar_conversa
from fraus.modelos import Conversa, Mensagem

RAIZ = Path(__file__).resolve().parent.parent


def _script():
    spec = importlib.util.spec_from_file_location("medir_deterioracao", RAIZ / "scripts" / "medir_deterioracao.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["medir_deterioracao"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


T0 = datetime(2026, 10, 1, 10, tzinfo=timezone.utc)


def _c(n):
    return Conversa(id="c", canal="chat", iniciada_em=T0, mensagens=[
        Mensagem(autor="cliente" if k % 2 == 0 else "bot", texto="x", enviada_em=T0 + timedelta(minutes=k))
        for k in range(n)])


def test_simulador_sorteia_falas_de_um_rotulo_so():
    """Se o simulador ganhar trajetoria, isto quebra e a declaracao de artefato
    tem de ser revista."""
    assert list(inspect.signature(gerar_conversa).parameters) == ["rotulo", "frases_cliente", "semente"]
    assert "artefato do gerador" in _script().conferir_trajetoria()


def test_medir_recall_falso_alarme_e_lead():
    m = _script()
    casos = [([90.0, 40.0, 30.0], _c(3), 0),     # detrator, virada no 1: 1 fala, 60 s
             ([90.0, 90.0, 90.0], _c(3), 0),     # detrator perdido
             ([90.0, 30.0, 30.0], _c(3), 2)]     # falso alarme
    r = m.medir(casos, {"limiar 65": lambda s: s < 65})["limiar 65"]
    assert r["recall_virada"] == 0.5 and r["recall_fim"] == 0.5
    assert r["falso_alarme"] == 1.0
    assert r["lead_falas_mediana"] == 1 and r["lead_segundos_mediana"] == 60.0


def test_denominador_zero_e_none():
    m = _script()
    r = m.medir([([90.0], _c(1), 2)], {"l": lambda s: s < 65})["l"]
    assert r["recall_virada"] is None and r["lead_falas_mediana"] is None


def test_sem_modelos_diz_nao_verificado_e_sai_2(capsys, monkeypatch):
    m = _script()

    def falha():
        raise FileNotFoundError("fusor.joblib ausente")

    monkeypatch.setattr(m, "montar_motor_real", falha)
    assert m.principal([]) == 2
    saida = capsys.readouterr().out
    assert "artefato do gerador" in saida
    assert "não verificado — modelos ausentes" in saida
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_medir_deterioracao.py -q`
Expected: FAIL, porque o script não existe.

- [ ] **Step 3: Implementação**

`scripts/medir_deterioracao.py` segue a estrutura de `scripts/medir_aditividade.py` (o `sys.path` para `RAIZ`, `main`/`principal`, uma docstring que diz o que mede e o que não mede). Ele precisa ter:

- `conferir_trajetoria()`: devolve o texto "O simulador sorteia todas as falas do cliente do conjunto de frases de UM rótulo (gerar_conversa(rotulo, frases_cliente, semente)): não há trajetória dentro da conversa. Lead time medido aqui é artefato do gerador, não previsão de produção."
- `montar_motor_real()`: carrega `Fusor.carregar(CAMINHO_FUSOR)` primeiro (falha antes de carregar as cabeças) e depois `montar_classificadores(backend_declarado())`, devolvendo `Motor(texto, fusor, emocao, ironia)`. Os imports e caminhos são os de `medir_aditividade.py`.
- `medir(casos, limiares)`: para cada nome → predicado `abaixo`:
  - `positivos` são os casos com `rotulo == 0`; os outros são negativos.
  - Para cada caso, calcule `virada = indice_de_virada(scores, abaixo)` e `fim = último score definido`.
  - `recall_virada` = positivos com virada / positivos.
  - `recall_fim` = positivos com `fim` definido e `abaixo(fim)` / positivos.
  - `falso_alarme` = negativos com virada / negativos.
  - Para os positivos com virada, o lead é `len(mensagens) − 1 − virada` falas e `(fim_da_conversa − enviada_em[virada])` segundos, com `fim_da_conversa = encerrada_em or última mensagem`. Reporte a mediana (`statistics.median`).
  - Qualquer métrica com denominador 0 é `None`.
- `principal(argv)`:
  1. Imprime `conferir_trajetoria()`.
  2. Tenta `montar_motor_real()`. Em qualquer `Exception`, imprime `f"não verificado — modelos ausentes: {erro}"` e retorna 2.
  3. Gera `--n` conversas com `gerar_lote` usando as frases que `scripts/medir_aditividade.py` usa (se ele não tiver frases próprias, use `{0: ["péssimo, não resolveu nada"], 1: ["ok"], 2: ["ótimo, resolveu rápido"]}` e declare isso na saída), roda `motor.scores_do_replay`.
  4. Imprime uma tabela por limiar: a faixa vigente de fábrica (`categoria_nps(s, FAIXAS_NPS) == "detrator"`) e `score < L` para L em 30, 40, 50, 60 e 70.
  5. Imprime a frase: "recall_virada = recall_fim por construção: a virada acrescenta lead time, não recall".
  6. Retorna 0.

Documentação:
- `docs/limitacoes.md`: seção "Impacto por tema e deterioração (E6)", com:
  - associação, não causa;
  - o mínimo de 30 nos dois lados;
  - tema por TF-IDF + DBSCAN, instável com pouco dado;
  - lead time em dado sintético não prevê produção;
  - o simulador não gera trajetória, então a medição dele é artefato;
  - "medição com o fusor real: não verificado — fusor log1p ausente em 14/10/2026";
  - retrospectivo, nunca alerta ao vivo.
- `docs/arquitetura.md`: uma linha junto do radar/replay da Operação.
- `CLAUDE.md`, no mapa de arquivos, depois de `fraus/sinalizadores.py`:
  - `| \`fraus/impacto.py\` | impacto do tema no NPS inferido, IC por bootstrap; associação, não causa |`
  - `| \`fraus/deterioracao.py\` | virada retrospectiva sobre os scores por prefixo do replay; nunca alerta ao vivo |`
- Spec do E6: o estado vira "aprovado em 14/10/2026" e entra a seção "Desvios aceitos", com as decisões 1 a 11 deste plano, uma linha cada.

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_medir_deterioracao.py tests/test_documentacao.py -q && uv run python scripts/medir_deterioracao.py; echo "saida=$?"`
Expected: PASS. O script imprime a declaração de artefato e, nesta máquina sem o fusor log1p, "não verificado — modelos ausentes: …" com `saida=2`.

- [ ] **Step 5: Commit**

```bash
git add scripts/medir_deterioracao.py tests/test_medir_deterioracao.py docs/limitacoes.md docs/arquitetura.md CLAUDE.md docs/superpowers/specs/2026-10-14-e6-tema-e-deterioracao-design.md
git commit -m "feat(deterioracao): instrumento de medicao e docs do E6"
```
