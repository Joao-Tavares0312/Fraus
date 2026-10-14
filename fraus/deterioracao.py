"""Trajetoria de deterioracao numa conversa ENCERRADA: retrospectiva, em lote.

Le os scores por prefixo que `Motor.scores_do_replay` ja produz -- cada um so
com as falas que ja tinham ocorrido -- e acha a VIRADA: a primeira mensagem a
partir da qual a estimativa fica detratora (faixa vigente, por parametro) e
nao volta ate o fim. O lead time e quantas mensagens e quanto tempo havia
entre a virada e o fim.

E HIPOTETICO E RETROSPECTIVO. Nao e alerta, nao roda durante o atendimento
(Conformidade, regra 3) e nada e gravado (invariante 5). Prefixo sem sinal do
cliente tem score `None`, que nao quebra a sequencia nem vira zero.

A virada existe se e so se o ultimo score definido e detrator: ela NAO aumenta
o recall sobre o score final. O que ela acrescenta e o lead time.
Spec: docs/superpowers/specs/2026-10-14-e6-tema-e-deterioracao-design.md
"""

from fraus.indicadores import categoria_nps

ROTULO_DETERIORACAO = "retrospectivo: lead time hipotético, não alerta"
CRITERIO_DETERIORACAO = (
    "primeira mensagem a partir da qual a estimativa por prefixo fica detratora "
    "(faixa vigente) e não volta até o fim"
)
MOTIVO_SEM_SINAL = "sem sinal do cliente"
MOTIVO_NAO_TERMINOU = "não terminou detratora"


def indice_de_virada(scores, abaixo) -> int | None:
    virada = None
    for indice, score in enumerate(scores):
        if score is None:
            continue
        if abaixo(score):
            if virada is None:
                virada = indice
        else:
            virada = None
    return virada


def deterioracao(scores, conversa, faixas) -> dict:
    base = {"criterio": CRITERIO_DETERIORACAO, "rotulo": ROTULO_DETERIORACAO}
    vazio = {"indice_virada": None, "falas_ate_o_fim": None, "segundos_ate_o_fim": None}
    if all(s is None for s in scores):
        return {**base, **vazio, "motivo": MOTIVO_SEM_SINAL}
    virada = indice_de_virada(scores, lambda s: categoria_nps(s, faixas) == "detrator")
    if virada is None:
        return {**base, **vazio, "motivo": MOTIVO_NAO_TERMINOU}
    fim = conversa.encerrada_em or conversa.mensagens[-1].enviada_em
    return {**base, "indice_virada": virada,
            "falas_ate_o_fim": len(conversa.mensagens) - 1 - virada,
            "segundos_ate_o_fim": (fim - conversa.mensagens[virada].enviada_em).total_seconds(),
            "motivo": None}
