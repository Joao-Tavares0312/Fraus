# Grafo da memória — plano de implementação

> **Para trabalhadores agênticos:** SUB-SKILL OBRIGATÓRIA: use
> superpowers:subagent-driven-development (recomendado) ou
> superpowers:executing-plans para implementar task a task. Os passos usam
> checkbox (`- [ ]`) para rastreio.

**Goal:** Uma página `/grafo` na dashboard e uma rota `GET /grafo` na API que
mostram, num grafo force-directed único, o que o Fraus guarda: léxico ativado,
conversas atendidas e proveniência do dado.

**Architecture:** Um módulo puro `fraus/grafo.py` (irmão de `indicadores.py`)
monta nós e arestas a partir dos registros do recorte — sem FastAPI, sem
`Motor`, sem inferência. Uma rota fina expõe isso. Na dashboard, um Server
Component busca e um Client Component desenha em canvas 2D com
`react-force-graph-2d`.

**Tech Stack:** Python 3 + FastAPI + pytest (backend); Next.js App Router +
React + Tailwind v4 + shadcn/ui + `react-force-graph-2d` (frontend).

**Spec:** `docs/superpowers/specs/2026-08-19-grafo-memoria-design.md` — leia
antes de começar. Este plano implementa aquele documento.

## Global Constraints

- **Ausência de dado não é insatisfação.** `score: None` nunca vira 0 — nem em
  valor, nem em raio de nó, nem em peso de aresta, nem em agregado do `meta`.
  Procure `?? 0` e `|| 0` antes de commitar.
- **Score, nota e categoria são derivados no SERVIDOR.** O TypeScript nunca
  recalcula faixa de NPS nem arredondamento.
- **Sem LLM em runtime, sem rede, sem inferência.** `fraus/grafo.py` e
  `fraus/api/rotas/grafo.py` não importam `Motor`, `ClassificadorTexto`,
  `ClassificadorEmocao` nem `ClassificadorIronia`. Se precisou, o desenho está
  errado.
- **Nomenclatura em português**, como todo o resto do projeto: arquivos,
  funções, variáveis, chaves de JSON.
- **Comentário explica o PORQUÊ**, nunca o quê. Siga a densidade dos arquivos
  vizinhos.
- Comandos: `uv sync --extra dev` (o `uv sync` puro remove o pytest),
  `uv run pytest -q`, `cd dashboard && npm run dev`.
- Não há `package.json` na raiz — todo comando npm roda dentro de `dashboard/`.

---

### Task 1: `Fusor.eixo_global()` — o peso global com sinal

O grafo precisa saber, por feature, se ela empurra para **promotor** ou para
**detrator**. `importancias()` já existe mas devolve valor **absoluto** (sem
sinal), e `contribuicoes()` é por conversa (exige rodar o modelo). Falta o
eixo global com sinal.

Isto também mata uma duplicação: a lógica de "qual diferença de coeficiente
usar conforme o número de classes aprendidas" está hoje dentro de
`contribuicoes` e seria copiada.

**Files:**
- Modify: `fraus/fusor.py` (dentro da classe `Fusor`, perto de
  `contribuicoes` e `importancias`)
- Test: `tests/test_fusor.py` (o arquivo já existe e já tem os helpers
  `_features()` e `_fusor_treinado()` no topo — reuse, não recrie)

**Interfaces:**
- Consumes: nada de tasks anteriores.
- Produces: `Fusor.eixo_global() -> dict[str, float]` — chave é o nome da
  feature (`NOMES_FEATURES`), valor é o coeficiente de satisfeito menos o de
  insatisfeito. **Positivo empurra para satisfeito, negativo para
  insatisfeito.** Devolve `{}` (dict vazio) se o pipeline não foi treinado.
  Usado pela Task 4.

- [ ] **Step 1: Escreva os testes que falham**

Acrescente ao fim de `tests/test_fusor.py`:

```python
def test_eixo_global_vazio_sem_treino():
    """Fusor nao treinado nao tem eixo -- e dict vazio, nao dezesseis zeros.

    Zero e um peso valido ("esta feature nao importa"); ausencia de treino e
    outra coisa. O grafo usa essa diferenca para OMITIR as arestas de feature
    em vez de desenhar dezesseis fios de peso zero.
    """
    assert Fusor().eixo_global() == {}


def test_eixo_global_tem_sinal():
    """Positivo empurra para satisfeito, negativo para insatisfeito.

    `importancias()` nao serve para o grafo porque e valor ABSOLUTO: ela diz
    que `escalou` pesa, nao para que lado.
    """
    eixo = _fusor_treinado().eixo_global()

    assert set(eixo) == set(NOMES_FEATURES)
    # No conjunto de treino, `escalou` so aparece nos exemplos insatisfeitos
    # e `texto_prob_satisfeito_media` so nos satisfeitos.
    assert eixo["escalou"] < 0
    assert eixo["texto_prob_satisfeito_media"] > 0


def test_contribuicoes_seguem_iguais_depois_da_extracao():
    """Trava o refactor: extrair `_diferenca` nao pode mudar a atribuicao."""
    fusor = _fusor_treinado()
    contribuicoes = fusor.contribuicoes(_features(escalou=1.0))

    assert set(contribuicoes) == set(NOMES_FEATURES)
    assert contribuicoes["escalou"] != 0.0
```

- [ ] **Step 2: Rode e veja falhar**

Run: `uv run pytest tests/test_fusor.py -q`
Expected: FAIL — `AttributeError: 'Fusor' object has no attribute 'eixo_global'`

- [ ] **Step 3: Extraia `_diferenca` e escreva `eixo_global`**

Em `fraus/fusor.py`, dentro da classe `Fusor`, substitua o bloco de
`if len(classes) >= 3: ... else: ...` de `contribuicoes` por uma chamada ao
helper novo, e adicione os dois métodos:

```python
    def _diferenca(self):
        """O eixo satisfeito-menos-insatisfeito dos coeficientes aprendidos.

        Mora aqui porque `contribuicoes` (por conversa) e `eixo_global` (peso
        do modelo) precisam da MESMA regra de qual diferenca usar conforme as
        classes que o treino de fato viu -- duas copias divergiriam em silencio
        no caso binario, que e justamente o que ninguem testa a mao.
        """
        modelo = self._pipeline.named_steps["modelo"]
        classes = list(modelo.classes_)

        if len(classes) >= 3:
            return modelo.coef_[classes.index(SATISFEITO)] - modelo.coef_[classes.index(INSATISFEITO)]
        if len(classes) == 2 and INSATISFEITO in classes and SATISFEITO in classes:
            # Caso binario: sklearn guarda uma unica linha de coeficiente, que
            # ja representa a classe mais alta (classes_[1]) contra a mais
            # baixa (classes_[0]) -- aqui sempre satisfeito vs insatisfeito,
            # porque classes_ vem ordenado e insatisfeito (0) < satisfeito (2).
            return modelo.coef_[0]
        return [0.0] * len(NOMES_FEATURES)

    def eixo_global(self) -> dict[str, float]:
        """Quanto cada feature empurra a nota NO MODELO INTEIRO, com sinal.

        Diferente de `importancias`, que e o peso ABSOLUTO (diz que a feature
        pesa, nao para que lado), e de `contribuicoes`, que e o numero de UMA
        conversa. O grafo da memoria consome este: ele responde "o que o modelo
        aprendeu que caracteriza um detrator".

        Nao ha padronizacao aqui porque nao ha conversa: e o coeficiente cru.

        Fusor nao treinado devolve `{}` -- e a ausencia de eixo, que o grafo
        distingue de "todas as features pesam zero".
        """
        if not hasattr(self._pipeline.named_steps["modelo"], "coef_"):
            return {}
        return dict(zip(NOMES_FEATURES, (float(v) for v in self._diferenca())))
```

E em `contribuicoes`, o corpo passa a ser:

```python
        escala = self._pipeline.named_steps["escala"]
        vetor_padronizado = escala.transform([vetorizar(features)])[0]
        contribuicoes = [d * v for d, v in zip(self._diferenca(), vetor_padronizado)]
        return dict(zip(NOMES_FEATURES, (float(v) for v in contribuicoes)))
```

Mantenha o docstring existente de `contribuicoes` — ele explica o eixo e o
caso degenerado, e a explicação continua valendo.

- [ ] **Step 4: Rode os testes**

Run: `uv run pytest tests/test_fusor.py -q`
Expected: PASS, incluindo os testes de `contribuicoes` que já existiam.

- [ ] **Step 5: Commit**

```bash
git add fraus/fusor.py tests/test_fusor.py
git commit -m "feat(fusor): eixo_global -- o peso aprendido COM sinal"
```

---

### Task 2: `fraus/grafo.py` — a camada de domínio

A espinha do grafo: conversa, e o que ela é (categoria, canal, desfecho).

**Files:**
- Create: `fraus/grafo.py`
- Test: `tests/test_grafo.py`

**Interfaces:**
- Consumes: `fraus.modelos.Conversa`, `fraus.indicadores.nota_0_10`,
  `fraus.resumo.desfecho`, `fraus.indicadores.FAIXAS_NPS`.
- Produces:
  - `CAMADAS: tuple[str, ...] = ("lexico", "dominio", "proveniencia")`
  - `TODAS_AS_CAMADAS: frozenset[str]`
  - `TETO_TERMOS_PADRAO: int = 120`
  - `montar_grafo(registros, faixas, *, camadas=TODAS_AS_CAMADAS,
    teto_termos=TETO_TERMOS_PADRAO, eixo=None, fontes=(), importacoes=())
    -> dict` com chaves `"nos"`, `"arestas"`, `"meta"`.
  - Formato de nó: `{"id", "tipo", "camada", "rotulo", "grau"}` e, só quando
    `tipo == "conversa"`, também `{"score", "nota", "categoria", "sem_sinal"}`.
  - Formato de aresta: `{"de", "para", "tipo", "peso"}`.
  - Convenção de id: `"<tipo>:<chave>"`.
  - Tasks 3, 4 e 5 acrescentam camadas a esta mesma função.

- [ ] **Step 1: Escreva os testes que falham**

Crie `tests/test_grafo.py`:

```python
from datetime import datetime, timedelta, timezone

from fraus.grafo import TODAS_AS_CAMADAS, montar_grafo
from fraus.indicadores import FAIXAS_NPS
from fraus.modelos import Conversa, Mensagem

BASE = datetime(2026, 8, 19, 10, 0, 0, tzinfo=timezone.utc)


def _conversa(identificador="c1", canal="whatsapp", falas=(("cliente", "demora demais"),)):
    mensagens = [
        Mensagem(autor=autor, texto=texto, enviada_em=BASE + timedelta(minutes=i))
        for i, (autor, texto) in enumerate(falas)
    ]
    return Conversa(id=identificador, canal=canal, iniciada_em=BASE, mensagens=mensagens)


def _nos_por_tipo(grafo, tipo):
    return [no for no in grafo["nos"] if no["tipo"] == tipo]


def _no(grafo, identificador):
    return next(no for no in grafo["nos"] if no["id"] == identificador)


def test_conversa_vira_no_ligado_a_categoria_canal_e_desfecho():
    grafo = montar_grafo([(_conversa(), 30.0)], FAIXAS_NPS)

    assert _no(grafo, "conversa:c1")["categoria"] == "detrator"
    ligacoes = {
        (aresta["de"], aresta["para"])
        for aresta in grafo["arestas"]
    }
    assert ("conversa:c1", "categoria:detrator") in ligacoes
    assert ("conversa:c1", "canal:whatsapp") in ligacoes
    # Ultima fala e do cliente e ninguem respondeu.
    assert ("conversa:c1", "desfecho:sem_resposta") in ligacoes


def test_sem_sinal_nao_vira_zero_em_lugar_nenhum():
    """A invariante central do projeto, agora em forma de no.

    Conversa sem fala do cliente tem `score: None`. Se ela aparecesse com
    score 0, o grafo diria visualmente que o pior atendimento do conjunto foi
    justamente aquele sobre o qual nao se sabe nada.
    """
    conversa = _conversa(falas=(("bot", "ola, posso ajudar?"),))
    grafo = montar_grafo([(conversa, None)], FAIXAS_NPS)

    no = _no(grafo, "conversa:c1")
    assert no["score"] is None
    assert no["nota"] is None
    assert no["categoria"] is None
    assert no["sem_sinal"] is True
    # Sem categoria nao ha aresta de categoria -- inventar uma seria escolher
    # uma faixa para quem nao tem nota.
    assert not _nos_por_tipo(grafo, "categoria")
    assert grafo["meta"]["sem_sinal"] == 1


def test_grau_conta_as_arestas_do_no():
    grafo = montar_grafo([(_conversa(), 95.0)], FAIXAS_NPS)
    assert _no(grafo, "categoria:promotor")["grau"] == 1
    assert _no(grafo, "conversa:c1")["grau"] == 3


def test_nenhuma_aresta_orfa():
    """Aresta apontando para no inexistente quebra a simulacao no cliente."""
    registros = [(_conversa("c1"), 30.0), (_conversa("c2", canal="discord"), 95.0)]
    grafo = montar_grafo(registros, FAIXAS_NPS)

    existentes = {no["id"] for no in grafo["nos"]}
    for aresta in grafo["arestas"]:
        assert aresta["de"] in existentes
        assert aresta["para"] in existentes


def test_camada_desligada_nao_emite_nada():
    grafo = montar_grafo([(_conversa(), 30.0)], FAIXAS_NPS, camadas=frozenset({"lexico"}))
    assert not _nos_por_tipo(grafo, "conversa")
    assert grafo["meta"]["camadas"] == ["lexico"]


def test_recorte_vazio_devolve_grafo_vazio_e_nao_erro():
    grafo = montar_grafo([], FAIXAS_NPS)
    assert grafo["nos"] == []
    assert grafo["arestas"] == []
    assert grafo["meta"]["conversas"] == 0
```

- [ ] **Step 2: Rode e veja falhar**

Run: `uv run pytest tests/test_grafo.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'fraus.grafo'`

- [ ] **Step 3: Escreva `fraus/grafo.py`**

```python
"""O grafo da memoria: o que o Fraus guarda, e como aquilo se liga.

Modulo PURO -- nenhum import de FastAPI, nenhum classificador, nenhuma
inferencia. Ele le registros que ja estao no banco e conta. Se algum dia
precisar do `Motor` para montar um no, o desenho esta errado: a rota que o
consome e uma tela de leitura, e carregar o BERTimbau por requisicao de
pagina foi exatamente o custo que este desenho existe para evitar.

Tres camadas, um grafo so. O no `conversa` e a espinha -- e o unico tipo que
aparece nas tres, e e por isso que a visao unificada se sustenta em vez de
virar tres nuvens soltas.

O que este modulo NAO tem, e por que:
  - `emocao`: sai do classificador, e inferencia (ver spec 2.0.1).
  - `feature -> conversa`: `contribuicoes` nao e persistida (spec 2.1).
  - `importacao -> conversa`: o schema nao guarda esse vinculo (spec 2.0).
"""

from collections import Counter

from fraus.indicadores import nota_0_10
from fraus.modelos import Conversa
from fraus.resumo import desfecho

CAMADAS = ("lexico", "dominio", "proveniencia")
TODAS_AS_CAMADAS = frozenset(CAMADAS)

# Teto de termos do lexico exibidos. O SentiLex tem 79.190 entradas: o grafo
# mostra os ATIVADOS no recorte, e ainda assim corta -- com o corte declarado
# no `meta`, nunca em silencio (spec 2.2).
TETO_TERMOS_PADRAO = 120


class _Montagem:
    """Acumulador de nos e arestas, com o grau saindo de graca.

    Existe para as quatro camadas nao repetirem o "ja adicionei este no?" --
    a checagem estava em toda funcao e um esquecimento produzia no duplicado,
    que na simulacao do cliente vira dois pontos empilhados no mesmo lugar.
    """

    def __init__(self) -> None:
        self._nos: dict[str, dict] = {}
        self.arestas: list[dict] = []

    def no(self, tipo: str, chave: str, camada: str, rotulo: str, **extras) -> str:
        identificador = f"{tipo}:{chave}"
        if identificador not in self._nos:
            self._nos[identificador] = {
                "id": identificador,
                "tipo": tipo,
                "camada": camada,
                "rotulo": rotulo,
                "grau": 0,
                **extras,
            }
        return identificador

    def aresta(self, de: str, para: str, tipo: str, peso: float = 1.0) -> None:
        self.arestas.append({"de": de, "para": para, "tipo": tipo, "peso": peso})
        self._nos[de]["grau"] += 1
        self._nos[para]["grau"] += 1

    @property
    def nos(self) -> list[dict]:
        return list(self._nos.values())


def _categoria_de(score: float | None, faixas: dict) -> str | None:
    """Categoria da nota, ou None sem score.

    Sem score nao ha nota, e sem nota nao ha faixa que cubra: devolver
    "detrator" aqui faria a ausencia de dado virar insatisfacao, que e a
    invariante que este projeto mais defende.
    """
    if score is None:
        return None
    nota = nota_0_10(score)
    for categoria, (minima, maxima) in faixas.items():
        if minima <= nota <= maxima:
            return categoria
    return None


def _camada_dominio(montagem: _Montagem, registros: list, faixas: dict) -> None:
    for conversa, score in registros:
        categoria = _categoria_de(score, faixas)
        conversa_id = montagem.no(
            "conversa",
            conversa.id,
            "dominio",
            f"Atendimento {conversa.id}",
            score=score,
            nota=None if score is None else nota_0_10(score),
            categoria=categoria,
            sem_sinal=score is None,
        )
        if categoria is not None:
            montagem.aresta(
                conversa_id,
                montagem.no("categoria", categoria, "dominio", categoria.capitalize()),
                "classificada",
            )
        montagem.aresta(
            conversa_id,
            montagem.no("canal", conversa.canal, "dominio", conversa.canal),
            "chegou_por",
        )
        fim = desfecho(conversa)
        montagem.aresta(
            conversa_id,
            montagem.no("desfecho", fim, "dominio", fim.replace("_", " ")),
            "terminou_em",
        )


def montar_grafo(
    registros: list[tuple[Conversa, float | None]],
    faixas: dict,
    *,
    camadas: frozenset[str] = TODAS_AS_CAMADAS,
    teto_termos: int = TETO_TERMOS_PADRAO,
    eixo: dict[str, float] | None = None,
    fontes: list[dict] = (),
    importacoes: list[dict] = (),
) -> dict:
    """Nos, arestas e metadados do recorte pedido.

    `faixas` vem da configuracao vigente (nunca de uma copia local): a
    categoria do no e a MESMA que `/conversas` e `/indicadores` devolvem, e
    duplicar a faixa aqui ja foi defeito deste projeto uma vez.
    """
    montagem = _Montagem()

    if "dominio" in camadas:
        _camada_dominio(montagem, registros, faixas)

    return {
        "nos": montagem.nos,
        "arestas": montagem.arestas,
        "meta": {
            "camadas": sorted(camadas),
            "conversas": len(registros),
            "sem_sinal": sum(1 for _, score in registros if score is None),
            "termos_totais": 0,
            "termos_exibidos": 0,
            "truncado": False,
        },
    }
```

- [ ] **Step 4: Rode os testes**

Run: `uv run pytest tests/test_grafo.py -q`
Expected: PASS (6 testes)

- [ ] **Step 5: Commit**

```bash
git add fraus/grafo.py tests/test_grafo.py
git commit -m "feat(grafo): a camada de dominio -- conversa, categoria, canal, desfecho"
```

---

### Task 3: A camada de léxico — termos e emojis ativados

O que o modelo de fato ativou no recorte, com teto declarado.

**Files:**
- Modify: `fraus/grafo.py`
- Test: `tests/test_grafo.py`

**Interfaces:**
- Consumes: `montar_grafo` e `_Montagem` da Task 2;
  `fraus.sinais.palavras.contar_palavras(textos: list[str]) -> Counter`;
  `fraus.sinais.emoji.emojis_com_posicao(texto: str) -> list[tuple[str, float]]`.
- Produces: nós `termo:<palavra>` e `emoji:<caractere>` na camada `lexico`,
  arestas `tipo="ativou"` com `peso` = número de ocorrências na conversa; e o
  `meta` passa a reportar `termos_totais`, `termos_exibidos` e `truncado` de
  verdade.

- [ ] **Step 1: Escreva os testes que falham**

Acrescente a `tests/test_grafo.py`:

```python
def test_termo_do_cliente_vira_no_ligado_a_conversa():
    conversa = _conversa(falas=(("cliente", "demora demais, demora"),))
    grafo = montar_grafo([(conversa, 30.0)], FAIXAS_NPS)

    aresta = next(a for a in grafo["arestas"] if a["para"] == "termo:demora")
    assert aresta["de"] == "conversa:c1"
    assert aresta["tipo"] == "ativou"
    assert aresta["peso"] == 2  # a palavra aparece duas vezes na fala


def test_fala_do_bot_nao_entra_no_lexico():
    """O texto do bot e roteiro, nao vocabulario do cliente.

    Mesma regra do `lexico_por_classe`: contar o roteiro faria o termo mais
    frequente do grafo ser sempre a saudacao automatica.
    """
    conversa = _conversa(falas=(
        ("bot", "protocolo aberto com sucesso"),
        ("cliente", "obrigado"),
    ))
    grafo = montar_grafo([(conversa, 95.0)], FAIXAS_NPS)

    rotulos = {no["rotulo"] for no in _nos_por_tipo(grafo, "termo")}
    assert "protocolo" not in rotulos
    assert "obrigado" in rotulos


def test_emoji_do_cliente_vira_no():
    conversa = _conversa(falas=(("cliente", "que raiva 😡"),))
    grafo = montar_grafo([(conversa, 20.0)], FAIXAS_NPS)
    assert _no(grafo, "emoji:😡")["camada"] == "lexico"


def test_teto_corta_por_frequencia_e_declara_o_corte():
    """Truncar calado afirmaria que aquilo e tudo o que o sistema sabe."""
    fala = " ".join(f"palavra{i}" for i in range(10)) + " campeao campeao campeao"
    grafo = montar_grafo(
        [(_conversa(falas=(("cliente", fala),)), 30.0)],
        FAIXAS_NPS,
        teto_termos=2,
    )

    assert grafo["meta"]["termos_totais"] == 11
    assert grafo["meta"]["termos_exibidos"] == 2
    assert grafo["meta"]["truncado"] is True
    # O corte e por frequencia: o termo repetido sobrevive.
    assert "termo:campeao" in {no["id"] for no in grafo["nos"]}
    assert len(_nos_por_tipo(grafo, "termo")) == 2


def test_sem_truncar_o_meta_diz_que_nao_truncou():
    grafo = montar_grafo([(_conversa(), 30.0)], FAIXAS_NPS)
    assert grafo["meta"]["truncado"] is False
    assert grafo["meta"]["termos_exibidos"] == grafo["meta"]["termos_totais"]


def test_camada_lexico_desligada_nao_emite_termo():
    grafo = montar_grafo([(_conversa(), 30.0)], FAIXAS_NPS, camadas=frozenset({"dominio"}))
    assert not _nos_por_tipo(grafo, "termo")
```

- [ ] **Step 2: Rode e veja falhar**

Run: `uv run pytest tests/test_grafo.py -q`
Expected: FAIL — `StopIteration` no primeiro teste (não existe nó `termo:`)

- [ ] **Step 3: Implemente a camada**

Em `fraus/grafo.py`, acrescente os imports e a função, e chame-a de
`montar_grafo`:

```python
from fraus.sinais.emoji import emojis_com_posicao
from fraus.sinais.palavras import contar_palavras
```

```python
def _camada_lexico(montagem: _Montagem, registros: list, teto_termos: int) -> dict:
    """Termos e emojis ATIVADOS no recorte, cortados por frequencia.

    Duas passadas de proposito: a primeira conta o conjunto inteiro para saber
    quais termos sobrevivem ao teto GLOBALMENTE, a segunda liga cada conversa
    aos sobreviventes. Cortar por conversa daria um teto por conversa, e o
    total do recorte estouraria de novo.

    So a fala do CLIENTE conta, e a extracao e a mesma de `lexico_por_classe`
    e do sinal de emoji -- contagem propria aqui divergiria do motor.
    """
    contagem_global: Counter = Counter()
    por_conversa: dict[str, Counter] = {}

    for conversa, _ in registros:
        falas = [mensagem.texto for mensagem in conversa.mensagens_cliente]
        contagem = contar_palavras(falas)
        por_conversa[conversa.id] = contagem
        contagem_global.update(contagem)

    sobreviventes = {termo for termo, _ in contagem_global.most_common(teto_termos)}

    for conversa, _ in registros:
        conversa_id = montagem.no(
            "conversa", conversa.id, "dominio", f"Atendimento {conversa.id}"
        )
        for termo, ocorrencias in por_conversa[conversa.id].items():
            if termo not in sobreviventes:
                continue
            montagem.aresta(
                conversa_id,
                montagem.no("termo", termo, "lexico", termo),
                "ativou",
                peso=ocorrencias,
            )
        for mensagem in conversa.mensagens_cliente:
            for emoji, _posicao in emojis_com_posicao(mensagem.texto):
                montagem.aresta(
                    conversa_id,
                    montagem.no("emoji", emoji, "lexico", emoji),
                    "ativou",
                )

    return {
        "termos_totais": len(contagem_global),
        "termos_exibidos": len(sobreviventes),
        "truncado": len(contagem_global) > len(sobreviventes),
    }
```

Em `montar_grafo`, entre a camada de domínio e o `return`:

```python
    lexico = {"termos_totais": 0, "termos_exibidos": 0, "truncado": False}
    if "lexico" in camadas:
        lexico = _camada_lexico(montagem, registros, teto_termos)
```

E no `meta`, troque os três zeros fixos por `**lexico`.

**Atenção:** `_camada_lexico` cria o nó `conversa` chamando `montagem.no` com
os mesmos `tipo`/`chave` da camada de domínio. Isso é intencional — `_Montagem`
deduplica por id, então com as duas camadas ligadas o nó é o mesmo objeto (o
que faz a ponte entre camadas existir), e com só o léxico ligado o nó conversa
ainda aparece, porque uma aresta precisa das duas pontas.

- [ ] **Step 4: Rode os testes**

Run: `uv run pytest tests/test_grafo.py -q`
Expected: PASS (12 testes). O `test_camada_desligada_nao_emite_nada` da Task 2
continua passando: com só `lexico` ligado a conversa vira nó, mas aquele teste
pede `camadas={"lexico"}` numa conversa cuja fala é "demora demais" — se ele
falhar agora, **atualize o teste** para verificar ausência de
`categoria`/`canal`/`desfecho` em vez de ausência de `conversa`, e explique no
docstring que a conversa é a ponte entre camadas.

- [ ] **Step 5: Commit**

```bash
git add fraus/grafo.py tests/test_grafo.py
git commit -m "feat(grafo): a camada de lexico -- so o que foi ativado, com teto declarado"
```

---

### Task 4: A camada de features — o que o modelo aprendeu

**Files:**
- Modify: `fraus/grafo.py`
- Test: `tests/test_grafo.py`

**Interfaces:**
- Consumes: `Fusor.eixo_global()` da Task 1, entregue como o parâmetro
  `eixo: dict[str, float] | None` de `montar_grafo`.
- Produces: nós `feature:<nome>` na camada `lexico` e arestas
  `feature → categoria` com `tipo="caracteriza"` e `peso=abs(coeficiente)`.

- [ ] **Step 1: Escreva os testes que falham**

Acrescente a `tests/test_grafo.py`:

```python
def test_feature_liga_na_categoria_que_ela_empurra():
    """Peso positivo aponta para promotor; negativo, para detrator.

    A aresta e para CATEGORIA e nao para conversa de proposito: `contribuicoes`
    nao e persistida, e uma aresta por conversa exigiria rodar o BERTimbau N
    vezes numa requisicao de pagina (spec 2.1).
    """
    eixo = {"escalou": -1.5, "emoji_score_medio": 0.8}
    grafo = montar_grafo([(_conversa(), 30.0)], FAIXAS_NPS, eixo=eixo)

    ligacoes = {(a["de"], a["para"]): a for a in grafo["arestas"]}
    assert ("feature:escalou", "categoria:detrator") in ligacoes
    assert ligacoes[("feature:escalou", "categoria:detrator")]["peso"] == 1.5
    assert ("feature:emoji_score_medio", "categoria:promotor") in ligacoes


def test_sem_fusor_treinado_nao_ha_aresta_de_feature():
    """Dezesseis fios de peso zero afirmariam que o modelo aprendeu nada disso."""
    grafo = montar_grafo([(_conversa(), 30.0)], FAIXAS_NPS, eixo=None)
    assert not _nos_por_tipo(grafo, "feature")

    grafo_vazio = montar_grafo([(_conversa(), 30.0)], FAIXAS_NPS, eixo={})
    assert not _nos_por_tipo(grafo_vazio, "feature")


def test_feature_de_peso_zero_fica_de_fora():
    """Peso zero e "nao importa" -- desenhar o fio poluiria sem informar."""
    grafo = montar_grafo([(_conversa(), 30.0)], FAIXAS_NPS, eixo={"escalou": 0.0})
    assert not _nos_por_tipo(grafo, "feature")
```

- [ ] **Step 2: Rode e veja falhar**

Run: `uv run pytest tests/test_grafo.py -q`
Expected: FAIL — `AssertionError` no primeiro teste (aresta não existe)

- [ ] **Step 3: Implemente**

Em `fraus/grafo.py`:

```python
def _camada_features(montagem: _Montagem, eixo: dict[str, float], faixas: dict) -> None:
    """O peso GLOBAL do fusor, ligado a categoria que ele empurra.

    Positivo aponta para a faixa mais alta (promotor), negativo para a mais
    baixa (detrator) -- lidas de `faixas` e nao escritas a mao, porque a
    configuracao vigente pode renomear ou remover uma delas.

    Peso zero nao vira aresta: e "esta feature nao importa", e desenhar o fio
    diria o contrario com a mesma tinta das que importam.
    """
    ordenadas = sorted(faixas.items(), key=lambda item: item[1][0])
    mais_baixa, mais_alta = ordenadas[0][0], ordenadas[-1][0]

    for nome, peso in eixo.items():
        if peso == 0.0:
            continue
        categoria = mais_alta if peso > 0 else mais_baixa
        montagem.aresta(
            montagem.no("feature", nome, "lexico", nome.replace("_", " ")),
            montagem.no("categoria", categoria, "dominio", categoria.capitalize()),
            "caracteriza",
            peso=abs(peso),
        )
```

Em `montar_grafo`, junto da camada de léxico:

```python
    if "lexico" in camadas and eixo:
        _camada_features(montagem, eixo, faixas)
```

- [ ] **Step 4: Rode os testes**

Run: `uv run pytest tests/test_grafo.py -q`
Expected: PASS (15 testes)

- [ ] **Step 5: Commit**

```bash
git add fraus/grafo.py tests/test_grafo.py
git commit -m "feat(grafo): features ligadas a categoria pelo eixo global do fusor"
```

---

### Task 5: A camada de proveniência — de onde o dado veio

**Files:**
- Modify: `fraus/grafo.py`
- Test: `tests/test_grafo.py`

**Interfaces:**
- Consumes: `Banco.listar_fontes() -> list[dict]` (cada dict tem `id`, `nome`,
  `canal`, `tipo`, `ativa`) e `Banco.listar_importacoes() -> list[dict]` (cada
  dict tem `id`, `ocorrida_em`, `arquivo`, `aceitas`, `rejeitadas`), passados
  como `fontes=` e `importacoes=`.
- Produces: nós `fonte:<id>` e `importacao:<id>` na camada `proveniencia`,
  arestas `tipo="alimenta_canal"` para o nó `canal:<canal>`. A importação liga
  ao canal **só quando** existe um canal com aquele nome no recorte — ela não
  guarda canal próprio, então a ligação sai do arquivo importado apenas se
  alguma fonte declarar aquele canal.

- [ ] **Step 1: Escreva os testes que falham**

Acrescente a `tests/test_grafo.py`:

```python
def test_fonte_liga_no_canal_e_nunca_na_conversa():
    """O schema nao guarda qual importacao criou qual conversa (spec 2.0).

    Ligar fonte -> conversa exigiria inventar o vinculo. O canal e o que
    existe de verdade, e a aresta diz isso no proprio tipo.
    """
    fontes = [{"id": 1, "nome": "Suporte WhatsApp", "canal": "whatsapp", "tipo": "webhook", "ativa": 1}]
    grafo = montar_grafo([(_conversa(), 30.0)], FAIXAS_NPS, fontes=fontes)

    ligacoes = {(a["de"], a["para"], a["tipo"]) for a in grafo["arestas"]}
    assert ("fonte:1", "canal:whatsapp", "alimenta_canal") in ligacoes
    assert not [a for a in grafo["arestas"] if a["de"].startswith("fonte:") and "conversa:" in a["para"]]
    assert _no(grafo, "fonte:1")["camada"] == "proveniencia"


def test_fonte_de_canal_fora_do_recorte_aparece_sozinha():
    """Ela existe no sistema mesmo sem conversa no periodo -- some-la esconderia
    uma integracao configurada e sem dado, que e justamente o que alguem
    precisa ver."""
    fontes = [{"id": 2, "nome": "Discord", "canal": "discord", "tipo": "bot", "ativa": 1}]
    grafo = montar_grafo([(_conversa(canal="whatsapp"), 30.0)], FAIXAS_NPS, fontes=fontes)

    assert _no(grafo, "fonte:2")
    assert _no(grafo, "canal:discord")["camada"] == "proveniencia"


def test_importacao_vira_no_com_o_arquivo_no_rotulo():
    importacoes = [{"id": 7, "ocorrida_em": "2026-08-19T10:00:00Z", "arquivo": "julho.csv",
                    "aceitas": 40, "rejeitadas": 2}]
    grafo = montar_grafo([(_conversa(), 30.0)], FAIXAS_NPS, importacoes=importacoes)

    no = _no(grafo, "importacao:7")
    assert "julho.csv" in no["rotulo"]
    assert no["camada"] == "proveniencia"


def test_camada_proveniencia_desligada_nao_emite_fonte():
    fontes = [{"id": 1, "nome": "Suporte", "canal": "whatsapp", "tipo": "webhook", "ativa": 1}]
    grafo = montar_grafo(
        [(_conversa(), 30.0)], FAIXAS_NPS, fontes=fontes, camadas=frozenset({"dominio"})
    )
    assert not _nos_por_tipo(grafo, "fonte")
```

- [ ] **Step 2: Rode e veja falhar**

Run: `uv run pytest tests/test_grafo.py -q`
Expected: FAIL — `StopIteration` (não existe nó `fonte:1`)

- [ ] **Step 3: Implemente**

Em `fraus/grafo.py`:

```python
def _camada_proveniencia(montagem: _Montagem, fontes: list[dict], importacoes: list[dict]) -> None:
    """De onde o dado veio -- ate onde o schema deixa afirmar.

    `importacoes` NAO tem coluna apontando para `conversas`, e
    `fontes_integracao` so compartilha o campo `canal`. Entao a ligacao e por
    canal, e o tipo da aresta diz exatamente isso: `alimenta_canal`, nao
    `criou`. A aresta que faltaria (importacao -> conversa) exige migracao de
    schema, e ela esta registrada na spec como decisao propria -- nao se
    inventa vinculo para o desenho ficar bonito.
    """
    for fonte in fontes:
        montagem.aresta(
            montagem.no("fonte", str(fonte["id"]), "proveniencia", fonte["nome"]),
            montagem.no("canal", fonte["canal"], "proveniencia", fonte["canal"]),
            "alimenta_canal",
        )

    canais = {no["id"] for no in montagem.nos if no["tipo"] == "canal"}
    for importacao in importacoes:
        rotulo = f"{importacao['arquivo']} ({importacao['aceitas']} aceitas)"
        importacao_id = montagem.no(
            "importacao", str(importacao["id"]), "proveniencia", rotulo
        )
        # A importacao so se liga a canal se algum canal existir no conjunto;
        # ela nao guarda canal proprio, e um arquivo CSV nao declara origem.
        for canal in sorted(canais):
            montagem.aresta(importacao_id, canal, "alimenta_canal")
```

Em `montar_grafo`:

```python
    if "proveniencia" in camadas:
        _camada_proveniencia(montagem, list(fontes), list(importacoes))
```

**Ordem importa:** chame a proveniência **depois** do domínio, para os nós de
canal já existirem e serem reaproveitados em vez de duplicados. O nó `canal`
criado pelo domínio mantém `camada="dominio"` (o `_Montagem` não sobrescreve
nó existente) — é o comportamento certo: o canal é do domínio, e a
proveniência só se pendura nele. O teste
`test_fonte_de_canal_fora_do_recorte_aparece_sozinha` cobre o caso inverso,
onde o canal nasce da proveniência.

- [ ] **Step 4: Rode os testes**

Run: `uv run pytest tests/test_grafo.py -q`
Expected: PASS (19 testes)

- [ ] **Step 5: Commit**

```bash
git add fraus/grafo.py tests/test_grafo.py
git commit -m "feat(grafo): proveniencia ligada por canal -- o vinculo que o schema tem"
```

---

### Task 6: A rota `GET /grafo`

**Files:**
- Create: `fraus/api/rotas/grafo.py`
- Modify: `fraus/api/main.py` (o import de `fraus.api.rotas` e o
  `include_router` correspondente — siga exatamente o que já está lá para
  `indicadores`)
- Test: `tests/test_api_grafo.py`

**Interfaces:**
- Consumes: `montar_grafo` (Tasks 2–5), `Contexto.registros_do_recorte`,
  `Contexto.faixas_vigentes`, `Banco.listar_fontes`,
  `Banco.listar_importacoes`, `Fusor.eixo_global` (via `Motor`).
- Produces: `GET /grafo` e a constante `TETO_TERMOS_GRAFO = 500`.

**Nota sobre o eixo:** `Contexto` expõe `motor`, e `Motor` guarda `_fusor`
privado com um passthrough público `importancias()`. Acrescente ao `Motor`, ao
lado dele, o passthrough gêmeo:

```python
    def eixo_global(self) -> dict:
        """Passthrough do peso global COM sinal -- o grafo da memoria consome."""
        return self._fusor.eixo_global()
```

- [ ] **Step 1: Escreva os testes que falham**

Crie `tests/test_api_grafo.py`. Copie o helper de cliente/app do topo de
`tests/test_api.py` (o projeto já tem o padrão de montar `criar_app` com dublê
de motor — **leia `tests/test_api.py` antes e siga o que estiver lá**, não
invente uma fábrica nova):

```python
def test_grafo_responde_com_nos_arestas_e_meta(cliente):
    resposta = cliente.get("/grafo")
    assert resposta.status_code == 200

    corpo = resposta.json()
    assert set(corpo) == {"nos", "arestas", "meta"}
    assert corpo["meta"]["camadas"] == ["dominio", "lexico", "proveniencia"]


def test_banco_vazio_devolve_grafo_vazio_e_nao_erro(cliente):
    """Vazio nao e falha -- a tela tem estado vazio proprio para isso."""
    resposta = cliente.get("/grafo")
    assert resposta.status_code == 200
    assert resposta.json()["nos"] == [] or resposta.json()["meta"]["conversas"] >= 0


def test_camada_desconhecida_da_400(cliente):
    """Ignorar em silencio devolveria um grafo diferente do pedido sem avisar."""
    resposta = cliente.get("/grafo?camadas=lexico,inventada")
    assert resposta.status_code == 400
    assert "inventada" in resposta.json()["detail"]


def test_camada_restrita_e_respeitada(cliente):
    corpo = cliente.get("/grafo?camadas=dominio").json()
    assert corpo["meta"]["camadas"] == ["dominio"]


def test_teto_de_termos_acima_do_limite_da_400(cliente):
    """O teto existe para o cliente nao conseguir pedir 80 mil nos."""
    resposta = cliente.get("/grafo?teto_termos=100000")
    assert resposta.status_code == 400


def test_periodo_invalido_da_400(cliente):
    """Mesma validacao de recorte das outras rotas -- nao uma copia local."""
    resposta = cliente.get("/grafo?de=2026-13-45")
    assert resposta.status_code == 400
```

- [ ] **Step 2: Rode e veja falhar**

Run: `uv run pytest tests/test_api_grafo.py -q`
Expected: FAIL — 404 em `/grafo`

- [ ] **Step 3: Escreva a rota e registre**

Crie `fraus/api/rotas/grafo.py`:

```python
"""GET /grafo -- a memoria do sistema como grafo.

Rota FINA: toda a montagem mora em `fraus/grafo.py`, que e modulo puro. Aqui
so acontecem a validacao dos parametros e a leitura do banco.

Ela NAO carrega modelo e NAO chama o `Motor` para pontuar nada: le o que ja
esta gravado e conta. O unico dado que vem do modelo e o eixo global do fusor
-- coeficiente ja treinado, em disco, sem inferencia.
"""

from fastapi import APIRouter, Depends, HTTPException

from fraus.api.contexto import Contexto, obter_contexto
from fraus.grafo import CAMADAS, TETO_TERMOS_PADRAO, TODAS_AS_CAMADAS, montar_grafo

# Teto de termos que o cliente PODE pedir. Sem ele, `?teto_termos=79190`
# devolveria o SentiLex inteiro numa resposta so.
TETO_TERMOS_GRAFO = 500

router = APIRouter()


def _camadas_ou_400(bruto: str | None) -> frozenset[str]:
    """Camadas pedidas, ou 400 nomeando a desconhecida.

    Ignorar o valor invalido devolveria um grafo DIFERENTE do pedido sem
    avisar ninguem -- e o tipo de silencio que faz alguem concluir que a
    camada esta vazia quando na verdade ela nunca foi consultada.
    """
    if not bruto:
        return TODAS_AS_CAMADAS
    pedidas = [parte.strip() for parte in bruto.split(",") if parte.strip()]
    desconhecidas = [parte for parte in pedidas if parte not in CAMADAS]
    if desconhecidas:
        raise HTTPException(
            status_code=400,
            detail=f"camada desconhecida: {', '.join(desconhecidas)}. Conhecidas: {', '.join(CAMADAS)}",
        )
    return frozenset(pedidas)


@router.get("/grafo")
def grafo(
    de: str | None = None,
    ate: str | None = None,
    camadas: str | None = None,
    teto_termos: int = TETO_TERMOS_PADRAO,
    ctx: Contexto = Depends(obter_contexto),
) -> dict:
    """Nos e arestas da memoria do sistema, no recorte pedido."""
    if teto_termos < 1 or teto_termos > TETO_TERMOS_GRAFO:
        raise HTTPException(
            status_code=400,
            detail=f"teto_termos precisa estar entre 1 e {TETO_TERMOS_GRAFO}",
        )

    pedidas = _camadas_ou_400(camadas)
    registros = ctx.registros_do_recorte(de, ate)

    # Fusor sem treino devolve `{}`, e o grafo omite as arestas de feature.
    # Nao ha try/except aqui de proposito: se o `Motor` quebrar ao ler um
    # coeficiente ja carregado, isso e defeito real e deve aparecer.
    eixo = ctx.motor.eixo_global()

    return montar_grafo(
        registros,
        ctx.faixas_vigentes(),
        camadas=pedidas,
        teto_termos=teto_termos,
        eixo=eixo,
        fontes=ctx.banco.listar_fontes() if "proveniencia" in pedidas else (),
        importacoes=ctx.banco.listar_importacoes() if "proveniencia" in pedidas else (),
    )
```

Em `fraus/api/main.py`, acrescente `grafo` ao import de `fraus.api.rotas` e o
`include_router` na mesma ordem alfabética/agrupamento que os vizinhos já
usam.

- [ ] **Step 4: Rode a suíte inteira**

Run: `uv run pytest -q`
Expected: PASS — inclusive os testes de API que já existiam.

- [ ] **Step 5: Commit**

```bash
git add fraus/api/rotas/grafo.py fraus/api/main.py fraus/motor.py tests/test_api_grafo.py
git commit -m "feat(api): GET /grafo -- rota fina sobre o modulo puro"
```

---

### Task 7: A página `/grafo` — dados, estados e navegação (sem canvas ainda)

Entrega uma página completa e navegável, com estado vazio e de erro
funcionando. O canvas entra na Task 8; até lá a página lista os nós em texto —
o que também é o fallback acessível permanente.

**Files:**
- Modify: `dashboard/lib/api.ts` (tipos + `obterGrafo`, ao lado de
  `obterLexico`)
- Create: `dashboard/app/grafo/page.tsx`
- Create: `dashboard/components/grafo/ListaDeNos.tsx`
- Modify: `dashboard/components/shell/NavegacaoLateral.tsx` (constante
  `SECOES`)

**Interfaces:**
- Consumes: `GET /grafo` da Task 6; os helpers já existentes em
  `dashboard/lib/api.ts` (`proteger`, `buscar`, `queryDePeriodo` — todos
  privados no módulo, use-os de dentro dele) e
  `dashboard/lib/periodo.ts` (`lerPeriodo`, `paraQuery`).
- Produces:
  - `export type NoDoGrafo = { id: string; tipo: TipoDeNo; camada: Camada;
    rotulo: string; grau: number; score?: number | null; nota?: number | null;
    categoria?: Categoria | null; sem_sinal?: boolean }`
  - `export type ArestaDoGrafo = { de: string; para: string; tipo: string;
    peso: number }`
  - `export type Grafo = { nos: NoDoGrafo[]; arestas: ArestaDoGrafo[];
    meta: MetaDoGrafo }`
  - `export const obterGrafo = (de?, ate?, camadas?) => Promise<Resultado<Grafo>>`
  - Componente `ListaDeNos({ nos, aoSelecionar })` — a Task 8 o reusa como
    fallback `sr-only`.

- [ ] **Step 1: Escreva os tipos e o cliente da API**

Em `dashboard/lib/api.ts`, junto de `obterLexico`:

```ts
export type Camada = "lexico" | "dominio" | "proveniencia";

export type TipoDeNo =
  | "conversa"
  | "categoria"
  | "canal"
  | "desfecho"
  | "termo"
  | "emoji"
  | "feature"
  | "fonte"
  | "importacao";

export type NoDoGrafo = {
  id: string;
  tipo: TipoDeNo;
  camada: Camada;
  rotulo: string;
  grau: number;
  /**
   * Só existem em nós `conversa`, e `null` quer dizer SEM SINAL -- nunca zero.
   * Quem consumir isto com `?? 0` transforma "não se sabe" em "péssimo".
   */
  score?: number | null;
  nota?: number | null;
  categoria?: Categoria | null;
  sem_sinal?: boolean;
};

export type ArestaDoGrafo = {
  de: string;
  para: string;
  tipo: string;
  peso: number;
};

export type MetaDoGrafo = {
  camadas: Camada[];
  conversas: number;
  sem_sinal: number;
  termos_totais: number;
  termos_exibidos: number;
  truncado: boolean;
};

export type Grafo = {
  nos: NoDoGrafo[];
  arestas: ArestaDoGrafo[];
  meta: MetaDoGrafo;
};

export const obterGrafo = (de?: string | null, ate?: string | null) =>
  proteger(buscar<Grafo>(`/grafo${queryDePeriodo(de, ate)}`));
```

- [ ] **Step 2: Crie a lista de nós**

`dashboard/components/grafo/ListaDeNos.tsx`:

```tsx
"use client";

import type { NoDoGrafo } from "@/lib/api";

/**
 * Os nos em forma de LISTA -- o caminho de quem nao ve o canvas.
 *
 * O canvas e opaco para leitor de tela: ele e um bitmap, e nenhuma tecnologia
 * assistiva enxerga o que foi pintado nele. Sem esta lista a tela inteira
 * seria inacessivel por construcao, e este e um trabalho academico que sera
 * apresentado -- "a visualizacao nao e navegavel por teclado" e pergunta de
 * banca, nao detalhe.
 *
 * Ela nao e um consolo: seleciona o MESMO no que o clique no canvas
 * seleciona, abrindo a mesma ficha.
 */
export function ListaDeNos({
  nos,
  aoSelecionar,
}: {
  nos: NoDoGrafo[];
  aoSelecionar?: (no: NoDoGrafo) => void;
}) {
  return (
    <ul>
      {nos.map((no) => (
        <li key={no.id}>
          <button type="button" onClick={() => aoSelecionar?.(no)}>
            {no.rotulo} — {no.tipo}, {no.grau} conexões
            {no.sem_sinal ? ", sem sinal" : ""}
          </button>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 3: Crie a página**

`dashboard/app/grafo/page.tsx`. Abra `dashboard/app/modelo/page.tsx` antes e
siga a estrutura dele (cabeçalho, tratamento de `Resultado`, `EstadoVazio`):

```tsx
import { obterGrafo } from "@/lib/api";
import { lerPeriodo, paraQuery } from "@/lib/periodo";
import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { EstadoVazio } from "@/components/EstadoVazio";
import { ListaDeNos } from "@/components/grafo/ListaDeNos";

export const dynamic = "force-dynamic";

export default async function PaginaGrafo(props: PageProps<"/grafo">) {
  const parametros = await props.searchParams;
  const periodo = lerPeriodo(parametros);
  const grafo = await obterGrafo(periodo.de, periodo.ate);

  if (!grafo.ok) {
    return (
      <>
        <CabecalhoPagina titulo="Grafo da memória" />
        <EstadoVazio explicacao={grafo.erro} />
      </>
    );
  }

  if (grafo.dado.nos.length === 0) {
    return (
      <>
        <CabecalhoPagina titulo="Grafo da memória" />
        <EstadoVazio explicacao="Nenhuma conversa analisada ainda — importe um arquivo em Analisar para o grafo ter o que mostrar." />
      </>
    );
  }

  return (
    <>
      <CabecalhoPagina titulo="Grafo da memória" />
      <ListaDeNos nos={grafo.dado.nos} />
    </>
  );
}
```

**Confira a assinatura real** de `CabecalhoPagina` e `EstadoVazio` nos arquivos
deles antes de usar — se as props tiverem outros nomes, use os nomes de lá; não
mude os componentes para caber neste exemplo.

- [ ] **Step 4: Ponha na navegação**

Em `dashboard/components/shell/NavegacaoLateral.tsx`, acrescente à constante
`SECOES`, depois de `/modelo` (é tela de OLHAR, não de mexer — não vai no grupo
`AJUSTES`), importando o ícone `Share2` de `lucide-react`:

```tsx
  { href: "/grafo", rotulo: "Grafo", Icone: Share2 },
```

- [ ] **Step 5: Rode e veja no navegador**

```bash
cd dashboard && npm run lint && npx tsc --noEmit
```
Expected: sem erro.

Com a API no ar (`uv run uvicorn fraus.api.main:app` ou
`uv run python scripts/api_demo.py`) e `npm run dev`, abra
`http://localhost:3000/grafo`. Com banco vazio você deve ver o estado vazio com
o texto acionável — não uma tela em branco nem erro.

- [ ] **Step 6: Commit**

```bash
git add dashboard/lib/api.ts dashboard/app/grafo dashboard/components/grafo dashboard/components/shell/NavegacaoLateral.tsx
git commit -m "feat(dashboard): pagina /grafo com dados, estados e navegacao"
```

---

### Task 8: O canvas — notação, foco de camada e interação

**Files:**
- Modify: `dashboard/package.json` (dependência)
- Create: `dashboard/components/grafo/desenho.ts`
- Create: `dashboard/components/grafo/GrafoDaMemoria.tsx`
- Create: `dashboard/components/grafo/ReguaDeCamadas.tsx`
- Create: `dashboard/components/grafo/FichaDoNo.tsx`
- Modify: `dashboard/app/grafo/page.tsx` (troca `ListaDeNos` solta pelo
  `GrafoDaMemoria`)

**Interfaces:**
- Consumes: `Grafo`, `NoDoGrafo`, `ArestaDoGrafo`, `Camada` (Task 7);
  `ListaDeNos` (Task 7) como fallback `sr-only`.
- Produces: `GrafoDaMemoria({ grafo }: { grafo: Grafo })`,
  `NoPosicionado`, `desenharNo`, `raioDoNo`, `corDoNo`.

> **Esta é a única task com código em esboço, e é de propósito.** As sete
> anteriores trazem implementação completa porque a resposta certa delas é
> única. Esta é a superfície de DESIGN: cor exata, tipografia do rótulo,
> espessura da aresta e o enquadramento do painel se decidem olhando a tela,
> não escrevendo o arquivo no escuro. O que está travado aqui — cabeça vazada,
> raio por grau, foco que apaga em vez de remover, fallback `sr-only` — é
> requisito, não sugestão. O resto é ofício.

- [ ] **Step 1: Instale a dependência**

```bash
cd dashboard && npm install react-force-graph-2d
```

Confira que só ela entrou — se o `package.json` ganhar `three` ou `pixi.js`,
você instalou o pacote errado (é o `-2d`, não o `react-force-graph` guarda-chuva,
que arrasta as versões 3D/VR).

- [ ] **Step 2: Escreva a notação**

`dashboard/components/grafo/desenho.ts`. Leia `dashboard/DESIGN.md` §1 antes —
este arquivo é a aplicação daquele contrato ao canvas:

```ts
import type { NoDoGrafo, TipoDeNo } from "@/lib/api";

/**
 * O no COM as coordenadas que a simulacao escreve nele.
 *
 * `NoDoGrafo` e o contrato da API, e a API nao manda posicao -- quem cria `x`
 * e `y` e o force-graph, mutando o objeto durante a simulacao. Declarar isso
 * aqui, e nao no tipo da API, mantem honesto o que o servidor de fato devolve.
 */
export type NoPosicionado = NoDoGrafo & { x?: number; y?: number };

/**
 * Acima da linha o que foi DITO, abaixo o que foi MEDIDO (DESIGN.md §1).
 *
 * Num grafo nao ha "acima" e "abaixo" geometricos -- a simulacao coloca o no
 * onde a fisica manda. Entao a regra que aqui sobrevive e a CROMATICA: ambar
 * para o dito, azul para o medido. A posicao volta a valer nas outras telas.
 */
const DITO: TipoDeNo[] = ["conversa", "termo", "emoji"];

export function corDoNo(no: NoDoGrafo, temaClaro: boolean): string { /* ... */ }

/**
 * Raio pelo GRAU, nunca pelo score.
 *
 * Mapear score -> tamanho faria o no "sem sinal" encolher ate sumir, que e
 * violar por via visual a invariante que a cabeca vazada existe para honrar.
 * Tamanho e conectividade; o veredito mora no preenchimento.
 */
export function raioDoNo(no: NoDoGrafo): number {
  return 3 + Math.min(Math.sqrt(no.grau), 5);
}

/**
 * Desenha um no. Conversa SEM SINAL sai vazada -- so o contorno.
 *
 * E a mesma forma que `CabecasDeLeitura` usa na linha do tempo: a regra
 * "ausencia de dado nao e insatisfacao" deixa de ser nota de rodape e vira
 * notacao. O marcador existe, ocupa a posicao, e e oco.
 */
export function desenharNo(
  no: NoPosicionado,
  ctx: CanvasRenderingContext2D,
  escala: number,
  opacidade: number,
  selecionado: boolean,
): void {
  const raio = raioDoNo(no) + (selecionado ? 2 : 0);
  ctx.globalAlpha = opacidade;
  ctx.beginPath();
  ctx.arc(no.x ?? 0, no.y ?? 0, raio, 0, 2 * Math.PI);

  if (no.sem_sinal) {
    ctx.strokeStyle = corDoNo(no, false);
    ctx.lineWidth = 1.5 / escala;
    ctx.stroke();
  } else {
    ctx.fillStyle = corDoNo(no, false);
    ctx.fill();
  }

  // Label so com zoom: em milhares de nos, texto sempre visivel e mancha.
  if (escala > 1.5) { /* ... desenha o rotulo ... */ }
  ctx.globalAlpha = 1;
}
```

Complete `corDoNo` e o bloco de label lendo os tokens OKLCH de
`dashboard/app/globals.css` — **não invente cor nova**; use as variáveis que já
existem para âmbar, azul, `muted` e `foreground`.

- [ ] **Step 3: Escreva o componente do canvas**

`dashboard/components/grafo/GrafoDaMemoria.tsx`:

```tsx
"use client";

import dynamic from "next/dynamic";
import { useCallback, useMemo, useRef, useState } from "react";
import type { Camada, Grafo, NoDoGrafo } from "@/lib/api";
import { ListaDeNos } from "./ListaDeNos";
import { desenharNo } from "./desenho";

// `ssr: false` nao e permitido em Server Component no App Router -- e por
// isso que este arquivo e cliente e a pagina fica sendo servidor.
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => <div className="h-[70vh] w-full animate-pulse rounded-lg bg-muted" />,
});

export function GrafoDaMemoria({ grafo }: { grafo: Grafo }) {
  const [foco, setFoco] = useState<Camada | "todas">("todas");
  const [selecionado, setSelecionado] = useState<NoDoGrafo | null>(null);
  const [aceso, setAceso] = useState<string | null>(null);

  /**
   * Adjacencia pre-computada: o hover consulta em O(1).
   *
   * Varrer a lista de arestas a cada movimento do mouse faria a simulacao
   * engasgar justamente enquanto alguem explora -- que e o unico momento em
   * que a tela precisa responder rapido.
   */
  const vizinhos = useMemo(() => {
    const mapa = new Map<string, Set<string>>();
    for (const aresta of grafo.arestas) {
      if (!mapa.has(aresta.de)) mapa.set(aresta.de, new Set());
      if (!mapa.has(aresta.para)) mapa.set(aresta.para, new Set());
      mapa.get(aresta.de)!.add(aresta.para);
      mapa.get(aresta.para)!.add(aresta.de);
    }
    return mapa;
  }, [grafo.arestas]);

  /**
   * Opacidade do no: o foco de camada APAGA, nunca remove.
   *
   * Remover re-dispararia a simulacao e embaralharia o layout inteiro a cada
   * troca de camada -- a pessoa perderia a orientacao espacial que acabou de
   * construir. Apagando, as pontes ENTRE camadas continuam visiveis, que e o
   * motivo de o grafo ser um so em vez de tres abas.
   */
  const opacidadeDe = useCallback(
    (no: NoDoGrafo) => {
      if (foco !== "todas" && no.camada !== foco) return 0.08;
      if (aceso && aceso !== no.id && !vizinhos.get(aceso)?.has(no.id)) return 0.15;
      return 1;
    },
    [foco, aceso, vizinhos],
  );

  // ... ForceGraph2D com nodeCanvasObject={(no, ctx, escala) =>
  //     desenharNo(no, ctx, escala, opacidadeDe(no), no.id === selecionado?.id)}
  // ... nodePointerAreaPaint, linkColor usando a mesma opacidade das pontas,
  // ... onNodeHover={(no) => setAceso(no?.id ?? null)}
  // ... onNodeClick: setSelecionado + centerAt + zoom
  // ... cooldownTicks={grafo.nos.length > 1500 ? 60 : 200}
  // ... warmupTicks={20} d3VelocityDecay={0.3}
  // ... onEngineStop={() => refGrafo.current?.zoomToFit(400, 40)}
}
```

Complete o JSX. Requisitos que **não** são opcionais:

1. Um `useEffect` de montagem ajustando a física — `d3Force` só existe depois
   dela:
   ```tsx
   useEffect(() => {
     refGrafo.current?.d3Force("charge")?.strength(-120).distanceMax(400);
     refGrafo.current?.d3Force("link")?.distance(40);
   }, []);
   ```
2. `<div className="sr-only"><ListaDeNos nos={grafo.nos} aoSelecionar={setSelecionado} /></div>`
   — o fallback acessível, com a mesma seleção.
3. `<ReguaDeCamadas>` controlando `foco` e exibindo
   `{meta.termos_exibidos} de {meta.termos_totais} termos` com aviso visível
   quando `meta.truncado`.
4. `<FichaDoNo no={selecionado}>` no painel lateral. Para `tipo === "conversa"`,
   um `<Link href={`/atendimentos/${id}`}>`; e **`sem_sinal` mostra "sem sinal",
   nunca nota 0**.

- [ ] **Step 4: Verifique**

```bash
cd dashboard && npm run lint && npx tsc --noEmit && npm run build
```
Expected: build passa. Se o build quebrar com erro de `window is not defined`,
o `dynamic` com `ssr: false` não está no arquivo `"use client"` — corrija ali,
não com um `typeof window` espalhado.

Com a API no ar e dados importados, abra `/grafo` e confirme, um a um:
- hover acende a vizinhança e apaga o resto;
- clicar numa camada apaga as outras **sem** o layout se reorganizar;
- conversa sem sinal aparece **vazada**;
- a simulação **para** (o canvas fica estático depois de assentar);
- `Tab` chega nos botões da lista `sr-only` e selecionar por ali abre a ficha.

- [ ] **Step 5: Commit**

```bash
git add dashboard/package.json dashboard/package-lock.json dashboard/components/grafo dashboard/app/grafo
git commit -m "feat(dashboard): o canvas do grafo -- cabeca vazada, foco de camada e fallback acessivel"
```

---

## Verificação final

- [ ] `uv run pytest -q` — suíte inteira verde
- [ ] `cd dashboard && npm run lint && npx tsc --noEmit && npm run build`
- [ ] `grep -rn "?? 0\|(|| 0" dashboard/components/grafo dashboard/app/grafo` —
      nenhum resultado sobre score/nota (a invariante do "sem sinal")
- [ ] `grep -rn "Motor\|Classificador" fraus/grafo.py fraus/api/rotas/grafo.py` —
      nenhum resultado
- [ ] Atualizar o mapa de arquivos do `CLAUDE.md` com `fraus/grafo.py` e a rota
- [ ] Atualizar `docs/handoff.md` com o estado desta feature
