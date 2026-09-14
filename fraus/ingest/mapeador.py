"""Mapeador: tabela de estrutura desconhecida -> conversas canonicas.

Existe para que um export novo NAO exija um adaptador novo. Ate 14/09/2026 cada
estrutura de tabela pedia um modulo escrito a mao (`csv_driver`, `totalk`); o
mapeador descobre sozinho qual coluna faz qual papel, sem LLM (invariante 1):
cada decisao e uma regra que cabe numa frase.

COMO ELE DECIDE. Cada coluna recebe uma nota por papel, somando duas evidencias:

- **nome**: sinonimos pt/en normalizados (`body`, `mensagem`, `created_at`...),
  com `difflib` para a variacao de grafia;
- **conteudo**: numa amostra, a fracao que parseia como data, o comprimento e a
  variedade do texto, a quantidade de valores distintos, e se os valores
  repetidos aparecem em BLOCOS contiguos (id de conversa) ou alternados (autor).

Depois a atribuicao e gulosa pela maior nota, e duas colunas nunca ficam com o
mesmo papel. Nome sozinho engana (uma coluna "data" de cadastro); conteudo
sozinho tambem (autor e id tem cara parecida) -- por isso sao somados.

O QUE ELE INFERE E RELATADO, NUNCA CALADO. A armadilha da Totalk (MM/DD lido
como DD/MM espalhando mensagens por meses e a latencia saindo absurda sem erro)
e o modo de falha de qualquer inferencia silenciosa. Toda escolha -- coluna,
ordem da data, fuso assumido, quem e o cliente -- vira aviso na `Extracao`.

AS INVARIANTES QUE VALEM AQUI:

- sem coluna de data, `tem_tempo` e falso e a conversa NAO recebe nota
  (ver `fraus.ingest.transcricao` -- zero de latencia nao e neutro);
- data sem fuso ganha America/Sao_Paulo e AVISA (invariante 6);
- valor que nao parseia vira None e rejeita a LINHA, nunca zero;
- o texto passa por `censurar_pii` aqui, porque isto e uma porta de entrada.
"""

import hashlib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

from pydantic import ValidationError

from fraus.modelos import Autor, Conversa, Mensagem
from fraus.seguranca.pii import censurar_pii

# Mesmo raciocinio de `totalk.FUSO_PADRAO`: sem horario de verao desde 2019.
FUSO_PADRAO = timezone(timedelta(hours=-3))

AMOSTRA = 500

# Abaixo disto o papel nao e atribuido: melhor recusar dizendo o que faltou do
# que montar conversa com a coluna errada no lugar do texto.
CONFIANCA_MINIMA = 0.45

SINONIMOS: dict[str, tuple[str, ...]] = {
    "texto": ("texto", "mensagem", "message", "body", "content", "conteudo", "text",
              "msg", "fala", "comentario", "comment", "descricao"),
    "autor": ("autor", "author", "sender", "remetente", "from", "de", "quem", "enviado por",
              "quem enviou", "role", "papel", "tipo", "origem", "user", "usuario", "nome",
              "name", "direcao", "direction"),
    "enviada_em": ("data", "date", "hora", "time", "timestamp", "created_at", "sent_at",
                   "enviada_em", "datahora", "data hora", "criado em", "criada em", "em",
                   "created", "sent", "datetime", "horario"),
    "conversa_id": ("conversa", "conversa_id", "conversation", "conversation_id", "ticket",
                    "ticket_id", "chat", "chat_id", "sessao", "session", "session_id",
                    "atendimento", "protocolo", "thread", "thread_id", "caso", "case"),
    "canal": ("canal", "channel", "plataforma", "platform", "via", "source"),
}

OBRIGATORIOS = ("texto", "autor")

PAPEL_DO_AUTOR: dict[Autor, tuple[str, ...]] = {
    "cliente": ("cliente", "client", "customer", "consumidor", "usuario", "user", "visitante",
                "visitor", "contato", "contact", "lead", "end-user", "end_user", "requester",
                "solicitante", "inbound", "recebida", "entrada"),
    "bot": ("bot", "robo", "chatbot", "assistente", "assistant", "automacao", "automatico",
            "sistema", "system", "ia", "ai", "virtual", "auto"),
    "humano": ("atendente", "agente", "agent", "humano", "human", "operador", "operator",
               "suporte", "support", "analista", "consultor", "staff", "admin", "outbound",
               "enviada", "saida"),
}


ORDENS_DE_DATA = ("dia/mes", "mes/dia")


class MapeamentoInsuficienteError(ValueError):
    """Nao deu para achar os papeis obrigatorios. A mensagem diz o que se achou."""


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(texto).strip().lower())
    limpo = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r"[\s_\-/.]+", " ", limpo).strip()


def assinatura(colunas: list[str]) -> str:
    """Identidade de uma ESTRUTURA de arquivo: as colunas, sem ordem, caixa ou acento.

    E a chave do perfil de mapeamento. O mesmo sistema exporta sempre as mesmas
    colunas, entao o que o analista confirmou uma vez vale para o proximo
    arquivo dele -- e so para ele: um export com uma coluna a mais e outra
    estrutura, e cai de novo na inferencia em vez de herdar um mapa que talvez
    nao sirva.
    """
    chave = "|".join(sorted(_normalizar(c) for c in colunas))
    return hashlib.sha256(chave.encode("utf-8")).hexdigest()[:32]


# --- datas -------------------------------------------------------------------

_BARRA = re.compile(
    r"^(?P<a>\d{1,2})[/.-](?P<b>\d{1,2})[/.-](?P<ano>\d{2,4})"
    r"(?:[ ,T]+(?P<h>\d{1,2}):(?P<m>\d{2})(?::(?P<s>\d{2}))?\s*(?P<ampm>[APap]\.?[Mm]\.?)?)?$"
)
_EPOCH = re.compile(r"^\d{10}(?:\d{3})?$")


@dataclass
class RelatoDatas:
    ordem: str | None = None
    """'dia/mes', 'mes/dia' ou None quando nenhuma data tinha barra."""
    ambigua: bool = False
    fuso_assumido: bool = False
    avisos: list[str] = field(default_factory=list)


def _iso(valor: str) -> datetime | None:
    texto = valor.strip().replace("Z", "+00:00").replace("z", "+00:00")
    try:
        return datetime.fromisoformat(texto)
    except ValueError:
        return None


def _com_barra(achado: re.Match, dia_primeiro: bool) -> datetime | None:
    a, b, ano = int(achado["a"]), int(achado["b"]), int(achado["ano"])
    dia, mes = (a, b) if dia_primeiro else (b, a)
    if ano < 100:
        ano += 2000
    hora = int(achado["h"] or 0)
    if achado["ampm"]:
        tarde = achado["ampm"][0].lower() == "p"
        hora = hora % 12 + (12 if tarde else 0)
    try:
        return datetime(ano, mes, dia, hora, int(achado["m"] or 0), int(achado["s"] or 0))
    except ValueError:
        return None


def _saltos_para_tras(datas: list[datetime | None], grupos: list[str] | None) -> int:
    """Quantas vezes o relogio anda para tras na ordem do arquivo, por conversa."""
    ultimo: dict[str, datetime] = {}
    saltos = 0
    for indice, data in enumerate(datas):
        if data is None:
            continue
        grupo = grupos[indice] if grupos else ""
        if grupo in ultimo and data < ultimo[grupo]:
            saltos += 1
        ultimo[grupo] = data
    return saltos


def interpretar_datas(
    valores: list[str], grupos: list[str] | None = None, ordem: str | None = None
) -> tuple[list[datetime | None], RelatoDatas]:
    """Parseia uma COLUNA inteira de datas, decidindo a ordem pela coluna, nao pela celula.

    Decidir celula a celula e o erro classico: `03/05` sai maio numa linha e
    `25/05` sai invalido na outra. A ordem dia/mes contra mes/dia e decidida
    uma vez, nesta sequencia:

    1. um primeiro campo > 12 so pode ser dia; um segundo campo > 12, so dia
       tambem -- e o dado decidindo;
    2. se nada passa de 12, vence a leitura em que o relogio anda MENOS para
       tras dentro de cada conversa (mensagens de um atendimento sao gravadas
       em ordem);
    3. empate: dia/mes (o publico e brasileiro), marcado como ambiguo e avisado.

    `ordem` e a resposta de quem CONHECE o sistema de origem (confirmada na
    previa ou gravada no perfil) e encerra a questao antes das tres regras.
    """
    relato = RelatoDatas()
    achados = [_BARRA.match(v.strip()) for v in valores]
    com_barra = [a for a in achados if a]

    dia_primeiro = True
    if com_barra and ordem in ORDENS_DE_DATA:
        dia_primeiro = ordem == "dia/mes"
        relato.ordem = ordem
    elif com_barra:
        primeiro_grande = any(int(a["a"]) > 12 for a in com_barra)
        segundo_grande = any(int(a["b"]) > 12 for a in com_barra)
        if primeiro_grande and not segundo_grande:
            dia_primeiro = True
        elif segundo_grande and not primeiro_grande:
            dia_primeiro = False
        else:
            relato.ambigua = True
            opcoes = {
                ordem: [_com_barra(a, ordem) if a else None for a in achados]
                for ordem in (True, False)
            }
            saltos = {ordem: _saltos_para_tras(d, grupos) for ordem, d in opcoes.items()}
            if saltos[False] < saltos[True]:
                dia_primeiro = False
                relato.avisos.append(
                    "Datas ambíguas (nenhum campo passa de 12): li como mês/dia porque "
                    "é a leitura em que as mensagens ficam em ordem. Confira."
                )
            elif saltos[True] < saltos[False]:
                relato.avisos.append(
                    "Datas ambíguas (nenhum campo passa de 12): li como dia/mês porque "
                    "é a leitura em que as mensagens ficam em ordem. Confira."
                )
            else:
                relato.avisos.append(
                    "Datas ambíguas (nenhum campo passa de 12) e a ordem das mensagens não "
                    "desempata: assumi dia/mês. Se o sistema de origem é americano, a "
                    "latência desta análise está errada."
                )
        relato.ordem = "dia/mes" if dia_primeiro else "mes/dia"

    datas: list[datetime | None] = []
    for valor, achado in zip(valores, achados):
        texto = valor.strip()
        if achado:
            data = _com_barra(achado, dia_primeiro)
        elif _EPOCH.match(texto):
            numero = int(texto)
            data = datetime.fromtimestamp(numero / 1000 if len(texto) == 13 else numero, timezone.utc)
        else:
            data = _iso(texto) if texto else None
        if data is not None and data.tzinfo is None:
            data = data.replace(tzinfo=FUSO_PADRAO)
            relato.fuso_assumido = True
        datas.append(data)

    if relato.fuso_assumido:
        relato.avisos.append(
            "As datas não declaram fuso: assumi America/Sao_Paulo (-03:00). Isso não "
            "muda a latência, mas muda o dia em que cada conversa cai na série."
        )
    return datas, relato


# --- notas por papel ---------------------------------------------------------


def _nota_nome(coluna: str, papel: str) -> float:
    nome = _normalizar(coluna)
    ultimo = nome.split(" ")[-1] if nome else ""
    melhor = 0.0
    for sinonimo in SINONIMOS[papel]:
        if nome == sinonimo:
            return 1.0
        if sinonimo in nome.split(" ") or ultimo == sinonimo:
            melhor = max(melhor, 0.8)
        elif len(sinonimo) >= 4 and sinonimo in nome:
            melhor = max(melhor, 0.7)
        elif SequenceMatcher(None, nome, sinonimo).ratio() >= 0.85:
            melhor = max(melhor, 0.6)
    return melhor


def _papel_do_valor(valor: str) -> Autor | None:
    limpo = _normalizar(valor)
    for papel, formas in PAPEL_DO_AUTOR.items():
        for forma in formas:
            if limpo == forma or limpo.startswith(forma + " ") or limpo.endswith(" " + forma):
                return papel
    return None


@dataclass
class _Perfil:
    frac_data: float
    comprimento_medio: float
    frac_distintos: float
    distintos: int
    frac_letras: float
    em_blocos: bool
    frac_papel_reconhecido: float


def _perfil(valores: list[str]) -> _Perfil:
    cheios = [v for v in valores if v.strip()]
    if not cheios:
        return _Perfil(0, 0, 0, 0, 0, False, 0)
    datas, _ = interpretar_datas(cheios)
    contagem = Counter(cheios)
    corridas = 1 + sum(1 for a, b in zip(cheios, cheios[1:]) if a != b)
    caracteres = "".join(cheios)
    return _Perfil(
        frac_data=sum(d is not None for d in datas) / len(cheios),
        comprimento_medio=sum(len(v) for v in cheios) / len(cheios),
        frac_distintos=len(contagem) / len(cheios),
        distintos=len(contagem),
        frac_letras=sum(c.isalpha() for c in caracteres) / max(len(caracteres), 1),
        em_blocos=len(contagem) < len(cheios) and corridas == len(contagem),
        frac_papel_reconhecido=sum(_papel_do_valor(v) is not None for v in cheios) / len(cheios),
    )


def _nota_conteudo(perfil: _Perfil, papel: str) -> float:
    if papel == "enviada_em":
        return perfil.frac_data
    if perfil.frac_data > 0.8:
        return 0.0
    if papel == "texto":
        comprimento = min(perfil.comprimento_medio / 25, 1.0)
        return comprimento * 0.5 + perfil.frac_distintos * 0.3 + perfil.frac_letras * 0.2
    if papel == "autor":
        if perfil.frac_papel_reconhecido > 0.5:
            return 0.6 + 0.4 * perfil.frac_papel_reconhecido
        curto = 1.0 if perfil.comprimento_medio <= 30 else 0.3
        repete = 1.0 if 2 <= perfil.distintos and perfil.frac_distintos <= 0.7 else 0.2
        return 0.45 * curto * repete * (0.5 if perfil.em_blocos else 1.0)
    if papel == "conversa_id":
        if perfil.frac_papel_reconhecido > 0.5 or perfil.distintos < 1:
            return 0.0
        base = 0.7 if perfil.em_blocos else 0.15
        return base * (1.0 if perfil.comprimento_medio <= 60 else 0.3)
    if papel == "canal":
        return 0.3 if perfil.distintos <= 5 and perfil.frac_distintos < 0.2 else 0.0
    return 0.0


# Papel sem nome casado precisa de conteudo MUITO claro: canal e conversa_id
# sao opcionais, e um id errado junta conversas diferentes numa so.
_SO_POR_CONTEUDO = {"texto": 0.9, "autor": 1.0, "enviada_em": 0.9, "conversa_id": 0.8, "canal": 0.0}


@dataclass
class PapelAtribuido:
    coluna: str
    indice: int
    confianca: float
    motivo: str


@dataclass
class Mapeamento:
    papeis: dict[str, PapelAtribuido]
    colunas: list[str]
    ordem_data: str | None = None
    data_ambigua: bool = False

    def coluna(self, papel: str) -> str | None:
        atribuido = self.papeis.get(papel)
        return atribuido.coluna if atribuido else None


def mapear(colunas: list[str], linhas: list[list[str]]) -> Mapeamento:
    amostra = linhas[:AMOSTRA]
    perfis = [
        _perfil([linha[i] if i < len(linha) else "" for linha in amostra])
        for i in range(len(colunas))
    ]

    candidatos: list[tuple[float, str, int, str]] = []
    for indice, coluna in enumerate(colunas):
        for papel in SINONIMOS:
            nome = _nota_nome(coluna, papel)
            conteudo = _nota_conteudo(perfis[indice], papel)
            if nome > 0:
                # Nome casado so vale se o conteudo nao desmentir.
                nota = 0.5 * nome + 0.5 * conteudo if conteudo > 0.1 else nome * 0.3
                motivo = "pelo nome e pelo conteúdo" if conteudo > 0.1 else "só pelo nome"
            else:
                nota = conteudo * _SO_POR_CONTEUDO[papel]
                motivo = "só pelo conteúdo"
            if nota >= CONFIANCA_MINIMA:
                candidatos.append((nota, papel, indice, motivo))

    papeis: dict[str, PapelAtribuido] = {}
    usadas: set[int] = set()
    for nota, papel, indice, motivo in sorted(candidatos, key=lambda c: -c[0]):
        if papel in papeis or indice in usadas:
            continue
        papeis[papel] = PapelAtribuido(colunas[indice], indice, round(min(nota, 1.0), 2), motivo)
        usadas.add(indice)
    return Mapeamento(papeis=papeis, colunas=list(colunas))


# --- conversao ---------------------------------------------------------------


@dataclass
class ResultadoMapeado:
    conversas: list[Conversa]
    tem_tempo: bool
    avisos: list[str]
    rejeitadas: list[dict]
    mapeamento: Mapeamento


def _decidir_autores(
    valores: list[str], grupos: list[str]
) -> tuple[dict[str, Autor], list[str]]:
    """Cada valor distinto da coluna de autor -> cliente, bot ou humano.

    Valor reconhecido (`customer`, `Atendente`, `bot`) decide sozinho. Nome de
    pessoa nao diz nada, e ai entram duas regras, nesta ordem:

    - com varias conversas, o lado da EMPRESA e quem aparece em muitas delas
      (a mesma atendente, a mesma conta) e o cliente e quem aparece em poucas;
    - com uma conversa so, o cliente e quem ABRE -- em atendimento, quem
      procura e o cliente.

    Nome nao reconhecido do lado da empresa vira `humano`, nao `bot`: sem
    evidencia de automacao, supor bot inflaria a contencao, que e indicador.
    As duas regras sao heuristica e o resultado e avisado nome a nome.
    """
    papeis: dict[str, Autor] = {}
    desconhecidos: list[str] = []
    for valor in dict.fromkeys(v for v in valores if v.strip()):
        papel = _papel_do_valor(valor)
        if papel:
            papeis[valor] = papel
        else:
            desconhecidos.append(valor)
    if not desconhecidos:
        return papeis, []

    conversas_por_valor: dict[str, set[str]] = {}
    abre: Counter[str] = Counter()
    vistas: set[str] = set()
    for valor, grupo in zip(valores, grupos):
        conversas_por_valor.setdefault(valor, set()).add(grupo)
        if grupo not in vistas:
            vistas.add(grupo)
            abre[valor] += 1

    total = len(vistas)
    clientes, empresa = [], []
    for valor in desconhecidos:
        if total > 1:
            e_cliente = len(conversas_por_valor[valor]) <= max(1, total // 2)
        else:
            e_cliente = abre[valor] > 0
        papeis[valor] = "cliente" if e_cliente else "humano"
        (clientes if e_cliente else empresa).append(valor)

    avisos = []
    regra = (
        "quem aparece em poucas conversas é cliente; quem aparece em muitas é da empresa"
        if total > 1 else "quem abre a conversa é o cliente"
    )
    avisos.append(
        f"Inferi quem é cliente pelo nome ({regra}). Clientes: "
        f"{', '.join(clientes[:5]) or 'nenhum'}; atendentes: {', '.join(empresa[:5]) or 'nenhum'}."
    )
    return papeis, avisos


def _aplicar_forcado(mapa: Mapeamento, forcado: dict[str, str | None]) -> None:
    """O que o analista confirmou vence a heuristica, papel a papel.

    `None` num papel quer dizer "este arquivo nao tem essa coluna" -- e diferente
    de o papel nao aparecer, que deixa a inferencia decidir. Coluna que nao
    existe no arquivo e recusa nomeando, nunca papel descartado em silencio:
    um perfil velho aplicado a um export que renomeou a coluna precisa falhar
    alto, nao montar conversa sem texto.
    """
    for papel, coluna in forcado.items():
        if papel not in SINONIMOS:
            raise MapeamentoInsuficienteError(
                f"papel desconhecido no mapeamento: '{papel}'. Papéis: {', '.join(SINONIMOS)}."
            )
        if coluna is None:
            mapa.papeis.pop(papel, None)
            continue
        if coluna not in mapa.colunas:
            raise MapeamentoInsuficienteError(
                f"o mapeamento aponta {papel} para a coluna '{coluna}', que não existe "
                f"neste arquivo. Colunas: {', '.join(mapa.colunas[:12])}."
            )
        for outro, atribuido in list(mapa.papeis.items()):
            if atribuido.coluna == coluna and outro != papel:
                del mapa.papeis[outro]
        mapa.papeis[papel] = PapelAtribuido(coluna, mapa.colunas.index(coluna), 1.0, "confirmado")


def converter(
    colunas: list[str],
    linhas: list[list[str]],
    origem: str,
    forcado: dict[str, str | None] | None = None,
    ordem_data: str | None = None,
) -> ResultadoMapeado:
    if not linhas:
        raise MapeamentoInsuficienteError(f"{origem} não tem linhas depois do cabeçalho.")
    mapa = mapear(colunas, linhas)
    if forcado:
        _aplicar_forcado(mapa, forcado)

    faltando = [papel for papel in OBRIGATORIOS if papel not in mapa.papeis]
    if faltando:
        achados = ", ".join(
            f"{p} → '{a.coluna}'" for p, a in mapa.papeis.items()
        ) or "nenhum papel"
        raise MapeamentoInsuficienteError(
            f"não consegui descobrir a(s) coluna(s) de {', '.join(faltando)} em {origem}. "
            f"Reconheci: {achados}. Colunas do arquivo: "
            f"{', '.join(colunas[:12])}{'…' if len(colunas) > 12 else ''}. "
            "Renomeie a coluna da fala para 'texto' e a de quem falou para 'autor'."
        )

    def valor(linha: list[str], papel: str) -> str:
        atribuido = mapa.papeis.get(papel)
        if atribuido is None or atribuido.indice >= len(linha):
            return ""
        return linha[atribuido.indice].strip()

    grupos = [valor(l, "conversa_id") or "conversa" for l in linhas]
    def _descrever(papel: str, a: PapelAtribuido) -> str:
        # Coluna confirmada nao leva numero: a nota e da heuristica, e quem
        # decidiu foi o analista -- exibir "1,00" fingiria uma medicao.
        if a.motivo == "confirmado":
            return f"{papel} ← '{a.coluna}'"
        return f"{papel} ← '{a.coluna}' ({a.confianca:.2f}, {a.motivo})".replace(".", ",", 1)

    confirmadas = all(a.motivo == "confirmado" for a in mapa.papeis.values())
    avisos = [
        ("Colunas confirmadas: " if confirmadas else "Colunas inferidas: ")
        + "; ".join(_descrever(p, a) for p, a in mapa.papeis.items()) + "."
    ]

    tem_tempo = "enviada_em" in mapa.papeis
    if tem_tempo:
        datas, relato = interpretar_datas(
            [valor(l, "enviada_em") for l in linhas], grupos, ordem_data
        )
        avisos.extend(relato.avisos)
        mapa.ordem_data, mapa.data_ambigua = relato.ordem, relato.ambigua
    else:
        inicio = datetime.now(timezone.utc).replace(microsecond=0)
        datas = [inicio + timedelta(seconds=i) for i in range(len(linhas))]
        avisos.append(
            "Não achei coluna de data: sem horário não há latência, e latência é "
            "feature do fusor. Estas conversas NÃO recebem nota — só a leitura por mensagem."
        )
    if "conversa_id" not in mapa.papeis:
        avisos.append("Não achei coluna de conversa: o arquivo inteiro virou uma conversa só.")

    autores, avisos_autor = _decidir_autores([valor(l, "autor") for l in linhas], grupos)
    avisos.extend(avisos_autor)

    por_conversa: dict[str, list[Mensagem]] = {}
    canais: dict[str, str] = {}
    rejeitadas: list[dict] = []
    for numero, (linha, grupo, data) in enumerate(zip(linhas, grupos, datas), start=2):
        texto = valor(linha, "texto")
        if not texto:
            rejeitadas.append({"numero_linha": numero, "motivo": "texto vazio"})
            continue
        if data is None:
            rejeitadas.append({
                "numero_linha": numero,
                "motivo": f"data ilegível na coluna '{mapa.coluna('enviada_em')}'",
            })
            continue
        autor = autores.get(valor(linha, "autor"))
        if autor is None:
            rejeitadas.append({"numero_linha": numero, "motivo": "autor vazio"})
            continue
        try:
            mensagem = Mensagem(autor=autor, texto=censurar_pii(texto), enviada_em=data)
        except ValidationError as erro:
            campos = ", ".join(str(e["loc"][0]) for e in erro.errors() if e.get("loc"))
            rejeitadas.append({"numero_linha": numero, "motivo": f"inválida em: {campos}"})
            continue
        por_conversa.setdefault(grupo, []).append(mensagem)
        canais.setdefault(grupo, valor(linha, "canal").lower() or origem.lower())

    conversas = []
    for grupo, mensagens in por_conversa.items():
        mensagens.sort(key=lambda m: m.enviada_em)
        conversas.append(Conversa(
            id=grupo[:80],
            canal=canais[grupo],
            iniciada_em=mensagens[0].enviada_em,
            encerrada_em=mensagens[-1].enviada_em,
            escalou_para_humano=any(m.autor == "humano" for m in mensagens),
            mensagens=mensagens,
        ))
    if not conversas:
        raise MapeamentoInsuficienteError(
            f"mapeei as colunas de {origem}, mas nenhuma linha virou mensagem válida "
            f"({len(rejeitadas)} rejeitada(s); a primeira: {rejeitadas[0]['motivo'] if rejeitadas else '—'})."
        )
    return ResultadoMapeado(conversas, tem_tempo, avisos, rejeitadas, mapa)
