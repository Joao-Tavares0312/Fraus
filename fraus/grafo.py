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

    lexico = {"termos_totais": 0, "termos_exibidos": 0, "truncado": False}
    if "lexico" in camadas:
        lexico = _camada_lexico(montagem, registros, teto_termos)

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
