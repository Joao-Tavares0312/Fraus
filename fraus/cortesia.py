"""Fala que e so formula de cortesia -- e por isso nao diz nada sobre satisfacao.

"ok, obrigado" fecha atendimento bom e atendimento ruim. Medido em 15/09/2026
(`docs/cartao-do-modelo.md`), o Fraus lia essas formulas como satisfacao: "valeu"
sozinho saia score 93,2, promotor; a cabeca de emocao lia "ok, obrigado" como
alegria 0,98. A causa e de corpus (o mapeamento do GoEmotions para as seis de
Ekman juntou `gratitude` com `joy`), e retreinar a emocao e o conserto de
verdade. Ate la, a decisao do projeto: conversa em que TODA fala do cliente e
formula de cortesia nao tem sinal -- `score: None`, invariante 2.

LISTA FECHADA, E CONSERVADORA DE PROPOSITO. So casa a fala INTEIRA, depois de
tirar caixa, acento e pontuacao. "valeu, resolveu na hora" tem conteudo e segue
pontuada; "obrigado por nada" tambem. Errar para este lado deixa passar uma
cortesia como sinal (o comportamento de antes); errar para o outro apagaria a
nota de quem disse alguma coisa.

Sem dependencia de `fraus.modelos`: e ele que importa daqui.
"""

import unicodedata

FORMULAS_DE_CORTESIA = frozenset(
    {
        "ok", "okay", "certo", "entendi", "entendido", "beleza", "blz", "tudo bem",
        "ta", "ta bom", "ta bom entao", "ta certo", "ok entao", "certo entendi",
        "obrigado", "obrigada", "obg", "brigado", "brigada", "muito obrigado",
        "muito obrigada", "ok obrigado", "ok obrigada", "ok valeu", "valeu",
        "vlw", "valeu obrigado", "so isso", "so isso mesmo", "so isso mesmo valeu",
        "so isso obrigado", "so isso obrigada",
    }
)


def normalizar_fala(texto: str) -> str:
    """Minuscula, sem acento, pontuacao vira espaco, espacos colapsados."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto.lower())
        if not unicodedata.combining(c)
    )
    limpo = "".join(c if c.isalnum() or c.isspace() else " " for c in sem_acento)
    return " ".join(limpo.split())


def e_so_cortesia(texto: str) -> bool:
    return normalizar_fala(texto) in FORMULAS_DE_CORTESIA
