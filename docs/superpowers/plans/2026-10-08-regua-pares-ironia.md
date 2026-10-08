# Régua de pares mínimos de ironia — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** um conjunto congelado de pares mínimos de ironia em atendimento, rotulado por humanos às cegas, que entra no laudo com acurácia por par, IC por bootstrap de pares, ECE e um baseline só-estilo.

**Architecture:** parte pura em `fraus/` (métricas por par, baseline de estilo, rascunho e conferência de registro, consolidação da anotação, carga da régua congelada), testada em `tests/`. A anotação acontece numa página privada do claude.ai que recebe só `{id, texto}`; o gabarito nunca sai do repositório. Um script lê as respostas, aplica a regra de entrada e grava os CSVs congelados com a impressão SHA-256.

**Tech Stack:** Python 3.11 via `uv`, numpy, scikit-learn 1.6.1 (já dependência), pytest. Página: HTML/JS publicado como Artifact com banco compartilhado e identidade do visitante.

**Spec:** `docs/superpowers/specs/2026-10-08-regua-pares-ironia-design.md`

## Global Constraints

- Identificadores e docstrings em português, **sem acento nos nomes de símbolo**; texto de interface e de documentação com acento normal.
- Commits em português, sem acento, `tipo(escopo): resumo`, terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- TDD: teste que falha primeiro, implementação mínima, teste verde, commit.
- Nenhuma dependência nova.
- Ordem das classes: `0` não irônico, `1` irônico (`fraus.sinais.ironia.IRONICO == 1`). Nunca redigitar a ordem.
- Arquivos CSV/JSON sempre lidos e escritos com `encoding="utf-8"`.
- 150 pares, 50 por estrato (`elogio`, `reclamacao`, `neutra`); piso de **100 pares** depois da anotação.
- A página de anotação nunca recebe `par_id`, `estrato` nem rótulo.
- A régua de 20 (`SINCERAS_COM_MARCADOR`, `IRONIAS_SEM_MARCADOR`) continua intacta; nenhuma frase dela entra na régua nova.
- Rodar testes com `uv run pytest -q <alvo>`; suíte inteira com `uv run pytest -q`.

## Review Focus

1. **Anotador que não termina:** frase com menos de 2 respostas vira ambígua, não quebra a consolidação nem conta como "não irônico" (Task 6, `test_frase_com_resposta_insuficiente_e_ambigua`).
2. **Anotador que volta e muda a resposta:** vale a última por `(anotador, frase_id)` pelo `instante` (Task 6, `test_ultima_resposta_do_anotador_vence`).
3. **Par incompleto ou com dois lados iguais:** acurácia por par recusa par sem exatamente um lado de cada rótulo (Task 1, `test_par_incompleto_e_recusado`).
4. **Régua editada depois de congelada:** a carga falha alto se a impressão não bate com o meta (Task 7, `test_carga_recusa_regua_editada`).
5. **Texto com emoji e acento:** traços e impressão usam UTF-8; o emoji conta em `tem_emoji` e a impressão não muda entre leituras (Task 3, `test_emoji_e_acento_nao_quebram_os_tracos`).

---

### Task 1: Métricas por par e ECE

**Files:**
- Modify: `fraus/comparacao_modelos.py` (após `bootstrap_da_diferenca`, antes do bloco `# --- O laudo`)
- Test: `tests/test_comparacao_por_par.py`

**Interfaces:**
- Produces:
  - `ResultadoIntervalo(valor: float, ic_inferior: float, ic_superior: float, reamostras: int)` (dataclass frozen)
  - `acuracia_por_par(rotulos: Sequence[int], preditos: Sequence[int], par_ids: Sequence[str]) -> float`
  - `bootstrap_por_par(rotulos, preditos, par_ids, *, preditos_referencia: Sequence[int] | None = None, reamostras: int = 2000, semente: int = 42) -> ResultadoIntervalo`
  - `ece(probabilidades: Sequence[float], rotulos: Sequence[int], *, faixas: int = 10) -> float`

- [ ] **Step 1: Write the failing tests**

```python
import numpy as np
import pytest

from fraus.comparacao_modelos import acuracia_por_par, bootstrap_por_par, ece


def test_par_so_conta_quando_os_dois_lados_acertam():
    rotulos = [0, 1, 0, 1]
    preditos = [0, 1, 0, 0]
    assert acuracia_por_par(rotulos, preditos, ["a", "a", "b", "b"]) == pytest.approx(0.5)


def test_par_incompleto_e_recusado():
    with pytest.raises(ValueError, match="um lado de cada rotulo"):
        acuracia_por_par([0, 1, 0], [0, 1, 0], ["a", "a", "b"])
    with pytest.raises(ValueError, match="um lado de cada rotulo"):
        acuracia_por_par([0, 0], [0, 0], ["a", "a"])


def test_classificador_aleatorio_fica_perto_de_um_quarto():
    gerador = np.random.default_rng(0)
    pares = [f"p{i}" for i in range(5000) for _ in range(2)]
    rotulos = [0, 1] * 5000
    preditos = gerador.integers(0, 2, 10000).tolist()
    assert acuracia_por_par(rotulos, preditos, pares) == pytest.approx(0.25, abs=0.02)


def test_bootstrap_por_par_e_deterministico_e_degenera_sem_quebrar():
    rotulos, pares = [0, 1] * 4, [p for p in "abcd" for _ in range(2)]
    perfeito = bootstrap_por_par(rotulos, rotulos, pares)
    assert (perfeito.valor, perfeito.ic_inferior, perfeito.ic_superior) == (1.0, 1.0, 1.0)
    metade = [0, 1, 0, 1, 1, 1, 1, 1]
    um = bootstrap_por_par(rotulos, metade, pares, semente=7)
    dois = bootstrap_por_par(rotulos, metade, pares, semente=7)
    assert um == dois
    assert um.valor == pytest.approx(0.5)


def test_bootstrap_da_diferenca_por_par():
    rotulos, pares = [0, 1] * 20, [f"p{i}" for i in range(20) for _ in range(2)]
    metade = [0, 1] * 10 + [1, 1] * 10
    resultado = bootstrap_por_par(rotulos, rotulos, pares, preditos_referencia=metade)
    assert resultado.valor == pytest.approx(0.5)
    assert 0.0 < resultado.ic_inferior <= 0.5 <= resultado.ic_superior <= 1.0


def test_ece_zero_quando_calibrado_e_positivo_quando_superconfiante():
    assert ece([0.8] * 10, [1] * 8 + [0] * 2) == pytest.approx(0.0)
    assert ece([1.0] * 10, [1] * 5 + [0] * 5) == pytest.approx(0.5)
    with pytest.raises(ValueError, match="0..1"):
        ece([1.2], [1])
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -q tests/test_comparacao_por_par.py`
Expected: FAIL com `ImportError: cannot import name 'acuracia_por_par'`

- [ ] **Step 3: Implement**

```python
@dataclass(frozen=True)
class ResultadoIntervalo:
    valor: float
    ic_inferior: float
    ic_superior: float
    reamostras: int


def _acertos_por_par(
    rotulos: Sequence[int], preditos: Sequence[int], par_ids: Sequence[str]
) -> dict[str, bool]:
    """Par certo e par com OS DOIS lados certos; par mal formado e erro alto."""
    if not len(rotulos) == len(preditos) == len(par_ids):
        raise ValueError("rotulos, predicoes e pares de tamanhos diferentes")
    lados: dict[str, list[tuple[int, bool]]] = {}
    for rotulo, predito, par in zip(rotulos, preditos, par_ids):
        lados.setdefault(str(par), []).append((int(rotulo), int(predito) == int(rotulo)))
    mal_formados = sorted(
        par for par, itens in lados.items() if sorted(r for r, _ in itens) != [0, 1]
    )
    if mal_formados:
        raise ValueError(f"par sem exatamente um lado de cada rotulo: {mal_formados[:5]}")
    return {par: all(acerto for _, acerto in itens) for par, itens in lados.items()}


def acuracia_por_par(
    rotulos: Sequence[int], preditos: Sequence[int], par_ids: Sequence[str]
) -> float:
    """Fracao de pares com os dois lados certos. O acaso e 25%, nao 50%."""
    acertos = _acertos_por_par(rotulos, preditos, par_ids)
    return sum(acertos.values()) / len(acertos)


def bootstrap_por_par(
    rotulos: Sequence[int],
    preditos: Sequence[int],
    par_ids: Sequence[str],
    *,
    preditos_referencia: Sequence[int] | None = None,
    reamostras: int = 2000,
    semente: int = 42,
) -> ResultadoIntervalo:
    """IC 95% percentil da acuracia por par -- ou da diferenca para a referencia.

    Reamostra PARES, nao frases: os dois lados de um par sao dependentes, e
    reamostrar frase estreitaria o intervalo sem motivo.
    """
    acertos = _acertos_por_par(rotulos, preditos, par_ids)
    pares = sorted(acertos)
    valores = np.array([acertos[p] for p in pares], dtype=float)
    if preditos_referencia is not None:
        referencia = _acertos_por_par(rotulos, preditos_referencia, par_ids)
        valores = valores - np.array([referencia[p] for p in pares], dtype=float)
    gerador = np.random.default_rng(semente)
    medias = np.empty(reamostras)
    for i in range(reamostras):
        medias[i] = valores[gerador.integers(0, len(valores), len(valores))].mean()
    inferior, superior = np.percentile(medias, [2.5, 97.5])
    return ResultadoIntervalo(
        valor=float(valores.mean()),
        ic_inferior=float(inferior),
        ic_superior=float(superior),
        reamostras=reamostras,
    )


def ece(probabilidades: Sequence[float], rotulos: Sequence[int], *, faixas: int = 10) -> float:
    """Erro de calibracao esperado de P(classe 1), em faixas iguais de 0 a 1.

    Media ponderada, por faixa, de |P media - frequencia observada da classe 1|.
    """
    p = np.asarray(probabilidades, dtype=float)
    y = np.asarray(rotulos, dtype=int)
    if len(p) != len(y) or len(p) == 0:
        raise ValueError("probabilidades e rotulos vazios ou de tamanhos diferentes")
    if ((p < 0.0) | (p > 1.0)).any():
        raise ValueError("probabilidade fora de 0..1")
    bordas = np.linspace(0.0, 1.0, faixas + 1)
    indices = np.clip(np.digitize(p, bordas[1:-1], right=True), 0, faixas - 1)
    total = 0.0
    for faixa in range(faixas):
        mascara = indices == faixa
        if mascara.any():
            total += mascara.mean() * abs(p[mascara].mean() - y[mascara].mean())
    return float(total)
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest -q tests/test_comparacao_por_par.py tests/test_comparacao_modelos.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add fraus/comparacao_modelos.py tests/test_comparacao_por_par.py
git commit -m "feat(comparacao): acuracia por par, bootstrap de pares e ece"
```

---

### Task 2: O laudo aceita pares

**Files:**
- Modify: `fraus/comparacao_modelos.py` (`avaliar_conjunto`)
- Test: `tests/test_comparacao_por_par.py`

**Interfaces:**
- Consumes: `acuracia_por_par`, `bootstrap_por_par` (Task 1)
- Produces: `avaliar_conjunto(..., par_ids: Sequence[str] | None = None)`. Com `par_ids`, cada `modelos[m]` ganha `"acuracia_por_par": float` e `"ic95_por_par": [inf, sup]`; `comparacao` ganha `"diferenca_acuracia_por_par": float`, `"ic95_diferenca_por_par": [inf, sup]`, `"por_par_demonstrada": bool`. Sem `par_ids`, o dicionário é idêntico ao de hoje.

- [ ] **Step 1: Write the failing tests**

```python
from fraus.comparacao_modelos import avaliar_conjunto


def _conjunto(par_ids=None):
    rotulos = [0, 1] * 20
    return avaliar_conjunto(
        identificador="regua_pares", tarefa="ironia", nome="Régua de pares",
        independente=True, rotulos=rotulos,
        preditos_por_modelo={"laya_treinado": rotulos, "bertimbau": [1, 1] * 20},
        classes=[0, 1], nomes_classes=["não irônico", "irônico"],
        par_ids=par_ids, reamostras=200,
    )


def test_conjunto_com_pares_traz_acuracia_por_par_e_comparacao():
    resultado = _conjunto([f"p{i}" for i in range(20) for _ in range(2)])
    assert resultado["modelos"]["laya_treinado"]["acuracia_por_par"] == 1.0
    assert resultado["modelos"]["bertimbau"]["acuracia_por_par"] == 0.0
    assert resultado["comparacao"]["diferenca_acuracia_por_par"] == 1.0
    assert resultado["comparacao"]["por_par_demonstrada"] is True


def test_conjunto_sem_pares_nao_muda():
    resultado = _conjunto()
    assert "acuracia_por_par" not in resultado["modelos"]["laya_treinado"]
    assert "diferenca_acuracia_por_par" not in resultado["comparacao"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -q tests/test_comparacao_por_par.py -k conjunto`
Expected: FAIL com `TypeError: avaliar_conjunto() got an unexpected keyword argument 'par_ids'`

- [ ] **Step 3: Implement** — acrescentar `par_ids: Sequence[str] | None = None` aos parâmetros de `avaliar_conjunto` (depois de `reamostras`), e antes do `return`:

```python
    if par_ids is not None:
        for modelo, preditos in preditos_por_modelo.items():
            intervalo = bootstrap_por_par(rotulos, preditos, par_ids, reamostras=reamostras)
            modelos[modelo]["acuracia_por_par"] = intervalo.valor
            modelos[modelo]["ic95_por_par"] = [intervalo.ic_inferior, intervalo.ic_superior]
        diferenca = bootstrap_por_par(
            rotulos, a, par_ids, preditos_referencia=b, reamostras=reamostras
        )
```

e, no dicionário `comparacao` devolvido, mesclar quando `par_ids is not None`:

```python
    comparacao = {
        "candidato": candidato,
        "referencia": referencia,
        "diferenca_f1_macro": bs.diferenca,
        "ic95": [bs.ic_inferior, bs.ic_superior],
        "mcnemar": {"so_candidato": mc.so_a, "so_referencia": mc.so_b, "p_valor": mc.p_valor},
        # Intervalo que contem o zero nao demonstra vantagem de ninguem.
        "diferenca_demonstrada": not (bs.ic_inferior <= 0.0 <= bs.ic_superior),
    }
    if par_ids is not None:
        comparacao["diferenca_acuracia_por_par"] = diferenca.valor
        comparacao["ic95_diferenca_por_par"] = [diferenca.ic_inferior, diferenca.ic_superior]
        comparacao["por_par_demonstrada"] = not (
            diferenca.ic_inferior <= 0.0 <= diferenca.ic_superior
        )
```

(o `return` passa a usar `"comparacao": comparacao`).

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest -q tests/test_comparacao_por_par.py tests/test_comparacao_modelos.py tests/test_rota_comparacao.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add fraus/comparacao_modelos.py tests/test_comparacao_por_par.py
git commit -m "feat(comparacao): o laudo mede acuracia por par quando o conjunto tem pares"
```

---

### Task 3: Baseline só-estilo

**Files:**
- Create: `fraus/baseline_estilo.py`
- Test: `tests/test_baseline_estilo.py`

**Interfaces:**
- Produces:
  - `NOMES_TRACOS: tuple[str, ...]` (15 nomes, ordem fixa)
  - `TRACOS_BINARIOS: tuple[str, ...]` (os traços 0/1)
  - `tracos_de_superficie(texto: str) -> dict[str, float]`
  - `matriz_de_tracos(textos: Sequence[str]) -> np.ndarray` (n × 15)
  - `BaselineEstilo(semente: int = 42)` com `.treinar(textos, rotulos) -> BaselineEstilo`, `.prever(textos) -> list[int]`, `.prever_probabilidades(textos) -> list[float]` (P da classe 1)

- [ ] **Step 1: Write the failing tests**

```python
import pytest

from fraus.baseline_estilo import (NOMES_TRACOS, TRACOS_BINARIOS, BaselineEstilo,
                                   tracos_de_superficie)
from fraus.comparacao_modelos import acuracia_por_par


def test_tracos_tem_nomes_fixos_e_nenhum_lexico():
    tracos = tracos_de_superficie("Ótimo serviço!!! kkkk https://x.y @loja #fail R$ 10...")
    assert tuple(tracos) == NOMES_TRACOS
    assert tracos["exclamacoes"] == 3.0
    assert tracos["risada"] == 1.0
    assert tracos["tem_url"] == tracos["tem_arroba"] == tracos["tem_hashtag"] == 1.0
    assert tracos["tem_reais"] == tracos["reticencias"] == 1.0
    assert set(TRACOS_BINARIOS) <= set(NOMES_TRACOS)


def test_emoji_e_acento_nao_quebram_os_tracos():
    tracos = tracos_de_superficie("ok, obrigado 🙂")
    assert tracos["tem_emoji"] == 1.0
    assert tracos["inicio_minusculo"] == 1.0
    assert tracos_de_superficie("ÉÉÉ")["prop_maiusculas"] == 1.0
    assert tracos_de_superficie("") == {nome: 0.0 for nome in NOMES_TRACOS}


def test_baseline_aprende_atalho_de_pontuacao():
    textos = [f"frase numero {i}." for i in range(30)] + [f"frase numero {i}" for i in range(30)]
    rotulos = [0] * 30 + [1] * 30
    modelo = BaselineEstilo().treinar(textos, rotulos)
    assert modelo.prever(["outra frase.", "outra frase"]) == [0, 1]


def test_baseline_nao_resolve_par_de_mesmo_registro():
    textos = [f"frase numero {i}." for i in range(30)] + [f"frase numero {i}" for i in range(30)]
    modelo = BaselineEstilo().treinar(textos, [0] * 30 + [1] * 30)
    # Os dois lados de cada par tem a mesma superficie: o baseline responde
    # igual para os dois, entao nunca acerta um par inteiro.
    regua = ["abc def", "ghi jkl", "mno pqr.", "stu vwx."]
    preditos = modelo.prever(regua)
    assert acuracia_por_par([0, 1, 0, 1], preditos, ["a", "a", "b", "b"]) == 0.0
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -q tests/test_baseline_estilo.py`
Expected: FAIL com `ModuleNotFoundError: No module named 'fraus.baseline_estilo'`

- [ ] **Step 3: Implement**

```python
"""Baseline que so enxerga a SUPERFICIE do texto -- nenhuma palavra.

Se um classificador de caixa, pontuacao e tamanho acerta a ironia de um
corpus, o corpus mede registro e nao ironia (foi o que o IDPT fez em
08/10/2026, ver docs/ironia.md). Na regua de pares, ele e a linha que todo
modelo de ironia tem de vencer para ser promovido.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

NOMES_TRACOS = (
    "comprimento_log", "prop_maiusculas", "inicio_minusculo", "termina_ponto",
    "exclamacoes", "interrogacoes", "reticencias", "tem_digito", "tem_reais",
    "tem_url", "tem_arroba", "tem_hashtag", "tem_emoji", "alongamento", "risada",
)
TRACOS_BINARIOS = (
    "inicio_minusculo", "termina_ponto", "reticencias", "tem_digito", "tem_reais",
    "tem_url", "tem_arroba", "tem_hashtag", "tem_emoji", "alongamento", "risada",
)

_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
_URL = re.compile(r"https?://|www\.")
_ALONGAMENTO = re.compile(r"([^\W\d_])\1{2,}")
_RISADA = re.compile(r"\b(k{3,}|(?:ha){2,}|(?:rs){2,})\b")


def tracos_de_superficie(texto: str) -> dict[str, float]:
    """Os 15 tracos, na ordem de `NOMES_TRACOS`."""
    texto = str(texto)
    aparado = texto.strip()
    letras = [c for c in texto if c.isalpha()]
    minusculo = texto.lower()
    return {
        "comprimento_log": float(np.log1p(len(texto))),
        "prop_maiusculas": sum(c.isupper() for c in letras) / len(letras) if letras else 0.0,
        "inicio_minusculo": float(bool(aparado) and aparado[0].isalpha() and aparado[0].islower()),
        "termina_ponto": float(aparado.endswith(".") and not aparado.endswith("...")),
        "exclamacoes": float(texto.count("!")),
        "interrogacoes": float(texto.count("?")),
        "reticencias": float("..." in texto or "…" in texto),
        "tem_digito": float(any(c.isdigit() for c in texto)),
        "tem_reais": float("r$" in minusculo),
        "tem_url": float(bool(_URL.search(texto))),
        "tem_arroba": float("@" in texto),
        "tem_hashtag": float("#" in texto),
        "tem_emoji": float(bool(_EMOJI.search(texto))),
        "alongamento": float(bool(_ALONGAMENTO.search(minusculo))),
        "risada": float(bool(_RISADA.search(minusculo))),
    }


def matriz_de_tracos(textos: Sequence[str]) -> np.ndarray:
    return np.array(
        [[tracos_de_superficie(t)[nome] for nome in NOMES_TRACOS] for t in textos], dtype=float
    ).reshape(len(textos), len(NOMES_TRACOS))


class BaselineEstilo:
    """Regressao logistica sobre os tracos de superficie."""

    def __init__(self, semente: int = 42):
        self._modelo = make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=1000, random_state=semente)
        )

    def treinar(self, textos: Sequence[str], rotulos: Sequence[int]) -> "BaselineEstilo":
        self._modelo.fit(matriz_de_tracos(textos), np.asarray(rotulos, dtype=int))
        return self

    def prever(self, textos: Sequence[str]) -> list[int]:
        return [int(c) for c in self._modelo.predict(matriz_de_tracos(textos))]

    def prever_probabilidades(self, textos: Sequence[str]) -> list[float]:
        classes = list(self._modelo.classes_)
        return [float(p[classes.index(1)]) for p in self._modelo.predict_proba(matriz_de_tracos(textos))]
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest -q tests/test_baseline_estilo.py`
Expected: PASS. Se `test_baseline_nao_resolve_par_de_mesmo_registro` falhar por `comprimento_log` diferente dentro do par, conferir que os textos de cada par têm o mesmo tamanho (os do teste têm).

- [ ] **Step 5: Commit**

```bash
git add fraus/baseline_estilo.py tests/test_baseline_estilo.py
git commit -m "feat(ironia): baseline so de estilo, a linha que todo modelo tem de vencer"
```

---

### Task 4: Rascunho dos 150 pares e conferência de registro

**Files:**
- Create: `fraus/dados/regua_ironia_rascunho.csv`
- Modify: `fraus/avaliacao_ironia.py` (acrescentar ao fim)
- Test: `tests/test_regua_pares_rascunho.py`

**Interfaces:**
- Consumes: `tracos_de_superficie`, `TRACOS_BINARIOS` (Task 3)
- Produces:
  - `CAMINHO_RASCUNHO: Path` = `fraus/dados/regua_ironia_rascunho.csv`
  - `FraseDoRascunho(par_id: str, estrato: str, dominio: str, rotulo: int, texto: str)` dataclass frozen, com propriedade `frase_id -> str` (12 primeiros hex do SHA-256 do texto UTF-8)
  - `carregar_rascunho(caminho: Path = CAMINHO_RASCUNHO) -> list[FraseDoRascunho]`
  - `conferir_registro_equilibrado(textos: Sequence[str], rotulos: Sequence[int], *, tolerancia: float = 0.10) -> None` — levanta `ValueError` nomeando o traço

Formato do CSV (cabeçalho exato): `par_id,estrato,dominio,rotulo,texto`. `par_id` = `elogio-01`…`elogio-50`, `reclamacao-01`…, `neutra-01`…; `rotulo` 0/1; `dominio` ∈ `banco, ecommerce, telecom, saude, servico_publico, delivery`.

Regras de redação (da spec, §1): mesma situação nos dois lados; registro sorteado **por par** e aplicado aos dois lados (minúscula inicial, ponto final, "vc/vcs", "kkk", emoji, caixa alta); sem empresa real nem dado pessoal; nada da régua de 20 nem das sondas do notebook 04. Exemplos do molde:

```csv
par_id,estrato,dominio,rotulo,texto
elogio-01,elogio,delivery,0,"chegou quentinho e antes do horário, muito bom"
elogio-01,elogio,delivery,1,"chegou frio e duas horas depois, muito bom"
reclamacao-01,reclamacao,banco,0,Cobraram a anuidade duas vezes e quero o estorno.
reclamacao-01,reclamacao,banco,1,Que maravilha cobrarem a anuidade duas vezes.
neutra-01,neutra,telecom,0,vcs sabem quando volta a internet aqui no bairro?
neutra-01,neutra,telecom,1,vcs sabem quando volta a internet aqui no bairro? ano que vem?
```

- [ ] **Step 1: Write the failing tests**

```python
from collections import Counter

import pytest

from fraus.avaliacao_ironia import (IRONIAS_SEM_MARCADOR, SINCERAS_COM_MARCADOR,
                                    carregar_rascunho, conferir_registro_equilibrado)

SONDAS_DO_04 = {
    "otimo servico, so esperei 3 horas",
    "parabens pelo atendimento, nota mil, so 5 dias sem resposta",
    "qual o prazo de entrega do meu pedido",
    "obrigado, resolveram rapido",
}


def test_rascunho_tem_150_pares_50_por_estrato_um_lado_de_cada():
    frases = carregar_rascunho()
    assert len(frases) == 300
    por_par = {}
    for frase in frases:
        por_par.setdefault(frase.par_id, []).append(frase)
    assert len(por_par) == 150
    assert all(sorted(f.rotulo for f in lados) == [0, 1] for lados in por_par.values())
    assert all(len({f.estrato for f in lados}) == 1 for lados in por_par.values())
    assert Counter(lados[0].estrato for lados in por_par.values()) == {
        "elogio": 50, "reclamacao": 50, "neutra": 50,
    }
    assert len({f.dominio for f in frases}) >= 6


def test_rascunho_sem_repeticao_nem_frase_da_regua_antiga():
    textos = [f.texto for f in carregar_rascunho()]
    assert len(set(textos)) == len(textos)
    assert len({f.frase_id for f in carregar_rascunho()}) == len(textos)
    proibidas = {t.lower() for t in (*SINCERAS_COM_MARCADOR, *IRONIAS_SEM_MARCADOR, *SONDAS_DO_04)}
    assert not proibidas & {t.lower() for t in textos}


def test_rascunho_tem_registro_equilibrado():
    frases = carregar_rascunho()
    conferir_registro_equilibrado([f.texto for f in frases], [f.rotulo for f in frases])


def test_conferencia_reprova_ponto_final_so_nos_ironicos():
    textos = ["a b"] * 10 + ["a b."] * 10
    with pytest.raises(ValueError, match="termina_ponto"):
        conferir_registro_equilibrado(textos, [0] * 10 + [1] * 10)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -q tests/test_regua_pares_rascunho.py`
Expected: FAIL com `ImportError: cannot import name 'carregar_rascunho'`

- [ ] **Step 3: Implement the code** (fim de `fraus/avaliacao_ironia.py`; importar `csv`, `hashlib`, `Path` no topo)

```python
# --- Regua de pares minimos (08/10/2026) -------------------------------------
#
# A regua de 20 acima continua sendo o que e: autoral. A de pares e escrita
# aqui como RASCUNHO e so vira regua depois da anotacao as cegas
# (docs/superpowers/specs/2026-10-08-regua-pares-ironia-design.md).

CAMINHO_RASCUNHO = Path(__file__).parent / "dados" / "regua_ironia_rascunho.csv"


@dataclass(frozen=True)
class FraseDoRascunho:
    par_id: str
    estrato: str
    dominio: str
    rotulo: int
    texto: str

    @property
    def frase_id(self) -> str:
        """Id opaco: e o que a pagina de anotacao ve no lugar de par e rotulo."""
        return hashlib.sha256(self.texto.encode("utf-8")).hexdigest()[:12]


def carregar_rascunho(caminho: Path = CAMINHO_RASCUNHO) -> list[FraseDoRascunho]:
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        return [
            FraseDoRascunho(
                par_id=linha["par_id"], estrato=linha["estrato"], dominio=linha["dominio"],
                rotulo=int(linha["rotulo"]), texto=linha["texto"],
            )
            for linha in csv.DictReader(arquivo)
        ]


def conferir_registro_equilibrado(
    textos: Sequence[str], rotulos: Sequence[int], *, tolerancia: float = 0.10
) -> None:
    """Nenhum traco de superficie pode acompanhar o rotulo.

    Para cada traco binario, a fracao entre as ironicas e entre as nao
    ironicas difere no maximo `tolerancia`. O comprimento medio (em log)
    tambem. Um traco que separa as classes seria a regua repetindo o defeito
    do IDPT.
    """
    from fraus.baseline_estilo import TRACOS_BINARIOS, tracos_de_superficie

    if len(textos) != len(rotulos):
        raise ValueError("textos e rotulos de tamanhos diferentes")
    tracos = [tracos_de_superficie(t) for t in textos]
    for nome in (*TRACOS_BINARIOS, "comprimento_log"):
        ironicas = [t[nome] for t, r in zip(tracos, rotulos) if r == IRONICO]
        sinceras = [t[nome] for t, r in zip(tracos, rotulos) if r != IRONICO]
        if not ironicas or not sinceras:
            raise ValueError("a conferencia exige frases das duas classes")
        diferenca = abs(sum(ironicas) / len(ironicas) - sum(sinceras) / len(sinceras))
        if diferenca > tolerancia:
            raise ValueError(
                f"o traco {nome} acompanha o rotulo: diferenca {diferenca:.2f} > {tolerancia:.2f}"
            )
```

- [ ] **Step 4: Write the 300 sentences** in `fraus/dados/regua_ironia_rascunho.csv` following the format and the rules above. Distribute the 6 domains across each stratum (8–9 pairs per domain per stratum). Per pair, draw the register once (e.g., with a fixed-seed list of combinations) and apply it to both sides. Keep the two sides within ±25% length of each other.

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest -q tests/test_regua_pares_rascunho.py tests/test_avaliacao_ironia.py`
Expected: PASS. If `test_rascunho_tem_registro_equilibrado` fails, the message names the trait — rewrite the pairs that carry it on only one side (often the ironic side ending in "..." or "!"), do not raise the tolerance.

- [ ] **Step 6: Commit**

```bash
git add fraus/avaliacao_ironia.py fraus/dados/regua_ironia_rascunho.csv tests/test_regua_pares_rascunho.py
git commit -m "feat(ironia): rascunho de 150 pares minimos com registro equilibrado"
```

---

### Task 5: Página de anotação às cegas

**Files:**
- Create: `fraus/anotacao_regua.py`
- Create: `scripts/gerar_anotacao_ironia.py`
- Create: `scripts/anotacao_ironia/index.html`
- Test: `tests/test_anotacao_regua.py`

**Interfaces:**
- Consumes: `carregar_rascunho`, `FraseDoRascunho.frase_id` (Task 4)
- Produces:
  - `frases_para_anotacao(frases: Sequence[FraseDoRascunho], *, semente: int = 42) -> list[dict[str, str]]` — só as chaves `id` e `texto`, numa ordem em que **os dois lados de um par nunca ficam adjacentes**, incluindo o último com o primeiro (a página roda a lista por anotador).
  - `scripts/anotacao_ironia/frases.json` gerado pelo script (não versionado à mão; o script é a fonte).
  - Registro gravado no banco da página por resposta: `{"anotador": str, "frase_id": str, "resposta": "ironico"|"nao_ironico"|"contexto", "instante": ISO-8601}`.

- [ ] **Step 1: Write the failing tests**

```python
from fraus.anotacao_regua import frases_para_anotacao
from fraus.avaliacao_ironia import carregar_rascunho


def test_pagina_nao_recebe_par_estrato_nem_rotulo():
    payload = frases_para_anotacao(carregar_rascunho())
    assert all(set(item) == {"id", "texto"} for item in payload)
    assert len(payload) == 300


def test_lados_do_par_nunca_vizinhos_nem_na_volta():
    frases = carregar_rascunho()
    par_de = {f.frase_id: f.par_id for f in frases}
    payload = frases_para_anotacao(frases)
    ids = [item["id"] for item in payload]
    for i, atual in enumerate(ids):
        seguinte = ids[(i + 1) % len(ids)]
        assert par_de[atual] != par_de[seguinte]


def test_ordem_e_deterministica():
    frases = carregar_rascunho()
    assert frases_para_anotacao(frases) == frases_para_anotacao(frases)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -q tests/test_anotacao_regua.py`
Expected: FAIL com `ModuleNotFoundError: No module named 'fraus.anotacao_regua'`

- [ ] **Step 3: Implement**

```python
"""O que a pagina de anotacao recebe: id opaco e texto. Nada mais.

Par, estrato e rotulo pretendido ficam no repositorio. A pagina mostra a
mesma sequencia a todos, girada por anotador; por isso a sequencia ja sai
daqui sem os dois lados de um par vizinhos -- nem o ultimo com o primeiro.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from fraus.avaliacao_ironia import FraseDoRascunho


def frases_para_anotacao(
    frases: Sequence[FraseDoRascunho], *, semente: int = 42
) -> list[dict[str, str]]:
    gerador = random.Random(semente)
    for _ in range(1000):
        ordem = list(frases)
        gerador.shuffle(ordem)
        vizinhos = zip(ordem, ordem[1:] + ordem[:1])
        if all(a.par_id != b.par_id for a, b in vizinhos):
            return [{"id": f.frase_id, "texto": f.texto} for f in ordem]
    raise RuntimeError("nao achei ordem sem par vizinho em 1000 tentativas")
```

`scripts/gerar_anotacao_ironia.py`:

```python
"""Gera scripts/anotacao_ironia/frases.json a partir do rascunho da regua."""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from fraus.anotacao_regua import frases_para_anotacao  # noqa: E402
from fraus.avaliacao_ironia import carregar_rascunho  # noqa: E402

destino = RAIZ / "scripts" / "anotacao_ironia" / "frases.json"
destino.write_text(
    json.dumps(frases_para_anotacao(carregar_rascunho()), ensure_ascii=False, indent=1) + "\n",
    encoding="utf-8",
)
print(f"{destino}: escrito")
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest -q tests/test_anotacao_regua.py && uv run python scripts/gerar_anotacao_ironia.py`
Expected: PASS e `scripts/anotacao_ironia/frases.json: escrito`

- [ ] **Step 5: Build the page.** Load the `artifact-capabilities` and `artifact-design` skills first (the runtime calls for the shared database and viewer identity come from their typed definitions — use them exactly). The page `scripts/anotacao_ironia/index.html` loads `frases.json` as a published file and must:
  - identify the viewer; the database key is the viewer id, never a typed name;
  - rotate the list by an offset derived from the viewer id (`hash(id) % 300`) and resume at the first sentence without an answer from this viewer;
  - show one sentence at a time, large, with three buttons — **Irônico** (tecla 1), **Não irônico** (tecla 2), **Depende do contexto** (tecla 3) — a "faltam N" counter and a "voltar" that lets the viewer change the previous answer (writes a new record; the latest `instante` wins);
  - show at the top: "Ironia aqui é dizer o contrário do que se quer dizer, em tom de crítica ou zombaria. 'Depende do contexto' é resposta válida, não falha.";
  - never read or show other viewers' records;
  - on finishing, show "Obrigado — suas N respostas foram salvas."
  - Grep the finished HTML: it must not contain `par_id`, `estrato`, `rotulo` or any `-01` style pair id.

- [ ] **Step 6: Publish** with the Artifact tool (`file_path: scripts/anotacao_ironia/index.html`, `files: {"frases.json": "scripts/anotacao_ironia/frases.json"}`, `icon: "check"`, capabilities as the skill prescribes). Open it, answer 3 sentences as a smoke test, read them back with `ArtifactData` (`list`), then delete those 3 smoke records. Record the artifact URL in `docs/ironia.md` (Task 8).

- [ ] **Step 7: Commit**

```bash
git add fraus/anotacao_regua.py scripts/gerar_anotacao_ironia.py scripts/anotacao_ironia tests/test_anotacao_regua.py
git commit -m "feat(ironia): pagina de anotacao as cegas da regua de pares"
```

---

### Task 6: Consolidação da anotação

**Files:**
- Create: `fraus/consolidacao_regua.py`
- Test: `tests/test_consolidacao_regua.py`

**Interfaces:**
- Consumes: `FraseDoRascunho` (Task 4)
- Produces:
  - `RESPOSTAS = ("ironico", "nao_ironico", "contexto")`
  - `ultimas_respostas(registros: Sequence[dict]) -> dict[str, list[str]]` — por `frase_id`, a última resposta de cada anotador (por `instante`)
  - `fleiss_kappa(contagens: Sequence[Sequence[int]]) -> float` — linhas = itens, colunas = categorias, mesmo total por linha
  - `rotulo_humano(respostas: Sequence[str], *, minimo: int = 2) -> int | None` — `IRONICO`, `0` ou `None` (ambígua)
  - `decidir_pares(frases: Sequence[FraseDoRascunho], respostas: dict[str, list[str]], *, minimo_pares: int = 100) -> tuple[list[dict], list[dict]]` — `(mantidas, descartadas)`; cada mantida `{"par_id","estrato","texto","rotulo","concordancia"}`; cada descartada `{"par_id","estrato","rotulo","texto","motivo","respostas"}`

- [ ] **Step 1: Write the failing tests**

```python
import pytest

from fraus.avaliacao_ironia import FraseDoRascunho
from fraus.consolidacao_regua import (decidir_pares, fleiss_kappa, rotulo_humano,
                                      ultimas_respostas)


def test_fleiss_kappa_bate_com_o_exemplo_de_livro():
    # Exemplo classico (Fleiss 1971, reproduzido na Wikipedia): 10 itens,
    # 14 anotadores, 5 categorias, kappa = 0,210.
    contagens = [
        [0, 0, 0, 0, 14], [0, 2, 6, 4, 2], [0, 0, 3, 5, 6], [0, 3, 9, 2, 0],
        [2, 2, 8, 1, 1], [7, 7, 0, 0, 0], [3, 2, 6, 3, 0], [2, 5, 3, 2, 2],
        [6, 5, 2, 1, 0], [0, 2, 2, 3, 7],
    ]
    assert fleiss_kappa(contagens) == pytest.approx(0.210, abs=0.001)


def test_rotulo_por_maioria_e_ambiguo_no_empate_e_no_contexto():
    assert rotulo_humano(["ironico", "ironico", "nao_ironico"]) == 1
    assert rotulo_humano(["nao_ironico", "nao_ironico"]) == 0
    assert rotulo_humano(["ironico", "nao_ironico"]) is None
    assert rotulo_humano(["contexto", "contexto", "ironico"]) is None


def test_frase_com_resposta_insuficiente_e_ambigua():
    assert rotulo_humano(["ironico"]) is None
    assert rotulo_humano([]) is None


def test_ultima_resposta_do_anotador_vence():
    registros = [
        {"anotador": "a", "frase_id": "f1", "resposta": "ironico", "instante": "2026-10-09T10:00:00Z"},
        {"anotador": "a", "frase_id": "f1", "resposta": "nao_ironico", "instante": "2026-10-09T10:05:00Z"},
        {"anotador": "b", "frase_id": "f1", "resposta": "ironico", "instante": "2026-10-09T10:01:00Z"},
    ]
    assert sorted(ultimas_respostas(registros)["f1"]) == ["ironico", "nao_ironico"]


def _par(n, rotulo_texto):
    return [
        FraseDoRascunho(f"elogio-{n:02d}", "elogio", "banco", 0, f"sincera {n}{rotulo_texto}"),
        FraseDoRascunho(f"elogio-{n:02d}", "elogio", "banco", 1, f"ironica {n}{rotulo_texto}"),
    ]


def test_par_so_entra_com_os_dois_lados_confirmados():
    frases = _par(1, "") + _par(2, "") + _par(3, "")
    ids = {f.texto: f.frase_id for f in frases}
    respostas = {
        ids["sincera 1"]: ["nao_ironico"] * 3, ids["ironica 1"]: ["ironico"] * 3,
        ids["sincera 2"]: ["nao_ironico"] * 3, ids["ironica 2"]: ["contexto"] * 3,
        ids["sincera 3"]: ["ironico"] * 3, ids["ironica 3"]: ["ironico"] * 3,
    }
    mantidas, descartadas = decidir_pares(frases, respostas, minimo_pares=1)
    assert {m["par_id"] for m in mantidas} == {"elogio-01"}
    assert {(d["par_id"], d["motivo"]) for d in descartadas} == {
        ("elogio-02", "ambigua"), ("elogio-02", "par_incompleto"),
        ("elogio-03", "divergente"), ("elogio-03", "par_incompleto"),
    }
    assert mantidas[0]["concordancia"] == 1.0


def test_menos_pares_que_o_piso_falha_alto():
    frases = _par(1, "")
    ids = {f.texto: f.frase_id for f in frases}
    respostas = {ids["sincera 1"]: ["nao_ironico"] * 2, ids["ironica 1"]: ["ironico"] * 2}
    with pytest.raises(ValueError, match="1 pares; o piso e 100"):
        decidir_pares(frases, respostas)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -q tests/test_consolidacao_regua.py`
Expected: FAIL com `ModuleNotFoundError: No module named 'fraus.consolidacao_regua'`

- [ ] **Step 3: Implement**

```python
"""Da anotacao as cegas a regua congelada. Parte pura.

Regra de entrada (spec, secao 3): o rotulo humano de uma frase e a maioria
simples das respostas; empate, maioria "contexto" ou menos de dois anotadores
deixam a frase ambigua. Um par so entra se OS DOIS lados tem rotulo humano
igual ao pretendido. O resto e descartado COM MOTIVO -- e dado publicado.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from fraus.avaliacao_ironia import FraseDoRascunho
from fraus.sinais.ironia import IRONICO

RESPOSTAS = ("ironico", "nao_ironico", "contexto")
_ROTULO_DA_RESPOSTA = {"ironico": IRONICO, "nao_ironico": 1 - IRONICO}


def ultimas_respostas(registros: Sequence[dict]) -> dict[str, list[str]]:
    ultima: dict[tuple[str, str], dict] = {}
    for registro in registros:
        if registro["resposta"] not in RESPOSTAS:
            raise ValueError(f"resposta desconhecida: {registro['resposta']!r}")
        chave = (registro["anotador"], registro["frase_id"])
        if chave not in ultima or registro["instante"] > ultima[chave]["instante"]:
            ultima[chave] = registro
    por_frase: dict[str, list[str]] = {}
    for (_, frase_id), registro in ultima.items():
        por_frase.setdefault(frase_id, []).append(registro["resposta"])
    return por_frase


def fleiss_kappa(contagens: Sequence[Sequence[int]]) -> float:
    totais = {sum(linha) for linha in contagens}
    if len(totais) != 1 or 0 in totais:
        raise ValueError("todo item precisa do mesmo numero (positivo) de anotadores")
    n = totais.pop()
    itens = len(contagens)
    p_itens = [(sum(c * c for c in linha) - n) / (n * (n - 1)) for linha in contagens]
    p_medio = sum(p_itens) / itens
    proporcoes = [sum(linha[j] for linha in contagens) / (itens * n) for j in range(len(contagens[0]))]
    p_acaso = sum(p * p for p in proporcoes)
    return (p_medio - p_acaso) / (1 - p_acaso) if p_acaso < 1 else 1.0


def rotulo_humano(respostas: Sequence[str], *, minimo: int = 2) -> int | None:
    if len(respostas) < minimo:
        return None
    ranking = Counter(respostas).most_common()
    if len(ranking) > 1 and ranking[0][1] == ranking[1][1]:
        return None
    return _ROTULO_DA_RESPOSTA.get(ranking[0][0])


def decidir_pares(
    frases: Sequence[FraseDoRascunho],
    respostas: dict[str, list[str]],
    *,
    minimo_pares: int = 100,
) -> tuple[list[dict], list[dict]]:
    por_par: dict[str, list[FraseDoRascunho]] = {}
    for frase in frases:
        por_par.setdefault(frase.par_id, []).append(frase)
    mantidas, descartadas = [], []
    for par_id in sorted(por_par):
        lados = por_par[par_id]
        motivos = {}
        for frase in lados:
            humano = rotulo_humano(respostas.get(frase.frase_id, []))
            if humano is None:
                motivos[frase.frase_id] = "ambigua"
            elif humano != frase.rotulo:
                motivos[frase.frase_id] = "divergente"
        for frase in lados:
            dados = respostas.get(frase.frase_id, [])
            if motivos:
                descartadas.append({
                    "par_id": par_id, "estrato": frase.estrato, "rotulo": frase.rotulo,
                    "texto": frase.texto,
                    "motivo": motivos.get(frase.frase_id, "par_incompleto"),
                    "respostas": "|".join(sorted(dados)),
                })
            else:
                alvo = "ironico" if frase.rotulo == IRONICO else "nao_ironico"
                mantidas.append({
                    "par_id": par_id, "estrato": frase.estrato, "texto": frase.texto,
                    "rotulo": frase.rotulo, "concordancia": dados.count(alvo) / len(dados),
                })
    pares = len({m["par_id"] for m in mantidas})
    if pares < minimo_pares:
        raise ValueError(f"a anotacao confirmou {pares} pares; o piso e {minimo_pares}")
    return mantidas, descartadas
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest -q tests/test_consolidacao_regua.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add fraus/consolidacao_regua.py tests/test_consolidacao_regua.py
git commit -m "feat(ironia): consolidacao da anotacao com kappa e descartes com motivo"
```

---

### Task 7: Congelamento e carga da régua

**Files:**
- Create: `scripts/consolidar_regua_ironia.py`
- Modify: `fraus/avaliacao_ironia.py` (acrescentar ao fim)
- Test: `tests/test_regua_pares_congelada.py`

**Interfaces:**
- Consumes: `carregar_rascunho`, `decidir_pares`, `ultimas_respostas`, `fleiss_kappa`, `RESPOSTAS` (Tasks 4, 6); `impressao_dos_textos` (`fraus/divisao.py`)
- Produces:
  - `fraus/dados/regua_ironia_pares.csv` (`par_id,estrato,texto,rotulo,concordancia`), `regua_ironia_descartes.csv`, `regua_ironia_invariancia.csv` (`frase_origem,variante,texto,rotulo`), `regua_ironia_meta.json` (`{"anotadores": int, "kappa": float, "kappa_por_estrato": {...}, "pares": int, "descartados": int, "data": "AAAA-MM-DD", "impressao": str}`)
  - `FraseDaRegua(par_id: str, estrato: str, texto: str, rotulo: int, concordancia: float)` dataclass frozen
  - `carregar_regua_pares(caminho: Path = CAMINHO_REGUA_PARES, meta: Path = CAMINHO_META_REGUA) -> list[FraseDaRegua]`
  - `variantes_de_invariancia(frases: Sequence[FraseDaRegua], *, quantas: int = 20, semente: int = 42) -> list[dict]` — para cada uma de `quantas` frases sorteadas, duas variantes: `sem_ponto_ou_com_ponto` (inverte a presença do ponto final) e `com_emoji` (acrescenta " 🙂")

- [ ] **Step 1: Write the failing tests**

```python
import json
from pathlib import Path

import pytest

from fraus.avaliacao_ironia import (CAMINHO_META_REGUA, CAMINHO_REGUA_PARES, FraseDaRegua,
                                    carregar_regua_pares, variantes_de_invariancia)
from fraus.divisao import impressao_dos_textos


def _gravar(tmp_path: Path, textos):
    regua = tmp_path / "regua.csv"
    linhas = ["par_id,estrato,texto,rotulo,concordancia"]
    linhas += [f"p{i // 2},elogio,{t},{i % 2},1.0" for i, t in enumerate(textos)]
    regua.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    meta = tmp_path / "meta.json"
    meta.write_text(json.dumps({"impressao": impressao_dos_textos(textos)}), encoding="utf-8")
    return regua, meta


def test_carga_le_a_regua_congelada(tmp_path):
    regua, meta = _gravar(tmp_path, ["a", "b", "c", "d"])
    frases = carregar_regua_pares(regua, meta)
    assert frases[1] == FraseDaRegua("p0", "elogio", "b", 1, 1.0)


def test_carga_recusa_regua_editada(tmp_path):
    regua, meta = _gravar(tmp_path, ["a", "b", "c", "d"])
    regua.write_text(regua.read_text(encoding="utf-8").replace(",c,", ",C,"), encoding="utf-8")
    with pytest.raises(ValueError, match="impressao"):
        carregar_regua_pares(regua, meta)


def test_invariancia_preserva_rotulo_e_muda_so_a_superficie():
    frases = [FraseDaRegua(f"p{i}", "elogio", f"frase {i}.", i % 2, 1.0) for i in range(40)]
    variantes = variantes_de_invariancia(frases, quantas=20)
    assert len(variantes) == 40
    origem = {f.texto: f for f in frases}
    for v in variantes:
        assert v["rotulo"] == origem[v["frase_origem"]].rotulo
        assert v["texto"].rstrip(" 🙂.") == v["frase_origem"].rstrip(".")


def test_regua_versionada_bate_com_o_meta():
    if not CAMINHO_REGUA_PARES.exists():
        pytest.skip("regua de pares ainda nao anotada e congelada")
    assert carregar_regua_pares()  # levanta se a impressao nao bate
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -q tests/test_regua_pares_congelada.py`
Expected: FAIL com `ImportError: cannot import name 'CAMINHO_META_REGUA'`

- [ ] **Step 3: Implement** (fim de `fraus/avaliacao_ironia.py`; importar `json` e `random` no topo)

```python
CAMINHO_REGUA_PARES = Path(__file__).parent / "dados" / "regua_ironia_pares.csv"
CAMINHO_META_REGUA = Path(__file__).parent / "dados" / "regua_ironia_meta.json"


@dataclass(frozen=True)
class FraseDaRegua:
    par_id: str
    estrato: str
    texto: str
    rotulo: int
    concordancia: float


def carregar_regua_pares(
    caminho: Path = CAMINHO_REGUA_PARES, meta: Path = CAMINHO_META_REGUA
) -> list[FraseDaRegua]:
    """A regua congelada. Frase mudada depois do congelamento e erro alto."""
    from fraus.divisao import impressao_dos_textos

    with open(caminho, encoding="utf-8", newline="") as arquivo:
        frases = [
            FraseDaRegua(
                par_id=linha["par_id"], estrato=linha["estrato"], texto=linha["texto"],
                rotulo=int(linha["rotulo"]), concordancia=float(linha["concordancia"]),
            )
            for linha in csv.DictReader(arquivo)
        ]
    esperada = json.loads(Path(meta).read_text(encoding="utf-8"))["impressao"]
    if impressao_dos_textos(f.texto for f in frases) != esperada:
        raise ValueError(
            "a impressao da regua nao bate com o meta: frase editada depois do "
            "congelamento. Reanote ou declare uma versao nova."
        )
    return frases


def variantes_de_invariancia(
    frases: Sequence[FraseDaRegua], *, quantas: int = 20, semente: int = 42
) -> list[dict]:
    """Mesma frase, outra superficie, mesmo rotulo. Fora da metrica principal."""
    escolhidas = random.Random(semente).sample(list(frases), quantas)
    variantes = []
    for frase in escolhidas:
        base = frase.texto.rstrip()
        ponto = base[:-1] if base.endswith(".") else base + "."
        for nome, texto in (("ponto_final", ponto), ("com_emoji", base + " 🙂")):
            variantes.append({
                "frase_origem": frase.texto, "variante": nome,
                "texto": texto, "rotulo": frase.rotulo,
            })
    return variantes
```

`scripts/consolidar_regua_ironia.py`:

```python
"""Respostas da pagina de anotacao -> regua congelada em fraus/dados/.

Uso: uv run python scripts/consolidar_regua_ironia.py respostas.json
(respostas.json = lista de registros {anotador, frase_id, resposta, instante}
exportada do banco da pagina).
"""

import csv
import json
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from fraus.avaliacao_ironia import (CAMINHO_META_REGUA, CAMINHO_REGUA_PARES,  # noqa: E402
                                    FraseDaRegua, carregar_rascunho,
                                    variantes_de_invariancia)
from fraus.consolidacao_regua import (RESPOSTAS, decidir_pares, fleiss_kappa,  # noqa: E402
                                      ultimas_respostas)
from fraus.divisao import impressao_dos_textos  # noqa: E402

DADOS = RAIZ / "fraus" / "dados"


def _gravar(caminho, campos, linhas):
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(linhas)


def _kappa(frases, respostas):
    n = max((len(r) for r in respostas.values()), default=0)
    contagens = [
        [respostas[f.frase_id].count(c) for c in RESPOSTAS]
        for f in frases if len(respostas.get(f.frase_id, [])) == n
    ]
    return fleiss_kappa(contagens) if n > 1 and contagens else None


def main(caminho_respostas: str) -> None:
    registros = json.loads(Path(caminho_respostas).read_text(encoding="utf-8"))
    rascunho = carregar_rascunho()
    respostas = ultimas_respostas(registros)
    mantidas, descartadas = decidir_pares(rascunho, respostas)
    _gravar(CAMINHO_REGUA_PARES, ["par_id", "estrato", "texto", "rotulo", "concordancia"], mantidas)
    _gravar(DADOS / "regua_ironia_descartes.csv",
            ["par_id", "estrato", "rotulo", "texto", "motivo", "respostas"], descartadas)
    frases = [FraseDaRegua(**m) for m in mantidas]
    _gravar(DADOS / "regua_ironia_invariancia.csv",
            ["frase_origem", "variante", "texto", "rotulo"], variantes_de_invariancia(frases))
    meta = {
        "anotadores": len({r["anotador"] for r in registros}),
        "kappa": _kappa(rascunho, respostas),
        "kappa_por_estrato": {
            estrato: _kappa([f for f in rascunho if f.estrato == estrato], respostas)
            for estrato in ("elogio", "reclamacao", "neutra")
        },
        "pares": len({m["par_id"] for m in mantidas}),
        "descartados": len({d["par_id"] for d in descartadas}),
        "data": date.today().isoformat(),
        "impressao": impressao_dos_textos(m["texto"] for m in mantidas),
        "tipo_avaliacao": "regua_de_pares_rotulada_as_cegas_rascunho_autoral",
    }
    CAMINHO_META_REGUA.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest -q tests/test_regua_pares_congelada.py`
Expected: 3 PASS, 1 SKIP ("regua de pares ainda nao anotada e congelada")

- [ ] **Step 5: Commit**

```bash
git add fraus/avaliacao_ironia.py scripts/consolidar_regua_ironia.py tests/test_regua_pares_congelada.py
git commit -m "feat(ironia): congelamento da regua de pares com impressao conferida na carga"
```

---

### Task 8: Documentação e conferência final

**Files:**
- Modify: `docs/ironia.md` (nova seção "Régua de pares mínimos" no fim, antes de "Conclusão")
- Modify: `docs/handoff.md` (o bloco "Suspenso em 08/10/2026" ganha o próximo passo)

- [ ] **Step 1: Write the section in `docs/ironia.md`:**

```markdown
## Régua de pares mínimos

Estado: **rascunho pronto, anotação em andamento.** Spec em
`docs/superpowers/specs/2026-10-08-regua-pares-ironia-design.md` (interno).

- 150 pares (elogio, reclamação, neutra), registro equilibrado conferido por
  `conferir_registro_equilibrado`. O rascunho é autoral; o rótulo que vale é o
  da anotação às cegas.
- **Critério de promoção de qualquer cabeça de ironia:** vencer o baseline só
  de estilo (`fraus/baseline_estilo.py`) em acurácia por par na régua, com IC
  95% da diferença excluindo zero. O teste interno do IDPT não entra.
- Depois da anotação: exportar as respostas da página e rodar
  `uv run python scripts/consolidar_regua_ironia.py respostas.json`. Menos de
  100 pares confirmados para o script com erro.
```

- [ ] **Step 2: Add to the handoff block** (after "Medições: …"): `Próximo passo: a régua de pares (docs/ironia.md, "Régua de pares mínimos") — anotar, consolidar, congelar.` Include the annotation page URL from Task 5.

- [ ] **Step 3: Run everything**

```bash
uv run pytest -q
uv run --extra dev --extra torch --extra docs mkdocs build --strict -d /tmp/fraus-site
uv run --extra dev --extra torch --extra docs mkdocs build --strict --config-file mkdocs-publico.yml -d /tmp/fraus-site-pub
```
Expected: suíte verde (com 1 skip novo), os dois builds sem WARNING.

- [ ] **Step 4: Commit**

```bash
git add docs/ironia.md docs/handoff.md
git commit -m "docs(ironia): regua de pares, criterio de promocao e como consolidar"
```
