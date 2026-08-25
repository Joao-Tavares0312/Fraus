# O léxico curado — plano de implementação

> **Para trabalhadores agênticos:** SUB-SKILL OBRIGATÓRIA: use
> `superpowers:subagent-driven-development` (recomendado) ou
> `superpowers:executing-plans` para implementar tarefa por tarefa. Os passos
> usam `- [ ]` para acompanhamento.

**Objetivo:** o analista cadastra palavras e emojis que o treino não pegou, com
peso, e eles passam a alimentar o sinal léxico — sem que ninguém edite o score.

**Arquitetura:** um objeto `Curadoria` carregado do banco **a cada requisição**
atravessa por parâmetro até os dois pontos de consulta que já existem
(`lexico._polaridade` e `emoji.score_do_emoji`), vencendo o léxico base. Nada de
estado global mutável. Uma versão de léxico marca cada conversa pontuada, e a
tela nomeia a divergência em vez de escondê-la.

**Stack:** Python 3.11 · FastAPI · SQLite sem ORM · pytest · Next.js 16 no front.

## Restrições globais

- **Identificadores e docstrings em português, sem acento nos nomes de símbolo.**
  Texto de interface leva acento normal.
- **Commits em português, sem acento, no formato `tipo(escopo): resumo`.**
- **TDD:** teste que falha primeiro, implementação mínima, teste verde, commit.
- **Invariante 3:** score, nota e categoria são derivados no SERVIDOR e nunca
  aceitos do corpo da requisição. O modelo de entrada aceita **só** `tipo`,
  `termo`, `peso` e `motivo`.
- **Invariante 4 (padrão de estado):** a curadoria passa **por parâmetro**,
  nunca por estado global mutável, e é lida a cada requisição.
- **Invariante 9:** as 35 chaves de feature continuam batendo com
  `NOMES_FEATURES`. Nenhuma tarefa acrescenta ou remove feature.
- **Escala:** palavra é inteiro **−1 / 0 / +1**; emoji é float em **[−1, 1]**.
  Nenhuma tarefa mistura as duas.
- **Sem curadoria (`None`), o comportamento é byte a byte o de hoje.** Toda
  assinatura ganha `curadoria=None` **ao fim**, nunca no meio.
- `uv run pytest -q` roda a suíte. `uv sync --extra dev` se o pytest sumir.

---

### Task 1: O objeto `Curadoria`

**Arquivos:**
- Criar: `fraus/sinais/curadoria.py`
- Criar: `tests/test_curadoria.py`

**Interfaces:**
- Consome: nada.
- Produz: `Curadoria` (dataclass congelada), `CURADORIA_VAZIA`,
  `Curadoria.polaridade_de(termo: str) -> int | None`,
  `Curadoria.score_de(caractere: str) -> float | None`,
  `Curadoria.total_de_palavras() -> int`, `Curadoria.total_de_emojis() -> int`.
  As tarefas 2, 3, 6 e 8 consomem.

- [ ] **Passo 1: escrever o teste que falha**

Criar `tests/test_curadoria.py`:

```python
"""A curadoria e um DICIONARIO BURRO, e e de proposito.

Ela nao normaliza, nao valida escala e nao sabe o que e acento. Quem normaliza e
quem escreve (a rota) e quem consulta (o lexico, que ja calcula `sem_acento`
para o proprio indice de reserva). Ensinar normalizacao a este objeto criaria
uma segunda regra de normalizacao no projeto, e duas regras divergem.
"""

from fraus.sinais.curadoria import CURADORIA_VAZIA, Curadoria


def test_vazia_nao_conhece_nada():
    assert CURADORIA_VAZIA.polaridade_de("lentissimo") is None
    assert CURADORIA_VAZIA.score_de("🙄") is None
    assert CURADORIA_VAZIA.versao == 0


def test_palavra_curada_responde_a_polaridade():
    c = Curadoria(palavras={"lentissimo": -1}, emojis={}, versao=3)
    assert c.polaridade_de("lentissimo") == -1
    assert c.versao == 3


def test_termo_nao_curado_devolve_None_e_nao_zero():
    # None e "nao curado" -- o lexico base decide. Zero seria "curado como
    # neutro", que e uma afirmacao diferente e silencia o termo.
    c = Curadoria(palavras={"lentissimo": -1}, emojis={}, versao=1)
    assert c.polaridade_de("otimo") is None


def test_palavra_curada_como_zero_e_diferente_de_ausente():
    c = Curadoria(palavras={"cobranca": 0}, emojis={}, versao=1)
    assert c.polaridade_de("cobranca") == 0


def test_emoji_curado_responde_ao_score():
    c = Curadoria(palavras={}, emojis={"🙄": -0.62}, versao=1)
    assert c.score_de("🙄") == -0.62
    assert c.score_de("🎉") is None


def test_contagens_para_a_ficha_do_modelo():
    c = Curadoria(palavras={"a": 1, "b": -1}, emojis={"🙄": -0.5}, versao=7)
    assert c.total_de_palavras() == 2
    assert c.total_de_emojis() == 1


def test_e_imutavel():
    import dataclasses
    import pytest

    c = Curadoria(palavras={}, emojis={}, versao=0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.versao = 9
```

- [ ] **Passo 2: rodar e ver falhar**

Executar: `uv run pytest tests/test_curadoria.py -q`
Esperado: FALHA — `ModuleNotFoundError: No module named 'fraus.sinais.curadoria'`.

- [ ] **Passo 3: a implementação mínima**

Criar `fraus/sinais/curadoria.py`:

```python
"""O que o analista ensinou ao lexico, e que o treino nao pegou.

O SentiLex-PT02 tem 79.189 formas e nao tem `lentissimo`. O Emoji Sentiment
Ranking tem 751 emojis anotados em 2015. Nem um nem outro conhece o jargao da
empresa que opera o atendimento. Este objeto e o que o analista acrescentou.

A CURADORIA VENCE O LEXICO BASE, e isso a faz servir aos dois casos: preencher
buraco (o termo nao existe) e corrigir polaridade errada para o dominio.

O QUE ELA NAO FAZ: corrigir score. Ela alimenta o sinal lexico, e quem pontua
continua sendo o fusor treinado -- o analista conserta o dicionario, nao a nota.
Um ajuste por cima do numero do modelo criaria uma SEGUNDA REGUA, que e a dor
que o README ja documenta com `PESO_NEUTRO_NO_SCORE`.

E UM DICIONARIO BURRO, DE PROPOSITO: nao normaliza, nao valida escala e nao sabe
o que e acento. Quem normaliza e quem escreve (a rota) e quem consulta (o
lexico, que ja calcula `sem_acento` para o proprio indice de reserva). Ensinar
normalizacao aqui criaria uma segunda regra de normalizacao, e duas regras
divergem.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class Curadoria:
    """Os termos curados nesta instalacao, e a versao do conjunto.

    `versao` acompanha o objeto porque ela e gravada na conversa no momento da
    pontuacao: e o que permite a tela dizer depois "41 de 62 atendimentos foram
    pontuados com um lexico anterior" em vez de misturar duas reguas em
    silencio.
    """

    palavras: Mapping[str, int] = field(default_factory=dict)
    emojis: Mapping[str, float] = field(default_factory=dict)
    versao: int = 0

    def polaridade_de(self, termo: str) -> int | None:
        """Polaridade curada, ou `None` se o termo nao foi curado.

        `None` e "nao curado" -- o lexico base decide. ZERO e outra coisa: e
        "curado como neutro", que SILENCIA um termo que o SentiLex anota com
        polaridade errada para atendimento. As duas respostas nao podem colapsar
        numa so.
        """
        return self.palavras.get(termo)

    def score_de(self, caractere: str) -> float | None:
        """Score curado do emoji, ou `None` se nao foi curado."""
        return self.emojis.get(caractere)

    def total_de_palavras(self) -> int:
        return len(self.palavras)

    def total_de_emojis(self) -> int:
        return len(self.emojis)


# O padrao de todo chamador que nao tem curadoria: um objeto real e vazio, nunca
# `None` espalhado por dentro dos sinais. `None` continua sendo o valor do
# PARAMETRO das assinaturas publicas -- quem converte um no outro e o proprio
# sinal, num lugar so.
CURADORIA_VAZIA = Curadoria(
    palavras=MappingProxyType({}), emojis=MappingProxyType({}), versao=0
)
```

- [ ] **Passo 4: rodar e ver passar**

Executar: `uv run pytest tests/test_curadoria.py -q`
Esperado: PASSA — 7 testes.

- [ ] **Passo 5: commit**

```bash
git add fraus/sinais/curadoria.py tests/test_curadoria.py
git commit -m "feat(lexico): o objeto que guarda o que o analista ensinou"
```

---

### Task 2: A curadoria vence o léxico de palavras

**Arquivos:**
- Modificar: `fraus/sinais/lexico.py` (`_polaridade`, `polaridade_do_termo`,
  `anotar_texto`, `features_lexico`)
- Modificar: `tests/test_sinal_lexico.py`

**Interfaces:**
- Consome: `Curadoria`, `CURADORIA_VAZIA` da Task 1.
- Produz: `polaridade_do_termo(termo, curadoria=None)`,
  `anotar_texto(texto, curadoria=None)`,
  `features_lexico(conversa, curadoria=None)`. A Task 4 consome a terceira.

- [ ] **Passo 1: escrever os testes que falham**

Acrescentar ao fim de `tests/test_sinal_lexico.py`:

```python
from fraus.sinais.curadoria import Curadoria


def test_curadoria_preenche_buraco_do_lexicon():
    """Termo ausente do SentiLex passa a valer o que o analista disse."""
    assert polaridade_do_termo("lentissimo") == 0  # hoje: desconhecido vale 0
    c = Curadoria(palavras={"lentissimo": -1})
    assert polaridade_do_termo("lentissimo", c) == -1


def test_curadoria_VENCE_o_lexicon_base():
    """Nao e so preencher buraco: e corrigir polaridade errada de dominio."""
    assert polaridade_do_termo("otimo") == 1
    c = Curadoria(palavras={"otimo": -1})
    assert polaridade_do_termo("otimo", c) == -1


def test_curado_como_zero_SILENCIA_o_termo():
    assert polaridade_do_termo("otimo") == 1
    c = Curadoria(palavras={"otimo": 0})
    assert polaridade_do_termo("otimo", c) == 0


def test_curadoria_alcanca_o_termo_sem_acento():
    """O cliente de chat nem sempre acentua, e o lexico ja trata isso com um
    indice de reserva. A curadoria entra na MESMA busca, senao a palavra curada
    com acento sumiria quando digitada sem."""
    c = Curadoria(palavras={"lentíssimo": -1})
    assert polaridade_do_termo("lentissimo", c) == -1


def test_negacao_continua_valendo_sobre_termo_curado():
    c = Curadoria(palavras={"lentissimo": -1})
    achados = anotar_texto("nao ficou lentissimo", c)
    assert ("lentissimo", 1, True) in achados


def test_ngrama_curado_vence_o_token_solto():
    """A curadoria entra no mesmo ponto da busca de n-gramas, entao um termo
    curado de duas palavras vence o token que o compoe -- igual a um idioma do
    SentiLex."""
    c = Curadoria(palavras={"fora do ar": -1, "ar": 1})
    achados = anotar_texto("o sistema ficou fora do ar", c)
    assert ("fora do ar", -1, False) in achados
    assert all(termo != "ar" for termo, _, _ in achados)


def test_curadoria_move_as_features(conversa_do_cliente):
    c = Curadoria(palavras={"lentissimo": -1})
    sem = features_lexico(conversa_do_cliente("o app ta lentissimo"))
    com = features_lexico(conversa_do_cliente("o app ta lentissimo"), c)
    assert sem["lexico_cobertura"] == 0.0
    assert com["lexico_cobertura"] > 0.0
    assert com["lexico_polaridade_media"] == -1.0


def test_sem_curadoria_o_comportamento_e_o_de_antes(conversa_do_cliente):
    """A garantia de que esta mudanca nao mexeu no que ja funcionava."""
    conversa = conversa_do_cliente("o atendimento foi otimo")
    assert features_lexico(conversa) == features_lexico(conversa, None)
```

Se `tests/test_sinal_lexico.py` ainda não tiver a fábrica `conversa_do_cliente`,
acrescentar no topo do arquivo:

```python
import pytest
from datetime import datetime, timezone

from fraus.modelos import Conversa, Mensagem


@pytest.fixture
def conversa_do_cliente():
    def montar(*textos: str) -> Conversa:
        quando = datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc)
        return Conversa(
            id="c1",
            canal="csv",
            iniciada_em=quando,
            mensagens=[
                Mensagem(autor="cliente", texto=t, enviada_em=quando)
                for t in textos
            ],
        )

    return montar
```

- [ ] **Passo 2: rodar e ver falhar**

Executar: `uv run pytest tests/test_sinal_lexico.py -q`
Esperado: FALHA — `polaridade_do_termo() takes 1 positional argument but 2 were given`.

- [ ] **Passo 3: a implementação**

Em `fraus/sinais/lexico.py`, acrescentar ao topo:

```python
from fraus.sinais.curadoria import CURADORIA_VAZIA, Curadoria
```

Substituir `_polaridade`, `polaridade_do_termo`, `anotar_texto` e
`features_lexico`:

```python
def _polaridade(termo: str, curadoria: Curadoria = CURADORIA_VAZIA) -> int | None:
    """Busca a polaridade. A CURADORIA VEM PRIMEIRO; sem acento como reserva.

    A ordem e o inteiro da regra: o que o analista curou vence as 79.189 formas
    do SentiLex, senao a feature so serviria para preencher buraco e nao para
    corrigir polaridade errada de dominio.

    A curadoria e consultada DUAS vezes -- com o termo cru e sem acento -- pelo
    mesmo motivo que o lexicon base tem indice de reserva: o cliente de chat nem
    sempre acentua, e uma palavra curada com acento sumiria quando digitada sem.
    Quem sabe normalizar e este modulo; a curadoria e um dicionario burro.
    """
    curado = curadoria.polaridade_de(termo)
    if curado is not None:
        return curado
    curado = curadoria.polaridade_de(sem_acento(termo))
    if curado is not None:
        return curado

    exato = _lexicon().get(termo)
    if exato is not None:
        return exato
    return _lexicon_sem_acento().get(sem_acento(termo))


def polaridade_do_termo(termo: str, curadoria: Curadoria | None = None) -> int:
    """Polaridade em -1/0/1. Termo fora do lexicon e nao curado vale 0."""
    resultado = _polaridade(termo.lower(), curadoria or CURADORIA_VAZIA)
    return 0 if resultado is None else resultado
```

Em `anotar_texto`, trocar a assinatura e as duas chamadas a `_polaridade`:

```python
def anotar_texto(
    texto: str, curadoria: Curadoria | None = None
) -> list[tuple[str, int, bool]]:
```

e, dentro do laço de n-gramas:

```python
                polaridade = _polaridade(termo, curadoria or CURADORIA_VAZIA)
```

Em `features_lexico`, trocar a assinatura e a montagem dos achados:

```python
def features_lexico(
    conversa: Conversa, curadoria: Curadoria | None = None
) -> dict[str, float]:
```

```python
    achados = [a for texto in textos for a in anotar_texto(texto, curadoria)]
```

- [ ] **Passo 4: rodar e ver passar**

Executar: `uv run pytest tests/test_sinal_lexico.py -q`
Esperado: PASSA.

- [ ] **Passo 5: a suíte inteira, para provar que nada regrediu**

Executar: `uv run pytest -q`
Esperado: PASSA. Se algum teste antigo quebrar, a assinatura entrou no meio em
vez de ao fim — o parâmetro novo é sempre o último.

- [ ] **Passo 6: commit**

```bash
git add fraus/sinais/lexico.py tests/test_sinal_lexico.py
git commit -m "feat(lexico): a curadoria vence as 79 mil formas do sentilex"
```

---

### Task 3: A curadoria vence o léxico de emoji

**Arquivos:**
- Modificar: `fraus/sinais/emoji.py` (`score_do_emoji`, `features_emoji`)
- Modificar: `tests/test_sinal_emoji.py`

**Interfaces:**
- Consome: `Curadoria`, `CURADORIA_VAZIA` da Task 1.
- Produz: `score_do_emoji(caractere, curadoria=None)`,
  `features_emoji(conversa, curadoria=None)`. A Task 4 consome a segunda.

- [ ] **Passo 1: escrever os testes que falham**

Acrescentar ao fim de `tests/test_sinal_emoji.py`:

```python
from fraus.sinais.curadoria import Curadoria


def test_emoji_curado_vence_o_ranking():
    assert score_do_emoji("😀") > 0
    c = Curadoria(emojis={"😀": -0.9})
    assert score_do_emoji("😀", c) == -0.9


def test_emoji_fora_do_ranking_e_nao_curado_continua_zero():
    assert score_do_emoji("🫠") == 0.0
    assert score_do_emoji("🫠", Curadoria()) == 0.0


def test_emoji_curado_preenche_o_que_o_ranking_de_2015_nao_tem():
    c = Curadoria(emojis={"🫠": -0.7})
    assert score_do_emoji("🫠", c) == -0.7


def test_curadoria_de_emoji_move_as_features(conversa_com_emoji):
    c = Curadoria(emojis={"🫠": -0.8})
    sem = features_emoji(conversa_com_emoji("acabou assim 🫠"))
    com = features_emoji(conversa_com_emoji("acabou assim 🫠"), c)
    assert sem["emoji_score_medio"] == 0.0
    assert com["emoji_score_medio"] == -0.8
    assert com["emoji_frac_negativos"] == 1.0


def test_sem_curadoria_o_comportamento_e_o_de_antes(conversa_com_emoji):
    conversa = conversa_com_emoji("tudo certo 😀")
    assert features_emoji(conversa) == features_emoji(conversa, None)
```

Se `tests/test_sinal_emoji.py` ainda não tiver a fábrica `conversa_com_emoji`,
acrescentar no topo do arquivo:

```python
import pytest
from datetime import datetime, timezone

from fraus.modelos import Conversa, Mensagem


@pytest.fixture
def conversa_com_emoji():
    def montar(*textos: str) -> Conversa:
        quando = datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc)
        return Conversa(
            id="c1",
            canal="csv",
            iniciada_em=quando,
            mensagens=[
                Mensagem(autor="cliente", texto=t, enviada_em=quando)
                for t in textos
            ],
        )

    return montar
```

- [ ] **Passo 2: rodar e ver falhar**

Executar: `uv run pytest tests/test_sinal_emoji.py -q`
Esperado: FALHA — `score_do_emoji() takes 1 positional argument but 2 were given`.

- [ ] **Passo 3: a implementação**

Em `fraus/sinais/emoji.py`, acrescentar ao topo:

```python
from fraus.sinais.curadoria import CURADORIA_VAZIA, Curadoria
```

Substituir `score_do_emoji` e a assinatura de `features_emoji`:

```python
def score_do_emoji(caractere: str, curadoria: Curadoria | None = None) -> float:
    """Polaridade em [-1, 1]. Emoji fora do lexicon e nao curado vale 0.

    A CURADORIA VEM PRIMEIRO. O Emoji Sentiment Ranking anotou 751 emojis em
    2015: tudo que o Unicode acrescentou depois vale 0 aqui, e e exatamente esse
    buraco que o analista preenche.
    """
    curado = (curadoria or CURADORIA_VAZIA).score_de(caractere)
    if curado is not None:
        return curado
    return _lexicon().get(caractere, 0.0)


def features_emoji(
    conversa: Conversa, curadoria: Curadoria | None = None
) -> dict[str, float]:
```

E, dentro de `features_emoji`, a linha dos scores:

```python
    scores = [score_do_emoji(caractere, curadoria) for caractere, _ in pares]
```

- [ ] **Passo 4: rodar e ver passar**

Executar: `uv run pytest tests/test_sinal_emoji.py -q`
Esperado: PASSA.

- [ ] **Passo 5: a suíte inteira**

Executar: `uv run pytest -q`
Esperado: PASSA.

- [ ] **Passo 6: commit**

```bash
git add fraus/sinais/emoji.py tests/test_sinal_emoji.py
git commit -m "feat(emoji): a curadoria preenche o que o ranking de 2015 nao tem"
```

---

### Task 4: A curadoria atravessa até o score

**Arquivos:**
- Modificar: `fraus/fusor.py` (`montar_features`)
- Modificar: `fraus/motor.py` (`pontuar_conversa`, `atribuir_conversa`)
- Modificar: `tests/test_fusor.py`

**Interfaces:**
- Consome: `features_lexico(conversa, curadoria)` da Task 2,
  `features_emoji(conversa, curadoria)` da Task 3.
- Produz: `montar_features(conversa, classificador, emocao, ironia, curadoria=None)`
  e `Motor.pontuar_conversa(conversa, curadoria=None)`. A Task 6 consome a
  segunda.

- [ ] **Passo 1: escrever o teste que falha**

Acrescentar ao fim de `tests/test_fusor.py`:

```python
from fraus.sinais.curadoria import Curadoria


def test_curadoria_atravessa_montar_features(classificador_duble, emocao_duble, ironia_duble, conversa_de_teste):
    """O elo que faltava: sem passar aqui, curar palavra nao moveria o score.

    As 35 chaves continuam as mesmas (invariante 9) -- o que muda e o VALOR de
    `lexico_polaridade_media`, nao o conjunto de features.
    """
    c = Curadoria(palavras={"lentissimo": -1})
    sem = montar_features(conversa_de_teste, classificador_duble, emocao_duble, ironia_duble)
    com = montar_features(conversa_de_teste, classificador_duble, emocao_duble, ironia_duble, c)

    assert set(sem) == set(com) == set(NOMES_FEATURES)
    assert sem["lexico_polaridade_media"] != com["lexico_polaridade_media"]
```

O `conversa_de_teste` desta fixture precisa conter a palavra `lentissimo` numa
fala de cliente. Se as fixtures do arquivo não servirem, montar a conversa
dentro do próprio teste com `Conversa`/`Mensagem`, como nas tarefas 2 e 3.

- [ ] **Passo 2: rodar e ver falhar**

Executar: `uv run pytest tests/test_fusor.py -q`
Esperado: FALHA — `montar_features() takes 4 positional arguments but 5 were given`.

- [ ] **Passo 3: a implementação**

Em `fraus/fusor.py`, na assinatura de `montar_features`, acrescentar o parâmetro
ao fim e repassá-lo às duas famílias que o consomem:

```python
def montar_features(conversa, classificador, emocao, ironia, curadoria=None) -> dict:
```

```python
        **features_emoji(conversa, curadoria),
```

```python
        **features_lexico(conversa, curadoria),
```

Em `fraus/motor.py`:

```python
    def pontuar_conversa(self, conversa, curadoria=None) -> float | None:
        """Score 0-100, ou `None` sem fala do cliente.

        `curadoria` chega POR PARAMETRO e o Motor nao a guarda: ele e construido
        uma vez no boot, e um atributo aqui envelheceria a cada palavra
        cadastrada -- o mesmo defeito que o `lru_cache` dos lexicons teria. Quem
        a carrega e o `Contexto`, a cada requisicao.
        """
        if not conversa.tem_sinal_cliente:
            return None  # ausencia de dado nao e insatisfacao
        return self._fusor.pontuar(
            montar_features(
                conversa, self._classificador, self._emocao, self._ironia, curadoria
            )
        )
```

Em `atribuir_conversa`, a montagem das contribuições e a assinatura:

```python
    def atribuir_conversa(self, conversa, curadoria=None) -> dict:
```

```python
        contribuicoes = None
        if conversa.tem_sinal_cliente:
            features = montar_features(
                conversa, self._classificador, self._emocao, self._ironia, curadoria
            )
            contribuicoes = self._fusor.contribuicoes(features)
```

E em `analisar_conversa`, para a análise refletir o mesmo léxico que pontuou:

```python
    def analisar_conversa(self, conversa, referencia=None, curadoria=None) -> dict:
```

```python
        atribuicao = self.atribuir_conversa(conversa, curadoria)
```

```python
        score = self.pontuar_conversa(conversa, curadoria)
```

- [ ] **Passo 4: rodar e ver passar**

Executar: `uv run pytest -q`
Esperado: PASSA — a suíte inteira.

- [ ] **Passo 5: commit**

```bash
git add fraus/fusor.py fraus/motor.py tests/test_fusor.py
git commit -m "feat(fusor): a curadoria atravessa ate o score, por parametro"
```

---

### Task 5: O banco — a tabela, a versão e a coluna

**Arquivos:**
- Modificar: `fraus/db.py` (`ESQUEMA`, `COLUNAS_ACRESCENTADAS`, `salvar`, métodos novos)
- Criar: `tests/test_db_lexico_curado.py`

**Interfaces:**
- Consome: nada.
- Produz, em `Banco`: `curar(tipo, termo, peso, motivo) -> dict`,
  `listar_curados() -> list[dict]`, `revogar_curado(id) -> bool`,
  `lexico_versao() -> int`, `carregar_curadoria() -> Curadoria`,
  `contar_defasadas() -> tuple[int, int]`. E `salvar(...)` ganha o parâmetro
  `lexico_versao`. A Task 6 consome todos.

- [ ] **Passo 1: escrever os testes que falham**

Criar `tests/test_db_lexico_curado.py`:

```python
"""O lexico curado no banco, e a VERSAO que impede a regua misturada."""

import pytest

from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem
from datetime import datetime, timezone


@pytest.fixture
def banco(tmp_path):
    b = Banco(tmp_path / "t.db")
    b.migrar()
    return b


def _conversa(id_):
    quando = datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc)
    return Conversa(
        id=id_, canal="csv", iniciada_em=quando,
        mensagens=[Mensagem(autor="cliente", texto="oi", enviada_em=quando)],
    )


def test_banco_novo_comeca_na_versao_zero(banco):
    assert banco.lexico_versao() == 0
    assert banco.listar_curados() == []


def test_curar_incrementa_a_versao(banco):
    banco.curar("palavra", "lentissimo", -1, "gente reclama de lentidao")
    assert banco.lexico_versao() == 1
    banco.curar("emoji", "🙄", -0.62, None)
    assert banco.lexico_versao() == 2


def test_curar_o_mesmo_termo_EDITA_em_vez_de_duplicar(banco):
    banco.curar("palavra", "lentissimo", -1, None)
    banco.curar("palavra", "lentissimo", 0, "na verdade e neutro aqui")
    curados = banco.listar_curados()
    assert len(curados) == 1
    assert curados[0]["peso"] == 0
    assert curados[0]["motivo"] == "na verdade e neutro aqui"


def test_o_mesmo_termo_em_tipos_DIFERENTES_coexiste(banco):
    banco.curar("palavra", "x", 1, None)
    banco.curar("emoji", "x", 1.0, None)
    assert len(banco.listar_curados()) == 2


def test_revogar_apaga_e_incrementa_a_versao(banco):
    registro = banco.curar("palavra", "lentissimo", -1, None)
    assert banco.revogar_curado(registro["id"]) is True
    assert banco.listar_curados() == []
    assert banco.lexico_versao() == 2  # curar=1, revogar=2


def test_revogar_o_que_nao_existe_devolve_False_e_nao_mexe_na_versao(banco):
    banco.curar("palavra", "a", 1, None)
    assert banco.revogar_curado(999) is False
    assert banco.lexico_versao() == 1


def test_carregar_curadoria_separa_palavra_de_emoji(banco):
    banco.curar("palavra", "lentissimo", -1, None)
    banco.curar("emoji", "🙄", -0.62, None)
    c = banco.carregar_curadoria()
    assert c.polaridade_de("lentissimo") == -1
    assert c.score_de("🙄") == -0.62
    assert c.versao == 2


def test_a_conversa_grava_a_versao_que_a_pontuou(banco):
    banco.curar("palavra", "lentissimo", -1, None)
    banco.salvar(_conversa("c1"), 70.0, "neutro", lexico_versao=1)
    defasadas, total = banco.contar_defasadas()
    assert (defasadas, total) == (0, 1)


def test_conversa_pontuada_antes_da_mudanca_conta_como_defasada(banco):
    banco.salvar(_conversa("c1"), 70.0, "neutro", lexico_versao=0)
    banco.curar("palavra", "lentissimo", -1, None)  # versao vira 1
    assert banco.contar_defasadas() == (1, 1)


def test_conversa_de_banco_antigo_com_versao_NULA_conta_como_defasada(banco):
    """Coluna acrescentada depois: linha antiga fica NULL e e anterior ao
    mecanismo -- que e defasada, nao 'em dia'."""
    banco.salvar(_conversa("c1"), 70.0, "neutro")  # sem passar a versao
    banco.curar("palavra", "x", -1, None)
    assert banco.contar_defasadas() == (1, 1)
```

- [ ] **Passo 2: rodar e ver falhar**

Executar: `uv run pytest tests/test_db_lexico_curado.py -q`
Esperado: FALHA — `AttributeError: 'Banco' object has no attribute 'lexico_versao'`.

- [ ] **Passo 3: a implementação**

Em `fraus/db.py`, acrescentar ao `ESQUEMA`:

```sql
-- O que o analista ensinou ao lexico: termos que o SentiLex-PT02 e o Emoji
-- Sentiment Ranking nao trazem, ou trazem com polaridade errada para o dominio
-- de atendimento. Ver fraus/sinais/curadoria.py.
--
-- O INDICE UNICO e o que faz recadastrar o mesmo termo ser EDICAO em vez de
-- duplicata silenciosa com uma das duas vencendo por ordem de leitura.
--
-- `motivo` e opcional e existe para a decisao sobreviver a quem a tomou: um
-- peso sem porque, seis meses depois, e indistinguivel de erro de digitacao.
CREATE TABLE IF NOT EXISTS lexico_curado (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    termo TEXT NOT NULL,
    peso REAL NOT NULL,
    motivo TEXT,
    criado_em TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_lexico_curado_termo
    ON lexico_curado(tipo, termo);
```

Acrescentar a `COLUNAS_ACRESCENTADAS`:

```python
        ("conversas", "lexico_versao", "INTEGER"),
```

Acrescentar os imports no topo do arquivo:

```python
from datetime import datetime, timezone

from fraus.sinais.curadoria import Curadoria
```

Trocar a assinatura de `salvar` e o `INSERT` (acrescentando a coluna ao fim, na
mesma ordem dos parâmetros):

```python
    def salvar(
        self,
        conversa: Conversa,
        score: float | None,
        categoria: str | None,
        lexico_versao: int | None = None,
    ) -> None:
```

```python
                "INSERT OR REPLACE INTO conversas "
                "(id, canal, iniciada_em, score, categoria, payload, lexico_versao) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
```

E acrescentar `lexico_versao` ao fim da tupla de valores.

Acrescentar os métodos:

```python
    # ---- lexico curado --------------------------------------------------

    # A versao mora na tabela de configuracoes, e nao numa tabela propria: ela e
    # UM inteiro, e a tabela chave/valor existe exatamente para isso. Comeca em
    # 0 e sobe a cada ESCRITA -- curar e revogar contam igual, porque as duas
    # mudam o que o lexico responde.
    CHAVE_VERSAO = "lexico_versao"

    def lexico_versao(self) -> int:
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT valor FROM configuracoes WHERE chave = ?", (self.CHAVE_VERSAO,)
            ).fetchone()
        return int(json.loads(linha["valor"])) if linha else 0

    def _incrementar_versao(self, conexao) -> int:
        """Sobe a versao DENTRO da transacao de quem chamou.

        Recebe a conexao em vez de abrir a propria: gravar o termo e subir a
        versao precisam acontecer juntos ou nenhum dos dois. Em transacoes
        separadas, uma falha no meio deixaria termo curado com versao antiga --
        e a tela diria que o banco esta em dia quando nao esta.
        """
        linha = conexao.execute(
            "SELECT valor FROM configuracoes WHERE chave = ?", (self.CHAVE_VERSAO,)
        ).fetchone()
        proxima = (int(json.loads(linha["valor"])) if linha else 0) + 1
        conexao.execute(
            "INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)",
            (self.CHAVE_VERSAO, json.dumps(proxima)),
        )
        return proxima

    def curar(
        self, tipo: str, termo: str, peso: float, motivo: str | None
    ) -> dict:
        """Cadastra ou EDITA um termo curado. Devolve o registro gravado."""
        agora = datetime.now(timezone.utc).isoformat()
        with self._conectar() as conexao:
            conexao.execute(
                "INSERT INTO lexico_curado (tipo, termo, peso, motivo, criado_em) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(tipo, termo) DO UPDATE SET "
                "peso = excluded.peso, motivo = excluded.motivo, "
                "criado_em = excluded.criado_em",
                (tipo, termo, peso, motivo, agora),
            )
            self._incrementar_versao(conexao)
            linha = conexao.execute(
                "SELECT * FROM lexico_curado WHERE tipo = ? AND termo = ?",
                (tipo, termo),
            ).fetchone()
        return dict(linha)

    def listar_curados(self) -> list[dict]:
        with self._conectar() as conexao:
            linhas = conexao.execute(
                "SELECT * FROM lexico_curado ORDER BY criado_em DESC"
            ).fetchall()
        return [dict(linha) for linha in linhas]

    def revogar_curado(self, curado_id: int) -> bool:
        """`False` quando nao havia o que revogar -- e ai a versao NAO sobe.

        Subir a versao numa revogacao que nao aconteceu marcaria o banco inteiro
        como defasado sem nenhuma mudanca de lexico por tras.
        """
        with self._conectar() as conexao:
            cursor = conexao.execute(
                "DELETE FROM lexico_curado WHERE id = ?", (curado_id,)
            )
            if cursor.rowcount == 0:
                return False
            self._incrementar_versao(conexao)
        return True

    def carregar_curadoria(self) -> Curadoria:
        """Monta o objeto que os sinais consomem. Lido a cada requisicao."""
        palavras: dict[str, int] = {}
        emojis: dict[str, float] = {}
        with self._conectar() as conexao:
            for linha in conexao.execute("SELECT tipo, termo, peso FROM lexico_curado"):
                if linha["tipo"] == "palavra":
                    palavras[linha["termo"]] = int(linha["peso"])
                else:
                    emojis[linha["termo"]] = float(linha["peso"])
        return Curadoria(palavras=palavras, emojis=emojis, versao=self.lexico_versao())

    def contar_defasadas(self) -> tuple[int, int]:
        """(pontuadas com lexico anterior, total). Do banco INTEIRO.

        `lexico_versao IS NULL` conta como defasada: e linha de banco anterior a
        este mecanismo, e "nao sei com qual lexico" nao e "em dia".
        """
        vigente = self.lexico_versao()
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT COUNT(*) AS total, "
                "SUM(CASE WHEN lexico_versao IS NULL OR lexico_versao <> ? "
                "THEN 1 ELSE 0 END) AS defasadas "
                "FROM conversas",
                (vigente,),
            ).fetchone()
        return int(linha["defasadas"] or 0), int(linha["total"] or 0)
```

- [ ] **Passo 4: rodar e ver passar**

Executar: `uv run pytest tests/test_db_lexico_curado.py -q`
Esperado: PASSA — 10 testes.

- [ ] **Passo 5: a suíte inteira**

Executar: `uv run pytest -q`
Esperado: PASSA. `salvar` ganhou parâmetro **ao fim com padrão**, então nenhum
chamador antigo quebra.

- [ ] **Passo 6: commit**

```bash
git add fraus/db.py tests/test_db_lexico_curado.py
git commit -m "feat(db): a tabela do lexico curado e a versao que marca a conversa"
```

---

### Task 6: A API — cadastrar, listar, revogar

**Arquivos:**
- Criar: `fraus/api/rotas/lexico.py`
- Modificar: `fraus/api/esquemas.py` (modelo de entrada)
- Modificar: `fraus/api/contexto.py` (`curadoria_vigente`)
- Modificar: `fraus/api/main.py` (registrar o router)
- Modificar: `fraus/api/rotas/conversas.py` e `fraus/api/rotas/ingestao.py`
  (passar a curadoria e gravar a versão)
- Criar: `tests/test_api_lexico.py`

**Interfaces:**
- Consome: `Banco.curar/listar_curados/revogar_curado/carregar_curadoria` da
  Task 5; `Motor.pontuar_conversa(conversa, curadoria)` da Task 4.
- Produz: `Contexto.curadoria_vigente() -> Curadoria`, o router `lexico.router`,
  e o esquema `PedidoCurado`. A Task 7 consome `curadoria_vigente`.

- [ ] **Passo 1: escrever os testes que falham**

Criar `tests/test_api_lexico.py`:

```python
"""As rotas do lexico curado, e a VALIDACAO que sustenta a fronteira.

A fronteira: o analista edita o DICIONARIO, nunca a nota. Por isso o modelo de
entrada nao tem campo que se pareca com score, e a escala de cada lexico e
imposta aqui -- valor fora dela injetaria na media de polaridade um numero que o
fusor nunca viu no treino.
"""

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco


class MotorFalso:
    def pontuar_conversa(self, conversa, curadoria=None):
        return 50.0


def _cliente(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    app = criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path)
    return TestClient(app), banco


def test_lista_vazia_num_banco_novo(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.get("/lexico/curado").json() == []


def test_cadastra_palavra_e_ela_aparece_na_lista(tmp_path):
    cliente, _ = _cliente(tmp_path)
    resposta = cliente.post(
        "/lexico/curado",
        json={"tipo": "palavra", "termo": "lentissimo", "peso": -1,
              "motivo": "reclamacao comum aqui"},
    )
    assert resposta.status_code == 201
    assert resposta.json()["termo"] == "lentissimo"

    lista = cliente.get("/lexico/curado").json()
    assert [(c["tipo"], c["termo"], c["peso"]) for c in lista] == [
        ("palavra", "lentissimo", -1.0)
    ]


def test_palavra_e_normalizada_para_minusculas(tmp_path):
    cliente, _ = _cliente(tmp_path)
    cliente.post("/lexico/curado", json={"tipo": "palavra", "termo": "LentÍssimo", "peso": -1})
    assert cliente.get("/lexico/curado").json()[0]["termo"] == "lentíssimo"


def test_peso_fracionario_em_PALAVRA_e_recusado(tmp_path):
    """A escala da palavra e a do SentiLex: -1/0/+1. Um -0,7 injetaria na media
    de polaridade um valor fora da distribuicao de treino do fusor."""
    cliente, _ = _cliente(tmp_path)
    resposta = cliente.post(
        "/lexico/curado", json={"tipo": "palavra", "termo": "x", "peso": -0.7}
    )
    assert resposta.status_code == 400
    assert "-1" in resposta.json()["detail"]


def test_peso_fracionario_em_EMOJI_e_aceito(tmp_path):
    cliente, _ = _cliente(tmp_path)
    resposta = cliente.post(
        "/lexico/curado", json={"tipo": "emoji", "termo": "🙄", "peso": -0.62}
    )
    assert resposta.status_code == 201


def test_peso_de_emoji_fora_da_faixa_e_recusado(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.post(
        "/lexico/curado", json={"tipo": "emoji", "termo": "🙄", "peso": 1.5}
    ).status_code == 400


def test_termo_de_emoji_com_dois_emojis_e_recusado(tmp_path):
    cliente, _ = _cliente(tmp_path)
    resposta = cliente.post(
        "/lexico/curado", json={"tipo": "emoji", "termo": "🙄🎉", "peso": 0.1}
    )
    assert resposta.status_code == 400


def test_termo_de_emoji_que_nao_e_emoji_e_recusado(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.post(
        "/lexico/curado", json={"tipo": "emoji", "termo": "abc", "peso": 0.1}
    ).status_code == 400


def test_tipo_invalido_e_recusado(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.post(
        "/lexico/curado", json={"tipo": "frase", "termo": "x", "peso": 1}
    ).status_code == 422


def test_o_corpo_NAO_aceita_score_nem_categoria(tmp_path):
    """Invariante 3: veredito nunca entra pelo corpo. Campo extra e ignorado
    por construcao, e o registro gravado nao carrega nada disso."""
    cliente, _ = _cliente(tmp_path)
    resposta = cliente.post(
        "/lexico/curado",
        json={"tipo": "palavra", "termo": "x", "peso": 1,
              "score": 99, "categoria": "promotor"},
    )
    assert resposta.status_code == 201
    assert "score" not in resposta.json()
    assert "categoria" not in resposta.json()


def test_revogar_tira_da_lista(tmp_path):
    cliente, _ = _cliente(tmp_path)
    criado = cliente.post(
        "/lexico/curado", json={"tipo": "palavra", "termo": "x", "peso": 1}
    ).json()
    assert cliente.delete(f"/lexico/curado/{criado['id']}").status_code == 204
    assert cliente.get("/lexico/curado").json() == []


def test_revogar_o_que_nao_existe_da_404(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.delete("/lexico/curado/999").status_code == 404
```

- [ ] **Passo 2: rodar e ver falhar**

Executar: `uv run pytest tests/test_api_lexico.py -q`
Esperado: FALHA — 404 em todas, porque o router não existe.

- [ ] **Passo 3: o esquema de entrada**

Em `fraus/api/esquemas.py`, acrescentar:

```python
class PedidoCurado(BaseModel):
    """Entrada de `POST /lexico/curado`.

    NENHUM campo de veredito -- invariante 3. O analista diz o que a PALAVRA
    vale para o lexico; o score continua saindo do fusor. Campo extra que o
    cliente mande e ignorado pelo pydantic, e e por isso que este modelo e a
    fronteira e nao um dicionario cru.
    """

    tipo: Literal["palavra", "emoji"]
    termo: str = Field(min_length=1, max_length=64)
    peso: float
    motivo: str | None = Field(default=None, max_length=280)
```

Se `Literal` e `Field` ainda não estiverem importados no arquivo, acrescentar
`from typing import Literal` e incluir `Field` no import de `pydantic`.

- [ ] **Passo 4: o contexto**

Em `fraus/api/contexto.py`, acrescentar ao `Contexto`:

```python
    def curadoria_vigente(self) -> Curadoria:
        """O que o analista ensinou ao lexico, lido A CADA requisicao.

        Irma de `faixas_vigentes`, pelo mesmo motivo escrito la: nao existe
        copia do estado envelhecendo em memoria depois de uma escrita. O `Motor`
        e construido uma vez no boot e continua sem saber da curadoria -- quem a
        passa e a rota, no momento de pontuar.
        """
        return self.banco.carregar_curadoria()
```

E o import: `from fraus.sinais.curadoria import Curadoria`.

- [ ] **Passo 5: o router**

Criar `fraus/api/rotas/lexico.py`:

```python
"""/lexico/curado -- o que o analista ensinou ao lexico.

A FRONTEIRA QUE ESTE MODULO SUSTENTA: o analista edita o DICIONARIO, nunca a
nota. O peso curado alimenta o sinal lexico e o fusor treinado decide quanto
isso vale no score -- exatamente como ja faz com as 79.189 formas do SentiLex.

A validacao de escala nao e burocracia. Palavra e -1/0/+1 porque e essa a escala
em que `lexico_polaridade_media` foi treinada; um -0,7 ali injetaria na feature
um valor que o fusor nunca viu, e o efeito no score deixaria de ser previsivel.
Emoji e continuo em [-1, 1] porque e a escala do Emoji Sentiment Ranking.

Nao e privilegio de mestra: curar lexico e trabalho do analista, nao
administracao de credencial. Vale a chave de acesso como o resto da API.
"""

import emoji as lib_emoji
from fastapi import APIRouter, Depends, HTTPException

from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoCurado

router = APIRouter()

PESOS_DE_PALAVRA = (-1, 0, 1)


def _validar(pedido: PedidoCurado) -> tuple[str, float]:
    """Normaliza o termo e impoe a escala do tipo. Devolve (termo, peso)."""
    if pedido.tipo == "palavra":
        if pedido.peso not in PESOS_DE_PALAVRA:
            raise HTTPException(
                status_code=400,
                detail=(
                    "peso de palavra e -1 (negativa), 0 (neutra) ou 1 (positiva)"
                    " -- a mesma escala do SentiLex-PT02"
                ),
            )
        # Minusculas, como o lexicon indexa. Sem isto "Lentissimo" e
        # "lentissimo" virariam duas linhas, e o indice unico nao pegaria.
        return pedido.termo.strip().lower(), float(pedido.peso)

    if not -1 <= pedido.peso <= 1:
        raise HTTPException(
            status_code=400,
            detail="peso de emoji fica entre -1 e 1 -- a escala do Emoji Sentiment Ranking",
        )
    termo = pedido.termo.strip()
    achados = lib_emoji.emoji_list(termo)
    # A mesma biblioteca que o sinal de emoji ja usa, e nunca regex propria:
    # duas nocoes de "o que e um emoji" divergem na primeira sequencia com
    # modificador de tom de pele.
    if len(achados) != 1 or achados[0]["emoji"] != termo:
        raise HTTPException(
            status_code=400, detail="informe exatamente um emoji"
        )
    return termo, float(pedido.peso)


@router.get("/lexico/curado")
def listar(ctx: Contexto = Depends(obter_contexto)) -> list[dict]:
    return ctx.banco.listar_curados()


@router.post("/lexico/curado", status_code=201)
def curar(
    pedido: PedidoCurado, ctx: Contexto = Depends(obter_contexto)
) -> dict:
    """Cadastra ou EDITA um termo. Vale da proxima pontuacao em diante."""
    termo, peso = _validar(pedido)
    return ctx.banco.curar(pedido.tipo, termo, peso, pedido.motivo)


@router.delete("/lexico/curado/{curado_id}", status_code=204)
def revogar(curado_id: int, ctx: Contexto = Depends(obter_contexto)) -> None:
    if not ctx.banco.revogar_curado(curado_id):
        raise HTTPException(status_code=404, detail="termo curado nao encontrado")
```

Em `fraus/api/main.py`, acrescentar `lexico` ao import de `fraus.api.rotas` e
registrar o router junto dos outros:

```python
    app.include_router(lexico.router)
```

- [ ] **Passo 6: as duas rotas que pontuam passam a usar a curadoria**

Em `fraus/api/rotas/conversas.py`, linha 55, e em
`fraus/api/rotas/ingestao.py`, linha 58, o mesmo par de mudanças:

```python
    curadoria = ctx.curadoria_vigente()
    score = ctx.motor.pontuar_conversa(conversa, curadoria)
```

e, na chamada a `ctx.banco.salvar(...)`, acrescentar o argumento ao fim:

```python
    ctx.banco.salvar(conversa, score, categoria, lexico_versao=curadoria.versao)
```

**Uma leitura por pontuação, e não duas:** a mesma `curadoria` que pontuou é a
que grava a versão. Ler de novo abriria janela para a conversa ser pontuada com
um léxico e marcada com a versão de outro — o defeito exato que a versão existe
para impedir.

- [ ] **Passo 7: rodar e ver passar**

Executar: `uv run pytest tests/test_api_lexico.py -q`
Esperado: PASSA — 12 testes.

- [ ] **Passo 8: a suíte inteira**

Executar: `uv run pytest -q`
Esperado: PASSA.

- [ ] **Passo 9: commit**

```bash
git add fraus/api/rotas/lexico.py fraus/api/esquemas.py fraus/api/contexto.py fraus/api/main.py fraus/api/rotas/conversas.py fraus/api/rotas/ingestao.py tests/test_api_lexico.py
git commit -m "feat(api): cadastrar, listar e revogar termo curado"
```

---

### Task 7: Repontuar, e o aviso de régua misturada

**Arquivos:**
- Modificar: `fraus/api/rotas/conversas.py` (rota nova `POST /conversas/repontuar`)
- Modificar: `fraus/api/rotas/indicadores.py` (as duas contagens)
- Criar: `tests/test_api_repontuar.py`

**Interfaces:**
- Consome: `Banco.contar_defasadas()` da Task 5,
  `Contexto.curadoria_vigente()` da Task 6.
- Produz: `POST /conversas/repontuar` → `{"repontuadas": int}`, e os campos
  `pontuadas_com_lexico_antigo` e `total_no_banco` em `GET /indicadores`. A
  Task 8 consome os dois campos.

- [ ] **Passo 1: escrever os testes que falham**

Criar `tests/test_api_repontuar.py`:

```python
"""A regua misturada deixa de ser silenciosa."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem


class MotorFalso:
    def pontuar_conversa(self, conversa, curadoria=None):
        return 50.0


def _cliente(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    app = criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path)
    return TestClient(app), banco


def _conversa(id_):
    quando = datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc)
    return Conversa(
        id=id_, canal="csv", iniciada_em=quando,
        mensagens=[Mensagem(autor="cliente", texto="oi", enviada_em=quando)],
    )


def test_banco_sem_curadoria_nao_tem_nada_defasado(tmp_path):
    cliente, banco = _cliente(tmp_path)
    banco.salvar(_conversa("c1"), 50.0, "neutro", lexico_versao=0)
    corpo = cliente.get("/indicadores").json()
    assert corpo["pontuadas_com_lexico_antigo"] == 0
    assert corpo["total_no_banco"] == 1


def test_curar_deixa_o_que_ja_existia_defasado(tmp_path):
    cliente, banco = _cliente(tmp_path)
    banco.salvar(_conversa("c1"), 50.0, "neutro", lexico_versao=0)
    cliente.post("/lexico/curado", json={"tipo": "palavra", "termo": "x", "peso": -1})
    assert cliente.get("/indicadores").json()["pontuadas_com_lexico_antigo"] == 1


def test_a_contagem_ignora_o_recorte_de_periodo(tmp_path):
    """A regua misturada e propriedade do BANCO, nao da semana que se olha. Um
    aviso que sumisse ao filtrar esconderia o problema de quem estivesse
    justamente investigando um numero estranho."""
    cliente, banco = _cliente(tmp_path)
    banco.salvar(_conversa("c1"), 50.0, "neutro", lexico_versao=0)
    cliente.post("/lexico/curado", json={"tipo": "palavra", "termo": "x", "peso": -1})
    corpo = cliente.get("/indicadores?de=2020-01-01&ate=2020-12-31").json()
    assert corpo["pontuadas_com_lexico_antigo"] == 1
    assert corpo["total_no_banco"] == 1


def test_repontuar_poe_tudo_na_versao_vigente(tmp_path):
    cliente, banco = _cliente(tmp_path)
    banco.salvar(_conversa("c1"), 50.0, "neutro", lexico_versao=0)
    banco.salvar(_conversa("c2"), 50.0, "neutro", lexico_versao=0)
    cliente.post("/lexico/curado", json={"tipo": "palavra", "termo": "x", "peso": -1})

    resposta = cliente.post("/conversas/repontuar")
    assert resposta.status_code == 200
    assert resposta.json()["repontuadas"] == 2
    assert cliente.get("/indicadores").json()["pontuadas_com_lexico_antigo"] == 0


def test_repontuar_com_banco_vazio_nao_quebra(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.post("/conversas/repontuar").json()["repontuadas"] == 0
```

- [ ] **Passo 2: rodar e ver falhar**

Executar: `uv run pytest tests/test_api_repontuar.py -q`
Esperado: FALHA — `KeyError: 'pontuadas_com_lexico_antigo'`.

- [ ] **Passo 3: os campos em `/indicadores`**

Em `fraus/api/rotas/indicadores.py`, dentro do dicionário de resposta,
acrescentar:

```python
        # AS DUAS CONTAGENS SAO DO BANCO INTEIRO, e sao a unica coisa nesta
        # resposta que ignora `de`/`ate`. A regua misturada e propriedade do
        # banco, nao do recorte: um aviso que sumisse ao filtrar o periodo
        # esconderia o problema exatamente de quem estivesse investigando um
        # numero estranho.
        **dict(
            zip(
                ("pontuadas_com_lexico_antigo", "total_no_banco"),
                ctx.banco.contar_defasadas(),
            )
        ),
```

- [ ] **Passo 4: a rota de repontuar**

Em `fraus/api/rotas/conversas.py`, acrescentar:

```python
@router.post("/conversas/repontuar")
def repontuar(ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Repontua o banco inteiro com o lexico vigente.

    O que ela conserta: o `score` e gravado na importacao, entao curar uma
    palavra nao mexe no que ja existe -- e um banco com conversas pontuadas
    antes e depois soma duas reguas no mesmo agregado. Esta rota e o unico jeito
    de zerar essa divergencia sem reimportar.

    LIMITACAO DECLARADA: repontuar roda os TRES BERTimbau de novo por conversa.
    O vetor e de 35 features e o fusor exige as 35 -- nao existe recalcular so
    as tres lexicas e as cinco de emoji sem o resto. Em dezenas de atendimentos
    sao segundos; em milhares vira trabalho de fila, e a fila nao existe aqui.
    A rota e SINCRONA de proposito: uma fila que ninguem observa seria pior que
    uma espera que se ve.
    """
    curadoria = ctx.curadoria_vigente()
    faixas = ctx.faixas_vigentes()
    quantas = 0
    for conversa, _ in ctx.banco.todas():
        score = ctx.motor.pontuar_conversa(conversa, curadoria)
        ctx.banco.salvar(
            conversa,
            score,
            ctx.categoria_de(score, faixas),
            lexico_versao=curadoria.versao,
        )
        quantas += 1
    return {"repontuadas": quantas}
```

**UMA leitura de faixa e UMA de curadoria para o lote inteiro**, fora do laço:
ler por conversa abriria janela para o lote começar com uma configuração e
terminar com outra — que é a régua misturada de novo, agora dentro da rota que
existe para acabar com ela.

- [ ] **Passo 5: rodar e ver passar**

Executar: `uv run pytest tests/test_api_repontuar.py -q`
Esperado: PASSA — 5 testes.

- [ ] **Passo 6: a suíte inteira**

Executar: `uv run pytest -q`
Esperado: PASSA.

- [ ] **Passo 7: commit**

```bash
git add fraus/api/rotas/conversas.py fraus/api/rotas/indicadores.py tests/test_api_repontuar.py
git commit -m "feat(api): repontuar o banco, e a contagem que denuncia regua misturada"
```

---

### Task 8: A dashboard — o painel e o aviso

**Arquivos:**
- Criar: `dashboard/components/LexicoCurado.tsx`
- Modificar: `dashboard/app/modelo/page.tsx`
- Modificar: `dashboard/lib/api.ts` (tipos e chamadas)
- Modificar: `dashboard/app/page.tsx` (o aviso na Visão geral)

**Interfaces:**
- Consome: `GET/POST/DELETE /lexico/curado`, `POST /conversas/repontuar` da
  Task 6 e 7; `pontuadas_com_lexico_antigo` e `total_no_banco` da Task 7.
- Produz: nada para tarefas seguintes.

- [ ] **Passo 1: os tipos e as chamadas**

Em `dashboard/lib/api.ts`, acrescentar, seguindo o padrão dos tipos e funções já
existentes no arquivo (toda chamada sai pelo proxy `/api/fraus/...`):

```ts
export type TermoCurado = {
  id: number;
  tipo: "palavra" | "emoji";
  termo: string;
  peso: number;
  motivo: string | null;
  criado_em: string;
};

export type NovoTermoCurado = {
  tipo: "palavra" | "emoji";
  termo: string;
  peso: number;
  motivo?: string;
};
```

E as três funções, no mesmo formato das que já existem no arquivo:
`listarCurados(): Promise<TermoCurado[]>` sobre `GET /lexico/curado`,
`curarTermo(novo: NovoTermoCurado): Promise<TermoCurado>` sobre
`POST /lexico/curado`, `revogarCurado(id: number): Promise<void>` sobre
`DELETE /lexico/curado/${id}`, e `repontuarBanco(): Promise<{ repontuadas: number }>`
sobre `POST /conversas/repontuar`.

- [ ] **Passo 2: o painel**

Criar `dashboard/components/LexicoCurado.tsx`. O esqueleto, com as decisões já
tomadas — o restante é preencher estados de carregamento e erro no padrão dos
painéis vizinhos (`ChavesDeAcesso.tsx` é o irmão mais próximo):

```tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import {
  type TermoCurado,
  curarTermo,
  listarCurados,
  revogarCurado,
} from "@/lib/api";

/**
 * O que o analista ensinou ao lexico.
 *
 * A ESCALA DE CADA TIPO E IMPOSTA PELA INTERFACE, e nao so validada no
 * servidor: palavra tem TRES BOTOES, nunca campo numerico livre. Um campo de
 * texto convidaria a digitar -0,7, que a API recusa com 400 -- e a tela nao
 * pode oferecer o que o servidor recusa.
 */
export function LexicoCurado() {
  const [curados, setCurados] = useState<TermoCurado[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [tipo, setTipo] = useState<"palavra" | "emoji">("palavra");
  const [termo, setTermo] = useState("");
  const [peso, setPeso] = useState(-1);
  const [motivo, setMotivo] = useState("");

  const recarregar = useCallback(async () => {
    try {
      setCurados(await listarCurados());
    } catch (e) {
      setErro(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void recarregar();
  }, [recarregar]);

  async function salvar() {
    setErro(null);
    try {
      await curarTermo({
        tipo,
        termo,
        peso,
        motivo: motivo.trim() || undefined,
      });
      setTermo("");
      setMotivo("");
      await recarregar();
    } catch (e) {
      // A MENSAGEM DA API SOBE COMO VEIO: ela nomeia a escala recusada, e
      // reescreve-la aqui duplicaria a regra em dois lugares -- que e o mesmo
      // erro que a tela de Configuracoes evita ao nao reimplementar a
      // validacao da faixa de NPS.
      setErro(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <section className="flex flex-col gap-4">
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => { setTipo("palavra"); setPeso(-1); }}
          aria-pressed={tipo === "palavra"}
        >
          Palavra
        </button>
        <button
          type="button"
          onClick={() => { setTipo("emoji"); setPeso(0); }}
          aria-pressed={tipo === "emoji"}
        >
          Emoji
        </button>
      </div>

      <label>
        {tipo === "palavra" ? "Palavra ou expressão" : "Emoji"}
        <input value={termo} onChange={(e) => setTermo(e.target.value)} />
      </label>

      {tipo === "palavra" ? (
        // Tres botoes, a escala do SentiLex. Rotulo textual junto do estado --
        // categoria nunca e comunicada so por cor (PRODUCT.md).
        <fieldset>
          <legend>Peso</legend>
          {([[-1, "negativa"], [0, "neutra"], [1, "positiva"]] as const).map(
            ([valor, rotulo]) => (
              <label key={rotulo}>
                <input
                  type="radio"
                  name="peso"
                  checked={peso === valor}
                  onChange={() => setPeso(valor)}
                />
                {rotulo}
              </label>
            ),
          )}
        </fieldset>
      ) : (
        <label>
          Peso
          <input
            type="range"
            min={-1}
            max={1}
            step={0.01}
            value={peso}
            onChange={(e) => setPeso(Number(e.target.value))}
          />
          {/* `.num` porque e numero que se compara: monoespacado e tabular. */}
          <span className="num">{peso.toFixed(2)}</span>
        </label>
      )}

      <label>
        Por que este peso
        <input value={motivo} onChange={(e) => setMotivo(e.target.value)} />
      </label>

      <button type="button" onClick={() => void salvar()} disabled={!termo.trim()}>
        Cadastrar
      </button>

      {erro ? <p role="alert">{erro}</p> : null}

      {curados === null ? null : curados.length === 0 ? (
        // ESTADO VAZIO NOMEIA O QUE FALTA, nunca "0 termos".
        <p>
          Nenhum termo curado. O léxico usa só o SentiLex-PT02 e o Emoji
          Sentiment Ranking.
        </p>
      ) : (
        <ul>
          {curados.map((c) => (
            <li key={c.id}>
              <span className="num">{c.termo}</span>
              <span className="num">{c.peso}</span>
              {c.motivo ? <span>{c.motivo}</span> : null}
              {/* A CONFIRMACAO USA O PADRAO DO PROJETO, nunca o `confirm()`
                  nativo: o painel de chaves de acesso ja resolveu isto, e um
                  dialogo do navegador aqui seria a unica peca da interface
                  fora do sistema de design. Copiar de la o componente e o
                  fluxo de dois passos. */}
              <ConfirmarRevogacao
                termo={c.termo}
                aoConfirmar={async () => {
                  await revogarCurado(c.id);
                  await recarregar();
                }}
              />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
```

Regras de interface que o esqueleto acima já cumpre, e que a estilização não
pode desfazer:

- **Palavra:** três botões — *negativa* / *neutra* / *positiva*. Nunca campo
  numérico livre: a escala é −1/0/+1 e um campo de texto convidaria a digitar
  `-0.7`, que a API recusa com 400. A tela não pode oferecer o que o servidor
  recusa.
- **Emoji:** `<input type="range" min={-1} max={1} step={0.01}>` com o valor
  numérico ao lado, monoespaçado (`.num`) — é número que se compara.
- **Motivo:** campo opcional, com o rótulo *"por que este peso"*. Não é
  obrigatório, e não deve virar: campo obrigatório sem uso vira lixo digitado.
- **Estado vazio** que nomeia o que falta: *"Nenhum termo curado. O léxico usa
  só o SentiLex-PT02 e o Emoji Sentiment Ranking."* Nunca "0 termos".
- **Revogar pede confirmação** com o componente do painel de chaves de acesso
  (`ConfirmarRevogacao` acima é o nome de referência — use o que existir lá,
  não crie um segundo). Nunca `confirm()` nativo.
- Erro de 400 da API aparece **como veio**: a mensagem do servidor nomeia a
  escala, e reescrevê-la no cliente duplicaria a regra.

- [ ] **Passo 3: a ficha do modelo declara a curadoria**

Em `dashboard/app/modelo/page.tsx`, ao lado das métricas, acrescentar a linha —
e **só quando houver termos**:

> **12 palavras e 3 emojis curados nesta instalação.**

Com zero termos a linha **some**. Um score influenciado por curadoria humana não
pode se apresentar como inferência pura do modelo — mesma regra que faz o NPS
carregar "estimativa" —, mas anunciar uma intervenção que não houve é o erro
simétrico.

- [ ] **Passo 4: o aviso na Visão geral**

Em `dashboard/app/page.tsx`, quando `pontuadas_com_lexico_antigo > 0`:

> ⚠️ **41 de 62 atendimentos foram pontuados com um léxico anterior.** Os
> números desta tela somam duas réguas. `[ Repontuar tudo ]`

O botão chama `repontuarBanco()`, mostra "repontuando…" enquanto roda e recarrega
a tela ao terminar. Com `pontuadas_com_lexico_antigo === 0` o aviso não existe.

- [ ] **Passo 5: verificar**

```bash
cd dashboard && npm run build && npm run lint && npm test && npm run contraste
```

Esperado: os quatro verdes. Depois, com `uv run python scripts/api_demo.py` num
terminal e `npm run dev` noutro: cadastrar uma palavra, ver o aviso aparecer na
Visão geral, clicar em repontuar, ver o aviso sumir.

- [ ] **Passo 6: commit**

```bash
git add dashboard/
git commit -m "feat(dashboard): o painel do lexico curado e o aviso de regua misturada"
```

---

### Task 9: A documentação

**Arquivos:**
- Modificar: `README.md`
- Modificar: `CLAUDE.md` (mapa de arquivos)

**Interfaces:** consome e produz nada.

- [ ] **Passo 1: a seção do README**

Acrescentar depois da seção *Indicadores*, uma seção **Léxico curado** com:

- o que o peso faz (alimenta o sinal léxico; o fusor decide o quanto pesa) e o
  que ele **não** faz (corrigir score), com o argumento da segunda régua;
- a escala de cada léxico e o porquê de não serem a mesma;
- que a curadoria **vence** o léxico base, e que `0` silencia um termo;
- a versão, o aviso de régua misturada e a limitação do repontuar (os três
  BERTimbau de novo, síncrono, sem fila);
- as quatro rotas.

- [ ] **Passo 2: as duas linhas do mapa em `CLAUDE.md`**

Na tabela do mapa de arquivos:

```markdown
| `fraus/sinais/curadoria.py` | o que o analista ensinou ao léxico — vence o SentiLex e o ranking de emoji |
| `fraus/api/rotas/lexico.py` | cadastrar, listar e revogar termo curado |
```

- [ ] **Passo 3: verificar**

Ler os trechos alterados. Confirmar que a seção nova não contradiz a nota
metodológica existente sobre o NPS inferido.

- [ ] **Passo 4: commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs(lexico): o que o peso curado faz, e o que ele nao faz"
```

---

## Fora deste plano — por decisão

- **A descoberta pela transcrição** (token desconhecido sublinhado na fala,
  popover para classificar no lugar): segunda spec.
- **A fila de "palavras que o modelo mais perdeu"**: terceira spec, e só vale
  depois de existir volume real.
- **A fila assíncrona do repontuar**: ver a docstring da rota.
- **Curadoria por canal ou por fonte**: sem evidência de que o domínio mude
  entre canais no volume deste trabalho.
