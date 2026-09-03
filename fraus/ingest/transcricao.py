"""Le uma transcricao em prosa -- o que sai de um .docx ou .pdf.

A DIFERENCA QUE GOVERNA ESTE MODULO: um CSV traz o instante de cada mensagem;
uma transcricao colada num Word quase nunca traz. E latencia e FEATURE do
fusor, com peso aprendido -- `latencia_mediana_s`, `latencia_p90_s`,
`latencia_primeira_resposta_s`, `duracao_total_s`.

Sem horario, o caminho facil seria preencher esses campos com zero. Zero nao e
neutro: o fusor aprendeu que resposta rapida acompanha cliente satisfeito,
entao uma conversa sem horario entraria como se TODA resposta tivesse sido
instantanea, e sairia com nota mais alta do que merece. Nao daria erro nenhum
-- so um numero melhor do que a verdade, exatamente o defeito que este projeto
existe para combater.

Por isso `Transcricao.tem_tempo` existe e a API o respeita: sem horario, a
analise entrega o que de fato mediu -- classificacao por mensagem, emocao,
ironia e peso de palavra, tudo derivado so do texto -- e NAO entrega nota da
conversa. A ausencia da nota e a resposta honesta, e vem com o motivo escrito.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from fraus.modelos import Autor, Mensagem
from fraus.seguranca.pii import censurar_pii

# Como cada papel costuma aparecer escrito. A chave e o autor canonico.
ALIASES: dict[Autor, tuple[str, ...]] = {
    "cliente": ("cliente", "client", "consumidor", "usuario", "usuário", "user", "visitante"),
    "bot": ("bot", "robo", "robô", "automatico", "automático", "atendimento automatico",
            "atendimento automático", "chatbot", "assistente", "sistema"),
    "humano": ("humano", "atendente", "agente", "operador", "suporte", "analista", "consultor"),
}

# `Cliente: texto` / `[10:03] Atendente: texto` / `10:03:15 - Bot: texto`
LINHA = re.compile(
    r"^\s*(?:[\[\(]?\s*(?P<hora>\d{1,2}:\d{2}(?::\d{2})?)\s*[\]\)]?\s*[-–—]?\s*)?"
    r"(?P<autor>[^:\n]{1,40}?)\s*:\s*(?P<texto>.*)$"
)


@dataclass
class Transcricao:
    mensagens: list[Mensagem]
    tem_tempo: bool
    rotulos_ignorados: list[str]


def _autor_de(rotulo: str) -> Autor | None:
    """Mapeia o rotulo escrito para o autor canonico, ou None se nao reconhecer.

    None, e nao um chute em "cliente": rotular fala de atendente como cliente
    faria o classificador -- treinado em texto de cliente -- pontuar o roteiro
    da empresa, e essa fala entraria nas features de texto da conversa.
    """
    limpo = re.sub(r"[*_#>\s]+", " ", rotulo).strip().lower()
    if not limpo:
        return None
    for canonico, formas in ALIASES.items():
        for forma in formas:
            if limpo == forma or limpo.startswith(forma + " ") or limpo.endswith(" " + forma):
                return canonico
    return None


def ler(texto: str, inicio: datetime) -> Transcricao:
    """Extrai as mensagens de uma transcricao em prosa.

    `inicio` ancora a conversa no tempo. Quando a transcricao TEM horarios, eles
    sao aplicados sobre a data de `inicio` (o relogio vira o instante real).
    Quando nao tem, cada mensagem recebe `inicio` mais um segundo por posicao --
    o suficiente para a ordem existir e o modelo canonico aceitar, e `tem_tempo`
    fica falso para que ninguem confunda isso com medicao.

    Linha sem `Autor:` reconhecido e tratada como CONTINUACAO da mensagem
    anterior. Transcricao de Word quebra paragrafo no meio da fala o tempo
    todo; comecar mensagem nova a cada linha picaria a fala do cliente em
    pedacos e cada pedaco viraria uma predicao separada.
    """
    mensagens: list[Mensagem] = []
    horas: list[str | None] = []
    ignorados: list[str] = []

    for linha in texto.splitlines():
        if not linha.strip():
            continue

        achado = LINHA.match(linha)
        autor = _autor_de(achado.group("autor")) if achado else None

        if autor is None:
            if mensagens:
                # Continuacao da fala anterior. Censura aqui tambem: esta
                # linha concatena a UM `Mensagem` ja construido, e censurar
                # so na construcao original (abaixo) deixaria passar PII que
                # caia numa linha de continuacao -- a armadilha que esta task
                # existe para fechar. Qualquer origem NOVA de dado real
                # precisa da mesma chamada.
                anterior = mensagens[-1]
                mensagens[-1] = anterior.model_copy(
                    update={
                        "texto": censurar_pii(f"{anterior.texto}\n{linha.strip()}")
                    }
                )
            elif achado and achado.group("autor").strip():
                ignorados.append(achado.group("autor").strip()[:40])
            continue

        conteudo = achado.group("texto").strip()
        if not conteudo:
            continue

        # `Mensagem` nasce aqui -- ponto principal de construcao de dado real
        # de cliente neste modulo. Censura tambem no ponto de continuacao
        # acima, senao PII que cai numa segunda linha de fala passa direto.
        mensagens.append(
            Mensagem(autor=autor, texto=censurar_pii(conteudo), enviada_em=inicio)
        )
        horas.append(achado.group("hora"))

    tem_tempo = any(hora is not None for hora in horas)

    ajustadas = []
    for posicao, mensagem in enumerate(mensagens):
        hora = horas[posicao] if posicao < len(horas) else None
        if tem_tempo and hora:
            partes = [int(p) for p in hora.split(":")]
            enviada_em = inicio.replace(
                hour=partes[0],
                minute=partes[1],
                second=partes[2] if len(partes) > 2 else 0,
                microsecond=0,
            )
        else:
            # Ordem sem medicao. `tem_tempo` diz a verdade sobre isto.
            enviada_em = inicio + timedelta(seconds=posicao)
        ajustadas.append(mensagem.model_copy(update={"enviada_em": enviada_em}))

    # Horario que "volta" atravessou a meia-noite: soma um dia para a ordem nao
    # inverter e a latencia nao ficar negativa.
    corrigidas: list[Mensagem] = []
    dias = 0
    for posicao, mensagem in enumerate(ajustadas):
        if tem_tempo and posicao > 0 and mensagem.enviada_em + timedelta(days=dias) < corrigidas[-1].enviada_em:
            dias += 1
        corrigidas.append(
            mensagem.model_copy(update={"enviada_em": mensagem.enviada_em + timedelta(days=dias)})
        )

    return Transcricao(
        mensagens=corrigidas, tem_tempo=tem_tempo, rotulos_ignorados=ignorados
    )
