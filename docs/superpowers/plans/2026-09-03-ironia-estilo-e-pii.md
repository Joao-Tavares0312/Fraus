# Incongruência, leitura de estilo e censura de PII — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Melhorar o sinal de ironia com 5 features de incongruência calculadas sem LLM, expor a leitura de estilo por mensagem na dashboard, e mascarar dados sensíveis (CPF, e-mail, telefone, cartão, endereço) antes de gravar e antes de inferir.

**Architecture:** Três frentes independentes numa sessão só. (1) `fraus/seguranca/pii.py` mascara PII no ponto de entrada compartilhado (`registrar_conversa` e `csv_driver`), antes de `Conversa` existir — é a frente mais a montante e vai primeiro. (2) `fraus/sinais/incongruencia.py` adiciona 5 features ao vetor do `Fusor` (35 → 40), reusando `lexico.py` e `emoji.py`, exigindo retreino do fusor. (3) `estilo.py` ganha uma leitura por mensagem exposta pelo motor e um componente novo na dashboard, mais revisão dos limiares fixos.

**Tech Stack:** Python 3.11 (uv), pydantic, scikit-learn, pytest; Next.js/TypeScript no front.

## Global Constraints

- **Sem LLM em runtime.** Nada do que este plano adiciona pode fazer chamada de rede no caminho de predição. As 5 features de incongruência e a censura de PII são regex + léxico + checksum, determinísticos.
- **Ausência de dado não é insatisfação.** Conversa sem fala do cliente devolve features zeradas e `score: None`; nunca `?? 0` / `|| 0` no front.
- **Score, nota e categoria derivados no SERVIDOR.** Nada recalculado no TypeScript.
- **Identificadores e docstrings em português, sem acento nos nomes de símbolo** (`censurar_pii`, `incongruencia_polaridade`). Texto de interface leva acento normal.
- **Commits em português, sem acento, no estilo `tipo(escopo): resumo`.**
- **TDD:** teste que falha primeiro, implementação mínima, teste verde, commit.
- **As chaves de feature batem exatamente com `NOMES_FEATURES`;** `vetorizar` levanta `KeyError` em falta, nunca zero silencioso. Ao fim deste plano são **40** chaves.
- **Ordem das classes: 0 insatisfeito, 1 neutro, 2 satisfeito.** Não inverter.
- **Nada de dependência nova** — tudo com stdlib (`re`, `unicodedata`) e o que já está no `pyproject.toml`.
- Comandos: `uv sync --extra dev` (o grupo dev é opt-in), `uv run pytest -q`, `cd dashboard && npm run dev`.

---

## Frente 1 — Censura de PII

### Task 1: Módulo de censura de PII

**Files:**
- Create: `fraus/seguranca/__init__.py`
- Create: `fraus/seguranca/pii.py`
- Test: `tests/test_pii.py`

**Interfaces:**
- Consumes: nada (módulo folha, só stdlib).
- Produces: `censurar_pii(texto: str) -> str`, usada nas Tasks 2 e 3.

- [ ] **Step 1: Write the failing test**

Crie `tests/test_pii.py`:

```python
from fraus.seguranca.pii import censurar_pii


def test_mascara_cpf_valido():
    # 529.982.247-25 e um CPF com digito verificador valido.
    assert censurar_pii("meu cpf e 529.982.247-25") == "meu cpf e [CPF]"
    assert censurar_pii("cpf 52998224725 ok") == "cpf [CPF] ok"


def test_sequencia_de_11_digitos_que_nao_e_cpf_cai_como_telefone():
    """Decisao do Joao em 03/09/2026: privacidade vence sinal.

    "12345678901" tem digito verificador de CPF invalido, entao nao e CPF --
    mas e indistinguivel de um celular com DDD digitado corrido. Mascarar
    apaga numero de protocolo do texto que alimenta os sinais; nao mascarar
    deixa passar telefone de cliente. A escolha foi mascarar.
    """
    assert censurar_pii("protocolo 12345678901") == "protocolo [TELEFONE]"
    assert censurar_pii("meu fone 11987654321") == "meu fone [TELEFONE]"


def test_mascara_email():
    assert censurar_pii("manda pra joao@exemplo.com") == "manda pra [EMAIL]"


def test_mascara_telefone_com_ddd():
    assert censurar_pii("liga (11) 98765-4321") == "liga [TELEFONE]"
    assert censurar_pii("meu numero e +55 11 98765-4321") == "meu numero e [TELEFONE]"


def test_mascara_cartao_com_luhn_valido():
    # 4539578763621486 passa no Luhn.
    assert censurar_pii("cartao 4539578763621486") == "cartao [CARTAO]"


def test_nao_mascara_numero_longo_que_falha_no_luhn():
    assert censurar_pii("pedido 4539578763621487") == "pedido 4539578763621487"


def test_mascara_endereco_com_tipo_de_logradouro_e_numero():
    assert censurar_pii("moro na Rua das Flores 123") == "moro na [ENDERECO]"
    assert censurar_pii("Av Paulista 1000 hoje") == "[ENDERECO] hoje"


def test_texto_sem_pii_fica_intacto():
    texto = "o atendimento foi pessimo e demorou tres horas"
    assert censurar_pii(texto) == texto


def test_mistura_de_tipos_na_mesma_mensagem():
    resultado = censurar_pii("cpf 529.982.247-25 e email joao@exemplo.com")
    assert resultado == "cpf [CPF] e email [EMAIL]"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pii.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'fraus.seguranca'`

- [ ] **Step 3: Write minimal implementation**

Crie `fraus/seguranca/__init__.py` vazio e `fraus/seguranca/pii.py`:

```python
"""Censura de dado sensivel ANTES de gravar e ANTES de inferir.

O texto original nunca chega ao disco nem ao classificador: `censurar_pii`
roda no ponto de entrada (ver `fraus/api/registro.py` e
`fraus/ingest/csv_driver.py`), sobre o texto de cada mensagem, antes de
`Conversa` existir. Isso resolve os dois riscos de uma vez -- PII em disco e
CPF virando token que o BERTimbau tenta interpretar.

POR QUE checksum onde da para ter: numero de pedido, protocolo e valor sao os
tokens mais comuns de um chat de atendimento, e apagar todos eles empobrece o
texto que alimenta os sinais -- o mesmo raciocinio que `fraus/sinais/estilo.py`
ja documenta para digito puro. CPF e cartao tem digito verificador, entao para
esses dois a duvida nao existe: ou o numero fecha a conta ou nao e um deles.

TELEFONE NAO TEM CHECKSUM, e ai a duvida e real: "12345678901" e um protocolo
ou um celular com DDD digitado corrido? Sao indistinguiveis. A decisao do Joao
em 03/09/2026 foi MASCARAR -- privacidade vence sinal, e um protocolo perdido
custa menos que um telefone vazado. E limitacao declarada, nao descuido.

LIMITACAO DECLARADA: endereco e heuristica de "tipo de logradouro + numero" e
tem falso-negativo alto (endereco sem essas palavras nao e pego). Nome
proprio sozinho NAO e coberto: exigiria NER, que e modelo a mais e esta fora
do escopo. O que esta aqui e o que se identifica por padrao deterministico.
"""

import re

MARCADORES = {
    "cpf": "[CPF]",
    "email": "[EMAIL]",
    "telefone": "[TELEFONE]",
    "cartao": "[CARTAO]",
    "endereco": "[ENDERECO]",
}

# Formato do CPF: 11 digitos, com ou sem os separadores usuais. A validacao
# do digito verificador acontece depois, em `_cpf_valido`.
_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# Telefone BR: +55 opcional, DDD opcional entre parenteses, 8 ou 9 digitos.
#
# `(?<!\d)` e `(?!\d)` NAO sao decoracao, e `\b` no lugar deles nao serve:
# digito e caractere de palavra, entao nao existe `\b` DENTRO de uma corrida
# de digitos, e o padrao casava no meio de um numero maior. Um cartao de 16
# digitos que falha no Luhn (numero de pedido longo, portanto) tinha os 11
# ultimos digitos comidos como se fossem telefone, saindo como
# "pedido 45395[TELEFONE]" -- mascaramento parcial, que e o pior dos dois
# mundos: nao protege o que era PII nem preserva o que nao era.
_TELEFONE = re.compile(r"(?<!\d)(?:\+55\s?)?(?:\(\d{2}\)|\d{2})[\s-]?\d{4,5}-?\d{4}(?!\d)")
# Cartao: 13 a 19 digitos, com ou sem espaco/hifen a cada quatro.
_CARTAO = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")
_ENDERECO = re.compile(
    r"\b(?:rua|av|avenida|alameda|travessa|rodovia|praca)\b[^,.;\n]{0,60}?\d+",
    re.IGNORECASE,
)


def _so_digitos(texto: str) -> str:
    return "".join(c for c in texto if c.isdigit())


def _cpf_valido(candidato: str) -> bool:
    """Digito verificador do CPF. Rejeita tambem as 10 sequencias repetidas."""
    digitos = _so_digitos(candidato)
    if len(digitos) != 11 or len(set(digitos)) == 1:
        return False
    for tamanho in (9, 10):
        soma = sum(
            int(digitos[i]) * (tamanho + 1 - i) for i in range(tamanho)
        )
        resto = (soma * 10) % 11
        esperado = 0 if resto == 10 else resto
        if esperado != int(digitos[tamanho]):
            return False
    return True


def _luhn_valido(candidato: str) -> bool:
    """Algoritmo de Luhn -- o mesmo que a bandeira usa para recusar digitacao."""
    digitos = [int(c) for c in _so_digitos(candidato)]
    if len(digitos) < 13:
        return False
    soma = 0
    for posicao, digito in enumerate(reversed(digitos)):
        if posicao % 2 == 1:
            digito *= 2
            if digito > 9:
                digito -= 9
        soma += digito
    return soma % 10 == 0


def censurar_pii(texto: str) -> str:
    """Mascara CPF, e-mail, telefone, cartao e endereco. Deterministico.

    A ORDEM importa: e-mail vem antes de telefone e cartao porque um e-mail
    pode conter digitos que o padrao de telefone casaria por dentro; cartao
    vem antes de telefone porque o padrao de cartao e mais longo e mais
    especifico (Luhn), e telefone casaria um pedaco dele.
    """
    if not texto:
        return texto

    texto = _EMAIL.sub(MARCADORES["email"], texto)
    texto = _CPF.sub(
        lambda m: MARCADORES["cpf"] if _cpf_valido(m.group()) else m.group(), texto
    )
    texto = _CARTAO.sub(
        lambda m: MARCADORES["cartao"] if _luhn_valido(m.group()) else m.group(),
        texto,
    )
    texto = _TELEFONE.sub(MARCADORES["telefone"], texto)
    texto = _ENDERECO.sub(MARCADORES["endereco"], texto)
    return texto
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_pii.py -v`
Expected: PASS — os 9 testes.

Se `test_mascara_cpf_valido` falhar porque `_CARTAO` ou `_TELEFONE` comeu o CPF já mascarado, confira que `[CPF]` não tem dígito (não tem) e que a ordem das substituições é a do código acima.

- [ ] **Step 5: Commit**

```bash
git add fraus/seguranca/ tests/test_pii.py
git commit -m "feat(seguranca): censura de PII por regex mais digito verificador"
```

---

### Task 2: Censurar na entrada da API

**Files:**
- Modify: `fraus/api/registro.py` (função `registrar_conversa`, montagem de `Conversa`)
- Test: `tests/test_pii_integracao.py`

**Interfaces:**
- Consumes: `censurar_pii(texto: str) -> str` da Task 1; `registrar_conversa(ctx, pedido, fonte) -> dict` já existente.
- Produces: garantia de que `Conversa.mensagens[*].texto` já chega mascarada a todo o resto do sistema.

- [ ] **Step 1: Write the failing test**

Crie `tests/test_pii_integracao.py`. Este teste monta um `PedidoIngestao` com PII e verifica que a `Conversa` construída dentro de `registrar_conversa` já saiu mascarada — checando pelo banco, que é onde o dado persistiria:

```python
from datetime import datetime, timezone

from fraus.api.esquemas import PedidoIngestao


def test_registrar_conversa_grava_texto_mascarado(ctx_de_teste):
    """PII nao pode chegar ao banco. O texto gravado ja vem mascarado."""
    from fraus.api.registro import registrar_conversa

    base = datetime(2026, 9, 3, 10, 0, 0, tzinfo=timezone.utc)
    pedido = PedidoIngestao(
        id="c-pii",
        encerrada_em=base,
        escalou_para_humano=False,
        mensagens=[
            {
                "autor": "cliente",
                "texto": "meu cpf e 529.982.247-25 e o email joao@exemplo.com",
                "enviada_em": base,
            }
        ],
    )
    registrar_conversa(ctx_de_teste, pedido, {"canal": "csv", "nome": "teste"})

    conversa, _score = ctx_de_teste.banco.todas()[0]
    texto = conversa.mensagens[0].texto
    assert "529.982.247-25" not in texto
    assert "joao@exemplo.com" not in texto
    assert "[CPF]" in texto
    assert "[EMAIL]" in texto
```

`ctx_de_teste` é uma fixture. Antes de escrever esta, procure em `tests/conftest.py` uma fixture que já monte um `Contexto` com banco temporário e motor dublê — os testes de `tests/test_api.py` certamente têm uma. **Reuse a que existir**; só crie fixture nova se não houver nenhuma, e nesse caso siga exatamente o padrão de montagem que `tests/test_api.py` usa.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pii_integracao.py -v`
Expected: FAIL — `assert "529.982.247-25" not in texto` falha, porque hoje o texto é gravado cru.

- [ ] **Step 3: Write minimal implementation**

Em `fraus/api/registro.py`, importe a censura e aplique na montagem das mensagens. Substitua o bloco `mensagens=sorted(...)` dentro do `try` por uma versão que mascara antes:

```python
from fraus.seguranca.pii import censurar_pii
```

e, dentro de `registrar_conversa`, antes de montar `Conversa`:

```python
    # PII morre AQUI, no ponto de entrada compartilhado pelas duas rotas --
    # nao mais adiante. Depois deste ponto nao existe texto cru no processo:
    # nem para o banco, nem para os sete sinais, nem para a tela. Este e o
    # mesmo motivo pelo qual o miolo de derivacao mora neste modulo: uma
    # segunda copia da regra em `/ingestao` e no webhook divergiria, e a que
    # envelhece e sempre a que ninguem olha.
    mensagens_limpas = [
        mensagem.model_copy(update={"texto": censurar_pii(mensagem.texto)})
        for mensagem in pedido.mensagens
    ]
```

e troque `mensagens=sorted(pedido.mensagens, key=lambda m: m.enviada_em)` por
`mensagens=sorted(mensagens_limpas, key=lambda m: m.enviada_em)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_pii_integracao.py tests/test_api.py -v`
Expected: PASS — o teste novo e a suíte de API inteira (nenhuma regressão).

- [ ] **Step 5: Commit**

```bash
git add fraus/api/registro.py tests/test_pii_integracao.py
git commit -m "feat(api): mascara PII antes de montar a conversa na entrada"
```

---

### Task 3: Censurar na ingestão de CSV

**Files:**
- Modify: `fraus/ingest/csv_driver.py:88-94` (montagem de `Mensagem` em `carregar_linhas`)
- Test: `tests/test_pii_integracao.py` (adiciona teste ao arquivo da Task 2)

**Interfaces:**
- Consumes: `censurar_pii(texto: str) -> str` da Task 1.
- Produces: `carregar_linhas`/`carregar_csv`/`carregar_texto` devolvendo conversas já mascaradas.

- [ ] **Step 1: Write the failing test**

Acrescente a `tests/test_pii_integracao.py`:

```python
def test_csv_driver_mascara_pii_na_leitura():
    """A outra porta de entrada. Mesma regra, senao ela vira o furo."""
    import io

    from fraus.ingest.csv_driver import carregar_linhas

    conteudo = (
        "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
        "c1,csv,cliente,meu cpf e 529.982.247-25,2026-09-03T10:00:00+00:00,false\n"
    )
    resultado = carregar_linhas(io.StringIO(conteudo, newline=""))

    texto = resultado.conversas[0].mensagens[0].texto
    assert "529.982.247-25" not in texto
    assert "[CPF]" in texto
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pii_integracao.py::test_csv_driver_mascara_pii_na_leitura -v`
Expected: FAIL — `assert "529.982.247-25" not in texto`.

- [ ] **Step 3: Write minimal implementation**

Em `fraus/ingest/csv_driver.py`, importe `from fraus.seguranca.pii import censurar_pii` e envolva o texto na montagem da `Mensagem`:

```python
                texto=censurar_pii(_exigir(linha, "texto", numero_linha)),
```

Acrescente ao docstring do módulo, no fim:

```
O texto de cada mensagem passa por `censurar_pii` AQUI, na leitura, e nao
depois: esta e a segunda porta de entrada do sistema (a outra e
`fraus/api/registro.py`), e uma porta sem a censura torna a outra inutil.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_pii_integracao.py tests/test_ingest.py -v`
Expected: PASS. Se algum teste existente de ingestão comparar texto literal que contenha algo parecido com PII (telefone, e-mail), ele vai falhar legitimamente — atualize a expectativa do teste para o texto mascarado, não relaxe a censura.

- [ ] **Step 5: Commit**

```bash
git add fraus/ingest/csv_driver.py tests/test_pii_integracao.py
git commit -m "feat(ingest): mascara PII na leitura do CSV"
```

---

## Frente 2 — Sinal de incongruência

### Task 4: Módulo de incongruência com as 5 features

**Files:**
- Create: `fraus/sinais/incongruencia.py`
- Test: `tests/test_sinal_incongruencia.py`

**Interfaces:**
- Consumes: `anotar_texto(texto, curadoria) -> list[tuple[str, int, bool]]` de `fraus/sinais/lexico.py`; `emojis_com_posicao(texto) -> list[tuple[str, float]]` e `score_do_emoji(caractere, curadoria) -> float` de `fraus/sinais/emoji.py`; `Curadoria`/`CURADORIA_VAZIA` de `fraus/sinais/curadoria.py`.
- Produces: `features_incongruencia(conversa: Conversa, curadoria: Curadoria | None = None) -> dict[str, float]` com exatamente as 5 chaves `incongruencia_polaridade`, `incongruencia_emoji_texto`, `incongruencia_marcador_contraste`, `incongruencia_hiperbole`, `incongruencia_aspas_ironicas`. Consumida pela Task 5.

- [ ] **Step 1: Write the failing test**

Crie `tests/test_sinal_incongruencia.py`:

```python
from datetime import datetime, timezone

from fraus.modelos import Conversa, Mensagem
from fraus.sinais.incongruencia import features_incongruencia

CHAVES = {
    "incongruencia_polaridade",
    "incongruencia_emoji_texto",
    "incongruencia_marcador_contraste",
    "incongruencia_hiperbole",
    "incongruencia_aspas_ironicas",
}


def _conversa(textos: list[str], autor: str = "cliente") -> Conversa:
    base = datetime(2026, 9, 3, 10, 0, 0, tzinfo=timezone.utc)
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=base,
        mensagens=[
            Mensagem(autor=autor, texto=t, enviada_em=base) for t in textos
        ],
    )


def test_devolve_exatamente_as_cinco_chaves():
    assert set(features_incongruencia(_conversa(["oi"]))) == CHAVES


def test_conversa_sem_fala_do_cliente_zera_tudo():
    """Ausencia de medida, nao medida zero -- quem distingue e o score None."""
    features = features_incongruencia(_conversa(["posso ajudar?"], autor="bot"))
    assert set(features) == CHAVES
    assert all(valor == 0.0 for valor in features.values())


def test_polaridade_mista_na_mesma_mensagem_marca_incongruencia():
    misto = features_incongruencia(_conversa(["otimo atendimento, pessimo servico"]))
    so_negativo = features_incongruencia(_conversa(["pessimo servico horrivel"]))
    assert misto["incongruencia_polaridade"] > so_negativo["incongruencia_polaridade"]


def test_texto_so_positivo_nao_marca_incongruencia_de_polaridade():
    features = features_incongruencia(_conversa(["otimo atendimento, excelente"]))
    assert features["incongruencia_polaridade"] == 0.0


def test_emoji_positivo_com_texto_negativo_marca_contraste():
    contraste = features_incongruencia(_conversa(["que servico pessimo 😊"]))
    alinhado = features_incongruencia(_conversa(["que servico pessimo 😡"]))
    assert contraste["incongruencia_emoji_texto"] > alinhado["incongruencia_emoji_texto"]


def test_marcador_de_contraste_entre_polaridades_opostas():
    com_marcador = features_incongruencia(
        _conversa(["o atendimento foi otimo, mas o servico foi pessimo"])
    )
    sem_marcador = features_incongruencia(_conversa(["o servico foi pessimo"]))
    assert com_marcador["incongruencia_marcador_contraste"] == 1.0
    assert sem_marcador["incongruencia_marcador_contraste"] == 0.0


def test_hiperbole_exige_intensificador_junto_de_polaridade():
    com = features_incongruencia(_conversa(["atendimento extremamente otimo"]))
    sem = features_incongruencia(_conversa(["atendimento otimo"]))
    assert com["incongruencia_hiperbole"] > sem["incongruencia_hiperbole"]
    assert sem["incongruencia_hiperbole"] == 0.0


def test_aspas_ironicas_com_polaridade_oposta_ao_resto():
    ironico = features_incongruencia(
        _conversa(['que "otimo" atendimento, servico pessimo e horrivel'])
    )
    assert ironico["incongruencia_aspas_ironicas"] == 1.0


def test_aspas_sem_conflito_de_polaridade_nao_marcam():
    features = features_incongruencia(_conversa(['ele disse "bom dia" e ajudou']))
    assert features["incongruencia_aspas_ironicas"] == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sinal_incongruencia.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'fraus.sinais.incongruencia'`

- [ ] **Step 3: Write minimal implementation**

Crie `fraus/sinais/incongruencia.py`:

```python
"""Sinal de incongruencia: o CONFLITO interno do texto, nao a polaridade dele.

Ironia e uma relacao entre o que o texto DIZ e o que ele SIGNIFICA, e a marca
computavel dessa relacao e a incongruencia -- polaridade que se contradiz
dentro da mesma fala, exagero implausivel, aspas que negam a palavra que
cercam. A literatura e consistente nisso: Riloff et al. (EMNLP 2013) definem
sarcasmo como contraste entre sentimento positivo e situacao negativa, e
Joshi et al. (ACL 2015) medem +8% F1 sobre features lexicas e pragmaticas so
com incongruencia explicita. Ver a bibliografia da spec de 03/09/2026.

POR QUE UM MODULO SEPARADO de `ironia.py`: aquele modulo E o classificador
BERTimbau -- carrega peso, roda `torch`, falha alto se o artefato nao existe.
Este nao carrega modelo nenhum: e lexico e regex, reusando `lexico.py` e
`emoji.py`. Juntar os dois faria a heuristica deterministica ficar refem do
artefato treinado, e um dos dois nao poderia rodar sem o outro sem motivo.

POR QUE COMPLEMENTA em vez de substituir: o classificador de ironia foi
treinado no IDPT 2021 (tweet e noticia), e a transferencia para atendimento
nao e verificada -- a propria dashboard ja avisa que ele erra 6 em 10 falas
sinceras. Estas cinco features tem procedencia independente dele: quando as
duas leituras concordam, a evidencia soma; quando discordam, a discordancia e
informacao, e quem pondera as duas e o fusor, com peso aprendido.

TODAS as cinco leem SO a fala do cliente, coerente com os demais sinais.
"""

import re

from fraus.modelos import Conversa
from fraus.sinais.curadoria import CURADORIA_VAZIA, Curadoria
from fraus.sinais.emoji import emojis_com_posicao, score_do_emoji
from fraus.sinais.lexico import anotar_texto

CHAVES = (
    "incongruencia_polaridade",
    "incongruencia_emoji_texto",
    "incongruencia_marcador_contraste",
    "incongruencia_hiperbole",
    "incongruencia_aspas_ironicas",
)

# Conectivos de contraste do portugues. Lista curta de proposito, pelo mesmo
# motivo que `NEGACOES` em `lexico.py` e curta: marcador duvidoso marca
# contraste que nao existe, e ruido correlacionado com fala normal e pior que
# feature ausente. Fonte: Portuguese Lexicon of Discourse Markers (CLUL).
MARCADORES_CONTRASTE = (
    "mas", "porem", "porém", "contudo", "todavia", "entretanto",
    "so que", "só que", "mesmo assim",
)

# Intensificadores que, junto de polaridade extrema, formam hiperbole
# (Troiano & Strapparava, EMNLP 2018; Burgers et al., 2012). "atendimento
# EXTREMAMENTE otimo, so esperei 3 horas" e o caso de manual.
INTENSIFICADORES = (
    "muito", "super", "extremamente", "totalmente", "completamente",
    "absurdamente", "demais",
)

# Limiar de emoji para "tem polaridade" -- o mesmo de `emoji.py`, e de
# proposito: duas reguas diferentes para a mesma pergunta ("este emoji e
# positivo?") divergiriam em silencio na fronteira.
LIMIAR_EMOJI = 0.1

_TOKEN = re.compile(r"[0-9a-zà-ÿA-ZÀ-Ý\-]+")
# Aspas retas e curvas: o cliente digita as duas, e o teclado do celular
# troca uma pela outra sem avisar.
_ENTRE_ASPAS = re.compile(r'["“”\']([^"“”\']{1,40})["“”\']')


def _polaridades(texto: str, curadoria: Curadoria) -> list[int]:
    """Polaridades dos termos do lexicon achados, ja com negacao aplicada."""
    return [p for _, p, _ in anotar_texto(texto, curadoria) if p != 0]


def _incongruencia_polaridade(texto: str, curadoria: Curadoria) -> float:
    """F1 -- positivo e negativo convivendo na MESMA fala (Riloff 2013).

    A razao e `min / total` e nao a contagem crua: uma fala com 1 positivo e 1
    negativo e mais incongruente que uma com 1 positivo e 9 negativos, que e
    so uma reclamacao com uma ressalva. O maximo (0,5) e o empate perfeito.
    """
    polaridades = _polaridades(texto, curadoria)
    positivos = sum(1 for p in polaridades if p > 0)
    negativos = sum(1 for p in polaridades if p < 0)
    total = positivos + negativos
    if total == 0:
        return 0.0
    return min(positivos, negativos) / total


def _contraste_emoji_texto(texto: str, curadoria: Curadoria) -> float:
    """F2 -- o emoji diz uma coisa e o texto diz o contrario.

    So conta quando as DUAS pontas tem polaridade: emoji neutro ou texto sem
    termo do lexicon nao e contraste, e um alinhamento com um lado ausente.
    """
    polaridades = _polaridades(texto, curadoria)
    if not polaridades:
        return 0.0
    scores = [score_do_emoji(c, curadoria) for c, _ in emojis_com_posicao(texto)]
    com_polaridade = [s for s in scores if abs(s) > LIMIAR_EMOJI]
    if not com_polaridade:
        return 0.0

    media_texto = sum(polaridades) / len(polaridades)
    media_emoji = sum(com_polaridade) / len(com_polaridade)
    # Sinais opostos: o produto e negativo. A magnitude e quanto as duas
    # pontas se afastam, limitada a 1 para nao deixar uma fala extrema
    # dominar a media da conversa.
    if media_texto * media_emoji >= 0:
        return 0.0
    return min(1.0, abs(media_texto - media_emoji) / 2)


def _marcador_contraste(texto: str, curadoria: Curadoria) -> bool:
    """F3 -- conectivo de contraste separando polaridades opostas.

    O conectivo SOZINHO nao basta: "mas" e uma das palavras mais comuns do
    portugues e aparece em fala perfeitamente sincera. O que marca e o
    conectivo com polaridade oposta de cada lado dele.
    """
    minusculo = texto.lower()
    for marcador in MARCADORES_CONTRASTE:
        posicao = minusculo.find(f" {marcador} ")
        if posicao == -1:
            continue
        antes = _polaridades(texto[:posicao], curadoria)
        depois = _polaridades(texto[posicao + len(marcador) + 2:], curadoria)
        if not antes or not depois:
            continue
        if (sum(antes) > 0) != (sum(depois) > 0):
            return True
    return False


def _hiperbole(texto: str, curadoria: Curadoria) -> float:
    """F4 -- intensificador colado em termo de polaridade.

    Fracao dos termos polares da fala que vem intensificados. Elogio
    intensificado e o formato mais comum da ironia de atendimento ("otimo
    demais"), e tambem o da satisfacao genuina -- por isso e feature com peso
    aprendido pelo fusor, nao regra de decisao.
    """
    tokens = _TOKEN.findall(texto.lower())
    if not tokens:
        return 0.0
    polares = 0
    intensificados = 0
    for indice, token in enumerate(tokens):
        from fraus.sinais.lexico import polaridade_do_termo

        if polaridade_do_termo(token, curadoria) == 0:
            continue
        polares += 1
        vizinhos = tokens[max(0, indice - 2):indice]
        if any(v in INTENSIFICADORES for v in vizinhos):
            intensificados += 1
    if polares == 0:
        return 0.0
    return intensificados / polares


def _aspas_ironicas(texto: str, curadoria: Curadoria) -> bool:
    """F5 -- palavra entre aspas com polaridade oposta ao resto da fala.

    As "scare quotes" (Burgers et al., 2012): o cliente marca tipograficamente
    a palavra de que ele discorda. `"otimo" atendimento, tudo pessimo` e o
    caso. Aspas sem conflito de polaridade sao citacao, nao deboche.
    """
    for achado in _ENTRE_ASPAS.finditer(texto):
        dentro = _polaridades(achado.group(1), curadoria)
        if not dentro:
            continue
        fora = _polaridades(
            texto[:achado.start()] + " " + texto[achado.end():], curadoria
        )
        if not fora:
            continue
        if (sum(dentro) > 0) != (sum(fora) > 0):
            return True
    return False


def features_incongruencia(
    conversa: Conversa, curadoria: Curadoria | None = None
) -> dict[str, float]:
    """As cinco features de incongruencia, media sobre as falas do cliente.

    Conversa sem fala do cliente devolve as cinco zeradas -- e ausencia de
    medida, e quem distingue "nao mediu" de "mediu e deu zero" e o
    `score: None` la em cima, nunca esta funcao (invariante 2).
    """
    curadoria = curadoria or CURADORIA_VAZIA
    textos = [m.texto for m in conversa.mensagens_cliente]
    if not textos:
        return {chave: 0.0 for chave in CHAVES}

    total = len(textos)
    return {
        "incongruencia_polaridade": sum(
            _incongruencia_polaridade(t, curadoria) for t in textos
        ) / total,
        "incongruencia_emoji_texto": sum(
            _contraste_emoji_texto(t, curadoria) for t in textos
        ) / total,
        "incongruencia_marcador_contraste": sum(
            1 for t in textos if _marcador_contraste(t, curadoria)
        ) / total,
        "incongruencia_hiperbole": sum(_hiperbole(t, curadoria) for t in textos) / total,
        "incongruencia_aspas_ironicas": sum(
            1 for t in textos if _aspas_ironicas(t, curadoria)
        ) / total,
    }
```

Mova o `from fraus.sinais.lexico import polaridade_do_termo` de dentro de `_hiperbole` para o topo do arquivo, junto de `anotar_texto` — o import dentro da função está ali só para deixar claro de onde vem; import no meio de laço é desperdício.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_sinal_incongruencia.py -v`
Expected: PASS — os 9 testes.

Se `test_polaridade_mista...` ou `test_hiperbole...` falhar, confirme no shell quais termos o SentiLex de fato reconhece antes de mudar o código: `uv run python -c "from fraus.sinais.lexico import polaridade_do_termo as p; print(p('otimo'), p('pessimo'), p('horrivel'), p('excelente'))"`. Se algum vier 0, troque a palavra do TESTE por uma que o lexicon conheça — não relaxe a asserção.

- [ ] **Step 5: Commit**

```bash
git add fraus/sinais/incongruencia.py tests/test_sinal_incongruencia.py
git commit -m "feat(sinais): cinco features de incongruencia complementando a ironia"
```

---

### Task 5: Ligar incongruência ao vetor de features (35 → 40)

**Files:**
- Modify: `fraus/fusor.py:34-77` (`NOMES_FEATURES`), `fraus/fusor.py:107-136` (`montar_features`)
- Test: `tests/test_fusor.py`

**Interfaces:**
- Consumes: `features_incongruencia(conversa, curadoria)` da Task 4.
- Produces: `NOMES_FEATURES` com 40 nomes; `montar_features(conversa, classificador, classificador_emocao, classificador_ironia, curadoria=None)` devolvendo as 40 chaves. Assinatura **inalterada** — incongruência não precisa de classificador.

- [ ] **Step 1: Write the failing test**

Acrescente a `tests/test_fusor.py`:

```python
def test_contrato_tem_quarenta_features_com_incongruencia():
    from fraus.fusor import NOMES_FEATURES
    from fraus.sinais.incongruencia import CHAVES

    assert len(NOMES_FEATURES) == 40
    assert len(set(NOMES_FEATURES)) == 40, "nome de feature duplicado"
    for chave in CHAVES:
        assert chave in NOMES_FEATURES
```

E um teste que prova que `montar_features` entrega exatamente o contrato. Antes de escrevê-lo, abra `tests/test_fusor.py` e **reuse os dublês de classificador que já existem lá** (os testes atuais de `montar_features` já precisam de três classificadores). Seguindo o padrão que estiver no arquivo:

```python
def test_montar_features_entrega_o_contrato_completo():
    from fraus.fusor import NOMES_FEATURES, montar_features

    features = montar_features(
        _conversa_de_teste(),
        _classificador_dubl(),
        _emocao_dubl(),
        _ironia_dubl(),
    )
    assert set(features) == set(NOMES_FEATURES)
```

(Substitua `_conversa_de_teste`/`_classificador_dubl`/`_emocao_dubl`/`_ironia_dubl` pelos nomes reais dos helpers já presentes em `tests/test_fusor.py`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_fusor.py -v`
Expected: FAIL — `assert len(NOMES_FEATURES) == 40` recebe 35, e `set(features) == set(NOMES_FEATURES)` acusa as 5 chaves faltando.

- [ ] **Step 3: Write minimal implementation**

Em `fraus/fusor.py`:

1. Import novo, junto dos outros sinais:
```python
from fraus.sinais.incongruencia import features_incongruencia
```

2. Acrescente o bloco ao fim de `NOMES_FEATURES`, depois de `estilo`:
```python
    # incongruencia (5)
    "incongruencia_polaridade",
    "incongruencia_emoji_texto",
    "incongruencia_marcador_contraste",
    "incongruencia_hiperbole",
    "incongruencia_aspas_ironicas",
]
```

**No fim da lista e não no meio, de propósito:** a ordem é o contrato que o fusor treinado espera, e inserir no meio desloca todos os índices seguintes. O fusor vai ser retreinado nesta mesma leva (Task 6), então a ordem antiga não sobrevive de qualquer jeito — mas anexar no fim mantém o diff legível e o histórico dos 35 nomes intacto.

3. Atualize o comentário de cabeçalho da lista, acrescentando ao fim:
```
# Subiu de 35 para 40 em 03/09/2026: a familia `incongruencia_*` entrou para
# complementar o classificador de ironia, cuja transferencia de dominio
# (IDPT 2021, tweet e noticia) nunca foi verificada em atendimento. Ver a
# spec de 03/09/2026 e a bibliografia dela.
```

4. Em `montar_features`, acrescente a chamada ao dict devolvido:
```python
        **features_incongruencia(conversa, curadoria),
```

5. Atualize o docstring de `montar_features`: onde diz "o contrato continua de 35 chaves (invariante 9)", troque para 40, e acrescente que `curadoria` agora alcança **três** famílias (`lexico_*`, `emoji_*` e `incongruencia_*`), porque a incongruência lê os dois léxicos por dentro.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_fusor.py -v`
Expected: PASS.

Depois rode a suíte inteira: `uv run pytest -q`. Testes que fixam `35` vão falhar — é a mudança de contrato, e o número tem que ser atualizado em cada um deles (procure com `grep -rn "35" tests/ --include=*.py` e avalie caso a caso; nem todo `35` é o contrato de features).

- [ ] **Step 5: Commit**

```bash
git add fraus/fusor.py tests/
git commit -m "feat(fusor): contrato sobe para 40 features com a familia incongruencia"
```

---

### Task 6: Guarda contra vazamento de rotulo nas features novas

**Files:**
- Modify: `tests/test_simulador.py`

**Interfaces:**
- Consumes: `features_incongruencia` e `CHAVES` da Task 4; `FRASES_POR_ROTULO`, `gerar_lote` de `fraus/ingest/simulador.py`.
- Produces: nada consumido por outras tasks -- e uma guarda.

**Por que esta task existe:** o invariante 10 do projeto existe porque uma faixa
de latencia disjunta por classe fez o primeiro fusor marcar 99,3% lendo so o
relogio, com o BERTimbau apagado. Feature nova entra no vetor sob suspeita: se
`incongruencia_*` separar as classes sozinha no corpus sintetico, o retreino da
Task 7 aprende a ler a feature em vez do texto e ninguem percebe.

**IMPORTANTE -- siga o padrao que ja existe.** `tests/test_simulador.py` ja faz
esta guarda para a familia `estilo_*`, e faz melhor do que o rascunho anterior
desta task. Leia os testes existentes (`agrupado_por_rotulo`,
`test_estilo_varia_dentro_de_cada_rotulo`,
`test_distribuicoes_de_estilo_se_sobrepoem_entre_rotulos`) e ESPELHE a forma
deles. Nao invente uma terceira maneira de fazer a mesma pergunta.

A API real do simulador:
```python
from fraus.ingest.simulador import FRASES_POR_ROTULO, gerar_lote
# gerar_lote(frases_por_rotulo: dict[int, list[str]], quantidade: int, semente: int)
#   -> list[tuple[Conversa, int]]     # (conversa, rotulo)
```

Duas perguntas diferentes, ambas importam:

1. **A feature varia dentro de cada rotulo?** Feature constante no treino nasce
   com peso zero -- e o bug do emoji na v1, ja documentado no arquivo.
2. **As distribuicoes se sobrepoem entre rotulos?** Disjuncao e o vazamento.

- [ ] **Step 1: Write the test**

Acrescente a `tests/test_simulador.py`, no registro do arquivo:

```python
@pytest.fixture(scope="module")
def incongruencia_por_rotulo() -> dict[int, list[dict]]:
    """Mesmo lote e mesma semente da guarda de estilo -- comparavel de proposito."""
    agrupado: dict[int, list[dict]] = {0: [], 1: [], 2: []}
    for conversa, rotulo in gerar_lote(FRASES_POR_ROTULO, 180, semente=7):
        agrupado[rotulo].append(features_incongruencia(conversa))
    return agrupado


def test_nenhuma_incongruencia_separa_as_classes_sozinha(incongruencia_por_rotulo):
    """Invariante 10: corpus de treino nao entrega o rotulo.

    Disjuncao = o maximo de uma classe abaixo do minimo de outra. Se isto
    falhar, a feature acusada NAO pode entrar no vetor como esta, e a cura e
    mexer no CORPUS (como se fez com a latencia log-normal), NUNCA afrouxar
    esta asercao.
    """
    for chave in CHAVES_INCONGRUENCIA:
        faixas = {
            rotulo: (
                min(linha[chave] for linha in linhas),
                max(linha[chave] for linha in linhas),
            )
            for rotulo, linhas in incongruencia_por_rotulo.items()
        }
        for a in sorted(faixas):
            for b in sorted(faixas):
                if a >= b:
                    continue
                assert not (faixas[a][1] < faixas[b][0]), (
                    f"{chave} separa {a} de {b}: {faixas[a]} nao encosta em {faixas[b]}"
                )
                assert not (faixas[b][1] < faixas[a][0]), (
                    f"{chave} separa {b} de {a}: {faixas[b]} nao encosta em {faixas[a]}"
                )
```

`CHAVES_INCONGRUENCIA` vem de `from fraus.sinais.incongruencia import CHAVES`.
Use o nome que couber no registro do arquivo (ele ja tem `CHAVES_ESTILO`).

- [ ] **Step 2: Rodar e INTERPRETAR**

Run: `uv run pytest tests/test_simulador.py -v -k incongruencia`

Tres desfechos, e o que fazer em cada:

- **PASSA:** as features se sobrepoem. Siga para o Step 3.
- **FALHA por disjuncao:** achado REAL, nao teste ruim. **PARE e reporte** qual
  feature separou quais rotulos e com que faixas. Nao afrouxe a asercao, nao
  mexa no codigo pra fazer passar, e nao siga adiante.
- **Faixa degenerada `(0.0, 0.0)` em todas as classes:** feature constante no
  sintetico. NAO e vazamento -- e o oposto, e nasce com peso zero. A asercao
  nao dispara. Mas ANOTE quais features ficaram constantes: e limitacao
  declarada que a Task 7 registra em `docs/treinamento.md`.

- [ ] **Step 3: Levantar a distribuicao real**

A Task 7 precisa desta saida no relatorio:

```bash
uv run python -c "
from fraus.ingest.simulador import FRASES_POR_ROTULO, gerar_lote
from fraus.sinais.incongruencia import CHAVES, features_incongruencia
import statistics
por_rotulo = {0: [], 1: [], 2: []}
for conversa, rotulo in gerar_lote(FRASES_POR_ROTULO, 180, semente=7):
    por_rotulo[rotulo].append(features_incongruencia(conversa))
for chave in CHAVES:
    partes = []
    for rotulo, linhas in sorted(por_rotulo.items()):
        v = [l[chave] for l in linhas]
        partes.append(f'{rotulo}: med={statistics.mean(v):.3f} dp={statistics.pstdev(v):.3f} max={max(v):.3f}')
    print(f'{chave:38} ' + ' | '.join(partes))
"
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_simulador.py
git commit -m "test(incongruencia): guarda contra vazamento de rotulo nas features novas"
```

### Task 7: Documentar o retreino do fusor

**Files:**
- Modify: `docs/treinamento.md`
- Modify: `notebooks/` — o notebook que treina o fusor (identifique qual; provavelmente `02_*`)

**Interfaces:**
- Consumes: `NOMES_FEATURES` de 40 (Task 5).
- Produces: procedimento documentado. **A execução do notebook é manual, no Colab, pelo João — este plano não a executa.**

- [ ] **Step 1: Localizar e ler o notebook do fusor**

Run: `ls notebooks/` e abra o que treina o fusor. Confirme se ele importa `NOMES_FEATURES`/`montar_features` do pacote (nesse caso as 40 features entram sozinhas) ou se repete a lista de nomes por dentro (nesse caso a lista precisa ser atualizada lá também — e isso é uma duplicação a apontar).

- [ ] **Step 2: Atualizar o notebook se ele repetir a lista**

Se o notebook tiver a lista de features própria, troque por `from fraus.fusor import NOMES_FEATURES, montar_features`. Duas listas de nomes de feature divergem, e a divergência aqui produz um fusor treinado com pesos trocados de posição — que não levanta erro nenhum, só pontua errado.

- [ ] **Step 3: Documentar o procedimento em `docs/treinamento.md`**

Acrescente uma seção:

```markdown
## Retreino do fusor apos as features de incongruencia (03/09/2026)

O contrato subiu de 35 para 40 features: a familia `incongruencia_*` entrou
em `NOMES_FEATURES`. O fusor salvo em `modelos/` foi treinado com 35 e
`vetorizar` agora produz 40 -- ele NAO serve mais, e carregar o antigo com o
vetor novo levanta erro de dimensao no `StandardScaler` (o que e o
comportamento certo: falha alta e explicita, invariante 7).

Passos, no Colab:

1. Rodar o notebook do fusor sem alterar o corpus. Ele importa
   `NOMES_FEATURES` e `montar_features` do pacote, entao as cinco features
   novas entram sozinhas.
2. Conferir a acuracia contra a do fusor de 35 features. **Acuracia alta
   demais e sintoma, nao vitoria** -- se saltar muito acima do valor
   anterior, suspeite de vazamento antes de comemorar, e rode
   `uv run pytest tests/test_incongruencia_nao_vaza_rotulo.py`.
3. Conferir os coeficientes das cinco features novas em
   `Fusor.eixo_global()`. Feature constante no corpus de treino nasce com
   peso proximo de zero -- e o caso esperado de `incongruencia_emoji_texto`
   e `incongruencia_aspas_ironicas`, porque o simulador nao emite emoji nem
   aspas ironicas. Peso zero por ausencia de exemplo e limitacao declarada,
   nao defeito.
4. Copiar o artefato para `modelos/` e rodar `uv run pytest -q` local.
```

- [ ] **Step 4: Commit**

```bash
git add docs/treinamento.md notebooks/
git commit -m "docs(treinamento): procedimento de retreino do fusor com 40 features"
```

---

## Frente 3 — Leitura de estilo e limiares

### Task 8: Revisão dos limiares de estilo

**Files:**
- Modify: `fraus/sinais/estilo.py:176-187` (`MINIMO_CAIXA_ALTA`, `MINIMO_ALONGAMENTO`, `PONTUACAO_ENFATICA`)
- Modify: `tests/test_sinal_estilo.py` (só se algum limiar mudar)

**Interfaces:**
- Consumes: nada.
- Produces: nada de novo — comportamento possivelmente ajustado nas funções `_e_grito` e `_tem_alongamento`, já existentes.

**Contexto para quem executa:** os valores atuais são `MINIMO_CAIXA_ALTA = 3` (palavra com 3+ letras conta como grito), `MINIMO_ALONGAMENTO = 3` (3+ repetições do mesmo caractere) e `PONTUACAO_ENFATICA = r"[!?]{2,}"` (2+ sinais seguidos). A referência é `docs/superpowers/specs/2026-09-03-incongruencia-bibliografia.md`, itens 26-29 (Burgers 2012; Ptáček et al. 2014; Bouazizi & Ohtsuki). **Isto não é calibração por dado real** — não há corpus rotulado de atendimento em português para isso.

- [ ] **Step 1: Ler a bibliografia e comparar**

Abra `docs/superpowers/specs/2026-09-03-incongruencia-bibliografia.md` e leia as entradas 26, 28 e 29. Para cada um dos três limiares, responda: a literatura indica um valor diferente do atual, e com que justificativa?

- [ ] **Step 2: Decidir por limiar, e registrar a decisão**

Para cada limiar, uma de duas saídas:

**(a) A literatura confirma o valor atual** — não mexa no código. Acrescente ao comentário que já existe sobre a constante uma linha de procedência, no formato que o arquivo já usa. Exemplo para `MINIMO_ALONGAMENTO`:

```python
# Revisado em 03/09/2026 contra Ptacek et al. (COLING 2014): o valor de tres
# se sustenta. Duas repeticoes sao grafia normal do portugues ("carro",
# "nossa"), e a literatura de marcador tipografico nao usa piso menor.
```

**(b) A literatura indica outro valor** — mude a constante, e substitua o comentário explicando: valor antigo, valor novo, referência, e o que muda na prática (que tipo de palavra passa a contar ou deixa de contar).

- [ ] **Step 3: Rodar os testes de estilo**

Run: `uv run pytest tests/test_sinal_estilo.py -v`
Expected: PASS se nenhum limiar mudou. Se algum mudou, os testes que fixam o comportamento antigo falham — atualize-os na mesma mudança, nunca em commit separado (limiar e teste andam juntos, senão o teste vira documentação de um comportamento que não existe mais).

- [ ] **Step 4: Commit**

```bash
git add fraus/sinais/estilo.py tests/test_sinal_estilo.py
git commit -m "docs(estilo): procedencia dos limiares revisada contra a literatura"
```

(Se algum limiar mudou de valor, o commit é `fix(estilo): ...` descrevendo a mudança, não `docs`.)

---

### Task 9: Leitura de estilo por mensagem na API

**Files:**
- Modify: `fraus/sinais/estilo.py` (nova função `estilo_da_mensagem`)
- Modify: `fraus/motor.py:136-148` (dict por mensagem) e `fraus/motor.py:228-240` (rota de simulação)
- Test: `tests/test_sinal_estilo.py`

**Interfaces:**
- Consumes: `_e_grito`, `_tem_alongamento`, `tem_censura`, `casar_censurado`, `carregar_palavroes`, `normalizar`, `PALAVRA`, `PONTUACAO_ENFATICA` — todos já em `estilo.py`.
- Produces: `estilo_da_mensagem(texto: str) -> dict` com as chaves `caixa_alta: bool`, `alongamento: bool`, `pontuacao_enfatica: int`, `palavrao: float | None`, `palavrao_dirigido: bool`, `censura: bool`. Consumida pela Task 10 (dashboard), via campo `"estilo"` no dict por mensagem do motor.

- [ ] **Step 1: Write the failing test**

Acrescente a `tests/test_sinal_estilo.py`:

```python
def test_estilo_da_mensagem_le_uma_fala_por_vez():
    from fraus.sinais.estilo import estilo_da_mensagem

    leitura = estilo_da_mensagem("ISSO E ABSURDO!!! naaaao acredito")
    assert leitura["caixa_alta"] is True
    assert leitura["alongamento"] is True
    assert leitura["pontuacao_enfatica"] == 1
    assert leitura["palavrao"] is None
    assert leitura["censura"] is False


def test_estilo_da_mensagem_sem_marca_nenhuma():
    from fraus.sinais.estilo import estilo_da_mensagem

    leitura = estilo_da_mensagem("bom dia, preciso de ajuda com o pedido")
    assert leitura["caixa_alta"] is False
    assert leitura["alongamento"] is False
    assert leitura["pontuacao_enfatica"] == 0
    assert leitura["palavrao"] is None
    assert leitura["palavrao_dirigido"] is False
    assert leitura["censura"] is False


def test_estilo_da_mensagem_marca_palavrao_com_intensidade():
    from fraus.sinais.estilo import estilo_da_mensagem

    leitura = estilo_da_mensagem("que droga de sistema")
    assert leitura["palavrao"] == 0.33
    assert leitura["palavrao_dirigido"] is False


def test_estilo_da_mensagem_marca_censura():
    from fraus.sinais.estilo import estilo_da_mensagem

    leitura = estilo_da_mensagem("que p*rra e essa")
    assert leitura["censura"] is True


def test_sigla_nao_conta_como_grito_na_leitura_por_mensagem():
    from fraus.sinais.estilo import estilo_da_mensagem

    assert estilo_da_mensagem("preciso do CPF")["caixa_alta"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sinal_estilo.py -v`
Expected: FAIL com `ImportError: cannot import name 'estilo_da_mensagem'`

- [ ] **Step 3: Write minimal implementation**

Em `fraus/sinais/estilo.py`, acrescente antes de `features_estilo`:

```python
def estilo_da_mensagem(texto: str) -> dict:
    """A leitura de estilo de UMA fala, para a tela mostrar onde ela aconteceu.

    `features_estilo` agrega a conversa inteira -- e o que o fusor consome, e
    e a media que pesa na nota. Esta funcao responde outra pergunta: em QUAL
    mensagem a marca apareceu. Uma conversa com 5% de caixa alta pode ser uma
    fala gritada entre dezenove calmas ou vinte falas levemente enfaticas, e a
    media nao distingue as duas.

    As duas leituras compartilham as MESMAS funcoes auxiliares de proposito:
    duas implementacoes da pergunta "isto e um grito?" divergiriam na
    fronteira, e a tela passaria a marcar o que a feature nao marcou.
    """
    palavras = PALAVRA.findall(texto)
    lexicon = carregar_palavroes()

    intensidade_maxima = None
    dirigido = False
    censurada = False

    for palavra in palavras:
        if tem_censura(palavra):
            entrada = casar_censurado(palavra, lexicon)
            if any(c.isalpha() for c in palavra):
                if entrada is not None:
                    censurada = True
            else:
                censurada = True
        else:
            entrada = lexicon.get(normalizar(palavra))
        if entrada is not None:
            valor, alvo_pessoa = entrada
            if intensidade_maxima is None or valor > intensidade_maxima:
                intensidade_maxima = valor
            dirigido = dirigido or alvo_pessoa

    return {
        "caixa_alta": any(_e_grito(p) for p in palavras),
        "alongamento": any(_tem_alongamento(p) for p in palavras),
        "pontuacao_enfatica": len(PONTUACAO_ENFATICA.findall(texto)),
        # O MAXIMO e nao a media: numa fala so, a media diluiria o xingamento
        # pesado entre os leves da mesma frase, e o que a tela precisa
        # mostrar e o pior que apareceu ali.
        "palavrao": intensidade_maxima,
        "palavrao_dirigido": dirigido,
        "censura": censurada,
    }
```

Em `fraus/motor.py`, acrescente ao dict por mensagem (por volta da linha 146, junto de `"emocao"` e `"prob_ironia"`):

```python
                    # Estilo e deterministico e nao depende de classificador:
                    # sai para TODA mensagem, inclusive as do bot, e a tela
                    # decide o que mostrar. As features do fusor continuam
                    # lendo so o cliente -- `features_estilo` nao mudou.
                    "estilo": estilo_da_mensagem(mensagem.texto),
```

com `from fraus.sinais.estilo import estilo_da_mensagem` no topo. Faça o mesmo na rota de simulação (por volta da linha 238), acrescentando `"estilo": estilo_da_mensagem(texto)` ao dict devolvido — confira o nome real da variável de texto naquele escopo.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_sinal_estilo.py tests/test_api.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fraus/sinais/estilo.py fraus/motor.py tests/test_sinal_estilo.py
git commit -m "feat(estilo): leitura por mensagem exposta pelo motor"
```

---

### Task 10: Componente de leitura de estilo na dashboard

**Files:**
- Modify: `dashboard/components/CabecasDeLeitura.tsx` (novo export `LeituraDeEstilo`)
- Modify: `dashboard/lib/api.ts` (tipo do campo `estilo` por mensagem)
- Modify: as telas que já renderizam `CabecasDeLeitura` (Simulador e Analisador — localize com `grep -rn "CabecasDeLeitura" dashboard/`)

**Interfaces:**
- Consumes: campo `estilo` por mensagem produzido na Task 9, com a forma `{ caixa_alta: boolean; alongamento: boolean; pontuacao_enfatica: number; palavrao: number | null; palavrao_dirigido: boolean; censura: boolean }`.
- Produces: componente `LeituraDeEstilo`.

- [ ] **Step 1: Localizar os consumidores**

Run: `cd dashboard && grep -rn "CabecasDeLeitura" --include=*.tsx .`
Anote cada tela que a usa — `LeituraDeEstilo` vai ao lado, nos mesmos lugares.

- [ ] **Step 2: Declarar o tipo em `dashboard/lib/api.ts`**

Encontre o tipo da mensagem analisada (o que já tem `emocao` e `prob_ironia`) e acrescente:

```ts
  estilo: {
    caixa_alta: boolean;
    alongamento: boolean;
    pontuacao_enfatica: number;
    /** Intensidade do pior palavrão da fala, ou null se não houve. */
    palavrao: number | null;
    palavrao_dirigido: boolean;
    censura: boolean;
  } | null;
```

`| null` porque uma resposta de API mais antiga (ou um motor dublê) pode não trazer o campo — e o componente precisa saber a diferença entre "não veio" e "veio tudo falso". **Não use `?? {}` nem `|| false` para preencher**: ausência de medida não é medida negativa (invariante 2).

- [ ] **Step 3: Escrever o componente**

Em `dashboard/components/CabecasDeLeitura.tsx`, acrescente:

```tsx
/**
 * A FORMA da escrita de uma fala -- caixa alta, alongamento, ênfase, palavrão.
 *
 * Irmão de `CabecasDeLeitura` e mora no mesmo arquivo pelo mesmo motivo que
 * ela: painel que explica um modelo, duplicado, envelhece separado.
 *
 * Diferente das duas cabeças de leitura, estilo não é modelo -- é
 * determinístico, calculado por regra em `fraus/sinais/estilo.py`. Por isso
 * não leva ressalva de confiabilidade: não há probabilidade para calibrar,
 * a marca ou está no texto ou não está. O que ele NÃO diz é o quanto isso
 * pesou na nota: quem pesa é a média da conversa inteira, nas features
 * `estilo_*` do fusor.
 */
export function LeituraDeEstilo({
  estilo,
}: {
  estilo: {
    caixa_alta: boolean;
    alongamento: boolean;
    pontuacao_enfatica: number;
    palavrao: number | null;
    palavrao_dirigido: boolean;
    censura: boolean;
  } | null;
}) {
  if (!estilo) return null;

  const marcas: string[] = [];
  if (estilo.caixa_alta) marcas.push("caixa alta");
  if (estilo.alongamento) marcas.push("alongamento");
  if (estilo.pontuacao_enfatica > 0) {
    marcas.push(`ênfase ×${estilo.pontuacao_enfatica}`);
  }
  if (estilo.palavrao !== null) {
    const grau =
      estilo.palavrao >= 1 ? "pesado" : estilo.palavrao >= 0.66 ? "médio" : "leve";
    marcas.push(
      estilo.palavrao_dirigido ? `palavrão ${grau}, dirigido` : `palavrão ${grau}`,
    );
  }
  if (estilo.censura) marcas.push("autocensura");

  // Nenhuma marca é resultado legítimo, não estado vazio: a fala foi medida e
  // não tem ênfase nenhuma. Some da tela em vez de anunciar "nada" vinte
  // vezes numa página que repete o painel por mensagem.
  if (marcas.length === 0) return null;

  return (
    <ul className="flex flex-wrap gap-1.5" aria-label="marcas de estilo da fala">
      {marcas.map((marca) => (
        <li
          key={marca}
          className="rounded-sm bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground"
        >
          {marca}
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 4: Ligar nas telas**

Em cada tela localizada no Step 1, renderize `<LeituraDeEstilo estilo={mensagem.estilo} />` logo abaixo de `<CabecasDeLeitura ... />`, passando o campo da mesma mensagem.

- [ ] **Step 5: Verificar**

Run: `cd dashboard && npm run build`
Expected: build limpo, sem erro de tipo.

Depois, com a API real no ar (`uv run uvicorn fraus.api.main:app`) e `npm run dev`, abra o Simulador e mande uma fala como `ISSO E UM ABSURDO!!! naaaao acredito` — as marcas "caixa alta", "alongamento" e "ênfase ×1" devem aparecer. Uma fala calma não deve mostrar nada.

- [ ] **Step 6: Commit**

```bash
git add dashboard/
git commit -m "feat(dashboard): leitura de estilo por mensagem ao lado das cabecas"
```

---

## Fechamento

- [ ] **Suíte inteira verde:** `uv run pytest -q` e `cd dashboard && npm run build`
- [ ] **Contrato conferido:** `uv run python -c "from fraus.fusor import NOMES_FEATURES; print(len(NOMES_FEATURES))"` → `40`
- [ ] **Retreino do fusor:** pendente, manual, no Colab — ver `docs/treinamento.md`. Até ele acontecer, a API **não sobe** com o fusor antigo (dimensão incompatível), e isso é o comportamento correto (invariante 7). Não contorne com fallback.

---

### Task 3b: Fechar as portas de ingestão que o plano não previu

**Files:**
- Modify: `fraus/ingest/totalk.py:220`
- Modify: `fraus/ingest/transcricao.py:95-97` e `:106-108`
- Test: `tests/test_pii_integracao.py`

**Interfaces:**
- Consumes: `censurar_pii(texto: str) -> str` da Task 1.
- Produces: cobertura completa de PII em todas as origens de dado real.

**Por que esta task existe:** a revisão da Task 3 achou um furo do PLANO, não da
implementação. As specs falavam em "as duas portas de entrada" (API e CSV), mas
existem **três** origens de dado real de cliente que constroem `Mensagem`:
`csv_driver.py` (coberta), `totalk.py:220` (adaptador do export da Totalk) e
`transcricao.py:107` (prosa de `.docx`/`.pdf`). As duas descobertas são
alcançadas por `fraus/ingest/arquivos.py` (`_de_tabela` → `totalk.converter`,
`_de_prosa` → `ler_transcricao`) e alimentam as rotas `/analisar` e
`/analisar/arquivo`, que rodam os classificadores sobre o texto e o exibem na
tela — os dois destinos exatos que a censura existe para impedir.

`fraus/ingest/simulador.py` permanece FORA de propósito: gera frases de um
corpus fixo de templates, sem PII real. Verificado na revisão da Task 3.

**Armadilha em `transcricao.py`, a não perder:** a linha 95-97 faz
`model_copy(update={"texto": f"{anterior.texto}\n{linha.strip()}"})` para juntar
linha de continuação a uma mensagem já montada. Censurar só no `Mensagem(...)`
da linha 107 deixaria passar toda PII que caia numa linha de continuação. Os
DOIS pontos precisam da censura.

- [ ] **Step 1: Write the failing test**

Acrescente a `tests/test_pii_integracao.py`:

```python
def test_totalk_mascara_pii_na_conversao():
    """Terceira porta de entrada: export da Totalk, dado real de cliente."""
    from fraus.ingest import totalk

    # Monte o `linhas` no formato que `totalk.converter` espera -- leia a
    # funcao para descobrir as colunas exatas antes de escrever isto.
    # O texto da mensagem do cliente deve conter "meu cpf e 529.982.247-25".
    resultado = totalk.converter(...)
    texto = resultado.conversas[0].mensagens[0].texto
    assert "529.982.247-25" not in texto
    assert "[CPF]" in texto


def test_transcricao_mascara_pii_inclusive_em_linha_de_continuacao():
    """Quarta armadilha: linha de continuacao e concatenada no texto ja montado.

    Censurar so no `Mensagem(...)` deixaria passar a PII que cair na segunda
    linha de uma fala que quebrou em duas.
    """
    from datetime import datetime, timezone

    from fraus.ingest.transcricao import ler

    inicio = datetime(2026, 9, 3, 10, 0, 0, tzinfo=timezone.utc)
    texto_bruto = "Cliente: primeira linha\ne meu cpf e 529.982.247-25\n"
    resultado = ler(texto_bruto, inicio)

    juntado = " ".join(m.texto for m in resultado.mensagens)
    assert "529.982.247-25" not in juntado
    assert "[CPF]" in juntado
```

Leia `fraus/ingest/totalk.py` e `fraus/ingest/transcricao.py` para acertar as
assinaturas reais (`converter` recebe o quê; `ler` devolve o quê) antes de
rodar. Ajuste os testes à realidade do código — não mude o código para caber
num teste chutado.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pii_integracao.py -v`
Expected: FAIL nos dois testes novos, com a PII crua presente no texto.

- [ ] **Step 3: Write minimal implementation**

Em `fraus/ingest/totalk.py`, importe `from fraus.seguranca.pii import censurar_pii`
e envolva o texto na construção:

```python
            mensagem = Mensagem(
                autor=autor, texto=censurar_pii(texto), enviada_em=enviada_em
            )
```

Em `fraus/ingest/transcricao.py`, importe o mesmo e censure nos DOIS pontos: na
concatenação da linha de continuação e na construção da mensagem.

Acrescente a cada um dos dois arquivos uma linha de comentário dizendo que a
censura mora ali porque é onde `Mensagem` nasce, e que qualquer origem NOVA de
dado real precisa da mesma chamada — no registro de comentário que cada arquivo
já usa.

- [ ] **Step 4: Guard against a fourth door**

Acrescente a `tests/test_pii_integracao.py` um teste que trava a invariante para
origens futuras:

```python
def test_toda_origem_de_dado_real_censura_pii():
    """Guarda contra a QUARTA porta que alguem abrir sem censura.

    O furo que originou esta task foi exatamente isto: o plano cobriu duas
    origens e existiam tres. Este teste falha quando surge uma quarta.
    """
    import pathlib
    import re

    raiz = pathlib.Path(__file__).parent.parent / "fraus" / "ingest"
    # O simulador esta fora de proposito: corpus fixo de templates, sem PII.
    isentos = {"simulador.py"}

    sem_censura = []
    for arquivo in raiz.glob("*.py"):
        if arquivo.name in isentos:
            continue
        fonte = arquivo.read_text(encoding="utf-8")
        if re.search(r"\bMensagem\(", fonte) and "censurar_pii" not in fonte:
            sem_censura.append(arquivo.name)

    assert not sem_censura, (
        f"origem de dado real sem censura de PII: {sem_censura}. "
        "Toda origem que monta Mensagem precisa chamar censurar_pii."
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_pii_integracao.py tests/test_csv_driver.py tests/test_api.py -v`
Expected: PASS, sem regressão.

- [ ] **Step 6: Commit**

```bash
git add fraus/ingest/totalk.py fraus/ingest/transcricao.py tests/test_pii_integracao.py
git commit -m "fix(ingest): censura de PII nas outras duas origens de dado real"
```
