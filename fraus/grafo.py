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
  - `importacao -> conversa` e `importacao -> canal`: o schema nao guarda
    vinculo nenhum de importacao com canal ou conversa (spec 2.0) -- o no
    `importacao` existe solto, sem aresta.
"""

from collections import Counter
from collections.abc import Sequence

from fraus.indicadores import nota_0_10
from fraus.modelos import Conversa
from fraus.resumo import desfecho
from fraus.sinais.emoji import emojis_com_posicao
from fraus.sinais.palavras import contar_palavras

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


def _no_conversa(montagem: _Montagem, conversa: Conversa, score: float | None, faixas: dict) -> str:
    """Cria (ou recupera) o no `conversa`, sempre com o mesmo schema.

    O no `conversa` e a ponte entre as camadas -- `_camada_dominio` e
    `_camada_lexico` chamam este helper. `_Montagem.no` so grava os `extras`
    na PRIMEIRA criacao do id; se cada camada montasse os seus proprios
    campos, o shape do no dependeria de qual camada rodou primeiro, e ponte
    com schema variavel e pior que ponte nenhuma.
    """
    categoria = _categoria_de(score, faixas)
    return montagem.no(
        "conversa",
        conversa.id,
        "dominio",
        f"Atendimento {conversa.id}",
        score=score,
        nota=None if score is None else nota_0_10(score),
        categoria=categoria,
        sem_sinal=score is None,
    )


def _no_canal(montagem: _Montagem, canal: str) -> str:
    """Cria (ou recupera) o no `canal`, sempre com `camada: "dominio"`.

    `_camada_dominio` e `_camada_proveniencia` ligam nele, e `_Montagem.no` so
    grava a `camada` na PRIMEIRA criacao do id -- sem este helper, quem
    rodasse primeiro decidia se o canal e "dominio" ou "proveniencia", bug de
    ordem de execucao. O canal e sempre do dominio (e onde o atendimento
    chegou); a proveniencia so se pendura nele, nao o redefine.
    """
    return montagem.no("canal", canal, "dominio", canal)


def _camada_dominio(montagem: _Montagem, registros: list, faixas: dict) -> None:
    for conversa, score in registros:
        categoria = _categoria_de(score, faixas)
        conversa_id = _no_conversa(montagem, conversa, score, faixas)
        if categoria is not None:
            montagem.aresta(
                conversa_id,
                montagem.no("categoria", categoria, "dominio", categoria.capitalize()),
                "classificada",
            )
        montagem.aresta(
            conversa_id,
            _no_canal(montagem, conversa.canal),
            "chegou_por",
        )
        fim = desfecho(conversa)
        montagem.aresta(
            conversa_id,
            montagem.no("desfecho", fim, "dominio", fim.replace("_", " ")),
            "terminou_em",
        )


def _camada_lexico(montagem: _Montagem, registros: list, teto_termos: int, faixas: dict) -> dict:
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

    for conversa, score in registros:
        conversa_id = _no_conversa(montagem, conversa, score, faixas)
        for termo, ocorrencias in por_conversa[conversa.id].items():
            if termo not in sobreviventes:
                continue
            montagem.aresta(
                conversa_id,
                montagem.no("termo", termo, "lexico", termo),
                "ativou",
                peso=ocorrencias,
            )
        # Agregado como o termo: emoji repetido 3x vira UMA aresta de peso 3,
        # nao 3 arestas de peso 1 -- o grau do no e o raio dele na tela, e
        # inflar arestas infla o desenho sem acrescentar informacao nova. A
        # posicao relativa que `emojis_com_posicao` devolve fica descartada
        # aqui: o grafo nao usa posicao, so contagem.
        emojis_da_conversa: Counter = Counter()
        for mensagem in conversa.mensagens_cliente:
            for emoji, _posicao in emojis_com_posicao(mensagem.texto):
                emojis_da_conversa[emoji] += 1
        for emoji, ocorrencias in emojis_da_conversa.items():
            montagem.aresta(
                conversa_id,
                montagem.no("emoji", emoji, "lexico", emoji),
                "ativou",
                peso=ocorrencias,
            )

    return {
        "termos_totais": len(contagem_global),
        "termos_exibidos": len(sobreviventes),
        "truncado": len(contagem_global) > len(sobreviventes),
    }


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


def _camada_proveniencia(montagem: _Montagem, fontes: list[dict], importacoes: list[dict]) -> None:
    """De onde o dado veio -- ate onde o schema deixa afirmar.

    `fontes_integracao` compartilha o campo `canal`, entao `fonte -> canal` e
    honesto. `importacoes`, porem, NAO tem coluna `canal` nem qualquer outra
    apontando para `conversas` (confira `fraus/db.py`) -- nao existe vinculo
    nenhum entre uma importacao e um canal. O no `importacao` continua
    aparecendo, com o arquivo e as aceitas no rotulo, mas fica SOLTO: ligar a
    "todo canal que existir no grafo" seria produto cartesiano de arestas
    falsas, nao informacao. Rastrear origem por conversa e migracao de schema
    (`conversas.importacao_id` + backfill), registrada como decisao propria
    fora deste escopo na spec (2.0) -- nao se inventa vinculo para o desenho
    ficar bonito.
    """
    for fonte in fontes:
        montagem.aresta(
            montagem.no("fonte", str(fonte["id"]), "proveniencia", fonte["nome"]),
            _no_canal(montagem, fonte["canal"]),
            "alimenta_canal",
        )

    for importacao in importacoes:
        rotulo = f"{importacao['arquivo']} ({importacao['aceitas']} aceitas)"
        montagem.no("importacao", str(importacao["id"]), "proveniencia", rotulo)


def montar_grafo(
    registros: list[tuple[Conversa, float | None]],
    faixas: dict,
    *,
    camadas: frozenset[str] = TODAS_AS_CAMADAS,
    teto_termos: int = TETO_TERMOS_PADRAO,
    eixo: dict[str, float] | None = None,
    fontes: Sequence[dict] = (),
    importacoes: Sequence[dict] = (),
) -> dict:
    """Nos, arestas e metadados do recorte pedido.

    `faixas` vem da configuracao vigente (nunca de uma copia local): a
    categoria do no e a MESMA que `/conversas` e `/indicadores` devolvem, e
    duplicar a faixa aqui ja foi defeito deste projeto uma vez.
    """
    montagem = _Montagem()

    if "dominio" in camadas:
        _camada_dominio(montagem, registros, faixas)

    lexico = {"termos_totais": 0, "termos_exibidos": 0, "truncado": False}
    if "lexico" in camadas:
        lexico = _camada_lexico(montagem, registros, teto_termos, faixas)

    # A aresta feature->categoria atravessa camadas: sem "dominio" pedido, o
    # no `categoria` nao existe, e a aresta nao tem onde chegar -- emiti-la
    # mesmo assim vazaria dado da camada dominio para um pedido que a excluiu
    # de proposito (camadas=lexico so, que e o que a rota sempre chama junto
    # de eixo).
    if "lexico" in camadas and "dominio" in camadas and eixo:
        _camada_features(montagem, eixo, faixas)

    if "proveniencia" in camadas:
        _camada_proveniencia(montagem, list(fontes), list(importacoes))

    return {
        "nos": montagem.nos,
        "arestas": montagem.arestas,
        "meta": {
            "camadas": sorted(camadas),
            "conversas": len(registros),
            "sem_sinal": sum(1 for _, score in registros if score is None),
            **lexico,
        },
    }
