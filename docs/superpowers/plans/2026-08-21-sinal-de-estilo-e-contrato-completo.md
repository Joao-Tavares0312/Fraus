# Sinal de estilo e contrato completo de 35 features — plano de implementacao

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar o sinal deterministico de estilo (caixa alta, pontuacao enfatica, alongamento, palavrao, censura) e subir `NOMES_FEATURES` de 16 para 35, ligando tambem emocao, lexico e ironia — que ja existem e estao fora do vetor — para entao retreinar o fusor e re-medir o NPS.

**Architecture:** `fraus/sinais/estilo.py` e um modulo deterministico sem modelo, irmao de `fraus/sinais/emoji.py`: le apenas `conversa.mensagens_cliente` e devolve seis floats. Um CSV curado (`fraus/dados/palavroes_ptbr.csv`) fornece termo, intensidade e alvo. `fraus/fusor.py` passa a compor sete familias de feature e a exigir tres classificadores; `fraus/motor.py` deixa de tratar emocao e ironia como opcionais. O simulador ganha emissao de estilo com cruzamento deliberado entre rotulos, para nao criar um vazamento novo.

**Tech Stack:** Python 3.11, `uv`, pytest, scikit-learn (LogisticRegression + StandardScaler), transformers/BERTimbau nos notebooks Colab.

## Global Constraints

- **Sem LLM em runtime.** Inferencia local em CPU, nenhuma chamada de rede no caminho de predicao (invariante 1).
- **Ausencia de dado nao e insatisfacao.** Conversa sem fala do cliente tem `score: None`. Nunca `?? 0`, nunca `|| 0` (invariante 2).
- **Ordem das classes: 0 insatisfeito, 1 neutro, 2 satisfeito** (invariante 8).
- **As chaves produzidas pelos sinais batem exatamente com `NOMES_FEATURES`;** `vetorizar` levanta `KeyError` em falta, nunca zero silencioso (invariante 9).
- **Corpus de treino nao pode entregar o rotulo.** Distribuicao por rotulo se sobrepoe; acuracia alta demais e sintoma, nao vitoria (invariante 10).
- **Identificadores e docstrings em portugues, sem acento nos nomes de simbolo** (`estilo_frac_caixa_alta`). Texto de interface leva acento normal.
- **Commits em portugues, sem acento, no formato `tipo(escopo): resumo`.**
- **Nenhuma dependencia nova.** O lexicon de palavroes e CSV versionado no repo, lido com o modulo `csv` da stdlib.
- **TDD:** teste que falha primeiro, implementacao minima, teste verde, commit.
- Rodar testes com `uv run pytest -q`. O ambiente ja deve ter `uv sync --extra dev`.

---

### Task 1: Lexicon de palavroes PT-BR

Cria o recurso de dados e a funcao que o le. Sem ele nenhuma feature de palavrao existe.

**Files:**
- Create: `fraus/dados/palavroes_ptbr.csv`
- Create: `fraus/sinais/estilo.py`
- Test: `tests/test_sinal_estilo.py`

**Interfaces:**
- Consumes: nada.
- Produces: `carregar_palavroes() -> dict[str, tuple[float, bool]]` — chave e o termo normalizado, valor e `(intensidade, dirigido)`. `intensidade` em `{0.33, 0.66, 1.0}` para leve/medio/pesado; `dirigido` e `True` quando o termo tipicamente xinga uma pessoa.

- [ ] **Step 1: Escrever o teste que falha**

Crie `tests/test_sinal_estilo.py`:

```python
from fraus.sinais.estilo import carregar_palavroes


def test_lexicon_tem_as_tres_intensidades():
    lexicon = carregar_palavroes()
    intensidades = {intensidade for intensidade, _ in lexicon.values()}
    assert intensidades == {0.33, 0.66, 1.0}


def test_lexicon_distingue_dirigido_de_desabafo():
    lexicon = carregar_palavroes()
    # "droga" e desabafo: ninguem chama o atendente de droga.
    assert lexicon["droga"] == (0.33, False)
    # "idiota" e dirigido a pessoa por definicao.
    assert lexicon["idiota"][1] is True


def test_lexicon_esta_normalizado_em_minusculas_sem_acento():
    for termo in carregar_palavroes():
        assert termo == termo.lower()
        assert all(ord(c) < 128 for c in termo)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_sinal_estilo.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'fraus.sinais.estilo'`

- [ ] **Step 3: Criar o CSV**

Crie `fraus/dados/palavroes_ptbr.csv` com cabecalho `termo,intensidade,alvo`. `intensidade` em `leve|medio|pesado`, `alvo` em `pessoa|desabafo`. Escreva as formas SEM acento e em minusculas (a normalizacao do texto de entrada tambem tira acento, entao acentuar aqui criaria chave inalcancavel).

Comece com este nucleo e complete ate ~150 linhas seguindo o mesmo criterio — variantes flexionadas contam como linhas proprias (`merda`, `merdas`), porque nao ha stemmer no caminho:

```csv
termo,intensidade,alvo
droga,leve,desabafo
drogas,leve,desabafo
porcaria,leve,desabafo
lixo,leve,desabafo
bosta,medio,desabafo
merda,medio,desabafo
merdas,medio,desabafo
inferno,leve,desabafo
caramba,leve,desabafo
caraca,leve,desabafo
porra,medio,desabafo
poha,medio,desabafo
caralho,pesado,desabafo
carai,medio,desabafo
foda,medio,desabafo
fodase,pesado,desabafo
puta,medio,desabafo
putaquepariu,pesado,desabafo
pqp,medio,desabafo
idiota,medio,pessoa
idiotas,medio,pessoa
imbecil,medio,pessoa
imbecis,medio,pessoa
burro,medio,pessoa
burra,medio,pessoa
otario,medio,pessoa
otaria,medio,pessoa
babaca,medio,pessoa
palhaco,medio,pessoa
palhacos,medio,pessoa
incompetente,leve,pessoa
incompetentes,leve,pessoa
inutil,leve,pessoa
retardado,pesado,pessoa
arrombado,pesado,pessoa
filhadaputa,pesado,pessoa
fdp,pesado,pessoa
vagabundo,medio,pessoa
vagabunda,medio,pessoa
cuzao,pesado,pessoa
```

- [ ] **Step 4: Implementar o carregador**

Crie `fraus/sinais/estilo.py`:

```python
"""Sinal de estilo: a FORMA da escrita, nao o conteudo dela.

Caixa alta, pontuacao repetida, alongamento de caractere, palavrao e censura
carregam intensidade que nenhum dos outros sinais captura. E deterministico de
proposito: o BERTimbau nao aprende enfase porque o B2W-Reviews01 -- resenha
moderada de e-commerce -- praticamente nao contem gritaria nem xingamento.
Modelo nao aprende fenomeno que o corpus nao tem, e mais epocas sobre o mesmo
texto so reproduzem o mesmo artefato. Ver a spec de 21/08/2026.

Le apenas as falas do cliente, coerente com os demais sinais: enfase do bot nao
e enfase do cliente.
"""

import csv
import unicodedata
from functools import lru_cache
from pathlib import Path

CAMINHO_PALAVROES = Path(__file__).parent.parent / "dados" / "palavroes_ptbr.csv"

INTENSIDADE_POR_NOME = {"leve": 0.33, "medio": 0.66, "pesado": 1.0}


@lru_cache(maxsize=1)
def carregar_palavroes() -> dict[str, tuple[float, bool]]:
    """Termo normalizado -> (intensidade, dirigido a pessoa).

    A gradacao existe porque "que droga" e "vai tomar no cu" nao sao o mesmo
    evento, e o alvo existe porque xingar o PRODUTO e reclamacao enquanto
    xingar o ATENDENTE e ruptura da conversa.
    """
    tabela: dict[str, tuple[float, bool]] = {}
    with CAMINHO_PALAVROES.open(encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            termo = linha["termo"].strip().lower()
            if not termo:
                continue
            tabela[termo] = (
                INTENSIDADE_POR_NOME[linha["intensidade"].strip()],
                linha["alvo"].strip() == "pessoa",
            )
    return tabela
```

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_sinal_estilo.py -q`
Expected: PASS, 3 testes.

- [ ] **Step 6: Commit**

```bash
git add fraus/dados/palavroes_ptbr.csv fraus/sinais/estilo.py tests/test_sinal_estilo.py
git commit -m "feat(estilo): lexicon de palavroes com gradacao e alvo"
```

---

### Task 2: Normalizacao de homoglifos e deteccao de censura

A ordem entre as duas operacoes e a decisao central desta task: a censura e detectada **antes** da normalizacao, porque o ato de censurar e o dado que `estilo_frac_censurado` mede. Normalizar primeiro apagaria a evidencia.

**Files:**
- Modify: `fraus/sinais/estilo.py`
- Test: `tests/test_sinal_estilo.py`

**Interfaces:**
- Consumes: `carregar_palavroes()` da Task 1.
- Produces:
  - `normalizar(palavra: str) -> str` — minusculas, sem acento, homoglifos revertidos.
  - `tem_censura(palavra: str) -> bool` — `True` se a palavra mistura letra e simbolo de censura.
  - `PALAVRA = re.compile(...)` — separador de palavra que PRESERVA os simbolos de censura.

- [ ] **Step 1: Escrever o teste que falha**

Adicione a `tests/test_sinal_estilo.py`:

```python
from fraus.sinais.estilo import normalizar, tem_censura


def test_normaliza_homoglifos_para_o_termo_do_lexicon():
    assert normalizar("c@r@lh0") == "caralho"
    assert normalizar("p0rra") == "porra"
    assert normalizar("MERDA") == "merda"
    assert normalizar("babaca") == "babaca"


def test_normalizacao_tira_acento():
    assert normalizar("otario") == "otario"
    assert normalizar("otário") == "otario"


def test_censura_detectada_em_palavra_mista():
    assert tem_censura("p*rra") is True
    assert tem_censura("c@ralho") is True
    assert tem_censura("#@$%") is True


def test_palavra_limpa_nao_e_censura():
    assert tem_censura("caralho") is False
    assert tem_censura("obrigado") is False


def test_pontuacao_sozinha_nao_e_censura():
    # "!!!" e enfase, medida por outra feature -- nao e palavrao mascarado.
    assert tem_censura("!!!") is False
    assert tem_censura("???") is False
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_sinal_estilo.py -q`
Expected: FAIL com `ImportError: cannot import name 'normalizar'`

- [ ] **Step 3: Implementar**

Acrescente a `fraus/sinais/estilo.py`, depois de `INTENSIDADE_POR_NOME`:

```python
import re

# Simbolos usados para mascarar palavrao. `!` e `?` NAO entram: eles sao
# enfase, medida por `estilo_pontuacao_enfatica`, e incluir aqui faria "!!!"
# contar como xingamento censurado.
SIMBOLOS_CENSURA = set("*@#$%&0134")

# Homoglifos: o que o cliente digita -> a letra que ele quis dizer. Sem isso o
# lexicon erra TODA ocorrencia censurada, que e justamente a mais interessante.
HOMOGLIFOS = str.maketrans({
    "@": "a", "4": "a",
    "0": "o",
    # "!" NAO entra aqui: `PALAVRA` nao o inclui, entao ele nunca chega a uma
    # palavra -- e mapeamento inalcancavel e some numa refatoracao futura.
    "1": "i",
    "3": "e",
    "$": "s", "5": "s",
    "*": "",
    "#": "", "%": "", "&": "",
})

# Separador de palavra que PRESERVA simbolo de censura: `\w` sozinho quebraria
# "p*rra" em "p" e "rra" e a censura sumiria antes de ser contada.
PALAVRA = re.compile(r"[\w" + re.escape("*@#$%&") + r"]+", re.UNICODE)


def normalizar(palavra: str) -> str:
    """Minusculas, sem acento, homoglifos revertidos.

    Roda DEPOIS de `tem_censura`, nunca antes: ela apaga exatamente a marca que
    a outra funcao precisa ver.
    """
    sem_acento = "".join(
        c
        for c in unicodedata.normalize("NFD", palavra.lower())
        if unicodedata.category(c) != "Mn"
    )
    return sem_acento.translate(HOMOGLIFOS)


def tem_censura(palavra: str) -> bool:
    """A palavra mistura letra e simbolo de mascara, ou e so simbolo.

    Autocensura e raiva COM autocontrole -- estado diferente de raiva crua, e
    por isso tem feature propria em vez de virar so mais um palavrao.
    """
    if not palavra:
        return False
    simbolos = sum(1 for c in palavra if c in SIMBOLOS_CENSURA)
    if simbolos == 0:
        return False
    letras = sum(1 for c in palavra if c.isalpha())
    # So simbolo (`#@$%`) e censura pura; letra + simbolo (`p*rra`) tambem.
    # Numero sozinho ("2024") nao e: precisa de letra junto ou de nenhum
    # caractere alfanumerico fora dos simbolos.
    return letras > 0 or all(c in SIMBOLOS_CENSURA for c in palavra)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_sinal_estilo.py -q`
Expected: PASS, 8 testes.

- [ ] **Step 5: Commit**

```bash
git add fraus/sinais/estilo.py tests/test_sinal_estilo.py
git commit -m "feat(estilo): normalizacao de homoglifos e deteccao de censura"
```

---

### Task 3: As seis features de estilo

**Files:**
- Modify: `fraus/sinais/estilo.py`
- Test: `tests/test_sinal_estilo.py`

**Interfaces:**
- Consumes: `carregar_palavroes()`, `normalizar()`, `tem_censura()`, `PALAVRA`.
- Produces: `features_estilo(conversa: Conversa) -> dict[str, float]` com exatamente estas seis chaves: `estilo_frac_caixa_alta`, `estilo_pontuacao_enfatica`, `estilo_frac_alongamento`, `estilo_palavrao_intensidade`, `estilo_palavrao_dirigido`, `estilo_frac_censurado`.

- [ ] **Step 1: Escrever o teste que falha**

Adicione a `tests/test_sinal_estilo.py` (o helper `_conversa` segue o padrao de `tests/test_sinal_emoji.py`):

```python
from datetime import datetime, timezone

from fraus.modelos import Conversa, Mensagem
from fraus.sinais.estilo import features_estilo

CHAVES = {
    "estilo_frac_caixa_alta",
    "estilo_pontuacao_enfatica",
    "estilo_frac_alongamento",
    "estilo_palavrao_intensidade",
    "estilo_palavrao_dirigido",
    "estilo_frac_censurado",
}


def _conversa(textos: list[str]) -> Conversa:
    base = datetime(2026, 8, 21, 10, 0, 0, tzinfo=timezone.utc)
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=base,
        mensagens=[
            Mensagem(autor="cliente", texto=t, enviada_em=base) for t in textos
        ],
    )


def test_devolve_exatamente_as_seis_chaves():
    assert set(features_estilo(_conversa(["ola"]))) == CHAVES


def test_conversa_sem_fala_do_cliente_zera_sem_estourar():
    base = datetime(2026, 8, 21, 10, 0, 0, tzinfo=timezone.utc)
    conversa = Conversa(
        id="c1",
        canal="csv",
        iniciada_em=base,
        mensagens=[Mensagem(autor="bot", texto="POSSO AJUDAR?!!", enviada_em=base)],
    )
    features = features_estilo(conversa)
    assert set(features) == CHAVES
    assert all(valor == 0.0 for valor in features.values())


def test_gritaria_eleva_a_caixa_alta():
    gritou = features_estilo(_conversa(["NAO ACREDITO NISSO"]))
    calmo = features_estilo(_conversa(["nao acredito nisso"]))
    assert gritou["estilo_frac_caixa_alta"] > 0.9
    assert calmo["estilo_frac_caixa_alta"] == 0.0


def test_sigla_nao_conta_como_gritaria():
    features = features_estilo(_conversa(["preciso do CPF e da NF do pedido"]))
    assert features["estilo_frac_caixa_alta"] == 0.0


def test_pontuacao_enfatica_conta_repeticao():
    com = features_estilo(_conversa(["cade minha entrega???"]))
    sem = features_estilo(_conversa(["cade minha entrega?"]))
    assert com["estilo_pontuacao_enfatica"] > sem["estilo_pontuacao_enfatica"]
    assert sem["estilo_pontuacao_enfatica"] == 0.0


def test_alongamento_detectado():
    features = features_estilo(_conversa(["naooooo pfvvvv"]))
    assert features["estilo_frac_alongamento"] > 0.0


def test_riso_nao_conta_como_alongamento():
    # kkkk e marcador positivo de chat BR, nao arrastar de vogal irritado.
    assert features_estilo(_conversa(["kkkkkk"]))["estilo_frac_alongamento"] == 0.0


def test_intensidade_do_palavrao_e_graduada():
    leve = features_estilo(_conversa(["que droga de sistema"]))
    pesado = features_estilo(_conversa(["que caralho de sistema"]))
    assert 0.0 < leve["estilo_palavrao_intensidade"] < pesado["estilo_palavrao_intensidade"]


def test_palavrao_dirigido_separado_de_desabafo():
    pessoa = features_estilo(_conversa(["voce e um idiota"]))
    desabafo = features_estilo(_conversa(["que merda de sistema"]))
    assert pessoa["estilo_palavrao_dirigido"] > 0.0
    assert desabafo["estilo_palavrao_dirigido"] == 0.0


def test_palavrao_censurado_conta_nas_duas_features():
    features = features_estilo(_conversa(["que p*rra e essa"]))
    assert features["estilo_frac_censurado"] > 0.0
    assert features["estilo_palavrao_intensidade"] > 0.0


def test_texto_limpo_zera_tudo():
    features = features_estilo(_conversa(["bom dia, poderia verificar meu pedido?"]))
    assert all(valor == 0.0 for valor in features.values())
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_sinal_estilo.py -q`
Expected: FAIL com `ImportError: cannot import name 'features_estilo'`

- [ ] **Step 3: Implementar**

Acrescente ao fim de `fraus/sinais/estilo.py`:

```python
from fraus.modelos import Conversa

# Siglas que sao caixa alta sem serem gritaria. Sem esta lista, "preciso do CPF"
# marcaria enfase que nao existe.
SIGLAS = {
    "CPF", "CNPJ", "NF", "NFE", "SAC", "PIX", "CEP", "RG", "ID", "OK",
    "SP", "RJ", "MG", "PR", "RS", "BA", "PE", "CE", "DF", "GO",
    "SMS", "PDF", "URL", "APP", "TV", "PC", "USB", "CD", "DVD",
}

# Piso de comprimento para uma palavra maiuscula contar como grito. Palavra de
# 1-2 letras em caixa alta e quase sempre sigla ou digitacao apressada.
MINIMO_CAIXA_ALTA = 3

# Quantas repeticoes seguidas do mesmo caractere marcam alongamento. Duas nao
# bastam: "carro", "passar" e "nossa" sao grafia normal do portugues.
MINIMO_ALONGAMENTO = 3

# Riso alongado e o marcador POSITIVO mais comum de chat brasileiro. Contar
# "kkkk" junto de "naooooo" inverteria o sentido da feature em boa parte das
# conversas, entao ele tem excecao explicita.
LETRAS_DE_RISO = set("kh")

PONTUACAO_ENFATICA = re.compile(r"[!?]{2,}")


def _e_grito(palavra: str) -> bool:
    """Palavra em caixa alta que nao e sigla nem palavra curta."""
    return (
        len(palavra) >= MINIMO_CAIXA_ALTA
        and palavra.isupper()
        and any(c.isalpha() for c in palavra)
        and palavra not in SIGLAS
    )


def _tem_alongamento(palavra: str) -> bool:
    """Tres ou mais repeticoes do mesmo caractere, exceto riso."""
    minuscula = palavra.lower()
    repeticoes = 1
    for anterior, atual in zip(minuscula, minuscula[1:]):
        if atual != anterior:
            repeticoes = 1
            continue
        repeticoes += 1
        if repeticoes >= MINIMO_ALONGAMENTO and atual not in LETRAS_DE_RISO:
            return True
    return False


def features_estilo(conversa: Conversa) -> dict[str, float]:
    """Agrega a FORMA da escrita das mensagens DO CLIENTE.

    Conversa sem fala do cliente devolve as seis features zeradas -- e ausencia
    de medida, e quem distingue "nao mediu" de "mediu e deu zero" e o
    `score: None` la em cima, nunca esta funcao (invariante 2).
    """
    textos = [m.texto for m in conversa.mensagens_cliente]
    vazio = {
        "estilo_frac_caixa_alta": 0.0,
        "estilo_pontuacao_enfatica": 0.0,
        "estilo_frac_alongamento": 0.0,
        "estilo_palavrao_intensidade": 0.0,
        "estilo_palavrao_dirigido": 0.0,
        "estilo_frac_censurado": 0.0,
    }
    if not textos:
        return vazio

    lexicon = carregar_palavroes()
    palavras: list[str] = []
    for texto in textos:
        palavras.extend(PALAVRA.findall(texto))

    if not palavras:
        return vazio

    total = len(palavras)
    gritos = 0
    alongadas = 0
    censuradas = 0
    intensidades: list[float] = []
    dirigidos = 0

    for palavra in palavras:
        if _e_grito(palavra):
            gritos += 1
        if _tem_alongamento(palavra):
            alongadas += 1
        # A censura e lida ANTES da normalizacao: `normalizar` apaga os
        # simbolos que sao justamente a evidencia.
        if tem_censura(palavra):
            censuradas += 1
        entrada = lexicon.get(normalizar(palavra))
        if entrada is not None:
            intensidade, dirigido = entrada
            intensidades.append(intensidade)
            if dirigido:
                dirigidos += 1

    enfaticas = sum(len(PONTUACAO_ENFATICA.findall(t)) for t in textos)

    return {
        "estilo_frac_caixa_alta": gritos / total,
        "estilo_pontuacao_enfatica": enfaticas / len(textos),
        "estilo_frac_alongamento": alongadas / total,
        "estilo_palavrao_intensidade": (
            sum(intensidades) / len(intensidades) if intensidades else 0.0
        ),
        "estilo_palavrao_dirigido": (
            dirigidos / len(intensidades) if intensidades else 0.0
        ),
        "estilo_frac_censurado": censuradas / total,
    }
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_sinal_estilo.py -q`
Expected: PASS, 19 testes.

Se `test_palavrao_censurado_conta_nas_duas_features` falhar, confira se `p*rra` normaliza para `porra` — o `*` mapeia para string vazia em `HOMOGLIFOS`, e `porra` precisa existir no CSV da Task 1.

- [ ] **Step 5: Commit**

```bash
git add fraus/sinais/estilo.py tests/test_sinal_estilo.py
git commit -m "feat(estilo): as seis features de forma da escrita"
```

---

### Task 4: Contrato de 35 features

Sobe `NOMES_FEATURES` e faz `montar_features` exigir os tres classificadores. Esta task quebra `fraus/motor.py` de proposito; a Task 5 conserta.

**Files:**
- Modify: `fraus/fusor.py:23-40` (`NOMES_FEATURES`), `fraus/fusor.py:70-76` (`montar_features`)
- Test: `tests/test_fusor.py`

**Interfaces:**
- Consumes: `features_estilo` (Task 3), `features_emocao`, `features_lexico`, `features_ironia` (ja existentes).
- Produces: `montar_features(conversa, classificador, classificador_emocao, classificador_ironia) -> dict[str, float]` — os tres classificadores sao POSICIONAIS e obrigatorios. `NOMES_FEATURES` com 35 entradas.

- [ ] **Step 1: Escrever o teste que falha**

Adicione a `tests/test_fusor.py`:

```python
from fraus.fusor import NOMES_FEATURES


def test_contrato_tem_trinta_e_cinco_features():
    assert len(NOMES_FEATURES) == 35


def test_contrato_nao_tem_duplicata():
    assert len(set(NOMES_FEATURES)) == len(NOMES_FEATURES)


def test_contrato_cobre_todos_os_prefixos_esperados():
    """Onze prefixos, sete familias: tempo sozinho usa cinco deles."""
    prefixos = {nome.split("_")[0] for nome in NOMES_FEATURES}
    assert prefixos == {
        "texto", "emoji", "latencia", "duracao", "qtd", "escalou",
        "abandonou", "emocao", "lexico", "ironia", "estilo",
    }


def test_vetorizar_estoura_em_feature_de_estilo_faltando():
    import pytest

    from fraus.fusor import vetorizar

    completas = {nome: 0.0 for nome in NOMES_FEATURES}
    del completas["estilo_frac_caixa_alta"]
    with pytest.raises(KeyError):
        vetorizar(completas)


def test_vetorizar_estoura_em_feature_de_emocao_faltando():
    import pytest

    from fraus.fusor import vetorizar

    completas = {nome: 0.0 for nome in NOMES_FEATURES}
    del completas["emocao_raiva_media"]
    with pytest.raises(KeyError):
        vetorizar(completas)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_fusor.py -q`
Expected: FAIL — `assert 16 == 35`

- [ ] **Step 3: Implementar**

Em `fraus/fusor.py`, acrescente os imports:

```python
from fraus.sinais.emocao import features_emocao
from fraus.sinais.estilo import features_estilo
from fraus.sinais.ironia import features_ironia
from fraus.sinais.lexico import features_lexico
```

Substitua `NOMES_FEATURES` pela lista completa, mantendo o agrupamento por familia:

```python
# Ordem canonica das 35 features, agrupadas por familia de sinal. A ordem
# importa: `vetorizar` produz o vetor nesta sequencia e o fusor treinado espera
# exatamente ela. Reordenar sem retreinar troca os pesos de lugar em silencio.
#
# Subiu de 16 para 35 em 21/08/2026: emocao, lexico e ironia ja existiam e
# estavam FORA do vetor esperando os notebooks 03 e 04, que agora existem;
# estilo nasceu junto. Ver a spec de 21/08/2026.
NOMES_FEATURES = [
    # texto (4)
    "texto_prob_insatisfeito_media",
    "texto_prob_satisfeito_media",
    "texto_prob_insatisfeito_max",
    "texto_prob_satisfeito_ultima",
    # emoji (5)
    "emoji_score_medio",
    "emoji_frac_positivos",
    "emoji_frac_negativos",
    "emoji_contagem",
    "emoji_posicao_relativa_media",
    # tempo (7)
    "latencia_mediana_s",
    "latencia_p90_s",
    "latencia_primeira_resposta_s",
    "duracao_total_s",
    "qtd_turnos_cliente",
    "escalou",
    "abandonou",
    # emocao (8)
    "emocao_alegria_media",
    "emocao_tristeza_media",
    "emocao_raiva_media",
    "emocao_medo_media",
    "emocao_nojo_media",
    "emocao_surpresa_media",
    "emocao_neutro_media",
    "emocao_desprezo_derivado",
    # lexico (3)
    "lexico_polaridade_media",
    "lexico_cobertura",
    "lexico_frac_negados",
    # ironia (2)
    "ironia_prob_media",
    "ironia_prob_max",
    # estilo (6)
    "estilo_frac_caixa_alta",
    "estilo_pontuacao_enfatica",
    "estilo_frac_alongamento",
    "estilo_palavrao_intensidade",
    "estilo_palavrao_dirigido",
    "estilo_frac_censurado",
]
```

Substitua `montar_features`:

```python
def montar_features(
    conversa: Conversa,
    classificador,
    classificador_emocao,
    classificador_ironia,
) -> dict[str, float]:
    """Junta os sete sinais numa linha unica de features.

    Os tres classificadores sao OBRIGATORIOS desde que o contrato subiu para 35:
    emocao e ironia deixaram de ser leitura decorativa e passaram a mover a
    nota. Aceitar `None` aqui produziria vetor incompleto, e vetor incompleto
    vira `KeyError` la em `vetorizar` -- com a diferenca de que o erro apontaria
    para o lugar errado.
    """
    return {
        **features_texto(conversa, classificador),
        **features_emoji(conversa),
        **features_tempo(conversa),
        **features_emocao(conversa, classificador_emocao),
        **features_lexico(conversa),
        **features_ironia(conversa, classificador_ironia),
        **features_estilo(conversa),
    }
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_fusor.py -q`
Expected: PASS.

Confira a soma: 4+5+7+8+3+2+6 = 35. Se `test_contrato_cobre_todos_os_prefixos_esperados` falhar, confira os nomes reais das chaves rodando:

```bash
uv run python -c "from fraus.sinais.lexico import features_lexico; print(features_lexico.__doc__)"
```

- [ ] **Step 5: Commit**

```bash
git add fraus/fusor.py tests/test_fusor.py
git commit -m "feat(fusor): contrato sobe de 16 para 35 features"
```

---

### Task 5: Motor com emocao e ironia obrigatorias

A docstring de `Motor` afirma hoje que emocao e ironia "nao movem a nota um centesimo". Depois da Task 4 isso e mentira, e docstring que mente e pior que docstring ausente.

**Files:**
- Modify: `fraus/motor.py:18-47` (docstring e `__init__`), `fraus/motor.py:72-75` (`pontuar_conversa`)
- Modify: `fraus/api/main.py:148-159`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `montar_features` com quatro parametros (Task 4).
- Produces: `Motor(classificador, fusor, emocao, ironia)` — os quatro obrigatorios, nesta ordem.

- [ ] **Step 1: Rodar a suite para ver o estrago**

Run: `uv run pytest -q`
Expected: FAIL em varios testes com `TypeError: montar_features() missing 2 required positional arguments`.

Anote quais arquivos falharam — sao os que a Task 5 precisa consertar.

- [ ] **Step 2: Corrigir o Motor**

Em `fraus/motor.py`, troque a docstring da classe e o `__init__`:

```python
class Motor:
    """Amarra os tres classificadores e o fusor num unico ponto de pontuacao.

    Emocao e ironia ENTRAM no score desde que o contrato subiu para 35 features
    (21/08/2026). Antes disso elas eram leitura decorativa e esta docstring
    dizia, corretamente, que nao moviam a nota -- nao dizem mais.

    A consequencia pratica: os tres modelos sao obrigatorios. Sem qualquer um
    deles a API nao sobe, e esse e o comportamento correto (invariante 7) --
    servir predicao com vetor incompleto e pior do que estar fora do ar.
    """

    def __init__(
        self,
        classificador: ClassificadorTexto,
        fusor: Fusor,
        emocao: ClassificadorEmocao,
        ironia: ClassificadorIronia,
    ) -> None:
        self._classificador = classificador
        self._fusor = fusor
        self._emocao = emocao
        self._ironia = ironia
```

Em `pontuar_conversa`:

```python
    def pontuar_conversa(self, conversa) -> float | None:
        if not conversa.tem_sinal_cliente:
            return None  # ausencia de dado nao e insatisfacao
        return self._fusor.pontuar(
            montar_features(conversa, self._classificador, self._emocao, self._ironia)
        )
```

Os guardas `if self._emocao is None` em `_emocao_de` e `_ironia_de` podem ficar: eles ainda protegem o caso de lista de textos vazia, que continua real.

- [ ] **Step 3: Corrigir a montagem da API**

Em `fraus/api/main.py`, na funcao que carrega os modelos (por volta da linha 148), os classificadores de emocao e ironia devem ser carregados **sem** try/except silencioso, do mesmo jeito que `ClassificadorTexto` ja e — propagando `ModeloAusenteError`. Leia o trecho atual antes de editar:

```bash
uv run python -c "import inspect, fraus.api.main as m; print(inspect.getsource(m))" | sed -n '135,170p'
```

Ajuste para que `emocao` e `ironia` sejam construidos incondicionalmente e passados posicionalmente a `Motor(classificador, fusor, emocao, ironia)`.

- [ ] **Step 4: Rodar a suite inteira**

Run: `uv run pytest -q`
Expected: PASS. Testes que construiam `Motor` com dois argumentos precisam de dublês para os dois novos — siga o padrao de dublê ja usado em `tests/test_api.py`.

- [ ] **Step 5: Commit**

```bash
git add fraus/motor.py fraus/api/main.py tests/
git commit -m "feat(motor): emocao e ironia passam a mover a nota"
```

---

### Task 6: Simulador emite estilo com cruzamento deliberado

Sem isto as seis features nascem constantes no treino e recebem peso zero — o destino de `emoji_score_medio` no primeiro fusor. Com isto feito do jeito ingenuo, o estilo vira o novo gabarito. O cruzamento e o que evita os dois.

**Files:**
- Modify: `fraus/ingest/simulador.py:51-59` e `fraus/ingest/simulador.py:118-122`
- Test: `tests/test_simulador.py`

**Interfaces:**
- Consumes: `features_estilo` (Task 3).
- Produces: `_com_estilo(aleatorio, texto, rotulo) -> str`, aplicado dentro de `gerar_conversa`.

- [ ] **Step 1: Escrever o teste que falha**

Adicione a `tests/test_simulador.py`:

```python
import statistics

from fraus.ingest.simulador import FRASES_POR_ROTULO, gerar_lote
from fraus.sinais.estilo import features_estilo

CHAVES_ESTILO = [
    "estilo_frac_caixa_alta",
    "estilo_pontuacao_enfatica",
    "estilo_frac_alongamento",
    "estilo_palavrao_intensidade",
    "estilo_palavrao_dirigido",
    "estilo_frac_censurado",
]


def _por_rotulo(quantidade: int = 180) -> dict[int, list[dict]]:
    agrupado: dict[int, list[dict]] = {0: [], 1: [], 2: []}
    for conversa, rotulo in gerar_lote(FRASES_POR_ROTULO, quantidade, semente=7):
        agrupado[rotulo].append(features_estilo(conversa))
    return agrupado


def test_estilo_varia_dentro_de_cada_rotulo():
    """Feature constante no treino nasce com peso zero -- e o bug do emoji na v1."""
    agrupado = _por_rotulo()
    for rotulo, linhas in agrupado.items():
        for chave in CHAVES_ESTILO:
            valores = [linha[chave] for linha in linhas]
            assert statistics.pstdev(valores) > 0.0, f"{chave} constante no rotulo {rotulo}"


def test_palavrao_aparece_nas_tres_classes():
    """Palavrao so em detrator seria a latencia disjunta com outra roupa."""
    agrupado = _por_rotulo()
    for rotulo, linhas in agrupado.items():
        com_palavrao = [l for l in linhas if l["estilo_palavrao_intensidade"] > 0]
        assert com_palavrao, f"nenhum palavrao no rotulo {rotulo}"


def test_gritaria_aparece_nas_tres_classes():
    agrupado = _por_rotulo()
    for rotulo, linhas in agrupado.items():
        assert any(l["estilo_frac_caixa_alta"] > 0 for l in linhas), rotulo


def test_distribuicoes_de_estilo_se_sobrepoem_entre_rotulos():
    """As caudas se cruzam: existe satisfeito que grita e detrator que e educado."""
    agrupado = _por_rotulo()
    maximo_satisfeito = max(l["estilo_palavrao_intensidade"] for l in agrupado[2])
    mediana_insatisfeito = statistics.median(
        l["estilo_palavrao_intensidade"] for l in agrupado[0]
    )
    assert maximo_satisfeito >= mediana_insatisfeito
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_simulador.py -q`
Expected: FAIL em `test_estilo_varia_dentro_de_cada_rotulo` — as features saem todas 0.0 porque o simulador nao emite estilo.

- [ ] **Step 3: Implementar**

Em `fraus/ingest/simulador.py`, depois de `PROB_EMOJI`:

```python
# Marcas de estilo por rotulo, com o MESMO cruzamento deliberado dos emojis: a
# ultima entrada de cada lista pertence ao registro da classe OPOSTA. Cliente
# satisfeito tambem grita ("OBRIGADOOO"), cliente insatisfeito tambem escreve
# em minusculas e agradece.
#
# Sem esse cruzamento o palavrao viraria o novo gabarito e a regressao
# logistica leria a gritaria em vez do texto -- exatamente o que a latencia
# disjunta fez com o primeiro fusor.
#
# Cada entrada e (sufixo, transforma_em_caixa_alta).
ESTILO_POR_ROTULO = {
    0: [
        ("que MERDA de atendimento", True),
        ("ja e a QUARTA vez!!!", True),
        ("que p*rra e essa???", False),
        ("nao aguento maisss", False),
        ("voces sao uns incompetentes", False),
        ("por favor, poderia verificar?", False),
    ],
    1: [
        ("ok???", False),
        ("hmmmm", False),
        ("que droga, mas tudo bem", False),
        ("CERTO", True),
        ("entendi", False),
    ],
    2: [
        ("OBRIGADOOO", True),
        ("kkkk PERFEITO", True),
        ("que caralho de suporte bom", False),
        ("valeuuuu", False),
        ("muito bom!!!", False),
        ("obrigado", False),
    ],
}

# Fracao das falas do cliente que recebem marca de estilo. Como no emoji: se
# todas tivessem, a AUSENCIA de estilo viraria informacao por si so.
PROB_ESTILO = 0.40
```

E, junto de `_com_emoji`:

```python
def _com_estilo(aleatorio: random.Random, texto: str, rotulo: int) -> str:
    """Anexa uma marca de estilo do perfil do rotulo, as vezes.

    Ver ESTILO_POR_ROTULO para o motivo do cruzamento entre classes.
    """
    if aleatorio.random() >= PROB_ESTILO:
        return texto
    sufixo, gritar = aleatorio.choice(ESTILO_POR_ROTULO[rotulo])
    return f"{texto} {sufixo.upper() if gritar else sufixo}"
```

Nas duas construcoes de `Mensagem` do cliente em `gerar_conversa` (linhas ~142 e ~161), envolva a chamada:

```python
                texto=_com_estilo(
                    aleatorio,
                    _com_emoji(aleatorio, aleatorio.choice(frases_cliente), rotulo),
                    rotulo,
                ),
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_simulador.py -q`
Expected: PASS.

Se `test_estilo_varia_dentro_de_cada_rotulo` continuar falhando em `estilo_frac_censurado` para os rotulos 1 e 2, acrescente uma entrada censurada as listas desses rotulos — toda feature precisa variar em TODOS os rotulos, senao ela vira gabarito parcial.

- [ ] **Step 5: Rodar a suite inteira**

Run: `uv run pytest -q`
Expected: PASS. O simulador alimenta `scripts/medir_faixas.py` e `scripts/api_demo.py`; se algo la quebrar, conserte antes de commitar.

- [ ] **Step 6: Commit**

```bash
git add fraus/ingest/simulador.py tests/test_simulador.py
git commit -m "feat(simulador): emite estilo com cruzamento entre rotulos"
```

---

### Task 7: Notebook 02 reescrito

**Files:**
- Modify: `notebooks/02_treino_fusor.ipynb`

**Interfaces:**
- Consumes: `montar_features` com quatro parametros (Task 4), `NOMES_FEATURES` com 35 (Task 4), simulador com estilo (Task 6).
- Produces: `modelos/fusor.joblib` e `modelos/importancias.json` treinados sobre 35 features.

- [ ] **Step 1: Ajustar a celula de conferencia de artefatos**

A primeira celula hoje confere apenas `modelos/bertimbau-satisfacao`. Passe a conferir os **tres** diretorios, falhando com mensagem que aponta o notebook responsavel:

```python
from pathlib import Path

EXIGIDOS = {
    "bertimbau-satisfacao": "notebook 01",
    "bertimbau-emocao": "notebook 03",
    "bertimbau-ironia": "notebook 04",
}
raiz = Path("/content/drive/MyDrive/fraus/modelos")
faltando = [f"{nome} (rode o {origem})" for nome, origem in EXIGIDOS.items()
            if not (raiz / nome).exists()]
assert not faltando, "Modelos ausentes: " + "; ".join(faltando)
```

- [ ] **Step 2: Ajustar a celula de extracao de features**

Carregue os tres classificadores e passe os tres a `montar_features`:

```python
from fraus.fusor import montar_features, NOMES_FEATURES
from fraus.sinais.texto import ClassificadorTexto
from fraus.sinais.emocao import ClassificadorEmocao
from fraus.sinais.ironia import ClassificadorIronia

classificador = ClassificadorTexto(raiz / "bertimbau-satisfacao")
emocao = ClassificadorEmocao(raiz / "bertimbau-emocao")
ironia = ClassificadorIronia(raiz / "bertimbau-ironia")

exemplos = [montar_features(c, classificador, emocao, ironia) for c, _ in lote]
rotulos = [r for _, r in lote]
assert len(NOMES_FEATURES) == 35
```

- [ ] **Step 3: Acrescentar a celula de sanidade de variancia (ANTES do treino)**

```python
import statistics
from collections import defaultdict

por_rotulo = defaultdict(list)
for features, rotulo in zip(exemplos, rotulos):
    por_rotulo[rotulo].append(features)

print(f"{'feature':<34} {'sigma r0':>10} {'sigma r1':>10} {'sigma r2':>10}")
mortas = []
for nome in NOMES_FEATURES:
    sigmas = [statistics.pstdev([f[nome] for f in por_rotulo[r]]) for r in (0, 1, 2)]
    marca = "  <-- CONSTANTE" if min(sigmas) == 0.0 else ""
    if marca:
        mortas.append(nome)
    print(f"{nome:<34} {sigmas[0]:>10.4f} {sigmas[1]:>10.4f} {sigmas[2]:>10.4f}{marca}")

if mortas:
    print(f"\nATENCAO: {len(mortas)} feature(s) constante(s) em algum rotulo.")
    print("Feature constante no treino nasce com peso ZERO -- foi o que aconteceu")
    print("com emoji_score_medio no primeiro fusor. Conserte o simulador antes de treinar.")
```

- [ ] **Step 4: Acrescentar a celula de pesos por grupo (DEPOIS do treino)**

```python
FAMILIAS = {
    "texto": "texto_", "emoji": "emoji_",
    "tempo": ("latencia_", "duracao_", "qtd_", "escalou", "abandonou"),
    "emocao": "emocao_", "lexico": "lexico_", "ironia": "ironia_", "estilo": "estilo_",
}
importancias = fusor.importancias()

def _da_familia(nome, prefixos):
    prefixos = prefixos if isinstance(prefixos, tuple) else (prefixos,)
    return any(nome.startswith(p) for p in prefixos)

print(f"{'familia':<10} {'soma |coef|':>12} {'media':>10}")
for familia, prefixos in FAMILIAS.items():
    valores = [v for n, v in importancias.items() if _da_familia(n, prefixos)]
    print(f"{familia:<10} {sum(valores):>12.4f} {sum(valores)/len(valores):>10.4f}")

print("\nCRITERIO: texto e emoji devem liderar. Se tempo ou estilo lideram,")
print("procure o vazamento -- e o modo de falha de 13/08/2026, nao vitoria.")
```

- [ ] **Step 5: Acrescentar a celula do teste do relogio (DEPOIS do treino)**

```python
from datetime import datetime, timedelta, timezone
from fraus.modelos import Conversa, Mensagem

BASE = datetime(2026, 8, 21, 10, 0, 0, tzinfo=timezone.utc)

def _conversa_de_teste(texto, latencia_s):
    return Conversa(
        id="t", canal="simulado", iniciada_em=BASE,
        encerrada_em=BASE + timedelta(seconds=latencia_s),
        mensagens=[
            Mensagem(autor="cliente", texto=texto, enviada_em=BASE),
            Mensagem(autor="bot", texto="Um momento, por favor.",
                     enviada_em=BASE + timedelta(seconds=latencia_s)),
        ],
    )

OTIMO = "perfeito, resolveu na hora, muito obrigado!"
PESSIMO = "pessimo, ja e a terceira vez e ninguem resolve"

print(f"{'texto':<10} {'5s':>8} {'30s':>8} {'200s':>8}")
for nome, texto in (("otimo", OTIMO), ("pessimo", PESSIMO)):
    notas = [
        fusor.pontuar(montar_features(_conversa_de_teste(texto, s), classificador, emocao, ironia))
        for s in (5, 30, 200)
    ]
    print(f"{nome:<10} " + " ".join(f"{n:>8.2f}" for n in notas))

print("\nCRITERIO: a separacao ENTRE as linhas deve ser dezenas de pontos;")
print("a variacao DENTRO de cada linha (so o relogio mudou) deve ser fracao de ponto.")
print("O fusor vazado de 13/08 separava 2,5 pontos; o corrigido separou 99,6.")
```

- [ ] **Step 6: Commit**

```bash
git add notebooks/02_treino_fusor.ipynb
git commit -m "feat(notebook): fusor treina sobre 35 features com tres diagnosticos"
```

---

### Task 8: Documentacao do contrato novo

**Files:**
- Modify: `docs/treinamento.md` (secao "Contrato de features", linhas ~157-172)
- Modify: `CLAUDE.md` (mapa de arquivos e invariante 9)

- [ ] **Step 1: Atualizar `docs/treinamento.md`**

Substitua a tabela de contrato pela versao com as sete familias, todas marcadas "sim" na coluna "no vetor?", e troque o paragrafo "Por que a espera e deliberada" por um registro do que aconteceu:

```markdown
Hoje sao **35 features**, das sete familias. O contrato subiu de 16 para 35 em
21/08/2026, quando os notebooks 03 e 04 passaram a existir e a condicao que
justificava a espera acabou.

| sinal | modulo | features | no vetor? |
|---|---|---|---|
| texto | `fraus/sinais/texto.py` | 4 | sim |
| emoji | `fraus/sinais/emoji.py` | 5 | sim |
| tempo | `fraus/sinais/tempo.py` | 7 | sim |
| emocao | `fraus/sinais/emocao.py` | 8 | sim |
| lexico | `fraus/sinais/lexico.py` | 3 | sim |
| ironia | `fraus/sinais/ironia.py` | 2 | sim |
| estilo | `fraus/sinais/estilo.py` | 6 | sim |

**Consequencia:** `montar_features` exige TRES classificadores, e a API nao sobe
sem os tres artefatos em `modelos/`. E o comportamento correto da invariante 7.
```

Acrescente uma secao "Sinal de estilo" no fim, no molde da secao "Sinal lexico" ja existente, cobrindo: por que e deterministico e nao treinado, a procedencia do `palavroes_ptbr.csv` (curadoria propria, com gradacao e alvo), a ordem censura-antes-de-normalizacao, e a excecao do `kkkk`.

- [ ] **Step 2: Atualizar `CLAUDE.md`**

No mapa de arquivos, acrescente a linha:

```markdown
| `fraus/sinais/estilo.py` | caixa alta, pontuacao, alongamento, palavrao, censura |
```

Na invariante 9, troque "As 16 chaves de feature" por "As 35 chaves de feature" e substitua o paragrafo sobre a espera dos sinais novos por:

```markdown
9. **As 35 chaves de feature** produzidas pelos sete sinais batem exatamente com
   `NOMES_FEATURES`. `vetorizar` levanta `KeyError` em falta — nunca zero
   silencioso. Emocao, lexico, ironia e estilo entraram no vetor em 21/08/2026:
   `montar_features` agora exige tres classificadores, e a API nao sobe sem os
   tres modelos treinados.
```

Na tabela de arquitetura em "Arquitetura em uma tela", troque "16 features" por "35 features".

- [ ] **Step 3: Verificar que nao sobrou "16 features" no repo**

Run: `grep -rn "16 features\|dezesseis" --include=*.py --include=*.md . | grep -v docs/superpowers/specs`
Expected: nenhuma linha fora dos documentos historicos (specs antigas e a secao do vazamento em `docs/treinamento.md`, que descreve o passado e deve continuar dizendo 16).

- [ ] **Step 4: Commit**

```bash
git add docs/treinamento.md CLAUDE.md
git commit -m "docs(contrato): registra as 35 features e o sinal de estilo"
```

---

### Task 9: Re-medicao do NPS

Roda DEPOIS de o fusor de 35 features estar em `modelos/`. Nao produz codigo — produz numero e decisao.

**Files:**
- Nenhum arquivo modificado por padrao. Se o criterio abaixo indicar mudanca de peso, ai sim `fraus/fusor.py:67`.

- [ ] **Step 1: Medir a regua vigente**

Run: `uv run python scripts/medir_faixas.py`

Anote: distribuicao por categoria, NPS, e as **tres medianas por classe**.

- [ ] **Step 2: Medir a regua antiga, para o antes e depois**

Run: `uv run python scripts/medir_faixas.py --peso-neutro 0.5`

- [ ] **Step 3: Aplicar o criterio de decisao**

O criterio foi fixado na spec ANTES de qualquer numero existir, e e para ser seguido como esta escrito:

- **medianas por classe continuam separadas** (a referencia de 16 features era ~0,11 / 50,99 / 99,03) **e so a distribuicao de categoria escorregou** → defeito de COMPOSICAO. O peso do neutro e o lugar certo de mexer;
- **medianas colapsaram umas nas outras** → defeito de TREINO. Mexer no peso maquiaria modelo ruim; volte para a Task 6 e investigue o simulador.

- [ ] **Step 4: PARAR e reportar ao Joao**

Nao altere `PESO_NEUTRO_NO_SCORE` por conta propria. Mudar o peso exige repontuar o banco inteiro — scores gravados sob duas reguas diferentes somados no mesmo agregado nao se separam na leitura. A decisao e do Joao, com os numeros dos passos 1 e 2 na mesa.

Reporte no formato:

```
regua 0.75:  detrator X% · neutro Y% · promotor Z% · NPS N
regua 0.50:  detrator X% · neutro Y% · promotor Z% · NPS N
medianas por classe verdadeira: A / B / C
diagnostico: composicao | treino
```

- [ ] **Step 5: Registrar o numero em `docs/treinamento.md`**

Independente da decisao, o numero medido entra na secao "Consequencia no NPS", ao lado do numero de 16 features, identificado como "com 35 features, 21/08/2026". Numero de banca que nao se reproduz e lembranca, nao medida.

```bash
git add docs/treinamento.md
git commit -m "docs(nps): mede as faixas com o fusor de 35 features"
```

---

## Ordem de execucao e dependencias

```
Task 1 (lexicon) -> Task 2 (normalizacao) -> Task 3 (features)
                                                  |
                                                  v
                                            Task 4 (contrato 35)
                                                  |
                                    +-------------+-------------+
                                    v                           v
                            Task 5 (motor)              Task 6 (simulador)
                                    |                           |
                                    +-------------+-------------+
                                                  v
                                        Task 7 (notebook 02, Colab)
                                                  |
                                                  v
                                        Task 8 (docs)  Task 9 (NPS)
```

Tasks 1-6 e 8 rodam localmente com `uv run pytest -q` verde ao fim de cada uma. A Task 7 roda no Google Colab e exige os tres artefatos treinados. A Task 9 exige o `fusor.joblib` novo baixado para `modelos/`.
