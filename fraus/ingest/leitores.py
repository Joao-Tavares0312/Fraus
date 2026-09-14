"""Leitores: bytes de um formato qualquer -> tabela (colunas e linhas de texto).

O leitor NAO sabe o que e conversa. Ele so resolve o que e do formato --
codificacao, delimitador, aninhamento de JSON, cabecalho de linha do WhatsApp --
e entrega uma tabela plana. Dar sentido as colunas e trabalho de
`fraus.ingest.mapeador`. A separacao e o que permite um formato novo sem
adaptador novo: leitor e por FORMATO (poucos, estaveis), mapeamento e por
ESTRUTURA (infinitas, e o mapeador as descobre).

Sem dependencia nova de proposito: `csv`, `json` e `re` da biblioteca padrao
fazem o trabalho, e cada heuristica cabe numa explicacao de banca. As
alternativas avaliadas (CleverCSV, charset-normalizer) ficam como proximo passo
se um arquivo real vencer estas regras -- ver o road map no README.
"""

import csv
import io
import json
import re
from collections import Counter

Tabela = tuple[list[str], list[list[str]]]

DELIMITADORES = (",", ";", "\t", "|")

# utf-8 primeiro porque ele FALHA alto em byte invalido; cp1252 e o export de
# Windows (Excel pt-BR), e cobre as aspas curvas que o latin-1 puro nao tem.
# latin-1 nunca falha -- e a rede, nao a escolha.
CODIFICACOES = ("utf-8-sig", "cp1252", "latin-1")


def decodificar(dados: bytes) -> tuple[str, str]:
    """Texto e o nome da codificacao usada -- o nome vai para o relato."""
    for codificacao in CODIFICACOES:
        try:
            texto = dados.decode(codificacao)
        except UnicodeDecodeError:
            continue
        return texto, "utf-8" if codificacao == "utf-8-sig" else codificacao
    raise UnicodeDecodeError("latin-1", dados, 0, 1, "inalcancavel")  # pragma: no cover


def detectar_delimitador(texto: str, amostra: int = 50) -> str:
    """O delimitador que produz o numero de colunas mais CONSISTENTE.

    `csv.Sniffer` erra justamente o caso que importa aqui -- virgula dentro de
    texto de mensagem entre aspas contra `;` do Excel brasileiro. A regra: para
    cada candidato, parseia a amostra respeitando aspas e mede quantas linhas
    tem a largura mais comum; vence o que tem mais colunas nessa largura
    dominante, desde que ela seja maior que 1.
    """
    linhas = [l for l in texto.splitlines()[:amostra] if l.strip()]
    melhor, melhor_nota = ",", (0.0, 0)
    for candidato in DELIMITADORES:
        larguras = [len(l) for l in csv.reader(io.StringIO("\n".join(linhas)), delimiter=candidato)]
        if not larguras:
            continue
        largura, vezes = Counter(larguras).most_common(1)[0]
        if largura < 2:
            continue
        nota = (vezes / len(larguras), largura)
        if nota > melhor_nota:
            melhor, melhor_nota = candidato, nota
    return melhor


def tabela_de_csv(texto: str) -> tuple[Tabela, str]:
    delimitador = detectar_delimitador(texto)
    linhas = [
        [c.strip() for c in linha]
        for linha in csv.reader(io.StringIO(texto, newline=""), delimiter=delimitador)
        if any(c.strip() for c in linha)
    ]
    if not linhas:
        return ([], []), delimitador
    return (linhas[0], linhas[1:]), delimitador


# --- JSON --------------------------------------------------------------------


def _achatar(objeto: dict, prefixo: str = "") -> dict[str, str]:
    """`{"autor": {"tipo": "bot"}}` -> `{"autor.tipo": "bot"}`. Lista vira texto."""
    plano: dict[str, str] = {}
    for chave, valor in objeto.items():
        nome = f"{prefixo}{chave}"
        if isinstance(valor, dict):
            plano.update(_achatar(valor, nome + "."))
        elif isinstance(valor, list):
            if all(not isinstance(v, (dict, list)) for v in valor):
                plano[nome] = ", ".join("" if v is None else str(v) for v in valor)
        else:
            plano[nome] = "" if valor is None else str(valor)
    return plano


def _listas_de_registros(no, caminho: str, herdado: dict[str, str], saida: dict) -> None:
    """Junta, por caminho, toda lista de objetos -- carregando os escalares dos pais.

    Export de atendimento quase sempre aninha: conversa -> mensagens. A lista de
    MENSAGENS e a mais longa quando somada entre todas as conversas, e o id da
    conversa mora no pai. Por isso cada registro herda os escalares dos
    ancestrais, prefixados pelo caminho (`conversas.id`).
    """
    if isinstance(no, list):
        objetos = [item for item in no if isinstance(item, dict)]
        if objetos:
            saida.setdefault(caminho, []).extend({**herdado, **_achatar(o)} for o in objetos)
            for objeto in objetos:
                escalares = {
                    f"{caminho}.{k}" if caminho else k: v
                    for k, v in _achatar(objeto).items()
                }
                for chave, filho in objeto.items():
                    if isinstance(filho, (list, dict)):
                        sub = f"{caminho}.{chave}" if caminho else chave
                        _listas_de_registros(filho, sub, {**herdado, **escalares}, saida)
    elif isinstance(no, dict):
        for chave, filho in no.items():
            if isinstance(filho, (list, dict)):
                sub = f"{caminho}.{chave}" if caminho else chave
                _listas_de_registros(filho, sub, herdado, saida)


def tabela_de_json(texto: str) -> Tabela:
    """JSON (objeto ou lista) ou JSON Lines -> a maior lista de registros, achatada."""
    try:
        raiz = json.loads(texto)
    except json.JSONDecodeError:
        raiz = [json.loads(linha) for linha in texto.splitlines() if linha.strip()]

    grupos: dict[str, list[dict[str, str]]] = {}
    _listas_de_registros(raiz, "", {}, grupos)
    if not grupos:
        return [], []
    registros = max(grupos.values(), key=len)

    colunas: list[str] = []
    for registro in registros:
        for chave in registro:
            if chave not in colunas:
                colunas.append(chave)
    return colunas, [[registro.get(c, "") for c in colunas] for registro in registros]


# --- WhatsApp ----------------------------------------------------------------

# Os dois cabecalhos do "Exportar conversa": Android (`14/05/2026 10:00 - Nome:`)
# e iOS (`[14/05/2026, 10:00:30] Nome:`). Escrito aqui e nao importado do
# whatstk porque ele e GPL-3.0 -- a licenca contaminaria o projeto.
CABECALHO_WHATSAPP = re.compile(
    r"^‎?\[?(?P<data>\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}),?\s+"
    r"(?P<hora>\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap]\.?[Mm]\.?)?)\]?\s*(?:-\s*)?"
    r"(?P<autor>[^:]{1,60}?):\s(?P<texto>.*)$"
)

# Fracao minima de linhas com cabecalho para o texto ser tratado como WhatsApp.
# Mensagem longa quebra em varias linhas sem cabecalho, entao nao pode ser 100%.
FRACAO_MINIMA_WHATSAPP = 0.5


def tabela_de_whatsapp(texto: str) -> Tabela | None:
    """Export de conversa do WhatsApp -> tabela, ou None se nao for um."""
    linhas = [l for l in texto.splitlines() if l.strip()]
    if not linhas:
        return None
    registros: list[list[str]] = []
    com_cabecalho = 0
    for linha in linhas:
        achado = CABECALHO_WHATSAPP.match(linha.strip())
        if achado:
            com_cabecalho += 1
            registros.append([
                f"{achado['data']} {achado['hora']}",
                achado["autor"].strip(),
                achado["texto"].strip(),
            ])
        elif registros:
            # Linha solta e continuacao da mensagem anterior, como na transcricao.
            registros[-1][2] = f"{registros[-1][2]}\n{linha.strip()}"
    if com_cabecalho / len(linhas) < FRACAO_MINIMA_WHATSAPP:
        return None
    return ["data", "autor", "mensagem"], registros
