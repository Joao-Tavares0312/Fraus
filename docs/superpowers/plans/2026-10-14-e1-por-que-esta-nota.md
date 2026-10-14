# E1 — "Por que esta nota" e drivers: plano de implementação

> **Para quem executa:** SUB-SKILL OBRIGATÓRIA: superpowers:subagent-driven-development (recomendada) ou superpowers:executing-plans, tarefa por tarefa. Os passos usam checkbox (`- [ ]`).

**Objetivo:** explicar cada nota de forma exata, com contribuições que somam o logit e reproduzem o score, efeito por família em pontos de score, texto por template e contrafactual de espera que recusa sair da faixa de treino. Mostrar também, numa amostra, o que mais puxa detratores e promotores.

**Arquitetura:**

- O `Fusor` ganha a decomposição exata (`decompor`) e o efeito por família (`efeitos_por_familia`).
- `fraus/explicacao.py` (puro) transforma isso em frases de template e agrega os drivers com bootstrap.
- O `Motor` anexa `explicacao` à atribuição que já existe.
- Entram duas rotas novas: `POST /conversas/{id}/contrafactual` e `GET /indicadores/drivers`.
- O front mostra um bloco na tela do atendimento e um painel sob demanda na Visão geral.
- Nada é gravado.

**Stack:** Python 3.11 (scikit-learn 1.6.1, numpy, FastAPI, pydantic), Next.js/TypeScript (vitest).

**Spec:** `docs/superpowers/specs/2026-10-14-e1-por-que-esta-nota-design.md`. Visão geral: `docs/superpowers/specs/2026-10-14-diferenciais-visao-geral.md`.

## Restrições globais

- Sem LLM em runtime. O texto sai de template, nunca de modelo.
- `score`, nota e categoria gravados **não mudam**. Nenhuma rota nova grava nada.
- Não tocar `modelos/`, `modelos-onnx/`, `NOMES_FEATURES`, `PESO_NEUTRO_NO_SCORE` (0,75), `FEATURES_EM_LOG` nem a cabeça de ironia.
- `None` nunca vira 0: conversa sem sinal fica fora das médias e é contada.
- A categoria sai de `ctx.categoria_de(score, ctx.faixas_vigentes())`, nunca de faixa digitada.
- Escopo por canal: tudo passa por `ctx.banco` (`BancoComEscopo`). Canal fora do escopo dá 404.
- "Faixa de treino" quer dizer `|z| ≤ LIMIAR_Z` (4,0, de `fraus/deriva.py`), sobre média e desvio do scaler. O artefato não guarda mínimo nem máximo.
- O tempo do fusor é sintético, e toda saída nova declara isso no texto de método.
- Identificadores em português, sem acento. Texto de tela com acento.
- Fonte mínima de 11 px. Ler `dashboard/DESIGN.md` antes das tarefas de front.
- A missão pede **um commit por entrega**: as tarefas só preparam o stage, e o commit único é a Tarefa 9.

## Desvios do spec (decididos aqui, registrados no spec na Tarefa 9)

1. **A explicação viaja dentro de `GET /conversas/{id}/atribuicao`** (campo novo `explicacao`), e não numa rota própria.
   - A atribuição já recalcula as features, e uma rota a mais pagaria o BERTimbau duas vezes.
   - Campo novo numa resposta sem `response_model` não muda o OpenAPI.
2. **Drivers ficam em `GET /indicadores/drivers`**, com amostra padrão de 50 e teto de 200 (o mesmo desenho de `/saude/deriva`).
   - O filtro por **tema** sai do E1: tema é calculado na hora pelo Radar, e o impacto por tema é o E6.
3. **O painel de drivers fica na Visão geral, atrás de um botão.** `/modelo/*` é só de `dev` (`fraus/api/seguranca.py:248`), e cada conversa da amostra custa uma passagem de modelo, então o painel não carrega sozinho.
4. **O contrafactual de primeira resposta recusa (422)** quando o alvo poria a resposta antes de uma fala anterior do cliente, porque reordenar a conversa inventaria outra conversa.

## Pontos de revisão

1. **Fusor binário (classes `[0, 2]`):** a decomposição tem um eixo só e o score refeito bate com `pontuar`. Teste na Tarefa 1.
2. **Conversa sem fala do cliente:** `explicacao` é `null`, o contrafactual responde 422 e os drivers contam a conversa em `sem_sinal`. Testes nas Tarefas 4, 5 e 6.
3. **Conversa de outra régua:** o contrafactual responde 409 (como `/atribuicao`) e os drivers a contam em `defasadas`. Testes nas Tarefas 5 e 6.
4. **Grupo vazio nos drivers** (nenhum detrator na amostra): `media` e `ic` saem `null`, nunca 0. Teste na Tarefa 6.
5. **Conversa sem par cliente→resposta:** o texto não inventa "espera de 0 s", e o contrafactual de primeira resposta responde 422. Testes nas Tarefas 3 e 5.

---

### Tarefa 1: decomposição exata do fusor

**Arquivos:**

- Modificar: `fraus/fusor.py`. Constantes `FAMILIAS` e `familia_da_feature` depois de `NOMES_FEATURES`; função `score_dos_logits`; métodos `_score_das_probabilidades` e `decompor`; `pontuar` passa a usar o helper.
- Teste: `tests/test_fusor_decomposicao.py` (novo).

**Interfaces:**

- Produz:
  - `FAMILIAS: tuple[str, ...]` = `("texto","emoji","tempo","emocao","lexico","estilo","incongruencia")`
  - `familia_da_feature(nome: str) -> str`
  - `score_dos_logits(referencia: int, eixos: list[dict]) -> float`
  - `Fusor.decompor(features) -> {"referencia": int, "eixos": [{"classe": int, "intercepto": float, "contribuicoes": dict[str, float], "por_familia": dict[str, float], "logit": float}], "score": float}`

- [ ] **Passo 1: escrever o teste que falha**

```python
# tests/test_fusor_decomposicao.py
"""Decomposicao EXATA do fusor: intercepto + contribuicoes = logit, e o score
sai dos logits sem aproximacao. E o que separa "explicacao" de "historia"."""
import math

import pytest

from fraus.fusor import (FAMILIAS, NOMES_FEATURES, Fusor, SATISFEITO,
                         familia_da_feature, score_dos_logits, vetorizar)


def _features(**sobrescritas):
    base = {nome: 0.0 for nome in NOMES_FEATURES}
    base.update(sobrescritas)
    return base


def _fusor_tres_classes() -> Fusor:
    exemplos, rotulos = [], []
    for i in range(30):
        ruido = (i % 7) / 10
        exemplos.append(_features(texto_prob_satisfeito_media=0.8 + ruido / 10,
                                  emoji_score_medio=0.6, latencia_mediana_s=10.0 + i))
        rotulos.append(2)
        exemplos.append(_features(texto_prob_satisfeito_media=0.4, texto_prob_insatisfeito_media=0.4,
                                  estilo_frac_caixa_alta=ruido, latencia_mediana_s=60.0 + i))
        rotulos.append(1)
        exemplos.append(_features(texto_prob_insatisfeito_media=0.9 - ruido / 10,
                                  emoji_score_medio=-0.6, latencia_mediana_s=400.0 + i, escalou=1.0))
        rotulos.append(0)
    fusor = Fusor()
    fusor.treinar(exemplos, rotulos)
    return fusor


def _fusor_binario() -> Fusor:
    exemplos, rotulos = [], []
    for i in range(20):
        exemplos.append(_features(texto_prob_satisfeito_media=0.9, latencia_mediana_s=8.0 + i))
        rotulos.append(2)
        exemplos.append(_features(texto_prob_insatisfeito_media=0.9, latencia_mediana_s=300.0 + i))
        rotulos.append(0)
    fusor = Fusor()
    fusor.treinar(exemplos, rotulos)
    return fusor


CASOS = [
    _features(texto_prob_satisfeito_media=0.7, emoji_score_medio=0.2, latencia_mediana_s=45.0),
    _features(texto_prob_insatisfeito_media=0.8, latencia_mediana_s=10800.0, escalou=1.0),
    _features(),
]


def test_familias_cobrem_o_contrato_exatamente_uma_vez():
    assert FAMILIAS == ("texto", "emoji", "tempo", "emocao", "lexico", "estilo", "incongruencia")
    assert [familia_da_feature(n) for n in NOMES_FEATURES].count("tempo") == 7
    assert {familia_da_feature(n) for n in NOMES_FEATURES} == set(FAMILIAS)


@pytest.mark.parametrize("fabrica", [_fusor_tres_classes, _fusor_binario])
@pytest.mark.parametrize("features", CASOS)
def test_intercepto_mais_contribuicoes_reproduz_o_log_da_razao(fabrica, features):
    fusor = fabrica()
    d = fusor.decompor(features)
    probabilidades = fusor._pipeline.predict_proba([vetorizar(features)])[0]
    classes = list(fusor._pipeline.named_steps["modelo"].classes_)
    p = dict(zip(classes, probabilidades))
    for eixo in d["eixos"]:
        soma = eixo["intercepto"] + sum(eixo["contribuicoes"].values())
        assert soma == pytest.approx(eixo["logit"], abs=1e-12)
        esperado = math.log(p[eixo["classe"]] / p[d["referencia"]])
        assert eixo["logit"] == pytest.approx(esperado, abs=1e-9)
        assert sum(eixo["por_familia"].values()) == pytest.approx(
            sum(eixo["contribuicoes"].values()), abs=1e-12)


@pytest.mark.parametrize("fabrica", [_fusor_tres_classes, _fusor_binario])
@pytest.mark.parametrize("features", CASOS)
def test_score_refeito_dos_logits_e_o_score_do_fusor(fabrica, features):
    fusor = fabrica()
    d = fusor.decompor(features)
    assert d["score"] == pytest.approx(fusor.pontuar(features), abs=1e-9)
    assert score_dos_logits(d["referencia"], d["eixos"]) == pytest.approx(d["score"], abs=1e-12)


def test_eixo_satisfeito_e_a_contribuicao_que_a_tela_ja_mostra():
    """Nada muda no numero que a tela mostra hoje: o eixo 2x0 E `contribuicoes`."""
    fusor = _fusor_tres_classes()
    features = CASOS[0]
    eixo = next(e for e in fusor.decompor(features)["eixos"] if e["classe"] == SATISFEITO)
    for nome, valor in fusor.contribuicoes(features).items():
        assert eixo["contribuicoes"][nome] == pytest.approx(valor, abs=1e-12)


def test_binario_tem_um_eixo_so():
    d = _fusor_binario().decompor(CASOS[0])
    assert d["referencia"] == 0
    assert [e["classe"] for e in d["eixos"]] == [2]
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_fusor_decomposicao.py`
Esperado: ERRO de import (`FAMILIAS` não existe).

- [ ] **Passo 3: implementação mínima.** Em `fraus/fusor.py`, logo depois da lista `NOMES_FEATURES`:

```python
# As SETE familias do vetor, na ordem de NOMES_FEATURES. Derivadas do NOME,
# nao digitadas de novo: o tempo e a unica familia sem prefixo comum, e por
# isso tem lista propria. O front recebe a familia do servidor em vez de
# repetir esta regra em TypeScript.
_FEATURES_DE_TEMPO = (
    "latencia_mediana_s", "latencia_p90_s", "latencia_primeira_resposta_s",
    "duracao_total_s", "qtd_turnos_cliente", "escalou", "abandonou",
)


def familia_da_feature(nome: str) -> str:
    """Familia de sinal de uma feature do contrato."""
    return "tempo" if nome in _FEATURES_DE_TEMPO else nome.split("_", 1)[0]


FAMILIAS = tuple(dict.fromkeys(familia_da_feature(nome) for nome in NOMES_FEATURES))
```

Depois de `PESO_NEUTRO_NO_SCORE`:

```python
def _score_das_probabilidades(por_classe: dict) -> float:
    """A projecao 0-100 das probabilidades por classe -- a UNICA copia da regra."""
    score = 100.0 * (
        por_classe.get(SATISFEITO, 0.0)
        + PESO_NEUTRO_NO_SCORE * por_classe.get(NEUTRO, 0.0)
    )
    return max(0.0, min(100.0, score))


def score_dos_logits(referencia: int, eixos: list[dict]) -> float:
    """O score a partir dos logits contra a classe de referencia.

    `P = softmax(0, l_1, l_2)`: e o que a regressao multinomial faz, so que
    escrito com os numeros que a explicacao mostra. Existe para o teste provar
    que a decomposicao REPRODUZ a nota, em vez de aproxima-la.
    """
    logits = {referencia: 0.0, **{eixo["classe"]: eixo["logit"] for eixo in eixos}}
    maior = max(logits.values())
    exponenciais = {classe: math.exp(valor - maior) for classe, valor in logits.items()}
    total = sum(exponenciais.values())
    return _score_das_probabilidades({c: v / total for c, v in exponenciais.items()})
```

`pontuar` troca o miolo pelo helper (o comportamento é idêntico):

```python
        probabilidades = self._pipeline.predict_proba([vetorizar(features)])[0]
        classes = list(self._pipeline.named_steps["modelo"].classes_)
        return _score_das_probabilidades(dict(zip(classes, probabilidades)))
```

Novo método no `Fusor`, depois de `contribuicoes`:

```python
    def decompor(self, features: dict[str, float]) -> dict:
        """A nota desmontada em parcelas que SOMAM, sem aproximacao.

        A regressao multinomial tem, contra a classe de referencia (a menor,
        insatisfeito), um eixo aditivo por classe:
        `log(P_c / P_ref) = (b_c - b_ref) + soma_i (w_c - w_ref)_i * z_i`, com `z`
        no espaco em que o fusor opera (espera em log1p, depois o scaler). O
        score sai EXATAMENTE desses logits (`score_dos_logits`). No caso
        binario o sklearn guarda uma linha so, que ja e classes_[1] contra
        classes_[0].
        """
        modelo = self._pipeline.named_steps["modelo"]
        z = self._pipeline.named_steps["escala"].transform([vetorizar(features)])[0]
        classes = [int(c) for c in modelo.classes_]
        if len(classes) == 2:
            linhas = [(classes[1], modelo.intercept_[0], modelo.coef_[0])]
        else:
            linhas = [
                (classe, modelo.intercept_[i] - modelo.intercept_[0], modelo.coef_[i] - modelo.coef_[0])
                for i, classe in enumerate(classes) if i > 0
            ]
        eixos = []
        for classe, intercepto, pesos in linhas:
            contribuicoes = {nome: float(p * v) for nome, p, v in zip(NOMES_FEATURES, pesos, z)}
            por_familia = dict.fromkeys(FAMILIAS, 0.0)
            for nome, valor in contribuicoes.items():
                por_familia[familia_da_feature(nome)] += valor
            eixos.append({
                "classe": classe,
                "intercepto": float(intercepto),
                "contribuicoes": contribuicoes,
                "por_familia": por_familia,
                "logit": float(intercepto) + sum(contribuicoes.values()),
            })
        return {"referencia": classes[0], "eixos": eixos, "score": score_dos_logits(classes[0], eixos)}
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `uv run pytest -q tests/test_fusor_decomposicao.py tests/test_fusor.py tests/test_indicadores.py`
Esperado: tudo PASS. `test_fusor.py` e `test_indicadores.py` provam que o `pontuar` refatorado não mudou nada, incluindo a fronteira 6/7 e 8/9.

- [ ] **Passo 5: stage**: `git add fraus/fusor.py tests/test_fusor_decomposicao.py`

---

### Tarefa 2: efeito por família em pontos de score

**Arquivos:**

- Modificar: `fraus/fusor.py` (métodos `score_com_familia_na_media` e `efeitos_por_familia`).
- Teste: `tests/test_fusor_decomposicao.py` (acrescentar).

**Interfaces:**

- Consome: `FAMILIAS`, `familia_da_feature`, `_score_das_probabilidades` (Tarefa 1).
- Produz:
  - `Fusor.score_com_familia_na_media(features, familia: str) -> float`
  - `Fusor.efeitos_por_familia(features) -> dict[str, float]`, em que positivo quer dizer que a família empurrou a nota para cima.

- [ ] **Passo 1: teste que falha** (acrescentar ao arquivo da Tarefa 1)

```python
def test_familia_ja_na_media_tem_efeito_zero():
    fusor = _fusor_tres_classes()
    media = fusor._pipeline.named_steps["escala"].mean_
    features = dict(CASOS[0])
    # Coloca TODA feature de estilo exatamente na media do treino.
    for i, nome in enumerate(NOMES_FEATURES):
        if familia_da_feature(nome) == "estilo":
            features[nome] = float(media[i])
    assert fusor.efeitos_por_familia(features)["estilo"] == pytest.approx(0.0, abs=1e-9)


def test_efeito_e_score_atual_menos_score_com_a_familia_na_media():
    fusor = _fusor_tres_classes()
    features = CASOS[1]
    efeitos = fusor.efeitos_por_familia(features)
    assert set(efeitos) == set(FAMILIAS)
    for familia, efeito in efeitos.items():
        assert efeito == pytest.approx(
            fusor.pontuar(features) - fusor.score_com_familia_na_media(features, familia), abs=1e-9)


def test_texto_insatisfeito_pesa_contra():
    efeitos = _fusor_tres_classes().efeitos_por_familia(CASOS[1])
    assert efeitos["texto"] < 0


def test_familia_desconhecida_e_erro():
    with pytest.raises(ValueError, match="ironia"):
        _fusor_tres_classes().score_com_familia_na_media(CASOS[0], "ironia")
```

O primeiro teste depende de que a família estilo não tenha feature em `FEATURES_EM_LOG`, o que vale hoje: o `log1p` só alcança as quatro de espera, e por isso o valor bruto na média do scaler dá `z = 0`.

- [ ] **Passo 2: rodar e ver falhar.** `uv run pytest -q tests/test_fusor_decomposicao.py` deve dar AttributeError em `efeitos_por_familia`.

- [ ] **Passo 3: implementação mínima** (métodos do `Fusor`, depois de `decompor`)

```python
    def score_com_familia_na_media(self, features: dict[str, float], familia: str) -> float:
        """O score se esta familia estivesse na MEDIA do treino (z = 0).

        E um recalculo exato, nao uma aproximacao -- mas nao aditivo: as
        familias nao somam o score, porque o score nao e linear. A soma exata
        mora no eixo de logit (`decompor`).
        """
        if familia not in FAMILIAS:
            raise ValueError(f"familia fora do vetor: {familia!r}; as do vetor sao {FAMILIAS}")
        modelo = self._pipeline.named_steps["modelo"]
        z = self._pipeline.named_steps["escala"].transform([vetorizar(features)])[0].copy()
        for i, nome in enumerate(NOMES_FEATURES):
            if familia_da_feature(nome) == familia:
                z[i] = 0.0
        probabilidades = modelo.predict_proba([z])[0]
        return _score_das_probabilidades(dict(zip(modelo.classes_, probabilidades)))

    def efeitos_por_familia(self, features: dict[str, float]) -> dict[str, float]:
        """Quantos pontos de score cada familia moveu nesta conversa, com sinal."""
        atual = self.pontuar(features)
        return {f: atual - self.score_com_familia_na_media(features, f) for f in FAMILIAS}
```

- [ ] **Passo 4: rodar e ver passar.** `uv run pytest -q tests/test_fusor_decomposicao.py` deve dar PASS.
- [ ] **Passo 5: stage.** `git add fraus/fusor.py tests/test_fusor_decomposicao.py`

---

### Tarefa 3: texto por template

**Arquivos:**

- Criar: `fraus/explicacao.py`.
- Teste: `tests/test_explicacao.py`.

**Interfaces:**

- Consome: `FAMILIAS` (Tarefa 1).
- Produz:
  - `LIMIAR_PONTOS = 1.0`, `ROTULO_FAMILIA: dict[str, str]`, `AVISO: str`, `ROTULO_ASSOCIACAO: str`
  - `formatar_duracao(segundos: float) -> str`
  - `explicar(efeitos: dict[str, float], features: dict[str, float], ha_latencia: bool) -> {"frases": list[str], "contra": list[dict], "a_favor": list[dict], "aviso": str}`. Cada item tem `familia`, `rotulo`, `pontos` e `detalhe`.

- [ ] **Passo 1: teste que falha**

```python
# tests/test_explicacao.py
from fraus.explicacao import AVISO, LIMIAR_PONTOS, explicar, formatar_duracao
from fraus.fusor import FAMILIAS


def _efeitos(**v):
    base = dict.fromkeys(FAMILIAS, 0.0)
    base.update(v)
    return base


FEATURES = {"latencia_mediana_s": 720.0, "latencia_primeira_resposta_s": 95.0}


def test_formatar_duracao():
    assert formatar_duracao(42) == "42 s"
    assert formatar_duracao(720) == "12 min"
    assert formatar_duracao(10800) == "3 h"
    assert formatar_duracao(5430) == "1 h 30 min"


def test_contra_e_a_favor_com_detalhe_de_tempo():
    r = explicar(_efeitos(tempo=-23.4, texto=31.0, emoji=2.0), FEATURES, ha_latencia=True)
    assert r["frases"][0] == (
        "Pesou contra: o ritmo do atendimento (espera mediana de 12 min; "
        "primeira resposta em 2 min), −23,4 pontos.")
    assert r["frases"][1] == "Pesou a favor: o texto do cliente, +31,0 pontos; os emojis, +2,0 pontos."
    assert r["aviso"] == AVISO


def test_no_maximo_dois_por_lado_em_ordem_de_magnitude():
    r = explicar(_efeitos(texto=-5, emoji=-9, estilo=-2, lexico=-30), FEATURES, ha_latencia=True)
    assert [i["familia"] for i in r["contra"]] == ["lexico", "emoji"]


def test_abaixo_do_limiar_nao_entra():
    r = explicar(_efeitos(texto=LIMIAR_PONTOS - 0.01), FEATURES, ha_latencia=True)
    assert r["contra"] == [] and r["a_favor"] == []
    assert r["frases"] == ["Nenhum sinal sozinho moveu a nota em 1 ponto ou mais."]


def test_sem_par_cliente_resposta_nao_inventa_espera():
    r = explicar(_efeitos(tempo=-8.0), {"latencia_mediana_s": 0.0,
                                        "latencia_primeira_resposta_s": 0.0}, ha_latencia=False)
    assert r["contra"][0]["detalhe"] is None
    assert "0 s" not in r["frases"][0]


def test_aviso_declara_associacao_tempo_sintetico_e_nao_aditividade():
    for trecho in ("não causa", "sintéticos", "não somam"):
        assert trecho in AVISO
```

- [ ] **Passo 2: rodar e ver falhar.** `uv run pytest -q tests/test_explicacao.py` deve dar ModuleNotFoundError.

- [ ] **Passo 3: implementação mínima**

```python
# fraus/explicacao.py
"""Explicacao de uma nota por TEMPLATE, a partir dos numeros do proprio fusor.

Sem LLM (invariante 1) e sem texto livre: cada frase e montada de pecas fixas
com os efeitos que `Fusor.efeitos_por_familia` calculou. A explicacao e o
modelo, nao uma historia sobre ele. Nada aqui grava ou corrige nota.
"""

from fraus.fusor import FAMILIAS

# Abaixo de 1 ponto de score, um efeito nao muda nota 0-10 em caso nenhum que
# importe, e lista-lo seria ruido. Limiar sem procedencia, declarado.
LIMIAR_PONTOS = 1.0
MAXIMO_POR_LADO = 2

ROTULO_FAMILIA = {
    "texto": "o texto do cliente",
    "emoji": "os emojis",
    "tempo": "o ritmo do atendimento",
    "emocao": "a emoção lida no texto",
    "lexico": "o vocabulário (léxico de sentimento)",
    "estilo": "o estilo da escrita",
    "incongruencia": "os sinais de incongruência",
}
assert set(ROTULO_FAMILIA) == set(FAMILIAS)

ROTULO_ASSOCIACAO = "associação no modelo, não causa"
AVISO = (
    "Efeito de cada sinal medido no próprio modelo, trocando o sinal pela média "
    "do treino. Os efeitos não somam a nota, porque a nota não é linear; a soma "
    "exata está no eixo de logit. É " + ROTULO_ASSOCIACAO + ". O sinal de tempo "
    "foi treinado em dados sintéticos."
)


def formatar_duracao(segundos: float) -> str:
    """42 s, 12 min, 3 h, 1 h 30 min -- arredondado, para leitura."""
    if segundos < 60:
        return f"{round(segundos)} s"
    minutos = round(segundos / 60)
    if minutos < 60:
        return f"{minutos} min"
    horas, resto = divmod(minutos, 60)
    return f"{horas} h" if resto == 0 else f"{horas} h {resto} min"


def _pontos(valor: float) -> str:
    return f"{valor:+.1f}".replace(".", ",").replace("-", "−") + " pontos"


def _detalhe(familia: str, features: dict[str, float], ha_latencia: bool) -> str | None:
    if familia != "tempo" or not ha_latencia:
        return None
    return (f"espera mediana de {formatar_duracao(features['latencia_mediana_s'])}; "
            f"primeira resposta em {formatar_duracao(features['latencia_primeira_resposta_s'])}")


def _trecho(item: dict) -> str:
    detalhe = f" ({item['detalhe']})" if item["detalhe"] else ""
    return f"{item['rotulo']}{detalhe}, {_pontos(item['pontos'])}"


def explicar(efeitos: dict[str, float], features: dict[str, float], ha_latencia: bool) -> dict:
    """As duas familias de maior efeito para cada lado, em frases fixas."""
    def itens(filtro, chave):
        escolhidos = sorted(((f, v) for f, v in efeitos.items() if filtro(v)), key=chave)
        return [
            {"familia": f, "rotulo": ROTULO_FAMILIA[f], "pontos": round(v, 1),
             "detalhe": _detalhe(f, features, ha_latencia)}
            for f, v in escolhidos[:MAXIMO_POR_LADO]
        ]

    contra = itens(lambda v: v <= -LIMIAR_PONTOS, lambda par: par[1])
    a_favor = itens(lambda v: v >= LIMIAR_PONTOS, lambda par: -par[1])
    frases = []
    if contra:
        frases.append("Pesou contra: " + "; ".join(_trecho(i) for i in contra) + ".")
    if a_favor:
        frases.append("Pesou a favor: " + "; ".join(_trecho(i) for i in a_favor) + ".")
    if not frases:
        frases.append("Nenhum sinal sozinho moveu a nota em 1 ponto ou mais.")
    return {"frases": frases, "contra": contra, "a_favor": a_favor, "aviso": AVISO}
```

- [ ] **Passo 4: rodar e ver passar.** `uv run pytest -q tests/test_explicacao.py` deve dar PASS.
- [ ] **Passo 5: stage.** `git add fraus/explicacao.py tests/test_explicacao.py`

---

### Tarefa 4: `explicacao` na atribuição (Motor e rota)

**Arquivos:**

- Modificar: `fraus/motor.py` (`_atribuir`, perto da linha 336) e `fraus/api/rotas/conversas.py` (resposta de `/atribuicao`, perto da linha 352).
- Teste: `tests/test_explicacao_motor.py` (novo).

**Interfaces:**

- Consome: `Fusor.decompor`, `Fusor.efeitos_por_familia`, `explicar`, `latencias_da_conversa` (`fraus/sinais/tempo.py`).
- Produz: `atribuicao["explicacao"]`. É `None` sem fala do cliente. Com fala, é `{"decomposicao": <decompor>, "efeitos": dict[str, float], "familia_da_feature": dict[str, str], "frases", "contra", "a_favor", "aviso"}`.

- [ ] **Passo 1: teste que falha**

```python
# tests/test_explicacao_motor.py
"""A explicacao viaja na atribuicao e bate com o score que o Motor da."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem
from tests.test_motor import _motor

BASE = datetime(2026, 9, 4, 10, 0, 0, tzinfo=timezone.utc)


def _conversa(id_="c1", com_cliente=True):
    mensagens = [Mensagem(autor="bot", texto="ola", enviada_em=BASE)]
    if com_cliente:
        mensagens += [
            Mensagem(autor="cliente", texto="demorou demais", enviada_em=BASE + timedelta(seconds=5)),
            Mensagem(autor="bot", texto="desculpe", enviada_em=BASE + timedelta(seconds=65)),
        ]
    return Conversa(id=id_, canal="csv", iniciada_em=BASE, mensagens=mensagens)


def test_motor_anexa_explicacao_que_reproduz_o_score():
    motor = _motor()
    conversa = _conversa()
    explicacao = motor.atribuir_conversa(conversa)["explicacao"]
    assert explicacao["decomposicao"]["score"] == pytest.approx(motor.pontuar_conversa(conversa), abs=1e-9)
    assert set(explicacao["efeitos"]) == set(explicacao["familia_da_feature"].values())
    assert explicacao["frases"]


def test_sem_fala_do_cliente_explicacao_e_none():
    assert _motor().atribuir_conversa(_conversa(com_cliente=False))["explicacao"] is None


def test_rota_de_atribuicao_devolve_explicacao_sem_mudar_o_score(tmp_path):
    motor = _motor()
    banco = Banco(tmp_path / "f.db")
    conversa = _conversa()
    score = motor.pontuar_conversa(conversa)
    banco.salvar_lote([(conversa, score, "neutro")], lexico_versao=0, regua=motor.regua())
    cliente = TestClient(criar_app(banco=banco, motor=motor))
    corpo = cliente.get("/conversas/c1/atribuicao").json()
    assert corpo["explicacao"]["decomposicao"]["score"] == pytest.approx(corpo["score"], abs=1e-9)
    assert banco.buscar("c1")[1] == score
```

Antes de rodar, conferir o formato de `Banco.salvar_lote` (`fraus/db.py:830`) e o de `regua_da_conversa`. Ajustar a tupla do teste ao formato real: nome e ordem dos campos vêm do código, não deste plano.

- [ ] **Passo 2: rodar e ver falhar.** `uv run pytest -q tests/test_explicacao_motor.py` deve dar KeyError `explicacao`.

- [ ] **Passo 3: implementação mínima.** Em `Motor._atribuir`, logo depois de `contribuicoes = self._fusor.contribuicoes(features)`:

```python
            efeitos = self._fusor.efeitos_por_familia(features)
            explicacao = {
                "decomposicao": self._fusor.decompor(features),
                "efeitos": efeitos,
                "familia_da_feature": {n: familia_da_feature(n) for n in NOMES_FEATURES},
                **explicar(efeitos, features, ha_latencia=bool(latencias_da_conversa(conversa))),
            }
```

Também:

- Inicializar `explicacao = None` ao lado de `contribuicoes = features = None`.
- Acrescentar `"explicacao": explicacao,` ao dict devolvido.
- Importar `familia_da_feature`, `NOMES_FEATURES`, `explicar` e `latencias_da_conversa`.

Em `fraus/api/rotas/conversas.py`, na resposta de `/atribuicao`, acrescentar:

```python
        # Decomposicao exata, efeito por familia e frases por template. `get`
        # porque motor duble de teste nao a produz; `None` e "nao ha".
        "explicacao": atribuicao.get("explicacao"),
```

- [ ] **Passo 4: rodar e ver passar.** `uv run pytest -q tests/test_explicacao_motor.py tests/test_motor.py tests/test_api.py tests/test_explicacao_usa_curadoria.py` deve dar PASS.
- [ ] **Passo 5: stage.** `git add fraus/motor.py fraus/api/rotas/conversas.py tests/test_explicacao_motor.py`

---

### Tarefa 5: contrafactual de espera

**Arquivos:**

- Modificar: `fraus/operacao.py`. Função `ajustar_primeira_resposta` ao lado de `limitar_esperas`, que é a reescrita de timestamps reaproveitada.
- Modificar: `fraus/motor.py` (método `comparar_cenario`) e `fraus/api/esquemas.py` (`PedidoContrafactual`).
- Modificar: `fraus/api/rotas/conversas.py`. Rota `POST /conversas/{conversa_id:path}/contrafactual` e helper `_exigir_regua_vigente`, usado também por `/atribuicao`.
- Teste: `tests/test_contrafactual.py` (novo).

**Interfaces:**

- Produz:
  - `ajustar_primeira_resposta(conversa, alvo_s: float) -> Conversa | None`. Devolve `None` sem par cliente→resposta e levanta `ValueError` se a ordem quebraria.
  - `Motor.comparar_cenario(original, alterada, curadoria=None) -> {"antes": float, "depois": float, "z_antes": dict, "z_depois": dict}`
  - Resposta da rota: `{"conversa_id", "antes": {score, nota, categoria}, "depois": {...}, "delta_score", "hipotese", "metodo"}`, ou 422 com `detail` citando as features fora da faixa.

- [ ] **Passo 1: teste que falha**

```python
# tests/test_contrafactual.py
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem
from fraus.operacao import ajustar_primeira_resposta
from fraus.sinais.tempo import latencias_da_conversa
from tests.test_motor import _motor

BASE = datetime(2026, 9, 4, 10, 0, 0, tzinfo=timezone.utc)


def _c(*falas, id_="c1", canal="csv"):
    return Conversa(id=id_, canal=canal, iniciada_em=BASE, mensagens=[
        Mensagem(autor=a, texto=t, enviada_em=BASE + timedelta(seconds=s)) for a, t, s in falas])


def test_ajusta_so_a_primeira_resposta_e_preserva_os_intervalos_seguintes():
    c = _c(("cliente", "oi", 0), ("bot", "ola", 600), ("cliente", "e ai", 620), ("bot", "ok", 680))
    alterada = ajustar_primeira_resposta(c, 60)
    assert latencias_da_conversa(alterada) == [60.0, 60.0]


def test_sem_par_cliente_resposta_devolve_none():
    assert ajustar_primeira_resposta(_c(("bot", "ola", 0)), 60) is None


def test_alvo_antes_de_fala_anterior_do_cliente_e_recusado():
    c = _c(("cliente", "oi", 0), ("cliente", "alo", 100), ("bot", "ola", 300))
    with pytest.raises(ValueError):
        ajustar_primeira_resposta(c, 30)


@pytest.fixture
def api(tmp_path):
    motor = _motor()
    banco = Banco(tmp_path / "f.db")
    conversas = [
        _c(("cliente", "oi", 0), ("bot", "ola", 120), ("cliente", "valeu", 130)),
        _c(("bot", "ola", 0), id_="mudo"),
    ]
    banco.salvar_lote([(c, motor.pontuar_conversa(c), None) for c in conversas],
                      lexico_versao=0, regua=motor.regua())
    return TestClient(criar_app(banco=banco, motor=motor)), banco, motor


def test_dentro_da_faixa_responde_antes_e_depois_sem_gravar(api):
    cliente, banco, _ = api
    gravado = banco.buscar("c1")[1]
    r = cliente.post("/conversas/c1/contrafactual", json={"primeira_resposta_s": 60})
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["antes"]["score"] == pytest.approx(gravado, abs=1e-9)
    assert "sintético" in corpo["metodo"]
    assert banco.buscar("c1")[1] == gravado


def test_exatamente_uma_hipotese(api):
    cliente, _, _ = api
    assert cliente.post("/conversas/c1/contrafactual", json={}).status_code == 422
    assert cliente.post("/conversas/c1/contrafactual",
                        json={"primeira_resposta_s": 60, "espera_maxima_s": 60}).status_code == 422


def test_fora_da_faixa_de_treino_e_recusado(api):
    cliente, _, _ = api
    r = cliente.post("/conversas/c1/contrafactual", json={"primeira_resposta_s": 86400})
    assert r.status_code == 422
    assert "faixa de treino" in r.json()["detail"]


def test_sem_sinal_do_cliente_e_422(api):
    cliente, _, _ = api
    assert cliente.post("/conversas/mudo/contrafactual",
                        json={"espera_maxima_s": 60}).status_code == 422


def test_inexistente_e_404(api):
    cliente, _, _ = api
    assert cliente.post("/conversas/nada/contrafactual",
                        json={"espera_maxima_s": 60}).status_code == 404
```

Antes de rodar, quatro conferências:

1. **Faixa no fusor sintético.** O teste de "fora da faixa" depende do `_fusor_treinado` de `tests/test_motor.py`, que tem `latencia_*` constante 0 no treino. No `StandardScaler`, feature constante tem `scale_ = 1`. 86400 s vira `log1p ≈ 11,4`, ou seja `|z| ≈ 11 > 4`. Conferir esse número no REPL antes de confiar no teste.
2. **Faixa no caso "dentro".** Pelo mesmo motivo, o caso "dentro da faixa" com 60 s dá `log1p(60) ≈ 4,1`, que **também** passa de 4. Nesse caso, construir na fixture um fusor treinado com `latencia_primeira_resposta_s` variando de 5 a 600 s e um `Motor` com ele, usando os dublês de `tests/test_motor.py`.
3. **Escopo.** Acrescentar um teste de escopo no molde dos testes de `/atribuicao` com `BancoComEscopo`. Procurar o molde com `grep -n "BancoComEscopo" tests/*.py`.
4. **Régua antiga.** Acrescentar um teste que grave a conversa com `regua="outra"` e espere 409.

- [ ] **Passo 2: rodar e ver falhar.** `uv run pytest -q tests/test_contrafactual.py` deve dar ImportError em `ajustar_primeira_resposta`.

- [ ] **Passo 3: implementação mínima.** Em `fraus/operacao.py`:

```python
def ajustar_primeira_resposta(conversa, alvo_s):
    """Cenario: a PRIMEIRA resposta chega `alvo_s` depois da primeira fala do
    cliente; dela em diante tudo anda junto, preservando os intervalos seguintes.

    `None` quando nao ha par cliente -> resposta (nao ha o que ajustar).
    `ValueError` quando o alvo poria a resposta antes de uma fala que ja
    aconteceu: reordenar a conversa seria inventar outra conversa.
    """
    mensagens = conversa.mensagens
    i = next((k for k, m in enumerate(mensagens) if m.autor == "cliente"), None)
    if i is None:
        return None
    j = next((k for k in range(i + 1, len(mensagens)) if mensagens[k].autor in RESPONDENTES), None)
    if j is None:
        return None
    novo = mensagens[i].enviada_em + timedelta(seconds=alvo_s)
    if novo < mensagens[j - 1].enviada_em:
        raise ValueError("a primeira resposta nao pode chegar antes de uma fala anterior do cliente")
    deslocamento = mensagens[j].enviada_em - novo
    alteradas = mensagens[:j] + [m.model_copy(update={"enviada_em": m.enviada_em - deslocamento})
                                 for m in mensagens[j:]]
    encerrada = conversa.encerrada_em - deslocamento if conversa.encerrada_em else None
    return conversa.model_copy(update={"mensagens": alteradas, "encerrada_em": encerrada})
```

Importar `RESPONDENTES` de `fraus.sinais.tempo`. `timedelta` já é importado ali por causa de `limitar_esperas`; confirmar.

Em `fraus/motor.py`:

```python
    def comparar_cenario(self, original, alterada, curadoria=None) -> dict:
        """Score e z das duas versoes. So o RELOGIO muda entre elas."""
        f_antes = montar_features(original, self._classificador, self._emocao, curadoria)
        f_depois = montar_features(alterada, self._classificador, self._emocao, curadoria)
        return {"antes": self._fusor.pontuar(f_antes), "depois": self._fusor.pontuar(f_depois),
                "z_antes": self._fusor.z_das_features(f_antes),
                "z_depois": self._fusor.z_das_features(f_depois)}
```

Em `fraus/api/esquemas.py`:

```python
class PedidoContrafactual(BaseModel):
    """Uma hipotese de espera por vez -- duas juntas nao diriam qual moveu a nota."""
    primeira_resposta_s: float | None = Field(default=None, ge=0, le=86400)
    espera_maxima_s: float | None = Field(default=None, gt=0, le=86400)

    @model_validator(mode="after")
    def _exatamente_uma(self):
        if (self.primeira_resposta_s is None) == (self.espera_maxima_s is None):
            raise ValueError("informe exatamente uma hipotese: primeira_resposta_s ou espera_maxima_s")
        return self
```

Conferir os imports de `Field` e `model_validator` no topo do arquivo.

Em `fraus/api/rotas/conversas.py`, extrair o bloco de régua de `/atribuicao` para:

```python
def _exigir_regua_vigente(ctx, conversa_id):
    versoes = ctx.banco.regua_da_conversa(conversa_id)
    vigente = (ctx.curadoria_vigente().versao, ctx.regua_vigente())
    if versoes != vigente:
        raise HTTPException(status_code=409, detail=(
            "a conversa foi pontuada com outra versao do lexico ou do modelo; "
            "repontue antes de gerar uma explicacao, para nao explicar uma nota "
            "historica com sinais atuais"))
```

Chamar o helper em `/atribuicao`, com a mesma mensagem e o mesmo status. Depois, a rota nova:

```python
METODO_CONTRAFACTUAL = (
    "sensibilidade da previsão a uma alteração controlada do relógio; não mede efeito "
    "real no cliente; nenhum score gravado é alterado; o sinal de tempo do fusor foi "
    "treinado em dados sintéticos")


@router.post("/conversas/{conversa_id:path}/contrafactual")
def contrafactual(conversa_id: str, pedido: PedidoContrafactual,
                  ctx: Contexto = Depends(obter_contexto)) -> dict:
    """E se a espera tivesse sido outra? So dentro da faixa de treino (|z| <= 4)."""
    exigir_real(ctx)
    achado = ctx.banco.buscar(conversa_id)
    if achado is None:
        raise HTTPException(404, "conversa nao encontrada")
    original = achado[0]
    if not original.tem_sinal_cliente:
        raise HTTPException(422, "sem sinal do cliente: nao ha nota para comparar")
    _exigir_regua_vigente(ctx, conversa_id)
    exigir_orcamento([original])
    try:
        alterada = (ajustar_primeira_resposta(original, pedido.primeira_resposta_s)
                    if pedido.primeira_resposta_s is not None
                    else limitar_esperas(original, pedido.espera_maxima_s))
    except ValueError as erro:
        raise HTTPException(422, str(erro)) from erro
    if alterada is None:
        raise HTTPException(422, "a conversa nao tem par cliente -> resposta para ajustar")
    r = ctx.motor.comparar_cenario(original, alterada, ctx.curadoria_vigente())
    fora = sorted({nome for z in (r["z_antes"], r["z_depois"])
                   for nome, valor in z.items() if abs(valor) > LIMIAR_Z})
    if fora:
        raise HTTPException(422, (
            f"fora da faixa de treino (|z| > {LIMIAR_Z:g}) em: {', '.join(fora)}. "
            "O modelo nao foi treinado com esses valores; extrapolar seria inventar a resposta."))
    faixas = ctx.faixas_vigentes()

    def ficha(score):
        return {"score": score, "nota": nota_0_10(score), "categoria": ctx.categoria_de(score, faixas)}

    return {"conversa_id": original.id, "antes": ficha(r["antes"]), "depois": ficha(r["depois"]),
            "delta_score": r["depois"] - r["antes"], "hipotese": pedido.model_dump(exclude_none=True),
            "metodo": METODO_CONTRAFACTUAL}
```

Imports: `exigir_real` e `exigir_orcamento` de `fraus.api.rotas.operacao`, `ajustar_primeira_resposta` e `limitar_esperas` de `fraus.operacao`, `LIMIAR_Z` de `fraus.deriva`, `PedidoContrafactual` de `fraus.api.esquemas`.

Se importar de `fraus.api.rotas.operacao` dentro de `conversas.py` criar import circular, mover `exigir_real` e `exigir_orcamento` para `fraus/api/rotas/_comum.py`. Isso só se o import quebrar, e o motivo vai registrado no commit.

- [ ] **Passo 4: rodar e ver passar.** `uv run pytest -q tests/test_contrafactual.py tests/test_explicacao_usa_curadoria.py tests/test_operacao.py` deve dar PASS. O teste de régua antiga de `/atribuicao` precisa continuar verde.
- [ ] **Passo 5: stage.** `git add fraus/operacao.py fraus/motor.py fraus/api/esquemas.py fraus/api/rotas/conversas.py tests/test_contrafactual.py`

---

### Tarefa 6: drivers agregados com bootstrap

**Arquivos:**

- Modificar: `fraus/explicacao.py` (função `drivers`) e `fraus/motor.py` (método `contribuicao_por_familia`).
- Modificar: `fraus/api/rotas/indicadores.py` (rota `GET /indicadores/drivers`).
- Teste: `tests/test_drivers.py` (novo).

**Interfaces:**

- Produz:
  - `drivers(linhas: list[tuple[str, dict[str, float]]], semente: int = SEMENTE_DRIVERS) -> list[{"familia", "detratores": {"n", "media", "ic"}, "promotores": {...}}]`. `media` é `None` se `n = 0`; `ic` é `None` se `n < 2`.
  - `Motor.contribuicao_por_familia(conversa, curadoria=None) -> dict[str, float] | None`, sobre o eixo satisfeito × insatisfeito.
  - Resposta da rota: `{"recorte", "n_pedido", "amostra", "elegiveis", "sem_sinal", "defasadas", "semente", "eixo", "familias", "rotulo", "metodo"}`.

- [ ] **Passo 1: teste que falha**

```python
# tests/test_drivers.py
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.explicacao import ROTULO_ASSOCIACAO, drivers
from fraus.fusor import FAMILIAS
from fraus.modelos import Conversa, Mensagem
from tests.test_api import MotorFalso
from tests.test_motor import _motor


def _linha(categoria, **v):
    base = dict.fromkeys(FAMILIAS, 0.0)
    base.update(v)
    return (categoria, base)


def test_media_por_grupo_e_ic_reprodutivel():
    linhas = [_linha("detrator", tempo=-2.0 - i / 10) for i in range(10)] + \
             [_linha("promotor", texto=1.5 + i / 10) for i in range(10)]
    a, b = drivers(linhas), drivers(linhas)
    assert a == b
    tempo = next(f for f in a if f["familia"] == "tempo")
    assert tempo["detratores"]["media"] == pytest.approx(-2.45)
    lo, hi = tempo["detratores"]["ic"]
    assert lo <= -2.45 <= hi


def test_grupo_vazio_e_none_e_nao_zero():
    r = drivers([_linha("promotor", texto=1.0), _linha("promotor", texto=2.0)])
    texto = next(f for f in r if f["familia"] == "texto")
    assert texto["detratores"] == {"n": 0, "media": None, "ic": None}


def test_um_so_tem_media_e_nao_tem_ic():
    r = drivers([_linha("detrator", texto=-1.0)])
    assert next(f for f in r if f["familia"] == "texto")["detratores"] == {"n": 1, "media": -1.0, "ic": None}


def test_neutro_nao_entra_em_grupo():
    r = drivers([_linha("neutro", texto=9.0)])
    assert all(f["detratores"]["n"] == 0 and f["promotores"]["n"] == 0 for f in r)


BASE = datetime(2026, 9, 4, 10, 0, 0, tzinfo=timezone.utc)


def _c(id_, texto, canal="csv"):
    return Conversa(id=id_, canal=canal, iniciada_em=BASE, mensagens=[
        Mensagem(autor="cliente", texto=texto, enviada_em=BASE),
        Mensagem(autor="bot", texto="ok", enviada_em=BASE + timedelta(seconds=10))])


def test_rota_conta_sem_sinal_e_defasadas_e_rotula(tmp_path):
    motor = _motor()
    banco = Banco(tmp_path / "f.db")
    mudo = Conversa(id="mudo", canal="csv", iniciada_em=BASE,
                    mensagens=[Mensagem(autor="bot", texto="ola", enviada_em=BASE)])
    banco.salvar_lote([(_c("a", "ruim"), motor.pontuar_conversa(_c("a", "ruim")), None),
                       (mudo, None, None)], lexico_versao=0, regua=motor.regua())
    banco.salvar_lote([(_c("velha", "ruim"), 10.0, None)], lexico_versao=0, regua="outra")
    corpo = TestClient(criar_app(banco=banco, motor=motor)).get("/indicadores/drivers").json()
    assert corpo["sem_sinal"] == 1 and corpo["defasadas"] == 1 and corpo["amostra"] == 1
    assert corpo["rotulo"] == ROTULO_ASSOCIACAO


def test_n_fora_do_teto_e_400_e_duble_e_503(tmp_path):
    banco = Banco(tmp_path / "f.db")
    real = TestClient(criar_app(banco=banco, motor=_motor()))
    assert real.get("/indicadores/drivers?n=201").status_code == 400
    duble = TestClient(criar_app(banco=banco, motor=MotorFalso()))
    assert duble.get("/indicadores/drivers").status_code == 503


def test_filtro_de_canal(tmp_path):
    motor = _motor()
    banco = Banco(tmp_path / "f.db")
    banco.salvar_lote([(_c(f"x{i}", "ruim", canal="x"), 20.0, None) for i in range(3)] +
                      [(_c("y", "ruim", canal="y"), 20.0, None)], lexico_versao=0, regua=motor.regua())
    corpo = TestClient(criar_app(banco=banco, motor=motor)).get("/indicadores/drivers?canal=y").json()
    assert corpo["elegiveis"] == 1
```

Antes de rodar, três conferências:

1. **Formato de `salvar_lote`.** Ajustar à assinatura real, como na Tarefa 4.
2. **Escopo.** Acrescentar um teste com `BancoComEscopo`, no mesmo molde da Tarefa 5, provando que canal fora do escopo não entra em `elegiveis`.
3. **`n` padrão de 50.** Acrescentar um teste com 60 conversas elegíveis e esperar `amostra == 50`, mais uma chamada com `n=60` esperando `amostra == 60`.

- [ ] **Passo 2: rodar e ver falhar.** `uv run pytest -q tests/test_drivers.py` deve dar ImportError em `drivers`.

- [ ] **Passo 3: implementação mínima.** Em `fraus/explicacao.py`:

```python
import numpy as np

SEMENTE_DRIVERS = 20261014
GRUPOS = (("detrator", "detratores"), ("promotor", "promotores"))


def _resumo(valores: list[float], gerador) -> dict:
    if not valores:
        return {"n": 0, "media": None, "ic": None}
    media = float(np.mean(valores))
    if len(valores) < 2:
        return {"n": 1, "media": media, "ic": None}
    amostras = gerador.choice(np.asarray(valores), size=(1000, len(valores)), replace=True).mean(axis=1)
    return {"n": len(valores), "media": media,
            "ic": [float(np.percentile(amostras, 2.5)), float(np.percentile(amostras, 97.5))]}


def drivers(linhas, semente: int = SEMENTE_DRIVERS) -> list[dict]:
    """Media da contribuicao por familia em detratores x promotores, com IC 95%
    por bootstrap. `linhas` = [(categoria, {familia: contribuicao})]. Neutro nao
    entra em grupo. Grupo vazio e None, nunca 0 (invariante 2)."""
    gerador = np.random.default_rng(semente)
    return [
        {"familia": familia, **{
            plural: _resumo([c[familia] for cat, c in linhas if cat == categoria], gerador)
            for categoria, plural in GRUPOS}}
        for familia in FAMILIAS
    ]
```

As 1.000 reamostras ficam fixas dentro de `_resumo`, porque ninguém as varia (YAGNI).

Em `fraus/motor.py`:

```python
    def contribuicao_por_familia(self, conversa, curadoria=None) -> dict | None:
        """Soma da contribuicao por familia no eixo satisfeito x insatisfeito."""
        if not conversa.tem_sinal_cliente:
            return None
        features = montar_features(conversa, self._classificador, self._emocao, curadoria)
        eixos = self._fusor.decompor(features)["eixos"]
        return next(e for e in eixos if e["classe"] == SATISFEITO)["por_familia"]
```

Em `fraus/api/rotas/indicadores.py`:

```python
AMOSTRA_DRIVERS, TETO_DRIVERS = 50, 200
METODO_DRIVERS = (
    "média da contribuição por família no eixo log(P(satisfeito)/P(insatisfeito)), em "
    "detratores e promotores de uma amostra sorteada por semente; IC 95% por bootstrap "
    "(1.000 reamostras). Cada conversa da amostra custa uma passagem de modelo. "
    "O sinal de tempo do fusor foi treinado em dados sintéticos.")


@router.get("/indicadores/drivers")
def drivers_do_recorte(de: str | None = None, ate: str | None = None, canal: str | None = None,
                       n: int = AMOSTRA_DRIVERS, ctx: Contexto = Depends(obter_contexto)) -> dict:
    """O que mais puxa detratores e promotores -- associacao no modelo, nao causa."""
    if n < 1 or n > TETO_DRIVERS:
        raise HTTPException(400, f"n precisa estar entre 1 e {TETO_DRIVERS}: cada conversa custa "
                                 "uma passagem completa de modelo em CPU.")
    if not motor_e_real(ctx.motor):
        raise HTTPException(503, "drivers exigem o motor real; o dublê não tem coeficientes.")
    registros = ctx.registros_do_recorte(de, ate)
    if canal is not None:
        registros = [r for r in registros if r[0].canal == canal]
    curadoria = ctx.curadoria_vigente()
    defasadas = ctx.banco.ids_defasadas(curadoria.versao, ctx.regua_vigente())
    com_score = [(c, s) for c, s in registros if s is not None]
    elegiveis = sorted(((c, s) for c, s in com_score if c.id not in defasadas), key=lambda r: r[0].id)
    amostra = random.Random(SEMENTE_DRIVERS).sample(elegiveis, min(n, len(elegiveis)))
    faixas = ctx.faixas_vigentes()
    linhas = []
    for conversa, score in amostra:
        por_familia = ctx.motor.contribuicao_por_familia(conversa, curadoria)
        if por_familia is not None:
            linhas.append((ctx.categoria_de(score, faixas), por_familia))
    return {"recorte": {"de": de, "ate": ate, "canal": canal}, "n_pedido": n,
            "amostra": len(linhas), "elegiveis": len(elegiveis),
            "sem_sinal": len(registros) - len(com_score),
            "defasadas": len(com_score) - len(elegiveis), "semente": SEMENTE_DRIVERS,
            "eixo": "log(P(satisfeito)/P(insatisfeito))", "familias": drivers(linhas),
            "rotulo": ROTULO_ASSOCIACAO, "metodo": METODO_DRIVERS}
```

Imports: `random`, `HTTPException`, `motor_e_real` de `fraus.api.motor_preguicoso`, e `drivers`, `ROTULO_ASSOCIACAO` e `SEMENTE_DRIVERS` de `fraus.explicacao`.

A rota `/indicadores/drivers` é GET em `/indicadores/...`, então **não** entra em `rota_administrativa`. Os papéis `dev` e `usuario` a alcançam, como `/indicadores`.

- [ ] **Passo 4: rodar e ver passar.** `uv run pytest -q tests/test_drivers.py tests/test_api.py` deve dar PASS.
- [ ] **Passo 5: stage.** `git add fraus/explicacao.py fraus/motor.py fraus/api/rotas/indicadores.py tests/test_drivers.py`

---

### Tarefa 7: bloco "Por que esta nota" na tela do atendimento

**Arquivos:**

- Modificar: `dashboard/lib/api.ts`. Tipos `Explicacao` e `Contrafactual`, campo `explicacao?: Explicacao | null` em `Atribuicao`, função `simularContrafactual` no molde de `simularTexto` (linha ~943).
- Criar: `dashboard/components/PorQueEstaNota.tsx` (client component) e `dashboard/components/PorQueEstaNota.test.tsx`.
- Modificar: `dashboard/app/dashboard/atendimentos/[id]/page.tsx`. Renderizar acima do `PainelContribuicoes` (linha ~225), dentro do mesmo `Painel`.

Ler antes: `dashboard/DESIGN.md`, `dashboard/PRODUCT.md`, `components/PainelContribuicoes.tsx` e `components/EstadoVazio.tsx`.

**Interfaces:**

- Consome: `explicacao` de `/atribuicao` (Tarefa 4) e `POST /conversas/{id}/contrafactual` (Tarefa 5).
- Produz: `<PorQueEstaNota conversaId explicacao />`.

- [ ] **Passo 1: teste que falha**

```tsx
// dashboard/components/PorQueEstaNota.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PorQueEstaNota } from "./PorQueEstaNota";
import type { Explicacao } from "@/lib/api";

const explicacao: Explicacao = {
  frases: ["Pesou contra: o ritmo do atendimento, −23,4 pontos.", "Pesou a favor: o texto do cliente, +31,0 pontos."],
  contra: [{ familia: "tempo", rotulo: "o ritmo do atendimento", pontos: -23.4, detalhe: null }],
  a_favor: [{ familia: "texto", rotulo: "o texto do cliente", pontos: 31, detalhe: null }],
  aviso: "Efeito de cada sinal medido no próprio modelo... associação no modelo, não causa.",
  efeitos: { texto: 31, emoji: 0, tempo: -23.4, emocao: 0, lexico: 0, estilo: 0, incongruencia: 0 },
  decomposicao: { referencia: 0, score: 41.2, eixos: [] },
  familia_da_feature: {},
};

describe("PorQueEstaNota", () => {
  it("mostra as frases e o aviso de associação", () => {
    render(<PorQueEstaNota conversaId="c1" explicacao={explicacao} />);
    expect(screen.getByText(/Pesou contra/)).toBeTruthy();
    expect(screen.getByText(/não causa/)).toBeTruthy();
  });

  it("sem explicação, nomeia o que falta em vez de mostrar zero", () => {
    render(<PorQueEstaNota conversaId="c1" explicacao={null} />);
    expect(screen.getByText(/sem sinal do cliente/i)).toBeTruthy();
    expect(screen.queryByText(/0 pontos/)).toBeNull();
  });

  it("efeito zero não vira barra de 0 pontos", () => {
    render(<PorQueEstaNota conversaId="c1" explicacao={explicacao} />);
    expect(screen.queryByText(/^0,0 pontos$/)).toBeNull();
  });
});
```

Conferir o setup de testes existente, por exemplo `components/NotaLED.test.tsx`, e copiar os imports de render e matchers que ele usa.

- [ ] **Passo 2: rodar e ver falhar.** `cd dashboard && npx vitest run components/PorQueEstaNota.test.tsx` deve dar FAIL (módulo não existe).

- [ ] **Passo 3: implementação.** Tipos em `lib/api.ts`:

```ts
export type ItemDeExplicacao = { familia: string; rotulo: string; pontos: number; detalhe: string | null };
/** `explicacao` de `GET /conversas/{id}/atribuicao`: decomposicao exata no
 * servidor; o front so desenha (invariante 3 -- nada e recalculado aqui). */
export type Explicacao = {
  frases: string[];
  contra: ItemDeExplicacao[];
  a_favor: ItemDeExplicacao[];
  aviso: string;
  efeitos: Record<string, number>;
  decomposicao: { referencia: number; score: number; eixos: unknown[] };
  familia_da_feature: Record<string, string>;
};
export type FichaDeNota = { score: number; nota: number; categoria: Categoria };
export type Contrafactual = {
  conversa_id: string; antes: FichaDeNota; depois: FichaDeNota;
  delta_score: number; hipotese: Record<string, number>; metodo: string;
};
```

Mais `explicacao?: Explicacao | null;` em `Atribuicao`, e `simularContrafactual(id, corpo)` copiando `simularTexto`, com rota `/conversas/${encodeURIComponent(id)}/contrafactual` e o `detail` do 422 repassado no `Error`.

Componente, com pontos de design obrigatórios:

- tokens de `DESIGN.md`, sem cor nova;
- texto mínimo `text-xs`;
- `formatarComSinal` de `lib/formato` para os pontos;
- as frases do servidor exibidas como vieram;
- lista "efeito por família" só com |efeito| ≥ 1, cada uma com uma barra divergente simples (largura proporcional ao maior |efeito|);
- o `aviso` em texto pequeno logo abaixo;
- formulário "E se a primeira resposta tivesse chegado em [__] s?" com `<input type="number" min=0 max=86400>` e botão "Calcular";
- resultado "antes X → depois Y (nota a → b)" com o `metodo` impresso abaixo;
- o erro 422 aparece com a mensagem do servidor, sem sumir;
- `explicacao === null` usa `EstadoVazio` com "Sem sinal do cliente neste atendimento: não há nota para explicar".

Na página, passar `explicacao={atribuicao.explicacao ?? null}`. API antiga sem o campo cai no estado vazio, sem quebrar a tela.

- [ ] **Passo 4: rodar e ver passar.** `cd dashboard && npx vitest run components/PorQueEstaNota.test.tsx && npx tsc --noEmit` deve dar PASS.
- [ ] **Passo 5: conferência visual (controlador).** Subir `scripts/api_demo.py` com os pesos e `npm run dev`, abrir um atendimento em 390 px e em desktop, e conferir piso de 11 px e contraste. O dublê da demo não tem `explicacao`, e nesse caso o estado vazio deve aparecer.
- [ ] **Passo 6: stage.** `git add dashboard/lib/api.ts dashboard/components/PorQueEstaNota.tsx dashboard/components/PorQueEstaNota.test.tsx "dashboard/app/dashboard/atendimentos/[id]/page.tsx"`

---

### Tarefa 8: painel de drivers na Visão geral (sob demanda)

**Arquivos:**

- Modificar: `dashboard/lib/api.ts`. Tipo `Drivers` e função `obterDrivers(params)` como chamada do navegador, no molde de `simularTexto` mas com GET.
- Criar: `dashboard/components/PainelDrivers.tsx` e `dashboard/components/PainelDrivers.test.tsx`.
- Modificar: `dashboard/app/dashboard/page.tsx`. Renderizar no fim da coluna de indicadores, recebendo o recorte `de`/`ate` que a página já usa.

**Interfaces:**

- Consome: `GET /indicadores/drivers` (Tarefa 6).
- Produz: `<PainelDrivers de ate />`.

- [ ] **Passo 1: teste que falha**

```tsx
// dashboard/components/PainelDrivers.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TabelaDrivers } from "./PainelDrivers";
import type { Drivers } from "@/lib/api";

const base: Drivers = {
  recorte: { de: null, ate: null, canal: null }, n_pedido: 50, amostra: 2, elegiveis: 2,
  sem_sinal: 3, defasadas: 1, semente: 20261014, eixo: "log(P(satisfeito)/P(insatisfeito))",
  rotulo: "associação no modelo, não causa", metodo: "…",
  familias: [{ familia: "tempo",
    detratores: { n: 0, media: null, ic: null },
    promotores: { n: 2, media: 0.8, ic: [0.5, 1.1] } }],
};

describe("TabelaDrivers", () => {
  it("grupo vazio aparece como sem dado, não como 0", () => {
    render(<TabelaDrivers drivers={base} />);
    expect(screen.getByText(/sem detratores na amostra/i)).toBeTruthy();
  });
  it("declara amostra, sem sinal, defasadas e o rótulo de associação", () => {
    render(<TabelaDrivers drivers={base} />);
    expect(screen.getByText(/não causa/)).toBeTruthy();
    expect(screen.getByText(/3 sem sinal/)).toBeTruthy();
    expect(screen.getByText(/1 .*repontuar/)).toBeTruthy();
  });
});
```

- [ ] **Passo 2: rodar e ver falhar.** `cd dashboard && npx vitest run components/PainelDrivers.test.tsx` deve dar FAIL.

- [ ] **Passo 3: implementação.** O tipo `Drivers` espelha a resposta da Tarefa 6, com `media: number | null` e `ic: [number, number] | null`.

`PainelDrivers` é um client component:

- botão "Medir drivers numa amostra de 50 atendimentos";
- ao clicar, chama `obterDrivers`, mostra estado de carregamento e, ao terminar, renderiza `TabelaDrivers`, exportada para o teste;
- o erro 503 do dublê aparece com a mensagem do servidor.

`TabelaDrivers` mostra uma linha por família com detratores e promotores:

- média com `formatarComSinal` e "[lo; hi]";
- grupo com `n = 0` mostra "sem detratores na amostra" (ou "promotores");
- grupo com `ic === null` e `n = 1` mostra "n = 1, sem intervalo".

No cabeçalho:

- "amostra de {amostra} de {elegiveis} elegíveis · {sem_sinal} sem sinal · {defasadas} de outra régua (repontuar para incluir)";
- o `rotulo`;
- o `metodo` em texto pequeno.

- [ ] **Passo 4: rodar e ver passar.** `cd dashboard && npx vitest run components/PainelDrivers.test.tsx && npx tsc --noEmit` deve dar PASS.
- [ ] **Passo 5: conferência visual (controlador)** em 390 px e desktop, como na Tarefa 7.
- [ ] **Passo 6: stage.** `git add dashboard/lib/api.ts dashboard/components/PainelDrivers.tsx dashboard/components/PainelDrivers.test.tsx dashboard/app/dashboard/page.tsx`

---

### Tarefa 9: documentação, verificação e commit único

**Arquivos:**

- Modificar: `docs/superpowers/specs/2026-10-14-e1-por-que-esta-nota-design.md` (seção "Desvios aceitos", copiada do topo deste plano).
- Modificar: `docs/limitacoes.md` (parágrafo novo, "A explicação é do modelo, não do cliente").
- Modificar: `docs/arquitetura.md` (as duas rotas e o campo `explicacao`).
- Modificar: `README.md` (rotas novas na lista de endpoints).

- [ ] **Passo 1:** escrever os parágrafos. Eles dizem que o efeito por família não soma a nota, que contribuição é associação, que faixa quer dizer `|z| ≤ 4` e que o tempo é sintético.
- [ ] **Passo 2: verificação completa, com a saída colada no relatório.**

```bash
uv run pytest -q
cd dashboard && npm test && npx tsc --noEmit && npm run build && cd ..
uv run python -c "
import json; from pathlib import Path; from fraus.db import Banco; from fraus.api.main import criar_app
novo=criar_app(Banco(Path('/tmp/claude-1000/-home-joaopedro-GITHUB-Fraus/1b6c4a0a-22af-4d3b-bfc7-03364b4bed6a/scratchpad/o.db')), motor=None).openapi()['paths']
velho=json.load(open('/tmp/claude-1000/-home-joaopedro-GITHUB-Fraus/1b6c4a0a-22af-4d3b-bfc7-03364b4bed6a/scratchpad/baseline/openapi.json'))['paths']
print('sumiram:', sorted(set(velho)-set(novo))); print('novas:', sorted(set(novo)-set(velho)))"
git diff --stat origin/main -- modelos/ requirements.txt
git diff origin/main -- fraus/fusor.py | grep -E '^[-+].*(NOMES_FEATURES =|PESO_NEUTRO_NO_SCORE =|FEATURES_EM_LOG =)' || echo "constantes intactas"
```

Esperado:

- testes verdes;
- `sumiram: []` e `novas: ['/conversas/{conversa_id}/contrafactual', '/indicadores/drivers']` (o nome exato do caminho vem do FastAPI);
- `modelos/` e `requirements.txt` sem diff;
- "constantes intactas".

- [ ] **Passo 3: com os pesos (quando chegarem): `scripts/medir_aditividade.py`.** É um instrumento no molde de `scripts/medir_faixas.py`: copia o bootstrap de `sys.path` e o carregamento do motor real que aquele script usa, e não grava nada.

  1. Gerar 90 conversas com `gerar_lote` de `fraus/ingest/simulador.py:305` (semente 20261014; conferir a assinatura real antes).
  2. Para cada conversa com sinal, montar as features com o motor real e medir `max |decompor(f)["score"] − pontuar(f)|` e `max |logit − log(p_c/p_ref)|`.
  3. Medir o tempo médio de `atribuir_conversa` com a explicação.
  4. Imprimir os três números.

  Rodar: `FRAUS_BACKEND=onnx uv run python scripts/medir_aditividade.py`.

  Esperado: erros abaixo de 1e-9. Os números entram no relatório com a condição "fusor de 15/09/2026, 90 conversas do simulador, CPU desta máquina".

- [ ] **Passo 4: `/review` do diff da entrega** e correção do que sair.
- [ ] **Passo 5: commit único da entrega**

```bash
git add -A fraus tests dashboard docs README.md scripts/medir_aditividade.py
git commit -F - <<'EOF'
feat(explicacao): por que esta nota, contrafactual de espera e drivers

Decomposicao exata do fusor (intercepto + contribuicoes = log da razao,
score refeito dos logits), efeito por familia em pontos de score, frases
por template; POST /conversas/{id}/contrafactual recusa |z| > 4;
GET /indicadores/drivers com amostra por semente e IC por bootstrap.
Nada e gravado; score, nota e categoria intactos.

Medicao: <erro maximo de aditividade e tempo, com a condicao>.

Co-Authored-By: Neuro <neuro.chan.dev@gmail.com>
EOF
```
