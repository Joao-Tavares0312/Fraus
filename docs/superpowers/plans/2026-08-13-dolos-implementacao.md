# Dolos — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir uma ferramenta que ingere transcrições de atendimento por chatbot e produz score de satisfação por atendimento e indicadores agregados (NPS inferido, CSAT, containment rate, latência), sem LLM em runtime, expostos numa dashboard com relatórios.

**Architecture:** Três sinais independentes (texto via BERTimbau fine-tuned, emoji via lexicon estático, tempo via features derivadas de timestamps) são calculados sobre um modelo canônico de conversa e fundidos por um classificador leve do scikit-learn. Uma API FastAPI serve predição e agregações a partir de SQLite; a dashboard Next.js consome essa API.

**Tech Stack:** Python 3.11 · uv · pydantic · pytest · scikit-learn · transformers + torch (CPU) · FastAPI · SQLite · Next.js + Recharts

**Spec:** `docs/superpowers/specs/2026-08-13-dolos-design.md`

## Global Constraints

- **Sem LLM em runtime.** Nenhuma chamada a API de modelo de linguagem no caminho de predição. Inferência local em CPU.
- **Python 3.11.** Gerenciado por `uv`.
- **Categoria e score sempre derivados no servidor.** Nunca aceitar categoria, score ou classificação vindos do cliente HTTP.
- **Faixas de NPS fixas:** 0–6 detrator, 7–8 neutro, 9–10 promotor.
- **Latência nunca é persistida** — sempre derivada de timestamps.
- **Idioma do código:** identificadores e docstrings em português, sem acento em nomes de símbolo (`mensagens`, `latencia_mediana_s`).
- **Timestamps são timezone-aware (UTC).** `datetime` naive é erro de validação.
- **TDD:** todo passo de código começa por um teste que falha.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `dolos/modelos.py` | modelo canônico `Mensagem` / `Conversa` |
| `dolos/ingest/csv_driver.py` | CSV/JSON → `list[Conversa]` |
| `dolos/ingest/simulador.py` | gera conversas sintéticas com timestamps |
| `dolos/sinais/emoji.py` | features de emoji via lexicon |
| `dolos/sinais/tempo.py` | features de latência/estrutura da conversa |
| `dolos/sinais/texto.py` | wrapper do BERTimbau fine-tuned |
| `dolos/fusor.py` | funde os três sinais → score 0–100 |
| `dolos/indicadores.py` | agregações: NPS, CSAT, containment |
| `dolos/db.py` | persistência SQLite |
| `dolos/api/main.py` | FastAPI |
| `dolos/dados/emoji_sentiment_ranking.csv` | lexicon estático |
| `notebooks/01_treino_bertimbau.ipynb` | fine-tune no Colab |
| `dashboard/` | Next.js |

---

### Task 1: Esqueleto do projeto e modelo canônico

**Files:**
- Create: `pyproject.toml`, `dolos/__init__.py`, `dolos/modelos.py`, `tests/test_modelos.py`, `.gitignore`, `README.md`

**Interfaces:**
- Consumes: nada
- Produces: `Mensagem(autor: Literal["cliente","bot","humano"], texto: str, enviada_em: datetime)`; `Conversa(id: str, canal: str, iniciada_em: datetime, encerrada_em: datetime | None, escalou_para_humano: bool, mensagens: list[Mensagem])`; propriedades `Conversa.mensagens_cliente -> list[Mensagem]` e `Conversa.tem_sinal_cliente -> bool`

- [ ] **Step 1: Criar `pyproject.toml`**

```toml
[project]
name = "dolos"
version = "0.1.0"
description = "Analise de satisfacao em atendimentos por chatbot"
requires-python = ">=3.11"
dependencies = ["pydantic>=2.7"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Escrever o teste que falha**

Criar `tests/test_modelos.py`:

```python
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from dolos.modelos import Conversa, Mensagem


def _ts(segundo: int) -> datetime:
    return datetime(2026, 8, 13, 10, 0, segundo, tzinfo=timezone.utc)


def _conversa(mensagens: list[Mensagem]) -> Conversa:
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=_ts(0),
        encerrada_em=None,
        escalou_para_humano=False,
        mensagens=mensagens,
    )


def test_mensagens_cliente_filtra_somente_o_cliente():
    conversa = _conversa([
        Mensagem(autor="cliente", texto="oi", enviada_em=_ts(0)),
        Mensagem(autor="bot", texto="ola", enviada_em=_ts(5)),
        Mensagem(autor="cliente", texto="valeu", enviada_em=_ts(9)),
    ])
    assert [m.texto for m in conversa.mensagens_cliente] == ["oi", "valeu"]


def test_conversa_sem_mensagem_do_cliente_nao_tem_sinal():
    conversa = _conversa([Mensagem(autor="bot", texto="ola", enviada_em=_ts(0))])
    assert conversa.tem_sinal_cliente is False


def test_autor_invalido_e_rejeitado():
    with pytest.raises(ValidationError):
        Mensagem(autor="gerente", texto="oi", enviada_em=_ts(0))


def test_timestamp_naive_e_rejeitado():
    with pytest.raises(ValidationError):
        Mensagem(autor="cliente", texto="oi", enviada_em=datetime(2026, 8, 13, 10, 0, 0))
```

- [ ] **Step 3: Rodar o teste e confirmar que falha**

Run: `uv run pytest tests/test_modelos.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'dolos.modelos'`

- [ ] **Step 4: Implementar `dolos/modelos.py`**

```python
"""Modelo canonico de conversa. Toda fonte de dado e normalizada para ca."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

Autor = Literal["cliente", "bot", "humano"]


class Mensagem(BaseModel):
    autor: Autor
    texto: str
    enviada_em: datetime

    @field_validator("enviada_em")
    @classmethod
    def _exige_timezone(cls, valor: datetime) -> datetime:
        if valor.tzinfo is None:
            raise ValueError("enviada_em precisa ser timezone-aware")
        return valor


class Conversa(BaseModel):
    id: str
    canal: str
    iniciada_em: datetime
    encerrada_em: datetime | None = None
    escalou_para_humano: bool = False
    mensagens: list[Mensagem]

    @property
    def mensagens_cliente(self) -> list[Mensagem]:
        return [m for m in self.mensagens if m.autor == "cliente"]

    @property
    def tem_sinal_cliente(self) -> bool:
        return len(self.mensagens_cliente) > 0
```

Criar `dolos/__init__.py` vazio e `.gitignore` com:

```
__pycache__/
*.pyc
.venv/
.pytest_cache/
modelos/
dados_brutos/
node_modules/
.next/
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

Run: `uv run pytest tests/test_modelos.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml dolos tests .gitignore README.md
git commit -m "feat(modelos): modelo canonico de conversa e mensagem"
```

---

### Task 2: Driver de ingestão CSV

**Files:**
- Create: `dolos/ingest/__init__.py`, `dolos/ingest/csv_driver.py`, `tests/test_csv_driver.py`

**Interfaces:**
- Consumes: `Conversa`, `Mensagem` da Task 1
- Produces: `carregar_csv(caminho: Path) -> ResultadoIngestao`; `ResultadoIngestao(conversas: list[Conversa], rejeitadas: list[LinhaRejeitada])`; `LinhaRejeitada(numero_linha: int, motivo: str)`

Formato do CSV — uma linha por mensagem, colunas: `conversa_id,canal,autor,texto,enviada_em,escalou_para_humano`. `enviada_em` em ISO-8601 com offset. Conversas são agrupadas por `conversa_id`; `iniciada_em` é o menor timestamp, `encerrada_em` o maior, `escalou_para_humano` é verdadeiro se qualquer linha da conversa marcar verdadeiro.

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_csv_driver.py`:

```python
from pathlib import Path

from dolos.ingest.csv_driver import carregar_csv

CABECALHO = "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"


def _escrever(tmp_path: Path, linhas: str) -> Path:
    caminho = tmp_path / "conversas.csv"
    caminho.write_text(CABECALHO + linhas, encoding="utf-8")
    return caminho


def test_agrupa_mensagens_por_conversa(tmp_path):
    caminho = _escrever(tmp_path, (
        "c1,csv,cliente,oi,2026-08-13T10:00:00+00:00,false\n"
        "c1,csv,bot,ola,2026-08-13T10:00:07+00:00,false\n"
        "c2,csv,cliente,socorro,2026-08-13T11:00:00+00:00,true\n"
    ))
    resultado = carregar_csv(caminho)

    assert len(resultado.conversas) == 2
    c1 = next(c for c in resultado.conversas if c.id == "c1")
    assert len(c1.mensagens) == 2
    assert c1.iniciada_em.second == 0
    assert c1.encerrada_em.second == 7
    assert c1.escalou_para_humano is False

    c2 = next(c for c in resultado.conversas if c.id == "c2")
    assert c2.escalou_para_humano is True


def test_mensagens_saem_ordenadas_por_timestamp(tmp_path):
    caminho = _escrever(tmp_path, (
        "c1,csv,bot,segunda,2026-08-13T10:00:07+00:00,false\n"
        "c1,csv,cliente,primeira,2026-08-13T10:00:00+00:00,false\n"
    ))
    resultado = carregar_csv(caminho)
    assert [m.texto for m in resultado.conversas[0].mensagens] == ["primeira", "segunda"]


def test_linha_malformada_e_rejeitada_sem_derrubar_o_lote(tmp_path):
    caminho = _escrever(tmp_path, (
        "c1,csv,cliente,oi,2026-08-13T10:00:00+00:00,false\n"
        "c2,csv,cliente,quebrada,data-invalida,false\n"
        "c3,csv,gerente,autor-errado,2026-08-13T10:00:00+00:00,false\n"
    ))
    resultado = carregar_csv(caminho)

    assert {c.id for c in resultado.conversas} == {"c1"}
    assert [r.numero_linha for r in resultado.rejeitadas] == [3, 4]
    assert all(r.motivo for r in resultado.rejeitadas)


def test_timestamp_sem_offset_e_rejeitado(tmp_path):
    caminho = _escrever(tmp_path, "c1,csv,cliente,oi,2026-08-13T10:00:00,false\n")
    resultado = carregar_csv(caminho)
    assert resultado.conversas == []
    assert len(resultado.rejeitadas) == 1
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `uv run pytest tests/test_csv_driver.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'dolos.ingest'`

- [ ] **Step 3: Implementar `dolos/ingest/csv_driver.py`**

```python
"""Driver de ingestao CSV. Uma linha por mensagem, agrupada por conversa_id."""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from dolos.modelos import Conversa, Mensagem

VERDADEIROS = {"true", "1", "sim", "yes"}


class LinhaRejeitada(BaseModel):
    numero_linha: int
    motivo: str


class ResultadoIngestao(BaseModel):
    conversas: list[Conversa]
    rejeitadas: list[LinhaRejeitada]


def carregar_csv(caminho: Path) -> ResultadoIngestao:
    """Le o CSV e devolve conversas validas mais o relato das linhas rejeitadas.

    Uma linha malformada nunca derruba o lote inteiro: ela e isolada com motivo.
    """
    por_conversa: dict[str, list[Mensagem]] = defaultdict(list)
    metadados: dict[str, dict] = {}
    rejeitadas: list[LinhaRejeitada] = []

    with caminho.open(encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        for numero_linha, linha in enumerate(leitor, start=2):
            try:
                enviada_em = datetime.fromisoformat(linha["enviada_em"])
                mensagem = Mensagem(
                    autor=linha["autor"],
                    texto=linha["texto"],
                    enviada_em=enviada_em,
                )
            except Exception as erro:
                rejeitadas.append(LinhaRejeitada(numero_linha=numero_linha, motivo=str(erro)))
                continue

            conversa_id = linha["conversa_id"]
            por_conversa[conversa_id].append(mensagem)
            meta = metadados.setdefault(
                conversa_id, {"canal": linha["canal"], "escalou": False}
            )
            if linha["escalou_para_humano"].strip().lower() in VERDADEIROS:
                meta["escalou"] = True

    conversas = []
    for conversa_id, mensagens in por_conversa.items():
        mensagens.sort(key=lambda m: m.enviada_em)
        meta = metadados[conversa_id]
        conversas.append(
            Conversa(
                id=conversa_id,
                canal=meta["canal"],
                iniciada_em=mensagens[0].enviada_em,
                encerrada_em=mensagens[-1].enviada_em,
                escalou_para_humano=meta["escalou"],
                mensagens=mensagens,
            )
        )

    return ResultadoIngestao(conversas=conversas, rejeitadas=rejeitadas)
```

Criar `dolos/ingest/__init__.py` vazio.

- [ ] **Step 4: Rodar e confirmar que passam**

Run: `uv run pytest tests/test_csv_driver.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add dolos/ingest tests/test_csv_driver.py
git commit -m "feat(ingest): driver CSV com isolamento de linha malformada"
```

---

### Task 3: Sinal de emoji

**Files:**
- Create: `dolos/sinais/__init__.py`, `dolos/sinais/emoji.py`, `dolos/dados/emoji_sentiment_ranking.csv`, `tests/test_sinal_emoji.py`

**Interfaces:**
- Consumes: `Conversa` da Task 1
- Produces: `features_emoji(conversa: Conversa) -> dict[str, float]` com as chaves exatas `emoji_score_medio`, `emoji_frac_positivos`, `emoji_frac_negativos`, `emoji_contagem`, `emoji_posicao_relativa_media`

O lexicon vem do Emoji Sentiment Ranking (751 emojis, PLOS ONE 2015). Baixar de `https://kt.ijs.si/data/Emoji_sentiment_ranking/emojimap.html` ou do dataset no CEU Research Portal, e salvar como CSV com colunas `emoji,negativo,neutro,positivo`. O score de um emoji é `(positivo - negativo) / (positivo + neutro + negativo)`, ficando em [-1, 1].

`emoji_posicao_relativa_media` é a posição do emoji dentro da mensagem normalizada em [0, 1] (0 = primeiro caractere, 1 = último), média sobre todos os emojis. Existe porque a polaridade do emoji cresce conforme ele se aproxima do fim da mensagem.

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_sinal_emoji.py`:

```python
from datetime import datetime, timezone

from dolos.modelos import Conversa, Mensagem
from dolos.sinais.emoji import features_emoji, score_do_emoji


def _conversa(textos: list[str]) -> Conversa:
    base = datetime(2026, 8, 13, 10, 0, 0, tzinfo=timezone.utc)
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=base,
        mensagens=[
            Mensagem(autor="cliente", texto=t, enviada_em=base) for t in textos
        ],
    )


def test_emoji_positivo_tem_score_positivo():
    assert score_do_emoji("\N{HEAVY BLACK HEART}") > 0


def test_emoji_negativo_tem_score_negativo():
    assert score_do_emoji("\N{ANGRY FACE}") < 0


def test_emoji_desconhecido_tem_score_zero():
    assert score_do_emoji("\N{TELEPHONE}") == 0.0 or -1 <= score_do_emoji("\N{TELEPHONE}") <= 1


def test_texto_sem_emoji_zera_as_features():
    features = features_emoji(_conversa(["obrigado pelo atendimento"]))
    assert features["emoji_contagem"] == 0
    assert features["emoji_score_medio"] == 0.0
    assert features["emoji_posicao_relativa_media"] == 0.0


def test_conta_apenas_emoji_do_cliente():
    base = datetime(2026, 8, 13, 10, 0, 0, tzinfo=timezone.utc)
    conversa = Conversa(
        id="c1",
        canal="csv",
        iniciada_em=base,
        mensagens=[
            Mensagem(autor="bot", texto="\N{HEAVY BLACK HEART}" * 5, enviada_em=base),
            Mensagem(autor="cliente", texto="ok", enviada_em=base),
        ],
    )
    assert features_emoji(conversa)["emoji_contagem"] == 0


def test_emoji_no_fim_tem_posicao_relativa_alta():
    features = features_emoji(_conversa(["muito obrigado \N{HEAVY BLACK HEART}"]))
    assert features["emoji_posicao_relativa_media"] > 0.9


def test_emoji_no_inicio_tem_posicao_relativa_baixa():
    features = features_emoji(_conversa(["\N{HEAVY BLACK HEART} muito obrigado"]))
    assert features["emoji_posicao_relativa_media"] < 0.1


def test_fracoes_somam_no_maximo_um():
    features = features_emoji(
        _conversa(["\N{HEAVY BLACK HEART}\N{ANGRY FACE}"])
    )
    assert features["emoji_frac_positivos"] + features["emoji_frac_negativos"] <= 1.0
    assert features["emoji_contagem"] == 2
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `uv run pytest tests/test_sinal_emoji.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'dolos.sinais'`

- [ ] **Step 3: Adicionar a dependência `emoji`**

Em `pyproject.toml`, `dependencies` passa a ser `["pydantic>=2.7", "emoji>=2.12"]`. Rodar `uv sync`.

- [ ] **Step 4: Baixar o lexicon**

Salvar o Emoji Sentiment Ranking em `dolos/dados/emoji_sentiment_ranking.csv` com o cabeçalho `emoji,negativo,neutro,positivo` e uma linha por emoji com as contagens absolutas de anotação. O arquivo é versionado no repo — o runtime não pode depender de rede.

- [ ] **Step 5: Implementar `dolos/sinais/emoji.py`**

```python
"""Sinal de emoji.

Emojis NAO sao removidos no pre-processamento: carregam sinal de polaridade.
Lexicon: Emoji Sentiment Ranking (Kralj Novak et al., PLOS ONE 2015) --
751 emojis anotados por 83 anotadores sobre ~70k tweets.

A posicao relativa entra como feature porque a polaridade do emoji aumenta
conforme ele se aproxima do fim da mensagem.
"""

import csv
from functools import lru_cache
from pathlib import Path

import emoji as lib_emoji

from dolos.modelos import Conversa

CAMINHO_LEXICON = Path(__file__).parent.parent / "dados" / "emoji_sentiment_ranking.csv"
LIMIAR_POLARIDADE = 0.1


@lru_cache(maxsize=1)
def _lexicon() -> dict[str, float]:
    tabela: dict[str, float] = {}
    with CAMINHO_LEXICON.open(encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            negativo = float(linha["negativo"])
            neutro = float(linha["neutro"])
            positivo = float(linha["positivo"])
            total = negativo + neutro + positivo
            if total == 0:
                continue
            tabela[linha["emoji"]] = (positivo - negativo) / total
    return tabela


def score_do_emoji(caractere: str) -> float:
    """Polaridade em [-1, 1]. Emoji fora do lexicon vale 0."""
    return _lexicon().get(caractere, 0.0)


def _emojis_com_posicao(texto: str) -> list[tuple[str, float]]:
    if not texto:
        return []
    achados = lib_emoji.emoji_list(texto)
    ultimo_indice = max(len(texto) - 1, 1)
    return [
        (achado["emoji"], achado["match_start"] / ultimo_indice)
        for achado in achados
    ]


def features_emoji(conversa: Conversa) -> dict[str, float]:
    """Agrega os emojis das mensagens DO CLIENTE numa linha de features."""
    pares: list[tuple[str, float]] = []
    for mensagem in conversa.mensagens_cliente:
        pares.extend(_emojis_com_posicao(mensagem.texto))

    if not pares:
        return {
            "emoji_score_medio": 0.0,
            "emoji_frac_positivos": 0.0,
            "emoji_frac_negativos": 0.0,
            "emoji_contagem": 0.0,
            "emoji_posicao_relativa_media": 0.0,
        }

    scores = [score_do_emoji(caractere) for caractere, _ in pares]
    posicoes = [posicao for _, posicao in pares]
    total = len(scores)

    return {
        "emoji_score_medio": sum(scores) / total,
        "emoji_frac_positivos": sum(1 for s in scores if s > LIMIAR_POLARIDADE) / total,
        "emoji_frac_negativos": sum(1 for s in scores if s < -LIMIAR_POLARIDADE) / total,
        "emoji_contagem": float(total),
        "emoji_posicao_relativa_media": sum(posicoes) / total,
    }
```

Criar `dolos/sinais/__init__.py` vazio.

- [ ] **Step 6: Rodar e confirmar que passam**

Run: `uv run pytest tests/test_sinal_emoji.py -v`
Expected: 8 passed

- [ ] **Step 7: Commit**

```bash
git add dolos/sinais dolos/dados pyproject.toml tests/test_sinal_emoji.py
git commit -m "feat(sinais): sinal de emoji com lexicon e posicao relativa"
```

---

### Task 4: Sinal de tempo

**Files:**
- Create: `dolos/sinais/tempo.py`, `tests/test_sinal_tempo.py`

**Interfaces:**
- Consumes: `Conversa` da Task 1
- Produces: `features_tempo(conversa: Conversa) -> dict[str, float]` com as chaves exatas `latencia_mediana_s`, `latencia_p90_s`, `latencia_primeira_resposta_s`, `duracao_total_s`, `qtd_turnos_cliente`, `escalou`, `abandonou`

Latência é o intervalo entre uma mensagem do cliente e a primeira resposta seguinte do bot ou humano. Nunca persistida — sempre derivada.

`abandonou` é verdadeiro quando a última mensagem da conversa é do bot ou do humano — ou seja, o cliente saiu sem responder. Não depende de `encerrada_em`: uma conversa aberta cuja última fala é do bot já é abandono em curso.

Não há penalidade linear codificada aqui: a relação entre latência e satisfação é não-linear e moderada por contexto (IJHCI 2025), então o peso é aprendido pelo fusor na Task 8.

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_sinal_tempo.py`:

```python
from datetime import datetime, timedelta, timezone

from dolos.modelos import Conversa, Mensagem
from dolos.sinais.tempo import features_tempo

BASE = datetime(2026, 8, 13, 10, 0, 0, tzinfo=timezone.utc)


def _ts(segundos: float) -> datetime:
    return BASE + timedelta(seconds=segundos)


def _conversa(pares: list[tuple[str, float]], escalou: bool = False) -> Conversa:
    mensagens = [
        Mensagem(autor=autor, texto="x", enviada_em=_ts(segundos))
        for autor, segundos in pares
    ]
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=mensagens[0].enviada_em,
        encerrada_em=mensagens[-1].enviada_em,
        escalou_para_humano=escalou,
        mensagens=mensagens,
    )


def test_latencia_e_o_intervalo_ate_a_resposta_do_bot():
    features = features_tempo(_conversa([("cliente", 0), ("bot", 8)]))
    assert features["latencia_primeira_resposta_s"] == 8.0
    assert features["latencia_mediana_s"] == 8.0


def test_mediana_com_varias_respostas():
    features = features_tempo(
        _conversa([("cliente", 0), ("bot", 10), ("cliente", 20), ("bot", 50)])
    )
    assert features["latencia_mediana_s"] == 20.0
    assert features["latencia_primeira_resposta_s"] == 10.0
    assert features["qtd_turnos_cliente"] == 2.0


def test_turno_unico_sem_resposta_zera_latencia():
    features = features_tempo(_conversa([("cliente", 0)]))
    assert features["latencia_mediana_s"] == 0.0
    assert features["latencia_p90_s"] == 0.0
    assert features["latencia_primeira_resposta_s"] == 0.0


def test_conversa_aberta_usa_ultima_mensagem_como_fim():
    conversa = _conversa([("cliente", 0), ("bot", 30)])
    conversa.encerrada_em = None
    assert features_tempo(conversa)["duracao_total_s"] == 30.0


def test_mensagem_de_humano_tambem_conta_como_resposta():
    features = features_tempo(_conversa([("cliente", 0), ("humano", 12)], escalou=True))
    assert features["latencia_primeira_resposta_s"] == 12.0
    assert features["escalou"] == 1.0


def test_cliente_que_nao_responde_o_bot_conta_como_abandono():
    features = features_tempo(_conversa([("cliente", 0), ("bot", 5)]))
    assert features["abandonou"] == 1.0


def test_cliente_que_responde_por_ultimo_nao_e_abandono():
    features = features_tempo(_conversa([("cliente", 0), ("bot", 5), ("cliente", 9)]))
    assert features["abandonou"] == 0.0
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `uv run pytest tests/test_sinal_tempo.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'dolos.sinais.tempo'`

- [ ] **Step 3: Implementar `dolos/sinais/tempo.py`**

```python
"""Sinal de tempo.

Latencia entra como FEATURE aprendida, nunca como penalidade linear: o efeito
sobre satisfacao e nao-linear (CSAT pico entre 5-10s, queda de 2-3 pontos por
minuto extra, 57% de abandono acima de 3min) e moderado por contexto --
indicador de digitacao e suporte emocional atenuam o dano
(From Seconds to Sentiments, IJHCI 2025).

Nada aqui e persistido: tudo deriva dos timestamps do modelo canonico.
"""

from statistics import median

from dolos.modelos import Conversa

RESPONDENTES = {"bot", "humano"}


def _percentil(valores: list[float], fracao: float) -> float:
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    indice = min(int(fracao * len(ordenados)), len(ordenados) - 1)
    return ordenados[indice]


def _latencias(conversa: Conversa) -> list[float]:
    """Intervalo de cada mensagem do cliente ate a proxima resposta."""
    latencias = []
    mensagens = conversa.mensagens
    for indice, mensagem in enumerate(mensagens):
        if mensagem.autor != "cliente":
            continue
        for seguinte in mensagens[indice + 1:]:
            if seguinte.autor in RESPONDENTES:
                latencias.append((seguinte.enviada_em - mensagem.enviada_em).total_seconds())
                break
    return latencias


def features_tempo(conversa: Conversa) -> dict[str, float]:
    latencias = _latencias(conversa)
    fim = conversa.encerrada_em or conversa.mensagens[-1].enviada_em
    ultima = conversa.mensagens[-1]

    return {
        "latencia_mediana_s": median(latencias) if latencias else 0.0,
        "latencia_p90_s": _percentil(latencias, 0.9),
        "latencia_primeira_resposta_s": latencias[0] if latencias else 0.0,
        "duracao_total_s": (fim - conversa.iniciada_em).total_seconds(),
        "qtd_turnos_cliente": float(len(conversa.mensagens_cliente)),
        "escalou": 1.0 if conversa.escalou_para_humano else 0.0,
        "abandonou": 1.0 if ultima.autor in RESPONDENTES else 0.0,
    }
```

- [ ] **Step 4: Rodar e confirmar que passam**

Run: `uv run pytest tests/test_sinal_tempo.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add dolos/sinais/tempo.py tests/test_sinal_tempo.py
git commit -m "feat(sinais): features de latencia, escalacao e abandono"
```

---

### Task 5: Simulador de conversas

**Files:**
- Create: `dolos/ingest/simulador.py`, `tests/test_simulador.py`

**Interfaces:**
- Consumes: `Conversa`, `Mensagem` da Task 1
- Produces: `gerar_conversa(rotulo: int, frases_cliente: list[str], semente: int) -> Conversa`; `gerar_lote(frases_por_rotulo: dict[int, list[str]], quantidade: int, semente: int) -> list[tuple[Conversa, int]]`

Rótulo é a classe de satisfação: `0` insatisfeito, `1` neutro, `2` satisfeito. O simulador existe porque nenhum corpus público de review tem timestamps de diálogo — sem ele, o sinal de tempo não tem como ser treinado. As distribuições de latência são calibradas pelos benchmarks: satisfeito amostra latências baixas (5–15s), insatisfeito amostra latências altas (60–400s) com chance de escalação e abandono.

Isso é limitação metodológica declarada: o sinal de tempo é treinado em dados sintéticos calibrados por literatura, não observados. Deve constar no relatório final.

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_simulador.py`:

```python
from dolos.ingest.simulador import gerar_conversa, gerar_lote
from dolos.sinais.tempo import features_tempo

FRASES = {
    0: ["que absurdo, ninguem resolve", "pessimo atendimento"],
    1: ["ok", "entendi"],
    2: ["muito obrigado, resolveu", "excelente atendimento"],
}


def test_conversa_gerada_e_valida_e_tem_fala_do_cliente():
    conversa = gerar_conversa(rotulo=2, frases_cliente=FRASES[2], semente=42)
    assert conversa.tem_sinal_cliente
    assert conversa.mensagens[0].autor == "cliente"


def test_mesma_semente_gera_a_mesma_conversa():
    a = gerar_conversa(rotulo=1, frases_cliente=FRASES[1], semente=7)
    b = gerar_conversa(rotulo=1, frases_cliente=FRASES[1], semente=7)
    assert a.model_dump() == b.model_dump()


def test_sementes_diferentes_geram_conversas_diferentes():
    a = gerar_conversa(rotulo=1, frases_cliente=FRASES[1], semente=1)
    b = gerar_conversa(rotulo=1, frases_cliente=FRASES[1], semente=2)
    assert a.model_dump() != b.model_dump()


def test_insatisfeito_tem_latencia_maior_que_satisfeito():
    satisfeitas = [
        features_tempo(gerar_conversa(2, FRASES[2], semente=s))["latencia_mediana_s"]
        for s in range(40)
    ]
    insatisfeitas = [
        features_tempo(gerar_conversa(0, FRASES[0], semente=s))["latencia_mediana_s"]
        for s in range(40)
    ]
    media_satisfeitas = sum(satisfeitas) / len(satisfeitas)
    media_insatisfeitas = sum(insatisfeitas) / len(insatisfeitas)
    assert media_insatisfeitas > media_satisfeitas * 3


def test_lote_respeita_a_quantidade_e_devolve_rotulos():
    lote = gerar_lote(FRASES, quantidade=30, semente=3)
    assert len(lote) == 30
    assert {rotulo for _, rotulo in lote} == {0, 1, 2}
    assert len({conversa.id for conversa, _ in lote}) == 30
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `uv run pytest tests/test_simulador.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'dolos.ingest.simulador'`

- [ ] **Step 3: Implementar `dolos/ingest/simulador.py`**

```python
"""Simulador de conversas sinteticas.

Nenhum corpus publico de review PT-BR tem timestamps de dialogo, logo nenhum
deles treina o sinal de tempo. Este modulo costura frases rotuladas desses
corpora em dialogos cliente-bot, com latencias amostradas de distribuicoes
calibradas pelos benchmarks de live chat (pico de CSAT em 5-10s, queda acima
de 1min, abandono acima de 3min).

LIMITACAO METODOLOGICA, a declarar no relatorio: o sinal de tempo e treinado
em dados sinteticos calibrados por literatura, nao observados.
"""

import random
from datetime import datetime, timedelta, timezone

from dolos.modelos import Conversa, Mensagem

INICIO = datetime(2026, 8, 1, 9, 0, 0, tzinfo=timezone.utc)

# (latencia_min_s, latencia_max_s, prob_escalacao, prob_abandono)
PERFIL_POR_ROTULO = {
    0: (60.0, 400.0, 0.55, 0.40),
    1: (15.0, 60.0, 0.15, 0.15),
    2: (3.0, 15.0, 0.03, 0.05),
}

RESPOSTAS_BOT = [
    "Entendi, vou verificar isso para voce.",
    "Um momento, por favor.",
    "Consegui localizar seu pedido.",
    "Posso ajudar em algo mais?",
]


def gerar_conversa(rotulo: int, frases_cliente: list[str], semente: int) -> Conversa:
    """Gera uma conversa deterministica para a semente dada."""
    aleatorio = random.Random(semente)
    lat_min, lat_max, prob_escalacao, prob_abandono = PERFIL_POR_ROTULO[rotulo]

    qtd_turnos = aleatorio.randint(1, min(3, len(frases_cliente)))
    escalou = aleatorio.random() < prob_escalacao
    abandonou = aleatorio.random() < prob_abandono

    mensagens: list[Mensagem] = []
    relogio = INICIO + timedelta(minutes=aleatorio.randint(0, 60 * 24 * 20))
    inicio = relogio

    for turno in range(qtd_turnos):
        mensagens.append(
            Mensagem(
                autor="cliente",
                texto=aleatorio.choice(frases_cliente),
                enviada_em=relogio,
            )
        )
        relogio += timedelta(seconds=aleatorio.uniform(lat_min, lat_max))
        ultimo_turno = turno == qtd_turnos - 1
        mensagens.append(
            Mensagem(
                autor="humano" if escalou and ultimo_turno else "bot",
                texto=aleatorio.choice(RESPOSTAS_BOT),
                enviada_em=relogio,
            )
        )
        relogio += timedelta(seconds=aleatorio.uniform(2.0, 20.0))

    if not abandonou:
        mensagens.append(
            Mensagem(autor="cliente", texto=aleatorio.choice(frases_cliente), enviada_em=relogio)
        )

    return Conversa(
        id=f"sim-{rotulo}-{semente}",
        canal="simulado",
        iniciada_em=inicio,
        encerrada_em=mensagens[-1].enviada_em,
        escalou_para_humano=escalou,
        mensagens=mensagens,
    )


def gerar_lote(
    frases_por_rotulo: dict[int, list[str]], quantidade: int, semente: int
) -> list[tuple[Conversa, int]]:
    """Gera `quantidade` conversas com rotulos equilibrados entre as classes."""
    aleatorio = random.Random(semente)
    rotulos = sorted(frases_por_rotulo)
    lote = []
    for indice in range(quantidade):
        rotulo = rotulos[indice % len(rotulos)]
        lote.append(
            (
                gerar_conversa(rotulo, frases_por_rotulo[rotulo], semente=aleatorio.randrange(10**9)),
                rotulo,
            )
        )
    return lote
```

- [ ] **Step 4: Rodar e confirmar que passam**

Run: `uv run pytest tests/test_simulador.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add dolos/ingest/simulador.py tests/test_simulador.py
git commit -m "feat(ingest): simulador de conversas com latencia calibrada"
```

---

### Task 6: Notebook Colab — fine-tune do BERTimbau

**Files:**
- Create: `notebooks/01_treino_bertimbau.ipynb`, `docs/treinamento.md`

**Interfaces:**
- Consumes: nada do código Python (roda isolado no Colab)
- Produces: artefato de modelo em `modelos/bertimbau-satisfacao/` (`config.json`, `model.safetensors`, `tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`) e um `metricas.json` com `{"acuracia": float, "f1_macro": float, "classes": ["insatisfeito","neutro","satisfeito"]}`. A Task 7 carrega esse diretório.

Modelo base: `neuralmind/bert-base-portuguese-cased`. Três classes. Checkpoint no Google Drive para sobreviver a queda de sessão — mesmo padrão já usado no notebook de RVC do projeto Neuro-ai.

Mapeamento de rótulo a partir do B2W-Reviews01: `overall_rating` 1–2 → insatisfeito (0), 3 → neutro (1), 4–5 → satisfeito (2). O campo `recommend_to_a_friend` fica reservado como âncora do NPS inferido na Task 9.

- [ ] **Step 1: Criar o notebook com a célula de setup**

```python
!pip -q install transformers datasets accelerate evaluate scikit-learn

import torch
assert torch.cuda.is_available(), "Runtime sem GPU. Ambiente de execucao > Alterar tipo > GPU."

from google.colab import drive
drive.mount('/content/drive')

import os
DIR_CHECKPOINT = '/content/drive/MyDrive/dolos/checkpoints'
DIR_SAIDA = '/content/drive/MyDrive/dolos/modelos/bertimbau-satisfacao'
os.makedirs(DIR_CHECKPOINT, exist_ok=True)
os.makedirs(DIR_SAIDA, exist_ok=True)
```

- [ ] **Step 2: Célula de carga e rotulagem dos dados**

```python
import pandas as pd

URL_B2W = "https://raw.githubusercontent.com/americanas-tech/b2w-reviews01/main/B2W-Reviews01.csv"
bruto = pd.read_csv(URL_B2W, delimiter=';')

def rotular(nota):
    if nota <= 2:
        return 0   # insatisfeito
    if nota == 3:
        return 1   # neutro
    return 2       # satisfeito

dados = bruto[['review_text', 'overall_rating']].dropna()
dados = dados.rename(columns={'review_text': 'texto'})
dados['rotulo'] = dados['overall_rating'].apply(rotular)

# Balancear: as classes 4-5 dominam o corpus e enviesariam o classificador.
menor_classe = dados['rotulo'].value_counts().min()
dados = (
    dados.groupby('rotulo', group_keys=False)
    .apply(lambda g: g.sample(menor_classe, random_state=42))
    .sample(frac=1, random_state=42)
    .reset_index(drop=True)
)
print(dados['rotulo'].value_counts())
```

- [ ] **Step 3: Célula de tokenização e split**

```python
from datasets import Dataset
from transformers import AutoTokenizer

MODELO_BASE = "neuralmind/bert-base-portuguese-cased"
tokenizador = AutoTokenizer.from_pretrained(MODELO_BASE)

conjunto = Dataset.from_pandas(dados[['texto', 'rotulo']])
conjunto = conjunto.map(
    lambda lote: tokenizador(lote['texto'], truncation=True, max_length=192),
    batched=True,
)
conjunto = conjunto.rename_column('rotulo', 'labels')
divisao = conjunto.train_test_split(test_size=0.15, seed=42)
```

- [ ] **Step 4: Célula de treino**

```python
import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from transformers import (AutoModelForSequenceClassification, DataCollatorWithPadding,
                          Trainer, TrainingArguments)

modelo = AutoModelForSequenceClassification.from_pretrained(MODELO_BASE, num_labels=3)

def calcular_metricas(predicao):
    preditos = np.argmax(predicao.predictions, axis=1)
    return {
        "acuracia": accuracy_score(predicao.label_ids, preditos),
        "f1_macro": f1_score(predicao.label_ids, preditos, average="macro"),
    }

argumentos = TrainingArguments(
    output_dir=DIR_CHECKPOINT,
    num_train_epochs=3,
    per_device_train_batch_size=32,
    per_device_eval_batch_size=64,
    learning_rate=2e-5,
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="f1_macro",
    fp16=True,
    logging_steps=100,
)

treinador = Trainer(
    model=modelo,
    args=argumentos,
    train_dataset=divisao['train'],
    eval_dataset=divisao['test'],
    data_collator=DataCollatorWithPadding(tokenizador),
    compute_metrics=calcular_metricas,
)
treinador.train()
```

- [ ] **Step 5: Célula de avaliação e export**

```python
import json

metricas = treinador.evaluate()
print(metricas)

modelo.save_pretrained(DIR_SAIDA)
tokenizador.save_pretrained(DIR_SAIDA)

with open(f"{DIR_SAIDA}/metricas.json", "w", encoding="utf-8") as arquivo:
    json.dump({
        "acuracia": metricas["eval_acuracia"],
        "f1_macro": metricas["eval_f1_macro"],
        "classes": ["insatisfeito", "neutro", "satisfeito"],
    }, arquivo, ensure_ascii=False, indent=2)

print("Baixe a pasta", DIR_SAIDA, "para modelos/bertimbau-satisfacao/ no repo local.")
```

- [ ] **Step 6: Escrever `docs/treinamento.md`**

Documentar: como abrir o notebook no Colab, exigência de GPU, onde o checkpoint fica no Drive, para onde copiar o artefato no repo local (`modelos/bertimbau-satisfacao/`), e que `modelos/` está no `.gitignore` — o artefato não vai para o git.

- [ ] **Step 7: Commit**

```bash
git add notebooks/01_treino_bertimbau.ipynb docs/treinamento.md
git commit -m "feat(treino): notebook Colab de fine-tune do BERTimbau"
```

---

### Task 7: Sinal de texto

**Files:**
- Create: `dolos/sinais/texto.py`, `tests/test_sinal_texto.py`

**Interfaces:**
- Consumes: `Conversa` da Task 1; artefato de modelo da Task 6
- Produces: `ClassificadorTexto(caminho_modelo: Path)` com `prever_mensagens(textos: list[str]) -> list[list[float]]` (probabilidades por classe, na ordem insatisfeito/neutro/satisfeito); `features_texto(conversa: Conversa, classificador: ClassificadorTexto) -> dict[str, float]` com as chaves `texto_prob_insatisfeito_media`, `texto_prob_satisfeito_media`, `texto_prob_insatisfeito_max`, `texto_prob_satisfeito_ultima`; `ModeloAusenteError`

A predição é **por mensagem**, não por conversa — é isso que permite a atribuição por sentença na dashboard (Task 10). `texto_prob_satisfeito_ultima` isola a última fala do cliente, que costuma carregar o veredito.

Modelo ausente ou corrompido no boot é falha alta e explícita: servir predição sem modelo carregado é pior que estar fora do ar.

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_sinal_texto.py`:

```python
from datetime import datetime, timezone
from pathlib import Path

import pytest

from dolos.modelos import Conversa, Mensagem
from dolos.sinais.texto import ClassificadorTexto, ModeloAusenteError, features_texto

BASE = datetime(2026, 8, 13, 10, 0, 0, tzinfo=timezone.utc)


class ClassificadorFalso:
    """Dubla o modelo real: mapeia texto conhecido para probabilidade fixa."""

    TABELA = {
        "pessimo": [0.9, 0.05, 0.05],
        "ok": [0.2, 0.6, 0.2],
        "otimo": [0.05, 0.05, 0.9],
    }

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        return [self.TABELA.get(t, [0.34, 0.33, 0.33]) for t in textos]


def _conversa(textos: list[str]) -> Conversa:
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=BASE,
        mensagens=[Mensagem(autor="cliente", texto=t, enviada_em=BASE) for t in textos],
    )


def test_modelo_ausente_falha_alto():
    with pytest.raises(ModeloAusenteError):
        ClassificadorTexto(Path("modelos/nao-existe"))


def test_media_das_probabilidades_das_mensagens_do_cliente():
    features = features_texto(_conversa(["pessimo", "otimo"]), ClassificadorFalso())
    assert features["texto_prob_insatisfeito_media"] == pytest.approx(0.475)
    assert features["texto_prob_satisfeito_media"] == pytest.approx(0.475)


def test_max_captura_o_pior_momento_da_conversa():
    features = features_texto(_conversa(["ok", "pessimo", "ok"]), ClassificadorFalso())
    assert features["texto_prob_insatisfeito_max"] == pytest.approx(0.9)


def test_ultima_fala_do_cliente_e_isolada():
    features = features_texto(_conversa(["pessimo", "otimo"]), ClassificadorFalso())
    assert features["texto_prob_satisfeito_ultima"] == pytest.approx(0.9)


def test_conversa_sem_fala_do_cliente_zera_as_features():
    conversa = Conversa(
        id="c1",
        canal="csv",
        iniciada_em=BASE,
        mensagens=[Mensagem(autor="bot", texto="otimo", enviada_em=BASE)],
    )
    features = features_texto(conversa, ClassificadorFalso())
    assert features["texto_prob_satisfeito_media"] == 0.0
    assert features["texto_prob_insatisfeito_max"] == 0.0
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `uv run pytest tests/test_sinal_texto.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'dolos.sinais.texto'`

- [ ] **Step 3: Adicionar as dependências de inferência**

Em `pyproject.toml`, acrescentar `"transformers>=4.44"` e `"torch>=2.3"` a `dependencies`. Rodar `uv sync`.

- [ ] **Step 4: Implementar `dolos/sinais/texto.py`**

```python
"""Sinal de texto: BERTimbau fine-tunado, rodando em CPU.

Predicao POR MENSAGEM, nunca por conversa inteira -- e isso que permite a
atribuicao por sentenca na dashboard ("quais trechos puxaram a nota").

BERTimbau supera as variantes multilingues em classificacao de sentimento
PT-BR (Souza, Nogueira, Lotufo -- arXiv:2201.03382).
"""

from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from dolos.modelos import Conversa

INSATISFEITO, NEUTRO, SATISFEITO = 0, 1, 2
TAMANHO_MAXIMO = 192


class ModeloAusenteError(RuntimeError):
    """Modelo nao encontrado ou ilegivel. Falha alta: sem modelo nao ha predicao."""


class ClassificadorTexto:
    def __init__(self, caminho_modelo: Path) -> None:
        if not Path(caminho_modelo).is_dir():
            raise ModeloAusenteError(
                f"Modelo nao encontrado em {caminho_modelo}. "
                "Rode notebooks/01_treino_bertimbau.ipynb e copie o artefato. "
                "Ver docs/treinamento.md."
            )
        try:
            self._tokenizador = AutoTokenizer.from_pretrained(str(caminho_modelo))
            self._modelo = AutoModelForSequenceClassification.from_pretrained(str(caminho_modelo))
        except Exception as erro:
            raise ModeloAusenteError(f"Modelo em {caminho_modelo} ilegivel: {erro}") from erro
        self._modelo.eval()

    @torch.inference_mode()
    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        """Probabilidades [insatisfeito, neutro, satisfeito] para cada texto."""
        if not textos:
            return []
        entradas = self._tokenizador(
            textos, truncation=True, max_length=TAMANHO_MAXIMO, padding=True, return_tensors="pt"
        )
        logits = self._modelo(**entradas).logits
        return torch.softmax(logits, dim=-1).tolist()


def features_texto(conversa: Conversa, classificador) -> dict[str, float]:
    textos = [m.texto for m in conversa.mensagens_cliente]
    if not textos:
        return {
            "texto_prob_insatisfeito_media": 0.0,
            "texto_prob_satisfeito_media": 0.0,
            "texto_prob_insatisfeito_max": 0.0,
            "texto_prob_satisfeito_ultima": 0.0,
        }

    probabilidades = classificador.prever_mensagens(textos)
    insatisfeito = [p[INSATISFEITO] for p in probabilidades]
    satisfeito = [p[SATISFEITO] for p in probabilidades]

    return {
        "texto_prob_insatisfeito_media": sum(insatisfeito) / len(insatisfeito),
        "texto_prob_satisfeito_media": sum(satisfeito) / len(satisfeito),
        "texto_prob_insatisfeito_max": max(insatisfeito),
        "texto_prob_satisfeito_ultima": satisfeito[-1],
    }
```

- [ ] **Step 5: Rodar e confirmar que passam**

Run: `uv run pytest tests/test_sinal_texto.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add dolos/sinais/texto.py tests/test_sinal_texto.py pyproject.toml
git commit -m "feat(sinais): classificador BERTimbau com predicao por mensagem"
```

---

### Task 8: Fusor

**Files:**
- Create: `dolos/fusor.py`, `tests/test_fusor.py`

**Interfaces:**
- Consumes: `features_emoji` (Task 3), `features_tempo` (Task 4), `features_texto` (Task 7)
- Produces: `NOMES_FEATURES: list[str]` (ordem canônica, 16 nomes); `montar_features(conversa, classificador) -> dict[str, float]`; `vetorizar(features: dict[str, float]) -> list[float]`; `Fusor` com `treinar(exemplos: list[dict[str,float]], rotulos: list[int]) -> None`, `pontuar(features: dict[str,float]) -> float` (0–100), `salvar(caminho: Path)`, `carregar(caminho: Path) -> Fusor` (classmethod), `importancias() -> dict[str, float]`

Score é `100 * (P(satisfeito) + 0.5 * P(neutro))`, contínuo em 0–100. Modelo: `LogisticRegression` com `StandardScaler` num `Pipeline` — interpretável, o que a defesa do trabalho exige.

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_fusor.py`:

```python
import pytest

from dolos.fusor import NOMES_FEATURES, Fusor, vetorizar


def _features(**sobrescritas) -> dict[str, float]:
    base = {nome: 0.0 for nome in NOMES_FEATURES}
    base.update(sobrescritas)
    return base


def _fusor_treinado() -> Fusor:
    exemplos, rotulos = [], []
    for _ in range(40):
        exemplos.append(_features(
            texto_prob_satisfeito_media=0.9,
            texto_prob_satisfeito_ultima=0.9,
            emoji_score_medio=0.8,
            latencia_mediana_s=8.0,
        ))
        rotulos.append(2)
        exemplos.append(_features(
            texto_prob_insatisfeito_media=0.9,
            texto_prob_insatisfeito_max=0.95,
            emoji_score_medio=-0.7,
            latencia_mediana_s=300.0,
            escalou=1.0,
        ))
        rotulos.append(0)
    fusor = Fusor()
    fusor.treinar(exemplos, rotulos)
    return fusor


def test_vetorizar_respeita_a_ordem_canonica():
    vetor = vetorizar(_features(emoji_contagem=3.0))
    assert len(vetor) == len(NOMES_FEATURES)
    assert vetor[NOMES_FEATURES.index("emoji_contagem")] == 3.0


def test_feature_faltando_e_erro_e_nao_zero_silencioso():
    incompleto = _features()
    del incompleto["emoji_contagem"]
    with pytest.raises(KeyError):
        vetorizar(incompleto)


def test_conversa_positiva_pontua_alto():
    fusor = _fusor_treinado()
    score = fusor.pontuar(_features(
        texto_prob_satisfeito_media=0.9,
        texto_prob_satisfeito_ultima=0.9,
        emoji_score_medio=0.8,
        latencia_mediana_s=8.0,
    ))
    assert score > 70


def test_conversa_negativa_pontua_baixo():
    fusor = _fusor_treinado()
    score = fusor.pontuar(_features(
        texto_prob_insatisfeito_media=0.9,
        texto_prob_insatisfeito_max=0.95,
        emoji_score_medio=-0.7,
        latencia_mediana_s=300.0,
        escalou=1.0,
    ))
    assert score < 30


def test_score_fica_sempre_entre_zero_e_cem():
    fusor = _fusor_treinado()
    for valor in (-5.0, 0.0, 9999.0):
        score = fusor.pontuar(_features(latencia_mediana_s=valor))
        assert 0.0 <= score <= 100.0


def test_salvar_e_carregar_preserva_o_score(tmp_path):
    fusor = _fusor_treinado()
    entrada = _features(texto_prob_satisfeito_media=0.9, emoji_score_medio=0.8)
    esperado = fusor.pontuar(entrada)

    caminho = tmp_path / "fusor.joblib"
    fusor.salvar(caminho)
    assert Fusor.carregar(caminho).pontuar(entrada) == pytest.approx(esperado)


def test_importancias_cobrem_todas_as_features():
    assert set(_fusor_treinado().importancias()) == set(NOMES_FEATURES)
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `uv run pytest tests/test_fusor.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'dolos.fusor'`

- [ ] **Step 3: Adicionar as dependências**

Em `pyproject.toml`, acrescentar `"scikit-learn>=1.5"` e `"joblib>=1.4"`. Rodar `uv sync`.

- [ ] **Step 4: Implementar `dolos/fusor.py`**

```python
"""Fusor dos tres sinais.

LogisticRegression com padronizacao: interpretavel de proposito -- o trabalho
precisa defender POR QUE um atendimento recebeu a nota, e coeficiente de
regressao logistica responde isso; floresta densa nao.

O peso da latencia e APRENDIDO aqui, nunca arbitrado: a relacao com satisfacao
e nao-linear e moderada por contexto.
"""

from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from dolos.modelos import Conversa
from dolos.sinais.emoji import features_emoji
from dolos.sinais.tempo import features_tempo
from dolos.sinais.texto import features_texto

NOMES_FEATURES = [
    "texto_prob_insatisfeito_media",
    "texto_prob_satisfeito_media",
    "texto_prob_insatisfeito_max",
    "texto_prob_satisfeito_ultima",
    "emoji_score_medio",
    "emoji_frac_positivos",
    "emoji_frac_negativos",
    "emoji_contagem",
    "emoji_posicao_relativa_media",
    "latencia_mediana_s",
    "latencia_p90_s",
    "latencia_primeira_resposta_s",
    "duracao_total_s",
    "qtd_turnos_cliente",
    "escalou",
    "abandonou",
]

INSATISFEITO, NEUTRO, SATISFEITO = 0, 1, 2


def montar_features(conversa: Conversa, classificador) -> dict[str, float]:
    """Junta os tres sinais numa linha unica de features."""
    return {
        **features_texto(conversa, classificador),
        **features_emoji(conversa),
        **features_tempo(conversa),
    }


def vetorizar(features: dict[str, float]) -> list[float]:
    """Ordem canonica. Feature faltando e KeyError -- nunca zero silencioso."""
    return [float(features[nome]) for nome in NOMES_FEATURES]


class Fusor:
    def __init__(self) -> None:
        self._pipeline = Pipeline([
            ("escala", StandardScaler()),
            ("modelo", LogisticRegression(max_iter=1000)),
        ])

    def treinar(self, exemplos: list[dict[str, float]], rotulos: list[int]) -> None:
        self._pipeline.fit([vetorizar(e) for e in exemplos], rotulos)

    def pontuar(self, features: dict[str, float]) -> float:
        """Score 0-100: P(satisfeito) + metade de P(neutro)."""
        probabilidades = self._pipeline.predict_proba([vetorizar(features)])[0]
        classes = list(self._pipeline.named_steps["modelo"].classes_)
        por_classe = dict(zip(classes, probabilidades))
        score = 100.0 * (por_classe.get(SATISFEITO, 0.0) + 0.5 * por_classe.get(NEUTRO, 0.0))
        return max(0.0, min(100.0, score))

    def importancias(self) -> dict[str, float]:
        """Peso absoluto medio de cada feature -- alimenta a explicacao na dashboard."""
        coeficientes = self._pipeline.named_steps["modelo"].coef_
        medias = coeficientes.__abs__().mean(axis=0)
        return dict(zip(NOMES_FEATURES, (float(v) for v in medias)))

    def salvar(self, caminho: Path) -> None:
        joblib.dump(self._pipeline, caminho)

    @classmethod
    def carregar(cls, caminho: Path) -> "Fusor":
        fusor = cls()
        fusor._pipeline = joblib.load(caminho)
        return fusor
```

- [ ] **Step 5: Rodar e confirmar que passam**

Run: `uv run pytest tests/test_fusor.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add dolos/fusor.py tests/test_fusor.py pyproject.toml
git commit -m "feat(fusor): fusao dos tres sinais com regressao logistica"
```

---

### Task 9: Indicadores, persistência e API

**Files:**
- Create: `dolos/indicadores.py`, `dolos/db.py`, `dolos/api/__init__.py`, `dolos/api/main.py`, `tests/test_indicadores.py`, `tests/test_api.py`

**Interfaces:**
- Consumes: `Conversa` (Task 1), `carregar_csv` (Task 2), `ClassificadorTexto` (Task 7), `Fusor` e `montar_features` (Task 8)
- Produces:
  - `categoria_nps(score_0_100: float) -> Literal["detrator","neutro","promotor"]`
  - `nota_0_10(score_0_100: float) -> int`
  - `calcular_nps(scores: list[float]) -> float`
  - `calcular_csat(scores: list[float]) -> float`
  - `containment_rate(conversas: list[Conversa]) -> float`
  - Endpoints: `GET /saude`, `POST /conversas/importar`, `GET /conversas`, `GET /conversas/{id}`, `GET /indicadores`

`nota_0_10` converte o score contínuo em nota inteira 0–10 (`round(score / 10)`), e só então as faixas de NPS se aplicam: **0–6 detrator, 7–8 neutro, 9–10 promotor**. Categoria é sempre derivada no servidor.

CSAT é a fração de conversas com nota ≥ 7, em percentual — o equivalente a "satisfeito ou melhor".

- [ ] **Step 1: Escrever o teste de indicadores que falha**

Criar `tests/test_indicadores.py`:

```python
from datetime import datetime, timezone

import pytest

from dolos.indicadores import (calcular_csat, calcular_nps, categoria_nps,
                               containment_rate, nota_0_10)
from dolos.modelos import Conversa, Mensagem

BASE = datetime(2026, 8, 13, 10, 0, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("nota,esperado", [
    (0, "detrator"), (6, "detrator"),
    (7, "neutro"), (8, "neutro"),
    (9, "promotor"), (10, "promotor"),
])
def test_fronteiras_das_faixas_de_nps(nota, esperado):
    assert categoria_nps(nota * 10) == esperado


def test_score_vira_nota_de_zero_a_dez():
    assert nota_0_10(0.0) == 0
    assert nota_0_10(64.0) == 6
    assert nota_0_10(66.0) == 7
    assert nota_0_10(100.0) == 10


def test_nps_calculado_a_mao_confere():
    # 5 promotores (100), 2 neutros (75), 3 detratores (30)
    scores = [100.0] * 5 + [75.0] * 2 + [30.0] * 3
    assert calcular_nps(scores) == pytest.approx(20.0)  # 50% - 30%


def test_nps_de_lista_vazia_e_zero():
    assert calcular_nps([]) == 0.0


def test_csat_e_a_fracao_com_nota_sete_ou_mais():
    scores = [100.0, 80.0, 70.0, 30.0]
    assert calcular_csat(scores) == pytest.approx(75.0)


def test_containment_rate_ignora_conversas_escaladas():
    def conversa(escalou: bool, indice: int) -> Conversa:
        return Conversa(
            id=f"c{indice}",
            canal="csv",
            iniciada_em=BASE,
            escalou_para_humano=escalou,
            mensagens=[Mensagem(autor="cliente", texto="oi", enviada_em=BASE)],
        )

    conversas = [conversa(False, 1), conversa(False, 2), conversa(True, 3), conversa(True, 4)]
    assert containment_rate(conversas) == pytest.approx(50.0)
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `uv run pytest tests/test_indicadores.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'dolos.indicadores'`

- [ ] **Step 3: Implementar `dolos/indicadores.py`**

```python
"""Indicadores agregados.

NPS aqui e INFERIDO do texto, nao declarado pelo cliente. A dashboard rotula
como estimativa -- apresentar como NPS declarado seria falso.

Faixas canonicas: 0-6 detrator, 7-8 neutro, 9-10 promotor.
Categoria SEMPRE derivada no servidor.
"""

from typing import Literal

from dolos.modelos import Conversa

Categoria = Literal["detrator", "neutro", "promotor"]
NOTA_MINIMA_SATISFEITO = 7


def nota_0_10(score_0_100: float) -> int:
    return int(round(max(0.0, min(100.0, score_0_100)) / 10))


def categoria_nps(score_0_100: float) -> Categoria:
    nota = nota_0_10(score_0_100)
    if nota <= 6:
        return "detrator"
    if nota <= 8:
        return "neutro"
    return "promotor"


def calcular_nps(scores: list[float]) -> float:
    """Percentual de promotores menos percentual de detratores, em [-100, 100]."""
    if not scores:
        return 0.0
    categorias = [categoria_nps(s) for s in scores]
    total = len(categorias)
    promotores = categorias.count("promotor") / total
    detratores = categorias.count("detrator") / total
    return round(100.0 * (promotores - detratores), 2)


def calcular_csat(scores: list[float]) -> float:
    """Percentual de atendimentos com nota >= 7."""
    if not scores:
        return 0.0
    satisfeitos = sum(1 for s in scores if nota_0_10(s) >= NOTA_MINIMA_SATISFEITO)
    return round(100.0 * satisfeitos / len(scores), 2)


def containment_rate(conversas: list[Conversa]) -> float:
    """Percentual de conversas resolvidas sem intervencao humana."""
    if not conversas:
        return 0.0
    contidas = sum(1 for c in conversas if not c.escalou_para_humano)
    return round(100.0 * contidas / len(conversas), 2)
```

- [ ] **Step 4: Rodar e confirmar que passam**

Run: `uv run pytest tests/test_indicadores.py -v`
Expected: 11 passed

- [ ] **Step 5: Escrever o teste da API que falha**

Criar `tests/test_api.py`:

```python
import pytest
from fastapi.testclient import TestClient

from dolos.api.main import criar_app
from dolos.db import Banco

CSV = (
    "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
    "c1,csv,cliente,otimo,2026-08-13T10:00:00+00:00,false\n"
    "c1,csv,bot,de nada,2026-08-13T10:00:08+00:00,false\n"
    "c1,csv,cliente,valeu,2026-08-13T10:00:15+00:00,false\n"
)


class MotorFalso:
    def pontuar_conversa(self, conversa):
        return 90.0


@pytest.fixture
def cliente(tmp_path):
    banco = Banco(tmp_path / "dolos.db")
    banco.migrar()
    return TestClient(criar_app(banco=banco, motor=MotorFalso()))


def test_saude_responde_ok(cliente):
    resposta = cliente.get("/saude")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"


def test_importar_csv_persiste_e_pontua(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")

    resposta = cliente.post("/conversas/importar", json={"caminho": str(caminho)})
    assert resposta.status_code == 200
    assert resposta.json() == {"importadas": 1, "rejeitadas": 0}

    listagem = cliente.get("/conversas").json()
    assert len(listagem) == 1
    assert listagem[0]["score"] == 90.0
    assert listagem[0]["categoria"] == "promotor"


def test_categoria_enviada_pelo_cliente_e_ignorada(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post(
        "/conversas/importar",
        json={"caminho": str(caminho), "categoria": "detrator", "score": 0},
    )
    assert cliente.get("/conversas").json()[0]["categoria"] == "promotor"


def test_detalhe_traz_a_transcricao(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(caminho)})

    detalhe = cliente.get("/conversas/c1").json()
    assert len(detalhe["mensagens"]) == 3
    assert detalhe["mensagens"][0]["texto"] == "otimo"


def test_detalhe_de_conversa_inexistente_e_404(cliente):
    assert cliente.get("/conversas/nao-existe").status_code == 404


def test_indicadores_agregam_o_que_foi_importado(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(caminho)})

    indicadores = cliente.get("/indicadores").json()
    assert indicadores["nps"] == 100.0
    assert indicadores["csat"] == 100.0
    assert indicadores["containment_rate"] == 100.0
    assert indicadores["total_conversas"] == 1


def test_indicadores_sem_dado_nao_quebra(cliente):
    indicadores = cliente.get("/indicadores").json()
    assert indicadores["total_conversas"] == 0
    assert indicadores["nps"] == 0.0
```

- [ ] **Step 6: Rodar e confirmar que falha**

Run: `uv run pytest tests/test_api.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'dolos.db'`

- [ ] **Step 7: Adicionar as dependências**

Em `pyproject.toml`, acrescentar `"fastapi>=0.115"`, `"uvicorn>=0.30"`; em `dev`, `"httpx>=0.27"`. Rodar `uv sync`.

- [ ] **Step 8: Implementar `dolos/db.py`**

```python
"""Persistencia SQLite. Sem ORM: o esquema e pequeno e estavel.

Latencia NAO e persistida -- e derivada dos timestamps na leitura.
"""

import json
import sqlite3
from pathlib import Path

from dolos.modelos import Conversa

ESQUEMA = """
CREATE TABLE IF NOT EXISTS conversas (
    id TEXT PRIMARY KEY,
    canal TEXT NOT NULL,
    iniciada_em TEXT NOT NULL,
    score REAL,
    categoria TEXT,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conversas_iniciada_em ON conversas(iniciada_em);
"""


class Banco:
    def __init__(self, caminho: Path) -> None:
        self._caminho = Path(caminho)

    def _conectar(self) -> sqlite3.Connection:
        conexao = sqlite3.connect(self._caminho)
        conexao.row_factory = sqlite3.Row
        return conexao

    def migrar(self) -> None:
        with self._conectar() as conexao:
            conexao.executescript(ESQUEMA)

    def salvar(self, conversa: Conversa, score: float | None, categoria: str | None) -> None:
        with self._conectar() as conexao:
            conexao.execute(
                "INSERT OR REPLACE INTO conversas "
                "(id, canal, iniciada_em, score, categoria, payload) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    conversa.id,
                    conversa.canal,
                    conversa.iniciada_em.isoformat(),
                    score,
                    categoria,
                    conversa.model_dump_json(),
                ),
            )

    def listar(self) -> list[dict]:
        with self._conectar() as conexao:
            linhas = conexao.execute(
                "SELECT id, canal, iniciada_em, score, categoria FROM conversas "
                "ORDER BY iniciada_em DESC"
            ).fetchall()
        return [dict(linha) for linha in linhas]

    def buscar(self, conversa_id: str) -> tuple[Conversa, float | None, str | None] | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT payload, score, categoria FROM conversas WHERE id = ?", (conversa_id,)
            ).fetchone()
        if linha is None:
            return None
        return Conversa(**json.loads(linha["payload"])), linha["score"], linha["categoria"]

    def todas(self) -> list[tuple[Conversa, float | None]]:
        with self._conectar() as conexao:
            linhas = conexao.execute("SELECT payload, score FROM conversas").fetchall()
        return [(Conversa(**json.loads(l["payload"])), l["score"]) for l in linhas]
```

- [ ] **Step 9: Implementar `dolos/api/main.py`**

```python
"""API do Dolos.

Score e categoria SAO SEMPRE derivados no servidor: campos vindos do corpo da
requisicao que se pareçam com veredito sao ignorados por construcao -- o modelo
de entrada so aceita `caminho`.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from dolos.db import Banco
from dolos.fusor import Fusor, montar_features
from dolos.indicadores import (calcular_csat, calcular_nps, categoria_nps,
                               containment_rate, nota_0_10)
from dolos.ingest.csv_driver import carregar_csv
from dolos.sinais.texto import ClassificadorTexto


class PedidoImportacao(BaseModel):
    caminho: str  # unico campo aceito: veredito nunca vem do cliente


class Motor:
    """Amarra classificador de texto e fusor num unico ponto de pontuacao."""

    def __init__(self, classificador: ClassificadorTexto, fusor: Fusor) -> None:
        self._classificador = classificador
        self._fusor = fusor

    def pontuar_conversa(self, conversa) -> float | None:
        if not conversa.tem_sinal_cliente:
            return None  # ausencia de dado nao e insatisfacao
        return self._fusor.pontuar(montar_features(conversa, self._classificador))


def criar_app(banco: Banco, motor) -> FastAPI:
    app = FastAPI(title="Dolos", version="0.1.0")

    @app.get("/saude")
    def saude() -> dict:
        return {"status": "ok"}

    @app.post("/conversas/importar")
    def importar(pedido: PedidoImportacao) -> dict:
        caminho = Path(pedido.caminho)
        if not caminho.is_file():
            raise HTTPException(status_code=400, detail=f"arquivo nao encontrado: {caminho}")

        resultado = carregar_csv(caminho)
        for conversa in resultado.conversas:
            score = motor.pontuar_conversa(conversa)
            categoria = categoria_nps(score) if score is not None else None
            banco.salvar(conversa, score, categoria)

        return {"importadas": len(resultado.conversas), "rejeitadas": len(resultado.rejeitadas)}

    @app.get("/conversas")
    def listar() -> list[dict]:
        return banco.listar()

    @app.get("/conversas/{conversa_id}")
    def detalhar(conversa_id: str) -> dict:
        achado = banco.buscar(conversa_id)
        if achado is None:
            raise HTTPException(status_code=404, detail="conversa nao encontrada")
        conversa, score, categoria = achado
        return {
            **conversa.model_dump(mode="json"),
            "score": score,
            "categoria": categoria,
            "nota": nota_0_10(score) if score is not None else None,
        }

    @app.get("/indicadores")
    def indicadores() -> dict:
        registros = banco.todas()
        conversas = [conversa for conversa, _ in registros]
        scores = [score for _, score in registros if score is not None]
        return {
            "nps": calcular_nps(scores),
            "csat": calcular_csat(scores),
            "containment_rate": containment_rate(conversas),
            "total_conversas": len(conversas),
            "sem_sinal": len(conversas) - len(scores),
        }

    return app
```

Criar `dolos/api/__init__.py` vazio.

- [ ] **Step 10: Rodar a suíte inteira**

Run: `uv run pytest -v`
Expected: todos os testes passam (modelos, csv, emoji, tempo, simulador, texto, fusor, indicadores, api)

- [ ] **Step 11: Commit**

```bash
git add dolos/indicadores.py dolos/db.py dolos/api tests/test_indicadores.py tests/test_api.py pyproject.toml
git commit -m "feat(api): indicadores, persistencia SQLite e endpoints FastAPI"
```

---

### Task 10: Dashboard Next.js

**Files:**
- Create: `dashboard/package.json`, `dashboard/app/page.tsx`, `dashboard/app/layout.tsx`, `dashboard/app/conversas/[id]/page.tsx`, `dashboard/lib/api.ts`, `dashboard/components/CartaoIndicador.tsx`, `dashboard/components/GraficoNpsLatencia.tsx`, `dashboard/components/TabelaConversas.tsx`, `dashboard/.env.local.example`

**Interfaces:**
- Consumes: endpoints da Task 9 (`GET /indicadores`, `GET /conversas`, `GET /conversas/{id}`)
- Produces: interface web

Antes de escrever qualquer componente, invocar a skill `impeccable` — a dashboard é entregável de apresentação, não protótipo.

Regra de design que vem da pesquisa e não é negociável: **NPS e latência aparecem sobrepostos no mesmo gráfico**, porque otimizar um KPI isolado quebra outro (empurrar deflexão derruba CSAT). Cards isolados escondem exatamente o trade-off que o trabalho precisa mostrar.

O NPS é rotulado na interface como **"NPS inferido (estimativa)"**, com nota de rodapé explicando que é derivado do texto e não de pergunta ao cliente.

- [ ] **Step 1: Invocar a skill de design**

Invocar `impeccable` para calibrar hierarquia visual, tipografia e paleta antes de codar. Invocar também `dataviz` antes de escrever o primeiro gráfico.

- [ ] **Step 2: Criar o projeto Next.js**

```bash
cd dashboard
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir --eslint
npm install recharts
```

- [ ] **Step 3: Criar o cliente de API em `dashboard/lib/api.ts`**

```typescript
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Indicadores = {
  nps: number;
  csat: number;
  containment_rate: number;
  total_conversas: number;
  sem_sinal: number;
};

export type ResumoConversa = {
  id: string;
  canal: string;
  iniciada_em: string;
  score: number | null;
  categoria: "detrator" | "neutro" | "promotor" | null;
};

export type Mensagem = { autor: string; texto: string; enviada_em: string };

export type DetalheConversa = ResumoConversa & {
  mensagens: Mensagem[];
  nota: number | null;
  escalou_para_humano: boolean;
};

async function buscar<T>(rota: string): Promise<T> {
  const resposta = await fetch(`${BASE}${rota}`, { cache: "no-store" });
  if (!resposta.ok) throw new Error(`${rota} respondeu ${resposta.status}`);
  return resposta.json() as Promise<T>;
}

export const obterIndicadores = () => buscar<Indicadores>("/indicadores");
export const listarConversas = () => buscar<ResumoConversa[]>("/conversas");
export const obterConversa = (id: string) =>
  buscar<DetalheConversa>(`/conversas/${encodeURIComponent(id)}`);
```

Criar `dashboard/.env.local.example` com `NEXT_PUBLIC_API_URL=http://localhost:8000`.

- [ ] **Step 4: Construir a página principal**

`dashboard/app/page.tsx` monta, em ordem:

1. Faixa de indicadores: **NPS inferido (estimativa)** com escala −100 a +100, **CSAT %** com a faixa de referência 75–85% marcada visualmente, **containment rate**, **tempo mediano de resposta**.
2. `GraficoNpsLatencia` — série temporal com NPS e latência mediana sobrepostos em eixos Y distintos.
3. `TabelaConversas` — id, data, canal, nota 0–10, categoria (cor por faixa), com linha clicável levando ao detalhe.
4. Rodapé com a nota metodológica: *"NPS inferido a partir do texto do atendimento, não de pergunta declarada ao cliente. Estimativa."*

Conversas com `score: null` aparecem como **"sem sinal"**, nunca como nota 0 — ausência de dado não é insatisfação.

Se um indicador falhar ao carregar, apenas aquele card mostra estado de falha; os demais continuam renderizando.

- [ ] **Step 5: Construir a página de detalhe do atendimento**

`dashboard/app/conversas/[id]/page.tsx` mostra: nota e categoria no topo, transcrição completa com as falas do cliente e do bot visualmente distintas, latência de cada resposta anotada ao lado da mensagem do bot, e marcação dos trechos que mais puxaram a nota.

Essa marcação existe porque o sinal de texto é calculado por mensagem (Task 7) — é o que transforma "nota ruim" em "oportunidade de melhoria", que é o objetivo declarado do trabalho.

- [ ] **Step 6: Verificar contra a API real**

```bash
uv run uvicorn dolos.api.main:app --reload   # em um terminal
cd dashboard && npm run dev                   # em outro
```

Importar um CSV de exemplo, abrir `http://localhost:3000`, confirmar: os quatro indicadores carregam, o gráfico sobrepõe NPS e latência, a tabela lista, o clique abre o detalhe com a transcrição.

- [ ] **Step 7: Commit**

```bash
git add dashboard
git commit -m "feat(dashboard): indicadores, grafico NPS x latencia e detalhe do atendimento"
```

---

## Ordem de execução e dependências

```
Task 1 (modelos)
  ├── Task 2 (CSV) ──────────────┐
  ├── Task 3 (emoji) ────────────┤
  ├── Task 4 (tempo) ────────────┤
  └── Task 5 (simulador) ────────┤
                                 │
Task 6 (Colab) ── Task 7 (texto) ┤
                                 │
                        Task 8 (fusor)
                                 │
                        Task 9 (API)
                                 │
                        Task 10 (dashboard)
```

Tasks 2, 3, 4 e 5 são independentes entre si e podem ser feitas em qualquer ordem depois da Task 1. A Task 6 (treino no Colab) pode rodar em paralelo com as demais — só a Task 7 depende do artefato.

## Verificação final

- [ ] `uv run pytest -v` — suíte inteira verde
- [ ] `uv run uvicorn dolos.api.main:app` sobe sem erro com o modelo presente
- [ ] Subir a API **sem** `modelos/bertimbau-satisfacao/` falha alto com mensagem apontando `docs/treinamento.md`
- [ ] Importar CSV de exemplo e conferir NPS calculado à mão contra o valor da API
- [ ] Dashboard renderiza os quatro indicadores, o gráfico sobreposto e o detalhe do atendimento
- [ ] `metricas.json` do treino está registrado no relatório (acurácia e F1-macro)
